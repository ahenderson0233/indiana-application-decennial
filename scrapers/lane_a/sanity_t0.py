import os, sys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")
for r in c.query("""
  SELECT bus_label, matched_substation_name, matched_source, lat, lon, match_confidence
  FROM `energy-platfrom.indiana_app.in_pjm_bus_locations_candidate`
  WHERE location_method='pjm_queue_facid' ORDER BY RAND() LIMIT 8""").result():
    print(f"  {r.bus_label!r:38} <-> FAC {r.matched_substation_name!r:12} [{r.matched_source}] "
          f"({r.lat:.4f},{r.lon:.4f}) {r.match_confidence}")
for r in c.query("""
  SELECT location_method, COUNT(*) n FROM `energy-platfrom.indiana_app.in_pjm_bus_locations_candidate`
  WHERE collision_count > 1 AND location_method='none' GROUP BY 1""").result():
    print(f"none-with-ambiguity: {r.n:,}")
