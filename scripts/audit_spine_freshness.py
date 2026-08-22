"""IS ANYTHING DOWNSTREAM OF THE SI SPINE OLDER THAN THE SPINE?

⛔ THE BUG THIS EXISTS FOR, 2026-08-22b. The standing rule reads *"After ANY build touching the
spine: re-export sites, the screener AND si surfaces."* I followed it exactly and still shipped a
stale number: **the screener export reported 23,821 signal-carrying parcels while the warehouse
held 24,654.**

⭐ THE RULE WAS INCOMPLETE, NOT DISOBEYED. `export_screener.py` does not read the spine — it reads
`in_screener_candidates`, which is a BUILD, not an export. Re-exporting without rebuilding ships
the previous generation's flags with a fresh timestamp on top. The registry row for that table has
said *"CADENCE: whenever ... in_si_sites_flags_v2 is rebuilt"* the whole time. **The rule was
written down and nothing enforced it, which is the same defect as an audit nobody dispatches.**

⚠ AND IT IS SILENT BY CONSTRUCTION. Every count still reconciles internally: the payload matches
in_screener_candidates, which matches the spine generation it was built from. Nothing is
inconsistent — it is just OLD, and "old" looks exactly like "correct" to every check that compares
a payload to the table it reads.

⭐ WHAT THIS ASSERTS: every table that READS the spine was built AFTER the spine's last build.
Derived from the loader sources on disk, not a hand-kept list — a pinned list of dependants is the
defect that made build_nfirs_structure_fires.py skip 2023 for a whole session.

RE-SCRAPE COMMAND: python scripts/audit_spine_freshness.py
⛔ READ-ONLY. Writes nothing.
"""
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "scripts")
client = bigquery.Client(project="energy-platfrom")

# the three tables build_si_signal_v2.py writes - the spine itself
SPINE = ("in_si_parcel_signals_v2", "in_si_sites_flags_v2", "in_si_signal_coverage")

# ⚠ a build writes a table; an export writes a file. Only builds can be compared by table time.
WRITE = re.compile(r"CREATE\s+OR\s+REPLACE\s+TABLE\s+`?\{?DS\}?[.`]*\.?(\w+)`?", re.I)


def modified(table):
    try:
        return client.get_table(f"{DS}.{table}").modified
    except Exception:
        return None


def main():
    print("=" * 100)
    print("SPINE FRESHNESS - is anything that READS the spine older than the spine?")
    print("=" * 100)

    spine_at = {t: modified(t) for t in SPINE}
    newest = max(v for v in spine_at.values() if v)
    for t, m in spine_at.items():
        print(f"  spine  {t:28} built {m:%Y-%m-%d %H:%M} UTC")
    print(f"  -> spine generation: {newest:%Y-%m-%d %H:%M} UTC\n")

    # which loaders read the spine, and what table does each of them WRITE?
    dependants = {}
    for fn in sorted(os.listdir(SCRIPTS)):
        if not fn.startswith("build_") or not fn.endswith(".py"):
            continue
        path = os.path.join(SCRIPTS, fn)
        src = io.open(path, encoding="utf-8", errors="replace").read()
        if not any(s in src for s in SPINE):
            continue
        if fn == "build_si_signal_v2.py":
            continue                       # it IS the spine
        for tbl in set(WRITE.findall(src)):
            if tbl not in SPINE:
                dependants.setdefault(tbl, fn)

    if not dependants:
        # ⛔ a zero here is a broken instrument, not a clean bill of health.
        raise SystemExit("⛔ found NO tables downstream of the spine - the source scan is broken, "
                         "not the warehouse. in_screener_candidates alone should appear.")

    fails, checked = [], 0
    print(f"  {len(dependants)} table(s) are built from something that reads the spine\n")
    print(f"  {'table':34} {'built':17} {'vs spine':>12}   builder")
    print("  " + "-" * 94)
    for tbl, fn in sorted(dependants.items()):
        m = modified(tbl)
        if m is None:
            print(f"  {tbl:34} {'(not built)':17} {'-':>12}   {fn}")
            continue
        checked += 1
        delta = (m - newest).total_seconds() / 60.0
        if delta < 0:
            fails.append(f"{tbl}: built {abs(delta):.0f} min BEFORE the spine - re-run {fn}")
            verdict = f"⛔ {abs(delta):.0f}m STALE"
        else:
            verdict = f"+{delta:.0f}m OK"
        print(f"  {tbl:34} {m:%m-%d %H:%M} UTC   {verdict:>12}   {fn}")

    print(f"\n  {checked} downstream table(s) compared against the spine")
    if fails:
        print(f"\n{len(fails)} FAILURE(S):")
        for f in fails:
            print(f"  ⛔ {f}")
        print("\n⚠ A stale downstream table is SILENT: its payload still matches it, so every "
              "\n  payload-vs-table check passes. Only this comparison can see it.")
        sys.exit(1)
    print("\n⭐ Everything downstream of the spine was built after it.")
    print("=" * 100)


if __name__ == "__main__":
    main()
