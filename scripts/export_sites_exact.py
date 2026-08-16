"""Re-export data/sites/*.geojson.gz for ALL 92 counties from ONE query snapshot, carrying
the exact-intersection acreage columns (exact_parcel_acres / exact_outdoor_acres /
exact_bldg_acres / footprints_intersecting / mw_*_exact / outdoor_acres_method).

WHY ONE PASS: a prior run of build_site_gates.py's export stopped at 18087 (44 of 92),
leaving two generations of site file on disk. Mixing generations is the §AC partial-swap
hazard — a user comparing two counties would be comparing two different instruments. This
script rewrites all 92 from a single snapshot so the set is internally consistent, and
refuses to write anything if the source columns are missing.

Export-only: it does NOT rebuild in_site_gates (build_site_gates.py owns that table), so it
creates no BigQuery table and needs no _registry row. Read-only against the warehouse.
Idempotent — safe to re-run. Dry-run measured 2.2 GB (~$0.01).
"""
import json, gzip, os, datetime, decimal, sys
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
OUT = os.path.join(REPO, "data", "sites")
EXACT = ["exact_parcel_acres", "exact_bldg_acres", "exact_outdoor_acres",
         "footprints_intersecting", "mw_datacenter_4_per_acre_exact",
         "mw_bess_10_per_acre_exact", "outdoor_acres_method"]
client = bigquery.Client(project="energy-platfrom")

# --- guard: never half-write a generation. If the source lacks the columns, stop. ---
cols = {s.name for s in client.get_table(f"{DS}.in_sites").schema}
missing = [c for c in EXACT if c not in cols]
if missing:
    sys.exit(f"ABORT: in_sites is missing {missing} — the exact-acres build has not landed. "
             f"Nothing written; the on-disk set is left untouched.")
print(f"in_sites carries all {len(EXACT)} exact-family columns", flush=True)

# --- guard: the SI flag on screen must be v2, never the vacancy flag it used to be. ---
try:
    client.get_table(f"{DS}.in_si_sites_flags_v2")
except Exception:
    sys.exit("ABORT: in_si_sites_flags_v2 is absent — run scripts/build_si_signal_v2.py first. "
             "Exporting without it would ship has_si_signal as a vacancy flag again.")
print("in_si_sites_flags_v2 present — SI columns come from v2", flush=True)

# in_sites' own SI columns are the SUPERSEDED generation (v1 has_si_signal was 99.2% empty land,
# because its only parcel-keyed input was footprint absence). They are EXCEPTed here so the
# payload never carries two rival truths for one field — the §AC partial-swap hazard.
V1_SI = ("has_si_signal", "si_signal_types", "si_signal_events", "si_signals", "si_last_event_date")

# The render predicate is deliberately ADDITIVE: everything that rendered before still renders.
# has_vacancy_signal keeps vacant land on screen (operator: still material for BESS siting, just
# not as an intent signal), and f.has_si_signal brings in the parcels v1 could not see.
q = f"""
SELECT sc.county_fips, s.* EXCEPT(parcel_geog, {", ".join(V1_SI)}),
       g.sfha_flood, g.wetland_on_parcel, g.protected_land, g.bonus_kinds,
       IFNULL(f.has_si_signal, FALSE) AS has_si_signal,
       IFNULL(f.si_signal_types, 0)   AS si_signal_types,
       IFNULL(f.si_signal_events, 0)  AS si_signal_events,
       f.si_signals, f.si_first_event_date, f.si_last_event_date,
       IFNULL(f.si_events_3y, 0)      AS si_events_3y,
       IFNULL(f.si_events_5y, 0)      AS si_events_5y,
       IFNULL(f.si_events_10y, 0)     AS si_events_10y,
       f.si_keying, f.si_date_basis,
       IFNULL(f.si_excluded_residential, 0)  AS si_excl_resid,
       IFNULL(f.si_excluded_low_severity, 0) AS si_excl_lowsev,
       ST_ASGEOJSON(s.parcel_geog) AS gj
FROM `{DS}.in_sites` s
JOIN `{DS}.in_sites_county` sc USING (parcel_source, parcel_key)
LEFT JOIN `{DS}.in_site_gates` g USING (parcel_source, parcel_key)
LEFT JOIN `{DS}.in_si_sites_flags_v2` f USING (parcel_source, parcel_key)
WHERE s.occ_group='ci' OR s.mw_datacenter_4_per_acre>=25
   OR s.has_vacancy_signal OR s.has_si_signal OR IFNULL(f.has_si_signal, FALSE)
ORDER BY sc.county_fips"""
dry = client.query(q, job_config=bigquery.QueryJobConfig(dry_run=True))
print(f"dry-run: {dry.total_bytes_processed/1e9:.1f} GB", flush=True)

def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)
def rc(x):
    if isinstance(x, float): return round(x, 7)
    if isinstance(x, list): return [rc(v) for v in x]
    return x

# The SI detail only means something on a flagged parcel. Emitting a dozen nulls on 1.2M
# unflagged features would add megabytes to the payload and say nothing — an absent key here
# reads as "no admitted signal", which is the truth, not as "cannot assess".
SI_DETAIL = ("si_signal_types", "si_signal_events", "si_signals", "si_first_event_date",
             "si_last_event_date", "si_events_3y", "si_events_5y", "si_events_10y",
             "si_keying", "si_date_basis", "si_excl_resid", "si_excl_lowsev")

counts, no_geom, n_si = {}, 0, 0
def flush(fips, buf):
    with gzip.open(os.path.join(OUT, f"{fips}.geojson.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
        json.dump({"type": "FeatureCollection", "features": buf}, f, separators=(",", ":"), default=jd)
    counts[fips] = len(buf)
    print(f"  {fips}: {len(buf):,}", flush=True)

it = client.query(q).result(page_size=20000)
cur, buf, total = None, [], 0
for r in it:
    d = dict(r); fips = d.pop("county_fips"); gj = d.pop("gj")
    if gj is None: no_geom += 1; continue
    if d.get("has_si_signal"): n_si += 1
    else:
        for k in SI_DETAIL: d.pop(k, None)
    if fips != cur and cur is not None:
        flush(cur, buf); buf = []
    cur = fips
    buf.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
    total += 1
if buf: flush(cur, buf)

with_exact = sum(1 for f in os.listdir(OUT) if f.endswith(".geojson.gz"))
print(f"\nRE-EXPORT COMPLETE: {len(counts)} counties written, {total:,} features, "
      f"{no_geom} skipped for null geometry; {with_exact} files on disk", flush=True)
print(f"carrying an ADMITTED seller-intent signal (v2, non-residential, severity-gated): "
      f"{n_si:,} features", flush=True)
if len(counts) != 92:
    print(f"WARNING: wrote {len(counts)} counties, expected 92 — the set is NOT consistent.", flush=True)
