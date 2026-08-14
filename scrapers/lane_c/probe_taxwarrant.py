import sys, re
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
import requests
from lane_c_util import UA, get, robots_allowed

checks = [
    ("mycase.in.gov robots", "https://mycase.in.gov/robots.txt"),
    ("public.courts.in.gov robots", "https://public.courts.in.gov/robots.txt"),
    ("courts bulk-data page", "https://www.in.gov/courts/admin/data/"),
    ("DOR tax warrant info", "https://www.in.gov/dor/business-tax/tax-warrants/"),
]
for label, u in checks:
    try:
        r = requests.get(u, headers={"User-Agent": UA}, timeout=30)
        body = r.text[:400].replace("\n", " ") if "robots" in u else ""
        print(f"{label}: {r.status_code} {u}")
        if body: print("   ", body)
        if "robots" not in u and r.status_code == 200:
            txt = re.sub(r"<[^>]+>", " ", r.text)
            txt = re.sub(r"\s+", " ", txt)
            for kw in ["bulk", "warrant", "agreement", "fee", "subscription"]:
                i = txt.lower().find(kw)
                if i >= 0:
                    print(f"    [{kw}] ...{txt[max(0,i-120):i+220]}...")
                    break
    except Exception as e:
        print(f"{label}: ERR {str(e)[:100]}")
