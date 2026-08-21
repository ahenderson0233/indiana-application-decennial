"""G132 / G104 / G70: OWNER NAME, OWNER MAILING ADDRESS AND ASSESSED VALUE — for Marion County, now.

Operator, 2026-08-21: *"Since we don't have the owner name for the parcel joins, we need to use
some other metric (e.g., assessed value, email addresses, or similar). As for assessed value, are
we able to determine this based on the data that we currently hold, or is this gated behind a paid
source?"*

================================================================================================
⛔ THE ANSWER IS BOTH, AND THREE DOCUMENTS SAID ONLY THE SECOND HALF
================================================================================================
The standing claim across SESSION_START, the handoff and the backlog is that owner, zoning and
assessed value are *"100% NULL for Indiana in both our clip and the national parent"*. Measured
2026-08-21, that is exactly true of the two tables it names and NOT true of the estate:

    energy.parcels_in            3,637,663 rows - NO value, owner, mail, email or phone column
                                 exists at all. Only tax DISTRICT codes, which are jurisdictions.
    energy.mat_parcel_attrs      3,553,381 Indiana rows - assessed_value, parcel_owner, zoning,
                                 land_use, year_built and owner_class are populated on ZERO.
    ⭐ indiana_app.in_marion_parcel_crosswalk   347,049 rows, and it carries ALL OF IT:
                                 FULLOWNERNAME on 347,049 (100%), OWNERADDRESS on 346,781 (99.9%),
                                 ASSESSORYEAR_TOTALAV on 347,049 with 340,212 above zero
                                 (median $211,200), plus land and improvement splits, ESTSQFT and
                                 the assessor property class.

⚠ AND THE NATIONAL FIGURE WAS WRONG TOO. The documents say the parent holds *"40.8M assessed
values for 43 other states"*. Measured: **44,177,912 values across 18 states**, not 43. The vendor
covers a third of the country, so Indiana's absence is a COVERAGE fact about that vendor, not a
clip defect — which is the same conclusion by a correct route.

⭐ SO: statewide owner and assessed value remain gated behind the DLGF Gateway purchase. **Marion
County — Indianapolis, the largest market in the state — does not need it.** This build makes that
county's owner identity, owner mailing address and assessed value joinable to a parcel today.

================================================================================================
⛔ THE JOIN KEY, AND THE THREE WRONG GUESSES THAT CAME FIRST
================================================================================================
I probed `PARCEL_C` (7-digit local, matches 59,211 of 342,718 = 17%), `CAMAPARCELID` (matches 313,
which is noise) and `PARCEL_I` (0) before reading the whole schema and finding
**`STATEPARCELNUMBER`** — the DLGF state parcel number, `49-01-15-113-002.000-400`, sitting there
named for exactly what it is. Stripped of punctuation it IS `in_sites.parcel_key`.

    6,965 of 7,097 Marion screener candidates join (98.1%)
    340,231 of in_sites rows join overall

⚠ That is the project's own oldest rule — *read the schema, never guess a column name* — costing
three queries again. The column list is 51 wide and I probed the three that looked like keys
instead of the one that says it is one.

RE-SCRAPE COMMAND: python scripts/build_marion_owner_value.py
⚠ IDEMPOTENT: replace_safe. CADENCE: annual — Marion re-publishes the assessor extract with each
assessment year; `MODDATE` carries the publisher's own row vintage.
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_marion_owner_value"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH x AS (
  SELECT
    -- ⭐ THE KEY. Punctuation stripped so it matches in_sites.parcel_key, which is the DLGF state
    -- parcel number without separators. ⚠ NOT PARCEL_C - that is the county's own 7-digit local
    -- number and it matches only 17% of Marion parcels.
    REGEXP_REPLACE(IFNULL(STATEPARCELNUMBER, ''), r'[^0-9]', '') AS parcel_key,
    -- ⚠ THE PUBLISHER CONCATENATES NAME PARTS AND LEAVES THE SEPARATORS. Raw values arrive as
    -- 'INDPLS/PARKS & RECREATION, , ,' - three empty name slots still separated by commas - which
    -- rendered on screen exactly like that. Trailing empty parts are stripped; an INTERNAL comma
    -- is left alone because 'SMITH, JOHN A' is the real name.
    NULLIF(TRIM(REGEXP_REPLACE(TRIM(FULLOWNERNAME), r'[,\\s]+$', '')), '') AS owner_name,
    NULLIF(TRIM(OWNERADDRESS), '')                         AS owner_mail_address,
    NULLIF(TRIM(OWNERCITY), '')                            AS owner_mail_city,
    NULLIF(TRIM(OWNERSTATE), '')                           AS owner_mail_state,
    NULLIF(TRIM(OWNERZIP), '')                             AS owner_mail_zip,
    SAFE_CAST(ASSESSORYEAR_TOTALAV   AS FLOAT64)           AS assessed_total,
    SAFE_CAST(ASSESSORYEAR_LANDTOTAL AS FLOAT64)           AS assessed_land,
    SAFE_CAST(ASSESSORYEAR_IMPTOTAL  AS FLOAT64)           AS assessed_improvement,
    SAFE_CAST(ACREAGE AS FLOAT64)                          AS assessor_acres,
    SAFE_CAST(ESTSQFT AS FLOAT64)                          AS assessor_building_sqft,
    NULLIF(TRIM(PROPERTY_CLASS), '')                       AS assessor_class,
    NULLIF(TRIM(PROPERTY_SUB_CLASS_DESCRIPTION), '')       AS assessor_class_label,
    NULLIF(TRIM(MODDATE), '')                              AS publisher_row_date
  FROM `{DS}.in_marion_parcel_crosswalk`
  WHERE STATEPARCELNUMBER IS NOT NULL
),
d AS (
  -- ⚠ ONE ROW PER PARCEL. The extract carries a row per assessor record and a parcel can appear
  -- more than once (split records, condo units against one state number). Aggregating rather than
  -- joining raw is what stops this fanning out in_screener_candidates - the same defect the
  -- 38,840 duplicated state_parcel_id values caused on the address join.
  SELECT parcel_key,
         COUNT(*)                                AS assessor_records,
         ANY_VALUE(owner_name)                   AS owner_name,
         ANY_VALUE(owner_mail_address)           AS owner_mail_address,
         ANY_VALUE(owner_mail_city)              AS owner_mail_city,
         ANY_VALUE(owner_mail_state)             AS owner_mail_state,
         ANY_VALUE(owner_mail_zip)               AS owner_mail_zip,
         -- ⛔ SUM, NOT ANY_VALUE, for money on a split record: two assessor rows against one state
         -- parcel number are two components of that parcel's value, and picking one understates it.
         SUM(assessed_total)                     AS assessed_total,
         SUM(assessed_land)                      AS assessed_land,
         SUM(assessed_improvement)               AS assessed_improvement,
         SUM(assessor_acres)                     AS assessor_acres,
         SUM(assessor_building_sqft)             AS assessor_building_sqft,
         ANY_VALUE(assessor_class)               AS assessor_class,
         ANY_VALUE(assessor_class_label)         AS assessor_class_label,
         MAX(publisher_row_date)                 AS publisher_row_date
  FROM x WHERE parcel_key != '' GROUP BY 1
)
SELECT
  'parcels_in' AS parcel_source,
  parcel_key,
  assessor_records,
  owner_name, owner_mail_address, owner_mail_city, owner_mail_state, owner_mail_zip,
  -- ⭐ THE SIGNAL, NOT JUST THE FIELD. An owner whose mailing address is in another state is not
  -- living on the parcel, which is the absentee-owner signal D9 already uses for Marion - now
  -- available from the assessor's own record rather than inferred.
  -- ⚠ NULL, never false, when we hold no mailing state: unpublished is not "resident".
  IF(owner_mail_state IS NULL, NULL, UPPER(owner_mail_state) != 'IN') AS owner_out_of_state,
  ROUND(assessed_total)       AS assessed_total,
  ROUND(assessed_land)        AS assessed_land,
  ROUND(assessed_improvement) AS assessed_improvement,
  -- ⭐ THE FIGURE A SITER ACTUALLY USES. A total value tells them nothing about a 600-acre field;
  -- value PER ACRE is what says whether this is farmland or a built-out block, and it is the
  -- number that makes two parcels comparable.
  -- ⚠ Only where the assessor's own acreage is positive. Dividing by our polygon area instead
  -- would mix two measurements into one ratio.
  IF(assessed_total > 0 AND assessor_acres > 0,
     ROUND(assessed_total / assessor_acres), NULL) AS assessed_per_acre,
  assessor_acres, assessor_building_sqft, assessor_class, assessor_class_label,
  publisher_row_date,
  CURRENT_TIMESTAMP() AS built_at
FROM d
"""

