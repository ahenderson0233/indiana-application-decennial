"""G120(b) + G120(e) - the two parcel-attribution defects the operator hit on real sites.

    python scripts/build_parcel_assembly.py [--dry]

Operator, from prospecting against a real list:
  (b) *"some of the addresses are attaching to the roadway, not the actual building"*
  (e) *"A site location is showing a C&I parcel, but has a sliver, or a couple of other parcels
      that are seemingly attached to that property that aren't being applied to the site."*

⭐ (b) IS THE ROOT CAUSE OF THE RETAIL-STORE REPORT AND IT IS A DIFFERENT BUG FROM (a).
G120(a) established that `structure_count` is FAITHFUL and the corpus is simply six years old.
That explains a NEW building reading as empty. It does not explain a 1990s retail store reading
as empty - and (b) does: the geocode lands on the ROAD, the road is its own right-of-way parcel,
that parcel genuinely has no building, and the tool answers correctly about the WRONG PARCEL.
The reader cannot tell those two failures apart, and the fix is different for each.

TWO THINGS ARE COMPUTED, both per candidate parcel:

  1. ROW-LIKE SHAPE. A road right-of-way is a ribbon: enormous perimeter for its area. The
     isoperimetric quotient 4*pi*A / P^2 is 1.0 for a circle, about 0.78 for a square, and
     collapses toward 0 as a polygon gets thinner. Combined with "no structure" and a road
     actually crossing it, that is a defensible ROW test.
     ⚠ IT IS A HEURISTIC AND IS LABELLED AS ONE. `rowlike_confidence` is 'high' only when the
     shape test AND a road-on-parcel test AND no-structure all agree. A creek, a rail spur and a
     pipeline easement are also ribbons, so shape alone says 'shape_only'.
     ⛔ We hold only PRIMARY and SECONDARY roads (225 + 861 features) - not local streets - so a
     ribbon parcel along a residential street cannot be confirmed by road geometry. That is a
     coverage limit, not a negative finding, and 'shape_only' is what it renders as.

  2. THE ASSEMBLY. Every parcel that physically TOUCHES the candidate, with how many acres and
     how many buildings they add. A 40-acre campus is rarely one parcel, and the operator is
     right that the tool was answering about one rectangle when the site is three.
     ⭐ AND IT IS THE OTHER HALF OF (b): if the point landed on a right-of-way, the parcel with
     the building is almost always a NEIGHBOUR - so `nearest_structured_key` is the answer to
     "you meant this one".

⛔ WHAT AN ASSEMBLY IS NOT. Touching does not mean co-owned. Indiana parcel owner is NULL on all
3,553,381 rows outside Marion County, so this CANNOT say "the same person owns both". It says
"these parcels adjoin, here is what they would add if you could buy them", which is a
different and weaker claim, and `assembly_basis` records that it is adjacency only.

⚠ D85 (`parcels_in/080500000047000018`) excluded on BOTH sides of the self-join. Left in, it
touches every parcel in Indiana and every site becomes a 3.5-million-parcel assembly.

WRITES `indiana_app.in_parcel_assembly`. Reads indiana_app only.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_parcel_assembly"
D85 = "080500000047000018"
DRY = "--dry" in _sys.argv
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH cand AS (
  SELECT c.parcel_source, c.parcel_key, c.county_fips, c.county_name, c.occ_group,
         c.structure_count, c.parcel_acres, c.lat, c.lon,
         s.parcel_geog AS g
  FROM `{DS}.in_screener_candidates` c
  JOIN `{DS}.in_sites` s USING (parcel_source, parcel_key)
  WHERE c.parcel_key != '{D85}'
),
-- ---- 1. shape ------------------------------------------------------------------------------
shaped AS (
  SELECT *,
         ST_AREA(g)      AS area_m2,
         ST_PERIMETER(g) AS perim_m
  FROM cand
),
compact AS (
  SELECT *,
         -- isoperimetric quotient: 1.0 = circle, ~0.78 = square, -> 0 as the polygon thins out
         SAFE_DIVIDE(4 * ACOS(-1) * area_m2, POW(NULLIF(perim_m, 0), 2)) AS compactness
  FROM shaped
),
-- roads we actually hold: TIGER primary + secondary only. Local streets are NOT held, so a
-- ribbon parcel that no road crosses is unconfirmed, never "confirmed not a road".
-- ⚠ the geometry column on these two is `geom`, not `geog` like everywhere else in the estate.
roads AS (
  SELECT geom AS g FROM `{DS}.in_roads_primary`   WHERE geom IS NOT NULL
  UNION ALL
  SELECT geom AS g FROM `{DS}.in_roads_secondary` WHERE geom IS NOT NULL
),
road_hit AS (
  SELECT c.parcel_source, c.parcel_key, COUNT(*) > 0 AS road_crosses
  FROM compact c JOIN roads r ON ST_INTERSECTS(c.g, r.g)
  GROUP BY 1, 2
),
-- ---- 2. the assembly -------------------------------------------------------------------------
-- ⚠ ST_DWITHIN(.., 1.0) rather than ST_TOUCHES: parcel corpora carry small gaps at shared
--    boundaries from coordinate rounding, and a strict TOUCHES misses most real neighbours.
--    1 metre is well inside any real setback and cannot bridge a street.
-- ⛔ "TOTAL ACRES OF EVERYTHING THAT TOUCHES" IS A USELESS NUMBER AND THE FIRST BUILD PROVED IT:
--    with a mean of 8 neighbours, 521,312 of 532,693 candidates (98%) "could more than double
--    their acreage". A statistic true of 98% of the corpus tells a siter nothing - it is volume
--    standing in for value, which the governing principle vetoes. Three narrower measures are
--    kept instead, each answering a question someone would actually ask:
--      sliver_*      the operator's own words: "a sliver ... attached to that property". Under
--                    half an acre, so almost certainly part of the same holding.
--      same_class_*  an assembly a developer would actually attempt: adjoining land of the SAME
--                    character (C&I next to C&I, open ground next to open ground).
--      largest_*     the single biggest adjoining parcel, which is what moves a site over a
--                    threshold - eight quarter-acre neighbours do not.
nbr AS (
  SELECT c.parcel_source, c.parcel_key,
         COUNT(*)                                          AS neighbours,
         ROUND(SUM(n.parcel_acres), 2)                     AS neighbour_acres,
         COUNTIF(n.structure_count > 0)                    AS neighbours_with_structure,
         ROUND(SUM(IF(n.occ_group = 'ci', n.parcel_acres, 0)), 2) AS neighbour_ci_acres,
         COUNTIF(n.parcel_acres < 0.5)                     AS sliver_neighbours,
         ROUND(SUM(IF(n.parcel_acres < 0.5, n.parcel_acres, 0)), 3) AS sliver_acres,
         COUNTIF(n.occ_group = c.occ_group)                AS same_class_neighbours,
         ROUND(SUM(IF(n.occ_group = c.occ_group, n.parcel_acres, 0)), 2) AS same_class_acres,
         ROUND(MAX(n.parcel_acres), 2)                     AS largest_neighbour_acres
  FROM compact c
  JOIN `{DS}.in_sites` n
    ON n.parcel_key != '{D85}'
   AND NOT (n.parcel_source = c.parcel_source AND n.parcel_key = c.parcel_key)
   AND ST_DWITHIN(c.g, n.parcel_geog, 1.0)
  GROUP BY 1, 2
),
-- ⭐ the "you meant this one" answer: nearest parcel WITH a building, within 150 m
near_struct AS (
  SELECT c.parcel_source, c.parcel_key,
         ARRAY_AGG(STRUCT(n.parcel_key AS k, n.occ_group AS og, n.parcel_acres AS ac,
                          n.structure_count AS sc, ST_DISTANCE(c.g, n.parcel_geog) AS m)
                   ORDER BY ST_DISTANCE(c.g, n.parcel_geog) LIMIT 1)[OFFSET(0)] AS w
  FROM compact c
  JOIN `{DS}.in_sites` n
    ON n.parcel_key != '{D85}'
   AND n.structure_count > 0
   AND NOT (n.parcel_source = c.parcel_source AND n.parcel_key = c.parcel_key)
   AND ST_DWITHIN(c.g, n.parcel_geog, 150.0)
  WHERE c.structure_count = 0            -- only asked when the parcel itself looks empty
  GROUP BY 1, 2
)
SELECT
  c.parcel_source, c.parcel_key, c.county_fips, c.county_name,
  ROUND(c.area_m2)   AS area_m2,
  ROUND(c.perim_m)   AS perimeter_m,
  ROUND(c.compactness, 4) AS compactness,
  IFNULL(rh.road_crosses, FALSE) AS road_crosses,
  -- the classifier, three-state by construction
  CASE
    WHEN c.compactness < 0.10 AND c.structure_count = 0 AND IFNULL(rh.road_crosses, FALSE)
      THEN 'high'
    WHEN c.compactness < 0.10 AND c.structure_count = 0 THEN 'shape_only'
    WHEN c.compactness < 0.18 AND c.structure_count = 0 THEN 'possible'
    ELSE 'no'
  END AS rowlike_confidence,
  IFNULL(n.neighbours, 0)                 AS neighbours,
  IFNULL(n.neighbour_acres, 0)            AS neighbour_acres,
  IFNULL(n.neighbours_with_structure, 0)  AS neighbours_with_structure,
  IFNULL(n.neighbour_ci_acres, 0)         AS neighbour_ci_acres,
  IFNULL(n.sliver_neighbours, 0)          AS sliver_neighbours,
  IFNULL(n.sliver_acres, 0)               AS sliver_acres,
  IFNULL(n.same_class_neighbours, 0)      AS same_class_neighbours,
  IFNULL(n.same_class_acres, 0)           AS same_class_acres,
  n.largest_neighbour_acres,
  -- the assembly a developer would actually attempt: this parcel plus adjoining land of the
  -- SAME character, not plus everything that happens to share a boundary.
  ROUND(c.parcel_acres + IFNULL(n.same_class_acres, 0), 2) AS assembly_acres_same_class,
  ROUND(c.parcel_acres + IFNULL(n.neighbour_acres, 0), 2)  AS assembly_acres_all_neighbours,
  'adjacency only - Indiana parcel owner is NULL outside Marion, so common ownership is NOT '
  'established' AS assembly_basis,
  ns.w.k  AS nearest_structured_key,
  ns.w.og AS nearest_structured_occ_group,
  ns.w.ac AS nearest_structured_acres,
  ROUND(ns.w.m, 1) AS nearest_structured_m,
  CURRENT_TIMESTAMP() AS built_at
FROM compact c
LEFT JOIN road_hit    rh USING (parcel_source, parcel_key)
LEFT JOIN nbr         n  USING (parcel_source, parcel_key)
LEFT JOIN near_struct ns USING (parcel_source, parcel_key)
"""

