import os, sys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")

print("=== created tables QA ===")
for t in ("in_miso_poi_identity", "in_pjm_rtep_upgrades", "in_rto_expansion"):
    n = list(c.query(f"SELECT COUNT(*) n FROM `energy-platfrom.indiana_app.{t}`").result())[0].n
    alarm = " <-- TRUNCATION ALARM" if n % 1000 == 0 or n % 2000 == 0 else ""
    print(f"  {t}: {n:,} rows{alarm}")

print("\n=== teac_materials / date sample (PJM, IN rows) ===")
for r in c.query("""
  SELECT upgrade_id, location, voltage, status,
         projected_in_service_date, actual_in_service_date, teac_materials, last_updated
  FROM `energy-platfrom.indiana_app.in_pjm_rtep_upgrades`
  WHERE REGEXP_CONTAINS(UPPER(IFNULL(state,'')), r'(^|[^A-Z])IN([^A-Z]|$)') LIMIT 4""").result():
    print(dict(r))

print("\n=== in_rto_expansion Indiana sample ===")
for r in c.query("""
  SELECT rto, project_id, project_name, kv_max, from_endpoint, to_endpoint, in_service_date,
         states_named, owner FROM `energy-platfrom.indiana_app.in_rto_expansion`
  WHERE rto='MISO' AND from_endpoint IS NOT NULL LIMIT 3""").result():
    print(dict(r))

print("\n=== _registry rows written this run ===")
for r in c.query("""
  SELECT table_name, n_rows, built_at FROM `energy-platfrom.indiana_app._registry`
  WHERE DATE(built_at) = CURRENT_DATE() ORDER BY built_at""").result():
    print(f"  {r.table_name}: {r.n_rows:,} @ {r.built_at}")

print("\n=== states_named token check (no false 'IN' matches) ===")
for r in c.query("""
  SELECT states_named, COUNT(*) n FROM `energy-platfrom.indiana_app.in_rto_expansion`
  GROUP BY 1 ORDER BY n DESC LIMIT 12""").result():
    print(f"  {r.states_named!r}: {r.n}")
