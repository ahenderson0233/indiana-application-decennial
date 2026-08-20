"""De-duplicate the substation table. 2,925 located rows are only 2,077 distinct substations.

WHY. Found by accident on 2026-08-17 while benchmarking coverage against a licensed extract: our
2,925 located substations collapse onto 2,077 distinct coordinates, so **848 located rows share a
coordinate with another row** - same name, same `sources` value, same voltage. `ROCKPORT STATION`
appears three times on one point. The duplicates are inherited from `energy.mat_grid_substations`
(3,858 Indiana rows on 2,077 distinct coordinates), so our clip is faithful and the merge upstream
simply did not collapse them. `energy` is read-only for us, so the fix lives here.

WHAT IT BREAKS TODAY. Any figure of the form "N substations" overstates by about 41%. The map draws
~848 redundant markers on top of each other.

WHAT IT DOES NOT BREAK. Nearest-substation DISTANCE is unaffected - the nearest of three identical
points is still the nearest - so the screener's distances were always right while its counts were
not. That distinction is why this is a display/count defect rather than a siting defect.

HOW THE WINNER IS PICKED. Group on rounded coordinate + upper-cased name, then keep the most
INFORMATIVE row rather than an arbitrary one: prefer a known voltage over NULL, then a real name
over an `UNKNOWN*`/`OSMUNKNOWN*` placeholder, then more line_count, then a HIFLD+OSM row over a
single-source row. Losing rows are counted, never silently dropped, and the count rides in the
registry.

⚠ UPDATED 2026-08-20 BY `repair_substation_geometry.py`, AND THE OLD NOTE HERE WAS THE CLUE.
This docstring used to read "footprint-only rows (933, the OSM-only contributions, which carry a
polygon instead of a point) are PASSED THROUGH UNTOUCHED". That was true and it was also the
answer to G20, which had separately concluded those same rows had "no coordinates either" after
testing `lat IS NULL`. The location was in `footprint_geojson` on 933 of 933.

The repair now derives a centroid for the 734 that fall inside Indiana, so EVERY in-state row has
a lat. That changes what this script must do:

  - `geom_kind` is no longer "does lat exist". It is **'point'** where the publisher gave us a
    point and **'footprint'** where the coordinate is a centroid we derived - because a derived
    centroid must never be drawn in place of an exact polygon.
  - 199 recovered footprints fall OUTSIDE Indiana (the upstream OSM slice is keyed on the scrape
    region, not a border test). They are kept, counted, and given **geom_kind='none'** so no
    exporter can put an out-of-state substation on an Indiana map.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

# ---------------------------------------------------------------------------------------------
# ASSET CLASS. Measured 2026-08-17: our "substation" table already holds 494 TAPs and 27 DEAD ENDs
# alongside 1,551 rows typed SUBSTATION - so a bare "N substations" count overstates real
# substations by about 21%, on top of the 41% the duplicates added. And `substation_type` carries
# TWO vocabularies mixed together: an upper-case one (SUBSTATION / TAP / DEAD END / RISER) and a
# lower-case one (industrial / distribution / transmission / traction / generation), which is the
# HIFLD and OSM halves of the merge never having been reconciled. 738 rows carry no type at all.
#
# This normalises them into one small vocabulary and NEVER guesses: unknown stays 'unknown'.
# A tap is a connection point on a line and a dead end is a line termination - neither is a place
# you can interconnect a data centre, so they must be separable from real substations rather than
# silently counted as them.
CLASS_SQL = """
  CASE
    WHEN UPPER(IFNULL(substation_type,'')) IN ('TAP','RISER','TRANSITION')
      OR REGEXP_CONTAINS(UPPER(IFNULL(substation_name,'')), r'^TAP\\d')          THEN 'tap'
    WHEN UPPER(IFNULL(substation_type,'')) IN ('DEAD END','DEADEND')
      OR REGEXP_CONTAINS(UPPER(IFNULL(substation_name,'')), r'^DEAD ?END\\d')    THEN 'dead_end'
    WHEN UPPER(IFNULL(substation_type,'')) = 'SUBSTATION'                        THEN 'substation'
    WHEN LOWER(IFNULL(substation_type,'')) IN
         ('industrial','distribution','minor_distribution','transmission','traction',
          'generation','gas','yes')                                              THEN 'substation'
    ELSE 'unknown'
  END"""

SQL = f"""
CREATE OR REPLACE TABLE `{DS}.in_substations_dedup` AS
WITH located AS (
  SELECT *,
         -- ~11 m of latitude. Tight on purpose: this collapses EXACT duplicates, not neighbouring
         -- substations that happen to share a fence line.
         FORMAT('%.4f|%.4f|%s', lat, lon, UPPER(IFNULL(substation_name, ''))) AS dup_key
  FROM `{DS}.in_substations`
  WHERE lat IS NOT NULL AND lon IS NOT NULL
),
ranked AS (
  SELECT *, COUNT(*) OVER (PARTITION BY dup_key) AS dup_group_size,
         ROW_NUMBER() OVER (
           PARTITION BY dup_key
           ORDER BY
             CASE WHEN max_kv IS NOT NULL THEN 0 ELSE 1 END,                    -- known voltage wins
             CASE WHEN REGEXP_CONTAINS(UPPER(IFNULL(substation_name,'')),
                                       r'^(OSM)?UNKNOWN|^DEAD ?END|^TAP') THEN 1 ELSE 0 END,
             IFNULL(line_count, -1) DESC,                                        -- better connected
             CASE WHEN sources LIKE '%+%' THEN 0 ELSE 1 END,                     -- merged over single
             substation_name
         ) AS rk
  FROM located
)
-- ⚠ geom_kind is EXCEPT-ed from the input because repair_substation_geometry.py now writes its
--    own, richer one (point_and_footprint / footprint_only_point_derived / point_only /
--    no_location). This table keeps the two-value vocabulary app.js filters on, but it is now
--    derived from coord_source rather than from "does lat exist", because after the repair EVERY
--    in-state row has a lat and 734 of those coordinates are CENTROIDS WE DERIVED.
-- ⛔ A DERIVED CENTROID MUST NOT REPLACE A REAL FOOTPRINT ON THE MAP. geom_kind='point' now means
--    "the publisher gave us this point"; 'footprint' means "we only have the polygon, and the
--    polygon is what gets drawn". Without this the repair would have silently converted 734
--    exact footprints into invented points.
SELECT * EXCEPT(dup_key, rk, dup_group_size, geom_kind),
       dup_group_size - 1 AS duplicates_collapsed,
       IF(coord_source = 'published_point', 'point', 'footprint') AS geom_kind,
       {CLASS_SQL} AS asset_class
