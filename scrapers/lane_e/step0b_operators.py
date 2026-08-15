"""Lane E step 0b: verify gas_eia_state_capacity contents (held EIA capacity) and
enumerate pipeline operators crossing Indiana from held geometry. All read-only."""
import os, json
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", r"C:\Users\ahend\bq-key.json")
from google.cloud import bigquery
client = bigquery.Client(project="energy-platfrom")

def run(label, sql, limit_print=200):
    print(f"\n=== {label} ===")
    job = client.query(sql)
    rows = list(job.result())
    print(f"gb_scanned={0 if job.total_bytes_processed is None else job.total_bytes_processed/1e9:.4f} n={len(rows)}")
    for r in rows[:limit_print]:
        print(json.dumps(dict(r), default=str, ensure_ascii=False))
    return rows

# schema of the held EIA capacity table
run("gas_eia_state_capacity columns", """
SELECT column_name, data_type FROM `energy-platfrom.energy.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'gas_eia_state_capacity' ORDER BY ordinal_position
""")

# columns of the IN pipeline clip
run("in_gas_pipelines columns", """
SELECT column_name, data_type FROM `energy-platfrom.indiana_app.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'in_gas_pipelines' ORDER BY ordinal_position
""")

# columns of the EIA living-atlas pipeline table (has TYPEPIPE per registry)
run("gas_pipelines columns", """
SELECT column_name, data_type FROM `energy-platfrom.energy.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'gas_pipelines' ORDER BY ordinal_position
""")
