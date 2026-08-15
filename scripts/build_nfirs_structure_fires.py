"""A4 — NFIRS structure fires, wired (not waived), with two defects fixed on the way in.

Measured before deciding:

  1. THESE TABLES ARE NOT A FIRE SIGNAL AS THEY STAND. Only ~21% of incidents are structure
     fires (8,145 of 38,287 in 2020; 8,119 of 38,492 in 2021). The rest is everything else a
     department logs — gas leaks (INC_TYPE 412), downed power lines (444), rubbish fires (151),
     vehicle fires (131), cooking fires (113). Admitting all 38k as "fires" would inflate D16
     roughly fivefold. Filtered to NFIRS INC_TYPE 111-123, the building/structure range.

  2. in_nfirs_fireincident_2024 IS NOT INDIANA-CLIPPED. Only 848 of its 1,255 rows are STATE='IN';
     407 (32%) belong to 43 other states — IL 74, OH 49, KY 29, MI 25, FL 22, CA 22, TX 12 …
     An `in_*` table in the Indiana dataset carrying a third out-of-state rows breaks the
     standing "Indiana only, clipped at the border" rule and would silently corrupt any count
     built on it. Every query here filters STATE='IN' explicitly rather than trusting the name.
     (2020 and 2021 are clean: 100% IN.)

  3. The addresses are GOOD, better than expected: of 8,119 structure fires in 2021, 8,102 carry
     a street name (99.8%), 7,387 a street number (91.0%) and all 8,119 a ZIP. That is enough to
     key to a parcel later through the address ladder — so this is wired as an address-grain
     CANDIDATE with its keying quality stated, not claimed as a parcel-level signal it has not
     yet earned.

Creates in_nfirs_structure_fires, registered in the same run.
"""
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
WITH inc AS (
  SELECT '2020' AS yr, INCIDENT_KEY, STATE, FDID, INC_DATE, INC_TYPE
  FROM `{DS}.in_nfirs_basicincident_2020` WHERE STATE = 'IN'
  UNION ALL
  SELECT '2021', INCIDENT_KEY, STATE, FDID, INC_DATE, INC_TYPE
  FROM `{DS}.in_nfirs_basicincident_2021` WHERE STATE = 'IN'),
addr AS (
  SELECT INCIDENT_KEY, NUM_MILE, STREET_PRE, STREETNAME, STREETTYPE, CITY, ZIP5
  FROM `{DS}.in_nfirs_incidentaddress_2020` WHERE STATE = 'IN'
  UNION ALL
  SELECT INCIDENT_KEY, NUM_MILE, STREET_PRE, STREETNAME, STREETTYPE, CITY, ZIP5
  FROM `{DS}.in_nfirs_incidentaddress_2021` WHERE STATE = 'IN'),
-- fireincident carries the NOT_RES flag: the non-residential subset is the C&I-relevant half
fire AS (
  SELECT INCIDENT_KEY, NOT_RES, BLDG_INVOL, ACRES_BURN
  FROM `{DS}.in_nfirs_fireincident_2020` WHERE STATE = 'IN'
  UNION ALL
  SELECT INCIDENT_KEY, NOT_RES, BLDG_INVOL, ACRES_BURN
  FROM `{DS}.in_nfirs_fireincident_2021` WHERE STATE = 'IN'
  UNION ALL
  SELECT INCIDENT_KEY, NOT_RES, BLDG_INVOL, ACRES_BURN
  FROM `{DS}.in_nfirs_fireincident_2024` WHERE STATE = 'IN')
SELECT i.yr, i.INCIDENT_KEY AS incident_key, i.FDID AS fdid,
       SAFE.PARSE_DATE('%m%d%Y', i.INC_DATE) AS incident_date,
       i.INC_TYPE AS inc_type,
       TRIM(CONCAT(IFNULL(a.NUM_MILE,''), ' ', IFNULL(a.STREET_PRE,''), ' ',
                   IFNULL(a.STREETNAME,''), ' ', IFNULL(a.STREETTYPE,''))) AS street_address,
       a.CITY AS city, a.ZIP5 AS zip5,
       f.NOT_RES AS non_residential, f.BLDG_INVOL AS buildings_involved,
       -- keying quality, stated per row rather than assumed downstream
       CASE WHEN a.STREETNAME IS NULL OR TRIM(CAST(a.STREETNAME AS STRING)) IN ('','None')
              THEN 'no street name'
            WHEN a.NUM_MILE IS NULL OR TRIM(CAST(a.NUM_MILE AS STRING)) IN ('','None')
              THEN 'street only, no number'
            ELSE 'number + street' END AS address_quality
FROM inc i
LEFT JOIN addr a USING (INCIDENT_KEY)
LEFT JOIN fire f USING (INCIDENT_KEY)
WHERE SAFE_CAST(i.INC_TYPE AS INT64) BETWEEN 111 AND 123
"""

dry = client.query(SQL, job_config=bigquery.QueryJobConfig(dry_run=True))
gb = dry.total_bytes_processed / 1e9
print(f"dry-run {gb:.3f} GB")
client.query(f"CREATE OR REPLACE TABLE `{DS}.in_nfirs_structure_fires` AS\n{SQL}").result()

for r in client.query(f"""
    SELECT yr, COUNT(*) fires, COUNTIF(non_residential='Y') non_res,
           COUNTIF(address_quality='number + street') keyable,
           COUNT(DISTINCT city) cities
    FROM `{DS}.in_nfirs_structure_fires` GROUP BY 1 ORDER BY 1"""):
    print(f"  {r.yr}: {r.fires:,} structure fires · {r.non_res:,} non-residential · "
          f"{r.keyable:,} with number+street · {r.cities} cities")
n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_nfirs_structure_fires`"))[0].n

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_nfirs_structure_fires'").result()
client.query(f"""INSERT `{DS}._registry`
  (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES (@t,@s,@m,@n,@g,CURRENT_TIMESTAMP(),@o)""",
  job_config=bigquery.QueryJobConfig(query_parameters=[
    bigquery.ScalarQueryParameter("t", "STRING", "in_nfirs_structure_fires"),
    bigquery.ScalarQueryParameter("s", "STRING",
      "indiana_app.in_nfirs_basicincident_2020/2021 x in_nfirs_incidentaddress_* x in_nfirs_fireincident_*"),
    bigquery.ScalarQueryParameter("m", "STRING",
      "INC_TYPE 111-123 (building/structure fires) only, STATE='IN' enforced on every input"),
    bigquery.ScalarQueryParameter("n", "INT64", n),
    bigquery.ScalarQueryParameter("g", "FLOAT64", round(gb, 4)),
    bigquery.ScalarQueryParameter("o", "STRING",
      "D16 candidate at ADDRESS grain - not yet keyed to parcels, and not claimed to be. Two "
      "defects fixed on the way in: (1) only ~21% of NFIRS incidents are structure fires, so "
      "admitting the raw tables would have inflated D16 about fivefold; (2) "
      "in_nfirs_fireincident_2024 is NOT Indiana-clipped - 407 of 1,255 rows (32%) are from 43 "
      "other states - so STATE='IN' is enforced explicitly rather than trusting the in_* name. "
      "Keying quality is carried per row: ~91% have number+street.")])).result()
print(f"in_nfirs_structure_fires: {n:,} rows, registered")
