"""indiana_app.in_rto_expansion — RTO-level expansion projects naming Indiana facilities.

Union of (a) held MISO MTEP tables (energy.txexp_miso_mtep_*, registry-first: NOT re-scraped) and
(b) the fresh PJM RTEP upgrade list (indiana_app.in_pjm_rtep_upgrades, pulled this run), filtered
to rows whose state list names Indiana with a token match (never a substring 'IN' match, which
would catch nothing bad here but is the kind of silent defect this project records).

COST UNITS DIFFER BY PUBLISHER and are never fused: MISO current_cost is dollars as published;
PJM 'Cost Estimate'/'TEAC Cost' are millions of dollars per the export's own Definitions sheet.
Both are carried as strings with an explicit cost_unit column.

PLOTTABILITY: neither publisher serves coordinates in these lists -> every row is
JOINABLE_IDENTITY (named substation endpoints, kV, owner, state). Nothing geocoded, nothing
guessed. State-jurisdictional plans (IURC TDSIC/IRP) are another lane's scope and are absent
here by design.
"""
import os
import sys

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from register_helper import register  # noqa: E402

c = bigquery.Client(project="energy-platfrom")
DEST = "energy-platfrom.indiana_app.in_rto_expansion"
IN_TOKEN = r"(^|[^A-Z])IN([^A-Z]|$)"

