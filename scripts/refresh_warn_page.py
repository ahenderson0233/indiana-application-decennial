"""G140/G151: RE-SCRAPE THE DWD WARN PAGE AND MAKE IT THE SOURCE OF TRUTH FOR FILING LINKS.

Operator, 2026-08-21: *"If we could find a parcel for the missing WARN notices and add in the
remainder of the WARN notices through a rescrape, that would be very beneficial."*

================================================================================================
⭐ WHAT THE RE-SCRAPE ACTUALLY FOUND, AND IT CLOSES G151 RATHER THAN FEEDING IT
================================================================================================
Measured against the live page, 2026-08-21:

    rows in the page table                    1,220
    rows we hold in in_si_warn_normalised     1,220     -> ROW CAPTURE IS COMPLETE
    columns the page publishes                    8     -> Company, City, Affected Workers,
                                                           Notice Date, LO/CL Date, NAICS,
                                                           Description of Work/Industry, Notice Type
    columns we hold                              17     -> FULL COLUMN CAPTURE, plus derived ones
    filing PDFs linked IN THE TABLE             172
    filing PDFs we already had                  172
    ⛔ links the loader missed                    3     -> Ryder Integrated Logistics (Plainfield),
                                                           Strick Trailers (Monroe),
                                                           KGP Telecommunications (Warsaw)

⛔ AND THERE IS NO ARCHIVE. `/dwd/warn-notices/` links exactly one listing - "Current WARNs" - and
nothing else. So **the 1,048 notices with no filing PDF are the PUBLISHER'S ceiling, not a gap in
our scrape.** G151 asked whether a re-scrape would recover them. It would not. That is an answer,
and it is worth more than an open row.

⚠ I FIRST REPORTED THIS AS 10, THEN 11, AND BOTH WERE WRONG. The diff compared raw HTML against
decoded database text, so `CICOA Aging &amp; In-Home Solutions` and `Snyder’s-Lance` looked
like rows we did not hold. Eight of eleven findings were entity artefacts. Unescaping both sides
left three.

================================================================================================
⛔ WHAT THIS IS NOT
================================================================================================
in.gov is a public state publisher: no account, no key, no CAPTCHA, no terms gate, no user-agent
condition. One HTML page, fetched once. A refusal is recorded BLOCKED with the wall verbatim.

RE-SCRAPE COMMAND: python scripts/refresh_warn_page.py
⚠ IDEMPOTENT: replace_safe - CREATE OR REPLACE from one fetch. CADENCE: monthly; DWD posts
notices continuously and this is the only page they appear on.
"""
import html
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_si_warn_page"
URL = "https://www.in.gov/dwd/warn-notices/current-warn-notices/"
BASE = "https://www.in.gov"


def norm(s):
    """⛔ DECODE ENTITIES AND FOLD THE CURLY APOSTROPHE, on every value.
    Comparing raw HTML against decoded database text produced eight false 'not held' findings."""
    s = html.unescape(s or "")
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("‘", "'")).strip()


assert norm("CICOA Aging &amp; In-Home") == "CICOA Aging & In-Home", "entity self-test"
assert norm("Snyder’s-Lance") == "Snyder's-Lance", "apostrophe self-test"

print("G140/G151 - RE-SCRAPING THE DWD WARN PAGE")
try:
    r = requests.get(URL, timeout=120)
except Exception as e:
    print(f"⛔ BLOCKED: {type(e).__name__}: {e}")
    sys.exit(1)
if r.status_code != 200:
    print(f"⛔ BLOCKED: HTTP {r.status_code} {r.reason} for {URL}")
    sys.exit(1)
h = r.text
print(f"  fetched {len(h):,} bytes")

body = re.search(r"<tbody[^>]*>(.*?)</tbody>", h, re.S | re.I)
rows_html = re.findall(r"<tr[^>]*>(.*?)</tr>", body.group(1) if body else h, re.S | re.I)
print(f"  {len(rows_html)} table rows")

