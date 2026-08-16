"""D11 + D27 (+ D19) — wire the OWNER-GRAIN signals at the grain they actually support.

WHAT THE MEASUREMENT SAYS, before any wiring. The backlog item was "fold staged D11/D21/D27 into
the signal corpus". D21 folded fine (it is address- and parcel-keyed). D11 and D27 do NOT:

    D11 entity dissolutions   983 rows -> address bridge matches      2 parcels
    D27 UCC lapses            156 rows -> address bridge matches      0 parcels

Canonicalising BOTH sides identically (strip punctuation, then strip street-type words) moves D11
from 2 to 6 and D27 from 0 to 0. So this is not a surface-form problem that a normaliser fixes —
and pushing further would be inventing matches. The cities ARE covered (123 of 154 D11 cities and
44 of 56 D27 cities appear in the bridge); the specific street addresses are not.

WHY, AND WHY MATCHING HARDER WOULD BE WRONG: these are BUSINESS REGISTRY addresses. A dissolved
entity's address of record is frequently its registered agent's office or a mailing address, not
the site it operated. A successful street match would therefore often point at a lawyer's office
and flag the WRONG parcel — worse than no match, because it would look like evidence.

THE REAL BLOCKER IS THE SAME ONE AS D9 AND D18. An owner-keyed signal reaches a parcel through
the OWNER NAME, and `energy.mat_parcel_attrs.parcel_owner` is NULL on all 3,553,381 Indiana rows
(B1, filed upstream). Measured again here rather than recalled. **D11 and D27 become parcel-
reachable the moment the DLGF Gateway owner pull lands** — which is the strongest argument yet
for prioritising B1/D9/D18, since one acquisition unblocks five signals rather than three.

SO THEY ARE WIRED AT OWNER/COUNTY GRAIN, which is honest and still useful: a siter looking at a
county can see how many businesses there have dissolved or had a UCC lapse recently, and those
are real leads to work by name. County is INFERRED from the city (the sources publish no county),
via the modal county of that city's parcels in the bridge — labelled as inferred, never published.

D19 (WARN layoff notices) is included because it is the same shape: owner-name keyed, reaching
just 2 parcels. Grouping the three makes the owner-grain block visible as a block, instead of
three separate near-zeros that each look like a failure.

Writes, and registers in the same run:
  in_si_owner_signals          entity-grain, dated, with inferred county
  in_si_owner_signals_county   per-county rollup for the SI Feed / Community pages
"""
import datetime
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")
BUILT = datetime.datetime.now(datetime.timezone.utc).isoformat()


def q1(sql): return list(client.query(sql))[0]


def run(sql, label):
    job = client.query(sql); job.result()
    print(f"  {label}: {job.total_bytes_processed/1e9:.2f} GB", flush=True)


# --- 0. re-measure the two claims this build rests on, rather than trusting the docstring ------
owner = q1(f"""SELECT COUNT(*) n, COUNTIF(parcel_owner IS NOT NULL) named
               FROM `{EN}.mat_parcel_attrs` WHERE state='IN'""")
print(f"B1 re-measured: mat_parcel_attrs IN rows={owner.n:,}, with an owner name={owner.named:,}")
if owner.named > 0:
    print("  *** OWNER NAMES HAVE APPEARED UPSTREAM — the owner->parcel route is now OPEN. ***")
    print("  *** Re-open D11/D27/D9/D18 as parcel-grain signals before accepting this build. ***")

