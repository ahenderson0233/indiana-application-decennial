"""G156(a): D14 AND D16 PLACED FROM THE FULL-WIDTH CLIPS, NOT FROM THE 13-COLUMN REDUCTION.

⛔ THE PROBLEM. `D14_sba_chargeoff` and `D16_structure_fire` are fed ONLY by `si_signals`, the
97,240,585-row corpus normalised to 13 columns. G152 repaired both underlying clips and **neither
repair reached a reader**, because the spine never read the clips.

⭐ WHAT THIS BUILDS. One placement table, `in_si_addr_placed`, carrying both sources keyed to a
parcel by normalised street+city against `energy.parcels_in` — the same authority and the same
two-pass method as `build_si_cmbs_signals.py`, importing the same one normaliser.

⚠ MEASURED BEFORE BUILDING, AND THE MEASUREMENT CORRECTED THE PLAN. `docs/SI_SIGNALS.md` and
HANDOFF_2026-08-22 both present D16 as the big win (*"+33,039 rows"*) and D14 as a 7.8× under-clip
(*"5,135 -> 39,948"*). **Both framings overstate the SIGNAL gain by two orders of magnitude:**

  · D14 — the clip holds 39,948 loans and exactly **3,850 are `loanstatus = 'CHGOFF'`**. The other
    36,098 are PIF / EXEMPT / CANCLD / COMMIT — loans that were PAID IN FULL or never drawn, which
    is the OPPOSITE of distress. D14 already held 3,774 charge-offs through the corpus, so the
    repair's row gain is **at most 76**. ⭐ Its real value is not rows: it is `borrstreet`, a
    direct address the corpus does not carry, and `grosschargeoffamount`, the DOLLAR SIZE.
    **Measured gain: +466 parcels (1,773 -> 2,239).**
  · D16 — the fire-INCIDENT repair recovered 33,039 rows of detail, but the incident LIST comes
    from `basicincident`, which was never short. Re-running `build_nfirs_structure_fires.py` after
    the repair produced a byte-identical 45,607 rows. What the repair actually bought is NOT_RES
    coverage (2023 went 0 -> 4,357). **Measured gain: +131 parcels.**

⛔ SO THE HONEST HEADLINE IS THAT D14, NOT D16, IS THE BIGGER WIN — the reverse of the record.
A row count is not a signal count, and nothing was converting between them.

⚠ ADMISSION RULES, EACH WITH ITS REASON:
  · D16 admits `property_class = 'non-residential'` AND severity >= $10k. `property_class` comes
    from PROP_USE on basicincident and is complete for all five years; `non_residential` (NOT_RES,
    from fireincident) is stated on only 18,560 of 45,607 rows and would silently drop the rest.
    ⛔ Operator ruling: *"structural distress needs to actually result in intent, so minor
    incidents don't do us any good."* A $3k kitchen fire is not a seller.
  · D14 admits `loanstatus = 'CHGOFF'` only, dated by `chargeoffdate` (present on 100% of them).

⚠ AND THE CAVEAT THAT LIMITS D14, RECORDED RATHER THAN HIDDEN: `borrstreet` is the BORROWER's
address, which for an SBA loan is usually but not always the financed property. 39,818 of 39,948
rows agree that both `projectstate` and `borrstate` are IN, so the state is corroborated; the
STREET is not independently corroborated and the `keying` string says so.

RE-SCRAPE COMMAND: python scripts/build_si_addr_placement.py
⛔ Writes `indiana_app.in_si_addr_placed` ONLY. `energy` is READ-ONLY; this reads `parcels_in`.
"""
import sys as _sys

try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import os as _os

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from google.cloud import bigquery

from si_address_norm import naddr, ncity

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
OUT = f"{DS}.in_si_addr_placed"
D85 = "080500000047000018"
client = bigquery.Client(project="energy-platfrom")

