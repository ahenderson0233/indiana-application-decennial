"""G12 — water. Clip the Indiana slice of the water estate into indiana_app.

WHY. Operator, 2026-08-17: *"We do not have water data currently hitting the app - this is located
in energy BQ and should be wired."* Water is a **first-order siting constraint** for a hyperscale
data centre, not a context layer: an evaporatively-cooled campus runs roughly **1-5 million gallons
per day**, which is the same order as a small city's entire public supply. A siting tool that
screens on power and land and says nothing about water is answering two thirds of the question.

⛔ CLIP, DO NOT DUPLICATE. Per the standing ruling on the ~140 energy source tables: take the
Indiana slice, register it, read the clip. `nhd_flowline` alone is 39.5M rows and 5.4 GB nationally;
none of that belongs in this application.

WHAT IS BUILT, and the question each answers for a developer:

  in_water_county          one row per county (92 of 92)
      * how much water the county already withdraws, split public-supply / industrial /
        thermoelectric, and ground vs surface -> is there an existing large-withdrawal culture
        here, and from what source
      * wastewater treatment capacity and its HEADROOM (design flow - existing flow) -> can the
        plant physically accept your discharge, which is the constraint people forget until late

  in_water_stress_basin    the 34 Indiana basins from WRI Aqueduct, kept at BASIN grain
      * baseline water stress, depletion, seasonal variability, drought risk -> will withdrawing
        here attract objection or a hard permit

⚠ BASIN GRAIN IS KEPT DELIBERATELY. Aqueduct is published per hydrological basin, and basins do not
follow county lines. Averaging a basin score onto a county would manufacture a per-county number the
publisher never issued - the same error class as a centroid: a derived value that looks more precise
than its source. The client joins spatially or shows the basin as itself.

⚠ VINTAGE. USGS county water use is **2015** - the most recent full national compilation. Say so
wherever it renders; a 2015 withdrawal figure is context, not a current measurement.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

# ---------------------------------------------------------------- county grain
SQL_COUNTY = f"""
CREATE OR REPLACE TABLE `{DS}.in_water_county` AS
WITH use AS (
  SELECT LPAD(CAST(fips AS STRING), 5, '0') AS county_fips,
         REGEXP_REPLACE(county, r' County$', '') AS county_name,
         SAFE_CAST(year AS INT64) AS use_year,
         SAFE_CAST(tp_totpop AS FLOAT64) AS population_k,
         -- all withdrawals are Mgal/d (million gallons per day)
         SAFE_CAST(ps_wtotl AS FLOAT64) AS public_supply_mgd,
         SAFE_CAST(ps_wgwto AS FLOAT64) AS public_supply_ground_mgd,
         SAFE_CAST(ps_wswto AS FLOAT64) AS public_supply_surface_mgd,
         SAFE_CAST(in_wtotl AS FLOAT64) AS industrial_mgd,
         SAFE_CAST(pt_wtotl AS FLOAT64) AS thermoelectric_mgd,
         SAFE_CAST(ir_wfrto AS FLOAT64) AS irrigation_mgd,
         SAFE_CAST(to_wtotl AS FLOAT64) AS total_withdrawal_mgd
  FROM `energy-platfrom.energy.water_use`
  WHERE UPPER(state) IN ('IN', 'INDIANA')
),
-- Wastewater: the discharge side, which is the half people forget.
-- ⚠ READS THE PLATFORM'S CANONICAL VIEW `vw_cwns_flow`, not a hand-rolled aggregation of the raw
-- table. The first version of this script summed the raw CWNS columns itself and thereby MISSED
-- `flow_existing_industrial_mgd` entirely - which is the single most relevant flow for a data
-- centre, since a DC discharges as an industrial user, not a domestic one. It also re-derived
-- `headroom_permitted_minus_existing_mgd`, which the view already publishes. Operator rule G25 in
-- its exact form: look at what we hold before building it again, badly.
-- ⚠⚠ TWO TRAPS HERE, BOTH MEASURED, BOTH SILENT IF MISSED.
--
-- TRAP 1 - THE JOIN KEY. `water_cwns_2022.facid` is **NULL on every row**, so the obvious join
-- produces zero matches and 92 counties silently lose their wastewater data (the first run of this
-- script did exactly that and reported "no wastewater match: 92"). The real key is `af_nbr`
-- ('18000001001') mapped to the view's `facility_id` ('180001001') by keeping the 2-digit state
-- prefix and dropping the next two characters. Verified empirically against four candidate
-- transformations rather than reasoned about.
--
-- TRAP 2 - THE GRAIN. `vw_cwns_flow` is one row per facility **per survey year**
-- (source_member = .../contents/1984/G#FLOW.csv, .../1986/..., and so on) - fan-out 9.79
-- nationally. SUMming across it adds the same plant's flow once per survey it ever appeared in and
-- inflates every Indiana figure roughly TENFOLD, while looking entirely plausible. So: take the
-- LATEST survey year per facility, then aggregate to the county.
flow_latest AS (
  SELECT facility_id,
         flow_existing_mgd, flow_permitted_design_mgd, flow_future_design_mgd,
         flow_existing_industrial_mgd, flow_future_industrial_mgd,
         headroom_permitted_minus_existing_mgd
  FROM `energy-platfrom.energy.vw_cwns_flow`
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY facility_id
    ORDER BY SAFE_CAST(REGEXP_EXTRACT(source_member, r'/(\\d{{4}})/') AS INT64) DESC NULLS LAST,
             flow_existing_mgd DESC NULLS LAST) = 1
),
cwns AS (
  SELECT UPPER(REGEXP_REPLACE(w.county_name, r' County$', '')) AS cnty,
         COUNT(*) AS treatment_facilities,
         ROUND(SUM(f.flow_existing_mgd), 2)              AS existing_flow_mgd,
         ROUND(SUM(f.flow_permitted_design_mgd), 2)      AS design_flow_mgd,
         ROUND(SUM(f.flow_future_design_mgd), 2)         AS future_design_flow_mgd,
         ROUND(SUM(f.flow_existing_industrial_mgd), 2)   AS industrial_flow_mgd,
         ROUND(SUM(f.flow_future_industrial_mgd), 2)     AS future_industrial_flow_mgd,
         ROUND(SUM(f.headroom_permitted_minus_existing_mgd), 2) AS wastewater_headroom_mgd,
         COUNTIF(f.flow_existing_mgd IS NULL)            AS facilities_without_flow
  FROM `energy-platfrom.energy.water_cwns_2022` w
  JOIN flow_latest f
    ON f.facility_id = CONCAT(SUBSTR(w.af_nbr, 1, 2), SUBSTR(w.af_nbr, 5))
  WHERE UPPER(w.state) = 'IN'
  GROUP BY cnty
),
-- Drought risk at county grain, from FEMA's National Risk Index. Water availability is not only a
-- question of what is there today; it is whether it is reliably there.
nri AS (
  SELECT LPAD(CAST(stcofips AS STRING), 5, '0') AS county_fips,
         SAFE_CAST(drgt_afreq AS FLOAT64) AS drought_annual_frequency,
         SAFE_CAST(drgt_evnts AS FLOAT64) AS drought_events_recorded,
         drgt_hlrr AS drought_hazard_rating,
         drgt_ealr AS drought_expected_annual_loss_rating
  FROM `energy-platfrom.energy.fema_nri_counties`
  WHERE UPPER(stateabbrv) = 'IN'
)
SELECT u.*,
       c.treatment_facilities, c.existing_flow_mgd, c.design_flow_mgd, c.future_design_flow_mgd,
       c.industrial_flow_mgd, c.future_industrial_flow_mgd, c.wastewater_headroom_mgd,
       c.facilities_without_flow,
       n.drought_annual_frequency, n.drought_events_recorded,
       n.drought_hazard_rating, n.drought_expected_annual_loss_rating,
       CURRENT_TIMESTAMP() AS built_at
