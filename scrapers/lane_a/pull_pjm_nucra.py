"""PJM NUCRA — Network Upgrade Cost Responsibility Allocation (public XLSX export, no login).

The cycle-service-request-status page's own export: POST jsonModel to
/m/ProjectTransition/GenerateExcelNUCRAProjectsAll -> XLSX of the whole NUCRA report:
network upgrade id -> allocated queue project ids -> cost -> TO -> state. This is the public
machine-readable mapping of queue project -> network upgrade cost (coordinator item 2).

Lands VERBATIM (every column, all states, names_indiana flag added) to
indiana_app.in_pjm_nucra_costs; registered same run. Observed event dates = the report's own
date/cycle columns; _pulled_at separate.
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
URL = "https://www.pjm.com/m/ProjectTransition/GenerateExcelNUCRAProjectsAll"
HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(HERE, "pjm_nucra.xlsx")
IN_TOKEN = r"(^|[^A-Z])IN([^A-Z]|$)"

model = {
    "GridName": "ProjectTransition", "ItemType": 0,
    "Items": [{"ItemType": 1, "FilterName": "ReportType", "IsSingleItem": True,
               "Filter": "NUCRA"}],
    "Paginator": {"ItemType": 7, "CurrentItmsPerPageValue": "25", "CurrentPageIndex": "1"},
    "Sort": "", "SortDirection": "", "RelatedGridsFilters": "",
}
body = urllib.parse.urlencode({"jsonModel": json.dumps(model)}).encode()
req = urllib.request.Request(URL, data=body, method="POST", headers={
    "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
with urllib.request.urlopen(req, timeout=300) as r:
    raw = r.read(200_000_000)
print(f"POST {URL} -> 200, {len(raw):,}b")
if raw[:2] != b"PK":
    print("NOT XLSX; head:", raw[:300].decode("utf-8", "replace"))
    sys.exit(1)
with open(XLSX, "wb") as f:
    f.write(raw)

import pandas as pd  # noqa: E402

xl = pd.ExcelFile(XLSX)
print("sheets:", xl.sheet_names)
df = xl.parse(xl.sheet_names[0], dtype=str)
print(f"rows {len(df):,} x cols {len(df.columns)}")
print("columns:", list(df.columns))
print(df.head(3).to_string()[:1200])

def bqcol(c):
    return re.sub(r"[^0-9a-zA-Z_]+", "_", str(c).strip()).strip("_").lower() or "col"

mapping, cols = {}, []
for c_ in df.columns:
    b, i, b0 = bqcol(c_), 2, bqcol(c_)
    while b in cols:
        b = f"{b0}_{i}"; i += 1
    cols.append(b); mapping[b] = str(c_)
df.columns = cols

state_col = next((k for k in cols if "state" in k), None)
if state_col:
    df["names_indiana"] = df[state_col].fillna("").str.upper().str.contains(IN_TOKEN, regex=True)
stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
df["_pulled_at"] = stamp
df["_source_url"] = URL
df["_colmap"] = json.dumps(mapping)

from google.cloud import bigquery  # noqa: E402

sys.path.insert(0, HERE)
from register_helper import register  # noqa: E402

c = bigquery.Client(project="energy-platfrom")
DEST = "energy-platfrom.indiana_app.in_pjm_nucra_costs"
c.load_table_from_dataframe(df, DEST, job_config=bigquery.LoadJobConfig(
    write_disposition="WRITE_TRUNCATE")).result()
n = list(c.query(f"SELECT COUNT(*) n FROM `{DEST}`").result())[0].n
n_in = list(c.query(f"SELECT COUNTIF(names_indiana) n FROM `{DEST}`").result())[0].n \
    if state_col else None
print(f"loaded {n:,} rows -> {DEST}; names_indiana={n_in}")
if n != len(df):
    raise RuntimeError(f"ROW CONSERVATION FAILED {len(df)} -> {n}")

register(
    "in_pjm_nucra_costs",
    "PJM NUCRA (Network Upgrade Cost Responsibility Allocation) - public XLSX export of the "
    "cycle-service-request-status page, endpoint " + URL,
    "replicated the page's own 'export all' POST (jsonModel GridName=ProjectTransition, "
    "ReportType=NUCRA); parsed verbatim, every column kept + names_indiana token-match flag; "
    "no login, no terms dialogue",
    int(n), 0.0,
    f"THE public machine-readable queue-project -> network-upgrade-cost mapping: network upgrade "
    f"id -> allocated queue project ids -> cost -> TO -> state. {n:,} rows all-states, "
    f"{n_in if n_in is not None else 'n/a'} name Indiana. Costs in $M per the page's conventions "
    f"(same family as RTEP export). PLOTTABILITY: JOINABLE_IDENTITY (upgrade id joins "
    f"in_pjm_rtep_upgrades/held txexp_pjm_tcic_upgrade_info; queue project ids join the PJM "
    f"queue/queuescope universe; no coords served). Per-upgrade drilldowns exist at "
    f"/m/ProjectTransition/NucraProjectDetails|UpgradeProjectsWithCostAlloc?upgradeId={{id}} "
    f"(not crawled this run).")
