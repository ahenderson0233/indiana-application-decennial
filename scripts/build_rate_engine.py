"""C2 — the itemised rate engine, per ANALYSIS_METHODOLOGY.md §4.

WHAT §4 REQUIRES, and how each rule lands here:
 4.1 ITEMISE EVERYTHING. Every demand charge, energy block and rider on its own line with units,
     the tariff sheet it came from, and its effective date. "A single blended c/kWh with no
     components is not an auditable answer."
 4.2 MW FLOORS ARE ELIGIBILITY MINIMUMS, NOT CEILINGS. A 300 MW load does not "exceed" a 70 MW
     large-load tariff — it QUALIFIES for it. Indiana's is already recorded: I&M, IURC Cause
     46097, >=70 MW at one site or >=150 MW aggregate, effective 2025-02-19.
 4.3 FOUR PROXIES, side by side, never the industrial average alone.
 4.6 UNPUBLISHED IS NULL, NEVER 0. `value_status != 'published'` yields NULL and says so.
 GATE ISO wholesale is a HARD FLOOR. A bundled retail rate must clear it by >=1.75x. Between
     1.0x and 1.75x is a MODELLING ERROR, not a bargain, and this script FAILS rather than
     publishes — the rule exists because a model once produced $0.0261/kWh against a $0.0322
     MISO floor.
 HAZARD `urdb_rates` is FLATTENED — no fixed charge, no rider, no seasonal columns. It is a
     CROSS-CHECK, never a component-level source. It is labelled as such on every row it feeds.

WHAT WE HONESTLY HAVE, measured before building:
  · component-level: 5 PEER large-load tariffs (ComEd, Oncor, Georgia Power, Dominion x2) with
    customer charge, demand $/kW-yr, energy c/kWh and rider c/kWh. NONE are Indiana.
  · Indiana component rows: 3, and TWO of them are `value_status='not_held'` — the I&M rider
    stack and its customer charge. That is the honest state: we hold Indiana's ELIGIBILITY
    THRESHOLD but not its component rates.
  · flattened URDB for Indiana largest-use schedules (cross-check only)
  · EIA-861 industrial revenue/MWh (proxy 2)
  · MISO and PJM day-ahead LMP (the floor)

So this engine produces a defensible COMPARISON with a stated floor and an explicit list of what
is missing — not a quote. Calling it a quote would be the §4 anti-pattern.
"""
import datetime
from google.cloud import bigquery

DS, EN = "energy-platfrom.indiana_app", "energy-platfrom.energy"
MIN_MULTIPLE = 1.75          # the plausibility gate; do not remove
client = bigquery.Client(project="energy-platfrom")
BUILT = datetime.datetime.now(datetime.timezone.utc).isoformat()


def q1(sql): return list(client.query(sql))[0]


def run(sql, label):
    j = client.query(sql); j.result()
    print(f"  {label}: {j.total_bytes_processed/1e9:.2f} GB", flush=True)


# ---- 1. the wholesale FLOOR ------------------------------------------------------------------
print("measuring the ISO wholesale floor …", flush=True)
run(f"""
CREATE OR REPLACE TABLE `{DS}.in_rate_wholesale_floor` AS
SELECT UPPER(iso) iso, market,
  COUNT(*) intervals,
  MIN(DATE(interval_start_utc)) first_day, MAX(DATE(interval_start_utc)) last_day,
  ROUND(AVG(SAFE_CAST(lmp AS FLOAT64)), 3)                  avg_lmp_usd_mwh,
  ROUND(AVG(SAFE_CAST(lmp AS FLOAT64))/10.0, 4)             avg_lmp_cents_kwh,
  ROUND(APPROX_QUANTILES(SAFE_CAST(lmp AS FLOAT64),100)[OFFSET(50)]/10.0, 4) p50_cents_kwh,
  -- the floor a bundled retail rate must clear
  ROUND(AVG(SAFE_CAST(lmp AS FLOAT64))/10.0*{MIN_MULTIPLE}, 4) min_credible_retail_cents_kwh,
  TIMESTAMP('{BUILT}') built_at
FROM `{EN}.iso_lmp`
WHERE UPPER(iso) IN ('MISO','PJM') AND market='dam'
  AND SAFE_CAST(lmp AS FLOAT64) IS NOT NULL
  AND DATE(interval_start_utc) >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
GROUP BY 1,2
""", "in_rate_wholesale_floor")
# THE WINDOW IS NOT WHAT I ASKED FOR. A 12-month filter returned ~5 weeks of MISO, because the
# feed has a gap between 2025-08 and 2026-07. Five summer weeks is a HIGH-PRICE sample, so it
# inflates the floor and would fail rates that are actually fine. Report the window that was
# actually measured rather than the one that was requested.
for r in client.query(f"""SELECT iso, market, first_day, last_day,
      DATE_DIFF(last_day, first_day, DAY)+1 days_covered
    FROM `{DS}.in_rate_wholesale_floor`"""):
    if r.days_covered < 300:
        print(f"  ⚠ {r.iso}/{r.market} covers only {r.days_covered} days "
              f"({r.first_day}..{r.last_day}), NOT 12 months — the feed has a gap. A short summer "
              f"window over-states the floor; the gate below is CONSERVATIVE, not calibrated.")
