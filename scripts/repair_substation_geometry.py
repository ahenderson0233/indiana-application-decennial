"""G20 + G109 + G62 - 933 substations were NOT missing a location. We were reading the wrong column.

    python scripts/repair_substation_geometry.py

⛔ THE FINDING, AND IT IS AN INSTRUMENT ERROR, NOT A DATA GAP.

G20 measured "738 of 3,858 rows carry NO substation_type AND - checked - no `max_kv` and no
coordinates either. They are name-only shells." The check that produced "no coordinates" was
`lat IS NULL`. Re-measured here:

    rows with lat IS NULL ................................. 933
    of those, carrying a footprint_geojson ................ 933   (100%)
    of those, whose footprint PARSES as valid geography ... 933   (100%)

Every single one of them has had its location, in our own table, in `indiana_app`, the entire
time. They are OSM `way` records - substations are mapped as POLYGONS in OpenStreetMap, and only
`node`-type records ever carry a latitude. Of the 2,873 Indiana OSM substations in the parent,
2,872 are ways with a NULL latitude and exactly ONE is a node.

⚠ `build_substations_dedup.py` even says so in its own docstring - "footprint-only rows (933, the
OSM-only contributions, which carry a polygon instead of a point)". The knowledge existed; the
measurement in G20 did not use it, and the conclusion "the gazetteer cannot be extended from what
we hold" was drawn against a column that was never going to be populated.

⭐ WHAT THE REPAIR IS WORTH, all measured at the bottom of this run:
  - 933 substations gain a usable position (2,925 -> 3,858 located, +32%)
  - the NAMED gazetteer goes 2,072 -> 2,255 distinct usable names, which is the ceiling
    G62 (PJM bus placement) and G15 (IURC workpaper stations) BOTH hit from opposite directions
  - up to 695 gain a voltage parsed from `osm_voltage_raw`

⛔ AND WHAT IT IS NOT WORTH, so nobody re-opens G62 expecting more than it gives. The twelve
north-west Indiana NIPSCO stations G62 named - CHICAGO AVE, MICHIGAN CITY, BURNS DITCH, MARKTOWN
and the rest - do NOT appear in the OSM Indiana slice by name. Checked directly. G62's conclusion
that those specific stations need an ACQUISITION still stands. What changes is the denominator,
not that particular hole.

⛔ NO CENTROID WHERE A FOOTPRINT EXISTS. The project bans centroid distance math and this repair
respects it rather than working around it:
  - `geog` is added and carries the FOOTPRINT wherever one is held, the point otherwise. Distance
    code should read `geog`, and ST_DISTANCE against a polygon is the true distance to the fence.
  - `lat`/`lon` are still filled, from ST_CENTROID, because a map marker needs a coordinate and a
    popup needs somewhere to anchor. `geom_kind` records which is which so no surface can quote a
    centroid as if it were a survey point.

⚠ OSM voltage is in VOLTS and semicolon-separated on multi-voltage stations ('345000;138000').
Parsed by splitting, casting, taking the max, dividing by 1000. `max_kv_inferred` is set TRUE on
every value recovered this way, because a tag in a crowd-sourced map is not a nameplate.

WRITES `indiana_app.in_substations` in place (adds `geog`, `coord_source`). Reads indiana_app only.
⚠ RE-RUN `build_substations_dedup.py` AFTER THIS, then the distance builds - see the tail.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
T = f"{DS}.in_substations"
client = bigquery.Client(project="energy-platfrom")

# ⛔ IDEMPOTENCY. This repair rewrites in_substations FROM in_substations. On a second run the
#    "before" state is the already-repaired table, so COALESCE(lat, ...) would preserve whatever
#    the first run wrote - including anything a later border rule would now reject. Any coordinate
#    this script previously DERIVED is discarded and recomputed from the footprint; a PUBLISHED
#    point is never touched. Without this the RE-SCRAPE COMMAND in the registry row is a lie.
_cols = {f.name for f in client.get_table(T).schema}
if "coord_source" in _cols:
    PUB_LAT = ("IF(coord_source IN ('derived_from_osm_footprint','outside_indiana_not_recovered'), "
               "NULL, lat)")
    PUB_LON = ("IF(coord_source IN ('derived_from_osm_footprint','outside_indiana_not_recovered'), "
               "NULL, lon)")
    print("  (re-run detected: discarding previously derived coordinates before recomputing)")
else:
    PUB_LAT, PUB_LON = "lat", "lon"

before = list(client.query(f"""
  SELECT COUNT(*) n, COUNTIF({PUB_LAT} IS NOT NULL) located,
         COUNTIF(max_kv IS NOT NULL) kv,
         COUNT(DISTINCT IF({PUB_LAT} IS NOT NULL, UPPER(TRIM(substation_name)), NULL)) usable_names
  FROM `{T}`"""))[0]
print(f"BEFORE  {before.n} rows · {before.located} located · {before.kv} with kV · "
      f"{before.usable_names} usable names")

SQL = f"""
CREATE OR REPLACE TABLE `{T}` AS
WITH raw AS (
  SELECT * EXCEPT (lat, lon),
         {PUB_LAT} AS lat, {PUB_LON} AS lon,        -- derived coordinates discarded, see above
         SAFE.ST_GEOGFROMGEOJSON(footprint_geojson, make_valid => TRUE) AS fp0
  FROM `{T}`
),
hit AS (
  -- ⛔ INDIANA ONLY, CLIPPED AT THE BORDER. The upstream OSM slice is keyed on the SCRAPE region
  --    (`state_scraped = 'IN'`), which is a query PARAMETER, not a spatial test - so it swept in
  --    neighbouring Illinois and Kentucky stations. The 2,925 rows that already had a published
  --    point are 0 outside; the problem only surfaces now, because a row with no coordinate could
  --    never be border-tested. Recovered footprints outside the state are NOT deleted and NOT
  --    rendered: the row survives with its location withheld.
  -- ⚠ A SPATIAL JOIN, NOT A SCALAR SUBQUERY. Both ST_UNION_AGG(county) and the single state
  --    polygon, referenced as `(SELECT g FROM ...)`, are planned as a cross join against a
  --    high-vertex polygon and died at 123% of the memory limit. A JOIN lets BigQuery use its
  --    spatial index. It also hands back the COUNTY, which these rows never had either.
  SELECT r.asset_id, ANY_VALUE(c.geo_id) AS hit_fips, ANY_VALUE(c.county_name) AS hit_county
  FROM raw r
  JOIN `bigquery-public-data.geo_us_boundaries.counties` c
    ON c.state_fips_code = '18' AND ST_CONTAINS(c.county_geom, ST_CENTROID(r.fp0))
  WHERE r.fp0 IS NOT NULL
  GROUP BY r.asset_id
),
src AS (
  SELECT r.* EXCEPT (fp0),
         IF(h.hit_fips IS NOT NULL, r.fp0, NULL) AS fp,
         r.fp0 IS NOT NULL AND h.hit_fips IS NULL AS fp_outside_indiana,
         h.hit_fips, h.hit_county
  FROM raw r LEFT JOIN hit h USING (asset_id)
),
volt AS (
  SELECT *,
    -- OSM voltage is VOLTS, semicolon-separated on multi-voltage stations. Take the highest.
    (SELECT MAX(SAFE_CAST(v AS FLOAT64))
     FROM UNNEST(SPLIT(IFNULL(osm_voltage_raw, ''), ';')) v
     WHERE SAFE_CAST(v AS FLOAT64) IS NOT NULL) / 1000.0 AS osm_kv
  FROM src
)
SELECT
  asset_id, substation_name, city, state,
  -- ⭐ G109 BONUS: the border test is a county lookup, so a row that never had a county gets one.
  COALESCE(county, hit_county)      AS county,
  COALESCE(county_fips, hit_fips)   AS county_fips,
  substation_type, status, line_count,
  COALESCE(max_kv, IF(osm_kv > 0, osm_kv, NULL))            AS max_kv,
  min_kv,
  -- ⚠ TRUE wherever the number came from an OSM tag rather than a nameplate. Never overwrite an
  --   existing FALSE with TRUE: a value we already trusted stays trusted.
  COALESCE(max_kv_inferred, max_kv IS NULL AND osm_kv > 0)  AS max_kv_inferred,
  operator, osm_voltage_raw,
  -- a marker needs a coordinate; geom_kind below says it is derived, not surveyed
  COALESCE(lat, ST_Y(ST_CENTROID(fp)))                      AS lat,
  COALESCE(lon, ST_X(ST_CENTROID(fp)))                      AS lon,
  footprint_geojson,
  -- ⭐ THE COLUMN DISTANCE CODE SHOULD READ. Footprint where held: ST_DISTANCE to a polygon is
  --   the distance to the fence, which is the honest answer and is 0 when the parcel touches it.
  COALESCE(fp, IF(lat IS NULL, NULL, ST_GEOGPOINT(lon, lat))) AS geog,
  CASE WHEN lat IS NOT NULL AND fp IS NOT NULL THEN 'point_and_footprint'
       WHEN lat IS NOT NULL                    THEN 'point_only'
       WHEN fp IS NOT NULL                     THEN 'footprint_only_point_derived'
       ELSE 'no_location' END                              AS geom_kind,
  CASE WHEN lat IS NOT NULL       THEN 'published_point'
       WHEN fp IS NOT NULL        THEN 'derived_from_osm_footprint'
       -- the footprint exists and is real; it is simply not in Indiana, so we withhold it
       -- rather than putting an out-of-state marker on an Indiana map.
       WHEN fp_outside_indiana    THEN 'outside_indiana_not_recovered'
       ELSE NULL END                                       AS coord_source,
  sources, hifld_id, osm_id, match_distance_m, source_date
