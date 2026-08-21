"""G130: WHERE FUTURE CAPACITY MAY APPEAR — every planned upgrade, placed as well as it honestly can be.

Operator, 2026-08-20f: *"I would like to place these upgrades or new developments on the map for
where future capacity may exist… we may NOT have a coordinate, but the documentation in the
filings often carry a regional location that we can use to estimate the locations… these upgrades
or new developments should NOT display the same as the current grid assets."*

================================================================================================
WHAT WE HELD BEFORE THIS, MEASURED
================================================================================================
  in_grid_plans_located     618 rows, 119 placed (19.3%)  ← the ONLY planned work on the map,
                                                            drawn as plain circles like real steel
  in_rtep_bus_join        1,229 endpoints over 907 PJM RTEP upgrades, 287 already carrying a
                                coordinate — ⛔ AND NOTHING RENDERED THEM. vw_pjm_rtep_upgrades_
                                located exists and holds 0 rows.
  in_txexp_miso_mtep_...    328 MISO MTEP projects with from_sub/to_sub, cost and expected ISD,
                                reaching the dossier only as a COUNT
  in_rto_expansion        2,034 rows, 0 placed
  in_miso_dpp2025_...       202 project costs, 0 placed

================================================================================================
⭐ THE THING THE MEASUREMENT FOUND: MOST "UNPLACEABLE" LOCATIONS ARE CORRIDORS, NOT FAILURES
================================================================================================
Reading the unmatched strings instead of counting them: `TWIN BRANCH - EAST ELKHART`,
`SORENSON - ILLINOIS ROAD`, `TANNERS CREEK - DESOTO - SORENSON`, `MADISON – CROSS STREET`,
`SORENSON/KEYSTONE`. Those are not failed station lookups. They are A-to-B LINE NAMES — the
upgrade is a rebuild of the corridor between two substations, and a corridor is not a point.
⚠ THE SEPARATOR VARIES: hyphen, EN DASH and slash all appear, and splitting on "-" alone misses
every en-dash row. That is the value-vocabulary trap in punctuation form.
⚠ And BigQuery's RE2 rejects \\uXXXX escapes outright, so the dashes are written literally.

================================================================================================
THE PLACEMENT TIERS, AND WHY EACH CARRIES AN UNCERTAINTY RADIUS
================================================================================================
Modelled on the operator's Illinois tool, read from its source. Its design decision worth copying
exactly: **the ring is keyed on HOW WELL WE KNOW THE LOCATION, never on project status.** A
project can be fully approved and still only be named by its town.

    verified_asset_match   NO RING  the filing names a substation we hold, corroborated by a bus
    substation_match       NO RING  the name resolves to exactly one substation we hold
    ⛔ THOSE TWO GET NO RADIUS AT ALL. Operator, 2026-08-20f: *"for the grid assets that we can
    actually place by coordinates or through a join with an existing asset, we do not need to
    apply a radius estimation."* Right, and it matters in both directions: a project joined to a
    substation IS at that substation, and drawing a ring around it would make a KNOWN position
    look guessed - the mirror of an estimate styling itself as published.

    corridor_midpoint      half     both ends of an A-to-B name resolve; the point is the midpoint
                           the span and the ring covers the corridor. The ENDPOINTS ship too, so
                                    the map can draw the line rather than a misleading dot
    corridor_one_end       3.0 mi   one end resolves; the work is somewhere off that station
    municipality_centroid  5.0 mi   only a town is named. ⛔ NOT the asset site
    county_centroid       20.0 mi   only a county is known
    unplaced               NULL     reported and never drawn. ⛔ An upgrade in the wrong place is
                                    worse than one with no place - it is a coordinate someone
                                    might plan around.

⛔ STATUS IS SEPARATE FROM PLACEMENT AND BOTH ARE PUBLISHED. `IS` / `M4 - Project in Service`
means the work is ALREADY BUILT — 9,163 of 15,443 PJM rows — and is NOT future capacity.
Cancelled and withdrawn work is carried with its own class so it can be excluded, because a
cancelled upgrade is the opposite of a promise.

RE-SCRAPE COMMAND: python scripts/build_planned_upgrades.py
⚠ IDEMPOTENT: replace_safe. CADENCE: quarterly — RTO planning cycles; the IURC grid-plan dockets
are event-driven.
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
OUT = f"{DS}.in_planned_upgrades"

client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS

WITH
-- ---------------------------------------------------------------------------------------------
-- GAZETTEERS. A substation name is only usable when it resolves to ONE place; a name shared by
-- three stations tells us the county, not the site.
-- ---------------------------------------------------------------------------------------------
sub AS (
  SELECT UPPER(TRIM(substation_name)) AS nm,
         COUNT(DISTINCT FORMAT('%.4f|%.4f', lat, lon)) AS pts,
         ANY_VALUE(lat) AS lat, ANY_VALUE(lon) AS lon,
         ANY_VALUE(county) AS county, ANY_VALUE(county_fips) AS county_fips
  FROM `{DS}.in_substations`
  WHERE geog IS NOT NULL AND substation_name IS NOT NULL AND TRIM(substation_name) != ''
  GROUP BY 1
),
sub1 AS (SELECT * FROM sub WHERE pts = 1),
town AS (
  SELECT UPPER(TRIM(city)) AS ct, AVG(lat) AS lat, AVG(lon) AS lon,
         ANY_VALUE(county) AS county, ANY_VALUE(county_fips) AS county_fips
  FROM `{DS}.in_substations`
  WHERE geog IS NOT NULL AND city IS NOT NULL AND TRIM(city) != ''
  GROUP BY 1
),
cty AS (
  SELECT LPAD(CAST(COUNTYFP AS STRING), 3, '0') AS county_fips,
         UPPER(TRIM(NAME)) AS county_name,
         ST_Y(ST_CENTROID(geom)) AS lat, ST_X(ST_CENTROID(geom)) AS lon,
         -- an honest radius for a county: the disc of equal area
         ROUND(SQRT(ST_AREA(geom) / ACOS(-1)) / 1609.344, 1) AS radius_mi
  FROM `{EN}.county_boundaries`
  WHERE STUSPS = 'IN'
),

-- =============================================================================================
-- SOURCE 1 - PJM RTEP
-- =============================================================================================
rtep_meta AS (
  SELECT CAST(upgrade_id AS STRING) AS pid,
         ANY_VALUE(status) AS status_raw,
         ANY_VALUE(cost_estimate) AS cost_raw,
         ANY_VALUE(projected_in_service_date) AS isd,
         ANY_VALUE(actual_in_service_date) AS aisd,
         ANY_VALUE(state) AS state,
         ANY_VALUE(transmission_owner) AS owner
  FROM `{DS}.in_pjm_rtep_upgrades`
  WHERE upgrade_id IS NOT NULL
  GROUP BY 1
),
rtep_det AS (
  SELECT CAST(upgrade_id AS STRING) AS pid,
         ANY_VALUE(description) AS descr,
         ANY_VALUE(driver) AS driver,
         ANY_VALUE(project_type) AS ptype,
         ANY_VALUE(location) AS loc_raw,
         ANY_VALUE(sub_region) AS sub_region
  FROM `{DS}.in_pjm_rtep_upgrade_details`
  GROUP BY 1
),
-- the bridge that already existed and never reached a surface
rtep_bridge AS (
  SELECT CAST(upgrade_id AS STRING) AS pid,
         ANY_VALUE(COALESCE(substation_lat, bus_lat)) AS lat,
         ANY_VALUE(COALESCE(substation_lon, bus_lon)) AS lon,
         ANY_VALUE(substation_name) AS anchor,
         ANY_VALUE(substation_county) AS county,
         ANY_VALUE(match_confidence) AS conf,
         COUNT(DISTINCT endpoint_name) AS n_endpoints
  FROM `{DS}.in_rtep_bus_join`
  WHERE COALESCE(substation_lat, bus_lat) IS NOT NULL
  GROUP BY 1
),
-- ⭐ split an A-to-B corridor name into its endpoints and resolve each one
rtep_parts AS (
  SELECT d.pid, TRIM(p) AS part, off
  FROM rtep_det d, UNNEST(REGEXP_EXTRACT_ALL(UPPER(d.loc_raw), r'[^-–—/,]+')) AS p WITH OFFSET off
  WHERE d.loc_raw IS NOT NULL AND TRIM(d.loc_raw) != ''
),
rtep_ends AS (
  SELECT p.pid,
         -- ⛔ MATCHED ENDPOINTS ONLY, AND THIS WAS A REAL BUG. The first version aggregated every
         -- part of the name, so `ends[OFFSET(0)]` could be an UNMATCHED fragment: 11 rows came
         -- out graded `corridor_midpoint` - both ends resolved - while carrying no coordinate at
         -- all, because the midpoint was averaged from two nulls. A grade that says "we know
         -- where this is" on a row with no position is the worst kind of wrong.
         ARRAY_AGG(IF(s.lat IS NULL, NULL,
                      STRUCT(s.lat AS lat, s.lon AS lon, p.part AS nm))
                   IGNORE NULLS ORDER BY p.off LIMIT 4) AS ends,
         COUNTIF(s.nm IS NOT NULL) AS n_sub,
         COUNTIF(s.nm IS NULL AND t.ct IS NOT NULL) AS n_town,
         ANY_VALUE(IF(s.nm IS NULL AND t.ct IS NOT NULL, t.lat, NULL)) AS town_lat,
         ANY_VALUE(IF(s.nm IS NULL AND t.ct IS NOT NULL, t.lon, NULL)) AS town_lon,
         ANY_VALUE(IF(s.nm IS NULL AND t.ct IS NOT NULL, t.county, NULL)) AS town_county
  FROM rtep_parts p
  LEFT JOIN sub1 s ON s.nm = p.part
  LEFT JOIN town t ON t.ct = p.part
  GROUP BY 1
),
rtep AS (
  SELECT
    'PJM RTEP' AS source,
    m.pid AS project_id,
    -- ⚠ THE LOCATION IS THE NAME, NOT THE DESCRIPTION. PJM's `description` is a work order -
    -- "Three 63 kA circuit breakers with associated..." - which is what the project DOES, not
    -- what a reader is looking for in a list. The station or corridor name is the identity, and
    -- it is what the map tip and the screener column need; the description rides along separately
    -- so nothing is lost.
    COALESCE(NULLIF(TRIM(d.loc_raw), ''), d.descr) AS title,
    d.driver, d.ptype AS project_type, d.loc_raw AS location_text, d.descr AS description,
    m.status_raw, m.isd AS in_service_date, m.aisd AS actual_in_service_date,
    -- ⛔ ALREADY IN MILLIONS. PJM publishes RTEP `cost_estimate` in $M - the raw values are
    -- '0.02', '0.1', '0.5', '1' - and dividing by 1e6 turned every one of them into zero, so the
    -- grid page reported "not published" for a column that is populated on all 15,443 rows.
    -- ⚠ MISO's `current_cost` in the branch below IS raw dollars (336506544), so the two feeds
    -- genuinely need different treatment. Two sources, two units, one column name: the
    -- value-vocabulary trap wearing a unit instead of a spelling.
    SAFE_CAST(m.cost_raw AS FLOAT64) AS cost_usd_m,
    m.owner, m.state,
    b.lat AS b_lat, b.lon AS b_lon, b.anchor AS b_anchor, b.county AS b_county, b.conf AS b_conf,
    e.ends, e.n_sub, e.n_town, e.town_lat, e.town_lon, e.town_county
  FROM rtep_meta m
  LEFT JOIN rtep_det d USING (pid)
  LEFT JOIN rtep_bridge b USING (pid)
  LEFT JOIN rtep_ends e USING (pid)
  WHERE UPPER(IFNULL(m.state, '')) = 'IN' OR b.pid IS NOT NULL OR e.pid IS NOT NULL
),
rtep_placed AS (
  SELECT source, project_id, title, driver, project_type, location_text, description,
         status_raw,
         CAST(in_service_date AS STRING) AS in_service_date,
         CAST(actual_in_service_date AS STRING) AS actual_in_service_date,
         cost_usd_m, owner,
         CASE
           WHEN b_lat IS NOT NULL THEN b_lat
           WHEN n_sub >= 2 THEN (ends[OFFSET(0)].lat + ends[OFFSET(1)].lat) / 2
           WHEN n_sub = 1 THEN (SELECT lat FROM UNNEST(ends) WHERE lat IS NOT NULL LIMIT 1)
           WHEN n_town >= 1 THEN town_lat
           ELSE NULL END AS lat,
         CASE
           WHEN b_lat IS NOT NULL THEN b_lon
           WHEN n_sub >= 2 THEN (ends[OFFSET(0)].lon + ends[OFFSET(1)].lon) / 2
           WHEN n_sub = 1 THEN (SELECT lon FROM UNNEST(ends) WHERE lon IS NOT NULL LIMIT 1)
           WHEN n_town >= 1 THEN town_lon
           ELSE NULL END AS lon,
         CASE
           WHEN b_lat IS NOT NULL AND UPPER(IFNULL(b_conf, '')) = 'CORROBORATED'
             THEN 'verified_asset_match'
           WHEN b_lat IS NOT NULL THEN 'substation_match'
           WHEN n_sub >= 2 THEN 'corridor_midpoint'
           WHEN n_sub = 1 THEN 'corridor_one_end'
           WHEN n_town >= 1 THEN 'municipality_centroid'
           ELSE 'unplaced' END AS loc_method,
         COALESCE(b_county, town_county) AS county_name,
         IF(n_sub >= 2, ends[OFFSET(0)].lat, NULL) AS end_a_lat,
         IF(n_sub >= 2, ends[OFFSET(0)].lon, NULL) AS end_a_lon,
         IF(n_sub >= 2, ends[OFFSET(1)].lat, NULL) AS end_b_lat,
         IF(n_sub >= 2, ends[OFFSET(1)].lon, NULL) AS end_b_lon,
         COALESCE(b_anchor, ends[SAFE_OFFSET(0)].nm) AS anchor_name
  FROM rtep
),

-- =============================================================================================
-- SOURCE 2 - MISO MTEP Appendix A
-- =============================================================================================
mtep AS (
  SELECT
    'MISO MTEP' AS source,
    CONCAT('MTEP-', CAST(ROW_NUMBER() OVER (ORDER BY from_sub, to_sub, expected_isd) AS STRING))
      AS project_id,
    CONCAT(IFNULL(from_sub, '?'), IF(to_sub IS NULL, '', CONCAT(' → ', to_sub))) AS title,
    CAST(NULL AS STRING) AS driver, CAST(NULL AS STRING) AS project_type,
    CONCAT(IFNULL(from_sub, ''), IF(to_sub IS NULL, '', CONCAT(' - ', to_sub))) AS location_text,
    CAST(NULL AS STRING) AS description,
    planning_status AS status_raw,
    CAST(expected_isd AS STRING) AS in_service_date,
    CAST(NULL AS STRING) AS actual_in_service_date,
    SAFE_CAST(current_cost AS FLOAT64) / 1e6 AS cost_usd_m,
    CAST(NULL AS STRING) AS owner,
    UPPER(TRIM(from_sub)) AS a_nm, UPPER(TRIM(to_sub)) AS b_nm
  FROM `{DS}.in_txexp_miso_mtep_appendix_a_status`
),
mtep_placed AS (
  SELECT m.source, m.project_id, m.title, m.driver, m.project_type, m.location_text,
         m.description, m.status_raw, m.in_service_date, m.actual_in_service_date, m.cost_usd_m, m.owner,
         CASE WHEN sa.lat IS NOT NULL AND sb.lat IS NOT NULL THEN (sa.lat + sb.lat) / 2
              WHEN sa.lat IS NOT NULL THEN sa.lat
              WHEN sb.lat IS NOT NULL THEN sb.lat
              WHEN ta.lat IS NOT NULL THEN ta.lat ELSE NULL END AS lat,
         CASE WHEN sa.lon IS NOT NULL AND sb.lon IS NOT NULL THEN (sa.lon + sb.lon) / 2
              WHEN sa.lon IS NOT NULL THEN sa.lon
              WHEN sb.lon IS NOT NULL THEN sb.lon
              WHEN ta.lon IS NOT NULL THEN ta.lon ELSE NULL END AS lon,
         CASE WHEN sa.lat IS NOT NULL AND sb.lat IS NOT NULL THEN 'corridor_midpoint'
              WHEN sa.lat IS NOT NULL OR sb.lat IS NOT NULL THEN 'substation_match'
              WHEN ta.lat IS NOT NULL THEN 'municipality_centroid'
              ELSE 'unplaced' END AS loc_method,
         COALESCE(sa.county, sb.county, ta.county) AS county_name,
         sa.lat AS end_a_lat, sa.lon AS end_a_lon, sb.lat AS end_b_lat, sb.lon AS end_b_lon,
         COALESCE(m.a_nm, m.b_nm) AS anchor_name
  FROM mtep m
  LEFT JOIN sub1 sa ON sa.nm = m.a_nm
  LEFT JOIN sub1 sb ON sb.nm = m.b_nm
  LEFT JOIN town ta ON ta.ct = m.a_nm
),

-- =============================================================================================
-- SOURCE 3 - utility grid plans (IURC TDSIC / IRP). 119 were already located by G15.
-- =============================================================================================
plans AS (
  SELECT
    'Utility grid plan' AS source,
    CONCAT('GP-', IFNULL(CAST(project_id AS STRING),
                         CAST(ROW_NUMBER() OVER (ORDER BY utility, station_name) AS STRING)))
      AS project_id,
    COALESCE(asset_name, station_name, document_name) AS title,
    asset_type AS driver, CAST(NULL AS STRING) AS project_type,
    station_name AS location_text,
    -- ⚠ NOT document_name. That column holds the FILENAME of the IURC exhibit
    -- ("dmccall_petitioner's exhibit no_12_31_2015...pdf"), and printing it under "what the work
    -- is" told a reader the work was a PDF. The TDSIC rows carry no work description at all, and
    -- an absent description renders as an absence rather than as a filename.
    CAST(NULL AS STRING) AS description,
    location_status AS status_raw,
    CAST(in_service_year AS STRING) AS in_service_date,
    CAST(NULL AS STRING) AS actual_in_service_date,
    cost_usd_m, utility AS owner,
    lat, lon,
    CASE WHEN lat IS NULL THEN 'unplaced'
         WHEN location_method = 'exact' THEN 'verified_asset_match'
         ELSE 'substation_match' END AS loc_method,
    county AS county_name,
    CAST(NULL AS FLOAT64) AS end_a_lat, CAST(NULL AS FLOAT64) AS end_a_lon,
    CAST(NULL AS FLOAT64) AS end_b_lat, CAST(NULL AS FLOAT64) AS end_b_lon,
    matched_substation AS anchor_name
  FROM `{DS}.in_grid_plans_located`
),

-- =============================================================================================
unioned AS (
  SELECT * FROM rtep_placed
  UNION ALL SELECT * FROM mtep_placed
  UNION ALL SELECT * FROM plans
),
-- last resort: a county centroid, with the county's own radius as the uncertainty
withcty AS (
  SELECT u.*, c.lat AS c_lat, c.lon AS c_lon, c.radius_mi AS c_radius
  FROM unioned u
  LEFT JOIN cty c ON c.county_name = UPPER(TRIM(REGEXP_REPLACE(
                       IFNULL(u.county_name, ''), r'(?i)\\s+county$', '')))
)

SELECT
  source, project_id, title, driver, project_type, location_text, description, owner,
  status_raw,
  -- ⛔ THREE STATUS CLASSES, and `in_service` is NOT future capacity. 9,163 of 15,443 PJM rows
  -- are already built. `cancelled` is carried so it can be excluded rather than silently mixed
  -- in - a cancelled upgrade is the opposite of a promise.
  CASE
    WHEN REGEXP_CONTAINS(UPPER(IFNULL(status_raw, '')), r'CANCEL|WITHDRAW|^W$') THEN 'cancelled'
    WHEN REGEXP_CONTAINS(UPPER(IFNULL(status_raw, '')), r'^IS$|IN SERVICE|M4') THEN 'in_service'
    WHEN REGEXP_CONTAINS(UPPER(IFNULL(status_raw, '')),
         r'^UC|CONSTRUCT|^EP$|M2|M3|APPROVED|ACTIVE|EXECUT') THEN 'approved'
    WHEN REGEXP_CONTAINS(UPPER(IFNULL(status_raw, '')), r'^PL$|PROPOS|M1|ON HOLD|PLANNED')
      THEN 'proposed'
    -- ⚠ A FOURTH CLASS, BECAUSE FORCING THESE INTO proposed/approved WOULD BE AN INVENTION.
    -- The IURC TDSIC/IRP rows are a utility's filed capital plan; the source carries no
    -- per-project approval status at all - `location_status` is about OUR geocoding, not the
    -- project - and in_service_year is NULL on 603 of 618. They are planned work by the nature
    -- of the filing, so they are labelled as a filed plan and left there.
    WHEN source = 'Utility grid plan' THEN 'filed_plan'
    ELSE 'unclassified'
  END AS status_class,
  in_service_date, actual_in_service_date, cost_usd_m,
  county_name, anchor_name,
  end_a_lat, end_a_lon, end_b_lat, end_b_lon,
  COALESCE(lat, IF(loc_method = 'unplaced', c_lat, NULL)) AS lat,
  COALESCE(lon, IF(loc_method = 'unplaced', c_lon, NULL)) AS lon,
  IF(loc_method = 'unplaced' AND c_lat IS NOT NULL, 'county_centroid', loc_method) AS loc_method,
  -- ⭐ THE RING. Keyed on how well the LOCATION is known, never on status.
  CASE
    -- ⛔ NO RING WHERE THE LOCATION IS NOT AN ESTIMATE. Operator, 2026-08-20f: *"for the grid
    -- assets that we can actually place by coordinates or through a join with an existing asset,
    -- we do not need to apply a radius estimation."* Correct, and it matters: a project joined to
    -- a substation we hold IS at that substation, and drawing ±1.5 miles around it invents a
    -- doubt we do not have. Worse, it would make a KNOWN location look like a guessed one, which
    -- is the same disease as an estimate styling itself as published - just pointing the other
    -- way. The ring is for ESTIMATED positions only.
    WHEN loc_method IN ('verified_asset_match', 'substation_match') THEN NULL
    WHEN loc_method = 'corridor_midpoint'    THEN
      GREATEST(1.0, ROUND(ST_DISTANCE(ST_GEOGPOINT(end_a_lon, end_a_lat),
                                      ST_GEOGPOINT(end_b_lon, end_b_lat)) / 1609.344 / 2, 1))
    WHEN loc_method = 'corridor_one_end'     THEN 3.0
    WHEN loc_method = 'municipality_centroid' THEN 5.0
    WHEN loc_method = 'unplaced' AND c_lat IS NOT NULL THEN c_radius
    ELSE NULL
  END AS uncertainty_mi,
  CASE
    WHEN loc_method = 'verified_asset_match'  THEN 'Joined to a substation we hold and corroborated by a bus — a known position, not an estimate'
    WHEN loc_method = 'substation_match'      THEN 'Joined to the one substation of that name we hold — a known position, not an estimate'
    WHEN loc_method = 'corridor_midpoint'     THEN 'Both ends of the line name resolve — midpoint of the corridor'
    WHEN loc_method = 'corridor_one_end'      THEN 'One end of the line name resolves — the work is off that station'
    WHEN loc_method = 'municipality_centroid' THEN 'Town centroid — NOT the asset site'
    WHEN loc_method = 'unplaced' AND c_lat IS NOT NULL THEN 'County only — the filing names no station or town we hold'
    ELSE 'No location we can resolve — reported, never drawn'
  END AS loc_basis,
  CURRENT_TIMESTAMP() AS built_at
FROM withcty
"""

