"""G81 - is 24,277 flagged parcels truthful, and why is it not more? Publish the FUNNEL.

    python scripts/build_si_funnel.py

Operator, 2026-08-19: *"We need to determine if ~24,000 seller intent properties is actually
truthful - why don't we have more?"*

⭐ THE NUMBER IS NOT A RENDERING ERROR. The checkpoint asserts payload-vs-warehouse agreement on
24,277 every run. The question is the FUNNEL, so this publishes it, with the loss at each stage
NAMED - and the dominant loss is not what the backlog row guessed.

⛔ THE HEADLINE: THE LARGEST SIGNAL IN THE ESTATE IS 99.4% BARE LAND.
`D5_vacancy` is **947,592 raw rows - 52% of everything we hold** - and it reaches the parcel-grain
rollup under no name at all. That looks like a wiring defect until you measure the parcels:

    of the 845,373 D5_vacancy parcels that match a real Indiana parcel,
        840,473  (99.4%)  have NO STRUCTURE
          3,946   (0.5%)  residential
            511   (0.1%)  commercial or industrial

A postal vacancy flag on a parcel with no building on it is not a seller-intent signal; it is
noise, and admitting it would inflate the flagged count by ~35x with bare land. ⭐ **So excluding
it is CORRECT, and this script's job is to say so out loud rather than let the absence look like an
oversight.** It is the same failure the D12 work already avoided - 40% of Indy's code corpus is
High Weeds & Grass, and admitting it whole would have added ~750,000 rows of lawn care.

⚠ TWO KEY NAMESPACES, AND COMPARING THEM NAIVELY GIVES A NONSENSE FUNNEL. `in_si_signals.parcel_key`
is state-prefixed (`'IN:640324226011000021'`) and `in_si_parcel_signals_v2.parcel_key` is bare
(`'020424400002000062'`). Joined raw, the two tables share **ZERO** parcels, which would read as
"nothing survives the pipeline". Strip the prefix and 847,410 of 951,348 match a real parcel.
⛔ The two stages are therefore reported as SEPARATE TRACKS with different populations, never as
one subtracting chain, because the row-grain feed and the parcel-grain rollup do not cover the same
signal set.

⭐ WHERE THE ADMITTED PARCELS ACTUALLY GO, and this IS one clean chain (all inside one table):
    106,659 parcels reach the parcel-grain rollup
    -76,612 excluded as RESIDENTIAL      (a house is not a data-centre site)
     -6,231 excluded as LOW SEVERITY     <- the hidden editorial filter G83 asks us to disclose
    = 24,277 admitted

WRITES `indiana_app.in_si_funnel` and `data/si_funnel.json.gz`. Reads indiana_app only.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import json
import gzip
import os
import datetime
from google.cloud import bigquery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")


def one(sql):
    return list(client.query(sql))[0]


print("measuring the raw feed ...")
raw = one(f"""
SELECT COUNT(*) rows_,
       COUNTIF(parcel_key IS NOT NULL AND TRIM(parcel_key)!='') keyed,
       COUNT(DISTINCT IF(parcel_key IS NOT NULL AND TRIM(parcel_key)!='', parcel_key, NULL)) parcels,
       COUNT(DISTINCT signal) signals
FROM `{DS}.in_si_signals`""")

print("resolving those keys against real parcels ...")
res = one(f"""
WITH sig AS (SELECT DISTINCT REGEXP_REPLACE(parcel_key, r'^IN:', '') AS pk
             FROM `{DS}.in_si_signals` WHERE parcel_key IS NOT NULL AND TRIM(parcel_key)!=''),
     site AS (SELECT DISTINCT parcel_key AS pk FROM `{DS}.in_sites`)
SELECT COUNT(*) n, COUNTIF(site.pk IS NOT NULL) matched
FROM sig LEFT JOIN site USING (pk)""")

print("measuring the structure test that removes D5_vacancy ...")
occ = [dict(r) for r in client.query(f"""
WITH sig AS (SELECT DISTINCT REGEXP_REPLACE(parcel_key, r'^IN:', '') AS pk
             FROM `{DS}.in_si_signals` WHERE signal='D5_vacancy' AND parcel_key IS NOT NULL)
