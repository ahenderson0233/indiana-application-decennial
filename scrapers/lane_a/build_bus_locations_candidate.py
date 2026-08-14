"""indiana_app.in_pjm_bus_locations_candidate — tiered PJM/AEP bus-location ladder (operator-
endorsed estimation; tiers never blended; a bus with no defensible match keeps NULL coords).

Ladder (first single-site hit wins; kV gate is HARD for 'high'):
  T0 pjm_queue_facid        PJM's OWN published queue points (in_pjm_gis_queues): FAC_ID =
                            name-prefix + state + kV. kV equality + name-overlap>=5 + single
                            site cluster -> high. (Method value beyond the requested enum —
                            it uses publisher coordinates and outranks name-matching.)
  T1 substation_match_exact HIFLD/OSM (AEP states), exact normalized name; kV-in-range -> high.
  T2 substation_match_prefix truncation-aware prefix; kV-consistent single-site -> med.
  T3 rtep_bridge            bus prefix -> RTEP full location name (AEP TO rows of
                            in_pjm_rtep_upgrades) -> HIFLD/OSM exact; kV-consistent -> med.
  T4 interpolated           SKIPPED-BY-MEASUREMENT: QueueScope bus_number (PSS/E 242508-290735)
                            joins energy.bus_hifld synthetic ids (1-75328) at exactly 0/1,475.
  none                      NULL coords; collision_count documents why (ambiguous matches seen).
"""
import os
import sys

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from register_helper import register  # noqa: E402

c = bigquery.Client(project="energy-platfrom")
DEST = "energy-platfrom.indiana_app.in_pjm_bus_locations_candidate"

