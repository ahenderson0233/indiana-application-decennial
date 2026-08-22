"""G163(a): D8_exit_intent, PLACED — the signal that held 142 rows and reached ZERO parcels.

⛔ THE STATE THIS REPLACES. `D8_exit_intent` reads **142 held, 0 reached, 0 admitted**. Its rows
come from `si_signals`, the 13-column reduction, and carry no address, no parcel key and no
coordinate — so the signal was never PLACEABLE rather than filtered down to nothing. Same shape as
D19_warn before G150.

⭐ ITS ACTUAL PARENT IS A LAYER WE NOW HOLD WHOLE. `in_si_up_indy_rezoning` (G152's full-width clip
of `energy.agis_indy_rezoning`) is **13,414 Indianapolis rezoning cases, 100% carrying geometry**,
8,499 a parcel number and 9,670 a petitioner name.

⚠ AND THE RECORD ABOUT IT WAS WRONG, WHICH IS WHY THIS GOT BUILT RATHER THAN DEFERRED.
`docs/SI_SIGNALS.md` §5 says *"Dates run 1990-2008, so AGE is the open question, not
availability"*, and on that basis ranked it second and left it. **Measured 2026-08-22b: that is
true only of the 142-row CORPUS reduction.** The clip's own `decision_date` runs to **2026-06-17**:
6,519 cases carry a sane date, **1,870 since 2015 and 1,042 since 2020**. The reduction was three
publisher-generations stale and the note describing it was inherited, not re-measured.

⛔ THE DATE IS EPOCH MILLISECONDS IN A FLOAT COLUMN — the Esri convention, and the standing rule
says it appears on at least eight columns in this estate. An ISO parse returns NULL on every row.
⚠ 135 values decode to before 1980 (one to the year 0199) and are rejected as garbage rather than
carried as history.

⛔ PLACEMENT IS BY ADDRESS, AND THE FIRST ATTEMPT WAS SPATIAL AND RETURNED ZERO. That failure is
worth keeping, because the column that caused it is still named `geometry_geojson`:

  · **IT IS NOT GeoJSON.** It is **Esri JSON** — `{{"rings": [[[...]]]}}`, not
    `{{"type":"Polygon","coordinates":[...]}}`. `ST_GEOGFROMGEOJSON` returns NULL on all 13,414
    rows, with and without `make_valid`.
  · **AND THE COORDINATES ARE NOT LAT/LON.** They read `200315.77, 1659378.77` — Indiana State
    Plane in FEET. Even correctly parsed they would land off the planet, and BigQuery has no
    reprojection function.

⚠ So `docs/SI_SIGNALS.md`'s *"13,414 Indianapolis rezoning cases, 100% carrying geometry"* is TRUE
and USELESS, and I repeated it before testing it. **A column named for a format is not a
measurement of that format** — the same shape as `hca_aep_im_mi_*` being Ohio and Michigan.

⭐ THE ROUTE THAT WORKS is the one already proven for D14/D16: `stnum` + `stdir` + `stname`
(9,727 cases carry number and name), normalised through the one shared normaliser and matched
against Marion County parcels — county FIPS 18097, because the layer is Indianapolis and the
publisher gives no city column. Admitted only where the address resolves to exactly ONE parcel.

⚠ SEVERITY IS RECENCY, AND THAT IS A JUDGEMENT WORTH ARGUING WITH. A rezoning petition filed in
1994 tells a siter nothing about today's owner. Admitted = a sane decision date within 10 years;
older cases are carried with `severe = FALSE` so they still appear in the denominator.

⛔ ONE THING THIS SCRIPT DELIBERATELY DOES NOT DECIDE. D8 sits in the DISTRESS family, but a filed
rezoning petition is a STATED intent, not an inferred one — which is the declared-intent (I-code)
family that I3_land_bank belongs to. Re-homing a signal changes what every surface says about it,
so it is flagged for the operator in G163 rather than done unilaterally here.

RE-SCRAPE COMMAND: python scripts/build_si_rezoning_placement.py
⛔ Writes `indiana_app.in_si_rezoning_placed` ONLY. Reads `energy.parcels_in` (READ-ONLY).
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

from si_address_norm import naddr

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
OUT = f"{DS}.in_si_rezoning_placed"
D85 = "080500000047000018"
RECENT_YEARS = 10
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH r AS (
  SELECT
    CAST(objectid AS STRING) AS case_id,
    caseno, petitner AS petitioner, dispos, pri_zon, sec_zon,
    SAFE_CAST(acres AS FLOAT64) AS acres,
    -- the publisher gives no city: the layer is Indianapolis, so the parcel side is cut to Marion
    TRIM(CONCAT(IFNULL(CAST(stnum AS STRING), ''), ' ', IFNULL(stdir, ''), ' ',
                IFNULL(stname, ''))) AS raw_street,
    -- EPOCH MILLISECONDS IN A FLOAT. SAFE_CAST twice: the column is FLOAT64, TIMESTAMP_MILLIS
    -- needs INT64, and a bad value must yield NULL rather than kill the query.
    DATE(TIMESTAMP_MILLIS(CAST(SAFE_CAST(decision_date AS FLOAT64) AS INT64))) AS decided,
    SAFE_CAST(SAFE_CAST(ent_date AS TIMESTAMP) AS DATE) AS entered
  FROM `{DS}.in_si_up_indy_rezoning`
  WHERE stname IS NOT NULL AND stname != '' AND stnum IS NOT NULL
),
rr AS (
  SELECT *, {{naddr_raw}} AS nstreet, {{naddr_raw_nd}} AS nstreet_nd,
    COALESCE(IF(decided BETWEEN '1980-01-01' AND CURRENT_DATE(), decided, NULL),
             IF(entered BETWEEN '1980-01-01' AND CURRENT_DATE(), entered, NULL)) AS event_date,
    IF(decided BETWEEN '1980-01-01' AND CURRENT_DATE(),
       'publisher decision date (epoch ms)', 'publisher entry date') AS date_basis
  FROM r
),
-- Marion County parcels only. county_fips 18097 - the layer is Indianapolis and matching a bare
-- street name statewide would collide across all 92 counties.
p AS (
  SELECT state_parcel_id AS parcel_key,
         {{naddr_dlgf}} AS nstreet, {{naddr_dlgf_nd}} AS nstreet_nd
  FROM `{EN}.parcels_in`
  WHERE state_parcel_id IS NOT NULL AND state_parcel_id != '{D85}'
    AND CAST(county_fips AS STRING) = '18097'
    AND dlgf_prop_address IS NOT NULL AND dlgf_prop_address != ''
),
pd  AS (SELECT nstreet,    COUNT(DISTINCT parcel_key) n_parcels,
               ANY_VALUE(parcel_key) parcel_key FROM p GROUP BY 1),
pnd AS (SELECT nstreet_nd, COUNT(DISTINCT parcel_key) n_parcels,
               ANY_VALUE(parcel_key) parcel_key FROM p GROUP BY 1),
m1 AS (SELECT rr.case_id, pd.parcel_key, pd.n_parcels, 'exact_normalised' AS match_method
       FROM rr JOIN pd USING (nstreet)),
m2 AS (SELECT rr.case_id, pnd.parcel_key, pnd.n_parcels, 'directional_dropped' AS match_method
       FROM rr JOIN pnd USING (nstreet_nd)
       WHERE NOT EXISTS (SELECT 1 FROM m1 WHERE m1.case_id = rr.case_id)
         AND pnd.n_parcels = 1),
hit AS (SELECT * FROM m1 UNION ALL SELECT * FROM m2)
-- LEFT JOIN. The universe is every addressed case, including those that match no parcel, so the
-- coverage denominator is honest. An inner join reports 100% placement by construction.
SELECT
  rr.case_id, rr.caseno, rr.petitioner, rr.dispos, rr.pri_zon, rr.sec_zon, rr.acres,
  rr.raw_street, rr.event_date, rr.date_basis,
  'parcels_in' AS parcel_source, hit.parcel_key,
  hit.n_parcels AS parcels_sharing_this_address, hit.match_method,
  CASE WHEN hit.parcel_key IS NULL THEN 'no_parcel_at_that_address'
       WHEN hit.n_parcels = 1      THEN 'exact_parcel'
       ELSE 'address_shared_by_several_parcels' END AS match_grain,
  (rr.event_date IS NOT NULL
   AND rr.event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {RECENT_YEARS} YEAR)) AS is_recent,
  CURRENT_TIMESTAMP() AS built_at
FROM rr LEFT JOIN hit USING (case_id)
"""
SQL = SQL.replace("{naddr_raw}", naddr("raw_street"))          .replace("{naddr_raw_nd}", naddr("raw_street", drop_dir=True))          .replace("{naddr_dlgf}", naddr("dlgf_prop_address"))          .replace("{naddr_dlgf_nd}", naddr("dlgf_prop_address", drop_dir=True))



