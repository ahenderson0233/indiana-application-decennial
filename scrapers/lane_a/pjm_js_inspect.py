import re, sys, time, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")

for path in ("/Scripts/MVC/Custom/PJM.Website.Feature.Planning.js",
             "/Scripts/MVC/Custom/PJM.Website.Foundation.PjmGrid.js"):
    js = get("https://www.pjm.com" + path)
    time.sleep(1.2)
    print(f"=== {path} ({len(js):,}b)")
    urls = set()
    for m in re.finditer(r'["\']((?:https?:)?/[^"\']*(?:api|Api|ashx|json|export|Export|Service|Handler|\.aspx)[^"\']*)["\']', js):
        urls.add(m.group(1))
    for u in sorted(urls):
        print("   ", u[:160])
    for m in re.finditer(r'(?:url|Url|URL)\s*[:=]\s*["\']([^"\']+)["\']', js):
        u = m.group(1)
        if len(u) > 3 and not u.startswith("#"):
            print("  url-assign:", u[:160])
