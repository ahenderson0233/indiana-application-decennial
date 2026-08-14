import os, sys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")

cands = [t.table_id for t in c.list_tables("energy-platfrom.energy")
         if "eia861" in t.table_id or "utility" in t.table_id.lower()]
print("candidate name tables:", cands)

name_tbl = None
for tid in cands:
    cols = [f.name for f in c.get_table(f"energy-platfrom.energy.{tid}").schema]
    if any("util" in x.lower() and "name" in x.lower() for x in cols) and \
       any("util" in x.lower() and "id" in x.lower() for x in cols):
        name_tbl = (tid,
                    next(x for x in cols if "util" in x.lower() and "id" in x.lower()),
                    next(x for x in cols if "util" in x.lower() and "name" in x.lower()))
        print(f"-> using {name_tbl}")
        break

if name_tbl:
    tid, idc, nmc = name_tbl
    q = f"""
    SELECT DISTINCT st.county AS county, st.utility_id_eia, u.{nmc} AS utility_name
    FROM `energy-platfrom.energy.eia861_service_territory` st
    JOIN (SELECT DISTINCT {idc} AS uid, {nmc} FROM `energy-platfrom.energy.{tid}`) u
      ON u.uid = st.utility_id_eia
    WHERE st.state = 'IN' AND REGEXP_CONTAINS(LOWER(u.{nmc}), r'indiana michigan')
    ORDER BY county
    """
else:
    # Fallback: EIA's published utility id for Indiana Michigan Power Co is 9324
    q = """
    SELECT DISTINCT county, utility_id_eia, 'Indiana Michigan Power Co (EIA 9324, fallback)' AS utility_name
    FROM `energy-platfrom.energy.eia861_service_territory`
    WHERE state = 'IN' AND utility_id_eia = 9324
    ORDER BY county
    """
rows = list(c.query(q).result())
print(f"\nI&M Indiana counties ({len(rows)}), utility_name={rows[0].utility_name if rows else '?'} (id {rows[0].utility_id_eia if rows else '?'}):")
print(", ".join(r.county for r in rows))
