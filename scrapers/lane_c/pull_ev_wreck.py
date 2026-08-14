"""Retry: Evansville wrecking permits via POST objectIds chunks (URL-length-safe)."""
import sys
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get, arcgis_count, load_to_bq

url = "https://maps.evansvillegis.com/arcgis_server/rest/services/BC/BUILDING_COMMISSION_PERMITS/MapServer/0"
where = "UPPER(USER_Project_Activity) LIKE '%WRECK%'"
pub = arcgis_count(url, where=where)
ids_resp = get(url + "/query", method="POST",
               data={"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=180)
ids = ids_resp.get("objectIds") or []
print(f"ids: {len(ids)} (publisher count {pub})", flush=True)
rows = []
CH = 100
for i in range(0, len(ids), CH):
    chunk = ids[i:i + CH]
    j = get(url + "/query", method="POST",
            data={"objectIds": ",".join(map(str, chunk)), "outFields": "*",
                  "returnGeometry": "false", "f": "json"}, timeout=180)
    if "error" in j:
        raise RuntimeError(f"chunk {i}: {j['error']}")
    for f in j.get("features", []):
        a = dict(f.get("attributes", {}))
        for k in list(a):
            if k.upper().startswith("SHAPE"):
                a.pop(k, None)
        rows.append(a)
    if (i // CH) % 10 == 0:
        print(f"  {len(rows)}/{len(ids)}", flush=True)
assert len(rows) == len(ids), f"PAGINATION ALARM: {len(rows)} vs {len(ids)}"
acts = {}
for r in rows:
    acts[r.get("USER_Project_Activity")] = acts.get(r.get("USER_Project_Activity"), 0) + 1
print("activity breakdown:", acts, flush=True)
load_to_bq(
    "in_si_evansville_demolition_permits", rows,
    source=url,
    method=f"arcgis_rest POST objectIds-chunked WHERE {where} (lane_c)",
    notes=("D21_demolition (Vanderburgh building-commission WRECKING permits). Subject values "
           "'BUILDING WRECKING COMMERCIAL'/'BUILDING WRECKING RESIDENTIAL' - corpus has NO "
           "'DEMOLITION' label (all 31 USER_Project_Activity values enumerated; DEMO=0, "
           "WRECK=4190, RAZ=0). OBSERVED EVENT DATE: USER_Application_Recv_d (epoch ms) = "
           "application received; USER_Actual_Start_Date/End_Date when present. USER_Parcel_ID "
           f"+ address keys. publisher_count={pub}. Parent corpus 153,909 permits/31 types; "
           "only the wrecking subject pulled as seller-intent. activity_breakdown=" + str(acts)),
)
