"""G124: the RESCRAPE LEDGER. Which loaders can re-run, how often, safely - and what they drop.

Operator, 2026-08-20c: *"I would like to know exactly which loaders can be rerun to rescrape all
of our data and append it for new observations and which ones can't, and why. This is crucial
since our data is all static... Additionally, we scraped only partial data (only some columns) for
most datasets, and we want to ensure that EVERY column is grabbed upon rescrape."*

⭐ HALF THE FOUNDATION ALREADY EXISTED AND IS NOT REBUILT HERE. Every registered object carries a
`RE-SCRAPE COMMAND:`, and `audit_registry_truth.py` resolves each into runnable / delegated /
ladder / unresolved. This adds the three things that were missing.

  ① APPEND vs REPLACE. A command that CAN be re-run is not one that can be re-run SAFELY.
     Derived from the loader's own source: `CREATE OR REPLACE TABLE <this table>` is
     replace_safe; `INSERT INTO <this table>` or a WRITE_APPEND load job is append_only.
     ⚠ AND A THIRD STATE THAT MATTERS MORE THAN EITHER: `not_idempotent`, where the script READS
     the table it also REPLACES. That is not theoretical - `build_land_gates.py` measured
     `in_tribal_land.geom`, then replaced that table with the column renamed `geog`, so every run
     after the first died at step 1 with "Unrecognized name: geom". It had been unrunnable for a
     day and its registry row still advertised a command. Found 2026-08-20d only because G122
     forced a rebuild of everything downstream of in_screener_candidates.

  ② CADENCE. ⛔ `in_refresh_cadence` EXISTS (268 rows) AND IS NOT ENOUGH - measured, it derives a
     cadence for 16 and says "cannot derive - the source publishes no event date" for the other
     252. It is asking the DATA when the question is about the PUBLISHER. The Drought Monitor is
     weekly whether or not our copy carries a date column; USGS water use is a five-yearly survey;
     TIGER is annual. Cadence here is keyed off the publisher, and where the publisher is not
     identifiable it says so instead of guessing.

  ③ ⭐ FULL-COLUMN CAPTURE - the half the operator was right about and the most valuable.
     For every object whose registry names an `energy.*` parent, our column list is compared
     against the parent's and the difference is reported by NAME. `audit_schema_truncation.py`
     guards three known `[:N]` sites; this asks the question of every clip, which is the wider
     job G124 specified. The known instance: build_gas_facilities.py cut the parent schema at
     [:10] and was silently dropping operator, owner, status, county, ownerpct and reservname -
     a cut by POSITION keeps whatever the publisher happened to put first, which is not a
     decision anybody made.

⛔ GENERATED, NEVER HAND-TYPED. This is precisely the document that goes stale first - it
describes 300-plus moving objects - so it is rebuilt from the warehouse and the loader sources on
every run, and `audit_rescrape_ledger.py` fails the checkpoint if it drifts.

RE-SCRAPE COMMAND: python scripts/build_rescrape_ledger.py
⚠ IDEMPOTENT: replace_safe.
"""
import io
import os
import re
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
OUT_MD = os.path.join(REPO, "docs", "RESCRAPE_LEDGER.md")
OUT_TBL = f"{DS}.in_rescrape_ledger"

# ---------------------------------------------------------------------------------------------
# Patterns. ⛔ TYPED AT MODULE LEVEL WITH A SELF-TEST, NEVER THROUGH A SHELL HEREDOC. That escape
# has been eaten six times in this project; the sixth was inside an audit and left an
# unterminated string.
# ---------------------------------------------------------------------------------------------
RESCRAPE_RE = re.compile(r"RE-SCRAPE COMMAND:\s*([^\r\n]+)")
# ⚠ THE SUBDIRECTORY IS NOT OPTIONAL. The first version required the .py to sit directly under
# scripts/ or scrapers/, so every `python scrapers/lane_f/pull_dc_actions_county.py` failed to
# match and 38 genuinely runnable loaders were reported as "unresolved" - which disagreed with
# audit_registry_truth.py's 49 and would have been read as 38 unrunnable tables. Two instruments
# disagreeing about the same contract is worse than either being wrong.
SCRIPT_RE = re.compile(r"(?:scripts|scrapers)[/\\](?:[A-Za-z0-9_.\-]+[/\\])*([A-Za-z0-9_]+\.py)")
ENERGY_PARENT_RE = re.compile(r"energy\.([a-z0-9_]+)", re.I)
DECLARED_RE = re.compile(r"IDEMPOTEN[TC]\w*\s*:?\s*(replace_safe|append_only|not_idempotent)", re.I)

