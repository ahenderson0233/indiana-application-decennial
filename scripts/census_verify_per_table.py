"""ONE-BY-ONE Indiana verification of every state-keyed (class A+B) and county/geoid-keyed
(class D) table in energy.*: a real COUNT per table, batched by emitted SQL length (never a
guessed batch size). Results -> indiana_app._indiana_census + verified section in the docs."""
import re, datetime
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

tables = {r.table_id: r.row_count for r in client.query(
    "SELECT table_id, row_count FROM `energy-platfrom.energy.__TABLES__` WHERE row_count > 0")}
EXCLUDE = re.compile(r"__snapshot|__pre_|_pre_wire|_pre_fix|_pre_recon|__predelete|^orennia_|^be_ustest_|_vs_orennia|^_")
tables = {t: n for t, n in tables.items() if not EXCLUDE.search(t)}

STATE_COL = re.compile(r"(?:^|_)(state|st|src_state|state_abbr|state_code|state_usps|stusps|state_name)(?:$|_)")
CTY_COL = re.compile(r"(?:^|_)(county_fips|county_id_fips|cnty_fips|countyfips|block_geoid|geoid)(?:$|_)")
targets = {}
for r in client.query("""SELECT table_id, column_name, data_type FROM `energy-platfrom.energy.column_census`"""):
    if r.table_id not in tables or r.table_id in targets: continue
    cn = r.column_name.lower()
    if STATE_COL.search(cn):
        targets[r.table_id] = ("state", r.column_name)
for r in client.query("""SELECT table_id, column_name FROM `energy-platfrom.energy.column_census`"""):
    if r.table_id not in tables or r.table_id in targets: continue
    if CTY_COL.search(r.column_name.lower()):
        targets[r.table_id] = ("geoid", r.column_name)
print(f"verifiable per-table targets: {len(targets)}")

client.query(f"""CREATE TABLE IF NOT EXISTS `{DS}._indiana_census`
  (table_id STRING, method STRING, key_column STRING, in_rows INT64, total_rows INT64,
   measured_at TIMESTAMP)""").result()
done = {r.table_id for r in client.query(f"SELECT DISTINCT table_id FROM `{DS}._indiana_census`")}

parts, batch, size = [], [], 0
MAX_SQL = 700_000
def sel(t, mode, col):
    if mode == "state":
        pred = f"UPPER(CAST(`{col}` AS STRING)) IN ('IN','INDIANA','18')"
    else:
        pred = f"STARTS_WITH(CAST(`{col}` AS STRING), '18')"
    return (f"SELECT '{t}' AS table_id, '{mode}' AS method, '{col}' AS key_column, "
            f"COUNTIF({pred}) AS in_rows, COUNT(*) AS total_rows "
            f"FROM `energy-platfrom.energy.{t}`")
for t, (mode, col) in sorted(targets.items()):
    if t in done: continue
    s = sel(t, mode, col)
    if size + len(s) > MAX_SQL and batch:
        parts.append(batch); batch, size = [], 0
    batch.append(s); size += len(s)
if batch: parts.append(batch)
print(f"batches: {len(parts)}")

total_gb = 0.0
for i, b in enumerate(parts):
    sql = (f"INSERT `{DS}._indiana_census` (table_id, method, key_column, in_rows, total_rows, measured_at)\n"
           + "\nUNION ALL\n".join(b).replace("SELECT '", "SELECT CURRENT_TIMESTAMP() AS _x, '", 0))
    sql = (f"INSERT `{DS}._indiana_census`\n"
           f"SELECT table_id, method, key_column, in_rows, total_rows, CURRENT_TIMESTAMP() FROM (\n"
           + "\nUNION ALL\n".join(b) + "\n)")
    try:
        dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
        gb = dry.total_bytes_processed / 1e9
        client.query(sql).result()
        total_gb += gb
        print(f"batch {i+1}/{len(parts)} ok ({gb:.2f} GB, {len(b)} tables)", flush=True)
    except Exception as ex:
        print(f"batch {i+1} FAILED ({len(b)} tables): {str(ex)[:160]} - retrying per-table", flush=True)
        for s in b:
            try:
                client.query(f"INSERT `{DS}._indiana_census`\nSELECT *, CURRENT_TIMESTAMP() FROM (\n{s}\n)").result()
            except Exception as e2:
                tname = s.split("'")[1]
                client.query(f"""INSERT `{DS}._indiana_census` VALUES ('{tname}','ERROR','{str(e2)[:80].replace("'","")}',NULL,NULL,CURRENT_TIMESTAMP())""").result()

res = list(client.query(f"""
SELECT COUNTIF(in_rows > 0) AS with_indiana, COUNTIF(in_rows = 0) AS zero_indiana,
       COUNTIF(method='ERROR') AS errors, COUNT(*) AS measured
FROM `{DS}._indiana_census`"""))[0]
print(f"RESULT: {dict(res)} | scanned {total_gb:.1f} GB")
top = list(client.query(f"""SELECT table_id, in_rows, total_rows FROM `{DS}._indiana_census`
  WHERE in_rows > 0 ORDER BY in_rows DESC LIMIT 500"""))
with open(f"{REPO}\\docs\\BQ_INDIANA_CENSUS.md", "a", encoding="utf-8") as f:
    f.write(f"\n\n## VERIFIED per-table Indiana counts — measured {datetime.date.today()}\n\n")
    f.write(f"{res.measured} tables measured one-by-one: **{res.with_indiana} hold Indiana rows**, "
            f"{res.zero_indiana} measured zero, {res.errors} errored (named in `indiana_app._indiana_census`).\n\n")
    f.write("| table | IN rows | total |\n|---|---:|---:|\n")
    for r in top:
        f.write(f"| `{r.table_id}` | {r.in_rows:,} | {r.total_rows:,} |\n")
print("census doc appended")
print("PER-TABLE CENSUS COMPLETE")
