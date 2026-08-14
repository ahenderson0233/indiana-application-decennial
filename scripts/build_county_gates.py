"""County-grain gate aggregates so P4/P3b render honestly before the tile pipeline:
  in_county_fibre    from in_fcc_bdc  (county fips = SUBSTR(block_geoid,1,5) - string, free)
  in_county_flood    from in_flood    (greatest-intersection county assignment)
  in_county_wetlands from in_wetlands (greatest-intersection county assignment)
Water (in_water, 2.4M flowlines) is DEFERRED to the tile pipeline - recorded as a waiver.
"""
from google.cloud import bigquery

client = bigquery.Client(project="energy-platfrom")
DS = "energy-platfrom.indiana_app"
CTY = ("(SELECT county_fips_code AS fips, county_geom FROM "
       "`bigquery-public-data.geo_us_boundaries.counties` WHERE state_fips_code='18')")

def run(tag, sql, register=None):
    dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
    gb = dry.total_bytes_processed / 1e9
    client.query(sql).result()
    print(f"[{tag}] ok ({gb:.2f} GB)")
    if register:
        n = list(client.query(f"SELECT COUNT(*) AS n FROM `{DS}.{register[0]}`"))[0].n
        client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
          VALUES ('{register[0]}','{register[1]}','county aggregate', {n}, {gb:.3f}, CURRENT_TIMESTAMP(), '{register[2] if len(register)>2 else ""}')""").result()
        print(f"   registered {register[0]}: {n} rows")

# value-sample FCC technology codes before believing them
print("FCC technology vocabulary (measured):")
for r in client.query(f"""SELECT technology, ANY_VALUE(prov_technology_desc) AS d, COUNT(*) AS n
                          FROM `{DS}.in_fcc_bdc` GROUP BY 1 ORDER BY n DESC"""):
    print(f"   tech={r.technology} desc={r.d} n={r.n:,}")

run("fibre county agg", f"""
CREATE OR REPLACE TABLE `{DS}.in_county_fibre` AS
SELECT SUBSTR(block_geoid,1,5) AS county_fips,
       COUNT(DISTINCT location_id) AS locations,
       COUNT(DISTINCT IF(LOWER(prov_technology_desc) LIKE '%fiber%', location_id, NULL)) AS fiber_locations,
       COUNT(DISTINCT IF(LOWER(prov_technology_desc) LIKE '%fiber%', provider_id, NULL)) AS fiber_providers,
       COUNT(DISTINCT IF(SAFE_CAST(max_advertised_download_speed AS FLOAT64)>=1000, location_id, NULL)) AS gig_locations
FROM `{DS}.in_fcc_bdc` GROUP BY 1""",
    register=("in_county_fibre", "indiana_app.in_fcc_bdc", "fiber defined by publisher tech desc, value-sampled"))

run("flood county agg", f"""
CREATE OR REPLACE TABLE `{DS}.in_county_flood` AS
SELECT fips AS county_fips,
       COUNT(*) AS flood_features,
       COUNTIF(SFHA_TF='T') AS sfha_features,
       COUNT(DISTINCT FLD_ZONE) AS zones
FROM (
  SELECT f.SFHA_TF, f.FLD_ZONE, c.fips,
         ROW_NUMBER() OVER (PARTITION BY f.DFIRM_ID, f.FLD_AR_ID
                            ORDER BY ST_AREA(ST_INTERSECTION(f.geog, c.county_geom)) DESC, c.fips) rk
  FROM `{DS}.in_flood` f JOIN {CTY} c ON ST_INTERSECTS(f.geog, c.county_geom))
WHERE rk=1 GROUP BY 1""",
    register=("in_county_flood", "indiana_app.in_flood", "greatest-intersection county"))

run("wetlands county agg", f"""
CREATE OR REPLACE TABLE `{DS}.in_county_wetlands` AS
SELECT fips AS county_fips, COUNT(*) AS wetland_features,
       ROUND(SUM(SAFE_CAST(acres AS FLOAT64)),0) AS wetland_acres
FROM (
  SELECT w.ACRES AS acres, c.fips,
         ROW_NUMBER() OVER (PARTITION BY w.NWI_ID ORDER BY ST_AREA(ST_INTERSECTION(w.geog, c.county_geom)) DESC, c.fips) rk
  FROM `{DS}.in_wetlands` w JOIN {CTY} c ON ST_INTERSECTS(w.geog, c.county_geom))
WHERE rk=1 GROUP BY 1""",
    register=("in_county_wetlands", "indiana_app.in_wetlands", "greatest-intersection county"))
print("DONE")
