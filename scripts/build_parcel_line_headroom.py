"""G118 - the screener's MW from BUS HEADROOM, by the operator's own method.

    python scripts/build_parcel_line_headroom.py

Operator, 2026-08-19, specifying the methodology outright: *"instead of saying how many MW a site
could get to based on acreage, we should calculate it off of buses. The methodology we should use
is the following: we should locate the nearest transmission asset to the site location and follow
it on both ends to the bus, taking the measurement of the lower bus headroom, for both withdrawal
AND injection. This allows the user to see the grid constraints and how they can apply to siting a
DC or BESS … the lower of the two is chosen since it requires flow from both ends."*

⭐ THIS CHANGES WHAT THE HEADLINE NUMBER MEANS. `mw_dc` today is `buildable_acres x density` - a
LAND figure. It answers "how much plant fits on this ground" and is completely silent on whether
one megawatt can be delivered to it. This is the DELIVERABLE figure.

⛔ BOTH ARE KEPT. They are different constraints and a site is capped by the LOWER of them.
Collapsing to one hides which one binds, and which one binds is the whole point: a 900-acre parcel
on a line whose weaker end has 12 MW is a 12 MW site, and a reader needs to see why.

    mw_dc            land:  buildable acres x your density assumption
    mw_deliverable   grid:  min(headroom at end A, headroom at end B) of the nearest line
    binding_basis    which of the two is smaller, named

⛔ THE MINIMUM-OF-BOTH-ENDS RULE IS THE OPERATOR'S AND IT IS ELECTRICALLY RIGHT - power reaches a
mid-line tap from both directions, so the weaker end bounds it. Not a modelling choice to revisit.

⚠ COVERAGE IS THE HONEST PROBLEM, AND IT IS STATED RATHER THAN PAPERED OVER. Only 1,018 of 3,736
lines (27.2%) resolve to a located bus at BOTH ends, because only 15.1% of PJM buses carry a
coordinate at all (G114). A parcel whose nearest line has one or zero resolved ends gets
**deliverable_basis = 'cannot_assess'** and a NULL figure. ⛔ It must never render as 0 MW: "we
cannot follow this line to its buses" and "this line can deliver nothing" are opposite claims.

⚠ AND THE NEAREST LINE IS NOT ALWAYS THE RIGHT LINE. This uses the nearest by exact ST_DISTANCE
(edge to edge, from `in_asset_distance_parcel`), which is the best available proxy for "what would
you tap". A developer may well tap a different circuit. The distance is carried so the reader can
judge - a line 8 miles away is a weaker premise than one crossing the parcel.

WRITES `indiana_app.in_parcel_line_headroom`. Reads indiana_app only.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_parcel_line_headroom"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
SELECT
  d.parcel_source, d.parcel_key,
  d.line_feature_id, d.line_mi, d.line_on_parcel, d.line_kv,
  e.a_bus_name, e.a_iso, e.a_wd_mw, e.a_inj_mw,
  e.b_bus_name, e.b_iso, e.b_wd_mw, e.b_inj_mw,
  e.ends_resolved,
  e.wd_min_mw   AS deliverable_wd_mw,
  e.inj_min_mw  AS deliverable_inj_mw,
  e.wd_binding_at_limit, e.inj_binding_at_limit, e.wd_limiting_end,
  /* ⛔ Three states, never two. NULL capacity with basis 'both_ends' would be a measured zero;
     NULL with 'cannot_assess' means we could not follow the line. A surface must tell them
     apart, so the basis rides on every row. */
  CASE
    WHEN d.line_feature_id IS NULL      THEN 'no_line_within_25mi'
    WHEN e.feature_id IS NULL           THEN 'line_not_in_topology'
    WHEN e.ends_resolved = 2            THEN 'both_ends'
    WHEN e.ends_resolved = 1            THEN 'cannot_assess_one_end_only'
    ELSE                                     'cannot_assess_no_end_located'
  END AS deliverable_basis
FROM `{DS}.in_asset_distance_parcel` d
LEFT JOIN `{DS}.in_line_bus_endpoints` e
       ON e.feature_id = d.line_feature_id
WHERE d.parcel_key != '080500000047000018'
"""

