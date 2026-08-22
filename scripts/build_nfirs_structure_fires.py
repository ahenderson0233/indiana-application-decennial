"""A4 — NFIRS structure fires, wired (not waived), with two defects fixed on the way in.

Measured before deciding:

  1. THESE TABLES ARE NOT A FIRE SIGNAL AS THEY STAND. Only ~21% of incidents are structure
     fires (8,145 of 38,287 in 2020; 8,119 of 38,492 in 2021). The rest is everything else a
     department logs — gas leaks (INC_TYPE 412), downed power lines (444), rubbish fires (151),
     vehicle fires (131), cooking fires (113). Admitting all 38k as "fires" would inflate D16
     roughly fivefold. Filtered to NFIRS INC_TYPE 111-123, the building/structure range.

  2. ✅ FIXED BY G152, 2026-08-21 — this paragraph is kept as the REASON the STATE='IN' filters
     below are still here. It used to read: *"in_nfirs_fireincident_2024 IS NOT INDIANA-CLIPPED.
     Only 848 of its 1,255 rows are STATE='IN'; 407 (32%) belong to 43 other states."* G152
     re-clipped every year Indiana-only at full width, so the out-of-state rows are gone.
     ⚠ THE EXPLICIT `STATE = 'IN'` FILTERS STAY ANYWAY. They cost nothing, and an `in_*` name is
     not a measurement — that is exactly what let a third of this table be out-of-state while
     nothing noticed.

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

# ⛔ 2026-08-20 (G72/G80): THIS SIGNAL WAS THREE YEARS STALE AGAINST DATA WE ALREADY HELD.
#    The union stopped at 2021 while `in_nfirs_basicincident_2022` (40,044),
#    `_2023` (46,748) and `_2024` (49,811) sat in indiana_app, registered and unread. A fire is
#    an EVENT signal, so its whole value is recency - the seller-intent case for a 2021 fire is
#    much weaker than for a 2024 one, and we were showing only the weak half.
#    ⚠ It also fixes a latent join defect: `fire` already unioned 2024 while `inc` did not, so
#    every 2024 NOT_RES flag joined to nothing and was silently discarded.
#
# ⛔ 2026-08-22b: THE LINE BELOW USED TO BE A PINNED LIST AND G152 INVALIDATED IT SILENTLY.
#    It read `FIRE_YEARS = ["2020","2021","2022","2024"]  # 2023 fireincident is not held`, and by
#    2026-08-21 that comment was false: G152 clipped `in_nfirs_fireincident_2023` (13,006 rows) and
#    repaired 2022 (1,221 -> 10,548) and 2024 (1,255 -> 11,961), recovering 33,039 Indiana rows.
#    Re-running this builder afterwards produced a BYTE-IDENTICAL 45,607 rows and 1,583 SI-grade,
#    because the pinned list still excluded 2023 and nothing compared the list to the warehouse.
#    ⚠ That is the project's pinned-literal defect for the FOURTH time: *a hardcoded list turns a
#    measurement into a constant, and a constant cannot notice that the data changed.*
#    ⭐ FIRE_YEARS is now MEASURED from __TABLES__ every run, so a year that arrives is picked up
#    and a year that vanishes is reported rather than silently skipped.
#
# ⚠ fireincident COVERAGE WAS UNEVEN AND IS NOW COMPLETE, BUT DO NOT ASSUME EITHER - the run prints
#   what it found. `non_residential` comes from NOT_RES on this table, so any year absent here
#   renders as "not stated", never as "residential" - the three-state rule that stopped 95 false
#   tariff violations. `property_class`, derived from PROP_USE on the basicincident table, is
#   complete for every year and is the column a surface should prefer.
YEARS = ["2020", "2021", "2022", "2023", "2024"]


def _fire_years_held():
    """Which in_nfirs_fireincident_YYYY clips actually hold rows, asked of the warehouse."""
    rows = list(client.query(f"""
      SELECT table_id, row_count FROM `{DS}.__TABLES__`
      WHERE table_id LIKE 'in_nfirs_fireincident_%' AND row_count > 0"""))
    held = sorted(r.table_id.replace("in_nfirs_fireincident_", "") for r in rows)
    got = [y for y in YEARS if y in held]
    missing = [y for y in YEARS if y not in held]
    print(f"  fireincident years held: {', '.join(got) or 'NONE'}"
          + (f"   ⚠ ABSENT: {', '.join(missing)}" if missing else "   (all five)"))
    if not got:
        raise SystemExit("⛔ no in_nfirs_fireincident_* clip holds any rows - NOT_RES would be "
                         "NULL on every row. Run scripts/build_si_upstream_wide.py first.")
    return got


FIRE_YEARS = _fire_years_held()

_inc = "\n  UNION ALL\n  ".join(
    f"""SELECT '{y}' AS yr, INCIDENT_KEY, STATE, FDID, INC_DATE, INC_TYPE,
         PROP_LOSS, CONT_LOSS, PROP_VAL, PROP_USE, OTH_DEATH, OTH_INJ
  FROM `{DS}.in_nfirs_basicincident_{y}` WHERE STATE = 'IN'""" for y in YEARS)
_addr = "\n  UNION ALL\n  ".join(
    f"""SELECT INCIDENT_KEY, NUM_MILE, STREET_PRE, STREETNAME, STREETTYPE, CITY, ZIP5
  FROM `{DS}.in_nfirs_incidentaddress_{y}` WHERE STATE = 'IN'""" for y in YEARS)
_fire = "\n  UNION ALL\n  ".join(
    f"""SELECT INCIDENT_KEY, NOT_RES, BLDG_INVOL, ACRES_BURN
  FROM `{DS}.in_nfirs_fireincident_{y}` WHERE STATE = 'IN'""" for y in FIRE_YEARS)

SQL = f"""
WITH inc AS (
  {_inc}),
