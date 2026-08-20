"""G72/G80 - wire EIGHT county-grain objects that reached no surface at all.

    python scripts/build_county_context_extras.py

Every one of these was already clipped into `indiana_app`, already registered, and rendered
NOWHERE. They are collapsed into ONE county-keyed table because eight separate merges into
`county_context.json` is eight places for a key to go wrong.

WHAT GOES IN, AND WHY A SITER CARES (the G21 veto - a layer with no "so what" is not built):

  in_water_use (92)              USGS county water use, 2015. ⭐ THE MOST IMPORTANT ONE. An
                                 evaporative-cooled campus asks for millions of gallons a day.
                                 The county's ENTIRE public supply withdrawal is the yardstick:
                                 asking for 5 MGD in a county whose public system withdraws 2.2
                                 MGD is not a rate negotiation, it is a new source. Also carries
                                 the ground-vs-surface split, which decides WHICH permit.
  in_qcew_county_labor (92)      BLS employment, establishments, average weekly wage, 2024.
                                 Construction wage sets the build cost; total employment says
                                 whether 1,500 trades can be hired locally or must be imported.
  in_acs_county (92)             population, median household income, civilian labour force.
  in_fema_nri_counties (92)      FEMA National Risk Index - composite risk, expected annual loss
                                 in dollars, and COMMUNITY RESILIENCE. The insurance input that
                                 pairs with in_severe_weather_county's event history.
  in_solar_potential (92)        NREL GHI kWh/m2/day. Decides whether on-site solar is worth
                                 acres at all - and Indiana's spread is narrow, which is itself
                                 the finding.
  in_usa_structures_county (92)  building count and total footprint - the denominator that says
                                 how built-up a county is.
  in_cbp_county_industry (234)   ⭐ NAICS 518210 "Data processing, hosting" - WHERE THE INDUSTRY
                                 ALREADY IS. 15 counties have any at all. A county with an
                                 existing cluster has the substation, the fibre and the permit
                                 precedent; one with none is a first mover's problem.
  in_workforce_ipeds_* (4,942)   CS and engineering degrees awarded, by institution, mapped to
                                 the county that institution sits in. Operations staffing.

⛔ THREE THINGS THAT ARE HELD-BUT-EMPTY AND MUST RENDER AS THEMSELVES (G51), NOT AS ZERO:

  1. `in_qcew_county_labor.construction_employment` is NULL on ALL 92 ROWS - the column exists
     and the publisher's suppression rules emptied it. `construction_breakout_held` carries
     FALSE so a surface says "not published at county grain" rather than printing a zero and
     inviting a reader to conclude the county has no builders.
  2. `in_usa_structures_county.avg_height_m` is NULL on all 92. Dropped rather than carried.
  3. IPEDS reaches only 34 of 92 counties, because that is where the institutions are. A county
     with no row has NO CAMPUS, which is a real finding; a county whose campus awards zero CS
     degrees is a different one. Both are distinguishable in the output.

⚠ VINTAGES DIFFER BY FIVE YEARS AND THE SURFACE MUST SAY SO. Water use is 2015 (USGS publishes
every five years; 2020 is the next release). QCEW is 2024, ACS 2023. Each vintage travels with
its figure rather than being asserted once in a footnote.

⚠ FEMA's key is `stcofips` (5 digits). `countyfips` on the same table is the 3-DIGIT county part
and joining on it silently matches nothing - checked, not assumed.

WRITES `indiana_app.in_county_context_extras`. Reads indiana_app only.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_county_context_extras"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH base AS (
  SELECT DISTINCT county_fips, county_name
  FROM `{DS}.in_county_rollup`
),
labour AS (
  SELECT geoid AS county_fips, estabs, employment, avg_weekly_wage, avg_annual_pay,
         year AS qcew_year,
         -- ⛔ 0 of 92 rows carry this. FALSE means "the publisher did not break it out",
         --    which is NOT "this county has no construction industry".
         COUNTIF(construction_employment IS NOT NULL) OVER () > 0 AS construction_breakout_held
  FROM `{DS}.in_qcew_county_labor`
),
demog AS (
  SELECT geoid AS county_fips,
         SAFE_CAST(population AS INT64)          AS population,
         SAFE_CAST(median_hh_income AS INT64)    AS median_hh_income,
         SAFE_CAST(civilian_labor_force AS INT64) AS civilian_labor_force,
         year AS acs_year
  FROM `{DS}.in_acs_county`
),
risk AS (
  -- ⚠ stcofips is the 5-digit key. countyfips is 3 digits and joins to nothing.
  SELECT stcofips AS county_fips,
         risk_ratng AS nri_risk_rating,
         ROUND(SAFE_CAST(risk_score AS FLOAT64), 1) AS nri_risk_score,
         ROUND(SAFE_CAST(eal_valt AS FLOAT64) / 1e6, 2) AS nri_expected_annual_loss_musd,
         resl_ratng AS nri_resilience_rating,
         ROUND(SAFE_CAST(resl_score AS FLOAT64), 1) AS nri_resilience_score
  FROM `{DS}.in_fema_nri_counties`
),
solar AS (
  SELECT GEOID AS county_fips,
         ROUND(ghi_kwh_m2_day_mean, 2) AS ghi_kwh_m2_day
  FROM `{DS}.in_solar_potential`
),
water AS (
  SELECT fips AS county_fips,
         SAFE_CAST(ps_wtotl AS FLOAT64) AS public_supply_mgd,
         SAFE_CAST(ps_wgwto AS FLOAT64) AS public_supply_groundwater_mgd,
         SAFE_CAST(ps_wswto AS FLOAT64) AS public_supply_surface_mgd,
         SAFE_CAST(in_wtotl AS FLOAT64) AS industrial_selfsupplied_mgd,
         SAFE_CAST(pt_wtotl AS FLOAT64) AS thermoelectric_mgd,
         SAFE_CAST(to_wtotl AS FLOAT64) AS all_uses_mgd,
         year AS water_use_year
  FROM `{DS}.in_water_use`
),
built AS (
  SELECT geoid AS county_fips, bldg_count, ROUND(total_sqft / 1e6, 1) AS building_msqft
  FROM `{DS}.in_usa_structures_county`
),
dcind AS (
  SELECT geoid AS county_fips,
         SAFE_CAST(establishments AS INT64) AS dc_industry_establishments,
         SAFE_CAST(employment AS INT64)     AS dc_industry_employment
  FROM `{DS}.in_cbp_county_industry` WHERE naics = '518210'
),
utilind AS (
  SELECT geoid AS county_fips,
         SAFE_CAST(employment AS INT64) AS utilities_employment
  FROM `{DS}.in_cbp_county_industry` WHERE naics = '22'
),
telco AS (
  SELECT geoid AS county_fips,
         SAFE_CAST(employment AS INT64) AS telecom_employment
  FROM `{DS}.in_cbp_county_industry` WHERE naics = '517'
),
-- IPEDS keys institutions to a county NAME, not a fips. Normalise both sides the same way.
campus AS (
  SELECT UPPER(TRIM(REGEXP_REPLACE(d.county_name, r'(?i)\\s+county$', ''))) AS cname,
         COUNT(DISTINCT d.unitid) AS institutions,
         SUM(a.awards) AS cs_eng_awards
  FROM `{DS}.in_workforce_ipeds_directory` d
  LEFT JOIN (
      SELECT unitid, SUM(SAFE_CAST(awards AS INT64)) AS awards
      FROM `{DS}.in_workforce_ipeds_cs_eng` GROUP BY unitid) a USING (unitid)
  WHERE d.county_name IS NOT NULL
  GROUP BY cname
)
SELECT
  b.county_fips, b.county_name,
  l.* EXCEPT (county_fips),
  d.* EXCEPT (county_fips),
  r.* EXCEPT (county_fips),
  s.* EXCEPT (county_fips),
  w.* EXCEPT (county_fips),
  bl.* EXCEPT (county_fips),
  di.dc_industry_establishments, di.dc_industry_employment,
  ui.utilities_employment, tc.telecom_employment,
  c.institutions AS campus_institutions,
  c.cs_eng_awards AS campus_cs_eng_awards,
  CURRENT_TIMESTAMP() AS built_at
FROM base b
LEFT JOIN labour  l ON l.county_fips  = b.county_fips
LEFT JOIN demog   d ON d.county_fips  = b.county_fips
LEFT JOIN risk    r ON r.county_fips  = b.county_fips
LEFT JOIN solar   s ON s.county_fips  = b.county_fips
LEFT JOIN water   w ON w.county_fips  = b.county_fips
LEFT JOIN built  bl ON bl.county_fips = b.county_fips
LEFT JOIN dcind  di ON di.county_fips = b.county_fips
LEFT JOIN utilind ui ON ui.county_fips = b.county_fips
LEFT JOIN telco  tc ON tc.county_fips = b.county_fips
LEFT JOIN campus  c ON c.cname =
      UPPER(TRIM(REGEXP_REPLACE(b.county_name, r'(?i)\\s+county$', '')))
"""

