"""PJM RTEP 'Project Status & Cost Allocation' — full public export, no login.

The public page https://www.pjm.com/planning/m/project-construction renders a grid of all RTEP
upgrades (баseline/network/supplemental) with an XLS export button. Its own JS
(PJM.Website.Feature.Planning.js) POSTs jsonModel={GridName:'CostAllocation',...} to
/m/ProjectConst/ProjectConstructionUpgrades and receives the XLSX for whatever filters are set;
empty filters = the full list. This replicates that exact call once, filters empty.

Lands VERBATIM (every column) to indiana_app.in_pjm_rtep_upgrades + registers in the same run.
Observed event dates live in the data itself (projected/actual in-service columns, status dates);
_pulled_at is stored separately.
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"
URL = "https://www.pjm.com/m/ProjectConst/ProjectConstructionUpgrades"
HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(HERE, "pjm_rtep_upgrades.xlsx")

model = {
    "GridName": "CostAllocation",
    "ItemType": 0,
    "Items": [],
    "Paginator": {"ItemType": 7, "CurrentItmsPerPageValue": "25", "CurrentPageIndex": "1"},
    "Sort": "",
    "SortDirection": "",
    "RelatedGridsFilters": "",
}
body = urllib.parse.urlencode({"jsonModel": json.dumps(model)}).encode()
req = urllib.request.Request(URL, data=body, method="POST", headers={
    "User-Agent": UA,
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept": "*/*",
})
t0 = time.time()
with urllib.request.urlopen(req, timeout=300) as r:
    raw = r.read(200_000_000)
    status = r.status
    ctype = r.headers.get("Content-Type")
print(f"POST {URL} -> {status}, {len(raw):,}b, Content-Type={ctype}, {time.time()-t0:.1f}s")

if raw[:2] != b"PK":
    print("NOT an XLSX (no PK magic). First 300 bytes:")
    print(raw[:300].decode("utf-8", "replace"))
    sys.exit(1)

with open(XLSX, "wb") as f:
    f.write(raw)
print(f"saved {XLSX}")

import pandas as pd  # noqa: E402

xl = pd.ExcelFile(XLSX)
print("sheets:", xl.sheet_names)
df = xl.parse(xl.sheet_names[0], dtype=str)
print(f"rows {len(df):,} x cols {len(df.columns)}")
print("columns:", list(df.columns))
print(df.head(3).to_string()[:1500])

# clean column names for BQ (verbatim names kept in a sidecar mapping note)
def bqcol(c):
    s = re.sub(r"[^0-9a-zA-Z_]+", "_", str(c).strip()).strip("_").lower()
    return s or "col"

mapping = {}
cols = []
for c in df.columns:
    b = bqcol(c)
    i, b0 = 2, b
    while b in cols:
        b = f"{b0}_{i}"
        i += 1
    cols.append(b)
    mapping[b] = str(c)
df.columns = cols

stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
df["_pulled_at"] = stamp
df["_source_url"] = URL
df["_source_note"] = ("public XLSX export of the PJM Project Status & Cost Allocation grid, "
                      "empty filter set = full list; column-name mapping: " + json.dumps(mapping))

from google.cloud import bigquery  # noqa: E402

c = bigquery.Client(project="energy-platfrom")
DEST = "energy-platfrom.indiana_app.in_pjm_rtep_upgrades"
job = c.load_table_from_dataframe(
    df, DEST,
    job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"))
job.result()
n = list(c.query(f"SELECT COUNT(*) n FROM `{DEST}`").result())[0].n
print(f"loaded {n:,} rows -> {DEST}")
if n != len(df):
    raise RuntimeError(f"ROW CONSERVATION FAILED {len(df)} -> {n}")

# Indiana visibility check (state column name discovered from the export)
state_col = next((k for k in cols if k in ("state", "states") or "state" in k), None)
n_in = None
if state_col:
    n_in = list(c.query(
        f"SELECT COUNT(*) n FROM `{DEST}` WHERE UPPER({state_col}) LIKE '%IN%'"
        f" AND REGEXP_CONTAINS(UPPER({state_col}), r'(^|[^A-Z])IN([^A-Z]|$)')").result())[0].n
    print(f"rows naming Indiana in {state_col}: {n_in:,}")

reg = f"""
INSERT INTO `energy-platfrom.indiana_app._registry`
  (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
  'in_pjm_rtep_upgrades',
  'PJM Project Status & Cost Allocation (RTEP upgrades) - public grid export at https://www.pjm.com/planning/m/project-construction, endpoint {URL}',
  'replicated the page''s own export: POST jsonModel (GridName=CostAllocation, no filters) -> XLSX blob; parsed verbatim, every column kept; no login, no terms dialogue encountered',
  {n},
  0.0,
  CURRENT_TIMESTAMP(),
  'Full PJM RTEP upgrade list, all states. {('%d rows name Indiana in the state column. ' % n_in) if n_in is not None else ''}Observed event dates are the in-service/status date columns in the data; _pulled_at={stamp} stored separately. PLOTTABILITY: no coordinates served - JOINABLE-IDENTITY via upgrade id, project names/endpoints text and state; facility endpoints are named in the description fields.'
)
"""
c.query(reg).result()
print("registered in indiana_app._registry (same run)")
