"""G69 — INDEX EVERY TABLE THIS APP USES OR DERIVES, AND WHAT IT IS FOR.

    python scripts/build_table_purpose_index.py

Operator, 2026-08-19: *"index and understand every single table that is either used or derived
within this application, and how it fits into our objectives."*

WHY THIS EXISTS, and why it is not one of the three documents that already look like it.

  * `docs/TABLE_INVENTORY.md` says what each object CARRIES (owner/geo/key/date/status flags).
    Its "what it is" column is the registry's source string, which is provenance, not purpose.
  * `docs/FEATURE_INVENTORY.md` maps features -> tables. It runs the other way, so a table that
    reaches no feature is INVISIBLE in it -- exactly the table this index has to find.
  * The wiring census answers a WEAKER question: 282 of 300 reach "a surface", where a surface
    counts a provenance line the reader cannot click, filter or toggle.

So the question none of them answers, and the one G65/G67 need answered before they can be
called finished:

    WHICH OF OUR OBJECTS REACHES A CONTROL THE USER CAN OPERATE, AND WHICH DOES NOT?

Everything here is MEASURED except the two classification tables at the top, which are stated
in the open so they can be corrected rather than argued with. A hand-typed inventory of 300
rows is correct exactly once -- that is why the checkpoint's state block is generated, and it
is why this is a script.
"""
import sys as _sys
try:                                    # cp1252 cannot encode this project's own glyphs;
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # three scripts have died
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")   # on their own print().
except Exception:
    pass

import glob
import io
import os
import re
import collections
from google.cloud import bigquery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DS = "energy-platfrom.indiana_app"
OUT = os.path.join(REPO, "docs", "TABLE_PURPOSE_INDEX.md")
client = bigquery.Client(project="energy-platfrom")

# ---------------------------------------------------------------- 1. the two stated classifications
# THE OBJECTIVE each object serves, in the developer's terms. Ordered: the FIRST pattern that
# matches wins, so put the specific before the general.
PARTS = [
    (r"^in_si_|^in_marion_(parcel|address)_crosswalk|^in_sba_|^in_acs_tract_vacancy",
     "P1 owner motivation", "who might sell, and how strongly we believe it"),
    (r"^in_(bus|pjm|miso|rtep|rto|queue|substations|transmission|grid_plans|generation|"
     r"power_plants|solar_pv|wind_turbines|eia860|balancing|txexp|osm_power)",
     "P2 power & grid", "can I get power here, in the direction I need, and when"),
    (r"^in_(sites|site_gates|parcel|county_rollup|sites_county|usa_structures|asset_distance|"
     r"logistics|railroads|roads|zctas|candidate_sites)",
     "P3 land & size", "is there enough usable land, and how far to what matters"),
    (r"^in_(flood|wetlands|padus|nonattainment|water|nhd|huc8|bonus_geo|incentive|coal_closure|"
     r"critical_habitat|echo|faa|storm|fema|seismic|drought|tribal|land_)",
     "P4 environmental", "what could stop or slow the permit"),
    (r"^in_(dc_actions|ordinances|openstates|iurc|receipts|iocs|commission_posture|news|"
     r"legislature|dc_docket|dc_opposition)",
     "P5 community & rules", "will the county let me build, and what have they done before"),
    (r"^in_(urdb|utility_tariff|eia861|eia923|cems|ferc714|gas_|eqr|rate_|elec_power|"
     r"econ_|dc_eei|dc_e3)",
     "P6 market & cost", "what will power actually cost me here"),
    (r"^in_(data_centers|fsis|workforce|cbp|qcew|acs_county|ghgrp|peeringdb|cloudscene|"
     r"gov_surplus|frpp|dc_colo_resolved|dc_operator_aliases)",
     "context", "who else is here, and what does the local economy look like"),
    # --- families the first pass left unclassified, filed by what they ANSWER, not by name ---
    (r"^in_(nfirs|ustp_ch7|sec_cik_registrant|gov_auction)",
     "P1 owner motivation", "who might sell, and how strongly we believe it"),
    (r"^in_(eia_plants|operating_generators|lbnl_interconnection|nrc_reactors|"
     r"state_irp_catalog|puc_state_access|pjm_nucra)",
     "P2 power & grid", "can I get power here, in the direction I need, and when"),
    (r"^in_(fcc_bdc|county_fibre|screener_candidates|county_rollup)",
     "P3 land & size", "is there enough usable land, and how far to what matters"),
    (r"^in_(county_flood|county_wetlands|spc_severe_events|solar_potential|"
     r"groundwater_sites|weather_stations)",
     "P4 environmental", "what could stop or slow the permit"),
    (r"^in_(territories|eia861_territory)",
     "P6 market & cost", "what will power actually cost me here"),
    (r"^(_|vw_|in_refresh_cadence|in_estate|in_indiana_census)",
     "infrastructure", "machinery: registries, censuses and join views"),
]

