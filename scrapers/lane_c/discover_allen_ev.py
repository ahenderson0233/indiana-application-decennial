import sys, re
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get

KEY = re.compile(r"demol|unsafe|condemn|vacan|abandon|tax.?sale|surplus|blight|nuisance|"
                 r"enforce|violat|foreclos|delinq|permit|code|sheriff|auction", re.I)

# 1. Everything in the allenco AGOL org
print("=== allenco AGOL items ===")
start = 1
while True:
    j = get("https://www.arcgis.com/sharing/rest/search",
            params={"q": 'owner:allenco', "f": "json", "num": 100, "start": start})
    for it in j.get("results", []):
        t = it.get("title", "")
        mark = " <<<" if KEY.search(t) else ""
        print(f"  [{it.get('type')}] {t} | {it.get('url')}{mark}")
    start = j.get("nextStart", -1)
    if start == -1:
        break

# 2. Evansville ArcGIS server directory
print("\n=== maps.evansvillegis.com server walk ===")
base = "https://maps.evansvillegis.com/arcgis_server/rest/services"
try:
    root = get(base, params={"f": "json"})
    print("folders:", root.get("folders"))
    for folder in [""] + root.get("folders", []):
        url = f"{base}/{folder}" if folder else base
        try:
            fj = get(url, params={"f": "json"})
        except Exception as e:
            print("  ERR", folder, e); continue
        for svc in fj.get("services", []):
            name, stype = svc["name"], svc["type"]
            if stype not in ("MapServer", "FeatureServer"):
                continue
            surl = f"{base}/{name}/{stype}"
            try:
                sj = get(surl, params={"f": "json"})
            except Exception:
                continue
            for lyr in (sj.get("layers") or []) + (sj.get("tables") or []):
                lname = lyr.get("name", "")
                if KEY.search(lname) or KEY.search(name):
                    print(f"  HIT {surl}/{lyr['id']} | {name} | {lname}")
except Exception as e:
    print("SERVER ERR:", e)
