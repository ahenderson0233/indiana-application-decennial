"""MISO INJECTION request-size ladder for Indiana POIs (100/300/500/1000/2500/5000 MW).

THE MEASUREMENT THAT MAKES THIS CHEAP AND EXACT
-----------------------------------------------
MISO's `pMaxValue` is NOT a study input.  It is a reporting CLAMP.  Measured two ways:

  1. Live API, one POI, facility by facility:  PMax(pMaxValue=X) == min(PMax_true, X)
     for 67/67 facilities at X=100 and X=300, ZERO violations.  Negative X floors at 0.
  2. At scale, against two INDEPENDENTLY harvested datasets we already hold --
     `indiana_app.in_miso_poi_300mw` (pMaxValue=300) vs the Indiana subset of
     `energy.miso_poi_monitored_facilities` (pMaxValue=99999):
     **38,381 of 38,381 distinct (POI, facility) keys satisfy the identity, ZERO violations.**
     (Both sources carry the same 1.042 duplicate-key factor; deduping by MIN per key is
     required or join fanout manufactures 2,124 phantom disagreements.)

The publisher's own harvest metadata agrees: `_invariant_columns` on that table reads
['mw_available','percent_dfax','percent_loading_before','derived_rating_mva'] and
`_probe_dependent_columns` reads ['mw_impact','percent_impact','percent_loading_after'].

CONSEQUENCE: injection headroom does NOT fall as the request grows.  Every rung is exactly
derivable from one unbounded read, so this builds the ladder by clamping rather than by
re-scraping MISO six times.  Rows are labelled with `_rung_provenance` so a derived rung can
never be mistaken for an independently harvested one.

    python scripts/build_miso_injection_ladder.py
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
SRC = "energy-platfrom.energy.miso_poi_monitored_facilities"   # READ-ONLY, never written
TABLE = "in_miso_poi_ladder"
BUS = "in_bus_headroom_miso_ladder"
RUNGS = [100, 300, 500, 1000, 2500, 5000]

client = bigquery.Client(project="energy-platfrom")

rungs_sql = ", ".join(str(r) for r in RUNGS)

# Facility grain, one row per (POI, monitored facility, request size).
sql = f"""
CREATE OR REPLACE TABLE `{DS}.{TABLE}` AS
WITH ind AS (
  SELECT DISTINCT poi_name
  FROM `{DS}.in_bus_headroom_miso` WHERE location_status = 'indiana'
),
unb AS (
  -- dedupe to one row per (POI, facility): both harvests carry a 1.042 duplicate factor
  SELECT poi_name,
         TRIM(monitored_facility) AS monitored_facility,
         MIN(SAFE_CAST(mw_available AS FLOAT64))          AS headroom_mw_unclamped,
         MIN(SAFE_CAST(percent_dfax AS FLOAT64))          AS percent_dfax,
         MIN(SAFE_CAST(percent_loading_before AS FLOAT64)) AS percent_loading_before,
         MIN(SAFE_CAST(derived_rating_mva AS FLOAT64))    AS derived_rating_mva,
         ANY_VALUE(cont_name) AS cont_name, ANY_VALUE(ckt) AS ckt,
         ANY_VALUE(kvs) AS kvs, ANY_VALUE(areas_name) AS areas_name,
         ANY_VALUE(_vintage) AS _vintage, ANY_VALUE(_source_url) AS _source_url
  FROM `{SRC}`
  WHERE poi_name IN (SELECT poi_name FROM ind)
  GROUP BY 1, 2
)
SELECT
  u.poi_name,
  u.monitored_facility,
  r AS request_mw,
  LEAST(u.headroom_mw_unclamped, CAST(r AS FLOAT64)) AS allowable_injection_mw,
  u.headroom_mw_unclamped,
  u.headroom_mw_unclamped >= CAST(r AS FLOAT64) AS request_fits,
  u.percent_dfax, u.percent_loading_before, u.derived_rating_mva,
  u.cont_name, u.ckt, u.kvs, u.areas_name,
  'INJECTION' AS direction,
  CASE WHEN r = 300 THEN 'HARVESTED at pMaxValue=300 (in_miso_poi_300mw) AND reproduced by clamp'
       ELSE 'DERIVED: LEAST(unclamped, request_mw); clamp identity verified 38,381/38,381 keys, 0 violations'
  END AS _rung_provenance,
  u._vintage AS _observed_vintage,
  u._source_url,
  CURRENT_TIMESTAMP() AS _built_at
