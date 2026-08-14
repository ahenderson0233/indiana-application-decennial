import json, sys, time, urllib.request, urllib.parse
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

for svc in ("Indiana_Michigan_EV_Map_WFL1", "Indiana_Michigan_EV_Eligibility"):
    for kind in ("FeatureServer",):
        url = f"https://services.arcgis.com/ZnwBsu4Q8SvSAofV/arcgis/rest/services/{svc}/{kind}"
        try:
            root = get(f"{url}?f=json")
        except Exception as e:
            print(f"{svc}/{kind}: {e}")
            continue
        print(f"\n=== {svc}/{kind}: layers={[(l['id'], l['name']) for l in root.get('layers', [])]} tables={[(t['id'], t['name']) for t in root.get('tables', [])]}")
        for l in root.get("layers", []) + root.get("tables", []):
            lid = l["id"]
            meta = get(f"{url}/{lid}?f=json")
            try:
                cnt = get(f"{url}/{lid}/query?where=1%3D1&returnCountOnly=true&f=json").get("count")
            except Exception as e:
                cnt = f"ERR {e}"
            print(f" layer {lid} {meta.get('name')!r}: geom={meta.get('geometryType')} count={cnt}")
            print(f"   fields={[f['name'] for f in meta.get('fields', [])][:25]}")
