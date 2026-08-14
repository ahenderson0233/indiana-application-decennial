import sys
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get
d = get("https://data-southbend.opendata.arcgis.com/api/feed/dcat-us/1.1.json")
ds = d.get("dataset", [])
print("total datasets:", len(ds))
for x in ds:
    t = x.get("title", "")
    dist = [y.get("accessURL") or y.get("downloadURL") for y in x.get("distribution", [])]
    rest = next((y for y in dist if y and "rest/services" in y), "")
    print(f"  {t} | {rest}")
