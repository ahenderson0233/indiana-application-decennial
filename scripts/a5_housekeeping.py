"""A5 — the last of Phase A: no empty table and no unregistered table left in indiana_app.

Three items, each measured before acting:
  · in_fcc_bdc_mobile_summary_by_geography and in_fcc_bdc_provider_summary_by_geography hold
    ZERO rows. They are leftovers of the `_st_pct` instrument bug — a state-column regex matched
    percentage columns like `mobilebb_4g_area_st_pct`, so the clip filtered on the wrong field
    and wrote nothing. The corrected tables (in_fcc_bdc_mobile_summary 533,
    in_fcc_bdc_provider_summary 12,196) already exist and are wired.
  · `_indiana_census` exists but is UNREGISTERED, which trips the other session's checkpoint
    invariant 3.

Default is to REGISTER with an explanation rather than DROP: a dropped table teaches nothing,
and the next census would rediscover the same two names as a "gap". Pass --drop-empties to
remove them instead.
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
import sys
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")
DROP = "--drop-empties" in sys.argv

EMPTIES = {
  "in_fcc_bdc_mobile_summary_by_geography":
    "EMPTY BY DEFECT, superseded. The `_st_pct` instrument bug: a state-column regex matched "
    "percentage columns (mobilebb_4g_area_st_pct), so this clip filtered on the wrong field and "
    "wrote 0 rows. Superseded by in_fcc_bdc_mobile_summary (533), which is wired to the county "
    "broadband panel. Kept as the record of a caught bug.",
  "in_fcc_bdc_provider_summary_by_geography":
    "EMPTY BY DEFECT, superseded. Same `_st_pct` regex bug as the mobile summary above. "
    "Superseded by in_fcc_bdc_provider_summary (12,196). Kept as the record of a caught bug.",
}

for t, why in EMPTIES.items():
    n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.{t}`"))[0].n
    if n:
        print(f"  {t}: {n} rows — NOT empty after all, leaving alone"); continue
    if DROP:
        client.query(f"DROP TABLE `{DS}.{t}`").result()
        client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{t}'").result()
        print(f"  {t}: dropped (0 rows)")
    else:
        client.query(f"""UPDATE `{DS}._registry` SET notes=@o
                         WHERE table_name=@t""",
          job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("o", "STRING", why),
            bigquery.ScalarQueryParameter("t", "STRING", t)])).result()
        print(f"  {t}: 0 rows — kept, registry note explains why")

# _indiana_census: register it so the checkpoint invariant stops flagging it
cen = list(client.query(f"""
  SELECT COUNT(*) n FROM `{DS}.INFORMATION_SCHEMA.TABLES` WHERE table_name='_indiana_census'"""))[0].n
if cen:
    rows = list(client.query(f"SELECT COUNT(*) n FROM `{DS}._indiana_census`"))[0].n
    have = list(client.query(f"""
      SELECT COUNT(*) n FROM `{DS}._registry` WHERE table_name='_indiana_census'"""))[0].n
    if not have:
        client.query(f"""INSERT `{DS}._registry`
          (table_name, source, method, n_rows, gb_scanned, built_at, notes)
          VALUES ('_indiana_census','energy.INFORMATION_SCHEMA + per-table Indiana counts',
                  'estate census: every table classified and counted for Indiana rows',
                  {rows}, 0, CURRENT_TIMESTAMP(),
                  'Meta table, not a data feature: the census behind docs/BQ_INDIANA_CENSUS.md. '
                  'Registered so it stops tripping checkpoint invariant 3 as an unregistered '
                  'object; it is deliberately not rendered anywhere.')""").result()
        print(f"  _indiana_census: registered ({rows:,} rows, meta table)")
    else:
        print("  _indiana_census: already registered")

for r in client.query(f"""
    SELECT COUNT(*) tables FROM `{DS}.INFORMATION_SCHEMA.TABLES`"""):
    print(f"\nindiana_app now holds {r.tables} tables")
for r in client.query(f"""
    SELECT COUNT(DISTINCT table_name) registered FROM `{DS}._registry`"""):
    print(f"registry covers {r.registered} distinct tables")
