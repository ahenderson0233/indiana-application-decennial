"""Target 1 discovery: data.indy.gov (ArcGIS Hub) + gis.indy.gov (ArcGIS Server).
Enumerate all services/layers; flag anything matching seller-intent subjects."""
import json
import re
import sys

sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get, robots_allowed

KEY = re.compile(r"demol|unsafe|condemn|vacan|abandon|tax.?sale|surplus|blight|"
                 r"board.?up|nuisance|enforce|violat|foreclos|permit|landbank|land.?bank|"
                 r"brownfield|delinq", re.I)

print("robots data.indy.gov:", robots_allowed("https://data.indy.gov/search"))
print("robots gis.indy.gov:", robots_allowed("https://gis.indy.gov/server/rest/services"))

# --- 1. ArcGIS Server directory walk ---
base = "https://gis.indy.gov/server/rest/services"
root = get(base, params={"f": "json"})
folders = [""] + root.get("folders", [])
hits = []
for folder in folders:
    url = f"{base}/{folder}" if folder else base
    try:
        j = get(url, params={"f": "json"})
    except Exception as e:
        print(f"  folder {folder}: ERROR {e}")
        continue
    for svc in j.get("services", []):
        name, stype = svc["name"], svc["type"]
        if stype not in ("MapServer", "FeatureServer"):
            continue
        surl = f"{base}/{name}/{stype}"
        try:
            sj = get(surl, params={"f": "json"})
        except Exception as e:
            print(f"  svc {name}: ERROR {e}")
            continue
        for lyr in (sj.get("layers") or []) + (sj.get("tables") or []):
            lname = lyr.get("name", "")
            if KEY.search(lname) or KEY.search(name):
                hits.append((f"{surl}/{lyr['id']}", name, lname))

print("\n=== gis.indy.gov keyword hits ===")
for u, s, l in hits:
    print(f"  {u} | svc={s} | layer={l}")

# --- 2. Hub search API ---
print("\n=== data.indy.gov hub search ===")
for kw in ["demolition", "unsafe building", "vacant", "condemned", "tax sale",
           "abandoned", "blight", "surplus property", "nuisance", "board up"]:
    try:
        j = get("https://opendata.arcgis.com/api/v3/search",
                params={"q": kw, "catalog[domain]": "data.indy.gov", "page[size]": 30})
        items = j.get("data", [])
    except Exception:
        items = []
    if not items:
        # fallback: hub site search API
        try:
            j = get("https://data.indy.gov/api/search/v1/collections/all/items",
                    params={"q": kw, "limit": 30})
            items = j.get("features", [])
        except Exception as e:
            print(f"  [{kw}] search error: {e}")
            items = []
    for it in items:
        if "attributes" in it:
            a = it["attributes"]
            print(f"  [{kw}] {a.get('name')} | id={a.get('id')} | type={a.get('type')} | url={a.get('url')}")
        else:
            p = it.get("properties", {})
            print(f"  [{kw}] {p.get('title')} | id={it.get('id')} | src={json.dumps(p.get('source',''))[:80]}")
