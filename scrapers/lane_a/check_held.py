import os, sys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")

for tid in ["energy.miso_poi_attributes", "indiana_app.in_miso_poi", "indiana_app._registry"]:
    t = c.get_table(f"energy-platfrom.{tid}")
    print(f"--- {tid}: {t.num_rows:,} rows")
    print("   ", [(f.name, f.field_type) for f in t.schema])

print()
q = """
SELECT
  (SELECT COUNT(*) FROM `energy-platfrom.energy.miso_poi_attributes`) AS attr_rows,
  (SELECT COUNT(DISTINCT poi_name) FROM `energy-platfrom.energy.miso_poi_attributes`) AS attr_pois,
  (SELECT COUNTIF(has_coordinates) FROM `energy-platfrom.energy.miso_poi_attributes`) AS attr_with_coords,
  (SELECT COUNT(DISTINCT bus_number) FROM `energy-platfrom.energy.miso_poi_attributes`) AS attr_busnums,
  (SELECT COUNT(DISTINCT poi_name) FROM `energy-platfrom.energy.miso_poi_monitored_facilities`) AS mf_pois,
  (SELECT COUNT(DISTINCT m.poi_name)
     FROM `energy-platfrom.energy.miso_poi_monitored_facilities` m
     JOIN `energy-platfrom.energy.miso_poi_attributes` a USING (poi_name)) AS mf_pois_matched
"""
r = list(c.query(q).result())[0]
print(dict(r))
print()
for r in c.query("SELECT * FROM `energy-platfrom.energy.miso_poi_attributes` LIMIT 3").result():
    print(dict(r))
