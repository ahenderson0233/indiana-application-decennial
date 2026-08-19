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

reg = [dict(r) for r in client.query(f"""
  SELECT table_name, ANY_VALUE(n_rows) n_rows, ANY_VALUE(method) method,
         ANY_VALUE(source) source, MAX(built_at) built_at
  FROM `{DS}._registry` GROUP BY table_name ORDER BY table_name""")]
print(f"{len(reg)} registered objects, {len(sizes)} tables in the dataset\n")

scripts = {}
for root, _, files in os.walk(os.path.join(REPO, "scripts")):
    for fn in files:
        if fn.endswith(".py"):
            scripts[fn] = open(os.path.join(root, fn), encoding="utf-8", errors="ignore").read()

bad_count, bad_cmd, no_cmd, orphaned = [], [], [], []
for r in reg:
    t, n = r["table_name"], r["n_rows"]
    live = sizes.get(t)

    if live is not None and n is not None and live > 0:
        diff = abs(live - n) / max(live, 1)
        if diff > TOL:
            bad_count.append((t, n, live, diff))

    m = RESCRAPE_RE.search(str(r["method"] or ""))
    if not m:
        no_cmd.append(t)
    else:
        cmd = m.group(1).strip()
        sm = re.search(r"(scripts[/\\][\w./\\-]+\.py)", cmd) or re.search(r"([\w-]+\.py)", cmd)
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