assert RESCRAPE_RE.search(
    "built by X. RE-SCRAPE COMMAND: python scripts/build_si_funnel.py"
).group(1).strip() == "python scripts/build_si_funnel.py", "RESCRAPE_RE self-test failed"
assert SCRIPT_RE.search("python scripts/build_gas_facilities.py").group(1) == \
    "build_gas_facilities.py", "SCRIPT_RE self-test failed"
assert SCRIPT_RE.search("python scrapers/lane_f/pull_dc_actions_county.py").group(1) == \
    "pull_dc_actions_county.py", "SCRIPT_RE must reach into a subdirectory"
assert ENERGY_PARENT_RE.findall("clip of energy.parcels_in x energy.roads_primary") == \
    ["parcels_in", "roads_primary"], "ENERGY_PARENT_RE self-test failed"
assert DECLARED_RE.search("⚠ IDEMPOTENT: replace_safe.").group(1) == "replace_safe", \
    "DECLARED_RE self-test failed"

# ---------------------------------------------------------------------------------------------
# CADENCE BY PUBLISHER. Keyed off the registry `source` text, because cadence is a property of
# who publishes, not of what our copy happens to contain. ⛔ Anything that matches nothing is
# reported as unknown rather than defaulted - a wrong schedule is worse than an absent one.
# ---------------------------------------------------------------------------------------------
CADENCE = [
    (r"drought\s*monitor",                    "weekly",      "USDM publishes every Thursday"),
    (r"\busgs\b.*water use|water use.*usgs",  "5-yearly",    "USGS water-use survey"),
    (r"tiger|census bureau",                  "annual",      "Census publishes a TIGER vintage a year"),
    (r"\bfrpp\b|federal real property",       "annual",      "GSA FRPP is an annual inventory"),
    (r"\bnfirs\b",                            "annual",      "NFIRS publishes a year at a time"),
    (r"\becho\b|\bepa\b|\bsdwis\b|\bghgrp\b", "quarterly",   "EPA refreshes ECHO/GHGRP quarterly"),
    (r"\beia\b",                              "monthly",     "EIA survey forms are monthly"),
    (r"queuescope|pjm queue|gis_queues|\bqueue\b",
                                              "monthly",     "the RTO queues are restated monthly"),
    (r"\bmiso\b|\bpjm\b|\brtep\b|\bmtep\b",   "quarterly",   "RTO planning cycles"),
    (r"ordinance|moratorium|council|commission|docket|legislat",
                                              "event-driven","changes at a single meeting - watch, do not schedule"),
    (r"\bwarn\b",                             "weekly",      "state WARN lists are posted as notices arrive"),
    (r"\bfema\b|flood",                       "as-revised",  "FEMA revises panels by map action, not on a clock"),
    (r"openstreetmap|\bosm\b",                "continuous",  "OSM is edited continuously; re-clip when it matters"),
    (r"tax sale|delinquen|foreclos|surplus",  "annual",      "county tax-sale cycles are annual"),
    (r"\bhifld\b|\bpad-us\b|padus",           "annual",      "HIFLD/PAD-US publish annual editions"),
    (r"\bfaa\b",                              "bi-monthly",  "FAA DOF is published on a 56-day cycle"),
    (r"tariff|urdb|rate schedule",            "as-filed",    "a rate case is filed, not scheduled"),
]

client = bigquery.Client(project="energy-platfrom")

# ---- loader sources on disk -------------------------------------------------------------------
sources = {}
for sub in ("scripts", "scrapers"):
    d = os.path.join(REPO, sub)
    if not os.path.isdir(d):
        continue
    for root, _, files in os.walk(d):
        for fn in files:
            if fn.endswith(".py"):
                sources[fn] = io.open(os.path.join(root, fn), encoding="utf-8",
                                      errors="ignore").read()
