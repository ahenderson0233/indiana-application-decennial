"""WIRING CENSUS — which registered objects actually reach a user-facing surface?

THE INSTRUMENT IS THE POINT. The first version of this measurement read "196 of 196 wired" because
it counted a table's OWN BUILD SCRIPT as a feature — every table is mentioned by the thing that
creates it, so everything scored. Truth was 139. This version separates the two roles:

  BUILDER   a file that CREATEs the object (`CREATE OR REPLACE TABLE|VIEW <name>`), or registers
            it. Being built is not being shown.
  CONSUMER  a file that READS the object on a path that ends at the user: an export script that
            writes into `data/`, or a page/JS file that names it.

An object reaches a surface only if it has at least one CONSUMER that is not also its builder.

Any headline of the form "N of N" is treated as suspect by construction: the count of registered
objects MOVES whenever a build registers something new, so a number carried over from a previous
session is stale the moment another table lands. It is recomputed here every run.
"""
import os, re, datetime
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

registered = [dict(r) for r in client.query(f"""
  SELECT table_name, ANY_VALUE(n_rows) n_rows, MAX(built_at) built_at
  FROM `{DS}._registry` GROUP BY table_name ORDER BY table_name""")]
print(f"registered objects in _registry: {len(registered)}")

# read every file once
files = {}
for sub in ("", "scripts", "scrapers"):
    root = os.path.join(REPO, sub) if sub else REPO
    if not os.path.isdir(root):
        continue
    for dirpath, _, names in os.walk(root):
        if any(x in dirpath for x in ("__pycache__", "_cache", ".git", "node_modules", "vendor")):
            continue
        for fn in names:
            if not fn.endswith((".py", ".js", ".html")):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, REPO).replace("\\", "/")
            if rel.startswith("data/"):
                continue
            try:
                files[rel] = open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                pass
print(f"source files scanned: {len(files)}")

# a file is an EXPORT path if it writes into data/, or is a page / front-end JS
def is_surface(rel, src):
    if rel.endswith((".html", ".js")):
        return True
    return bool(re.search(r'["\']data["\']\s*,|data[/\\\\][A-Za-z0-9_]+\.(json|geojson)', src))

# A surface can also enumerate a FAMILY dynamically instead of naming members. The Data page's
# join register does exactly that (`_registry WHERE STARTS_WITH(table_name,'vw_')`), so every
# vw_* view is rendered with its source, method and measured yield without ever being named in
# code. Missing this reported 9 live views as unwired — the instrument, not the tables.
dynamic_prefixes = set()
for rel, src in files.items():
    if "_registry" in src and is_surface(rel, src):
        for m in re.finditer(r"STARTS_WITH\(\s*table_name\s*,\s*['\"]([A-Za-z0-9_]+)['\"]", src):
            dynamic_prefixes.add((m.group(1), rel))
print(f"registry-driven family panels: {sorted(dynamic_prefixes) or 'none'}")

