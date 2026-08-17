"""G7d/G20/G22 — reproduce the benchmark's BUS CAPACITY schema from OUR OWN FERC Order 2023 data.
Writes `in_bus_capacity_ferc2023`.

⛔ OPERATOR RULING, BINDING AND RESTATED 2026-08-17: *"we do NOT want to copy them, but would like
to use them as a reference point to derive the same numbers as they have."* So this script reads
**nothing** from the vendor extract. It replicates their **column set, grain and derivation** and
computes every value from MISO's and PJM's own published FERC Order 2023 data. Their file is the
yardstick that told us WHAT to compute; `scripts/benchmark_vs_orennia.py` is where the comparison
lives, and it writes a markdown report only.

⛔ AND CARTOVISTA IS NOT THE ROUTE. The backlog promoted G7d on the strength of a registry row
reading `access: public` for the MISO FERC heatmap. That is the CATALOGUE row. The PROBE rows beside
it record the measurement, and **I re-tested it 2026-08-17 rather than inherit either verdict**:

    ferc.cartovista.com/api/settings/miso/ferc          200
    cloud.cartovista.com/.../mvt/8/12/5.pbf             200   <- locations only, x/y, no attributes
    cloud.cartovista.com/.../Layer/{id}/geojson         403   <- the wall reproduces

The 691,523-row transfer study is unreachable by every known route (geojson, DataRows,
dataQueryExecute, joined aggregate all 403). **19,223 buses via CartoVista is not available.**
What IS available, and what this script uses, is MISO's own legacy giqueue viewer — from which the
registry records POI attributes and headroom were obtained COMPLETE.

THE GRAIN WE ARE REPRODUCING, measured from their Indiana slice (19,846 rows, 2,023 buses):

    (bus) x (interconnection type: Injection | Withdrawal) x (upgrade tier: 0,1,2,3,4)

⚠ WE CAN ONLY PRODUCE TIER 0, and that must be stated on the face of the output rather than implied.
An upgrade tier asks "what could this bus take if we PAID for N network upgrades" — that requires the
per-upgrade cost/rating study, which is their second file (331,383 rows) and which no public MISO
route we hold publishes. **Tier 0 is not a weaker version of tiers 1-4; it is a different question**,
and it is where their median capacity is 0 MW too. `upgrade_tier` is therefore a real column pinned
to 0, and `upgrade_tiers_available` says 1 so nobody reads a tier-0 number as a bus's ceiling.

⭐ WHAT PROFILING THEIR FILE SETTLED, and it changes our method:
**`Existing Overload Flag` is TRUE on 8,232 of their 19,846 rows (41.5%) — they do NOT drop
pre-existing overloads, they FLAG them and still report a capacity.** G26 framed our choice as
"exclude overloads (100% of POIs get headroom) or keep them (0.2%)". Their answer is neither:
carry the flag, report the number, let the reader judge. That is what `existing_overload_flag` does
here — the same shape as our own "cannot assess renders as itself" rule.

⚠ VINTAGE IS OUR REMAINING HONEST GAP AND IT RIDES ON EVERY ROW. Theirs is
`DPP-2025-Cycle_SUM_D_ERIS-mitigated_Final` with MTEP-2025 upgrades as of Jan 2026. Ours is an
unmitigated DPP-2021 case. That is the mechanism behind their 39.3% of buses having tier-0 injection
headroom against our 0.2%, and it is NOT closed by this script. `powerflow_case` and
`transmission_modeling_assumptions` are columns precisely so the difference is never invisible.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
TARGET = "in_bus_capacity_tier0"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{DS}.{TARGET}` AS
WITH ind AS (          -- the 642 located Indiana MISO POIs
  SELECT DISTINCT poi_name FROM `{DS}.in_bus_headroom_miso` WHERE location_status = 'indiana'
),
-- The BINDING constraint per POI is the minimum over monitored facilities: headroom is a MIN over
-- binding constraints, never a median (G22-A). Rank so we can lift the primary limiting constraint
-- and all of its metadata onto the bus row, exactly as their file does.
f AS (
  SELECT p.*,
         ROW_NUMBER() OVER (PARTITION BY p.poi_name ORDER BY p.mw_available ASC, p.percent_dfax DESC) AS rk
  FROM `energy-platfrom.energy.miso_poi_monitored_facilities` p
  JOIN ind USING (poi_name)
),
binding AS (SELECT * FROM f WHERE rk = 1),
miso AS (
  SELECT
    CAST(h.bus_number AS STRING)                   AS bus_id,
    h.bus_name                                     AS bus_name,
    CAST(h.kv AS FLOAT64)                          AS bus_voltage_kv,
    'MISO'                                         AS iso,
    'Injection'                                    AS interconnection_type,   -- MISO poi_mf is generator-side
    0                                              AS upgrade_tier,
    h.headroom_mw                                  AS bus_interconnection_capacity_mw,
    b.monitored_facility                           AS primary_limiting_constraint,
    CONCAT(IFNULL(CAST(b.fr_bus AS STRING),'?'),'-',IFNULL(CAST(b.to_bus AS STRING),'?'),
           IFNULL(CONCAT('-',b.ckt),''))           AS primary_limiting_constraint_branch_id,
    b.cont_name                                    AS contingency_name,
    CAST(b.cont_id AS STRING)                      AS contingency_id,
    b.percent_dfax                                 AS shift_factor_pct,
    SAFE_CAST(b.base_flow_mw AS FLOAT64)           AS constraint_base_flow_mw,
    SAFE_CAST(b.cont_flow_mw AS FLOAT64)           AS constraint_contingency_flow_mw,
    b.percent_loading_before                       AS constraint_loading_before_pct,
    b.percent_loading_after                        AS constraint_loading_after_pct,
    CAST(b.rate_base_mva AS FLOAT64)               AS constraint_rate_base_mva,
    b.rate_cont_mva                                AS constraint_rate_contingency_mva,
    b.mw_available                                 AS constraint_headroom_mw,
    b.kvs                                          AS constraint_voltage,
    b.areas_name                                   AS constraint_area,
    -- ⭐ THEY FLAG IT RATHER THAN DROPPING IT. 41.5% of their rows carry this true.
    (b.percent_loading_before >= 100)              AS existing_overload_flag,
    h.n_facilities_overloaded_base                 AS n_facilities_overloaded_base,
    h.n_monitored_facilities                       AS n_monitored_facilities,
    h.headroom_state                               AS publisher_headroom_state,
    h.area_name                                    AS bus_area,
    h.latitude                                     AS latitude,
    h.longitude                                    AS longitude,
    h._vintage                                     AS powerflow_case,
    'MISO giqueue POI Analysis (legacy viewer)'    AS study_source,
    FALSE                                          AS is_ferc_order_2023
  FROM `energy-platfrom.energy.miso_poi_headroom` h
  JOIN ind USING (poi_name)
  LEFT JOIN binding b USING (poi_name)
),
-- PJM is the other direction and the other publisher. in_pjm_bus_withdrawal is our rollup of
-- QueueScope, which is load-side: exactly the direction a data centre needs and the one MISO's
-- generator tool cannot answer (G7, G7e: measured on 200 AEP buses, injection and withdrawal agree
-- on ZERO of them, so one must never stand in for the other).
-- ⚠ TYPE TRAP, and the schema check caught it: in_pjm_bus_withdrawal.bus_number is STRING while
-- in_pjm_bus_locations_candidate.bus_number is INTEGER, and bus_kv is STRING on one side and FLOAT
-- on the other. Both sides are CAST explicitly. Guessing either would have joined nothing.
pjm AS (
  SELECT
    CAST(w.bus_number AS STRING)                   AS bus_id,
    COALESCE(l.bus_label, w.bus_label)             AS bus_name,
    COALESCE(l.bus_kv, SAFE_CAST(w.bus_kv AS FLOAT64)) AS bus_voltage_kv,
    'PJM'                                          AS iso,
    'Withdrawal'                                   AS interconnection_type,
    0                                              AS upgrade_tier,
    w.withdrawal_mw                                AS bus_interconnection_capacity_mw,
    w.binding_facility                             AS primary_limiting_constraint,
    CAST(NULL AS STRING)                           AS primary_limiting_constraint_branch_id,
    CAST(NULL AS STRING)                           AS contingency_name,
    CAST(NULL AS STRING)                           AS contingency_id,
    CAST(NULL AS FLOAT64)                          AS shift_factor_pct,
    CAST(NULL AS FLOAT64)                          AS constraint_base_flow_mw,
    CAST(NULL AS FLOAT64)                          AS constraint_contingency_flow_mw,
    CAST(NULL AS FLOAT64)                          AS constraint_loading_before_pct,
    CAST(NULL AS FLOAT64)                          AS constraint_loading_after_pct,
    CAST(NULL AS FLOAT64)                          AS constraint_rate_base_mva,
    CAST(NULL AS FLOAT64)                          AS constraint_rate_contingency_mva,
    CAST(NULL AS FLOAT64)                          AS constraint_headroom_mw,
    CAST(NULL AS STRING)                           AS constraint_voltage,
    CAST(NULL AS STRING)                           AS constraint_area,
    -- PJM publishes the overload COUNT rather than a per-constraint loading percentage, so the
    -- flag is derived from it. Same finding as MISO, different column.
    (w.existing_overloads > 0)                     AS existing_overload_flag,
    w.existing_overloads                           AS n_facilities_overloaded_base,
    w.facilities                                   AS n_monitored_facilities,
    CAST(NULL AS STRING)                           AS publisher_headroom_state,
    CAST(NULL AS STRING)                           AS bus_area,
    l.lat                                          AS latitude,
    l.lon                                          AS longitude,
    COALESCE(w.case_label, 'PJM QueueScope withdrawal') AS powerflow_case,
    'PJM QueueScope'                               AS study_source,
    FALSE                                          AS is_ferc_order_2023
  FROM `{DS}.in_pjm_bus_withdrawal` w
  LEFT JOIN `{DS}.in_pjm_bus_locations_candidate` l
         ON CAST(l.bus_number AS STRING) = CAST(w.bus_number AS STRING)
)
SELECT *,
       -- Stated on the face of every row so a tier-0 number is never read as a bus ceiling.
       1     AS upgrade_tiers_available,
       'TIER 0 ONLY - upgrade tiers 1-4 require the per-upgrade cost/rating study, which no public '
       'route we hold publishes. Tier 0 asks a DIFFERENT question from tier 4, it is not a weaker '
       'version of it.'                                        AS upgrade_tier_note,
       'ISO Base Case'                                         AS interconnection_scenario,
       CURRENT_TIMESTAMP()                                     AS built_at
FROM (SELECT * FROM miso UNION ALL SELECT * FROM pjm)
"""

