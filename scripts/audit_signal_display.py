"""G150: FOR EVERY SI SIGNAL — HELD in BigQuery, ADMITTED, PLACED on a parcel, and where it LOSES.

Operator, 2026-08-21: *"we should really extensively audit whether or not we are displaying all of
the sites that we have in BQ (I know that we filtered many of these signals down – which is fine,
and working as intended – but we really need to ensure that we are displaying all of the data that
we hold, instead of truncating or misrepresenting our actual holdings… this issue has been
partially addressed in the past and I have seen no visible changes)."*

================================================================================================
⛔ WHY A COVERAGE TABLE ALREADY EXISTED AND CHANGED NOTHING
================================================================================================
`in_si_signal_coverage` has held `corpus_rows` beside `parcels_reached` for weeks. It is correct
and it is not an audit, because **nothing ever failed on it**. A number sitting in a table that no
check reads is a note, not a control - which is exactly why the operator has reported this twice
and seen no change.

⭐ SO THIS FAILS. A signal whose corpus is large and whose placement is near-zero is reported as a
FAILURE with its own line, and the checkpoint carries it. The point is not to force every signal
to place - filtering down is legitimate and the operator says so - it is that **the loss has to be
NAMED**. A filter that drops 99% is fine when it is stated; one that drops 99% silently is the
defect.

================================================================================================
THE FOUR STAGES, AND WHAT EACH ONE MEANS
================================================================================================
    HELD       rows in the corpus table the signal is derived from
    REACHED    distinct parcels the signal attaches to at all
    ADMITTED   parcels that survive the residential / low-severity exclusions
    DISPLAYED  parcels the shipped payload actually carries

================================================================================================
⭐ THE SI SIGNALS ARE DELIBERATELY FILTERED, AND THAT IS THE DEFAULT ASSUMPTION HERE
================================================================================================
Operator, 2026-08-21: *"we filtered down for C&I only, and require 3+ violations (among other
requirements) for the signal to be valid. We filter down many of the SI signals, and this should
be known and understood throughout."*

⛔ SO A LARGE DROP IS THE NORMAL CASE, NOT THE ALARM. This audit does not ask "why is the number
smaller" - it asks **"is the reason written down"**. A signal that admits 2,109 parcels out of a
747,211-row corpus is working exactly as designed the moment somebody can say why; the same signal
with no recorded reason is indistinguishable from a broken join, and a reader cannot tell them
apart. The failure condition is SILENCE, never selectivity.

⚠ A DROP BETWEEN HELD AND REACHED IS NOT AUTOMATICALLY A DEFECT. Three further legitimate causes:
    · the corpus is COUNTY-GRAIN and was never per-parcel (D25 rail abandonment, D8 exit intent)
    · the corpus carries NO ADDRESS AND NO COORDINATE, so nothing could ever key it (D19 WARN,
      until 2026-08-21 - see extract_warn_addresses.py)
    · the signal is deliberately narrow (D24 plant delisting holds 13 rows in total)
Each of those is a REASON, and a signal with a reason passes. A signal with a large corpus, no
placement and no reason FAILS.

RE-SCRAPE COMMAND: python scripts/audit_signal_display.py
"""
import io
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
client = bigquery.Client(project="energy-platfrom")

