"""G116 - what is the headroom on BOTH buses a transmission line attaches to?

    python scripts/build_line_bus_endpoints.py

Operator, 2026-08-19: *"We need to know what the headroom is on BOTH buses that the nearest
transmission line attaches to."* And the reason, from G118: *"follow it on both ends to the bus,
taking the measurement of the lower bus headroom … the lower of the two is chosen since it
requires flow from both ends."*

⭐ WHY THIS IS THE RIGHT QUESTION. Every grid figure the app shows today is "the nearest bus by
STRAIGHT-LINE DISTANCE", which says nothing about whether that bus is electrically connected to the
wire running past the parcel. A line is the thing a site actually taps, and a line is fed from both
ends — so the capacity it can deliver is bounded by the WEAKER end, not by whichever bus
happens to be closest as the crow flies.

⛔ NAMES DO NOT WORK HERE, AND THAT WAS MEASURED BEFORE THIS WAS BUILT. `in_transmission_union`
carries `sub_1` / `sub_2`, and on paper 2,553 of 3,737 lines (68.3%) name both. But most of those
names are HIFLD placeholders - `UNKNOWN123179`, `TAP139012` - not stations. Excluding them,
**only 289 lines (7.7%) name a real substation at both ends.** A name-based chain would have
covered a fourteenth of the network and looked like a coverage problem rather than a method problem.

⭐ GEOMETRY WORKS. A line's endpoints ARE its own first and last vertices:
`ST_DUMP(ST_BOUNDARY(geog), 0)` returns exactly 2.00 points per LineString across all 3,736 of
them. Match each endpoint to the nearest LOCATED bus and the chain needs no names at all.

⭐ THE TOLERANCE IS READ OFF THE DATA, NOT CHOSEN. Endpoint-to-nearest-bus distance is sharply
bimodal: deciles run 0, 3, 8, 23, 118, 902, 3178, 7860 m. The first four deciles are inside 23 m -
those endpoints are literally AT a bus - and then it breaks hard. **100 m** sits in the gap, and
catches 2,914 of 7,472 endpoints (39.0%). Loosening to 2 km would only reach 54.8% while starting
to attach lines to buses they do not touch.

⛔ ONE END IS NOT AN ANSWER. If only one endpoint resolves, `wd_min_mw` is NULL - NOT the one
value we happen to have. The operator's rule is the MINIMUM of both ends because power has to flow
in from both; a single end is a different, weaker claim and must not be dressed as this one. Every
row carries `ends_resolved` (0, 1 or 2) so a surface can say which case it is looking at.

WRITES `indiana_app.in_line_bus_endpoints`. Reads indiana_app only.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_line_bus_endpoints"
TOL_M = 100          # read off the bimodal break, see the header
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH
-- one row per line endpoint, numbered so the two ends stay distinguishable
ends AS (
  /* ⚠ HIFLD's not-available marker for voltage is the literal -999999, on 335 lines. app.js
     already guards it (see its note at the transmission layer) but this table would have
     passed it straight through to a new surface as a negative kilovolt. NULL is the only
     honest value: unpublished is NULL, never a sentinel. */
  SELECT l.feature_id, IF(l.kv > 0, l.kv, NULL) AS kv, l.volt_class, l.owner, l.km,
         ep, ROW_NUMBER() OVER (PARTITION BY l.feature_id ORDER BY ST_ASTEXT(ep)) AS end_no
  FROM `{DS}.in_transmission_union` l, UNNEST(ST_DUMP(ST_BOUNDARY(l.geog), 0)) ep
  WHERE l.geog IS NOT NULL AND ST_GEOMETRYTYPE(l.geog) = 'ST_LineString'
),
-- one row per located bus, with BOTH directions folded onto it (G111)
bus AS (
  SELECT bus_id,
         ANY_VALUE(bus_name) bus_name, ANY_VALUE(iso) iso,
         ANY_VALUE(bus_voltage_kv) bus_kv,
         ST_GEOGPOINT(ANY_VALUE(longitude), ANY_VALUE(latitude)) g,
         MAX(IF(interconnection_type = 'Withdrawal', bus_interconnection_capacity_mw, NULL)) wd_mw,
         MAX(IF(interconnection_type = 'Injection',  bus_interconnection_capacity_mw, NULL)) inj_mw,
         MAX(IF(interconnection_type = 'Withdrawal', primary_limiting_constraint, NULL)) wd_binding,
         MAX(IF(interconnection_type = 'Injection',  primary_limiting_constraint, NULL)) inj_binding,
         ANY_VALUE(provenance_class) provenance
  FROM `{DS}.in_bus_capacity_tier0`
  WHERE latitude IS NOT NULL AND longitude IS NOT NULL
  GROUP BY bus_id
),
-- nearest bus to each endpoint, inside the tolerance
matched AS (
  SELECT e.feature_id, e.kv, e.volt_class, e.owner, e.km, e.end_no,
         ARRAY_AGG(STRUCT(b.bus_id, b.bus_name, b.iso, b.bus_kv, b.wd_mw, b.inj_mw,
                          b.wd_binding, b.inj_binding, b.provenance,
                          ST_DISTANCE(e.ep, b.g) AS dist_m)
                   ORDER BY ST_DISTANCE(e.ep, b.g) LIMIT 1)[OFFSET(0)] AS m
  FROM ends e
  LEFT JOIN bus b ON ST_DWITHIN(e.ep, b.g, {TOL_M})
  GROUP BY 1, 2, 3, 4, 5, 6
),
wide AS (
  SELECT feature_id, ANY_VALUE(kv) kv, ANY_VALUE(volt_class) volt_class,
         ANY_VALUE(owner) owner, ANY_VALUE(km) km,
         MAX(IF(end_no = 1, m.bus_id,      NULL)) a_bus_id,
         MAX(IF(end_no = 1, m.bus_name,    NULL)) a_bus_name,
         MAX(IF(end_no = 1, m.iso,         NULL)) a_iso,
         MAX(IF(end_no = 1, m.wd_mw,       NULL)) a_wd_mw,
         MAX(IF(end_no = 1, m.inj_mw,      NULL)) a_inj_mw,
         MAX(IF(end_no = 1, m.wd_binding,  NULL)) a_wd_binding,
         MAX(IF(end_no = 1, m.inj_binding, NULL)) a_inj_binding,
         MAX(IF(end_no = 1, m.dist_m,      NULL)) a_dist_m,
         MAX(IF(end_no = 2, m.bus_id,      NULL)) b_bus_id,
         MAX(IF(end_no = 2, m.bus_name,    NULL)) b_bus_name,
         MAX(IF(end_no = 2, m.iso,         NULL)) b_iso,
         MAX(IF(end_no = 2, m.wd_mw,       NULL)) b_wd_mw,
         MAX(IF(end_no = 2, m.inj_mw,      NULL)) b_inj_mw,
         MAX(IF(end_no = 2, m.wd_binding,  NULL)) b_wd_binding,
         MAX(IF(end_no = 2, m.inj_binding, NULL)) b_inj_binding,
         MAX(IF(end_no = 2, m.dist_m,      NULL)) b_dist_m
  FROM matched GROUP BY feature_id
)
SELECT *,
  (CAST(a_bus_id IS NOT NULL AS INT64) + CAST(b_bus_id IS NOT NULL AS INT64)) AS ends_resolved,
  /* ⛔ THE MINIMUM IS ONLY DEFINED WHEN BOTH ENDS ARE KNOWN. With one end we hold a number, but
     it is not the answer to the operator's question and must not be served as one. */
  IF(a_bus_id IS NOT NULL AND b_bus_id IS NOT NULL, LEAST(a_wd_mw,  b_wd_mw),  NULL) AS wd_min_mw,
  IF(a_bus_id IS NOT NULL AND b_bus_id IS NOT NULL, LEAST(a_inj_mw, b_inj_mw), NULL) AS inj_min_mw,
  IF(a_bus_id IS NOT NULL AND b_bus_id IS NOT NULL,
     IF(IFNULL(a_wd_mw, 1e18) <= IFNULL(b_wd_mw, 1e18), a_wd_binding, b_wd_binding), NULL)
     AS wd_binding_at_limit,
  IF(a_bus_id IS NOT NULL AND b_bus_id IS NOT NULL,
     IF(IFNULL(a_inj_mw, 1e18) <= IFNULL(b_inj_mw, 1e18), a_inj_binding, b_inj_binding), NULL)
     AS inj_binding_at_limit,
  IF(a_bus_id IS NOT NULL AND b_bus_id IS NOT NULL,
     IF(IFNULL(a_wd_mw, 1e18) <= IFNULL(b_wd_mw, 1e18), a_bus_name, b_bus_name), NULL)
     AS wd_limiting_end
FROM wide
"""