sql = r"""
CREATE OR REPLACE TABLE `energy-platfrom.indiana_app.in_pjm_bus_locations_candidate` AS
WITH buses AS (
  SELECT SAFE_CAST(bus_number AS INT64) AS bus_number,
         ANY_VALUE(bus_label) AS bus_label,
         ANY_VALUE(REGEXP_REPLACE(UPPER(TRIM(REGEXP_EXTRACT(bus_label,
           r'^\d{2}(.*?)\s+[0-9.]+\s*[kK][vV]', 1))), r'[^A-Z0-9]', '')) AS bus_norm,
         ANY_VALUE(SAFE_CAST(REGEXP_EXTRACT(bus_label, r'\s([0-9.]+)\s*[kK][vV]') AS FLOAT64))
           AS bus_kv
  FROM `energy-platfrom.energy.pjm_queuescope_results`
  WHERE owner_label = 'AEP' AND bus_label IS NOT NULL
  GROUP BY 1
),
-- T0: PJM's own queue points. FAC_ID = <name><STATE><kv>, state anchored before trailing digits.
fac AS (
  SELECT fac_name, fac_state, fac_kv,
         ST_Y(site) AS lat, ST_X(site) AS lon, spread_m, n_points
  FROM (
    SELECT REGEXP_EXTRACT(FAC_ID, r'^([A-Z0-9]+?)[A-Z]{2}[0-9]+$') AS fac_name,
           REGEXP_EXTRACT(FAC_ID, r'([A-Z]{2})[0-9]+$') AS fac_state,
           SAFE_CAST(REGEXP_EXTRACT(FAC_ID, r'([0-9]+)$') AS FLOAT64) AS fac_kv,
           ST_CENTROID_AGG(ST_GEOGPOINT(lon, lat)) AS site,
           -- cluster spread proxy: bbox diagonal (upper bound on point spread)
           ST_DISTANCE(ST_GEOGPOINT(MIN(lon), MIN(lat)),
                       ST_GEOGPOINT(MAX(lon), MAX(lat))) AS spread_m,
           COUNT(*) AS n_points
    FROM `energy-platfrom.indiana_app.in_pjm_gis_queues`
    WHERE lat IS NOT NULL AND lon IS NOT NULL AND FAC_ID IS NOT NULL
    GROUP BY FAC_ID
  )
  WHERE fac_state IN ('IN','MI','OH','WV','VA','KY','TN')
    AND fac_name IS NOT NULL AND LENGTH(fac_name) >= 4 AND spread_m <= 2000
),
t0_pairs AS (
  -- >=5-char overlap: 4-char FAC names measured ambiguous (CLIN matched CLINCHFLD and CLINTO;
  -- VALL pulled a WV bus to a MI point). Never again.
  SELECT b.bus_number, b.bus_norm, f.fac_name, f.fac_kv, f.lat, f.lon
  FROM buses b
  JOIN fac f
    ON b.bus_kv = f.fac_kv
   AND (STARTS_WITH(b.bus_norm, f.fac_name) OR STARTS_WITH(f.fac_name, b.bus_norm))
   AND LEAST(LENGTH(b.bus_norm), LENGTH(f.fac_name)) >= 5
),
fac_unambiguous AS (
  -- a FAC code claimed by more than one distinct bus-name family is ambiguous; drop ALL its matches
  SELECT fac_name, fac_kv FROM t0_pairs
  GROUP BY fac_name, fac_kv HAVING COUNT(DISTINCT bus_norm) = 1
),
t0 AS (
  SELECT p.bus_number,
         COUNT(DISTINCT FORMAT('%.3f|%.3f', p.lat, p.lon)) AS n_sites,
         ANY_VALUE(p.lat) AS lat, ANY_VALUE(p.lon) AS lon,
         ANY_VALUE(p.fac_name) AS matched_name,
         LOGICAL_OR(TRUE) AS kv_eq
  FROM t0_pairs p
  JOIN fac_unambiguous u ON u.fac_name = p.fac_name AND u.fac_kv = p.fac_kv
  GROUP BY p.bus_number
),
subs AS (
  SELECT 'hifld' AS src, name,
         SAFE_CAST(latitude AS FLOAT64) AS lat, SAFE_CAST(longitude AS FLOAT64) AS lon,
         SAFE_CAST(max_volt AS FLOAT64) AS max_kv, SAFE_CAST(min_volt AS FLOAT64) AS min_kv,
         REGEXP_REPLACE(UPPER(TRIM(REGEXP_REPLACE(UPPER(name),
           r'\b(SUBSTATION|SUB|STATION|SWITCHYARD|SWITCHING|TAP|JUNCTION|JCT|SS)\b', ''))),
           r'[^A-Z0-9]', '') AS sub_norm
  FROM `energy-platfrom.energy.nat_substations_hifld`
  WHERE state IN ('IN','MI','OH','WV','VA','KY','TN') AND name IS NOT NULL
    AND NOT REGEXP_CONTAINS(UPPER(name), r'^(UNKNOWN|TAP)\d*$')
  UNION ALL
  SELECT 'osm', COALESCE(NULLIF(name, ''), operator),
         COALESCE(SAFE_CAST(latitude AS FLOAT64),
                  ST_Y(ST_CENTROID(SAFE.ST_GEOGFROMGEOJSON(geometry_geojson)))),
         COALESCE(SAFE_CAST(longitude AS FLOAT64),
                  ST_X(ST_CENTROID(SAFE.ST_GEOGFROMGEOJSON(geometry_geojson)))),
         (SELECT MAX(SAFE_CAST(v AS FLOAT64))/1000 FROM UNNEST(SPLIT(IFNULL(voltage,''),';')) v),
         (SELECT MIN(SAFE_CAST(v AS FLOAT64))/1000 FROM UNNEST(SPLIT(IFNULL(voltage,''),';')) v),
         REGEXP_REPLACE(UPPER(TRIM(REGEXP_REPLACE(UPPER(COALESCE(NULLIF(name,''), operator, '')),
           r'\b(SUBSTATION|SUB|STATION|SWITCHYARD|SWITCHING|TAP|JUNCTION|JCT|SS)\b', ''))),
           r'[^A-Z0-9]', '') AS sub_norm
  FROM `energy-platfrom.energy.osm_power_substations`
  WHERE state_scraped IN ('IN','MI','OH','WV','VA','KY','TN')
    AND COALESCE(NULLIF(name, ''), NULLIF(operator, '')) IS NOT NULL
),
t1 AS (
  SELECT b.bus_number,
         COUNT(DISTINCT FORMAT('%.3f|%.3f', s.lat, s.lon)) AS n_sites,
         ANY_VALUE(s.lat) AS lat, ANY_VALUE(s.lon) AS lon,
         ANY_VALUE(s.name) AS matched_name, ANY_VALUE(s.src) AS matched_src,
         LOGICAL_OR(b.bus_kv BETWEEN s.min_kv - 1 AND s.max_kv + 1) AS kv_ok
  FROM buses b JOIN subs s ON b.bus_norm != '' AND s.sub_norm = b.bus_norm
  WHERE s.lat IS NOT NULL
  GROUP BY b.bus_number
),
t2 AS (
  SELECT b.bus_number,
         COUNT(DISTINCT FORMAT('%.3f|%.3f', s.lat, s.lon)) AS n_sites,
         ANY_VALUE(s.lat) AS lat, ANY_VALUE(s.lon) AS lon,
         ANY_VALUE(s.name) AS matched_name, ANY_VALUE(s.src) AS matched_src,
         LOGICAL_OR(b.bus_kv BETWEEN s.min_kv - 1 AND s.max_kv + 1) AS kv_ok
  FROM buses b JOIN subs s
    ON b.bus_norm != '' AND LENGTH(b.bus_norm) >= 5
   AND STARTS_WITH(s.sub_norm, b.bus_norm) AND s.sub_norm != b.bus_norm
  WHERE s.lat IS NOT NULL
  GROUP BY b.bus_number
),
rtep_names AS (
  SELECT DISTINCT
    REGEXP_REPLACE(UPPER(TRIM(loc_part)), r'[^A-Z0-9]', '') AS rtep_norm
  FROM `energy-platfrom.indiana_app.in_pjm_rtep_upgrades`,
       UNNEST(SPLIT(IFNULL(location, ''), '-')) AS loc_part
  WHERE UPPER(IFNULL(transmission_owner, '')) LIKE '%AEP%' AND TRIM(loc_part) != ''
),
t3 AS (
  SELECT b.bus_number,
         COUNT(DISTINCT FORMAT('%.3f|%.3f', s.lat, s.lon)) AS n_sites,
         ANY_VALUE(s.lat) AS lat, ANY_VALUE(s.lon) AS lon,
         ANY_VALUE(s.name) AS matched_name, ANY_VALUE(s.src) AS matched_src,
         LOGICAL_OR(b.bus_kv BETWEEN s.min_kv - 1 AND s.max_kv + 1) AS kv_ok
  FROM buses b
  JOIN rtep_names r
    ON LENGTH(b.bus_norm) >= 5 AND STARTS_WITH(r.rtep_norm, b.bus_norm)
   AND r.rtep_norm != b.bus_norm
  JOIN subs s ON s.sub_norm = r.rtep_norm
  WHERE s.lat IS NOT NULL
  GROUP BY b.bus_number
)
SELECT
  b.bus_number, b.bus_label, b.bus_kv,
  CASE
    WHEN t0.bus_number IS NOT NULL AND t0.n_sites = 1 THEN 'pjm_queue_facid'
    WHEN t1.bus_number IS NOT NULL AND t1.n_sites = 1 THEN 'substation_match_exact'
    WHEN t2.bus_number IS NOT NULL AND t2.n_sites = 1 AND t2.kv_ok
         THEN 'substation_match_prefix'
    WHEN t3.bus_number IS NOT NULL AND t3.n_sites = 1 AND t3.kv_ok THEN 'rtep_bridge'
    ELSE 'none' END AS location_method,
  CASE
    WHEN t0.bus_number IS NOT NULL AND t0.n_sites = 1 THEN 'high'
    WHEN t1.bus_number IS NOT NULL AND t1.n_sites = 1 AND t1.kv_ok THEN 'high'
    WHEN t1.bus_number IS NOT NULL AND t1.n_sites = 1 THEN 'med'
    WHEN t2.bus_number IS NOT NULL AND t2.n_sites = 1 AND t2.kv_ok THEN 'med'
    WHEN t3.bus_number IS NOT NULL AND t3.n_sites = 1 AND t3.kv_ok THEN 'med'
    ELSE NULL END AS match_confidence,
  CASE
    WHEN t0.bus_number IS NOT NULL AND t0.n_sites = 1
      THEN 'PJM-published queue point; FAC_ID kV == bus kV; name overlap >=5; FAC code claimed by exactly one bus-name family; single site cluster <=2km'
    WHEN t1.bus_number IS NOT NULL AND t1.n_sites = 1
      THEN CONCAT('exact normalized name; single site; kV-in-range=', CAST(t1.kv_ok AS STRING))
    WHEN t2.bus_number IS NOT NULL AND t2.n_sites = 1 AND t2.kv_ok
      THEN 'PSS/E-truncation prefix; single site; kV-in-range'
    WHEN t3.bus_number IS NOT NULL AND t3.n_sites = 1 AND t3.kv_ok
      THEN 'bus prefix -> RTEP full endpoint name (AEP TO) -> substation exact; kV-in-range'
    ELSE 'no defensible match; interpolation skipped (bus-number vocabularies join at 0/1475)'
    END AS match_basis,
  CASE
    WHEN t0.bus_number IS NOT NULL AND t0.n_sites = 1 THEN t0.lat
    WHEN t1.bus_number IS NOT NULL AND t1.n_sites = 1 THEN t1.lat
    WHEN t2.bus_number IS NOT NULL AND t2.n_sites = 1 AND t2.kv_ok THEN t2.lat
    WHEN t3.bus_number IS NOT NULL AND t3.n_sites = 1 AND t3.kv_ok THEN t3.lat
    ELSE NULL END AS lat,
  CASE
    WHEN t0.bus_number IS NOT NULL AND t0.n_sites = 1 THEN t0.lon
    WHEN t1.bus_number IS NOT NULL AND t1.n_sites = 1 THEN t1.lon
    WHEN t2.bus_number IS NOT NULL AND t2.n_sites = 1 AND t2.kv_ok THEN t2.lon
    WHEN t3.bus_number IS NOT NULL AND t3.n_sites = 1 AND t3.kv_ok THEN t3.lon
    ELSE NULL END AS lon,
  CASE
    WHEN t0.bus_number IS NOT NULL AND t0.n_sites = 1 THEN t0.matched_name
    WHEN t1.bus_number IS NOT NULL AND t1.n_sites = 1 THEN t1.matched_name
    WHEN t2.bus_number IS NOT NULL AND t2.n_sites = 1 AND t2.kv_ok THEN t2.matched_name
    WHEN t3.bus_number IS NOT NULL AND t3.n_sites = 1 AND t3.kv_ok THEN t3.matched_name
    ELSE NULL END AS matched_substation_name,
  CASE
    WHEN t0.bus_number IS NOT NULL AND t0.n_sites = 1 THEN 'pjm_gis'
    WHEN t1.bus_number IS NOT NULL AND t1.n_sites = 1 THEN t1.matched_src
    WHEN t2.bus_number IS NOT NULL AND t2.n_sites = 1 AND t2.kv_ok THEN t2.matched_src
    WHEN t3.bus_number IS NOT NULL AND t3.n_sites = 1 AND t3.kv_ok THEN t3.matched_src
    ELSE NULL END AS matched_source,
  CASE
    WHEN t0.bus_number IS NOT NULL AND t0.n_sites = 1 THEN TRUE
    WHEN t1.bus_number IS NOT NULL AND t1.n_sites = 1 THEN t1.kv_ok
    WHEN t2.bus_number IS NOT NULL AND t2.n_sites = 1 AND t2.kv_ok THEN TRUE
    WHEN t3.bus_number IS NOT NULL AND t3.n_sites = 1 AND t3.kv_ok THEN TRUE
    ELSE NULL END AS kv_consistent,
  CASE
    WHEN t0.bus_number IS NOT NULL AND t0.n_sites = 1 THEN t0.n_sites
    WHEN t1.bus_number IS NOT NULL AND t1.n_sites = 1 THEN t1.n_sites
    WHEN t2.bus_number IS NOT NULL AND t2.n_sites = 1 AND t2.kv_ok THEN t2.n_sites
    WHEN t3.bus_number IS NOT NULL AND t3.n_sites = 1 AND t3.kv_ok THEN t3.n_sites
    ELSE GREATEST(IFNULL(t0.n_sites, 0), IFNULL(t1.n_sites, 0),
                  IFNULL(t2.n_sites, 0), IFNULL(t3.n_sites, 0)) END AS collision_count,
  'AEP (QueueScope owner_label) bus universe; candidate layers restricted to AEP-footprint states'
    AS _universe_note,
  CURRENT_TIMESTAMP() AS _built_at
FROM buses b
LEFT JOIN t0 USING (bus_number)
LEFT JOIN t1 USING (bus_number)
LEFT JOIN t2 USING (bus_number)
LEFT JOIN t3 USING (bus_number)
"""
job = c.query(sql)
job.result()
gb = (job.total_bytes_processed or 0) / 1e9

