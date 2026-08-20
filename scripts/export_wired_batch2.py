"""G72 / G80 batch 2 - take the remaining worklist to zero.

    python scripts/export_wired_batch2.py

Writes:
  data/wired2.json.gz        the tabular remainder
  data/wired2.geojson.gz     the three that carry real coordinates
  data/zip_index.json.gz     ZIP -> point, so the map search bar accepts a ZIP (extends G121)

⭐ THE TWO THAT MATTER MOST WERE THE SMALLEST, WHICH IS THE LESSON OF THIS WHOLE ROW.
`in_econ_gjf_megadeals` has 26 rows. One of them is **Amazon Data Services, Indiana, 2024,
$8,282,300,000** - the largest subsidy package in the state's history, awarded to a data centre,
and it reached no surface. `in_dc_eei_tariffs` has 5 rows and every one is an INDIANA data-centre
deal with its utility and its terms: AWS at New Carlisle ($11bn), Google at Fort Wayne ($2bn),
Google/AES at Morgan Township (390 MW, with $770m of ratepayer savings agreed over 15 years),
Meta at Jeffersonville ($800m), Microsoft at Granger. For a developer asking "what did the last
five people to do this actually get", those 31 rows are worth more than several 40,000-row tables.
Row count was never the right way to triage this list.

⛔ AND ONE MORE `in_*` TABLE WITH NO INDIANA IN IT. The Chapter 7 trustee final-report table
holds 33 rows across MO, CA, MA, IL, OK, OH, MT, VA and SD - and **zero Indiana rows**. That is
the same defect G72 found in the tribal-land clip (14 rows, none in Indiana): an unwired table is
an UNAUDITED table, and an `in_` prefix is not a clip. It is reclassified in
`audit_unwired_classification.py` rather than wired.
⚠ Its name is deliberately NOT written here. The wiring census counts an object as reaching a
surface if any export or page NAMES it, so putting the identifier in this comment would mark it
wired - which is precisely the fake signal the census was already gamed by once (FEATURE_HOME).

⚠ `in_echo_cwa_facilities` holds 13,205 Indiana Clean Water Act dischargers and carries
`faclong` with NO LATITUDE COLUMN AT ALL - the platform-side defect G27 already recorded. A
longitude alone cannot be mapped, so this ships at COUNTY grain from `facstdcountyname` and the
surface says why. ⭐ It is worth having anyway: a site with an existing NPDES discharge permit is
a place where a cooling-water discharge has already been permitted once.

⛔ EXPORTS MAY NOT READ `energy`. Everything here reads indiana_app.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = (r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California"
        r"\ca-capacity-deploy\indiana-application-decennial")
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")


def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    if isinstance(o, decimal.Decimal):
        return float(o)
    return str(o)


def gzwrite(name, obj):
    p = os.path.join(REPO, "data", name)
    with gzip.open(p, "wt", encoding="utf-8", compresslevel=6) as f:
        json.dump(obj, f, separators=(",", ":"), default=jd)
    return os.path.getsize(p)


def rows(sql):
    return [{k: v for k, v in dict(r).items() if v is not None} for r in client.query(sql)]


# ---- tabular ---------------------------------------------------------------------------------
w2 = {
    "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),

    # ⭐ WHAT THE LAST FIVE PEOPLE TO DO THIS ACTUALLY GOT.
    "dc_deals": rows(f"""
        SELECT eei_member_company AS utility, customer_type, location, key_details
        FROM `{DS}.in_dc_eei_tariffs` ORDER BY eei_member_company"""),
    # ⚠ the dollar columns are STRINGS with $ and commas. Strip before casting or every one is NULL.
    "megadeals": rows(f"""
        SELECT company, parent, year,
               SAFE_CAST(REGEXP_REPLACE(original_subsidy_value, r'[^0-9.]', '') AS FLOAT64)
                 AS subsidy_usd,
               SAFE_CAST(REGEXP_REPLACE(subsidy_value_in_2023_dollars, r'[^0-9.]', '') AS FLOAT64)
                 AS subsidy_2023_usd
        FROM `{DS}.in_econ_gjf_megadeals`
        ORDER BY subsidy_2023_usd DESC"""),

    # EIA monthly generation by fuel, 2022-01 to 2026-04. The state's own supply mix and how fast
    # it is moving - the denominator for "can Indiana serve another 1,000 MW of load".
    "generation_mix": rows(f"""
        SELECT fuelTypeDescription AS fuel,
               ROUND(SUM(SAFE_CAST(generation AS FLOAT64)), 1) AS gwh,
               MAX(period) AS latest_period
        FROM `{DS}.in_elec_power_operational`
        WHERE sectorDescription = 'All Sectors'
          AND period >= FORMAT_DATE('%Y-%m', DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH))
        GROUP BY 1 HAVING gwh > 0 ORDER BY gwh DESC"""),
    "generation_trend": rows(f"""
        SELECT period, ROUND(SUM(SAFE_CAST(generation AS FLOAT64)), 1) AS gwh
        FROM `{DS}.in_elec_power_operational`
        WHERE sectorDescription = 'All Sectors' AND fuelTypeDescription = 'all fuels'
        GROUP BY 1 ORDER BY period"""),

    # ⚠ MOVED HERE FROM export_wired_layers.py, 2026-08-20. market.html reads wired2 and
    #   this key was being written into wired.json.gz, so the panel would have rendered
    #   empty forever. audit_frontend.py caught it: it checks every key a page reads
    #   against the keys the export actually writes, which is exactly this class of bug.
    # ⭐ THE PRICE CHECK. in_eia861_sales_ult_cust held every Indiana utility's INDUSTRIAL revenue
    #    and MWh and reached no surface. revenue / sales is the implied industrial rate actually
    #    BILLED last year - a yardstick against the tariff engine's modelled figure, from a
    #    different source entirely.
    #    ⚠ It is an AVERAGE across every industrial customer, not a large-load rate, and it is
    #    NOT a substitute for the tariff: it carries no demand/energy split and no rider stack.
    "utility_implied_industrial": rows(f"""
        SELECT utility_name, data_year, ownership, ba_code,
               ROUND(ind_sales_mwh) AS ind_mwh, ROUND(ind_customers) AS ind_customers,
               ROUND(100 * SAFE_DIVIDE(ind_rev_kusd, ind_sales_mwh), 2) AS implied_cents_kwh,
               ROUND(100 * SAFE_DIVIDE(tot_rev_kusd, tot_sales_mwh), 2) AS all_class_cents_kwh
        FROM `{DS}.in_eia861_sales_ult_cust`
        WHERE ind_sales_mwh > 0 ORDER BY ind_sales_mwh DESC"""),

    # ⭐ G100 - "see if we are missing any data inputs for how much gas is free in a given day".
    #    The answer is measured rather than guessed, and it has TWO halves. 13 interstate
    #    operators cross Indiana. We hold an operationally-available-capacity board for 9 of them.
    #    But only TWO of those boards carry a state or county column, so only two can be attached
    #    to an Indiana point at all - the rest post the operator's whole system, and Texas Gas
    #    (which has more Indiana segments than anyone) posts 23,220 rows we cannot place.
    # ⛔ SO THE BIGGER GAP IS ATTRIBUTION, NOT ACQUISITION. Scraping four more boards would add
    #    four more unplaceable boards. What is missing is a point-level location on the boards we
    #    already have, which is a different ask entirely.
    "gas_coverage": rows(f"""
        WITH ops AS (
          SELECT operator, COUNT(*) AS segments
          FROM `{DS}.in_gas_pipelines` WHERE operator IS NOT NULL GROUP BY 1),
        boards AS (
          SELECT 'Panhandle Eastern Pipe Line Co.' AS operator, 'in_gas_capacity_panhandle_eastern' AS board, TRUE AS placeable UNION ALL
          SELECT 'Trunkline Gas Co.',              'in_gas_capacity_trunkline',       TRUE  UNION ALL
          SELECT 'ANR Pipeline Co.',               'in_gas_capacity_anr',             FALSE UNION ALL
          SELECT 'Crossroads Pipeline Co.',        'in_gas_capacity_crossroads',      FALSE UNION ALL
          SELECT 'Midwestern Gas Transmission Co.','in_gas_capacity_midwestern',      FALSE UNION ALL
          SELECT 'Natural Gas PL Co. of Am',       'in_gas_capacity_ngpl',            FALSE UNION ALL
          SELECT 'Northern Border PL Co.',         'in_gas_capacity_northern_border', FALSE UNION ALL
          SELECT 'Texas Gas Transmission Co.',     'in_gas_capacity_texas_gas',       FALSE UNION ALL
          SELECT 'Vector Pipeline Co.',            'in_gas_capacity_vector',          FALSE)
        SELECT o.operator, o.segments, b.board, IFNULL(b.placeable, FALSE) AS placeable,
               b.board IS NOT NULL AS have_board
        FROM ops o LEFT JOIN boards b USING (operator)
        ORDER BY o.segments DESC"""),

    # weekly state drought. ⚠ a STATE series, not county - it must not render on a parcel.
    "drought": rows(f"""
        SELECT SUBSTR(validstart, 1, 10) AS week, none AS pct_none, d0, d1, d2, d3, d4
        FROM `{DS}.in_drought_by_state`
        WHERE stateabbreviation = 'IN' ORDER BY validstart DESC LIMIT 60"""),

    # WRI Aqueduct basins touching Indiana. name_1 is the STATE, not the basin.
    "aqueduct": rows(f"""
        SELECT aq30_id AS basin, bws_label AS baseline_water_stress,
               bwd_label AS baseline_water_depletion, iav_label AS interannual_variability,
               drr_label AS drought_risk, sev_label AS seasonal_variability
        FROM `{DS}.in_water_aqueduct` WHERE name_1 = 'Indiana' ORDER BY aq30_id"""),

    # Clean Water Act dischargers, COUNTY grain - see the header for why not mapped.
    # ⚠ `cwpstate = 'IN'` DOES NOT MEAN THE COUNTY IS IN INDIANA. Measured: rows flagged IN carry
    #   KOOCHICHING COUNTY (Minnesota), COOK COUNTY (Illinois) and LACKAWANNA COUNTY
    #   (Pennsylvania), which is why a naive GROUP BY returned 95 counties for a 92-county state.
    #   Joined against the real county list; the residue is counted, not silently absorbed.
    "cwa_by_county": rows(f"""
        -- ⚠ BOTH SIDES CARRY THE WORD "COUNTY" and the first version of this join stripped it
        --   from one side only: in_county_rollup says 'Allen County', ECHO says 'ALLEN COUNTY'.
        --   Result was 13,205 of 13,205 unmatched, which the cwa_note check caught immediately.
        --   A join that matches nothing is a claim about the instrument, not the data.
        WITH cty AS (SELECT DISTINCT UPPER(REGEXP_REPLACE(county_name, r'(?i)\\s+county$', '')) AS nm
                     FROM `{DS}.in_county_rollup`)
        SELECT e.facstdcountyname AS county, COUNT(*) AS facilities,
               COUNTIF(SAFE_CAST(e.cwptotaldesignflownmbr AS FLOAT64) > 0) AS with_design_flow,
               ROUND(SUM(SAFE_CAST(e.cwptotaldesignflownmbr AS FLOAT64)), 2) AS design_flow_mgd
        FROM `{DS}.in_echo_cwa_facilities` e
        JOIN cty ON cty.nm = UPPER(REGEXP_REPLACE(e.facstdcountyname, r'(?i)\\s+COUNTY$', ''))
        WHERE e.cwpstate = 'IN'
        GROUP BY 1 ORDER BY facilities DESC"""),
    "cwa_note": rows(f"""
        -- ⚠ BOTH SIDES CARRY THE WORD "COUNTY" and the first version of this join stripped it
        --   from one side only: in_county_rollup says 'Allen County', ECHO says 'ALLEN COUNTY'.
        --   Result was 13,205 of 13,205 unmatched, which the cwa_note check caught immediately.
        --   A join that matches nothing is a claim about the instrument, not the data.
        WITH cty AS (SELECT DISTINCT UPPER(REGEXP_REPLACE(county_name, r'(?i)\\s+county$', '')) AS nm
                     FROM `{DS}.in_county_rollup`)
        SELECT COUNT(*) AS rows_flagged_indiana,
               COUNTIF(cty.nm IS NULL) AS rows_whose_county_is_not_in_indiana
        FROM `{DS}.in_echo_cwa_facilities` e
        LEFT JOIN cty ON cty.nm = UPPER(REGEXP_REPLACE(e.facstdcountyname, r'(?i)\\s+COUNTY$', ''))
        WHERE e.cwpstate = 'IN'"""),

    # ---- owner-motivation corpora that si.html summarised but never named ----
    "dissolution": rows(f"""
        SELECT status_family, COUNT(*) AS entities,
               COUNTIF(address_line IS NOT NULL) AS with_address,
               CAST(MAX(observed_date) AS STRING) AS latest
        FROM `{DS}.in_si_d11_entity_dissolution` GROUP BY 1 ORDER BY entities DESC"""),
    "ucc_lapse": rows(f"""
        SELECT debtor_name, city, CAST(lapse_date AS STRING) AS lapse_date,
               CAST(filing_date AS STRING) AS filing_date, keying
        FROM `{DS}.in_si_d27_ucc_lapse_v2` ORDER BY lapse_date DESC LIMIT 60"""),
    "rail_abandonment": rows(f"""
        SELECT filing_type, COUNT(*) AS filings,
               MIN(SUBSTR(filed_date, 1, 10)) AS first_filed,
               MAX(SUBSTR(filed_date, 1, 10)) AS last_filed
        FROM `{DS}.in_si_d25_stb_abandonment_state`
        WHERE state = 'IN' GROUP BY 1 ORDER BY filings DESC"""),

    # ⭐ the NCES table is NOT a surplus register - it is the school DIRECTORY. The signal in it is
    #   the handful of CLOSED schools: a closed school is a built site on land, with power and a
    #   public-body owner. The name of the table promised far more than the table holds.
    "closed_schools": rows(f"""
        SELECT sch_name, lea_name, lcity AS city, sch_type_text AS school_type,
               updated_status_text AS status
        FROM `{DS}.in_gov_surplus_nces`
        WHERE updated_status_text = 'Closed' ORDER BY lcity"""),
    "nces_status": rows(f"""
        SELECT updated_status_text AS status, COUNT(*) AS schools
        FROM `{DS}.in_gov_surplus_nces` GROUP BY 1 ORDER BY schools DESC"""),

    "gsa_auctions": rows(f"""
        SELECT name, city, property_price, status, bidding_end, closing_status_name
        FROM `{DS}.in_gov_auction_gsa` ORDER BY bidding_end DESC"""),
}
size = gzwrite("wired2.json.gz", w2)
print(f"  data/wired2.json.gz  {size:,} bytes")
for k, v in w2.items():
    if isinstance(v, list):
        print(f"      {k:22s} {len(v):>5}")

# ---- the three with real coordinates ----------------------------------------------------------
feats = []
for r in client.query(f"""
  SELECT NAME AS name, CITY AS city, NMCNTY AS county, LOCALE AS locale,
         SAFE_CAST(LAT AS FLOAT64) AS la, SAFE_CAST(LON AS FLOAT64) AS lo
  FROM `{DS}.in_candidate_sites_colleges` WHERE SAFE_CAST(LAT AS FLOAT64) IS NOT NULL"""):
    d = dict(r); la, lo = d.pop("la"), d.pop("lo"); d["layer"] = "college"
    feats.append({"type": "Feature", "properties": d,
                  "geometry": {"type": "Point", "coordinates": [round(lo, 6), round(la, 6)]}})
n_col = len(feats)
for r in client.query(f"""
  SELECT establishment_name AS name, city, county, TRIM(size) AS size, activities,
         SAFE_CAST(latitude AS FLOAT64) AS la, SAFE_CAST(longitude AS FLOAT64) AS lo
  FROM `{DS}.in_fsis_establishments` WHERE SAFE_CAST(latitude AS FLOAT64) IS NOT NULL"""):
    d = dict(r); la, lo = d.pop("la"), d.pop("lo"); d["layer"] = "foodplant"
    feats.append({"type": "Feature", "properties": d,
                  "geometry": {"type": "Point", "coordinates": [round(lo, 6), round(la, 6)]}})
size = gzwrite("wired2.geojson.gz", {"type": "FeatureCollection", "features": feats})
print(f"  data/wired2.geojson.gz  {len(feats):,} features "
      f"({n_col} colleges + {len(feats) - n_col} food plants), {size:,} bytes")

# ---- ZIP index for the search bar (G121 extension) ---------------------------------------------
# ⛔ A POINT, NOT A POLYGON. 807 ZCTA polygons are ~4 MB and the search bar needs one thing: where
#    to fly to. The centroid of a ZCTA is not a place anybody lives, so the label says "ZIP <n>
#    (approximate centre)" rather than presenting it as an address.
zips = {}
for r in client.query(f"""
  SELECT ZCTA5CE20 AS zip, ROUND(ST_Y(ST_CENTROID(geom)), 5) AS la,
         ROUND(ST_X(ST_CENTROID(geom)), 5) AS lo
  FROM `{DS}.in_zctas` WHERE geom IS NOT NULL"""):
    zips[r.zip] = [r.la, r.lo]
size = gzwrite("zip_index.json.gz", {"note": "ZCTA centroid - an approximate centre, not an "
                                             "address", "zips": zips})
print(f"  data/zip_index.json.gz  {len(zips)} ZIPs, {size:,} bytes")
print("WIRED BATCH 2 COMPLETE")
