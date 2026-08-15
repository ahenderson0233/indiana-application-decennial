"""WIRE-NEXT batch 2 (audit batch-2 finds): plants/generators, legislative trio, emitters,
turbines, hazards, DR, CWNS, QCT (into bonus set), EQR identity route, and friends.
Census-keyed predicates; everything registered."""
import json, datetime, decimal
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
E = "`energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")

TARGETS = ["eia860_generators", "eia_plants", "eia860m_generators", "storm_events",
           "osm_power_lines", "osm_power_substations", "openstates_energy_bill_vote_people",
           "openstates_energy_bill_actions", "openstates_energy_bill_sponsorships",
           "ghgrp_facilities", "ghgrp_emitter_facilities", "wind_turbines",
           "gov_surplus_frpp", "fema_disaster_declarations", "weather_stations",
           "eia923_fuel_receipts_costs", "eia861_demand_response", "water_cwns_2022",
           "sba_foia_loans", "acs_tract_vacancy", "eqr_identity", "gas_phmsa_distribution",
           "candidate_sites_schools", "candidate_sites_private_schools", "nfirs_fireincident_2024"]
keys = {r.table_id: (r.method, r.key_column) for r in client.query(
    f"""SELECT table_id, method, key_column FROM `{DS}._indiana_census`
        WHERE in_rows > 0 AND table_id IN UNNEST({TARGETS!r})""")}
for t in TARGETS:
    if t not in keys:
        print(f"SKIP {t}: not census-positive"); continue
    method, col = keys[t]
    pred = (f"UPPER(CAST(`{col}` AS STRING)) IN ('IN','INDIANA','18')" if method == "state"
            else f"STARTS_WITH(CAST(`{col}` AS STRING), '18')")
    dest = "in_" + t
    sql = f"CREATE OR REPLACE TABLE `{DS}.{dest}` AS SELECT * FROM {E}.{t}` WHERE {pred}"
    dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
    client.query(sql).result()
    n = list(client.query(f"SELECT COUNT(*) AS n FROM `{DS}.{dest}`"))[0].n
    client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
      VALUES ('{dest}','energy.{t}','census-keyed clip ({method}:{col})', {n},
              {dry.total_bytes_processed/1e9:.3f}, CURRENT_TIMESTAMP(),
              'WIRE-NEXT batch 2 (audit batch 2)')""").result()
    print(f"{dest}: {n:,}")

# QCT into the bonus set (the fifth bonus geography)
cols = [s.name for s in client.get_table("energy-platfrom.energy.incentive_qct").schema]
gcol = next((c for c in cols if c.lower() in ("geog", "geom")), None)
gjson = next((c for c in cols if "geojson" in c.lower()), None)
geo = gcol if gcol else f"SAFE.ST_GEOGFROMGEOJSON({gjson})"
keyc = next((c for c in cols if "geoid" in c.lower() or "fips" in c.lower() or "tract" in c.lower()), cols[0])
statec = next((c for c in cols if "state" in c.lower()), None)
client.query(f"""
INSERT `{DS}.in_bonus_geo` (kind, key, geog, attrs_json)
SELECT 'qct', CAST({keyc} AS STRING), g, TO_JSON_STRING(STRUCT(CAST({statec} AS STRING) AS state))
FROM (SELECT *, {geo} AS g FROM {E}.incentive_qct`)
WHERE g IS NOT NULL
  AND (UPPER(CAST({statec} AS STRING)) IN ('IN','INDIANA','18') OR STARTS_WITH(CAST({keyc} AS STRING),'18'))
  AND NOT EXISTS (SELECT 1 FROM `{DS}.in_bonus_geo` b WHERE b.kind='qct')""").result()
nq = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_bonus_geo` WHERE kind='qct'"))[0].n
client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES ('in_bonus_geo','energy.incentive_qct','APPEND qct kind',
          (SELECT COUNT(*) FROM `{DS}.in_bonus_geo`), 0.05, CURRENT_TIMESTAMP(),
          'qct added: {nq} IN tracts - fifth bonus geography')""").result()
print(f"qct bonus features: {nq}")
print("WIRE-NEXT BATCH 2 COMPLETE")