dry = client.query(SQL, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
gb = dry.total_bytes_processed / 1024 ** 3
print(f"DRY RUN: {gb:,.2f} GiB -> approx ${gb/1024*6.25:,.2f}")
job = client.query(SQL); job.result()

m = list(client.query(f"""
SELECT COUNT(*) n, COUNT(DISTINCT bus_id) buses,
       COUNTIF(iso='MISO') miso, COUNTIF(iso='PJM') pjm,
       COUNTIF(interconnection_type='Injection') inj, COUNTIF(interconnection_type='Withdrawal') wd,
       COUNTIF(bus_interconnection_capacity_mw > 0) gt0,
       COUNTIF(existing_overload_flag) ovl,
       COUNTIF(existing_overload_flag IS NOT NULL) ovl_known,
       COUNTIF(latitude IS NOT NULL) located,
       ROUND(APPROX_QUANTILES(bus_interconnection_capacity_mw, 2)[OFFSET(1)],1) med_mw
FROM `{DS}.{TARGET}`"""))[0]

print(f"{TARGET}: {m.n:,} rows over {m.buses:,} distinct buses")
print(f"  MISO {m.miso:,} (Injection) / PJM {m.pjm:,} (Withdrawal)")
print(f"  capacity > 0 MW               : {m.gt0:,} of {m.n:,}")
print(f"  median capacity               : {m.med_mw} MW")
print(f"  existing-overload flag TRUE   : {m.ovl:,} of {m.ovl_known:,} where known")
print(f"  located (lat/lon present)     : {m.located:,}")
print()
print("  BASELINE for comparison (their Indiana slice, NOT copied - yardstick only):")
print("    19,846 rows / 2,023 buses / 5 upgrade tiers / both directions / 41.5% overload-flagged")
print("    -> our gap is UPGRADE TIERS (we have tier 0 only) and VINTAGE (DPP-2021 vs DPP-2025).")

assert m.n > 0, "empty table"

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{TARGET}'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
    f"VALUES (@t,@s,@m,@n,@g,CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", TARGET),
        bigquery.ScalarQueryParameter("s", "STRING",
            "energy.miso_poi_headroom + energy.miso_poi_monitored_facilities (MISO giqueue FERC "
            "Order 2023) + indiana_app.in_pjm_bus_withdrawal (PJM QueueScope)"),
        bigquery.ScalarQueryParameter("m", "STRING",
            "Reproduces the vendor extract's COLUMN SET and GRAIN (bus x interconnection type x "
            "upgrade tier) from our own FERC Order 2023 sources. NO vendor data is read. Binding "
            "constraint = MIN(mw_available) per POI, so headroom is a minimum over binding "
            "constraints and never a median. Pre-existing overloads are FLAGGED, not dropped - the "
            "vendor flags 41.5% of their Indiana rows the same way. "
            "RE-SCRAPE COMMAND: python scripts/build_bus_capacity_ferc2023.py"),
        bigquery.ScalarQueryParameter("n", "INT64", int(m.n)),
        bigquery.ScalarQueryParameter("g", "FLOAT64", round(job.total_bytes_processed / 1024**3, 3)),
        bigquery.ScalarQueryParameter("no", "STRING",
            "TIER 0 ONLY (upgrade_tiers_available=1) - tiers 1-4 need the per-upgrade cost/rating "
            "study, unavailable on every public route we hold. VINTAGE GAP RIDES ON EVERY ROW: ours "
            "is an unmitigated DPP-2021 case, theirs DPP-2025-Cycle_SUM_D_ERIS-mitigated_Final with "
            "MTEP-2025 upgrades as of Jan 2026 - the mechanism behind their 39.3% vs our 0.2%. "
            "CartoVista is NOT a route: re-tested 2026-08-17, geojson 403 reproduces, MVT serves "
            "locations only with no attributes, so the 691,523-row transfer study stays unreachable.")])).result()