FROM use u
LEFT JOIN cwns c ON c.cnty = UPPER(u.county_name)
LEFT JOIN nri  n USING (county_fips)
"""

# ---------------------------------------------------------------- basin grain (NOT flattened)
SQL_BASIN = f"""
CREATE OR REPLACE TABLE `{DS}.in_water_stress_basin` AS
SELECT
  aq30_id AS basin_id, name_1 AS state, area_km2,
  SAFE_CAST(bws_score AS FLOAT64) AS stress_score,   bws_label AS stress_label,
  SAFE_CAST(bwd_score AS FLOAT64) AS depletion_score, bwd_label AS depletion_label,
  SAFE_CAST(sev_score AS FLOAT64) AS seasonal_variability_score, sev_label AS seasonal_variability_label,
  SAFE_CAST(gtd_score AS FLOAT64) AS groundwater_decline_score,  gtd_label AS groundwater_decline_label,
  SAFE_CAST(rfr_score AS FLOAT64) AS riverine_flood_score,       rfr_label AS riverine_flood_label,
  CURRENT_TIMESTAMP() AS built_at
FROM `energy-platfrom.energy.water_aqueduct`
WHERE UPPER(IFNULL(name_1, '')) LIKE '%INDIANA%'
"""

for name, sql in [("in_water_county", SQL_COUNTY), ("in_water_stress_basin", SQL_BASIN)]:
    client.query(sql).result()
    print(f"built {name}")

m = list(client.query(f"""
SELECT COUNT(*) n,
       COUNTIF(treatment_facilities IS NULL) no_cwns,
       COUNTIF(wastewater_headroom_mgd IS NULL) no_headroom,
       COUNTIF(wastewater_headroom_mgd <= 0) at_or_over_capacity,
       ROUND(SUM(total_withdrawal_mgd), 1) total_mgd,
       ROUND(SUM(thermoelectric_mgd), 1) thermo_mgd,
       ANY_VALUE(use_year) yr
