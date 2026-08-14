import os, sys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")
q = """
SELECT
  (SELECT COUNT(DISTINCT bus_number) FROM `energy-platfrom.energy.pjm_queuescope_results`
   WHERE owner_label='AEP') AS n_qs_bus,
  (SELECT COUNT(DISTINCT b.bus_number)
   FROM (SELECT DISTINCT bus_number FROM `energy-platfrom.energy.pjm_queuescope_results`
         WHERE owner_label='AEP') b
   JOIN `energy-platfrom.energy.bus_hifld` h ON SAFE_CAST(h.bus_id AS INT64) = SAFE_CAST(b.bus_number AS INT64)) AS by_id,
  (SELECT MIN(SAFE_CAST(bus_id AS INT64)) FROM `energy-platfrom.energy.bus_hifld`) AS h_min,
  (SELECT MAX(SAFE_CAST(bus_id AS INT64)) FROM `energy-platfrom.energy.bus_hifld`) AS h_max,
  (SELECT MIN(SAFE_CAST(bus_number AS INT64)) FROM `energy-platfrom.energy.pjm_queuescope_results` WHERE owner_label='AEP') AS q_min,
  (SELECT MAX(SAFE_CAST(bus_number AS INT64)) FROM `energy-platfrom.energy.pjm_queuescope_results` WHERE owner_label='AEP') AS q_max,
  (SELECT COUNTIF(NOT STARTS_WITH(name,'UNKNOWN')) FROM `energy-platfrom.energy.bus_hifld`) AS h_named
"""
r = list(c.query(q).result())[0]
print(dict(r))
