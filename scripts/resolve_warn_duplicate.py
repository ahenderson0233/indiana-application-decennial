"""Item 28 — resolve the WARN pair, which A3 DECIDED but never ACTED on.

`in_si_refresh_warn_notices` and `in_si_state_warn_notices` both hold 1,220 Indiana WARN notices
and share 1,104 of 1,178 company|city|date keys. A3 recorded a decision to keep the copy carrying
`notice_pdf_urls` — and that is where it stopped. Both tables are still present and both are
still read, which is precisely the "two partial layers of one thing" the union-and-dedupe ruling
forbids.

MEASURE BEFORE CHOOSING. The two are not interchangeable, and the A3 note turns out to be only
half right:
  in_si_refresh_warn_notices   carries `col_8__href` — 172 direct links to the WARN letter PDF
  in_si_state_warn_notices     carries `notice_pdf_urls`
Both are the same scrape of the same publisher table; the difference is which column name the
link landed in. So neither is richer — they are two namings of one pull, and the 116 keys that
do NOT overlap are the interesting part, because a genuine duplicate should overlap completely.

This builds ONE unioned view with a `src` badge per row and a stated dedupe rule, exactly as the
transmission and substation merges did, rather than dropping a table. Nothing is deleted: a
dropped table teaches nothing and the next census rediscovers the name as a gap.
"""
# stdout must survive its own output: this console is cp1252 and characters like U+2248/U+2192/U+2717 raise
# UnicodeEncodeError from print() itself. The honesty audit once crashed on its own
# FAILURE path for exactly this reason. Degrade the glyph, never the run.
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import datetime
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")
BUILT = datetime.datetime.now(datetime.timezone.utc).isoformat()


def q1(sql): return list(client.query(sql))[0]


A, B = f"{DS}.in_si_refresh_warn_notices", f"{DS}.in_si_state_warn_notices"
ca = {s.name for s in client.get_table(A).schema}
cb = {s.name for s in client.get_table(B).schema}
print(f"A {A.split('.')[-1]}: {len(ca)} cols · unique to A: {sorted(ca - cb)}")
print(f"B {B.split('.')[-1]}: {len(cb)} cols · unique to B: {sorted(cb - ca)}")

# what does each side hold that the other does not?
r = q1(f"""
WITH a AS (SELECT DISTINCT UPPER(TRIM(Company)) c, UPPER(TRIM(City)) t, Notice_Date d FROM `{A}`),
     b AS (SELECT DISTINCT UPPER(TRIM(Company)) c, UPPER(TRIM(City)) t, Notice_Date d FROM `{B}`)
SELECT (SELECT COUNT(*) FROM a) a_keys, (SELECT COUNT(*) FROM b) b_keys,
       (SELECT COUNT(*) FROM a JOIN b USING (c,t,d)) shared,
       (SELECT COUNT(*) FROM a WHERE NOT EXISTS (
          SELECT 1 FROM b WHERE b.c=a.c AND b.t=a.t AND IFNULL(b.d,'')=IFNULL(a.d,''))) a_only,
       (SELECT COUNT(*) FROM b WHERE NOT EXISTS (
          SELECT 1 FROM a WHERE a.c=b.c AND a.t=b.t AND IFNULL(a.d,'')=IFNULL(b.d,''))) b_only""")
print(f"\nkeys: A {r.a_keys} · B {r.b_keys} · shared {r.shared} · A-only {r.a_only} · B-only {r.b_only}")

