"""G142: EVERY TRANSMISSION LINE WITHIN REACH, NOT JUST THE NEAREST ONE.

Operator, 2026-08-21: *"In the case where there are multiple transmission lines within our
specified parameters, we should include ALL bus headrooms that stem from each of the two ends of
the transmission lines, since we may not always interconnect with the closest transmission line."*

================================================================================================
⭐ WHY THE NEAREST LINE IS A BAD PROXY, MEASURED RATHER THAN ASSERTED
================================================================================================
`in_parcel_line_headroom` follows ONE line — the nearest by exact edge-to-edge distance — to the
buses at its two ends and takes the lower (G116/G118/G131). That is the right calculation for that
line. It is the wrong question when the parcel has five.

Measured across the 431,048 parcels with at least one capacity-bearing line inside 3 miles:
    · the average parcel has **5.11 candidate lines**, and we were showing one
    · **196,528 (45.6%) have a BETTER line than their nearest**
    · **131,503** are better by more than 100 MW
    · ⭐ **91,836 cross the 300 MW threshold** — their nearest line reads under 300 MW while a line
      within three miles delivers 300 or more. Those are hyperscale-capable sites the screener was
      presenting as not.
    · **50,735 gain a figure they did not have at all**, because the nearest line's endpoints do
      not resolve to a bus and a neighbouring line's do.
⚠ The median uplift is 0.0 MW, and that is the honest other half: for most parcels the nearest line
IS the best one. The point is the tail, not the average.

================================================================================================
⛔ WHAT THIS DOES NOT DO, AND WHY
================================================================================================
It does NOT replace the nearest-line figure. A better line further away is not free — reaching it
means a gen-tie, an easement, and a longer route — so both travel together and the DISTANCE rides
with the alternative. Presenting the best figure alone would be the mirror image of the defect
being fixed: a number the reader cannot act on without knowing what it costs to reach.

⚠ 3 MILES IS A STATED PARAMETER, NOT A DISCOVERED ONE. The operator's phrasing is "within our
specified parameters". 3 miles (4,828 m) is a plausible gen-tie for a large load and it keeps the
join at 2.2M pairs. It is a single constant here so it can be argued with and changed.

⛔ D85 excluded. ⚠ Fan-out is asserted at 1.0 — one row per parcel, never one per line.

RE-SCRAPE COMMAND: python scripts/build_parcel_line_options.py
⚠ IDEMPOTENT: replace_safe. Depends on in_line_bus_endpoints and in_parcel_line_headroom.
⛔ THEN RE-EXPORT: scripts/build_screener_candidates.py, scripts/export_screener.py.
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_parcel_line_options"
D85 = "080500000047000018"
RADIUS_M = 4828          # 3 miles. A stated parameter - see the header.
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH lc AS (
  -- every line that can actually offer a number, with the bus figures already resolved by G131
  SELECT e.feature_id, e.kv, e.wd_min_mw, e.inj_min_mw, e.ends_resolved,
         e.wd_limiting_end, e.wd_limiting_iso, e.wd_limiting_tier, l.geog
  FROM `{DS}.in_line_bus_endpoints` e
  JOIN `{DS}.in_transmission_union` l USING (feature_id)
  WHERE e.wd_min_mw IS NOT NULL AND l.geog IS NOT NULL
),
/* ⛔ RESTRICTED TO THE PARCELS in_parcel_line_headroom ACTUALLY COVERS, AND THE FIRST VERSION WAS
   NOT. Joining all 3.55M rows of in_sites produced a table over parcels that have no nearest-line
   figure to compare against, and the summary then reported **2,828,776 parcels "gaining a figure
   they had none for"** - which counts parcels that were never in the comparison at all. The two
   tables must describe the same population or the uplift is not an uplift.
   ⚠ A clean, alarming number is a claim about the instrument first. 2.8M was both. */
p AS (
  SELECT s.parcel_source, s.parcel_key, s.parcel_geog
  FROM `{DS}.in_sites` s
  JOIN `{DS}.in_parcel_line_headroom` hh
    ON hh.parcel_source = s.parcel_source AND hh.parcel_key = s.parcel_key
  WHERE s.parcel_key != '{D85}' AND s.parcel_geog IS NOT NULL
),
pair AS (
  SELECT p.parcel_source, p.parcel_key, lc.feature_id, lc.kv,
         lc.wd_min_mw, lc.inj_min_mw, lc.wd_limiting_end, lc.wd_limiting_iso, lc.wd_limiting_tier,
         ST_DISTANCE(p.parcel_geog, lc.geog) / 1609.344 AS mi
  FROM p JOIN lc ON ST_DWITHIN(p.parcel_geog, lc.geog, {RADIUS_M})
),
ranked AS (
  SELECT *, ROW_NUMBER() OVER (
      PARTITION BY parcel_source, parcel_key
      -- ⚠ best CAPACITY first, then nearest as the tie-break. A tie on MW should prefer the line
      -- that is cheaper to reach.
      ORDER BY wd_min_mw DESC, mi ASC) AS rk
  FROM pair
),
agg AS (
  SELECT parcel_source, parcel_key,
         COUNT(*)                                   AS n_line_options,
         COUNTIF(wd_min_mw >= 300)                  AS n_options_300mw,
         MAX(wd_min_mw)                             AS best_wd_mw
  FROM pair GROUP BY 1, 2
)
SELECT
  a.parcel_source, a.parcel_key,
  a.n_line_options, a.n_options_300mw,
  -- the winner, with everything needed to judge whether it is worth reaching
  r.feature_id                       AS best_line_feature_id,
  ROUND(r.mi, 2)                     AS best_line_mi,
  r.kv                               AS best_line_kv,
  ROUND(r.wd_min_mw, 1)              AS best_wd_mw,
  ROUND(r.inj_min_mw, 1)             AS best_inj_mw,
  r.wd_limiting_end                  AS best_limiting_end,
  r.wd_limiting_iso                  AS best_limiting_iso,
  r.wd_limiting_tier                 AS best_limiting_tier,
  -- the nearest-line figure this sits beside, so the uplift is computable on one row
  ROUND(h.deliverable_wd_mw, 1)      AS nearest_wd_mw,
  ROUND(h.line_mi, 2)                AS nearest_line_mi,
  h.deliverable_basis                AS nearest_basis,
  /* ⭐ THE "SO WHAT", PRECOMPUTED. A positive uplift means a better circuit exists within
     {RADIUS_M} m and the reader is currently being shown the weaker one. ⚠ It is only actionable
     WITH `best_line_mi` beside it - the extra MW costs the extra distance in gen-tie. */
  ROUND(r.wd_min_mw - IFNULL(h.deliverable_wd_mw, 0), 1) AS uplift_wd_mw,
  (r.wd_min_mw >= 300 AND IFNULL(h.deliverable_wd_mw, 0) < 300) AS crosses_300mw,
  CURRENT_TIMESTAMP() AS built_at
FROM agg a
JOIN ranked r ON r.parcel_source = a.parcel_source AND r.parcel_key = a.parcel_key AND r.rk = 1
LEFT JOIN `{DS}.in_parcel_line_headroom` h
       ON h.parcel_source = a.parcel_source AND h.parcel_key = a.parcel_key
"""

