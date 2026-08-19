"""G48 input - how many operating data centres sit in each Indiana county.

    python scripts/build_dc_county_counts.py

⛔ WHY THIS IS A BUILD AND NOT PART OF THE EXPORTER. `in_data_centers_all` carries no county, only
lat/lon, so the county has to come from a spatial join against `energy.county_boundaries`. The
first version of G48 did that join inside `export_grid_sentiment.py` and the checkpoint caught it
immediately:

    X no EXPORT reads energy directly: ['scripts/export_grid_sentiment.py']

That rule is not bureaucracy. An export is on the path to what the user sees, so if an export
needs the platform's dataset then the app cannot be rebuilt without it. Build scripts may read
`energy`; exports may not. The documented pattern is: clip the slice into `indiana_app`, register
it in the same run, and let the export read the clip. That is what this does.

⚠ A NAME MATCH WOULD BE WRONG HERE. Joining data centres to counties by name is the
CLOUDSCENE_GAP mistake -- eight fabricated matches, including two different companies joined
because they shared a city. ST_CONTAINS against the publisher's own boundary, or nothing.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import datetime
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
TARGET = "in_dc_county_counts"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{DS}.{TARGET}` AS
SELECT c.GEOID           AS county_geoid,
       c.NAME            AS county_name,
       COUNT(*)          AS data_centres,
       COUNT(DISTINCT d.operator) AS operators,
       CURRENT_TIMESTAMP() AS built_at
FROM `{DS}.in_data_centers_all` d
JOIN `energy-platfrom.energy.county_boundaries` c
  ON ST_CONTAINS(c.geom, ST_GEOGPOINT(d.lon, d.lat))
WHERE c.STATEFP = '18' AND d.lat IS NOT NULL AND d.lon IS NOT NULL
GROUP BY 1, 2
"""
job = client.query(SQL)
job.result()
print(f"{TARGET} built: {job.total_bytes_processed / 1e9:.2f} GB scanned")

r = list(client.query(f"""
  SELECT COUNT(*) counties, SUM(data_centres) dcs,
         (SELECT COUNT(*) FROM `{DS}.in_data_centers_all` WHERE lat IS NOT NULL) placeable
  FROM `{DS}.{TARGET}`"""))[0]
print(f"  {r.dcs:,} of {r.placeable:,} located data centres fell inside a county, "
      f"across {r.counties} counties")
# a point that lands in no county is a finding, not a rounding error -- say so rather than let the
# difference sit unexplained
if r.dcs != r.placeable:
    print(f"  ⚠ {r.placeable - r.dcs} located data centre(s) fell in NO Indiana county -- "
          f"out of state, or a coordinate defect. Not silently dropped: counted here.")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name=@t",
             job_config=bigquery.QueryJobConfig(query_parameters=[
                 bigquery.ScalarQueryParameter("t", "STRING", TARGET)])).result()
client.query(
    f"""INSERT INTO `{DS}._registry`
        (table_name, source, method, n_rows, gb_scanned, built_at, notes)
        VALUES (@t, @s, @m, @n, @g, CURRENT_TIMESTAMP(), @notes)""",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", TARGET),
        bigquery.ScalarQueryParameter(
            "s", "STRING",
            "indiana_app.in_data_centers_all x energy.county_boundaries (STATEFP='18')"),
        bigquery.ScalarQueryParameter(
            "m", "STRING",
            "ST_CONTAINS(county.geom, ST_GEOGPOINT(dc.lon, dc.lat)) -- SPATIAL, never a name "
            "match (a name match is the CLOUDSCENE_GAP defect). Exists so that "
            "export_grid_sentiment.py can shade a county green for an operating data centre "
            "WITHOUT an export reading `energy` directly. "
            "RE-SCRAPE COMMAND: python scripts/build_dc_county_counts.py"),
        bigquery.ScalarQueryParameter("n", "INT64", int(r.counties)),
        bigquery.ScalarQueryParameter("g", "FLOAT64", (job.total_bytes_processed or 0) / 1e9),
        bigquery.ScalarQueryParameter(
            "notes", "STRING",
            f"G48 input. {r.dcs} located data centres across {r.counties} counties. "
            f"Excludes rows with no coordinate.")])).result()
print(f"_registry row written for {TARGET}")