print(f"{len(sources)} loader sources on disk")

# ---- the registry, same append-only-aware rule audit_registry_truth.py uses --------------------
reg = [dict(r) for r in client.query(f"""
  WITH latest AS (
    SELECT table_name, n_rows, method, notes, source, built_at,
           ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY built_at DESC) AS rk
    FROM `{DS}._registry`),
  cmd AS (
    SELECT table_name,
           ARRAY_AGG(method ORDER BY built_at DESC LIMIT 1)[OFFSET(0)] AS cmd_method,
           ARRAY_AGG(notes  ORDER BY built_at DESC LIMIT 1)[OFFSET(0)] AS cmd_notes
    FROM `{DS}._registry`
    WHERE STRPOS(UPPER(IFNULL(method, '')), 'RE-SCRAPE COMMAND') > 0
       OR STRPOS(UPPER(IFNULL(notes,  '')), 'RE-SCRAPE COMMAND') > 0
    GROUP BY table_name)
  SELECT l.table_name, l.n_rows, l.source, l.built_at,
         COALESCE(c.cmd_method, l.method) AS method,
         COALESCE(c.cmd_notes,  l.notes)  AS notes
  FROM latest l LEFT JOIN cmd c USING (table_name)
  WHERE l.rk = 1 ORDER BY l.table_name""")]
print(f"{len(reg)} registered objects")

live = {r.table_id: r.row_count
        for r in client.query(f"SELECT table_id, row_count FROM `{DS}.__TABLES__`")}

# ---- every column of every table on both sides, in two queries rather than 600 get_table calls -
def schema_map(dataset):
    out = defaultdict(list)
    for r in client.query(f"""
      SELECT table_name, column_name, ordinal_position
      FROM `{dataset}`.INFORMATION_SCHEMA.COLUMNS ORDER BY table_name, ordinal_position"""):
        out[r.table_name].append(r.column_name)
    return out

ours = schema_map(DS)
parents = schema_map(EN)
print(f"schemas: {len(ours)} in indiana_app, {len(parents)} in energy")


def cadence_for(text):
    t = (text or "").lower()
    for pat, cad, why in CADENCE:
        if re.search(pat, t):
            return cad, why
    return "unknown", "no publisher recognised in the registry source"


# ⛔ SEVENTH OCCURRENCE OF THE HEREDOC/REGEX TRAP, 2026-08-20d, and it was mine. This line was
# first written through a shell heredoc and the `\n` inside the character class arrived as a
# LITERAL NEWLINE, leaving an unterminated string exactly as it did the previous six times. The
# rule is not "be careful with heredocs", it is "never write a regex through one" - type it with
# an editor, at module level, with a self-test underneath.
ASSIGN_RE = re.compile(r"^[ \t]*([A-Z_][A-Z0-9_]*)[ \t]*=[ \t]*f?[\"']([^\"'\r\n]+)[\"']", re.M)
CREATE_RE = re.compile(r"CREATE\s+OR\s+REPLACE\s+TABLE\s+`([^`]+)`", re.I)
INSERT_RE = re.compile(r"INSERT\s+INTO\s+`([^`]+)`", re.I)
FROM_RE = re.compile(r"FROM\s+`([^`]+)`", re.I)
BRACE_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
LOADJOB_RE = re.compile(r"load_table_from_(?:dataframe|json|file|uri)")

assert ASSIGN_RE.search('OUT = f"{DS}.in_roads_all"').group(1) == "OUT", "ASSIGN_RE self-test"
assert CREATE_RE.search("CREATE OR REPLACE TABLE `{OUT}` AS").group(1) == "{OUT}", "CREATE_RE self-test"
assert BRACE_RE.findall("{DS}.{TARGET}") == ["DS", "TARGET"], "BRACE_RE self-test"


def _expand(target, env, depth=0):
    """Resolve `{OUT}` / `{DS}.{TARGET}` through the script's own module-level assignments."""
    if depth > 4:
        return target
    out = target
    for v in BRACE_RE.findall(target):
        if v in env:
            out = out.replace("{" + v + "}", env[v])
    return _expand(out, env, depth + 1) if out != target else out


