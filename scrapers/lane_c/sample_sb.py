import sys
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get, arcgis_count

CANDS = [
    ("SB Demolition Orders", "https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services/Active_Demolition_Orders/FeatureServer/0"),
    ("SB All Vacant+Abandoned", "https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services/AllVacantandAbandonedProperties/FeatureServer/3"),
    ("SB Chronic Problem Properties", "https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services/Chronic_Problem_Properties_List/FeatureServer/0"),
    ("SB Continuous Enforcement", "https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services/Continuous_Enforcement/FeatureServer/4"),
    ("SB Code Enforcement 2018-2020", "https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services/Code_Enforcement_Cases/FeatureServer/0"),
    ("SB VacantAbandoned Map svc", "https://gis.southbendin.gov/arcgis/rest/services/OpenData/VacantAbandoned/MapServer"),
]
for label, url in CANDS:
    print("=" * 95)
    print(label, "->", url)
    try:
        meta = get(url, params={"f": "json"})
    except Exception as e:
        print("  META ERR:", e); continue
    if url.endswith("MapServer"):
        for coll in ("layers", "tables"):
            for l in meta.get(coll) or []:
                print(f"  {coll[:-1]} {l['id']}: {l.get('name')}")
        continue
    flds = [f["name"] for f in meta.get("fields") or []]
    print("  fields:", flds)
    try:
        n = arcgis_count(url)
        print("  COUNT:", n)
        jq = get(url.rstrip("/") + "/query",
                 params={"where": "1=1", "outFields": "*", "returnGeometry": "false",
                         "resultRecordCount": 3, "f": "json"})
        for f in jq.get("features", [])[:3]:
            a = {k: v for k, v in f["attributes"].items() if v not in (None, "", " ")}
            print("  ROW:", str(a)[:500])
    except Exception as e:
        print("  Q ERR:", e)