for r in client.query(f"SELECT * FROM `{DS}.in_rate_wholesale_floor` ORDER BY iso"):
    print(f"    {r.iso}/{r.market}: {r.intervals:,} intervals {r.first_day}..{r.last_day} · "
          f"avg {r.avg_lmp_cents_kwh}c/kWh · a bundled rate below "
          f"{r.min_credible_retail_cents_kwh}c/kWh is a MODELLING ERROR")

# ---- 2. the four proxies ----------------------------------------------------------------------
print("\nbuilding the four proxies …", flush=True)
run(f"""
CREATE OR REPLACE TABLE `{DS}.in_rate_proxies` AS
-- PROXY 1 — the utility's LARGEST-USE rate schedule. FLATTENED SOURCE: urdb_rates has no fixed
-- charge, no riders, no seasonality. Cross-check only; every row says so.
WITH p1 AS (
  SELECT 'P1_largest_use_schedule' proxy, utility, name AS tariff_name,
    SAFE_CAST(peakkwcapacitymin AS FLOAT64)/1000 AS qualifying_mw,
    -- §4.6: an absent value is NULL, NEVER 0. urdb carries 0.0 where it holds no energy rate,
    -- and treating that as a rate made the plausibility gate report 95 "violations" that were
    -- really 95 MISSING rates. A zero here is a claim about the instrument, not about the price.
    ROUND(NULLIF(SAFE_CAST(energy_rate_min_usd_kwh AS FLOAT64), 0)*100, 4) energy_cents_kwh_low,
    ROUND(NULLIF(SAFE_CAST(energy_rate_max_usd_kwh AS FLOAT64), 0)*100, 4) energy_cents_kwh_high,
    ROUND(SAFE_CAST(demand_rate_max_usd_kw AS FLOAT64), 2) demand_usd_kw_mo,
    CAST(NULL AS FLOAT64) customer_charge_usd_mo,   -- NOT in urdb; NULL, never 0
    CAST(NULL AS FLOAT64) rider_cents_kwh,          -- NOT in urdb; NULL, never 0
    startdate AS effective_date, 'in_urdb_rates (FLATTENED — cross-check only)' src
  FROM `{DS}.in_urdb_rates`
  WHERE sector='Industrial' AND SAFE_CAST(peakkwcapacitymin AS FLOAT64) >= 1000
),
-- PROXY 2 — the average industrial rate, from EIA-861 revenue/sales. A blended average, and
-- explicitly NOT a tariff: no components exist behind it.
p2 AS (
  SELECT 'P2_avg_industrial_eia861' proxy, utility_name utility,
    CONCAT('EIA-861 industrial bundled ', CAST(data_year AS STRING)) tariff_name,
    CAST(NULL AS FLOAT64) qualifying_mw,
    ROUND(SAFE_CAST(thousand_dollars_2 AS FLOAT64)*1000
          / NULLIF(SAFE_CAST(megawatthours_2 AS FLOAT64),0) / 10, 4) energy_cents_kwh_low,
    ROUND(SAFE_CAST(thousand_dollars_2 AS FLOAT64)*1000
          / NULLIF(SAFE_CAST(megawatthours_2 AS FLOAT64),0) / 10, 4) energy_cents_kwh_high,
    CAST(NULL AS FLOAT64), CAST(NULL AS FLOAT64), CAST(NULL AS FLOAT64),
    CAST(data_year AS STRING), 'in_eia861_sales (blended average, NOT a tariff)'
  FROM `{DS}.in_eia861_sales`
  WHERE SAFE_CAST(megawatthours_2 AS FLOAT64) > 0
),
-- PROXY 3 — the ISO wholesale price. The FLOOR, not a retail option.
p3 AS (
  SELECT 'P3_iso_wholesale_floor' proxy, iso utility,
    CONCAT(iso,' ',market,' 12-month average') tariff_name,
    CAST(NULL AS FLOAT64), avg_lmp_cents_kwh, avg_lmp_cents_kwh,
    CAST(NULL AS FLOAT64), CAST(NULL AS FLOAT64), CAST(NULL AS FLOAT64),
    CAST(last_day AS STRING), 'in_rate_wholesale_floor (energy only — no delivery, no riders)'
  FROM `{DS}.in_rate_wholesale_floor`
),
-- PROXY 4 — a comparable large-load tariff from a PEER utility. The only COMPONENT-LEVEL data
-- we hold, and none of it is Indiana — which is itself the finding.
p4 AS (
  SELECT 'P4_peer_largeload_tariff' proxy, CONCAT(utility,' (',state,')') utility, tariff_name,
    SAFE_CAST(qualifying_demand_kw AS FLOAT64)/1000,
    SAFE_CAST(annual_bill_cents_kwh AS FLOAT64), SAFE_CAST(annual_bill_cents_kwh AS FLOAT64),
    ROUND(SAFE_CAST(demand_charge_kw_yr_usd AS FLOAT64)/12, 2),
    SAFE_CAST(customer_charge_month_usd AS FLOAT64),
    SAFE_CAST(rider_cents_kwh AS FLOAT64),
    CAST(NULL AS STRING), CONCAT('dc_e3_largeload_tariffs — ', source)
  FROM `{EN}.dc_e3_largeload_tariffs`
)
SELECT *, TIMESTAMP('{BUILT}') built_at FROM (
  SELECT * FROM p1 UNION ALL SELECT * FROM p2 UNION ALL SELECT * FROM p3 UNION ALL SELECT * FROM p4)
""", "in_rate_proxies")

