import os, sys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")
q = r"""
SELECT source_name, status, endpoint, object_names, acquisition_method
FROM `energy-platfrom.energy.registry_sources`
WHERE REGEXP_CONTAINS(LOWER(source_name), r'pjm')
   OR REGEXP_CONTAINS(LOWER(IFNULL(endpoint,'')), r'pjm')
"""
for r in c.query(q).result():
    print("-" * 90)
    print("NAME:", r.source_name)
    print("STATUS:", (r.status or "")[:260])
    print("ENDPOINT:", r.endpoint)
    print("OBJECTS:", r.object_names)
    print("METHOD:", (r.acquisition_method or "")[:180])
