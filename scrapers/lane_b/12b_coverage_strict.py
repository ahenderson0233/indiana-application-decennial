"""Strict county receipts: county (or a city inside it) named IN THE TITLE, or a county-attributed
ordinance/action/grid-project row. Query-only attribution is reported separately as weak."""
import json, os, re
from bq_util import save_scratch

SCRATCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_scratch")
ALL92 = json.load(open(os.path.join(SCRATCH, "county_coverage.json"), encoding="utf-8"))["with"]  # 92 names

# city -> county (IN)
c2c = {}
for line in open(os.path.join(SCRATCH, "national_place_by_county2020.txt"), encoding="utf-8", errors="replace").read().splitlines()[1:]:
    f = line.split("|")
    if len(f) >= 8 and f[0] == "IN":
        base = re.sub(r"\s+(city|town|CDP)$", "", f[6], flags=re.I).strip()
        c2c.setdefault(base.lower(), set()).add(f[3].replace(" County", ""))

strong = {}
def mark(county, src):
    county = county.replace(" County", "").strip()
    for c in ALL92:
        if c.lower() == county.lower():
            strong.setdefault(c, set()).add(src)

news = json.load(open(os.path.join(SCRATCH, "news_rows.json"), encoding="utf-8"))
for a in news:
    t = a.get("title") or ""
    for m in re.finditer(r"\b([A-Z][a-zA-Z.]+(?: [A-Z][a-zA-Z.]+)?) County\b", t):
        mark(m.group(1), "news_title_county")
    tl = t.lower()
    for city, counties in c2c.items():
        if len(city) > 4 and re.search(r"\b" + re.escape(city) + r"\b", tl):
            # require IN context: query was county-keyed or title says Indiana — news rows are IN-scoped queries
            for cty in counties:
                mark(cty, f"news_title_city:{city}")

for a in json.load(open(os.path.join(SCRATCH, "dc_action_rows.json"), encoding="utf-8")):
    if a.get("county"):
        for part in a["county"].split("|"):
            mark(part, "dc_action")

for o in json.load(open(os.path.join(SCRATCH, "municode_rows.json"), encoding="utf-8")):
    if o.get("county"):
        for part in o["county"].split("|"):
            mark(part, "ordinance")

try:
    for g in json.load(open(os.path.join(SCRATCH, "grid_xlsx_rows.json"), encoding="utf-8")):
        if g.get("county"):
            mark(g["county"], "grid_project")
except FileNotFoundError:
    pass
for g in json.load(open(os.path.join(SCRATCH, "grid_plan_rows.json"), encoding="utf-8")):
    if g.get("county"):
        mark(g["county"], "grid_project")

have = sorted(strong)
miss = [c for c in ALL92 if c not in strong]
print(f"STRICT receipts: {len(have)}/92")
print("WITH:", have)
print("WITHOUT (weak/query-only coverage):", miss)
save_scratch("county_coverage_strict.json", json.dumps(
    {"strict_with": have, "strict_without": miss,
     "detail": {c: sorted(s) for c, s in strong.items()}}, indent=1))
