"""Complete-estate sampling: columns + 1-2 raw sample rows for EVERY populated table not
already sampled (spatial-only, national-grain, census-absent, and state-keyed zeros —
wonky formats mean a zero may hide Indiana under another spelling). TABLESAMPLE keeps the
geometry monsters from billing full scans; small tables fall back to LIMIT.
Output: docs/SAMPLES_ALL_PART2.md — the rest of the eyes-open corpus."""
import re, datetime
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

tables = {r.table_id: r.row_count for r in client.query(
    "SELECT table_id, row_count FROM `energy-platfrom.energy.__TABLES__` WHERE row_count > 0")}
EXCLUDE = re.compile(r"__snapshot|__pre_|_pre_wire|_pre_fix|_pre_recon|__predelete|^orennia_|^be_ustest_|_vs_orennia|^_")
tables = {t: n for t, n in tables.items() if not EXCLUDE.search(t)}
already = {r.table_id for r in client.query(
    f"SELECT DISTINCT table_id FROM `{DS}._indiana_census` WHERE in_rows > 0")}
todo = sorted((t for t in tables if t not in already), key=lambda t: -tables[t])
print(f"sampling {len(todo)} remaining tables (of {len(tables)} populated)")

def trunc(v, n=44):
    s = str(v)
    return s[:n] + "…" if len(s) > n else s

out = [f"# Complete-estate samples, part 2 — generated {datetime.date.today()}", "",
  f"Columns + raw sample rows for the {len(todo)} populated tables NOT in the Indiana-verified",
  "308 (spatial-only, national-grain, unkeyed, and state-keyed zeros whose formats may hide",
  "Indiana under another spelling). Geometry values truncated. TABLESAMPLE used on big",
  "tables so no monster billed a full scan.", ""]
done = 0
for t in todo:
    n = tables[t]
    try:
        tt = client.get_table(f"energy-platfrom.energy.{t}")
        cols = [f"{s.name}:{s.field_type}" for s in tt.schema]
        big = (tt.num_bytes or 0) > 200_000_000
        q = (f"SELECT * FROM `energy-platfrom.energy.{t}` TABLESAMPLE SYSTEM (0.05 PERCENT) LIMIT 2"
             if big else f"SELECT * FROM `energy-platfrom.energy.{t}` LIMIT 2")
        rows = list(client.query(q))
        if big and not rows:
            rows = list(client.query(f"SELECT * FROM `energy-platfrom.energy.{t}` TABLESAMPLE SYSTEM (1 PERCENT) LIMIT 2"))
        out.append(f"## `{t}` — {n:,} rows")
        out.append("cols: " + ", ".join(cols[:34]) + ("…" if len(cols) > 34 else ""))
        for r in rows:
            out.append("  - " + " | ".join(f"{k}={trunc(v)}" for k, v in list(dict(r).items())[:12]))
        if not rows: out.append("  - (sample returned no rows)")
        out.append("")
    except Exception as ex:
        out.append(f"## `{t}` — {n:,} rows — SAMPLE FAILED: {trunc(ex, 100)}")
        out.append("")
    done += 1
    if done % 50 == 0:
        print(f"  {done}/{len(todo)}", flush=True)
        open(f"{REPO}\\docs\\SAMPLES_ALL_PART2.md", "w", encoding="utf-8").write("\n".join(out))
open(f"{REPO}\\docs\\SAMPLES_ALL_PART2.md", "w", encoding="utf-8").write("\n".join(out))
print("SAMPLES PART2 COMPLETE")
