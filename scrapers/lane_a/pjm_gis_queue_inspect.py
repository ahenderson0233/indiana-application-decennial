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
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read(8_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(400).decode("utf-8", "replace")

B = "https://gis.pjm.com/arcgis/rest/services"
# exact wall on a secured service
s, body = get(f"{B}/CTC/Footprint/MapServer?f=json")
print(f"CTC/Footprint meta [{s}]: {body[:240]}")
s, body = get(f"{B}/RTDMS/RTDMS/MapServer?f=json")
print(f"RTDMS meta [{s}]: {body[:240]}")

# queue layer metadata + count + fields
s, body = get(f"{B}/Renewables/Queue/MapServer/0?f=json")
meta = json.loads(body)
print(f"\nQueue/0 [{s}]: name={meta.get('name')!r} geom={meta.get('geometryType')} "
      f"maxRecordCount={meta.get('maxRecordCount')} supportsPagination="
      f"{(meta.get('advancedQueryCapabilities') or {}).get('supportsPagination')}")
print("fields:", [f["name"] for f in meta.get("fields", [])])
s, body = get(f"{B}/Renewables/Queue/MapServer/0/query?where=1%3D1&returnCountOnly=true&f=json")
print("count:", body[:200])
s, body = get(f"{B}/Renewables/Queue/MapServer/0/query?where=1%3D1&outFields=*&outSR=4326&resultRecordCount=2&f=json")
js = json.loads(body)
for f_ in js.get("features", [])[:2]:
    print("sample:", {k: str(v)[:40] for k, v in f_.get("attributes", {}).items()}, f_.get("geometry"))
# City layer too (Interregional/LMP/0)
s, body = get(f"{B}/Interregional/LMP/MapServer/0?f=json")
meta = json.loads(body)
print(f"\nLMP/City [{s}]: geom={meta.get('geometryType')} fields={[f['name'] for f in meta.get('fields', [])]}")
s, body = get(f"{B}/Interregional/LMP/MapServer/0/query?where=1%3D1&returnCountOnly=true&f=json")
print("count:", body[:200])
