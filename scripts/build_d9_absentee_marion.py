"""D9 absentee + D18 owner contact for Marion County — from data we already hold.

WHAT THIS CORRECTS. `SI_COVERAGE.md` recorded D9 as "NOT HELD — blocked on the DLGF Gateway owner
pull" and D18 as "NOT HELD — mat_parcel_attrs is 100% NULL upstream". Both statements are true
STATEWIDE and both were wrong about Marion, because `in_marion_parcel_crosswalk` — pulled this
morning for an entirely different reason, to bridge Marion's local parcel ids to state ids —
carries the owner block:

    FULLOWNERNAME · OWNERADDRESS · OWNERADDRESS2 · OWNERCITY · OWNERSTATE · OWNERZIP
    OWNERFOREIGNSTATE · OWNERFOREIGNCOUNTRY

populated on ~99.9% of 347,049 parcels, beside STATEPARCELNUMBER. That is the whole D9 input and
the whole D18 input, for the largest county in the state, with no acquisition.

This is the Lane D lesson for the third time: PULL ALL COLUMNS, because an endpoint routinely
carries a signal nobody asked it for. It is also why `docs/TABLE_INVENTORY.md` now flags every
object that holds an owner column.

ABSENTEE IS GRADUATED, NOT BINARY. "Owner mails somewhere else" spans a landlord one suburb over
and a fund in another country, and those are not the same lead. Classes, widest first:
    foreign_country > out_of_state > out_of_county_in_state > same_city_different_address > local
`local` here means the mailing address matches the situs address — an owner-occupier, the weakest
possible approach signal.

ADMISSION IS NOT DECIDED HERE. The operator's standing ruling is that only distress which would
plausibly move an owner to sell is admitted into `has_si_signal`. Absentee ownership is an
APPROACHABILITY signal, not distress — an out-of-state owner is easier to approach, not in
trouble. So this builds and surfaces the signal and leaves `has_si_signal` untouched, with the
admission question put to the operator explicitly rather than answered quietly.

Writes only to energy-platfrom.indiana_app. energy.* is READ-ONLY.
"""
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
D85 = "080500000047000018"          # the inverted whole-Earth parcel; excluded from every join
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{DS}.in_si_d9_absentee_marion` AS
WITH x AS (
  SELECT
    REGEXP_REPLACE(STATEPARCELNUMBER, r'[^0-9]', '')      AS parcel_key,
    NULLIF(TRIM(FULLOWNERNAME), '')                        AS owner_name,
    NULLIF(TRIM(OWNERADDRESS), '')                         AS owner_address,
    NULLIF(TRIM(OWNERCITY), '')                            AS owner_city,
    UPPER(NULLIF(TRIM(OWNERSTATE), ''))                    AS owner_state,
    NULLIF(TRIM(OWNERZIP), '')                             AS owner_zip,
    NULLIF(TRIM(OWNERFOREIGNCOUNTRY), '')                  AS owner_country,
    NULLIF(TRIM(CITY), '')                                 AS situs_city,
    NULLIF(TRIM(ZIPCODE), '')                              AS situs_zip,
    NULLIF(TRIM(PROPERTY_CLASS), '')                       AS property_class,
    NULLIF(TRIM(PROPERTY_SUB_CLASS_DESCRIPTION), '')       AS property_class_desc,
    SAFE_CAST(NULLIF(TRIM(ASSESSORYEAR_TOTALAV), '') AS FLOAT64) AS assessed_value,
    -- situs street address, rebuilt from the crosswalk's own parts, to detect owner-occupancy
    TRIM(CONCAT(IFNULL(STNUMBER,''), ' ', IFNULL(PRE_DIR,''), ' ',
                IFNULL(STREET_NAME,''), ' ', IFNULL(SUFFIX,'')))  AS situs_address
  FROM `{DS}.in_marion_parcel_crosswalk`
  WHERE STATEPARCELNUMBER IS NOT NULL AND LENGTH(TRIM(STATEPARCELNUMBER)) > 1
),
j AS (
  SELECT x.*, s.occ_group, s.parcel_acres, s.exact_parcel_acres, s.outdoor_acres,
         s.mw_datacenter_4_per_acre, s.mw_bess_10_per_acre, s.lat, s.lon
  FROM x
  JOIN `{DS}.in_sites` s
    ON s.parcel_key = x.parcel_key AND s.parcel_source = 'parcels_in'
  WHERE s.parcel_key != '{D85}'          -- D85: matches everything if left in
)
SELECT
  'parcels_in' AS parcel_source, parcel_key,
  owner_name, owner_address, owner_city, owner_state, owner_zip, owner_country,
  situs_address, situs_city, situs_zip, property_class, property_class_desc, assessed_value,
  occ_group, parcel_acres, exact_parcel_acres, outdoor_acres,
  mw_datacenter_4_per_acre, mw_bess_10_per_acre, lat, lon,
  CASE
    WHEN owner_country IS NOT NULL                              THEN 'foreign_country'
    WHEN owner_state IS NULL                                     THEN 'unknown'
    WHEN owner_state != 'IN'                                     THEN 'out_of_state'
    -- in-state but mailing to a different town than the property sits in
    WHEN owner_city IS NOT NULL AND situs_city IS NOT NULL
         AND UPPER(owner_city) != UPPER(situs_city)              THEN 'out_of_county_in_state'
    -- same town, but the mailing address is not the property itself
    WHEN owner_address IS NOT NULL AND situs_address IS NOT NULL
         AND UPPER(REGEXP_REPLACE(owner_address, r'[^A-Za-z0-9]', ''))
           != UPPER(REGEXP_REPLACE(situs_address, r'[^A-Za-z0-9]', ''))
                                                                 THEN 'same_city_different_address'
    ELSE 'local_owner_occupied'
  END AS absentee_class,
  CASE
    WHEN owner_country IS NOT NULL THEN TRUE
    WHEN owner_state IS NOT NULL AND owner_state != 'IN' THEN TRUE
    ELSE FALSE
  END AS is_absentee_out_of_state,
  occ_group != 'residential' AS is_non_residential,
  CURRENT_TIMESTAMP() AS built_at
FROM j
"""

print("building in_si_d9_absentee_marion …")
job = client.query(SQL)
job.result()
print(f"  scanned {job.total_bytes_processed/1e9:.2f} GB")

n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_si_d9_absentee_marion`"))[0].n
print(f"  {n:,} Marion parcels with owner data, joined to the spine\n")

