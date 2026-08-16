"""Place the Indianapolis code-enforcement corpus using Indy's OWN address authority.

THE GAP. We hold 54,995 rows of the strongest derived abandoned-building evidence in the estate —
29,108 'Unsafe Buildings' and 25,887 'Vacant Board Order' cases, ~24,789 distinct addresses, all
carrying OPEN_DATE — and they reach **711 parcels**. The generic address bridge cannot help:
its Indianapolis coverage is ~2,713 resolved addresses, and D12's 747,122 rows match ZERO because
their addresses carry no city suffix.

THE FIX IS NOT A GEOCODER. Indy publishes its own address authority, and it already carries the
parcel key:

    gis.indy.gov/.../sde_Addressing/sde_Addressing/MapServer/0  'Address'
    465,050 addresses · FULL_ADDRESS ('15 W ARIZONA ST') + STATEPARCELNUMBER + PARCEL_I

Same publisher as the code corpus, so the address TEXT agrees without an invented normaliser.
This is a published crosswalk, not an estimate — which matters, because a geocoded rooftop is an
estimate and would have to be styled as one.

WHY THE MATCH IS DELIBERATELY CONSERVATIVE. Both sides are canonicalised IDENTICALLY (upper, strip
punctuation, collapse whitespace) and nothing else. No street-type expansion, no fuzzy matching,
no nearest-neighbour. A one-sided fix-up aimed at one source's quirks is how a wrong parcel gets
flagged as evidence; this project has already recorded that trap for D12. Whatever the yield is,
it is reported rather than improved by loosening the join.

Writes, and registers in the same run:
  in_si_indy_code_placed   Unsafe Buildings + Vacant Board Order, placed on a parcel, WITH dates
"""
import datetime
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
D85 = "080500000047000018"
client = bigquery.Client(project="energy-platfrom")
BUILT = datetime.datetime.now(datetime.timezone.utc).isoformat()


def q1(sql): return list(client.query(sql))[0]


CANON = """
CREATE TEMP FUNCTION canon(s STRING) AS (
  TRIM(REGEXP_REPLACE(REGEXP_REPLACE(UPPER(IFNULL(s,'')), r'[.,#]', ''), r'\\s+', ' ')));
CREATE TEMP FUNCTION pdate(s STRING) AS (
  CASE WHEN s IS NULL OR TRIM(s) IN ('','None','NA','null') THEN NULL
       WHEN REGEXP_CONTAINS(s, r'^[0-9]{13}$') THEN DATE(TIMESTAMP_MILLIS(CAST(s AS INT64)))
       WHEN REGEXP_CONTAINS(s, r'^[0-9]{10}$') THEN DATE(TIMESTAMP_SECONDS(CAST(s AS INT64)))
       WHEN REGEXP_CONTAINS(s, r'^[0-9]{4}-[0-9]{2}-[0-9]{2}') THEN SAFE.PARSE_DATE('%Y-%m-%d', SUBSTR(s,1,10))
       ELSE NULL END);
"""

SQL = f"""{CANON}
CREATE OR REPLACE TABLE `{DS}.in_si_indy_code_placed` AS
WITH addr AS (
  SELECT canon(FULL_ADDRESS) ak,
         REGEXP_REPLACE(STATEPARCELNUMBER, r'[^0-9]', '') pk
  FROM `{DS}.in_marion_address_crosswalk`
  WHERE FULL_ADDRESS IS NOT NULL AND STATEPARCELNUMBER IS NOT NULL
    AND LENGTH(REGEXP_REPLACE(STATEPARCELNUMBER, r'[^0-9]','')) = 18),
-- an address that maps to MORE THAN ONE parcel cannot place a case on one of them without
-- guessing, so those are excluded and counted rather than resolved arbitrarily
-- NOTE the alias: naming the output `pk` would make `MAX(pk)` in HAVING resolve to the ALIAS
-- (i.e. MAX(MIN(pk))), which BigQuery rejects as an aggregation of an aggregation.
addr1 AS (SELECT ak, MIN(pk) AS parcel_pk FROM addr GROUP BY ak HAVING MIN(pk) = MAX(pk)),
code AS (
  SELECT canon(STREET_ADDRESS) ak,
         IF(CASE_TYPE LIKE '%Unsafe Buildings%', 'D5_unsafe_building', 'D5_vacant_board_order') signal,
         pdate(OPEN_DATE) obs, CASE_NUMBER, CASE_STATUS, OWNER
  FROM `{DS}.in_si_refresh_indy_code_enforcement`
  WHERE (CASE_TYPE LIKE '%Unsafe Buildings%' OR CASE_TYPE LIKE '%Vacant Board Order%')
    AND STREET_ADDRESS IS NOT NULL)
SELECT c.signal, x.parcel_pk AS parcel_key, c.ak AS address_canon,
       c.obs AS event_date, c.CASE_NUMBER case_number, c.CASE_STATUS case_status, c.OWNER owner_name,
       TIMESTAMP('{BUILT}') AS built_at
FROM code c JOIN addr1 x ON x.ak = c.ak
WHERE x.parcel_pk != '{D85}'
"""
job = client.query(SQL); job.result()
print(f"built in_si_indy_code_placed ({job.total_bytes_processed/1e9:.2f} GB)")