print("building in_parcel_line_headroom ...")
job = client.query(SQL)
job.result()
gb = round((job.total_bytes_processed or 0) / 1e9, 3)

n = list(client.query(f"""SELECT COUNT(*) n, COUNT(DISTINCT parcel_key) p FROM `{OUT}`"""))[0]
print(f"  {n.n:,} rows over {n.p:,} parcels -> fan-out {n.n/max(n.p,1):.3f}")
assert abs(n.n / max(n.p, 1) - 1.0) < 0.001, "FAN-OUT: the line join duplicated parcels"

print("\n  deliverable_basis:")
for r in client.query(f"""SELECT deliverable_basis b, COUNT(*) n FROM `{OUT}`
                          GROUP BY 1 ORDER BY n DESC"""):
    print(f"    {r.b:32s} {r.n:>9,}")

s = list(client.query(f"""
SELECT COUNTIF(deliverable_wd_mw IS NOT NULL) wd,
       COUNTIF(deliverable_inj_mw IS NOT NULL) inj,
       COUNTIF(deliverable_wd_mw >= 300) wd300,
       COUNTIF(deliverable_wd_mw = 0) wd0,
       ROUND(APPROX_QUANTILES(deliverable_wd_mw, 2)[OFFSET(1)], 1) wd_med,
       ROUND(APPROX_QUANTILES(deliverable_inj_mw, 2)[OFFSET(1)], 1) inj_med
FROM `{OUT}`"""))[0]
print(f"\n  parcels with a DELIVERABLE withdrawal figure : {s.wd:,}   median {s.wd_med} MW")
print(f"  parcels with a DELIVERABLE injection figure  : {s.inj:,}   median {s.inj_med} MW")
print(f"  ...of which >= 300 MW deliverable            : {s.wd300:,}")
print(f"  ...measured at exactly 0 MW (real, not gap)  : {s.wd0:,}")

print("\n  LAND vs GRID — which constraint actually binds?")
for r in client.query(f"""
  SELECT CASE WHEN h.deliverable_wd_mw IS NULL THEN 'grid not assessable'
              WHEN c.mw_dc IS NULL             THEN 'land not assessable'
              WHEN h.deliverable_wd_mw < c.mw_dc THEN 'GRID binds (deliverable < buildable)'
              ELSE 'LAND binds (buildable < deliverable)' END AS who,
         COUNT(*) n
  FROM `{OUT}` h JOIN `{DS}.in_screener_candidates` c USING (parcel_source, parcel_key)
  GROUP BY 1 ORDER BY n DESC"""):
    print(f"    {r.who:40s} {r.n:>9,}")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_parcel_line_headroom',
 'indiana_app.in_asset_distance_parcel x in_line_bus_endpoints',
 'parcel -> nearest transmission line by exact edge-to-edge ST_DISTANCE -> the two '
 'endpoint buses -> MIN(headroom) per direction, per the operator stated method. The minimum '
 'is emitted ONLY where both ends resolve; one end or none yields NULL with an explicit '
 'cannot_assess basis, never 0. '
 'RE-SCRAPE COMMAND: python scripts/build_parcel_line_headroom.py',
 {n.n}, {gb}, CURRENT_TIMESTAMP(),
 'G118. The DELIVERABLE figure, to sit beside the LAND figure (mw_dc = acres x density) rather '
 'than replace it - a site is capped by the lower of the two and which one binds is the point. '
 'Coverage is bounded by G114: only 27.2% of lines resolve at both ends because only 15.1% of '
 'PJM buses carry a coordinate.'
)""").result()
print("\n  _registry row written")
print("PARCEL LINE HEADROOM COMPLETE")
