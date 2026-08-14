import sys
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get

# AGOL public item search for Fort Wayne / Allen County / Evansville feature services
QUERIES = [
    '("Fort Wayne" OR "Allen County") AND (demolition OR vacant OR "unsafe building" OR "code enforcement" OR "tax sale" OR blight) AND type:"Feature Service"',
    '("Evansville" OR "Vanderburgh") AND (demolition OR vacant OR "unsafe building" OR "code enforcement" OR "tax sale" OR blight) AND type:"Feature Service"',
    'owner:CityofFortWayne',
    'orgid:* AND title:"Fort Wayne" AND type:"Feature Service"',
]
for q in QUERIES:
    print("=" * 90)
    print("Q:", q)
    try:
        j = get("https://www.arcgis.com/sharing/rest/search",
                params={"q": q, "f": "json", "num": 25})
        print("  total:", j.get("total"))
        for it in j.get("results", []):
            print(f"  {it.get('title')} | owner={it.get('owner')} | {it.get('url')}")
    except Exception as e:
        print("  ERR:", e)
