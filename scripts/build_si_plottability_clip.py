"""Clip the one figure `export_spine.py` was still reading live from `energy`.

WHY THIS EXISTS. The checkpoint's energy-dependency check found exactly one leak: every other
export reads `indiana_app` alone, but `export_spine.py` ran a live COUNT against
`energy.mat_si_plottable` to report how many Indiana SI rows carry no geometry.

That single line meant **the app could not be rebuilt without the platform's dataset**. A build
script reading `energy` is fine and expected — that is how the clips are made. An EXPORT reading it
is not: exports are on the path to what the user sees.

So the count becomes a registered one-row clip in `indiana_app`, and the export reads that. Build
scripts may read `energy`; the app may not.

This is also the answer to "should we duplicate the ~140 energy tables?" — no. Clip the SLICE you
need, register it, and read the clip. `mat_si_plottable` is national; the Indiana answer is a
handful of numbers.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

client.query(f"""
CREATE OR REPLACE TABLE `{DS}.in_si_plottability` AS
SELECT geom_kind,
       COUNT(*) AS rows_,
       CURRENT_TIMESTAMP() AS built_at
FROM `energy-platfrom.energy.mat_si_plottable`
WHERE state = 'IN'
GROUP BY geom_kind
""").result()

rows = list(client.query(f"SELECT geom_kind, rows_ FROM `{DS}.in_si_plottability` ORDER BY rows_ DESC"))
total = sum(r.rows_ for r in rows)
unmapped = sum(r.rows_ for r in rows if r.geom_kind == "none")
print(f"in_si_plottability: {len(rows)} geometry kinds, {total:,} Indiana SI rows")
for r in rows:
    print(f"  {str(r.geom_kind):16s} {r.rows_:>10,}")
print(f"  -> unmapped (geom_kind='none'): {unmapped:,}")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_si_plottability'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
    f"VALUES (@t,@s,@m,@n,0.0,CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "in_si_plottability"),
        bigquery.ScalarQueryParameter("s", "STRING",
            "energy-platfrom.energy.mat_si_plottable WHERE state='IN' (READ-ONLY clip)"),
        bigquery.ScalarQueryParameter("m", "STRING",
            "Indiana slice of the national plottability table, aggregated to one row per "
            "geom_kind, so export_spine.py can read indiana_app instead of querying energy live."),
        bigquery.ScalarQueryParameter("n", "INT64", int(len(rows))),
        bigquery.ScalarQueryParameter("no", "STRING",
            "Built to close the ONE place an export still depended on the platform dataset. "
            "Build scripts may read energy; exports may not — an export is on the path to what "
            "the user sees, and the app must be rebuildable from indiana_app alone. "
            "Refresh this whenever the platform rebuilds mat_si_plottable.")])).result()
print("registered in_si_plottability")
