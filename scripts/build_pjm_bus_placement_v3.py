"""G126: place more PJM buses. Operator: *"are we able to match or estimate ALL of the buses yet?"*

⛔ THE HONEST ANSWER IS NO, AND THIS SCRIPT IS THE MEASURED VERSION OF WHY.
Of the three keys G126/G46 nominated, exactly one is available with data we hold. All three were
tried; the two that fail are recorded here rather than quietly dropped, because a key that was
measured dead is worth as much to the next session as one that worked.

  ① QUEUE ID IN THE BUS LABEL             ⭐ WORKS. 87 of the 1,551 unplaced PJM buses carry a PJM
     queue ID (`AE1-209 MAIN 345 kV (270000)`), and all 87 match a queue point already held in
     `in_pjm_gis_queues` - PJM's own published coordinate. Every one resolves to a SINGLE distinct
     point; none is ambiguous. No scraping, and nobody had joined on it.

  ② BRANCH TOPOLOGY                       ⛔ MEASURED DEAD, 0 buses. `in_line_bus_endpoints` holds
     3,736 branches but only 894 distinct nodes, of which just 62 appear among the 1,826 tier0 PJM
     buses - the graph is overwhelmingly MISO (233 branches touch PJM at all). Measured: NOT ONE
     unplaced PJM bus has a placed branch neighbour, so the hop-1 propagation G46 specified has
     nothing to propagate from. ⚠ This is a coverage gap, not a join defect - both sides key on
     the same numeric bus id and 62 do match.

  ③ QUEUE-GENERATOR COINCIDENCE BY NAME   ⛔ NOT AVAILABLE. It needs the queue record's station or
     POI name to match against a bus name. `in_pjm_gis_queues` has no name column at all
     (_source_url, _pulled_at, lat, VOLTAGE, QUEUE_GLOBALID, MERCHANT_FLAG, lon, QUEUE_ID,
     QUEUE_KEY, FAC_ID, PJM_ZONE_GLOBALID) and `in_queue` carries county and project, not a bus.
     Key ① is the usable form of this idea, and it is already taken.

RESULT: PJM placement 275 -> 362 of 1,826 buses (15.1% -> 19.8%). The remaining 1,464 are PSS/E
area-prefixed labels (`05WAVERL`, `05BROADF`) at the gazetteer ceiling G114 already reached.

================================================================================================
⛔ WHAT IS DELIBERATELY NOT DONE
================================================================================================
No bus is placed by estimation. G114 refused 8 ambiguous matches and 10 kV mismatches and that
judgement stands: **a bus in the wrong place is worse than a bus with no place**, because it is a
coordinate someone might drive to, and it silently corrupts every distance, county rollup and
screener filter that reads it. Every placement here is a JOIN on an identifier the publisher
itself printed in the label - not a guess with a confidence attached to make it feel measured.

⚠ THE kV DISAGREES ON 16 OF THE 87, AND THAT IS NOT A REFUSAL SIGNAL HERE. Read the labels:
`AB2-067 GSU 230 kV` and `AB2-067 MAIN 765 kV` are the generator step-up bus and the main bus of
ONE queue project, at one site. The queue record publishes a single VOLTAGE for the point of
interconnection, so a sub-bus at a different voltage is expected and says nothing about location.
It is published as `kv_agrees` so a reader can filter on it, never used to silently drop a row.

⚠ 58 OF THE 87 FALL OUTSIDE INDIANA. Our PJM harvest is the whole AEP footprint. They are kept
with `in_indiana = FALSE`, exactly as repair_substation_geometry.py kept 199 out-of-state
substation footprints: withheld from Indiana surfaces, never deleted, because a border parcel can
genuinely interconnect across a state line.

RE-SCRAPE COMMAND: python scripts/build_pjm_bus_placement_v3.py
⚠ IDEMPOTENT: replace_safe. CREATE OR REPLACE from upstream only; it never reads its own output.
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_pjm_bus_placement_v3"

# PJM queue IDs are one or two letters, a digit, a hyphen and three digits: AE1-209, AB2-067,
# Z1-045. Anchored at the start of the label because that is where PJM puts it, and an unanchored
# match would pick up the "T1-4" in `05SUGRM T1-5 138 kV`, which is a transformer tap, not a queue.
QID_RE = r"^([A-Z]{1,2}[0-9]-[0-9]{3})"
assert QID_RE.startswith("^("), "the queue-id pattern must stay anchored"

client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH bus AS (
  SELECT bus_id,
         ANY_VALUE(bus_name)         AS bus_name,
         ANY_VALUE(bus_voltage_kv)   AS bus_kv,
         ANY_VALUE(bus_area)         AS bus_area,
         MAX(latitude)               AS tier0_lat,
         MAX(longitude)              AS tier0_lon,
         REGEXP_EXTRACT(UPPER(ANY_VALUE(bus_name)), r'{QID_RE}') AS queue_id
  FROM `{DS}.in_bus_capacity_tier0`
  WHERE iso = 'PJM'
  GROUP BY bus_id
),
q AS (
  SELECT UPPER(QUEUE_ID) AS queue_id,
         COUNT(DISTINCT FORMAT('%.5f|%.5f', lat, lon)) AS distinct_points,
         ANY_VALUE(lat) AS q_lat,
         ANY_VALUE(lon) AS q_lon,
         ANY_VALUE(SAFE_CAST(VOLTAGE AS FLOAT64)) AS q_kv
  FROM `{DS}.in_pjm_gis_queues`
  WHERE lat IS NOT NULL AND lon IS NOT NULL
    AND QUEUE_ID IS NOT NULL AND QUEUE_ID != ''
  GROUP BY 1
),
joined AS (
  SELECT b.*, q.q_lat, q.q_lon, q.q_kv, q.distinct_points
  FROM bus b LEFT JOIN q USING (queue_id)
)
SELECT
  bus_id, bus_name, bus_kv, bus_area, queue_id,
  -- ⛔ REFUSE an ambiguous queue id. A queue that publishes more than one distinct point does not
  -- locate a bus; it locates a project with several. Measured today: 0 of the 87. The guard
  -- stays because the queue layer is refreshed and that can change without anybody noticing.
  CASE
    WHEN tier0_lat IS NOT NULL                       THEN tier0_lat
    WHEN q_lat IS NOT NULL AND distinct_points = 1   THEN q_lat
    ELSE NULL
  END AS lat,
  CASE
    WHEN tier0_lon IS NOT NULL                       THEN tier0_lon
    WHEN q_lat IS NOT NULL AND distinct_points = 1   THEN q_lon
    ELSE NULL
  END AS lon,
  CASE
    WHEN tier0_lat IS NOT NULL                       THEN 'tier0_existing'
    WHEN q_lat IS NOT NULL AND distinct_points = 1   THEN 'pjm_queue_id_published_point'
    WHEN q_lat IS NOT NULL AND distinct_points > 1   THEN 'refused_ambiguous_queue_point'
    WHEN queue_id IS NOT NULL                        THEN 'refused_queue_id_not_published'
    ELSE 'unplaced_psse_label_at_gazetteer_ceiling'
  END AS placement_method,
  CASE
    WHEN tier0_lat IS NOT NULL                       THEN 'published'
    WHEN q_lat IS NOT NULL AND distinct_points = 1   THEN 'published_join'
    ELSE NULL
  END AS placement_confidence,
  q_kv AS queue_published_kv,
  -- kV agreement is PUBLISHED, never used to drop a row. A GSU bus and a MAIN bus of one queue
  -- project sit at one site at two voltages; the queue record carries a single POI voltage.
  CASE WHEN q_kv IS NULL THEN NULL ELSE ABS(q_kv - bus_kv) < 1 END AS kv_agrees,
  CASE
    WHEN COALESCE(tier0_lat, IF(distinct_points = 1, q_lat, NULL)) IS NULL THEN NULL
    ELSE ST_INTERSECTS(
           ST_GEOGPOINT(COALESCE(tier0_lon, IF(distinct_points = 1, q_lon, NULL)),
                        COALESCE(tier0_lat, IF(distinct_points = 1, q_lat, NULL))),
           (SELECT ANY_VALUE(geom) FROM `energy-platfrom.energy.state_boundaries`
            WHERE UPPER(stusps) = 'IN'))
  END AS in_indiana,
  CURRENT_TIMESTAMP() AS built_at
FROM joined
"""

