import os, sys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")
q = """
SELECT table_name, row_count
FROM `energy-platfrom.energy.__TABLES__`
WHERE REGEXP_CONTAINS(LOWER(table_id), r'substation|osm|hifld')
"""
# __TABLES__ uses table_id/row_count
q = """
SELECT table_id, row_count
FROM `energy-platfrom.energy.__TABLES__`
WHERE REGEXP_CONTAINS(LOWER(table_id), r'substation|osm_|hifld')
ORDER BY table_id
"""
for r in c.query(q).result():
    print(f"  {r.table_id}: {r.row_count:,}")