SELECT s.occ_group, COUNT(*) n
FROM sig JOIN `{DS}.in_sites` s ON s.parcel_key = sig.pk
GROUP BY 1 ORDER BY n DESC""")]

print("measuring the admit chain ...")
adm = [dict(r) for r in client.query(f"""
SELECT admit_status, COUNT(*) rows_, COUNT(DISTINCT parcel_key) parcels
FROM `{DS}.in_si_parcel_signals_v2` GROUP BY 1 ORDER BY parcels DESC""")]
roll = one(f"""SELECT COUNT(*) rows_, COUNT(DISTINCT parcel_key) parcels,
                      COUNT(DISTINCT signal) signals
               FROM `{DS}.in_si_parcel_signals_v2`""")
admitted = one(f"""SELECT COUNT(DISTINCT parcel_key) p FROM `{DS}.in_si_parcel_signals_v2`
                   WHERE si_admitted""")

print("measuring the owner-grain signals G82 just moved ...")
try:
    a2p = one(f"""SELECT COUNT(*) n, COUNT(DISTINCT parcel_id) p FROM `{DS}.in_si_address_parcel`""")
    a2p_n, a2p_p = a2p.n, a2p.p
except Exception:
    a2p_n = a2p_p = 0

stages = [
    {"stage": "Raw signal rows held", "n": raw.rows_, "grain": "row",
     "note": f"{raw.signals} distinct signals across the whole estate."},
    {"stage": "Rows carrying a parcel id", "n": raw.keyed, "grain": "row",
     "lost": raw.rows_ - raw.keyed,
     "note": "The rest are keyed by normalised address, owner name or an aggregate, and were "
             "never resolved to a specific parcel."},
    {"stage": "Distinct parcels those keys name", "n": raw.parcels, "grain": "parcel"},
    {"stage": "…that are a real Indiana parcel we hold", "n": res.matched, "grain": "parcel",
     "lost": res.n - res.matched,
     "note": "⚠ Requires stripping the 'IN:' prefix first — the raw feed and the parcel corpus "
             "use different key namespaces, and joined naively they share ZERO parcels."},
    {"stage": "…that actually carry a STRUCTURE", "n": None, "grain": "parcel",
     "note": "This is where the largest signal dies, and correctly. 840,473 of the 845,373 "
             "D5_vacancy parcels (99.4%) have NO STRUCTURE on them. A postal vacancy flag on "
             "bare land is not evidence an owner wants to sell."},
    {"stage": "Parcels reaching the parcel-grain rollup", "n": roll.parcels, "grain": "parcel",
     "note": f"A DIFFERENT POPULATION, not a subtraction of the line above: the rollup covers "
             f"{roll.signals} signals, and D5_vacancy is deliberately not one of them."},
    {"stage": "…admitted as an owner-motivation signal", "n": admitted.p, "grain": "parcel",
     "note": "The number on the page."},
]

payload = {
    "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "headline": raw.rows_,
    "admitted_parcels": admitted.p,
    "stages": stages,
    "admit_breakdown": adm,
    "d5_vacancy_occ": occ,
    "address_recovered": {"rows": a2p_n, "parcels": a2p_p},
    "answer": (
        "24,277 is truthful — the checkpoint asserts payload-vs-warehouse agreement on it every "
        "run. It is not larger for three measured reasons, in order of size: (1) the biggest feed "
        "we hold, D5_vacancy at 947,592 rows, sits on parcels that are 99.4% BARE LAND, and a "
        "vacancy flag with no building under it is not seller intent; (2) 76,612 parcels that DO "
        "carry a signal are RESIDENTIAL, and a house is not a data-centre site; (3) 865,312 rows "
        "are keyed only by address or owner name and never resolve to a parcel at all — and that "
        "last one is the acquisition-shaped gap, because Indiana parcel owner is NULL on all "
        "3,553,381 rows and the only address-to-parcel corpus we hold is Marion County's."),
}

out = os.path.join(REPO, "data", "si_funnel.json.gz")
with gzip.open(out, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(payload, f, separators=(",", ":"))

print(f"\n{'stage':52s}{'count':>12s}")
print("-" * 66)
for s in stages:
    print(f"{s['stage'][:50]:52s}{'—' if s['n'] is None else format(s['n'], ','):>12s}")
print("\nadmit breakdown (one clean chain, all inside one table):")
for a in adm:
    print(f"   {a['admit_status']:28s} rows={a['rows_']:>7,}  parcels={a['parcels']:>7,}")
print(f"\nG82 recovered by address match: {a2p_n} rows -> {a2p_p} parcels")
print(f"payload: {os.path.getsize(out):,} bytes")

client.query(f"CREATE OR REPLACE TABLE `{DS}.in_si_funnel` AS SELECT * FROM UNNEST([STRUCT("
             f"{raw.rows_} AS raw_rows, {raw.keyed} AS rows_with_parcel_key, "
             f"{raw.parcels} AS parcels_named, {res.matched} AS parcels_real, "
             f"{roll.parcels} AS rollup_parcels, {admitted.p} AS admitted_parcels, "
             f"CURRENT_TIMESTAMP() AS built_at)])").result()
client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_si_funnel',
 'indiana_app.in_si_signals + in_sites + in_si_parcel_signals_v2',
 'stage-by-stage count of the owner-motivation pipeline; the raw feed key is state-prefixed and '
 'must have IN: stripped before it will join the parcel corpus. '
 'RE-SCRAPE COMMAND: python scripts/build_si_funnel.py',
 1, 0.0, CURRENT_TIMESTAMP(),
 'G81. Answers why the flagged count is 24,277 and not larger. Dominant cause: D5_vacancy is 52% '
 'of all raw rows and 99.4% of its parcels have NO STRUCTURE, so excluding it is correct, not an '
 'oversight. Second: 76,612 signal-carrying parcels are residential. Third: 865,312 rows never '
 'resolve to a parcel because owner is NULL statewide and only Marion publishes an address '
 'crosswalk. The row-grain and parcel-grain tracks are DIFFERENT populations and must not be '
 'presented as one subtracting chain.'
)""").result()
print("  _registry row written")
print("SI FUNNEL COMPLETE")
