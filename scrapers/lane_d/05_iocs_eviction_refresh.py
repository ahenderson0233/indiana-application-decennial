"""Lane D refresh: Indiana Office of Court Services (IOCS) statewide eviction/civil-case
statistics (D17 signal).

Feeds si_signals source_id = si_d17_in_iocs_court_year (370 IN rows held, observed
2022-01-01 .. 2025-01-01). Registry-mapped endpoint (public XLSX file, BUILT+LOADED
before, statewide):
  https://www.in.gov/courts/iocs/files/rpts-ijs-2025-pending-incoming-disposed-miscellaneous.xlsx

Probed 2026-08-14: a same-pattern 2026 filename
(rpts-ijs-2026-pending-incoming-disposed-miscellaneous.xlsx) 404s - the 2025 file is
still the latest published year. Re-pulled anyway for a same-file freshness diff (the
publisher may revise the current year's file in place without a filename change).

Full re-pull, ALL sheet columns, every year-tab in the workbook ->
energy-platfrom.indiana_app.in_si_refresh_iocs_eviction.
"""
import os
import sys
import io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lane_d_util as u
import pandas as pd

URL_2025 = "https://www.in.gov/courts/iocs/files/rpts-ijs-2025-pending-incoming-disposed-miscellaneous.xlsx"
URL_2026_PROBE = "https://www.in.gov/courts/iocs/files/rpts-ijs-2026-pending-incoming-disposed-miscellaneous.xlsx"
TABLE = "in_si_refresh_iocs_eviction"

u.ensure_dataset_and_registry()

if not u.robots_allowed(URL_2025):
    raise SystemExit(f"BLOCKED: robots.txt disallows {URL_2025}")

import requests
probe = requests.head(URL_2026_PROBE, headers={"User-Agent": u.UA}, timeout=30)
probe_note = f"2026 filename probe ({URL_2026_PROBE}): HTTP {probe.status_code}"
print(probe_note)

print(f"Downloading {URL_2025} ...")
u._throttle(URL_2025)
r = requests.get(URL_2025, headers={"User-Agent": u.UA}, timeout=120)
r.raise_for_status()
content = r.content
print(f"Downloaded {len(content)} bytes")

xls = pd.ExcelFile(io.BytesIO(content))
print(f"Sheets: {xls.sheet_names}")

all_rows = []
for sheet in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet, dtype=str)
    df.columns = [str(c) for c in df.columns]
    print(f"  sheet '{sheet}': {len(df)} rows, {len(df.columns)} cols: {list(df.columns)}")
    for _, row in df.iterrows():
        d = row.to_dict()
        d["_src_sheet"] = sheet
        all_rows.append(d)

print(f"Total rows across all sheets: {len(all_rows)}")
if not all_rows:
    raise SystemExit("ABORT: zero rows parsed, refusing to load/register")

n = u.load_to_bq(
    TABLE, all_rows,
    source="www.in.gov/courts/iocs (Indiana Office of Court Services statewide case statistics XLSX)",
    method="direct file download (requests), all sheets/columns parsed with pandas",
    notes=(f"Lane D freshness refresh of si_d17_in_iocs_court_year/D17 eviction "
           f"(370 IN rows held in si_signals, observed 2022-01-01..2025-01-01; registry "
           f"separately measured 1,543 rows in BigQuery - discrepancy vs si_signals's 370 is "
           f"itself a finding, see LANE_D_FINDINGS.md). {probe_note} - no 2026 file published "
           f"yet under the same naming pattern, so the 2025 file remains the latest; re-pulled "
           f"anyway in case the publisher revised the current file in place. All "
           f"{len(xls.sheet_names)} sheet(s) and all columns captured, not just the originally-"
           f"wired subset."),
)
print(f"DONE: {n} rows loaded to {TABLE}")
