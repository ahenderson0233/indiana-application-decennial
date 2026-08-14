import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")
print("TABLES in indiana_app:")
try:
    for t in c.list_tables("energy-platfrom.indiana_app"):
        tbl = c.get_table(f"energy-platfrom.indiana_app.{t.table_id}")
        print(f"  {t.table_id}: {tbl.num_rows} rows")
except Exception as e:
    print("  ERROR:", e)
