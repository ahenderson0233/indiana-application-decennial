import os, sys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery
c = bigquery.Client(project="energy-platfrom")

SQL = r"""
WITH buses AS (
  SELECT DISTINCT
    REGEXP_REPLACE(UPPER(TRIM(REGEXP_EXTRACT(bus_label, r'^\d{2}(.*?)\s+[0-9.]+\s*[kK][vV]', 1))),
                   r'[^A-Z0-9]', '') AS bus_norm,
    ANY_VALUE(bus_label) AS bus_label,
    SAFE_CAST(REGEXP_EXTRACT(bus_label, r'\s([0-9.]+)\s*[kK][vV]') AS FLOAT64) AS bus_kv
  FROM `energy-platfrom.energy.pjm_queuescope_results`
  WHERE owner_label='AEP' AND bus_label IS NOT NULL
  GROUP BY bus_norm, bus_kv
),
hifld AS (
  SELECT 'HIFLD' AS src, id, name, city, county,
    SAFE_CAST(latitude AS FLOAT64) AS lat, SAFE_CAST(longitude AS FLOAT64) AS lon,
    SAFE_CAST(max_volt AS FLOAT64) AS max_kv, SAFE_CAST(min_volt AS FLOAT64) AS min_kv,
    (max_infer='Y' OR min_infer='Y') AS kv_inferred,
    REGEXP_REPLACE(UPPER(TRIM(REGEXP_REPLACE(UPPER(name),
      r'\b(SUBSTATION|SUB|STATION|SWITCHYARD|SWITCHING|TAP|JUNCTION|JCT|SS)\b',''))),
      r'[^A-Z0-9]','') AS sub_norm
  FROM `energy-platfrom.energy.nat_substations_hifld`
  WHERE state='IN' AND name IS NOT NULL AND NOT REGEXP_CONTAINS(UPPER(name), r'^(UNKNOWN|TAP)\d*$')
),
osm AS (
  SELECT 'OSM' AS src, osm_id AS id, COALESCE(NULLIF(name,''), operator) AS name,
    CAST(NULL AS STRING) AS city, CAST(NULL AS STRING) AS county,
    COALESCE(SAFE_CAST(latitude AS FLOAT64),
             ST_Y(ST_CENTROID(SAFE.ST_GEOGFROMGEOJSON(geometry_geojson)))) AS lat,
    COALESCE(SAFE_CAST(longitude AS FLOAT64),
             ST_X(ST_CENTROID(SAFE.ST_GEOGFROMGEOJSON(geometry_geojson)))) AS lon,
    (SELECT MAX(SAFE_CAST(v AS FLOAT64))/1000 FROM UNNEST(SPLIT(IFNULL(voltage,''),';')) v) AS max_kv,
    (SELECT MIN(SAFE_CAST(v AS FLOAT64))/1000 FROM UNNEST(SPLIT(IFNULL(voltage,''),';')) v) AS min_kv,
    FALSE AS kv_inferred,
    REGEXP_REPLACE(UPPER(TRIM(REGEXP_REPLACE(UPPER(COALESCE(NULLIF(name,''), operator,'')),
      r'\b(SUBSTATION|SUB|STATION|SWITCHYARD|SWITCHING|TAP|JUNCTION|JCT|SS)\b',''))),
      r'[^A-Z0-9]','') AS sub_norm
  FROM `energy-platfrom.energy.osm_power_substations`
  WHERE state_scraped='IN' AND COALESCE(NULLIF(name,''), NULLIF(operator,'')) IS NOT NULL
),
subs AS (SELECT * FROM hifld UNION ALL SELECT * FROM osm),
wireable AS (
  SELECT b.bus_norm, b.bus_label, b.bus_kv, s.src, s.id, s.name, s.city, s.county,
         s.lat, s.lon, s.min_kv, s.max_kv, s.kv_inferred
  FROM buses b JOIN subs s ON b.bus_norm != '' AND s.sub_norm = b.bus_norm
  WHERE b.bus_kv BETWEEN s.min_kv - 1 AND s.max_kv + 1
)
SELECT * FROM wireable ORDER BY bus_norm, src
"""
rows = list(c.query(SQL).result())
import collections
bus_srcs = collections.defaultdict(set)
bus_sites = collections.defaultdict(set)
for r in rows:
    bus_srcs[r.bus_norm].add(r.src)
    bus_sites[r.bus_norm].add((round(r.lat, 3), round(r.lon, 3)))
n_union = len(bus_srcs)
both = sum(1 for v in bus_srcs.values() if len(v) == 2)
agree = sum(1 for k in bus_srcs if len(bus_srcs[k]) == 2 and len(bus_sites[k]) == 1)
multi_site = sum(1 for v in bus_sites.values() if len(v) > 1)
print(f"UNION wireable tier (exact name + kV-validated, IN): {n_union} distinct buses")
print(f"  found in both HIFLD and OSM: {both}; of those, coordinates agree to ~100m: {agree}")
print(f"  buses with >1 distinct site among matches (needs review): {multi_site}")
print("\nsamples:")
seen = set()
for r in rows:
    if r.bus_norm in seen: continue
    seen.add(r.bus_norm)
    print(f"  {r.bus_label!r:36} <-> [{r.src}] {r.name!r:26} {r.city or ''}/{r.county or ''} "
          f"kv {r.bus_kv} in [{r.min_kv},{r.max_kv}]{' inf' if r.kv_inferred else ''} "
          f"@({r.lat:.4f},{r.lon:.4f})")
    if len(seen) >= 10: break