FROM ranked WHERE rk = 1

UNION ALL

-- Rows with no usable location at all. After the repair these are the 199 OSM footprints that
-- fall OUTSIDE Indiana (the upstream slice is keyed on the scrape region, not a border test).
-- They are carried so the count stays honest and DELIBERATELY given geom_kind='none' so no
-- exporter can draw an out-of-state substation on an Indiana map.
SELECT * EXCEPT(geom_kind), 0 AS duplicates_collapsed, 'none' AS geom_kind,
       {CLASS_SQL} AS asset_class
FROM `{DS}.in_substations`
WHERE lat IS NULL
"""

client.query(SQL).result()

m = list(client.query(f"""
SELECT COUNT(*) n,
       COUNTIF(geom_kind = 'point') pts,
       COUNTIF(geom_kind = 'footprint') fps,
       COUNTIF(geom_kind = 'none') nones,
       SUM(duplicates_collapsed) collapsed,
       COUNT(DISTINCT IF(geom_kind='point', FORMAT('%.4f|%.4f', lat, lon), NULL)) distinct_pts,
       COUNTIF(max_kv IS NULL AND geom_kind = 'point') no_kv,
       COUNTIF(asset_class = 'substation') c_sub,
       COUNTIF(asset_class = 'tap') c_tap,
       COUNTIF(asset_class = 'dead_end') c_de,
       COUNTIF(asset_class = 'unknown') c_unk
FROM `{DS}.in_substations_dedup`"""))[0]
before = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_substations`"))[0].n

print(f"in_substations       : {before:,} rows (before)")
print(f"in_substations_dedup : {m.n:,} rows  =  {m.pts:,} published points + {m.fps:,} "
      f"drawn as their footprint + {m.nones:,} with no in-state location")
print(f"  duplicates collapsed : {m.collapsed:,}")
print(f"  distinct coordinates : {m.distinct_pts:,}")
print(f"  points with no voltage recorded: {m.no_kv:,}  <- NULL, never 0")
print(f"  asset class -> substation {m.c_sub:,} | tap {m.c_tap:,} | dead_end {m.c_de:,} "
      f"| unknown {m.c_unk:,}")

# Points may legitimately exceed distinct coordinates: two DIFFERENTLY-NAMED assets can share one
# structure (measured: 3 cases, all tap/tap or dead-end/dead-end pairs with distinct publisher IDs).
# Merging those on coordinate alone would delete a real record, so the check is that the excess is
# small and confined to network nodes - not that it is zero.
excess = m.pts - m.distinct_pts
assert excess <= 5, f"{excess} coordinates carry multiple named assets - investigate before trusting"
print(f"  {excess} coordinate(s) carry two differently-named assets (kept: distinct publisher IDs)")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_substations_dedup'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
    f"VALUES (@t,@s,@m,@n,0.0,CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "in_substations_dedup"),
        bigquery.ScalarQueryParameter("s", "STRING", f"{DS}.in_substations"),
        bigquery.ScalarQueryParameter("m", "STRING",
            "group on 4dp coordinate + upper(name); keep the most informative row (known voltage > "
            "real name over UNKNOWN/TAP placeholder > higher line_count > merged source); "
            "footprint-only rows passed through untouched"),
        bigquery.ScalarQueryParameter("n", "INT64", int(m.n)),
        bigquery.ScalarQueryParameter("no", "STRING",
            f"Collapsed {m.collapsed} duplicate rows inherited from energy.mat_grid_substations, "
            f"which holds 3,858 Indiana rows on only 2,077 distinct coordinates. Counts of "
            f"'N substations' previously overstated by ~41%. Nearest-substation DISTANCE was never "
            f"affected - the nearest of three identical points is still the nearest. "
            f"`duplicates_collapsed` records how many rows each surviving row absorbed.")])).result()
print("registered in_substations_dedup")
