"""Parcel-to-water DISTANCE, against real geometry. Writes `in_water_distance_parcel`.

⚠⚠ THIS SCRIPT WAS DANGEROUS AND HAS BEEN REPOINTED. Read this before running it.

The first version measured against `energy.nhd_waterbody.SHAPE` and `energy.nhd_flowline.SHAPE`.
**Both of those columns are NULL on every row nationally** — verified 2026-08-17: 0 of 39,542,980
flowlines and 0 of 10,431,981 waterbodies carry geometry. So `ST_DWITHIN` matched nothing and the
script produced a table where every parcel had NULL water, **failing without erroring**. It ran, it
reported success, and it was wrong.

⛔ WORSE: it wrote to `in_water_parcel`, which is now the parcel **water-STRESS** table
(basin_id, stress_score, depletion_score …, 532,868 rows, built from `in_screener_candidates` x
`energy.water_aqueduct`). Running the old script would have **replaced a working stress table with
an all-NULL distance table** — a silent regression on a table the front end consumes.
This version writes to **`in_water_distance_parcel`** and never touches `in_water_parcel`.

REAL GEOMETRY NOW EXISTS, in indiana_app:
    in_nhd_flowline_geom   160,128 named rivers/streams (ftype 460), column `geog`
    in_nhd_waterbody_geom    6,415 waterbodies, column `geog`, with a decoded `water_role`:
                             source     = 4,276 Reservoir + 1,460 LakePond (>=10 ha)
                             constraint =   679 SwampMarsh
⭐ `water_role = 'source'` IS THE FILTER THAT MATTERS. A swamp is not a water supply. Counting the
679 marshes as sources would tell a developer there is water to draw where there is a wetland to
permit around — the opposite of the truth, and on the same parcel.

⚠ LAKE MICHIGAN IS A LEGITIMATE MEMBER at 57,743 km². It will dominate "nearest lake" in Lake and
Porter counties and that is correct, not a bug — but it is also a Great Lake with its own compact
and withdrawal regime, so `water_name` and `water_area_sqkm` ride on every row and the size is never
hidden behind a bare distance.

⭐ THIS IS ALSO G29 DONE RIGHT: `ST_DISTANCE(parcel_geog, geog)` between real geometries, so a river
running THROUGH a parcel returns **0.0** — not the ~0.55 mi the map's client-side first-vertex
method reports for the same case.

⚠ D85 (`parcels_in/080500000047000018`, the inverted whole-Earth polygon) is excluded BY KEY before
any spatial work. Left in, it is "within 0 m" of every river in the state.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
D85 = "080500000047000018"
RADIUS_M = 16093          # 10 miles. Past that, piping water is its own project.
TARGET = "in_water_distance_parcel"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{DS}.{TARGET}` AS
WITH cand AS (
  SELECT c.parcel_source, c.parcel_key, c.county_fips, c.county_name, s.parcel_geog
  FROM `{DS}.in_screener_candidates` c
  JOIN `{DS}.in_sites` s USING (parcel_source, parcel_key)
  WHERE s.parcel_geog IS NOT NULL AND c.parcel_key != '{D85}'
),
-- SOURCES ONLY. water_role='source' keeps reservoirs and lakes and drops the 679 SwampMarsh
-- polygons: a wetland is something to permit around, not something to draw from.
src AS (
  SELECT gnis_name AS nm, ftype_label AS kind, areasqkm, geog
  FROM `{DS}.in_nhd_waterbody_geom` WHERE water_role = 'source' AND geog IS NOT NULL
  UNION ALL
  SELECT gnis_name AS nm, 'River/Stream' AS kind, CAST(NULL AS FLOAT64) AS areasqkm, geog
  FROM `{DS}.in_nhd_flowline_geom` WHERE water_role = 'source' AND geog IS NOT NULL
),
near AS (
  SELECT c.parcel_source, c.parcel_key,
         ARRAY_AGG(STRUCT(s.nm, s.kind, s.areasqkm, ST_DISTANCE(c.parcel_geog, s.geog) AS m)
                   ORDER BY ST_DISTANCE(c.parcel_geog, s.geog) LIMIT 1)[OFFSET(0)] AS w
  FROM cand c
  JOIN src s ON ST_DWITHIN(c.parcel_geog, s.geog, {RADIUS_M})
  GROUP BY 1, 2
)
SELECT c.parcel_source, c.parcel_key, c.county_fips, c.county_name,
       n.w.nm   AS water_name,
       n.w.kind AS water_kind,
       ROUND(n.w.areasqkm, 3) AS water_area_sqkm,
       ROUND(n.w.m / 1609.344, 3) AS water_mi,
       -- the honest headline: does water physically touch this parcel?
       (n.w.m = 0) AS water_on_parcel,
       -- Lake Michigan is legitimate but is a Great Lake with its own withdrawal compact; flag it
       -- rather than let a 0.2 mi distance imply an ordinary permit.
       (n.w.areasqkm > 1000) AS nearest_is_great_lake,
       CURRENT_TIMESTAMP() AS built_at
FROM cand c
LEFT JOIN near n USING (parcel_source, parcel_key)
"""

