"""G122: decide, per parcel, whether it is a ROAD RIGHT-OF-WAY - and exclude it if it is.

Operator, 2026-08-20c: *"The parcels extend to roadways (where the roadway is acting as a parcel
with no structure, and no one can actually own a roadway, so this needs to be fixed immediately in
the next session)."*

⛔ WHY A NEW TABLE RATHER THAN A COLUMN ON in_parcel_assembly. That table READS
in_screener_candidates, and the candidate build has to read the exclusion, which would be a cycle.
This one is built from in_sites + parcels_in + in_roads_all and depends on neither.

================================================================================================
THE INSTRUMENT, AND THE TRAP IT WAS BUILT TO AVOID
================================================================================================
The previous test was "does a held road cross this polygon". It was only ever safe because we held
1,086 roads - 225 primary and 861 secondary, no local streets at all. G122 called for TIGER All
Roads, `load_tiger_all_roads.py` loaded 379,165 features, and ⛔ THAT MAKES THE OLD TEST WORSE,
NOT BETTER. Measured over three counties: `ST_INTERSECTS` fires on 7,052 of 23,678 parcels that
are NOT ribbon-shaped, against 55 before. A test whose positives rise 128x because the corpus grew
is measuring the corpus.

The replacement asks whether the road runs ALONG the parcel instead of across it:

    along_ratio = (length of road centreline inside the polygon) / (perimeter / 2)

For a right-of-way ribbon the centreline runs its whole length, so the ratio approaches 1 - and
exceeds it where a divided highway contributes two centrelines. For a 200-acre farm clipped by a
county road it is a few percent. Same join, and it separates the two cases the old test could not.

⚠ along_ratio ALONE STILL OVER-FIRES, and the measurement says where: a 174-acre industrial site
(`1555 KENTUCKY AV`, class 399) and a private-drive common area (`PRIVATE DRIVES OF THE CLIFFS`,
class 599) both score above 1.0 because they contain internal road networks. They are not
rights-of-way. So the class code gates it.

================================================================================================
THE CLASS CODE - what it can and cannot do, measured
================================================================================================
⛔ INDIANA HAS NO RIGHT-OF-WAY CLASS CODE. Searching Marion's own published class descriptions for
ROAD / RIGHT / R/W / STREET / HIGHWAY / ALLEY returns ZERO rows. The code cannot positively
identify a road, and any design that assumed it would was wrong before it started.

⭐ WHAT IT CAN DO IS EXONERATE, which is worth more here. Measured across the 5,757 ribbon
parcels, the road-crossing rate by class band:

    6xx public/exempt   23.3%      <- the pool that contains rights-of-way
    unclassed           10.0%
    8xx utility/rail     6.9%
    1xx agricultural     1.7%      <- long thin FARM FIELDS
    4xx commercial       1.3%
    5xx residential      1.1%      <- long thin HOUSE LOTS

A ribbon coded `510 RES ONE FAMILY PLATTED LOT` is a narrow house lot. Excluding it because it is
thin would be a false positive, and there are thousands of them.

⚠ THE JOIN KEY IS `state_parcel_id`, NOT `parcel_id`. `in_sites.parcel_key` is the state parcel
number (`100200400004000026`); `parcels_in.parcel_id` is the county's dashed form
(`10-02-00-400-004.000-026`). Joining the wrong one returns ~1% and looks like missing data - it
reported "99.0% of candidates carry no class code" against a column that is 97.8% populated.
⚠ 38,840 state_parcel_id values are duplicated in parcels_in, so the parcel side is de-duplicated
by GROUP BY before it is joined. Fan-out is asserted below, not assumed.

================================================================================================
WHAT IS EXCLUDED, AND WHAT IS ONLY REPORTED
================================================================================================
  road_row   EXCLUDED. Ribbon + the road runs along it + no structure + not a taxable private
             class. This is the operator's case: it is not a weak site, it is not a site.
  rail_row   EXCLUDED. Class 841 (measured: 65.2% of its ribbons intersect a railroad we hold, and
             their addresses read "RR") or a rail line running along it. A live rail corridor is
             no more ownable than a road. ⚠ Reported SEPARATELY - the operator asked about
             roadways, and a rail corridor answering to "roadway" would be us widening the ask.
  shape_only REPORTED, NOT EXCLUDED. Ribbon-shaped with no road along it: creeks, pipeline
             easements, legitimately long narrow industrial land. ⛔ Widening the threshold until
             these disappear is how a heuristic eats its own corpus.
  none       everything else.

RE-SCRAPE COMMAND: python scripts/build_parcel_row_class.py
⚠ IDEMPOTENT: replace_safe. CREATE OR REPLACE, reads only upstream tables, never its own output.
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_parcel_row_class"
D85 = "080500000047000018"

# Thresholds. Stated here so they are one edit, and so the registry row can quote them.
RIBBON_COMPACT = 0.18     # isoperimetric quotient below which a polygon is "unusually elongated"
ALONG_MIN = 0.60          # road centreline length inside / (perimeter/2)
STRICT_COMPACT = 0.12     # the tighter shape gate used for exclusion

# Real roadways only. ⛔ S1710 walkway, S1820 bike path, S1780 parking-lot road and S1750 private
# driveway are NOT public road right-of-way; a bike path clipping a parcel must not condemn it.
ROADWAY_MTFCC = "('S1100','S1200','S1400','S1630','S1640','S1730','S1740')"

client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH p AS (
  -- de-duplicated parcel attributes; 38,840 state_parcel_id values repeat in the source
  SELECT state_parcel_id AS parcel_key,
         ANY_VALUE(NULLIF(dlgf_prop_class_code, '')) AS class_code,
         ANY_VALUE(NULLIF(COALESCE(NULLIF(dlgf_prop_address, ''),
                                   NULLIF(prop_add, '')), '')) AS prop_address
  FROM `energy-platfrom.energy.parcels_in`
  WHERE state_parcel_id IS NOT NULL AND state_parcel_id != '{D85}'
  GROUP BY 1
),
base AS (
  SELECT s.parcel_source, s.parcel_key, s.structure_count, s.parcel_acres,
         s.parcel_geog AS g,
         ST_AREA(s.parcel_geog) AS area_m2,
         ST_PERIMETER(s.parcel_geog) AS perim_m,
         SAFE_DIVIDE(4 * ACOS(-1) * ST_AREA(s.parcel_geog),
                     POW(NULLIF(ST_PERIMETER(s.parcel_geog), 0), 2)) AS compactness,
         p.class_code, p.prop_address
  FROM `{DS}.in_sites` s
  LEFT JOIN p USING (parcel_key)
  WHERE s.parcel_geog IS NOT NULL AND s.parcel_key != '{D85}'
),
-- ⭐ Only ELONGATED polygons are put through the spatial joins. A compact parcel cannot be a road
-- corridor however many roads clip it, and this keeps a 379,165-feature join to a few thousand
-- candidates instead of 3.5 million.
ribbon AS (
  SELECT * FROM base WHERE compactness < {RIBBON_COMPACT}
),
road_hit AS (
  SELECT b.parcel_source, b.parcel_key,
         SUM(ST_LENGTH(ST_INTERSECTION(r.geom, b.g))) AS road_len_m,
         COUNT(*) AS n_road_segments,
         ARRAY_AGG(DISTINCT r.FULLNAME IGNORE NULLS ORDER BY r.FULLNAME LIMIT 4) AS road_names
  FROM ribbon b
  JOIN `{DS}.in_roads_all` r
    ON ST_INTERSECTS(r.geom, b.g) AND r.MTFCC IN {ROADWAY_MTFCC}
  GROUP BY 1, 2
),
rail_hit AS (
  SELECT b.parcel_source, b.parcel_key,
         SUM(ST_LENGTH(ST_INTERSECTION(rr.geom, b.g))) AS rail_len_m
  FROM ribbon b
  JOIN `{DS}.in_railroads` rr ON ST_INTERSECTS(rr.geom, b.g)
  GROUP BY 1, 2
),
graded AS (
  SELECT b.parcel_source, b.parcel_key, b.class_code, b.prop_address,
         b.structure_count, b.parcel_acres,
         ROUND(b.area_m2) AS area_m2, ROUND(b.perim_m) AS perimeter_m,
         ROUND(b.compactness, 4) AS compactness,
         IFNULL(rh.n_road_segments, 0) AS n_road_segments,
         rh.road_names,
         ROUND(SAFE_DIVIDE(rh.road_len_m, b.perim_m / 2), 3) AS road_along_ratio,
         ROUND(SAFE_DIVIDE(rl.rail_len_m, b.perim_m / 2), 3) AS rail_along_ratio,
         -- a taxable PRIVATE class is proof this is somebody's lot, not a public corridor
         (b.class_code IS NOT NULL
          AND REGEXP_CONTAINS(b.class_code, r'^[13457]')) AS private_taxable_class
  FROM ribbon b
  LEFT JOIN road_hit rh USING (parcel_source, parcel_key)
  LEFT JOIN rail_hit rl USING (parcel_source, parcel_key)
)
SELECT
  parcel_source, parcel_key, class_code, prop_address, structure_count, parcel_acres,
  area_m2, perimeter_m, compactness, n_road_segments, road_names,
  road_along_ratio, rail_along_ratio, private_taxable_class,
  CASE
    WHEN compactness < {STRICT_COMPACT}
         AND IFNULL(road_along_ratio, 0) >= {ALONG_MIN}
         AND IFNULL(structure_count, 0) = 0
         AND NOT private_taxable_class                      THEN 'road_row'
    WHEN compactness < {STRICT_COMPACT}
         AND (class_code = '841' OR IFNULL(rail_along_ratio, 0) >= {ALONG_MIN})
         AND IFNULL(structure_count, 0) = 0
         AND NOT private_taxable_class                      THEN 'rail_row'
    WHEN compactness < {STRICT_COMPACT}
         AND IFNULL(structure_count, 0) = 0                 THEN 'shape_only'
    ELSE 'none'
  END AS row_class,
  CASE
    WHEN compactness < {STRICT_COMPACT}
         AND IFNULL(road_along_ratio, 0) >= {ALONG_MIN}
         AND IFNULL(structure_count, 0) = 0
         AND NOT private_taxable_class                      THEN TRUE
    WHEN compactness < {STRICT_COMPACT}
         AND (class_code = '841' OR IFNULL(rail_along_ratio, 0) >= {ALONG_MIN})
         AND IFNULL(structure_count, 0) = 0
         AND NOT private_taxable_class                      THEN TRUE
    ELSE FALSE
  END AS row_excluded,
  CASE
    WHEN IFNULL(road_along_ratio, 0) >= {ALONG_MIN} THEN
      CONCAT('road centreline runs ',
             CAST(CAST(ROUND(LEAST(road_along_ratio, 9.99) * 100) AS INT64) AS STRING),
             '% of the parcel length')
    WHEN class_code = '841' THEN 'railroad class 841'
    WHEN IFNULL(rail_along_ratio, 0) >= {ALONG_MIN} THEN 'rail line runs along the parcel'
    ELSE 'elongated shape only, no road or rail along it'
  END AS row_basis,
  CURRENT_TIMESTAMP() AS built_at
FROM graded
"""

