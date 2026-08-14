"""Follow-up: correct schemas for registry_sources, dc_bans, googlenews count, table list."""
import json
from bq_util import query, save_scratch

OUT = {}

def try_q(label, sql, show=40):
    try:
        rows, gb = query(sql)
        OUT[label] = {"gb": round(gb, 4), "n": len(rows), "rows": rows}
        print(f"\n=== {label} ({len(rows)} rows, {gb:.4f} GB) ===")
        for r in rows[:show]:
            print(json.dumps({k: str(v)[:300] for k, v in r.items()}, ensure_ascii=False)[:900])
    except Exception as e:
        OUT[label] = {"error": str(e)[:400]}
        print(f"\n=== {label} FAILED: {str(e)[:250]}")

try_q("registry_sources_cols", """
SELECT column_name, data_type FROM `energy-platfrom.energy.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name='registry_sources' ORDER BY ordinal_position
""")

try_q("dc_bans_cols", """
SELECT column_name, data_type FROM `energy-platfrom.energy.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name='dc_bans' ORDER BY ordinal_position
""")

try_q("energy_tables", """
SELECT table_id, row_count FROM `energy-platfrom.energy.__TABLES__`
WHERE REGEXP_CONTAINS(LOWER(table_id), r'amlegal|news|ban|opposition|moratorium|iurc|docket|ordinance|indiana|registry')
ORDER BY table_id
""")

try_q("googlenews_in_count", """
SELECT COUNT(*) n, COUNT(DISTINCT link) n_links, MIN(pub_date) min_pub, MAX(pub_date) max_pub
FROM `energy-platfrom.energy.googlenews_dc_state` WHERE state='Indiana'
""")

try_q("amlegal_in_count", """
SELECT COUNT(*) n, COUNT(DISTINCT client_slug) n_juris FROM `energy-platfrom.energy.amlegal_dc_ordinances` WHERE LOWER(region)='in'
""")

save_scratch("00b_schema_fix.json", json.dumps(OUT, default=str, indent=1))
