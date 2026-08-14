import sys
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
import requests
from lane_c_util import UA

CANDS = [
    # Fort Wayne / Allen County
    "https://maps.cityoffortwayne.org/arcgis/rest/services",
    "https://gis.acimap.us/arcgis/rest/services",
    "https://www.acimap.us/arcgis/rest/services",
    "https://gis.allencounty.us/arcgis/rest/services",
    "https://data-cityoffortwayne.opendata.arcgis.com/api/feed/dcat-us/1.1.json",
    # South Bend / St. Joseph
    "https://data.southbendin.gov/api/catalog/v1",
    "https://gis.southbendin.gov/arcgis/rest/services",
    "https://sjcgis.sjcindiana.com/arcgis/rest/services",
    "https://gis.macog.com/arcgis/rest/services",
    "https://data-southbend.opendata.arcgis.com/api/feed/dcat-us/1.1.json",
    # Evansville / Vanderburgh
    "https://gis.evansville.in.gov/arcgis/rest/services",
    "https://www.evansvillegis.com/arcgis/rest/services",
    "https://gisdata.evansville.in.gov/arcgis/rest/services",
]
for u in CANDS:
    try:
        r = requests.get(u, params={"f": "json"} if "rest/services" in u else None,
                         headers={"User-Agent": UA}, timeout=25, allow_redirects=True)
        ct = r.headers.get("Content-Type", "")
        head = r.text[:180].replace("\n", " ")
        print(f"{r.status_code} {u}\n    ct={ct} head={head}")
    except Exception as e:
        print(f"ERR {u} -> {type(e).__name__}: {str(e)[:120]}")
