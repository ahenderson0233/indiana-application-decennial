import json, sys, time, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"
_last = [0.0]
def get(url):
    dt = time.time() - _last[0]
    if dt < 1.1: time.sleep(1.1 - dt)
    _last[0] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

# 1. the webapp config -> webmap id -> operational layers
app = get("https://www.arcgis.com/sharing/rest/content/items/4f6d46d67a2f4023ba7aae0953baf66a/data?f=json")
wmid = (app.get("map") or {}).get("itemId") or app.get("webmap")
print("webapp values.webmap:", (app.get("values") or {}).get("webmap"), "| map.itemId:", wmid)
wmid = wmid or (app.get("values") or {}).get("webmap")
if wmid:
    wm = get(f"https://www.arcgis.com/sharing/rest/content/items/{wmid}/data?f=json")
    print(f"webmap {wmid} operational layers:")
    for lyr in wm.get("operationalLayers", []):
        print(f"   {lyr.get('title')!r} -> {lyr.get('url')}")

# 2. enumerate the known feature service
SVC = "https://services3.arcgis.com/oX5r75R7mapdoI2F/arcgis/rest/services/Duke_Energy_Distributed_Guidance_2023/FeatureServer"
root = get(f"{SVC}?f=json")
print(f"\nservice: {root.get('serviceDescription') or ''}".strip())
for l in root.get("layers", []) + root.get("tables", []):
    lid = l["id"]
    meta = get(f"{SVC}/{lid}?f=json")
    try:
        cnt = get(f"{SVC}/{lid}/query?where=1%3D1&returnCountOnly=true&f=json").get("count")
    except Exception as e:
        cnt = f"ERR {str(e)[:60]}"
    print(f"  layer {lid} {meta.get('name')!r}: geom={meta.get('geometryType')} count={cnt} maxRec={meta.get('maxRecordCount')}")
    print(f"    fields: {[f['name'] for f in meta.get('fields', [])]}")

# 3. what else does org oX5r75R7mapdoI2F serve?
try:
    sd = get("https://services3.arcgis.com/oX5r75R7mapdoI2F/arcgis/rest/services?f=json")
    print(f"\norg oX5r75R7mapdoI2F services ({len(sd.get('services', []))}):")
    for s in sd.get("services", []):
        print("   ", s["name"], s["type"])
except Exception as e:
    print("org services dir:", e)