def main():
    print("=" * 96)
    print("G163(a) - D8_exit_intent PLACED FROM THE FULL-WIDTH REZONING CLIP")
    print("=" * 96)
    dry = client.query(SQL, job_config=bigquery.QueryJobConfig(dry_run=True))
    gb = dry.total_bytes_processed / 1e9
    print(f"  dry-run {gb:.2f} GB")
    if gb > 60:
        raise SystemExit(f"⛔ {gb:.0f} GB is above the cost flag - tighten the prefilter first")
    client.query(SQL).result()

    r = list(client.query(f"""
      SELECT COUNT(*) cases,
             COUNTIF(event_date IS NOT NULL) dated,
             COUNTIF(parcel_key IS NOT NULL) placed,
             COUNT(DISTINCT IF(match_grain='exact_parcel', parcel_key, NULL)) parcels,
             COUNTIF(match_grain='address_shared_by_several_parcels') spanning,
             COUNTIF(match_grain='exact_parcel' AND is_recent) admissible,
             COUNTIF(petitioner IS NOT NULL AND petitioner != '') named
      FROM `{OUT}`"""))[0]

    # ⛔ THE ZERO-ROW GUARD, AND IT EXISTS BECAUSE THIS SCRIPT ALREADY FAILED WITHOUT IT.
    # The first version parsed `geometry_geojson` as GeoJSON, matched NOTHING, wrote an EMPTY
    # table, and then PASSED its own fan-out check — because 0 rows / 0 ids evaluated to 0.000,
    # which is "below 1.05". It printed a registry row and exited 0 on a table with no data.
    # ⚠ *A ratio guard cannot see an empty numerator.* Count first, ratio second.
    if r.cases == 0 or r.placed == 0:
        raise SystemExit(
            f"⛔ {r.cases:,} cases, {r.placed:,} placed - a zero here is a BROKEN INSTRUMENT until\n"
            f"   proven otherwise, not a finding. Check, in order: does in_si_up_indy_rezoning\n"
            f"   still carry stnum/stdir/stname; does energy.parcels_in still have county_fips\n"
            f"   18097 rows; did the normaliser change. NOTHING WAS WRITTEN TO THE REGISTRY.")

    print(f"\n  {r.cases:,} rezoning cases · {r.dated:,} with a usable date")
    print(f"  {r.placed:,} matched an address · ⭐ {r.parcels:,} on EXACTLY ONE parcel")
    print(f"  ⚠ {r.spanning:,} matched an address shared by several parcels - carried, NOT admitted")
    print(f"  ⭐ {r.admissible:,} are on one parcel AND within {RECENT_YEARS} years - ADMISSIBLE")
    print(f"  ⭐ {r.named:,} carry a petitioner NAME - an owner name, on a signal that had none")

    print("\n  by decade, so the recency gate is arguable rather than asserted:")
    for x in client.query(f"""
      SELECT CAST(FLOOR(EXTRACT(YEAR FROM event_date)/10)*10 AS INT64) dec_,
             COUNT(*) n, COUNTIF(match_grain='exact_parcel') placed
      FROM `{OUT}` WHERE event_date IS NOT NULL GROUP BY 1 ORDER BY 1"""):
        print(f"     {x.dec_}s   {x.n:>6,} cases   {x.placed:>6,} on one parcel")

    fan = list(client.query(
        f"SELECT COUNT(*) n, COUNT(DISTINCT case_id) k FROM `{OUT}`"))[0]
    ratio = fan.n / fan.k if fan.k else 0
    print(f"\n  fan-out {ratio:.3f} - {'OK' if ratio < 1.05 else '⛔ DUPLICATING CASES'}")
    if ratio >= 1.05:
        raise SystemExit("⛔ fan-out above 1.05 - the spatial join is multiplying cases")

    client.query(f"""
      INSERT INTO `{DS}._registry` (table_name, source, method, built_at)
      VALUES ('in_si_rezoning_placed',
        'indiana_app.in_si_up_indy_rezoning x energy.parcels_in',
        'D8_exit_intent placed by normalised stnum+stdir+stname against dlgf_prop_address on '
        'Marion County parcels (county_fips 18097), two passes (exact, then directional-dropped '
        'where unique), D85 excluded, LEFT JOIN so the universe is the denominator. Admitted only '
        'where the address resolves to EXACTLY ONE parcel. '
        '⛔ NOT placed spatially: the column named geometry_geojson holds ESRI JSON ({{"rings":...}}) '
        'in Indiana State Plane FEET, so ST_GEOGFROMGEOJSON returns NULL on all 13,414 rows. '
        'decision_date is EPOCH MILLISECONDS in a FLOAT column - 135 values decode to '
        'before 1980 and are rejected. Severity = decided within {RECENT_YEARS} years. '
        'RE-SCRAPE COMMAND: python scripts/build_si_rezoning_placement.py '
        '⚠ IDEMPOTENT: replace_safe - CREATE OR REPLACE, a re-run cannot double-count.',
        CURRENT_TIMESTAMP())""").result()
    print("  _registry row written")
    print("=" * 96)


if __name__ == "__main__":
    main()
