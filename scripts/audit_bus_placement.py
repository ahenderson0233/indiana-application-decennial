"""G148: IS EVERY BUS WE PUBLISH A HEADROOM FOR ACTUALLY SOMEWHERE?

Operator, 2026-08-21: *"it is crucial that we don't have floating buses, since they should be
essentially at/closely proximate to a substation… If you reference the Orennia numbers, they place
all of their buses alongside transmission and substations in immediate proximity."* And: *"our
estimated bus points should land on a substation, which I believe is exactly what Orennia does —
please factcheck me on that."*

================================================================================================
⭐ THE FACT-CHECK: RIGHT ABOUT THE INTENT, NOT ABOUT THE EXECUTION
================================================================================================
Measured across BOTH substation corpora we hold (HIFLD `in_substations` 3,858 + OSM
`in_osm_power_substations` 2,873), for all 1,731 located MISO/Orennia buses:
    median distance 0.0 m · 1,301 (75.2%) within 50 m · p90 = 2,081 m · 175 (10.1%) beyond 2 km
So Orennia plainly DOES aim buses at substations and the median lands exactly on one — but one in
ten does not, and *"all of their buses"* is not literally true of the vendor data we hold.

⛔ THE OBVIOUS ESCAPE WAS CHECKED AND DOES NOT HOLD: our substation corpus is Indiana-clipped, but
1,730 of the 1,731 MISO buses are inside Indiana, so a cross-border artefact accounts for at most
one of the 175.

⛔ AND THE CENTROID-FALLBACK HYPOTHESIS IS DEAD. If a vendor could not place a bus and fell back to
a city or county centroid, the floating set would cluster on a few repeated coordinates. Measured:
**156 distinct points across 175 buses, largest cluster 3.** These are individually placed points,
not a fallback.

⚠ THE OPERATOR'S OWN HYPOTHESIS — *"may be simply due to the distribution systems throughout
Indiana, and we may only hold transmission-level substation data"* — IS PLAUSIBLE AND UNTESTABLE
WITH WHAT WE HOLD, and that is recorded rather than resolved:
  · `in_substations`: 138 of 3,858 are under 69 kV; only 31 are typed `distribution`.
  · `energy.mat_grid_substations` (122,527 national) returns the SAME 3,858 for Indiana, with
    **zero** under 69 kV — it is the same transmission corpus, not a wider one.
  · `in_osm_power_substations` is a complete clip (2,873 = 2,873) with 123 under 69 kV.
  · ⛔ The AEP hosting-capacity tables DO carry distribution detail — `substation`, `circuitid`,
    `feeder_rating`, `station_max_hcload` — but `hca_aep_im_mi_load` and `hca_aep_hc_grid_load_all`
    hold **Ohio (105,763) and Michigan (12,972) rows and ZERO Indiana**. The "IM" is the operating
    company, Indiana Michigan Power, not the state it covers here. *A table named for a utility is
    not a clip of that utility's home state* — the same lesson as `in_ustp_ch7_tfr`.
  So: we cannot confirm or refute the distribution explanation. It stays open, honestly.

================================================================================================
⛔ WHAT THIS AUDIT FAILS ON, AND WHY IT IS NOT THE FLOATING COUNT
================================================================================================
A floating bus is only a DEFECT if it changes a number a reader sees. Measured by `bus_id`:
**not one of the 296 floating buses reaches a transmission-line endpoint**, because the endpoint
matcher requires 100 m proximity or a substation bridge and a bus far from both can satisfy
neither. The placement discipline of the matcher is already protecting every published figure.

So the invariant this audit enforces is the one that would actually mislead:
    ⛔ NO BUS MAY BIND A PUBLISHED DELIVERABLE FIGURE UNLESS WE CAN PLACE IT.
A raw floating COUNT is reported as context and cannot fail the build — it is a coverage ceiling
(G114/G126) that no amount of care here will move.

⚠ AND PJM BUSES OUTSIDE INDIANA ARE EXCLUDED FROM THE VERDICT, NOT COUNTED AS FAILURES. 185 of the
275 located PJM buses sit outside the state (up to 800 km); our substation corpus stops at the
border, so they have nothing to anchor to for a reason about OUR corpus. Counting them would mean
176 permanent false failures. ⭐ Inside Indiana our own placement is EXCELLENT: 89 of 90 PJM buses
are within 250 m of a substation. We have not placed worse than the vendor — we have placed fewer.

⚠ ONE INSTRUMENT NOTE, PAID FOR HERE: `wd_limiting_end` stores a bus NAME, and **93 bus names are
shared by more than one bus**. A first version of this check joined on the name and reported one
floating bus binding a figure; joining on `bus_id` returns zero. Never key a bus by its name.

⛔ READ-ONLY. Writes nothing.

RE-SCRAPE COMMAND: python scripts/audit_bus_placement.py
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
SUB_M = 2000     # anchored: within 2 km of a substation in EITHER corpus
LINE_M = 500     # defensible: not at a station, but on a line - a tap or a line-side node
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
WITH ind AS (SELECT geom AS g FROM `{EN}.state_boundaries`
             WHERE UPPER(IFNULL(STUSPS,'')) = 'IN'),
osm AS (SELECT ST_GEOGPOINT(longitude, latitude) AS g
        FROM `{DS}.in_osm_power_substations`
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL),
b AS (
  SELECT bus_id, ANY_VALUE(bus_name) AS bus_name, ANY_VALUE(iso) AS iso,
         ANY_VALUE(provenance_class) AS provenance,
         ST_GEOGPOINT(ANY_VALUE(longitude), ANY_VALUE(latitude)) AS g
  FROM `{DS}.in_bus_capacity_tier0`
  WHERE latitude IS NOT NULL AND longitude IS NOT NULL
  GROUP BY bus_id
),
d AS (
  SELECT b.*,
    (SELECT LOGICAL_OR(ST_INTERSECTS(b.g, i.g)) FROM ind i) AS in_indiana,
    LEAST(
      IFNULL((SELECT MIN(ST_DISTANCE(b.g, s.geog)) FROM `{DS}.in_substations` s
                WHERE ST_DWITHIN(b.g, s.geog, 50000)), 1e9),
      IFNULL((SELECT MIN(ST_DISTANCE(b.g, o.g)) FROM osm o
                WHERE ST_DWITHIN(b.g, o.g, 50000)), 1e9)) AS sub_m,
    IFNULL((SELECT MIN(ST_DISTANCE(b.g, l.geom)) FROM `{DS}.in_transmission_lines` l
              WHERE ST_DWITHIN(b.g, l.geom, 50000)), 1e9) AS line_m
  FROM b
),
cls AS (
  SELECT *, CASE WHEN sub_m  <= {SUB_M}  THEN 'anchored_to_a_substation'
                 WHEN line_m <= {LINE_M} THEN 'on_a_line_no_substation'
                 ELSE 'floating_far_from_both' END AS placement_class
  FROM d
),
-- ⚠ BY bus_id, NEVER by bus_name: 93 names are shared by more than one bus.
reached AS (
  SELECT a_bus_id AS bus_id FROM `{DS}.in_line_bus_endpoints` WHERE a_bus_id IS NOT NULL
  UNION DISTINCT
  SELECT b_bus_id            FROM `{DS}.in_line_bus_endpoints` WHERE b_bus_id IS NOT NULL
)
SELECT c.iso, c.provenance, c.placement_class,
       COUNT(*) AS buses,
       COUNTIF(c.in_indiana) AS inside_indiana,
       COUNTIF(c.bus_id IN (SELECT bus_id FROM reached)) AS reaches_a_line_end
FROM cls c
GROUP BY 1, 2, 3
ORDER BY 1, buses DESC
"""

