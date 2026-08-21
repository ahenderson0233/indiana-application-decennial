"""G152: TWO NEW SI SIGNALS THE 13-COLUMN REDUCTION COULD NOT HAVE PRODUCED.

Operator, 2026-08-21: *"when you do this, you may find additional signals beyond the ones we are
searching for, and those should be documented and updated accordingly, including wiring them into
the application, if warranted."*

================================================================================================
⭐ WHY THIS IS THE PROOF OF G152
================================================================================================
`energy.si_signals` reduces every source to 13 columns — signal, state, county_fips, parcel_key,
address_norm, owner_name, keying, flag, value_num, observed_date, source_id, ingested_at,
quality_mult. Under that shape `edgar_abs_ee_cmbs` could only ever produce ONE signal, because one
date and one flag is all that survives. It produced `D20_loan_maturity`, 419 rows.

The parent carries **153 columns on 19,187 Indiana rows covering 1,173 distinct properties**, and
it is a *servicer's monthly report on a commercial building*. It knows whether the loan is being
worked out, whether the borrower is paying, whether income covers debt service, how full the
building is, who the largest tenant is, and when that tenant's lease ends.

⛔ A SOURCE REDUCED TO A DATE AND A FLAG PRODUCES EXACTLY ONE SIGNAL BY CONSTRUCTION. That is not
an opinion about this dataset; it is arithmetic about the schema.

================================================================================================
THE TWO SIGNALS, AND THE "SO WHAT" FOR EACH
================================================================================================
⭐ **D28_cmbs_loan_distress** — the LENDER is under pressure on this specific building.
   Delinquent, in a servicer workout, transferred to special servicing, or income below debt
   service. **So what:** a special-serviced loan is the single most reliable predictor that a
   commercial property will trade, because the servicer's mandate is to resolve it — and unlike a
   tax sale the owner is usually willing to negotiate before it gets that far.

⭐ **D29_anchor_tenant_exit** — the BUILDING is emptying.
   Physical occupancy at or below 60%, or the largest tenant's lease expiring within 24 months.
   **So what:** a half-empty building with an anchor rolling off is an owner who needs a plan. For
   a data-centre or BESS developer this is the moment a re-use conversation is welcome.

⚠ THEY ARE DELIBERATELY NOT FIVE SIGNALS. Delinquency, workout, special servicing and DSCR are
four measurements of one condition — the loan is in trouble — and splitting them would let one
building present as four independent reasons to sell. The components are carried as columns so the
dossier can say WHICH, without inflating the signal count.

================================================================================================
⛔ THREE FORMAT TRAPS IN THIS SOURCE, ALL OF WHICH PRODUCED A WRONG NUMBER FIRST
================================================================================================
1. **Dates are `MM-DD-YYYY` STRINGS.** `SAFE_CAST(maturitydate AS DATE)` returns NULL on every
   row, so the first measurement reported **0 loans maturing within 24 months** and 0 anchor
   leases expiring. Parsed properly it is 95 and 109. An ISO parse on a non-ISO date does not
   error, it returns nothing — the exact failure mode this project already documented for Esri
   epoch-milliseconds.
2. **Occupancy is a FRACTION, and `0` is the null sentinel.** `0.8534` means 85.34%. Counting
   `<= 60` on the raw value reported **705 properties at or below 60% occupancy**; almost all of
   them are unpublished zeros. Corrected: 39 of the 603 that publish a figure.
   ⚠ *Unpublished is NULL, never 0* — the same rule that produced 95 false "below floor" rate
   violations earlier in this project.
3. **`paymentstatusloancode` is a CREFC code, not a number.** `0` is *current*; `A` and `B` are
   grace-period and under-30-days, which are NOT distress; `1`/`2`/`3` are 30/60/90+ days and `5`
   is a non-performing matured balloon. Reading it as "non-zero means late" would admit the 20
   rows that are explicitly fine.

⚠ THE EVENT DATE FOR D29 IS USUALLY IN THE FUTURE — a lease expires next year. That is only
  renderable because G145 taught the spine to carry a scheduled future date instead of collapsing
  it to "date unknown". These two rows were built in the same session for that reason.

RE-SCRAPE COMMAND: python scripts/build_si_cmbs_signals.py
⚠ IDEMPOTENT: replace_safe. Depends on in_si_up_cmbs (scripts/build_si_upstream_wide.py).
⛔ AND RE-RUN THE SPINE AFTERWARDS: scripts/build_si_signal_v2.py, then the exporters.
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
OUT = f"{DS}.in_si_cmbs_placed"
D85 = "080500000047000018"
client = bigquery.Client(project="energy-platfrom")

# ⚠ THE SAME NORMALISER AS build_warn_placement.py, AND THAT IS A KNOWN DUPLICATE. It is repeated
# rather than imported because the two scripts must be independently re-runnable, and the lists are
# asserted identical by scripts/audit_si_upstream_width.py so they cannot drift apart silently.
SUFFIXES = [("STREET", "ST"), ("AVENUE", "AVE"), ("ROAD", "RD"), ("DRIVE", "DR"),
            ("BOULEVARD", "BLVD"), ("PARKWAY", "PKWY"), ("LANE", "LN"), ("COURT", "CT"),
            ("PLACE", "PL"), ("CIRCLE", "CIR"), ("HIGHWAY", "HWY"), ("TERRACE", "TER"),
            ("TRAIL", "TRL"), ("SUITE", ""), ("STE", ""), ("UNIT", ""), ("BUILDING", ""),
            ("BLDG", "")]
DIRECTIONALS = [("NORTH", "N"), ("SOUTH", "S"), ("EAST", "E"), ("WEST", "W"),
                ("NORTHEAST", "NE"), ("NORTHWEST", "NW"), ("SOUTHEAST", "SE"),
                ("SOUTHWEST", "SW")]


def naddr(col, drop_dir=False):
    e = f"UPPER(TRIM({col}))"
    e = f"REGEXP_REPLACE({e}, r'[^A-Z0-9 ]', ' ')"
    for long, short in SUFFIXES:
        e = f"REGEXP_REPLACE({e}, r'\\b{long}\\b', '{short}')"
    for long, short in DIRECTIONALS:
        e = f"REGEXP_REPLACE({e}, r'\\b{long}\\b', '{short}')"
    if drop_dir:
        e = f"REGEXP_REPLACE({e}, r'\\b(N|S|E|W|NE|NW|SE|SW)\\b', ' ')"
    return f"TRIM(REGEXP_REPLACE({e}, r' +', ' '))"


def ncity(col):
    return (f"TRIM(REGEXP_REPLACE(REGEXP_REPLACE(UPPER(TRIM({col})), r'[^A-Z0-9]', ''), "
            r"r' +', ' '))")


# `D` = the parsed-date helper. Every date column in this source is MM-DD-YYYY text.
def D(col):
    return f"SAFE.PARSE_DATE('%m-%d-%Y', {col})"


def F(col):
    return f"SAFE_CAST({col} AS FLOAT64)"


SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH latest AS (
  -- ⚠ ONE ROW PER PROPERTY. The source is a MONTHLY series: 19,187 Indiana rows are 1,173
  -- properties re-reported across 249 periods. Admitting rows would multiply one building into
  -- hundreds of "events" and every count downstream would be a reporting artefact.
  SELECT *, ROW_NUMBER() OVER (PARTITION BY assetnumber, propertyaddress
                               ORDER BY {D('reportingperiodenddate')} DESC) AS rn
  FROM `{DS}.in_si_up_cmbs`
  WHERE propertyaddress IS NOT NULL AND propertyaddress <> ''
    AND propertycity IS NOT NULL AND propertycity <> ''
),
x AS (
  SELECT
    assetnumber, propertyname, propertyaddress, propertycity, propertycounty, propertyzip,
    propertytypecode, largesttenant,
    {D('reportingperiodenddate')}              AS period_end,
    {D('maturitydate')}                        AS maturity_date,
    {D('leaseexpirationlargesttenantdate')}    AS anchor_lease_end,
    {D('mostrecentspecialservicertransferdate')} AS special_servicer_date,
    paymentstatusloancode                      AS pay_code,
    workoutstrategycode                        AS workout_code,
    {F('mostrecentdebtservicecoveragenetoperatingincomepercentage')} AS dscr,
    {F('mostrecentphysicaloccupancypercentage')}                     AS occupancy,
    {F('mostrecentvaluationamount')}           AS valuation,
    {F('netrentablesquarefeetnumber')}         AS sqft,
    {F('reportperiodendactualbalanceamount')}  AS loan_balance
  FROM latest WHERE rn = 1
),
flagged AS (
  SELECT *,
    -- ⛔ CREFC codes: 0=current, A=in grace, B=late under 30 days - none of those is distress.
    (pay_code IN ('1','2','3','5'))                                   AS f_delinquent,
    (workout_code IS NOT NULL AND workout_code NOT IN ('','0'))       AS f_workout,
    (special_servicer_date IS NOT NULL)                               AS f_special_serviced,
    -- ⚠ dscr > 0 first: an unpublished DSCR reads as 0 and would otherwise be "below 1.0".
    (dscr > 0 AND dscr < 1.0)                                         AS f_dscr_under_1,
    (maturity_date IS NOT NULL AND maturity_date < CURRENT_DATE()
       AND IFNULL(loan_balance, 0) > 0)                               AS f_past_maturity,
    -- ⚠ occupancy is a FRACTION and 0 is the null sentinel, not an empty building.
    (occupancy > 0 AND occupancy <= 0.60)                             AS f_low_occupancy,
    (anchor_lease_end BETWEEN CURRENT_DATE() AND DATE_ADD(CURRENT_DATE(), INTERVAL 24 MONTH))
                                                                      AS f_anchor_rolling
  FROM x
),
sig AS (
  SELECT *,
    (f_delinquent OR f_workout OR f_special_serviced OR f_dscr_under_1 OR f_past_maturity)
                                                                      AS is_loan_distress,
    (f_low_occupancy OR f_anchor_rolling)                             AS is_tenant_exit
  FROM flagged
),
w AS (
  SELECT *, {naddr('propertyaddress')} AS nstreet,
            {naddr('propertyaddress', drop_dir=True)} AS nstreet_nd,
            {ncity('propertycity')} AS ncity
  FROM sig WHERE is_loan_distress OR is_tenant_exit
),
p AS (
  SELECT state_parcel_id AS parcel_key,
         {naddr('dlgf_prop_address')} AS nstreet,
         {naddr('dlgf_prop_address', drop_dir=True)} AS nstreet_nd,
         {ncity('dlgf_prop_address_city')} AS ncity
  FROM `{EN}.parcels_in`
  WHERE state_parcel_id IS NOT NULL AND state_parcel_id != '{D85}'
    AND dlgf_prop_address IS NOT NULL AND dlgf_prop_address != ''
    AND dlgf_prop_address_city IS NOT NULL
),
pd AS (SELECT nstreet, ncity, COUNT(DISTINCT parcel_key) n_parcels,
              ANY_VALUE(parcel_key) parcel_key FROM p GROUP BY 1,2),
pnd AS (SELECT nstreet_nd, ncity, COUNT(DISTINCT parcel_key) n_parcels,
               ANY_VALUE(parcel_key) parcel_key FROM p GROUP BY 1,2),
m1 AS (
  SELECT w.*, pd.parcel_key, pd.n_parcels, 'exact_normalised' AS match_method
  FROM w JOIN pd ON pd.nstreet = w.nstreet AND pd.ncity = w.ncity
),
m2 AS (
  SELECT w.*, pnd.parcel_key, pnd.n_parcels, 'directional_dropped' AS match_method
  FROM w JOIN pnd ON pnd.nstreet_nd = w.nstreet_nd AND pnd.ncity = w.ncity
  WHERE NOT EXISTS (SELECT 1 FROM m1
                    WHERE m1.assetnumber = w.assetnumber
                      AND m1.propertyaddress = w.propertyaddress)
    AND pnd.n_parcels = 1
),
hit AS (
  SELECT assetnumber, propertyaddress, parcel_key, n_parcels, match_method
  FROM (SELECT * FROM m1 UNION ALL SELECT * FROM m2)
)
-- ⛔ A LEFT JOIN, NOT AN INNER ONE, AND THAT IS THE WHOLE POINT OF G150. This table is the
-- UNIVERSE of Indiana CMBS properties carrying a condition, with `parcel_key` NULL where we could
-- not place it. An inner join would have made the coverage denominator equal to the numerator, so
-- every signal would report 100% placement and the loss would be invisible - which is exactly the
-- disease the operator reported twice.
SELECT
  'parcels_in' AS parcel_source, hit.parcel_key,
  assetnumber, propertyname, propertyaddress, propertycity, propertycounty, propertyzip,
  propertytypecode, largesttenant, period_end, maturity_date, anchor_lease_end,
  special_servicer_date, pay_code, workout_code, dscr, occupancy, valuation, sqft, loan_balance,
  f_delinquent, f_workout, f_special_serviced, f_dscr_under_1, f_past_maturity,
  f_low_occupancy, f_anchor_rolling, is_loan_distress, is_tenant_exit,
  hit.n_parcels AS parcels_sharing_this_address, hit.match_method,
  CASE WHEN hit.parcel_key IS NULL THEN 'no_parcel_at_this_address'
       WHEN hit.n_parcels = 1     THEN 'exact_address'
       ELSE 'address_shared_by_several_parcels' END AS match_grain,
  CURRENT_TIMESTAMP() AS built_at
FROM w LEFT JOIN hit USING (assetnumber, propertyaddress)
"""

