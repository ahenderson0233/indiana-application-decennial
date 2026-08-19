"""G72/G80 - wire NOAA severe-weather history, one of the 83 objects reaching no surface.

    python scripts/build_severe_weather_county.py

`in_spc_severe_events` holds **24,716 located severe-weather events** across Indiana, 1950-2024,
and nothing in the application rendered a single one of them.

⭐ WHY A SITER CARES, which is the test for whether this should be on a page at all. Tornado and
hail history is a STRUCTURAL DESIGN AND INSURANCE input, not trivia: a campus in a county with
five EF3+ tornadoes since 1950 is hardened and underwritten differently from one that has had
none. It is also the rare county fact that does NOT change with policy - a board can lift a
moratorium, it cannot move the storm track.

WHAT IS COUNTED, and at what grain:
    tornado  1,731 events   the one with a severity scale, so max EF is carried
    hail     7,343
    wind    15,642

⛔ COUNTY GRAIN, DELIBERATELY, AND NOT PER PARCEL. A tornado is a TRACK, not a point, and this
table carries only its start coordinate. Attributing a 40-mile track to the parcel nearest its
start point would be precision we do not have. County frequency is a real planning input; a
per-parcel tornado risk would be an invention.

⚠ `mag = '-9'` IS A NULL SENTINEL on 9 tornadoes, not a magnitude. Treating it as a number would
put an EF-minus-9 in the data and drag every average down. Excluded from the max and counted
separately, the same rule as FEMA's -9999 base flood elevation and HIFLD's -999999 kV.

⚠ COVERAGE IS NOT UNIFORM ACROSS TIME and the surface must not imply it is. Reporting practice
changed enormously between 1950 and 2024 - hail and wind reports especially rise with population
and spotter networks, so a raw all-time count partly measures *observation*, not weather. Both an
all-time count and a since-2000 count are carried so a reader can see that for themselves.

WRITES `indiana_app.in_severe_weather_county`. Reads indiana_app + the public boundary dataset.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_severe_weather_county"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH cty AS (
  SELECT geo_id AS county_geoid, county_name, county_geom AS g
  FROM `bigquery-public-data.geo_us_boundaries.counties`
  WHERE state_fips_code = '18'
),
ev AS (
  SELECT hazard,
         SAFE_CAST(yr AS INT64) AS yr,
         -- ⚠ '-9' is the publisher's "unknown", NOT an EF rating.
         IF(SAFE_CAST(mag AS INT64) >= 0, SAFE_CAST(mag AS INT64), NULL) AS mag,
         SAFE_CAST(inj AS INT64) AS inj, SAFE_CAST(fat AS INT64) AS fat,
         ST_GEOGPOINT(SAFE_CAST(slon AS FLOAT64), SAFE_CAST(slat AS FLOAT64)) AS pt
  FROM `{DS}.in_spc_severe_events`
  WHERE SAFE_CAST(slat AS FLOAT64) IS NOT NULL AND SAFE_CAST(slon AS FLOAT64) IS NOT NULL
),
j AS (
  SELECT c.county_geoid, c.county_name, e.*
  FROM cty c JOIN ev e ON ST_CONTAINS(c.g, e.pt)
)
SELECT
  county_geoid, ANY_VALUE(county_name) AS county_name,
  COUNTIF(hazard = 'torn')                          AS tornado_all,
  COUNTIF(hazard = 'torn' AND yr >= 2000)           AS tornado_since_2000,
  MAX(IF(hazard = 'torn', mag, NULL))               AS tornado_max_ef,
  COUNTIF(hazard = 'torn' AND mag >= 3)             AS tornado_ef3_plus,
  COUNTIF(hazard = 'torn' AND mag IS NULL)          AS tornado_unrated,
  COUNTIF(hazard = 'hail')                          AS hail_all,
  COUNTIF(hazard = 'hail' AND yr >= 2000)           AS hail_since_2000,
  COUNTIF(hazard = 'wind')                          AS wind_all,
  COUNTIF(hazard = 'wind' AND yr >= 2000)           AS wind_since_2000,
  SUM(IFNULL(inj, 0))                               AS injuries,
  SUM(IFNULL(fat, 0))                               AS fatalities,
  MIN(yr) AS first_year, MAX(yr) AS last_year
FROM j
GROUP BY county_geoid
"""

print("building in_severe_weather_county ...")
job = client.query(SQL)
job.result()
gb = round((job.total_bytes_processed or 0) / 1e9, 3)

s = list(client.query(f"""
  SELECT COUNT(*) n, SUM(tornado_all) t, SUM(hail_all) h, SUM(wind_all) w,
         SUM(tornado_ef3_plus) ef3, SUM(tornado_unrated) unrated
  FROM `{OUT}`"""))[0]
print(f"  {s.n} counties, {gb} GB scanned")
print(f"  tornadoes {s.t:,} (EF3+ {s.ef3}, unrated {s.unrated}) · hail {s.h:,} · wind {s.w:,}")
print(f"  total placed: {s.t + s.h + s.w:,} of 24,716 located events")

print("\n  worst counties by EF3+ tornadoes:")
for r in client.query(f"""SELECT county_name, tornado_all, tornado_ef3_plus, tornado_max_ef,
                                 hail_all, wind_all
                          FROM `{OUT}` ORDER BY tornado_ef3_plus DESC, tornado_all DESC LIMIT 8"""):
    print(f"    {r.county_name:16s} tornadoes {r.tornado_all:>3}  EF3+ {r.tornado_ef3_plus:>2}  "
          f"max EF{r.tornado_max_ef}  hail {r.hail_all:>4}  wind {r.wind_all:>4}")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_severe_weather_county',
 'indiana_app.in_spc_severe_events (NOAA Storm Prediction Center), counties from '
 'bigquery-public-data.geo_us_boundaries.counties',
 'events placed by ST_CONTAINS on the event START point; mag = -9 treated as NULL (publisher '
 'unknown, not an EF rating); all-time and since-2000 counts both carried because reporting '
 'practice changed enormously over the window. '
 'RE-SCRAPE COMMAND: python scripts/build_severe_weather_county.py',
 {s.n}, {gb}, CURRENT_TIMESTAMP(),
 'G72/G80. in_spc_severe_events held 24,716 located events and reached NO surface. County grain '
 'deliberately: a tornado is a TRACK and this table carries only its start point, so a per-parcel '
 'risk figure would be invented precision.'
)""").result()
print("\n  _registry row written")
print("SEVERE WEATHER COUNTY COMPLETE")
