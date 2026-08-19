"""G88 - county posture: how many data centres are HERE, how many are COMING, and who serves them.

    python scripts/build_dc_county_posture.py

Operator, 2026-08-19: *"For county posture, instead of having queued MW, we should put the number
of DC developments that are either completed/in progress (maybe one field for each), and the
utility should be able to be determined."*

⭐ QUEUED MW DESERVES TO GO, and the measurement says so. It is an INTERCONNECTION-QUEUE figure
standing in for development activity, and G35 measured that 49 of 87 counties have had >=50% of
everything ever queued WITHDRAWN. It overstates by construction.

⛔ "COMPLETED VS IN PROGRESS" CANNOT COME FROM THE DATA-CENTRE DIRECTORIES, and that is worth
stating plainly rather than faking. `in_data_centers_located` has no status, stage or
under-construction column at all - baxtel, datacentermap, OSM and PeeringDB list FACILITIES, not
construction stages. So the two counts come from two DIFFERENT sources and mean two different
things, and the surface must not merge them:

  dc_listed    a facility a directory lists in this county TODAY. Closest thing we hold to
               "completed". ⚠ It is a directory listing, not a certificate of occupancy.
  dc_approved  a county/municipal body has APPROVED one (confirmed_action_type
               'approval-permissive'), verified at the official source. Closest thing to
               "in progress" - the permission exists, the building may not.
  dc_proposed  filed and pending ('proposed' / 'petition-pending'). Not yet permitted.

⚠ AND THE NEGATIVE CASES ARE CARRIED TOO (dc_denied, dc_withdrawn). A county that has denied three
data centres and approved none is telling a developer something load-bearing, and a posture panel
that only counts successes hides it.

⚠ 92 OF 249 PINS ARE CITY CENTROIDS, so `dc_listed_city_precision` rides beside every count. A
county whose four data centres are four gazetteer points near one town square has a very different
evidence base from one with four surveyed coordinates, and the number alone cannot distinguish
them. ⛔ The count must never be shown without it.

⛔ SERVING UTILITY IS **NOT** RANKED BY AREA, AND THE FIRST VERSION OF THIS SCRIPT PROVED WHY.
`in_territories` is not an exclusive partition of the state: 145 polygons sum to **191,328 km2
over a state of ~94,300 km2 - 2.03x the land** - because they are overlapping service-area
ENVELOPES, not carved franchises. Ranking Allen County by intersection area returned NOBLE COUNTY
REMC at "100.0%", ahead of Indiana Michigan Power, in the county that contains Fort Wayne. Three
utilities each intersect ~1,707 km2 of Allen's 1,707 km2, so area cannot separate them at all and
the winner was whichever sorted first.

The rule is therefore: among utilities whose envelope covers **>=50% of the county**, the primary
is the **largest by published customer count**; every intersecting utility is still carried with
its share, and `n_utilities_covering_half` exposes how ambiguous the answer was. Slivers under 1%
of county area are dropped as boundary noise. After the fix Allen reads Indiana Michigan Power,
St. Joseph I&M, Lake/LaPorte/Porter NIPSCO, Marion IPL, Clark/Hendricks Duke.

Reads `bigquery-public-data.geo_us_boundaries` (public, not `energy`) + indiana_app.
WRITES `indiana_app.in_dc_county_posture`.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_dc_county_posture"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH cty AS (
  SELECT geo_id AS county_geoid, county_name, county_geom AS g
  FROM `bigquery-public-data.geo_us_boundaries.counties`
  WHERE state_fips_code = '18'
),
dc AS (
  SELECT c.county_geoid,
         COUNT(*)                                        AS dc_listed,
         COUNTIF(d.location_precision = 'city')          AS dc_listed_city_precision,
         COUNTIF(d.location_precision = 'site')          AS dc_listed_site_precision,
         ARRAY_AGG(DISTINCT d.operator IGNORE NULLS ORDER BY d.operator LIMIT 12) AS operators
  FROM cty c
  JOIN `{DS}.in_data_centers_located` d
    ON d.lat IS NOT NULL AND d.lon IS NOT NULL
   AND ST_CONTAINS(c.g, ST_GEOGPOINT(d.lon, d.lat))
  GROUP BY 1
),
act AS (
  -- ⛔ posture_renderable only. An action that is not VERIFIED_AT_OFFICIAL_SOURCE must never
  -- reach a count a reader treats as fact -- news is a lead, never a verification.
  SELECT TRIM(county) AS county_name,
         COUNTIF(confirmed_action_type = 'approval-permissive')              AS dc_approved,
         COUNTIF(confirmed_action_type IN ('proposed', 'petition-pending'))  AS dc_proposed,
         COUNTIF(confirmed_action_type = 'denied')                           AS dc_denied,
         COUNTIF(confirmed_action_type = 'withdrawn')                        AS dc_withdrawn
  FROM `{DS}.in_dc_actions_resolved`
  WHERE posture_renderable
  GROUP BY 1
),
terr AS (
  SELECT c.county_geoid, t.utility, t.utility_type, t.customers,
         SAFE_DIVIDE(ST_AREA(ST_INTERSECTION(c.g, t.geog)), NULLIF(ST_AREA(c.g), 0)) AS share
  FROM cty c
  JOIN `{DS}.in_territories` t ON ST_INTERSECTS(c.g, t.geog)
),
terr_agg AS (
  /* ⛔ DO NOT RANK BY AREA SHARE. MEASURED 2026-08-19b: these polygons are NOT an exclusive
     partition of the state. 145 territories sum to 191,328 km2 over a state of ~94,300 -- 2.03x
     the land -- because they are service-area ENVELOPES that overlap, not carved franchises.

     The first version of this build ranked by intersection area and put NOBLE COUNTY REMC at
     "100.0%" of Allen County, ahead of Indiana Michigan Power. Allen County is Fort Wayne and I&M
     serves it. The number was not wrong; the QUESTION was. Three utilities each intersect ~1,707
     km2 of Allen's 1,707 km2, so "share of county area" cannot separate them and the winner was
     whichever happened to sort first.

     The honest discriminator among utilities that all blanket the county is SIZE: `customers` is
     published per utility on this table. So the primary is the largest by customer count among
     those whose envelope covers at least half the county, and the full overlapping list is kept
     with its shares so a reader can see the ambiguity rather than inherit our tiebreak. */
  SELECT county_geoid,
         ARRAY_AGG(STRUCT(utility, utility_type, customers,
                          ROUND(share * 100, 1) AS pct_of_county)
                   ORDER BY share DESC, customers DESC) AS utilities,
         ARRAY_AGG(utility ORDER BY IF(share >= 0.5, 1, 0) DESC,
                                    customers DESC, share DESC LIMIT 1)[OFFSET(0)]
           AS primary_utility,
         ROUND(MAX(IF(share >= 0.5, share, NULL)) * 100, 1) AS primary_utility_pct,
         COUNT(*) AS n_utilities,
         COUNTIF(share >= 0.5) AS n_utilities_covering_half
  FROM terr
  WHERE share >= 0.01        -- boundary slivers are not service territory
  GROUP BY 1
)
SELECT
  c.county_geoid, c.county_name,
  IFNULL(dc.dc_listed, 0)                    AS dc_listed,
  IFNULL(dc.dc_listed_city_precision, 0)     AS dc_listed_city_precision,
  IFNULL(dc.dc_listed_site_precision, 0)     AS dc_listed_site_precision,
  dc.operators,
  IFNULL(a.dc_approved, 0)                   AS dc_approved,
  IFNULL(a.dc_proposed, 0)                   AS dc_proposed,
  IFNULL(a.dc_denied, 0)                     AS dc_denied,
  IFNULL(a.dc_withdrawn, 0)                  AS dc_withdrawn,
  t.primary_utility, t.primary_utility_pct, t.n_utilities, t.n_utilities_covering_half,
  t.utilities
FROM cty c
LEFT JOIN dc ON dc.county_geoid = c.county_geoid
LEFT JOIN act a ON a.county_name = c.county_name
LEFT JOIN terr_agg t ON t.county_geoid = c.county_geoid
ORDER BY dc_listed DESC, c.county_name
"""

