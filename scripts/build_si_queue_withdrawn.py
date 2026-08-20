"""G53 + G98 - a WITHDRAWN interconnection request as a seller-intent signal, placed.

    python scripts/build_si_queue_withdrawn.py

Operator (G53): *"the owner was interested in placing an energy development there regardless, and
we could then step in with either a DC or BESS development in its place... filterable by date of
withdrawn application."*
Operator (G98): *"Use withdrawn queue projects as an SI signal, so long as they can be address or
coordinate-indexed."*

⭐ THE OPERATOR TURNED THE BLOCKER INTO A GATE, AND THE GATE IS PASSABLE WITHOUT SCRAPING.
G53 sat open for two sessions because the row assumed the address lives in late-stage filings.
It does not have to. The G98 row already spotted the cheaper route, and this build takes it:

  PJM   `in_queue.q_id` joins `in_pjm_gis_queues.QUEUE_ID` - PJM PUBLISHES the queue point's
        coordinate in its own ArcGIS service. No filing parse, no scrape; we already hold it.
  MISO  `in_queue_miso.poiname` names the interconnection substation in words
        ("Cayuga 345 kV Substation", "SCHAHFER GEN STA"), which resolves against
        `in_substations` by the same stem match G114 built for PJM bus labels.

⛔ WHAT THIS BUYS AND WHAT IT DOES NOT, stated before any number, because the difference is the
whole honesty of the signal. A queue point is where the project would have INTERCONNECTED. It is
NOT the parcel the generator would have sat on - those can be a mile apart down a gen-tie. So:

    placed              a published or resolved coordinate exists       -> map it, fly to it
    parcel_under_point  a parcel contains that coordinate               -> a LEAD, not the site
    county_only         no coordinate                                   -> county-grain context

`placement_grain` carries which one, on every row, and a surface that prints a parcel without it
is claiming precision this data does not have.

⛔ A BOUNDING BOX AROUND INDIANA CONTAINS ILLINOIS - trap 6, which sent the map search bar to
Chicago. Points are filtered by ST_CONTAINS against the actual county polygons, never a box.
`in_queue` also carries out-of-state counties (a "Clarke" row belongs to Louisville Gas &
Electric, i.e. Kentucky), so the state test is done on geometry where a coordinate exists and on
the county gazetteer where it does not.

⚠ RECENCY GOVERNS, and this is the operator's own filter. A 2006 withdrawal says almost nothing
about today's owner; a 2026 one is a warm lead. `years_since_withdrawal` ships so the surface can
band it rather than treating a 20-year-old coal cancellation as live intent.

⚠ SIZE IS THE SECOND GATE (G53). The queue MW is the proxy for how much land and interconnection
the owner once contemplated. A withdrawn 5 MW solar project does not imply room for a 300 MW
campus. `capacity_mw` ships on every row for exactly that comparison.

⚠ DOUBLE-COUNT WARNING kept from G53: queued MW is already a county shading (G48), where a
withdrawal reads as BAD for the county. Here the same event reads as GOOD for the parcel. Both
are true; one number must not carry both meanings.

WRITES `indiana_app.in_si_queue_withdrawn`. Reads indiana_app + the public boundary dataset.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_si_queue_withdrawn"
D85 = "080500000047000018"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH cty AS (
  SELECT county_name, geo_id AS county_fips, county_geom AS g
  FROM `bigquery-public-data.geo_us_boundaries.counties`
  WHERE state_fips_code = '18'
),
in_poly AS (SELECT ST_UNION_AGG(g) AS g FROM cty),

-- ---- PJM / LBNL route: the publisher's own queue point -------------------------------------
lbnl AS (
  SELECT q_id, county AS county_text, capacity_mw, resource_type, utility, entity, developer,
         DATE(wd_date) AS wd_date, DATE(queue_date) AS queue_date, region
  FROM `{DS}.in_queue`
  WHERE LOWER(status) = 'withdrawn'
),
gis AS (
  SELECT QUEUE_ID AS q_id, ANY_VALUE(lat) AS lat, ANY_VALUE(lon) AS lon
  FROM `{DS}.in_pjm_gis_queues` WHERE lat IS NOT NULL AND lon IS NOT NULL
  GROUP BY QUEUE_ID
),
pjm AS (
  SELECT l.q_id AS project_id, 'PJM' AS iso, l.county_text, l.capacity_mw, l.resource_type,
         COALESCE(l.utility, l.entity) AS counterparty, l.wd_date, l.queue_date,
         g.lat, g.lon,
         IF(g.lat IS NULL, NULL, 'pjm_published_queue_point') AS location_method,
         CAST(NULL AS STRING) AS poi_name
  FROM lbnl l LEFT JOIN gis g USING (q_id)
),

-- ---- MISO route: the POI substation named in words, resolved on the gazetteer ---------------
mw AS (
  SELECT projectnumber AS project_id, county AS county_text, poiname,
         SAFE_CAST(summernetmw AS FLOAT64) AS capacity_mw,
         fueltype AS resource_type, transmissionowner AS counterparty,
         DATE(SAFE_CAST(withdrawndate AS TIMESTAMP)) AS wd_date,
         DATE(SAFE_CAST(queuedate    AS TIMESTAMP)) AS queue_date
  FROM `{DS}.in_queue_miso`
  WHERE applicationstatus = 'Withdrawn' AND state = 'IN'
),
-- the same stem reduction G114 used on PJM bus labels: drop the voltage, the word
-- SUBSTATION/STATION/SUB, and any trailing noise, then match on the remaining name.
subs AS (
  SELECT UPPER(TRIM(substation_name)) AS nm, ANY_VALUE(lat) AS lat, ANY_VALUE(lon) AS lon,
         COUNT(*) AS collisions
  FROM `{DS}.in_substations` WHERE lat IS NOT NULL GROUP BY nm
),
mw_stem AS (
  SELECT *, UPPER(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(poiname,
             r'(?i)\\b\\d+(\\.\\d+)?\\s*kv\\b', ''),
             r'(?i)\\b(substation|station|sub|gen\\s*sta|generating)\\b', ''))) AS stem
  FROM mw
),
miso AS (
  SELECT m.project_id, 'MISO' AS iso, m.county_text, m.capacity_mw, m.resource_type,
         m.counterparty, m.wd_date, m.queue_date,
         -- ⛔ REFUSE an ambiguous name. A point in the wrong place is worse than no point,
         --    because it is a coordinate someone might drive to (G114's own rule).
         IF(s.collisions = 1, s.lat, NULL) AS lat,
         IF(s.collisions = 1, s.lon, NULL) AS lon,
         IF(s.collisions = 1, 'miso_poi_substation_name', NULL) AS location_method,
         m.poiname AS poi_name
  FROM mw_stem m LEFT JOIN subs s ON s.nm = m.stem
),
u AS (SELECT * FROM pjm UNION ALL SELECT * FROM miso),
placed AS (
  SELECT u.*,
         IF(u.lat IS NULL, FALSE, ST_CONTAINS((SELECT g FROM in_poly),
                                              ST_GEOGPOINT(u.lon, u.lat))) AS point_in_indiana
  FROM u
)
SELECT
  p.project_id, p.iso, p.poi_name, p.county_text, p.capacity_mw, p.resource_type, p.counterparty,
  p.wd_date, p.queue_date,
  DATE_DIFF(CURRENT_DATE(), p.wd_date, YEAR) AS years_since_withdrawal,
  IF(p.point_in_indiana, p.lat, NULL) AS lat,
  IF(p.point_in_indiana, p.lon, NULL) AS lon,
  IF(p.point_in_indiana, p.location_method, NULL) AS location_method,
  s.parcel_source, s.parcel_key, s.parcel_acres, s.occ_group, s.structure_count,
  CASE WHEN s.parcel_key IS NOT NULL      THEN 'parcel_under_point'
       WHEN p.point_in_indiana            THEN 'placed'
       ELSE 'county_only' END             AS placement_grain,
  CURRENT_TIMESTAMP() AS built_at
FROM placed p
LEFT JOIN `{DS}.in_sites` s
  ON p.point_in_indiana
 AND s.parcel_key != '{D85}'                                  -- ⚠ D85 whole-Earth polygon
 AND ST_CONTAINS(s.parcel_geog, ST_GEOGPOINT(p.lon, p.lat))
"""