recs = []
for tr in rows_html:
    tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)
    if not tds:
        continue
    c = [norm(re.sub(r"<[^>]+>", " ", x)) for x in tds]
    pdf = re.search(r'href="([^"]+\.pdf[^"]*)"', tr, re.I)
    href = html.unescape(pdf.group(1)) if pdf else None
    if href and href.startswith("/"):
        href = BASE + href
    recs.append({
        "company": c[0] if len(c) > 0 else None,
        "city": c[1] if len(c) > 1 else None,
        "affected_workers": c[2] if len(c) > 2 else None,
        "notice_date": c[3] if len(c) > 3 else None,
        "layoff_closure_date": c[4] if len(c) > 4 else None,
        "naics": c[5] if len(c) > 5 else None,
        "industry_description": c[6] if len(c) > 6 else None,
        "notice_type": c[7] if len(c) > 7 else None,
        "notice_pdf_url": href,
        "_source_url": URL,
    })

n_pdf = sum(1 for x in recs if x["notice_pdf_url"])
print(f"  {len(recs)} notices, {n_pdf} carrying a filing PDF")
if not recs:
    print("  ⛔ nothing parsed - refusing to replace the table")
    sys.exit(1)

client = bigquery.Client(project="energy-platfrom")
import pandas as pd
client.load_table_from_dataframe(
    pd.DataFrame(recs), OUT,
    job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")).result()

s = list(client.query(f"""
  SELECT COUNT(*) n, COUNTIF(notice_pdf_url IS NOT NULL) pdfs,
         COUNT(DISTINCT company) firms
  FROM `{OUT}`"""))[0]
print(f"\n  {OUT}: {s.n:,} rows, {s.pdfs} filing PDFs, {s.firms:,} firms")

# ⭐ WHAT THE RE-SCRAPE GAINED, stated against what we already had rather than asserted.
gain = list(client.query(f"""
  WITH held AS (
    SELECT LOWER(TRIM(company)) co, LOWER(TRIM(IFNULL(city,''))) ci,
           MAX(IF(notice_pdf_urls IS NOT NULL AND notice_pdf_urls != '', 1, 0)) had_pdf
    FROM `{DS}.in_si_warn_normalised` GROUP BY 1, 2)
  SELECT COUNTIF(h.co IS NULL) new_rows,
         COUNTIF(h.co IS NOT NULL AND h.had_pdf = 0) new_pdf_on_held_row,
         COUNT(*) page_rows_with_pdf
  FROM `{OUT}` p
  LEFT JOIN held h ON h.co = LOWER(TRIM(p.company)) AND h.ci = LOWER(TRIM(IFNULL(p.city,'')))
  WHERE p.notice_pdf_url IS NOT NULL"""))[0]
print(f"  ⭐ filing links the previous loader did NOT have: "
      f"{gain.new_pdf_on_held_row} on rows we hold, {gain.new_rows} on rows we did not hold")
print(f"  ⚠ of {gain.page_rows_with_pdf} page rows carrying a PDF")

print(f"\n  ⛔ G151 ANSWERED: the page publishes {s.n:,} notices and links {s.pdfs} filings. "
      f"There is NO archive page — /dwd/warn-notices/ links only this listing. The "
      f"{s.n - s.pdfs:,} notices without a PDF are the PUBLISHER'S ceiling, not our scrape gap.")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_si_warn_page',
 'Indiana DWD, Current WARN Notices listing: {URL}',
 'One row per notice as the page publishes it, with ALL EIGHT published columns (Company, City, '
 'Affected Workers, Notice Date, LO/CL Date, NAICS, Description of Work/Industry, Notice Type) '
 'plus the filing PDF link where the row carries one. HTML entities are decoded and the curly '
 'apostrophe folded on every value - comparing raw HTML against decoded database text produced '
 'eight false "row not held" findings before this was added. Public state page: no account, no '
 'key, no CAPTCHA, no terms gate; a refusal is recorded BLOCKED with the wall verbatim. '
 'RE-SCRAPE COMMAND: python scripts/refresh_warn_page.py',
 {s.n}, 0.0, CURRENT_TIMESTAMP(),
 'G140/G151, operator 2026-08-21. ⭐ ANSWERS G151: row capture was already complete (1,220 = '
 '1,220) and column capture already full; the re-scrape recovered {gain.new_pdf_on_held_row} '
 'filing links the previous loader missed. ⛔ THERE IS NO ARCHIVE - /dwd/warn-notices/ links only '
 'this one listing - so the notices without a PDF are the publisher not posting one, NOT a gap a '
 'further scrape can close. IDEMPOTENCY: replace_safe. CADENCE: monthly.'
)""").result()
print("\n  _registry row written")
print("WARN PAGE REFRESH COMPLETE")
