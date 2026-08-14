import sys, re
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get, robots_allowed
import requests
from lane_c_util import UA

# 1. acimap SPA: find service URLs in page/config
print("robots acimap:", robots_allowed("https://www.acimap.us/"))
try:
    html = get("https://www.acimap.us/", as_json=False, check_robots=True)
    urls = set(re.findall(r'https?://[^"\'\s\]+(?:rest/services|FeatureServer|MapServer)[^"\'\s\]*', html))
    print("acimap embedded service urls:", urls or "none")
    js = re.findall(r'src="([^"]+\.js[^"]*)"', html)
    print("js files:", js[:8])
    for j in js[:4]:
        u = j if j.startswith("http") else "https://www.acimap.us/" + j.lstrip("/")
        try:
            t = get(u, as_json=False)
            for m in set(re.findall(r'https?://[^"\'\s\]+(?:rest/services)[^"\'\s\]*', t)):
                print("  in", j.split("?")[0][-40:], "->", m)
        except Exception as e:
            print("  js err", e)
except Exception as e:
    print("acimap ERR:", e)

# 2. candidate hosts
for u in ["https://gisweb.cityoffortwayne.org/arcgis/rest/services?f=json",
          "https://arcgis.acimap.us/arcgis/rest/services?f=json",
          "https://services.acimap.us/arcgis/rest/services?f=json",
          "https://data.fortwayne.gov",
          "https://gis.fwcs.k12.in.us/arcgis/rest/services?f=json"]:
    try:
        r = requests.get(u, headers={"User-Agent": UA}, timeout=20)
        print(r.status_code, u, "|", r.text[:100].replace("\n", " "))
    except Exception as e:
        print("ERR", u, "|", str(e)[:90])
