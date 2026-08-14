"""Build (or rebuild) the Indiana clips in energy-platfrom.indiana_app.

- READ-ONLY on energy.*; writes only to indiana_app.*
- Every clip dry-runs first; a 400 GB guard catches accidents.
- Every table lands with an indiana_app._registry row (source, method, rows, GB, built_at).
- Idempotent: CREATE OR REPLACE per table; safe to re-run after any upstream refresh.

Run:  python scripts/build_indiana_clips.py
Auth: GOOGLE_APPLICATION_CREDENTIALS must point at a key with read on energy.*
      and write on indiana_app.* (never the reverse).

Baselines measured 2026-08-14 (a rebuild should land at or above these):
  wetlands 453,995 | flood 66,140 | padus 4,736 | water 2,415,369
  fcc 12,649,532 | sites 3,553,194 | si 1,818,158
"""
from google.cloud import bigquery

client = bigquery.Client(project="energy-platfrom")
GUARD_GB = 400.0
DS = "energy-platfrom.indiana_app"

ds = bigquery.Dataset(DS)
ds.location = "US"
ds.description = ("Indiana siting-intelligence PoC (static app). Clips + scrapes only; "
                  "the shared energy.* dataset is never written by this workstream.")
client.create_dataset(ds, exists_ok=True)

client.query(f"""
CREATE TABLE IF NOT EXISTS `{DS}._registry` (
  table_name STRING, source STRING, method STRING,
  n_rows INT64, gb_scanned FLOAT64, built_at TIMESTAMP, notes STRING)
""").result()

E = "`energy-platfrom.energy"
ST = ("(SELECT state_geom FROM `bigquery-public-data.geo_us_boundaries.states` "
      "WHERE state = 'IN')")