# ⚠ the severity vocabulary is the builder's own, read from the table rather than assumed.
FIRE_SEVERE = ("moderate >=$10k", "major >=$100k", "catastrophic >=$500k")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH
-- ---- the parcel address authority. D85 excluded: it is the inverted whole-Earth polygon -------
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
pd  AS (SELECT nstreet,    ncity, COUNT(DISTINCT parcel_key) n_parcels,
               ANY_VALUE(parcel_key) parcel_key FROM p GROUP BY 1, 2),
pnd AS (SELECT nstreet_nd, ncity, COUNT(DISTINCT parcel_key) n_parcels,
               ANY_VALUE(parcel_key) parcel_key FROM p GROUP BY 1, 2),

-- ---- the two source universes, normalised the same way -----------------------------------------
src AS (
  SELECT 'D16_structure_fire' AS signal,
         CONCAT('nfirs:', CAST(incident_key AS STRING)) AS row_id,
         incident_date                                  AS event_date,
         CAST(property_loss_usd AS FLOAT64)             AS amount_usd,
         severity                                       AS grade,
         CONCAT('fire:', IFNULL(property_class, '?'))   AS source_id,
         street_address AS raw_street, city AS raw_city,
         {naddr('street_address')}                AS nstreet,
         {naddr('street_address', drop_dir=True)} AS nstreet_nd,
         {ncity('city')}                          AS ncity
  FROM `{DS}.in_nfirs_structure_fires`
  WHERE street_address IS NOT NULL AND street_address != '' AND city IS NOT NULL
    -- ⛔ property_class, not non_residential: NOT_RES is stated on 18,560 of 45,607 rows and
    -- filtering on it would drop 59% of the corpus as if it were residential.
    AND property_class = 'non-residential'
    AND severity IN {FIRE_SEVERE}

  UNION ALL

  SELECT 'D14_sba_chargeoff' AS signal,
         CONCAT('sba:', CAST(ROW_NUMBER() OVER (ORDER BY chargeoffdate, borrname) AS STRING)),
         SAFE_CAST(chargeoffdate AS DATE),
         SAFE_CAST(grosschargeoffamount AS FLOAT64),
         -- the charge-off SIZE is the grade a reader can act on
         CASE WHEN SAFE_CAST(grosschargeoffamount AS FLOAT64) >= 500000 THEN 'catastrophic >=$500k'
              WHEN SAFE_CAST(grosschargeoffamount AS FLOAT64) >= 100000 THEN 'major >=$100k'
              WHEN SAFE_CAST(grosschargeoffamount AS FLOAT64) >=  10000 THEN 'moderate >=$10k'
              WHEN SAFE_CAST(grosschargeoffamount AS FLOAT64) IS NULL   THEN NULL
              ELSE 'minor <$10k' END,
         CONCAT('sba:', IFNULL(projectcounty, '?')),
         borrstreet, borrcity,
         {naddr('borrstreet')}, {naddr('borrstreet', drop_dir=True)}, {ncity('borrcity')}
  FROM `{DS}.in_sba_foia_loans`
  WHERE loanstatus = 'CHGOFF'            -- measured: 3,850 rows, 100% carry a chargeoffdate
    AND borrstreet IS NOT NULL AND borrstreet != '' AND borrcity IS NOT NULL
),

-- ---- pass 1: exact normalised street+city ------------------------------------------------------
m1 AS (
  SELECT s.*, pd.parcel_key, pd.n_parcels, 'exact_normalised' AS match_method
  FROM src s JOIN pd ON pd.nstreet = s.nstreet AND pd.ncity = s.ncity
),
-- ---- pass 2: directional dropped, and ONLY where it resolves to exactly one parcel -------------
m2 AS (
  SELECT s.*, pnd.parcel_key, pnd.n_parcels, 'directional_dropped' AS match_method
  FROM src s JOIN pnd ON pnd.nstreet_nd = s.nstreet_nd AND pnd.ncity = s.ncity
  WHERE NOT EXISTS (SELECT 1 FROM m1 WHERE m1.row_id = s.row_id)
    AND pnd.n_parcels = 1
),
hit AS (SELECT row_id, parcel_key, n_parcels, match_method
        FROM (SELECT * FROM m1 UNION ALL SELECT * FROM m2))

