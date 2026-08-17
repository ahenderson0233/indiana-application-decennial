"""Parcel-grain water: how far is each candidate site from water it could actually draw from.

WHY. County totals say what the county uses. They do not say whether THIS parcel can get water,
which is the question a siting screener has to answer. Operator, 2026-08-17: *"If we can get
granular to a parcel join, that would be amazing."*

⭐ THIS IS ALSO G29 DONE RIGHT FROM THE START. Distance is `ST_DISTANCE(parcel_geog, SHAPE)` -
true geodesic distance between the two real geometries - so a river running THROUGH a parcel
returns **0.0**, not the ~0.55 mi the map's client-side first-vertex method reports. No
representative point, no centroid, no vertex sampling.

⛔ ftype CODES ARE DECODED BEFORE THEY ARE SCREENED ON. NHD ftype is a bare integer and the codes
are not interchangeable:
    436 Reservoir      -> a SOURCE
    390 LakePond       -> a SOURCE, but only if it is big enough to matter (>= 10 ha here)
    460 StreamRiver    -> a SOURCE, and named ones are the substantial ones
    466 SwampMarsh     -> a CONSTRAINT, not a source. Wetland, not water you can take.
    336 CanalDitch · 420 UndergroundConduit · 428 Pipeline · 558 ArtificialPath -> NOT sources
Screening on ftype without decoding it counts a drainage ditch as a river.

⚠ SIZE GATE, STATED RATHER THAN HIDDEN. Indiana has 186,667 waterbodies but only 2,301 are >= 10 ha
and 159 are >= 1 sq km. A farm pond is not a cooling source, so lakes below 10 ha are excluded and
that exclusion is recorded here and in the registry - it is a judgement, not a fact.

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
RADIUS_M = 16093          # 10 miles. Past that, hauling or piping water is its own project.
MIN_LAKE_SQKM = 0.1       # 10 hectares
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{DS}.in_water_parcel` AS
WITH cand AS (
  SELECT parcel_source, parcel_key, county_fips, county_name, parcel_geog
  FROM `{DS}.in_screener_candidates` c
  JOIN `{DS}.in_sites` s USING (parcel_source, parcel_key)
  WHERE s.parcel_geog IS NOT NULL AND c.parcel_key != '{D85}'
),
-- SOURCES only. Reservoirs and substantial lakes.
wb AS (
  SELECT gnis_name AS nm, areasqkm,
         CASE SAFE_CAST(ftype AS INT64) WHEN 436 THEN 'reservoir' ELSE 'lake' END AS kind,
         SHAPE AS g
  FROM `energy-platfrom.energy.nhd_waterbody`
  WHERE UPPER(IFNULL(src_state, '')) = 'IN'
    AND SAFE_CAST(ftype AS INT64) IN (436, 390)
    AND SAFE_CAST(areasqkm AS FLOAT64) >= {MIN_LAKE_SQKM}
),
-- Named rivers/streams. The unnamed 460s are mostly headwater trickles; naming is NHD's own
-- proxy for "this is a real watercourse", and it is the publisher's judgement rather than ours.
fl AS (
  SELECT gnis_name AS nm, CAST(NULL AS FLOAT64) AS areasqkm, 'river' AS kind, SHAPE AS g
  FROM `energy-platfrom.energy.nhd_flowline`
  WHERE UPPER(IFNULL(src_state, '')) = 'IN'
    AND SAFE_CAST(ftype AS INT64) = 460
    AND gnis_name IS NOT NULL
),
src AS (SELECT * FROM wb UNION ALL SELECT * FROM fl),
near AS (
  SELECT c.parcel_source, c.parcel_key,
         ARRAY_AGG(STRUCT(s.nm, s.kind, s.areasqkm,
                          ST_DISTANCE(c.parcel_geog, s.g) AS m)
                   ORDER BY ST_DISTANCE(c.parcel_geog, s.g) LIMIT 1)[OFFSET(0)] AS w
  FROM cand c
  JOIN src s ON ST_DWITHIN(c.parcel_geog, s.g, {RADIUS_M})
  GROUP BY 1, 2
)
SELECT c.parcel_source, c.parcel_key, c.county_fips, c.county_name,
       n.w.nm   AS water_name,
       n.w.kind AS water_kind,
       ROUND(n.w.areasqkm, 3) AS water_area_sqkm,
       ROUND(n.w.m / 1609.344, 3) AS water_mi,
       -- the honest headline: does water physically touch this parcel?
       (n.w.m = 0) AS water_on_parcel,
       CURRENT_TIMESTAMP() AS built_at
FROM cand c
LEFT JOIN near n USING (parcel_source, parcel_key)
"""

