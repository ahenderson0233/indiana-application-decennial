"""Lane D refresh: Indiana WARN (Worker Adjustment and Retraining Notification) notices
(D19 signal).

Feeds si_signals source_id = warn_notices (1,039 IN D19 rows held, observed
1994-05-12 .. 2026-07-21). Registry-mapped endpoint (public HTML table, BUILT+LOADED
before, full 2008-2026 history on one page per Lane C's 2026-08-14 findings):
  https://www.in.gov/dwd/warn-notices/current-warn-notices/

THE TIME-SENSITIVITY PAYOFF: each notice carries its own 'LO/CL Date' (layoff/closure
date) and 'Notice Type' (e.g. WARN vs CL=closure). A held notice whose LO/CL date has
now passed, or whose Notice Type has flipped to a closure/amendment, is the remediation
signal this whole lane exists to surface.

robots.txt checked (allowed). Full HTML table, ALL columns captured (not just the
originally-wired subset) -> energy-platfrom.indiana_app.in_si_refresh_warn_notices.
"""
import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lane_d_util as u
from bs4 import BeautifulSoup

URL = "https://www.in.gov/dwd/warn-notices/current-warn-notices/"
TABLE = "in_si_refresh_warn_notices"

u.ensure_dataset_and_registry()

if not u.robots_allowed(URL):
    raise SystemExit(f"BLOCKED: robots.txt disallows {URL}")

print(f"Fetching {URL} ...")
html = u.get(URL, as_json=False, timeout=90)
soup = BeautifulSoup(html, "lxml")
tables = soup.find_all("table")
if not tables:
    raise SystemExit("ABORT: no <table> found on the WARN page - page structure changed")
tbl = tables[0]
trs = tbl.find_all("tr")
if len(trs) < 2:
    raise SystemExit("ABORT: WARN table has no data rows")

headers = [c.get_text(strip=True) or f"col_{i}" for i, c in enumerate(trs[0].find_all(["th", "td"]))]
# de-dupe blank/repeated headers
seen_h = {}
clean_headers = []
for h in headers:
    seen_h[h] = seen_h.get(h, 0) + 1
    clean_headers.append(h if seen_h[h] == 1 else f"{h}_{seen_h[h]}")

rows = []
for tr in trs[1:]:
    cells = tr.find_all(["td", "th"])
    if not cells:
        continue
    row = {}
    for i, c in enumerate(cells):
        col = clean_headers[i] if i < len(clean_headers) else f"col_{i}"
        row[col] = c.get_text(strip=True)
        # capture any link href in this cell too (detail pages, PDFs) as a sibling column
        a = c.find("a")
        if a and a.get("href"):
            row[f"{col}__href"] = a.get("href")
    rows.append(row)

print(f"Parsed {len(rows)} data rows from the WARN table; columns: {clean_headers}")
if not rows:
    raise SystemExit("ABORT: zero rows parsed, refusing to load/register")

n = u.load_to_bq(
    TABLE, rows,
    source="www.in.gov/dwd/warn-notices/current-warn-notices/ (Indiana DWD WARN notices, full history table)",
    method="HTML table scrape (bs4), single page, robots.txt allowed",
    notes=(f"Lane D freshness refresh of warn_notices/D19 (1,039 IN rows held in si_signals, "
           f"observed 1994-05-12..2026-07-21; registry separately measured 1,220 IN rows in "
           f"BigQuery for source_state=IN). Parsed {len(rows)} rows from the current single-page "
           f"table this run. ALL columns captured: {clean_headers}. Time-sensitivity payoff: "
           f"'LO/CL Date' (layoff/closure date) and 'Notice Type' (WARN vs CL) per row let a "
           f"consumer identify notices whose layoff/closure has since occurred."),
)
print(f"DONE: {n} rows loaded to {TABLE}")
