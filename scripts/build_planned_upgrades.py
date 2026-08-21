"""G130: WHERE FUTURE CAPACITY MAY APPEAR — every planned upgrade, placed as well as it honestly can be.

Operator, 2026-08-20f: *"I would like to place these upgrades or new developments on the map for
where future capacity may exist… we may NOT have a coordinate, but the documentation in the
filings often carry a regional location that we can use to estimate the locations… these upgrades
or new developments should NOT display the same as the current grid assets."*

================================================================================================
⭐ 2026-08-21 — THE SEVEN THINGS THE FIRST VERSION LEFT OUT, AND WHAT MEASURING THEM FOUND
================================================================================================
G130 was marked DONE on 2026-08-20f while three whole upgrade inventories were absent. It was
corrected back to PARTIAL and this rebuild closes items 1-7 of that list. ⛔ TWO OF THE THREE
INVENTORIES WERE DESCRIBED WRONGLY IN EVERY DOCUMENT, and measuring them first is the only reason
this build is not wrong in the same way:

  ⛔ THE MISO DPP-2025 COST FIGURE IS A 14-STATE TOTAL, NOT INDIANA'S. Three documents quote
     `in_miso_dpp2025_ph1_project_costs` as "$29,522M across 56,043 MW, ~$527k per MW - the best
     answer we hold to what an interconnection will cost". Measured: the 202 projects span
     FOURTEEN states. Indiana is 21 projects, $1,704M, 6,034 MW - about $282k per MW. The figure
     was real and the geography was not, and `audit_handoff_docs.py` passed it because the audit
     re-measured the NUMBER and never its SCOPE. Operator ruling 2026-08-21: Indiana only, and the
     MISO-wide headline is dropped rather than kept as a benchmark. Only the 21 are loaded here.

  ⛔ "375 ROWS" OF COST ALLOCATION IS 26 UPGRADES. `in_pjm_rtep_cost_allocations` holds 375 rows
     across 26 distinct upgrade_ids - it is a per-ZONE share breakdown, 21-24 zones per upgrade.
     All 375 join cleanly, so the work is real, but it attributes cost on 26 projects and the
     coverage card must say 26.

  ⚠ THE 774 UNREPRESENTED MISO ROWS ARE 697 ALREADY-BUILT + 77 UNDER EVALUATION. All 774 are
     Indiana (769 `IN`, 5 shared-border). Operator ruling 2026-08-21: include them, class the 697
     `in_service`, and default them OFF - exactly how PJM's 9,163 in-service rows are already
     handled. ⛔ Coverage is therefore stated TWICE: a total denominator and a future-capacity-only
     denominator, because the second is the one a siter actually wants.

================================================================================================
⭐ THE THING THE MEASUREMENT FOUND FIRST TIME: MOST "UNPLACEABLE" LOCATIONS ARE CORRIDORS
================================================================================================
Reading the unmatched strings instead of counting them: `TWIN BRANCH - EAST ELKHART`,
`SORENSON - ILLINOIS ROAD`, `TANNERS CREEK - DESOTO - SORENSON`, `MADISON – CROSS STREET`,
`SORENSON/KEYSTONE`. Those are not failed station lookups. They are A-to-B LINE NAMES — the
upgrade is a rebuild of the corridor between two substations, and a corridor is not a point.
⚠ THE SEPARATOR VARIES: hyphen, EN DASH and slash all appear, and splitting on "-" alone misses
every en-dash row. That is the value-vocabulary trap in punctuation form.
⚠ And BigQuery's RE2 rejects \\uXXXX escapes outright, so the dashes are written literally.

⭐ 2026-08-21 ADDS A FOURTH SEPARATOR: U+FFFD, THE REPLACEMENT CHARACTER. `New Substation along
the Desoto <?> Fall Creek 345 kV` reached our table with the en dash already destroyed upstream.
A mojibake byte is still a separator, and refusing to split on it loses the row twice over.

================================================================================================
⭐ NORMALISATION — WHY 32 SUBSTATIONS WERE INVISIBLE TO AN EXACT MATCH
================================================================================================
Reading the 437 unresolved PJM strings: `Sullivan 345 kV`, `Desoto 345 kV`, `Mississinewa Sub`,
`Sullivan 345kV switching station`, `Liberty Center 69 kV`. The station is named and the exact
match fails on a VOLTAGE SUFFIX and a descriptor word. Normalising both sides - strip a kV token,
strip SUBSTATION/STATION/SUB/SWITCHING STATION/TAP, drop punctuation, collapse spaces - is not
fuzzy matching: it is comparing the two names after removing the parts that are not the name.

⛔ AND IT STOPS THERE. `RANDOLF` vs `RANDOLPH` is a spelling variant and an edit-distance matcher
would "fix" it - along with pairs that are genuinely different stations. Operator rule, carried
from the first build: *refuse below a confidence threshold*, because an upgrade in the wrong place
is a coordinate someone might plan around. Everything that survives normalisation and still does
not match is REPORTED as unresolved, not guessed.

⛔ SENTINELS ARE REFUSED EXPLICITLY. `tbd`, `TBD`, `n/a`, `P5 Substation: Location CEII` are in
the location column. `CEII` in particular is the publisher saying the location is withheld by
regulation - the one string we must never treat as a place name.

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
    municipality_centroid  MEASURED the place's own equal-area radius + 4.0 mi. See below.
    county_centroid        the county's own equal-area radius
    unplaced               NULL     reported and never drawn. ⛔ An upgrade in the wrong place is
                                    worse than one with no place - it is a coordinate someone
                                    might plan around.

⭐ THE MUNICIPALITY RING IS NOW CALIBRATED, NOT ASSUMED — and the calibration overturned the
first design. `in_places` (G130 item 4, TIGER PLACE, 976 places) gives each town its own
equal-area radius, so the obvious move was to use it directly in place of the flat 5.0 mi. ⛔ THAT
WOULD HAVE BEEN WORSE. Measured against 2,691 cases where a substation names the town it sits in
or beside:

      ring                containment   mean ring
      place radius alone      41.4%       1.95 mi   <- claims precision we do not have
      radius + 2 mi           71.8%       3.96 mi
      radius + 3 mi           80.7%       4.96 mi
      radius + 4 mi           86.7%       5.96 mi   <- CHOSEN
      radius + 5 mi           91.6%       6.96 mi
      the flat 5.0 mi it replaces  83.0%  5.00 mi

A substation serving a town is frequently OUTSIDE its corporate limits, which is why the polygon
alone contains only two cases in five. `radius + 4` beats the flat ring it replaces on containment
AND scales with the place - Indianapolis gets 14.8 mi, a four-street village gets 5.0 - where the
old constant gave both the same. ⚠ The +4 is an empirical margin and is recorded as one.

⛔ THE OLD 406-NAME GAZETTEER IS KEPT AS A FALLBACK, NOT REPLACED. It was built from
`in_substations.city`, so it is the set of towns that host a substation - a by-product. TIGER
holds 971 distinct names against its 406, but 27 names are in the by-product and NOT in TIGER:
unincorporated localities that are real places a filing can name. Dropping them to adopt the
better source would have lost coverage silently.

⛔ STATUS IS SEPARATE FROM PLACEMENT AND BOTH ARE PUBLISHED. `IS` / `M4 - Project in Service`
means the work is ALREADY BUILT — 9,163 of 15,443 PJM rows — and is NOT future capacity.
Cancelled and withdrawn work is carried with its own class so it can be excluded, because a
cancelled upgrade is the opposite of a promise.

RE-SCRAPE COMMAND: python scripts/build_planned_upgrades.py
⚠ IDEMPOTENT: replace_safe. CADENCE: quarterly — RTO planning cycles; the IURC grid-plan dockets
are event-driven.
⚠ DEPENDS ON `in_places` — run `python scripts/load_tiger_place.py` first if it is absent.
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

# ================================================================================================
# ⭐ ONE NORMALISER, APPLIED TO BOTH SIDES OF EVERY NAME MATCH.
# Defined once as a SQL expression over a column named by the caller, because a normaliser applied
# to only one side of a join is worse than none: it manufactures misses that look like absent data.
# ⛔ RE2, NOT PCRE. BigQuery rejects \uXXXX; every character class here is literal ASCII.
# ================================================================================================
def norm(col):
    """SQL that reduces a station/place name to the part that is actually the name."""
    return (
        "TRIM(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE("
        f"UPPER(TRIM({col}))"
        r", r'[0-9]+(\.[0-9]+)? ?KV', ' ')"
        r", r'\b(SWITCHING STATION|SUBSTATION|STATION|SUB|TAP|SITE|PROPOSED|THE)\b', ' ')"
        r", r'[^A-Z0-9 ]', ' ')"
        r", r' +', ' '))"
    )


# ⛔ `NEW` IS NOT IN THAT LIST, AND IT WAS, AND REMOVING IT IS THE POINT OF THIS COMMENT.
# The first version of this normaliser stripped NEW as a descriptor. Measured against the two
# gazetteers: it rewrites 24 Indiana place names and **13 of them collide with a DIFFERENT REAL
# TOWN** - New Albany -> ALBANY (130 miles apart), New Palestine -> PALESTINE, New Harmony ->
# HARMONY, New Carlisle -> CARLISLE. `New` is not a descriptor in Indiana, it is the first word of
# the name. Every other strip-word was measured the same way; SWITCHING STATION, TAP, SITE,
# PROPOSED and THE collide with nothing at all.
#
# ⚠ AND THE PROBE THAT FOUND IT LIED FIRST. The initial collision audit was written as a regex
# inside a `python -c` string passed through the shell, the backslashes were eaten, and it
# reported ZERO collisions for all nine words - while a collision was already visible on screen.
# That is the ninth-and-tenth occurrence of this project's oldest trap wearing a new hat: an
# all-clean answer is a claim about the instrument first. Re-written as a file, it found them.

# ⚠ A SELF-TEST, because this expression is the load-bearing part of items 5 and 7 and a silent
# change to it would move hundreds of placements without failing anything.
assert "KV" in norm("x") and "SUBSTATION" in norm("x"), "norm() lost a rule"
assert norm("x").count("REGEXP_REPLACE") == 4, "norm() should apply exactly four rewrites"
assert r"|NEW|" not in norm("x"), "NEW must NOT be stripped - it collides with 13 real towns"

# ⛔ THE SENTINELS. These are the publisher saying "we are not telling you", and every one of them
# would otherwise be treated as a place name. CEII is a legal withholding, not a location.
SENTINEL = r"^(TBD|TBA|N A|NA|NONE|VARIOUS|UNKNOWN|CEII|LOCATION CEII|X|XX)$"

# ⚠ THE SEPARATORS, WRITTEN LITERALLY. hyphen, EN DASH, EM DASH, slash, comma, and U+FFFD - the
# replacement character an upstream encoding failure left where an en dash used to be.
SPLIT = "[^-–—/,�]+"

MUNI_MARGIN = 4.0        # miles. Measured: 86.7% containment. See the calibration table above.

# ⭐ How far apart two points sharing a normalised substation name may be and still be treated as
# ONE site. Measured, not chosen: the 25 colliding names split 11 under 1.03 mi against 14 over
# 120 mi, with nothing in between. 2.0 sits in a gap two orders of magnitude wide.
SUB_SPREAD_MAX = 2.0

# ⛔ THE LONGEST A "CORRIDOR" MAY BE BEFORE WE STOP BELIEVING IT IS ONE.
# A-to-B splitting assumes the name is a LINE. Some of these names are LISTS: `Twin Branch,
# Riverside` resolved South Bend against Evansville and produced a 267-mile "corridor" whose ring
# covered most of the state, and `East Side, South Bend, Twin Branch` did the same. A ring that
# large is not a placement - it is the whole map with a circle on it.
# ⚠ THERE IS NO CLEAN GAP HERE, unlike SUB_SPREAD_MAX, so this is a judgement and is recorded as
# one. Measured spans: p50 12.4, p75 22.8, p90 64.0, max 267.6 over 80 corridors. 75 keeps the
# genuine long line TWIN BRANCH - ROBISON PARK (64.0 mi, Mishawaka to Fort Wayne, two real
# stations) and refuses the seven that are comma-separated lists of unrelated places.
CORRIDOR_MAX = 75.0

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
-- ⭐ THE NORMALISED GAZETTEER (item 5), AND ITS ACCEPTANCE RULE IS MEASURED, NOT ASSUMED.
--
-- The obvious rule - "a normalised name covering more than one point is ambiguous, refuse it" -
-- is what the exact gazetteer above uses, and here it is WRONG. Measured: 25 normalised names
-- cover two or more distinct points, and the spread between them splits perfectly in two:
--
--       0.01 mi  PARR                 PARR | Parr Substation
--       0.07 mi  EDWARDSPORT          EDWARDSPORT STATION (138 KV) | ... (69 KV)
--       0.11 mi  TWIN BRANCH          TWIN BRANCH (138 KV) | TWIN BRANCH (345 KV)
--        ...                          (eleven of these, all under 1.03 mi)
--       1.03 mi  CLAY CITY            CLAY CITY | Clay City Substation
--     ---------- NOTHING AT ALL BETWEEN 1.03 AND 120.36 MILES ----------
--     120.36 mi  HILLSDALE            HILLSDALE | Hillsdale Substation
--     223.46 mi  GIBSON               GIBSON STATION | Gibson Substation
--
-- The first eleven are ONE substation recorded twice - the 138 kV yard and the 345 kV yard of the
-- same site, or the same station spelled with and without the word "Substation". The last
-- fourteen are genuinely different stations that happen to share a county name. Refusing both
-- groups would have thrown away TWIN BRANCH, which is one of the exact strings the backlog names
-- as unresolved.
--
-- ⭐ So the threshold is a spread test at 2.0 mi, sitting in a gap two orders of magnitude wide.
-- That is what "refuse below a confidence threshold" means when the threshold is measured instead
-- of picked: the data drew the line, not the author.
subn AS (
  SELECT {norm('substation_name')} AS nm,
         COUNT(DISTINCT FORMAT('%.4f|%.4f', lat, lon)) AS pts,
         ROUND(ST_MAXDISTANCE(ST_UNION_AGG(ST_GEOGPOINT(lon, lat)),
                              ST_UNION_AGG(ST_GEOGPOINT(lon, lat))) / 1609.344, 2) AS spread_mi,
         -- ⛔ NOT A CENTROID, and deterministically chosen. Within a 2-mile spread either point
         -- is the site; ANY_VALUE would pick a different one between runs and make the build
         -- irreproducible, which is its own defect.
         ARRAY_AGG(STRUCT(lat, lon) ORDER BY lat, lon LIMIT 1)[OFFSET(0)].lat AS lat,
         ARRAY_AGG(STRUCT(lat, lon) ORDER BY lat, lon LIMIT 1)[OFFSET(0)].lon AS lon,
         ANY_VALUE(county) AS county
  FROM `{DS}.in_substations`
  WHERE geog IS NOT NULL AND substation_name IS NOT NULL AND TRIM(substation_name) != ''
  GROUP BY 1
  -- ⚠ THE ALIASES, NOT THE EXPRESSIONS REPEATED. Inside HAVING the names `lat` and `lon` resolve
  -- to the SELECT-list aliases - which are aggregates - so repeating an aggregate over them is an
  -- aggregation of an aggregation and BigQuery rejects it outright. The alias is also the only
  -- version that cannot drift from the one actually computed.
  HAVING nm != '' AND (pts = 1 OR spread_mi <= {SUB_SPREAD_MAX})
),
-- ⭐ TIGER PLACE (item 4): a REAL municipality gazetteer with each place's own centre and radius
place AS (
  SELECT {norm('name')} AS nm, ANY_VALUE(lat) AS lat, ANY_VALUE(lon) AS lon,
         ANY_VALUE(radius_mi) AS radius_mi
  FROM `{DS}.in_places`
  GROUP BY 1
  HAVING COUNT(*) = 1 AND nm != ''
),
-- ⛔ KEPT, NOT REPLACED: 27 names live here and not in TIGER (unincorporated localities)
town AS (
  SELECT {norm('city')} AS ct, AVG(lat) AS lat, AVG(lon) AS lon,
         ANY_VALUE(county) AS county, ANY_VALUE(county_fips) AS county_fips
  FROM `{DS}.in_substations`
  WHERE geog IS NOT NULL AND city IS NOT NULL AND TRIM(city) != ''
  GROUP BY 1
),
cty AS (
  SELECT LPAD(CAST(COUNTYFP AS STRING), 3, '0') AS county_fips,
         UPPER(TRIM(NAME)) AS county_name,
         {norm('NAME')} AS county_nm,
         ST_Y(ST_CENTROID(geom)) AS lat, ST_X(ST_CENTROID(geom)) AS lon,
         -- an honest radius for a county: the disc of equal area
         ROUND(SQRT(ST_AREA(geom) / ACOS(-1)) / 1609.344, 1) AS radius_mi
  FROM `{EN}.county_boundaries`
  WHERE STUSPS = 'IN'
),

-- =============================================================================================
-- COST ALLOCATION (item 1). 375 rows / 26 upgrades - a per-ZONE share, not 375 projects.
-- ⚠ TWO share_types coexist ('Load Ratio Share', 'Non-Load Ratio Share') and an upgrade can
-- carry both. They are NOT summed together: they are different allocation methods over the same
-- cost, and adding them would invent a total above 100%.
-- =============================================================================================
alloc AS (
  SELECT upgrade_id AS pid,
         COUNT(DISTINCT zone) AS n_zones,
         COUNT(DISTINCT share_type) AS n_methods,
         -- the zone bearing the largest share, which is the one a reader asks about
         ARRAY_AGG(zone ORDER BY percent DESC LIMIT 1)[OFFSET(0)] AS top_zone,
         ROUND(MAX(percent), 2) AS top_pct,
         STRING_AGG(FORMAT('%s %.1f%%', zone, percent), ', '
                    ORDER BY percent DESC LIMIT 5) AS top5
  FROM `{DS}.in_pjm_rtep_cost_allocations`
  WHERE percent IS NOT NULL AND zone IS NOT NULL
  GROUP BY 1
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
  SELECT d.pid, TRIM(p) AS part, {norm('p')} AS partn, off
  FROM rtep_det d, UNNEST(REGEXP_EXTRACT_ALL(UPPER(d.loc_raw), r'{SPLIT}')) AS p WITH OFFSET off
  WHERE d.loc_raw IS NOT NULL AND TRIM(d.loc_raw) != ''
    -- ⛔ refuse the sentinels before they can be matched against anything
    AND NOT REGEXP_CONTAINS({norm('p')}, r'{SENTINEL}')
),
rtep_ends AS (
  SELECT p.pid,
         -- ⛔ MATCHED ENDPOINTS ONLY, AND THIS WAS A REAL BUG. The first version aggregated every
         -- part of the name, so `ends[OFFSET(0)]` could be an UNMATCHED fragment: 11 rows came
         -- out graded `corridor_midpoint` - both ends resolved - while carrying no coordinate at
         -- all, because the midpoint was averaged from two nulls. A grade that says "we know
         -- where this is" on a row with no position is the worst kind of wrong.
         ARRAY_AGG(IF(COALESCE(s.lat, sn.lat) IS NULL, NULL,
                      STRUCT(COALESCE(s.lat, sn.lat) AS lat,
                             COALESCE(s.lon, sn.lon) AS lon, p.part AS nm))
                   IGNORE NULLS ORDER BY p.off LIMIT 4) AS ends,
         COUNTIF(COALESCE(s.nm, sn.nm) IS NOT NULL) AS n_sub,
         -- ⭐ item 5: TIGER place first, the substation-city by-product second
         COUNTIF(COALESCE(s.nm, sn.nm) IS NULL
                 AND COALESCE(pl.nm, t.ct) IS NOT NULL) AS n_town,
         ANY_VALUE(IF(COALESCE(s.nm, sn.nm) IS NULL, COALESCE(pl.lat, t.lat), NULL)) AS town_lat,
         ANY_VALUE(IF(COALESCE(s.nm, sn.nm) IS NULL, COALESCE(pl.lon, t.lon), NULL)) AS town_lon,
         -- a place we matched in TIGER carries its own radius; the by-product does not, and the
         -- median TIGER radius stands in for it rather than a silent zero
         ANY_VALUE(IF(COALESCE(s.nm, sn.nm) IS NULL, pl.radius_mi, NULL)) AS town_radius,
         ANY_VALUE(IF(COALESCE(s.nm, sn.nm) IS NULL, t.county, NULL)) AS town_county,
         -- ⭐ item 6: a bare county name IS a location, just a coarse one. `Jay`, `Adams`,
         -- `Sullivan` and `Newton` are Indiana counties and appear alone in the location column.
         COUNTIF(COALESCE(s.nm, sn.nm, pl.nm, t.ct) IS NULL AND c.county_nm IS NOT NULL) AS n_cty,
         ANY_VALUE(IF(COALESCE(s.nm, sn.nm, pl.nm, t.ct) IS NULL, c.county_name, NULL)) AS cty_name
  FROM rtep_parts p
  LEFT JOIN sub1  s  ON s.nm  = p.part
  LEFT JOIN subn  sn ON sn.nm = p.partn
  LEFT JOIN place pl ON pl.nm = p.partn
  LEFT JOIN town  t  ON t.ct  = p.partn
  LEFT JOIN cty   c  ON c.county_nm = p.partn
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
    CAST(NULL AS FLOAT64) AS mw_enabled,
    m.owner, m.state,
    a.n_zones AS alloc_n_zones, a.top_zone AS alloc_top_zone, a.top_pct AS alloc_top_pct,
    a.top5 AS alloc_top5, a.n_methods AS alloc_n_methods,
    b.lat AS b_lat, b.lon AS b_lon, b.anchor AS b_anchor, b.county AS b_county, b.conf AS b_conf,
    e.ends, e.n_sub, e.n_town, e.town_lat, e.town_lon, e.town_radius, e.town_county,
    e.n_cty, e.cty_name
  FROM rtep_meta m
  LEFT JOIN rtep_det d USING (pid)
  LEFT JOIN rtep_bridge b USING (pid)
  LEFT JOIN rtep_ends e USING (pid)
  LEFT JOIN alloc a USING (pid)
  WHERE UPPER(IFNULL(m.state, '')) = 'IN' OR b.pid IS NOT NULL OR e.pid IS NOT NULL
),
rtep_placed AS (
  SELECT source, project_id, title, driver, project_type, location_text, description,
         status_raw,
         CAST(in_service_date AS STRING) AS in_service_date,
         CAST(actual_in_service_date AS STRING) AS actual_in_service_date,
         cost_usd_m, mw_enabled, owner,
         alloc_n_zones, alloc_top_zone, alloc_top_pct, alloc_top5, alloc_n_methods,
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
         town_radius AS place_radius_mi,
         CASE
           WHEN b_lat IS NOT NULL AND UPPER(IFNULL(b_conf, '')) = 'CORROBORATED'
             THEN 'verified_asset_match'
           WHEN b_lat IS NOT NULL THEN 'substation_match'
           WHEN n_sub >= 2 THEN 'corridor_midpoint'
           WHEN n_sub = 1 THEN 'corridor_one_end'
           WHEN n_town >= 1 THEN 'municipality_centroid'
           ELSE 'unplaced' END AS loc_method,
         COALESCE(b_county, town_county, cty_name) AS county_name,
         IF(n_sub >= 2, ends[OFFSET(0)].lat, NULL) AS end_a_lat,
         IF(n_sub >= 2, ends[OFFSET(0)].lon, NULL) AS end_a_lon,
         IF(n_sub >= 2, ends[OFFSET(1)].lat, NULL) AS end_b_lat,
         IF(n_sub >= 2, ends[OFFSET(1)].lon, NULL) AS end_b_lon,
         COALESCE(b_anchor, ends[SAFE_OFFSET(0)].nm) AS anchor_name
  FROM rtep
),

-- =============================================================================================
-- SOURCE 2 - MISO MTEP Appendix A (status)
-- =============================================================================================
mtep AS (
  SELECT
    'MISO MTEP' AS source,
    CONCAT('MTEP-', CAST(ROW_NUMBER() OVER (ORDER BY from_sub, to_sub, expected_isd) AS STRING))
      AS project_id,
    CONCAT(IFNULL(from_sub, '?'), IF(to_sub IS NULL, '', CONCAT(' -> ', to_sub))) AS title,
    CAST(NULL AS STRING) AS driver, CAST(NULL AS STRING) AS project_type,
    CONCAT(IFNULL(from_sub, ''), IF(to_sub IS NULL, '', CONCAT(' - ', to_sub))) AS location_text,
    CAST(NULL AS STRING) AS description,
    planning_status AS status_raw,
    CAST(expected_isd AS STRING) AS in_service_date,
    CAST(NULL AS STRING) AS actual_in_service_date,
    SAFE_CAST(current_cost AS FLOAT64) / 1e6 AS cost_usd_m,
    CAST(NULL AS FLOAT64) AS mw_enabled,
    CAST(NULL AS STRING) AS owner,
    {norm('from_sub')} AS a_nm, {norm('to_sub')} AS b_nm
  FROM `{DS}.in_txexp_miso_mtep_appendix_a_status`
),
mtep_placed AS (
  SELECT m.source, m.project_id, m.title, m.driver, m.project_type, m.location_text,
         m.description, m.status_raw, m.in_service_date, m.actual_in_service_date,
         m.cost_usd_m, m.mw_enabled, m.owner,
         CAST(NULL AS INT64) AS alloc_n_zones, CAST(NULL AS STRING) AS alloc_top_zone,
         CAST(NULL AS FLOAT64) AS alloc_top_pct, CAST(NULL AS STRING) AS alloc_top5,
         CAST(NULL AS INT64) AS alloc_n_methods,
         CASE WHEN sa.lat IS NOT NULL AND sb.lat IS NOT NULL THEN (sa.lat + sb.lat) / 2
              WHEN sa.lat IS NOT NULL THEN sa.lat
              WHEN sb.lat IS NOT NULL THEN sb.lat
              WHEN pa.lat IS NOT NULL THEN pa.lat
              WHEN ta.lat IS NOT NULL THEN ta.lat ELSE NULL END AS lat,
         CASE WHEN sa.lat IS NOT NULL AND sb.lat IS NOT NULL THEN (sa.lon + sb.lon) / 2
              WHEN sa.lat IS NOT NULL THEN sa.lon
              WHEN sb.lat IS NOT NULL THEN sb.lon
              WHEN pa.lat IS NOT NULL THEN pa.lon
              WHEN ta.lat IS NOT NULL THEN ta.lon ELSE NULL END AS lon,
         pa.radius_mi AS place_radius_mi,
         CASE WHEN sa.lat IS NOT NULL AND sb.lat IS NOT NULL THEN 'corridor_midpoint'
              WHEN sa.lat IS NOT NULL OR sb.lat IS NOT NULL THEN 'substation_match'
              WHEN pa.lat IS NOT NULL OR ta.lat IS NOT NULL THEN 'municipality_centroid'
              ELSE 'unplaced' END AS loc_method,
         COALESCE(sa.county, sb.county, ta.county) AS county_name,
         sa.lat AS end_a_lat, sa.lon AS end_a_lon, sb.lat AS end_b_lat, sb.lon AS end_b_lon,
         COALESCE(m.a_nm, m.b_nm) AS anchor_name
  FROM mtep m
  LEFT JOIN subn  sa ON sa.nm = m.a_nm
  LEFT JOIN subn  sb ON sb.nm = m.b_nm
  LEFT JOIN place pa ON pa.nm = m.a_nm
  LEFT JOIN town  ta ON ta.ct = m.a_nm
),

-- =============================================================================================
-- SOURCE 3 - utility grid plans (IURC TDSIC / IRP). 119 were already located by G15.
-- ⭐ item 7: the 499 unplaced now get a second chance against the NORMALISED substation
-- gazetteer and TIGER PLACE. The other half of that item is G15's workpaper parser and is not
-- reachable from here - it is reported, not quietly absorbed.
-- =============================================================================================
plans_raw AS (
  SELECT
    CONCAT('GP-', IFNULL(CAST(project_id AS STRING),
                         CAST(ROW_NUMBER() OVER (ORDER BY utility, station_name) AS STRING)))
      AS project_id,
    COALESCE(asset_name, station_name, document_name) AS title,
    asset_type AS driver,
    station_name AS location_text,
    location_status AS status_raw,
    CAST(in_service_year AS STRING) AS in_service_date,
    cost_usd_m, utility AS owner, lat, lon, location_method, county, matched_substation,
    {norm('station_name')} AS stn
  FROM `{DS}.in_grid_plans_located`
),
plans AS (
  SELECT
    'Utility grid plan' AS source,
    p.project_id, p.title, p.driver, CAST(NULL AS STRING) AS project_type,
    p.location_text,
    -- ⚠ NOT document_name. That column holds the FILENAME of the IURC exhibit
    -- ("dmccall_petitioner's exhibit no_12_31_2015...pdf"), and printing it under "what the work
    -- is" told a reader the work was a PDF. The TDSIC rows carry no work description at all, and
    -- an absent description renders as an absence rather than as a filename.
    CAST(NULL AS STRING) AS description,
    p.status_raw, p.in_service_date, CAST(NULL AS STRING) AS actual_in_service_date,
    p.cost_usd_m, CAST(NULL AS FLOAT64) AS mw_enabled, p.owner,
    CAST(NULL AS INT64) AS alloc_n_zones, CAST(NULL AS STRING) AS alloc_top_zone,
    CAST(NULL AS FLOAT64) AS alloc_top_pct, CAST(NULL AS STRING) AS alloc_top5,
    CAST(NULL AS INT64) AS alloc_n_methods,
    COALESCE(p.lat, sn.lat, pl.lat) AS lat,
    COALESCE(p.lon, sn.lon, pl.lon) AS lon,
    pl.radius_mi AS place_radius_mi,
    CASE WHEN p.lat IS NOT NULL AND p.location_method = 'exact' THEN 'verified_asset_match'
         WHEN p.lat IS NOT NULL THEN 'substation_match'
         WHEN sn.lat IS NOT NULL THEN 'substation_match'
         WHEN pl.lat IS NOT NULL THEN 'municipality_centroid'
         ELSE 'unplaced' END AS loc_method,
    COALESCE(p.county, sn.county) AS county_name,
    CAST(NULL AS FLOAT64) AS end_a_lat, CAST(NULL AS FLOAT64) AS end_a_lon,
    CAST(NULL AS FLOAT64) AS end_b_lat, CAST(NULL AS FLOAT64) AS end_b_lon,
    COALESCE(p.matched_substation, sn.nm, pl.nm) AS anchor_name
  FROM plans_raw p
  LEFT JOIN subn  sn ON p.lat IS NULL AND sn.nm = p.stn
  LEFT JOIN place pl ON p.lat IS NULL AND pl.nm = p.stn
),

-- =============================================================================================
-- ⭐ SOURCE 4 (item 2) - MISO DPP-2025 Phase 1 network-upgrade costs, INDIANA ONLY
-- ⛔ THE PUBLISHED TABLE IS 14 STATES. Operator ruling 2026-08-21: Indiana only, and the
-- MISO-wide total is DROPPED rather than shown as a benchmark. The join key is the queue project
-- number, and `in_queue_miso_extras` (our own Indiana clip) carries all 21 - so this build does
-- NOT need to read energy for it.
-- ⭐ AND THIS IS WHAT FINALLY FEEDS county_centroid (item 6): the queue publishes a COUNTY on
-- every row, which no other planned-upgrade source does.
-- =============================================================================================
dpp AS (
  SELECT
    'MISO DPP-2025' AS source,
    CONCAT('DPP-', c.project) AS project_id,
    CONCAT(c.project, ' - ', CAST(CAST(ROUND(c.nris_mw) AS INT64) AS STRING), ' MW ',
           IFNULL(c.fuel_type, 'generation'),
           IF(q.poiname IS NULL, '', CONCAT(' at ', q.poiname))) AS title,
    c.fuel_type AS driver,
    c.service_type AS project_type,
    q.poiname AS location_text,
    CONCAT('Interconnection request ', c.project, ': DPP-2025 Phase 1 network upgrade cost for ',
           CAST(CAST(ROUND(c.nris_mw) AS INT64) AS STRING), ' MW NRIS / ',
           CAST(CAST(ROUND(c.eris_mw) AS INT64) AS STRING), ' MW ERIS.') AS description,
    q.applicationstatus AS status_raw,
    q.inservice AS in_service_date,
    CAST(NULL AS STRING) AS actual_in_service_date,
    -- ⚠ RAW DOLLARS, like the MTEP feed and unlike PJM's. Third source, third unit convention.
    ROUND(c.total_dpp_2025_phase_1_network_upgrade_cost / 1e6, 2) AS cost_usd_m,
    c.nris_mw AS mw_enabled,
    q.transmissionowner AS owner,
    q.county AS county_raw,
    {norm('q.poiname')} AS poi_nm
  FROM `{DS}.in_miso_dpp2025_ph1_project_costs` c
  JOIN (SELECT projectnumber, ANY_VALUE(county) county, ANY_VALUE(poiname) poiname,
               ANY_VALUE(applicationstatus) applicationstatus,
               ANY_VALUE(transmissionowner) transmissionowner, ANY_VALUE(inservice) inservice
        FROM `{DS}.in_queue_miso_extras` GROUP BY 1) q
    ON q.projectnumber = c.project
),
-- the POI name is often itself an A-to-B corridor ("Gibson Sta - Francisco 345.0kV")
dpp_parts AS (
  SELECT d.project_id, {norm('p')} AS partn, off
  FROM dpp d, UNNEST(REGEXP_EXTRACT_ALL(UPPER(d.location_text), r'{SPLIT}')) AS p WITH OFFSET off
  WHERE d.location_text IS NOT NULL
    AND NOT REGEXP_CONTAINS({norm('p')}, r'{SENTINEL}')
    -- ⛔ 'Other_' is MISO's own placeholder for "the POI is not a named station"
    AND {norm('p')} NOT IN ('OTHER', 'OTHER_')
),
dpp_ends AS (
  SELECT p.project_id,
         ARRAY_AGG(IF(s.lat IS NULL, NULL, STRUCT(s.lat AS lat, s.lon AS lon, p.partn AS nm))
                   IGNORE NULLS ORDER BY p.off LIMIT 4) AS ends,
         COUNTIF(s.nm IS NOT NULL) AS n_sub
  FROM dpp_parts p LEFT JOIN subn s ON s.nm = p.partn
  GROUP BY 1
),
dpp_placed AS (
  SELECT d.source, d.project_id, d.title, d.driver, d.project_type, d.location_text,
         d.description, d.status_raw, d.in_service_date, d.actual_in_service_date,
         d.cost_usd_m, d.mw_enabled, d.owner,
         CAST(NULL AS INT64) AS alloc_n_zones, CAST(NULL AS STRING) AS alloc_top_zone,
         CAST(NULL AS FLOAT64) AS alloc_top_pct, CAST(NULL AS STRING) AS alloc_top5,
         CAST(NULL AS INT64) AS alloc_n_methods,
         CASE WHEN e.n_sub >= 2 THEN (e.ends[OFFSET(0)].lat + e.ends[OFFSET(1)].lat) / 2
              WHEN e.n_sub = 1 THEN e.ends[OFFSET(0)].lat
              ELSE NULL END AS lat,
         CASE WHEN e.n_sub >= 2 THEN (e.ends[OFFSET(0)].lon + e.ends[OFFSET(1)].lon) / 2
              WHEN e.n_sub = 1 THEN e.ends[OFFSET(0)].lon
              ELSE NULL END AS lon,
         CAST(NULL AS FLOAT64) AS place_radius_mi,
         CASE WHEN e.n_sub >= 2 THEN 'corridor_midpoint'
              WHEN e.n_sub = 1 THEN 'corridor_one_end'
              ELSE 'unplaced' END AS loc_method,
         d.county_raw AS county_name,
         IF(e.n_sub >= 2, e.ends[OFFSET(0)].lat, NULL) AS end_a_lat,
         IF(e.n_sub >= 2, e.ends[OFFSET(0)].lon, NULL) AS end_a_lon,
         IF(e.n_sub >= 2, e.ends[OFFSET(1)].lat, NULL) AS end_b_lat,
         IF(e.n_sub >= 2, e.ends[OFFSET(1)].lon, NULL) AS end_b_lon,
         e.ends[SAFE_OFFSET(0)].nm AS anchor_name
  FROM dpp d LEFT JOIN dpp_ends e USING (project_id)
),

-- =============================================================================================
-- ⭐ SOURCE 5 (item 3) - the 774 MISO rows in in_rto_expansion that nothing represented
-- ⚠ A DENOMINATOR AND COST GAP, and the documents said it was ONLY that. Measured: from_endpoint
-- and to_endpoint are NULL on all 774, but `project_name` embeds a station - "Hiple 345 kV
-- interconnection (NIPS-AEP)", "Replace Mount Vernon T3 138/69 kV Transformer", "New Antioch
-- 345 kV Station and Load". So they are partly placeable after all, which is the argument for
-- reading a column instead of counting it.
-- ⛔ 697 of the 774 are M4 - already built. They are carried, classed in_service and default OFF,
-- exactly as PJM's 9,163 in-service rows already are (operator ruling 2026-08-21).
-- ⚠ ONE row shares a project_name with the appendix_a_status feed already loaded above; it is
-- excluded here so the one-row-per-project assertion still holds.
-- =============================================================================================
rtoexp AS (
  SELECT
    'MISO MTEP' AS source,
    CONCAT('RTOX-', CAST(ROW_NUMBER() OVER (ORDER BY x.project_id, x.project_name) AS STRING))
      AS project_id,
    x.project_name AS title,
    x.project_type AS driver, x.project_type AS project_type,
    x.project_name AS location_text,
    x.description,
    x.status AS status_raw,
    x.in_service_date, CAST(NULL AS STRING) AS actual_in_service_date,
    -- ⚠ 'USD (as published)' - raw dollars, like the other MISO feed
    SAFE_CAST(x.cost_raw AS FLOAT64) / 1e6 AS cost_usd_m,
    CAST(NULL AS FLOAT64) AS mw_enabled,
    x.owner
  FROM `{DS}.in_rto_expansion` x
  WHERE x.rto = 'MISO'
    AND x.source_table != 'energy.txexp_miso_mtep_appendix_a_status'
    AND UPPER(TRIM(x.project_name)) NOT IN (
      SELECT UPPER(TRIM(project_name)) FROM `{DS}.in_rto_expansion`
      WHERE source_table = 'energy.txexp_miso_mtep_appendix_a_status'
        AND project_name IS NOT NULL)
),
rtoexp_parts AS (
  SELECT r.project_id, {norm('p')} AS partn, off
  FROM rtoexp r, UNNEST(REGEXP_EXTRACT_ALL(UPPER(r.title), r'{SPLIT}')) AS p WITH OFFSET off
  WHERE r.title IS NOT NULL AND NOT REGEXP_CONTAINS({norm('p')}, r'{SENTINEL}')
),
rtoexp_ends AS (
  SELECT p.project_id,
         ARRAY_AGG(IF(s.lat IS NULL, NULL, STRUCT(s.lat AS lat, s.lon AS lon, p.partn AS nm))
                   IGNORE NULLS ORDER BY p.off LIMIT 4) AS ends,
         COUNTIF(s.nm IS NOT NULL) AS n_sub,
         COUNTIF(s.nm IS NULL AND pl.nm IS NOT NULL) AS n_town,
         ANY_VALUE(IF(s.nm IS NULL, pl.lat, NULL)) AS town_lat,
         ANY_VALUE(IF(s.nm IS NULL, pl.lon, NULL)) AS town_lon,
         ANY_VALUE(IF(s.nm IS NULL, pl.radius_mi, NULL)) AS town_radius,
         COUNTIF(COALESCE(s.nm, pl.nm) IS NULL AND c.county_nm IS NOT NULL) AS n_cty,
         ANY_VALUE(IF(COALESCE(s.nm, pl.nm) IS NULL, c.county_name, NULL)) AS cty_name
  FROM rtoexp_parts p
  LEFT JOIN subn  s  ON s.nm  = p.partn
  LEFT JOIN place pl ON pl.nm = p.partn
  LEFT JOIN cty   c  ON c.county_nm = p.partn
  GROUP BY 1
),
rtoexp_placed AS (
  SELECT r.source, r.project_id, r.title, r.driver, r.project_type, r.location_text,
         r.description, r.status_raw, r.in_service_date, r.actual_in_service_date,
         r.cost_usd_m, r.mw_enabled, r.owner,
         CAST(NULL AS INT64) AS alloc_n_zones, CAST(NULL AS STRING) AS alloc_top_zone,
         CAST(NULL AS FLOAT64) AS alloc_top_pct, CAST(NULL AS STRING) AS alloc_top5,
         CAST(NULL AS INT64) AS alloc_n_methods,
         CASE WHEN e.n_sub >= 2 THEN (e.ends[OFFSET(0)].lat + e.ends[OFFSET(1)].lat) / 2
              WHEN e.n_sub = 1 THEN e.ends[OFFSET(0)].lat
              WHEN e.n_town >= 1 THEN e.town_lat ELSE NULL END AS lat,
         CASE WHEN e.n_sub >= 2 THEN (e.ends[OFFSET(0)].lon + e.ends[OFFSET(1)].lon) / 2
              WHEN e.n_sub = 1 THEN e.ends[OFFSET(0)].lon
              WHEN e.n_town >= 1 THEN e.town_lon ELSE NULL END AS lon,
         e.town_radius AS place_radius_mi,
         CASE WHEN e.n_sub >= 2 THEN 'corridor_midpoint'
              WHEN e.n_sub = 1 THEN 'corridor_one_end'
              WHEN e.n_town >= 1 THEN 'municipality_centroid'
              ELSE 'unplaced' END AS loc_method,
         e.cty_name AS county_name,
         IF(e.n_sub >= 2, e.ends[OFFSET(0)].lat, NULL) AS end_a_lat,
         IF(e.n_sub >= 2, e.ends[OFFSET(0)].lon, NULL) AS end_a_lon,
         IF(e.n_sub >= 2, e.ends[OFFSET(1)].lat, NULL) AS end_b_lat,
         IF(e.n_sub >= 2, e.ends[OFFSET(1)].lon, NULL) AS end_b_lon,
         e.ends[SAFE_OFFSET(0)].nm AS anchor_name
  FROM rtoexp r LEFT JOIN rtoexp_ends e USING (project_id)
),

-- =============================================================================================
unioned AS (
  SELECT * FROM rtep_placed
  UNION ALL SELECT * FROM mtep_placed
  UNION ALL SELECT * FROM plans
  UNION ALL SELECT * FROM dpp_placed
  UNION ALL SELECT * FROM rtoexp_placed
),

-- =============================================================================================
-- ⛔ TWO REFUSALS APPLIED TO EVERY TIER AT ONCE, because both defects below were found in the
-- OUTPUT after each individual tier looked correct - which is the argument for a guard that sits
-- downstream of all of them rather than five guards that each cover one.
--
--   1. OUTSIDE INDIANA. Three upgrades placed into Michigan, Ohio and Wisconsin: `Keystone -
--      Desoto 345 kV` landed at 44.70,-85.62, which is near Traverse City. ⚠ AND THE GAZETTEER
--      WAS NOT AT FAULT - in_substations is clean, 3,659 of 3,659 inside the state box. The bad
--      coordinates came through `in_rtep_bus_join`, which is not clipped to Indiana and which
--      nothing had ever checked, because until this build nothing rendered it. "Indiana only,
--      clipped at the border" is a standing rule and this is where it gets enforced.
--
--   2. A CORRIDOR THAT IS ACTUALLY A LIST. See CORRIDOR_MAX above.
--
-- ⭐ A REFUSED PLACEMENT IS RECORDED, NOT ERASED. `placement_refused` names the reason on the row
-- itself, so the coverage figure can be reconciled against the refusals instead of a reader
-- wondering where a project went.
-- =============================================================================================
instate AS (
  SELECT ST_UNION_AGG(geom) AS g FROM `{EN}.state_boundaries` WHERE STUSPS = 'IN'
),
flagged AS (
  SELECT u.*,
    (u.loc_method = 'corridor_midpoint'
     AND u.end_a_lat IS NOT NULL AND u.end_b_lat IS NOT NULL
     AND ST_DISTANCE(ST_GEOGPOINT(u.end_a_lon, u.end_a_lat),
                     ST_GEOGPOINT(u.end_b_lon, u.end_b_lat)) / 1609.344 > {CORRIDOR_MAX}
    ) AS span_bad,
    (u.lat IS NOT NULL
     AND NOT ST_INTERSECTS(ST_GEOGPOINT(u.lon, u.lat), s.g)) AS out_of_state
  FROM unioned u CROSS JOIN instate s
),
capped AS (
  SELECT
    * EXCEPT(lat, lon, loc_method, end_a_lat, end_a_lon, end_b_lat, end_b_lon,
             span_bad, out_of_state),
    IF(span_bad OR out_of_state, NULL, lat) AS lat,
    IF(span_bad OR out_of_state, NULL, lon) AS lon,
    IF(span_bad OR out_of_state, 'unplaced', loc_method) AS loc_method,
    IF(span_bad OR out_of_state, NULL, end_a_lat) AS end_a_lat,
    IF(span_bad OR out_of_state, NULL, end_a_lon) AS end_a_lon,
    IF(span_bad OR out_of_state, NULL, end_b_lat) AS end_b_lat,
    IF(span_bad OR out_of_state, NULL, end_b_lon) AS end_b_lon,
    CASE WHEN out_of_state THEN 'outside_indiana'
         WHEN span_bad     THEN 'corridor_span_not_credible'
         ELSE NULL END AS placement_refused
  FROM flagged
),
-- last resort: a county centroid, with the county's own radius as the uncertainty
withcty AS (
  SELECT u.*, c.lat AS c_lat, c.lon AS c_lon, c.radius_mi AS c_radius
  FROM capped u
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
    -- ⚠ THE MISO QUEUE VOCABULARY IS ITS OWN. 'Done' means the interconnection agreement is
    -- executed and the project is built - it is NOT a synonym for approved, and letting it fall
    -- to `unclassified` would hide 68 finished projects among the promises.
    WHEN source = 'MISO DPP-2025' AND UPPER(IFNULL(status_raw, '')) = 'DONE' THEN 'in_service'
    WHEN source = 'MISO DPP-2025' AND REGEXP_CONTAINS(UPPER(IFNULL(status_raw, '')),
         r'ACTIVE|PENDING') THEN 'proposed'
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
  in_service_date, actual_in_service_date, cost_usd_m, mw_enabled,
  -- ⭐ ITEM 1: who pays. 26 PJM upgrades carry a published zone allocation.
  alloc_n_zones, alloc_top_zone, alloc_top_pct, alloc_top5, alloc_n_methods,
  county_name, anchor_name,
  -- ⭐ NULL unless a placement was REFUSED, and then it names the reason on the row itself
  placement_refused,
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
    -- ⭐ MEASURED, NOT ASSUMED: the place's own equal-area radius plus a {MUNI_MARGIN} mi margin,
    -- which contains 86.7% of the 2,691 substation-to-town cases against 83.0% for the flat 5.0
    -- it replaces - and unlike the constant, it scales with the town. Where TIGER did not supply
    -- a radius (the 27 unincorporated by-product names) the old constant still applies, because
    -- inventing a radius for a place with no polygon would be worse than reusing a known one.
    WHEN loc_method = 'municipality_centroid' THEN
      IF(place_radius_mi IS NULL, 5.0, ROUND(place_radius_mi + {MUNI_MARGIN}, 1))
    WHEN loc_method = 'unplaced' AND c_lat IS NOT NULL THEN c_radius
    ELSE NULL
  END AS uncertainty_mi,
  CASE
    WHEN loc_method = 'verified_asset_match'  THEN 'Joined to a substation we hold and corroborated by a bus — a known position, not an estimate'
    WHEN loc_method = 'substation_match'      THEN 'Joined to the one substation of that name we hold — a known position, not an estimate'
    WHEN loc_method = 'corridor_midpoint'     THEN 'Both ends of the line name resolve — midpoint of the corridor'
    WHEN loc_method = 'corridor_one_end'      THEN 'One end of the line name resolves — the work is off that station'
    -- ⚠ NO APOSTROPHE IN THIS STRING. BigQuery does not read '' as an escaped quote the way
    -- ANSI SQL does - it reads two adjacent string literals and fails to parse. Rephrased rather
    -- than backslash-escaped, because the escape is the thing a later edit silently breaks.
    WHEN loc_method = 'municipality_centroid' THEN 'Town centroid — NOT the asset site. The ring is the radius of that town plus a measured margin'
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
         COUNTIF(status_class IN ('proposed','approved','filed_plan')) future
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

# ⭐ ITEM 6, RE-MEASURED RATHER THAN REMEMBERED. It fired 0 times in the first build because no
# source published a county. The MISO queue does, so the tier is now fed - but the number is read
# from the artefact, never asserted.
cc = list(client.query(f"""
  SELECT COUNTIF(loc_method = 'county_centroid') n,
         COUNT(DISTINCT IF(loc_method = 'county_centroid', county_name, NULL)) counties
  FROM `{OUT}`"""))[0]
if cc.n:
    print(f"\n  ⭐ county_centroid now fires {cc.n} time(s) across {cc.counties} counties — the "
          f"tier was wired and unfed until a county-bearing source arrived (item 6)")
else:
    print("\n  ⚠ county_centroid still fires 0 times — the tier is wired and unfed, and is "
          "reported, not hidden")

# ⭐ ITEM 1 - the cost attribution, stated as UPGRADES rather than as rows
al = list(client.query(f"""
  SELECT COUNTIF(alloc_n_zones IS NOT NULL) upg, SUM(alloc_n_zones) zone_rows
  FROM `{OUT}`"""))[0]
print(f"  ⭐ cost allocation attached to {al.upg} upgrade(s) across {al.zone_rows or 0} zone "
      f"shares — the source's 375 ROWS are 26 UPGRADES, and the card must say 26")

# ⭐ COVERAGE STATED TWICE (operator ruling 2026-08-21): the total, and the future-only figure a
# siter actually wants. Reporting only the first makes already-built steel look like a promise.
s = list(client.query(f"""
  SELECT COUNT(*) n, COUNTIF(lat IS NOT NULL) placed,
         COUNTIF(status_class IN ('proposed','approved','filed_plan')) future,
         COUNTIF(lat IS NOT NULL AND status_class IN ('proposed','approved','filed_plan'))
           future_placed,
         COUNTIF(status_class = 'in_service') built,
         COUNTIF(end_a_lat IS NOT NULL AND end_b_lat IS NOT NULL) corridors
  FROM `{OUT}`"""))[0]
print(f"\n  ⭐ ALL planned items:    {s.placed:,} of {s.n:,} carry a position "
      f"({100 * s.placed / s.n:.1f}%)")
print(f"  ⭐ STILL TO COME only:  {s.future_placed:,} of {s.future:,} "
      f"({100 * s.future_placed / s.future:.1f}%) — the figure a siter wants")
print(f"  ⚠ already built and OFF by default: {s.built:,}")
print(f"  ⭐ {s.corridors:,} resolve BOTH ends and can be drawn as a corridor, not a dot")

# ⛔ THE REFUSALS, REPORTED OUT LOUD. A guard that silently drops rows is indistinguishable from
# data we never had, and this project has already paid for that once.
for r in client.query(f"""
  SELECT placement_refused, COUNT(*) n FROM `{OUT}`
  WHERE placement_refused IS NOT NULL GROUP BY 1 ORDER BY 2 DESC"""):
    print(f"  ⛔ REFUSED {r.n:>3}: {r.placement_refused}")

# ⛔ INDIANA ONLY, ASSERTED ON THE ARTEFACT. This is the check that would have caught the three
# out-of-state placements before they reached a map, and it did not exist until they did.
oos = list(client.query(f"""
  SELECT COUNTIF(lat IS NOT NULL
                 AND NOT (lat BETWEEN 37.7 AND 41.8 AND lon BETWEEN -88.2 AND -84.7)) n
  FROM `{OUT}`"""))[0].n
assert oos == 0, f"{oos} placement(s) outside the Indiana box - the border clip is not holding"
print("  ⭐ every placement is inside Indiana (0 outside the state box)")

# ⛔ INDIANA ONLY, ASSERTED. The DPP source table is 14 states and the operator ruled Indiana
# only; if a future re-clip widens it, this fails loudly rather than shipping other states.
dq = list(client.query(f"""
  SELECT COUNT(*) n, ROUND(SUM(cost_usd_m)) cost, ROUND(SUM(mw_enabled)) mw
  FROM `{OUT}` WHERE source = 'MISO DPP-2025'"""))[0]
assert dq.n <= 25, (f"MISO DPP-2025 loaded {dq.n} projects; Indiana had 21 of the published 202. "
                    f"A jump means the Indiana filter stopped filtering.")
print(f"\n  ⭐ MISO DPP-2025, INDIANA ONLY: {dq.n} projects, ${dq.cost:,.0f}M, {dq.mw:,.0f} MW "
      f"(${1000 * dq.cost / dq.mw:,.0f}k per MW)")
print(f"  ⛔ the published table is 14 states / $29,522M — that total is NOT Indiana's and is "
      f"not carried")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_planned_upgrades',
 'indiana_app.in_pjm_rtep_upgrades + in_pjm_rtep_upgrade_details + in_rtep_bus_join + '
 'in_pjm_rtep_cost_allocations x indiana_app.in_txexp_miso_mtep_appendix_a_status x '
 'indiana_app.in_rto_expansion (MISO rows outside appendix A status) x '
 'indiana_app.in_miso_dpp2025_ph1_project_costs x in_queue_miso_extras (project -> county/POI) x '
 'indiana_app.in_grid_plans_located x indiana_app.in_substations + in_places (gazetteers) x '
 'energy.county_boundaries (county centroids)',
 'One row per PLANNED grid upgrade, placed by a tiered method and carrying an uncertainty radius. '
 'Tiers: verified_asset_match and substation_match carry NO ring (a known position must not look '
 'guessed); corridor_midpoint half the span; corridor_one_end 3 mi; municipality_centroid the '
 'TIGER place radius + 4.0 mi (MEASURED: 86.7% containment over 2,691 substation-to-town cases, '
 'against 83.0% for the flat 5.0 mi it replaces); county_centroid the county equal-area radius; '
 'else unplaced and never drawn. Names are matched after NORMALISATION - a kV token and the words '
 'SUBSTATION/STATION/SUB/SWITCHING STATION/TAP are stripped from both sides - and TBD/N-A/CEII '
 'sentinels are refused outright. A-to-B corridor names split on hyphen, EN DASH, EM DASH, slash, '
 'comma and U+FFFD (an upstream mojibake en dash). A name resolving to more than one substation '
 'is NOT used. status_class separates proposed / approved / filed_plan / in_service / cancelled; '
 'in_service is already built and is NOT future capacity, so coverage is published TWICE - a '
 'total and a still-to-come figure. MISO DPP-2025 is INDIANA ONLY (21 of the published 202; the '
 'source spans 14 states and its $29,522M headline is not Indiana s). '
 'RE-SCRAPE COMMAND: python scripts/build_planned_upgrades.py',
 {n}, {gb}, CURRENT_TIMESTAMP(),
 'G130 items 1-7, operator 2026-08-20f and 2026-08-21. Before this build 119 of 618 utility grid '
 'plans were the ONLY planned work on the map and were drawn as plain circles like existing '
 'assets; 287 PJM RTEP upgrades were already placed in in_rtep_bus_join and NOTHING rendered '
 'them. This revision adds PJM cost allocation (26 upgrades), MISO DPP-2025 Indiana costs, the '
 '774 MISO rows in_rto_expansion held and nothing represented, the TIGER PLACE gazetteer, '
 'normalised name matching and the county tier. DEPENDS ON in_places - run '
 'scripts/load_tiger_place.py first. IDEMPOTENCY: replace_safe. CADENCE: quarterly (RTO planning '
 'cycles); the IURC grid-plan dockets are event-driven.'
)""").result()
print("\n  _registry row written")
print("PLANNED UPGRADES COMPLETE")