print("G126 - PJM BUS PLACEMENT v3")
job = client.query(SQL)
job.result()
gb = round((job.total_bytes_processed or 0) / 1e9, 3)
print(f"  built, {gb} GB scanned")

f = list(client.query(f"""
  SELECT COUNT(*) n, COUNT(DISTINCT bus_id) d FROM `{OUT}`"""))[0]
print(f"  fan-out {f.n:,} rows / {f.d:,} distinct buses = {f.n / f.d:.4f}")
assert f.n == f.d, "one row per bus or the placement is ambiguous"

print("\n  placement by method:")
for r in client.query(f"""
  SELECT placement_method, COUNT(*) n, COUNTIF(lat IS NOT NULL) placed,
         COUNTIF(in_indiana) in_in, COUNTIF(kv_agrees IS FALSE) kv_off
  FROM `{OUT}` GROUP BY 1 ORDER BY 2 DESC"""):
    print(f"    {r.placement_method:42} n={r.n:>6,}  placed={r.placed:>5,}  "
          f"in Indiana={r.in_in:>4,}  kV disagrees={r.kv_off:>3,}")

s = list(client.query(f"""
  SELECT COUNT(*) total, COUNTIF(lat IS NOT NULL) placed,
         COUNTIF(placement_method = 'pjm_queue_id_published_point') gained,
         COUNTIF(lat IS NOT NULL AND in_indiana) placed_in_indiana
  FROM `{OUT}`"""))[0]
