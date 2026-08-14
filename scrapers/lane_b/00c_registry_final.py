"""Corrected registry-first queries."""
import json
from bq_util import query, save_scratch

OUT = {}

def try_q(label, sql, show=60):
    try:
        rows, gb = query(sql)
        OUT[label] = {"gb": round(gb, 4), "n": len(rows), "rows": rows}
        print(f"\n=== {label} ({len(rows)} rows, {gb:.4f} GB) ===")
        for r in rows[:show]:
            print(json.dumps({k: str(v)[:260] for k, v in r.items()}, ensure_ascii=False)[:1100])
    except Exception as e:
        OUT[label] = {"error": str(e)[:400]}
        print(f"\n=== {label} FAILED: {str(e)[:250]}")

try_q("registry_sources_relevant", """
SELECT source_name, status, endpoint, endpoint_kind, acquisition_method, access, notes
FROM `energy-platfrom.energy.registry_sources`
WHERE REGEXP_CONTAINS(LOWER(source_name||' '||IFNULL(domain,'')||' '||IFNULL(endpoint,'')),
      r'iurc|indiana|amlegal|municode|legistar|granicus|civicplus')
""")

try_q("dc_bans_indiana", """
SELECT * FROM `energy-platfrom.energy.dc_bans` WHERE UPPER(state) IN ('IN','INDIANA')
""")

try_q("dc_docket_tracker_sample", """
SELECT * FROM `energy-platfrom.energy.dc_docket_tracker` LIMIT 40
""")

try_q("dc_regulatory_news_in", """
SELECT * FROM `energy-platfrom.energy.dc_regulatory_news`
WHERE REGEXP_CONTAINS(LOWER(TO_JSON_STRING(t)), r'indiana|iurc') LIMIT 20
""".replace("FROM `energy-platfrom.energy.dc_regulatory_news`", "FROM `energy-platfrom.energy.dc_regulatory_news` t"))

save_scratch("00c_registry_final.json", json.dumps(OUT, default=str, indent=1))
