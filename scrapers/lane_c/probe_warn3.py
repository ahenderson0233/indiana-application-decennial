import sys, re
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get, robots_allowed
import requests
from lane_c_util import UA

for url in ["https://dwdportal.dwd.in.gov/WARN/warn_landing/",
            "https://www.in.gov/dwd/warn-notices/current-warn-notices/"]:
    print("=" * 80)
    print(url, "robots:", robots_allowed(url))
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=60, allow_redirects=True)
        print("  status:", r.status_code, "| final:", r.url, "| len:", len(r.text))
        html = r.text
        tables = len(re.findall(r"<table", html, re.I))
        print("  tables:", tables)
        api = re.findall(r'(?:src|href)="([^"]*(?:api|json|csv|xlsx)[^"]*)"', html, re.I)
        print("  api-ish refs:", api[:10])
        scripts = re.findall(r'<script[^>]+src="([^"]+)"', html)
        print("  scripts:", [s for s in scripts if "static" in s or "app" in s or "main" in s][:10])
        if tables:
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I)
            print("  first rows:")
            for tr in rows[:6]:
                cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)
                cells = [re.sub(r"<[^>]+>|\s+", " ", c).strip() for c in cells]
                print("   ", cells)
    except Exception as e:
        print("  ERR:", e)
