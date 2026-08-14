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

queries = [
    '(title:"hosting capacity" OR title:"DG Guidance" OR title:GHC) AND (duke OR DEI OR DEC OR DEP)',
    'duke "hosting capacity"',
    'duke energy indiana hosting',
    '"grid hosting capacity"',
]
seen = set()
for q in queries:
    js = get("https://www.arcgis.com/sharing/rest/search?f=json&num=40&q=" + urllib.parse.quote(q))
    for it in js.get("results", []):
        key = it["id"]
        if key in seen: continue
        seen.add(key)
        print(f"[{it.get('type')}] {it.get('title')!r} owner={it.get('owner')} access={it.get('access')} id={it['id']}")
        if it.get("url"): print("      url:", it["url"])
print(f"\n{len(seen)} distinct items")
