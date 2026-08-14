"""Authoritative I&M (Indiana Michigan Power / AEP) county list for IN from EIA-861 territory table."""
import json
from bq_util import query, save_scratch

try:
    rows, gb = query("""
        SELECT DISTINCT county FROM `energy-platfrom.energy.eia861_service_territory`
        WHERE state='IN' AND REGEXP_CONTAINS(LOWER(utility_name), r'indiana michigan')
        ORDER BY county
    """)
    counties = [r["county"] for r in rows]
    print(f"I&M IN counties ({len(counties)}, {gb:.4f} GB): {counties}")
    save_scratch("im_counties.json", json.dumps({"counties": counties, "gb": gb}, indent=1))
except Exception as e:
    msg = str(e)[:400]
    print("utility_name/county query failed:", msg)
    # fall back: inspect columns
    cols, gb2 = query("""
        SELECT column_name, data_type FROM `energy-platfrom.energy.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name='eia861_service_territory' ORDER BY ordinal_position
    """)
    print("columns:", [c["column_name"] for c in cols])
    save_scratch("im_counties_error.json", json.dumps({"error": msg, "columns": cols}, default=str))
