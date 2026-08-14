import sys, re, json
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get

KEY = re.compile(r"demol|unsafe|condemn|vacan|abandon|tax.?sale|surplus|blight|nuisance|"
                 r"enforce|violat|foreclos|delinq|permit|code", re.I)

base = "https://gis.southbendin.gov/arcgis/rest/services"
root = get(base, params={"f": "json"})
print("folders:", root.get("folders"))
hits = []
for folder in [""] + root.get("folders", []):
    url = f"{base}/{folder}" if folder else base
    try:
        fj = get(url, params={"f": "json"})
    except Exception as e:
        print("  ERR folder", folder, e); continue
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
                hits.append((f"{surl}/{lyr['id']}", name, lname))
print("\nSOUTH BEND HITS:")
for u, s, l in hits:
    print(f"  {u} | {s} | {l}")

# DCAT catalog
print("\nDCAT data-southbend:")
try:
    d = get("https://data-southbend.opendata.arcgis.com/api/feed/dcat-us/1.1.json")
    for ds in d.get("dataset", []):
        t = ds.get("title", "")
        if KEY.search(t):
            dist = [x.get("accessURL") or x.get("downloadURL") for x in ds.get("distribution", [])]
            rest = [x for x in dist if x and "rest/services" in x]
            print(f"  {t} | {rest[0] if rest else (dist[0] if dist else '')}")
except Exception as e:
    print("  DCAT err:", e)
