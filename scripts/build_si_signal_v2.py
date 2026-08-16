"""SI signal v2 — the widened, NON-RESIDENTIAL, severity-gated, date-filterable seller-intent flag.

Why this exists. `in_sites.has_si_signal` was 847,410 parcels of which 840,819 (99.2%) were empty
land, because the only parcel-keyed block was `D5_vacancy` (945,896 rows, zero dates) — footprint
absence, which the operator ruled is NOT seller intent. So the flag was a vacancy flag, and 44,806
parcels carrying a real dated distress signal were invisible to the application.

WHAT ACTUALLY BLOCKED THE WIDENING was not the flag definition. The signal corpus and the parcel
layer live in THREE KEY NAMESPACES, and a naive join reads zero:

    in_sites.parcel_key            bare 18-digit state number   011222300004000006
    in_si_signals.parcel_key       'IN:'-PREFIXED               IN:640324226011000021
    Indy abandoned/vacant          7-digit MARION LOCAL id      5019155
    South Bend / Evansville        PUNCTUATED state number      71-03-34-406-009.000-026

A join reading 0 of 945,896 is a claim about the instrument. Stripping `IN:` reproduces
`in_sites.has_vacancy_signal` at EXACTLY 845,373 — which is how we know the bridge is right rather
than merely plausible. Marion has NO state key in any held table (`PARCELNUMBER` turned out to be
the same 7-digit local id, not a crosswalk), so Indy DEFERS TO ADDRESS: 125 of 7,120. That is the
honest ceiling and it is reported, not hidden.

SEVERITY — the first build of this script admitted 14,293 parcels and it was WRONG. Two blocks
were the D5 mistake in a new costume:
  · South Bend "code enforcement" is 95% Litter (9,382), Grass and Weeds (7,710) and Vegetation
    (2,293). A weed citation is not intent to sell. Only Sub-standard Housing and Secure Property
    are structural: 871 rows / 518 parcels, down from 10,370.
  · Evansville "demolition permits" is 3,771 BUILDING WRECKING RESIDENTIAL vs 419 COMMERCIAL —
    and a demolished house leaves a parcel classed `no_structure`, so it slips PAST the
    non-residential test on parcel class alone. Commercial wrecking only: 369 parcels, down
    from 3,385.
This is the same funnel A4 applied to NFIRS: 76,779 raw → 469 SI-grade.

DATES — "a code violation in the 1990s doesn't do anything for us." Every admitted row carries an
event date and a `date_basis` saying where it came from, and the roll-up carries 3/5/10-year event
counts so recency is filterable on screen. Two sources publish the event date in the LAYER NAME
rather than a column ("Tax Sale Property From July 2024", "Foreclosures - 2009"); that is used,
and marked month- or year-precision so an approximation never styles as a published date.

OPERATOR RULINGS ENCODED HERE (2026-08-15/16):
  · SI is admitted at the NON-RESIDENTIAL level only. A ~300 MW datacentre and a ~5 MW BESS both
    need land a house does not have. Residential rows are still BUILT and KEPT — they carry
    admit_status='excluded_residential' so nothing is left behind and the exclusion is auditable.
  · Footprint absence is NOT seller intent; it stays as has_vacancy_signal and the BESS basis.
  · Where no parcel key can be reached, DEFER TO ADDRESS rather than drop the row.

D85 GUARD: parcels_in/080500000047000018 is an inverted whole-Earth polygon (196,936,707 sq mi)
that silently matches everything. Excluded by key here, in every block.

Writes, and registers in the same run:
D22 is folded in here rather than shipped as its own layer, so the application has ONE seller-
intent flag instead of two rival partial ones (operator ruling on union-and-dedupe). It needs
`scripts/build_d22_wiring.py` to have run first — that script owns the ECHO clip and the spatial
join; this one only reads `in_si_d22_parcel_join`.

Writes, and registers in the same run:
  in_si_parcel_signals_v2   one row per (parcel, signal) — the evidence grain, with admit_status
  in_si_sites_flags_v2      one row per parcel — the flag the app reads
  in_si_signal_coverage     one row per signal — held, keyed how, dated how far back, reach
"""
# stdout must survive its own output: this console is cp1252 and characters like U+2248/U+2192/U+2717 raise
# UnicodeEncodeError from print() itself. The honesty audit once crashed on its own
# FAILURE path for exactly this reason. Degrade the glyph, never the run.
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import datetime
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
D85 = "080500000047000018"
client = bigquery.Client(project="energy-platfrom")
BUILT = datetime.datetime.now(datetime.timezone.utc).isoformat()


