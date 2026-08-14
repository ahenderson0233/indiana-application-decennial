"""Full I&M (EIA 9324) Indiana county list, deduped; latest report year."""
import json, re
from bq_util import query, save_scratch

rows, gb = query("""
SELECT county, MAX(report_date) latest
FROM `energy-platfrom.energy.eia861_service_territory`
WHERE state='IN' AND utility_id_eia=9324
GROUP BY county ORDER BY county
""")
def norm(c):
    c = re.sub(r"\s+county$", "", c.strip(), flags=re.I).strip()
    c = {"Dekalb": "DeKalb", "Laporte": "LaPorte", "Lagrange": "LaGrange", "De Kalb": "DeKalb",
         "St Joseph": "St. Joseph", "St. Joseph": "St. Joseph"}.get(c.title(), c.title())
    return c
seen = {}
for r in rows:
    n = norm(r["county"])
    seen[n] = max(str(r["latest"]), seen.get(n, ""))
counties = sorted(seen)
print(f"I&M IN counties (deduped): {len(counties)} ({gb:.4f} GB)")
print(counties)
save_scratch("im_counties_final.json", json.dumps({"utility_id_eia": 9324, "n": len(counties),
              "counties": counties, "latest_by_county": seen, "gb": gb}, indent=1))