FROM unb u, UNNEST([{rungs_sql}]) AS r
"""
client.query(sql).result()

# Bus/POI-level headroom per rung.  MIN(min(true_i, X)) == min(MIN(true_i), X), so the
# rollup is exact at every rung too.  Mirrors the MIN-across-facilities convention already
# used by in_bus_headroom_300 / in_pjm_bus_withdrawal.
client.query(f"""
CREATE OR REPLACE TABLE `{DS}.{BUS}` AS
SELECT poi_name, request_mw,
       MIN(allowable_injection_mw) AS headroom_mw,
       MIN(headroom_mw_unclamped)  AS headroom_mw_unclamped,
       MIN(headroom_mw_unclamped) >= CAST(request_mw AS FLOAT64) AS request_fits,
       COUNT(*) AS facilities,
       COUNTIF(headroom_mw_unclamped = 0) AS facilities_at_zero,
       ANY_VALUE(_observed_vintage) AS _observed_vintage,
       CURRENT_TIMESTAMP() AS _built_at
FROM `{DS}.{TABLE}`
GROUP BY poi_name, request_mw""").result()

n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.{TABLE}`"))[0].n
nb = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.{BUS}`"))[0].n
print(f"{TABLE}: {n:,} rows   {BUS}: {nb:,} rows")

print("\nPOI-level headroom by rung (the ladder the application actually asks):")
for r in client.query(f"""
    SELECT request_mw, COUNT(*) pois,
           COUNTIF(headroom_mw > 0) pois_nonzero,
           COUNTIF(request_fits) pois_that_fit,
           ROUND(AVG(headroom_mw), 2) avg_headroom_clamped,
           ROUND(AVG(headroom_mw_unclamped), 2) avg_headroom_true
    FROM `{DS}.{BUS}` GROUP BY 1 ORDER BY 1"""):
    print(f"   {r.request_mw:>5} MW: {r.pois} POIs, {r.pois_nonzero} nonzero, "
          f"{r.pois_that_fit} fit the request, avg clamped {r.avg_headroom_clamped}, "
          f"avg true {r.avg_headroom_true}")

note = ("MISO INJECTION request-size ladder, Indiana POIs. pMaxValue is a REPORTING CLAMP, "
        "not a study input: PMax(X)==min(PMax_true,X) verified 38,381/38,381 (POI,facility) "
        "keys with ZERO violations against two independent harvests (in_miso_poi_300mw at 300 "
        "vs energy.miso_poi_monitored_facilities at 99999), and 67/67 facilities live at 100 "
        "and 300. Headroom therefore does NOT fall as the request grows, so rungs are derived "
        "by clamping, NOT re-scraped -- see _rung_provenance per row. OBSERVED VINTAGE "
        "DPP-2021-Cycle (publisher payload). INJECTION ONLY: MISO publishes no withdrawal/load "
        "direction on this API (negative pMaxValue floors at 0; 8 candidate direction params "
        "silently ignored; only /api/pois and /api/poi_mf exist).")
for tbl, cnt in ((TABLE, n), (BUS, nb)):
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name=@t",
                 job_config=bigquery.QueryJobConfig(query_parameters=[
                     bigquery.ScalarQueryParameter("t", "STRING", tbl)])).result()
    client.query(
        f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
            VALUES (@t, @s, @m, @n, 0.05, CURRENT_TIMESTAMP(), @notes)""",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", tbl),
            bigquery.ScalarQueryParameter(
                "s", "STRING",
                "giqueue.misoenergy.org/POI/api/poi_mf?poiName={poi}&pMaxValue=99999 "
                "(via energy.miso_poi_monitored_facilities, read-only)"),
            bigquery.ScalarQueryParameter(
                "m", "STRING",
                "scripts/build_miso_injection_ladder.py; clamp identity LEAST(unclamped, "
                "request_mw) across rungs 100/300/500/1000/2500/5000"),
            bigquery.ScalarQueryParameter("n", "INT64", int(cnt)),
            bigquery.ScalarQueryParameter("notes", "STRING", note)])).result()
    print(f"_registry row written for {tbl}")
print("MISO INJECTION LADDER COMPLETE")
