import sys
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get, arcgis_count

def sample(label, url, n=3):
    print("=" * 95)
    print(label, "->", url)
    try:
        meta = get(url, params={"f": "json"})
        flds = [f["name"] for f in meta.get("fields") or []]
        print("  fields:", flds[:40])
        cnt = arcgis_count(url)
        print("  COUNT:", cnt)
        jq = get(url.rstrip("/") + "/query",
                 params={"where": "1=1", "outFields": "*", "returnGeometry": "false",
                         "resultRecordCount": n, "f": "json"})
        if "error" in jq:
            print("  QUERY ERROR:", jq["error"]); return
        for f in jq.get("features", [])[:n]:
            a = {k: v for k, v in f["attributes"].items() if v not in (None, "", " ")}
            print("  ROW:", str(a)[:450])
    except Exception as e:
        print("  ERR:", e)

# Allen County AGOL layers (layer 0 of each FS)
sample("ALLEN tax delinquent", "https://services6.arcgis.com/tuxY7TQIaDhLWARO/arcgis/rest/services/Tax_delinquent_parcels/FeatureServer/0")
sample("ALLEN vacant parcels", "https://services6.arcgis.com/tuxY7TQIaDhLWARO/arcgis/rest/services/Vacant_parcels/FeatureServer/0")
sample("ALLEN landbank parcels", "https://services6.arcgis.com/tuxY7TQIaDhLWARO/arcgis/rest/services/Landbank_parcels/FeatureServer/0")
# Evansville
sample("EV foreclosures 2019 (svc FORECLOSURES/14)", "https://maps.evansvillegis.com/arcgis_server/rest/services/ASSESSOR/FORECLOSURES/MapServer/14")
sample("EV taxsale current Aug2026", "https://maps.evansvillegis.com/arcgis_server/rest/services/SITE_PROJECTS/TAX_SALE/MapServer/0")
sample("EV taxsale transfers 2011", "https://maps.evansvillegis.com/arcgis_server/rest/services/ASSESSOR/TAX_SALES/MapServer/0")
sample("EV building permits", "https://maps.evansvillegis.com/arcgis_server/rest/services/BC/BUILDING_COMMISSION_PERMITS/MapServer/0", n=5)
