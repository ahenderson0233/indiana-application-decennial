import os, sys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")
t = c.get_table("energy-platfrom.energy.bus_hifld")
print("bus_hifld cols:", [f.name for f in t.schema])
for r in c.query("SELECT * FROM `energy-platfrom.energy.bus_hifld` LIMIT 2").result():
    print("  ", {k: str(v)[:40] for k, v in dict(r).items() if v is not None})
q = """
SELECT
  (SELECT COUNT(DISTINCT bus_number) FROM `energy-platfrom.energy.pjm_queuescope_results`
   WHERE owner_label='AEP') AS n_qs_bus,
  (SELECT COUNT(DISTINCT b.bus_number)
   FROM (SELECT DISTINCT bus_number FROM `energy-platfrom.energy.pjm_queuescope_results`
         WHERE owner_label='AEP') b
   JOIN `energy-platfrom.energy.bus_hifld` h ON CAST(h.bus_id AS INT64) = b.bus_number) AS joined
"""
try:
    r = list(c.query(q).result())[0]
    print(f"AEP QueueScope distinct bus_number: {r.n_qs_bus:,}; joining bus_hifld.bus_id: {r.joined:,}")
except Exception as e:
    print("join attempt failed (column name?):", str(e)[:300])
