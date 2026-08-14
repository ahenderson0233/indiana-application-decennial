"""Target 2: enumerate hub.mph.in.gov CKAN catalog, flag seller-intent subjects."""
import re
import sys
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get

KEY = re.compile(r"dissol|tax.?warrant|warn\b|layoff|unemploy|unsafe|demol|"
                 r"vacan|abandon|foreclos|delinq|lien|bankrupt|"
                 r"closure|blight|condemn|code.?enforce|violat|surplus|auction|"
                 r"tax.?sale|sheriff|business|corporat|entity", re.I)

base = "https://hub.mph.in.gov/api/3/action/package_search"
start, total = 0, None
hits = []
all_names = []
while True:
    j = get(base, params={"rows": 100, "start": start})
    res = j["result"]
    if total is None:
        total = res["count"]
        print("CKAN dataset count:", total)
    for pkg in res["results"]:
        name = pkg.get("title") or pkg.get("name")
        notes = (pkg.get("notes") or "")[:300]
        all_names.append(pkg.get("name"))
        blob = f"{name} {notes} {pkg.get('name')}"
        if KEY.search(blob):
            resources = [(r.get("format"), r.get("id"), (r.get("name") or "")[:60],
                          r.get("datastore_active"), (r.get("url") or "")[:120])
                         for r in pkg.get("resources", [])]
            hits.append((pkg.get("name"), name, notes, resources))
    start += 100
    if start >= total:
        break

print(f"\nlisted {len(all_names)} datasets; {len(hits)} keyword hits\n")
for slug, title, notes, resources in hits:
    print("=" * 90)
    print(f"{slug} | {title}")
    print(f"  notes: {notes[:200]}")
    for fmt, rid, rname, ds, url in resources:
        print(f"  res [{fmt}] datastore={ds} {rid} {rname} {url}")
