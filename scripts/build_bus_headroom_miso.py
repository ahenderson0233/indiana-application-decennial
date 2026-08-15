"""in_bus_headroom_miso: per-POI MISO headroom, made plottable via in_miso_poi_identity.

Headroom = MIN(mw_available) across a POI's monitored facilities (the PJM-proven
derivation). Identity/coords come from the publisher's own POI API (DPP-2021-Cycle
vintage, per its disclaimer). Indiana slice by point-in-state on PUBLISHER coordinates;
rows whose published coords are the publisher's 0,0 "unknown" are kept statewide-agnostic
in the national table and counted, never guessed onto the map.
"""
from google.cloud import bigquery

client = bigquery.Client(project="energy-platfrom")
DS = "energy-platfrom.indiana_app"
ST = ("(SELECT state_geom FROM `bigquery-public-data.geo_us_boundaries.states` "
      "WHERE state = 'IN')")

sql = f"""
CREATE OR REPLACE TABLE `{DS}.in_bus_headroom_miso` AS
WITH headroom AS (
  -- The probe ran at _pmax_request_mw=99999 (an effectively infinite request), so a
  -- bare MIN reads 0 on 88% of POIs. Keep WORST and BEST and the binding facility;
  -- never fuse them into one number (the platform's mat_bus_headroom pattern).
  SELECT poi_name,
         -- THE single representative number (operator ruling 2026-08-15): MIN over
         -- facilities a realistic request actually stresses (|dfax| >= 5%, the standard
         -- study cutoff) — removes infinite-probe zeros from remote constraints.
         MIN(IF(ABS(SAFE_CAST(percent_dfax AS FLOAT64)) >= 5,
                SAFE_CAST(mw_available AS FLOAT64), NULL)) AS headroom_mw,
         MIN(SAFE_CAST(mw_available AS FLOAT64)) AS worst_mw,
         MAX(SAFE_CAST(mw_available AS FLOAT64)) AS best_mw,
         APPROX_QUANTILES(SAFE_CAST(mw_available AS FLOAT64), 2)[OFFSET(1)] AS median_mw,
         COUNTIF(SAFE_CAST(mw_available AS FLOAT64) = 0) AS facilities_at_zero,
         COUNT(*) AS monitored_facilities,
         ARRAY_AGG(monitored_facility ORDER BY SAFE_CAST(mw_available AS FLOAT64) ASC LIMIT 1)[OFFSET(0)] AS worst_binding_facility,
         ANY_VALUE(_vintage) AS vintage,
         MAX(_pulled_at) AS pulled_at
  FROM `energy-platfrom.energy.miso_poi_monitored_facilities`
  GROUP BY poi_name
),
ident AS (
  SELECT poi_name, bus_number, bus_name, kv, area_name,
         latitude AS lat, longitude AS lon,
         (has_coordinates IS TRUE
          AND NOT (latitude = 0 AND longitude = 0)) AS has_real_coords
  FROM `{DS}.in_miso_poi_identity`
)
SELECT h.poi_name, i.bus_number, i.bus_name, i.kv, i.area_name,
       h.headroom_mw, h.worst_mw, h.best_mw, h.median_mw, h.facilities_at_zero,
       h.worst_binding_facility, h.monitored_facilities, h.vintage, h.pulled_at,
       i.lat, i.lon, i.has_real_coords,
       CASE
         WHEN i.poi_name IS NULL THEN 'unjoined'
         WHEN NOT i.has_real_coords THEN 'joinable_no_coords'
         WHEN ST_CONTAINS({ST}, ST_GEOGPOINT(i.lon, i.lat)) THEN 'indiana'
         ELSE 'outside_indiana'
       END AS location_status
FROM headroom h
LEFT JOIN ident i USING (poi_name)
"""
job = client.query(sql)
job.result()
gb = (job.total_bytes_processed or 0) / 1e9

counts = list(client.query(f"""
SELECT location_status, COUNT(*) AS n,
       COUNTIF(worst_mw > 0) AS worst_positive,
       COUNTIF(median_mw > 0) AS median_positive,
       COUNTIF(best_mw > 0) AS best_positive
FROM `{DS}.in_bus_headroom_miso` GROUP BY 1 ORDER BY n DESC"""))
n = sum(r.n for r in counts)
for r in counts:
    print(f"{r.location_status:20s} pois={r.n:,} worst>0={r.worst_positive:,} "
          f"median>0={r.median_positive:,} best>0={r.best_positive:,}")

# a zero-check control: Indiana must not be zero (MISO covers most of the state)
indiana = next((r.n for r in counts if r.location_status == "indiana"), 0)
assert indiana > 0, "Indiana POI count is zero - suspect the join, then the filter, then the data"

client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES ('in_bus_headroom_miso',
          'energy.miso_poi_monitored_facilities x indiana_app.in_miso_poi_identity',
          'worst/best/median mw_available per POI + publisher coords join',
          {n}, {gb:.3f}, CURRENT_TIMESTAMP(),
          'probe ran at pmax_request=99999 so worst_mw=0 on ~88 pct of POIs - display worst AND best, never one fused number; vintage DPP-2021-Cycle per publisher disclaimer')""").result()
print(f"registered in_bus_headroom_miso: {n:,} POIs ({gb:.2f} GB)")
