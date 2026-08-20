"""G29 — parcel-to-GRID-ASSET distance, measured the way the operator asked. Writes
`in_asset_distance_parcel`.

THE DEFECT THIS CLOSES. `app.js` measures distance with `repPt()`:

    function repPt(geom) { let c = geom.coordinates;
      while (typeof c[0] !== "number") c = c[0]; return c; }   // <- THE FIRST VERTEX

so it measures *an arbitrary corner of the parcel* to *one binned vertex of the line*. Both ends are
wrong, the error is always in the same direction (it OVERSTATES), and it can never return 0.0 even
when the asset physically crosses the parcel. Operator, 2026-08-17: *"a parcel that has transmission
running through it should say 0.0mi from transmission, and it is currently stating ~0.55mi."*

⭐ WHY TRANSMISSION IS THE ONE THAT MATTERS, and why this table exists at all.
`in_screener_candidates` ALREADY carries exact `ST_DISTANCE` values for buses (`inj_mi`, `wd_mi`) and
substations (`sub_mi`) — the screener was always right. But it has **no transmission-line distance at
all**, and a line is the only one of the three that is a *LineString*: a point can be near a parcel,
but a line can run straight THROUGH it. So the asset with the largest first-vertex error is exactly
the asset nobody had measured. That is the gap this fills.

`in_transmission_union.geog` is real LineString GEOGRAPHY (3,737 segments), so
`ST_DISTANCE(parcel_geog, geog)` returns **0.0** when the conductor crosses the parcel — the answer
the operator asked for, from the geometry rather than from an approximation.

⚠ D85 (`parcels_in/080500000047000018`, the inverted whole-Earth polygon) is excluded BY KEY before
any spatial work. Left in, it is "within 0 m" of every line in the state. Fan-out is asserted ~1.0.

⛔ UNKNOWN VOLTAGE IS NOT ZERO VOLTAGE. `in_transmission_union.kv` is NULL on 1,114 of 3,737 OSM rows
and HIFLD writes -999999 as its not-available marker (G13). Both are carried through as NULL and
reported as `unknown`, never as the bottom of a scale — a 765 kV backbone and an unlabelled lateral
are not remotely the same siting fact.

SO WHAT (the governing principle — this table must change a decision, not just be correct):
  line_on_parcel = TRUE  -> the conductor is already on the land. No greenfield line to build, but
                            an easement/clearance constraint that shapes the site plan.
  line_kv                -> what it is worth interconnecting to. 765/345 kV is a backbone; a sub-100
                            kV lateral will not serve a 300 MW campus whatever its distance says.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
D85 = "080500000047000018"
RADIUS_M = 40234          # 25 miles - matches the app's own nearestBus() cap
TARGET = "in_asset_distance_parcel"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{DS}.{TARGET}` AS
WITH cand AS (
  SELECT c.parcel_source, c.parcel_key, c.county_fips, c.county_name, s.parcel_geog
  FROM `{DS}.in_screener_candidates` c
  JOIN `{DS}.in_sites` s USING (parcel_source, parcel_key)
  WHERE s.parcel_geog IS NOT NULL AND c.parcel_key != '{D85}'
),
-- TRANSMISSION LINES. Real LineString geometry, so a conductor crossing a parcel returns 0.0.
-- HIFLD's -999999 not-available marker and OSM's NULL both become NULL, never 0 (G13).
lines AS (
  SELECT geog, feature_id,
         CASE WHEN kv IS NULL OR kv <= 0 THEN NULL ELSE kv END AS kv,
         volt_class, owner, src
  FROM `{DS}.in_transmission_union`
  WHERE geog IS NOT NULL
),
near_line AS (
  SELECT c.parcel_source, c.parcel_key,
         /* G116/G118: carry the line's IDENTITY, not just its attributes. Without feature_id a
            parcel knows its nearest line's voltage and owner but cannot be followed to that
            line's two END BUSES - which is the whole basis of the headroom figure the operator
            specified. One extra column, no extra spatial work. */
         ARRAY_AGG(STRUCT(l.feature_id, l.kv, l.volt_class, l.owner, l.src,
                          ST_DISTANCE(c.parcel_geog, l.geog) AS m)
                   ORDER BY ST_DISTANCE(c.parcel_geog, l.geog) LIMIT 1)[OFFSET(0)] AS w
  FROM cand c
  JOIN lines l ON ST_DWITHIN(c.parcel_geog, l.geog, {RADIUS_M})
  GROUP BY 1, 2
),
-- SUBSTATIONS. Points, but the PARCEL end was still wrong under repPt().
-- ⛔ EXCLUDE taps (503) and dead ends (27) - G19/G20 established those are line structures, not
--    substations, and merging them recreates the taxonomy confusion in the other direction.
-- ⭐ but KEEP asset_class='unknown' (739). "Unknown" is a MISSING LABEL, not evidence the thing is
--    not a substation. Dropping it would silently move a parcel's nearest substation further away
--    for a reason about our metadata, which is the same error as treating unknown voltage as 0.
--    It is carried through as sub_class_unknown so the uncertainty is visible rather than hidden.
-- ⛔ NO CENTROID WHERE A FOOTPRINT EXISTS - 2026-08-20. This read ST_GEOGPOINT(lon, lat), which
--    was correct while every located substation carried a published point. It is not correct now:
--    repair_substation_geometry.py recovered 734 substations whose only geometry is a POLYGON, and
--    measuring to their centre point would overstate the distance to the fence by half the yard's
--    width - on exactly the OSM-contributed stations that nothing had measured before.
--    `geog` carries the footprint where held and the point otherwise, so ST_DISTANCE returns the
--    distance to the boundary, and 0.0 when the parcel touches the substation.
-- ⛔ geom_kind='none' is excluded: those are recovered footprints that fall outside Indiana.
subs AS (
  SELECT geog AS g, substation_name, max_kv, asset_class
  FROM `{DS}.in_substations_dedup`
  WHERE geog IS NOT NULL AND geom_kind != 'none'
    AND asset_class IN ('substation', 'unknown')
),
near_sub AS (
  SELECT c.parcel_source, c.parcel_key,
         ARRAY_AGG(STRUCT(s.substation_name, s.max_kv, s.asset_class,
                          ST_DISTANCE(c.parcel_geog, s.g) AS m)
                   ORDER BY ST_DISTANCE(c.parcel_geog, s.g) LIMIT 1)[OFFSET(0)] AS w
  FROM cand c
  JOIN subs s ON ST_DWITHIN(c.parcel_geog, s.g, {RADIUS_M})
  GROUP BY 1, 2
)
SELECT c.parcel_source, c.parcel_key, c.county_fips, c.county_name,

       -- ⭐ transmission: the measurement that was missing entirely
       nl.w.feature_id                       AS line_feature_id,
       ROUND(nl.w.m / 1609.344, 3)          AS line_mi,
       (nl.w.m = 0)                          AS line_on_parcel,
       nl.w.kv                               AS line_kv,
       nl.w.volt_class                       AS line_volt_class,
       nl.w.owner                            AS line_owner,
       (nl.w.kv IS NULL)                     AS line_kv_unknown,

       ROUND(ns.w.m / 1609.344, 3)          AS sub_mi,
       ns.w.substation_name                  AS sub_name,
       ns.w.max_kv                           AS sub_kv,
       (ns.w.asset_class = 'unknown')        AS sub_class_unknown,

       CURRENT_TIMESTAMP() AS built_at
FROM cand c
LEFT JOIN near_line nl USING (parcel_source, parcel_key)
LEFT JOIN near_sub  ns USING (parcel_source, parcel_key)
"""

