"""G133: FEDERAL SURPLUS AND THE WITHDRAWN QUEUE AS SI SIGNALS, not just as map layers.

Operator, 2026-08-21: *"Incorporate federal surplus properties and withdrawn interconnection
queues directly into the SI signals throughout the application, with plans to add state surplus
facilities later… We should also add land banks to our SI signals as well."*

================================================================================================
⛔ WHY THEY WERE NOT ALREADY SIGNALS, AND WHY THAT WAS A REAL GAP
================================================================================================
Both shipped as map LAYERS - G97 and G98 - and neither ever entered the SI signal set. Measured:
`in_si_parcel_signals_v2` holds 135,590 rows across ten signals and every one of them is a
DISTRESS code (D1 tax sale, D2 foreclosure, D4 delinquency, D5 unsafe/abandoned, D12 code
violation, D16 fire, D21 demolition, D22 environmental, D26 appeal, D14 SBA charge-off). So a
parcel whose owner has FORMALLY DECLARED it surplus, or whose owner already signed an
interconnection agreement and then withdrew, carried no owner-motivation signal at all - while a
parcel with one code violation did.

⭐ AND THEY ARE A DIFFERENT KIND OF SIGNAL, WHICH IS THE INTERESTING PART. Every existing D-code
INFERS willingness from distress: the owner is in trouble, so they may sell. These two REVEAL it:
  · A federal asset marked excess or surplus is the owner saying, on the record, that they intend
    to dispose of it.
  · A withdrawn interconnection request is an owner who already consented to host energy
    infrastructure on that land, and who now has a studied grid position with no project on it.
Distress is a proxy for willingness. This is willingness stated.

⛔ SO THEY ARE COUNTED SEPARATELY, AND THAT IS DELIBERATE. Folding them into
`in_si_sites_flags_v2` would move the flagged-parcel count - 23,766, which the checkpoint asserts
against the shipped payload - and would mix inferred willingness with declared willingness under
one number. Two different claims under one count is how a reader stops trusting both. They are an
ADDITIVE family with their own codes and their own count.

================================================================================================
⚠ THE TWO SOURCES NEED DIFFERENT TREATMENT, AND ONE OF THEM IS NOT KEYED AT ALL
================================================================================================
  in_si_queue_withdrawn   872 rows, and it ALREADY carries parcel_source + parcel_key. Direct.
  in_si_gov_surplus_v2  1,594 rows, and it carries NO parcel key - only lat/lon. It needs a
                        spatial join, and ⛔ D85 (the inverted whole-Earth parcel) must be
                        excluded or every federal point lands on it. Fan-out is asserted.

⚠ AND ONLY A FRACTION OF THE FEDERAL SET IS A SIGNAL. G97 already established this and it is the
reason that control was split in two: 1,548 of the 1,594 points are in Current or Future Mission
Need. The label "federal surplus property" was true of nine locations. Only rows the source itself
marks excess / surplus / unutilised are admitted here.

⛔ LAND BANKS ARE NOT IN THIS BUILD BECAUSE WE HOLD NO LAND-BANK DATA. Checked, per standing rule
G25, before writing a line of it: no table in `indiana_app` or `energy` carries an Indiana land
bank register. That half of G133 is an ACQUISITION - it belongs with G102 (state surplus), and
inventing a placeholder layer for it would be a data gap wearing a UI costume.

RE-SCRAPE COMMAND: python scripts/build_si_intent_signals.py
⚠ IDEMPOTENT: replace_safe. CADENCE: quarterly - FRPP is annual, the ISO queues are monthly.
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_si_intent_signals"
D85 = "080500000047000018"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS

WITH
-- the parcel corpus we are allowed to attach a signal to
cand AS (
  SELECT parcel_source, parcel_key, parcel_geog
  FROM `{DS}.in_sites`
  -- ⛔ D85. An inverted whole-Earth polygon swallows every point in the state; excluding it is a
  -- standing rule and the fan-out assertion below is what proves the guard held.
  WHERE parcel_key != '{D85}' AND parcel_geog IS NOT NULL
),

-- =============================================================================================
-- I1 - A FEDERAL OWNER HAS DECLARED THE ASSET EXCESS OR SURPLUS
-- ⚠ ADMITTED ON THE PUBLISHER'S OWN STATUS, never on the fact that a point is federal. G97 found
-- this control asserting "surplus" about 1,594 points when it was true of nine.
-- =============================================================================================
surplus AS (
  SELECT s.asset_id, s.agency, s.installation_name, s.asset_status, s.surplus_class,
         s.acres, s.excess_date, s.dispose_date, s.disposition_method, s.years_underutilized,
         ST_GEOGPOINT(s.lon, s.lat) AS pt
  FROM `{DS}.in_si_gov_surplus_v2` s
  WHERE s.lat IS NOT NULL AND s.lon IS NOT NULL
    AND (s.is_si_signal OR REGEXP_CONTAINS(UPPER(IFNULL(s.asset_status, '')),
                                           r'EXCESS|SURPLUS|UNUTILIZ|UNDERUTILIZ|DISPOS'))
),
surplus_on_parcel AS (
  SELECT c.parcel_source, c.parcel_key,
         'I1_declared_surplus' AS signal,
         COUNT(*) AS n_events,
         -- ⚠ the publisher's own date, and it is often absent: an asset can be marked excess
         -- with no date recorded. NULL, never today.
         CAST(MAX(COALESCE(sp.excess_date, sp.dispose_date)) AS STRING) AS last_event_date,
         STRING_AGG(DISTINCT sp.agency, '; ' LIMIT 3) AS who,
         STRING_AGG(DISTINCT sp.asset_status, '; ' LIMIT 3) AS status_verbatim,
         ROUND(SUM(sp.acres), 1) AS signal_acres,
         MAX(sp.years_underutilized) AS years_underutilized
  FROM cand c
  JOIN surplus sp ON ST_INTERSECTS(c.parcel_geog, sp.pt)
  GROUP BY 1, 2
),

-- =============================================================================================
-- I2 - THE OWNER ALREADY CONSENTED TO HOST ENERGY INFRASTRUCTURE, AND THE PROJECT IS GONE
-- ⚠ THE POINT IS THE INTERCONNECTION POINT, NOT THE GENERATOR PARCEL - G98's own caveat, and it
-- can be a mile away down a gen-tie. `placement_grain` carries how precise the placement is and
-- it ships with the signal rather than being averaged away.
-- ⭐ AND THE SIZE MATTERS: a cancelled 5 MW solar project does not imply land for a 300 MW campus,
-- so the largest capacity given up on that parcel is part of the signal.
-- =============================================================================================
withdrawn_on_parcel AS (
  SELECT parcel_source, parcel_key,
         'I2_withdrawn_interconnection' AS signal,
         COUNT(*) AS n_events,
         CAST(MAX(wd_date) AS STRING) AS last_event_date,
         STRING_AGG(DISTINCT counterparty, '; ' LIMIT 3) AS who,
         STRING_AGG(DISTINCT CONCAT(iso, ' ', IFNULL(resource_type, '?')), '; ' LIMIT 3)
           AS status_verbatim,
         CAST(NULL AS FLOAT64) AS signal_acres,
         CAST(NULL AS INT64) AS years_underutilized
  FROM `{DS}.in_si_queue_withdrawn`
  WHERE parcel_key IS NOT NULL AND parcel_key != '{D85}'
  GROUP BY 1, 2
),
withdrawn_mw AS (
  SELECT parcel_source, parcel_key, ROUND(MAX(capacity_mw), 1) AS wd_max_mw,
         ANY_VALUE(placement_grain) AS placement_grain
  FROM `{DS}.in_si_queue_withdrawn`
  WHERE parcel_key IS NOT NULL AND parcel_key != '{D85}'
  GROUP BY 1, 2
),

unioned AS (
  SELECT s.*, CAST(NULL AS FLOAT64) AS mw_given_up, CAST(NULL AS STRING) AS placement_grain
  FROM surplus_on_parcel s
  UNION ALL
  SELECT w.*, m.wd_max_mw AS mw_given_up, m.placement_grain
  FROM withdrawn_on_parcel w LEFT JOIN withdrawn_mw m USING (parcel_source, parcel_key)
)

SELECT
  parcel_source, parcel_key, signal,
  -- ⭐ THE FAMILY, STATED. Every existing SI code infers willingness from distress; both of these
  -- REVEAL it. A reader has to be able to tell those apart, so the distinction is a column and
  -- not a footnote.
  'declared_intent' AS signal_family,
  n_events, last_event_date, who, status_verbatim,
  signal_acres, years_underutilized, mw_given_up, placement_grain,
  CASE signal
    WHEN 'I1_declared_surplus' THEN
      'The federal owner has recorded this asset as excess, surplus or unutilized — a stated '
      || 'intention to dispose, not an inference from distress.'
    WHEN 'I2_withdrawn_interconnection' THEN
      'An interconnection request on this parcel was withdrawn. The owner already consented to '
      || 'host energy infrastructure and the studied grid position is now unused. ⚠ The point is '
      || 'the interconnection point, which can sit a mile from the generator parcel.'
  END AS so_what,
  CURRENT_TIMESTAMP() AS built_at
FROM unioned
"""