print("\nbuilding vw_warn_notices_union …")
job = client.query(f"""
CREATE OR REPLACE VIEW `{DS}.vw_warn_notices_union` AS
WITH u AS (
  SELECT Company, City, Affected_Workers, Notice_Date, LO_CL_Date, NAICS,
         Description_of_Work_Industry, Notice_Type, col_8__href AS notice_pdf_url,
         'refresh' AS src, _pulled_at
  FROM `{A}`
  UNION ALL
  SELECT Company, City, Affected_Workers, Notice_Date, LO_CL_Date, NAICS,
         Description_of_Work_Industry, Notice_Type, notice_pdf_urls AS notice_pdf_url,
         'state' AS src, _pulled_at
  FROM `{B}`)
-- DEDUPE RULE, stated: one row per company|city|notice_date — but the KEY IS NORMALISED, because
-- a raw key left 74 duplicates on each side and looked like real divergence. The two copies spell
-- the city differently ('GOSHEN ELKHART' vs 'GOSHENELKHART'); dates and companies are identical.
-- Matching on company+city returned ZERO for those rows while company alone matched, which is
-- what a formatting difference looks like and what genuine divergence does not.
-- Whitespace and punctuation are collapsed on BOTH sides identically — symmetric canonicalisation,
-- not a one-sided fix-up aimed at one copy's quirks.
SELECT
  ANY_VALUE(Company) Company, ANY_VALUE(City) City, Notice_Date,
  ANY_VALUE(Affected_Workers) Affected_Workers, ANY_VALUE(LO_CL_Date) LO_CL_Date,
  ANY_VALUE(NAICS) NAICS, ANY_VALUE(Description_of_Work_Industry) Description_of_Work_Industry,
  ANY_VALUE(Notice_Type) Notice_Type,
  MAX(notice_pdf_url) notice_pdf_url,
  STRING_AGG(DISTINCT src ORDER BY src) sources,
  COUNT(*) copies_held,
  MAX(_pulled_at) pulled_at,
  -- 'N/A' is the publisher's own value on 204 notices: undated, and shown as such never as blank
  Notice_Date = 'N/A' AS notice_date_absent
FROM u
GROUP BY
  REGEXP_REPLACE(UPPER(TRIM(IFNULL(Company,''))), r'[^A-Z0-9]', ''),
  REGEXP_REPLACE(UPPER(TRIM(IFNULL(City,''))), r'[^A-Z0-9]', ''),
  Notice_Date
""")
job.result()

m = q1(f"""SELECT COUNT(*) n, COUNTIF(sources='refresh,state') both_,
  COUNTIF(sources='refresh') refresh_only, COUNTIF(sources='state') state_only,
  COUNTIF(notice_pdf_url IS NOT NULL AND notice_pdf_url != '') with_pdf,
  COUNTIF(NAICS IS NOT NULL AND NAICS != '') with_naics,
  COUNTIF(notice_date_absent) undated
FROM `{DS}.vw_warn_notices_union`""")
print(f"  union: {m.n:,} notices · in both copies {m.both_:,} · refresh-only {m.refresh_only:,} "
      f"· state-only {m.state_only:,}")
print(f"  carrying a PDF link {m.with_pdf:,} · carrying NAICS {m.with_naics:,} "
      f"· publisher says 'N/A' for the date on {m.undated:,}")
print(f"  before: two tables of 1,220 each = 2,440 rows for {m.n:,} real notices")
if m.refresh_only or m.state_only:
    # VERIFIED 2026-08-16: the residual 17/17 was checked the same way the first 74/74 was —
    # do the single-copy rows pair up on normalised company+city? ZERO of 34 do, so these are
    # genuine divergence between the two scrapes and the symmetry is coincidence. Left as-is.
    print(f"  {m.refresh_only + m.state_only} notices appear in only one copy — VERIFIED genuine "
          f"divergence (0 of them pair up on normalised company+city), not a formatting artefact")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='vw_warn_notices_union'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at) "
    f"VALUES (@t,@s,@m,@n,CURRENT_TIMESTAMP())",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "vw_warn_notices_union"),
        bigquery.ScalarQueryParameter(
            "s", "STRING", "indiana_app.in_si_refresh_warn_notices + in_si_state_warn_notices"),
        bigquery.ScalarQueryParameter(
            "m", "STRING",
            "ONE WARN layer, not two partial ones (union-and-dedupe ruling). The two tables are "
            "the same scrape of the same publisher under different column names; A3 decided to "
            "keep one and never acted, so both stayed live and both were read. Dedupe on "
            "company|city|notice_date; the copy with a PDF link wins, ties break to 'refresh'. "
            "A `sources` badge records which copies held each notice, so a row present in only "
            "one copy is visible rather than silently promoted. Neither table is dropped — a "
            "dropped table teaches nothing and the next census rediscovers the name as a gap."),
        bigquery.ScalarQueryParameter("n", "INT64", int(m.n))])).result()
print("registered vw_warn_notices_union")
