import os, sys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")
for tid in ("nat_substations_hifld", "osm_power_substations", "mat_grid_substations"):
    t = c.get_table(f"energy-platfrom.energy.{tid}")
    print(f"--- {tid} ({t.num_rows:,}):")
    print("   ", [f.name for f in t.schema])
    for r in c.query(f"SELECT * FROM `energy-platfrom.energy.{tid}` LIMIT 1").result():
        print("   ", {k: str(v)[:45] for k, v in dict(r).items() if v is not None})
