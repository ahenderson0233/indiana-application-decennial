"""Resolve AEP/I&M AGOL dashboard 268618e992264d14a552f70a43c7afa3 -> webmap -> feature layers.
Anonymous AGOL item/data REST reads only (public sharing API). >=1.1s/host, identifying UA."""
import json, sys, time, urllib.request
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

ITEM = "268618e992264d14a552f70a43c7afa3"
base = "https://www.arcgis.com/sharing/rest/content/items"
meta = get(f"{base}/{ITEM}?f=json")
print("item:", meta.get("type"), "|", meta.get("title"), "| access:", meta.get("access"),
      "| owner org item err:", meta.get("error"))
data = get(f"{base}/{ITEM}/data?f=json")
widgets = data.get("widgets") or []
maps = set()
def walk(o):
    if isinstance(o, dict):
        if o.get("type") == "mapWidget" and o.get("itemId"): maps.add(o["itemId"])
        if "itemId" in o and o.get("type") in ("mapWidget",): maps.add(o["itemId"])
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(data)
print("webmap itemIds found:", maps)
for mid in maps:
    wm = get(f"{base}/{mid}/data?f=json")
    for lyr in (wm.get("operationalLayers") or []):
        print(f"  layer: {lyr.get('title')!r}  url={lyr.get('url')}  itemId={lyr.get('itemId')}")
        for sub in (lyr.get('layers') or []):
            print(f"     sub: {sub.get('title')!r} url={sub.get('url')}")
