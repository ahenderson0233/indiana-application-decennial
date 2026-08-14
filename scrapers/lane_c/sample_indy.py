"""Value-sample candidate Indy layers: read fields + 20 rows before believing any name."""
import sys
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get, arcgis_count, epoch_ms_to_date

CANDIDATES = [
    ("OpenData_NonSpatial (full service listing)", "https://gis.indy.gov/server/rest/services/OpenData/OpenData_NonSpatial/MapServer", None),
    ("TaxSale PARCELSTAXSALE", "https://gis.indy.gov/server/rest/services/TaxSaleViewer/TaxSaleParcels_BuildingBlocks/MapServer/0", 5),
    ("SurplusParcels", "https://gis.indy.gov/server/rest/services/SurplusProperties/SurplusPropertiesFeatures2/MapServer/7", 5),
    ("Abandoned+Vacant Houses (OpenData_Infrastructure/2)", "https://gis.indy.gov/server/rest/services/OpenData/OpenData_Infrastructure/MapServer/2", 5),
    ("Abandoned and Vacant Properties (MapIndyProperty/16)", "https://gis.indy.gov/server/rest/services/MapIndy/MapIndyProperty/MapServer/16", 5),
    ("MapIndyProperty/11 Abandoned and Vacant", "https://gis.indy.gov/server/rest/services/MapIndy/MapIndyProperty/MapServer/11", 3),
]

for label, url, nsamp in CANDIDATES:
    print("=" * 100)
    print(label, "->", url)
    try:
        meta = get(url, params={"f": "json"})
    except Exception as e:
        print("  META ERROR:", e)
        continue
    if nsamp is None:
        # service listing: show layers and tables
        for coll in ("layers", "tables"):
            for lyr in meta.get(coll) or []:
                print(f"  {coll[:-1]} {lyr['id']}: {lyr.get('name')}")
        continue
    fields = [f["name"] for f in meta.get("fields") or []]
    print("  type:", meta.get("type"), "| geom:", meta.get("geometryType"), "| fields:", fields)
    try:
        n = arcgis_count(url)
        print("  COUNT:", n)
    except Exception as e:
        print("  COUNT ERROR:", e)
        continue
    try:
        j = get(url.rstrip("/") + "/query",
                params={"where": "1=1", "outFields": "*", "returnGeometry": "false",
                        "resultRecordCount": nsamp, "f": "json"})
        for f in j.get("features", [])[:nsamp]:
            a = f["attributes"]
            compact = {k: v for k, v in list(a.items()) if v not in (None, "", " ")}
            print("  ROW:", str(compact)[:600])
    except Exception as e:
        print("  SAMPLE ERROR:", e)
