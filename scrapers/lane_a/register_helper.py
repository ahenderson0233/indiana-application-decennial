"""Parameterized _registry insert (BQ escapes handled by parameters, not string literals)."""
import os, sys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery

def register(table_name, source, method, n_rows, gb_scanned, notes):
    c = bigquery.Client(project="energy-platfrom")
    job = c.query(
        """INSERT INTO `energy-platfrom.indiana_app._registry`
           (table_name, source, method, n_rows, gb_scanned, built_at, notes)
           VALUES (@t, @s, @m, @n, @g, CURRENT_TIMESTAMP(), @o)""",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", table_name),
            bigquery.ScalarQueryParameter("s", "STRING", source),
            bigquery.ScalarQueryParameter("m", "STRING", method),
            bigquery.ScalarQueryParameter("n", "INT64", n_rows),
            bigquery.ScalarQueryParameter("g", "FLOAT64", gb_scanned),
            bigquery.ScalarQueryParameter("o", "STRING", notes),
        ]))
    job.result()
    print(f"registered {table_name} ({n_rows:,} rows)")

if __name__ == "__main__":
    register(
        "in_pjm_rtep_upgrades",
        "PJM Project Status & Cost Allocation (RTEP upgrades) - public grid export at "
        "https://www.pjm.com/planning/m/project-construction, endpoint "
        "https://www.pjm.com/m/ProjectConst/ProjectConstructionUpgrades",
        "replicated the page's own export: POST jsonModel (GridName=CostAllocation, no filters) "
        "-> XLSX blob (2.58 MB, sheets Data + Definitions-Mapping); parsed verbatim, all 31 "
        "columns kept; no login, no terms dialogue encountered",
        15443, 0.0,
        "Full PJM RTEP upgrade list, all states; 932 rows name Indiana in the state column "
        "(state can be multi-valued). Observed event dates are the in-service/status/TEAC date "
        "columns in the data; _pulled_at=2026-08-14 stored separately. PLOTTABILITY: no "
        "coordinates served - JOINABLE-IDENTITY (upgrade id b/n/s-numbers, named substation "
        "endpoints in Location/Description, kV in Voltage, Transmission Owner, State). Named "
        "endpoints let Indiana buses join to the held substation layer; never geocoded here.")
