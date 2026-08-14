import sys, re
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get

html = get("https://www.in.gov/dwd/warn-notices/current-warn-notices/", as_json=False)
links = sorted(set(re.findall(r'href="([^"]+)"', html)))
arch = [l for l in links if re.search(r"warn|archiv|notice", l, re.I) and not l.startswith("mailto")]
for l in arch: print(l)