cfg = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
dry = client.query(SQL, job_config=cfg)
gib = dry.total_bytes_processed / 2**30
print(f"DRY RUN: {gib:.1f} GiB  ->  approx ${gib * 5 / 1024:.2f}")
if DRY:
    _sys.exit(0)
if gib > 6000:
    print("⛔ over the $25 cost flag - stopping. Re-run deliberately if this is intended.")
    _sys.exit(1)

print("building in_parcel_assembly ...")
job = client.query(SQL)
job.result()
gb = round((job.total_bytes_processed or 0) / 1e9, 3)

s = list(client.query(f"""
  SELECT COUNT(*) n, COUNT(DISTINCT FORMAT('%s|%s', parcel_source, parcel_key)) d
  FROM `{OUT}`"""))[0]
print(f"  {s.n:,} rows over {s.d:,} parcels -> fan-out {s.n / max(s.d,1):.3f}")
assert s.n == s.d, "FAN-OUT: the self-join multiplied rows"

print("\n  ⭐ (b) ROAD RIGHT-OF-WAY CLASSIFIER:")
for r in client.query(f"""SELECT rowlike_confidence, COUNT(*) n,
                                 ROUND(AVG(compactness), 3) avg_compact,
                                 COUNTIF(road_crosses) with_road,
                                 COUNTIF(nearest_structured_key IS NOT NULL) can_redirect
                          FROM `{OUT}` GROUP BY 1
                          ORDER BY CASE rowlike_confidence WHEN 'high' THEN 1 WHEN 'shape_only'
                                   THEN 2 WHEN 'possible' THEN 3 ELSE 4 END"""):
    print(f"    {r.rowlike_confidence:12s} {r.n:>7,} parcels  mean compactness {r.avg_compact}  "
          f"road crosses {r.with_road:>6,}  can point at a built parcel {r.can_redirect:>7,}")

