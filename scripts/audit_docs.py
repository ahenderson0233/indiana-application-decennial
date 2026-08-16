"""Audit the documentation itself: is any of it stale, and does any of it state a figure that
the warehouse now contradicts?

A stale doc is worse than a missing one, because the next session TRUSTS it. This project has
already shipped "199 of 199 objects wired" into a handoff and had it be wrong within the hour.
So: which docs are GENERATED (and therefore self-correcting), which are hand-written (and
therefore at risk), and which contain a number the estate no longer agrees with.
"""
# stdout must survive its own output: this console is cp1252 and characters like U+2248/U+2192/U+2717 raise
# UnicodeEncodeError from print() itself. The honesty audit once crashed on its own
# FAILURE path for exactly this reason. Degrade the glyph, never the run.
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import os, re, glob, datetime, subprocess
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")


def q1(sql): return list(client.query(sql))[0]


GENERATED = {  # doc -> the script that regenerates it
    "CODE_CATALOG.md": "scripts/build_code_catalog.py",
    "SI_COVERAGE.md": "scripts/build_si_coverage_doc.py",
    "WIRING_CENSUS.md": "scripts/audit_wiring_census.py",
    "NATIONAL_HANDOVER.md": "scripts/build_handover_pack.py",
    "PLOTTABILITY.md": "scripts/audit_plottability.py",
    "HONESTY_AUDIT.json": "scripts/audit_honesty.py",
    "ACCEPTANCE_RUN.json": "scripts/acceptance_run.py",
}

# the live figures a doc might contradict
live = {
    "registered objects": q1(f"SELECT COUNT(DISTINCT table_name) n FROM `{DS}._registry`").n,
    "flagged parcels": q1(f"SELECT COUNTIF(has_si_signal) n FROM `{DS}.in_si_sites_flags_v2`").n,
}
print("LIVE FIGURES: " + " · ".join(f"{k}={v:,}" for k, v in live.items()))

# figures that were TRUE EARLIER TODAY and are now wrong — a doc still asserting one is stale
SUPERSEDED = {
    "199 of 199": "wiring; the denominator has moved to 252",
    "196 of 199": "wiring; superseded",
    "226 of 226": "wiring; superseded",
    "242 of 242": "wiring; superseded — re-run the census",
    "8,422": "SI flag; superseded by 23,140",
    "9,383": "SI flag; superseded by 23,140",
    "9,990": "SI flag; superseded by 23,140",
    "11,117": "SI flag; superseded by 23,140",
    "847,410 parcels of which": "the OLD flag — fine as history, wrong as current state",
}

print(f"\n{'doc':38s} {'kind':10s} {'lines':>6s}  status")
print("-" * 92)
rows = []
for p in sorted(glob.glob(os.path.join(REPO, "docs", "*.md")) +
                glob.glob(os.path.join(REPO, "docs", "*.json")) +
                glob.glob(os.path.join(REPO, "scrapers", "lane_*", "*.md"))):
    rel = os.path.relpath(p, REPO).replace("\\", "/")
    base = os.path.basename(p)
    txt = open(p, encoding="utf-8", errors="ignore").read()
    kind = "GENERATED" if base in GENERATED else "hand-written"
    hits = [f"{k} ({why})" for k, why in SUPERSEDED.items()
            if k in txt and "superseded" not in txt[max(0, txt.find(k)-160):txt.find(k)].lower()]
    mtime = datetime.date.fromtimestamp(os.path.getmtime(p))
    status = "ok"
    if kind == "GENERATED":
        status = f"regenerate: {GENERATED[base]}"
    elif hits:
        status = "⚠ STALE FIGURE: " + "; ".join(h[:52] for h in hits[:2])
    rows.append((rel, kind, txt.count("\n"), mtime, status))
    print(f"{rel[:38]:38s} {kind:10s} {txt.count(chr(10)):>6,}  {mtime}  {status[:60]}")

stale = [r for r in rows if r[4].startswith("⚠")]
print(f"\n{len(rows)} documents · {sum(1 for r in rows if r[1]=='GENERATED')} generated "
      f"(self-correcting) · {len(stale)} carrying a superseded figure")
for r in stale:
    print(f"  ⚠ {r[0]}: {r[4]}")
if not stale:
    print("  no hand-written doc asserts a figure the estate now contradicts")