print("G122 - ROAD RIGHT-OF-WAY CLASSIFICATION")
print(f"  ribbon gate compactness < {RIBBON_COMPACT}, exclusion gate < {STRICT_COMPACT}, "
      f"along_ratio >= {ALONG_MIN}")
job = client.query(SQL)
job.result()
gb = round((job.total_bytes_processed or 0) / 1e9, 2)
print(f"  built, {gb} GB scanned")

# --- fan-out. The parcel side is grouped, so this must be exactly 1.0.
f = list(client.query(f"""
  SELECT (SELECT COUNT(*) FROM `{OUT}`) AS rows_out,
         (SELECT COUNT(DISTINCT CONCAT(parcel_source,'/',parcel_key)) FROM `{OUT}`) AS distinct_out
"""))[0]
ratio = f.rows_out / f.distinct_out if f.distinct_out else 0
print(f"  fan-out {f.rows_out:,} rows / {f.distinct_out:,} distinct parcels = {ratio:.4f}")
assert abs(ratio - 1.0) < 1e-9, f"FAN-OUT {ratio} - the class-code join duplicated parcels"

print("\n  classification of every elongated parcel in the state:")
for r in client.query(f"""
  SELECT row_class, COUNT(*) n, COUNTIF(row_excluded) excl,
         ROUND(AVG(compactness), 4) mean_compact,
         ROUND(AVG(road_along_ratio), 3) mean_along,
         ROUND(SUM(parcel_acres)) acres
  FROM `{OUT}` GROUP BY 1
  ORDER BY CASE row_class WHEN 'road_row' THEN 1 WHEN 'rail_row' THEN 2
                          WHEN 'shape_only' THEN 3 ELSE 4 END"""):
    print(f"    {r.row_class:12} {r.n:>8,} parcels  excluded {r.excl:>7,}  "
          f"mean compactness {r.mean_compact}  mean along {r.mean_along}  "
          f"{(r.acres or 0):>10,.0f} acres")