CLIPS = [
 ("in_si_signals", "energy.si_signals",
  f"SELECT * FROM {E}.si_signals` WHERE state='IN'"),
 ("in_sites", "energy.vw_parcel_sites (all parcels, SI-agnostic)",
  f"SELECT * FROM {E}.vw_parcel_sites` WHERE state='IN'"),
 ("in_substations", "energy.mat_grid_substations (HIFLD+OSM deduped)",
  f"SELECT * FROM {E}.mat_grid_substations` WHERE UPPER(state) IN ('IN','INDIANA')"),
 ("in_transmission_lines", "energy.transmission_lines (HIFLD), spatial clip",
  f"SELECT t.* FROM {E}.transmission_lines` t WHERE ST_INTERSECTS(t.geom, {ST})"),
 ("in_queue", "energy.interconnection_queue",
  f"SELECT * FROM {E}.interconnection_queue` WHERE UPPER(state) IN ('IN','INDIANA')"),
 ("in_queue_counties", "energy.vw_grid_queue_counties",
  f"SELECT * FROM {E}.vw_grid_queue_counties` WHERE UPPER(state) IN ('IN','INDIANA')"),
 ("in_miso_poi", "energy.miso_poi_monitored_facilities (points in IN polygon)",
  f"""SELECT m.* FROM {E}.miso_poi_monitored_facilities` m
      WHERE SAFE_CAST(m.longitude_raw AS FLOAT64) IS NOT NULL
        AND SAFE_CAST(m.latitude_raw AS FLOAT64) IS NOT NULL
        AND ST_CONTAINS({ST},
            ST_GEOGPOINT(SAFE_CAST(m.longitude_raw AS FLOAT64),
                         SAFE_CAST(m.latitude_raw AS FLOAT64)))"""),
 ("in_pjm_queuescope_aep", "energy.pjm_queuescope_results (AEP = the I&M sliver)",
  f"SELECT * FROM {E}.pjm_queuescope_results` WHERE owner_label='AEP'"),
 ("in_water", "energy.nhd_flowline",
  f"SELECT * FROM {E}.nhd_flowline` WHERE src_state='IN'"),
 ("in_fcc_bdc", "energy.fcc_bdc_fixed_availability",
  f"SELECT * FROM {E}.fcc_bdc_fixed_availability` WHERE state_usps='IN'"),
 ("in_wetlands", "energy.nwi_wetlands",
  f"SELECT * FROM {E}.nwi_wetlands` WHERE src_state='IN'"),
 ("in_flood", "energy.nfhl_flood_zones",
  f"SELECT * FROM {E}.nfhl_flood_zones` WHERE src_state='IN'"),
 ("in_padus", "energy.padus",
  f"SELECT * FROM {E}.padus` WHERE src_state='IN'"),
 ("in_bonus_geo", "energy communities + LIC tracts + opportunity zones + critical habitat",
  f"""SELECT 'energy_community' AS kind, CAST(geoid_cty_2020 AS STRING) AS key, geog,
             TO_JSON_STRING(STRUCT(msa_area_name, ec_qual_status, ffe_ind_qual)) AS attrs_json
      FROM {E}.energy_communities_msa` WHERE UPPER(state_name)='INDIANA'
      UNION ALL
      SELECT 'low_income_tract', CAST(CensusTrac AS STRING), geog,
             TO_JSON_STRING(STRUCT(NMTCQualif, CountyName, Vintage))
      FROM {E}.low_income_bonus_tracts` WHERE UPPER(StateName)='INDIANA'
      UNION ALL
      SELECT 'opportunity_zone', CAST(geoid10 AS STRING),
             SAFE.ST_GEOGFROMGEOJSON(geometry_geojson),
             TO_JSON_STRING(STRUCT(county, rural))
      FROM {E}.incentive_opportunity_zones` WHERE state='18'
      UNION ALL
      SELECT 'critical_habitat', CAST(comname AS STRING), c.geog,
             TO_JSON_STRING(STRUCT(sciname, status, unitname))
      FROM {E}.critical_habitat` c WHERE ST_INTERSECTS(c.geog, {ST})"""),
 ("in_cems_monthly", "energy.cems_hourly aggregated to plant-unit-month",
  f"""SELECT plant_id_epa, emissions_unit_id_epa,
             DATE_TRUNC(DATE(operating_datetime_utc), MONTH) AS month,
             SUM(gross_load_mw) AS gross_load_mwh,
             SUM(co2_mass_tons) AS co2_tons,
             SUM(operating_time_hours) AS run_hours
      FROM {E}.cems_hourly` WHERE state='IN' GROUP BY 1,2,3"""),
]

total_gb = 0.0
for name, source, sql in CLIPS:
    create = f"CREATE OR REPLACE TABLE `{DS}.{name}` AS\n{sql}"
    dry = client.query(create, job_config=bigquery.QueryJobConfig(dry_run=True))
    gb = dry.total_bytes_processed / 1e9
    if gb > GUARD_GB:
        print(f"[{name}] SKIPPED - dry-run {gb:.1f} GB exceeds guard")
        continue
    client.query(create).result()
    total_gb += gb
    n = list(client.query(f"SELECT COUNT(*) AS n FROM `{DS}.{name}`"))[0].n
    client.query(
        f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
            VALUES ('{name}', '{source}', 'clip rebuild', {n}, {gb:.3f},
                    CURRENT_TIMESTAMP(), NULL)""").result()
    print(f"[{name}] {n:,} rows ({gb:.2f} GB scanned)")

# disclose SAFE-parse losses in the OZ branch rather than hiding them
oz = list(client.query(f"""
  SELECT COUNTIF(geog IS NULL) AS failed, COUNT(*) AS total
  FROM `{DS}.in_bonus_geo` WHERE kind='opportunity_zone'"""))[0]
print(f"opportunity_zone geometry parse: {oz.failed} failed of {oz.total}")
print(f"TOTAL scanned: {total_gb:.1f} GB (~${total_gb*6.25/1000:.2f} on-demand)")
