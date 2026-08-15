"""T5: gas OAC per-location table for Indiana (PEPL + Trunkline publish State+County).
Value-read columns first; export data/gas_locations.json.gz for market.html."""
import json, gzip, os
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

out = []
for pipe, tbl in [("Panhandle Eastern", "in_gas_capacity_panhandle_eastern"),
                  ("Trunkline", "in_gas_capacity_trunkline")]:
    cols = [s.name for s in client.get_table(f"{DS}.{tbl}").schema]
    print(f"{tbl} cols:", cols[:20])
    pick = {}
    for want, pats in [("loc", ["loc name", "location name", "loc_name", "point name", "locname"]),
                       ("county", ["county"]), ("state", ["state"]),
                       ("design", ["design capacity", "dc", "design"]),
                       ("oac", ["operationally available", "oac", "available"]),
                       ("tsq", ["total scheduled", "tsq", "scheduled"]),
                       ("gasday", ["gas day", "gasday", "eff gas day", "effective"])]:
        for c in cols:
            if any(p in c.lower() for p in pats):
                pick[want] = c; break
    print("  picked:", pick)
    need = [v for v in pick.values()]
    q = (f"SELECT {', '.join(f'`{c}`' for c in need)} FROM `{DS}.{tbl}` "
         f"WHERE UPPER(TRIM(CAST(`{pick['state']}` AS STRING)))='IN'") if "state" in pick else None
    if not q: continue
    for r in client.query(q):
        d = dict(r)
        out.append({"pipeline": pipe,
                    "location": str(d.get(pick.get("loc"), "")),
                    "county": str(d.get(pick.get("county"), "")),
                    "design": str(d.get(pick.get("design"), "")),
                    "oac": str(d.get(pick.get("oac"), "")),
                    "tsq": str(d.get(pick.get("tsq"), "")),
                    "gas_day": str(d.get(pick.get("gasday"), ""))})
with gzip.open(os.path.join(REPO, "data", "gas_locations.json.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(out, f, separators=(",", ":"))
print(f"gas_locations.json.gz: {len(out)} Indiana location rows")