print("G133 - DECLARED-INTENT SI SIGNALS (federal surplus + withdrawn queue)")
job = client.query(SQL)
job.result()
gb = round((job.total_bytes_processed or 0) / 1e9, 2)
print(f"  built, {gb} GB scanned")

n = list(client.query(f"SELECT COUNT(*) n FROM `{OUT}`"))[0].n
d = list(client.query(f"""SELECT COUNT(DISTINCT CONCAT(parcel_source,'|',parcel_key,'|',signal)) n
                          FROM `{OUT}`"""))[0].n
print(f"  fan-out {n:,} rows / {d:,} distinct (parcel, signal) = {n / d:.4f}")
assert n == d, "one row per parcel per signal, or D85 or a join fanned out"

for r in client.query(f"""
  SELECT signal, COUNT(*) parcels, SUM(n_events) events,
         COUNTIF(last_event_date IS NOT NULL) dated,
         ROUND(MAX(mw_given_up)) max_mw, ROUND(SUM(signal_acres)) acres
  FROM `{OUT}` GROUP BY 1 ORDER BY 2 DESC"""):
    print(f"    {r.signal:30} parcels={r.parcels:>6,}  events={r.events:>6,}  "
          f"dated={r.dated:>5,}  max MW given up={r.max_mw}  acres={r.acres}")

