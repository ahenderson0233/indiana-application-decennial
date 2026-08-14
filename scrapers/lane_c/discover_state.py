"""Target 2 discovery: Indiana MPH / state open data via Socrata discovery API.
Enumerate full catalog for hub.mph.in.gov and data.in.gov, flag seller-intent subjects."""
import re
import sys
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get

KEY = re.compile(r"dissol|tax.?warrant|warrant|warn|layoff|unemploy|unsafe|demol|"
                 r"vacan|abandon|foreclos|delinq|lien|bankrupt|business.?clos|"
                 r"closure|blight|condemn|code.?enforce|violat|surplus|auction|"
                 r"tax.?sale|sheriff", re.I)

for domain in ["hub.mph.in.gov", "data.in.gov"]:
    print("=" * 90)
    print("DOMAIN:", domain)
    offset, total_listed, hits = 0, 0, []
    while True:
        try:
            j = get("https://api.us.socrata.com/api/catalog/v1",
                    params={"domains": domain, "limit": 100, "offset": offset,
                            "search_context": domain})
        except Exception as e:
            print("  DISCOVERY ERROR:", e)
            break
        results = j.get("results", [])
        if offset == 0:
            print("  resultSetSize:", j.get("resultSetSize"))
        for r in results:
            res = r.get("resource", {})
            name = res.get("name") or ""
            desc = (res.get("description") or "")[:200]
            rid = res.get("id")
            rtype = res.get("type")
            total_listed += 1
            if KEY.search(name) or KEY.search(desc):
                hits.append((rid, rtype, name, desc))
        if len(results) < 100:
            break
        offset += 100
    print(f"  total catalog items listed: {total_listed}")
    for rid, rtype, name, desc in hits:
        print(f"  HIT {rid} [{rtype}] {name}")
        print(f"      {desc[:160]}")
