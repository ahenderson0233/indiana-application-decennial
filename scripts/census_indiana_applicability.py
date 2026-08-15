"""Full-estate Indiana-applicability census: classify EVERY populated energy.* table by
HOW its Indiana slice is reachable. Metadata-only (column_census + __TABLES__), ~pennies.
Writes docs/BQ_INDIANA_CENSUS.md — the named list of what we hold and aren't yet using."""
import re, datetime
from collections import defaultdict
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
c = bigquery.Client(project="energy-platfrom")

tables = {r.table_id: r.row_count for r in c.query(
    "SELECT table_id, row_count FROM `energy-platfrom.energy.__TABLES__` WHERE row_count > 0")}
EXCLUDE = re.compile(r"__snapshot|__pre_|_pre_wire|_pre_fix|_pre_recon|__predelete|^orennia_|^be_ustest_|_vs_orennia|^_")
tables = {t: n for t, n in tables.items() if not EXCLUDE.search(t)}
print(f"populated, non-backup, non-licensed tables: {len(tables)}")

cols = defaultdict(list)
for r in c.query("""SELECT table_id, column_name, n_distinct,
      (SELECT STRING_AGG(v, '|' ORDER BY n DESC LIMIT 60) FROM UNNEST(top_values)) AS vals
    FROM `energy-platfrom.energy.column_census`"""):
    cols[r.table_id].append((r.column_name.lower(), r.n_distinct or 0, r.vals or ""))

IN_VAL = re.compile(r"(?:^|\|)(IN|in|Indiana|INDIANA|18)(?:\||$)")
ISO_VAL = re.compile(r"(?:^|\|)(MISO|PJM|miso|pjm)(?:\||$)")
STATE_COL = re.compile(r"(?:^|_)(state|st|src_state|state_abbr|state_code|state_usps|stusps|state_name)(?:$|_)")
CTY_COL = re.compile(r"(?:^|_)(county_fips|fips|geoid|county_id_fips|cnty_fips|countyfips|block_geoid|tract)(?:$|_)")
ISO_COL = re.compile(r"(?:^|_)(iso|rto|region|balancing|ba|market)(?:$|_)")
GEO_COL = re.compile(r"geog|geom|geometry|latitude|longitude|(?:^|_)lat(?:$|_)|(?:^|_)lon(?:$|_)|shape")

cls = defaultdict(list)
for t, n in sorted(tables.items(), key=lambda kv: -kv[1]):
    cc = cols.get(t, [])
    state_in = any(STATE_COL.search(cn) and IN_VAL.search(v) for cn, _, v in cc)
    state_col = any(STATE_COL.search(cn) for cn, _, v in cc)
    cty = any(CTY_COL.search(cn) for cn, _, _ in cc)
    iso_in = any(ISO_COL.search(cn) and ISO_VAL.search(v) for cn, _, v in cc)
    geo = any(GEO_COL.search(cn) for cn, _, _ in cc)
    if state_in: cls["A_state_keyed_holds_IN"].append((t, n))
    elif state_col: cls["B_state_keyed_IN_unverified_by_census"].append((t, n))
    elif iso_in: cls["C_iso_rto_keyed_MISO_or_PJM"].append((t, n))
    elif cty: cls["D_county_or_geoid_keyed"].append((t, n))
    elif geo: cls["E_spatial_only"].append((t, n))
    elif not cc: cls["G_not_in_column_census"].append((t, n))
    else: cls["F_national_or_other_grain"].append((t, n))

lines = [f"# BigQuery Indiana-applicability census — generated {datetime.date.today()}",
  "", "Method: metadata classification of every populated, non-backup, non-licensed `energy.*`",
  "table by how its Indiana slice is reachable. Classes A-E are directly filterable;",
  "F holds national/series grain applicable AT Indiana (prices, ISO series, weather);",
  "G needs a schema read. **A name is never trusted — wiring requires a value-read per table.**", ""]
for k in sorted(cls):
    lst = cls[k]
    lines.append(f"## {k.replace('_', ' ')} — {len(lst)} tables")
    for t, n in lst[:400]:
        lines.append(f"- `{t}` ({n:,})")
    lines.append("")
open(f"{REPO}\\docs\\BQ_INDIANA_CENSUS.md", "w", encoding="utf-8").write("\n".join(lines))
for k in sorted(cls):
    print(f"{k}: {len(cls[k])}")
print("census written")
