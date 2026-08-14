import os, sys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")

q1 = r"""
SELECT source_name, status, endpoint, object_names, notes, acquisition_method, access
FROM `energy-platfrom.energy.registry_sources`
WHERE REGEXP_CONTAINS(LOWER(source_name), r'miso|nipsco|aes indiana|duke.*ind|centerpoint|vectren|indiana michigan|i&m|iurc|hosting')
"""
for r in c.query(q1).result():
    print("-" * 90)
    print("NAME:", r.source_name)
    print("STATUS:", (r.status or "")[:300])
    print("ENDPOINT:", r.endpoint)
    print("OBJECTS:", r.object_names)
    print("METHOD:", (r.acquisition_method or "")[:200])
    print("ACCESS:", r.access)
    print("NOTES:", (r.notes or "")[:300])

print()
print("=== indiana_app tables ===")
try:
    for t in c.list_tables("energy-platfrom.indiana_app"):
        print(" ", t.table_id)
except Exception as e:
    print("  ", type(e).__name__, str(e)[:200])

print()
print("=== miso_poi_monitored_facilities schema+sample ===")
t = c.get_table("energy-platfrom.energy.miso_poi_monitored_facilities")
print("cols:", [f.name for f in t.schema])
for r in c.query("SELECT * FROM `energy-platfrom.energy.energy.miso_poi_monitored_facilities` LIMIT 2" if False else "SELECT * FROM `energy-platfrom.energy.miso_poi_monitored_facilities` LIMIT 2").result():
    print(dict(r))
