"""Batch 6b fix-ups from measured flags:
- DC family via COORDS point-in-state (baxtel/wikidata direct; DCM via slug-join to coords)
  -> in_data_centers_all union with per-source provenance (dedupe deliberately NOT done - flagged)
- FCC mobile/provider summaries via geography_id ('18' prefix) - my '_st_pct' regex hit was a 2.17 bug
- elec_power_operational location='IN'; operating_generators stateid='IN';
  drought_by_state stateabbreviation='IN'; ghgrp_emissions via facility join; zctas 46/47 prefix
- cloudscene: value-read of its state vocabulary first"""
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
E = "`energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")
ST = "(SELECT state_geom FROM `bigquery-public-data.geo_us_boundaries.states` WHERE state='IN')"

def reg(dest, src, method, n, gb=0.05, note=""):
    client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
      VALUES ('{dest}','{src}','{method}', {n}, {gb}, CURRENT_TIMESTAMP(), '{note}')""").result()

def run(dest, sql, src, method, note=""):
    client.query(f"CREATE OR REPLACE TABLE `{DS}.{dest}` AS {sql}").result()
    n = list(client.query(f"SELECT COUNT(*) AS n FROM `{DS}.{dest}`"))[0].n
    reg(dest, src, method, n, note=note)
    print(f"{dest}: {n:,}")
    return n

# cloudscene vocabulary (value-read, small)
for r in client.query(f"""SELECT state, COUNT(*) n FROM {E}.data_centers_cloudscene`
    WHERE REGEXP_CONTAINS(UPPER(CAST(state AS STRING)), 'IND|^IN') GROUP BY 1 LIMIT 8"""):
    print("cloudscene state sample:", dict(r))

run("in_data_centers_all", f"""
SELECT 'osm' AS src, CAST(name AS STRING) AS name, CAST(NULL AS STRING) AS operator,
       ST_Y(_g) AS lat, ST_X(_g) AS lon
FROM (SELECT *, geog AS _g FROM {E}.data_centers`) WHERE ST_INTERSECTS(_g, {ST})
UNION ALL
SELECT 'baxtel', site_name, company_name, SAFE_CAST(latitude AS FLOAT64), SAFE_CAST(longitude AS FLOAT64)
FROM {E}.data_centers_baxtel`
WHERE SAFE_CAST(latitude AS FLOAT64) IS NOT NULL
  AND ST_CONTAINS({ST}, ST_GEOGPOINT(SAFE_CAST(longitude AS FLOAT64), SAFE_CAST(latitude AS FLOAT64)))
UNION ALL
SELECT 'wikidata', name, operator, SAFE_CAST(latitude AS FLOAT64), SAFE_CAST(longitude AS FLOAT64)
FROM {E}.data_centers_wikidata`
WHERE SAFE_CAST(latitude AS FLOAT64) IS NOT NULL
  AND ST_CONTAINS({ST}, ST_GEOGPOINT(SAFE_CAST(longitude AS FLOAT64), SAFE_CAST(latitude AS FLOAT64)))
UNION ALL
SELECT 'datacentermap', d.name, CAST(NULL AS STRING),
       SAFE_CAST(c.latitude AS FLOAT64), SAFE_CAST(c.longitude AS FLOAT64)
FROM {E}.data_centers_datacentermap` d
JOIN {E}.data_centers_datacentermap_coords` c ON c.dcm_slug = d.dcm_slug
WHERE SAFE_CAST(c.latitude AS FLOAT64) IS NOT NULL
  AND ST_CONTAINS({ST}, ST_GEOGPOINT(SAFE_CAST(c.longitude AS FLOAT64), SAFE_CAST(c.latitude AS FLOAT64)))""",
 "data_centers + baxtel + wikidata + datacentermap(+coords slug-join)",
 "coords point-in-state union",
 "EXISTING-DC layer, per-source rows; DEDUPE FLAGGED not done (same facility appears in multiple sources); DCM pinless status in gap register is STALE - coords exist")

run("in_fcc_bdc_mobile_summary", f"""SELECT * FROM {E}.fcc_bdc_mobile_summary_by_geography`
    WHERE STARTS_WITH(CAST(geography_id AS STRING), '18')""",
 "energy.fcc_bdc_mobile_summary_by_geography", "geoid prefix (regex bug fixed)", "mobile coverage summaries")
run("in_fcc_bdc_provider_summary", f"""SELECT * FROM {E}.fcc_bdc_provider_summary_by_geography`
    WHERE STARTS_WITH(CAST(geography_id AS STRING), '18')""",
 "energy.fcc_bdc_provider_summary_by_geography", "geoid prefix (regex bug fixed)", "per-provider summaries")
run("in_elec_power_operational", f"""SELECT * FROM {E}.elec_power_operational`
    WHERE UPPER(TRIM(CAST(location AS STRING)))='IN'""",
 "energy.elec_power_operational", "location=IN", "EIA state-month operations")
run("in_operating_generators", f"""SELECT * FROM {E}.operating_generators`
    WHERE UPPER(TRIM(CAST(stateid AS STRING)))='IN'""",
 "energy.operating_generators", "stateid=IN", "EIA-860M live generators")
run("in_drought_by_state", f"""SELECT * FROM {E}.drought_by_state`
    WHERE UPPER(TRIM(CAST(stateabbreviation AS STRING)))='IN'""",
 "energy.drought_by_state", "stateabbreviation=IN", "drought monitor series")
run("in_ghgrp_emissions", f"""SELECT e.* FROM {E}.ghgrp_emissions` e
    WHERE CAST(e.facility_id AS STRING) IN
      (SELECT CAST(facility_id AS STRING) FROM `{DS}.in_ghgrp_facilities`)""",
 "energy.ghgrp_emissions x in_ghgrp_facilities", "facility-id join", "emissions series for IN facilities")
run("in_zctas", f"""SELECT * FROM {E}.zctas`
    WHERE STARTS_WITH(CAST(GEOID20 AS STRING),'46') OR STARTS_WITH(CAST(GEOID20 AS STRING),'47')""",
 "energy.zctas", "ZCTA 46/47 prefix (18-prefix was wrong - ZCTAs are not FIPS)", "IN zip-code areas")
print("BATCH 6B COMPLETE")
