"""ANGLE 1 (in-warehouse): AEP QueueScope bus names vs HIFLD and OSM substation layers.

Fixes measured defects of experiment 1:
  - candidate layer: in_substations was 66% UNKNOWN#### -> use energy.nat_substations_hifld
    (real names) and energy.osm_power_substations (name/operator tags), IN slices.
  - denominator: AEP's zone spans ~IN,MI,OH,WV,VA,KY,TN — an IN-only candidate set bounds the
    bus-side match rate by the (unknown) IN share of AEP buses. Both panels are reported:
    AEP-states ceiling (method quality) and IN-only (the siting product).
  - validator: bus kV must be consistent with the station's kV range/list (coordinator's rule:
    a 138 bus must land in a station carrying 138). HIFLD *_infer='Y' voltages are counted but
    flagged in the validated-rate note.
REPORT ONLY. Nothing wired.
"""
import os
import sys

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery  # noqa: E402

c = bigquery.Client(project="energy-platfrom")

BUSES = r"""
buses AS (
  SELECT DISTINCT bus_label,
    REGEXP_REPLACE(UPPER(TRIM(REGEXP_EXTRACT(bus_label, r'^\d{2}(.*?)\s+[0-9.]+\s*[kK][vV]', 1))),
                   r'[^A-Z0-9]', '') AS bus_norm,
    SAFE_CAST(REGEXP_EXTRACT(bus_label, r'\s([0-9.]+)\s*[kK][vV]') AS FLOAT64) AS bus_kv
  FROM `energy-platfrom.energy.pjm_queuescope_results`
  WHERE owner_label = 'AEP' AND bus_label IS NOT NULL
)"""

HIFLD = r"""
subs AS (
  SELECT id, name, city, state, county, latitude AS lat, longitude AS lon,
    SAFE_CAST(max_volt AS FLOAT64) AS max_kv, SAFE_CAST(min_volt AS FLOAT64) AS min_kv,
    (max_infer = 'Y' OR min_infer = 'Y') AS kv_inferred,
    REGEXP_REPLACE(UPPER(TRIM(REGEXP_REPLACE(UPPER(name),
      r'\b(SUBSTATION|SUB|STATION|SWITCHYARD|SWITCHING|TAP|JUNCTION|JCT|SS)\b', ''))),
      r'[^A-Z0-9]', '') AS sub_norm
  FROM `energy-platfrom.energy.nat_substations_hifld`
  WHERE state IN ({states})
    AND name IS NOT NULL
    AND NOT REGEXP_CONTAINS(UPPER(name), r'^(UNKNOWN|TAP)\d*$')
)"""

OSM = r"""
subs AS (
  SELECT osm_id AS id,
    COALESCE(NULLIF(name, ''), NULLIF(operator, '')) AS name,
    CAST(NULL AS STRING) AS city, state_scraped AS state, CAST(NULL AS STRING) AS county,
    COALESCE(SAFE_CAST(latitude AS FLOAT64),
             ST_Y(ST_CENTROID(SAFE.ST_GEOGFROMGEOJSON(geometry_geojson)))) AS lat,
    COALESCE(SAFE_CAST(longitude AS FLOAT64),
             ST_X(ST_CENTROID(SAFE.ST_GEOGFROMGEOJSON(geometry_geojson)))) AS lon,
    (SELECT MAX(SAFE_CAST(v AS FLOAT64))/1000 FROM UNNEST(SPLIT(IFNULL(voltage,''), ';')) v)
      AS max_kv,
    (SELECT MIN(SAFE_CAST(v AS FLOAT64))/1000 FROM UNNEST(SPLIT(IFNULL(voltage,''), ';')) v)
      AS min_kv,
    FALSE AS kv_inferred,
    REGEXP_REPLACE(UPPER(TRIM(REGEXP_REPLACE(UPPER(COALESCE(NULLIF(name,''), operator, '')),
      r'\b(SUBSTATION|SUB|STATION|SWITCHYARD|SWITCHING|TAP|JUNCTION|JCT|SS)\b', ''))),
      r'[^A-Z0-9]', '') AS sub_norm
  FROM `energy-platfrom.energy.osm_power_substations`
  WHERE state_scraped IN ({states})
    AND COALESCE(NULLIF(name, ''), NULLIF(operator, '')) IS NOT NULL
)"""

