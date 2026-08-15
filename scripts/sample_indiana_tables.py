"""Small-sample every Indiana-positive table (operator directive: a name is not the data —
read a couple of rows of each to learn its format). Writes docs/SAMPLES_INDIANA.md.
Sampling is of the INDIANA slice (filtered on the measured key column), 3 rows per table,
values truncated. Machine time only; the next session opens with formats known."""
import datetime
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

targets = list(client.query(f"""
  SELECT table_id, method, key_column, in_rows, total_rows
  FROM `{DS}._indiana_census` WHERE in_rows > 0 ORDER BY in_rows DESC"""))
print(f"sampling {len(targets)} Indiana-positive tables")

out = [f"# Indiana-slice samples — generated {datetime.date.today()}",
  "", f"3-row samples of the INDIANA slice of all {len(targets)} verified tables.",
  "Values truncated to 48 chars. A sample shows FORMAT, not coverage — counts are in",
  "`indiana_app._indiana_census` and BQ_INDIANA_CENSUS.md.", ""]
for i, t in enumerate(targets):
    pred = (f"UPPER(CAST(`{t.key_column}` AS STRING)) IN ('IN','INDIANA','18')"
            if t.method == "state" else f"STARTS_WITH(CAST(`{t.key_column}` AS STRING), '18')")
    try:
        rows = list(client.query(
            f"SELECT * FROM `energy-platfrom.energy.{t.table_id}` WHERE {pred} LIMIT 3"))
        out.append(f"## `{t.table_id}` — IN {t.in_rows:,} of {t.total_rows:,} (key: {t.key_column})")
        if rows:
            cols = list(dict(rows[0]).keys())
            out.append("cols: " + ", ".join(cols[:30]) + ("…" if len(cols) > 30 else ""))
            for r in rows:
                vals = []
                for k, v in list(dict(r).items())[:14]:
                    s = str(v)
                    if len(s) > 48: s = s[:48] + "…"
                    vals.append(f"{k}={s}")
                out.append("  - " + " | ".join(vals))
        out.append("")
    except Exception as ex:
        out.append(f"## `{t.table_id}` — SAMPLE FAILED: {str(ex)[:120]}")
        out.append("")
    if (i + 1) % 25 == 0:
        print(f"  {i+1}/{len(targets)}", flush=True)
open(f"{REPO}\\docs\\SAMPLES_INDIANA.md", "w", encoding="utf-8").write("\n".join(out))
print("SAMPLES COMPLETE")
