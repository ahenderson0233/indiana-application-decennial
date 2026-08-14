import os, sys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")

for tid in ("txexp_pjm_rtep_upgrades", "txexp_pjm_tcic_upgrade_info"):
    t = c.get_table(f"energy-platfrom.energy.{tid}")
    print(f"--- {tid}: {t.num_rows:,} rows")
    print("cols:", [f.name for f in t.schema])
for r in c.query("SELECT * FROM `energy-platfrom.energy.txexp_pjm_rtep_upgrades` WHERE upgrade_id='b0839' LIMIT 1").result():
    print("\nb0839 held XML row:", {k: str(v)[:90] for k, v in dict(r).items() if v is not None})
for r in c.query("SELECT * FROM `energy-platfrom.energy.txexp_pjm_tcic_upgrade_info` LIMIT 2").result():
    print("\nTCIC row:", {k: str(v)[:70] for k, v in dict(r).items() if v is not None})