def q1(sql):
    return list(client.query(sql))[0]


def run(sql, label):
    job = client.query(sql)
    job.result()
    print(f"  {label}: {job.total_bytes_processed/1e9:.1f} GB", flush=True)


# The estate stores event dates four ways — epoch MILLISECONDS as a string (the Esri convention
# found in A3), epoch SECONDS (the Indy code corpus), ISO, and US m/d/Y. A string-only parse
# silently drops the majority of our rows, so one parser is used everywhere.
PARSE = """
CREATE TEMP FUNCTION pdate(s STRING) AS (
  CASE
    WHEN s IS NULL OR TRIM(s) IN ('','None','NA','N/A','null','-1','-2') THEN NULL
    WHEN REGEXP_CONTAINS(s, r'^[0-9]{13}$') THEN DATE(TIMESTAMP_MILLIS(CAST(s AS INT64)))
    WHEN REGEXP_CONTAINS(s, r'^[0-9]{10}$') THEN DATE(TIMESTAMP_SECONDS(CAST(s AS INT64)))
    WHEN REGEXP_CONTAINS(s, r'^[0-9]{4}-[0-9]{2}-[0-9]{2}') THEN SAFE.PARSE_DATE('%Y-%m-%d', SUBSTR(s,1,10))
    WHEN REGEXP_CONTAINS(s, r'^[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}$') THEN SAFE.PARSE_DATE('%m/%d/%Y', s)
    ELSE NULL END);
-- the publisher writes the event date into the LAYER NAME on two Evansville sources
CREATE TEMP FUNCTION layerdate(s STRING) AS (
  COALESCE(
    SAFE.PARSE_DATE('%b %Y', CONCAT(
      SUBSTR(REGEXP_EXTRACT(s, r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'), 1, 3),
      ' ', REGEXP_EXTRACT(s, r'(20[0-9]{2})'))),
    SAFE.PARSE_DATE('%Y', REGEXP_EXTRACT(s, r'(20[0-9]{2})'))));
CREATE TEMP FUNCTION layerbasis(s STRING) AS (
  IF(REGEXP_CONTAINS(s, r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'),
     'publisher layer name (month precision)', 'publisher layer name (year precision)'));
CREATE TEMP FUNCTION statekey(s STRING) AS (
  IF(LENGTH(REGEXP_REPLACE(IFNULL(s,''), r'[^0-9]', '')) = 18,
     REGEXP_REPLACE(s, r'[^0-9]', ''), NULL));
"""

# ---------------------------------------------------------------------------------------------
# 1. evidence: every parcel-reachable signal row, from every namespace, with its admit verdict
# ---------------------------------------------------------------------------------------------
print("building in_si_parcel_signals_v2 …", flush=True)

