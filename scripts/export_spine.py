"""Export the v0 map-spine artifacts from indiana_app into the repo's data/ tree.

⛔ THIS SCRIPT AND export_sites_exact.py BOTH WRITE data/sites/*.geojson.gz, AND THEY DISAGREE.
This one carries the v1 `has_si_signal` — about 847,400 flagged, 99% of it empty land.
export_sites_exact.py carries the v2 flag: 24,275, non-residential and severity-gated.
WHICHEVER RUNS LAST WINS.

Running this on 2026-08-17 silently reverted the shipped payload to the old flag. Nothing errored
and no panel went blank; the map would simply have shown 847,403 "seller-intent" parcels, almost
all of them vacant land. `scripts/checkpoint.py` caught it on the next run by comparing the
payload against the warehouse — which is the entire reason that check exists.

**AFTER RUNNING THIS: run scripts/export_sites_exact.py, THEN scripts/checkpoint.py.**
Treat the site files this script emits as the superseded generation.

Outputs (all gzipped; the client decompresses natively via DecompressionStream):
  data/counties.geojson.gz     92 county polygons + full rollup stats (100% of parcels counted)
  data/sites/{fips}.geojson.gz per-county class-union parcels, EXACT geometry, full attributes
  data/state_summary.json      denominators, cannot-assess ledger, per-table provenance, build stamp

Class union (explicit, user-visible in the app): occ_group='ci' OR mw@4>=25 OR has_si_signal.
Parcels outside the union are fully counted in county aggregates — aggregation, not truncation;
individual rendering for ALL parcels is the flagged PMTiles upgrade.
"""
import json, gzip, os, sys, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

os.makedirs(os.path.join(REPO, "data", "sites"), exist_ok=True)

def jdefault(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)

def round_coords(x):
    if isinstance(x, float): return round(x, 7)
    if isinstance(x, list): return [round_coords(v) for v in x]
    return x

# ---- counties.geojson.gz ----
q_counties = f"""
SELECT c.county_fips_code AS fips, r.county_name, ST_ASGEOJSON(c.county_geom) AS gj,
       r.parcels, r.with_building, r.ci, r.ge25mw, r.si_sites, r.class_union,
       CAST(r.mw_potential_at_4 AS INT64) AS mw_potential_at_4,
       -- ⭐ G163(c): the SI signal whose publisher grain is a COUNTY, so it reaches a reader at the
       -- grain it actually has instead of showing as a bare zero on the signal list.
       -- ⚠ CONTEXT, NOT A FINDING, and it must never be merged into si_sites.
       -- ⛔ THE EVICTION KEYS WERE HERE AND WERE REMOVED, 2026-08-22b. `evictions_2022_2025` and
       -- `foreclosures_2022_2025` shipped for one build. The Indiana courts publish no
       -- commercial/residential split, so ~278,645 mostly-RESIDENTIAL filings were riding under a
       -- signal named `D17_commercial_eviction`. Operator's rule: only non-residential reaches the
       -- application. Removed from the table, the payload AND the popup in one change — G146 is
       -- the worked example of why a control and its data come out together.
       cc.rail_abandonment_dockets, cc.rail_abandonment_latest,
       -- ⭐ G170 THE COVERAGE MASK. Without this a county with no D12_code_violation looks
       -- exactly like a county we searched and found clean. It is neither: D12 comes from
       -- Indianapolis's own portal and reaches 2 counties, so in the other 90 we did not
       -- LOOK. 56.8% of all signal-county cells are not-covered and every one of them
       -- currently renders as 'none'. This is the unpublished-rate-as-zero defect at county
       -- grain, and G51's third state is the fix.
       cov.si_signals_searched, cov.si_signals_not_covered, cov.si_signals_with_hits
FROM `bigquery-public-data.geo_us_boundaries.counties` c
JOIN `{DS}.in_county_rollup` r ON r.county_fips = c.county_fips_code
LEFT JOIN (
  SELECT county_fips,
         MAX(IF(signal='D25_rail_abandonment', CAST(value_num AS INT64), NULL))
           AS rail_abandonment_dockets,
         MAX(IF(signal='D25_rail_abandonment', CAST(last_event_date AS STRING), NULL))
           AS rail_abandonment_latest
  FROM `{DS}.in_si_county_context` GROUP BY 1
) cc ON cc.county_fips = c.county_fips_code
LEFT JOIN (
  SELECT county_fips,
         COUNTIF(coverage_state != 'not_covered')   AS si_signals_searched,
         COUNTIF(coverage_state  = 'not_covered')   AS si_signals_not_covered,
         COUNTIF(coverage_state  = 'covered_with_hits') AS si_signals_with_hits
  FROM `{DS}.in_si_signal_county_coverage` GROUP BY 1
) cov ON cov.county_fips = c.county_fips_code
WHERE c.state_fips_code = '18'"""
feats = []
for r in client.query(q_counties).result():
    g = round_coords(json.loads(r.gj))
    props = {k: v for k, v in dict(r).items() if k != "gj"}
    feats.append({"type": "Feature", "properties": props, "geometry": g})