dry = client.query(SQL, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
gb = dry.total_bytes_processed / 1024 ** 3
usd = gb / 1024 * 6.25
print(f"DRY RUN: {gb:,.1f} GiB -> approx ${usd:,.2f}")
if usd > 25 and "--force" not in _sys.argv:
    print(f"COST GATE TRIPPED at ${usd:,.2f}. Not running. Re-run with --force if intended.")
    _sys.exit(1)

job = client.query(SQL); job.result()

m = list(client.query(f"""
SELECT COUNT(*) n, COUNT(DISTINCT CONCAT(parcel_source,'|',parcel_key)) d,
       COUNTIF(line_mi IS NOT NULL) with_line,
       COUNTIF(line_on_parcel) line_on,
       COUNTIF(line_mi <= 1) line_1mi,
       COUNTIF(line_kv_unknown) kv_unk,
       COUNTIF(line_kv >= 345) kv_345,
       COUNTIF(sub_mi IS NOT NULL) with_sub,
       COUNTIF(sub_mi = 0) sub_on,
       ROUND(APPROX_QUANTILES(line_mi, 2)[OFFSET(1)], 3) med_line,
       ROUND(APPROX_QUANTILES(sub_mi, 2)[OFFSET(1)], 3) med_sub
FROM `{DS}.{TARGET}`"""))[0]
fan = m.n / m.d if m.d else 0
print(f"{TARGET}: {m.n:,} rows over {m.d:,} parcels -> fan-out {fan:.3f}")
print(f"  with a transmission line within 25 mi : {m.with_line:,}")
print(f"  *** line PHYSICALLY ON the parcel     : {m.line_on:,}   <- the map reports ~0.55 mi for these")
print(f"  within 1 mile of a line               : {m.line_1mi:,}")
print(f"  nearest line is >= 345 kV             : {m.kv_345:,}")
print(f"  nearest line voltage UNKNOWN          : {m.kv_unk:,}  (reported as unknown, never 0)")
print(f"  median line distance                  : {m.med_line} mi")
print(f"  with a substation within 25 mi        : {m.with_sub:,}")
print(f"  substation ON the parcel              : {m.sub_on:,}")
print(f"  median substation distance            : {m.med_sub} mi")
assert fan < 1.01, "fan-out above 1.0 - a join duplicated parcels"
assert m.with_line > 0, "zero parcels matched a line - check in_transmission_union.geog"

# ---- both registries, same run (G16) ----
client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{TARGET}'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
    f"VALUES (@t,@s,@m,@n,@g,CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", TARGET),
        bigquery.ScalarQueryParameter("s", "STRING",
            f"{DS}.in_screener_candidates x {DS}.in_sites x {DS}.in_transmission_union "
            f"+ {DS}.in_substations_dedup"),
        bigquery.ScalarQueryParameter("m", "STRING",
            f"G29: exact ST_DISTANCE(parcel_geog, asset) within {RADIUS_M/1609.344:.0f} mi, so an "
            f"asset crossing a parcel returns 0.0 rather than the first-vertex approximation the map "
            f"console computes. Substations restricted to asset_class='substation' (taps and dead "
            f"ends excluded, G19). Line kv <= 0 or NULL -> NULL (HIFLD -999999 marker, G13); never 0. "
            f"D85 excluded by key before any spatial work; fan-out asserted < 1.01. "
            f"RE-SCRAPE COMMAND: python scripts/build_asset_distance_parcel.py"),
        bigquery.ScalarQueryParameter("n", "INT64", int(m.n)),
        bigquery.ScalarQueryParameter("g", "FLOAT64", round(job.total_bytes_processed / 1024**3, 2)),
        bigquery.ScalarQueryParameter("no", "STRING",
            f"Closes G29 for transmission and substations. {m.line_on:,} parcels have a transmission "
            f"line PHYSICALLY ON them (0.0 mi) where app.js repPt() reports ~0.55 mi. Bus distances "
            f"were already exact in in_screener_candidates (inj_mi/wd_mi/sub_mi); TRANSMISSION LINE "
            f"distance did not exist anywhere in the estate before this table, and it is the asset "
            f"where the error is largest because a LineString can cross a polygon. "
            f"line_kv_unknown is carried explicitly so an unlabelled line is never rendered as 0 kV.")])).result()