# CONTROL -> the MapLibre layer id prefix it governs -> the payload those layers are drawn from.
# Taken from LAYER_MAP / CONTEXT_LAYERS in app.js, which G34 made the single source of truth.
LAYER_PREFIX_PAYLOAD = {
    "grid-": "grid.geojson.gz", "pjm-": "pjm.geojson.gz", "gas-": "gas.geojson.gz",
    "terr-": "territories.geojson.gz", "env-": "overlays.geojson.gz",
    "water-": "water.geojson.gz", "fac-": "facilities.geojson.gz",
    "log-": "logistics.geojson.gz", "ctx-": "context.geojson.gz",
    "scr-": "screener.json.gz",
    # G72, 2026-08-19. ⚠ THIS MAP IS A HAND-MAINTAINED MIRROR OF LAYER_MAP AND IT WENT STALE
    # IMMEDIATELY. Four new gate layers shipped, browser-verified, and this generator still
    # reported TOGGLE = 38 because it had no "gate-" prefix and therefore could not connect
    # gates.geojson.gz to any control. The work was done; the INSTRUMENT could not see it --
    # which is the project's own rule (a clean or unchanged number is a claim about the
    # instrument first) landing on the tool built to measure the rule.
    # ⛔ ADD A PREFIX HERE IN THE SAME COMMIT THAT ADDS A LAYER, or this file will under-report
    # and the under-report will look like a finding.
    "gate-": "gates.geojson.gz",
}

TABLE_RE = re.compile(r"\bin_[a-z0-9_]+|\bvw_[a-z0-9_]+|\b_indiana_census\b")
PAYLOAD_RE = re.compile(r"data[/\\]((?:sites[/\\])?[A-Za-z0-9_.]+\.(?:geo)?json(?:\.gz)?)")
CTRL_RE = re.compile(r'id="((?:L|f|s|sc|w|ws)-[A-Za-z0-9_-]+)"')


def part_of(name):
    for pat, part, question in PARTS:
        if re.search(pat, name):
            return part, question
    return "unclassified", "-- no rule matched; add one to PARTS rather than guessing here"


# ---------------------------------------------------------------- 2. the warehouse, measured
print("reading the registry and live row counts ...")
reg = {}
for r in client.query(f"""
        SELECT table_name, ANY_VALUE(source) source, ANY_VALUE(method) method,
               MAX(built_at) built_at
        FROM `{DS}._registry` GROUP BY table_name"""):
    reg[r.table_name] = {"source": r.source or "", "method": r.method or "",
                         "built_at": r.built_at}

live = {r.table_id: r.row_count for r in client.query(f"""
        SELECT table_id, row_count FROM `{DS}.__TABLES__`""")}

objects = sorted(set(reg) | {t for t in live if not t.startswith("_") or t == "_indiana_census"})
print(f"  {len(objects)} objects ({len(reg)} registered, {len(live)} physically present)")

# ---------------------------------------------------------------- 3. table -> payload, from the exporters
# ⛔ THE FIRST VERSION OF THIS WAS WRONG AND IT IS WORTH RECORDING WHY. It took the CROSS-PRODUCT
# of every table a script mentions with every payload that script writes. `export_grid_sentiment.py`
# alone reads ~20 tables and writes several payloads, so one script minted ~60 false links -- and
# the result claimed `in_sites` (the 3.55M-parcel spine) was exposed by `L-terr`, the utility-
# TERRITORY checkbox. A control coverage figure built on that join would have been fiction.
#
# The fix is PROXIMITY: a payload write is attributed only to tables named near it, i.e. inside the
# query or block that actually produces it. Still an approximation, and it is labelled as one on
# the face of the document -- but it no longer links a parcel table to a territory toggle.
WINDOW = 2500
print("scanning scripts for table -> payload lineage (proximity-scoped) ...")
tbl_payload = collections.defaultdict(set)
tbl_script = collections.defaultdict(set)
for f in glob.glob(os.path.join(REPO, "scripts", "*.py")) + \
         glob.glob(os.path.join(REPO, "scrapers", "**", "*.py"), recursive=True):
    src = io.open(f, encoding="utf-8", errors="replace").read()
    rel = os.path.relpath(f, REPO).replace("\\", "/")
    for t in set(TABLE_RE.findall(src)):
        tbl_script[t].add(rel)
    for pm in PAYLOAD_RE.finditer(src):
        payload = pm.group(1).replace("\\", "/")
        lo, hi = max(0, pm.start() - WINDOW), min(len(src), pm.end() + WINDOW)
        for t in set(TABLE_RE.findall(src[lo:hi])):
            tbl_payload[t].add(payload)