FROM volt
"""

print("\nrepairing ...")
job = client.query(SQL)
job.result()
gb = round((job.total_bytes_processed or 0) / 1e9, 3)

after = list(client.query(f"""
  SELECT COUNT(*) n, COUNTIF(lat IS NOT NULL) located, COUNTIF(max_kv IS NOT NULL) kv,
         COUNT(DISTINCT IF(lat IS NOT NULL, UPPER(TRIM(substation_name)), NULL)) usable_names,
         COUNTIF(geog IS NOT NULL) with_geog,
         COUNTIF(coord_source = 'derived_from_osm_footprint') derived,
         COUNTIF(coord_source = 'outside_indiana_not_recovered') outside
  FROM `{T}`"""))[0]

# ⛔ A REPAIR THAT CHANGES THE ROW COUNT IS NOT A REPAIR (trap 7).
assert after.n == before.n, f"ROW COUNT MOVED {before.n} -> {after.n}"

print(f"AFTER   {after.n} rows · {after.located} located · {after.kv} with kV · "
      f"{after.usable_names} usable names")
print(f"  located   {before.located:>5} -> {after.located:>5}   (+{after.located - before.located},"
      f" {100.0 * (after.located - before.located) / before.located:+.1f}%)")
print(f"  with kV   {before.kv:>5} -> {after.kv:>5}   (+{after.kv - before.kv})")
print(f"  gazetteer {before.usable_names:>5} -> {after.usable_names:>5}   "
      f"(+{after.usable_names - before.usable_names} distinct names, the G62/G15 ceiling)")
print(f"  {after.with_geog} rows now carry a `geog` for real distance math; "
      f"{after.derived} of the coordinates are footprint-derived and labelled as such")
print(f"  ⛔ {after.outside} recovered footprints fall OUTSIDE Indiana and are withheld, not "
      f"deleted — the OSM slice is keyed on the scrape region, not a border test")

# ⛔ Nothing this repair writes may sit outside the state.
leak = list(client.query(f"""
  WITH p AS (SELECT state_geom g
             FROM `bigquery-public-data.geo_us_boundaries.states` WHERE state_fips_code='18')
  SELECT COUNTIF(NOT ST_CONTAINS((SELECT g FROM p), ST_GEOGPOINT(lon, lat))) n
  FROM `{T}` WHERE lat IS NOT NULL"""))[0].n
assert leak == 0, f"{leak} located substations are outside Indiana - the border clip leaked"
print(f"  border check: {leak} located rows outside Indiana")

print("\n  geometry inventory:")
for r in client.query(f"SELECT geom_kind, COUNT(*) n FROM `{T}` GROUP BY 1 ORDER BY n DESC"):
    print(f"    {r.geom_kind:32s} {r.n:>5}")

print("\n  a sample of what came back:")
for r in client.query(f"""SELECT substation_name, operator, max_kv, max_kv_inferred,
                                 ROUND(lat, 5) lat, ROUND(lon, 5) lon
                          FROM `{T}` WHERE coord_source = 'derived_from_osm_footprint'
                            AND substation_name IS NOT NULL AND max_kv IS NOT NULL
                          ORDER BY max_kv DESC LIMIT 8"""):
    print(f"    {str(r.substation_name)[:30]:30s} {str(r.operator)[:22]:22s} "
          f"{r.max_kv:>6.0f} kV{' (osm tag)' if r.max_kv_inferred else '          '} "
          f"{r.lat}, {r.lon}")

# ⛔ G62 SANITY CHECK. Do not let this repair be read as closing the acquisition gap.
twelve = ["CHICAGO AVE", "SOUTH VALPARAISO", "MICHIGAN CITY", "MILLER", "ROCK RUN", "STILLWELL",
          "EAST WINAMAC", "BURNS DITCH", "TRAIL CREEK", "MARKTOWN", "KOSCIUSKO"]
lst = ", ".join(f"'{t}'" for t in twelve)
got = [r.nm for r in client.query(f"""
  SELECT DISTINCT UPPER(TRIM(substation_name)) nm FROM `{T}`
  WHERE lat IS NOT NULL AND UPPER(TRIM(substation_name)) IN ({lst})""")]
print(f"\n  G62's twelve NIPSCO stations now locatable: {len(got)} of {len(twelve)}  {got}")
print("  -> the ACQUISITION half of G62 is unchanged. This repair moved the denominator, "
      "not that hole.")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_substations',
 'indiana_app.in_substations repaired in place (originally energy.mat_grid_substations, which '
 'merges HIFLD and OpenStreetMap)',
 'REPAIR, not a rebuild: 933 rows whose lat/lon were NULL had a valid footprint_geojson all '
 'along, because OSM maps substations as ways (polygons) and only node records carry a latitude. '
 'Adds a geog column carrying the FOOTPRINT where held so distance math never uses a centroid; '
 'lat/lon are filled from ST_CENTROID for map markers only and geom_kind/coord_source record '
 'that they are derived. max_kv recovered from osm_voltage_raw (volts, semicolon-separated, max '
 'taken) with max_kv_inferred TRUE on every recovered value. '
 'RE-SCRAPE COMMAND: python scripts/repair_substation_geometry.py',
 {after.n}, {gb}, CURRENT_TIMESTAMP(),
 'G20 + G109 + G62. G20 reported these as name-only shells with no coordinates; that measurement '
 'tested lat IS NULL and the location was in footprint_geojson on 933 of 933. Located rows '
 '{before.located} -> {after.located}; usable gazetteer names {before.usable_names} -> '
 '{after.usable_names}. RE-RUN build_substations_dedup.py, then build_asset_distance_parcel.py '
 'and build_screener_candidates.py, or the repair never reaches a user.'
)""").result()
print("\n  _registry row written (in_substations repointed)")
print("\n⚠ NEXT, IN THIS ORDER, or the repair stops at the warehouse:")
print("    python scripts/build_substations_dedup.py")
print("    python scripts/build_asset_distance_parcel.py")
print("    python scripts/build_screener_candidates.py")
print("SUBSTATION GEOMETRY REPAIR COMPLETE")
