import json, sys, time, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"
_last = [0.0]
def get(url):
    dt = time.time() - _last[0]
    if dt < 1.1: time.sleep(1.1 - dt)
    _last[0] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

import math
def merc2ll(x, y):
    lon = x / 20037508.342789244 * 180.0
    lat = math.degrees(2 * math.atan(math.exp(math.radians(y / 20037508.342789244 * 180.0))) - math.pi / 2)
    return lon, lat

BASE = "https://services3.arcgis.com/oX5r75R7mapdoI2F/arcgis/rest/services"
for svc in ("Generation_Hosting_Capacity_November_2025", "Generation_Map_Publishing",
            "Ohio_Generation_Map", "Ohio_Load_Map", "Total_Available_Ohio", "DukeTransmission"):
    try:
        root = get(f"{BASE}/{svc}/FeatureServer?f=json")
    except Exception as e:
        print(f"\n=== {svc}: ERR {str(e)[:80]}")
        continue
    print(f"\n=== {svc}: desc={str(root.get('serviceDescription'))[:80]!r}")
    for l in root.get("layers", []) + root.get("tables", []):
        lid = l["id"]
        meta = get(f"{BASE}/{svc}/FeatureServer/{lid}?f=json")
        try:
            cnt = get(f"{BASE}/{svc}/FeatureServer/{lid}/query?where=1%3D1&returnCountOnly=true&f=json").get("count")
        except Exception as e:
            cnt = f"ERR {str(e)[:40]}"
        ext = meta.get("extent") or {}
        sr = (ext.get("spatialReference") or {}).get("latestWkid") or (ext.get("spatialReference") or {}).get("wkid")
        bbox = ""
        try:
            if sr in (3857, 102100):
                w, s = merc2ll(ext["xmin"], ext["ymin"]); e_, n = merc2ll(ext["xmax"], ext["ymax"])
                bbox = f" bbox=({w:.1f},{s:.1f})..({e_:.1f},{n:.1f})"
            elif sr == 4326:
                bbox = f" bbox=({ext['xmin']:.1f},{ext['ymin']:.1f})..({ext['xmax']:.1f},{ext['ymax']:.1f})"
        except Exception:
            pass
        print(f"  layer {lid} {meta.get('name')!r}: geom={meta.get('geometryType')} count={cnt}{bbox}")
        print(f"    fields: {[f['name'] for f in meta.get('fields', [])][:32]}")
