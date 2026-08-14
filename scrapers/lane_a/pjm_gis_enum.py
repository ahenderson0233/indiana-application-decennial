import json, sys, time, urllib.error, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"
_last = [0.0]
def get(url):
    dt = time.time() - _last[0]
    if dt < 1.1: time.sleep(1.1 - dt)
    _last[0] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, json.loads(r.read(6_000_000).decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return None, {"err": str(e)}

BASE = "https://gis.pjm.com/arcgis/rest/services"
for folder in ("CTC", "ESM", "Interregional", "Renewables", "RTDMS", "Utilities"):
    s, js = get(f"{BASE}/{folder}?f=json")
    svcs = js.get("services", [])
    print(f"\n=== /{folder} [{s}]: {len(svcs)} services")
    for sv in svcs:
        name, typ = sv["name"], sv["type"]
        s2, meta = get(f"{BASE}/{name}/{typ}?f=json")
        layers = meta.get("layers", []) or []
        tables = meta.get("tables", []) or []
        secured = "error" in meta or s2 in (401, 403, 499)
        cap = meta.get("capabilities", "")
        print(f"  {name} ({typ}) [{s2}] cap={cap!r} layers={len(layers)} tables={len(tables)}"
              + (" SECURED" if secured else ""))
        for L in layers[:25]:
            print(f"     {L.get('id'):>3} {L.get('name')}")
