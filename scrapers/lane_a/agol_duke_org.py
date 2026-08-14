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

BASE = "https://dukeenergy.maps.arcgis.com/sharing/rest/search?f=json&num=60&q="
for q in ["hosting", "guidance", "GHC", "capacity", "indiana"]:
    try:
        js = get(BASE + urllib.parse.quote(q))
    except Exception as e:
        print(f"q={q!r}: {e}")
        continue
    print(f"\n=== org search q={q!r}: total={js.get('total')}")
    for it in js.get("results", []):
        print(f"  [{it.get('type')}] {it.get('title')!r} access={it.get('access')} id={it['id']}"
              + (f" url={it.get('url')}" if it.get("url") else ""))

# the Code Attachment's parent item
try:
    it = get("https://www.arcgis.com/sharing/rest/content/items/4f6d46d67a2f4023ba7aae0953baf66a?f=json")
    print("\nparent item 4f6d...:", it.get("type"), it.get("title"), "access:", it.get("access"),
          "err:", it.get("error", {}).get("message"))
except Exception as e:
    print("\nparent item err:", e)
