"""G115 - reconcile `_registry` row counts that have drifted from the live tables.

    python scripts/reconcile_registry_counts.py            # report only
    python scripts/reconcile_registry_counts.py --apply     # write the reconciliation rows

⛔ APPENDS, NEVER OVERWRITES. A registry row records what a LOAD produced at a moment in time, and
rewriting it destroys that. So a drift is corrected by appending a NEW row that states the live
count and says it is a reconciliation, leaving the original in place as history. Same discipline as
"archive, never delete".

⚠ A DRY RUN THAT WRITES IS WORSE THAN NO DRY RUN — a trap this project already hit on 2026-08-19,
when `apply_action_verification.py` ran its UPDATE unconditionally and gated only the registry
insert on `--apply`. Here NOTHING touches BigQuery without `--apply`, and the flag is checked once,
before any write, not inside the loop.

Found by `audit_registry_truth.py`, which was itself crying wolf until its parser was fixed: a
non-greedy regex truncated "python scripts/build_si_funnel.py" at the dot in ".py" and reported 25
sound rows as broken.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
TOL = 0.05
APPLY = "--apply" in _sys.argv
client = bigquery.Client(project="energy-platfrom")

sizes = {r.table_id: r.row_count
         for r in client.query(f"SELECT table_id, row_count FROM `{DS}.__TABLES__`")}
reg = [dict(r) for r in client.query(f"""
  SELECT table_name, ANY_VALUE(n_rows) n_rows, ANY_VALUE(source) source, ANY_VALUE(method) method
  FROM `{DS}._registry` GROUP BY table_name""")]

drift = []
for r in reg:
    live, n = sizes.get(r["table_name"]), r["n_rows"]
    if live is None or n is None or live == 0:
        continue
    if abs(live - n) / max(live, 1) > TOL:
        drift.append((r["table_name"], n, live, r["source"], r["method"]))

print(f"{len(drift)} registry rows disagree with the live table by more than {TOL:.0%}\n")
for t, n, live, _, _ in sorted(drift, key=lambda x: -abs(x[2] - x[1])):
    print(f"  {t:40s} registry {str(n):>9s} -> live {live:>9,}")

if not drift:
    print("\nnothing to reconcile")
    _sys.exit(0)

if not APPLY:
    print("\nDRY RUN — nothing written. Re-run with --apply to append the reconciliation rows.")
    _sys.exit(0)

rows = [{
    "table_name": t,
    "source": src,
    "method": (f"ROW-COUNT RECONCILIATION 2026-08-19b (G115). The prior registry row claimed "
               f"{n} rows; the live table holds {live}. The build itself was not changed by this "
               f"reconciliation and the earlier row is retained as history. "
               f"Original method: {str(meth or '')[:600]}"),
    "n_rows": live,
    "gb_scanned": 0.0,
    "notes": ("Appended by scripts/reconcile_registry_counts.py. This row corrects a COUNT only - "
              "it does not assert that the source or method were re-verified."),
} for t, n, live, src, meth in drift]

# ⚠ load_table_from_json with WRITE_APPEND, not a parameterised INSERT. An ArrayQueryParameter
# typed "STRUCT<...>" is rejected by the API ("is not a valid value"); the loader is also what the
# rest of this repo uses, so the append behaves the same way every other build's registry write does.
import datetime as _dt
_now = _dt.datetime.now(_dt.timezone.utc).isoformat()
for _r in rows:
    _r["built_at"] = _now
client.load_table_from_json(
    rows, f"{DS}._registry",
    job_config=bigquery.LoadJobConfig(write_disposition="WRITE_APPEND"),
).result()
print(f"\n{len(rows)} reconciliation rows appended")
print("RECONCILE COMPLETE")
