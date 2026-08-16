"""Attach the PUBLISHER'S OWN location-precision label to every data-centre pin, and stop
rendering city centroids as if they were facility locations.

WHY: data_centers_datacentermap_coords carries `method` and `precision` columns that were
never read. In the Indiana bbox, 119 of 149 rows are method='census_gazetteer',
precision='city' - census CITY CENTROIDS - collapsed onto 11 distinct points. Only 3 rows are
precision='site'. The consequence on our map: 93 of 242 pins sit in a coordinate stack, the
worst being 32 pins on ONE point near New Carlisle, which includes Microsoft Mishawaka - a
facility about 15 km away. Two standing rules were being broken at once: "city-precision
coordinates never in distance math" and "estimated locations never style as published ones"
(and a census-gazetteer city point is a centroid, which the project bans outright).

FIX: rebuild in_data_centers_deduped with a location_precision column - 'site' where the
source publishes a facility coordinate, 'city' where it is a gazetteer centroid, 'unknown'
where the publisher says nothing. The map then styles and labels the three tiers apart, and
nothing city-precision is offered as a location.

Idempotent, registered in the same run. READ-ONLY except the one table it owns.
"""
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")

# --- measure first, so the notes carry numbers rather than adjectives -------------------
for r in client.query(f"""
    SELECT src, COUNT(*) n FROM `{DS}.in_data_centers_deduped` GROUP BY 1 ORDER BY n DESC"""):
    print(f"  before: {r.src:<16} {r.n:>4}")

SQL = f"""
WITH
-- peeringdb was clipped as a separate "connectivity layer" and never merged into the DC union,
-- so 19 Indiana facilities with SITE-precision coordinates (Netrality Indy Telcom 701/733 W
-- Henry, DataBank IND1/IND2, Lifeline Eastgate, Aunalytics, GAP Union Station, Indiana
-- University, ...) never reached the map, while 92 city centroids did. Merge it as a fourth
-- source, keeping only facilities that are not already represented: same name-stem, or any
-- existing pin within 150 m (these are downtown carrier hotels, so the radius is tight).
pdb AS (
  SELECT id, 'peeringdb' AS src, name, CAST(NULL AS STRING) AS operator,
         latitude AS lat, longitude AS lon
  FROM `{DS}.in_peeringdb_facilities`
  WHERE latitude IS NOT NULL AND longitude IS NOT NULL),
-- BigQuery refuses an anti-join whose only condition is spatial, so collect the matched ids
-- first (inner join, non-equality allowed) and anti-join on id equality afterwards.
pdb_matched AS (
  SELECT DISTINCT p.id
  FROM pdb p JOIN `{DS}.in_data_centers_deduped` d
    ON ST_DWITHIN(ST_GEOGPOINT(d.lon, d.lat), ST_GEOGPOINT(p.lon, p.lat), 150)
    OR (LENGTH(REGEXP_REPLACE(LOWER(IFNULL(d.name,'')), r'[^a-z0-9]','')) > 3
        AND STARTS_WITH(REGEXP_REPLACE(LOWER(IFNULL(p.name,'')), r'[^a-z0-9]',''),
                        REGEXP_REPLACE(LOWER(IFNULL(d.name,'')), r'[^a-z0-9]','')))),
pdb_new AS (
  SELECT p.* EXCEPT(id) FROM pdb p
  LEFT JOIN pdb_matched m ON p.id = m.id WHERE m.id IS NULL),
union_all AS (
  SELECT src, name, operator, lat, lon, unnamed_cannot_dedupe, dedupe_note
  FROM `{DS}.in_data_centers_deduped`
  UNION ALL
  SELECT src, name, operator, lat, lon, FALSE AS unnamed_cannot_dedupe,
         'added from peeringdb - site-precision, not previously on the map' AS dedupe_note
  FROM pdb_new),
dcm AS (
  -- the publisher's own labels, keyed by coordinate (our union kept no slug)
  SELECT ROUND(latitude, 6) AS lat6, ROUND(longitude, 6) AS lon6,
         ANY_VALUE(precision) AS precision, ANY_VALUE(method) AS method
  FROM `{EN}.data_centers_datacentermap_coords`
  WHERE latitude IS NOT NULL AND longitude IS NOT NULL
  GROUP BY 1, 2),
joined AS (
  SELECT d.*, dcm.precision AS dcm_precision, dcm.method AS dcm_method
  FROM union_all d
  LEFT JOIN dcm ON ROUND(d.lat, 6) = dcm.lat6 AND ROUND(d.lon, 6) = dcm.lon6),
stacks AS (
  SELECT ROUND(lat, 6) lat6, ROUND(lon, 6) lon6, COUNT(*) AS pins_here
  FROM union_all GROUP BY 1, 2),
-- F6 CORRECTION. B4 resolved eight Indianapolis colos against the operators' own statements and
-- recorded, per facility, the parcel each one actually sits on. Comparing our held pin with that
-- resolution: five agree to within 26 m and land on the SAME parcel, so their offsets are
-- cosmetic. ONE DOES NOT.
--
--   Databank Indianapolis IND2 — our pin was 96.8 m out and fell on parcel 491111183001014101,
--   which is in the 701/731/733 group on the SOUTH side of Henry Street. IND2 is 650 West Henry
--   Street, on the NORTH side, parcel 491111138006000101 — the parcel B4 recorded and the one
--   PeeringDB's published point lands on. The pin was on the wrong side of the road and therefore
--   attributed to the wrong parcel.
--
-- So a resolved point OVERRIDES the held pin where B4 established one. This is not a nudge for
-- neatness: a data-centre pinned to the wrong parcel corrupts every spatial join that facility
-- takes part in. Only rows B4 actually investigated are touched; everything else is unchanged.
corrections AS (
  SELECT REGEXP_REPLACE(UPPER(REGEXP_EXTRACT(already_pinned_as, r'^([^(]*)')), r'[^A-Z0-9]', '') AS key_norm,
         CAST(latitude AS FLOAT64) AS fix_lat, CAST(longitude AS FLOAT64) AS fix_lon,
         coord_source AS fix_source
  FROM `{DS}.in_dc_colo_resolved`
  WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND already_pinned_as IS NOT NULL
)
SELECT j.src, j.name, j.operator,
       IFNULL(c.fix_lat, j.lat) AS lat, IFNULL(c.fix_lon, j.lon) AS lon,
       j.unnamed_cannot_dedupe,
       IF(c.key_norm IS NULL, j.dedupe_note,
          CONCAT(IFNULL(j.dedupe_note, ''),
                 ' | coordinate corrected to the resolved point (B4): ', c.fix_source)) AS dedupe_note,
       CASE
         WHEN j.src = 'datacentermap' AND j.dcm_precision = 'city' THEN 'city'
         WHEN j.src = 'datacentermap' AND j.dcm_precision = 'site' THEN 'site'
         WHEN j.src = 'datacentermap' AND j.dcm_precision IS NULL THEN 'unknown'
         ELSE 'site'          -- baxtel / osm / wikidata publish per-facility coordinates
       END AS location_precision,
       j.dcm_method AS precision_method,
       s.pins_here AS pins_at_this_point
FROM joined j
LEFT JOIN corrections c
  ON c.key_norm = REGEXP_REPLACE(UPPER(j.name), r'[^A-Z0-9]', '')
JOIN stacks s ON ROUND(j.lat, 6) = s.lat6 AND ROUND(j.lon, 6) = s.lon6
"""
dry = client.query(SQL, job_config=bigquery.QueryJobConfig(dry_run=True))
print(f"dry-run {dry.total_bytes_processed/1e9:.3f} GB")
client.query(f"CREATE OR REPLACE TABLE `{DS}.in_data_centers_located` AS\n{SQL}").result()

