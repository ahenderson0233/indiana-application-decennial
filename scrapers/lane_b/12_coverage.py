"""County-receipt rollup across the lane_b tables in indiana_app."""
import json, re
from bq_util import query, save_scratch

ALL92 = ["Adams","Allen","Bartholomew","Benton","Blackford","Boone","Brown","Carroll","Cass","Clark",
"Clay","Clinton","Crawford","Daviess","Dearborn","Decatur","DeKalb","Delaware","Dubois","Elkhart",
"Fayette","Floyd","Fountain","Franklin","Fulton","Gibson","Grant","Greene","Hamilton","Hancock",
"Harrison","Hendricks","Henry","Howard","Huntington","Jackson","Jasper","Jay","Jefferson","Jennings",
"Johnson","Knox","Kosciusko","LaGrange","Lake","LaPorte","Lawrence","Madison","Marion","Marshall",
"Martin","Miami","Monroe","Montgomery","Morgan","Newton","Noble","Ohio","Orange","Owen","Parke",
"Perry","Pike","Porter","Posey","Pulaski","Putnam","Randolph","Ripley","Rush","St. Joseph","Scott",
"Shelby","Spencer","Starke","Steuben","Sullivan","Switzerland","Tippecanoe","Tipton","Union",
"Vanderburgh","Vermillion","Vigo","Wabash","Warren","Warrick","Washington","Wayne","Wells","White","Whitley"]

def norm(c):
    if not c:
        return None
    c = re.sub(r"\s*county\s*$", "", c.strip(), flags=re.I).strip()
    fix = {"dekalb": "DeKalb", "laporte": "LaPorte", "lagrange": "LaGrange", "st joseph": "St. Joseph",
           "st. joseph": "St. Joseph", "saint joseph": "St. Joseph"}
    return fix.get(c.lower(), c.title().replace("Mc ", "Mc"))

hits = {}  # county -> set(table)
def mark(county_field, table):
    for part in re.split(r"[|;]", county_field or ""):
        n = norm(part)
        if n in ALL92:
            hits.setdefault(n, set()).add(table)
        elif n and n + " " in " ".join(ALL92):  # safety no-op
            pass

Q = [
    ("in_news_dc", "SELECT query_county AS c, COUNT(*) n FROM `energy-platfrom.indiana_app.in_news_dc` GROUP BY 1"),
    ("in_ordinances_dc", "SELECT county AS c, COUNT(*) n FROM `energy-platfrom.indiana_app.in_ordinances_dc` GROUP BY 1"),
    ("in_dc_actions", "SELECT county AS c, COUNT(*) n FROM `energy-platfrom.indiana_app.in_dc_actions` GROUP BY 1"),
    ("in_grid_plans", "SELECT county AS c, COUNT(*) n FROM `energy-platfrom.indiana_app.in_grid_plans` WHERE county IS NOT NULL GROUP BY 1"),
]
tot_gb = 0.0
for t, sql in Q:
    try:
        rows, gb = query(sql)
        tot_gb += gb
        for r in rows:
            mark(r["c"], t)
    except Exception as e:
        print(t, "skip:", str(e)[:150])

cov = {c: sorted(hits.get(c, [])) for c in ALL92}
have = [c for c in ALL92 if hits.get(c)]
miss = [c for c in ALL92 if not hits.get(c)]
print(f"counties with >=1 receipt: {len(have)}/92 (scan {tot_gb:.4f} GB)")
print("WITH:", have)
print("WITHOUT:", miss)
save_scratch("county_coverage.json", json.dumps({"with": have, "without": miss, "detail": cov}, indent=1))