# --- 1. city -> county, inferred from the bridge (the sources publish no county) ---------------
print("building in_si_owner_signals …", flush=True)
run(f"""
CREATE OR REPLACE TABLE `{DS}.in_si_owner_signals` AS
WITH city_county AS (
  SELECT city, county_fips, n,
         ROW_NUMBER() OVER (PARTITION BY city ORDER BY n DESC) rk
  FROM (
    SELECT UPPER(TRIM(REGEXP_EXTRACT(b.address_norm, r'([A-Z][A-Z ]+)$'))) city,
           sc.county_fips, COUNT(*) n
    FROM `{DS}.in_si_address_parcel_bridge` b
    JOIN `{DS}.in_sites_county` sc USING (parcel_source, parcel_key)
    WHERE REGEXP_EXTRACT(b.address_norm, r'([A-Z][A-Z ]+)$') IS NOT NULL
    GROUP BY 1, 2)),
cc AS (SELECT city, county_fips FROM city_county WHERE rk = 1),
sig AS (
  SELECT 'D11_entity_dissolution' signal, entity_name AS party, raw_status AS detail,
         observed_date AS event_date, address_line, UPPER(TRIM(city)) city,
         'in_si_d11_admitted' source_table
  FROM `{DS}.in_si_d11_admitted`
  UNION ALL
  SELECT 'D27_ucc_lapse', debtor_name, raw_filing_type, lapse_date,
         address_line, UPPER(TRIM(city)), 'in_si_d27_admitted'
  FROM `{DS}.in_si_d27_admitted`
  UNION ALL
  SELECT 'D19_warn', owner_name, signal, observed_date,
         CAST(NULL AS STRING), CAST(NULL AS STRING), 'in_si_signals'
  FROM `{DS}.in_si_signals` WHERE signal='D19_warn' AND keying='owner_name'
)
SELECT s.signal, s.party, s.detail, s.event_date, s.address_line, s.city,
       cc.county_fips,
       IF(cc.county_fips IS NULL, NULL, 'inferred from city, not published by the source')
         AS county_basis,
       s.event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 YEAR) AS within_3y,
       s.event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 5 YEAR) AS within_5y,
       s.source_table,
       FALSE AS parcel_reachable,   -- measured: 6 of 983 and 0 of 156; see the docstring
       TIMESTAMP('{BUILT}') AS built_at
FROM sig s LEFT JOIN cc ON cc.city = s.city
""", "in_si_owner_signals")

print("building in_si_owner_signals_county …", flush=True)
run(f"""
CREATE OR REPLACE TABLE `{DS}.in_si_owner_signals_county` AS
SELECT county_fips,
  COUNTIF(signal='D11_entity_dissolution') dissolutions,
  COUNTIF(signal='D27_ucc_lapse') ucc_lapses,
  COUNTIF(signal='D19_warn') warn_notices,
  COUNTIF(within_3y) events_3y, COUNTIF(within_5y) events_5y,
  COUNT(*) events_total, MAX(event_date) last_event,
  TIMESTAMP('{BUILT}') AS built_at
FROM `{DS}.in_si_owner_signals`
WHERE county_fips IS NOT NULL GROUP BY 1
""", "in_si_owner_signals_county")

# --- 2. measure ------------------------------------------------------------------------------
print("\n--- MEASURED ---")
for r in client.query(f"""SELECT signal, COUNT(*) n,
    COUNTIF(event_date IS NOT NULL) dated, COUNTIF(within_3y) r3,
    COUNTIF(county_fips IS NOT NULL) with_county, COUNT(DISTINCT county_fips) counties,
    MIN(event_date) mn, MAX(event_date) mx
  FROM `{DS}.in_si_owner_signals` GROUP BY 1 ORDER BY n DESC"""):
    print(f"  {r.signal:26s} n={r.n:>5,} dated={r.dated:>5,} 3y={r.r3:>4,} "
          f"county-inferred={r.with_county:>5,} ({r.counties} counties)  {r.mn}..{r.mx}")

tot = q1(f"""SELECT COUNT(*) n, COUNT(DISTINCT county_fips) co,
  COUNTIF(county_fips IS NULL) no_co FROM `{DS}.in_si_owner_signals`""")
print(f"  TOTAL {tot.n:,} rows · {tot.co} counties inferred · {tot.no_co:,} with no county "
      f"(shown as cannot-assess, never as zero)")

# --- 3. register -----------------------------------------------------------------------------
reg = [
 ("in_si_owner_signals", int(tot.n),
  "indiana_app.in_si_d11_admitted + in_si_d27_admitted + in_si_signals(D19_warn)",
  "OWNER-GRAIN seller-intent signals, unioned and dated. They are NOT parcel-keyed and the "
  "measurement says they cannot be: the address bridge matches 6 of 983 (D11) and 0 of 156 "
  "(D27), and these are business-registry addresses where a street match would often point at "
  "a registered agent's office rather than the site. The route that WOULD work is owner name, "
  "blocked by mat_parcel_attrs.parcel_owner being NULL on all 3,553,381 Indiana rows (B1). "
  "County is INFERRED from the city via the modal county of that city's bridge parcels."),
 ("in_si_owner_signals_county",
  int(q1(f"SELECT COUNT(*) n FROM `{DS}.in_si_owner_signals_county`").n),
  "indiana_app.in_si_owner_signals",
  "per-county counts of dissolutions, UCC lapses and WARN notices, with 3y/5y recency, for the "
  "SI Feed and Community pages. Counties with no inferred rows are absent, not zero."),
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
print("\nDONE")
