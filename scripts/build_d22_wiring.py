"""D22 environmental — clip, grade for severity, and join to parcels.

PROVENANCE — THE ROUTE ACTUALLY TAKEN WAS NOT THE ONE PLANNED. Record it, because the console
output from the attempt shows a long run of FAILED COUNTIES and that failure is the whole story:
the REST county walk (`echo_rest_services.get_facilities` -> `get_qid`, 92 counties) was defeated
by HTTP 429 rate-limiting, exactly as GAMEPLAN predicted. The agent then fell back to GAMEPLAN
route 2, ECHO's BULK EXPORT, and that is where every row in `in_si_d22_echo_facilities` came from:

    https://echo.epa.gov/files/echodownloads/echo_exporter.zip  ->  ECHO_EXPORTER.csv

The bulk file is a BETTER instrument than the REST route the handoff described, and it changes
two things a future session would otherwise get wrong:
  · it carries 133 source columns, not the 59 that `get_qid` returns;
  · it uses SCREAMING_SNAKE names (`FAC_SNC_FLG`), not REST camel (`FacSNCFlg`). Checking the
    handoff's REST names against this table reports all nine signal columns MISSING when every
    one is present — the same exact-name trap that produced the "79 tables not locatable" error.
  · Adams reads 282 here against the 928 the REST county call reported. That is NOT a short page:
    REST counts programme records, the bulk file counts FACILITIES. Different denominators.

CROSS-CHECKS THAT SAY THE PULL IS SOUND (measured against Lane F's independent figures):
    total penalties            $1.86B   Lane F: $1.86B    exact
    active facilities          25,225   Lane F: 25,330    99.6%
    significant violators      372      Lane F: 372       exact
    facilities with lat/lon    58,003 of 58,003 (100%)

SEVERITY — being IN the ECHO universe is not seller intent; 58,003 Indiana facilities are simply
regulated. Only distress is admitted, and the vocabulary had to be read rather than guessed:
  · `FAC_SNC_FLG` is 'N' on ALL 58,003 — the bulk export does not populate it. The significant-
    non-compliance signal lives in `FAC_COMPLIANCE_STATUS='Significant Violation'` (372), which is
    how it reconciles with Lane F.
  · A `LIKE '%VIOLATION%'` test on that column reads 24,976 — because it matches "No Violation
    Identified". The real violation count is 1,432. Never pattern-match a negation.
  · `FAC_ACTIVE_FLAG` is 'Y' or NULL, never 'N'; ceased operation is `FAC_COMPLIANCE_STATUS=
    'Inactive'` (5,780) and is admitted as its OWN signal — a shut regulated plant with existing
    power and water service is a site opportunity, not a compliance problem.

IDEM (`in_si_d22_idem_enforcement`, 22,565 rows) CARRIES NO EVENT DATE. `document_published` is a
Y/N publication flag, not a date, despite the pull being scoped 1995-01-01..current. It is wired
as an UNDATED owner-name-keyed signal and the missing date is recorded as a gap, not invented.

D85 GUARD: parcels_in/080500000047000018 excluded from the spatial join.
"""
import datetime
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
D85 = "080500000047000018"
client = bigquery.Client(project="energy-platfrom")
BUILT = datetime.datetime.now(datetime.timezone.utc).isoformat()


def q1(sql): return list(client.query(sql))[0]


def run(sql, label):
    job = client.query(sql); job.result()
    print(f"  {label}: {job.total_bytes_processed/1e9:.2f} GB", flush=True)


# --- 1. the Indiana-clipped, severity-graded facility layer -----------------------------------
print("building in_si_d22_echo_indiana …", flush=True)
run(f"""
CREATE OR REPLACE TABLE `{DS}.in_si_d22_echo_indiana` AS
SELECT * EXCEPT(FAC_LAT, FAC_LONG),
  SAFE_CAST(FAC_LAT AS FLOAT64)  AS lat,
  SAFE_CAST(FAC_LONG AS FLOAT64) AS lon,
  -- the distress grade, from the vocabulary as it is actually written
  CASE
    WHEN FAC_COMPLIANCE_STATUS = 'Significant Violation'          THEN 'significant_violation'
    WHEN CAA_HPV_FLAG = 'Y'                                       THEN 'high_priority_violator'
    WHEN FAC_COMPLIANCE_STATUS IN ('Violation Identified','Violation') THEN 'violation'
    WHEN SAFE_CAST(FAC_PENALTY_COUNT AS INT64) > 0                THEN 'penalised'
    WHEN FAC_COMPLIANCE_STATUS = 'Inactive'                       THEN 'facility_inactive'
    ELSE 'no_distress_marker' END                                 AS distress_class,
  (FAC_COMPLIANCE_STATUS IN ('Significant Violation','Violation Identified','Violation')
     OR CAA_HPV_FLAG = 'Y'
     OR SAFE_CAST(FAC_PENALTY_COUNT AS INT64) > 0)                AS is_distress,
  (FAC_COMPLIANCE_STATUS = 'Inactive')                            AS is_inactive_facility,
  -- FAC_COUNTY holds 230 spellings for a 92-county state ('ADAMS' / 'Adams' / 'ADAMS COUNTY');
  -- the FIPS is the reliable key where present, so both are carried and neither is guessed
  UPPER(REGEXP_REPLACE(TRIM(IFNULL(FAC_COUNTY,'')), r'\\s+COUNTY$', '')) AS county_norm,
  NULLIF(SUBSTR(IFNULL(FAC_DERIVED_STCTY_FIPS,''), 1, 5), '')     AS county_fips,
  TIMESTAMP('{BUILT}')                                            AS built_at
FROM `{DS}.in_si_d22_echo_facilities`
WHERE FAC_STATE = 'IN'      -- Indiana, clipped at the border: 16 out-of-state + 2 null rows drop
""", "in_si_d22_echo_indiana")