print("G130 - PLANNED UPGRADES: where future capacity may appear")
job = client.query(SQL)
job.result()
gb = round((job.total_bytes_processed or 0) / 1e9, 2)
print(f"  built, {gb} GB scanned")

n = list(client.query(f"SELECT COUNT(*) n FROM `{OUT}`"))[0].n
d = list(client.query(f"SELECT COUNT(DISTINCT CONCAT(source,'|',project_id)) n FROM `{OUT}`"))[0].n
print(f"  fan-out {n:,} rows / {d:,} distinct projects = {n / d:.4f}")
assert n == d, "one row per project, or a join duplicated something"

print("\n  by source and placement:")
for r in client.query(f"""
  SELECT source, COUNT(*) n, COUNTIF(lat IS NOT NULL) placed,
         COUNTIF(status_class IN ('proposed','approved')) future
  FROM `{OUT}` GROUP BY 1 ORDER BY 2 DESC"""):
    pct = 100 * r.placed / r.n if r.n else 0
    print(f"    {r.source:20} n={r.n:>6,}  placed {r.placed:>5,} ({pct:5.1f}%)  "
          f"still to come {r.future:>5,}")

print("\n  by loc_method (the ring is sized from this):")
for r in client.query(f"""
  SELECT loc_method, COUNT(*) n, ROUND(AVG(uncertainty_mi), 1) mi,
         COUNTIF(lat IS NOT NULL) placed
  FROM `{OUT}` GROUP BY 1 ORDER BY 2 DESC"""):
    print(f"    {r.loc_method:24} n={r.n:>6,}  placed {r.placed:>5,}  "
          f"mean ring {str(r.mi):>6} mi")

