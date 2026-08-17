"""Build the statewide screener candidate table: capability + motivation + GRID CAPACITY.

WHY THIS EXISTS. The map console screens grid access as "within X miles of a substation >= Y kV".
Proximity is not capacity. A parcel 0.4 mi from a 345 kV substation with no available headroom is a
worse site than one 3 mi from a bus with 800 MW, and the proximity screener ranks them the wrong way
round. This table joins the capacity answer onto every candidate parcel so the screener can rank on
what a site can actually GET, not on how close it happens to sit to a piece of steel.

*** DIRECTION IS CARRIED SEPARATELY AND IS NEVER FUSED. ***
    MISO publishes INJECTION headroom  -- generator-side.
    PJM  publishes WITHDRAWAL capacity -- load-side. A data centre is LOAD.
Two nearest-bus joins run, one per direction, and they land in differently named columns. There is
deliberately no "nearest bus" column, because answering "which bus is nearest" without saying which
question that bus answers is how a screener ends up confidently wrong across the two thirds of
Indiana that sits in MISO. See docs/BACKLOG.md G7.

*** THE SI FLAG. *** `in_sites.has_si_signal` is the V1 flag: 847,410 parcels, ~99% empty land.
The LIVE flag is `in_si_sites_flags_v2.has_si_signal` (24,275), non-residential and severity-gated.
export_spine.py shipped the v1 flag by accident on 2026-08-17 and nothing errored. This table joins
v2 explicitly and NEVER reads in_sites.has_si_signal.

*** D85. *** `parcels_in/080500000047000018` is an inverted whole-Earth polygon, live and unrepaired
upstream. It is excluded by key BEFORE any spatial join. Left in, it is "within 40 km" of every bus
in the state and would attach itself to every parcel's nearest-bus result.

Writes `indiana_app.in_screener_candidates` and registers it in the same run.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
D85 = "080500000047000018"
RADIUS_M = 40000          # 40 km / ~25 mi. Beyond this a bus is not a siting fact for the parcel.
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{DS}.in_screener_candidates` AS
WITH cand AS (
  SELECT s.parcel_source, s.parcel_key, s.occ_group, s.occ_cls, s.site_kind,
         s.parcel_acres, s.exact_parcel_acres, s.outdoor_acres, s.exact_outdoor_acres,
         s.structure_count, s.total_bldg_sqft,
         s.mw_datacenter_4_per_acre, s.mw_bess_10_per_acre,
         s.lat, s.lon, s.parcel_geog
  FROM `{DS}.in_sites` s
  WHERE s.parcel_geog IS NOT NULL
    AND s.parcel_key != '{D85}'                      -- D85 excluded BEFORE the spatial joins
    AND (s.mw_datacenter_4_per_acre >= 25
         OR EXISTS (SELECT 1 FROM `{DS}.in_si_sites_flags_v2` f
                    WHERE f.parcel_source = s.parcel_source AND f.parcel_key = s.parcel_key
                      AND f.has_si_signal))
),
-- MISO: INJECTION. Generator-side. Present so a co-located generation play can be screened,
-- NOT as an answer to "can this site be served".
-- ⛔ THE ACTUAL IS A **MINIMUM** OVER BINDING CONSTRAINTS, NOT A MEDIAN OVER THE CONSTRAINT SET.
-- This query previously took `median_mw` and it was badly wrong. Measured 2026-08-17: median_mw
-- averages ~1,193 MW across the 642 Indiana POIs while the ACTUAL at a 300 MW request is 0 MW on
-- 641 of 642, because facilities_at_zero averages 15.8 of 59.8 monitored facilities - the binding
-- constraints are already at their limit in the base case. A median mixes the one constraint that
-- sets the answer in with dozens that do not, so it reads as ~1,193 MW of capacity that is not
-- there. The worst/median/best triple was never a methodology, it was a workaround for a probe run
-- at pmax_request=99999 that returned worst_mw=0 on ~88% of POIs.
bus_inj AS (
  SELECT m.bus_name AS nm, m.poi_name AS poi, m.kv,
         l.headroom_mw AS mw,          -- ACTUAL at the 300 MW rung (min over binding constraints)
         l.request_fits AS fits_300,
         m.worst_mw, m.best_mw,
         m.worst_binding_facility AS binding, ST_GEOGPOINT(m.lon, m.lat) AS g
  FROM `{DS}.in_bus_headroom_miso` m
  LEFT JOIN `{DS}.in_bus_headroom_miso_ladder` l
    ON l.poi_name = m.poi_name AND l.request_mw = 300
  WHERE m.location_status = 'indiana' AND m.lat IS NOT NULL AND m.lon IS NOT NULL
),
-- PJM: WITHDRAWAL. Load-side. THIS is the direction a data centre needs.
bus_wd AS (
  SELECT bus_label AS nm, bus_label AS poi, SAFE_CAST(bus_kv AS FLOAT64) AS kv,
         withdrawal_mw AS mw, binding_facility AS binding, match_confidence AS conf,
         ST_GEOGPOINT(lon, lat) AS g
  FROM `{DS}.vw_pjm_bus_withdrawal_located`
  WHERE lat IS NOT NULL AND lon IS NOT NULL
),
subs AS (
  SELECT substation_name AS nm, max_kv, ST_GEOGPOINT(lon, lat) AS g
  FROM `{DS}.in_substations`
  WHERE lat IS NOT NULL AND lon IS NOT NULL
),
n_inj AS (
  SELECT c.parcel_source, c.parcel_key,
         ARRAY_AGG(STRUCT(b.nm, b.kv, b.mw, b.worst_mw, b.best_mw, b.binding,
                          ST_DISTANCE(c.parcel_geog, b.g) AS m)
                   ORDER BY ST_DISTANCE(c.parcel_geog, b.g) LIMIT 1)[OFFSET(0)] AS b
  FROM cand c JOIN bus_inj b ON ST_DWITHIN(c.parcel_geog, b.g, {RADIUS_M})
  GROUP BY 1, 2
),
n_wd AS (
  SELECT c.parcel_source, c.parcel_key,
         ARRAY_AGG(STRUCT(b.nm, b.kv, b.mw, b.binding, b.conf,
                          ST_DISTANCE(c.parcel_geog, b.g) AS m)
                   ORDER BY ST_DISTANCE(c.parcel_geog, b.g) LIMIT 1)[OFFSET(0)] AS b
  FROM cand c JOIN bus_wd b ON ST_DWITHIN(c.parcel_geog, b.g, {RADIUS_M})
  GROUP BY 1, 2
),
n_sub AS (
  SELECT c.parcel_source, c.parcel_key,
         ARRAY_AGG(STRUCT(s.nm, s.max_kv, ST_DISTANCE(c.parcel_geog, s.g) AS m)
                   ORDER BY ST_DISTANCE(c.parcel_geog, s.g) LIMIT 1)[OFFSET(0)] AS s
  FROM cand c JOIN subs s ON ST_DWITHIN(c.parcel_geog, s.g, {RADIUS_M})
  GROUP BY 1, 2
)
SELECT
  c.parcel_source, c.parcel_key, sc.county_fips, sc.county_name,
  c.occ_group, c.occ_cls, c.site_kind, c.structure_count, c.total_bldg_sqft,
  c.parcel_acres, c.exact_parcel_acres, c.outdoor_acres, c.exact_outdoor_acres,
  c.mw_datacenter_4_per_acre AS mw_dc, c.mw_bess_10_per_acre AS mw_bess,
  c.lat, c.lon,

  -- owner motivation (the LIVE v2 flag only)
  IFNULL(f.has_si_signal, FALSE) AS has_signal,
  f.si_signals AS signals, f.si_signal_types AS signal_types, f.si_signal_events AS signal_events,
  f.si_first_event_date AS first_event, f.si_last_event_date AS last_event,
  f.si_events_3y AS events_3y, f.si_events_5y AS events_5y, f.si_events_10y AS events_10y,
  f.si_keying AS keying, f.si_date_basis AS date_basis,

  -- environmental gates
  g.sfha_flood, g.wetland_on_parcel, g.protected_land, g.bonus_kinds,

  -- GRID CAPACITY, per direction, never fused
  ni.b.nm AS inj_bus, ni.b.kv AS inj_kv, ROUND(ni.b.mw, 1) AS inj_mw,
  ROUND(ni.b.worst_mw, 1) AS inj_mw_worst, ROUND(ni.b.best_mw, 1) AS inj_mw_best,
  ni.b.binding AS inj_binding, ROUND(ni.b.m / 1609.344, 2) AS inj_mi,

  nw.b.nm AS wd_bus, nw.b.kv AS wd_kv, ROUND(nw.b.mw, 1) AS wd_mw,
  nw.b.binding AS wd_binding, nw.b.conf AS wd_conf, ROUND(nw.b.m / 1609.344, 2) AS wd_mi,

  ns.s.nm AS sub_name, ns.s.max_kv AS sub_kv, ROUND(ns.s.m / 1609.344, 2) AS sub_mi,

  CURRENT_TIMESTAMP() AS built_at
FROM cand c
LEFT JOIN `{DS}.in_sites_county`        sc USING (parcel_source, parcel_key)
LEFT JOIN `{DS}.in_si_sites_flags_v2`   f  USING (parcel_source, parcel_key)
LEFT JOIN `{DS}.in_site_gates`          g  USING (parcel_source, parcel_key)
LEFT JOIN n_inj ni USING (parcel_source, parcel_key)
LEFT JOIN n_wd  nw USING (parcel_source, parcel_key)
LEFT JOIN n_sub ns USING (parcel_source, parcel_key)
"""