def _targets(src, pattern, env):
    return [_expand(m.group(1), env) for m in pattern.finditer(src)]


def idempotency_for(table, script_name):
    """Read the loader and decide how a re-run behaves. Returns (verdict, basis).

    ⛔ THE FIRST VERSION OF THIS FUNCTION WAS THE INSTRUMENT DEFECT THIS PROJECT KEEPS PAYING FOR.
    It matched `CREATE OR REPLACE TABLE <literal table name>` and reported `unknown` for 123 of
    336 objects - because almost nothing here writes a literal. Measured: 14 builds target
    `{OUT}`, six `{DS}.{dest}`, five `{DS}.{TARGET}`, and so on. The variable form IS the house
    style, and an audit that cannot read the house style is measuring its own blind spot.
    Targets are now resolved through the script's module-level assignments before matching.
    """
    src = sources.get(script_name or "")
    if src is None:
        return "unknown", "loader source not on disk"

    env = {k: v for k, v in ASSIGN_RE.findall(src)}
    creates = _targets(src, CREATE_RE, env)
    inserts = [x for x in _targets(src, INSERT_RE, env) if "_registry" not in x
               and "registry_sources" not in x]
    hit_create = [x for x in creates if x.endswith("." + table) or x == table]
    hit_insert = [x for x in inserts if x.endswith("." + table) or x == table]

    declared = DECLARED_RE.search(src)
    if declared:
        v, basis = declared.group(1).lower(), "declared by the loader itself"
    elif hit_insert:
        v, basis = "append_only", "the loader INSERTs into this table"
    elif "WRITE_APPEND" in src and not hit_create:
        v, basis = "append_only", "the loader loads with WRITE_APPEND"
    elif hit_create:
        v, basis = "replace_safe", "the loader CREATE OR REPLACEs this table"
    elif len(creates) == 1 and script_name:
        v, basis = "replace_safe", (f"the loader has one CREATE OR REPLACE target ({creates[0]}) "
                                    f"and the registry names it as this table's builder")
    elif LOADJOB_RE.search(src):
        # ⭐ A WHOLE CLASS THE DDL SCAN CANNOT SEE. 49 objects were reported `unknown` purely
        # because their loader is a SCRAPER that writes with client.load_table_from_dataframe()
        # rather than with SQL. The write DISPOSITION is the idempotency property, and it is
        # stated plainly in the job config, so read that instead of the DDL.
        # ⚠ Only when the loader uses ONE disposition - a script mixing both is genuinely
        # ambiguous about this table and stays unknown rather than being guessed at.
        trunc, app = "WRITE_TRUNCATE" in src, "WRITE_APPEND" in src
        if trunc and not app:
            v, basis = "replace_safe", "the loader load-jobs this data with WRITE_TRUNCATE"
        elif app and not trunc:
            v, basis = "append_only", "the loader load-jobs this data with WRITE_APPEND"
        elif trunc and app:
            return "unknown", ("the loader uses BOTH WRITE_TRUNCATE and WRITE_APPEND and no DDL "
                               "names this table, so which applies here is not determinable "
                               "from the source")
        else:
            return "unknown", ("the loader writes via a load job with no explicit disposition "
                               "(BigQuery defaults to WRITE_APPEND - verify before re-running)")
    else:
        return "unknown", "no write of this table found in the loader"

    # ⭐ POSITIONAL, not merely "does the name appear in a FROM". The dangerous shape is a read of
    # the table that happens BEFORE the write - that is what killed build_land_gates.py. A read
    # AFTER the write is the ordinary "measure what we just produced" pattern and is not a defect;
    # flagging it produced 57 findings, nearly all of them innocent, which is the crying-wolf
    # failure this project deleted rather than shipped once already.
    if v == "replace_safe":
        cm = next((m for m in CREATE_RE.finditer(src)
                   if _expand(m.group(1), env).endswith("." + table)), None)
        if cm:
            reads_before = [m for m in FROM_RE.finditer(src)
                            if m.start() < cm.start()
                            and _expand(m.group(1), env).endswith("." + table)]
            if reads_before:
                basis += ("; ⛔ it READS this table before it replaces it, so the second run sees "
                          "what the first wrote - verify before trusting the command")
    return v, basis