print("building in_si_queue_withdrawn ...")
job = client.query(SQL)
job.result()
gb = round((job.total_bytes_processed or 0) / 1e9, 3)

s = list(client.query(f"""
  SELECT COUNT(*) rows_, COUNT(DISTINCT project_id) projects,
         COUNTIF(iso='PJM') pjm, COUNTIF(iso='MISO') miso
  FROM `{OUT}`"""))[0]
src = list(client.query(f"""
  SELECT (SELECT COUNT(*) FROM `{DS}.in_queue` WHERE LOWER(status)='withdrawn')
       + (SELECT COUNT(*) FROM `{DS}.in_queue_miso`
          WHERE applicationstatus='Withdrawn' AND state='IN') AS n"""))[0].n
fan = s.rows_ / max(src, 1)
print(f"  {s.rows_} rows from {src} withdrawn requests (fan-out {fan:.2f})   "
      f"PJM/LBNL {s.pjm} · MISO {s.miso}")
assert fan < 1.6, f"FAN-OUT {fan:.2f} - a whole-Earth polygon is probably in the join"

print("\n  ⭐ THE OPERATOR'S GATE: can a withdrawn request be coordinate-indexed?")
for r in client.query(f"""SELECT placement_grain, iso, COUNT(*) n,
                                 COUNT(DISTINCT parcel_key) parcels,
                                 ROUND(SUM(capacity_mw)) mw
                          FROM `{OUT}` GROUP BY 1,2 ORDER BY 1,2"""):
    print(f"    {r.placement_grain:20s} {r.iso:5s} {r.n:>4} requests  "
          f"{(r.parcels or 0):>3} parcels  {int(r.mw or 0):>7,} MW")