# --- 2. facility -> parcel, spatially. NO CENTROIDS: the facility point is the publisher's own.
print("building in_si_d22_parcel_join …", flush=True)
run(f"""
CREATE OR REPLACE TABLE `{DS}.in_si_d22_parcel_join` AS
SELECT
  s.parcel_source, s.parcel_key, s.occ_group,
  f.REGISTRY_ID, f.FAC_NAME, f.FAC_CITY, f.county_norm, f.distress_class,
  f.is_distress, f.is_inactive_facility,
  f.FAC_NAICS_CODES, f.FAC_MAJOR_FLAG,
  SAFE_CAST(f.FAC_TOTAL_PENALTIES AS FLOAT64)      AS total_penalties,
  SAFE_CAST(f.FAC_PENALTY_COUNT AS INT64)          AS penalty_count,
  SAFE_CAST(f.FAC_FORMAL_ACTION_COUNT AS INT64)    AS formal_action_count,
  SAFE.PARSE_DATE('%m/%d/%Y', f.FAC_DATE_LAST_FORMAL_ACTION) AS last_formal_action,
  SAFE.PARSE_DATE('%m/%d/%Y', f.FAC_DATE_LAST_PENALTY)       AS last_penalty_date,
  SAFE.PARSE_DATE('%m/%d/%Y', f.FAC_DATE_LAST_INSPECTION)    AS last_inspection_date,
  f.lat, f.lon,
  TIMESTAMP('{BUILT}') AS built_at
FROM `{DS}.in_si_d22_echo_indiana` f
JOIN `{DS}.in_sites` s
  ON ST_CONTAINS(s.parcel_geog, ST_GEOGPOINT(f.lon, f.lat))
WHERE f.lat IS NOT NULL AND f.lon IS NOT NULL
  AND s.parcel_key != '{D85}'          -- D85 whole-Earth polygon: matches everything if kept
""", "in_si_d22_parcel_join")

# --- 3. county roll-up for the Community / Data pages -----------------------------------------
print("building in_si_d22_county_rollup …", flush=True)
run(f"""
CREATE OR REPLACE TABLE `{DS}.in_si_d22_county_rollup` AS
SELECT county_norm, ANY_VALUE(county_fips) county_fips,
  COUNT(*) facilities,
  COUNTIF(is_distress) distress_facilities,
  COUNTIF(distress_class='significant_violation') significant_violations,
  -- HPV is counted from ITS OWN FLAG, not from distress_class. distress_class is a priority
  -- ladder and all 95 Indiana HPVs are ALSO in significant violation, so reading it off the
  -- ladder returned 0 — a zero that contradicts a known count, rendered as if none existed.
  COUNTIF(CAA_HPV_FLAG='Y') high_priority_violators,
  COUNTIF(is_inactive_facility) inactive_facilities,
  ROUND(SUM(SAFE_CAST(FAC_TOTAL_PENALTIES AS FLOAT64))) total_penalties,
  COUNTIF(FAC_MAJOR_FLAG='Y') major_facilities,
  TIMESTAMP('{BUILT}') AS built_at
FROM `{DS}.in_si_d22_echo_indiana`
WHERE county_norm != '' GROUP BY county_norm
""", "in_si_d22_county_rollup")

# --- 4. measure -------------------------------------------------------------------------------
print("\n--- MEASURED ---")
r = q1(f"""SELECT COUNT(*) n, COUNTIF(is_distress) distress, COUNTIF(is_inactive_facility) inactive,
  COUNTIF(lat IS NOT NULL) located, COUNT(DISTINCT county_norm) counties,
  COUNTIF(county_fips IS NOT NULL) with_fips
FROM `{DS}.in_si_d22_echo_indiana`""")
print(f"facilities (IN only) {r.n:,} · distress {r.distress:,} · inactive {r.inactive:,} · "
      f"located {r.located:,} · county spellings {r.counties} · with FIPS {r.with_fips:,}")
print("\ndistress_class breakdown:")
for x in client.query(f"""SELECT distress_class, COUNT(*) n FROM `{DS}.in_si_d22_echo_indiana`
    GROUP BY 1 ORDER BY n DESC"""):
    print(f"  {x.distress_class:26s} {x.n:>8,}")

