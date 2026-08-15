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
-- PARENT-GRAIN TIER (operator-approved 2026-08-15): Indiana 18-digit keys are
-- county(2)-twp(2)-sec(2)-block(3)-parcel(3).subparcel(3)-district(3). A permit on a
-- child parcel absent from the statewide layer is placed on its PARENT (subparcel 000),
-- labeled parent_grain — a coarser location tier, never styled as exact.
-- Indiana spines carry no .000 parent rows (measured: subparcels start at .001), so the
-- family representative = the spine parcel sharing the permit's 12-digit prefix. Placed
-- only when the family is a SINGLE spine parcel, or on the lowest-subparcel member with
-- family_size disclosed — never styled as exact.
families AS (
  SELECT SUBSTR(REGEXP_REPLACE(parcel_key, r'[^0-9]', ''), 1, 12) AS p12,
         ARRAY_AGG(STRUCT(parcel_source, parcel_key, parcel_geog)
                   ORDER BY parcel_key LIMIT 1)[OFFSET(0)] AS rep,
         COUNT(*) AS family_size
  FROM `{DS}.in_sites` WHERE parcel_geog IS NOT NULL
  GROUP BY 1),
parent_m AS (
  SELECT f.rep.parcel_source, f.rep.parcel_key, f.rep.parcel_geog,
         ev.activity, ev.observed_date, ev.owner,
         CONCAT('parent_family_of_', CAST(f.family_size AS STRING)) AS match_method,
         ev.k AS evk
  FROM ev
  JOIN families f ON f.p12 = SUBSTR(REGEXP_REPLACE(ev.k, r'[^0-9]', ''), 1, 12)
  WHERE ev.k NOT IN (SELECT evk FROM exact_m))
SELECT c.parcel_source, c.parcel_key, 'D21_demolition' AS candidate_signal,
       'in_si_evansville_demolition_permits' AS candidate_source,
       c.activity, c.observed_date, c.owner, c.match_method, si.occ_group,
       ST_ASGEOJSON(c.parcel_geog) AS gj
FROM (SELECT * FROM exact_m UNION ALL SELECT * FROM parent_m) c
LEFT JOIN (SELECT parcel_source, parcel_key, occ_group FROM `{DS}.in_sites`) si
  USING (parcel_source, parcel_key)""").result()
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
