import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")
t = c.get_table("energy-platfrom.energy.registry_sources")
print("SCHEMA:", [f.name for f in t.schema])
q = """SELECT * FROM `energy-platfrom.energy.registry_sources`
WHERE REGEXP_CONTAINS(LOWER(source_name), r'indiana|indianapolis|marion|allen|vanderburgh|fort wayne|evansville|sri|zeus')"""
for r in c.query(q).result():
    d = dict(r)
    print("---")
    for k, v in d.items():
        print(f"  {k}: {str(v)[:400]}")