dry = client.query(SQL, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
gb = dry.total_bytes_processed / 1024 ** 3
usd = gb / 1024 * 6.25
print(f"DRY RUN: {gb:,.1f} GiB -> approx ${usd:,.2f}")
if usd > 25 and "--force" not in _sys.argv:
    print(f"COST GATE TRIPPED at ${usd:,.2f}. Not running. Re-run with --force if intended.")
    _sys.exit(1)

job = client.query(SQL); job.result()
m = list(client.query(f"""
SELECT COUNT(*) n, COUNT(DISTINCT CONCAT(parcel_source,'|',parcel_key)) d,
       COUNTIF(water_mi IS NOT NULL) with_water,
       COUNTIF(water_on_parcel) on_parcel,
       COUNTIF(water_mi <= 1) within_1mi,
       COUNTIF(water_kind = 'river') rivers, COUNTIF(water_kind = 'reservoir') reservoirs,
       ROUND(APPROX_QUANTILES(water_mi, 2)[OFFSET(1)], 2) median_mi
FROM `{DS}.in_water_parcel`"""))[0]
fan = m.n / m.d if m.d else 0
print(f"in_water_parcel: {m.n:,} rows over {m.d:,} parcels -> fan-out {fan:.3f}")
print(f"  with a water source within 10 mi : {m.with_water:,}")
print(f"  ⭐ water ON the parcel (0.0 mi)   : {m.on_parcel:,}   <- the case the map reports as ~0.55")
print(f"  within 1 mile                    : {m.within_1mi:,}")
print(f"  nearest is a river / reservoir   : {m.rivers:,} / {m.reservoirs:,}")
print(f"  median distance                  : {m.median_mi} mi")
assert fan < 1.01, "fan-out above 1.0 - a join duplicated parcels"

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_water_parcel'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
    f"VALUES (@t,@s,@m,@n,@g,CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "in_water_parcel"),
        bigquery.ScalarQueryParameter("s", "STRING",
            "in_screener_candidates x energy.nhd_waterbody (ftype 436/390) x energy.nhd_flowline (ftype 460, named)"),
        bigquery.ScalarQueryParameter("m", "STRING",
            f"nearest surface-water SOURCE within {RADIUS_M/1609.344:.0f} mi, by true "
            f"ST_DISTANCE(parcel_geog, SHAPE); lakes gated at >= {MIN_LAKE_SQKM} sq km; D85 excluded "
            f"by key before any spatial work; fan-out asserted < 1.01"),
        bigquery.ScalarQueryParameter("n", "INT64", int(m.n)),
        bigquery.ScalarQueryParameter("g", "FLOAT64", round(job.total_bytes_processed / 1024**3, 2)),
        bigquery.ScalarQueryParameter("no", "STRING",
            "Exact geometry-to-geometry distance, so water crossing a parcel returns 0.0 - this is "
            "G29 done correctly, unlike the map's client-side first-vertex method which reports "
            "~0.55 mi for the same case. ftype decoded: 436 reservoir and 460 river are SOURCES, "
            "466 swamp/marsh is a CONSTRAINT, 336/420/428/558 are ditches/conduits/pipelines. "
            "Lakes under 10 ha excluded as not cooling-relevant - a judgement, not a fact.")])).result()
print("registered in_water_parcel")
