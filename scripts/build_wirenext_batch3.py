"""WIRE-NEXT batch 3 (audit batch-3 finds): existing data centers, plants, solar,
interconnection-cost benchmarks, legislative remainder, county context pack, retail sales."""
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
E = "`energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")

TARGETS = ["power_plants", "data_centers_datacentermap", "solar_pv_facilities",
           "lbnl_interconnection_costs", "openstates_energy_bill_versions",
           "openstates_energy_bill_sources", "openstates_energy_bill_votes",
           "openstates_energy_bill_abstracts", "openstates_energy_bills_v2",
           "fema_nri_counties", "qcew_county_labor", "acs_county", "water_use",
           "solar_potential", "usa_structures_county", "cbp_county_industry",
           "workforce_ipeds_directory", "candidate_sites_colleges",
           "eia861_sales", "eia861_sales_ult_cust", "fsis_establishments"]
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
              'WIRE-NEXT batch 3 (audit batch 3)')""").result()
    print(f"{dest}: {n:,}")
print("WIRE-NEXT BATCH 3 COMPLETE")