with gzip.open(os.path.join(REPO, "data", "counties.geojson.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump({"type": "FeatureCollection", "features": feats}, f, separators=(",", ":"), default=jdefault)
print(f"counties.geojson.gz: {len(feats)} features", flush=True)

# ---- per-county site files ----
q_sites = f"""
SELECT sc.county_fips, s.* EXCEPT(parcel_geog), ST_ASGEOJSON(s.parcel_geog) AS gj
FROM `{DS}.in_sites` s
JOIN `{DS}.in_sites_county` sc USING (parcel_source, parcel_key)
WHERE s.occ_group='ci' OR s.mw_datacenter_4_per_acre>=25 OR s.has_si_signal
ORDER BY sc.county_fips"""
it = client.query(q_sites).result(page_size=20000)
cur_fips, buf, files, total = None, [], 0, 0

def flush(fips, buf):
    p = os.path.join(REPO, "data", "sites", f"{fips}.geojson.gz")
    with gzip.open(p, "wt", encoding="utf-8", compresslevel=6) as f:
        json.dump({"type": "FeatureCollection", "features": buf}, f, separators=(",", ":"), default=jdefault)
    print(f"  sites/{fips}.geojson.gz: {len(buf):,} features", flush=True)

for r in it:
    d = dict(r)
    fips = d.pop("county_fips")
    gj = d.pop("gj")
    if gj is None:
        continue
    if fips != cur_fips and cur_fips is not None:
        flush(cur_fips, buf); files += 1; buf = []
    cur_fips = fips
    geom = round_coords(json.loads(gj))
    buf.append({"type": "Feature", "properties": d, "geometry": geom})
    total += 1
if buf:
    flush(cur_fips, buf); files += 1
print(f"site files: {files} counties, {total:,} features", flush=True)

# ---- state_summary.json ----
tot = list(client.query(f"""
SELECT COUNT(*) AS all_parcels,
       COUNTIF(parcel_geog IS NULL) AS no_geometry,
       COUNTIF(occ_group='ci') AS ci,
       COUNTIF(mw_datacenter_4_per_acre>=25) AS ge25,
       COUNTIF(has_si_signal) AS si,
       COUNTIF(occ_group='ci' OR mw_datacenter_4_per_acre>=25 OR has_si_signal) AS class_union
FROM `{DS}.in_sites`"""))[0]
unassigned = list(client.query(f"""
SELECT (SELECT COUNT(*) FROM `{DS}.in_sites` WHERE parcel_geog IS NOT NULL)
     - (SELECT COUNT(*) FROM `{DS}.in_sites_county`) AS n"""))[0].n
si_unmapped = list(client.query(f"""
-- reads the CLIP, not energy. An export is on the path to what the user sees, so the app must
-- be rebuildable from indiana_app alone; build scripts may read energy, exports may not.
SELECT IFNULL(SUM(rows_), 0) AS n FROM `{DS}.in_si_plottability`
WHERE geom_kind = 'none'"""))[0].n
reg = [dict(r) for r in client.query(
    f"SELECT table_name, source, n_rows, CAST(built_at AS STRING) AS built_at FROM `{DS}._registry` "
    f"QUALIFY ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY built_at DESC)=1 ORDER BY table_name")]
summary = {
    "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "state": "IN",
    "totals": dict(tot),
    "cannot_assess": {
        "parcels_without_geometry": tot.no_geometry,
        "parcels_geometry_but_no_county": unassigned,
        "si_observations_unmappable": si_unmapped,
        "note": "listed, never rendered as zero or dropped",
    },
    "class_union_definition": "occ_group='ci' OR mw_datacenter_4_per_acre>=25 OR has_si_signal",
    "defaults": {"mw_per_acre_datacenter": 4, "mw_per_acre_bess": 10, "note": "defaults only, user-adjustable"},
    "provenance": reg,
}
with open(os.path.join(REPO, "data", "state_summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=1, default=jdefault)
print("state_summary.json written", flush=True)
print("EXPORT COMPLETE", flush=True)
