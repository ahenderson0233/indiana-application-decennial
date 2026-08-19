"""G90(a) - normalise the WARN notice vocabulary, and stop throwing away the CLOSURES.

    python scripts/build_warn_normalised.py

Operator, 2026-08-19: *"For WARN notices, we should have more than just layoff data, and much of
this is actually useful in determining SI (e.g., a closure or future closure would be useful)."*

⭐ THE OPERATOR IS RIGHT AND THE CLOSURES ARE THE MAJORITY. `Notice_Type` reads CL on 564 rows and
LO on 415. A layoff keeps the site OPERATING; a closure VACATES it. Those are not two grades of
one signal, they are different facts about whether the land can be bought, and the application has
been treating the whole table as "layoff data".

⚠ WHAT THIS SCRIPT DOES **NOT** DO. It does not make WARN reach a parcel. It cannot: the table
carries Company and City and NO STREET ADDRESS, and matching a company name to land needs a parcel
OWNER, which is NULL on all 3,553,381 Indiana parcels. `D19_warn` is on exactly 2 parcels today and
this script leaves it there. That half is blocked on the DLGF Gateway acquisition, with G104, G70,
G71 and G81. ⛔ Do not attempt a company-name-to-parcel match before owner data exists.

WHAT THE VOCABULARY ACTUALLY LOOKS LIKE (measured, not assumed):

    CL 564 · LO 415 · N/A 204 · Potential Closure 22 · RH 4 · TR 4
    + 'CL (Holiday)', 'CL -Relocating', 'PENDING CL', 'L/O', 'LO and CL', 'LO/CL',
      'LO (3-month temporary layoff)'  -- one row each

⛔ THE 204 `N/A` ROWS ARE NOT UNTYPED LAYOFFS - THEY ARE EMPTY ROWS. Measured: on all 204, the
notice type AND the event date AND the affected-worker count are ALL the literal string 'N/A'.
They carry a company and a city and nothing else. Defaulting them to layoff would invent 204
events; they are classed NOT_STATED and counted openly. This is "unpublished is NULL, never 0"
applied to a vocabulary instead of a rate.

⚠ DATES LIE HERE IN FOUR DIFFERENT WAYS, so `event_date_precision` is carried beside every date:
  950 parse clean as %m/%d/%Y
  204 are 'N/A'
   66 are free text -- ranges ('3/2/2009 to 4/6/2009'), '&' pairs, 'Sept. 2016',
      '3rd Quarter of 2009', 'No closure date announced. Layoffs to commence 5/27/2015'
      and two dates that DO NOT EXIST: '10/37/2008' and '2/29/2013' (2013 is not a leap year).
A range yields its START, flagged as a range. A month or quarter yields the first day, flagged as
month/quarter precision. ⛔ An imprecise date must never render as a published one.

⭐ SIX EVENTS ARE DATED IN THE FUTURE. A forward-dated closure is the scarcest thing in the entire
signal estate -- it is the only class of row that says a site is ABOUT to become available rather
than that it once did.

WRITES `indiana_app.in_si_warn_normalised`. Reads indiana_app only.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
SRC = f"{DS}.in_si_state_warn_notices"
OUT = f"{DS}.in_si_warn_normalised"
client = bigquery.Client(project="energy-platfrom")

# ⚠ DECLARATIVE, and ordered longest-match-first where prefixes overlap: 'LO and CL' and 'LO/CL'
# must be tested BEFORE bare 'LO', or a substring test would file a combined notice as a layoff.
# The residue is reported, never defaulted.
SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH raw AS (
  SELECT
    Company AS company, City AS city, NAICS AS naics,
    Description_of_Work_Industry AS industry,
    notice_pdf_urls,
    TRIM(Notice_Type)  AS nt_raw,
    TRIM(Notice_Date)  AS nd_raw,
    TRIM(LO_CL_Date)   AS ev_raw,
    TRIM(Affected_Workers) AS w_raw
  FROM `{SRC}`
),
typed AS (
  SELECT *,
    CASE
      WHEN UPPER(nt_raw) IN ('LO AND CL', 'LO/CL')                THEN 'LAYOFF_AND_CLOSURE'
      WHEN UPPER(nt_raw) = 'POTENTIAL CLOSURE'                    THEN 'POTENTIAL_CLOSURE'
      WHEN UPPER(nt_raw) LIKE 'PENDING CL%'                       THEN 'POTENTIAL_CLOSURE'
      WHEN UPPER(nt_raw) LIKE 'CL%'                               THEN 'CLOSURE'
      WHEN UPPER(nt_raw) IN ('LO', 'L/O') OR UPPER(nt_raw) LIKE 'LO (%' THEN 'LAYOFF'
      WHEN UPPER(nt_raw) = 'RH'                                   THEN 'REDUCED_HOURS'
      WHEN UPPER(nt_raw) = 'TR'                                   THEN 'TRANSFER'
      WHEN UPPER(nt_raw) = 'N/A'                                  THEN 'NOT_STATED'
      ELSE 'UNMAPPED'
    END AS notice_class,
    -- first M/D/YYYY appearing anywhere in the string; picks up the START of a range
    REGEXP_EXTRACT(ev_raw, r'(\\d{{1,2}}/\\d{{1,2}}/\\d{{4}})') AS ev_first,
    REGEXP_EXTRACT(nd_raw, r'(\\d{{1,2}}/\\d{{1,2}}/\\d{{4}})') AS nd_first
  FROM raw
),
dated AS (
  SELECT *,
    SAFE.PARSE_DATE('%m/%d/%Y', ev_first) AS ev_date,
    SAFE.PARSE_DATE('%m/%d/%Y', nd_first) AS nd_date,
    -- Month / quarter fallbacks, consulted only when no numeric date is present.
    -- ⚠ ONE CAPTURING GROUP PER EXTRACT. BigQuery rejects a REGEXP_EXTRACT carrying two
    -- ("Regular expressions passed into extraction functions must not have more than 1
    -- capturing group"), so month and year are pulled by separate patterns and rejoined.
    -- The month is matched by its 3-letter prefix so 'Sept. 2016' and 'September 2016' both land.
    REGEXP_EXTRACT(ev_raw,
      r'(?i)\\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z.]*\\s+\\d{{4}}\\b') AS ev_mon3,
    REGEXP_EXTRACT(ev_raw,
      r'(?i)\\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z.]*\\s+(\\d{{4}})\\b') AS ev_mon_year,
    REGEXP_EXTRACT(ev_raw, r'(?i)(\\d)(?:st|nd|rd|th)\\s+Quarter\\s+of\\s+\\d{{4}}') AS ev_qn,
    REGEXP_EXTRACT(ev_raw, r'(?i)\\d(?:st|nd|rd|th)\\s+Quarter\\s+of\\s+(\\d{{4}})') AS ev_qy
  FROM typed
),
dated2 AS (
  SELECT *,
    SAFE.PARSE_DATE('%b %Y',
      CONCAT(UPPER(SUBSTR(ev_mon3, 1, 1)), LOWER(SUBSTR(ev_mon3, 2)), ' ', ev_mon_year)) AS ev_month_x
  FROM dated
),
final AS (
  SELECT
    company, city, naics, industry, notice_pdf_urls,
    nt_raw AS notice_type_verbatim,
    notice_class,
    -- ⭐ the ranking the surfaces order by. A closure vacates the site; a layoff does not.
    CASE notice_class
      WHEN 'CLOSURE'            THEN 5
      WHEN 'LAYOFF_AND_CLOSURE' THEN 5
      WHEN 'POTENTIAL_CLOSURE'  THEN 4
      WHEN 'TRANSFER'           THEN 3
      WHEN 'LAYOFF'             THEN 2
      WHEN 'REDUCED_HOURS'      THEN 1
      ELSE NULL                                   -- NOT_STATED / UNMAPPED: unknown, NOT zero
    END AS si_strength,
    (notice_class IN ('CLOSURE', 'LAYOFF_AND_CLOSURE', 'POTENTIAL_CLOSURE')) AS vacates_site,
    ev_raw AS event_date_verbatim,
    COALESCE(ev_date,
             ev_month_x,
             CASE WHEN ev_qn IS NOT NULL AND ev_qy IS NOT NULL
                  THEN DATE(CAST(ev_qy AS INT64), (CAST(ev_qn AS INT64) - 1) * 3 + 1, 1) END) AS event_date,
    CASE
      WHEN ev_raw = 'N/A'                          THEN 'not_stated'
      WHEN ev_date IS NOT NULL
           AND REGEXP_CONTAINS(ev_raw, r'(?i)\\bto\\b|&')  THEN 'range_start'
      WHEN ev_date IS NOT NULL
           AND ev_raw != ev_first                  THEN 'embedded_in_prose'
      WHEN ev_date IS NOT NULL                     THEN 'exact'
      WHEN ev_month_x IS NOT NULL                  THEN 'month'
      WHEN ev_qn IS NOT NULL AND ev_qy IS NOT NULL THEN 'quarter'
      ELSE 'unparseable'
    END AS event_date_precision,
    nd_date AS notice_date,
    -- ⚠ NULL, not 0: 'N/A' is a worker count we were never given, not a notice affecting nobody
    SAFE_CAST(REGEXP_REPLACE(w_raw, r'[^0-9]', '') AS INT64) AS affected_workers,
    SUBSTR(naics, 1, 2) AS naics2
  FROM dated2
)
SELECT *,
  -- ⭐ NOT every closure is a siting opportunity. A restaurant closing vacates a lease, not a
  -- powered industrial site. The sector decides whether the vacancy is even interesting.
  CASE
    WHEN naics2 IN ('31', '32', '33') THEN 'industrial'
    WHEN naics2 IN ('48', '49')       THEN 'logistics'
    WHEN naics2 = '22'                THEN 'utility'
    WHEN naics2 = '23'                THEN 'construction'
    WHEN naics2 = '42'                THEN 'wholesale'
    WHEN naics2 IN ('44', '45', '72') THEN 'retail_or_food'
    WHEN naics2 IN ('61', '62')       THEN 'institutional'
    WHEN naics IS NULL OR naics = 'N/A' THEN NULL
    ELSE 'other'
  END AS site_kind,
  (event_date IS NOT NULL AND event_date > CURRENT_DATE()) AS event_is_future
FROM final
"""

