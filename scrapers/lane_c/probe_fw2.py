import sys, re
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get

RX = re.compile(r'https?://[^"\'()<>\s]+?(?:rest/services|FeatureServer|MapServer)[^"\'()<>\s]*')
html = get("https://www.acimap.us/", as_json=False)
print("page len:", len(html))
urls = set(RX.findall(html))
print("embedded service urls:", urls or "none")
js = re.findall(r'(?:src|href)="([^"]+\.(?:js|json)[^"]*)"', html)
print("js/json refs:", js[:12])
seen = set()
for j in js[:10]:
    u = j if j.startswith("http") else "https://www.acimap.us/" + j.lstrip("/")
    if u in seen: continue
    seen.add(u)
    try:
        t = get(u, as_json=False)
        found = set(RX.findall(t))
        for m in found:
            print("  ", j.split("?")[0].split("/")[-1], "->", m)
    except Exception as e:
        print("  err", u.split("/")[-1][:40], str(e)[:60])
# also look for config endpoints typical of geocortex/webappbuilder
for probe in ["https://www.acimap.us/config.json", "https://www.acimap.us/appconfig.json",
              "https://www.acimap.us/arcgis/rest/info?f=json",
              "https://www.acimap.us/arcgis/rest/services/?f=pjson"]:
    try:
        t = get(probe, as_json=False)
        print(probe, "->", t[:150].replace("\n", " "))
    except Exception as e:
        print(probe, "ERR", str(e)[:80])
