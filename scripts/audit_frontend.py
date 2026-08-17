"""Audit every page against the defects this application has ACTUALLY had.

Not a style check. Each test below exists because the failure it looks for has already shipped
here at least once:

  1. JS REFERENCES A MISSING ELEMENT ID. `si.html:128 Cannot set properties of null` was reported
     as a live bug for exactly this shape. A getElementById that returns null throws on the next
     property write and kills the REST of the script — every panel after it silently goes blank.

  2. AN ELEMENT ID NOTHING EVER TOUCHES. Dead UI: a table or stat that renders empty forever
     because no code ever fills it. The logistics layer sat broken for weeks this way.

  3. A PAYLOAD THE PAGE FETCHES THAT DOES NOT EXIST. A missing .gz is a blank panel and, on the
     map page, a dead boot.

  4. A PAYLOAD KEY THE PAGE READS THAT THE EXPORT NEVER WRITES. The other half of the same
     failure: the file exists, the key does not, and `(O.foo || [])` renders nothing forever
     without erroring.

  5. A CONST DECLARED TWICE IN ONE SCOPE. A redeclaration is a SyntaxError that aborts the WHOLE
     inline script, so the page renders nothing at all. Nearly shipped as `const VER` today.

  6. DUPLICATE id ATTRIBUTES. getElementById returns the first, so the second silently never
     updates.

Static only — no browser needed, so it runs in CI or on a machine with no display.
"""
import gzip
import json
import os
import re
from collections import Counter, defaultdict

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
PAGES = ["index.html", "grid.html", "market.html", "community.html", "si.html", "data.html"]
SHARED_JS = ["app.js", "common.js"]

# FIRST RUN OF THIS AUDIT PRODUCED 56 FINDINGS AND ROUGHLY ZERO REAL ONES. That is worse than no
# audit: a check that cries wolf gets ignored, which is how the wiring census came to count each
# table's own build script as a "feature". Every filter below was added because the first version
# reported something that was demonstrably fine:
#
#   'sc-open-parcel'  flagged as a missing element. It is CREATED at app.js:879 inside an
#                     innerHTML template and bound two lines later. Fix: also collect ids that
#                     appear inside JS string literals.
#   'const rows' x3   flagged as redeclared in grid.html. They sit at lines 78, 109 and 146 — one
#                     top-level, two inside functions. Fix: track brace depth, not indentation.
#   'L-subs', 'f-mw-val'  flagged as dead. They are read through LAYER_MAP and the V() helper, not
#                     through getElementById. Fix: count any string mention in JS.
#   '.geojson'        flagged as an absent payload key. The regex was matching inside the literal
#                     "data/grid.geojson.gz". Fix: strip string literals before scanning for
#                     property access.
def strip_strings(js):
    """Remove string and template literals so property-access scanning cannot match inside them."""
    js = re.sub(r"`(?:[^`\\]|\\.)*`", "``", js, flags=re.S)
    js = re.sub(r'"(?:[^"\\]|\\.)*"', '""', js)
    js = re.sub(r"'(?:[^'\\]|\\.)*'", "''", js)
    return js


def top_level_decls(js):
    """Names declared with const/let at brace depth 0 of this script block. Indentation lies;
    depth does not."""
    out, depth, i, n = [], 0, 0, len(js)
    stripped = strip_strings(js)
    for m in re.finditer(r"[{}]|(?:^|[\s;(])(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=", stripped, re.M):
        tok = m.group(0)
        if m.group(1) and depth == 0:
            out.append(m.group(1))
        elif tok.endswith("{"):
            depth += 1
        elif tok.endswith("}"):
            depth = max(0, depth - 1)
    return out

findings = []


def add(page, kind, detail):
    findings.append({"page": page, "kind": kind, "detail": detail})


def read(p):
    fp = os.path.join(REPO, p)
    return open(fp, encoding="utf-8", errors="ignore").read() if os.path.exists(fp) else ""


shared = "\n".join(read(f) for f in SHARED_JS)
shared_ids = set(re.findall(r'getElementById\(["\']([^"\']+)["\']\)', shared))
shared_ids |= set(re.findall(r'\$\(["\']([^"\']+)["\']\)', shared))

