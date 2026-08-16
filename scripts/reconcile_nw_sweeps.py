"""F5 — settle the two northwest sweeps against official-source verification.

THE SITUATION. Northwest Indiana was swept twice. Only the re-sweep produced a batch file; the
first pass returned its results in-message and was never collected, and was recovered from the
agent transcript into `in_dc_actions_nw_first_pass`. The two disagreed, and neither dominated:
17 actions / 11 verified in the first pass against 20 / 9 in the re-sweep.

They contradicted outright on one row. Jasper County rezone petition Cause #PC-22-25 (NIPSCO,
~5 parcels Ag->I-2, Kankakee Township) was recorded `denied` by the first pass and
`petition-pending` by the re-sweep, BOTH graded VERIFIED_AT_OFFICIAL_SOURCE. That is not
reconcilable by inspection, and picking the more plausible one would mean choosing between two
agents who each claim to have read the record.

So it was referred to a third instrument: official-source verification, which went to the Plan
Commission's own minutes.

THE ANSWER, AND NEITHER SWEEP HAD IT. The Plan Commission issued an UNFAVORABLE RECOMMENDATION on
2025-12-15 — an advisory act, not a denial — and the Board of Commissioners then APPROVED the
rezone on 2026-02-02 with nine written commitments. So the first pass's "denied" was wrong, and
the re-sweep's "petition-pending" was correct only for the seven weeks between those two dates.
The current status is APPROVED.

That is worth recording rather than quietly overwriting: two independent sweeps both reported a
verified fact, both were wrong, and only a third instrument reading the primary record settled it.
A disagreement between instruments is evidence that at least one is wrong — not a tie to be broken
by preference.

Writes only to energy-platfrom.indiana_app.
"""
import datetime

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()

SQL = f"""
CREATE OR REPLACE TABLE `{DS}.in_dc_actions_nw_reconciled` AS
WITH first_pass AS (
  SELECT county, action_type, evidence_grade AS grade_first,
         SUBSTR(instrument, 1, 200) AS instrument_first
  FROM `{DS}.in_dc_actions_nw_first_pass`
),
resweep AS (
  SELECT county, action_type, evidence_grade AS grade_resweep,
         SUBSTR(instrument, 1, 200) AS instrument_resweep
  FROM `{DS}.in_dc_actions_county_v2` WHERE source_batch = 'A'
),
verified AS (      -- the third instrument: official-source verification
  -- ONE ROW PER (county, action_type). Without this the join fans out: Jasper carried 2 first-pass
  -- rows x 2 re-sweep rows x 2 verification rows and printed the same disagreement EIGHT TIMES,
  -- which reads as eight findings instead of one. A comparison table that multiplies its own rows
  -- is the fan-out defect in miniature — the same reason parcel joins are checked at ~1.0.
  SELECT county, confirmed_action_type,
         ANY_VALUE(verdict) AS verdict,
         ANY_VALUE(final_evidence_grade) AS final_evidence_grade,
         ANY_VALUE(SUBSTR(verified_instrument, 1, 200)) AS instrument_verified,
         ANY_VALUE(verified_observed_date) AS verified_observed_date,
         ANY_VALUE(official_url) AS official_url,
         LOGICAL_OR(posture_renderable) AS posture_renderable,
         COUNT(*) AS n_verification_rows
  FROM `{DS}.in_dc_actions_resolved`
  WHERE confirmed_action_type IS NOT NULL
  GROUP BY county, confirmed_action_type
)
SELECT
  COALESCE(f.county, r.county) AS county,
  COALESCE(f.action_type, r.action_type) AS action_type,
  f.grade_first, r.grade_resweep,
  f.instrument_first, r.instrument_resweep,
  v.verdict AS verification_verdict,
  v.confirmed_action_type, v.instrument_verified, v.verified_observed_date, v.official_url,
  CASE
    WHEN f.county IS NULL                       THEN 'resweep_only'
    WHEN r.county IS NULL                       THEN 'first_pass_only'
    WHEN f.grade_first = r.grade_resweep        THEN 'both_agree'
    ELSE 'grade_disagreement'
  END AS reconciliation,
  CASE WHEN v.verdict IS NULL THEN 'not re-verified at an official source'
       ELSE 'settled by official-source verification' END AS settled_by,
  TIMESTAMP('{NOW}') AS built_at
FROM first_pass f
FULL OUTER JOIN resweep r USING (county, action_type)
LEFT JOIN verified v
  ON v.county = COALESCE(f.county, r.county)
 AND v.confirmed_action_type = COALESCE(f.action_type, r.action_type)
"""
client.query(SQL).result()
n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_dc_actions_nw_reconciled`"))[0].n
print(f"built in_dc_actions_nw_reconciled: {n} rows\n")

for r in client.query(f"""SELECT reconciliation, COUNT(*) n,
  COUNTIF(verification_verdict IS NOT NULL) settled
FROM `{DS}.in_dc_actions_nw_reconciled` GROUP BY 1 ORDER BY n DESC"""):
    print(f"  {r.reconciliation:22s} {r.n:>3}  ({r.settled} settled by verification)")

print("\nwhere the two sweeps disagreed on grade:")
for r in client.query(f"""SELECT county, action_type, grade_first, grade_resweep,
  verification_verdict, confirmed_action_type
FROM `{DS}.in_dc_actions_nw_reconciled`
WHERE reconciliation = 'grade_disagreement' ORDER BY county"""):
    print(f"  {r.county:12s} {r.action_type:26s} first={str(r.grade_first)[:12]:12s} "
          f"resweep={str(r.grade_resweep)[:12]:12s} -> {r.verification_verdict or 'UNSETTLED'}")

print("\nrows present in only ONE sweep (the collection failure made visible):")
for r in client.query(f"""SELECT reconciliation, county, action_type
FROM `{DS}.in_dc_actions_nw_reconciled`
WHERE reconciliation IN ('first_pass_only','resweep_only') ORDER BY reconciliation, county"""):
    print(f"  {r.reconciliation:16s} {r.county:12s} {r.action_type}")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_dc_actions_nw_reconciled'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
    f"VALUES (@t,@s,@m,@n,0.0,CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "in_dc_actions_nw_reconciled"),
        bigquery.ScalarQueryParameter("s", "STRING",
            "indiana_app.in_dc_actions_nw_first_pass x in_dc_actions_county_v2 (batch A) x "
            "in_dc_actions_resolved"),
        bigquery.ScalarQueryParameter("m", "STRING",
            "FULL OUTER JOIN of the two northwest sweeps, with official-source verification as a "
            "third instrument where it exists. Nothing is merged and no winner is picked by "
            "preference; disagreements are carried."),
        bigquery.ScalarQueryParameter("n", "INT64", int(n)),
        bigquery.ScalarQueryParameter("no", "STRING",
            "THE HEADLINE: on Jasper Cause #PC-22-25 both sweeps reported a VERIFIED fact and BOTH "
            "WERE WRONG. The Plan Commission issued an unfavourable RECOMMENDATION on 2025-12-15 "
            "(advisory, not a denial) and the Commissioners APPROVED the rezone on 2026-02-02 with "
            "nine written commitments. 'denied' was never true; 'petition-pending' was true only "
            "for those seven weeks. A disagreement between two instruments means at least one is "
            "wrong — it is not a tie to break by preference. "
            "This table is a COMPARISON, not a posture source: read in_dc_actions_resolved for "
            "what may be rendered.")])).result()
print("\nregistered in_dc_actions_nw_reconciled")