# ---------------------------------------------------------------------------------------------
# ⛔ 2026-08-20 INSTRUMENT FIX: the build detector could not see an f-string target, which is how
#    most build scripts in this repo are written:
#        OUT = f"{DS}.in_county_context_extras"
#        CREATE OR REPLACE TABLE `{OUT}` AS ...
#    The literal `CREATE ... TABLE `...in_county_context_extras`` never appears, so the file was
#    filed as a READER of its own output and as a builder of NOTHING. Consequence: the derivative
#    pass, which asks "does this file build something already reaching a surface", found no build
#    for such a file and every INPUT to it stayed unwired. in_acs_county, in_fema_nri_counties,
#    in_water_use and six more were reported unreached while their figures were on the county
#    panel. Resolve the variable first, then match.
VAR_TABLE = re.compile(r'^\s*([A-Za-z_]\w*)\s*=\s*f?["\'][^"\']*?\.([a-z_][a-z0-9_]*)["\']', re.M)
CREATE_VAR = re.compile(r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW)\s+`?\{(\w+)\}", re.I)
fstring_builds = {}          # rel -> set of table names this file creates via a variable
for rel, src in files.items():
    vt = {m.group(1): m.group(2) for m in VAR_TABLE.finditer(src)}
    got = {vt[v] for v in (m.group(1) for m in CREATE_VAR.finditer(src)) if v in vt}
    if got:
        fstring_builds[rel] = got
print(f"f-string CREATE targets resolved in {len(fstring_builds)} file(s)")

# pass 1: who builds what, who reads what
builds, reads = {}, {}
for r in registered:
    name = r["table_name"]
    pat = re.compile(re.escape(name) + r"\b")
    builds[name], reads[name] = [], []
    for rel, src in files.items():
        if not pat.search(src):
            continue
        if (re.search(r"CREATE\s+(OR\s+REPLACE\s+)?(TABLE|VIEW)\s+`?[^`\s]*" + re.escape(name),
                      src, re.I)
                or name in fstring_builds.get(rel, ())):
            builds[name].append(rel)
        else:
            reads[name].append(rel)

file_builds = {}
for name, bs in builds.items():
    for b in bs:
        file_builds.setdefault(b, []).append(name)

reg_names = [r["table_name"] for r in registered]
status = {}
for name in reg_names:
    direct = [f for f in reads[name] if is_surface(f, files[f])]
    if direct:
        status[name] = ("direct", direct)
        continue
    fam = [(p, f) for p, f in dynamic_prefixes if name.startswith(p)]
    if fam:
        status[name] = ("registry panel", [f"{f} (family `{p}*`)" for p, f in fam])

# pass 2: DERIVATIVE reach, to a fixpoint. A table that feeds a table the user sees is reached
# THROUGH it — that is how GAP_REGISTER already classifies these, so the census must agree.
for _ in range(6):
    changed = False
    for name in reg_names:
        if name in status:
            continue
        for f in reads[name]:
            for built in file_builds.get(f, []):
                if built != name and built in status:
                    status[name] = ("derivative", [f"feeds `{built}` via `{f}`"])
                    changed = True
                    break
            if name in status:
                break
    if not changed:
        break

# ---------------------------------------------------------------------------------------------
# pass 3: CO-BUILT reach — 2026-08-20, and this is an INSTRUMENT FIX, not a coverage change.
#
# ⛔ THE FALSE NEGATIVE. `in_faa_obstacles` (15,638 rows) has had its own checkbox on the map
#    console — "Tall obstructions >=200 ft (4,591)" — for days, and this census reported it as
#    reaching no surface. Cause: `build_land_gates.py` CREATEs `in_faa_obstacles` AND CREATEs
#    `in_land_gate_parcel` from it in the same file. Passes 1 and 2 only ever look at `reads`,
#    and a table consumed inside the very script that creates it has no `reads` entry at all. So
#    the object was invisible to every route, and G72 has been carrying it on the worklist as
#    unwired work that was already done.
#
# ⚠ THIS ROUTE IS WEAKER THAN THE OTHERS AND IS COUNTED SEPARATELY FOR THAT REASON. Two tables
#    built by one script are not necessarily related — a housekeeping script could build two
#    unrelated things and this would mark both reached. It is reported as its own category and
#    listed member by member below, so the headline can be read with it and without it. The
#    alternative — leaving it out — is worse: it sends sessions to re-wire layers already shipped.
for _ in range(6):
    changed = False
    for name in reg_names:
        if name in status:
            continue
        for f in builds[name]:
            sibling = [b for b in file_builds.get(f, []) if b != name and b in status]
            if sibling:
                status[name] = ("co-built", [f"built beside `{sibling[0]}` in `{f}`"])
                changed = True
                break
    if not changed:
        break
_cob = sorted(n for n in reg_names if status.get(n, ("",))[0] == "co-built")
print(f"co-built route (weaker — audit these by hand): {len(_cob)}")
for n in _cob:
    print(f"    {n:44s} {status[n][1][0]}")

rowsout, unwired = [], []
for r in registered:
    name = r["table_name"]
    how, via = status.get(name, (None, []))
    rowsout.append((name, how, via))
    if how is None:
        unwired.append((name, r["n_rows"], builds[name]))

n_ok = len(rowsout) - len(unwired)
from collections import Counter
print("reach by route: " + ", ".join(f"{k}={v}" for k, v in
      Counter(h for _, h, _ in rowsout if h).items()))
print(f"\nREACHING A SURFACE: {n_ok} of {len(registered)} "
      f"({100*n_ok/max(len(registered),1):.0f}%)")
print(f"NOT reaching a surface: {len(unwired)}\n")
for name, n, builders in unwired:
    b = builders[0] if builders else "(no builder found in repo)"
    print(f"  {name:44s} rows={str(n):>10s}  built by {b}")

doc = [f"# WIRING CENSUS — generated {datetime.date.today()}", "",
       "**GENERATED by `scripts/audit_wiring_census.py`.** Regenerate after any build that",
       "registers a new object — the denominator moves, so a carried-over \"N of N\" is stale.", "",
       "The instrument separates two roles, because the first version of this measurement read",
       "**196 of 196** by counting each table's own build script as a feature. Truth was 139.", "",
       "| role | test |", "|---|---|",
       "| **builder** | the file that `CREATE`s the object. Being built is not being shown |",
       "| **consumer** | a file that READS it on a path ending at the user — an export writing into `data/`, or a page/JS naming it |",
       "", f"## {n_ok} of {len(registered)} registered objects reach a surface", ""]
if unwired:
    doc += ["### Not reaching a surface", "",
            "| object | rows | built by |", "|---|---:|---|"]
    for name, n, builders in unwired:
        doc.append(f"| `{name}` | {n if n is not None else '—'} | "
                   f"`{builders[0] if builders else '—'}` |")
else:
    doc += ["**Every registered object reaches at least one surface.**", ""]
doc += ["", "Three routes count as reaching a surface, and each is reported separately so the",
        "headline can be audited rather than taken on trust:", "",
        "| route | meaning |", "|---|---|",
        "| **direct** | an export or page names the object |",
        "| **registry panel** | a purpose-built panel enumerates the whole family from `_registry` "
        "(the Data page's join register does this for `vw_*`, rendering source, method and measured yield) |",
        "| **derivative** | it feeds an object the user sees — how `GAP_REGISTER.md` already classifies these |",
        "", "### Every object and where it surfaces", "",
        "| object | route | via |", "|---|:---:|---|"]
for name, how, via in rowsout:
    doc.append(f"| `{name}` | {how or '**none**'} | "
               f"{', '.join(f'`{v}`' for v in via[:2]) if via else '—'} |")
open(f"{REPO}\\docs\\WIRING_CENSUS.md", "w", encoding="utf-8").write("\n".join(doc) + "\n")
print(f"\ndocs/WIRING_CENSUS.md written")