print("=" * 96)
print("G152 - TWO NEW SI SIGNALS FROM THE FULL-WIDTH CMBS CLIP")
print("=" * 96)
job = client.query(SQL)
job.result()
print(f"  built, {round((job.total_bytes_processed or 0) / 1e9, 2)} GB scanned")

u = list(client.query(f"""
  WITH latest AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY assetnumber, propertyaddress
             ORDER BY {D('reportingperiodenddate')} DESC) rn
    FROM `{DS}.in_si_up_cmbs`
    WHERE propertyaddress IS NOT NULL AND propertyaddress <> '')
  SELECT COUNT(*) properties FROM latest WHERE rn = 1"""))[0]

s = list(client.query(f"""
  SELECT COUNT(*) n, COUNT(DISTINCT parcel_key) parcels,
         COUNTIF(match_grain='exact_address') exact,
         COUNTIF(is_loan_distress) distress, COUNTIF(is_tenant_exit) exiting,
         COUNTIF(f_special_serviced) ss, COUNTIF(f_workout) wo, COUNTIF(f_delinquent) dq,
         COUNTIF(f_dscr_under_1) dscr, COUNTIF(f_low_occupancy) occ,
         COUNTIF(f_anchor_rolling) anchor
  FROM `{OUT}`"""))[0]

