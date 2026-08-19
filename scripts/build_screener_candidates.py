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
-- ============================================================================================
-- BUS CAPACITY, BOTH DIRECTIONS, BOTH ISOs -- repointed 2026-08-19.
--
-- ⛔ WHAT WAS HERE WAS SUPERSEDED AND IT SILENTLY CRIPPLED THE SCREENER.
--   `bus_inj` read in_bus_headroom_miso joined to the ladder AT request_mw = 300, so inj_mw was
--   "headroom at a 300 MW probe" -- structurally capped at 300, and 514,270 of 515,934 rows were 0.
--   `bus_wd` read vw_pjm_bus_withdrawal_located -- PJM ONLY, 227 located buses -- so wd_mw spanned
--   just 13-132 MW and THE SCREENER HELD NO MISO LOAD-SIDE DATA AT ALL. The operator reported it
--   from the other end: "even for MISO, I wasn't able to populate a single site based on bus
--   headroom over 300MW." Nothing could: 132 was the ceiling, and the page's own default target
--   is 300.
--
-- G63 rebuilt capacity into in_bus_capacity_tier0 (7,102 rows, both directions, both ISOs) and
-- this build was never repointed. It is now.
--
-- ⚠ COORDINATES ARE THE LIMIT ON PJM, NOT THIS QUERY. tier0 carries lat/lon on 1,731 of 1,731 MISO
-- buses in each direction but only 223/1,814 PJM injection and 227/1,826 PJM withdrawal -- the G62
-- gazetteer ceiling. A bus with no coordinate cannot be joined to a parcel, so it is excluded here
-- and that exclusion is REPORTED rather than hidden.
-- ============================================================================================
bus_inj AS (
  SELECT bus_name AS nm, bus_name AS poi, bus_voltage_kv AS kv, iso,
         bus_interconnection_capacity_mw AS mw,
         primary_limiting_constraint AS binding,
         provenance_class AS conf,
         -- ⚠ OUR PJM HARVEST IS THE WHOLE AEP FOOTPRINT, NOT INDIANA. Measured 2026-08-19: of the
         -- 227 located PJM withdrawal buses, only 42 are inside the state line - the rest sit in
         -- Ohio, West Virginia, Virginia, Kentucky and Michigan. A border parcel CAN genuinely
         -- interconnect across a state line, so these are kept rather than dropped, but crossing
         -- one means a different state commission and often a different utility. That is a fact
         -- the reader must be told, not one we quietly absorb into a distance.
         ST_INTERSECTS(ST_GEOGPOINT(longitude, latitude),
           (SELECT ANY_VALUE(geom) FROM `energy-platfrom.energy.state_boundaries`
            WHERE UPPER(stusps) = 'IN'))                 AS in_state,
         ST_GEOGPOINT(longitude, latitude) AS g
  FROM `{DS}.in_bus_capacity_tier0`
  WHERE interconnection_type = 'Injection'
    AND latitude IS NOT NULL AND longitude IS NOT NULL
),
-- WITHDRAWAL. Load-side. THIS is the direction a data centre needs, and it now carries BOTH
-- operators rather than PJM alone.
bus_wd AS (
  SELECT bus_name AS nm, bus_name AS poi, bus_voltage_kv AS kv, iso,
         bus_interconnection_capacity_mw AS mw,
         primary_limiting_constraint AS binding,
         provenance_class AS conf,
         -- ⚠ OUR PJM HARVEST IS THE WHOLE AEP FOOTPRINT, NOT INDIANA. Measured 2026-08-19: of the
         -- 227 located PJM withdrawal buses, only 42 are inside the state line - the rest sit in
         -- Ohio, West Virginia, Virginia, Kentucky and Michigan. A border parcel CAN genuinely
         -- interconnect across a state line, so these are kept rather than dropped, but crossing
         -- one means a different state commission and often a different utility. That is a fact
         -- the reader must be told, not one we quietly absorb into a distance.
         ST_INTERSECTS(ST_GEOGPOINT(longitude, latitude),
           (SELECT ANY_VALUE(geom) FROM `energy-platfrom.energy.state_boundaries`
            WHERE UPPER(stusps) = 'IN'))                 AS in_state,
         ST_GEOGPOINT(longitude, latitude) AS g
  FROM `{DS}.in_bus_capacity_tier0`
  WHERE interconnection_type = 'Withdrawal'
    AND latitude IS NOT NULL AND longitude IS NOT NULL
),
subs AS (
  SELECT substation_name AS nm, max_kv, ST_GEOGPOINT(lon, lat) AS g
  FROM `{DS}.in_substations`
  WHERE lat IS NOT NULL AND lon IS NOT NULL
),
n_inj AS (
  SELECT c.parcel_source, c.parcel_key,
         ARRAY_AGG(STRUCT(b.nm, b.kv, b.mw, b.iso, b.binding, b.conf, b.in_state,
                          ST_DISTANCE(c.parcel_geog, b.g) AS m)
                   ORDER BY ST_DISTANCE(c.parcel_geog, b.g) LIMIT 1)[OFFSET(0)] AS b
  FROM cand c JOIN bus_inj b ON ST_DWITHIN(c.parcel_geog, b.g, {RADIUS_M})
  GROUP BY 1, 2
),
n_wd AS (
  SELECT c.parcel_source, c.parcel_key,
         ARRAY_AGG(STRUCT(b.nm, b.kv, b.mw, b.iso, b.binding, b.conf, b.in_state,
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
  -- ⛔ inj_mw_worst / inj_mw_best ARE GONE ON PURPOSE. tier0 carries ONE binding figure per bus
  -- per direction; the worst/median/best triple was retired because three rival numbers let a
  -- reader pick the flattering one. Fabricating them from a single value would undo that ruling.
  ni.b.nm AS inj_bus, ni.b.kv AS inj_kv, ROUND(ni.b.mw, 1) AS inj_mw,
  ni.b.iso AS inj_iso, ni.b.binding AS inj_binding, ni.b.conf AS inj_conf,
  ni.b.in_state AS inj_bus_in_state,
  ROUND(ni.b.m / 1609.344, 2) AS inj_mi,

  nw.b.nm AS wd_bus, nw.b.kv AS wd_kv, ROUND(nw.b.mw, 1) AS wd_mw,
  nw.b.iso AS wd_iso, nw.b.binding AS wd_binding, nw.b.conf AS wd_conf,
  nw.b.in_state AS wd_bus_in_state,
  ROUND(nw.b.m / 1609.344, 2) AS wd_mi,

  ns.s.nm AS sub_name, ns.s.max_kv AS sub_kv, ROUND(ns.s.m / 1609.344, 2) AS sub_mi,

  -- TRANSMISSION LINE (2026-08-19). These columns have existed on in_asset_distance_parcel since
  -- G29 and this build joined only the substation half of the same table. A line is the one asset
  -- that can run THROUGH a parcel rather than merely near it -- 41,986 parcels have one on them --
  -- so `line_on_parcel` is a different and stronger fact than a small `line_mi`.
  ad.line_mi, ad.line_on_parcel, ad.line_kv, ad.line_volt_class, ad.line_kv_unknown,

  CURRENT_TIMESTAMP() AS built_at
FROM cand c
LEFT JOIN `{DS}.in_sites_county`        sc USING (parcel_source, parcel_key)
LEFT JOIN `{DS}.in_si_sites_flags_v2`   f  USING (parcel_source, parcel_key)
LEFT JOIN `{DS}.in_site_gates`          g  USING (parcel_source, parcel_key)
LEFT JOIN n_inj ni USING (parcel_source, parcel_key)
LEFT JOIN n_wd  nw USING (parcel_source, parcel_key)
LEFT JOIN n_sub ns USING (parcel_source, parcel_key)
LEFT JOIN `{DS}.in_asset_distance_parcel` ad USING (parcel_source, parcel_key)
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
            "in_bus_capacity_tier0 (BOTH directions, BOTH ISOs) x in_substations x "
            "in_asset_distance_parcel"),
        bigquery.ScalarQueryParameter("m", "STRING",
            f"candidates = fits>=25MW OR carries a v2 owner-motivation signal; nearest bus within "
            f"{RADIUS_M/1000:.0f} km computed SEPARATELY per direction; D85 excluded by key before "
            f"any spatial join; fan-out asserted < 1.01. REPOINTED 2026-08-19 from "
            f"in_bus_headroom_miso(300 MW probe, injection only) + "
            f"vw_pjm_bus_withdrawal_located(PJM only, 227 buses) onto in_bus_capacity_tier0 - "
            f"the old pair capped wd_mw at 132 MW and inj_mw at exactly 300, and carried NO "
            f"MISO load-side data at all. Bus coverage is limited by COORDINATES: MISO 1,731 "
            f"of 1,731 per direction, PJM 227 of 1,826 withdrawal and 223 of 1,814 injection "
            f"(the G62 gazetteer ceiling)"),
        bigquery.ScalarQueryParameter("n", "INT64", int(m.n)),
        bigquery.ScalarQueryParameter("g", "FLOAT64", round(job.total_bytes_processed / 1024**3, 2)),
        bigquery.ScalarQueryParameter("no", "STRING",
            "Grid capacity, not grid proximity. INJECTION (MISO, generator-side) and WITHDRAWAL "
            "(PJM, load-side) are separate columns and must never be fused or compared - a data "
            "centre is load and needs withdrawal. Reads the LIVE v2 signal flag, never "
            "in_sites.has_si_signal which is the v1 flag (847,410, ~99% empty land).")])).result()
print("registered in_screener_candidates")