print("G132/G104/G70 - MARION OWNER, MAILING ADDRESS AND ASSESSED VALUE")
job = client.query(SQL)
job.result()
gb = round((job.total_bytes_processed or 0) / 1e9, 2)
print(f"  built, {gb} GB scanned")

s = list(client.query(f"""
  SELECT COUNT(*) n, COUNT(DISTINCT parcel_key) k,
         COUNTIF(owner_name IS NOT NULL) own,
         COUNTIF(owner_mail_address IS NOT NULL) mail,
         COUNTIF(owner_out_of_state) oos,
         COUNTIF(assessed_total > 0) av,
         COUNTIF(assessed_per_acre IS NOT NULL) per_acre,
         ROUND(APPROX_QUANTILES(assessed_total, 100)[OFFSET(50)]) med_av,
         ROUND(APPROX_QUANTILES(assessed_per_acre, 100)[OFFSET(50)]) med_per_acre,
         MAX(assessor_records) max_rec
  FROM `{OUT}`"""))[0]
print(f"  {s.n:,} rows / {s.k:,} distinct parcel keys -> fan-out {s.n / s.k:.4f}")
assert s.n == s.k, "one row per parcel_key, or the aggregation failed"
print(f"  owner name           {s.own:>7,}")
print(f"  owner mail address   {s.mail:>7,}")
print(f"  ⭐ owner OUT OF STATE {s.oos:>7,}  <- an absentee signal from the assessor's own record")
print(f"  assessed value > 0   {s.av:>7,}  median ${s.med_av:,.0f}")
print(f"  value per acre       {s.per_acre:>7,}  median ${s.med_per_acre:,.0f}/acre")
print(f"  most assessor records against one state parcel number: {s.max_rec}")