dry = client.query(SQL, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
gb = dry.total_bytes_processed / 1024 ** 3
usd = gb / 1024 * 6.25
print(f"DRY RUN: {gb:,.1f} GiB -> approx ${usd:,.2f}")
if usd > 25 and "--force" not in _sys.argv:
    print(f"COST GATE TRIPPED at ${usd:,.2f}. Not running.")
    _sys.exit(1)

job = client.query(SQL); job.result()

m = list(client.query(f"""
SELECT COUNT(*) n, COUNT(DISTINCT CONCAT(parcel_source,'|',parcel_key)) d,
       COUNTIF(water_mi IS NOT NULL) with_water,
       COUNTIF(water_on_parcel) on_parcel,
       COUNTIF(water_mi <= 1) within_1mi,
       COUNTIF(nearest_is_great_lake) great_lake,
       COUNTIF(water_kind = 'River/Stream') rivers,
       COUNTIF(water_kind = 'Reservoir') reservoirs,
       ROUND(APPROX_QUANTILES(water_mi, 2)[OFFSET(1)], 2) median_mi
FROM `{DS}.{TARGET}`"""))[0]
fan = m.n / m.d if m.d else 0
print(f"{TARGET}: {m.n:,} rows over {m.d:,} parcels -> fan-out {fan:.3f}")
print(f"  with a water SOURCE within 10 mi : {m.with_water:,}")
print(f"  ⭐ water ON the parcel (0.0 mi)   : {m.on_parcel:,}   <- the case the map reports as ~0.55")
print(f"  within 1 mile                    : {m.within_1mi:,}")
print(f"  nearest is a river / reservoir   : {m.rivers:,} / {m.reservoirs:,}")
print(f"  nearest is a Great Lake          : {m.great_lake:,}  (Lake/Porter counties, legitimate)")
print(f"  median distance                  : {m.median_mi} mi")
assert fan < 1.01, "fan-out above 1.0 - a join duplicated parcels"
assert m.with_water > 0, "zero parcels matched - check the geometry columns are non-null"

# ---- both registries, same run ----
client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{TARGET}'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
    f"VALUES (@t,@s,@m,@n,@g,CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", TARGET),
        bigquery.ScalarQueryParameter("s", "STRING",
            f"{DS}.in_screener_candidates x {DS}.in_nhd_flowline_geom + {DS}.in_nhd_waterbody_geom"),
        bigquery.ScalarQueryParameter("m", "STRING",
            f"nearest water SOURCE within {RADIUS_M/1609.344:.0f} mi by true ST_DISTANCE against "
            f"real geometry; water_role='source' only (SwampMarsh excluded); D85 excluded by key "
            f"before any spatial work; fan-out asserted < 1.01. "
            f"RE-SCRAPE COMMAND: python scripts/build_water_parcel.py"),
        bigquery.ScalarQueryParameter("n", "INT64", int(m.n)),
        bigquery.ScalarQueryParameter("g", "FLOAT64", round(job.total_bytes_processed / 1024**3, 2)),
        bigquery.ScalarQueryParameter("no", "STRING",
            "DISTINCT FROM in_water_parcel, which holds water-STRESS scores and must not be "
            "overwritten. Exact geometry-to-geometry distance, so water crossing a parcel returns "
            "0.0 - G29 done right, unlike the map's client-side first-vertex method. "
            "water_role='source' drops 679 SwampMarsh polygons: a wetland is something to permit "
            "around, not draw from. Lake Michigan (57,743 km2) is a legitimate member and dominates "
            "nearest-lake in Lake and Porter counties - flagged by nearest_is_great_lake because a "
            "Great Lake carries its own withdrawal compact.")])).result()
print(f"registered {TARGET} in indiana_app._registry")

tb = client.get_table("energy-platfrom.energy.registry_sources")
cols = {f.name for f in tb.schema}
row = {k: v for k, v in {
    "source_name": "Indiana parcel-to-water distance (derived)",
    "endpoint": "derived - no external endpoint",
    "endpoint_kind": "derived",
    "access": "internal-derived",
    "status": f"BUILT+LOADED ({m.n:,} parcels, {m.with_water:,} with a source within 10 mi)",
    "acquisition_method": "RE-SCRAPE COMMAND: python scripts/build_water_parcel.py",
    "what_it_provides": "nearest surface-water SOURCE per candidate parcel, by true geodesic "
                        "distance against real NHD geometry; 0.0 where water crosses the parcel",
    "object_names": [TARGET],
    "geography_state": "IN",
    "measured_rows": int(m.n),
    "notes": "Supersedes an earlier version that measured against energy.nhd_*.SHAPE, which is NULL "
             "on all 50M rows nationally - it matched nothing and produced an all-NULL table without "
             "erroring. Written by the indiana_app workstream 2026-08-17; APPEND-only.",
}.items() if k in cols}
errs = client.insert_rows_json("energy-platfrom.energy.registry_sources", [row])
print(f"appended to energy.registry_sources: {errs if errs else 'ok'}")
