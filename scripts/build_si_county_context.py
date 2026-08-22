"""G163(c): THE AGGREGATE SIGNALS REACH THE APPLICATION — AT THE GRAIN THEY ACTUALLY HAVE.

⛔ THE PROBLEM. Three of 27 SI signals admit zero parcels for the same reason: `wrong_grain`. The
publisher does not describe a property, so no source block can put them on a parcel, and for weeks
they have shown as bare zeros with nothing saying why.

⭐ OPERATOR, 2026-08-22b: *"We need to ensure that everything hits the application, to the extent
possible."* ⚠ The honest reading of *to the extent possible* is NOT to force a county number onto a
parcel — that would invent precision we do not have, which is the defect that put 705 false
distressed buildings on the map when a CMBS `0` was read as an occupancy. It is to publish them at
the grain they have, on the surface that already answers a county-level question.

⭐ ONE OF THE THREE SHIPS. THE OTHER TWO ARE RECORDED REFUSALS, AND ONE OF THEM WAS BUILT FIRST
AND THEN WITHDRAWN — the measurement that killed it is in the D17 block below, kept deliberately.

  · **D25_rail_abandonment** — SHIPS. `si_d25_stb_abandonment_state`; its `docket_title` names the
    county verbatim: *"FULTON COUNTY, LLC--ABANDONMENT EXEMPTION--IN FULTON COUNTY, IND."* A rail
    line being abandoned is a genuine siting fact — it frees a corridor and it removes a rail
    option — the county is the grain the STB publishes at, and rail corridors are non-residential
    by nature, so the operator's rule is satisfied rather than assumed.
    ⚠ RECENCY GATE: last 10 years only, matching D8. 127 Indiana dockets run 2000-2026 and a
    corridor abandoned in 2003 has long since been railbanked, sold or built over.

  · **D17_commercial_eviction** — BUILT, THEN WITHDRAWN. It cannot satisfy the non-residential
    rule and no filter can make it. See the block in the SQL below.

  · **D6_bankruptcy** — refused; named private individuals and office-level financial totals.

⛔ AND THE THIRD IS A REFUSAL, FOR A BETTER REASON THAN GRAIN. `D6_bankruptcy` has two parents and
neither can ship:
  · `in_ustp_ch7_tfr` (76,010 rows) is trustee financial totals BY OFFICE AND MONTH. No debtor,
    no case, no address. Three documents called this one of the *"cheapest wins… what is missing
    is a source block"*; no source block can place a county-month dollar total.
  · `in_si_up_bankruptcy` (90 dockets) — **measured: 0 of 90 carry a business-entity token. All
    ninety are named private individuals filing personal Chapter 7.** Even a perfect owner-name
    bridge would land them on RESIDENTIAL parcels, which the spine excludes by rule anyway. ⚠ And
    it would mean publishing named individuals' financial distress against their home addresses.
    **That is not a data gap to close. It is a thing not to build**, and the reason belongs in the
    record so nobody re-opens it as an opportunity.

⚠ THIS IS CONTEXT, NOT A FINDING, AND MUST RENDER AS SUCH. The governing principle's own test:
*"Is it context rather than a finding? Say so explicitly, and keep it small."* These rows carry
`grain = 'county'` and MUST NOT be merged into any parcel signal count — a county with 1,228
evictions does not make its 40,000 parcels distressed.

RE-SCRAPE COMMAND: python scripts/build_si_county_context.py
⛔ Writes `indiana_app.in_si_county_context` ONLY.
"""
import sys as _sys

