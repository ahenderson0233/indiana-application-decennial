import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")
q = """SELECT DISTINCT county FROM `energy-platfrom.energy.eia861_service_territory`
WHERE state='IN' AND utility_id_eia=9324 ORDER BY county"""
rows = [r.county for r in c.query(q).result()]
print("I&M(9324) IN COUNTIES (%d):" % len(rows), rows)