stats = list(client.query(f"""
  SELECT location_precision, COUNT(*) n, MAX(pins_at_this_point) worst_stack
  FROM `{DS}.in_data_centers_located` GROUP BY 1 ORDER BY n DESC"""))
for s in stats: print(f"  after: {s.location_precision:<8} {s.n:>4}  worst stack {s.worst_stack}")
n = sum(s.n for s in stats)
city = sum(s.n for s in stats if s.location_precision == "city")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_data_centers_located'").result()
client.query(f"""INSERT `{DS}._registry`
  (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES (@t,@s,@m,@n,@g,CURRENT_TIMESTAMP(),@o)""",
  job_config=bigquery.QueryJobConfig(query_parameters=[
    bigquery.ScalarQueryParameter("t", "STRING", "in_data_centers_located"),
    bigquery.ScalarQueryParameter("s", "STRING",
      "indiana_app.in_data_centers_deduped x energy.data_centers_datacentermap_coords"),
    bigquery.ScalarQueryParameter("m", "STRING",
      "attach the publisher's own precision/method labels; count pins sharing each coordinate"),
    bigquery.ScalarQueryParameter("n", "INT64", n),
    bigquery.ScalarQueryParameter("g", "FLOAT64", round(dry.total_bytes_processed/1e9, 4)),
    bigquery.ScalarQueryParameter("o", "STRING",
      f"{city} of {n} pins are CITY-PRECISION census-gazetteer centroids, not facility "
      "locations - datacentermap publishes precision='city' for most of its Indiana rows and "
      "we had been rendering them as pins. They must never enter distance math and must never "
      "style as published coordinates. pins_at_this_point exposes the stacking: the worst "
      "single point carries 32 facilities incl. Microsoft Mishawaka ~15 km from New Carlisle.")])).result()
print(f"in_data_centers_located: {n} rows, {city} city-precision, registered")