# ⭐ HOW MUCH IS GENUINELY NEW? A parcel that already carries a distress signal is not a new lead.
ov = list(client.query(f"""
  SELECT COUNT(DISTINCT i.parcel_key) intent_parcels,
         COUNT(DISTINCT IF(f.has_si_signal, i.parcel_key, NULL)) also_distressed,
         COUNT(DISTINCT IF(f.has_si_signal IS NOT TRUE, i.parcel_key, NULL)) intent_only
  FROM `{OUT}` i
  LEFT JOIN `{DS}.in_si_sites_flags_v2` f USING (parcel_source, parcel_key)"""))[0]
print(f"\n  ⭐ {ov.intent_parcels:,} parcels carry a declared-intent signal")
print(f"  ⭐ {ov.intent_only:,} of them carry NO distress signal at all — these are leads the "
      f"existing SI set could not see")
print(f"  ⚠ {ov.also_distressed:,} already had one, so they are a stronger case rather than a "
      f"new one")

# ⛔ THE HALF WE CANNOT DO, SAID OUT LOUD RATHER THAN QUIETLY OMITTED.
print("\n  ⛔ LAND BANKS: not in this build. Checked per standing rule G25 before writing it - no")
print("     object in indiana_app or energy carries an Indiana land-bank register. That is an")
print("     ACQUISITION (it belongs with G102, state surplus), not a join we are missing.")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_si_intent_signals',
 'indiana_app.in_si_gov_surplus_v2 (spatial join to in_sites) x indiana_app.in_si_queue_withdrawn '
 '(already parcel-keyed)',
 'DECLARED-INTENT owner signals, one row per parcel per signal. I1_declared_surplus: a federal '
 'asset the publisher marks excess / surplus / unutilized, attached by ST_INTERSECTS against the '
 'parcel polygon. ⚠ Admitted on the publisher status only - 1,548 of the 1,594 federal points are '
 'in Current or Future Mission Need and are NOT a signal (G97). I2_withdrawn_interconnection: a '
 'withdrawn ISO interconnection request, carrying the largest capacity given up and the placement '
 'grain, because the interconnection point can sit a mile from the generator parcel (G98). '
 '⭐ COUNTED SEPARATELY FROM in_si_sites_flags_v2 ON PURPOSE: every existing SI code INFERS '
 'willingness from distress, these two REVEAL it, and merging them would move the 23,766 flagged '
 'count and mix two different claims under one number. D85 excluded; fan-out asserted at 1.0. '
 'RE-SCRAPE COMMAND: python scripts/build_si_intent_signals.py',
 {n}, {gb}, CURRENT_TIMESTAMP(),
 'G133, operator 2026-08-21. Both sources shipped as MAP LAYERS in G97/G98 and neither ever '
 'entered the SI signal set, so a parcel formally declared surplus carried no owner-motivation '
 'signal while a parcel with one code violation did. ⛔ LAND BANKS ARE NOT INCLUDED - checked per '
 'G25, no Indiana land-bank register exists in either dataset; that half is an acquisition and '
 'belongs with G102. State surplus is also still G102. '
 'IDEMPOTENCY: replace_safe. CADENCE: quarterly (FRPP annual, ISO queues monthly).'
)""").result()
print("\n  _registry row written")
print("INTENT SIGNALS COMPLETE")
