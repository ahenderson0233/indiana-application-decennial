"""Registry-first: what do we already know/hold before probing anything."""
import json
from bq_util import query, client, PROJECT

OUT = {}

def try_q(label, sql):
    try:
        rows, gb = query(sql)
        OUT[label] = {"gb": round(gb, 4), "n": len(rows), "rows": rows}
        print(f"\n=== {label} ({len(rows)} rows, {gb:.4f} GB) ===")
        for r in rows[:25]:
            print(json.dumps({k: str(v)[:220] for k, v in r.items()}, ensure_ascii=False)[:1200])
    except Exception as e:
        OUT[label] = {"error": str(e)[:500]}
        print(f"\n=== {label} FAILED: {str(e)[:300]}")

try_q("registry_sources_relevant", """
SELECT source_name, status, endpoint, access_notes
FROM `energy-platfrom.energy.registry_sources`
WHERE REGEXP_CONTAINS(LOWER(source_name), r'iurc|indiana|amlegal|municode|legistar|granicus|civicplus')
""")

try_q("energy_tables", """
SELECT table_name, ROUND(size_bytes/1e6,1) mb, row_count
FROM `energy-platfrom.energy.__TABLES__`
WHERE REGEXP_CONTAINS(LOWER(table_name), r'amlegal|news|ban|opposition|moratorium|iurc|docket|ordinance|indiana')
ORDER BY table_name
""")

try_q("amlegal_in_sample", """
SELECT * FROM `energy-platfrom.energy.amlegal_dc_ordinances`
WHERE LOWER(region)='in' LIMIT 20
""")

try_q("amlegal_in_jurisdictions", """
SELECT jurisdiction, COUNT(*) n
FROM `energy-platfrom.energy.amlegal_dc_ordinances`
WHERE LOWER(region)='in'
GROUP BY 1 ORDER BY 1
""")

try_q("googlenews_dc_state_sample", """
SELECT * FROM `energy-platfrom.energy.googlenews_dc_state` WHERE state='Indiana' LIMIT 10
""")

try_q("googlenews_dc_state_count", """
SELECT COUNT(*) n, MIN(CAST(published AS STRING)) min_pub, MAX(CAST(published AS STRING)) max_pub
FROM `energy-platfrom.energy.googlenews_dc_state` WHERE state='Indiana'
""")

try_q("dc_bans_indiana", """
SELECT * FROM `energy-platfrom.energy.dc_bans`
WHERE REGEXP_CONTAINS(LOWER(CAST(jurisdiction AS STRING)), r'indiana|,\\s*in$') OR LOWER(CAST(state AS STRING)) IN ('indiana','in')
""")

try_q("dc_opposition_tracker_indiana", """
SELECT * FROM `energy-platfrom.energy.dc_opposition_tracker`
WHERE LOWER(CAST(state AS STRING)) IN ('indiana','in')
LIMIT 60
""")

# does indiana_app exist yet, and what's in it?
try:
    ds = client().get_dataset(f"{PROJECT}.indiana_app")
    tables = [t.table_id for t in client().list_tables(ds)]
    print(f"\n=== indiana_app EXISTS (location={ds.location}), tables: {tables}")
    OUT["indiana_app"] = {"exists": True, "location": ds.location, "tables": tables}
except Exception as e:
    print(f"\n=== indiana_app dataset: {str(e)[:200]}")
    OUT["indiana_app"] = {"exists": False, "error": str(e)[:200]}

try:
    loc = client().get_dataset(f"{PROJECT}.energy").location
    print(f"energy dataset location: {loc}")
    OUT["energy_location"] = loc
except Exception as e:
    print(f"energy dataset location check failed: {e}")

import bq_util
p = bq_util.save_scratch("00_registry_check.json", json.dumps(OUT, default=str, indent=1))
print("\nsaved ->", p)