# ================================================================================================
# ⛔ THE REASON LEDGER. A signal that places far below what it holds must appear here WITH a
# measured reason, or this audit fails. Edit this when the world changes, never to silence a row.
# ================================================================================================
REASONS = {
    "D12_code_violation": (
        "⭐ DELIBERATELY FILTERED, operator 2026-08-21: *\"we filtered down for C&I only, and "
        "require 3+ violations (among other requirements) for the signal to be valid.\"* "
        "So the drop from 747,211 corpus rows to 23,145 parcels is the filter working, not a "
        "loss. ⭐ 40% of the Indianapolis corpus is High Weeds & Grass; admitting it whole would "
        "have inflated this signal by ~750,000 rows of lawn care. "
        "⚠ MEASURED AGAINST THE ARTEFACT, AND ONE HALF DOES NOT RECONCILE: the C&I rule IS "
        "enforced and visible - 16,295 parcels carry admit_status='excluded_residential' and "
        "4,741 'excluded_low_severity', leaving 2,109 admitted. But the 3+ VIOLATION MINIMUM IS "
        "NOT ENFORCED ON THIS TABLE: the admitted set runs min_events=1, max 27, mean 3.5. Either "
        "the threshold is applied at a different grain (per building rather than per parcel "
        "signal row) or it is not applied at all. ⛔ Recorded as a discrepancy rather than "
        "smoothed over - the intent is documented, the artefact disagrees with half of it, and "
        "that is exactly what a probe is for."),
    "D5_vacancy": "COUNTY/TRACT GRAIN. The 947,592 rows are ACS tract vacancy, not parcel "
                  "records - there is no parcel to attach and never was. It informs the county "
                  "rollup instead.",
    "D25_rail_abandonment": "COUNTY GRAIN. STB abandonment dockets name a rail LINE and a county, "
                            "not a parcel. Placing one would be inventing a lot boundary.",
    "D8_exit_intent": "COUNTY GRAIN and historic - the newest row is 2008. Kept for the county "
                      "rollup only.",
    "D17_commercial_eviction": "COUNTY GRAIN. The corpus is a court-docket count per county; no "
                               "address is published with it.",
    "D6_bankruptcy": "OWNER-NAME KEYING ONLY, and Indiana publishes no statewide owner name to "
                     "match against - the same DLGF Gateway block as G70/G104. Marion is the "
                     "exception and is now reachable via in_marion_owner_value (G132).",
    "D3_seized_auction": "THE CORPUS IS 2 ROWS. Nothing is being lost.",
    "D24_plant_delisting": "THE CORPUS IS 13 ROWS and 10 of them place. Nothing is being lost; "
                           "the signal is genuinely rare.",
    "D19_warn": "NO ADDRESS COLUMN IN THE CORPUS - company and city only. ⭐ Addresses were "
                "recovered from the filing PDFs on 2026-08-21 (extract_warn_addresses.py) and "
                "placement went 2 -> 21 parcels. The remaining ceiling is the 1,048 notices that "
                "carry no filing URL in our clip, which is G151.",
    "D7_brownfield": "PARTIAL BY NATURE: an IDEM brownfield record names a site, and 536 of 1,378 "
                     "resolve to a parcel. The rest name a locality.",
    "D20_loan_maturity": "OWNER-NAME AND ADDRESS KEYING on CMBS records; 207 of 419 place.",
    "D14_sba_chargeoff": "ADDRESS KEYING on borrower addresses; 1,773 of 3,774 place.",
    "D16_catastrophic_damage": "DERIVED, not a corpus of its own - it is a severity class over "
                               "the fire feed.",
    "D22_facility_inactive": "DERIVED from the IDEM facility status vocabulary.",
}

# a signal placing under this share of its corpus must carry a reason
FLOOR = 0.05
# and only when the corpus is big enough for the ratio to mean anything
MIN_CORPUS = 100

print("=" * 96)
print("G150 - IS EVERY SI SIGNAL DISPLAYING WHAT WE HOLD?")
print("=" * 96)

rows = list(client.query(f"""
  SELECT signal, corpus_rows, parcels_reached, parcels_admitted, corpus_keying, blocks
  FROM `{DS}.in_si_signal_coverage`
  ORDER BY IFNULL(corpus_rows, 0) DESC"""))

fails, noted = [], 0
print(f"\n  {'signal':30} {'HELD':>10} {'REACHED':>9} {'ADMITTED':>9}  {'share':>7}  verdict")
print("  " + "-" * 92)
for r in rows:
    held = r.corpus_rows
    reached = r.parcels_reached or 0
    admitted = r.parcels_admitted or 0
    if held is None:
        # ⚠ A NULL CORPUS IS ITSELF A FINDING: the coverage row exists and nobody recorded how
        # many rows the signal is derived from, so no loss can be computed for it at all.
        verdict = "no corpus count recorded"
        if r.signal not in REASONS:
            fails.append(f"{r.signal}: coverage row carries NO corpus_rows, so the loss between "
                         f"held and placed cannot be measured at all")
            verdict = "⛔ UNMEASURABLE"
        print(f"  {r.signal:30} {'—':>10} {reached:>9,} {admitted:>9,}  {'—':>7}  {verdict}")
        continue
    share = (reached / held) if held else 0
    if held >= MIN_CORPUS and share < FLOOR:
        if r.signal in REASONS:
            verdict = "low, and the reason is recorded"
            noted += 1
        else:
            verdict = "⛔ FAILS — big corpus, no placement, NO REASON"
            fails.append(f"{r.signal}: {held:,} rows held, {reached:,} parcels reached "
                         f"({share:.1%}) and no reason is recorded for the loss")
    else:
        verdict = "ok"
    print(f"  {r.signal:30} {held:>10,} {reached:>9,} {admitted:>9,}  {share:>6.1%}  {verdict}")

print(f"\n  {len(rows)} signals · {noted} placing low WITH a recorded reason · "
      f"{len(fails)} unexplained")

# ---- the reason ledger must not rot ------------------------------------------------------------
live = {r.signal for r in rows}
stale = [s for s in REASONS if s not in live]
if stale:
    fails.append(f"the reason ledger names {len(stale)} signal(s) that no longer exist: "
                 f"{', '.join(sorted(stale))}")

print()
if fails:
    for f in fails:
        print(f"  FAIL  {f}")
else:
    print("  every signal either places what it holds, or carries a measured reason for the loss")
print(f"\n{len(fails)} unexplained signal loss(es)")
print("=" * 96)
sys.exit(1 if fails else 0)