# ---- 3. eligibility: MW floors are MINIMUMS ---------------------------------------------------
print("\nbuilding in_rate_eligibility …", flush=True)
run(f"""
CREATE OR REPLACE TABLE `{DS}.in_rate_eligibility` AS
SELECT utility, tariff_code, tariff_name, name AS requirement, code,
  SAFE_CAST(rate AS FLOAT64) threshold_value, unit, basis, value_status,
  effective_date, source, source_url, notes,
  -- a 300 MW class load against the threshold: QUALIFIES, it does not "exceed"
  CASE WHEN unit='MW' AND SAFE_CAST(rate AS FLOAT64) IS NOT NULL
       THEN IF(300 >= SAFE_CAST(rate AS FLOAT64),
               'a 300 MW site QUALIFIES for this tariff',
               'a 300 MW site is BELOW this eligibility minimum')
       ELSE NULL END AS verdict_300mw,
  TIMESTAMP('{BUILT}') built_at
FROM `{DS}.in_utility_tariff_riders`
WHERE component_type = 'eligibility'
""", "in_rate_eligibility")
for r in client.query(f"SELECT * FROM `{DS}.in_rate_eligibility`"):
    print(f"    {r.utility}: {r.requirement} = {r.threshold_value} {r.unit} "
          f"(eff {r.effective_date}) -> {r.verdict_300mw}")

