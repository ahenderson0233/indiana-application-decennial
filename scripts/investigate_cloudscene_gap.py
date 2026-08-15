"""Investigate the cloudscene colo facilities that do NOT match our pinned data-centre layer.

Question being answered: of the genuine colo/enterprise facilities cloudscene lists in Indiana,
which are truly absent from our map, and which are already in the warehouse under another name
or in a source we never merged?

Order of work follows the standing rule - exhaust BigQuery before acquiring anything. The DC
union (in_data_centers_all) was built from OSM + Baxtel + Wikidata + DCM-via-coords. It does NOT
include peeringdb, which was clipped separately as a "connectivity layer" and carries
coordinates. That is the first place to look.

READ-ONLY. Writes docs/CLOUDSCENE_GAP.md and prints the verdict table.
"""
import re, unicodedata
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")

# Carrier central offices are telecom plant, not data centres - excluded from the gap question
# entirely (229 of the 260, 223 of them Frontier). Same regex the Data page uses.
TELCO = re.compile(r"^(frontier|at&t|centurylink|lumen|windstream|comcast|charter|spectrum|"
                   r"verizon|smithville|mediacom|nex-tech|tds|citizens)", re.I)

def stem(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())

def tokens(s):
    """Content words, minus the filler that makes everything look alike."""
    STOP = {"data", "center", "centers", "centre", "centres", "the", "inc", "llc", "corp",
            "company", "technology", "technologies", "partners", "solutions", "communications"}
    return {w for w in re.findall(r"[a-z0-9]+", str(s or "").lower()) if w not in STOP and len(w) > 2}

cloud = [dict(r) for r in client.query(f"""
    SELECT name, city, market, url FROM `{DS}.in_cloudscene_crosscheck` ORDER BY name""")]
colo = [c for c in cloud if not TELCO.match(c["name"] or "")]
print(f"cloudscene Indiana: {len(cloud)} rows, {len(cloud)-len(colo)} carrier COs, {len(colo)} colo/enterprise")

# ---- every candidate we hold, from every source, with coordinates where they exist ----
def grab(label, sql):
    try:
        rows = [dict(r) for r in client.query(sql)]
        print(f"  {label:<38} {len(rows):>4} Indiana rows")
        for r in rows: r["_src"] = label
        return rows
    except Exception as ex:
        print(f"  {label:<38} ERROR {str(ex)[:70]}")
        return []

print("\nsources checked:")
held = []
held += grab("in_data_centers_deduped (on the map)", f"""
    SELECT name, CAST(NULL AS STRING) city, lat, lon FROM `{DS}.in_data_centers_deduped`""")
held += grab("in_peeringdb_facilities (NOT merged)", f"""
    SELECT name, city, latitude AS lat, longitude AS lon FROM `{DS}.in_peeringdb_facilities`""")
held += grab("in_data_centers_peeringdb (NOT merged)", f"""
    SELECT name, city, latitude AS lat, longitude AS lon FROM `{DS}.in_data_centers_peeringdb`""")
# Column names READ, not guessed: DCM-coords keys on `dcm_slug` (a URL slug, no display name),
# baxtel on `site_name`/`company_name`. Both were assumed to have `name` on the first pass and
# errored - the §4 trap. The slug is hyphenated, which stem() flattens into the same shape as
# a display name, so it still matches.
held += grab("data_centers_datacentermap_coords", f"""
    SELECT dcm_slug AS name, CAST(NULL AS STRING) city, latitude AS lat, longitude AS lon
    FROM `{EN}.data_centers_datacentermap_coords`
    WHERE latitude BETWEEN 37.7 AND 41.8 AND longitude BETWEEN -88.2 AND -84.7""")
held += grab("data_centers_baxtel (site_name)", f"""
    SELECT site_name AS name, CAST(NULL AS STRING) city, latitude AS lat, longitude AS lon
    FROM `{EN}.data_centers_baxtel`
    WHERE latitude BETWEEN 37.7 AND 41.8 AND longitude BETWEEN -88.2 AND -84.7""")
held += grab("data_centers_baxtel (company_name)", f"""
    SELECT company_name AS name, CAST(NULL AS STRING) city, latitude AS lat, longitude AS lon
    FROM `{EN}.data_centers_baxtel`
    WHERE latitude BETWEEN 37.7 AND 41.8 AND longitude BETWEEN -88.2 AND -84.7""")
held += grab("data_centers (OSM)", f"""
    SELECT name, CAST(NULL AS STRING) city, latitude AS lat, longitude AS lon FROM `{EN}.data_centers`
    WHERE latitude BETWEEN 37.7 AND 41.8 AND longitude BETWEEN -88.2 AND -84.7""")

for h in held:
    h["stem"] = stem(h.get("name")); h["tok"] = tokens(h.get("name"))

ON_MAP = [h for h in held if h["_src"].startswith("in_data_centers_deduped")]

def initials(s):
    """GAP = Global Access Point. An operator abbreviated in one source and spelled out in
    another defeats both stem and token matching, so try the acronym explicitly."""
    ws = [w for w in re.findall(r"[A-Za-z]+", str(s or "")) if len(w) > 1]
    return "".join(w[0].lower() for w in ws[:4]) if len(ws) >= 2 else ""