print("building in_dc_county_posture ...")
job = client.query(SQL)
job.result()
gb = round((job.total_bytes_processed or 0) / 1e9, 3)
n = list(client.query(f"SELECT COUNT(*) c FROM `{OUT}`"))[0].c
print(f"  {n} counties, {gb} GB scanned\n")

# ⚠ THE JOIN IS BY COUNTY NAME and that is the risky part of this build -- 'LaPorte' vs
# 'La Porte', 'St. Joseph' vs 'St Joseph'. Prove it landed rather than assuming.
unmatched = list(client.query(f"""
  SELECT DISTINCT TRIM(county) AS county
  FROM `{DS}.in_dc_actions_resolved` WHERE posture_renderable
    AND TRIM(county) NOT IN (SELECT county_name FROM `{OUT}`)"""))
print(f"action counties that did NOT match a county row: {len(unmatched)}")
for u in unmatched:
    print(f"   ⛔ {u.county!r}")

tot = list(client.query(f"""
  SELECT SUM(dc_listed) l, SUM(dc_listed_city_precision) cp, SUM(dc_approved) ap,
         SUM(dc_proposed) pr, SUM(dc_denied) dn, SUM(dc_withdrawn) wd,
         COUNTIF(dc_listed > 0) c_listed, COUNTIF(dc_approved > 0) c_appr,
         COUNTIF(primary_utility IS NULL) c_noutil
  FROM `{OUT}`"""))[0]
