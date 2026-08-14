import re, sys, time, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")

html = get("https://www.pjm.com/planning/m/project-construction")
print(f"page bytes: {len(html):,}")
pats = set()
for m in re.finditer(r'["\'](/[^"\']*(?:api|Api|service|Service|export|Export|\.ashx|\.json|\.xlsx?)[^"\']*)["\']', html):
    pats.add(m.group(1))
for m in re.finditer(r'["\'](https?://[^"\']*(?:api|service|export|pjm)[^"\']*\.(?:json|xlsx?|ashx|xml))["\']', html):
    pats.add(m.group(1))
for m in re.finditer(r'(https?://[a-z0-9.-]*pjm\.com[^"\'<> ]*)', html):
    u = m.group(1)
    if any(k in u.lower() for k in ("api", "service", "export", "project")):
        pats.add(u)
for p in sorted(pats):
    print("  ", p[:160])
# script srcs
print("\nscripts:")
for m in re.finditer(r'<script[^>]+src="([^"]+)"', html):
    print("  ", m.group(1)[:150])