rows = []
for r in reg:
    t = r["table_name"]
    blob = f"{r['method'] or ''}\n{r['notes'] or ''}\n{r['source'] or ''}"
    m = RESCRAPE_RE.search(blob)
    cmd = m.group(1).strip() if m else None

    if cmd is None:
        resolution, script = "no_command", None
    elif re.match(r"^UNKNOWN\b", cmd, re.I):
        resolution, script = "unresolved", None
    elif re.search(r"run_pjm_ladder\.ps1", cmd, re.I):
        resolution, script = "ladder", None
    elif re.search(r"not ours to run|re-clip from", cmd, re.I):
        resolution, script = "delegated", None
    else:
        sm = SCRIPT_RE.search(cmd)
        script = sm.group(1) if sm else None
        resolution = "runnable_here" if script and script in sources else (
            "command_names_missing_script" if script else "unresolved")

    idem, idem_basis = idempotency_for(t, script)
    if resolution == "delegated":
        idem, idem_basis = "delegated", "a re-clip owned by the platform session"

    cad, cad_why = cadence_for(f"{r['source'] or ''} {r['method'] or ''}")
    if cad == "unknown" and resolution == "delegated":
        cad = "on the platform re-clip"
        cad_why = ("a clip of energy.*; it refreshes when the platform session re-clips, "
                   "not on a schedule of ours")

    # ---- column coverage against the energy parent ------------------------------------------
    named = [p for p in ENERGY_PARENT_RE.findall(r["source"] or "") if p in parents]
    our_cols = [c for c in ours.get(t, [])]
    dropped, parent_name, parent_n = [], None, None
    if named and our_cols:
        # the parent that shares the most columns with us is the one we clipped
        best = max(named, key=lambda p: len(set(parents[p]) & set(our_cols)))
        parent_name = best
        pcols = parents[best]
        parent_n = len(pcols)
        lower_ours = {c.lower() for c in our_cols}
        dropped = [c for c in pcols if c.lower() not in lower_ours]

    rows.append({
        "table_name": t,
        "n_rows": live.get(t, r["n_rows"]),
        "loader": script or (cmd[:120] if cmd else None),
        "resolution": resolution,
        "idempotency": idem,
        "idempotency_basis": idem_basis,
        "cadence": cad,
        "cadence_basis": cad_why,
        "last_built": r["built_at"].isoformat() if r["built_at"] else None,
        "parent": parent_name,
        "parent_columns": parent_n,
        "our_columns": len(our_cols) or None,
        "columns_dropped": len(dropped) if parent_name else None,
        "columns_dropped_names": ", ".join(dropped[:24]) if dropped else None,
    })

print(f"{len(rows)} ledger rows built")

# ---- load the table -----------------------------------------------------------------------
import pandas as pd

