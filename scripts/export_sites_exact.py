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

q = f"""
SELECT sc.county_fips, s.* EXCEPT(parcel_geog), g.sfha_flood, g.wetland_on_parcel,
       g.protected_land, g.bonus_kinds, ST_ASGEOJSON(s.parcel_geog) AS gj
FROM `{DS}.in_sites` s
JOIN `{DS}.in_sites_county` sc USING (parcel_source, parcel_key)
LEFT JOIN `{DS}.in_site_gates` g USING (parcel_source, parcel_key)
WHERE s.occ_group='ci' OR s.mw_datacenter_4_per_acre>=25 OR s.has_si_signal
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

counts, no_geom = {}, 0
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
    if fips != cur and cur is not None:
        flush(cur, buf); buf = []
    cur = fips
    buf.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
    total += 1
if buf: flush(cur, buf)

with_exact = sum(1 for f in os.listdir(OUT) if f.endswith(".geojson.gz"))
print(f"\nRE-EXPORT COMPLETE: {len(counts)} counties written, {total:,} features, "
      f"{no_geom} skipped for null geometry; {with_exact} files on disk", flush=True)
if len(counts) != 92:
    print(f"WARNING: wrote {len(counts)} counties, expected 92 — the set is NOT consistent.", flush=True)