try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
OUT = f"{DS}.in_si_county_context"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH counties AS (
  -- ⛔ in_county_rollup stores 'Allen County'; the court table stores 'ALLEN'; the STB title says
  -- 'FULTON COUNTY'. Three spellings of one thing, and the first version of this join compared
  -- 'ALLEN COUNTY' to 'ALLEN' and matched ZERO rows. `cname` is the BARE upper-case name, and the
  -- ' COUNTY' is added back only where the other side carries it.
  SELECT county_fips, county_name,
         UPPER(REGEXP_REPLACE(county_name, r'(?i)\\s+COUNTY$', '')) AS cname
  FROM `{DS}.in_county_rollup`
),
-- ================================================================================================
-- ⛔ D17_commercial_eviction IS REFUSED, 2026-08-22b. IT WAS BUILT, MEASURED, AND WITHDRAWN.
--
-- Operator: *"ensure that ONLY non-residential (as is the current working rule) observations make
-- it through to the application."* ⭐ MEASURED AGAINST THAT RULE, THIS SOURCE CANNOT PASS IT.
-- `in_si_up_iocs_court` publishes Indiana court case-type COUNTS — ev 347,511 · sc 388,462 ·
-- mf 47,734 · cc 598,145 · ct 63,209 · pl 50,972 — and **there is no commercial/residential split
-- in any of them.** Indiana's EV case type is overwhelmingly residential landlord-tenant.
--
-- ⛔ So a signal NAMED `D17_commercial_eviction` cannot be shown to be commercial, and no filter
-- available to us can make it so. Shipping it would have published ~278,645 mostly-residential
-- filings under a commercial label — the exact shape of the CMBS `0`-means-unpublished defect
-- that invented 705 distressed buildings.
-- ⚠ A RECENCY WINDOW WOULD NOT HAVE SAVED IT. Narrowing 2022-2025 to one year makes the number
-- smaller and no more commercial. The defect is the label, not the volume.
-- ⭐ Recorded as `refused_residential` on in_si_signal_coverage so the reason survives, and so
-- nobody re-opens it as an easy county-grain win. What WOULD close it is a source that separates
-- commercial tenancies — the courts do not publish one.
-- ================================================================================================
-- ---- D25: the STB docket, placed by the county its own title names ----------------------------
stb AS (
  -- ⛔ filed_date is 'M/D/YYYY' — `1/29/2013`, not ISO. A plain CAST returns NULL on every row and
  -- the first build printed `latest None` for all 22 counties. The standing rule spells this out:
  -- *"MM/DD/YYYY is not ISO"*, and %m/%d/%Y parses a single-digit month and day too.
  SELECT DISTINCT docket, docket_title,
         SAFE.PARSE_DATE('%m/%d/%Y', filed_date) AS filed
  FROM `{EN}.si_d25_stb_abandonment_state`
  WHERE UPPER(IFNULL(state, '')) = 'IN' AND docket_title IS NOT NULL
),
stb_recent AS (
  -- ⚠ RECENCY, on the operator's instruction and matching D8's 10-year gate. 127 Indiana
  -- dockets run 2000-2026; a corridor abandoned in 2003 has long since been railbanked, sold
  -- or built over, and tells a siter nothing about today. Undated dockets are DROPPED rather
  -- than assumed recent - absence of a date is not evidence of currency.
  SELECT * FROM stb
  WHERE filed IS NOT NULL AND filed >= DATE_SUB(CURRENT_DATE(), INTERVAL 10 YEAR)
),
d25 AS (
  SELECT c.county_fips, c.county_name, 'D25_rail_abandonment' AS signal,
         COUNT(DISTINCT stb.docket)                AS value_num,
         'STB abandonment dockets'                 AS value_unit,
         CAST(EXTRACT(YEAR FROM MIN(stb.filed)) AS STRING) || '-' ||
           CAST(EXTRACT(YEAR FROM MAX(stb.filed)) AS STRING) AS period,
         CAST(NULL AS INT64)                       AS value_secondary,
         CAST(NULL AS STRING)                      AS secondary_unit,
         MAX(stb.filed)                            AS last_event_date,
         'US Surface Transportation Board abandonment dockets'                    AS publisher
  FROM counties c
  -- ⚠ the county is matched as a WHOLE WORD followed by COUNTY, against the 92 real names. A bare
  -- substring would match LAKE inside 'LAKELAND' and WHITE inside 'WHITLEY'.
  JOIN stb_recent stb ON REGEXP_CONTAINS(UPPER(stb.docket_title), r'\\b' || c.cname || r' COUNTY\\b')
  GROUP BY 1, 2
)
SELECT *, 'county' AS grain, CURRENT_TIMESTAMP() AS built_at
FROM d25
ORDER BY signal, value_num DESC
"""


def main():
    print("=" * 96)
    print("G163(c) - THE AGGREGATE SI SIGNALS, PUBLISHED AT COUNTY GRAIN")
    print("=" * 96)
    dry = client.query(SQL, job_config=bigquery.QueryJobConfig(dry_run=True))
    print(f"  dry-run {dry.total_bytes_processed / 1e9:.3f} GB")
    client.query(SQL).result()

    rows = list(client.query(f"""
      SELECT signal, COUNT(*) counties, SUM(value_num) total,
             ANY_VALUE(value_unit) unit, MIN(period) period
      FROM `{OUT}` GROUP BY 1 ORDER BY 1"""))
    if not rows:
        raise SystemExit("⛔ EMPTY. A zero here is a broken instrument, not a finding: check that "
                         "in_county_rollup still has 92 county_name rows and that the court table "
                         "still spells its counties in upper case. Nothing was registered.")
    for r in rows:
        print(f"\n  {r.signal}")
        print(f"     {r.counties} counties · {int(r.total):,} {r.unit} · {r.period}")

    # ⛔ D17 is deliberately absent - it is a recorded refusal, not an omission. Saying so on every
    # run is the point: a signal that silently stops appearing looks exactly like a broken build.
    print("\n  ⛔ D17_commercial_eviction is NOT in this table, by decision. The Indiana courts "
          "publish\n     no commercial/residential split, so it cannot meet the non-residential "
          "rule and no\n     filter can make it. See the D17 block in the SQL, and "
          "in_si_signal_coverage.zero_reason.")
    print("\n  rail abandonment, by county (last 10 years only):")
    for x in client.query(f"""
      SELECT county_name, value_num, last_event_date FROM `{OUT}`
      WHERE signal = 'D25_rail_abandonment' ORDER BY value_num DESC LIMIT 6"""):
        print(f"     {x.county_name:16} {int(x.value_num):>3} docket(s), latest {x.last_event_date}")

    # ⛔ 92 is the ceiling. More than that means a county name matched twice.
    n = list(client.query(
        f"SELECT COUNT(*) n FROM (SELECT DISTINCT county_fips, signal FROM `{OUT}`)"))[0].n
    tot = list(client.query(f"SELECT COUNT(*) n FROM `{OUT}`"))[0].n
    print(f"\n  fan-out {tot / n:.3f} ({tot} rows / {n} county-signal pairs)")
    if tot != n:
        raise SystemExit("⛔ a county appears twice for one signal - the name match is ambiguous")

    client.query(f"""
      INSERT INTO `{DS}._registry` (table_name, source, method, built_at)
      VALUES ('in_si_county_context',
        'indiana_app.in_si_up_iocs_court + energy.si_d25_stb_abandonment_state x in_county_rollup',
        'The SI signals whose publisher grain is a COUNTY, published as county context rather than '
        'forced onto parcels. D17 sums the courts per county-year (row_scope=court only; the 3 '
        'statewide_total rows are excluded). D25 matches the county named in the STB docket_title '
        'as a whole word followed by COUNTY, against the 92 real names. '
        '⚠ grain=county. MUST NOT be merged into any parcel signal count - a county with 1,228 '
        'evictions does not make its parcels distressed. '
        'RE-SCRAPE COMMAND: python scripts/build_si_county_context.py '
        '⚠ IDEMPOTENT: replace_safe - CREATE OR REPLACE, a re-run cannot double-count.',
        CURRENT_TIMESTAMP())""").result()
    print("  _registry row written")
    print("=" * 96)


if __name__ == "__main__":
    main()