print(f"\nlisted data centres placed : {tot.l} ({tot.cp} of them city-precision) "
      f"across {tot.c_listed} counties")
print(f"approved / proposed        : {tot.ap} / {tot.pr}  (denied {tot.dn}, withdrawn {tot.wd})")
print(f"counties with no utility resolved: {tot.c_noutil}")

print("\ntop counties:")
for r in client.query(f"""SELECT county_name, dc_listed, dc_listed_city_precision cp, dc_approved,
                                 dc_proposed, dc_denied, primary_utility, primary_utility_pct,
                                 n_utilities, n_utilities_covering_half
                          FROM `{OUT}` ORDER BY dc_listed DESC, dc_approved DESC LIMIT 12"""):
    print(f"  {r.county_name:14s} listed={r.dc_listed:3d} (city {r.cp:2d})  appr={r.dc_approved} "
          f"prop={r.dc_proposed} den={r.dc_denied}  "
          f"{str(r.primary_utility)[:26]:28s} {r.n_utilities_covering_half} blanket / {r.n_utilities} touch")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_dc_county_posture',
 'indiana_app.in_data_centers_located + in_dc_actions_resolved + in_territories, counties from '
 'bigquery-public-data.geo_us_boundaries.counties (state_fips_code=18)',
 'listed data centres placed by ST_CONTAINS on the county polygon (NOT a name match); approved / '
 'proposed / denied / withdrawn counted from VERIFIED actions only (posture_renderable), joined '
 'by county name with the unmatched set asserted to be empty; serving utilities by '
 'ST_INTERSECTION with the county, slivers under 1% dropped. PRIMARY IS BY CUSTOMER COUNT among '
 'utilities covering >=50% of the county, NOT by area: the territory polygons OVERLAP (145 sum '
 'to 191,328 km2 over a ~94,300 km2 state), so area cannot separate two that both blanket it. '
 'RE-SCRAPE COMMAND: python scripts/build_dc_county_posture.py',
 {n}, {gb}, CURRENT_TIMESTAMP(),
 'G88. Replaces queued MW, which G35 showed overstates by construction (49 of 87 counties have '
 '>=50% of everything ever queued withdrawn). dc_listed and dc_approved come from DIFFERENT '
 'sources and must not be summed. dc_listed_city_precision must be shown beside dc_listed - the '
 'directories give 92 of 249 pins only city-centroid precision.'
)""").result()
print("\n  _registry row written")
print("DC COUNTY POSTURE COMPLETE")