print("\n  ⭐ (b) THE REDIRECT - empty parcels with a built parcel next door:")
for r in client.query(f"""SELECT
        COUNTIF(nearest_structured_key IS NOT NULL) redirectable,
        COUNTIF(nearest_structured_m <= 10) within_10m,
        COUNTIF(nearest_structured_m <= 30) within_30m,
        ROUND(APPROX_QUANTILES(nearest_structured_m, 2)[OFFSET(1)], 1) median_m
      FROM `{OUT}` WHERE nearest_structured_key IS NOT NULL"""):
    print(f"    {r.redirectable:,} empty parcels have a built parcel within 150 m "
          f"({r.within_10m:,} within 10 m, {r.within_30m:,} within 30 m, median {r.median_m} m)")

print("\n  ⭐ (e) THE ASSEMBLY - narrow measures, because the wide one was true of 98%:")
for r in client.query(f"""SELECT
        COUNTIF(neighbours > 0) with_nbrs,
        ROUND(AVG(neighbours), 1) avg_nbrs,
        COUNTIF(sliver_neighbours > 0) with_sliver,
        ROUND(AVG(IF(sliver_neighbours > 0, sliver_neighbours, NULL)), 1) avg_slivers,
        COUNTIF(same_class_neighbours > 0) same_class,
        COUNTIF(same_class_acres > parcel_acres_proxy) same_class_doubles,
        COUNTIF(largest_neighbour_acres >= 25) big_nbr
      FROM (SELECT a.*, s.parcel_acres AS parcel_acres_proxy
            FROM `{OUT}` a JOIN `{DS}.in_screener_candidates` s
            USING (parcel_source, parcel_key))"""):
    print(f"    {r.with_nbrs:,} candidates adjoin another parcel (mean {r.avg_nbrs})")
    print(f"    {r.with_sliver:,} have a SLIVER attached - the operator's own case "
          f"(mean {r.avg_slivers} each, under half an acre)")
    print(f"    {r.same_class:,} adjoin land of the SAME character; {r.same_class_doubles:,} "
          f"would more than double on same-class land alone")
    print(f"    {r.big_nbr:,} have one adjoining parcel of 25+ acres - the neighbour that moves "
          f"a site over a threshold")

