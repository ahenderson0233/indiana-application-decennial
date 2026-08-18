"""Rebuild in_bus_capacity_tier0: MISO from the licensed vendor DPP-2025, PJM from OUR case 23.

Operator, 2026-08-18: *"Now attack the buses, understanding that we are using the Orennia datasets
for MISO."* And, on PJM: *"we are looking to EXACTLY replicate the data that they hold ... the only
caveat is that we haven't yet scraped PJM for ALL of their scenarios ... we only scraped for 100MW
and 500MW."*

WHAT THIS REPLACES, AND WHY IT MATTERED
---------------------------------------
The old table was the single worst input in the application, and it fed the dossier's headline
number - the one figure a developer carries to a utility:

    PJM  Withdrawal  "2027 RTEP Base Case (Summer Peak)"  1,475 buses,  229 with a location
    MISO Injection   DPP-2021-Cycle                         603 buses

Both halves were wrong in a different way. The PJM half was a SUPERSEDED case while we hold the
current one. The MISO half was INJECTION ONLY - the generator question - so a data centre asking
"how much load can I connect" got either silence or the wrong direction, across the two thirds of
Indiana that sits in MISO.

    PJM  both directions  2028 TC2 Phase II (case 23)     1,826 buses  <- ours, freshly harvested
    MISO both directions  DPP-2025 ERIS-mitigated Final   1,731 buses  <- licensed vendor proxy

⭐ THE MISO HALF IS THE BIG WIN AND IT IS NOT OURS. `in_bus_headroom_miso_vendor` carries the
WITHDRAWAL direction, which MISO publishes nowhere - four independent sweeps found no public route,
and the case itself is CEII. Every MISO row here is stamped `provenance_class` and is removable in
one statement when the licence lapses (late 2027). It is a yardstick we are licensed to stand on,
not a source we derived.

⛔ THE PJM HALF CANNOT YET REPLICATE THEIRS, AND THIS SCRIPT DOES NOT PRETEND OTHERWISE.
Measured against their export, bus by bus, on the 283 buses we share:

    same powerflow case      Final_2024 Series RTEP 2028 SUM_BD_05282026_TC2_PHII_SENS_Topo  ✓
    same shift-factor cutoff 0.05                                                            ✓
    exact agreement          0 of 283                                                        ✗
    within 20%              12 of 283 (4.2%)                                                 ✗
    Spearman rank corr      +0.15 withdrawal, +0.25 injection                                ✗
    median ours/theirs       0.111 withdrawal, 0.174 injection

The cause is the one the operator already named. **We hold a single 100 MW probe.** Their "Bus
Interconnection Capacity" is the MW at which the first non-overloaded constraint binds, solved
continuously and capped at 5,000 (24 PJM and 67 MISO rows sit exactly on 5,000, which is a ceiling
artefact, not a bus property). `available_mw` at a fixed 100 MW request is a different quantity,
and the weak rank correlation says it is not merely the same quantity at a different scale - at
100 MW a different facility binds than at the maximum.

So the PJM rows here are labelled for what they are: **headroom at a 100 MW request**, not a bus
maximum. `probe_mw` is a column so no surface can forget it.

WHAT THE COMPARISON DID SETTLE, and it corrects our own method note
-------------------------------------------------------------------
Their binding constraint is the tightest facility that is NOT already overloaded. Bus 243209 is the
worked example: our four tightest constraints there sit at 118-153% loading BEFORE any request, so
`available_mw` is 0; their primary limiting constraint is a different facility at 89.68% with
`Existing Overload Flag = false`. They still REPORT a zero when the bus itself is overloaded - 147
of their 152 flagged rows are exactly 0 - so they do not drop the bus, they drop the overloaded
FACILITY when choosing what binds. That is the rule applied below, and it moved our withdrawal
median from 0.0 to 42.0 MW.

RE-SCRAPE COMMAND: python scripts/build_bus_capacity_tier0_v2.py
"""
import sys

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
TARGET = "in_bus_capacity_tier0"
PROBE_MW = 100.0
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{DS}.{TARGET}` AS

-- ================================================================= PJM: OURS, case 23
-- One row per (bus, direction). The binding constraint is the tightest facility that the request
-- actually stresses (|dfax| >= 0.05, the vendor's own cutoff) and that is NOT already over its
-- rating. Pre-existing overloads are still COUNTED and flagged on the row - dropping them from the
-- count would hide why a bus is tight - they are only excluded from the choice of what binds.
WITH pjm_raw AS (
  SELECT 'Withdrawal' AS direction, * FROM `{DS}.in_pjm_qs_c23sens_wd`
  UNION ALL
  SELECT 'Injection'  AS direction, * FROM `{DS}.in_pjm_qs_c23sens_inj`
),
pjm_scoped AS (
  SELECT *, (pre_loading_pct >= 100) AS facility_overloaded
  FROM pjm_raw
  WHERE ABS(dfax) >= 0.05
),
pjm_rank AS (
  SELECT *, ROW_NUMBER() OVER (
      PARTITION BY bus_number, direction
      ORDER BY facility_overloaded ASC, available_mw ASC, ABS(dfax) DESC) AS rk
  FROM pjm_scoped
),
pjm_agg AS (
  SELECT bus_number, direction,
         COUNT(*)                                        AS n_scoped,
         COUNTIF(facility_overloaded)                    AS n_overloaded,
         MIN(IF(facility_overloaded, NULL, available_mw)) AS mw_clean,
         MIN(available_mw)                               AS mw_all
  FROM pjm_scoped GROUP BY 1, 2
),
pjm AS (
  SELECT
    b.bus_number                                   AS bus_id,
    b.bus_label                                    AS bus_name,
    SAFE_CAST(b.bus_kv AS FLOAT64)                 AS bus_voltage_kv,
    'PJM'                                          AS iso,
    b.direction                                    AS interconnection_type,
    0                                              AS upgrade_tier,
    -- a bus whose every scoped facility is already overloaded reports 0, exactly as theirs does
    IFNULL(a.mw_clean, 0.0)                        AS bus_interconnection_capacity_mw,
    b.transmission_facility                        AS primary_limiting_constraint,
    CAST(NULL AS STRING)                           AS primary_limiting_constraint_branch_id,
    b.contingency_type                             AS contingency_name,
    CAST(NULL AS STRING)                           AS contingency_id,
    b.dfax * 100                                   AS shift_factor_pct,
    CAST(NULL AS FLOAT64)                          AS constraint_base_flow_mw,
    CAST(NULL AS FLOAT64)                          AS constraint_contingency_flow_mw,
    b.pre_loading_pct                              AS constraint_loading_before_pct,
    b.post_loading_pct                             AS constraint_loading_after_pct,
    CAST(NULL AS FLOAT64)                          AS constraint_rate_base_mva,
    CAST(NULL AS FLOAT64)                          AS constraint_rate_contingency_mva,
    CAST(NULL AS FLOAT64)                          AS constraint_headroom_mw,
    CAST(NULL AS STRING)                           AS constraint_voltage,
    CAST(NULL AS STRING)                           AS constraint_area,
    (a.n_overloaded > 0)                           AS existing_overload_flag,
    a.n_overloaded                                 AS n_facilities_overloaded_base,
    a.n_scoped                                     AS n_monitored_facilities,
    CAST(NULL AS STRING)                           AS publisher_headroom_state,
    b.owner_label                                  AS bus_area,
    l.lat                                          AS latitude,
    l.lon                                          AS longitude,
    b.case_label                                   AS powerflow_case,
    'PJM QueueScope case 23 (ours)'                AS study_source,
    FALSE                                          AS is_ferc_order_2023,
    'own_harvest'                                  AS provenance_class,
    {PROBE_MW}                                     AS probe_mw
  FROM pjm_rank b
  JOIN pjm_agg a USING (bus_number, direction)
  LEFT JOIN `{DS}.in_pjm_bus_locations_candidate` l
         ON CAST(l.bus_number AS STRING) = b.bus_number
  WHERE b.rk = 1
),

-- ================================================================= MISO: LICENSED VENDOR PROXY
-- Operator-authorised. Both directions, DPP-2025, every bus located. Stamped so it stays visible
-- and removable: this is the ONE place vendor numbers are a source rather than a yardstick.
miso AS (
  SELECT
    v.bus_id                                       AS bus_id,
    v.bus_name                                     AS bus_name,
    v.bus_kv                                       AS bus_voltage_kv,
    'MISO'                                         AS iso,
    v.operating_mode                               AS interconnection_type,
    IFNULL(v.upgrade_tier, 0)                      AS upgrade_tier,
    -- a bus whose every constraint is already overloaded reports 0, exactly as PJM does above
    IF(v.existing_overload_flag, 0.0, v.capacity_mw) AS bus_interconnection_capacity_mw,
    v.primary_limiting_constraint                  AS primary_limiting_constraint,
    CAST(NULL AS STRING)                           AS primary_limiting_constraint_branch_id,
    v.contingency_name                             AS contingency_name,
    CAST(NULL AS STRING)                           AS contingency_id,
    v.shift_factor * 100                           AS shift_factor_pct,
    CAST(NULL AS FLOAT64)                          AS constraint_base_flow_mw,
    CAST(NULL AS FLOAT64)                          AS constraint_contingency_flow_mw,
    CAST(NULL AS FLOAT64)                          AS constraint_loading_before_pct,
    CAST(NULL AS FLOAT64)                          AS constraint_loading_after_pct,
    CAST(NULL AS FLOAT64)                          AS constraint_rate_base_mva,
    CAST(NULL AS FLOAT64)                          AS constraint_rate_contingency_mva,
    v.local_transfer_capacity_mw                   AS constraint_headroom_mw,
    CAST(NULL AS STRING)                           AS constraint_voltage,
    CAST(NULL AS STRING)                           AS constraint_area,
    v.existing_overload_flag                       AS existing_overload_flag,
    CAST(NULL AS INT64)                            AS n_facilities_overloaded_base,
    CAST(NULL AS INT64)                            AS n_monitored_facilities,
    CAST(NULL AS STRING)                           AS publisher_headroom_state,
    v.county                                       AS bus_area,
    v.lat                                          AS latitude,
    v.lon                                          AS longitude,
    v.powerflow_case                               AS powerflow_case,
    'Orennia licensed proxy (MISO only)'           AS study_source,
    FALSE                                          AS is_ferc_order_2023,
    v.provenance_class                             AS provenance_class,
    CAST(NULL AS FLOAT64)                          AS probe_mw
  FROM `{DS}.in_bus_headroom_miso_vendor` v
  -- The vendor ships one row per (bus, direction, CONSTRAINT) and the capacity differs between
  -- them - measured, it varies within 2,688 of 3,462 bus/direction groups - so the bus figure is
  -- a MIN over constraints. ⭐ And the binding pick uses the SAME rule as PJM above: the tightest
  -- facility that is not ALREADY over its rating. 44% of their MISO rows carry the overload flag,
  -- so taking a naive MIN returned 0 for most buses; excluding overloaded facilities from the
  -- CHOICE (never from the count) moves the withdrawal median from 0.0 to 42.2 MW and the
  -- non-zero bus count from 418 to 1,079 of 1,731.
  -- One rule across both ISOs matters here: this table is read as a single list, and a reader
  -- comparing a MISO bus to a PJM bus must be comparing the same quantity.
  QUALIFY ROW_NUMBER() OVER (PARTITION BY v.bus_id, v.operating_mode
                             ORDER BY v.existing_overload_flag ASC, v.capacity_mw ASC) = 1
)

SELECT *,
       1 AS upgrade_tiers_available,
       'TIER 0 ONLY. PJM rows are headroom at a 100 MW PROBE, not a bus maximum - we hold no other '
       'scenario yet. MISO rows are the licensed Orennia DPP-2025 proxy, both directions, and are '
       'removable in one statement when the licence lapses.'    AS upgrade_tier_note,
       'ISO Base Case'                                          AS interconnection_scenario,
       CURRENT_TIMESTAMP()                                      AS built_at
FROM (SELECT * FROM pjm UNION ALL SELECT * FROM miso)
"""

print("building...", flush=True)
client.query(SQL).result()

m = list(client.query(f"""
  SELECT iso, interconnection_type AS dir, COUNT(*) n, COUNT(DISTINCT bus_id) buses,
         COUNTIF(latitude IS NOT NULL) located,
         COUNTIF(bus_interconnection_capacity_mw > 0) nonzero,
         ROUND(APPROX_QUANTILES(bus_interconnection_capacity_mw, 2)[OFFSET(1)], 1) med,
         COUNT(DISTINCT powerflow_case) cases
  FROM `{DS}.{TARGET}` GROUP BY 1, 2 ORDER BY 1, 2"""))
print()
for r in m:
    print(f"  {r.iso:5s} {r.dir:11s} rows={r.n:>6,} buses={r.buses:>5,} located={r.located:>6,} "
          f"({100*r.located/max(1,r.n):5.1f}%) nonzero={r.nonzero:>5,} median={r.med}")
tot = list(client.query(f"SELECT COUNT(*) n, COUNT(DISTINCT bus_id) b FROM `{DS}.{TARGET}`"))[0]
print(f"\n  TOTAL {tot.n:,} rows / {tot.b:,} distinct buses  (was 2,117 rows / one direction each)")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{TARGET}'").result()
client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at, notes)
VALUES ('{TARGET}',
 'PJM: indiana_app.in_pjm_qs_c23sens_wd/_inj (our QueueScope harvest, case 23, owner 1568, 100 MW). '
 'MISO: indiana_app.in_bus_headroom_miso_vendor (Orennia licensed proxy, DPP-2025, operator-authorised).',
 'One row per (bus, direction). Binding constraint = tightest facility with |dfax| >= 0.05 that is '
 'NOT already over its rating; pre-existing overloads are counted and flagged but excluded from the '
 'choice of what binds, which is the vendor method verified against their export on bus 243209. '
 'PJM capacity is headroom at a 100 MW PROBE and is NOT a bus maximum - measured against the vendor '
 'on 283 shared buses: 0 exact, 12 within 20%, Spearman +0.15/+0.25. MISO rows carry provenance_class '
 'and are removable when the licence lapses (late 2027). '
 'RE-SCRAPE COMMAND: python scripts/build_bus_capacity_tier0_v2.py',
 {tot.n}, CURRENT_TIMESTAMP(),
 'Replaces the 2027-RTEP/DPP-2021 build: PJM moves to the current case and gains the injection '
 'direction; MISO gains the WITHDRAWAL direction, which MISO publishes nowhere.')
""").result()
print("  registry row written")
