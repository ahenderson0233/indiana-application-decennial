"""Task 1 deliverable: indiana_app.in_miso_poi_identity — poi_name -> bus/kV/coords mapping.

WHY DERIVED, NOT RE-SCRAPED. Registry-first found the identity payload ALREADY HELD:
`energy.miso_poi_attributes` (12,845 rows) is the publisher's complete /POI/api/pois blob from
MISO's own legacy giqueue viewer (giqueue.misoenergy.org), pulled 2026-08-02, vintage
DPP-2021-Cycle per the publisher's own disclaimer. It joins the 904,486-row
miso_poi_monitored_facilities on poi_name at 11,820/11,820 = 100%. Re-scraping a held source is
the exact defect the registry-first rule exists to stop.

CartoVista (cloud.cartovista.com/miso) was RE-PROBED 2026-08-14 (cartovista_miso_probe.py):
metadata routes 200, but geojson / DataRows / dataQueryExecute all still 403 on the
MISO_POIs_2025-11-11 table — identity is NOT served there; it IS served by giqueue.

Footprint-wide as served (all 12,845 POIs, entire MISO footprint), per the brief.
energy dataset is READ-ONLY here: one SELECT, writes go to indiana_app only.
"""
import os
import sys

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google.cloud import bigquery  # noqa: E402

c = bigquery.Client(project="energy-platfrom")
DEST = "energy-platfrom.indiana_app.in_miso_poi_identity"

sql = f"""
CREATE OR REPLACE TABLE `{DEST}` AS
SELECT
  a.poi_name,
  a.bus_number,
  a.bus_name,
  a.kv,
  a.area_code,
  a.area_name,
  a.zip_code,
  a.latitude,            -- NULL where publisher served 0,0 (its own 'unknown')
  a.longitude,
  a.latitude_raw,        -- verbatim, incl. the 0.0 unknowns
  a.longitude_raw,
  a.has_coordinates,
  (m.poi_name IS NOT NULL) AS in_monitored_facilities,   -- keys to the held 904,486-row table
  m.n_facilities,
  a._vintage   AS vintage,          -- OBSERVED EVENT DATE basis: DPP-2021-Cycle model set
  a._pulled_at AS _pulled_at,       -- original giqueue pull time (kept, not overwritten)
  a._source_url AS _source_url,
  CURRENT_TIMESTAMP() AS _built_at,
  'derived from held energy.miso_poi_attributes (giqueue /POI/api/pois, publisher-complete single blob); CartoVista identity routes re-probed 403 on 2026-08-14' AS _method
FROM `energy-platfrom.energy.miso_poi_attributes` a
LEFT JOIN (
  SELECT poi_name, COUNT(*) AS n_facilities
  FROM `energy-platfrom.energy.miso_poi_monitored_facilities`
  GROUP BY poi_name
) m USING (poi_name)
"""
job = c.query(sql)
job.result()
gb = (job.total_bytes_processed or 0) / 1e9

n = list(c.query(f"SELECT COUNT(*) n FROM `{DEST}`").result())[0].n
chk = list(c.query(f"""
  SELECT COUNT(*) nrows, COUNT(DISTINCT poi_name) pois, COUNT(DISTINCT bus_number) busnums,
         COUNTIF(has_coordinates) with_coords, COUNTIF(in_monitored_facilities) in_mf
  FROM `{DEST}`""").result())[0]
print(f"built {DEST}: {n:,} rows")
print(f"   distinct poi_name {chk.pois:,} | distinct bus_number {chk.busnums:,} | "
      f"with coords {chk.with_coords:,} | joined to monitored-facilities {chk.in_mf:,}")
if n != 12845 or chk.pois != n:
    raise RuntimeError(f"ROW CONSERVATION FAILED: expected 12,845 one-per-POI, got {n}/{chk.pois}")

# Register IN THE SAME RUN (indiana_app._registry contract columns).
reg_sql = f"""
INSERT INTO `energy-platfrom.indiana_app._registry`
  (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
  'in_miso_poi_identity',
  'MISO giqueue legacy POI viewer https://giqueue.misoenergy.org/POI/api/pois (via held energy.miso_poi_attributes, pulled 2026-08-02; AES blob the viewer decrypts client-side for every visitor, key ships in the public JS bundle)',
  'derived: SELECT from held energy.miso_poi_attributes LEFT JOIN facility counts from energy.miso_poi_monitored_facilities; registry-first, no re-scrape. CartoVista re-probe 2026-08-14: maps/details+DataColumns 200, geojson/DataRows/dataQueryExecute all 403 (MISO_POIs_2025-11-11, 19,223 rows, ProtectedData) - identity NOT served by CartoVista.',
  {n},
  {gb:.6f},
  CURRENT_TIMESTAMP(),
  'poi_name -> bus_number/bus_name/kV/area/lat-lon, footprint-wide as served: 12,845 POIs, 12,179 distinct bus_number, 9,981 with usable coords (publisher serves 0,0 as its own unknown; flagged, never dropped). Joins energy.miso_poi_monitored_facilities on poi_name at 11,820/11,820 = 100%. VINTAGE DPP-2021-Cycle (publisher disclaimer) - NOT the 2025-11-11 vintage of the protected CartoVista layer; the held DPP2025 geometry-only set is energy.cartovista_miso_poi_locations (8,219 x/y) with energy.miso_poi_location_crosswalk relating the two.'
)
"""
c.query(reg_sql).result()
print("registered in indiana_app._registry (same run)")
