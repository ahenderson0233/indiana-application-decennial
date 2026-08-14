"""Target 3: Indiana DWD WARN notices (current list) -> in_si_state_warn_notices.
Observed event date = Notice Date column (plus LO/CL effective date kept verbatim)."""
import re
import sys
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get, load_to_bq

URL = "https://www.in.gov/dwd/warn-notices/current-warn-notices/"
html = get(URL, as_json=False, check_robots=True)

tables = re.findall(r"<table[^>]*>(.*?)</table>", html, re.S | re.I)
print("tables found:", len(tables))
assert tables, "no table on WARN page"

rows_out = []
for tbl in tables:
    trs = re.findall(r"<tr[^>]*>(.*?)</tr>", tbl, re.S | re.I)
    header = None
    for tr in trs:
        cells_raw = re.findall(r"<t([dh])[^>]*>(.*?)</t\1>", tr, re.S | re.I)
        cells = []
        hrefs = []
        for _tag, c in cells_raw:
            hrefs += re.findall(r'href="([^"]+)"', c)
            txt = re.sub(r"<[^>]+>", " ", c)
            txt = re.sub(r"&nbsp;?", " ", txt)
            txt = re.sub(r"&amp;", "&", txt)
            txt = re.sub(r"&#8217;|’", "'", txt)
            txt = re.sub(r"\s+", " ", txt).strip()
            cells.append(txt)
        if header is None:
            header = [c if c else f"col_{i}" for i, c in enumerate(cells)]
            continue
        if not any(cells):
            continue
        row = dict(zip(header, cells))
        if hrefs:
            row["notice_pdf_urls"] = ";".join(
                h if h.startswith("http") else "https://www.in.gov" + h for h in hrefs)
        rows_out.append(row)

print("parsed rows:", len(rows_out))
print("sample:", rows_out[0])
print("last:", rows_out[-1])

# sanity: Notice Date should parse as dates on most rows
dcol = next((k for k in rows_out[0] if "notice date" in k.lower()), None)
ok = sum(1 for r in rows_out if re.match(r"\d{1,2}/\d{1,2}/\d{4}", r.get(dcol, "")))
print(f"rows with parseable {dcol}: {ok}/{len(rows_out)}")

load_to_bq(
    "in_si_state_warn_notices", rows_out,
    source=URL,
    method="html_table_parse (lane_c, robots-checked)",
    notes=("D19_warn extension: Indiana DWD current WARN notice list. Columns verbatim from "
           "page table: Company/City/Affected Workers/Notice Date/LO-CL Date/NAICS/"
           "Description/Notice Type + notice_pdf_urls. OBSERVED EVENT DATE = 'Notice Date'; "
           "'LO/CL Date' is the announced layoff/closure effective date. Notice Type LO=layoff "
           f"CL=closure. {ok}/{len(rows_out)} rows have parseable Notice Date. "
           "Extends held D19 (1,039 rows) with current-period rows; dedupe on "
           "company+notice_date downstream."),
)
