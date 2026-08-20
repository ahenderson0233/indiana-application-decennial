"""Is docs/BACKLOG.md an accurate description of the application as it stands?

    python scripts/audit_backlog_state.py

⚠ THIS IS NOT `audit_backlog_truth.py`. That one probes the WAREHOUSE and the PAYLOADS to ask
whether an open item is secretly finished. This one reads the LEDGER ITSELF and asks whether it is
internally coherent - the failure mode where a row is worked, committed, and never marked, so the
next session re-opens finished work or trusts a status that is a day stale.

FOUR CHECKS, each earned:

  ACTIVE DUPLICATES  two rows for one G-number where NEITHER is marked superseded.
    ⛔ A ~~superseded~~ row is NOT a duplicate - it is the documented way this project retires a
    row while keeping its history, and an earlier version of this check reported G11 and G18 as
    drift when both were correctly annotated. An audit that cries wolf gets ignored.
  MISSING NUMBERS    a gap in G1..Gmax, which usually means a row was deleted rather than retired.
  UNCLASSIFIED       a status cell matching none of the known markers, so the row's state is
    whatever the reader guesses.
  DANGLING REFS      a row citing `scripts/x.py` or `docs/y.md` that does not exist.

It prints the OPEN and PARTIAL set last, because that is the list the next session actually works
from and it should be read in full rather than sampled.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import io
import os
import re
import collections

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "BACKLOG.md")
text = io.open(DOC, encoding="utf-8").read()
lines = text.split("\n")

ROW = re.compile(r"\|\s*\*\*(G\d+)\*\*\s*\|([^|]*)\|([^|]*)\|")
rows = collections.defaultdict(list)
for i, ln in enumerate(lines):
    m = ROW.match(ln)
    if m:
        rows[m.group(1)].append((i + 1, m.group(2).strip(), m.group(3).strip()))


def classify(status):
    """⛔ THE MARKER WINS, AND WORD MATCHING IS THE LAST RESORT. An earlier version tested for the
    word "OPEN" anywhere in the cell, and classified

        G28  🟢 THE OPEN HALF IS NOW WRITTEN — docs/BUILDABLE_AREA_BASIS.md

    as OPEN work. It says the opposite. A status cell is prose with a marker in front of it, so the
    marker is the signal and the prose is commentary; reading the prose first is how a finished
    item gets re-opened by the next session."""
    s = status.upper()
    if "~~" in status or "SUPERSEDED" in s:
        return "SUPERSEDED"
    for marker, kind in (("✅", "DONE"), ("🟢", "DONE"), ("📌", "STANDING"),
                         ("🟡", "PARTIAL"), ("🔴", "OPEN")):
        if marker in status:
            return kind
    # no marker at all - fall back to words, and only then
    if "DONE" in s or "FIXED" in s or "COMPLETE" in s:
        return "DONE"
    if "STANDING" in s:
        return "STANDING"
    if "OPEN" in s:
        return "OPEN"
    return "UNCLASSIFIED"


active = {}
dupes = []
for g, entries in rows.items():
    live = [(n, t, s) for (n, t, s) in entries if classify(s) != "SUPERSEDED"]
    if len(live) > 1:
        dupes.append((g, [n for n, _, _ in live]))
    if live:
        active[g] = live[0]
    else:
        active[g] = entries[0]

counts = collections.Counter(classify(s) for _, _, s in active.values())
nums = sorted(int(g[1:]) for g in active)
missing = sorted(set(range(1, max(nums) + 1)) - set(nums))

print("=" * 92)
print(f"BACKLOG STATE — {len(active)} G-rows (G1..G{max(nums)})")
print("=" * 92)
for k in ("DONE", "PARTIAL", "OPEN", "STANDING", "SUPERSEDED", "UNCLASSIFIED"):
    if counts.get(k):
        print(f"  {k:14s} {counts[k]:>4}")
print(f"  retired rows kept as history: {sum(len(v) for v in rows.values()) - len(active)}")

print(f"\nACTIVE DUPLICATES (two live rows for one number): {len(dupes)}")
for g, ns in dupes:
    print(f"  ⛔ {g} at lines {ns}")

print(f"\nMISSING NUMBERS: {missing or 'none'}")
for n in missing:
    inline = len(re.findall(rf"\bG{n}\b", text))
    print(f"  G{n}: referenced {inline}x in prose"
          + ("  (a standing rule stated in text, not a row)" if inline else "  ⛔ never mentioned"))

unc = [(g, a) for g, a in active.items() if classify(a[2]) == "UNCLASSIFIED"]
print(f"\nUNCLASSIFIED STATUS: {len(unc)}")
for g, (n, t, s) in unc:
    print(f"  ⛔ {g} line {n}: {s[:70]!r}")

refs = set(re.findall(r"`(scripts/[\w./-]+\.py|docs/[\w./-]+\.md)`", text))
missing_refs = sorted(r for r in refs if not os.path.exists(os.path.join(REPO, r)))
print(f"\nDANGLING FILE REFERENCES: {len(missing_refs)} of {len(refs)}")
for r in missing_refs:
    print(f"  ⛔ {r}")

print("\n" + "=" * 92)
print("THE WORK LIST — every OPEN and PARTIAL row, in full")
print("=" * 92)
for g in sorted(active, key=lambda x: int(x[1:])):
    n, t, s = active[g]
    k = classify(s)
    if k in ("OPEN", "PARTIAL"):
        clean = re.sub(r"[*_`⭐⛔⚠]", "", t).strip()
        print(f"  {k:8s} {g:6s} {clean[:78]}")

bad = len(dupes) + len(unc) + len(missing_refs)
print(f"\n{bad} structural problem(s)")
_sys.exit(1 if bad else 0)
