import os, sys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")

t = c.get_table("energy-platfrom.energy.pjm_queuescope_results")
print("pjm_queuescope_results cols:", [f.name for f in t.schema], f"({t.num_rows:,} rows)")
t = c.get_table("energy-platfrom.indiana_app.in_substations")
print("in_substations cols:", [f.name for f in t.schema], f"({t.num_rows:,} rows)")

print("\nAEP bus_label samples:")
for r in c.query("""
  SELECT DISTINCT bus_label FROM `energy-platfrom.energy.pjm_queuescope_results`
  WHERE owner_label='AEP' LIMIT 20""").result():
    print("  ", repr(r.bus_label))
print("\nin_substations name samples:")
for r in c.query("SELECT * FROM `energy-platfrom.indiana_app.in_substations` LIMIT 6").result():
    print("  ", {k: str(v)[:40] for k, v in dict(r).items()})