print("=" * 100)
print("G148 - IS EVERY BUS WE PUBLISH A HEADROOM FOR ACTUALLY SOMEWHERE?")
print("=" * 100)
rows = list(client.query(SQL).result())

print(f"\n{'ISO':6} {'provenance':24} {'placement':28} {'buses':>7} {'in IN':>7} {'reaches a line':>15}")
print("-" * 100)
violations = 0
for r in rows:
    print(f"{r.iso:6} {r.provenance:24} {r.placement_class:28} "
          f"{r.buses:>7,} {r.inside_indiana:>7,} {r.reaches_a_line_end:>15,}")
    # ⛔ THE ONLY FAILING CONDITION: a bus we cannot place that nonetheless feeds a figure.
    if r.placement_class == "floating_far_from_both" and r.reaches_a_line_end > 0:
        violations += r.reaches_a_line_end

tot = sum(r.buses for r in rows)
floating = sum(r.buses for r in rows if r.placement_class == "floating_far_from_both")
anchored = sum(r.buses for r in rows if r.placement_class == "anchored_to_a_substation")
onlin = sum(r.buses for r in rows if r.placement_class == "on_a_line_no_substation")
float_in = sum(r.inside_indiana for r in rows if r.placement_class == "floating_far_from_both")

print("\n" + "=" * 100)
print(f"  {tot:,} located buses · {anchored:,} anchored to a substation "
      f"· {onlin:,} on a line but not at a station · {floating:,} floating")
print(f"  ⚠ of the floating, {float_in:,} are inside Indiana; the rest are outside the state and "
      f"our\n    substation corpus stops at the border, so they have nothing to anchor to.")
print(f"  ⭐ COVERAGE IS A CEILING (G114/G126), NOT A DEFECT. What matters is whether an unplaceable")
print(f"     bus reaches a reader, and the endpoint matcher already refuses one.")

print("\n" + "=" * 100)
if violations:
    print(f"⛔ {violations} FLOATING BUS(ES) REACH A TRANSMISSION-LINE ENDPOINT.")
    print("   A bus we cannot place is feeding a published deliverable figure. Either the bus has a")
    print("   real position we are missing, or the endpoint match is wrong. Do not ship this.")
    sys.exit(1)
print("0 unplaceable bus(es) reach a published figure — every deliverable number is bound by a bus")
print("we can put on a map.")
print("=" * 100)