# ---------------------------------------------------------------- 4. pages: controls, and what they read
print("scanning pages for controls ...")
page_tables = collections.defaultdict(set)      # page -> tables it names
page_payloads = collections.defaultdict(set)    # page -> payloads it fetches
controls = {}                                   # control id -> page
for f in glob.glob(os.path.join(REPO, "*.html")) + [os.path.join(REPO, "app.js"),
                                                    os.path.join(REPO, "common.js")]:
    if not os.path.exists(f):
        continue
    src = io.open(f, encoding="utf-8", errors="replace").read()
    rel = os.path.basename(f)
    page_tables[rel] |= set(TABLE_RE.findall(src))
    page_payloads[rel] |= {p.replace("\\", "/") for p in PAYLOAD_RE.findall(src)}
    for c in CTRL_RE.findall(src):
        controls.setdefault(c, rel)

# control -> payload, via LAYER_MAP / CONTEXT_LAYERS in app.js
appjs = io.open(os.path.join(REPO, "app.js"), encoding="utf-8", errors="replace").read()
ctrl_payload = collections.defaultdict(set)


def _harvest(block):
    for ctrl, body in re.findall(r'"((?:L)-[A-Za-z0-9_-]+)"\s*:\s*(\[[^\]]*\]|"[^"]*")', block):
        for lyr in re.findall(r'"([a-z]+-[a-z0-9-]+)"', body):
            for pre, pay in LAYER_PREFIX_PAYLOAD.items():
                if lyr.startswith(pre):
                    ctrl_payload[ctrl].add(pay)


m = re.search(r"const LAYER_MAP = \{(.*?)\};", appjs, re.S)
if m:
    _harvest(m.group(1))
m = re.search(r"const CONTEXT_LAYERS = \{(.*?)\};", appjs, re.S)
if m:
    _harvest(m.group(1))
ctrl_payload["L-parcels"].add("sites/{fips}.geojson.gz")
ctrl_payload["L-screener"].add("screener.json.gz")

payload_ctrl = collections.defaultdict(set)
for c, ps in ctrl_payload.items():
    for p in ps:
        payload_ctrl[p].add(c)

# every non-layer control still belongs to a page; a page's filters gate every payload it fetches
PAGE_FILTERED = {"index.html": "map console filters", "screener.html": "screener filters",
                 "market.html": "market inputs", "grid.html": "grid page",
                 "community.html": "community page", "si.html": "owner-signals page",
                 "insights.html": "insights page", "data.html": "data page"}

# ---------------------------------------------------------------- 4b. the wiring census is the
# AUTHORITY on whether an object reaches a surface at all. It already resolves builder-vs-consumer
# and the registry-panel and derivative routes, and it has been the trusted instrument for weeks.
# Re-deriving it here would be a second copy of one measurement, which is the defect this project
# hits most (two copies of one thing WILL drift). Read its output instead.
census_route = {}
_cp = os.path.join(REPO, "docs", "WIRING_CENSUS.md")
if os.path.exists(_cp):
    for line in io.open(_cp, encoding="utf-8", errors="replace"):
        m = re.match(r"\|\s*`([a-z_0-9]+)`\s*\|\s*([^|]+?)\s*\|\s*(.+?)\s*\|\s*$", line)
        if m and m.group(2).strip() in ("direct", "registry panel", "derivative", "**none**"):
            census_route[m.group(1)] = (m.group(2).strip(), m.group(3).strip("` "))
    print(f"  wiring census read: {len(census_route)} objects with a resolved route")

# ---------------------------------------------------------------- 5. resolve each object
print("resolving control coverage per object ...")
rows = []
for t in objects:
    r = reg.get(t, {})
    payloads = sorted(tbl_payload.get(t, set()))
    pages = sorted(p for p, ts in page_tables.items() if t in ts)
    ctrls = set()
    for p in payloads:
        ctrls |= payload_ctrl.get(p, set())
    # a table named directly by a page is reachable through that page's own controls
    surf = sorted(set(pages) | {pg for pg, ps in page_payloads.items()
                                if set(ps) & set(payloads)})
    route, via = census_route.get(t, (None, ""))
    if route and route != "**none**" and not surf:
        surf = [f"{route}: {via[:40]}"]
    part, question = part_of(t)

    if ctrls:
        verdict = "TOGGLE"
    elif any(s in PAGE_FILTERED for s in surf):
        verdict = "PAGE ONLY"
    elif part == "infrastructure":
        verdict = "INFRASTRUCTURE"
    elif surf:
        verdict = "READ-ONLY"
    else:
        verdict = "NO SURFACE"

    rows.append({
        "table": t, "rows": live.get(t), "part": part, "question": question,
        "source": (r.get("source") or "").split("\n")[0][:70],
        "payloads": payloads, "surfaces": surf, "controls": sorted(ctrls),
        "verdict": verdict, "registered": t in reg,
    })