sql = f"""
CREATE OR REPLACE TABLE `{DEST}` AS
WITH miso_a_inservice AS (
  SELECT 'MISO' AS rto, 'energy.txexp_miso_mtep_appendix_a_in_service' AS source_table,
         CAST(mtep_project_id AS STRING) AS project_id, CAST(NULL AS STRING) AS facility_id,
         project_name, project_description AS description,
         COALESCE(NULLIF(other_type, ''), project_type) AS project_type,
         SAFE_CAST(max_kv AS FLOAT64) AS kv_max, SAFE_CAST(min_kv AS FLOAT64) AS kv_min,
         CAST(NULL AS STRING) AS from_endpoint, CAST(NULL AS STRING) AS to_endpoint,
         state_s AS states_named, submitting_to AS owner,
         planning_status AS status,
         CAST(expected_isd AS STRING) AS in_service_date,
         CAST(board_approved_date AS STRING) AS approval_date,
         CAST(current_cost AS STRING) AS cost_raw, 'USD (as published)' AS cost_unit,
         target_mtep_cycle AS cycle, prov_source_url AS _source_url,
         CAST(prov_pulled_at AS STRING) AS _pulled_at
  FROM `energy-platfrom.energy.txexp_miso_mtep_appendix_a_in_service`
  WHERE REGEXP_CONTAINS(UPPER(IFNULL(state_s, '')), r'{IN_TOKEN}')
),
miso_a_status AS (
  SELECT 'MISO' AS rto, 'energy.txexp_miso_mtep_appendix_a_status' AS source_table,
         CAST(mtep_project_id AS STRING) AS project_id, CAST(facility_id AS STRING) AS facility_id,
         COALESCE(NULLIF(name, ''), project) AS project_name,
         facility_description AS description,
         COALESCE(NULLIF(facility_type, ''), project_type) AS project_type,
         SAFE_CAST(max_kv AS FLOAT64) AS kv_max, SAFE_CAST(min_kv AS FLOAT64) AS kv_min,
         from_sub AS from_endpoint, to_sub AS to_endpoint,
         CONCAT(IFNULL(state_1, ''), IF(state_2 IS NULL OR state_2 = '', '', CONCAT(',', state_2)))
           AS states_named,
         COALESCE(NULLIF(facility_owner_s, ''), submitting_to) AS owner,
         planning_status AS status,
         CAST(expected_isd AS STRING) AS in_service_date,
         CAST(NULL AS STRING) AS approval_date,
         CAST(current_cost AS STRING) AS cost_raw, 'USD (as published)' AS cost_unit,
         target_mtep_cycle AS cycle, prov_source_url AS _source_url,
         CAST(prov_pulled_at AS STRING) AS _pulled_at
  FROM `energy-platfrom.energy.txexp_miso_mtep_appendix_a_status`
  WHERE REGEXP_CONTAINS(UPPER(IFNULL(state_1, '')), r'{IN_TOKEN}')
     OR REGEXP_CONTAINS(UPPER(IFNULL(state_2, '')), r'{IN_TOKEN}')
),
miso_eval AS (
  SELECT 'MISO' AS rto, 'energy.txexp_miso_mtep_under_evaluation' AS source_table,
         CAST(mtep_project_id AS STRING) AS project_id, CAST(NULL AS STRING) AS facility_id,
         project_name, project_description AS description,
         COALESCE(NULLIF(other_type, ''), project_type) AS project_type,
         SAFE_CAST(max_kv AS FLOAT64) AS kv_max, SAFE_CAST(min_kv AS FLOAT64) AS kv_min,
         CAST(NULL AS STRING) AS from_endpoint, CAST(NULL AS STRING) AS to_endpoint,
         state_s AS states_named, submitting_to AS owner,
         planning_status AS status,
         CAST(expected_isd AS STRING) AS in_service_date,
         CAST(NULL AS STRING) AS approval_date,
         CAST(current_cost AS STRING) AS cost_raw, 'USD (as published)' AS cost_unit,
         target_mtep_cycle AS cycle, prov_source_url AS _source_url,
         CAST(prov_pulled_at AS STRING) AS _pulled_at
  FROM `energy-platfrom.energy.txexp_miso_mtep_under_evaluation`
  WHERE REGEXP_CONTAINS(UPPER(IFNULL(state_s, '')), r'{IN_TOKEN}')
),
pjm AS (
  SELECT 'PJM' AS rto, 'indiana_app.in_pjm_rtep_upgrades' AS source_table,
         upgrade_id AS project_id, CAST(NULL AS STRING) AS facility_id,
         location AS project_name, description,
         project_type,
         SAFE_CAST(voltage AS FLOAT64) AS kv_max, CAST(NULL AS FLOAT64) AS kv_min,
         location AS from_endpoint, CAST(NULL AS STRING) AS to_endpoint,
         state AS states_named, transmission_owner AS owner,
         status,
         COALESCE(actual_in_service_date, revised_in_service_date,
                  projected_in_service_date, isa_in_service_date) AS in_service_date,
         pjm_board_approval_date AS approval_date,
         cost_estimate AS cost_raw,
         'millions USD (per PJM export Definitions sheet)' AS cost_unit,
         region AS cycle, _source_url,
         _pulled_at
  FROM `energy-platfrom.indiana_app.in_pjm_rtep_upgrades`
  WHERE REGEXP_CONTAINS(UPPER(IFNULL(state, '')), r'{IN_TOKEN}')
)
SELECT *,
       'JOINABLE_IDENTITY' AS plottability,
       'no coordinates served by either publisher; join via named endpoints/kV/owner to held substation layer; never geocoded' AS plottability_note,
       CURRENT_TIMESTAMP() AS _built_at
FROM (
  SELECT * FROM miso_a_inservice UNION ALL
  SELECT * FROM miso_a_status    UNION ALL
  SELECT * FROM miso_eval        UNION ALL
  SELECT * FROM pjm
)
"""
job = c.query(sql)
job.result()
gb = (job.total_bytes_processed or 0) / 1e9
n = list(c.query(f"SELECT COUNT(*) n FROM `{DEST}`").result())[0].n
brk = {f"{r.rto}/{r.source_table.split('.')[-1]}": r.n for r in c.query(
    f"SELECT rto, source_table, COUNT(*) n FROM `{DEST}` GROUP BY 1,2 ORDER BY 1,2").result()}
print(f"built {DEST}: {n:,} rows")
for k, v in brk.items():
    print(f"   {k}: {v:,}")

register(
    "in_rto_expansion",
    "MISO MTEP (held energy.txexp_miso_mtep_appendix_a_in_service/_status/_under_evaluation, "
    "cdn.misoenergy.org public XLSX, pulled 2026-08-07) + PJM RTEP Project Status & Cost "
    "Allocation (indiana_app.in_pjm_rtep_upgrades, public export pulled 2026-08-14)",
    "derived UNION, Indiana token-match on the publishers' own state columns; MISO side "
    "registry-first from held tables (not re-scraped); cost units kept per publisher and never "
    "fused (MISO: USD; PJM: millions USD)",
    int(n), gb,
    f"RTO-level expansion/upgrade projects naming Indiana: {brk}. Columns: project_id, "
    "facility_id, name, description, type, kv_max/min, from/to_endpoint (named subs where "
    "published), states_named, owner, status, in_service_date, approval_date, cost_raw+cost_unit, "
    "cycle. PLOTTABILITY: JOINABLE_IDENTITY on every row (no coords served; named endpoints + kV "
    "+ owner are the join keys; nothing geocoded). State-jurisdictional plans (IURC TDSIC/IRP) "
    "deliberately absent - other lane's scope.")