EVIDENCE = f"""{PARSE}
CREATE OR REPLACE TABLE `{DS}.in_si_parcel_signals_v2` AS
WITH
-- ---- A. already parcel-keyed in the corpus, once the 'IN:' prefix is stripped ---------------
a_corpus AS (
  SELECT REGEXP_REPLACE(parcel_key, r'^IN:', '') pk, signal, observed_date obs,
         'publisher event date' basis, 'corpus_parcel_key' keying,
         'IN: prefix stripped' bridge, source_id, 'si_signals corpus' blk, TRUE severe
  FROM `{DS}.in_si_signals`
  WHERE parcel_key IS NOT NULL AND keying IN ('parcel','parcel_key')
    AND signal != 'D5_vacancy'          -- footprint absence is not seller intent (operator)
),
-- ---- B. the address bridge built by the date-keying agent ------------------------------------
b_bridged AS (
  SELECT parcel_key pk, signal, max_past_observed_date obs,
         'publisher event date' basis, 'address_bridge' keying, match_method bridge,
         'in_si_signals_parcel_dated' source_id, 'si_signals corpus' blk, TRUE severe
  FROM `{DS}.in_si_signals_parcel_dated`
),
-- ---- C. South Bend — the publisher's own state number, punctuated ----------------------------
c_sb_vacant AS (
  SELECT statekey(State_ID_LU) pk, 'D5_abandoned_building' signal,
         pdate(Added_to_V_A_on_) obs, 'publisher event date' basis, 'publisher_state_id' keying,
         'State_ID_LU punctuation stripped' bridge, 'southbend_vacant_abandoned' source_id,
         'publisher table (new in v2)' blk, TRUE severe
  FROM `{DS}.in_si_southbend_vacant_abandoned` WHERE statekey(State_ID_LU) IS NOT NULL
),
c_sb_code AS (   -- SEVERITY GATE: 95% of this table is litter, weeds and vegetation
  SELECT statekey(State_ID__) pk, 'D12_code_violation' signal,
         pdate(Record_Open_Date) obs, 'publisher event date' basis, 'publisher_state_id' keying,
         'State_ID__ punctuation stripped' bridge,
         CONCAT('southbend_code_enforcement:', IFNULL(Record_Type,'?')) source_id,
         'publisher table (new in v2)' blk,
         Record_Type IN ('Sub-standard Housing','Secure Property') severe
  FROM `{DS}.in_si_southbend_code_enforcement` WHERE statekey(State_ID__) IS NOT NULL
),
c_sb_cont AS (
  SELECT statekey(STATE_ID) pk, 'D21_demolition_order' signal,
         pdate(HEARING__OR_LETTER_DATE) obs, 'publisher event date' basis,
         'publisher_state_id' keying, 'STATE_ID punctuation stripped' bridge,
         'southbend_continuous_enforcement' source_id, 'publisher table (new in v2)' blk, TRUE
  FROM `{DS}.in_si_southbend_continuous_enforcement` WHERE statekey(STATE_ID) IS NOT NULL
),
-- ---- D. Evansville — StatePIN is the state number; the DATE is in the layer name -------------
d_ev_tax AS (
  SELECT statekey(StatePIN) pk, 'D1_tax_sale' signal, layerdate(src_layer_name) obs,
         layerbasis(src_layer_name) basis, 'publisher_state_id' keying,
         'StatePIN punctuation stripped' bridge,
         CONCAT('evansville_taxsale:', IFNULL(src_layer_name,'?')) source_id,
         'publisher table (new in v2)' blk, TRUE
  FROM `{DS}.in_si_evansville_taxsale` WHERE statekey(StatePIN) IS NOT NULL
),
d_ev_fore AS (   -- SaleDate is the sheriff's-sale date and agrees with the layer year; use it
  SELECT statekey(StatePIN) pk, 'D2_foreclosure' signal,
         COALESCE(pdate(SaleDate), layerdate(src_layer_name)) obs,
         IF(pdate(SaleDate) IS NOT NULL, 'publisher event date', layerbasis(src_layer_name)) basis,
         'publisher_state_id' keying, 'StatePIN punctuation stripped' bridge,
         CONCAT('evansville_foreclosures:', IFNULL(src_layer_name,'?')) source_id,
         'publisher table (new in v2)' blk, TRUE
  FROM `{DS}.in_si_evansville_foreclosures` WHERE statekey(StatePIN) IS NOT NULL
),
d_ev_demo AS (   -- SEVERITY GATE: 3,771 residential teardowns vs 419 commercial wreckings
  SELECT statekey(USER_Parcel_ID) pk, 'D21_demolition_order' signal,
         pdate(USER_Application_Recv_d) obs, 'publisher event date' basis,
         'publisher_state_id' keying, 'USER_Parcel_ID punctuation stripped' bridge,
         CONCAT('evansville_demolition:', IFNULL(USER_Project_Activity,'?')) source_id,
         'publisher table (new in v2)' blk,
         USER_Project_Activity LIKE '%COMMERCIAL%' severe
  FROM `{DS}.in_si_evansville_demolition_permits` WHERE statekey(USER_Parcel_ID) IS NOT NULL
),
-- ---- E. Indy: NO state key exists in any held table, so DEFER TO ADDRESS ----------------------
-- THE MARION CROSSWALK, which turns 1.8% into 100%. The earlier conclusion "Marion has no state
-- key in any held table" was right about the tables we HELD and wrong about the world: Marion's
-- own parcel service publishes both keys side by side.
--   gis.indy.gov/.../sde_Parcel/sde_Parcel/MapServer/5  'Parcel State Pin'
--   347,049 parcels · PARCEL_I (7-digit local) + STATEPARCELNUMBER (49-06-25-178-053.000-101)
-- Pulled by scrapers/lane_f/pull_marion_crosswalk.py. 98.2% of its state pins exist in in_sites,
-- and it places 7,132 of 7,132 abandoned rows against 125 via the address bridge.
e_indy_abandoned AS (
  SELECT x.st pk, 'D5_abandoned_building' signal, CAST(NULL AS DATE) obs,
         'publisher carries no event date' basis, 'marion_parcel_crosswalk' keying,
         'PARCEL_I -> STATEPARCELNUMBER (Marion sde_Parcel layer 5)' bridge,
         'indy_abandoned_vacant' source_id, 'publisher table (new in v2)' blk, TRUE
  FROM `{DS}.in_si_indy_abandoned_vacant` a
  JOIN (SELECT DISTINCT PARCEL_I loc, REGEXP_REPLACE(STATEPARCELNUMBER, r'[^0-9]','') st
        FROM `{DS}.in_marion_parcel_crosswalk`
        WHERE PARCEL_I IS NOT NULL AND STATEPARCELNUMBER IS NOT NULL) x
    ON x.loc = a.PARCEL_I
),
-- ---- F. the derive-from-held win: Unsafe Buildings + Vacant Board Order, WITH open dates ------
-- Placed through INDY'S OWN ADDRESS AUTHORITY (sde_Addressing layer 0, 465,050 addresses each
-- carrying FULL_ADDRESS *and* STATEPARCELNUMBER) rather than the generic address bridge. Same
-- publisher as the code corpus, so the address text agrees without an invented normaliser, and
-- the result is a PUBLISHED crosswalk rather than a geocode estimate.
-- 46,411 of 54,995 rows (84.4%) on 14,378 parcels — the generic bridge reached 711.
-- Built by scripts/build_indy_address_placement.py.
f_indy_unsafe AS (
  SELECT parcel_key pk, signal, event_date obs,
         'publisher event date' basis, 'indy_address_authority' keying,
         'STREET_ADDRESS -> sde_Addressing FULL_ADDRESS -> STATEPARCELNUMBER' bridge,
         CONCAT('indy_code_enforcement:', signal) source_id,
         'publisher table (new in v2)' blk, TRUE
  FROM `{DS}.in_si_indy_code_placed`
),
-- ---- G. D22 environmental (EPA ECHO bulk export), already spatially joined to parcels --------
-- Two DIFFERENT signals, deliberately kept apart: a facility in violation is owner distress; a
-- facility that has CEASED OPERATING is a site opportunity with power and water already run to
-- it. Being merely present in ECHO is neither, so 50,334 no-marker facilities are not admitted.
g_d22_violation AS (
  SELECT parcel_key pk, 'D22_environmental_violation' signal,
         COALESCE(last_formal_action, last_penalty_date) obs,
         IF(COALESCE(last_formal_action, last_penalty_date) IS NOT NULL,
            'publisher event date', 'publisher carries no action date') basis,
         'spatial_facility_point' keying,
         'ST_CONTAINS(parcel_geog, ECHO facility point) [D85 excluded]' bridge,
         CONCAT('echo:', distress_class) source_id, 'publisher table (new in v2)' blk, TRUE severe
  FROM `{DS}.in_si_d22_parcel_join` WHERE is_distress
),
g_d22_inactive AS (
  SELECT parcel_key pk, 'D22_facility_inactive' signal,
         last_inspection_date obs,
         IF(last_inspection_date IS NOT NULL, 'last inspection (proxy for cessation)',
            'publisher carries no cessation date') basis,
         'spatial_facility_point' keying,
         'ST_CONTAINS(parcel_geog, ECHO facility point) [D85 excluded]' bridge,
         'echo:facility_inactive' source_id, 'publisher table (new in v2)' blk, TRUE severe
  FROM `{DS}.in_si_d22_parcel_join` WHERE is_inactive_facility
),
-- ---- H. Lane D columns that were pulled and never wired (item 10) ---------------------------
-- Two of the eleven are PLACEMENT, not enrichment: SRI publishes its own lat/lon on 29,955 of
-- 83,547 rows, and IBTR publishes stateParcelNumber on its appeals. Both are the publisher's own
-- key/point — no geocoder, no centroid, no estimate. saleTypeDescription splits the SRI corpus
-- into D2 (Foreclosure) and D1 (Tax/Certificate/Deed Sale), which are different claims.
-- Auction dates are largely in the FUTURE — scheduled sales — which the roll-up already keeps
-- apart from past events rather than treating as an error.
h_sri AS (
  SELECT parcel_key pk, signal, auction_date obs, 'publisher event date' basis,
         'publisher_point' keying,
         'ST_CONTAINS(parcel_geog, SRI published lat/lon) [D85 excluded]' bridge,
         CONCAT('sri_taxsale:', IFNULL(sale_type,'?')) source_id,
         'publisher table (new in v2)' blk, TRUE AS severe
  FROM `{DS}.in_si_sri_placed`
),
h_ibtr AS (
  SELECT parcel_key pk, signal, date_received obs, 'publisher event date' basis,
         'publisher_state_parcel_number' keying,
         'IBTR stateParcelNumber (publisher key, not the corpus IN: copy)' bridge,
         CONCAT('ibtr:', IFNULL(appeal_type,'?')) source_id,
         'publisher table (new in v2)' blk, TRUE AS severe
  FROM `{DS}.in_si_ibtr_placed`
),
-- A5: the Indianapolis code corpus, widened from 2 case types to 7 and gated on INTENT rather
-- than on incident. 910,483 rows of which 40% is High Weeds & Grass; admitted are the
-- condemnation-track types on a single occurrence, plus building/repair/environmental ONLY where
-- the address is chronically cited (>=3 structural cases) or the case was never resolved.
-- Operator ruling: "structural distress needs to actually result in intent, so minor incidents
-- don't do us any good." Placed via Indy's OWN FULL_ADDRESS -> STATEPARCELNUMBER authority.
h_indy_wide AS (
  SELECT parcel_key pk, signal, event_date obs, 'publisher event date (epoch ms)' basis,
         'indy_address_authority' keying,
         'STREET_ADDRESS -> sde_Addressing FULL_ADDRESS -> STATEPARCELNUMBER (widened, intent-gated)' bridge,
         CONCAT('indy_code:', IFNULL(admit_basis, '?')) source_id,
         'publisher table (A5 widening)' blk, TRUE AS severe
  FROM `{DS}.in_si_indy_code_widened`
),
allsig AS (
  SELECT * FROM h_indy_wide UNION ALL
  SELECT * FROM h_sri UNION ALL SELECT * FROM h_ibtr UNION ALL
  SELECT * FROM a_corpus UNION ALL SELECT * FROM b_bridged
  UNION ALL SELECT * FROM c_sb_vacant UNION ALL SELECT * FROM c_sb_code
  UNION ALL SELECT * FROM c_sb_cont
  UNION ALL SELECT * FROM d_ev_tax  UNION ALL SELECT * FROM d_ev_fore
  UNION ALL SELECT * FROM d_ev_demo
  UNION ALL SELECT * FROM e_indy_abandoned UNION ALL SELECT * FROM f_indy_unsafe
  UNION ALL SELECT * FROM g_d22_violation UNION ALL SELECT * FROM g_d22_inactive
)
SELECT
  s.parcel_source, s.parcel_key, a.signal, s.occ_group,
  CASE WHEN s.occ_group = 'residential' THEN 'excluded_residential'
       WHEN NOT LOGICAL_OR(a.severe)    THEN 'excluded_low_severity'
       ELSE 'admitted' END                          AS admit_status,
  (s.occ_group != 'residential' AND LOGICAL_OR(a.severe)) AS si_admitted,
  ANY_VALUE(a.blk)                                  AS source_block,
  COUNT(*)                                          AS n_events,
  COUNTIF(a.obs IS NOT NULL)                        AS n_events_dated,
  MIN(a.obs)                                        AS first_event_date,
  MAX(a.obs)                                        AS last_event_date,
  MAX(IF(a.obs <= CURRENT_DATE(), a.obs, NULL))     AS last_past_event_date,
  COUNTIF(a.obs BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 3 YEAR) AND CURRENT_DATE())  AS n_events_3y,
  COUNTIF(a.obs BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 5 YEAR) AND CURRENT_DATE())  AS n_events_5y,
  COUNTIF(a.obs BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 10 YEAR) AND CURRENT_DATE()) AS n_events_10y,
  COUNTIF(a.obs > CURRENT_DATE())                   AS n_events_future,
  STRING_AGG(DISTINCT a.basis  ORDER BY a.basis)    AS date_basis,
  STRING_AGG(DISTINCT a.keying ORDER BY a.keying)   AS keying_methods,
  STRING_AGG(DISTINCT a.bridge ORDER BY a.bridge)   AS bridge_methods,
  STRING_AGG(DISTINCT a.source_id ORDER BY a.source_id LIMIT 6) AS source_ids,
  TIMESTAMP('{BUILT}')                              AS built_at
FROM allsig a
JOIN `{DS}.in_sites` s ON s.parcel_key = a.pk
WHERE a.pk != '{D85}'                                -- D85 whole-Earth polygon guard
GROUP BY 1,2,3,4
"""
run(EVIDENCE, "in_si_parcel_signals_v2")

