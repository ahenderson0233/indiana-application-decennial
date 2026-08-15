"""Enforce the Indiana border on the PJM payload (queue points were PJM-wide) and
diagnose the parent-grain zero (subparcel structure of Vanderburgh spine keys)."""
import json, gzip, os
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

# 1) parent-grain zero diagnosis: what do Vanderburgh spine subparcels look like?
for r in client.query(f"""
SELECT SUBSTR(REGEXP_REPLACE(parcel_key, r'[^0-9]', ''), 13, 3) AS subparcel, COUNT(*) n
FROM `{DS}.in_sites`
WHERE STARTS_WITH(REGEXP_REPLACE(parcel_key, r'[^0-9]', ''), '82')
GROUP BY 1 ORDER BY n DESC LIMIT 6"""):
    print(f"  spine subparcel '{r.subparcel}': {r.n:,}")
for r in client.query(f"""
WITH ev AS (SELECT DISTINCT UPPER(REGEXP_REPLACE(CAST(USER_Parcel_ID AS STRING), r'[^A-Za-z0-9]', '')) k
  FROM `{DS}.in_si_evansville_demolition_permits` WHERE USER_Parcel_ID IS NOT NULL),
s AS (SELECT DISTINCT UPPER(REGEXP_REPLACE(parcel_key, r'[^A-Za-z0-9]', '')) k,
             SUBSTR(REGEXP_REPLACE(parcel_key, r'[^0-9]', ''), 1, 12) p12 FROM `{DS}.in_sites`),
un AS (SELECT k, SUBSTR(REGEXP_REPLACE(k, r'[^0-9]', ''), 1, 12) p12 FROM ev
       WHERE k NOT IN (SELECT k FROM s))
SELECT COUNT(*) AS unmatched,
       COUNTIF(EXISTS (SELECT 1 FROM s WHERE s.p12 = un.p12)) AS p12_in_spine
FROM un"""):
    print(f"  unmatched={r.unmatched} | parent-12-prefix exists in spine for {r.p12_in_spine}")

# 2) re-export pjm.geojson.gz with queue points clipped to Indiana
with gzip.open(os.path.join(REPO, "data", "pjm.geojson.gz"), "rt", encoding="utf-8") as f:
    fc = json.load(f)
before = len(fc["features"])
kept = []
minx, miny, maxx, maxy = -88.16, 37.75, -84.75, 41.78  # Indiana envelope (generous)
def inside(coords):
    if isinstance(coords[0], (int, float)):
        return minx <= coords[0] <= maxx and miny <= coords[1] <= maxy
    return any(inside(c) for c in coords)
for ft in fc["features"]:
    if ft["properties"].get("layer") != "queue_point" or inside(ft["geometry"]["coordinates"]):
        kept.append(ft)
fc["features"] = kept
with gzip.open(os.path.join(REPO, "data", "pjm.geojson.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(fc, f, separators=(",", ":"))
print(f"pjm.geojson.gz: {before} -> {len(kept)} features (queue points bounded to the Indiana envelope; exact border clip at next BQ export)")
