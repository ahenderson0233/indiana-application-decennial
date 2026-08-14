import sys
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
import requests, json
from lane_c_util import UA

def j(u, **kw):
    r = requests.get(u, headers={"User-Agent": UA}, timeout=30, **kw)
    return r.status_code, r

# 1. acimap with explicit f=pjson
for u in ["https://www.acimap.us/arcgis/rest/services?f=pjson",
          "https://www.acimap.us/arcgis/rest/services?f=json",
          "https://maps.cityoffortwayne.org/server/rest/services?f=json",
          "https://maps.cityoffortwayne.org/gis/rest/services?f=json",
          "https://www.evansvillegis.com/server/rest/services?f=json",
          "https://www.evansvillegis.com/arcgis/sharing/rest/search?q=demolition&f=json&num=10",
          "https://www.evansvillegis.com/portal/sharing/rest/search?q=demolition&f=json&num=10"]:
    try:
        s, r = j(u)
        head = r.text[:250].replace("\n", " ")
        print(f"{s} {u}\n    {head}\n")
    except Exception as e:
        print(f"ERR {u} -> {str(e)[:100]}\n")