# ---------------------------------------------------------------------------------------------
# 2. the per-parcel flag the app reads
# ---------------------------------------------------------------------------------------------
print("building in_si_sites_flags_v2 …", flush=True)
FLAGS = f"""
CREATE OR REPLACE TABLE `{DS}.in_si_sites_flags_v2` AS
WITH agg AS (
SELECT
  parcel_source, parcel_key, ANY_VALUE(occ_group) occ_group,
  LOGICAL_OR(si_admitted)                          AS has_si_signal,
  COUNTIF(si_admitted)                             AS si_signal_types,
  SUM(IF(si_admitted, n_events, 0))                AS si_signal_events,
  STRING_AGG(IF(si_admitted, signal, NULL), ',' ORDER BY signal) AS si_signals,
  MIN(IF(si_admitted, first_event_date, NULL))     AS si_first_event_date,
  MAX(IF(si_admitted, last_past_event_date, NULL)) AS si_last_event_date,
  MAX(IF(si_admitted, last_event_date, NULL))      AS si_last_event_date_incl_future,
  SUM(IF(si_admitted, n_events_3y, 0))             AS si_events_3y,
  SUM(IF(si_admitted, n_events_5y, 0))             AS si_events_5y,
  SUM(IF(si_admitted, n_events_10y, 0))            AS si_events_10y,
  SUM(IF(si_admitted, n_events_dated, 0))          AS si_events_dated,
  -- kept, not dropped: what each ruling excluded, so the exclusion is auditable on screen
  COUNTIF(admit_status='excluded_residential')     AS si_excluded_residential,
  COUNTIF(admit_status='excluded_low_severity')    AS si_excluded_low_severity,
  STRING_AGG(DISTINCT IF(si_admitted, keying_methods, NULL)) AS si_keying,
  STRING_AGG(DISTINCT IF(si_admitted, date_basis, NULL))     AS si_date_basis,
  TIMESTAMP('{BUILT}')                             AS built_at
FROM `{DS}.in_si_parcel_signals_v2`
GROUP BY 1,2)
-- CAN THE PARCEL HOST THE USE CASE AT ALL? A distinct question from "did an event occur", and the
-- one the D5 fix did not answer. Measured after the Lane D placements landed: 17,318 of 23,140
-- flagged parcels are UNDER ONE ACRE, and the median flagged vacant lot is 0.13 acres. A tax sale
-- on a 0.11-acre lot is a genuine event — unlike D5's footprint absence, it has a date and an
-- auction — but it can never host a ~300 MW datacentre or even a ~5 MW BESS.
-- The flag stays a FACT about the parcel; capability is carried alongside it so the screener and
-- the headline can gate on physical possibility without deleting the evidence. At the operator's
-- stated 10 MW/acre BESS, 5 MW needs ~0.5 acres — the smallest use case in scope.
SELECT a.*,
  s.parcel_acres,
  IFNULL(s.parcel_acres, 0) >= 0.5  AS fits_min_bess_5mw,
  IFNULL(s.mw_datacenter_4_per_acre, 0) >= 25 AS fits_dc_25mw
FROM agg a LEFT JOIN `{DS}.in_sites` s USING (parcel_source, parcel_key)
"""
run(FLAGS, "in_si_sites_flags_v2")

