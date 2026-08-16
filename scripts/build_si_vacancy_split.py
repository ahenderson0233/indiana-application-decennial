"""Split D5 vacancy into the two DIFFERENT things it has been conflating.

OPERATOR RULING 2026-08-15: "vacancy lives in BQ under two separate, distinct things: a parcel
without a property, and an abandoned building (which IS an SI signal)."

Measured, and the conflation is corrupting a live feature:

  · `D5_vacancy` is 947,592 rows — 52% of the entire Indiana SI corpus — and 945,896 of them
    (99.8%) come from `si_d5_vacancy_derived`, which flags FOOTPRINT ABSENCE. That is a parcel
    with no building: a LAND STATE we already carry as `occ_group='no_structure'`, not intent to
    sell. It is undated because it is not an event.
  · Consequence on screen: 840,819 of 847,410 signal-flagged parcels (99.2%) are `no_structure`.
    The screener's "Requires seller-intent signal" filter has therefore been selecting EMPTY LAND.
    The genuinely non-residential signalled universe is 1,363 parcels (880 ci + 277 agriculture +
    206 other_nonres), of which 415 carry a date.
  · The REAL abandoned-BUILDING signal was sitting unwired the whole time:
    in_si_indy_abandoned_vacant (7,120 — STATUS 'Abandoned' 5,709 / 'Vacant' 1,411),
    in_si_southbend_vacant_abandoned (47), in_si_southbend_chronic_problem (7).
  · Removing the non-signal also repairs the date picture: the corpus becomes 872,262 rows of
    which 869,755 (99.7%) are dated. The "only 47.8% dated" figure was itself an artifact of
    counting footprint-absence as a signal.

Builds two clearly-named tables rather than one ambiguous one, and registers both.
"""
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

def build(name, sql, source, method, notes):
    dry = client.query(f"CREATE OR REPLACE TABLE `{DS}.{name}` AS\n{sql}",
                       job_config=bigquery.QueryJobConfig(dry_run=True))
    gb = dry.total_bytes_processed / 1e9
    client.query(f"CREATE OR REPLACE TABLE `{DS}.{name}` AS\n{sql}").result()
    n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.{name}`"))[0].n
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{name}'").result()
    client.query(f"""INSERT `{DS}._registry`
      (table_name, source, method, n_rows, gb_scanned, built_at, notes)
      VALUES (@t,@s,@m,@n,@g,CURRENT_TIMESTAMP(),@o)""",
      job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", name),
        bigquery.ScalarQueryParameter("s", "STRING", source),
        bigquery.ScalarQueryParameter("m", "STRING", method),
        bigquery.ScalarQueryParameter("n", "INT64", n),
        bigquery.ScalarQueryParameter("g", "FLOAT64", round(gb, 4)),
        bigquery.ScalarQueryParameter("o", "STRING", notes)])).result()
    print(f"  {name:<38} {n:>9,} rows  ({gb:.2f} GB)")
    return n

# ---- 1. ABANDONED BUILDINGS — the real D5 signal -----------------------------------------
n_ab = build("in_si_d5_abandoned_buildings", f"""
  SELECT 'D5_abandoned_building' AS signal, 'indy_abandoned_vacant' AS source_id,
         CAST(PARCEL_I AS STRING) AS parcel_key,
         TRIM(CONCAT(IFNULL(CAST(STNUMBER AS STRING),''),' ',IFNULL(FULL_STNAME,''))) AS address,
         CITY AS city, CAST(ZIPCODE AS STRING) AS zip,
         STATUS AS status,
         -- 'Abandoned' is the stronger claim; 'Vacant' is a weaker one. Kept distinct rather
         -- than merged into one flag, because they are different assertions about a building.
         CASE WHEN UPPER(STATUS)='ABANDONED' THEN 1.0 ELSE 0.7 END AS quality_mult
  FROM `{DS}.in_si_indy_abandoned_vacant`
  UNION ALL
  SELECT 'D5_abandoned_building', 'southbend_vacant_abandoned',
         CAST(NULL AS STRING), CAST(NULL AS STRING), 'South Bend', CAST(NULL AS STRING),
         'Vacant/Abandoned', 0.7
  FROM `{DS}.in_si_southbend_vacant_abandoned`
  UNION ALL
  SELECT 'D5_abandoned_building', 'southbend_chronic_problem',
         CAST(NULL AS STRING), CAST(NULL AS STRING), 'South Bend', CAST(NULL AS STRING),
         'Chronic problem property', 1.0
  FROM `{DS}.in_si_southbend_chronic_problem`""",
  "indiana_app.in_si_indy_abandoned_vacant + in_si_southbend_vacant_abandoned + _chronic_problem",
  "the ABANDONED-BUILDING half of D5, which is the actual seller-intent signal",
  "OPERATOR RULING 2026-08-15: vacancy is two distinct things and only this half is seller "
  "intent. An abandoned building is a distressed asset an owner may want rid of; a parcel with "
  "no building is simply vacant land. Indy contributes 5,709 'Abandoned' and 1,411 'Vacant' - "
  "kept distinct at quality_mult 1.0 vs 0.7 because they are different assertions.")

# ---- 2. VACANT LAND — a land attribute, explicitly NOT an SI signal ----------------------
n_land = build("in_si_d5_vacant_land_NOT_A_SIGNAL", f"""
  SELECT g.parcel_key, g.county_fips, g.quality_mult,
         s.occ_group, s.parcel_acres, s.mw_datacenter_4_per_acre
  FROM `{DS}.in_si_signals` g
  LEFT JOIN `{DS}.in_sites` s ON CAST(s.parcel_key AS STRING) = CAST(g.parcel_key AS STRING)
  WHERE g.source_id = 'si_d5_vacancy_derived'""",
  "indiana_app.in_si_signals WHERE source_id='si_d5_vacancy_derived'",
  "footprint-absence rows isolated OUT of the signal corpus",
  "NOT A SELLER-INTENT SIGNAL - named so it cannot be mistaken for one. 945,896 rows flagging "
  "that a parcel has no building footprint. That is a LAND STATE already carried on in_sites as "
  "occ_group='no_structure', and it is undated because it is not an event. Counting it as D5 "
  "made it 52% of the Indiana SI corpus and made the screener's 'requires seller-intent signal' "
  "filter select EMPTY LAND: 840,819 of 847,410 flagged parcels were no_structure. Retained for "
  "traceability, never to be re-admitted as a signal.")

# ---- 3. what the corpus looks like once the non-signal is removed ------------------------
print("\ncorpus with the non-signal removed:")
for r in client.query(f"""
    SELECT COUNT(*) rows_kept, COUNTIF(observed_date IS NOT NULL) dated,
           ROUND(100*COUNTIF(observed_date IS NOT NULL)/COUNT(*),1) pct_dated,
           COUNTIF(observed_date >= DATE '2023-08-15') last_3y
    FROM `{DS}.in_si_signals` WHERE source_id != 'si_d5_vacancy_derived'"""):
    print(f"  {r.rows_kept:,} rows · {r.dated:,} dated ({r.pct_dated}%) · {r.last_3y:,} in last 3 years")
print(f"\n  was: 1,818,158 rows / 869,755 dated (47.8%) — the 47.8% was an artifact of counting")
print(f"       945,896 undated footprint-absence rows as a signal.")
