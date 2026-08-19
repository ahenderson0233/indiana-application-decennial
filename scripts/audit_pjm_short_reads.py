"""Find PJM buses whose harvest landed SHORT, and clear their checkpoint markers so they re-run.

    python scripts/audit_pjm_short_reads.py                 measure only
    python scripts/audit_pjm_short_reads.py --clear-markers also unmark the affected batches

⛔ THE DEFECT. `ingest/load_pjm_queuescope_bq.py` reads each bus's grid and, when it gets fewer
rows than the page itself reports, prints

    SHORT 05JEFRSO 765 kV (243208): read 188 of 594

and then loads the 188 rows anyway. The batch is marked `.done`, so a resume will NEVER come back
for the missing 406. The table looks complete and is not.

This is the ECHO defect exactly, already recorded in this repo's own history: *"a SILENT SHORT
PAGE: Adams returned 825 of 928 and it was accepted, so shortfall detection is required."* It is
required here too.

⛔ `ingest/` IS NOT EDITABLE by this workstream -- that is why the wrapper pattern exists. So this
does not fix the loader. It does the two things we can do from here: MEASURE which buses are
short, and DELETE their markers so the next run re-harvests them instead of skipping.

HOW A SHORT BUS IS IDENTIFIED WITHOUT THE LOG. The log only exists for runs we captured. The
durable signal is in the data: a bus harvested at one MW should return the SAME constraint-key set
as the same bus at any other MW -- proven on 4,673 of 4,673 keys, max delta 0.0. So a bus holding
materially fewer rows than the same bus in a known-good table is short. The 100 MW harvest
(`in_pjm_qs_c23sens_inj`, 1,826 of 1,826 buses, registered complete) is that reference.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import argparse
import os
import re
from google.cloud import bigquery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

CHECKS = [
    # (table under test, known-good reference, marker dir, mode, mw)
    ("in_pjm_qs_c23_inj_5000", "in_pjm_qs_c23sens_inj",
     "_ckpt_pjm_qs_case23_injection", "INJECTION", 5000),
    ("in_pjm_qs_c23_wd_5000", "in_pjm_qs_c23sens_wd",
     "_ckpt_pjm_qs_case23_withdrawal", "WITHDRAWAL", 5000),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clear-markers", action="store_true")
    a = ap.parse_args()

    for table, ref, ckpt, mode, mw in CHECKS:
        print(f"\n{'=' * 88}\n{table}  vs the complete {ref}\n{'=' * 88}")
        try:
            rows = list(client.query(f"""
              WITH t AS (SELECT bus_label, COUNT(*) n FROM `{DS}.{table}` GROUP BY 1),
                   r AS (SELECT bus_label, COUNT(*) n FROM `{DS}.{ref}`   GROUP BY 1)
              SELECT t.bus_label, t.n AS got, r.n AS want
              FROM t JOIN r USING (bus_label)
              WHERE t.n < r.n
              ORDER BY (r.n - t.n) DESC"""))
        except Exception as e:
            print(f"  probe failed: {e}")
            continue

        tot = list(client.query(f"""
          SELECT COUNT(DISTINCT bus_label) buses, COUNT(*) rows_
          FROM `{DS}.{table}`"""))[0]
        if not rows:
            print(f"  CLEAN - {tot.buses:,} buses, {tot.rows_:,} rows, none short of the reference")
            continue

        got = sum(r.got for r in rows)
        want = sum(r.want for r in rows)
        print(f"  ⛔ {len(rows):,} of {tot.buses:,} harvested buses are SHORT")
        print(f"     {got:,} of {want:,} rows captured on those buses "
              f"({100 * got / want:.1f}%) - {want - got:,} rows missing")
        print(f"     worst: " + ", ".join(f"{r.bus_label} {r.got}/{r.want}" for r in rows[:4]))

        if not a.clear_markers:
            print("     (re-run with --clear-markers to unmark these batches so they re-harvest)")
            continue

        # A marker covers a BATCH of ~25 buses and the file name carries only the batch index, not
        # the buses in it. We cannot map bus -> batch from disk, so the honest move is to unmark
        # every batch at or after the FIRST short one is impossible to identify either... therefore
        # unmark ALL markers for this rung. Re-harvesting a clean batch costs time; keeping a short
        # one costs correctness, and only one of those is recoverable later.
        d = os.path.join(REPO, "data", ckpt)
        pat = re.compile(rf"^23__{mode}__{mw}__1568__\d+\.done$")
        hit = [f for f in os.listdir(d) if pat.match(f)] if os.path.isdir(d) else []
        arch = os.path.join(REPO, "data", f"_SHORT_ARCHIVED_{ckpt}_{mode}_{mw}")
        os.makedirs(arch, exist_ok=True)
        for f in hit:
            os.replace(os.path.join(d, f), os.path.join(arch, f))   # ARCHIVE, never delete
        print(f"     archived {len(hit)} marker(s) to data/{os.path.basename(arch)}/ "
              f"- the next run re-harvests this rung from the start")
        print("     ⚠ rows already loaded are replaced per batch by the loader's own "
              "DELETE-then-append, so re-running repairs rather than duplicates")


if __name__ == "__main__":
    main()
