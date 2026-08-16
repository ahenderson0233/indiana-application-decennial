"""A5 — widen the Indianapolis code-enforcement placement beyond two case types.

WHERE THIS STOOD. The corpus is 910,483 rows. `in_si_indy_code_placed` placed 46,411 of them,
covering exactly TWO of the 29 case types — Unsafe Buildings and Vacant Board Order — so
D12_code_violation reached 10,370 parcels and admitted 228. The recorded diagnosis, that Indy's
addresses "match nothing", predates the Marion address crosswalk pulled 2026-08-16: measured
against it, **134,097 of 156,052 distinct code addresses (85.9%) match FULL_ADDRESS exactly.**
The bridge is not the problem any more. The gate is.

READ THE VALUE VOCABULARY BEFORE WIDENING. This is the D5 mistake in its third costume, and the
numbers make it unmistakable — of 910,483 rows:

    High Weeds & Grass   363,844   40%    a lawn, not a reason to sell
    Trash                103,792
    Zoning (inv/viol)    225,359          largely minor
    Vehicle               46,969          an untagged car on a driveway
    Illegal Dumping       13,461

Admitting the corpus wholesale would inflate D12 by roughly 750,000 rows of litter and parking.
South Bend's corpus was 95% litter and weeds and was gated for exactly this reason.

WHAT IS ADMITTED, and why each one is distress ON THE STRUCTURE:
    Unsafe Buildings      29,108   the building is dangerous
    Vacant Board Order    25,887   the building is empty and boarded
    Building violation    45,787   the structure itself is in violation
    Repair No Hearing     15,000   ordered repairs, no hearing granted
    Repair                 5,029   ordered repairs
    Demolition             2,386   the building is coming down
    Environmental          5,570   contamination on the parcel

Everything excluded is KEPT with a reason, never dropped, so the discard is auditable.

Placement uses Indy's OWN address authority — the publisher's FULL_ADDRESS to STATEPARCELNUMBER
mapping — not a geocoder. Both sides are canonicalised IDENTICALLY and no further, because a
normalisation applied to one side only is an invented match. D85 excluded from the join.
"""
import datetime

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
D85 = "080500000047000018"
client = bigquery.Client(project="energy-platfrom")
BUILT = datetime.datetime.now(datetime.timezone.utc).isoformat()

# OPERATOR RULING 2026-08-16: "structural distress needs to actually RESULT IN INTENT, so minor
# incidents don't do us any good." A single building violation does not move an owner to sell.
# So admission is two-tier, and the data supports both tiers:
#
#   TIER 1 — CONDEMNATION TRACK. Admitted on a single occurrence, because each one already means
#   the building is unusable: Unsafe Buildings (dangerous), Vacant Board Order (empty and
#   boarded), Demolition (coming down).
#
#   TIER 2 — CHRONIC ONLY. Building violations and repair orders are admitted ONLY where the
#   address is chronically cited (>=3 structural cases) or the case is UNRESOLVED. Measured
#   distribution of structural cases per address: 16,325 addresses have exactly one, 7,349 have
#   3-4, and 2,176 have TEN OR MORE. A single citation is an incident; ten is an owner who has
#   stopped maintaining the property.
#
# And a status gate over both: `Closed, No Violation` (60,449 rows) means an inspector found
# NOTHING, and `Void` (13,987) means the case was cancelled. Counting either as distress would be
# the "0 high-priority violators" error inverted -- reading a negative finding as a positive one.
TIER1 = {
    "Unsafe Buildings":     "D5_unsafe_building",
    "Vacant Board Order":   "D5_vacant_board_order",
    "Violation/Demolition": "D21_demolition_order",
}
TIER2 = {
    "Violation/Building":   "D12_code_violation",
    "Repair No Hearing":    "D12_code_violation",
    "Violation/Repair/":    "D12_code_violation",
    "Violation/Environmental": "D22_environmental_violation",
}
SEVERE = {**TIER1, **TIER2}
CASE = "\n".join(
    f"    WHEN CASE_TYPE LIKE '%{frag}%' THEN '{sig}'" for frag, sig in SEVERE.items())
