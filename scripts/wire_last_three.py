"""Wire the last three registered objects that reached no surface.

Operator ruling 2026-08-16: *every* table and view gets at least one feature. Phase A closed at
196 of 199 with three written waivers; a waiver is a reason, not a surface, so these three now
get real panels on the Data page — built from what they actually hold.

  `_indiana_census` (773 rows)   the estate census: every warehouse table tested for Indiana
                                 rows, by what method and on which key column. 465 of 773 have
                                 NO Indiana rows — that is the useful half of the finding, and
                                 it is what stops a future session re-testing 465 dead ends.
  `in_fcc_bdc_mobile_summary_by_geography`     0 rows, EMPTY BY DEFECT
  `in_fcc_bdc_provider_summary_by_geography`   0 rows, EMPTY BY DEFECT
                                 Both were emptied by the `_st_pct` instrument bug: the clip's
                                 state-column regex matched PERCENTAGE columns
                                 (`mobilebb_4g_area_st_pct`, `res_st_pct`), so it filtered on the
                                 wrong field and wrote nothing. They are kept, not dropped,
                                 because a dropped table teaches nothing and the next census
                                 would rediscover the names as a gap.

The emptiness IS the content. The panel reads their LIVE row count rather than a hard-coded 0,
so if a future rebuild ever fixes the clip the panel changes by itself instead of lying.

Export-only: creates no BigQuery table, needs no `_registry` row. Read-only on the warehouse.
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
import json, gzip, os, datetime
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")


def rows(sql):
    return [dict(r) for r in client.query(sql)]


def live_count(t):
    """Read the CURRENT row count, never a remembered one."""
    return list(client.query(f"SELECT COUNT(*) n FROM `{DS}.{t}`"))[0].n


out = {"built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}

# ---- 1. the estate census -------------------------------------------------------------------
summary = rows(f"""
SELECT COUNT(*) tables_tested,
       COUNTIF(in_rows > 0) with_indiana_rows,
       COUNTIF(in_rows = 0) no_indiana_rows,
       SUM(in_rows) indiana_rows_found,
       SUM(total_rows) national_rows_scanned,
       MIN(measured_at) measured_at
FROM `{DS}._indiana_census`""")[0]
out["census_summary"] = summary

out["census_by_method"] = rows(f"""
SELECT method, COUNT(*) tables, COUNTIF(in_rows > 0) productive,
       SUM(in_rows) indiana_rows
FROM `{DS}._indiana_census` GROUP BY 1 ORDER BY tables DESC""")

# the key columns the census had to discover — a name is not the data, and `state` is not the
# only way a table says Indiana (owner_state and mail_state are OWNER addresses, not sites)
out["census_by_key"] = rows(f"""
SELECT key_column, COUNT(*) tables, COUNTIF(in_rows > 0) productive, SUM(in_rows) indiana_rows
FROM `{DS}._indiana_census` GROUP BY 1 ORDER BY tables DESC LIMIT 24""")

out["census_top"] = rows(f"""
SELECT table_id, method, key_column, in_rows, total_rows,
       ROUND(100 * SAFE_DIVIDE(in_rows, total_rows), 2) pct_indiana
FROM `{DS}._indiana_census` WHERE in_rows > 0
ORDER BY in_rows DESC LIMIT 60""")

# 465 dead ends, listed so nobody re-tests them
out["census_empty"] = rows(f"""
SELECT table_id, method, key_column, total_rows
FROM `{DS}._indiana_census` WHERE in_rows = 0 AND total_rows > 0
ORDER BY total_rows DESC LIMIT 80""")

# ---- 2. the two tables that are empty BY DEFECT ----------------------------------------------
EMPTY = [
 {"table": "in_fcc_bdc_mobile_summary_by_geography",
  "superseded_by": "in_fcc_bdc_mobile_summary",
  "defect": "the clip's state-column regex matched a PERCENTAGE column "
            "(`mobilebb_3g_area_st_pct`), so it filtered on the wrong field and wrote 0 rows",
  "holds": "mobile broadband coverage share by geography (3G/4G/5G area percentages)"},
 {"table": "in_fcc_bdc_provider_summary_by_geography",
  "superseded_by": "in_fcc_bdc_provider_summary",
  "defect": "the same `_st_pct` regex bug, here matching `res_st_pct`",
  "holds": "per-provider residential/business coverage share by geography"},
]
for e in EMPTY:
    e["rows_now"] = live_count(e["table"])
    e["superseding_rows_now"] = live_count(e["superseded_by"])
    reg = rows(f"""SELECT ANY_VALUE(source) source, ANY_VALUE(method) method, ANY_VALUE(notes) notes
                   FROM `{DS}._registry` WHERE table_name='{e['table']}'""")
    e["source"] = reg[0]["source"] if reg else None
    e["registry_note"] = reg[0]["notes"] if reg else None
    e["still_empty"] = e["rows_now"] == 0
out["empty_by_defect"] = EMPTY

# ---- write ----------------------------------------------------------------------------------
path = os.path.join(REPO, "data", "estate_census.json.gz")
with gzip.open(path, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(out, f, separators=(",", ":"), default=str)

print(f"data/estate_census.json.gz — {os.path.getsize(path)/1024:.0f} KB")
print(f"  census: {summary['tables_tested']} tables tested, "
      f"{summary['with_indiana_rows']} productive, {summary['no_indiana_rows']} dead ends, "
      f"{summary['indiana_rows_found']:,} Indiana rows found in "
      f"{summary['national_rows_scanned']:,} scanned")
for e in EMPTY:
    print(f"  {e['table']}: {e['rows_now']} rows "
          f"({'still empty by defect' if e['still_empty'] else 'NO LONGER EMPTY — panel updates itself'}) "
          f"· superseded by {e['superseded_by']} ({e['superseding_rows_now']:,})")