print(f"building in_line_bus_endpoints (tolerance {TOL_M} m) ...")
job = client.query(SQL)
job.result()
gb = round((job.total_bytes_processed or 0) / 1e9, 3)

s = list(client.query(f"""
SELECT COUNT(*) lines,
       COUNTIF(ends_resolved = 2) both_,
       COUNTIF(ends_resolved = 1) one_,
       COUNTIF(ends_resolved = 0) none_,
       COUNTIF(wd_min_mw IS NOT NULL) wd,
       COUNTIF(inj_min_mw IS NOT NULL) inj,
       ROUND(APPROX_QUANTILES(wd_min_mw, 2)[OFFSET(1)], 1) wd_med,
       ROUND(APPROX_QUANTILES(inj_min_mw, 2)[OFFSET(1)], 1) inj_med
FROM `{OUT}`"""))[0]
print(f"  {s.lines:,} lines, {gb} GB scanned\n")
print(f"  BOTH ends resolved to a bus : {s.both_:,}  ({100*s.both_/s.lines:.1f}%)")
print(f"  one end only                : {s.one_:,}   -> min is NULL, deliberately")
print(f"  neither end                 : {s.none_:,}")
print(f"  with a withdrawal minimum   : {s.wd:,}  median {s.wd_med} MW")
print(f"  with an injection minimum   : {s.inj:,}  median {s.inj_med} MW")