print("building in_si_warn_normalised ...")
job = client.query(SQL)
job.result()
gb = round((job.total_bytes_processed or 0) / 1e9, 4)

n = list(client.query(f"SELECT COUNT(*) c FROM `{OUT}`"))[0].c
print(f"  {n:,} rows, {gb} GB scanned\n")

print("notice_class:")
rows = list(client.query(f"""
  SELECT notice_class, COUNT(*) n, COUNTIF(vacates_site) vac,
         COUNTIF(event_date IS NOT NULL) dated, COUNTIF(event_is_future) fut
  FROM `{OUT}` GROUP BY 1 ORDER BY n DESC"""))
for r in rows:
    print(f"  {r.notice_class:20s} {r.n:5d}  vacates={r.vac:4d}  dated={r.dated:4d}  future={r.fut}")

unmapped = [r for r in rows if r.notice_class == "UNMAPPED"]
print(f"\nUNMAPPED (the residue -- reported, never defaulted): {unmapped[0].n if unmapped else 0}")
if unmapped:
    for r in client.query(f"""SELECT DISTINCT notice_type_verbatim FROM `{OUT}`
                              WHERE notice_class='UNMAPPED'"""):
        print(f"    {r.notice_type_verbatim!r}")

print("\nevent_date_precision:")
for r in client.query(f"""SELECT event_date_precision p, COUNT(*) n FROM `{OUT}`
                          GROUP BY 1 ORDER BY n DESC"""):
    print(f"  {r.p:20s} {r.n:5d}")

