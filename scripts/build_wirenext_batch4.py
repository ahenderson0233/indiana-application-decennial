"""WIRE-NEXT batch 4 (audit tail): connectivity (PeeringDB), airspace, tribal land,
bills master, SEC registrants, plant closures, commission/docket context."""
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
E = "`energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")

TARGETS = ["data_centers_peeringdb", "peeringdb_facilities", "openstates_energy_bills",
           "land_faa_sua", "tribal_land", "sec_cik_registrant_state",
           "fsis_establishments_inactive", "commission_posture", "dc_docket_tracker",
           "balancing_authority_areas", "groundwater_sites", "puc_state_access_ledger"]
keys = {r.table_id: (r.method, r.key_column) for r in client.query(
    f"""SELECT table_id, method, key_column FROM `{DS}._indiana_census`
        WHERE in_rows > 0 AND table_id IN UNNEST({TARGETS!r})""")}
for t in TARGETS:
    if t not in keys:
        print(f"SKIP {t}"); continue
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
              {dry.total_bytes_processed/1e9:.3f}, CURRENT_TIMESTAMP(), 'WIRE-NEXT batch 4 (audit tail)')""").result()
    print(f"{dest}: {n:,}")
print("WIRE-NEXT BATCH 4 COMPLETE")