print("\n  worked examples (both ends, lowest first):")
for r in client.query(f"""
  SELECT kv, a_bus_name, a_wd_mw, b_bus_name, b_wd_mw, wd_min_mw, wd_limiting_end
  FROM `{OUT}` WHERE ends_resolved = 2 AND wd_min_mw IS NOT NULL
  ORDER BY wd_min_mw DESC LIMIT 6"""):
    print(f"   {str(r.kv):>5} kV  {str(r.a_bus_name)[:16]:18s}{r.a_wd_mw:>8,.0f}  |  "
          f"{str(r.b_bus_name)[:16]:18s}{r.b_wd_mw:>8,.0f}  ->  MIN {r.wd_min_mw:>8,.0f} MW"
          f"  (limited at {str(r.wd_limiting_end)[:14]})")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_line_bus_endpoints',
 'indiana_app.in_transmission_union x in_bus_capacity_tier0',
 'line endpoints taken GEOMETRICALLY via ST_DUMP(ST_BOUNDARY(geog),0) - not from sub_1/sub_2, '
 'which name a real substation at both ends on only 289 of 3,737 lines; each endpoint matched to '
 'the nearest located bus within {TOL_M} m, a tolerance read off the bimodal distance '
 'distribution; both directions folded per bus; the MINIMUM is emitted only when BOTH ends '
 'resolve. RE-SCRAPE COMMAND: python scripts/build_line_bus_endpoints.py',
 {s.lines}, {gb}, CURRENT_TIMESTAMP(),
 'G116, and the input to G118. {s.both_} of {s.lines} lines resolve at both ends. A line with one '
 'end resolved reports NULL for the minimum, never the single end we happen to hold - the '
 'operator asked for the lower of two because flow comes from both ends, and one end is a '
 'different and weaker claim.'
)""").result()
print("\n  _registry row written")
print("LINE-BUS ENDPOINTS COMPLETE")
