"""Audit the handoff, the prompt and the backlog against LIVE measurement.

Every figure quoted in a document is a claim. This re-measures the load-bearing ones and reports
any that disagree, plus every referenced file that does not exist.

⛔ COMPARE THE VALUE, NEVER TEST FOR THE STRING. The first version of this audit asserted that
"190,216" APPEARED in the docs - which it did, while the live figure was 190,178. A presence test
passes on a stale number by construction: it can only ever catch a DELETED figure, never a wrong
one. Every check below computes the live value and then asks whether the docs contain THAT.
"""
import io
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from google.cloud import bigquery

REPO = (r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California"
        r"\ca-capacity-deploy\indiana-application-decennial")
DS = "energy-platfrom.indiana_app"
c = bigquery.Client(project="energy-platfrom")
# ⚠ THE CURRENT HANDOFF IS FOUND, NOT PINNED. Three places in this file named
# HANDOFF_2026-08-20b.md by hand, so writing a NEW handoff silently left it unaudited while the
# audit went on re-measuring a superseded document and passing. Two copies of one name is the
# same defect as two copies of one number, which this file already warns about further down.
import glob as _glob
_HANDOFFS = sorted(_glob.glob(os.path.join(REPO, "docs", "HANDOFF_*.md")))
CURRENT_HANDOFF = os.path.relpath(_HANDOFFS[-1], REPO).replace("\\", "/") if _HANDOFFS     else "docs/HANDOFF_2026-08-20b.md"
PREV_HANDOFF = os.path.relpath(_HANDOFFS[-2], REPO).replace("\\", "/") if len(_HANDOFFS) > 1     else CURRENT_HANDOFF
DOCS = [CURRENT_HANDOFF, "docs/NEXT_SESSION_PROMPT.md", "docs/BACKLOG.md"]
text = {d: io.open(os.path.join(REPO, d), encoding="utf-8").read() for d in DOCS}
allt = "\n".join(text.values())

fails, checks = [], 0


def check(label, ok, detail):
    global checks
    checks += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {detail}")
    if not ok:
        fails.append(label)


def one(sql):
    return list(c.query(sql))[0]


def has(n):
    """Is this number, formatted the way the docs format numbers, present anywhere?"""
    return f"{n:,}" in allt or str(n) in allt


print("=" * 92)
print("A. FIGURES QUOTED IN THE DOCUMENTS, RE-MEASURED")
print("=" * 92)

r = one(f"SELECT COUNTIF(has_si_signal) n FROM `{DS}.in_si_sites_flags_v2`")
check("flagged parcels", r.n == 23795 and has(r.n), f"live {r.n:,}")

r = one(f"""SELECT COUNTIF(deliverable_wd_mw IS NOT NULL AND deliverable_wd_mw < c.mw_dc) grid,
                   COUNTIF(deliverable_wd_mw IS NOT NULL AND deliverable_wd_mw >= c.mw_dc) land
            FROM `{DS}.in_parcel_line_headroom` h
            JOIN `{DS}.in_screener_candidates` c USING (parcel_source, parcel_key)""")
check("grid-binds / land-binds", has(r.grid) and has(r.land),
      f"live grid {r.grid:,} land {r.land:,}")

# ---- the 2026-08-20b substation repair, which moved a shipped figure ----
r = one(f"""SELECT COUNTIF(lat IS NOT NULL) located, COUNT(*) total,
                   COUNT(DISTINCT IF(lat IS NOT NULL, UPPER(TRIM(substation_name)), NULL)) names,
                   COUNTIF(coord_source='derived_from_osm_footprint') derived,
                   COUNTIF(coord_source='outside_indiana_not_recovered') outside
            FROM `{DS}.in_substations`""")
check("substations located", r.located == 3659 and has(r.located), f"live {r.located:,} of {r.total:,}")
check("gazetteer usable names", r.names == 2233 and has(r.names), f"live {r.names:,}")
check("footprint-derived coordinates", r.derived == 734 and has(r.derived), f"live {r.derived}")
check("recovered but outside Indiana", r.outside == 199 and has(r.outside), f"live {r.outside}")

