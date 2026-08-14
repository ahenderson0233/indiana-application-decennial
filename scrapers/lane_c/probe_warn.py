import sys, re
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get, robots_allowed

for url in ["https://www.in.gov/dwd/warn-notices/",
            "https://www.in.gov/dwd/employer-services/warn-notices/",
            "https://www.in.gov/dwd/warn/"]:
    try:
        print(url, "robots:", robots_allowed(url))
        html = get(url, as_json=False, check_robots=True)
        print("  OK", len(html), "bytes")
        # find tables/links to xlsx/csv/pdf
        links = re.findall(r'href="([^"]+\.(?:xlsx?|csv|pdf))"', html, re.I)
        print("  file links:", links[:20])
        # look for embedded tables
        m = re.findall(r"<table", html, re.I)
        print("  <table> count:", len(m))
        if "warn" in html.lower():
            # show title
            t = re.search(r"<title>(.*?)</title>", html, re.S)
            print("  title:", t.group(1).strip() if t else "?")
        break
    except Exception as e:
        print("  ERR:", e)
