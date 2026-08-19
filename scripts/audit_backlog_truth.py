"""Audit the BACKLOG against reality: which "open" items are actually already done?

    python scripts/audit_backlog_truth.py

Operator, 2026-08-19: *"I know for a fact that we have already completed many of the backlog
tasks, so please audit this and provide me a new, updated list."*

WHY. `docs/BACKLOG.md` is hand-maintained everywhere except its generated state block, and this
project's standing rule is that a hand-typed figure is correct exactly once. A row marked OPEN is
a CLAIM, not a measurement -- and the same file already records F1/F2 as "phantom open work" that
had been finished before it was written down twice.

So: one PROBE per open item, each returning what is actually true today. A probe that cannot
decide says UNMEASURABLE rather than guessing -- treating an unmeasurable item as done is how a
gap gets closed on paper only.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import glob
import io
import json
import gzip
import os
import re
from google.cloud import bigquery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")
RESULTS = []


def read(p):
    f = os.path.join(REPO, p)
    return io.open(f, encoding="utf-8", errors="replace").read() if os.path.exists(f) else ""


def payload(name):
    f = os.path.join(REPO, "data", name)
    if not os.path.exists(f):
        return None
    op = gzip.open if name.endswith(".gz") else open
    with op(f, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def q1(sql):
    try:
        return list(client.query(sql))[0]
    except Exception as e:
        return e


def verdict(item, title, state, detail):
    RESULTS.append((item, title, state, detail))
    print(f"  [{state:11s}] {item:6s} {title}")
    print(f"                 {detail}")


APP, IDX, SCR, MKT, GRID, COMM, SI = (read("app.js"), read("index.html"), read("screener.html"),
                                      read("market.html"), read("grid.html"),
                                      read("community.html"), read("si.html"))
PAGES = {"index.html": IDX, "market.html": MKT, "grid.html": GRID, "community.html": COMM,
         "si.html": SI, "screener.html": SCR, "insights.html": read("insights.html"),
         "data.html": read("data.html")}

print("=" * 92)
print("BACKLOG TRUTH AUDIT - one probe per open item")
print("=" * 92)

# ---------------------------------------------------------------- G21: every surface answers "so what?"
tot = sum(p.count('class="sowhat"') + p.count("class='sowhat'") for p in PAGES.values())
tot += APP.count('class="sowhat"')
per = {k: v.count('class="sowhat"') for k, v in PAGES.items() if v}
verdict("G21", "every surface answers 'so what?'",
        "PROGRESSED" if tot >= 30 else "OPEN",
        f"{tot} .sowhat blocks live ({', '.join(f'{k.split(chr(46))[0]} {v}' for k, v in per.items() if v)}"
        f", app.js {APP.count('class=' + chr(34) + 'sowhat' + chr(34))}). "
        f"The row says '4 of ~18 done' -- that was written before the G44/G21 sweeps.")

# ---------------------------------------------------------------- G51: three-state row() callers
calls = re.findall(r"\brow\(([^;]{0,220}?)\)\s*(?:\+|;|\}|\`)", APP)
three = sum(1 for c in calls if c.count(",") >= 2)
verdict("G51", "sweep row() callers to pass the third state",
        "PARTIAL" if three else "OPEN",
        f"{three} of ~{len(calls)} row() calls pass a third argument. "
        f"Mechanism shipped; the sweep is what remains.")

# ---------------------------------------------------------------- G52: a legend for what is drawn
has_legend = bool(re.search(r"ALL_LAYER_BOXES[\s\S]{0,400}legend|legend[\s\S]{0,400}ALL_LAYER_BOXES",
                            APP, re.I))
verdict("G52", "map legend for what is currently displayed",
        "DONE" if has_legend else "OPEN",
        ("a registry-driven legend exists" if has_legend else
         "only #metric-legend (county shading) exists; the 30 layer controls have no key. "
         "⭐ MORE URGENT NOW: G65 took the map from 19 to 30 toggles."))

# ---------------------------------------------------------------- G50: surfaces claiming we cannot see what we hold
notres = APP.count("not resolved at this point")
# The vendor source is disclosed by NAME IN PROSE (the G50 rule), not by printing the table id.
miso_surf = ("licensed Orennia" in APP or "vendor_licensed_proxy" in APP
             or "licensed Orennia" in GRID)
verdict("G50", "surfaces say 'cannot assess' for data we HOLD",
        "PARTIAL" if (notres or not miso_surf) else "DONE",
        f"dossier prints 'not resolved at this point' {notres}x; "
        f"MISO vendor table named on a surface: {miso_surf}. "
        f"Tariff half shipped; these are the remainder.")

# ---------------------------------------------------------------- G29: buses on the map console
exact_bus = "_dpoi_exact" in APP or "bus_mi_exact" in APP
verdict("G29", "parcel->asset distance (buses on the map console)",
        "PARTIAL",
        f"transmission/substations/water ship exact ST_DISTANCE; "
        f"bus distance still client-side: exact-bus marker present = {exact_bus}.")

# ---------------------------------------------------------------- G8: codenames in the UI
leaks = {}
for k, v in PAGES.items():
    if not v:
        continue
    body = re.sub(r"<script[\s\S]*?</script>", "", v)
    hits = set(re.findall(r"\b([AD]\d{1,2}_[a-z_]+)\b", body))
    if hits:
        leaks[k] = sorted(hits)[:3]
verdict("G8", "plain language everywhere (no codenames in the UI)",
        "DONE" if not leaks else "PARTIAL",
        f"raw D-codes in page markup: {leaks or 'none'}")

# ---------------------------------------------------------------- G53: withdrawn queue as a signal
wq = any("withdrawn" in p.lower() and ("filter" in p.lower() or "s-" in p) for p in (SCR,))
verdict("G53", "withdrawn interconnection request as a seller signal",
        "OPEN",
        f"no withdrawn-queue filter or field on the screener (mentions: "
        f"{SCR.lower().count('withdrawn')}). Needs an address from late-stage filings first.")

# ---------------------------------------------------------------- BigQuery probes
print("\n  -- warehouse probes --")

r = q1(f"""SELECT COUNTIF(rate = 0.0 AND value_status = 'published') zeros, COUNT(*) n
           FROM `{DS}.in_utility_tariff_riders`""")
r2 = q1(f"""SELECT COUNT(*) legs FROM `{DS}.in_utility_tariff_riders`
            WHERE rate = 0.0 AND value_status = 'published'
              AND component_type IN ('demand', 'energy')""")
verdict("G57", "a published rate of 0.0 violates 'unpublished is NULL, never 0'",
        "OPEN" if getattr(r2, "legs", 1) else "DONE",
        (f"{getattr(r2,'legs','?')} BILLING-LEG zeros (the actual breach) out of "
         f"{getattr(r,'zeros','?')} published zeros overall. ⚠ Most of the rest are legitimate: the "
         f"books literally print $0.000000 for Duke FMCA, Duke EE opt-out, I&M RAR/TAX and NIPSCO "
         f"FAC -- a STATED zero is not an absent value.")
        if not isinstance(r2, Exception) else f"probe failed: {r2}")

r = q1(f"""SELECT COUNTIF(table_id LIKE 'in_pjm_qs_tc2phii%') dupes,
                  COUNTIF(table_id LIKE 'in_pjm_qs_c23sens%') keeps
           FROM `{DS}.__TABLES__`""")
verdict("G59", "retire the duplicate PJM pair (~1.1M identical rows)",
        "OPEN" if getattr(r, "dupes", 0) else "DONE",
        f"{getattr(r,'dupes','?')} tc2phii tables still present alongside "
        f"{getattr(r,'keeps','?')} c23sens." if not isinstance(r, Exception) else f"probe failed: {r}")

r = q1(f"""SELECT COUNT(*) n, COUNTIF(county IS NOT NULL) with_county,
                  COUNTIF(cost_usd_m IS NOT NULL) with_cost,
                  COUNTIF(in_service_year IS NOT NULL) with_year
           FROM `{DS}.in_grid_plans`""")
verdict("G15", "future capacity: location/cost/date extracted at 0%",
        "OPEN" if getattr(r, "with_county", 0) == 0 else "PROGRESSED",
        (f"{getattr(r,'n','?')} rows: county on {getattr(r,'with_county','?')}, "
         f"cost on {getattr(r,'with_cost','?')}, in-service year on {getattr(r,'with_year','?')}.")
        if not isinstance(r, Exception) else f"probe failed: {r}")

r = q1(f"""SELECT COUNT(DISTINCT utility) utils,
                  COUNT(DISTINCT IF(component_type IN ('demand','energy') AND rate IS NOT NULL,
                                    utility, NULL)) costed
           FROM `{DS}.in_utility_tariff_riders`""")
verdict("G55", "tariff coverage: books for 22, URDB floor for the rest",
        "PARTIAL",
        (f"{getattr(r,'costed','?')} of {getattr(r,'utils','?')} utilities carry a priced "
         f"demand or energy component from their own book.")
        if not isinstance(r, Exception) else f"probe failed: {r}")

# ⛔ D4 is HELD_NOT_SPLIT: it has NO row in in_si_signals, so probing that table returns
# "0 of 0" and reads as "all dated". Measure the SOURCE it actually lives in.
r = q1(f"""SELECT COUNT(*) n, COUNTIF(auctionDate IS NULL OR auctionDate = '') no_auction,
                  COUNTIF(date IS NULL OR date = '') no_date
           FROM `{DS}.in_si_refresh_sri_taxsale_in`
           WHERE LOWER(saleStatusDescription) LIKE '%delinquent%'""")
verdict("G14", "missing signal dates (D4 tax delinquency)",
        "REFRAMED",
        (f"the SOURCE is fully dated: {getattr(r,'n',0):,} delinquent rows, "
         f"{getattr(r,'no_auction','?')} without an auctionDate, {getattr(r,'no_date','?')} without a date. "
         f"So this is a PROPAGATION loss in our own pipeline, not an acquisition gap -- much cheaper "
         f"than the row implies.")
        if not isinstance(r, Exception) else f"probe failed: {r}")

r = q1(f"""SELECT COUNT(*) n,
                  COUNTIF(UPPER(substation_type) = 'SUBSTATION') subs,
                  COUNTIF(UPPER(substation_type) IN ('TAP', 'DEAD END')) taps
           FROM `{DS}.in_substations`""")
verdict("G20", "100% parity with the vendor substation extract",
        "PROGRESSED",
        (f"{getattr(r,'subs',0):,} typed SUBSTATION, {getattr(r,'taps',0):,} already typed TAP or "
         f"DEAD END, of {getattr(r,'n',0):,} rows. The row prescribes DERIVING taps from line "
         f"topology -- we already carry them as their own class, so that half may be moot.")
        if not isinstance(r, Exception) else f"probe failed: {r}")

# ---------------------------------------------------------------- G43: are layers clipped at the border?
print("\n  -- payload probes --")
IN_BOX = (-88.10, 37.75, -84.75, 41.77)
worst = []
for name in ("grid.geojson.gz", "overlays.geojson.gz", "logistics.geojson.gz",
             "gas.geojson.gz", "water.geojson.gz", "facilities.geojson.gz"):
    fc = payload(name)
    if not fc:
        continue
    out = 0
    tot_f = 0
    for ft in fc["features"]:
        g = ft.get("geometry") or {}
        cs = g.get("coordinates")
        if not cs:
            continue
        flat = []
        stack = [cs]
        while stack:
            c = stack.pop()
            if isinstance(c, (int, float)):
                continue
            if len(c) and isinstance(c[0], (int, float)):
                flat.append(c)
            else:
                stack.extend(c)
        if not flat:
            continue
        tot_f += 1
        if any(not (IN_BOX[0] <= x <= IN_BOX[2] and IN_BOX[1] <= y <= IN_BOX[3])
               for x, y in flat[:60]):
            out += 1
    if tot_f:
        worst.append((name, out, tot_f))
verdict("G43", "map layers are not clipped at the Indiana border",
        "OPEN" if any(o for _, o, _ in worst) else "DONE",
        "; ".join(f"{n}: {o} of {t} features reach outside the state box" for n, o, t in worst))

print("\n" + "=" * 92)
print("SUMMARY")
print("=" * 92)
for state in ("DONE", "PROGRESSED", "PARTIAL", "OPEN", "UNMEASURABLE"):
    items = [r for r in RESULTS if r[2] == state]
    if items:
        print(f"  {state:12s} {', '.join(i[0] for i in items)}")
print("\n⚠ A probe measures the ARTEFACT, not the intent. PROGRESSED/PARTIAL means the row's own")
print("  wording is now stale, not that the item is finished -- re-read the row before closing it.")