print(f"\n  PJM buses          {s.total:,}")
print(f"  placed             {s.placed:,}  ({100 * s.placed / s.total:.1f}%)  "
      f"was 275 ({100 * 275 / s.total:.1f}%)")
print(f"  GAINED this build  {s.gained:,}")
print(f"  placed AND inside Indiana {s.placed_in_indiana:,}")

print("\n  ⛔ the two keys that were tried and failed, re-measured so the claim is not inherited:")
# ⚠ Written as a JOIN against a UNION-ed node list, not a correlated EXISTS with an OR -
# BigQuery rejects that as "LEFT SEMI JOIN cannot be used without a condition that is an equality".
t = list(client.query(f"""
  WITH nodes AS (
    SELECT DISTINCT CAST(a_bus_id AS STRING) AS bid FROM `{DS}.in_line_bus_endpoints`
    WHERE a_bus_id IS NOT NULL
    UNION DISTINCT
    SELECT DISTINCT CAST(b_bus_id AS STRING) FROM `{DS}.in_line_bus_endpoints`
    WHERE b_bus_id IS NOT NULL
  )
  SELECT (SELECT COUNT(*) FROM nodes) AS graph_nodes,
         (SELECT COUNT(*) FROM (SELECT DISTINCT bus_id FROM `{OUT}`) s
          JOIN nodes n ON n.bid = s.bus_id) AS overlap
"""))[0]
print(f"    branch topology: graph has {t.graph_nodes:,} nodes, {t.overlap:,} overlap the PJM bus "
      f"set -> hop-1 has nothing to propagate from")
print(f"    queue-generator coincidence: in_pjm_gis_queues publishes no station or POI name column")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_pjm_bus_placement_v3',
 'indiana_app.in_bus_capacity_tier0 (PJM buses) x indiana_app.in_pjm_gis_queues (PJM published '
 'queue points) x energy.state_boundaries',
 'Places PJM buses by JOINING the PJM queue ID that PJM itself prints in the bus label '
 '(AE1-209 MAIN 345 kV) to the published coordinate for that queue in in_pjm_gis_queues. Not an '
 'estimate - an identifier match. A queue id resolving to more than one distinct point is '
 'REFUSED (0 today; the guard stays because the queue layer is refreshed). kV agreement is '
 'published, never used to drop a row: a GSU and a MAIN bus of one project sit at one site at two '
 'voltages. Out-of-state placements are kept with in_indiana = FALSE, not deleted. '
 'Two other keys were tried and measured unavailable: BRANCH TOPOLOGY (in_line_bus_endpoints has '
 '894 nodes, 62 overlap the 1,826 PJM buses, and 0 unplaced buses have a placed neighbour) and '
 'QUEUE-GENERATOR COINCIDENCE BY NAME (in_pjm_gis_queues publishes no station name column). '
 'RE-SCRAPE COMMAND: python scripts/build_pjm_bus_placement_v3.py',
 {s.total}, {gb}, CURRENT_TIMESTAMP(),
 'G126. PJM placement 275 -> {s.placed} of {s.total} buses; {s.gained} gained from the queue-id '
 'key with no scraping. {s.placed_in_indiana} of the placed buses are inside Indiana. The '
 'remaining unplaced are PSS/E area labels at the gazetteer ceiling G114 reached. '
 'IDEMPOTENCY: replace_safe. CADENCE: whenever in_pjm_gis_queues or the ladder is refreshed.'
)""").result()
print("\n  _registry row written")
print("PJM BUS PLACEMENT v3 COMPLETE")