def best_match(c, pool):
    cs, ct = stem(c["name"]), tokens(c["name"])
    if not cs: return None
    exact = [h for h in pool if h["stem"] and (h["stem"].startswith(cs) or cs.startswith(h["stem"]))]
    if exact: return ("name-stem", exact[0])
    # acronym both ways, requiring 3+ letters so two-word coincidences do not fire
    for n in (3, 4):
        ac = initials(" ".join(str(c["name"]).split()[:n]))
        if len(ac) >= 3:
            hit = [h for h in pool if h["stem"].startswith(ac)]
            if hit: return (f"acronym {ac.upper()}", hit[0])
    for h in pool:
        ah = initials(h.get("name"))
        if len(ah) >= 3 and cs.startswith(ah): return (f"acronym {ah.upper()}", h)
    # Token overlap, scored on DISTINCTIVE words only. Place names are stripped before scoring:
    # every colo in the state shares "indianapolis", so a match on it says nothing. Scoring them
    # equally also broke the tie-break - a useless "indianapolis" overlap could outrank a real
    # "indy" one purely on pool order, then get rejected, and the pair was reported as a gap.
    PLACES = {"indianapolis", "indy", "fort", "wayne", "ft", "south", "bend", "evansville",
              "indiana", "carmel", "fishers", "bloomington", "lafayette", "columbus", "hammond",
              "munster", "elkhart", "noblesville", "mishawaka", "carlisle", "terre", "haute"}
    scored = []
    for h in pool:
        ov = ct & h["tok"]
        strong = ov - PLACES
        if strong or len(ov) >= 2:
            scored.append((len(strong), len(ov), sorted(strong) or sorted(ov), h))
    if scored:
        scored.sort(key=lambda x: (-x[0], -x[1]))
        nstrong, ntot, ov, h = scored[0]
        if nstrong >= 1: return (f"tokens {'+'.join(ov)}", h)
        if ntot >= 2: return (f"place tokens {'+'.join(ov)}", h)
    return None

rows = []
for c in colo:
    on_map = best_match(c, ON_MAP)
    other = best_match(c, [h for h in held if h not in ON_MAP])
    rows.append({"name": c["name"], "city": c["city"], "market": c["market"],
                 "on_map": on_map, "elsewhere": other})

on = [r for r in rows if r["on_map"]]
recoverable = [r for r in rows if not r["on_map"] and r["elsewhere"]]
absent = [r for r in rows if not r["on_map"] and not r["elsewhere"]]

print(f"\nVERDICT over {len(colo)} colo facilities:")
print(f"  already on the map                : {len(on)}")
print(f"  IN THE WAREHOUSE, NOT ON THE MAP  : {len(recoverable)}   <- recoverable now, with coordinates")
print(f"  not found in any source we hold   : {len(absent)}")

out = ["# Cloudscene gap — what the 25 unmatched colo facilities actually are",
       "", f"Measured {len(cloud)} cloudscene Indiana rows: **{len(cloud)-len(colo)} are carrier central "
       f"offices** (223 Frontier alone) and are not data centres at all. The real question is the "
       f"**{len(colo)} colo/enterprise facilities**.", "",
       f"| verdict | n |", "|---|---:|",
       f"| already pinned on our map | {len(on)} |",
       f"| **held in the warehouse but never merged into the map layer** | **{len(recoverable)}** |",
       f"| not present in any source we hold | {len(absent)} |", ""]

out += ["## Recoverable now — in a source we already hold, with coordinates", "",
        "The DC union was built from OSM + Baxtel + Wikidata + DCM-via-coords. **peeringdb was "
        "clipped separately as a 'connectivity layer' and never merged**, so its facilities never "
        "reached the map even though they carry coordinates.", "",
        "| cloudscene name | city | found in | matched on | lat | lon |", "|---|---|---|---|---:|---:|"]
for r in recoverable:
    how, h = r["elsewhere"]
    out.append(f"| {r['name']} | {r['city']} | `{h['_src']}` | {how} — *{h.get('name')}* | "
               f"{h.get('lat')} | {h.get('lon')} |")

out += ["", "## Not found in anything we hold", "",
        "| cloudscene name | city | market |", "|---|---|---|"]
for r in absent:
    out.append(f"| {r['name']} | {r['city']} | {r['market']} |")

out += ["", "## Already pinned (matched our map layer)", "",
        "| cloudscene name | matched on | our name |", "|---|---|---|"]
for r in on:
    how, h = r["on_map"]
    out.append(f"| {r['name']} | {how} | {h.get('name')} |")

open(f"{REPO}\\docs\\CLOUDSCENE_GAP.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print(f"\ndocs/CLOUDSCENE_GAP.md written")
for r in recoverable:
    how, h = r["elsewhere"]
    print(f"   RECOVERABLE  {r['name'][:40]:<40} <- {h['_src'][:28]:<28} {h.get('lat')},{h.get('lon')}")
for r in absent:
    print(f"   ABSENT       {r['name'][:40]:<40} ({r['city']})")