print("=" * 96)
print("FRONT-END AUDIT — every page, against the defects this app has actually had")
print("=" * 96)

for page in PAGES:
    html = read(page)
    if not html:
        add(page, "MISSING_PAGE", "file not found")
        continue

    # a page's own inline scripts, plus app.js only where the page loads it
    inline = "\n".join(re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S))
    # ⚠ MATCH THE FILENAME, NOT THE WHOLE URL. Assets now carry a cache-busting content hash
    # (`app.js?v=d798ada5`, see scripts/stamp_assets.py), and an exact-string test for
    # 'src="app.js"' silently stopped matching the moment stamping shipped. The audit then believed
    # index.html loaded NO script and reported all 33 of its element ids as unreferenced - the
    # entire scoring UI declared dead, which is precisely the rule-9 false-positive class this file
    # was rewritten to eliminate. An audit that cries wolf gets ignored, so it must tolerate a
    # query string.
    loads_app = re.search(r'src="app\.js(\?[^"]*)?"', html) is not None
    js = inline + ("\n" + read("app.js") if loads_app else "")

    # ---- 6. duplicate id attributes -----------------------------------------------------------
    ids_in_html = re.findall(r'\bid="([^"]+)"', html)
    for i, n in Counter(ids_in_html).items():
        if n > 1:
            add(page, "DUPLICATE_ID",
                f"id={i!r} appears {n} times — getElementById returns the first, the rest never update")
    html_ids = set(ids_in_html)

    # ids the JS CREATES at runtime inside template/string literals are legitimately absent from
    # the page file — they exist by the time anything binds to them
    created_at_runtime = set(re.findall(r'\bid="([^"]+)"', js)) | set(re.findall(r"\bid='([^']+)'", js))

    # ---- 1. JS referencing an id that is not in the HTML --------------------------------------
    used = set(re.findall(r'getElementById\(["\']([^"\']+)["\']\)', js))
    used |= set(re.findall(r'\$\(["\']([^"\']+)["\']\)', js))
    for i in sorted(used - html_ids - created_at_runtime):
        add(page, "JS_REFS_MISSING_ID",
            f"{i!r} — getElementById returns null; the next property write throws and kills the rest of the script")

    # ---- 2. an id in the HTML that no code ever touches ---------------------------------------
    # "touched" means mentioned ANYWHERE in the JS as a string — through getElementById, through a
    # lookup table like LAYER_MAP, or through a helper like V(). Only the first was checked before,
    # which flagged every working layer toggle on the map page.
    mentioned = set(re.findall(r'["\']([A-Za-z][\w-]{2,})["\']', js)) | shared_ids
    # IDS BUILT FROM TEMPLATE LITERALS. `$(`w-${k}`)` constructs w-p1..w-p6 at runtime, so a
    # literal-string search cannot see them. The first version of this audit reported all six
    # weight sliders and all six value displays as dead UI — twelve findings, none real, on the
    # scoring feature that §13(7) turns on. Treat the static prefix as a wildcard.
    for prefix in re.findall(r'[$]\(\s*`([A-Za-z][\w-]*?)\$\{', js) + \
                  re.findall(r'getElementById\(\s*`([A-Za-z][\w-]*?)\$\{', js):
        mentioned |= {i for i in html_ids if i.startswith(prefix)}
    for i in sorted(html_ids - used - mentioned):
        if re.match(r"^(map|main|rail|panel|hdr|nav|foot|wrap|content|layout|topbar|topbtns|title|presets)", i):
            continue
        add(page, "DEAD_ELEMENT_ID",
            f"{i!r} — in the page and never mentioned by any script: it can only ever render empty")

    # ---- 5. const redeclared in the SAME scope -------------------------------------------------
    for blk in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S):
        for name, n in Counter(top_level_decls(blk)).items():
            if n > 1:
                add(page, "CONST_REDECLARED",
                    f"{name!r} declared {n} times at brace depth 0 — a SyntaxError aborts the WHOLE script")

    # ---- 3 & 4. payloads and the keys read out of them -----------------------------------------
    for payload in sorted(set(re.findall(r'fetchGz\(["\']([^"\']+)["\']\)', js) +
                              re.findall(r'fetch\(["\'](data/[^"\'?]+)["\']', js))):
        fp = os.path.join(REPO, payload)
        if not os.path.exists(fp):
            add(page, "PAYLOAD_MISSING", f"{payload} — fetched but not on disk")
            continue
        try:
            obj = (json.load(gzip.open(fp, "rt", encoding="utf-8")) if payload.endswith(".gz")
                   else json.load(open(fp, encoding="utf-8")))
        except Exception as e:
            add(page, "PAYLOAD_UNREADABLE", f"{payload} — {str(e)[:70]}")
            continue
        if not isinstance(obj, dict):
            continue
        var = None
        m = re.search(r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*await\s+fetchGz\(["\']'
                      + re.escape(payload) + r'["\']\)', js)
        if m:
            var = m.group(1)
        if not var:
            continue
        # scan property access with STRING LITERALS REMOVED — otherwise `grid.geojson` matches
        # inside the literal "data/grid.geojson.gz" and reports a key that was never read
        for key in sorted(set(re.findall(rf"\b{re.escape(var)}\.([A-Za-z_$][\w$]*)", strip_strings(js)))):
            if key in ("then", "catch", "map", "filter", "length", "forEach", "features", "find"):
                continue
            if key not in obj:
                add(page, "PAYLOAD_KEY_ABSENT",
                    f"{payload}: page reads .{key} — the export never writes it, so it renders empty forever")

# ---- 7. A SURFACE READING A SUPERSEDED TABLE -------------------------------------------------
# THE CHECK THIS AUDIT WAS MISSING, and the operator caught it before the audit did: the map's
# county-receipts feed was showing FOUR ordinances. It read `in_ordinances_dc` — the v1 table, 4
# rows, one of them a false positive — while `in_ordinances_dc_v2` (153 candidates, 19 admitted by
# triage) and `in_dc_actions_resolved` (73 verified county actions) sat in the warehouse unread.
#
# Nothing was broken: no console error, no empty panel, no missing key. The page rendered exactly
# what it was told to render, and what it was told was two generations out of date. Every other
# check in this file asks "does it work"; this one asks "is it current", which is a different
# question and the one that was failing.
#
# Generalised: if a script reads table X, and a table named X_v2 / X_v3 / X_widened / X_resolved
# exists with MORE rows, the script is probably reading the older generation.
print("\n" + "=" * 96)
print("SUPERSEDED-TABLE CHECK — is any surface reading an older generation?")
print("=" * 96)
try:
    from google.cloud import bigquery

    _c = bigquery.Client(project="energy-platfrom")
    _DS = "energy-platfrom.indiana_app"
    sizes = {r.table_id: r.row_count for r in
             _c.query(f"SELECT table_id, row_count FROM `{_DS}.__TABLES__`")}

    scripts = {}
    for d in ("scripts", "scrapers"):
        for root, _, files in os.walk(os.path.join(REPO, d)):
            for fn in files:
                if fn.endswith(".py"):
                    fp = os.path.join(root, fn)
                    scripts[os.path.relpath(fp, REPO)] = open(fp, encoding="utf-8",
                                                              errors="ignore").read()

    SUCCESSOR = ("_v2", "_v3", "_widened", "_resolved", "_dated", "_reconciled")
    for rel, src in sorted(scripts.items()):
        rel = rel.replace("\\", "/")
        # SURFACES ONLY. A loader legitimately names its own predecessor in a note ("in_ordinances_dc
        # (v1, 4 rows) was not touched"), and audits read everything by design. This check asks
        # whether something the USER SEES is a generation behind, so it looks at exports only.
        if not rel.startswith("scripts/export_"):
            continue
        if rel.startswith("scripts\\audit") or "audit_" in rel:
            continue
        for tbl in sorted(set(re.findall(r"\{DS\}\.(\w+)", src)) & set(sizes)):
            better = [(tbl + s, sizes[tbl + s]) for s in SUCCESSOR
                      if tbl + s in sizes and sizes[tbl + s] > sizes.get(tbl, 0)]
            # only flag when the script does NOT already read the successor
            better = [(n, c) for n, c in better if f"{{DS}}.{n}" not in src]
            for name, cnt in better:
                add(rel, "READS_SUPERSEDED_TABLE",
                    f"reads {tbl} ({sizes.get(tbl,0):,} rows) but {name} ({cnt:,} rows) exists "
                    f"and is not read here — the surface may be a generation behind")
except Exception as e:
    print(f"  (warehouse unreachable, skipped: {str(e)[:60]})")

# ---------------------------------------------------------------------------------------------
# BOOT CHECK — the defect class this audit could not see, because it reads SOURCE, not RUNTIME.
#
# 2026-08-17: a data-driven expression was given to `line-dasharray`. MapLibre does not accept a
# data-driven value for that property, so it THREW during map construction. Every layer after the
# throw — including the parcels — was never added. The page served 200, every asset loaded, this
# audit reported zero findings, and the operator's report was "I can no longer see the parcels."
# Nothing in the source is syntactically wrong; the property simply cannot take that value.
#
# Two defences, because neither alone is enough:
#   1. STATIC (here): the paint properties MapLibre requires to be CONSTANT. If one of them is
#      handed an expression array — ["case"...], ["match"...], ["get"...] — flag it.
#   2. RUNTIME (app.js): `document.body.dataset.ready` is stamped only after the style loads and
#      every layer is added. If the boot throws, the attribute is absent. Check it in a browser:
#          await page.evaluate(() => document.body.dataset.ready)   // "1" == booted
#      A source-only audit can never prove a map booted; only the browser can.
CONSTANT_ONLY_PAINT = [
    "line-dasharray", "line-gradient", "fill-antialias", "fill-extrusion-pattern",
    "raster-fade-duration", "line-translate", "fill-translate", "icon-translate",
    "text-translate", "circle-translate", "background-pattern",
]
EXPR_HEADS = ("case", "match", "step", "interpolate", "get", "coalesce", "has", "to-number")
for rel in PAGES + SHARED_JS:
    src = read(rel)
    if not src:
        continue
    for prop in CONSTANT_ONLY_PAINT:
        # find `"line-dasharray":` and look at what follows, up to the next property or close
        for m in re.finditer(r'["\']' + re.escape(prop) + r'["\']\s*:\s*(.{0,120})', src, re.S):
            tail = m.group(1).lstrip()
            if not tail.startswith("["):
                continue
            inner = tail[1:].lstrip()
            if inner[:1] in ('"', "'") and any(
                    inner[1:].startswith(h) for h in EXPR_HEADS):
                add(rel, "CONSTANT_ONLY_PAINT_GIVEN_EXPRESSION",
                    f"'{prop}' is handed a data-driven expression. MapLibre requires a constant "
                    f"here and THROWS during map construction — every layer added after it, "
                    f"including the parcels, silently never appears")

if not any(re.search(r"dataset\.ready\s*=", read(f)) for f in SHARED_JS + ["app.js"]):
    add("app.js", "NO_BOOT_MARKER",
        "no `document.body.dataset.ready` is stamped after the map finishes booting, so no "
        "runtime check can distinguish 'booted' from 'threw halfway through addLayer'")

by_kind = defaultdict(list)
for f in findings:
    by_kind[f["kind"]].append(f)

SEVERE = {"JS_REFS_MISSING_ID", "CONST_REDECLARED", "PAYLOAD_MISSING", "PAYLOAD_UNREADABLE",
          "DUPLICATE_ID", "MISSING_PAGE", "READS_SUPERSEDED_TABLE",
          "CONSTANT_ONLY_PAINT_GIVEN_EXPRESSION"}
for kind in sorted(by_kind, key=lambda k: (k not in SEVERE, k)):
    mark = "!!" if kind in SEVERE else "  "
    print(f"\n{mark} {kind}  ({len(by_kind[kind])})")
    for f in by_kind[kind]:
        print(f"     {f['page']:16s} {f['detail']}")

severe = sum(len(v) for k, v in by_kind.items() if k in SEVERE)
print("\n" + "=" * 96)
print(f"{len(findings)} findings across {len(PAGES)} pages · {severe} would break a page or a panel")
if not findings:
    print("  no page references a missing element, no payload key is absent, no const is redeclared")