df = pd.DataFrame(rows)
client.load_table_from_dataframe(
    df, OUT_TBL,
    job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")).result()
print(f"  {OUT_TBL} written")


def tally(key):
    d = defaultdict(int)
    for x in rows:
        d[x[key]] += 1
    return dict(sorted(d.items(), key=lambda kv: -kv[1]))


res_t, idem_t, cad_t = tally("resolution"), tally("idempotency"), tally("cadence")
gap = [x for x in rows if (x["columns_dropped"] or 0) > 0]
gap.sort(key=lambda x: -x["columns_dropped"])
notidem = [x for x in rows if x["idempotency"] in ("not_idempotent", "unknown")]
# ⚠ MATCH THE WORDING THE DETECTOR ACTUALLY EMITS. This filter was still looking for an earlier
# phrasing and so reported 0 while the detector was correctly flagging in_tribal_land in the very
# same run - the instrument worked and the REPORT was blind, which is the harder version of the
# same mistake. Proven against the known build_land_gates.py case before being trusted.
risky = [x for x in rows if "READS this table before it replaces it" in (x["idempotency_basis"] or "")]
assert any(x["table_name"] == "in_tribal_land" for x in risky) or not any(
    x["table_name"] == "in_tribal_land" and x["idempotency"] == "replace_safe" for x in rows), \
    "the known read-before-write case must appear in `risky` or the filter is wrong again"

print("\n  resolution:", res_t)
print("  idempotency:", idem_t)
print("  cadence:", cad_t)
print(f"  objects dropping at least one parent column: {len(gap)}")
print(f"  objects that read their own output while replacing it: {len(risky)}")

# ---- the document ---------------------------------------------------------------------------
L = []
w = L.append
w("# RESCRAPE LEDGER — which loaders can re-run, how often, safely, and what they drop")
w("")
w("<!-- GENERATED by scripts/build_rescrape_ledger.py. ⛔ DO NOT HAND-EDIT — edit the generator.")
w("     This is the document that goes stale first: it describes 300+ moving objects. -->")
w("")
w(f"> **{len(rows)} registered objects.** Every figure below is read from the warehouse and from")
w("> the loader sources on disk at build time. Rebuild with `python scripts/build_rescrape_ledger.py`.")
w("")
w("## What the operator asked, and the four answers")
w("")
w("> *\"I would like to know exactly which loaders can be rerun to rescrape all of our data and")
w("> append it for new observations and which ones can't, and why… we scraped only partial data")
w("> (only some columns) for most datasets, and we want to ensure that EVERY column is grabbed")
w("> upon rescrape.\"*")
w("")
w("| question | answer |")
w("|---|---|")
w(f"| Which can I re-run here? | **{res_t.get('runnable_here', 0)}** name a script that exists on disk |")
w(f"| Which are somebody else's? | **{res_t.get('delegated', 0)}** are clips of `energy.*` — the re-run is a re-clip and `energy` is READ-ONLY to this workstream |")
w(f"| Which cannot be re-run at all? | **{res_t.get('unresolved', 0)}** honestly unresolved + **{res_t.get('no_command', 0)}** with no command + **{res_t.get('command_names_missing_script', 0)}** whose command names a script that is not on disk |")
w(f"| Which are unsafe to re-run? | **{len(risky)}** read their own output while replacing it — see §3 |")
w("")

w("## 1. APPEND vs REPLACE — can this be re-run *safely*?")
w("")
w("⛔ **A command that can be re-run is not the same as one that can be re-run safely.** Most")
w("builds here are `CREATE OR REPLACE TABLE`, which discards history — right for a clip, wrong")
w("for an observation series where the whole point is to accumulate.")
w("")
w("| verdict | n | what it means for a refresh |")
w("|---|---|---|")
w(f"| `replace_safe` | {idem_t.get('replace_safe', 0)} | rebuilds from source; re-running cannot double-count |")
w(f"| `append_only` | {idem_t.get('append_only', 0)} | ⚠ accumulates. Re-running **adds** rows — right for a series, a defect for a snapshot |")
w(f"| `delegated` | {idem_t.get('delegated', 0)} | a re-clip owned by the platform session |")
w(f"| `not_idempotent` | {idem_t.get('not_idempotent', 0)} | ⛔ do not re-run without reading the loader first |")
w(f"| `unknown` | {idem_t.get('unknown', 0)} | no write of this table found in the named loader |")
w("")
w("⚠ **The shape of the append defect, paid for on 2026-08-20b:** `build_gas_facilities.py`")
w("appended to a payload it did not own and took compressor features 24 → 48 and storage 22 → 44")
w("on one re-run. Valid GeoJSON, no error, every count overstated exactly 2×.")
w("")

w("## 2. CADENCE — how often is there anything new to get?")
w("")
w("⛔ **`in_refresh_cadence` exists and is not enough.** Measured: it derives a cadence for **16**")
w("of its 268 rows and answers *\"cannot derive — the source publishes no event date\"* for the")
w("other 252. It asks the DATA when the question is about the PUBLISHER. The Drought Monitor is")
w("weekly whether or not our copy carries a date column.")
w("")
w("| cadence | n |")
w("|---|---|")
for k, v in cad_t.items():
    w(f"| `{k}` | {v} |")
w("")
w("⚠ `unknown` is reported rather than defaulted. A wrong refresh schedule is worse than an")
w("absent one: it invites a re-run that costs money and returns the same rows.")
w("")

w("## 3. ⛔ LOADERS THAT READ THEIR OWN OUTPUT — re-run these only after reading them")
w("")
w("A build that SELECTs from the table it also replaces is not idempotent in practice, even")
w("though its write mode looks safe. **This is not theoretical.** `build_land_gates.py` measured")
w("`in_tribal_land.geom`, then replaced that table with the geometry column renamed `geog` — so")
w("every run after the first died with *\"Unrecognized name: geom\"*. It had been unrunnable for a")
w("day while its registry row advertised a working command. Fixed 2026-08-20d; found only because")
w("G122 forced a rebuild of everything downstream of `in_screener_candidates`.")
w("")
if risky:
    w("| object | loader |")
    w("|---|---|")
    for x in risky[:40]:
        w(f"| `{x['table_name']}` | `{x['loader']}` |")
else:
    w("*None detected in this run.*")
w("")

w("## 4. ⭐ FULL-COLUMN CAPTURE — what every clip is leaving behind")
w("")
w("The operator is right that we took partial slices. For every object whose registry names an")
w("`energy.*` parent, our column list is compared against the parent's.")
w("")
w("⚠ **A dropped column is not automatically a defect** — a clip that deliberately keeps five")
w("columns of a 200-column parent is a decision. What was never a decision is a cut by POSITION:")
w("`build_gas_facilities.py` sliced the parent schema at `[:10]` and silently dropped `operator`,")
w("`owner`, `status`, `county`, `ownerpct` and `reservname`, because a positional cut keeps")
w("whatever the publisher happened to put first.")
w("")
w(f"**{len(gap)} objects drop at least one parent column.** The 40 widest gaps:")
w("")
w("| object | parent | ours | parent | dropped | column names |")
w("|---|---|---:|---:|---:|---|")
for x in gap[:40]:
    names = (x["columns_dropped_names"] or "")[:150]
    w(f"| `{x['table_name']}` | `energy.{x['parent']}` | {x['our_columns']} | "
      f"{x['parent_columns']} | **{x['columns_dropped']}** | {names} |")
w("")

w("## 5. THE FULL LEDGER")
w("")
w("| object | rows | loader | re-run | idempotency | cadence | last built |")
w("|---|---:|---|---|---|---|---|")
for x in sorted(rows, key=lambda y: y["table_name"]):
    lb = (x["last_built"] or "")[:10]
    w(f"| `{x['table_name']}` | {x['n_rows'] or 0:,} | `{x['loader'] or '—'}` | "
      f"{x['resolution']} | {x['idempotency']} | {x['cadence']} | {lb} |")
w("")

io.open(OUT_MD, "w", encoding="utf-8").write("\n".join(L) + "\n")
print(f"  {OUT_MD} written ({len(L)} lines)")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_rescrape_ledger',
 'indiana_app._registry x indiana_app.INFORMATION_SCHEMA.COLUMNS x '
 'energy.INFORMATION_SCHEMA.COLUMNS x the loader sources on disk under scripts/ and scrapers/',
 'One row per registered object carrying its loader, whether the re-scrape command resolves, an '
 'APPEND-vs-REPLACE idempotency verdict read from the loader source, a cadence keyed off the '
 'PUBLISHER rather than off our copy event dates, and the column coverage of the clip against '
 'its energy.* parent by NAME. Generates docs/RESCRAPE_LEDGER.md in the same run. '
 'RE-SCRAPE COMMAND: python scripts/build_rescrape_ledger.py',
 {len(rows)}, 0.0, CURRENT_TIMESTAMP(),
 'G124. {len(gap)} objects drop at least one parent column; {len(risky)} loaders read their own '
 'output while replacing it. IDEMPOTENCY: replace_safe. CADENCE: every session - it describes '
 'moving objects and is the document that goes stale first.'
)""").result()
print("  _registry row written")
print("RESCRAPE LEDGER COMPLETE")