print("\n  by status_class:")
for r in client.query(f"""
  SELECT status_class, COUNT(*) n, COUNTIF(lat IS NOT NULL) placed,
         ROUND(SUM(cost_usd_m)) cost
  FROM `{OUT}` GROUP BY 1 ORDER BY 2 DESC"""):
    print(f"    {r.status_class:16} n={r.n:>6,}  placed {r.placed:>5,}  "
          f"${(r.cost or 0):,.0f}M")

# ⛔ THE COUNTY TIER IS BUILT AND UNREACHABLE, AND SAYING SO IS THE POINT. Measured: 0 of the
# 618 grid plans carry a county WITHOUT also carrying a coordinate, and neither the PJM RTEP nor
# the MISO MTEP feed publishes a county at all. Leaving the code path in place while pretending it
# contributes coverage would be a control drawn over data we do not have - the defect
# REFERENCE_TOOL_GAP.md calls "a data gap wearing a UI costume". It stays wired for the day a
# county-bearing source arrives, and until then it reports zero out loud.
cc = list(client.query(f"""
  SELECT COUNTIF(loc_method = 'county_centroid') n FROM `{OUT}`"""))[0].n
print(f"\n  ⚠ county_centroid fired {cc} times — no source in this build publishes a county for a "
      f"project it cannot otherwise place. The tier is wired and unfed, and is reported, not hidden.")