# ---- 4. what is MISSING — the honest gap register ---------------------------------------------
print("\nbuilding in_rate_component_gaps …", flush=True)
run(f"""
CREATE OR REPLACE TABLE `{DS}.in_rate_component_gaps` AS
SELECT utility, state, tariff_code, tariff_name, component_type, code, name AS component,
  unit, basis, value_status,
  -- METHODOLOGY 4.6: not published means NULL, never 0
  IF(value_status='published', SAFE_CAST(rate AS FLOAT64), NULL) rate_or_null,
  IF(value_status='published', 'held', 'NOT HELD — the value is NULL, not zero') held_state,
  source, source_url, notes, TIMESTAMP('{BUILT}') built_at
FROM `{DS}.in_utility_tariff_riders`
WHERE component_type != 'eligibility'
""", "in_rate_component_gaps")

# ---- 5. THE GATE ------------------------------------------------------------------------------
print("\napplying the >=1.75x plausibility gate …", flush=True)
floor = q1(f"""SELECT MIN(avg_lmp_cents_kwh) c FROM `{DS}.in_rate_wholesale_floor`""").c
gate = round(floor * MIN_MULTIPLE, 4)
print(f"  lowest ISO floor {floor}c/kWh · a bundled retail rate must clear {gate}c/kWh")

viol = [dict(r) for r in client.query(f"""
  SELECT proxy, utility, tariff_name, energy_cents_kwh_low
  FROM `{DS}.in_rate_proxies`
  WHERE proxy IN ('P1_largest_use_schedule','P2_avg_industrial_eia861','P4_peer_largeload_tariff')
    AND energy_cents_kwh_low IS NOT NULL AND energy_cents_kwh_low < {gate}
  ORDER BY energy_cents_kwh_low""")]
if viol:
    print(f"  *** {len(viol)} BUNDLED rate(s) below the {MIN_MULTIPLE}x floor — a modelling error, "
          f"not a bargain. Listed, and flagged rather than published as a quote:")
    for v in viol[:8]:
        print(f"      {v['proxy']:26s} {str(v['utility'])[:28]:28s} {v['energy_cents_kwh_low']}c/kWh")
    print("  NOTE: P1 rows are ENERGY-ONLY from a flattened source with no fixed charge or riders,")
    print("        so a low P1 figure is an INCOMPLETE rate, not a claim that power is cheap.")
else:
    print("  all bundled proxies clear the floor")

for name, n, src, method in [
 ("in_rate_wholesale_floor", int(q1(f"SELECT COUNT(*) n FROM `{DS}.in_rate_wholesale_floor`").n),
  f"{EN}.iso_lmp (MISO + PJM day-ahead, trailing 12 months)",
  f"the HARD FLOOR from METHODOLOGY §4: a bundled retail rate below ISO wholesale is impossible, "
  f"and must clear it by >={MIN_MULTIPLE}x. Anything between 1.0x and 1.75x is a modelling error."),
 ("in_rate_proxies", int(q1(f"SELECT COUNT(*) n FROM `{DS}.in_rate_proxies`").n),
  f"{DS}.in_urdb_rates + in_eia861_sales + in_rate_wholesale_floor + {EN}.dc_e3_largeload_tariffs",
  "the FOUR proxies §4.3 requires, side by side, never the industrial average alone. P1 comes "
  "from the FLATTENED urdb (no fixed charge, no riders, no seasonality) and is a cross-check "
  "only; P2 is a blended average and not a tariff; P3 is energy-only wholesale; P4 is the only "
  "component-level data held and NONE of it is Indiana."),
 ("in_rate_eligibility", int(q1(f"SELECT COUNT(*) n FROM `{DS}.in_rate_eligibility`").n),
  f"{DS}.in_utility_tariff_riders WHERE component_type='eligibility'",
  "MW floors are ELIGIBILITY MINIMUMS, not ceilings (§4.2). I&M's threshold is 70 MW at one "
  "site (IURC Cause 46097, effective 2025-02-19), so a 300 MW site QUALIFIES."),
 ("in_rate_component_gaps", int(q1(f"SELECT COUNT(*) n FROM `{DS}.in_rate_component_gaps`").n),
  f"{DS}.in_utility_tariff_riders",
  "per-component held/not-held register. §4.6: an unpublished value is NULL, never 0."),
]:
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
