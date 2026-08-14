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

SVC = "https://services.arcgis.com/ZnwBsu4Q8SvSAofV/arcgis/rest/services/PROD_MI_HC_GRID/FeatureServer"
stats = urllib.parse.quote(json.dumps([{"statisticType": "count", "onStatisticField": "OBJECTID_1",
                                        "outStatisticFieldName": "n"}]))
for lid in (0, 1):
    js = get(f"{SVC}/{lid}/query?where=1%3D1&groupByFieldsForStatistics=STATE_ABBR,OPCO"
             f"&outStatistics={stats}&f=json")
    print(f"layer {lid} STATE_ABBR x OPCO:")
    for f in js.get("features", []):
        a = f["attributes"]
        print(f"   {a.get('STATE_ABBR')!r:8} {a.get('OPCO')!r:12} {a.get('n'):,}")

# also check the AEP org for any OTHER HC services (IN might be a separate service)
org = get("https://www.arcgis.com/sharing/rest/search?q=owner%3A%22AEPGIS%22%20OR%20orgid%3AZnwBsu4Q8SvSAofV%20hosting%20capacity&num=50&f=json")
# orgid search via services directory instead:
try:
    sd = get("https://services.arcgis.com/ZnwBsu4Q8SvSAofV/arcgis/rest/services?f=json")
    names = [s["name"] for s in sd.get("services", [])]
    print(f"\norg ZnwBsu4Q8SvSAofV services ({len(names)}):")
    for n in names:
        print("  ", n)
except Exception as e:
    print("services dir:", e)