j = q1(f"""SELECT COUNT(*) n, COUNT(DISTINCT parcel_key) parcels,
  COUNT(DISTINCT REGISTRY_ID) facs, COUNTIF(is_distress) distress_rows,
  COUNT(DISTINCT IF(is_distress, parcel_key, NULL)) distress_parcels,
  COUNT(DISTINCT IF(is_distress AND occ_group!='residential', parcel_key, NULL)) admitted_parcels
FROM `{DS}.in_si_d22_parcel_join`""")
tot = q1(f"SELECT COUNT(*) n FROM `{DS}.in_si_d22_echo_indiana` WHERE lat IS NOT NULL").n
print(f"\nspatial join: {j.facs:,} of {tot:,} facilities landed on a parcel "
      f"({100*j.facs/tot:.1f}%) · {j.parcels:,} distinct parcels")
print(f"  fan-out {j.n/max(j.facs,1):.3f} rows per facility "
      f"(a value near 2.0 would mean D85 is still in the join)")
print(f"  distress on a parcel: {j.distress_parcels:,} · NON-RESIDENTIAL (admitted): "
      f"{j.admitted_parcels:,}")

# --- 5. register, in the same run ------------------------------------------------------------
ECHO_URL = "https://echo.epa.gov/files/echodownloads/echo_exporter.zip"
reg = [
 ("in_si_d22_echo_indiana", int(r.n), f"indiana_app.in_si_d22_echo_facilities ({ECHO_URL})",
  "Indiana clip (FAC_STATE='IN'; 16 out-of-state + 2 null rows dropped) of the ECHO BULK EXPORT "
  "- NOT the REST county walk, which was defeated by HTTP 429. All 133 source columns kept, "
  "lat/lon cast, plus distress_class graded from FAC_COMPLIANCE_STATUS / CAA_HPV_FLAG / "
  "FAC_PENALTY_COUNT. FAC_SNC_FLG is 'N' on every row in the bulk file - the SNC signal is "
  "FAC_COMPLIANCE_STATUS='Significant Violation' (372, matching Lane F exactly)."),
 ("in_si_d22_parcel_join", int(j.n), "indiana_app.in_si_d22_echo_indiana + in_sites",
  "ST_CONTAINS(parcel_geog, publisher's own facility point) - no centroid anywhere. D85 "
  "whole-Earth parcel excluded by key."),
 ("in_si_d22_county_rollup",
  int(q1(f"SELECT COUNT(*) n FROM `{DS}.in_si_d22_county_rollup`").n),
  "indiana_app.in_si_d22_echo_indiana",
  "per-county facility, distress, significant-violation, inactive and penalty totals. "
  "county_norm strips the ' COUNTY' suffix and case-folds 230 publisher spellings."),
]
for name, n, src, method in reg:
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{name}'").result()
    client.query(
        f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at) "
        f"VALUES (@t,@s,@m,@n,CURRENT_TIMESTAMP())",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", name),
            bigquery.ScalarQueryParameter("s", "STRING", src),
            bigquery.ScalarQueryParameter("m", "STRING", method),
            bigquery.ScalarQueryParameter("n", "INT64", n)])).result()
    print(f"registered {name} ({n:,})")

# --- 6. the endpoint registry: record the route ACTUALLY taken, so it is not lost -------------
cols = {s.name for s in client.get_table(f"{EN}.registry_sources").schema}
print(f"\nregistry_sources columns: {sorted(cols)}")
row = {"source_name": "D22 EPA ECHO — Indiana facilities (BULK EXPORT route)",
       "status": "done",
       "endpoint": ECHO_URL,
       "endpoint_kind": "bulk zip -> CSV (ECHO_EXPORTER.csv)",
       "acquisition_method":
           "scrapers/lane_f/pull_d22_environmental.py — REST county walk "
           "(echo_rest_services.get_facilities -> get_qid) FAILED on HTTP 429 rate-limiting; "
           "fell back to the bulk export, which carries 133 columns vs the REST route's 59 and "
           "uses SCREAMING_SNAKE names. No key, no account, no terms wall.",
       "object_names": ["in_si_d22_echo_facilities", "in_si_d22_echo_indiana"],
       "updated_by": "indiana-app-session-20260816-d22"}
row2 = {"source_name": "D22 IDEM enforcement — Actions and Orders",
        "status": "done",
        "endpoint": "https://oe.idem.in.gov/idem_oe_order",
        "endpoint_kind": "HTML form POST (county=All, media=All, type=All, page=F)",
        "acquisition_method":
            "scrapers/lane_f/pull_d22_environmental.py — single POST for 1995-01-01..current. "
            "GAP: the result table carries NO EVENT DATE; document_published is a Y/N publication "
            "flag. Keyed by company_person + city/county only.",
        "object_names": ["in_si_d22_idem_enforcement"],
        "updated_by": "indiana-app-session-20260816-d22"}
for rw in (row, row2):
    use = {k: v for k, v in rw.items() if k in cols}
    missing = [k for k in rw if k not in cols]
    if missing:
        print(f"  (registry_sources has no {missing} column — those facts stay in _registry.method)")
    errs = client.insert_rows_json(f"{EN}.registry_sources", [use])
    print(f"  appended registry_sources: {rw['source_name'][:52]} "
          f"{'OK' if not errs else errs}")
print("\nDONE")
