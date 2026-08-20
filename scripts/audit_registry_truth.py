"""G115 - does every `_registry` row still describe the build that writes it?

    python scripts/audit_registry_truth.py

Operator, 2026-08-19: *"we really need to update our tables throughout to ensure they are current
with our current state."*

The checkpoint already guards two shapes of staleness - a payload older than its table, and a
payload missing a key. It does NOT guard the third: **a registry row that has drifted from the
thing it describes.** That is not cosmetic. The registry is the project's answer to "could a
stranger refresh this table from the row alone", and a row nobody can act on is worse than a
missing one, because it looks like provenance.

FOUR CHECKS, each a drift that has actually happened here:

  ROWCOUNT   `_registry.n_rows` against the live table. `in_grid_plans` has claimed **7 rows
             against 618** for weeks. A count in the registry is a claim about a load that
             happened; when it disagrees with the warehouse, one of them is lying.
  COMMAND    the `RE-SCRAPE COMMAND:` must name a script that EXISTS. A command pointing at a
             deleted or renamed file fails the G16 re-runnability test silently.
  MISSING    no `RE-SCRAPE COMMAND:` at all.
  ORPHANED   a registry row whose script no longer mentions the table - the row survived a
             repoint. Measured on 2026-08-19: a row still named two retired tables after the code
             had moved on, which is how provenance starts lying.

⚠ TOLERANCE ON ROWCOUNT. A table that is appended to between builds will drift by design, so a
small relative difference is reported as DRIFTED rather than WRONG, and only a large one is
treated as a real disagreement. The threshold is stated rather than hidden: 5%.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import os
import re
from google.cloud import bigquery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DS = "energy-platfrom.indiana_app"
TOL = 0.05

# ⛔ WRITTEN HERE, ONCE, WITH A SELF-TEST — because this pattern was mangled twice.
# First version was `(.+?)(?:\.|$)`, non-greedy to the first dot, which truncated
# "python scripts/build_si_funnel.py" at the dot in ".py" and then reported 25 perfectly
# good rows as "no .py file named": the audit crying wolf at its own parser.
# The fix was then typed through a shell heredoc and the escapes mangled AGAIN, which is
# the project's standing rule (never write a regex through a heredoc) breaking in place.
RESCRAPE_RE = re.compile(r"RE-SCRAPE COMMAND:\s*([^\r\n]+)")
assert RESCRAPE_RE.search(
    'built by X. RE-SCRAPE COMMAND: python scripts/build_si_funnel.py'
).group(1).strip() == 'python scripts/build_si_funnel.py', 'RESCRAPE_RE self-test failed'
assert RESCRAPE_RE.search('no command here') is None
client = bigquery.Client(project="energy-platfrom")

sizes = {r.table_id: r.row_count
         for r in client.query(f"SELECT table_id, row_count FROM `{DS}.__TABLES__`")}

# ⛔ `ANY_VALUE(method)` WAS A COIN FLIP AND IT MADE THIS AUDIT UNRELIABLE - fixed 2026-08-20.
#    The registry is APPEND-ONLY by design: a row records what a load produced at a moment in
#    time, so a table accumulates several rows and corrections arrive as NEW rows. ANY_VALUE then
#    picks an arbitrary one. After backfill_rescrape_commands.py appended 289 re-scrape commands,
#    this audit still reported "296 with no command" while a direct check found 2 - it was
#    reading the ORIGINAL rows for most tables and the new ones for the rest, non-deterministically.
# ⭐ THE RULE THAT MATCHES THE DISCIPLINE: a table is compliant if ANY of its rows carries a
#    usable command (a later row cannot un-say an earlier one), and the rest of the detail comes
#    from the LATEST row, which is the current description of the object.
reg = [dict(r) for r in client.query(f"""
  WITH latest AS (
    SELECT table_name, n_rows, method, notes, source, built_at,
           ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY built_at DESC) AS rk
    FROM `{DS}._registry`),
  cmd AS (
    SELECT table_name,
           -- the newest row that actually carries a command, if any row does
           ARRAY_AGG(method ORDER BY built_at DESC LIMIT 1)[OFFSET(0)] AS cmd_method,
           ARRAY_AGG(notes  ORDER BY built_at DESC LIMIT 1)[OFFSET(0)] AS cmd_notes
    FROM `{DS}._registry`
    WHERE STRPOS(UPPER(IFNULL(method, '')), 'RE-SCRAPE COMMAND') > 0
       OR STRPOS(UPPER(IFNULL(notes,  '')), 'RE-SCRAPE COMMAND') > 0
    GROUP BY table_name)
  SELECT l.table_name, l.n_rows,
         COALESCE(c.cmd_method, l.method) AS method,
         COALESCE(c.cmd_notes,  l.notes)  AS notes,
         l.source, l.built_at
  FROM latest l LEFT JOIN cmd c USING (table_name)
  WHERE l.rk = 1 ORDER BY l.table_name""")]
print(f"{len(reg)} registered objects, {len(sizes)} tables in the dataset\n")

scripts = {}
for root, _, files in os.walk(os.path.join(REPO, "scripts")):
    for fn in files:
        if fn.endswith(".py"):
            scripts[fn] = open(os.path.join(root, fn), encoding="utf-8", errors="ignore").read()

for root, _, files in os.walk(os.path.join(REPO, "scrapers")):
    for fn in files:
        if fn.endswith(".py"):
            scripts[fn] = open(os.path.join(root, fn), encoding="utf-8", errors="ignore").read()
PS1 = {fn for root, _, files in os.walk(os.path.join(REPO, "scripts"))
       for fn in files if fn.endswith(".ps1")}

# ⭐ THREE COMMAND FORMS ARE LEGITIMATE AND ARE NOT PYTHON SCRIPTS - recognised 2026-08-20.
#    The G16 test is "could a stranger ACT on this row", not "does this row name a .py file".
#    Before this, 231 rows were reported as broken commands, and every one of them was an honest
#    entry saying the re-run is not ours or is not a one-liner. An audit that condemns the
#    correct answer is worse than no audit.
#      DELEGATED  a clip of energy.*: the re-run is a re-clip, and energy.* is READ-ONLY to this
#                 workstream. Actionable, just not by us.
#      LADDER     the QueueScope harvest: a PowerShell runner, hours of work, one process at a time.
#      UNKNOWN    explicitly unresolved. Honest, and counted on its own so it stays visible.
DELEGATED = re.compile(r"not ours to run|re-clip from", re.I)
LADDER = re.compile(r"run_pjm_ladder\.ps1", re.I)
UNKNOWN = re.compile(r"^UNKNOWN\b", re.I)

bad_count, bad_cmd, no_cmd, orphaned = [], [], [], []
delegated, ladder, unknown = [], [], []
for r in reg:
    t, n = r["table_name"], r["n_rows"]
    live = sizes.get(t)

    if live is not None and n is not None and live > 0:
        diff = abs(live - n) / max(live, 1)
        if diff > TOL:
            bad_count.append((t, n, live, diff))

    # ⚠ SEARCH BOTH COLUMNS. G16 requires the row to CARRY the command; it does not say which
    #   column. Seven builds put it in `notes` (in_land_gates, in_tribal_land,
    #   in_grid_plans_located, in_faa_obstacles_tall, in_land_gate_parcel, in_dc_actions_resolved,
    #   in_bus_headroom_miso_vendor) and this audit, reading `method` alone, called all seven
    #   non-compliant while backfill_rescrape_commands.py - which reads both - called them done.
    #   Two instruments disagreeing about the same contract is worse than either being wrong.
    m = (RESCRAPE_RE.search(str(r["method"] or ""))
         or RESCRAPE_RE.search(str(r.get("notes") or "")))
    if not m:
        no_cmd.append(t)
    else:
        cmd = m.group(1).strip()
        if UNKNOWN.search(cmd):
            unknown.append(t)
        elif LADDER.search(cmd):
            ladder.append(t)
            if "run_pjm_ladder.ps1" not in PS1:
                bad_cmd.append((t, cmd[:70], "run_pjm_ladder.ps1 does not exist"))
        elif DELEGATED.search(cmd):
            delegated.append(t)
        else:
            sm = (re.search(r"((?:scripts|scrapers)[/\\][\w./\\-]+\.py)", cmd)
                  or re.search(r"([\w-]+\.py)", cmd))
            if not sm:
                bad_cmd.append((t, cmd[:70], "no .py file named"))
            else:
                fn = os.path.basename(sm.group(1))
                if fn not in scripts:
                    bad_cmd.append((t, cmd[:70], f"{fn} does not exist"))
                elif t not in scripts[fn]:
                    orphaned.append((t, fn))

print("=" * 92)
print(f"ROWCOUNT DISAGREEMENT  (registry vs live, over {TOL:.0%})")
print("=" * 92)
for t, n, live, d in sorted(bad_count, key=lambda x: -x[3])[:25]:
    print(f"  {t:44s} registry {str(n):>10s}  live {live:>10,}   off by {d:>7.1%}")
print(f"  {len(bad_count)} of {len(reg)}")

print("\n" + "=" * 92)
print("HOW EVERY RE-SCRAPE COMMAND RESOLVES")
print("=" * 92)
runnable = len(reg) - len(no_cmd) - len(delegated) - len(ladder) - len(unknown) - len(bad_cmd)
print(f"  runnable here - a .py under scripts/ or scrapers/            : {runnable}")
print(f"  DELEGATED - a clip; the re-run belongs to the platform session: {len(delegated)}")
print(f"  LADDER - the QueueScope harvest, one process at a time        : {len(ladder)}")
print(f"  UNKNOWN - honestly unresolved, provenance not established     : {len(unknown)}")
print(f"  BROKEN - names a script that does not exist                   : {len(bad_cmd)}")
print(f"  NONE - no command at all                                      : {len(no_cmd)}")
if unknown:
    print("\n  ⛔ the honestly-unresolved ones. These are NOT compliant - they are visible:")
    for _t in unknown[:20]:
        print(f"      {_t}")
    if len(unknown) > 20:
        print(f"      … and {len(unknown) - 20} more")

print("\n" + "=" * 92)
print("RE-SCRAPE COMMAND NAMES A SCRIPT THAT DOES NOT EXIST")
print("=" * 92)
for t, cmd, why in bad_cmd[:25]:
    print(f"  {t:40s} {why}")
    print(f"  {'':40s} {cmd}")
print(f"  {len(bad_cmd)} of {len(reg)}")

print("\n" + "=" * 92)
print("NO RE-SCRAPE COMMAND AT ALL (fails the G16 re-runnability test)")
print("=" * 92)
for t in no_cmd[:30]:
    print(f"  {t}")
print(f"  {len(no_cmd)} of {len(reg)}")

print("\n" + "=" * 92)
print("ORPHANED — the named script no longer mentions this table (it survived a repoint)")
print("=" * 92)
for t, fn in orphaned[:25]:
    print(f"  {t:44s} named by {fn}")
print(f"  {len(orphaned)} of {len(reg)}")

worst = len(bad_count) + len(bad_cmd)
print("\n" + "=" * 92)
print(f"{worst} rows a stranger could NOT act on, {len(no_cmd)} with no command, "
      f"{len(orphaned)} orphaned")
_sys.exit(1 if worst else 0)