print("=" * 96)
print(f"G142 - EVERY LINE WITHIN {RADIUS_M} m ({RADIUS_M/1609.344:.0f} miles), NOT JUST THE NEAREST")
print("=" * 96)
job = client.query(SQL)
job.result()
print(f"  built, {round((job.total_bytes_processed or 0)/1e9, 2)} GB scanned")

s = list(client.query(f"""
  SELECT COUNT(*) n, COUNT(DISTINCT CONCAT(parcel_source,'|',parcel_key)) d,
         ROUND(AVG(n_line_options),2) avg_opts,
         COUNTIF(uplift_wd_mw > 0)   better,
         COUNTIF(uplift_wd_mw > 100) better_100,
         COUNTIF(crosses_300mw)      crosses,
         COUNTIF(nearest_wd_mw IS NULL) gains_a_figure,
         ROUND(APPROX_QUANTILES(best_line_mi,100)[OFFSET(50)],2) med_best_mi,
         ROUND(APPROX_QUANTILES(nearest_line_mi,100)[OFFSET(50)],2) med_near_mi
  FROM `{OUT}`"""))[0]
fan = s.n / s.d if s.d else 0
print(f"  fan-out {s.n:,} rows / {s.d:,} parcels = {fan:.4f}")
if fan > 1.0001:
    raise SystemExit(f"⛔ fan-out {fan:.4f} - this must be ONE row per parcel, not one per line.")

print(f"\n  {s.d:,} parcels · {s.avg_opts} candidate lines each on average")
print(f"  ⭐ {s.better:,} have a BETTER line than their nearest  ({s.better_100:,} better by >100 MW)")
print(f"  ⭐ {s.crosses:,} cross the 300 MW threshold that their nearest line said they could not")
print(f"  ⭐ {s.gains_a_figure:,} gain a deliverable figure they had NONE for")
print(f"  ⚠ median distance: nearest line {s.med_near_mi} mi · best line {s.med_best_mi} mi "
      f"- the extra MW costs the extra reach")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_parcel_line_options'").result()
client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at)
VALUES ('in_parcel_line_options',
 'indiana_app.in_line_bus_endpoints + in_transmission_union + in_sites + in_parcel_line_headroom',
 'G142. Every capacity-bearing transmission line within {RADIUS_M} m (3 miles) of the parcel, '
 'ranked by deliverable withdrawal MW then by distance, keeping the winner plus a count of the '
 'options. Sits BESIDE the nearest-line figure rather than replacing it - a better line further '
 'away costs a gen-tie, so best_line_mi always travels with best_wd_mw. D85 excluded; fan-out '
 'asserted at 1.0 (one row per parcel). '
 'RE-SCRAPE COMMAND: python scripts/build_parcel_line_options.py IDEMPOTENT: replace_safe. '
 'THEN RE-EXPORT scripts/build_screener_candidates.py and scripts/export_screener.py.',
 (SELECT COUNT(*) FROM `{OUT}`), CURRENT_TIMESTAMP())""").result()
print("\n  registered in_parcel_line_options")
print("\nDONE")
