import sys
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get
import requests
from lane_c_util import UA

# 1. discovery API without search_context
for domain in ["hub.mph.in.gov", "data.in.gov", "www.in.gov"]:
    try:
        j = get("https://api.us.socrata.com/api/catalog/v1",
                params={"domains": domain, "limit": 3})
        print(domain, "-> socrata resultSetSize:", j.get("resultSetSize"))
        for r in j.get("results", [])[:3]:
            print("   ", r.get("resource", {}).get("name"))
    except Exception as e:
        print(domain, "-> discovery err:", e)

# 2. what do the hosts serve?
for url in ["https://hub.mph.in.gov", "https://data.in.gov", "https://hub.mph.in.gov/api/3/action/package_list", "https://data.in.gov/api/3/action/package_list"]:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30, allow_redirects=True)
        ct = r.headers.get("Content-Type", "")
        print(url, "->", r.status_code, ct, "| final:", r.url, "| body head:", r.text[:150].replace("\n", " "))
    except Exception as e:
        print(url, "-> ERR:", e)
