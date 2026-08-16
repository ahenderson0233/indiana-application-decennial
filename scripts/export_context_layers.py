"""A2 — route the orphaned context tables to a surface.

Every one was value-read first; four of the eight checks changed what gets built:

  · in_wind_turbines is a FALSE ORPHAN. Its coordinates are `xlong`/`ylat` (not lat/lon, which
    is why a naive scan missed them) and its 1,652 turbines are ALREADY on the map inside
    facilities.geojson. It needed a provenance line, not a feature. Not exported here.
  · in_water_cwns_2022 is STRUCTURALLY EMPTY — 404 rows, 0 with facid, 0 with latitude; only
    `state` is populated. Waived, not wired. A zero is a claim about the instrument, and here
    the instrument is right: there is nothing in it.
  · in_ghgrp_emitter_facilities is a SUBSET of in_ghgrp_facilities (all 246 of its facility_ids
    are among the other's 263). facilities is the layer; emitter supplies the year/NAICS detail.
  · in_osm_power_lines is ADDITIVE, not duplicate: 5,013 of its lines are >=100 kV against
    2,623 in in_transmission_lines. OSM is materially more complete for Indiana transmission.

Writes data/context.geojson.gz (map layers) and data/context.json.gz (page tables).
Read-only against BigQuery. Idempotent.
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
import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)
def rows(sql): return [dict(r) for r in client.query(sql)]

# ================= MAP LAYERS =================
feats = []
def pt(lon, lat, props):
    if lon is None or lat is None: return
    feats.append({"type": "Feature", "properties": props,
                  "geometry": {"type": "Point", "coordinates": [round(float(lon), 6), round(float(lat), 6)]}})

# --- OSM power lines and substations: REMOVED from this payload 2026-08-15, superseded by the
#     A6 union (operator ruling: one merged layer, not two partial ones).
#     Lines now reach the map through `in_transmission_union` in grid.geojson — HIFLD plus the
#     1,114 OSM lines (2,706 km) that no HIFLD line comes within 100 m of.
#     Substations were ALREADY unioned upstream in `in_substations` (sources = HIFLD+OSM 2,354 /
#     OSM-only 933 / HIFLD-only 571); drawing them again here was a rival partial copy, and
#     2,439 of the 2,873 ids were already in that union.

# --- GHGRP emitters: neighbours that already hold air permits. facilities is the superset;
#     emitter adds the reporting year and NAICS.
ghgrp = rows(f"""
  WITH latest AS (
    SELECT CAST(facility_id AS STRING) fid, MAX(SAFE_CAST(year AS INT64)) yr,
           ANY_VALUE(primary_naics) naics
    FROM `{DS}.in_ghgrp_emitter_facilities` GROUP BY 1)
  SELECT ANY_VALUE(f.facility_name) name, CAST(f.facility_id AS STRING) fid,
         ANY_VALUE(f.city) city, ANY_VALUE(f.county) county,
         ANY_VALUE(f.parent_company) parent, ANY_VALUE(f.naics_code) naics_code,
         ANY_VALUE(f.latitude) lat, ANY_VALUE(f.longitude) lon,
         ANY_VALUE(l.yr) report_year, ANY_VALUE(l.naics) emitter_naics
  FROM `{DS}.in_ghgrp_facilities` f
  LEFT JOIN latest l ON l.fid = CAST(f.facility_id AS STRING)
  WHERE f.latitude IS NOT NULL AND f.longitude IS NOT NULL
  GROUP BY f.facility_id""")
for r in ghgrp:
    pt(r["lon"], r["lat"], {"layer": "ghgrp", "name": r["name"], "city": r["city"],
       "county": r["county"], "parent": r["parent"],
       "naics": r["naics_code"] or r["emitter_naics"], "report_year": r["report_year"]})

# --- Federal surplus real property: a genuine siting lead, not just context.
frpp = rows(f"""
  SELECT reporting_agency, using_agency, county_name, city_name, street_address,
         latitude, longitude
  FROM `{DS}.in_gov_surplus_frpp`
  WHERE latitude IS NOT NULL AND longitude IS NOT NULL""")
for r in frpp:
    pt(r["longitude"], r["latitude"], {"layer": "frpp", "agency": r["reporting_agency"],
       "using": r["using_agency"], "county": r["county_name"], "city": r["city_name"],
       "addr": r["street_address"]})

# --- Schools: REMOVED 2026-08-15 by operator ruling. They were staged for a separate Illinois
#     experiment and carry no material value in Indiana siting. Waived below rather than
#     silently deleted, so the next session does not "rediscover" them as a gap.

# --- Weather stations: REMOVED 2026-08-15 by operator ruling. A GHCN station tells a siter
#     nothing they act on; the weather that matters reaches them through the storm-event and
#     disaster history on Community. Waived below rather than deleted.

gp = os.path.join(REPO, "data", "context.geojson.gz")
with gzip.open(gp, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump({"type": "FeatureCollection", "features": feats}, f, separators=(",", ":"), default=jd)
by = {}
for ft in feats: by[ft["properties"]["layer"]] = by.get(ft["properties"]["layer"], 0) + 1
print(f"context.geojson.gz {os.path.getsize(gp)/1024:.0f} KB · " + " · ".join(f"{k} {v}" for k, v in sorted(by.items())))

# ================= PAGE TABLES =================
out = {}

# Grid: the current Indiana generating fleet, by status. 2001-2026 is a time series; the
# CURRENT picture is the latest report_date only - summing all years would trible-count.
out["fleet"] = rows(f"""
  SELECT operational_status, technology_description tech,
         COUNT(*) units, ROUND(SUM(SAFE_CAST(capacity_mw AS FLOAT64)),1) mw
  FROM `{DS}.in_eia860_generators`
  WHERE report_date = (SELECT MAX(report_date) FROM `{DS}.in_eia860_generators`)
  GROUP BY 1,2 HAVING mw > 0 ORDER BY mw DESC""")
out["fleet_asof"] = rows(f"""SELECT CAST(MAX(report_date) AS STRING) d FROM `{DS}.in_eia860_generators`""")[0]["d"]

# eia860m: monthly, forward-looking - planned retirements are what a 300 MW load cares about
out["retirements"] = rows(f"""
  SELECT plant_name, county, technology, entity_name,
         SAFE_CAST(nameplate_capacity_mw AS FLOAT64) mw,
         SAFE_CAST(planned_retirement_year AS INT64) yr,
         SAFE_CAST(planned_retirement_month AS INT64) mo
  FROM `{DS}.in_eia860m_generators`
  WHERE SAFE_CAST(planned_retirement_year AS INT64) IS NOT NULL
  ORDER BY yr, mo""")

# Market: fuel cost history, demand response, FERC EQR filers
out["fuel_costs"] = rows(f"""
  SELECT CAST(report_date AS STRING) d, fuel_type_code_pudl fuel,
         ROUND(AVG(SAFE_CAST(fuel_cost_per_mmbtu AS FLOAT64)),3) usd_per_mmbtu,
         ROUND(SUM(SAFE_CAST(fuel_received_mmbtu AS FLOAT64))) mmbtu
  FROM `{DS}.in_eia923_fuel_receipts_costs`
  WHERE fuel_cost_per_mmbtu IS NOT NULL
  GROUP BY 1,2 ORDER BY d""")
out["demand_response"] = rows(f"""
  SELECT utility_name_eia utility, customer_class, CAST(report_date AS STRING) d,
         SAFE_CAST(actual_peak_demand_savings_mw AS FLOAT64) actual_mw,
         SAFE_CAST(potential_peak_demand_savings_mw AS FLOAT64) potential_mw,
         SAFE_CAST(customers AS FLOAT64) customers
  FROM `{DS}.in_eia861_demand_response`
  WHERE actual_peak_demand_savings_mw IS NOT NULL
     OR potential_peak_demand_savings_mw IS NOT NULL
  ORDER BY d DESC, actual_mw DESC""")
out["dr_denominator"] = rows(f"""
  SELECT COUNT(*) n, COUNTIF(actual_peak_demand_savings_mw IS NOT NULL) with_actual,
         COUNTIF(potential_peak_demand_savings_mw IS NOT NULL) with_potential
  FROM `{DS}.in_eia861_demand_response`""")[0]
out["eqr_filers"] = rows(f"""
  SELECT company_name, ANY_VALUE(contact_city) city, COUNT(*) quarters,
         MIN(year_quarter) first_q, MAX(year_quarter) last_q
  FROM `{DS}.in_eqr_identity` GROUP BY company_name ORDER BY quarters DESC""")

# Community / risk: disasters and severe weather, both county grain
out["disasters"] = rows(f"""
  SELECT incidentType incident, COUNT(*) n, COUNT(DISTINCT disasterNumber) events,
         COUNT(DISTINCT designatedArea) counties,
         MIN(SUBSTR(CAST(declarationDate AS STRING),1,10)) first_seen,
         MAX(SUBSTR(CAST(declarationDate AS STRING),1,10)) last_seen
  FROM `{DS}.in_fema_disaster_declarations` GROUP BY 1 ORDER BY n DESC""")
# fipsCountyCode='000' is NOT a county: it carries 'Statewide' and a tribal TDSA designation.
# Left in, the county roll-up reads 93 areas for a 92-county state - the same shape as the IOCS
# 'STATE' poison row. Excluded here and surfaced separately so it is not simply discarded.
out["disasters_by_county"] = rows(f"""
  SELECT CONCAT(fipsStateCode, LPAD(CAST(fipsCountyCode AS STRING),3,'0')) fips,
         COUNT(DISTINCT disasterNumber) declarations
  FROM `{DS}.in_fema_disaster_declarations`
  WHERE fipsCountyCode IS NOT NULL AND CAST(fipsCountyCode AS STRING) != '000'
  GROUP BY 1""")
out["disasters_noncounty"] = rows(f"""
  SELECT designatedArea area, COUNT(DISTINCT disasterNumber) declarations
  FROM `{DS}.in_fema_disaster_declarations`
  WHERE CAST(fipsCountyCode AS STRING) = '000' GROUP BY 1 ORDER BY declarations DESC""")
out["storms"] = rows(f"""
  SELECT event_type, COUNT(*) n, MIN(year) first_yr, MAX(year) last_yr,
         SUM(SAFE_CAST(injuries_direct AS INT64)) injuries
  FROM `{DS}.in_storm_events` GROUP BY 1 ORDER BY n DESC LIMIT 20""")

# SI context: tract vacancy and SBA lending
out["vacancy_top"] = rows(f"""
  SELECT geoid, name, SAFE_CAST(housing_units_total AS INT64) units,
         SAFE_CAST(vacant_total AS INT64) vacant,
         ROUND(SAFE_CAST(vacancy_rate AS FLOAT64),1) rate, acs_year
  FROM `{DS}.in_acs_tract_vacancy`
  WHERE SAFE_CAST(housing_units_total AS INT64) > 200
  ORDER BY SAFE_CAST(vacancy_rate AS FLOAT64) DESC LIMIT 60""")
out["sba"] = rows(f"""
  SELECT program, approvalfy fy, COUNT(*) loans,
         ROUND(SUM(SAFE_CAST(grossapproval AS FLOAT64))) gross_usd
  FROM `{DS}.in_sba_foia_loans` GROUP BY 1,2 ORDER BY fy DESC, program""")

# Gas distribution operators (mileage by operator-year)
out["gas_operators"] = rows(f"""
  SELECT operator_name, MAX(SAFE_CAST(report_year AS INT64)) latest_year, COUNT(*) reports,
         ROUND(MAX(SAFE_CAST(mmiles_plastic AS FLOAT64)),1) plastic_miles,
         ROUND(MAX(SAFE_CAST(mmiles_steel_cp_coated AS FLOAT64)),1) steel_coated_miles
  FROM `{DS}.in_gas_phmsa_distribution` GROUP BY 1 ORDER BY reports DESC""")

out["waivers"] = [{"table": "in_water_cwns_2022", "rows": 404,
   "reason": "structurally empty — 0 of 404 rows carry facid or latitude; only `state` is "
             "populated. Nothing to render. Measured, not assumed."},
  {"table": "in_wind_turbines", "rows": 1652,
   "reason": "not a gap — already rendered inside facilities.geojson as the 'wind' layer "
             "(coords are xlong/ylat). Given a provenance line instead of a duplicate layer."},
  {"table": "in_osm_power_lines", "rows": 10906,
   "reason": "MERGED, not waived — reaches the map through in_transmission_union alongside the "
             "HIFLD linework. 1,114 OSM lines (2,706 km) had no HIFLD line within 100 m and are "
             "now visible for the first time; the rest were duplicates and are suppressed. One "
             "layer, not two partial ones."},
  {"table": "in_osm_power_substations", "rows": 2873,
   "reason": "MERGED UPSTREAM — in_substations was already a HIFLD+OSM union (sources: HIFLD+OSM "
             "2,354 matched at 0.5 m average, OSM-only 933, HIFLD-only 571). 2,439 of these 2,873 "
             "ids were already in it, so a separate layer was a rival partial copy and has been "
             "removed. The union's `sources` badge now shows on every substation."},
  {"table": "in_weather_stations", "rows": 2108,
   "reason": "OPERATOR RULING 2026-08-15: removed from the app. A GHCN station location is not "
             "something a siter acts on; the weather that matters reaches them through the storm "
             "event and disaster history on Community. Held, not rendered."},
  {"table": "in_candidate_sites_schools + in_candidate_sites_private_schools", "rows": 2518,
   "reason": "OPERATOR RULING 2026-08-15: removed from the app. These were staged for a separate "
             "Illinois experiment and carry no material value in Indiana siting. Kept in the "
             "warehouse, deliberately not rendered — recorded here so they are not rediscovered "
             "as a coverage gap later."},
  {"table": "in_data_centers_deduped", "rows": 242,
   "reason": "superseded 2026-08-15 by in_data_centers_located, which carries the same rows plus "
             "the publisher's location_precision and 7 peeringdb facilities the union had missed. "
             "The successor is what the map reads; this is kept as the build's intermediate step."}]

jp = os.path.join(REPO, "data", "context.json.gz")
with gzip.open(jp, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(out, f, separators=(",", ":"), default=jd)
print(f"context.json.gz {os.path.getsize(jp)/1024:.0f} KB · " +
      " · ".join(f"{k} {len(v) if isinstance(v, list) else 1}" for k, v in out.items()))