# ---------------------------------------------------------------------------------------------
# 3. per-signal coverage. `source_block` keeps the corpus and the newly-bridged publisher tables
#    apart — without it D12 reads "10,370 of 747,211 matched", which is two different sources.
# ---------------------------------------------------------------------------------------------
print("building in_si_signal_coverage …", flush=True)
COVER = f"""
CREATE OR REPLACE TABLE `{DS}.in_si_signal_coverage` AS
WITH corpus AS (
  SELECT signal, COUNT(*) corpus_rows, COUNTIF(observed_date IS NOT NULL) corpus_dated,
         MIN(observed_date) corpus_first, MAX(observed_date) corpus_last,
         STRING_AGG(DISTINCT keying ORDER BY keying) corpus_keying
  FROM `{DS}.in_si_signals` GROUP BY 1),
reached AS (
  SELECT signal,
         COUNT(*) parcels_reached, COUNTIF(si_admitted) parcels_admitted,
         COUNTIF(si_admitted AND occ_group='ci') parcels_ci,
         COUNTIF(admit_status='excluded_residential') excl_residential,
         COUNTIF(admit_status='excluded_low_severity') excl_low_severity,
         SUM(IF(si_admitted,n_events,0)) events,
         SUM(IF(si_admitted,n_events_3y,0)) events_3y,
         SUM(IF(si_admitted,n_events_5y,0)) events_5y,
         MIN(IF(si_admitted,first_event_date,NULL)) first_event,
         MAX(IF(si_admitted,last_past_event_date,NULL)) last_event,
         STRING_AGG(DISTINCT IF(si_admitted,keying_methods,NULL)) keying,
         STRING_AGG(DISTINCT source_block) blocks
  FROM `{DS}.in_si_parcel_signals_v2` GROUP BY 1)
SELECT COALESCE(r.signal, c.signal) AS signal,
  c.corpus_rows, c.corpus_dated, c.corpus_first, c.corpus_last, c.corpus_keying,
  IFNULL(r.parcels_reached,0) parcels_reached, IFNULL(r.parcels_admitted,0) parcels_admitted,
  IFNULL(r.parcels_ci,0) parcels_ci, IFNULL(r.excl_residential,0) excl_residential,
  IFNULL(r.excl_low_severity,0) excl_low_severity,
  r.events, r.events_3y, r.events_5y, r.first_event, r.last_event, r.keying, r.blocks,
  TIMESTAMP('{BUILT}') AS built_at
FROM reached r FULL OUTER JOIN corpus c ON c.signal = r.signal
ORDER BY parcels_admitted DESC, corpus_rows DESC
"""
run(COVER, "in_si_signal_coverage")