TIER1_PRED = " OR ".join(f"CASE_TYPE LIKE '%{f}%'" for f in TIER1)
# a case still open, overdue or owing fees is UNRESOLVED distress; a corrected one is not
UNRESOLVED = ("(CASE_STATUS LIKE '%Overdue%' OR CASE_STATUS LIKE '%Fees Due%' "
              "OR CASE_STATUS IS NULL OR CASE_STATUS IN ('None',''))")
NO_VIOLATION = "(CASE_STATUS LIKE '%No Violation%' OR CASE_STATUS LIKE '%Void%')"
NORM = r"REGEXP_REPLACE(REGEXP_REPLACE(UPPER(TRIM({c})), r'[^A-Z0-9 ]', ' '), r'\s+', ' ')"

SQL = f"""
CREATE OR REPLACE TABLE `{DS}.in_si_indy_code_widened` AS
WITH src AS (
  SELECT CASE_NUMBER, CASE_TYPE, CASE_STATUS, OWNER,
         {NORM.format(c='STREET_ADDRESS')} AS ad,
         -- OPEN_DATE is EPOCH MILLISECONDS IN A STRING ('1277438400000'), the Esri/ArcGIS
         -- convention. An ISO parse returns NULL on every row, which is how this build first
         -- reported 88,544 placements and ZERO dates. A3 already recorded that seven of the
         -- eighteen date columns in this estate store epoch ms as strings; this is an eighth.
         -- Recency is the whole point of the corpus, so an undated placement is nearly worthless.
         COALESCE(
           SAFE_CAST(TIMESTAMP_MILLIS(SAFE_CAST(TRIM(OPEN_DATE) AS INT64)) AS DATE),
           SAFE.PARSE_DATE('%Y-%m-%d', SUBSTR(TRIM(OPEN_DATE), 1, 10))
         ) AS ev,
         CASE
{CASE}
           ELSE NULL END AS signal
  FROM `{DS}.in_si_refresh_indy_code_enforcement`
  WHERE STREET_ADDRESS IS NOT NULL AND LENGTH(TRIM(STREET_ADDRESS)) > 3
    AND NOT {NO_VIOLATION}        -- an inspector finding NOTHING is not distress
),
-- how many STRUCTURAL cases has this address ever had? repetition is the intent signal
chronic AS (
  SELECT ad, COUNT(*) structural_cases FROM src WHERE signal IS NOT NULL GROUP BY ad
),
xw AS (   -- the publisher's OWN address authority; one state key per canonical address
  -- NOTE THE ALIAS. Naming the output `sp` would make COUNT(DISTINCT sp) in HAVING resolve to
  -- the ALIAS rather than the column, which BigQuery rejects as an aggregate of an aggregate.
  -- This project has already lost time to exactly this shape once, as `MIN(pk) pk`.
  SELECT ad, ANY_VALUE(sp) AS parcel_sp FROM (
    SELECT {NORM.format(c='FULL_ADDRESS')} ad,
           REGEXP_REPLACE(STATEPARCELNUMBER, r'[^0-9]', '') sp
    FROM `{DS}.in_marion_address_crosswalk`
    WHERE STATEPARCELNUMBER IS NOT NULL AND FULL_ADDRESS IS NOT NULL)
  GROUP BY ad HAVING COUNT(DISTINCT sp) = 1   -- ambiguous addresses are DROPPED, not guessed
)
SELECT s.signal, 'parcels_in' AS parcel_source, x.parcel_sp AS parcel_key,
       s.ad AS address_canon, s.ev AS event_date, s.CASE_NUMBER AS case_number,
       s.CASE_TYPE AS case_type, s.CASE_STATUS AS case_status, s.OWNER AS owner_name,
       ch.structural_cases,
       CASE WHEN {TIER1_PRED} THEN 'tier1_condemnation_track'
            WHEN ch.structural_cases >= 3 THEN 'tier2_chronic'
            ELSE 'tier2_unresolved' END AS admit_basis,
       si.occ_group, TIMESTAMP('{BUILT}') AS built_at
FROM src s
JOIN xw x ON x.ad = s.ad
JOIN chronic ch ON ch.ad = s.ad
JOIN `{DS}.in_sites` si ON si.parcel_key = x.parcel_sp AND si.parcel_source = 'parcels_in'
WHERE s.signal IS NOT NULL AND si.parcel_key != '{D85}'
  -- the operator's rule, encoded: a lone minor citation is NOT intent
  AND ( {TIER1_PRED}                       -- condemnation track stands alone
        OR ch.structural_cases >= 3        -- or the address is chronically cited
        OR {UNRESOLVED} )                  -- or the case was never resolved
"""