print("\n  what the class code contributed - ribbons SAVED from exclusion by a taxable class:")
for r in client.query(f"""
  SELECT SUBSTR(class_code, 1, 1) band, COUNT(*) n
  FROM `{OUT}`
  WHERE private_taxable_class AND compactness < {STRICT_COMPACT}
    AND IFNULL(road_along_ratio, 0) >= {ALONG_MIN} AND IFNULL(structure_count, 0) = 0
  GROUP BY 1 ORDER BY 2 DESC"""):
    print(f"    class {r.band}xx  {r.n:>6,} elongated parcels with a road along them that are "
          f"somebody's taxable lot, NOT a right-of-way")

print("\n  the strongest road_row evidence - read the addresses:")
for r in client.query(f"""
  SELECT class_code, prop_address, ROUND(parcel_acres, 1) ac, compactness, road_along_ratio,
         road_names
  FROM `{OUT}` WHERE row_class = 'road_row'
  ORDER BY road_along_ratio DESC LIMIT 12"""):
    nm = ", ".join(r.road_names or [])[:34]
    print(f"    cc={str(r.class_code):>5} along={r.road_along_ratio:>6} "
          f"{(r.ac or 0):>8,.1f}ac  {str(r.prop_address)[:34]:36} [{nm}]")

n = list(client.query(f"SELECT COUNT(*) n FROM `{OUT}`"))[0].n
excl = list(client.query(f"SELECT COUNTIF(row_excluded) n FROM `{OUT}`"))[0].n
client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_parcel_row_class',
 'indiana_app.in_sites x energy.parcels_in (dlgf_prop_class_code, dlgf_prop_address) x '
 'indiana_app.in_roads_all (TIGER {'{}'} All Roads, 379,165 features) x indiana_app.in_railroads',
 'Right-of-way classification for every parcel whose isoperimetric quotient is below '
 '{RIBBON_COMPACT}. The discriminator is along_ratio = length of road centreline INSIDE the '
 'polygon / (perimeter/2): a corridor carries the road down its whole length, a farm clipped by a '
 'county road does not. ST_INTERSECTS alone was retired - with the full road corpus it fires on '
 '30 percent of ordinary parcels, against 55 of 23,678 when only primary and secondary roads were '
 'held. Excluded when compactness < {STRICT_COMPACT} AND along_ratio >= {ALONG_MIN} AND '
 'structure_count = 0 AND the DLGF class is not a taxable private class (1/3/4/5/7xx). '
 'Indiana publishes NO right-of-way class code - Marion class descriptions contain no '
 'ROAD/RIGHT/STREET/HIGHWAY/ALLEY row - so the code EXONERATES rather than identifies. '
 'MTFCC restricted to real roadways; walkways, bike paths, parking-lot roads and private '
 'driveways are excluded from confirmation. Joined on state_parcel_id, de-duplicated; fan-out '
 'asserted at exactly 1.0. D85 excluded on both sides. '
 'RE-SCRAPE COMMAND: python scripts/build_parcel_row_class.py',
 {n}, {gb}, CURRENT_TIMESTAMP(),
 'G122. {excl} parcels are excluded from the candidate set by in_screener_candidates. '
 'shape_only is REPORTED, never excluded - creeks, pipeline easements and genuinely long narrow '
 'industrial land are ribbons too, and widening the threshold until they vanish would eat the '
 'corpus. IDEMPOTENCY: replace_safe. CADENCE: with the parcel refresh, or a new TIGER vintage.'
)""").result()
print("\n  _registry row written")
print("ROW CLASSIFICATION COMPLETE")
