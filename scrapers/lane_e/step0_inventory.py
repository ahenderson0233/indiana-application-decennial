"""Lane E step 0: verify held-vs-new for gas pipeline CAPACITY data.

Read-only queries against energy-platfrom.energy (NEVER written to).
"""
import os
import json

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", r"C:\Users\ahend\bq-key.json")
from google.cloud import bigquery

client = bigquery.Client(project="energy-platfrom")

def run(label, sql):
    print(f"\n=== {label} ===")
    job = client.query(sql)
    rows = list(job.result())
    print(f"gb_scanned={job.total_bytes_processed / 1e9:.4f}")
    for r in rows:
        print(json.dumps(dict(r), default=str, ensure_ascii=False))
    return rows

# (a) registry_sources: any gas/pipeline/ebb/lng/ferc sources already tracked?
run("registry_sources gas/pipeline", """
SELECT source_name, status, endpoint, access, notes, what_it_provides
FROM `energy-platfrom.energy.registry_sources`
WHERE REGEXP_CONTAINS(LOWER(source_name), r'gas|pipeline|ebb|lng|ferc 7')
""")

# (b) held gas tables in warehouse
run("held gas tables (energy)", """
SELECT table_id, row_count
FROM `energy-platfrom.energy.__TABLES__`
WHERE REGEXP_CONTAINS(table_id, r'gas|ng_|pipeline')
ORDER BY table_id
""")

# (c) also check indiana_app for anything already landed by a prior lane run
run("held gas tables (indiana_app)", """
SELECT table_id, row_count
FROM `energy-platfrom.indiana_app.__TABLES__`
WHERE REGEXP_CONTAINS(table_id, r'gas|ng_|pipeline|capacity')
ORDER BY table_id
""")

# (d) registry of indiana_app (what has been registered so far)
run("indiana_app._registry", """
SELECT table_name, source, method, n_rows, built_at
FROM `energy-platfrom.indiana_app._registry`
ORDER BY built_at
""")
