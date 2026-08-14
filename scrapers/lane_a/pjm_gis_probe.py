import json, re, sys, time, urllib.error, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"
_last = [0.0]
def get(url, binary=False):
    dt = time.time() - _last[0]
    if dt < 1.1: time.sleep(1.1 - dt)
    _last[0] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            b = r.read(4_000_000)
            return r.status, (b if binary else b.decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, (e.read(500).decode("utf-8", "replace") if not binary else b"")
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

candidates = [
    "https://gis.pjm.com/arcgis/rest/services?f=json",
    "https://gis.pjm.com/server/rest/services?f=json",
    "https://gis.pjm.com/rest/services?f=json",
    "https://gis.pjm.com/esm/default.html",
]
for u in candidates:
    s, body = get(u)
    print(f"[{s}] {u}")
    if s == 200 and isinstance(body, str):
        if "services" in body[:2000] or "folders" in body[:2000]:
            try:
                js = json.loads(body)
                print("   folders:", js.get("folders"))
                print("   services:", [(x.get("name"), x.get("type")) for x in js.get("services", [])][:30])
            except Exception:
                pass
        elif ".html" in u:
            # scrape the ESM page for service/config URLs
            urls = set(re.findall(r'["\'](https?://[^"\']+|/[^"\']*(?:rest/services|config|\.json)[^"\']*)["\']', body))
            for x in sorted(urls)[:40]:
                if any(k in x.lower() for k in ("rest", "config", "json", "gis", "esri", "arcgis", "map")):
                    print("   ref:", x[:140])
