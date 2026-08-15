"""A6 — ONE transmission layer, not two partial ones (operator ruling 2026-08-15).

What the measurement found, and it corrects an A2 mistake:

  · SUBSTATIONS WERE ALREADY UNIONED. `in_substations` carries `sources` = HIFLD+OSM (2,354,
    matched at 0.5 m average), OSM-only (933) and HIFLD-only (571), plus `footprint_geojson`
    for 3,287 of the 3,858. A2 added a separate "OSM substation footprints" layer, which was a
    rival partial copy of a merge that already existed — 2,439 of its 2,873 ids were already in
    the union. That layer is removed; instead the existing union now SHOWS its provenance and
    draws its footprints. Read before calling anything a gap: it applied to me here.

  · LINES WERE NOT UNIONED, and the gap is real. HIFLD holds 25,160 km of Indiana transmission;
    OSM holds 14,822 km at >=100 kV, of which 2,706 km has NO HIFLD line within 100 m. That is
    1,114 of 5,013 OSM lines the map never showed — an 11% length gain on the layer the parcel
    screener measures "distance to transmission" against.

Dedupe rule (spatial, and stated): an OSM line is a DUPLICATE if any HIFLD line lies within
100 m of it. Not name-based — 70% of substation names in this estate are blank or UNKNOWN####,
so names cannot carry a merge here. Every row keeps `src` and, for OSM rows, the fact that no
HIFLD counterpart was found.

Creates `in_transmission_union`, registered in the same run.
"""
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
WITH osm AS (
  SELECT CAST(osm_id AS STRING) osm_id, name, operator,
         SAFE_CAST(voltage AS INT64) volts,
         ST_GEOGFROMGEOJSON(geometry_geojson, make_valid => TRUE) g
  FROM `{DS}.in_osm_power_lines`
  WHERE geometry_geojson IS NOT NULL AND SAFE_CAST(voltage AS INT64) >= 100000),
hif AS (SELECT geom g FROM `{DS}.in_transmission_lines` WHERE geom IS NOT NULL),
-- an OSM line with ANY HIFLD line within 100 m is treated as already represented
dupes AS (SELECT DISTINCT o.osm_id FROM osm o JOIN hif h ON ST_DWITHIN(o.g, h.g, 100))
-- HIFLD `voltage` is a DOUBLE in kV; OSM `voltage` is a string in VOLTS. Both are carried
-- verbatim as text in voltage_raw, and normalised to kV in `kv`, so neither is silently rescaled.
SELECT 'hifld' AS src, CAST(t.id AS STRING) AS feature_id, t.owner,
       CAST(t.voltage AS STRING) AS voltage_raw,
       SAFE_CAST(t.voltage AS INT64) AS kv, t.volt_class, t.status, t.sub_1, t.sub_2,
       CAST(NULL AS STRING) AS osm_name,
       'published HIFLD linework' AS merge_note,
       ROUND(ST_LENGTH(t.geom)/1000, 3) AS km, t.geom AS geog
FROM `{DS}.in_transmission_lines` t WHERE t.geom IS NOT NULL
UNION ALL
SELECT 'osm', o.osm_id, o.operator, CAST(o.volts AS STRING),
       CAST(ROUND(o.volts/1000) AS INT64), CAST(NULL AS STRING), CAST(NULL AS STRING),
       CAST(NULL AS STRING), CAST(NULL AS STRING), o.name,
       'OSM only — no HIFLD line within 100 m',
       ROUND(ST_LENGTH(o.g)/1000, 3), o.g
FROM osm o WHERE o.osm_id NOT IN (SELECT osm_id FROM dupes)
"""

dry = client.query(SQL, job_config=bigquery.QueryJobConfig(dry_run=True))
gb = dry.total_bytes_processed / 1e9
print(f"dry-run {gb:.2f} GB")
client.query(f"CREATE OR REPLACE TABLE `{DS}.in_transmission_union` AS\n{SQL}").result()

st = list(client.query(f"""
  SELECT src, COUNT(*) lines, ROUND(SUM(km)) km FROM `{DS}.in_transmission_union`
  GROUP BY 1 ORDER BY km DESC"""))
for s in st: print(f"  {s.src:<6} {s.lines:>6,} lines  {s.km:>8,.0f} km")
n = sum(s.lines for s in st); km = sum(s.km for s in st)
osm_km = next((s.km for s in st if s.src == "osm"), 0)

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_transmission_union'").result()
client.query(f"""INSERT `{DS}._registry`
  (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES (@t,@s,@m,@n,@g,CURRENT_TIMESTAMP(),@o)""",
  job_config=bigquery.QueryJobConfig(query_parameters=[
    bigquery.ScalarQueryParameter("t", "STRING", "in_transmission_union"),
    bigquery.ScalarQueryParameter("s", "STRING",
      "indiana_app.in_transmission_lines + in_osm_power_lines (>=100 kV)"),
    bigquery.ScalarQueryParameter("m", "STRING",
      "spatial union: OSM line kept only when NO HIFLD line lies within 100 m; src retained per row"),
    bigquery.ScalarQueryParameter("n", "INT64", n),
    bigquery.ScalarQueryParameter("g", "FLOAT64", round(gb, 4)),
    bigquery.ScalarQueryParameter("o", "STRING",
      f"ONE transmission layer replacing two partial ones. {km:,.0f} km total; OSM contributes "
      f"{osm_km:,.0f} km that HIFLD does not carry. Dedupe is spatial, not by name - 70% of "
      "substation names in this estate are blank or UNKNOWN####, so names cannot carry a merge. "
      "NOTE substations were ALREADY unioned in in_substations (sources=HIFLD+OSM 2,354 / "
      "OSM 933 / HIFLD 571); no rival substation layer should be built.")])).result()
print(f"in_transmission_union: {n:,} lines, {km:,.0f} km ({osm_km:,.0f} km from OSM alone), registered")