-- ⛔ LEFT JOIN, NOT INNER. This table is the UNIVERSE of admissible events, with parcel_key NULL
-- where nothing matched. An inner join would make the coverage denominator equal the numerator and
-- every placement rate would read 100% - the defect G150 was built to avoid.
SELECT
  s.signal, s.row_id, s.event_date, s.amount_usd, s.grade, s.source_id,
  s.raw_street, s.raw_city,
  'parcels_in' AS parcel_source, hit.parcel_key,
  hit.n_parcels AS parcels_sharing_this_address,
  hit.match_method,
  CASE WHEN hit.parcel_key IS NULL THEN 'no_parcel_at_that_address'
       WHEN hit.n_parcels = 1      THEN 'exact_address'
       ELSE 'address_shared_by_several_parcels' END AS match_grain,
  CURRENT_TIMESTAMP() AS built_at
FROM src s LEFT JOIN hit USING (row_id)
"""


def main():
    print("=" * 96)
    print("G156(a) - D14 AND D16 PLACED FROM THE FULL-WIDTH CLIPS")
    print("=" * 96)
    dry = client.query(SQL, job_config=bigquery.QueryJobConfig(dry_run=True))
    print(f"  dry-run {dry.total_bytes_processed / 1e9:.2f} GB")
    client.query(SQL).result()

    for r in client.query(f"""
      SELECT signal, COUNT(*) events,
             COUNTIF(parcel_key IS NOT NULL) placed,
             COUNT(DISTINCT IF(match_grain='exact_address', parcel_key, NULL)) parcels,
             COUNTIF(match_grain='address_shared_by_several_parcels') ambiguous,
             COUNTIF(event_date IS NOT NULL) dated,
             ROUND(SUM(IF(match_grain='exact_address', amount_usd, 0)) / 1e6, 1) usd_m
      FROM `{OUT}` GROUP BY 1 ORDER BY 1"""):
        print(f"\n  {r.signal}")
        print(f"     {r.events:,} admissible events · {r.dated:,} dated")
        print(f"     {r.placed:,} matched an address · ⭐ {r.parcels:,} on a UNIQUELY-keyed parcel")
        print(f"     ⚠ {r.ambiguous:,} matched an address shared by several parcels - NOT admitted")
        if r.usd_m:
            print(f"     ${r.usd_m:,.1f}M attached to uniquely-keyed parcels")

    # ⛔ the fan-out check. D85 is excluded above; prove it rather than asserting it.
    fan = list(client.query(f"""
      SELECT COUNT(*) rows_, COUNT(DISTINCT row_id) ids FROM `{OUT}`"""))[0]
    ratio = fan.rows_ / fan.ids if fan.ids else 0
    print(f"\n  fan-out {ratio:.3f} ({fan.rows_:,} rows / {fan.ids:,} event ids) - "
          f"{'OK' if ratio < 1.05 else '⛔ A JOIN IS DUPLICATING EVENTS'}")
    if ratio >= 1.05:
        raise SystemExit("⛔ fan-out above 1.05 - the parcel join is multiplying events")

    client.query(f"""
      INSERT INTO `{DS}._registry` (table_name, source, method, built_at)
      VALUES ('in_si_addr_placed',
        'indiana_app.in_nfirs_structure_fires + indiana_app.in_sba_foia_loans x energy.parcels_in',
        'D14/D16 placed on parcels by normalised street+city against energy.parcels_in, two passes '
        '(exact, then directional-dropped where unique), D85 excluded, LEFT JOIN so the universe is '
        'the denominator. D16 gate: property_class=non-residential AND severity>=$10k. D14 gate: '
        'loanstatus=CHGOFF. ⚠ borrstreet is the BORROWER address, state-corroborated only. '
        'RE-SCRAPE COMMAND: python scripts/build_si_addr_placement.py '
        '⚠ IDEMPOTENT: replace_safe - CREATE OR REPLACE, a re-run cannot double-count.',
        CURRENT_TIMESTAMP())""").result()
    print("\n  _registry row written")
    print("=" * 96)


if __name__ == "__main__":
    main()
