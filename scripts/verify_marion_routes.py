"""Do the TWO INDEPENDENT Marion routes agree about which parcel an abandoned building sits on?

Route A  key crosswalk    PARCEL_I -> STATEPARCELNUMBER (sde_Parcel layer 5, 347,049 parcels)
Route B  polygon geometry the building footprint itself, spatially contained by a parcel

They share no mechanism: one is a published key mapping, the other is geography. Where they
agree, the placement is corroborated by two instruments. Where they DISAGREE, that is a finding
to report — not something to quietly resolve in favour of whichever is more convenient.

Writes `in_si_marion_route_check` and registers it in the same run.
D85 excluded: the whole-Earth polygon would "contain" every point on the planet.
"""
import datetime
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
D85 = "080500000047000018"
client = bigquery.Client(project="energy-platfrom")
BUILT = datetime.datetime.now(datetime.timezone.utc).isoformat()

SQL = f"""
CREATE OR REPLACE TABLE `{DS}.in_si_marion_route_check` AS
WITH xw AS (
  SELECT DISTINCT PARCEL_I loc, REGEXP_REPLACE(STATEPARCELNUMBER, r'[^0-9]','') st
  FROM `{DS}.in_marion_parcel_crosswalk`
  WHERE PARCEL_I IS NOT NULL AND STATEPARCELNUMBER IS NOT NULL),
geo AS (
  SELECT PARCEL_I loc, ADDRESS, CITY, STATUS,
         ST_CENTROID(SAFE.ST_GEOGFROMGEOJSON(geometry_json, make_valid => TRUE)) pt
  FROM `{DS}.in_si_indy_abandoned_vacant_spatial` WHERE geometry_json IS NOT NULL),
spatial_hit AS (
  SELECT g.loc, g.ADDRESS, g.CITY, g.STATUS, s.parcel_key spatial_key
  FROM geo g
  LEFT JOIN `{DS}.in_sites` s
    ON s.parcel_key != '{D85}' AND ST_CONTAINS(s.parcel_geog, g.pt)
)
SELECT h.loc AS parcel_local_id, h.ADDRESS address, h.CITY city, h.STATUS status,
       xw.st  AS crosswalk_key,
       h.spatial_key,
       CASE WHEN xw.st IS NULL AND h.spatial_key IS NULL THEN 'neither route placed it'
            WHEN xw.st IS NULL                            THEN 'geometry only'
            WHEN h.spatial_key IS NULL                    THEN 'crosswalk only'
            WHEN xw.st = h.spatial_key                    THEN 'AGREE'
            ELSE 'DISAGREE' END AS verdict,
       TIMESTAMP('{BUILT}') AS built_at
FROM spatial_hit h LEFT JOIN xw ON xw.loc = h.loc
"""
job = client.query(SQL); job.result()
print(f"built in_si_marion_route_check ({job.total_bytes_processed/1e9:.2f} GB)")

print("\n--- do the two routes agree? ---")
tot = 0
for r in client.query(f"""SELECT verdict, COUNT(*) n FROM `{DS}.in_si_marion_route_check`
                          GROUP BY 1 ORDER BY n DESC"""):
    print(f"  {r.verdict:26s} {r.n:>6,}")
    tot += r.n
agree = list(client.query(f"""SELECT COUNTIF(verdict='AGREE') a, COUNTIF(verdict='DISAGREE') d
    FROM `{DS}.in_si_marion_route_check`"""))[0]
both = agree.a + agree.d
print(f"\n  where BOTH routes placed it: {both:,} · agreement "
      f"{100*agree.a/max(both,1):.2f}%")
if agree.d:
    print("  disagreements (first 5) — reported, not resolved by preference:")
    for r in client.query(f"""SELECT parcel_local_id, address, crosswalk_key, spatial_key
        FROM `{DS}.in_si_marion_route_check` WHERE verdict='DISAGREE' LIMIT 5"""):
        print(f"    {r.parcel_local_id} {str(r.address)[:28]:28s} "
              f"xw={r.crosswalk_key} geo={r.spatial_key}")

n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_si_marion_route_check`"))[0].n
client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_si_marion_route_check'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at) "
    f"VALUES (@t,@s,@m,@n,CURRENT_TIMESTAMP())",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "in_si_marion_route_check"),
        bigquery.ScalarQueryParameter(
            "s", "STRING",
            "indiana_app.in_marion_parcel_crosswalk + in_si_indy_abandoned_vacant_spatial + in_sites"),
        bigquery.ScalarQueryParameter(
            "m", "STRING",
            "Two-instrument check on Marion placement: the published local->state key mapping "
            "versus ST_CONTAINS of the building's own polygon centroid. The routes share no "
            "mechanism, so agreement is corroboration and disagreement is a finding. D85 excluded."),
        bigquery.ScalarQueryParameter("n", "INT64", int(n))])).result()
print(f"registered in_si_marion_route_check ({n:,})")