print("absentee class × non-residential (the operator ruling that gates admission):")
for r in client.query(f"""
SELECT absentee_class, COUNT(*) parcels,
       COUNTIF(is_non_residential) non_resid,
       COUNTIF(occ_group = 'ci') ci,
       COUNTIF(is_non_residential AND IFNULL(mw_bess_10_per_acre,0) >= 5) fits_bess,
       COUNTIF(is_non_residential AND IFNULL(mw_datacenter_4_per_acre,0) >= 25) fits_dc
FROM `{DS}.in_si_d9_absentee_marion` GROUP BY 1 ORDER BY parcels DESC"""):
    print(f"  {r.absentee_class:30s} {r.parcels:>8,}  non-res {r.non_resid:>6,}  "
          f"C/I {r.ci:>5,}  fits 5MW BESS {r.fits_bess:>4,}  fits 25MW DC {r.fits_dc:>4,}")

print("\nD18 owner contact — how many carry a usable owner NAME?")
r = list(client.query(f"""SELECT COUNT(*) n, COUNTIF(owner_name IS NOT NULL) named,
  COUNT(DISTINCT owner_name) distinct_owners,
  COUNTIF(owner_name IS NOT NULL AND is_non_residential) named_nonres
FROM `{DS}.in_si_d9_absentee_marion`"""))[0]
print(f"  {r.named:,} of {r.n:,} carry an owner name · {r.distinct_owners:,} distinct owners "
      f"· {r.named_nonres:,} of them non-residential")

print("\nthe biggest non-residential absentee owners (a portfolio approach list):")
for r in client.query(f"""
SELECT owner_name, owner_state, COUNT(*) parcels,
       ROUND(SUM(IFNULL(exact_parcel_acres, parcel_acres)), 1) acres
FROM `{DS}.in_si_d9_absentee_marion`
WHERE is_absentee_out_of_state AND is_non_residential AND owner_name IS NOT NULL
GROUP BY 1,2 ORDER BY acres DESC LIMIT 10"""):
    print(f"  {str(r.owner_name)[:44]:44s} {str(r.owner_state):3s} {r.parcels:>4} parcels {r.acres:>9,.1f} ac")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_si_d9_absentee_marion'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
    f"VALUES (@t,@s,@m,@n,@g,CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "in_si_d9_absentee_marion"),
        bigquery.ScalarQueryParameter("s", "STRING",
            "energy-platfrom.indiana_app.in_marion_parcel_crosswalk (gis.indy.gov sde_Parcel "
            "MapServer/5) x in_sites"),
        bigquery.ScalarQueryParameter("m", "STRING",
            "D9 absentee + D18 owner contact for Marion, derived from owner mailing fields the "
            "crosswalk already carried. Graduated: foreign_country > out_of_state > "
            "out_of_county_in_state > same_city_different_address > local_owner_occupied. "
            "D85 (080500000047000018) excluded from the join."),
        bigquery.ScalarQueryParameter("n", "INT64", int(n)),
        bigquery.ScalarQueryParameter("g", "FLOAT64", round(job.total_bytes_processed / 1e9, 3)),
        bigquery.ScalarQueryParameter("no", "STRING",
            "MARION ONLY — 1 of 92 counties. This is a PUBLISHING footprint, not statewide "
            "coverage; its absence elsewhere is OUR gap, not the absence of absentee owners, and "
            "a statewide ranking must not weight it as if it were evenly available. Statewide D9 "
            "still needs the DLGF Gateway pull. "
            "NOT admitted into has_si_signal: absentee ownership is APPROACHABILITY, not distress, "
            "and the operator's standing ruling admits only distress that would plausibly move an "
            "owner to sell. Admission is an open operator question.")])).result()
print("\nregistered in_si_d9_absentee_marion")