print("\n  the most extreme ribbons (these are the geocode traps):")
for r in client.query(f"""SELECT county_name, parcel_key, area_m2, perimeter_m, compactness,
                                 road_crosses, nearest_structured_m
                          FROM `{OUT}` WHERE rowlike_confidence = 'high'
                          ORDER BY compactness ASC LIMIT 8"""):
    print(f"    {str(r.county_name)[:14]:14s} {r.parcel_key[:20]:20s} "
          f"{r.area_m2:>9,.0f} m2  perimeter {r.perimeter_m:>8,.0f} m  "
          f"compactness {r.compactness:.4f}  built parcel {r.nearest_structured_m} m away")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_parcel_assembly',
 'indiana_app.in_screener_candidates x indiana_app.in_sites (self-join for adjacency) x '
 'indiana_app.in_roads_primary + in_roads_secondary',
 'Two computations per candidate parcel. (1) Road-right-of-way likelihood from the isoperimetric '
 'quotient 4*pi*area/perimeter^2, combined with structure_count = 0 and whether a held road '
 'actually crosses the polygon; graded high / shape_only / possible / no, never a bare boolean, '
 'because only PRIMARY and SECONDARY roads are held and a local street cannot confirm. '
 '(2) Adjacency assembly via ST_DWITHIN(1.0 m) rather than ST_TOUCHES, because parcel corpora '
 'carry rounding gaps at shared boundaries; plus the nearest parcel WITH a structure within '
 '150 m, which is the redirect for a geocode that landed on a road. D85 excluded on both sides '
 'of the self-join. '
 'RE-SCRAPE COMMAND: python scripts/build_parcel_assembly.py',
 {s.n}, {gb}, CURRENT_TIMESTAMP(),
 'G120(b) + G120(e). Adjacency is NOT common ownership - Indiana parcel owner is NULL on all '
 '3,553,381 rows outside Marion, so assembly_basis says adjacency only. rowlike is a HEURISTIC: '
 'creeks, rail spurs and pipeline easements are ribbons too.'
)""").result()
print("\n  _registry row written")
print("PARCEL ASSEMBLY COMPLETE")
