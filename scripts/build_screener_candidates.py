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
    -- ⛔ G122: A ROAD OR RAIL RIGHT-OF-WAY IS NOT A WEAK SITE, IT IS NOT A SITE.
    -- Operator, 2026-08-20c: "no one can actually own a roadway". Until now the ribbon detection
    -- was ADVISORY - the screener warned and the parcel still counted, still scored, still
    -- appeared in search and in every "fits N MW" total. It is now an exclusion.
    -- in_parcel_row_class confirms a corridor by the length of road centreline running ALONG the
    -- polygon, not by a bare ST_INTERSECTS, which with the full 379,165-feature TIGER corpus
    -- fires on ~30% of ordinary parcels. shape_only is NOT excluded - creeks, pipeline easements
    -- and genuinely long narrow industrial land are ribbons too.
    AND NOT EXISTS (SELECT 1 FROM `{DS}.in_parcel_row_class` rc
                    WHERE rc.parcel_source = s.parcel_source
                      AND rc.parcel_key = s.parcel_key AND rc.row_excluded)
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
  SELECT t0.bus_name AS nm, t0.bus_name AS poi, t0.bus_voltage_kv AS kv, t0.iso,
         t0.bus_interconnection_capacity_mw AS mw,
         t0.primary_limiting_constraint AS binding,
         t0.provenance_class AS conf,
         -- ⚠ OUR PJM HARVEST IS THE WHOLE AEP FOOTPRINT, NOT INDIANA. Measured 2026-08-19: of the
         -- 227 located PJM withdrawal buses, only 42 are inside the state line - the rest sit in
         -- Ohio, West Virginia, Virginia, Kentucky and Michigan. A border parcel CAN genuinely
         -- interconnect across a state line, so these are kept rather than dropped, but crossing
         -- one means a different state commission and often a different utility. That is a fact
         -- the reader must be told, not one we quietly absorb into a distance.
         ST_INTERSECTS(ST_GEOGPOINT(COALESCE(t0.longitude, v3.lon), COALESCE(t0.latitude, v3.lat)),
           (SELECT ANY_VALUE(geom) FROM `energy-platfrom.energy.state_boundaries`
            WHERE UPPER(stusps) = 'IN'))                 AS in_state,
         ST_GEOGPOINT(COALESCE(t0.longitude, v3.lon), COALESCE(t0.latitude, v3.lat)) AS g
  FROM `{DS}.in_bus_capacity_tier0` t0
  LEFT JOIN `{DS}.in_pjm_bus_placement_v3` v3 ON v3.bus_id = t0.bus_id
  WHERE t0.interconnection_type = 'Injection'
    AND COALESCE(t0.latitude, v3.lat) IS NOT NULL
    AND COALESCE(t0.longitude, v3.lon) IS NOT NULL
),
-- WITHDRAWAL. Load-side. THIS is the direction a data centre needs, and it now carries BOTH
-- operators rather than PJM alone.
bus_wd AS (
  SELECT t0.bus_name AS nm, t0.bus_name AS poi, t0.bus_voltage_kv AS kv, t0.iso,
         t0.bus_interconnection_capacity_mw AS mw,
         t0.primary_limiting_constraint AS binding,
         t0.provenance_class AS conf,
         -- ⚠ OUR PJM HARVEST IS THE WHOLE AEP FOOTPRINT, NOT INDIANA. Measured 2026-08-19: of the
         -- 227 located PJM withdrawal buses, only 42 are inside the state line - the rest sit in
         -- Ohio, West Virginia, Virginia, Kentucky and Michigan. A border parcel CAN genuinely
         -- interconnect across a state line, so these are kept rather than dropped, but crossing
         -- one means a different state commission and often a different utility. That is a fact
         -- the reader must be told, not one we quietly absorb into a distance.
         ST_INTERSECTS(ST_GEOGPOINT(COALESCE(t0.longitude, v3.lon), COALESCE(t0.latitude, v3.lat)),
           (SELECT ANY_VALUE(geom) FROM `energy-platfrom.energy.state_boundaries`
            WHERE UPPER(stusps) = 'IN'))                 AS in_state,
         ST_GEOGPOINT(COALESCE(t0.longitude, v3.lon), COALESCE(t0.latitude, v3.lat)) AS g
  FROM `{DS}.in_bus_capacity_tier0` t0
  LEFT JOIN `{DS}.in_pjm_bus_placement_v3` v3 ON v3.bus_id = t0.bus_id
  WHERE t0.interconnection_type = 'Withdrawal'
    AND COALESCE(t0.latitude, v3.lat) IS NOT NULL
    AND COALESCE(t0.longitude, v3.lon) IS NOT NULL
),
-- ⛔ NO CENTROID WHERE A FOOTPRINT EXISTS - 2026-08-20. This read ST_GEOGPOINT(lon, lat), which
--    was right while every located substation had a published point, and stopped being right when
--    repair_substation_geometry.py recovered 734 stations whose only geometry is a POLYGON.
--    `geog` is the footprint where held, so sub_mi is the distance to the fence and 0 when the
--    substation sits on the parcel. Measured effect on this table: median sub_mi 2.56 -> 2.16 mi
--    across all 532,693 candidates, and on-parcel substations 871 -> 974.
subs AS (
  SELECT substation_name AS nm, max_kv, geog AS g
  FROM `{DS}.in_substations`
  WHERE geog IS NOT NULL
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

  -- ⭐ G125: WHERE AM I? The operator asked for "EITHER coordinates OR addresses ... so they can
  -- self-verify the results". `lat`/`lon` were already here and the popup simply did not print
  -- them. The ADDRESS is the finding: three documents recorded address as MARION-ONLY, on the
  -- strength of in_si_address_parcel_bridge (51,309 Marion rows). Measured 2026-08-20d against
  -- energy.parcels_in, which is a DIFFERENT source - the DLGF's own property address - and it is
  -- populated on 3,578,398 of 3,637,663 Indiana parcels (98.4%) across all 92 counties.
  -- ⚠ Marion's bridge is still the right thing for address SEARCH, because it resolves a typed
  -- address to a parcel. This is the reverse lookup and it is statewide.
  -- ⛔ Still NULL on ~1.6%, and a parcel with no address must say so rather than print a blank.
  loc.prop_address, loc.prop_city, loc.prop_zip, loc.dlgf_class_code,

  -- ⭐ G53, the half the operator named and that never shipped. The row asked for the withdrawn
  -- queue to be "filterable by date of withdrawn application"; the data was built and placed on
  -- 2026-08-20b and the screener carried no such field - measured, the word "withdrawn" appeared
  -- 0 times in screener.html. The row was corrected back from DONE for exactly that.
  -- ⚠ AGGREGATED PER PARCEL, because a parcel can carry more than one cancelled request and a
  -- LEFT JOIN to the raw table would fan the candidate set out. The fan-out assertion below is
  -- what would have caught that.
  wdq.wd_requests, wdq.wd_last_date, wdq.wd_max_mw,

  -- ⭐ G130, operator 2026-08-20f: a screener control for whether site locations are seen "with
  -- or without the planned system upgrades". That only means anything if each site knows what
  -- planned work is near it, so the nearest FUTURE upgrade rides along with every candidate.
  -- ⛔ FUTURE ONLY. in_service work is already built and is not future capacity; cancelled work
  -- is the opposite of a promise. Both are excluded from this join.
  -- ⚠ THE DISTANCE IS MEANINGLESS WITHOUT THE UNCERTAINTY and both ship together. "2.3 mi from a
  -- planned rebuild" reads as precision; if that project is placed only to a town centroid its
  -- ring is 5 miles, and the honest reading is "somewhere around here".
  pu.pu_name, pu.pu_src, pu.pu_status, pu.pu_isd, pu.pu_cost_m, pu.pu_mi, pu.pu_unc_mi,
  pu.pu_loc_method,

  -- ⭐ G132, operator 2026-08-21: *"Since we don't have the owner name for the parcel joins, we
  -- need to use some other metric (e.g., assessed value…). As for assessed value, are we able to
  -- determine this based on the data that we currently hold, or is this gated behind a paid
  -- source?"* ⛔ BOTH, and three documents only said the second half. Statewide it IS gated - the
  -- DLGF purchase - but Marion County publishes owner name, owner MAILING address and assessed
  -- value, and we already held all of it in in_marion_parcel_crosswalk.
  -- ⚠ ONE COUNTY OF 92, ~1.3% of candidates. These columns are NULL everywhere else and that is
  -- a fact about the publisher, not a gap in the join - so they render as absent, never as zero.
  mv.owner_name, mv.owner_mail_city, mv.owner_mail_state, mv.owner_out_of_state,
  mv.assessed_total, mv.assessed_land, mv.assessed_improvement, mv.assessed_per_acre,
  mv.assessor_class_label,

  -- ⭐ G133, operator 2026-08-21: federal surplus and the withdrawn queue as SI SIGNALS rather
  -- than only as map layers. ⛔ A SEPARATE FAMILY, NOT MERGED INTO has_signal. Every existing
  -- SI code INFERS willingness from distress; these two REVEAL it - a federal owner recording an
  -- asset as excess, or an owner who already consented to host energy infrastructure. Merging
  -- them would move the 23,766 flagged count the checkpoint asserts and would put an inference
  -- and a declaration under one number.
  -- ⭐ Measured: 174 parcels, and 167 of them carry NO distress signal - leads the existing set
  -- could not see at all.
  -- ⚠ READ FROM THE FLAG TABLE, NOT FROM in_si_intent_signals DIRECTLY. The first version of G133
  -- joined the intent table here, which put the signal on the SCREENER ONLY - the map console,
  -- si.html and the county rollups all read in_si_sites_flags_v2 and saw nothing. Operator,
  -- 2026-08-21: *"all of the changes you made have to flow throughout the application, not just in
  -- one section."* Two join paths to one fact is also the two-copies defect; there is now one.
  f.has_intent_signal, f.intent_signals, f.intent_last_date, f.intent_who, f.intent_mw_given_up,

  -- ⛔ G125 SECOND FINDING, AND IT CONTRADICTS THE ROW AS WRITTEN. G125 says "the parcel payload
  -- ships lat/lon on every row" and the popup merely fails to print it. Measured 2026-08-20d:
  -- `lat` is populated on 2,284,133 of 3,553,194 in_sites rows, so only 40.3% of CANDIDATES carry
  -- a published point. Printing "no coordinate" for the other 59.7% would be a worse answer than
  -- the silence it replaced, because every one of those parcels HAS a polygon - `parcel_geog` is
  -- non-null on 3,553,193 of 3,553,194 and is required by the WHERE clause above.
  -- ⭐ So a DISPLAY point is derived from the polygon where the published one is absent, and it is
  -- LABELLED. The operator's purpose is self-verification against satellite imagery, and an
  -- interior point of the parcel does that exactly.
  -- ⛔ IT IS A SEPARATE COLUMN ON PURPOSE. "No centroid where a footprint exists" governs DISTANCE
  -- MATH, and nothing here may feed it: every distance on this table is already measured to a
  -- geography. map_lat/map_lon are for the reader's eye and the deep link, never for a join.
  COALESCE(c.lat, ST_Y(ST_CENTROID(c.parcel_geog))) AS map_lat,
  COALESCE(c.lon, ST_X(ST_CENTROID(c.parcel_geog))) AS map_lon,
  IF(c.lat IS NOT NULL, 'published', 'parcel_interior_point') AS coord_basis,

  CURRENT_TIMESTAMP() AS built_at
FROM cand c
LEFT JOIN (
  -- de-duplicated: 38,840 state_parcel_id values repeat in the source, and joining them raw
  -- fans the candidate table out. ⚠ The key is state_parcel_id, NOT parcel_id - the latter is the
  -- county's dashed form and matches ~1% of our keys, which reads as missing data.
  -- ⚠ aliased to loc_key, NOT parcel_key: a second column of that name reaches the later
  -- USING (parcel_source, parcel_key) joins and BigQuery rejects it as ambiguous on the left side.
  SELECT state_parcel_id AS loc_key,
         ANY_VALUE(NULLIF(COALESCE(NULLIF(dlgf_prop_address, ''),
                                   NULLIF(prop_add, '')), ''))       AS prop_address,
         ANY_VALUE(NULLIF(COALESCE(NULLIF(dlgf_prop_address_city, ''),
                                   NULLIF(prop_city, '')), ''))      AS prop_city,
         ANY_VALUE(NULLIF(COALESCE(NULLIF(dlgf_prop_address_zip, ''),
                                   NULLIF(prop_zip, '')), ''))       AS prop_zip,
         ANY_VALUE(NULLIF(dlgf_prop_class_code, ''))                 AS dlgf_class_code
  FROM `energy-platfrom.energy.parcels_in`
  WHERE state_parcel_id IS NOT NULL AND state_parcel_id != '{D85}'
  GROUP BY 1
) loc ON loc.loc_key = c.parcel_key
LEFT JOIN (
  -- one row per parcel: how many cancelled requests, the most recent withdrawal date, and the
  -- largest capacity that was given up there. ⭐ The SIZE figure is the other half of G53: a
  -- cancelled 5 MW solar project does not imply land for a 300 MW campus.
  SELECT parcel_source, parcel_key,
         COUNT(*)                                   AS wd_requests,
         CAST(MAX(wd_date) AS STRING)               AS wd_last_date,
         ROUND(MAX(capacity_mw), 1)                 AS wd_max_mw
  FROM `{DS}.in_si_queue_withdrawn`
  WHERE parcel_key IS NOT NULL
  GROUP BY 1, 2
) wdq USING (parcel_source, parcel_key)
LEFT JOIN (
  -- nearest FUTURE planned upgrade per candidate, within 25 miles
  SELECT c.parcel_source, c.parcel_key,
         ARRAY_AGG(STRUCT(p.title AS pu_name, p.source AS pu_src, p.status_class AS pu_status,
                          p.in_service_date AS pu_isd, ROUND(p.cost_usd_m, 1) AS pu_cost_m,
                          ROUND(ST_DISTANCE(c.parcel_geog,
                                ST_GEOGPOINT(p.lon, p.lat)) / 1609.344, 2) AS pu_mi,
                          p.uncertainty_mi AS pu_unc_mi, p.loc_method AS pu_loc_method)
                   ORDER BY ST_DISTANCE(c.parcel_geog, ST_GEOGPOINT(p.lon, p.lat))
                   LIMIT 1)[OFFSET(0)].*
  FROM cand c
  JOIN `{DS}.in_planned_upgrades` p
    ON p.lat IS NOT NULL
   AND p.status_class IN ('proposed', 'approved', 'filed_plan')
   AND ST_DWITHIN(c.parcel_geog, ST_GEOGPOINT(p.lon, p.lat), 40000)
  GROUP BY 1, 2
) pu USING (parcel_source, parcel_key)
-- ⭐ G132: Marion owner identity and assessed value. One row per parcel_key by construction
-- (asserted in its own build), so this cannot fan out the candidate table.
LEFT JOIN `{DS}.in_marion_owner_value`  mv USING (parcel_source, parcel_key)
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
            # ⛔ THIS ROW CARRIED NO `RE-SCRAPE COMMAND:` AT ALL and audit_registry_truth.py said
            # so - one of only three objects in the estate missing one, and the other two are
            # ladder rungs the running harvest has not registered yet. G16's test is whether a
            # stranger could re-run the work from the registry row alone, and for the table the
            # whole screener is built from, they could not.
            "RE-SCRAPE COMMAND: python scripts/build_screener_candidates.py . "
            "IDEMPOTENCY: replace_safe - CREATE OR REPLACE from upstream tables only. "
            "CADENCE: whenever in_sites, in_bus_capacity_tier0, in_parcel_row_class or "
            "in_si_sites_flags_v2 is rebuilt. "
            "Grid capacity, not grid proximity. INJECTION (MISO, generator-side) and WITHDRAWAL "
            "(PJM, load-side) are separate columns and must never be fused or compared - a data "
            "center is load and needs withdrawal. Reads the LIVE v2 signal flag, never "
            "in_sites.has_si_signal which is the v1 flag (847,410, ~99% empty land). "
            "G122: confirmed road and rail rights-of-way are EXCLUDED via in_parcel_row_class. "
            "G125: carries the DLGF address and a labelled display coordinate. "
            "G53: carries the withdrawn-queue aggregate (wd_requests, wd_last_date, wd_max_mw).")
        ])).result()
print("registered in_screener_candidates")