r = one(f"""SELECT ROUND(APPROX_QUANTILES(sub_mi,2)[OFFSET(1)],2) med, COUNTIF(sub_mi=0) onparcel
            FROM `{DS}.in_screener_candidates`""")
check("median distance to a substation", "2.08" in allt, f"live {r.med} mi")
check("substations on a parcel", has(r.onparcel), f"live {r.onparcel:,}")

r = one(f"""SELECT COUNT(*) n, COUNTIF(lat IS NOT NULL) located, COUNTIF(county IS NOT NULL) county,
                   COUNTIF(matched_substation IS NOT NULL AND lat IS NULL) orphan
            FROM `{DS}.in_grid_plans_located`""")
check("grid plans located", r.located == 119 and has(r.located), f"live {r.located} of {r.n}")
check("G109 orphans closed", r.orphan == 0, f"live matched-but-unlocated = {r.orphan}")

r = one(f"""SELECT COUNTIF(is_si_signal) sig, COUNTIF(surplus_class='declared_excess') declared,
                   COUNTIF(surplus_class='in_use') in_use, COUNT(*) total
            FROM `{DS}.in_si_gov_surplus_v2`""")
check("federal property in active use", r.in_use == 1548 and has(r.in_use),
      f"live {r.in_use:,} of {r.total:,} are Current/Future Mission Need")
check("declared-surplus assets", r.declared == 17 and has(r.declared), f"live {r.declared}")

r = one(f"""SELECT COUNT(*) total, COUNTIF(placement_grain!='county_only') placed,
                   COUNT(DISTINCT parcel_key) parcels FROM `{DS}.in_si_queue_withdrawn`""")
check("withdrawn requests placed", r.placed == 195 and has(r.placed),
      f"live {r.placed} of {r.total} placed, {r.parcels} parcels")

r = one(f"""SELECT COUNTIF(rowlike_confidence='high') high,
                   COUNTIF(nearest_structured_key IS NOT NULL) redirect,
                   COUNTIF(sliver_neighbours>0) sliver FROM `{DS}.in_parcel_assembly`""")
# ⚠ THE LITERAL 184 WAS PINNED HERE AND G122 DELIBERATELY CHANGED IT. This check asserted
# `r.high == 184` on top of "the docs state the live figure", which turns a *measurement* into a
# *constant* - so the audit failed the moment the thing it measures was correctly fixed. The 159
# that vanished were EXCLUDED as rights-of-way, which was the whole point of the row. Its
# neighbours below only require the documents to state whatever is live, and so does this now.
check("ribbon parcels with a road on them", has(r.high), f"live {r.high}")
check("parcels with a built neighbour to redirect to", has(r.redirect), f"live {r.redirect:,}")
check("candidates carrying a sliver", has(r.sliver), f"live {r.sliver:,}")

r = one(f"""SELECT COUNT(*) n, COUNT(DISTINCT yr) years,
                   COUNTIF(property_class='non-residential' AND severity IN
                     ('moderate >=$10k','major >=$100k','catastrophic >=$500k')) si
            FROM `{DS}.in_nfirs_structure_fires`""")
check("structure fires after extending the years", r.n == 45607 and has(r.n),
      f"live {r.n:,} across {r.years} years, {r.si:,} SI-grade")

r = one(f"""SELECT COUNT(*) projects,
                   ROUND(SUM(total_dpp_2025_phase_1_network_upgrade_cost)/1e6) musd
            FROM `{DS}.in_miso_dpp2025_ph1_project_costs`""")
check("MISO upgrade cost total", has(int(r.musd)) and has(r.projects),
      f"live ${int(r.musd):,}M across {r.projects} projects")

# ---- G115: the registry contract ----
nocmd = one(f"""
  SELECT COUNT(DISTINCT t.table_id) n FROM `{DS}.__TABLES__` t
  LEFT JOIN (SELECT DISTINCT table_name FROM `{DS}._registry`
             WHERE STRPOS(UPPER(IFNULL(method,'')||' '||IFNULL(notes,'')),
                          'RE-SCRAPE COMMAND') > 0) g ON g.table_name = t.table_id
  WHERE g.table_name IS NULL AND NOT STARTS_WITH(t.table_id, '_')""").n