METRICS = r"""
, matched AS (
  SELECT b.bus_label, b.bus_norm, b.bus_kv, s.id, s.name, s.city, s.county, s.state,
         s.lat, s.lon, s.max_kv, s.min_kv, s.kv_inferred,
         (b.bus_norm = s.sub_norm) AS exact_eq,
         (b.bus_kv IS NOT NULL AND s.max_kv IS NOT NULL
          AND b.bus_kv BETWEEN s.min_kv - 1 AND s.max_kv + 1) AS kv_ok
  FROM buses b JOIN subs s
    ON b.bus_norm != '' AND LENGTH(b.bus_norm) >= 5
   AND (s.sub_norm = b.bus_norm OR STARTS_WITH(s.sub_norm, b.bus_norm))
)
SELECT
  (SELECT COUNT(DISTINCT bus_norm) FROM buses WHERE bus_norm != '') AS n_bus,
  (SELECT COUNT(DISTINCT id) FROM subs) AS n_sub,
  COUNT(DISTINCT IF(exact_eq, bus_norm, NULL)) AS bus_exact,
  COUNT(DISTINCT bus_norm) AS bus_prefix,
  COUNT(DISTINCT IF(exact_eq, id, NULL)) AS sub_exact,
  COUNT(DISTINCT id) AS sub_prefix,
  COUNT(DISTINCT IF(exact_eq AND kv_ok, bus_norm, NULL)) AS bus_exact_kvok,
  COUNT(DISTINCT IF(kv_ok, bus_norm, NULL)) AS bus_prefix_kvok,
  (SELECT COUNT(*) FROM (SELECT bus_norm FROM matched WHERE exact_eq GROUP BY bus_norm
                         HAVING COUNT(DISTINCT id) > 1)) AS exact_collisions,
  (SELECT COUNT(*) FROM (SELECT bus_norm FROM matched GROUP BY bus_norm
                         HAVING COUNT(DISTINCT id) > 1)) AS prefix_collisions,
  (SELECT COUNT(*) FROM (SELECT bus_norm FROM matched WHERE exact_eq AND kv_ok GROUP BY bus_norm
                         HAVING COUNT(DISTINCT id) > 1)) AS exact_kvok_collisions
FROM matched
"""

AEP_STATES = "'IN','MI','OH','WV','VA','KY','TN'"
IN_ONLY = "'IN'"

for label, layer_sql in (("HIFLD", HIFLD), ("OSM", OSM)):
    for states_label, states in (("AEP-states", AEP_STATES), ("IN-only", IN_ONLY)):
        sql = "WITH " + BUSES.strip().lstrip("buses AS").join([]) or ""
        sql = "WITH " + BUSES.strip() + ", " + layer_sql.format(states=states).strip() + METRICS
        r = list(c.query(sql).result())[0]
        d = dict(r)
        nb, ns = d["n_bus"], d["n_sub"]
        print(f"=== {label} / {states_label}: {ns:,} named candidate substations, {nb:,} bus names")
        print(f"    exact:  bus {d['bus_exact']:,}/{nb:,} = {100*d['bus_exact']/nb:.1f}%   "
              f"sub {d['sub_exact']:,}   collisions {d['exact_collisions']:,}")
        print(f"    prefix: bus {d['bus_prefix']:,}/{nb:,} = {100*d['bus_prefix']/nb:.1f}%   "
              f"sub {d['sub_prefix']:,}   collisions {d['prefix_collisions']:,}")
        print(f"    kV-validated: exact {d['bus_exact_kvok']:,} "
              f"({100*d['bus_exact_kvok']/nb:.1f}%), collisions {d['exact_kvok_collisions']:,}; "
              f"prefix {d['bus_prefix_kvok']:,} ({100*d['bus_prefix_kvok']/nb:.1f}%)")

# 10 samples: HIFLD IN-only, exact + kv_ok (the wireable-quality tier)
sample_sql = "WITH " + BUSES.strip() + ", " + HIFLD.format(states=IN_ONLY).strip() + r"""
SELECT b.bus_label, s.name, s.city, s.county, b.bus_kv, s.min_kv, s.max_kv, s.kv_inferred,
       s.lat, s.lon
FROM buses b JOIN subs s ON b.bus_norm != '' AND s.sub_norm = b.bus_norm
WHERE b.bus_kv BETWEEN s.min_kv - 1 AND s.max_kv + 1
ORDER BY RAND() LIMIT 10"""
print("\n=== 10 samples: HIFLD IN-only, EXACT name + kV-validated ===")
for r in c.query(sample_sql).result():
    print(f"  {r.bus_label!r:36} <-> {r.name!r:22} {r.city}/{r.county} "
          f"kv {r.bus_kv} in [{r.min_kv},{r.max_kv}]{' (inferred)' if r.kv_inferred else ''} "
          f"@({r.lat:.4f},{r.lon:.4f})")
