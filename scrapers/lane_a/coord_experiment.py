"""COORDINATE EXPERIMENT (report-only, per coordinator): AEP QueueScope bus_label vs
indiana_app.in_substations.substation_name. NO wired table is created — findings section only.

Format facts measured first (they shape the result):
  - bus_label is PSS/E-style: '05LEBANO 138 kV (242700)' = 2-digit area + NAME TRUNCATED ~6-8
    chars + kV + bus number. Truncation means exact-equality is expected to undercount.
  - in_substations.substation_name is HIFLD-derived; many are 'UNKNOWN\\d+' placeholders.
Both an exact normalized join (as specified) AND a truncation-aware prefix diagnostic are
measured, both directions, with collision rates and samples.
"""
import os
import sys

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery  # noqa: E402

c = bigquery.Client(project="energy-platfrom")

SQL = r"""
WITH buses AS (
  SELECT DISTINCT bus_label,
    REGEXP_REPLACE(UPPER(TRIM(
      REGEXP_EXTRACT(bus_label, r'^\d{2}(.*?)\s+[0-9.]+\s*[kK][vV]', 1)
    )), r'[^A-Z0-9]', '') AS bus_norm,
    SAFE_CAST(REGEXP_EXTRACT(bus_label, r'\s([0-9.]+)\s*[kK][vV]') AS FLOAT64) AS bus_kv
  FROM `energy-platfrom.energy.pjm_queuescope_results`
  WHERE owner_label = 'AEP' AND bus_label IS NOT NULL
),
subs AS (
  SELECT DISTINCT asset_id, substation_name, city, county, SAFE_CAST(max_kv AS FLOAT64) AS max_kv,
    REGEXP_REPLACE(UPPER(TRIM(REGEXP_REPLACE(UPPER(substation_name),
      r'\b(SUBSTATION|SUB|STATION|SWITCHYARD|SWITCHING|TAP|JUNCTION|JCT|SS)\b', ''))),
      r'[^A-Z0-9]', '') AS sub_norm
  FROM `energy-platfrom.indiana_app.in_substations`
  WHERE substation_name IS NOT NULL AND NOT STARTS_WITH(UPPER(substation_name), 'UNKNOWN')
),
counts AS (
  SELECT
    (SELECT COUNT(DISTINCT bus_norm) FROM buses WHERE bus_norm != '') AS n_bus,
    (SELECT COUNT(DISTINCT bus_label) FROM buses) AS n_bus_labels,
    (SELECT COUNT(DISTINCT sub_norm) FROM subs WHERE sub_norm != '') AS n_sub,
    (SELECT COUNT(DISTINCT asset_id) FROM subs) AS n_sub_assets,
    (SELECT COUNT(DISTINCT asset_id) FROM `energy-platfrom.indiana_app.in_substations`) AS n_sub_total,
    (SELECT COUNT(DISTINCT asset_id) FROM `energy-platfrom.indiana_app.in_substations`
      WHERE STARTS_WITH(UPPER(IFNULL(substation_name,'UNKNOWN')), 'UNKNOWN')) AS n_sub_unknown
),
exact AS (
  SELECT b.bus_label, b.bus_norm, b.bus_kv, s.asset_id, s.substation_name, s.city, s.county, s.max_kv
  FROM buses b JOIN subs s ON s.sub_norm = b.bus_norm AND b.bus_norm != ''
),
prefix AS (
  SELECT b.bus_label, b.bus_norm, b.bus_kv, s.asset_id, s.substation_name, s.city, s.county, s.max_kv
  FROM buses b JOIN subs s
    ON b.bus_norm != '' AND LENGTH(b.bus_norm) >= 5 AND STARTS_WITH(s.sub_norm, b.bus_norm)
)
SELECT 'counts' AS section, TO_JSON_STRING((SELECT AS STRUCT * FROM counts)) AS payload
UNION ALL SELECT 'exact_bus_matched', CAST(COUNT(DISTINCT bus_norm) AS STRING) FROM exact
UNION ALL SELECT 'exact_sub_matched', CAST(COUNT(DISTINCT asset_id) AS STRING) FROM exact
UNION ALL SELECT 'exact_collisions', CAST(COUNT(*) AS STRING) FROM
  (SELECT bus_norm FROM exact GROUP BY bus_norm HAVING COUNT(DISTINCT asset_id) > 1)
UNION ALL SELECT 'prefix_bus_matched', CAST(COUNT(DISTINCT bus_norm) AS STRING) FROM prefix
UNION ALL SELECT 'prefix_sub_matched', CAST(COUNT(DISTINCT asset_id) AS STRING) FROM prefix
UNION ALL SELECT 'prefix_collisions', CAST(COUNT(*) AS STRING) FROM
  (SELECT bus_norm FROM prefix GROUP BY bus_norm HAVING COUNT(DISTINCT asset_id) > 1)
"""
res = {r.section: r.payload for r in c.query(SQL).result()}
import json  # noqa: E402
cnt = json.loads(res["counts"])
n_bus, n_sub = cnt["n_bus"], cnt["n_sub_assets"]
print("=== universe ===")
print(f"AEP distinct bus_labels: {cnt['n_bus_labels']:,} -> distinct normalized names: {n_bus:,}")
print(f"in_substations assets: {cnt['n_sub_total']:,} total; {cnt['n_sub_unknown']:,} are UNKNOWN#### placeholders; "
      f"{n_sub:,} usable-named ({cnt['n_sub']:,} distinct normalized names)")