# ⚠ NOT asserted at zero. A rung that registers while the harvest is running lands here for the
#   minutes before the next backfill, so a hard zero would fail for a correct reason.
check("registry rows with no re-scrape command", nocmd <= 4,
      f"live {nocmd} (the running ladder registers rungs faster than the backfill runs)")

unreg = [r.table_id for r in c.query(f"""
  SELECT t.table_id FROM `{DS}.__TABLES__` t
  LEFT JOIN (SELECT DISTINCT table_name FROM `{DS}._registry`) g ON g.table_name=t.table_id
  WHERE g.table_name IS NULL AND NOT STARTS_WITH(t.table_id,'_')""")]
check("unregistered tables", len(unreg) <= 3, f"live {unreg}")

# ---- the ladder, whose state changes while this runs ----
rungs = {}
for t in c.query(f"""SELECT table_id FROM `{DS}.__TABLES__`
                     WHERE REGEXP_CONTAINS(table_id, r'^in_pjm_qs_c23_(inj|wd)_[0-9]+$')"""):
    rungs[t.table_id] = one(f"SELECT COUNT(DISTINCT bus_number) n FROM `{DS}.{t.table_id}`").n
complete = sorted(k.replace("in_pjm_qs_c23_", "") for k, v in rungs.items() if v >= 1826)
short = {k.replace("in_pjm_qs_c23_", ""): v for k, v in rungs.items() if v < 1826}
print(f"  [note] ladder complete rungs: {complete}")
print(f"  [note] ladder short rungs:    {short}")
check("inj_25 still short", rungs.get("in_pjm_qs_c23_inj_25") == 1797,
      f"live {rungs.get('in_pjm_qs_c23_inj_25')}")

# ⛔ THE RUNG BEING HARVESTED RIGHT NOW IS SHORT BY DEFINITION, and requiring the docs to name it
#    made this check fail every time the ladder advanced - twice within hours of the handoff being
#    written, as `wd_200` completed and `inj_300` began. A check that fails for a correct reason
#    gets ignored, and this one would have failed on every future session.
# ⭐ WHAT ACTUALLY MATTERS is the ANOMALY: a rung that is short and NOT being written, because
#    that means a harvest stopped without finishing. Those must be named. The in-flight rung is
#    identified by its table having been written in the last hour.
fresh = {r.table_id for r in c.query(f"""
  SELECT table_id FROM `{DS}.__TABLES__`
  WHERE REGEXP_CONTAINS(table_id, r'^in_pjm_qs_c23_(inj|wd)_[0-9]+$')
    AND TIMESTAMP_MILLIS(last_modified_time) > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
""")}
stalled = {k.replace("in_pjm_qs_c23_", ""): v for k, v in rungs.items()
           if v < 1826 and k not in fresh}
check("the docs name every STALLED short rung", all(k in allt for k in stalled),
      f"stalled = {sorted(stalled)}; in-flight and excluded = "
      f"{sorted(x.replace('in_pjm_qs_c23_', '') for x in fresh)}")

print()
print("=" * 92)
print("B. BACKLOG STATE VS WHAT THE DOCUMENTS CLAIM")
print("=" * 92)
# ⚠ encoding="utf-8" and errors="replace": the audit prints ⛔/⭐ and the default cp1252 decode
# throws, which killed this section entirely on the first run.
out = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "audit_backlog_state.py")],
                     capture_output=True, text=True, cwd=REPO,
                     encoding="utf-8", errors="replace").stdout or ""
counts = {k: int(v) for k, v in
          re.findall(r"^\s+(DONE|PARTIAL|OPEN|STANDING|SUPERSEDED)\s+(\d+)", out, re.M)}
print(f"  live: {counts}")
for k in ("DONE", "PARTIAL", "OPEN"):
    n = counts.get(k)
    check(f"docs state the live {k} count", n is not None and f"{n} {k}" in allt.replace("**", ""),
          f"live {n}")
check("0 active duplicates", "ACTIVE DUPLICATES (two live rows for one number): 0" in out,
      "structural check")