# ---- cost gate: never run a spatial join over 3.5M geographies without pricing it first ----
dry = client.query(SQL, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
gb = dry.total_bytes_processed / 1024 ** 3
usd = gb / 1024 * 6.25          # $6.25/TiB on-demand
print(f"DRY RUN: {gb:,.1f} GiB  ->  approx ${usd:,.2f}")
if usd > 25:
    print(f"COST GATE TRIPPED at ${usd:,.2f} (> $25). Not running. Re-run with --force if intended.")
    if "--force" not in _sys.argv:
        _sys.exit(1)

job = client.query(SQL)
job.result()
print(f"in_screener_candidates built: {job.total_bytes_processed / 1024**3:,.1f} GiB scanned")

# ---- measure what we produced, and prove the D85 guard by fan-out ----
m = list(client.query(f"""
SELECT COUNT(*) n,
       COUNT(DISTINCT CONCAT(parcel_source,'|',parcel_key)) n_distinct,
       COUNTIF(has_signal) with_signal,
       COUNTIF(mw_dc >= 25) ge25,
       COUNTIF(wd_mw IS NOT NULL) has_withdrawal,
       COUNTIF(inj_mw IS NOT NULL) has_injection,
       COUNTIF(wd_mw IS NULL AND inj_mw IS NULL) no_bus_either,
       COUNT(DISTINCT county_fips) counties
FROM `{DS}.in_screener_candidates`"""))[0]
fanout = m.n / m.n_distinct if m.n_distinct else 0
print(f"  rows {m.n:,} over {m.n_distinct:,} distinct parcels -> fan-out {fanout:.3f} "
      f"({'OK - D85 guard holds' if fanout < 1.01 else 'FAIL - a join is duplicating parcels'})")
print(f"  with an owner-motivation signal : {m.with_signal:,}")
print(f"  fits >= 25 MW                   : {m.ge25:,}")
print(f"  has a WITHDRAWAL bus (load)     : {m.has_withdrawal:,}")
print(f"  has an INJECTION bus (gen)      : {m.has_injection:,}")
print(f"  no bus of EITHER direction      : {m.no_bus_either:,}  <- cannot-assess, not zero")
print(f"  counties represented            : {m.counties}")
assert fanout < 1.01, "fan-out above 1.0 means a join duplicated parcels - D85 or a bad key"

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_screener_candidates'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
    f"VALUES (@t,@s,@m,@n,@g,CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "in_screener_candidates"),
        bigquery.ScalarQueryParameter("s", "STRING",
            "in_sites x in_si_sites_flags_v2 x in_site_gates x in_sites_county x "
            "in_bus_headroom_miso(injection) x vw_pjm_bus_withdrawal_located(withdrawal) x in_substations"),
        bigquery.ScalarQueryParameter("m", "STRING",
            f"candidates = fits>=25MW OR carries a v2 owner-motivation signal; nearest bus within "
            f"{RADIUS_M/1000:.0f} km computed SEPARATELY per direction; D85 excluded by key before "
            f"any spatial join; fan-out asserted < 1.01"),
        bigquery.ScalarQueryParameter("n", "INT64", int(m.n)),
        bigquery.ScalarQueryParameter("g", "FLOAT64", round(job.total_bytes_processed / 1024**3, 2)),
        bigquery.ScalarQueryParameter("no", "STRING",
            "Grid capacity, not grid proximity. INJECTION (MISO, generator-side) and WITHDRAWAL "
            "(PJM, load-side) are separate columns and must never be fused or compared - a data "
            "centre is load and needs withdrawal. Reads the LIVE v2 signal flag, never "
            "in_sites.has_si_signal which is the v1 flag (847,410, ~99% empty land).")])).result()
print("registered in_screener_candidates")