print(f"\n  universe: {u.properties:,} distinct Indiana CMBS-financed properties")
print(f"  {s.n} of them carry a condition; {s.exact} placed at an address held by exactly one "
      f"parcel")
print(f"  ⭐ {s.parcels} PARCELS reached")
print(f"     D28_cmbs_loan_distress  {s.distress:>4}   "
      f"(special-serviced {s.ss}, in workout {s.wo}, delinquent {s.dq}, DSCR<1.0 {s.dscr})")
print(f"     D29_anchor_tenant_exit  {s.exiting:>4}   "
      f"(occupancy<=60% {s.occ}, anchor lease rolling within 24mo {s.anchor})")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_si_cmbs_placed'").result()
client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at)
VALUES ('in_si_cmbs_placed', 'indiana_app.in_si_up_cmbs (from energy.edgar_abs_ee_cmbs)',
  'Latest reporting period per (assetnumber, propertyaddress); CREFC payment-status codes '
  '1/2/3/5 = delinquent; workout or special-servicer transfer; DSCR<1.0 where published; past '
  'maturity with a balance -> D28_cmbs_loan_distress. Published occupancy <=60% (a FRACTION, 0 = '
  'unpublished) or largest-tenant lease expiring within 24 months -> D29_anchor_tenant_exit. '
  'Placed on parcels by normalised street+city against energy.parcels_in, two passes, D85 '
  'excluded. RE-SCRAPE COMMAND: python scripts/build_si_cmbs_signals.py '
  'IDEMPOTENT: replace_safe. Depends on scripts/build_si_upstream_wide.py. '
  'THEN RE-RUN scripts/build_si_signal_v2.py and the exporters.',
  (SELECT COUNT(*) FROM `{OUT}`), CURRENT_TIMESTAMP())""").result()
print("\n  registered in_si_cmbs_placed")
print("\nDONE")
