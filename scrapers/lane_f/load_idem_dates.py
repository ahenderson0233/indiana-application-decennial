"""A6 — give IDEM's 22,565 enforcement actions an event date.

THE PROBLEM. `in_si_d22_idem_enforcement` has eleven columns and NOT ONE of them is a date.
`document_published` carries exactly two values, 'Y' and 'N' — a publication flag. Undated, the
whole corpus is unusable for the thing that matters: a 1997 Notice of Violation is not a lead and
a 2026 one might be, and there was no way to tell them apart.

TWO ROUTES, AND THEY CHECK EACH OTHER.

  1. WINDOW SLICING (all 22,565). IDEM's public search form accepts a date range, so 380
     month-window POSTs from Jan 1995 to Aug 2026 partition the entire corpus by action month —
     rows are matched back by a 7-field identity tuple plus normalised document_url. This is
     WINDOW MEMBERSHIP, not a printed date: it says the action falls in that month because the
     publisher's own search returned it for that month. One request per month beat 20,728 per
     document, which is why the brief said find the bulk route before grinding.

  2. PRINTED DATES (1,946 so far). The per-case document pages carry the real date in the
     signature block, in four printed forms — 'Signed <date>', 'APPROVED AND ADOPTED ... THIS
     <n>th DAY OF <Month>, <year>', 'For the Commissioner: Date: <date>', and 'Dated at
     Indianapolis ... this <n> day of <Month>'.

THE AGREEMENT IS THE POINT. Where both exist: 1,897 agree on the month, 49 differ — 97.5%. Two
instruments sharing no logic landing on the same month is how you know the window route is sound
rather than merely plausible, exactly as stripping the 'IN:' prefix reproduced an existing flag at
exactly 845,373. The 49 disagreements are KEPT and flagged, not reconciled away: they are mostly
a few days either side of a month boundary, where IDEM's internal action date and the printed
signature date genuinely differ.

PRECISION IS CARRIED, NEVER IMPLIED. A month-precision row gets `date_precision='month'` and its
date is the FIRST of that month — it must never be read as a day. Only rows with a printed date
get `date_precision='day'`. Presenting a window month as a precise date would be an estimate
styled as a published fact.
"""
import datetime
import json
import os

from google.cloud import bigquery

HERE = os.path.dirname(os.path.abspath(__file__))
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()

d = json.loads(open(os.path.join(HERE, "idem_dates.json"), encoding="utf-8").read())
exact = {}
for r in d.get("dates", []):
    k = (r.get("case_number"), r.get("document_url"))
    if r.get("event_date"):
        exact[k] = r
months = d.get("month_windows", [])
print(f"read {len(months):,} month-window rows · {len(exact):,} exact printed dates")

rows, agree, differ, day_only, month_only = [], 0, 0, 0, 0
for m in months:
    k = (m.get("case_number"), m.get("document_url"))
    ex = exact.get(k)
    am = (m.get("action_month") or "")[:7]
    month_date = f"{am}-01" if len(am) == 7 else None
    if ex and ex.get("event_date"):
        same = str(ex["event_date"])[:7] == am
        agree += same; differ += (not same)
        day_only += 1
        rows.append({
            "case_number": m.get("case_number"), "old_case_number": m.get("old_case_number"),
            "company_person": m.get("company_person"), "county": m.get("county"),
            "city": m.get("city"), "media": m.get("media"),
            "type_of_action_order": m.get("type_of_action_order"),
            "document_url": m.get("document_url"),
            "event_date": ex["event_date"], "date_precision": "day",
            "date_kind": ex.get("date_kind"), "date_verbatim": ex.get("date_verbatim"),
            "action_month": am,
            "month_agrees_with_document": str(same),
            "date_basis": ("printed signature date; publisher's search window agrees"
                           if same else
                           "printed signature date; publisher's search window says a DIFFERENT "
                           "month — both kept, neither reconciled away"),
            "_assembled_at": NOW})
    elif month_date:
        month_only += 1
        rows.append({
            "case_number": m.get("case_number"), "old_case_number": m.get("old_case_number"),
            "company_person": m.get("company_person"), "county": m.get("county"),
            "city": m.get("city"), "media": m.get("media"),
            "type_of_action_order": m.get("type_of_action_order"),
            "document_url": m.get("document_url"),
            "event_date": month_date, "date_precision": "month",
            "date_kind": None, "date_verbatim": None, "action_month": am,
            "month_agrees_with_document": None,
            "date_basis": ("MONTH PRECISION ONLY — the publisher's own search returned this row "
                           "for this month. The day is NOT known; the date is the 1st of the "
                           "month and must never be read as a day."),
            "_assembled_at": NOW})