print("building in_county_context_extras ...")
job = client.query(SQL)
job.result()
gb = round((job.total_bytes_processed or 0) / 1e9, 3)

s = list(client.query(f"""
  SELECT COUNT(*) n,
         COUNTIF(employment IS NOT NULL) lab,
         COUNTIF(population IS NOT NULL) acs,
         COUNTIF(nri_risk_rating IS NOT NULL) nri,
         COUNTIF(ghi_kwh_m2_day IS NOT NULL) sol,
         COUNTIF(public_supply_mgd IS NOT NULL) wat,
         COUNTIF(bldg_count IS NOT NULL) blt,
         COUNTIF(dc_industry_employment IS NOT NULL) dci,
         COUNTIF(campus_institutions IS NOT NULL) cmp,
         LOGICAL_OR(construction_breakout_held) con
  FROM `{OUT}`"""))[0]
print(f"  {s.n} counties, {gb} GB scanned")
print(f"  labour {s.lab}/92 · acs {s.acs}/92 · FEMA NRI {s.nri}/92 · solar {s.sol}/92 · "
      f"water {s.wat}/92")
print(f"  structures {s.blt}/92 · DC industry {s.dci}/92 (real: most counties have none) · "
      f"campus {s.cmp}/92")
print(f"  construction breakout published by BLS: {s.con}  <- FALSE is the honest state, not 0")