print("building in_si_indy_code_widened …", flush=True)
job = client.query(SQL); job.result()
print(f"  scanned {job.total_bytes_processed/1e9:.2f} GB")

r = list(client.query(f"""SELECT COUNT(*) n, COUNT(DISTINCT parcel_key) parcels,
  COUNT(DISTINCT IF(occ_group!='residential', parcel_key, NULL)) nonres,
  COUNTIF(event_date IS NOT NULL) dated,
  COUNTIF(owner_name IS NOT NULL) owned
FROM `{DS}.in_si_indy_code_widened`"""))[0]
print(f"  {r.n:,} rows on {r.parcels:,} parcels · {r.nonres:,} non-residential · "
      f"{r.dated:,} dated · {r.owned:,} carry an owner name")

print("\nby signal:")
for x in client.query(f"""SELECT signal, COUNT(*) n, COUNT(DISTINCT parcel_key) p,
  COUNT(DISTINCT IF(occ_group!='residential', parcel_key, NULL)) nr,
  MIN(event_date) lo, MAX(event_date) hi
FROM `{DS}.in_si_indy_code_widened` GROUP BY 1 ORDER BY n DESC"""):
    print(f"  {x.signal:30s} {x.n:>7,} rows · {x.p:>6,} parcels · {x.nr:>5,} non-res · {x.lo}..{x.hi}")

print("\nEXCLUDED, counted rather than dropped silently:")
for x in client.query(f"""SELECT CASE_TYPE, COUNT(*) n
FROM `{DS}.in_si_refresh_indy_code_enforcement`
WHERE NOT ({" OR ".join(f"CASE_TYPE LIKE '%{f}%'" for f in SEVERE)})
GROUP BY 1 ORDER BY n DESC LIMIT 6"""):
    print(f"  {str(x.CASE_TYPE)[:46]:46s} {x.n:>8,}")

prev = list(client.query(f"SELECT COUNT(DISTINCT parcel_key) p FROM `{DS}.in_si_indy_code_placed`"))[0].p
print(f"\nprior placement reached {prev:,} parcels; this reaches {r.parcels:,}")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_si_indy_code_widened'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
    f"VALUES (@t,@s,@m,@n,@g,CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "in_si_indy_code_widened"),
        bigquery.ScalarQueryParameter("s", "STRING",
            "indiana_app.in_si_refresh_indy_code_enforcement x in_marion_address_crosswalk "
            "(gis.indy.gov sde_Addressing/0) x in_sites"),
        bigquery.ScalarQueryParameter("m", "STRING",
            "SEVERITY-GATED widening from 2 case types to 7. Placement via Indy's OWN "
            "FULL_ADDRESS -> STATEPARCELNUMBER authority, both sides canonicalised identically "
            "(upper, strip punctuation, collapse whitespace) and no further. Addresses mapping to "
            ">1 state parcel number are DROPPED, never guessed. D85 excluded."),
        bigquery.ScalarQueryParameter("n", "INT64", int(r.n)),
        bigquery.ScalarQueryParameter("g", "FLOAT64", round(job.total_bytes_processed / 1e9, 3)),
        bigquery.ScalarQueryParameter("no", "STRING",
            "40% of this corpus is High Weeds & Grass (363,844 rows) and a further 150,000+ is "
            "trash and untagged vehicles. Admitting it wholesale would inflate D12 by ~750,000 "
            "rows of lawn care -- the same error that made South Bend's corpus 95% litter. Only "
            "distress ON THE STRUCTURE is admitted: Unsafe Buildings, Vacant Board Order, "
            "Building violation, Repair, Repair No Hearing, Demolition, Environmental. "
            "MARION ONLY -- 1 of 92 counties, a publishing footprint, not statewide coverage.")])).result()
print("registered in_si_indy_code_widened")