print(f"  day precision {day_only:,} · month precision {month_only:,} · total {len(rows):,}")
print(f"  where both routes exist: {agree:,} agree on the month, {differ:,} differ "
      f"({100*agree/max(agree+differ,1):.1f}% agreement)")

COLS = ["case_number", "old_case_number", "company_person", "county", "city", "media",
        "type_of_action_order", "document_url", "event_date", "date_precision", "date_kind",
        "date_verbatim", "action_month", "month_agrees_with_document", "date_basis",
        "_assembled_at"]
out = [{c: (None if r.get(c) is None else str(r.get(c))) for c in COLS} for r in rows]
client.load_table_from_json(
    out, f"{DS}.in_si_d22_idem_dated",
    job_config=bigquery.LoadJobConfig(
        schema=[bigquery.SchemaField(c, "STRING") for c in COLS],
        write_disposition="WRITE_TRUNCATE")).result()
n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_si_d22_idem_dated`"))[0].n
print(f"loaded {n:,} rows -> in_si_d22_idem_dated")

# what did dating actually buy? recency is the whole reason this was worth doing
print("\nwhat the dates reveal — recency of the corpus:")
for r in client.query(f"""SELECT
  CASE WHEN SAFE.PARSE_DATE('%Y-%m-%d', event_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 YEAR)
         THEN 'a. last 3 years'
       WHEN SAFE.PARSE_DATE('%Y-%m-%d', event_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 10 YEAR)
         THEN 'b. 3-10 years'
       ELSE 'c. older than 10 years' END band,
  COUNT(*) n, COUNTIF(date_precision='day') exact_day
FROM `{DS}.in_si_d22_idem_dated` GROUP BY 1 ORDER BY 1"""):
    print(f"  {r.band:24s} {r.n:>7,}  ({r.exact_day:,} with an exact printed day)")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_si_d22_idem_dated'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
    f"VALUES (@t,@s,@m,@n,0.0,CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "in_si_d22_idem_dated"),
        bigquery.ScalarQueryParameter("s", "STRING",
            "https://oe.idem.in.gov/idem_oe_order search form (380 month windows, 1995-01 to "
            "2026-08) + per-case document pages at apps.idem.in.gov/idem/oe/cause/"),
        bigquery.ScalarQueryParameter("m", "STRING",
            "TWO INDEPENDENT ROUTES. Window slicing dates all 22,565 to MONTH precision by "
            "partitioning the publisher's own search by date range and matching rows back on a "
            "7-field identity tuple plus normalised document_url. Document scraping extracts the "
            "PRINTED signature date to DAY precision. Where both exist they agree on the month "
            "97.5% of the time (1,897 v 49)."),
        bigquery.ScalarQueryParameter("n", "INT64", int(n)),
        bigquery.ScalarQueryParameter("no", "STRING",
            "READ date_precision BEFORE USING event_date. 'month' rows carry the FIRST OF THE "
            "MONTH as a placeholder and the day is NOT known — rendering one as a precise date "
            "would be an estimate styled as a published fact. Only date_precision='day' rows "
            "carry a date the publisher actually printed. "
            "The 49 rows where the window month and the printed date disagree are KEPT and "
            "flagged in month_agrees_with_document, not reconciled: they are mostly a few days "
            "across a month boundary, where IDEM's internal action date and the signature date "
            "genuinely differ. "
            "IDEM remains OWNER-KEYED and still cannot reach a parcel — dating it makes it "
            "filterable and usable as owner-grain context, not parcel-grain evidence.")])).result()
print("registered in_si_d22_idem_dated")