addr AS (
  {_addr}),
-- fireincident carries the NOT_RES flag: the non-residential subset is the C&I-relevant half
fire AS (
  {_fire})
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
      "INC_TYPE 111-123 (building/structure fires) only, STATE='IN' enforced on every input. "
      "basicincident supplies the incident LIST and the loss columns; incidentaddress supplies the "
      "street; fireincident supplies NOT_RES and BLDG_INVOL and its year list is MEASURED from "
      "__TABLES__ every run, never pinned. "
      # ⛔ THIS ROW HAD NO RE-SCRAPE COMMAND AND audit_handoff_docs.py said so, 2026-08-22b - the
      # only non-ladder object in the estate missing one. G16's test is whether a stranger could
      # re-run the work from the registry row alone, and for a table feeding a live signal they
      # could not.
      "RE-SCRAPE COMMAND: python scripts/build_nfirs_structure_fires.py . "
      "IDEMPOTENCY: replace_safe - CREATE OR REPLACE from indiana_app clips only, so a re-run "
      "cannot double-count. CADENCE: whenever any in_nfirs_* clip is rebuilt."),
    bigquery.ScalarQueryParameter("n", "INT64", n),
    bigquery.ScalarQueryParameter("g", "FLOAT64", round(gb, 4)),
    bigquery.ScalarQueryParameter("o", "STRING",
      "⭐ 2026-08-22b: NO LONGER address-grain only. build_si_addr_placement.py keys the "
      "non-residential, >=$10k subset to parcels and D16_structure_fire now admits 1,783. "
      "Two defects fixed on the way in: (1) only ~21% of NFIRS incidents are structure fires, so "
      "admitting the raw tables would have inflated D16 about fivefold; (2) the fireincident clips "
      "used to carry out-of-state rows - G152 re-clipped every year Indiana-only, and STATE='IN' "
      "is STILL enforced explicitly because an in_* name is not a measurement. "
      "⛔ AND A PINNED YEAR LIST USED TO SWALLOW THE REPAIR: FIRE_YEARS excluded 2023 after G152 "
      "had clipped it, so a re-run produced a byte-identical 45,607 rows. It is measured now; "
      "2023 NOT_RES coverage went 0 -> 4,357. "
      "Keying quality is carried per row: ~91% have number+street.")])).result()
print(f"in_nfirs_structure_fires: {n:,} rows, registered")
