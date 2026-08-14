import sys
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get, arcgis_count

url = "https://maps.evansvillegis.com/arcgis_server/rest/services/BC/BUILDING_COMMISSION_PERMITS/MapServer/0"
j = get(url + "/query", params={
    "where": "1=1", "outFields": "USER_Project_Activity",
    "returnDistinctValues": "true", "returnGeometry": "false", "f": "json",
    "resultRecordCount": 500})
vals = sorted({(f["attributes"].get("USER_Project_Activity") or "").strip()
               for f in j.get("features", [])})
print("distinct USER_Project_Activity (%d):" % len(vals))
for v in vals:
    print("  ", repr(v))
for pat in ["DEMO", "WRECK", "RAZ"]:
    n = arcgis_count(url, where=f"UPPER(USER_Project_Activity) LIKE '%{pat}%'")
    print(f"count LIKE %{pat}%:", n)