pl = list(client.query(f"""SELECT COUNTIF(placement_grain != 'county_only') placed, COUNT(*) tot
                           FROM `{OUT}`"""))[0]
print(f"\n  => {pl.placed} of {pl.tot} ({100.0*pl.placed/pl.tot:.1f}%) carry a real coordinate "
      f"WITHOUT touching a filing. G53's blocker was never the whole story.")

print("\n  the warmest leads - large, recent, and sitting on a parcel:")
for r in client.query(f"""SELECT project_id, iso, county_text, capacity_mw, resource_type,
                                 wd_date, years_since_withdrawal, parcel_key, parcel_acres,
                                 placement_grain
                          FROM `{OUT}`
                          WHERE placement_grain = 'parcel_under_point'
                            AND years_since_withdrawal <= 5
                          ORDER BY capacity_mw DESC LIMIT 10"""):
    print(f"    {r.project_id:10s} {r.iso:5s} {str(r.county_text)[:14]:14s} "
          f"{r.capacity_mw:>7.0f} MW {str(r.resource_type)[:14]:14s} wd {r.wd_date} "
          f"({r.years_since_withdrawal}y)  parcel {r.parcel_key[:20]} "
          f"{r.parcel_acres:.0f} ac" if r.parcel_acres else "")

print("\n  recency bands - a 2006 withdrawal is not a 2026 one:")
for r in client.query(f"""SELECT CASE WHEN years_since_withdrawal <= 2 THEN 'a: 0-2 years'
                                      WHEN years_since_withdrawal <= 5 THEN 'b: 3-5 years'
                                      WHEN years_since_withdrawal <= 10 THEN 'c: 6-10 years'
                                      WHEN years_since_withdrawal IS NULL THEN 'e: no date'
                                      ELSE 'd: over 10 years' END AS band,
                                 COUNT(*) n, ROUND(SUM(capacity_mw)) mw
                          FROM `{OUT}` GROUP BY 1 ORDER BY 1"""):
    print(f"    {r.band:18s} {r.n:>4} requests  {int(r.mw or 0):>8,} MW")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_si_queue_withdrawn',
 'indiana_app.in_queue (LBNL Queued Up 2026), indiana_app.in_pjm_gis_queues (PJM ArcGIS queue '
 'point service), indiana_app.in_queue_miso, indiana_app.in_substations, indiana_app.in_sites; '
 'Indiana polygon from bigquery-public-data.geo_us_boundaries.counties',
 -- ⚠ NO doubled apostrophe here. Inside a multi-line concatenated BigQuery literal, ''
 -- terminates one string and starts the next, and two adjacent literals with no separator is a
 -- syntax error. Reword instead of escaping.
 'PJM/LBNL requests are placed by joining q_id to the PJM published QUEUE_ID coordinate. MISO '
 'requests are placed by reducing poiname to a station stem (voltage and the words '
 'SUBSTATION/STATION/SUB/GEN STA removed) and matching in_substations, REFUSING any name that '
 'matches more than one station. Every point is tested with ST_CONTAINS against the union of the '
 'Indiana county polygons, never a bounding box. placement_grain records whether a row is a '
 'parcel lead, a placed point, or county-only. '
 'RE-SCRAPE COMMAND: python scripts/build_si_queue_withdrawn.py',
 {s.rows_}, {gb}, CURRENT_TIMESTAMP(),
 'G53 + G98. NO SCRAPING: the coordinate route uses data already held, which is what G98 '
 'predicted. A queue point is the INTERCONNECTION point, not the generator parcel - '
 'parcel_under_point is a lead, not the site. Recency and capacity_mw ship on every row because '
 'the operator made both a gate. Double-count warning: the same withdrawal reads as bad for the '
 'county queue (G48) and good for the parcel.'
)""").result()
print("\n  _registry row written")
print("QUEUE WITHDRAWN SIGNAL COMPLETE")