# ---------------------------------------------------------------------------------------------
# 4. measure what was built
# ---------------------------------------------------------------------------------------------
print("\n--- MEASURED ---", flush=True)
m = q1(f"""SELECT COUNT(*) n_rows, COUNT(DISTINCT parcel_key) parcels,
  COUNT(DISTINCT IF(si_admitted, parcel_key, NULL)) admitted_parcels,
  COUNT(DISTINCT signal) signals,
  COUNTIF(admit_status='excluded_residential') excl_res,
  COUNTIF(admit_status='excluded_low_severity') excl_sev
FROM `{DS}.in_si_parcel_signals_v2`""")
print(f"evidence: {m.n_rows:,} (parcel,signal) rows · {m.parcels:,} parcels · {m.signals} signals")
print(f"  excluded residential   {m.excl_res:,}")
print(f"  excluded low severity  {m.excl_sev:,}")

b = q1(f"""SELECT COUNTIF(has_si_signal) n_flagged,
  COUNTIF(has_si_signal AND si_last_event_date IS NOT NULL) n_dated,
  COUNTIF(has_si_signal AND si_events_3y>0) n_3y, COUNTIF(has_si_signal AND si_events_5y>0) n_5y,
  COUNTIF(has_si_signal AND occ_group='ci') n_ci,
  COUNTIF(has_si_signal AND occ_group='other_nonres') n_other,
  COUNTIF(has_si_signal AND occ_group='agriculture') n_ag,
  COUNTIF(has_si_signal AND occ_group='no_structure') n_land
FROM `{DS}.in_si_sites_flags_v2`""")
print(f"\nFLAG v2 (non-residential, severity-gated): {b.n_flagged:,} parcels")
print(f"  dated {b.n_dated:,} · event within 3y {b.n_3y:,} · within 5y {b.n_5y:,}")
print(f"  C/I {b.n_ci:,} · other non-res {b.n_other:,} · agriculture {b.n_ag:,} · "
      f"vacant land {b.n_land:,}")
