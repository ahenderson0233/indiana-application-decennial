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
# stdout must survive its own output: this console is cp1252 and characters like U+2248/U+2192/U+2717 raise
# UnicodeEncodeError from print() itself. The honesty audit once crashed on its own
# FAILURE path for exactly this reason. Degrade the glyph, never the run.
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
WITH inc AS (
  SELECT '2020' AS yr, INCIDENT_KEY, STATE, FDID, INC_DATE, INC_TYPE,
         PROP_LOSS, CONT_LOSS, PROP_VAL, PROP_USE, OTH_DEATH, OTH_INJ
  FROM `{DS}.in_nfirs_basicincident_2020` WHERE STATE = 'IN'
  UNION ALL
  SELECT '2021', INCIDENT_KEY, STATE, FDID, INC_DATE, INC_TYPE,
         PROP_LOSS, CONT_LOSS, PROP_VAL, PROP_USE, OTH_DEATH, OTH_INJ
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
       -- SEVERITY (operator ruling 2026-08-15): a minor contained fire does not move an owner to
       -- sell, so loss dollars decide whether an incident is seller intent at all. Measured:
       -- 6,322 of 8,119 structure fires in 2021 report ZERO property loss.
       SAFE_CAST(i.PROP_LOSS AS INT64) AS property_loss_usd,
       SAFE_CAST(i.CONT_LOSS AS INT64) AS contents_loss_usd,
       SAFE_CAST(i.PROP_VAL AS INT64) AS property_value_usd,
       CASE WHEN IFNULL(SAFE_CAST(i.PROP_LOSS AS INT64), 0)
                 + IFNULL(SAFE_CAST(i.CONT_LOSS AS INT64), 0) >= 500000 THEN 'catastrophic >=$500k'
            WHEN IFNULL(SAFE_CAST(i.PROP_LOSS AS INT64), 0)
                 + IFNULL(SAFE_CAST(i.CONT_LOSS AS INT64), 0) >= 100000 THEN 'major >=$100k'
            WHEN IFNULL(SAFE_CAST(i.PROP_LOSS AS INT64), 0)
                 + IFNULL(SAFE_CAST(i.CONT_LOSS AS INT64), 0) >= 10000 THEN 'moderate >=$10k'
            WHEN IFNULL(SAFE_CAST(i.PROP_LOSS AS INT64), 0)
                 + IFNULL(SAFE_CAST(i.CONT_LOSS AS INT64), 0) > 0 THEN 'minor <$10k'
            ELSE 'no loss reported' END AS severity,
       -- PROPERTY USE (operator ruling): SI only counts at the NON-RESIDENTIAL level. NFIRS 5.0
       -- property-use codes 400-499 are residential (419 = 1-family, 429 = multifamily); 100s
       -- assembly, 200s educational, 300s health/detention, 500s mercantile, 600s utility/
       -- industrial, 700s manufacturing, 800s storage, 900s outside/special.
       i.PROP_USE AS property_use_code,
       CASE WHEN i.PROP_USE IS NULL OR CAST(i.PROP_USE AS STRING) IN ('','NNN','UUU')
              THEN 'unknown'
            WHEN SAFE_CAST(i.PROP_USE AS INT64) BETWEEN 400 AND 499 THEN 'residential'
            WHEN SAFE_CAST(i.PROP_USE AS INT64) IS NULL THEN 'unknown'
            ELSE 'non-residential' END AS property_class,
       SAFE_CAST(i.OTH_DEATH AS INT64) AS civilian_deaths,
       SAFE_CAST(i.OTH_INJ AS INT64) AS civilian_injuries,
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
    SELECT yr, COUNT(*) fires,
           COUNTIF(property_class='non-residential') non_res,
           COUNTIF(severity != 'no loss reported') with_loss,
           COUNTIF(property_class='non-residential' AND severity IN
                   ('moderate >=$10k','major >=$100k','catastrophic >=$500k')) si_grade,
           COUNTIF(address_quality='number + street') keyable
    FROM `{DS}.in_nfirs_structure_fires` GROUP BY 1 ORDER BY 1"""):
    print(f"  {r.yr}: {r.fires:,} structure fires · {r.non_res:,} non-residential · "
          f"{r.with_loss:,} with any loss · **{r.si_grade:,} SI-GRADE** (non-res + >=$10k loss) · "
          f"{r.keyable:,} keyable")
print("\n  severity x property class:")
for r in client.query(f"""
    SELECT property_class, severity, COUNT(*) n FROM `{DS}.in_nfirs_structure_fires`
    GROUP BY 1,2 ORDER BY property_class, n DESC"""):
    print(f"    {r.property_class:<16} {r.severity:<22} {r.n:>6,}")
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