s = list(client.query(f"""
  SELECT COUNT(*) n, COUNTIF(lat IS NOT NULL) placed,
         COUNTIF(lat IS NOT NULL AND status_class IN ('proposed','approved')) future_placed,
         -- ⚠ BOTH ends, not just A. The first version counted `end_a_lat IS NOT NULL` and
         -- reported 133 "corridors" while the export could only draw 81 lines - the MISO branch
         -- sets each end independently, so a row can carry A and not B. A figure in a build's
         -- own summary that the export then contradicts is the two-instruments defect in
         -- miniature.
         COUNTIF(end_a_lat IS NOT NULL AND end_b_lat IS NOT NULL) corridors
  FROM `{OUT}`"""))[0]
print(f"\n  ⭐ {s.placed:,} of {s.n:,} planned items now carry a position "
      f"({100 * s.placed / s.n:.1f}%)")
print(f"  ⭐ {s.future_placed:,} of those are still to come (proposed or approved) — "
      f"the ones that mean future capacity")
print(f"  ⭐ {s.corridors:,} resolve BOTH ends and can be drawn as a corridor, not a dot")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_planned_upgrades',
 'indiana_app.in_pjm_rtep_upgrades + in_pjm_rtep_upgrade_details + in_rtep_bus_join x '
 'indiana_app.in_txexp_miso_mtep_appendix_a_status x indiana_app.in_grid_plans_located x '
 'indiana_app.in_substations (gazetteer) x energy.county_boundaries (county centroids)',
 'One row per PLANNED grid upgrade, placed by a tiered method and carrying an uncertainty radius. '
 'Tiers: verified_asset_match 0.5 mi, substation_match 1.5 mi, corridor_midpoint half the span, '
 'corridor_one_end 3 mi, municipality_centroid 5 mi, county_centroid the county radius, else '
 'unplaced and never drawn. ⭐ The ring is keyed on HOW WELL THE LOCATION IS KNOWN, never on '
 'project status - a fully approved project can still be named only by its town. '
 'A-to-B corridor names are split on hyphen, EN DASH, EM DASH, slash and comma and each end '
 'resolved separately; a name resolving to more than one substation is NOT used, because a '
 'shared name tells us the county rather than the site. status_class separates proposed / '
 'approved / in_service / cancelled - in_service is already built and is NOT future capacity. '
 'RE-SCRAPE COMMAND: python scripts/build_planned_upgrades.py',
 {n}, {gb}, CURRENT_TIMESTAMP(),
 'G130, operator 2026-08-20f. Before this, 119 of 618 utility grid plans were the ONLY planned '
 'work on the map and were drawn as plain circles like existing assets; 287 PJM RTEP upgrades '
 'were already placed in in_rtep_bus_join and NOTHING rendered them. '
 'IDEMPOTENCY: replace_safe. CADENCE: quarterly (RTO planning cycles); the IURC grid-plan '
 'dockets are event-driven.'
)""").result()
print("\n  _registry row written")
print("PLANNED UPGRADES COMPLETE")
