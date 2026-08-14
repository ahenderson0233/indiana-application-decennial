import os, sys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")
mine = ["in_miso_poi_identity", "in_pjm_rtep_upgrades", "in_rto_expansion",
        "in_pjm_nucra_costs", "in_pjm_gis_queues", "in_pjm_bus_locations_candidate",
        "in_pjm_rtep_upgrade_details", "in_pjm_rtep_cost_allocations"]
print("=== lane-A created tables ===")
for t in mine:
    n = list(c.query(f"SELECT COUNT(*) n FROM `energy-platfrom.indiana_app.{t}`").result())[0].n
    alarm = "  <-- TRUNCATION ALARM" if n % 1000 == 0 or n % 2000 == 0 else ""
    print(f"  {t}: {n:,}{alarm}")
print("\n=== registry rows for lane-A tables ===")
q = """SELECT table_name, n_rows, built_at FROM `energy-platfrom.indiana_app._registry`
WHERE table_name IN UNNEST(@t) ORDER BY table_name, built_at"""
job = c.query(q, job_config=bigquery.QueryJobConfig(query_parameters=[
    bigquery.ArrayQueryParameter("t", "STRING", mine)]))
for r in job.result():
    print(f"  {r.table_name}: {r.n_rows:,} @ {r.built_at}")