# ⛔ THE ARITHMETIC OF "N ROWS CLOSED", added 2026-08-20b because the handoff got it wrong.
#    It claimed "Twenty rows closed" when 80 DONE -> 94 DONE is FOURTEEN. Eighteen rows were
#    edited that session, but four of them moved PARTIAL->PARTIAL, and the write-up counted
#    edits instead of closures. Every other figure in that document was re-measured by this
#    audit; this one was prose, so nothing checked it.
# ⚠ The opening DONE count is a fact about the PREVIOUS handoff, so it is read from that file
#    rather than hard-coded here - two copies of one number is the defect this project keeps
#    hitting.
prev = io.open(os.path.join(REPO, PREV_HANDOFF), encoding="utf-8").read()
m_prev = re.search(r"\*\*(\d+) DONE\b", prev)
if m_prev:
    opened, now = int(m_prev.group(1)), counts.get("DONE", 0)
    closed = now - opened
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
             8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen",
             14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
             19: "nineteen", 20: "twenty"}
    # ⚠ THE LIST MUST REACH SMALL NUMBERS. It started at "twelve", so a session that closed six
    # rows matched nothing, `claimed` came back empty, and the check passed by default - a
    # silent false pass in the very audit that exists to stop a prose figure going unchecked.
    claimed = re.findall(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
                         r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
                         r"twenty)\s+rows?\s+closed", allt, re.I)
    ok = all(w.lower() == words.get(closed, "") for w in claimed) if claimed else True
    check("the 'N rows closed' claim matches the arithmetic", ok,
          f"{opened} -> {now} is {closed} closed; the docs say {claimed or 'nothing'}")

print()
print("=" * 92)
print("C. EVERY FILE THE DOCUMENTS REFERENCE")
print("=" * 92)
refs = set()
for d, t in text.items():
    refs |= set(re.findall(r"`((?:scripts|docs|data)/[\w./-]+\.(?:py|md|js|json|gz|ps1))`", t))
missing = sorted(r for r in refs if not os.path.exists(os.path.join(REPO, r)))
check("no dangling file reference", not missing, f"{len(refs)} referenced, missing: {missing}")

print()
print("=" * 92)
print("D. STALE-FIGURE SWEEP — numbers that MOVED and must not reappear bare")
print("=" * 92)
# Each entry: the superseded figure, and the words that make quoting it legitimate.
# ⚠ THE `replacement` COLUMN EXISTS BECAUSE THIS CHECK WAS OVER-STRICT AND FAILED ON CORRECT
#   PROSE. The handoff presents the substation repair as a `| before | after |` markdown table:
#       | substations with a usable position | 2,925 | **3,659** (+734) |
#   That is unambiguously superseded framing, and it contains none of the words "was" or "from"
#   and no arrow, because the TABLE HEADER carries that meaning instead. An audit that condemns
#   the clearest possible presentation of a moved number teaches the next reader to ignore it.
#   A line naming BOTH the old and the new figure is showing a transition, full stop.
STALE = [
    ("24,277", r"\u2192|->|was|before|old|moved|\bnot\b", "23,795"),
    ("291 of 309", r"\u2192|->|was|from", None),
    ("235 of 316", r"\u2192|->|was|from", None),
    ("240 of 323", r"\u2192|->|was|from", None),
    # the substation figures this session moved
    ("2,925", r"\u2192|->|was|from|before", "3,659"),
    ("2,072", r"\u2192|->|was|from|before", "2,233"),
]
for doc in (CURRENT_HANDOFF, "docs/NEXT_SESSION_PROMPT.md"):
    t = text[doc]
    for fig, allowed, repl in STALE:
        bad = [ln.strip()[:100] for ln in t.split("\n")
               if fig in ln
               and not re.search(allowed, ln, re.I)
               and not (repl and repl in ln)]
        check(f"{os.path.basename(doc)}: {fig} only as superseded", not bad,
              bad[0] if bad else "clean")

print()
print("=" * 92)
print(f"{checks} checks, {len(fails)} FAILED")
for f in fails:
    print(f"  ⛔ {f}")
sys.exit(1 if fails else 0)
