"""Sanity checks on loaded tables."""
import json
from bq_util import query

for label, sql in [
    ("iurc by relevance", """SELECT relevance, COUNT(*) n FROM `energy-platfrom.indiana_app.in_iurc_dockets`
                             GROUP BY 1 ORDER BY n DESC LIMIT 15"""),
    ("iurc dc_party rows", """SELECT docket_number, petition_type, status, filed_date, SUBSTR(parties,0,150) p
                              FROM `energy-platfrom.indiana_app.in_iurc_dockets`
                              WHERE relevance LIKE '%dc_party%' ORDER BY filed_date DESC LIMIT 25"""),
    ("iurc llc/econdev recent", """SELECT docket_number, petition_type, status, filed_date, SUBSTR(parties,0,120) p
                              FROM `energy-platfrom.indiana_app.in_iurc_dockets`
                              WHERE petition_type IN ('LLC Project','Economic Development','TDSIC') AND filed_date>='2024-01-01'
                              ORDER BY filed_date DESC LIMIT 20"""),
    ("grid projects by county", """SELECT county, COUNT(*) n FROM `energy-platfrom.indiana_app.in_grid_plans`
                              WHERE row_type='project' AND county IS NOT NULL GROUP BY 1 ORDER BY n DESC LIMIT 15"""),
    ("grid location_status", """SELECT row_type, location_status, COUNT(*) n FROM `energy-platfrom.indiana_app.in_grid_plans`
                              GROUP BY 1,2 ORDER BY 1,3 DESC"""),
    ("ordinances", "SELECT jurisdiction, county, section_title, observed_date FROM `energy-platfrom.indiana_app.in_ordinances_dc`"),
    ("registry", "SELECT table_name, n_rows, SUBSTR(notes,0,90) note FROM `energy-platfrom.indiana_app._registry` ORDER BY built_at"),
]:
    try:
        rows, gb = query(sql)
        print(f"\n=== {label} ({len(rows)}) ===")
        for r in rows:
            print("  ", json.dumps({k: str(v)[:150] for k, v in r.items()}, ensure_ascii=False)[:400])
    except Exception as e:
        print(f"\n=== {label} FAILED: {str(e)[:200]}")