print(f"registered {TARGET} in indiana_app._registry")

tb = client.get_table("energy-platfrom.energy.registry_sources")
cols = {f.name for f in tb.schema}
row = {k: v for k, v in {
    "source_name": "Indiana parcel-to-grid-asset distance (derived)",
    "endpoint": "derived - no external endpoint",
    "endpoint_kind": "derived",
    "access": "internal-derived",
    "status": f"BUILT+LOADED ({m.n:,} parcels; {m.line_on:,} with a line on the parcel)",
    "acquisition_method": "RE-SCRAPE COMMAND: python scripts/build_asset_distance_parcel.py",
    "what_it_provides": "nearest transmission line and substation per candidate parcel by true "
                        "geodesic ST_DISTANCE against real geometry; 0.0 where the asset crosses "
                        "the parcel; carries line kV with unknown flagged rather than zeroed",
    "object_names": [TARGET],
    "geography_state": "IN",
    "measured_rows": int(m.n),
    "notes": "G29. Replaces the client-side first-vertex approximation in app.js repPt(), which "
             "measured an arbitrary parcel corner to one binned vertex per line and therefore always "
             "overstated distance and never returned 0. Written by the indiana_app workstream "
             "2026-08-17; APPEND-only.",
}.items() if k in cols}
errs = client.insert_rows_json("energy-platfrom.energy.registry_sources", [row])
print(f"appended to energy.registry_sources: {errs if errs else 'ok'}")