# ⛔ FAN-OUT GUARD. Nine LEFT JOINs on one base; if any right side is not unique per county the
#    row count silently multiplies. 92 in, 92 out or this build is wrong (trap 7).
assert s.n == 92, f"FAN-OUT: expected 92 counties, got {s.n}"

print("\n  the water figure that does the work (lowest public supply, biggest ask risk):")
for r in client.query(f"""SELECT county_name, public_supply_mgd, public_supply_groundwater_mgd,
                                 public_supply_surface_mgd, all_uses_mgd
                          FROM `{OUT}` WHERE public_supply_mgd IS NOT NULL
                          ORDER BY public_supply_mgd ASC LIMIT 5"""):
    print(f"    {r.county_name:16s} public supply {r.public_supply_mgd:>7.2f} MGD  "
          f"(gw {r.public_supply_groundwater_mgd:>6.2f} / sw {r.public_supply_surface_mgd:>6.2f})  "
          f"all uses {r.all_uses_mgd:>8.2f}")

print("\n  where the data-centre industry already employs people:")
for r in client.query(f"""SELECT county_name, dc_industry_establishments, dc_industry_employment
                          FROM `{OUT}` WHERE dc_industry_employment IS NOT NULL
                          ORDER BY dc_industry_employment DESC LIMIT 6"""):
    print(f"    {r.county_name:16s} {r.dc_industry_establishments:>3} establishments, "
          f"{r.dc_industry_employment:>5} employed")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_county_context_extras',
 'indiana_app.in_water_use (USGS 2015), in_qcew_county_labor (BLS 2024), in_acs_county (ACS 2023), '
 'in_fema_nri_counties (FEMA National Risk Index), in_solar_potential (NREL GHI), '
 'in_usa_structures_county, in_cbp_county_industry (Census CBP), '
 'in_workforce_ipeds_directory + in_workforce_ipeds_cs_eng',
 'eight county-grain objects that reached NO surface, merged on the 5-digit county FIPS from '
 'in_county_rollup. FEMA joins on stcofips (5 digits) NOT countyfips (3 digits). IPEDS joins on '
 'a normalised county NAME because its own fips column is the state. Row count asserted at 92 '
 'to catch LEFT JOIN fan-out. construction_breakout_held is FALSE because BLS suppresses the '
 'construction split on all 92 rows - carried as a three-state flag, never as zero. '
 'RE-SCRAPE COMMAND: python scripts/build_county_context_extras.py',
 {s.n}, {gb}, CURRENT_TIMESTAMP(),
 'G72/G80. Vintages differ by up to nine years (water 2015, ACS 2023, QCEW 2024) and each one '
 'travels with its figure. IPEDS reaches 34 of 92 counties because that is where the campuses '
 'are - an absent row means no institution, which is a finding, not a gap.'
)""").result()
print("\n  _registry row written")
print("COUNTY CONTEXT EXTRAS COMPLETE")