print("\nsite_kind of the rows that VACATE a site (the ones that matter):")
for r in client.query(f"""SELECT IFNULL(site_kind,'(naics not stated)') k, COUNT(*) n
                          FROM `{OUT}` WHERE vacates_site GROUP BY 1 ORDER BY n DESC"""):
    print(f"  {r.k:22s} {r.n:5d}")

print("\nFUTURE-DATED events -- the scarcest rows we hold:")
for r in client.query(f"""SELECT company, city, notice_class, event_date, event_date_precision,
                                 affected_workers, site_kind
                          FROM `{OUT}` WHERE event_is_future ORDER BY event_date"""):
    w = f"{r.affected_workers:,}" if r.affected_workers is not None else "not stated"
    print(f"  {str(r.event_date)}  {r.notice_class:18s} {str(r.company)[:34]:36s} "
          f"{str(r.city)[:16]:18s} {w:>10s}  {r.site_kind or '-'}")

# ---- registry, in the SAME run (G16) ----
client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_si_warn_normalised',
 'indiana_app.in_si_state_warn_notices (Indiana DWD WARN notice list)',
 'declarative Notice_Type mapping, longest-match-first so LO/CL is not filed as LO; event date '
 'parsed %m/%d/%Y with range-start, month and quarter fallbacks, each labelled in '
 'event_date_precision; the 204 rows whose type AND date AND worker count are all the literal '
 'N/A are classed NOT_STATED and never defaulted to layoff; affected_workers NULL where not '
 'stated. RE-SCRAPE COMMAND: python scripts/build_warn_normalised.py',
 {n}, {gb}, CURRENT_TIMESTAMP(),
 'G90(a). Closures are the MAJORITY (CL 564 vs LO 415) and were being read as layoff data. '
 'vacates_site marks the ones that free the land; si_strength ranks them. NULL si_strength means '
 'unknown, not weak. This does NOT make WARN reach a parcel - the table has no street address '
 'and Indiana parcel owner is NULL, so D19_warn stays on 2 parcels until the DLGF Gateway pull.'
)""").result()
print("\n  _registry row written")
print("WARN NORMALISATION COMPLETE")