print(f"registered {TARGET} in indiana_app._registry")

tb = client.get_table("energy-platfrom.energy.registry_sources")
cols = {f.name for f in tb.schema}
row = {k: v for k, v in {
    "source_name": "Indiana bus interconnection capacity, FERC Order 2023 schema (derived)",
    "endpoint": "derived - no external endpoint",
    "endpoint_kind": "derived",
    "access": "internal-derived",
    "status": f"BUILT+LOADED ({m.n:,} rows, {m.buses:,} buses, tier 0 only)",
    "acquisition_method": "RE-SCRAPE COMMAND: python scripts/build_bus_capacity_ferc2023.py",
    "what_it_provides": "per-bus interconnection capacity in the FERC Order 2023 reporting schema - "
                        "capacity MW, primary limiting constraint, contingency, shift factor, "
                        "loading before/after, ratings, and an existing-overload FLAG rather than a "
                        "silent exclusion",
    "object_names": [TARGET],
    "geography_state": "IN",
    "measured_rows": int(m.n),
    "notes": "Replicates a commercial extract's schema and method from public data; reads none of "
             "it. Written by the indiana_app workstream 2026-08-17; APPEND-only.",
}.items() if k in cols}
errs = client.insert_rows_json("energy-platfrom.energy.registry_sources", [row])
print(f"appended to energy.registry_sources: {errs if errs else 'ok'}")
