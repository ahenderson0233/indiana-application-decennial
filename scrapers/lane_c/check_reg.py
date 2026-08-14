import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")
t = c.get_table("energy-platfrom.indiana_app._registry")
print("REGISTRY SCHEMA:", [(f.name, f.field_type) for f in t.schema])
q = "SELECT table_name, source, method, n_rows, built_at FROM `energy-platfrom.indiana_app._registry` ORDER BY built_at"
for r in c.query(q).result():
    print(f"  {r.table_name} | {r.source[:60] if r.source else ''} | {r.n_rows} | {r.built_at}")
