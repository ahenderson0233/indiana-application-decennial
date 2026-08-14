import json, os, sys, time, urllib.request, urllib.parse
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
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

SVC = "https://services.arcgis.com/ZnwBsu4Q8SvSAofV/arcgis/rest/services/PROD_MI_HC_GRID/FeatureServer"
root = get(f"{SVC}?f=json")
print("service layers:", [(l["id"], l["name"]) for l in root.get("layers", [])])
for lid in [l["id"] for l in root.get("layers", [])]:
    meta = get(f"{SVC}/{lid}?f=json")
    cnt = get(f"{SVC}/{lid}/query?where=1%3D1&returnCountOnly=true&f=json")
    print(f" layer {lid} {meta.get('name')!r}: type={meta.get('geometryType')} maxRecordCount={meta.get('maxRecordCount')}")
    print(f"   count={cnt.get('count')}")
    print(f"   fields={[f['name'] for f in meta.get('fields', [])]}")
    ed = (meta.get("editingInfo") or {}).get("lastEditDate")
    if ed: print(f"   lastEditDate={time.strftime('%Y-%m-%d', time.gmtime(ed/1000))}")

from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")
print("\nheld candidates in energy dataset:")
for t in c.list_tables("energy-platfrom.energy"):
    tid = t.table_id.lower()
    if any(k in tid for k in ("aep", "_im_", "im_hc", "mi_hc", "indiana_michigan", "hc_grid")):
        tt = c.get_table(f"energy-platfrom.energy.{t.table_id}")
        print(f"  {t.table_id}: {tt.num_rows:,} rows")
