import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")
q = """SELECT r.table_name, r.n_rows, r.built_at
FROM `energy-platfrom.indiana_app._registry` r
WHERE r.table_name LIKE 'in_si_%' AND r.table_name != 'in_si_signals'
ORDER BY r.built_at"""
print("REGISTRY (lane C rows):")
tot = 0
for r in c.query(q).result():
    print(f"  {r.table_name:45s} {r.n_rows:>8,d}  {r.built_at}")
    tot += r.n_rows
print(f"  TOTAL NEW ROWS: {tot:,d}")
# confirm table row counts match registry
print("\nTABLE vs REGISTRY check:")
for t in c.list_tables("energy-platfrom.indiana_app"):
    if t.table_id.startswith("in_si_") and t.table_id != "in_si_signals":
        n = c.get_table(f"energy-platfrom.indiana_app.{t.table_id}").num_rows
        print(f"  {t.table_id:45s} {n:>8,d}")
