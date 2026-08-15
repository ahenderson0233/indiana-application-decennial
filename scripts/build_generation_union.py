"""A6 (final merges) — generation, and the two subjects that turned out NOT to be duplicated.

GENERATION IS THREE GRAINS, NOT ONE SUBJECT HELD THREE TIMES. Measured:
  · in_eia_plants        281 distinct plants (2,675 rows = plant-YEARS)
  · in_power_plants      208 HIFLD plants, of which 205 share a plant code with EIA -> DUPLICATE
  · in_solar_pv_facilities 114 arrays, ALL carrying an eia_id -> ties to the plant layer
  · in_wind_turbines     1,652 individual TURBINES across 33 projects, 3,622 MW -> DIFFERENT GRAIN
  · in_operating_generators 11,795 GENERATORS -> different grain again
Merging turbines or generators into a plant layer would not dedupe anything; it would
double-count a wind farm 50 times. Only the plant-grain sources are merged here. Turbines stay
their own layer (already rendered) and generators stay a Grid table.

NOT DUPLICATED, measured rather than assumed:
  · GAS PIPELINES - the spec §14 duplicate pair (natural_gas_pipelines vs gas_pipelines_hifld)
    lives in `energy` and was never clipped here; indiana_app holds ONE table, in_gas_pipelines
    (215). Nothing to merge.
  · BROWNFIELDS - spec §14 says the trio are NOT duplicates and should union with a
    program_source column, but only ONE of the three was ever clipped to Indiana
    (in_si_refresh_brownfield_epa_in). Nothing to merge until the other two are clipped.
  · WARN - already resolved in A3: in_si_refresh_warn_notices and in_si_state_warn_notices hold
    the same 1,220 notices (1,104 shared company|city|date keys); the copy carrying
    notice_pdf_urls is the keeper. Recorded there.
"""
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
WITH eia AS (
  -- 2,675 rows are plant-YEARS; take the latest row per plant so a plant is counted once
  SELECT CAST(plant_id_eia AS STRING) AS plant_code, plant_name_eia AS name, city, county,
         latitude AS lat, longitude AS lon, report_date,
         ROW_NUMBER() OVER (PARTITION BY plant_id_eia ORDER BY report_date DESC) rn
  FROM `{DS}.in_eia_plants` WHERE latitude IS NOT NULL AND longitude IS NOT NULL),
eia1 AS (SELECT * EXCEPT(rn) FROM eia WHERE rn = 1),
hif AS (
  SELECT CAST(Plant_Code AS STRING) AS plant_code, Plant_Name AS name, City AS city,
         County AS county, PrimSource AS prim_source, tech_desc,
         SAFE_CAST(Total_MW AS FLOAT64) AS total_mw, SAFE_CAST(Install_MW AS FLOAT64) AS install_mw,
         Utility_Na AS utility
  FROM `{DS}.in_power_plants`)
SELECT
  COALESCE(e.plant_code, h.plant_code) AS plant_code,
  COALESCE(h.name, e.name) AS name,
  COALESCE(h.city, e.city) AS city,
  COALESCE(h.county, e.county) AS county,
  h.prim_source, h.tech_desc, h.total_mw, h.install_mw, h.utility,
  e.lat, e.lon,
  CASE WHEN e.plant_code IS NOT NULL AND h.plant_code IS NOT NULL THEN 'EIA+HIFLD'
       WHEN e.plant_code IS NOT NULL THEN 'EIA only'
       ELSE 'HIFLD only' END AS sources,
  CAST(e.report_date AS STRING) AS eia_report_date
FROM eia1 e
FULL OUTER JOIN hif h ON e.plant_code = h.plant_code
"""

dry = client.query(SQL, job_config=bigquery.QueryJobConfig(dry_run=True))
gb = dry.total_bytes_processed / 1e9
print(f"dry-run {gb:.3f} GB")
client.query(f"CREATE OR REPLACE TABLE `{DS}.in_generation_union` AS\n{SQL}").result()

for r in client.query(f"""
    SELECT sources, COUNT(*) plants, COUNTIF(lat IS NOT NULL) with_coords,
           ROUND(SUM(total_mw)) mw FROM `{DS}.in_generation_union` GROUP BY 1 ORDER BY plants DESC"""):
    print(f"  {r.sources:<12} {r.plants:>4} plants · {r.with_coords:>4} with coords · {r.mw or 0:,.0f} MW")
n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_generation_union`"))[0].n

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_generation_union'").result()
client.query(f"""INSERT `{DS}._registry`
  (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES (@t,@s,@m,@n,@g,CURRENT_TIMESTAMP(),@o)""",
  job_config=bigquery.QueryJobConfig(query_parameters=[
    bigquery.ScalarQueryParameter("t", "STRING", "in_generation_union"),
    bigquery.ScalarQueryParameter("s", "STRING", "indiana_app.in_eia_plants + in_power_plants"),
    bigquery.ScalarQueryParameter("m", "STRING",
      "FULL OUTER JOIN on plant code; EIA reduced to its latest row per plant first (2,675 rows "
      "are plant-YEARS, 281 plants)"),
    bigquery.ScalarQueryParameter("n", "INT64", n),
    bigquery.ScalarQueryParameter("g", "FLOAT64", round(gb, 4)),
    bigquery.ScalarQueryParameter("o", "STRING",
      "PLANT grain only. in_wind_turbines (1,652 turbines / 33 projects) and "
      "in_operating_generators (11,795 generators) are DIFFERENT GRAINS and are deliberately NOT "
      "merged - folding them in would double-count a wind farm ~50x rather than dedupe it. "
      "205 of 208 HIFLD plant codes were already in EIA, which is the duplication this fixes.")])).result()
print(f"in_generation_union: {n} plants, registered")
