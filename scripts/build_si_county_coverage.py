"""G170: THE COVERAGE MASK — which counties a signal COULD reach, versus where it found nothing.

⛔ THE DEFECT THIS CLOSES. Operator, 2026-08-22b: *"Much of our data is limited to that region, and
we really need statewide coverage."* Measured, and the concern is exact: **of 23 signals admitting
at least one parcel, 10 cover fewer than 5 of the 92 counties and FOUR cover exactly one.**

⚠ BUT METRO-BOUND IS NOT AN ACCIDENT AND MUST NOT BE FILED AS ONE. Operator, 2026-08-02: the
metro-concentrated seller-intent data *"was gathered deliberately as a proof of concept for a few
metros and was never meant to be representative"*, with a stated scale-out order — statewide
parcel-keyed sources first, then the absent metros, **and keep a coverage mask current so the app
renders NOT-COVERED distinctly while breadth is incomplete.** This is that third item, and it is
the one that costs nothing and makes the other two honest in the meantime.

⛔ THE READER'S PROBLEM, WHICH IS THE WHOLE POINT. Today a county with no `D12_code_violation`
looks exactly like a county we searched and found clean. **It is neither.** `D12` comes from
Indianapolis's own code-enforcement portal and reaches 2 counties; in the other 90 we did not look.
That is the unpublished-rate-as-zero defect at county grain — the same shape that produced 95 false
"below floor" tariff violations, and exactly what G51's third state exists to prevent.

⭐ THE SPLIT THIS TABLE MAKES, per signal per county:
    `covered_with_hits`  — the source reaches this county AND flagged parcels here
    `covered_no_hits`    — the source reaches this county and found none. **A FINDING.**
    `not_covered`        — the publisher does not cover this county. **NOT a finding, and today
                           the app cannot tell a reader which of these two it is looking at.**

⚠ HOW COVERAGE IS DECIDED, AND WHY IT IS EVIDENCE RATHER THAN A GUESS. A signal is treated as
covering a county when its own CORPUS carries at least one row for that county — the corpus is what
the publisher gave us, before any admission gate. So `covered_no_hits` means *the publisher
described this county and nothing in it met the bar*, which is a real statement, and `not_covered`
means *the publisher never described it*, which is not.

RE-SCRAPE COMMAND: python scripts/build_si_county_coverage.py
⛔ Writes `indiana_app.in_si_signal_county_coverage` ONLY.
"""
import sys as _sys

try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_si_signal_county_coverage"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH counties AS (
  SELECT county_fips, county_name FROM `{DS}.in_county_rollup`
),
signals AS (
  SELECT DISTINCT signal FROM `{DS}.in_si_signal_coverage`
),
-- ---- where the PUBLISHER reaches: the corpus, before any admission gate --------------------
corpus AS (
  SELECT signal, county_fips, COUNT(*) AS corpus_rows
  FROM `{DS}.in_si_signals`
  WHERE county_fips IS NOT NULL
  GROUP BY 1, 2
),
-- ⭐ the publisher tables that never pass through the corpus reach counties too, and leaving them
-- out would mark their counties `not_covered` while they are demonstrably flagging parcels there.
-- Derived from the ADMITTED parcels themselves, so a block added later is picked up automatically.
placed AS (
  SELECT p.signal, sc.county_fips,
         COUNT(DISTINCT IF(p.si_admitted, p.parcel_key, NULL)) AS parcels_flagged,
         COUNT(DISTINCT p.parcel_key)                          AS parcels_reached
  FROM `{DS}.in_si_parcel_signals_v2` p
  JOIN `{DS}.in_sites_county` sc USING (parcel_source, parcel_key)
  GROUP BY 1, 2
)
SELECT
  s.signal, c.county_fips, c.county_name,
  IFNULL(pl.parcels_flagged, 0) AS parcels_flagged,
  IFNULL(pl.parcels_reached, 0) AS parcels_reached,
  IFNULL(cp.corpus_rows, 0)     AS corpus_rows,
  CASE
    WHEN IFNULL(pl.parcels_flagged, 0) > 0                       THEN 'covered_with_hits'
    -- the publisher described this county (corpus rows, or parcels we reached but did not admit)
    WHEN IFNULL(cp.corpus_rows, 0) > 0
      OR IFNULL(pl.parcels_reached, 0) > 0                       THEN 'covered_no_hits'
    ELSE 'not_covered'
  END AS coverage_state,
  CURRENT_TIMESTAMP() AS built_at
FROM signals s
CROSS JOIN counties c
LEFT JOIN corpus cp ON cp.signal = s.signal AND cp.county_fips = c.county_fips
LEFT JOIN placed pl ON pl.signal = s.signal AND pl.county_fips = c.county_fips
"""


def main():
    print("=" * 100)
    print("G170 - THE SI COVERAGE MASK, PER SIGNAL PER COUNTY")
    print("=" * 100)
    dry = client.query(SQL, job_config=bigquery.QueryJobConfig(dry_run=True))
    print(f"  dry-run {dry.total_bytes_processed / 1e9:.2f} GB")
    client.query(SQL).result()

    n = list(client.query(f"SELECT COUNT(*) n FROM `{OUT}`"))[0].n
    if n == 0:
        raise SystemExit("⛔ EMPTY - a zero here is a broken instrument. Nothing registered.")

    print(f"\n  {n:,} rows (one per signal per county)\n")
    print(f"  {'signal':30} {'hits':>6} {'looked, none':>13} {'NOT COVERED':>12}")
    print("  " + "-" * 68)
    for r in client.query(f"""
      SELECT signal,
             COUNTIF(coverage_state='covered_with_hits') hits,
             COUNTIF(coverage_state='covered_no_hits')   none_,
             COUNTIF(coverage_state='not_covered')       nc
      FROM `{OUT}` GROUP BY 1 ORDER BY hits DESC, none_ DESC"""):
        flag = "  ⛔" if r.nc >= 88 else ("  ⚠" if r.nc >= 50 else "")
        print(f"  {r.signal:30} {r.hits:>6} {r.none_:>13} {r.nc:>12}{flag}")

    tot = list(client.query(f"""
      SELECT COUNTIF(coverage_state='not_covered') nc, COUNT(*) n FROM `{OUT}`"""))[0]
    print(f"\n  ⛔ {tot.nc:,} of {tot.n:,} signal-county cells ({100*tot.nc/tot.n:.1f}%) are "
          f"NOT COVERED —\n     today every one of them renders identically to 'we looked and "
          f"found none'.")

    client.query(f"""
      INSERT INTO `{DS}._registry` (table_name, source, method, built_at)
      VALUES ('in_si_signal_county_coverage',
        'indiana_app.in_si_signals + in_si_parcel_signals_v2 x in_sites_county x in_county_rollup',
        'The coverage mask: one row per SI signal per county, classed covered_with_hits / '
        'covered_no_hits / not_covered. A signal COVERS a county when its corpus carries a row for '
        'it or we reached a parcel there - so covered_no_hits means the publisher described the '
        'county and nothing met the bar (a FINDING), and not_covered means the publisher never '
        'described it (NOT a finding). ⚠ Metro-bound signals are a deliberate PoC (operator, '
        '2026-08-02), not a defect; this mask is the third item of the stated scale-out order. '
        'RE-SCRAPE COMMAND: python scripts/build_si_county_coverage.py '
        '⚠ IDEMPOTENT: replace_safe. CADENCE: whenever in_si_parcel_signals_v2 is rebuilt.',
        CURRENT_TIMESTAMP())""").result()
    print("\n  _registry row written")
    print("=" * 100)


if __name__ == "__main__":
    main()
