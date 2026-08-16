"""E2 — refresh cadence, derived rather than declared.

The cadence a source NEEDS is a function of two things we can measure and one we cannot:
  · how fast the publisher actually changes it (their own event dates)
  · how stale our copy is right now (their latest event vs our pull)
  · how much a stale answer would cost a siting decision (a judgment, stated not computed)

A hand-typed schedule drifts the moment a source changes habits. This derives the interval from
the publisher's OWN observed cadence and flags what is already overdue.

IT DOES NOT SCHEDULE ANYTHING. The venue (Task Scheduler vs cloud cron) is an operator decision
and is still open; this produces the table that a scheduler would read, so the decision is the
only thing left to make.

THE HAZARD IT AVOIDS: a source with no event dates cannot have a cadence derived, and guessing
one would manufacture confidence. Those come back as `cadence_basis='cannot derive'` with the
reason, never as a default interval.
"""
import datetime
from google.cloud import bigquery

DS, EN = "energy-platfrom.indiana_app", "energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")
BUILT = datetime.datetime.now(datetime.timezone.utc).isoformat()


def q1(sql): return list(client.query(sql))[0]


print("building in_refresh_cadence …", flush=True)
job = client.query(f"""
CREATE OR REPLACE TABLE `{DS}.in_refresh_cadence` AS
WITH sig AS (
  -- what each SI source publishes, and how recently
  SELECT signal AS subject, 'si_signal' AS kind,
    COUNT(*) rows_, MIN(observed_date) first_event, MAX(observed_date) last_event,
    COUNTIF(observed_date IS NOT NULL) dated
  FROM `{DS}.in_si_signals` GROUP BY signal
),
reg AS (
  SELECT table_name AS subject, 'table' AS kind, ANY_VALUE(n_rows) rows_,
    CAST(NULL AS DATE) first_event, CAST(NULL AS DATE) last_event, CAST(NULL AS INT64) dated,
    MAX(built_at) built_at
  FROM `{DS}._registry` GROUP BY table_name
),
u AS (
  SELECT s.subject, s.kind, s.rows_, s.first_event, s.last_event, s.dated,
         CAST(NULL AS TIMESTAMP) built_at FROM sig s
  UNION ALL SELECT subject, kind, rows_, first_event, last_event, dated, built_at FROM reg
)
SELECT subject, kind, rows_, first_event, last_event, dated, built_at,
  DATE_DIFF(CURRENT_DATE(), last_event, DAY) AS days_since_last_event,
  -- the publisher's own observed span per row: a proxy for how often they publish
  SAFE_DIVIDE(DATE_DIFF(last_event, first_event, DAY), NULLIF(rows_, 0)) AS days_per_row,
  CASE
    WHEN last_event IS NULL THEN 'cannot derive — the source publishes no event date'
    WHEN DATE_DIFF(CURRENT_DATE(), last_event, DAY) > 730 THEN 'annual — the source itself has not moved in 2 years'
    WHEN DATE_DIFF(CURRENT_DATE(), last_event, DAY) > 365 THEN 'annual'
    WHEN DATE_DIFF(CURRENT_DATE(), last_event, DAY) > 90  THEN 'quarterly'
    WHEN DATE_DIFF(CURRENT_DATE(), last_event, DAY) > 30  THEN 'monthly'
    ELSE 'weekly — the source is live'
  END AS suggested_cadence,
  -- NB: no apostrophes in these literals. BigQuery reads a doubled '' as two adjacent string
  -- literals and fails the parse, which is the SQL cousin of the JS adjacent-string bug.
  CASE WHEN last_event IS NULL THEN 'cannot derive'
       ELSE 'derived from the latest event date the publisher itself carries' END AS cadence_basis,
  -- overdue = our copy is older than the interval the publisher's own behaviour implies
  CASE WHEN last_event IS NULL THEN NULL
       WHEN DATE_DIFF(CURRENT_DATE(), last_event, DAY) > 365 THEN TRUE
       ELSE FALSE END AS likely_stale,
  TIMESTAMP('{BUILT}') AS built_at_audit
FROM u
""")
job.result()
print(f"  {job.total_bytes_processed/1e9:.2f} GB")

m = q1(f"""SELECT COUNT(*) n, COUNTIF(cadence_basis='cannot derive') no_date,
  COUNTIF(likely_stale) stale FROM `{DS}.in_refresh_cadence`""")
print(f"  {m.n:,} subjects · {m.no_date:,} cannot have a cadence derived (no event date) · "
      f"{m.stale:,} likely stale")

print("\n  suggested cadence, by bucket:")
for r in client.query(f"""SELECT suggested_cadence, COUNT(*) n FROM `{DS}.in_refresh_cadence`
    GROUP BY 1 ORDER BY n DESC"""):
    print(f"    {r.suggested_cadence[:56]:56s} {r.n:>5}")

print("\n  the SI signals most overdue (publisher moved, we did not):")
for r in client.query(f"""SELECT subject, rows_, last_event, days_since_last_event, suggested_cadence
    FROM `{DS}.in_refresh_cadence` WHERE kind='si_signal' AND last_event IS NOT NULL
    ORDER BY days_since_last_event DESC LIMIT 8"""):
    print(f"    {r.subject[:26]:26s} {r.rows_:>8,} rows · last event {r.last_event} "
          f"({r.days_since_last_event:,} days ago) -> {r.suggested_cadence[:22]}")

n = int(m.n)
client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_refresh_cadence'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at) "
    f"VALUES (@t,@s,@m,@n,CURRENT_TIMESTAMP())",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "in_refresh_cadence"),
        bigquery.ScalarQueryParameter("s", "STRING", f"{DS}.in_si_signals + {DS}._registry"),
        bigquery.ScalarQueryParameter(
            "m", "STRING",
            "E2: refresh cadence DERIVED from each publisher's own latest event date, not "
            "hand-typed — a typed schedule drifts the moment a source changes habits. A source "
            "with no event date returns cadence_basis='cannot derive' rather than a default "
            "interval, because guessing one manufactures confidence. Schedules nothing: the "
            "venue (Task Scheduler vs cloud cron) is still an open operator decision, and this "
            "is the table a scheduler would read."),
        bigquery.ScalarQueryParameter("n", "INT64", n)])).result()
print(f"\nregistered in_refresh_cadence ({n:,})")