n = list(c.query(f"SELECT COUNT(*) n FROM `{DEST}`").result())[0].n
print(f"built {DEST}: {n:,} rows (one per distinct AEP bus)")
per = list(c.query(f"""
  SELECT location_method, match_confidence, COUNT(*) n,
         COUNTIF(lat IS NOT NULL) with_coords
  FROM `{DEST}` GROUP BY 1, 2 ORDER BY n DESC""").result())
for r in per:
    print(f"   {r.location_method:26} conf={str(r.match_confidence):5} n={r.n:,} coords={r.with_coords:,}")
located = list(c.query(f"SELECT COUNTIF(lat IS NOT NULL) n FROM `{DEST}`").result())[0].n
print(f"located share: {located:,}/{n:,} = {100*located/n:.1f}%")

register(
    "in_pjm_bus_locations_candidate",
    "DERIVED ladder over: indiana_app.in_pjm_gis_queues (PJM-published points), "
    "energy.nat_substations_hifld + energy.osm_power_substations (AEP-footprint states), "
    "indiana_app.in_pjm_rtep_upgrades (name bridge); universe = energy.pjm_queuescope_results "
    "owner_label='AEP'",
    "tiered name-match ladder, tiers never blended, every row carries location_method + "
    "match_confidence + match_basis + collision_count; kV gate hard for 'high'; buses with no "
    "single-site defensible match keep NULL coords (never guessed); interpolation tier "
    "SKIPPED-BY-MEASUREMENT (QueueScope PSS/E bus numbers join energy.bus_hifld synthetic ids "
    "at 0/1,475)",
    int(n), gb,
    f"One row per distinct AEP QueueScope bus ({n:,}). Located {located:,} = "
    f"{100*located/n:.1f}%. Methods: " + "; ".join(
        f"{r.location_method}/{r.match_confidence}={r.n}" for r in per) +
    ". CANDIDATE table - estimation product, NOT publisher truth; style estimates differently. "
    "T0 'pjm_queue_facid' (added method value) uses PJM's own queue-point coordinates keyed by "
    "FAC_ID name+state+kV; T0 requires >=5-char name overlap AND a FAC code claimed by exactly "
    "one bus-name family (REBUILD: first build's 4-char rule produced false highs - CLIN matched "
    "both CLINCHFLD and CLINTO; this row supersedes the prior registry row for this table). "
    "No Orennia/commercial data touched.")