# --- measure, honestly: what fraction of the corpus actually landed? --------------------------
before = q1(f"""SELECT COUNT(*) n, COUNT(DISTINCT STREET_ADDRESS) addrs
  FROM `{DS}.in_si_refresh_indy_code_enforcement`
  WHERE CASE_TYPE LIKE '%Unsafe Buildings%' OR CASE_TYPE LIKE '%Vacant Board Order%'""")
after = q1(f"""SELECT COUNT(*) n, COUNT(DISTINCT parcel_key) parcels,
  COUNT(DISTINCT address_canon) addrs, COUNTIF(event_date IS NOT NULL) dated,
  MIN(event_date) mn, MAX(event_date) mx
  FROM `{DS}.in_si_indy_code_placed`""")
print(f"\ncorpus  : {before.n:,} rows across {before.addrs:,} distinct addresses")
print(f"placed  : {after.n:,} rows ({100*after.n/before.n:.1f}%) on {after.parcels:,} parcels "
      f"from {after.addrs:,} addresses")
print(f"dated   : {after.dated:,} · {after.mn} .. {after.mx}")
print(f"was     : 711 parcels via the generic address bridge")

print("\nby signal, and what the non-residential ruling will admit:")
for r in client.query(f"""SELECT p.signal, COUNT(*) rows_, COUNT(DISTINCT p.parcel_key) parcels,
    COUNT(DISTINCT IF(s.occ_group != 'residential', p.parcel_key, NULL)) nonres,
    COUNT(DISTINCT IF(s.occ_group = 'ci', p.parcel_key, NULL)) ci
  FROM `{DS}.in_si_indy_code_placed` p
  LEFT JOIN `{DS}.in_sites` s USING (parcel_key)
  GROUP BY 1 ORDER BY parcels DESC"""):
    print(f"  {r.signal:26s} rows={r.rows_:>7,} parcels={r.parcels:>6,} "
          f"NON-RESIDENTIAL={r.nonres:>5,} C/I={r.ci:>4,}")

n = int(after.n)
client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_si_indy_code_placed'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at) "
    f"VALUES (@t,@s,@m,@n,CURRENT_TIMESTAMP())",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "in_si_indy_code_placed"),
        bigquery.ScalarQueryParameter(
            "s", "STRING",
            "indiana_app.in_si_refresh_indy_code_enforcement + in_marion_address_crosswalk"),
        bigquery.ScalarQueryParameter(
            "m", "STRING",
            "Unsafe Buildings + Vacant Board Order cases placed on parcels through Indy's OWN "
            "address authority (sde_Addressing layer 0, 465,050 addresses carrying FULL_ADDRESS "
            "and STATEPARCELNUMBER). Same publisher as the code corpus, so no invented "
            "normalisation: both sides canonicalised IDENTICALLY (upper, strip punctuation, "
            "collapse whitespace) and nothing more. A published crosswalk, not a geocode "
            "estimate. D85 excluded."),
        bigquery.ScalarQueryParameter("n", "INT64", n)])).result()
print(f"\nregistered in_si_indy_code_placed ({n:,})")
