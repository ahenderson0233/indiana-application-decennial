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
# stdout must survive its own output: this console is cp1252 and characters like U+2248/U+2192/U+2717 raise
# UnicodeEncodeError from print() itself. The honesty audit once crashed on its own
# FAILURE path for exactly this reason. Degrade the glyph, never the run.
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
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
       -- G29: EXACT parcel-to-asset distance, measured polygon-to-geometry in BigQuery.
       -- The map computes these client-side from the parcel's FIRST VERTEX, which always
       -- overstates and can never return 0. Shipping the exact value lets app.js prefer it and
       -- fall back to its approximation only where one was never computed (e.g. uploaded rows).
       d.line_mi AS x_line_mi, d.line_kv AS x_line_kv, d.line_on_parcel AS x_line_on,
       d.sub_mi  AS x_sub_mi,  d.sub_kv  AS x_sub_kv,  d.sub_name AS x_sub_name,
       -- G29 final piece: EXACT bus distance, both directions, never fused. The map console was
       -- the last surface still measuring this client-side from the parcel's first vertex. These
       -- come from in_screener_candidates, which has carried exact ST_DISTANCE per direction for
       -- all 532,868 candidates since it was built -- the screener was always right.
       b.wd_mi  AS x_bus_wd_mi,  b.wd_bus  AS x_bus_wd_name,
       b.wd_kv  AS x_bus_wd_kv,  b.wd_mw   AS x_bus_wd_mw,
       b.inj_mi AS x_bus_inj_mi, b.inj_bus AS x_bus_inj_name,
       b.inj_kv AS x_bus_inj_kv, b.inj_mw  AS x_bus_inj_mw,
       -- WATER, at parcel grain and by the same exact method (G12d). Cooling is a first-order
       -- constraint for a hyperscale DC, and this is the half of G12 that never reached a surface.
       w.water_mi AS x_wat_mi, w.water_on_parcel AS x_wat_on, w.water_name AS x_wat_name,
       w.water_kind AS x_wat_kind, w.nearest_is_great_lake AS x_wat_greatlake,
       ST_ASGEOJSON(s.parcel_geog) AS gj
FROM `{DS}.in_sites` s
JOIN `{DS}.in_sites_county` sc USING (parcel_source, parcel_key)
LEFT JOIN `{DS}.in_site_gates` g USING (parcel_source, parcel_key)
LEFT JOIN `{DS}.in_si_sites_flags_v2` f USING (parcel_source, parcel_key)
LEFT JOIN `{DS}.in_asset_distance_parcel` d USING (parcel_source, parcel_key)
LEFT JOIN `{DS}.in_water_distance_parcel`  w USING (parcel_source, parcel_key)
LEFT JOIN `{DS}.in_screener_candidates`     b USING (parcel_source, parcel_key)
WHERE s.occ_group='ci' OR s.mw_datacenter_4_per_acre>=25
   OR s.has_vacancy_signal OR s.has_si_signal OR IFNULL(f.has_si_signal, FALSE)
ORDER BY sc.county_fips"""
dry = client.query(q, job_config=bigquery.QueryJobConfig(dry_run=True))
print(f"dry-run: {dry.total_bytes_processed/1e9:.1f} GB", flush=True)

def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)

# COORDINATE PRECISION. ⚠ This function had a silent defect for its whole life: it was called as
# rc(json.loads(gj)) — i.e. with a GeoJSON geometry, which is a **dict** — and it handled only float
# and list, so it hit `return x` and returned the geometry COMPLETELY UNROUNDED. The rounding the
# author intended never once ran, and the shipped files carry up to 16 decimal places.
# Measured consequence: data/sites/ is 334 MB, and 45% of that is precision nobody can use.
#
# 6 decimals is ~0.11 m at Indiana's latitude. County assessor parcel boundaries are not accurate to
# a metre, let alone to the 0.01 mm that 13 decimals implies, so this discards no real information —
# it discards the false precision of a float printed in full. The dict branch is the fix.
NDP = 6
def rc(x):
    if isinstance(x, float): return round(x, NDP)
    if isinstance(x, list):  return [rc(v) for v in x]
    if isinstance(x, dict):  return {k: rc(v) for k, v in x.items()}   # <- the branch that was missing
    return x

# The SI detail only means something on a flagged parcel. Emitting a dozen nulls on 1.2M
# unflagged features would add megabytes to the payload and say nothing — an absent key here
# reads as "no admitted signal", which is the truth, not as "cannot assess".
SI_DETAIL = ("si_signal_types", "si_signal_events", "si_signals", "si_first_event_date",
             "si_last_event_date", "si_events_3y", "si_events_5y", "si_events_10y",
             "si_keying", "si_date_basis", "si_excl_resid", "si_excl_lowsev")

# G29 exact-distance keys. in_asset_distance_parcel covers the 532,868 SCREENER CANDIDATES, not all
# ~1.2M rendered parcels, so most features have no exact value. An absent key is the honest encoding
# of "not computed for this parcel" and lets app.js fall back to its own measurement; emitting six
# nulls on 700k features would add megabytes and say nothing.
X_DIST = ("x_line_mi", "x_line_kv", "x_line_on", "x_sub_mi", "x_sub_kv", "x_sub_name",
          "x_wat_mi", "x_wat_on", "x_wat_name", "x_wat_kind", "x_wat_greatlake",
          "x_bus_wd_mi", "x_bus_wd_name", "x_bus_wd_kv", "x_bus_wd_mw",
          "x_bus_inj_mi", "x_bus_inj_name", "x_bus_inj_kv", "x_bus_inj_mw")

counts, no_geom, n_si, n_exact, n_online, n_wat, n_waton = {}, 0, 0, 0, 0, 0, 0
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
    if d.get("x_line_mi") is not None:
        n_exact += 1
        if d.get("x_line_on"): n_online += 1
    if d.get("x_wat_mi") is not None:
        n_wat += 1
        if d.get("x_wat_on"): n_waton += 1
    for k in X_DIST:                      # drop the key entirely rather than ship a null
        if d.get(k) is None: d.pop(k, None)
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
print(f"carrying EXACT G29 grid distances: {n_exact:,} features, of which "
      f"{n_online:,} have a transmission line PHYSICALLY ON the parcel (0.0 mi) — the case the "
      f"map's first-vertex method reported as ~0.55 mi", flush=True)
print(f"carrying EXACT water distance (G12d): {n_wat:,} features, of which {n_waton:,} have a "
      f"water SOURCE physically on the parcel", flush=True)
mb = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT) if f.endswith(".gz")) / 1e6
print(f"data/sites/ on disk: {mb:,.0f} MB at {NDP} decimal places "
      f"(~{0.11 if NDP==6 else 0.011:.2f} m; assessor boundaries are not accurate to that)", flush=True)
if len(counts) != 92:
    print(f"WARNING: wrote {len(counts)} counties, expected 92 — the set is NOT consistent.", flush=True)