order = {"TOGGLE": 0, "PAGE ONLY": 1, "READ-ONLY": 2, "NO SURFACE": 3, "INFRASTRUCTURE": 4}
tally = collections.Counter(x["verdict"] for x in rows)
by_part = collections.Counter(x["part"] for x in rows)

# ---------------------------------------------------------------- 6. write it
print(f"writing {OUT} ...")
o = []
A = o.append
A("# TABLE PURPOSE INDEX — every object, what it is FOR, and the control that exposes it")
A("")
A("**GENERATED by `scripts/build_table_purpose_index.py`. Do not hand-edit — regenerate.**")
A("")
A("> Operator, 2026-08-19: *\"index and understand every single table that is either used or")
A("> derived within this application, and how it fits into our objectives.\"*")
A("")
A("This answers the question the other three documents do not. `TABLE_INVENTORY.md` says what an")
A("object CARRIES; `FEATURE_INVENTORY.md` maps features→tables and so cannot see a table that")
A("reaches no feature; and the wiring census counts a *surface*, which includes a provenance line")
A("nobody can click. **The question here is whether a USER CAN OPERATE A CONTROL that reaches it** —")
A("which is the denominator for **G65** (every map feature its own toggle) and **G67** (the screener")
A("filters on everything).")
A("")
A("## The verdicts")
A("")
A("| verdict | meaning | n |")
A("|---|---|---:|")
A(f"| **TOGGLE** | a checkbox or layer control the user can operate reaches it | **{tally['TOGGLE']}** |")
A(f"| **PAGE ONLY** | it reaches a filterable page, but no control names it — a G67 candidate | **{tally['PAGE ONLY']}** |")
A(f"| **READ-ONLY** | rendered, but nothing the user can ask a question with | **{tally['READ-ONLY']}** |")
A(f"| **NO SURFACE** | reaches nothing at all | **{tally['NO SURFACE']}** |")
A(f"| **INFRASTRUCTURE** | registries, censuses and join views — correctly not a control | **{tally['INFRASTRUCTURE']}** |")
A("")
A(f"**{len(rows)} objects.** ⭐ **{tally['TOGGLE']} of them can be turned on and off by the reader.**")
A("Everything in PAGE ONLY and READ-ONLY is data we hold and the user cannot ask about.")
A("")
A("## By objective")
A("")
A("| objective | the developer question it answers | objects |")
A("|---|---|---:|")
seen_q = {}
for pat, part, question in PARTS:
    seen_q[part] = question
for part, n in by_part.most_common():
    A(f"| **{part}** | {seen_q.get(part, '—')} | {n} |")
A("")
A("⚠ The objective classification is a **stated rule table** at the top of the generator, not a")
A("judgement buried in prose. If a row is filed wrongly, fix the rule and regenerate — do not")
A("edit this file.")
A("")
A("## ⚠ Two limits of this instrument, stated rather than discovered later")
A("")
A("**1. The control column resolves to PAYLOAD granularity, not layer granularity.** Several")
A("controls draw from one payload — `L-bus`, `L-lines` and `L-subs` all read `grid.geojson.gz` —")
A("so a table feeding only the bus half is credited to all three. The verdict (is there ANY control)")
A("is sound; treat the named controls as *the controls on the payload it feeds*.")
A("")
A("**2. Table→payload is proximity-scoped, not parsed.** ⛔ The first version cross-produced every")
A("table a script mentions with every payload it writes, and claimed `in_sites` — the 3.55M-parcel")
A("spine — was exposed by `L-terr`, the utility-territory checkbox. It now attributes a payload only")
A("to tables named within ~2,500 characters of the write. That is an approximation and it will")
A("mis-file some rows; it no longer invents whole categories of them.")
A("")

for verdict in sorted(tally, key=lambda v: order[v]):
    sel = [x for x in rows if x["verdict"] == verdict]
    A(f"---\n\n## {verdict} — {len(sel)} objects\n")
    A("| object | rows | objective | control / surface | what it is |")
    A("|---|---:|---|---|---|")
    for x in sorted(sel, key=lambda x: (x["part"], -(x["rows"] or 0))):
        n = f"{x['rows']:,}" if x["rows"] is not None else "—"
        ctl = ", ".join(f"`{c}`" for c in x["controls"]) or ", ".join(x["surfaces"]) or "—"
        A(f"| `{x['table']}` | {n} | {x['part']} | {ctl[:60]} | {x['source'][:60]} |")
    A("")

io.open(OUT, "w", encoding="utf-8", newline="").write("\n".join(o))
print(f"\n{len(rows)} objects indexed")
for v, n in sorted(tally.items(), key=lambda kv: order[kv[0]]):
    print(f"  {v:16s} {n:4d}")