FROM `{DS}.in_water_county`"""))[0]
b = list(client.query(f"""
SELECT COUNT(*) n, ROUND(AVG(stress_score), 2) avg_stress,
       COUNTIF(stress_score >= 3) high_stress
FROM `{DS}.in_water_stress_basin`"""))[0]

print()
print(f"in_water_county      : {m.n} counties (use year {m.yr})")
print(f"  statewide withdrawal: {m.total_mgd:,} Mgal/d, of which thermoelectric {m.thermo_mgd:,}")
print(f"  no wastewater match : {m.no_cwns}")
print(f"  headroom unknown    : {m.no_headroom}   at/over design capacity: {m.at_or_over_capacity}")
print(f"in_water_stress_basin: {b.n} basins, avg stress score {b.avg_stress}, "
      f"{b.high_stress} scoring high or worse")
assert m.n == 92, f"expected 92 Indiana counties, got {m.n}"

for t, src, meth, n, note in [
    ("in_water_county", "energy.water_use (USGS 2015) x energy.water_cwns_2022 (EPA CWNS 2022)",
     "Indiana slice; withdrawals in Mgal/d by sector and by ground/surface; wastewater rolled up "
     "per county with headroom = design flow - existing flow", m.n,
     "Water is a first-order DC constraint: an evaporatively-cooled campus runs ~1-5 Mgal/d. "
     "Wastewater headroom is the discharge-side limit people forget until late; NULL where either "
     "side is unpublished and must never read as unlimited. USGS use year is 2015 - context, not a "
     "current measurement."),
    ("in_water_stress_basin", "energy.water_aqueduct (WRI Aqueduct 3.0)",
     "Indiana basins, kept at BASIN grain", b.n,
     "Deliberately NOT averaged onto counties. Aqueduct publishes per hydrological basin and basins "
     "do not follow county lines; a per-county average would manufacture a number the publisher "
     "never issued - the same error class as a centroid."),
]:
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name=@t",
                 job_config=bigquery.QueryJobConfig(query_parameters=[
                     bigquery.ScalarQueryParameter("t", "STRING", t)])).result()
    client.query(
        f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
        f"VALUES (@t,@s,@m,@n,0.0,CURRENT_TIMESTAMP(),@no)",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", t),
            bigquery.ScalarQueryParameter("s", "STRING", src),
            bigquery.ScalarQueryParameter("m", "STRING", meth),
            bigquery.ScalarQueryParameter("n", "INT64", int(n)),
            bigquery.ScalarQueryParameter("no", "STRING", note)])).result()
    print(f"registered {t}")