for tag in ("exact", "prefix"):
    bm, sm, col = int(res[f"{tag}_bus_matched"]), int(res[f"{tag}_sub_matched"]), int(res[f"{tag}_collisions"])
    print(f"=== {tag} join ===")
    print(f"buses matched:        {bm:,}/{n_bus:,} = {100*bm/n_bus:.1f}%")
    print(f"substations matched:  {sm:,}/{n_sub:,} = {100*sm/n_sub:.1f}%")
    print(f"bus norms hitting >1 substation (collisions): {col:,} ({100*col/max(bm,1):.1f}% of matched)")

print("\n=== 10 sample matched pairs (prefix join, for human review) ===")
for r in c.query(r"""
WITH buses AS (
  SELECT DISTINCT bus_label,
    REGEXP_REPLACE(UPPER(TRIM(REGEXP_EXTRACT(bus_label, r'^\d{2}(.*?)\s+[0-9.]+\s*[kK][vV]', 1))),
                   r'[^A-Z0-9]', '') AS bus_norm,
    SAFE_CAST(REGEXP_EXTRACT(bus_label, r'\s([0-9.]+)\s*[kK][vV]') AS FLOAT64) AS bus_kv
  FROM `energy-platfrom.energy.pjm_queuescope_results` WHERE owner_label='AEP'),
subs AS (
  SELECT DISTINCT asset_id, substation_name, city, county, SAFE_CAST(max_kv AS FLOAT64) AS max_kv,
    REGEXP_REPLACE(UPPER(TRIM(REGEXP_REPLACE(UPPER(substation_name),
      r'\b(SUBSTATION|SUB|STATION|SWITCHYARD|SWITCHING|TAP|JUNCTION|JCT|SS)\b',''))),
      r'[^A-Z0-9]','') AS sub_norm
  FROM `energy-platfrom.indiana_app.in_substations`
  WHERE substation_name IS NOT NULL AND NOT STARTS_WITH(UPPER(substation_name),'UNKNOWN'))
SELECT b.bus_label, s.substation_name, s.city, s.county, b.bus_kv, s.max_kv,
       (b.bus_norm = s.sub_norm) AS exact_equal
FROM buses b JOIN subs s
  ON b.bus_norm != '' AND LENGTH(b.bus_norm) >= 5 AND STARTS_WITH(s.sub_norm, b.bus_norm)
ORDER BY RAND() LIMIT 10""").result():
    print(f"  {r.bus_label!r:38} <-> {r.substation_name!r:28} {r.city}/{r.county}"
          f"  bus_kv={r.bus_kv} sub_max_kv={r.max_kv} exact={r.exact_equal}")