old = q1(f"""SELECT COUNTIF(has_si_signal) n, COUNTIF(has_si_signal AND occ_group='no_structure') land
             FROM `{DS}.in_sites`""")
print(f"FLAG v1 was {old.n:,} parcels, {old.land:,} ({100*old.land/old.n:.1f}%) of them empty land")

print("\nper-bridge yield (admitted only):")
for r in client.query(f"""SELECT bridge_methods b, COUNT(*) n, COUNT(DISTINCT parcel_key) p
    FROM `{DS}.in_si_parcel_signals_v2` WHERE si_admitted GROUP BY 1 ORDER BY p DESC"""):
    print(f"  {str(r.b)[:60]:60s} rows={r.n:>7,} parcels={r.p:>7,}")

print("\nper-signal coverage:")
for r in client.query(f"""SELECT signal, corpus_rows, parcels_reached, parcels_admitted,
    parcels_ci, excl_low_severity, first_event, last_event, blocks
    FROM `{DS}.in_si_signal_coverage` ORDER BY parcels_admitted DESC, corpus_rows DESC"""):
    print(f"  {str(r.signal)[:24]:24s} corpus={str(r.corpus_rows or '-'):>8s} "
          f"reached={r.parcels_reached:>6,} admitted={r.parcels_admitted:>6,} "
          f"C/I={r.parcels_ci:>5,} lowsev={r.excl_low_severity:>6,} "
          f"{r.first_event}..{r.last_event}")