j = list(client.query(f"""
  SELECT COUNT(*) cands,
         COUNTIF(m.parcel_key IS NOT NULL) matched,
         COUNTIF(m.assessed_total > 0) with_value,
         COUNTIF(m.owner_name IS NOT NULL) with_owner
  FROM `{DS}.in_screener_candidates` c
  LEFT JOIN `{OUT}` m USING (parcel_source, parcel_key)
  WHERE c.county_name = 'Marion County'"""))[0]
print(f"\n  ⭐ Marion screener candidates: {j.matched:,} of {j.cands:,} matched "
      f"({100 * j.matched / j.cands:.1f}%), {j.with_owner:,} with an owner name, "
      f"{j.with_value:,} with an assessed value")

# ⛔ THE HONEST DENOMINATOR: this is ONE county of 92, and saying so is the point.
st = list(client.query(f"""
  SELECT COUNT(*) all_cands,
         COUNTIF(county_name = 'Marion County') marion
  FROM `{DS}.in_screener_candidates`"""))[0]
print(f"  ⚠ STATEWIDE THIS IS {100 * st.marion / st.all_cands:.1f}% OF CANDIDATES "
      f"({st.marion:,} of {st.all_cands:,}). The other 91 counties publish none of this to us "
      f"and remain blocked on the DLGF Gateway purchase — not on a better join.")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_marion_owner_value',
 'indiana_app.in_marion_parcel_crosswalk (Marion County assessor / GIS parcel extract)',
 'One row per DLGF state parcel number for Marion County, carrying OWNER NAME, owner MAILING '
 'address, an out-of-state-owner flag, and ASSESSED VALUE split into total / land / improvement, '
 'plus assessor acreage, building square feet, class and the publisher row date. '
 'JOIN KEY: STATEPARCELNUMBER stripped of punctuation = in_sites.parcel_key. '
 'Money is SUMMED across multiple assessor records against one state parcel number because those '
 'are components of one parcel; identity fields take ANY_VALUE. assessed_per_acre is computed '
 'only where the assessor publishes positive acreage. owner_out_of_state is NULL, never false, '
 'when no mailing state is published. '
 'RE-SCRAPE COMMAND: python scripts/build_marion_owner_value.py',
 {s.n}, {gb}, CURRENT_TIMESTAMP(),
 'G132 (operator 2026-08-21), and it partially unblocks G104 (assessed value) and G70 (owner) for '
 'ONE county. ⛔ CONTEXT THAT MATTERS: three project documents state that owner and assessed value '
 'are 100% NULL for Indiana in both our clip and the national parent. That is true of '
 'energy.parcels_in (no such column exists) and of energy.mat_parcel_attrs (0 of 3,553,381 Indiana '
 'rows populated) and NOT true of the estate - this crosswalk held all of it. The national parent '
 'covers 44,177,912 assessed values across 18 states, not the 40.8M across 43 states the documents '
 'claim. Marion is ~1.3% of candidates; the other 91 counties remain blocked on the DLGF Gateway '
 'purchase, which is an acquisition and not a join. '
 'IDEMPOTENCY: replace_safe. CADENCE: annual, per assessment year.'
)""").result()
print("\n  _registry row written")
print("MARION OWNER / VALUE COMPLETE")
