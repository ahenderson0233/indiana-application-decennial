"""D21 demolition CANDIDATE signal (operator-approved for this app, distinct from the
national engine): join Evansville wrecking permits to the parcel spine by parcel id,
export the matched parcels as a badged overlay. South Bend orders are address-keyed
(80 rows) - county-grain only until an address join is built; recorded, not guessed."""
import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

jr = list(client.query(f"""
WITH ev AS (SELECT UPPER(REGEXP_REPLACE(CAST(USER_Parcel_ID AS STRING), r'[^A-Za-z0-9]', '')) k,
                   USER_Owner AS owner, USER_Project_Activity AS activity,
                   CAST(USER_Application_Recv_d AS STRING) AS observed_date, USER_Location AS location
            FROM `{DS}.in_si_evansville_demolition_permits`
            WHERE USER_Parcel_ID IS NOT NULL),
s AS (SELECT parcel_source, parcel_key,
             UPPER(REGEXP_REPLACE(parcel_key, r'[^A-Za-z0-9]', '')) k
      FROM `{DS}.in_sites`)
SELECT (SELECT COUNT(*) FROM ev) AS ev_rows,
       (SELECT COUNT(DISTINCT ev.k) FROM ev JOIN s USING (k)) AS matched_keys"""))[0]
print(f"evansville D21 join: {jr.matched_keys}/{jr.ev_rows} permit parcels match the spine")

client.query(f"""
CREATE OR REPLACE TABLE `{DS}.in_si_candidates` AS
WITH ev AS (SELECT UPPER(REGEXP_REPLACE(CAST(USER_Parcel_ID AS STRING), r'[^A-Za-z0-9]', '')) k,
                   SUBSTR(REGEXP_REPLACE(CAST(USER_Parcel_ID AS STRING), r'[^0-9]', ''), 1, 10) AS md10,
                   USER_Owner AS owner, USER_Project_Activity AS activity,
                   CAST(USER_Application_Recv_d AS STRING) AS observed_date
            FROM `{DS}.in_si_evansville_demolition_permits`
            WHERE USER_Parcel_ID IS NOT NULL),
s AS (SELECT parcel_source, parcel_key, parcel_geog,
             UPPER(REGEXP_REPLACE(parcel_key, r'[^A-Za-z0-9]', '')) k,
             SUBSTR(REGEXP_REPLACE(parcel_key, r'[^0-9]', ''), 1, 10) AS md10
      FROM `{DS}.in_sites` WHERE parcel_geog IS NOT NULL),
-- md10 is admissible only where it identifies EXACTLY ONE spine parcel (collision guard)
md10_unique AS (SELECT md10 FROM s GROUP BY md10 HAVING COUNT(*) = 1),
exact_m AS (
  SELECT s.parcel_source, s.parcel_key, s.parcel_geog, ev.activity, ev.observed_date, ev.owner,
         'exact' AS match_method, ev.k AS evk
  FROM s JOIN ev USING (k)),
md10_m AS (
  SELECT s.parcel_source, s.parcel_key, s.parcel_geog, ev.activity, ev.observed_date, ev.owner,
         'md10_unique' AS match_method, ev.k AS evk
  FROM ev
  JOIN md10_unique u ON u.md10 = ev.md10
  JOIN s ON s.md10 = ev.md10
  WHERE ev.k NOT IN (SELECT evk FROM exact_m))
SELECT parcel_source, parcel_key, 'D21_demolition' AS candidate_signal,
       'in_si_evansville_demolition_permits' AS candidate_source,
       activity, observed_date, owner, match_method,
       ST_ASGEOJSON(parcel_geog) AS gj
FROM (SELECT * FROM exact_m UNION ALL SELECT * FROM md10_m)""").result()
n = list(client.query(f"SELECT COUNT(*) AS n FROM `{DS}.in_si_candidates`"))[0].n
client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES ('in_si_candidates','in_si_evansville_demolition_permits x in_sites','normalized parcel-id join',
          {n}, 0.5, CURRENT_TIMESTAMP(),
          'CANDIDATE signals for THIS app only - never the national engine; southbend orders are address-keyed, county-grain pending')""").result()
print(f"in_si_candidates: {n:,}")

def rc(x):
    if isinstance(x, float): return round(x, 7)
    if isinstance(x, list): return [rc(v) for v in x]
    return x
feats = []
for r in client.query(f"SELECT * FROM `{DS}.in_si_candidates`"):
    d = dict(r); gj = d.pop("gj")
    feats.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
with gzip.open(os.path.join(REPO, "data", "candidates.geojson.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump({"type": "FeatureCollection", "features": feats}, f, separators=(",", ":"), default=str)
print(f"candidates.geojson.gz: {len(feats)}")