# ---------------------------------------------------------------------------------------------
# 5. register — in the SAME RUN that writes (checkpoint invariant 3)
# ---------------------------------------------------------------------------------------------
reg = [
 ("in_si_parcel_signals_v2", int(m.n_rows),
  "indiana_app.in_si_signals + in_si_signals_parcel_dated + in_si_southbend_* + "
  "in_si_evansville_* + in_si_indy_abandoned_vacant + in_si_refresh_indy_code_enforcement",
  "every parcel-reachable SI signal after normalising THREE key namespaces (IN: prefix strip, "
  "punctuated state-id strip, address bridge), with a SEVERITY gate on South Bend code "
  "enforcement (95% litter/weeds) and Evansville demolition (90% residential teardowns). "
  "D85 whole-Earth parcel excluded. admit_status records WHY a row was excluded; nothing dropped."),
 ("in_si_sites_flags_v2", int(q1(f"SELECT COUNT(*) n FROM `{DS}.in_si_sites_flags_v2`").n),
  "indiana_app.in_si_parcel_signals_v2",
  "per-parcel roll-up the app reads: has_si_signal (NON-RESIDENTIAL, severity-gated), signal "
  "list, first/last event date and 3/5/10-year event counts so recency is filterable on screen."),
 ("in_si_signal_coverage", int(q1(f"SELECT COUNT(*) n FROM `{DS}.in_si_signal_coverage`").n),
  "indiana_app.in_si_signals + in_si_parcel_signals_v2",
  "per-signal coverage: corpus rows, keying, publisher date range, parcels reached and admitted, "
  "and what each ruling excluded. source_block keeps the corpus and new publisher tables apart."),
]
for name, n, src, method in reg:
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{name}'").result()
    client.query(
        f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at) "
        f"VALUES (@t,@s,@m,@n,CURRENT_TIMESTAMP())",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", name),
            bigquery.ScalarQueryParameter("s", "STRING", src),
            bigquery.ScalarQueryParameter("m", "STRING", method),
            bigquery.ScalarQueryParameter("n", "INT64", n)])).result()
    print(f"registered {name} ({n:,})")
print("\nDONE")
