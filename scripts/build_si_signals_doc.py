"""GENERATE docs/SI_SIGNALS.md — the whole SI signal system, measured rather than remembered.

Operator, 2026-08-22: *"we did a lot of SI signal work (through rescraping and adding new fields),
and I want to make sure all of the work is documented, including any next steps that may be in
order."*

⛔ WHY THIS IS GENERATED AND NOT WRITTEN. The account of the SI signals was spread across sixteen
backlog rows, three handoffs and a dozen script docstrings, and the one file that DID summarise it
— `docs/SIGNAL_REALITY.json` — went **five days without regenerating** while sitting on the
required reading list, still reporting `D19_warn` at 2 parcels. A hand-written summary of a system
this size is a snapshot that starts decaying the moment it is saved.

⭐ SO EVERY NUMBER BELOW IS A LIVE QUERY. The only hand-written parts are the NEXT STEPS at the
bottom, which are judgements and are labelled as such.

RE-SCRAPE COMMAND: python scripts/build_si_signals_doc.py
⛔ READ-ONLY against the warehouse; writes one markdown file.
"""
import io
import os
import re
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.cloud import bigquery

from si_upstream_sources import REPAIRS, SOURCES, YEAR_GAPS

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "docs", "SI_SIGNALS.md")
client = bigquery.Client(project="energy-platfrom")

# ⚠ HAND-WRITTEN AND LABELLED AS SUCH — a CHANGE LOG cannot be generated, because the warehouse
# knows its current state and not its history or the reasoning behind it. Operator, 2026-08-22:
# *"so we can track exactly what was completed, how it was completed, and why we completed each
# task for the SI signals that we worked with."*
CHANGE_LOG = [
 ("**all 27**", "every event date, per signal, plus a link to the publisher",
  "G145 added `si_next_event_date` and a per-signal `si_signal_dates` array carrying `date_basis`, "
  "`source_ids` and `keying`; G153 renders it through one resolver in `common.js`",
  "8,573 parcels printed *\"date unknown\"* over a date we held — the rollup read the last event "
  "ON OR BEFORE TODAY, so a scheduled tax auction vanished. And no signal said where it came from",
  "— closed"),
 ("`D19_warn`", "43 → **57** parcels reached",
  "G154 geocoded the 34 addresses string-matching could not place (US Census, permission checked), "
  "then `ST_INTERSECTS` against the parcel polygon, then required the parcel's OWN street address "
  "to corroborate the snap",
  "the DLGF address is the assessor's address for a LOT; a medical campus has none per building, "
  "so more regex could never have worked",
  "8 of 34 refused with a written reason. ⛔ The real ceiling is that most Indiana WARN notices "
  "carry no filing PDF, and the address exists only inside the PDF"),
 ("`D22_facility_inactive`", "its **first denominator**, 5,584",
  "counted the INACTIVE marker in `in_si_d22_parcel_join`, the same flag its own source block "
  "filters on",
  "it was the last signal reporting *\"no corpus count recorded\"* — a signal with no denominator "
  "cannot be audited for loss",
  "— closed"),
 ("`D22_environmental_violation`", "denominator corrected **34,116 → 3,340**",
  "counted `is_distress` rather than `COUNT(*)` on a table that carries TWO signals",
  "attributing a whole table to one of the two signals it holds overstates the denominator and is "
  "how `reached > held` gets manufactured",
  "— closed"),
 ("`D28_cmbs_loan_distress`", "**NEW** — 95 held, 27 reached, 13 admitted",
  "full-width clip of `edgar_abs_ee_cmbs` (153 columns), then delinquency / servicer workout / "
  "special servicing / DSCR<1.0 / past maturity folded into ONE condition",
  "under the 13-column reduction this source could produce exactly ONE signal by construction. "
  "A special-serviced loan is the strongest predictor a commercial property will trade",
  "⛔ **G160** — the parent is only ~70% loaded upstream"),
 ("`D29_anchor_tenant_exit`", "**NEW** — 146 held, 24 reached, 20 admitted",
  "same clip: published occupancy ≤60% (a FRACTION, where 0 means unpublished) or the largest "
  "tenant's lease expiring within 24 months",
  "a half-empty building with an anchor rolling off is an owner who needs a plan — and its event "
  "date is in the FUTURE, which only became renderable once G145 landed",
  "⛔ **G160**, same parent"),
 ("`I3_land_bank`", "**NEW** — **691 parcels**",
  "Evansville joined on `StatePIN` (1,528 of 1,660); Indianapolis placed by normalised street "
  "address unique within Marion, because its `parcelnumber` is a 7-digit LOCAL id that appears "
  "nowhere in the state corpus",
  "G133 had recorded land banks as *an acquisition we hold nothing for*. We held two — the G25 "
  "check had grepped for the words *land bank*, and they are filed as `landbank` and `surplus`",
  "— closed"),
 ("`D14_sba_chargeoff`", "⭐ **WIRED 2026-08-22b. 762 → 1,139 admitted parcels (+49%)**",
  "G156(a) built `in_si_addr_placed`: `borrstreet`+`borrcity` normalised through the one shared "
  "normaliser against `dlgf_prop_address`, two passes, admitted only where the address resolves "
  "to exactly one parcel. The clip repair itself re-keyed `cdc_state` → `projectstate`/`borrstate`",
  "⛔ **AND THE MEASUREMENT CORRECTED THE RECORD.** The 5,135 → 39,948 repair was real but its "
  "SIGNAL value was overstated ~450×: only **3,850 loans are `CHGOFF`**, and D14 already held "
  "3,774 through the corpus, so the ROW gain is at most 76. The other 36,098 are PIF / EXEMPT / "
  "CANCLD — paid in full or never drawn, the OPPOSITE of distress. What the clip actually buys is "
  "`borrstreet` (a direct address the corpus lacks) and `grosschargeoffamount` — **$247.2M** now "
  "attached to parcels",
  "⚠ `borrstreet` is the BORROWER address. `projectstate` and `borrstate` both read IN on 39,818 "
  "of 39,948 rows so the STATE is corroborated; the STREET is not. ⚠ Dates reach back to 1993 — "
  "an ageing rule is not yet applied to D14"),
 ("`D16_structure_fire`", "⭐ **WIRED 2026-08-22b. 1,680 → 1,783 admitted parcels**",
  "same builder: NFIRS incident street+city → `dlgf_prop_address`. Gated on "
  "`property_class = 'non-residential'` AND loss ≥ $10k — 1,583 SI-grade incidents, 532 on a "
  "uniquely-keyed parcel, **$43.5M** of loss attached",
  "⛔ **AND A PINNED LITERAL WAS SWALLOWING THE REPAIR.** `build_nfirs_structure_fires.py` carried "
  "`FIRE_YEARS = [2020,2021,2022,2024]  # 2023 fireincident is not held` — false since G152. "
  "Re-running it after the repair produced a **byte-identical 45,607 rows**. FIRE_YEARS is now "
  "MEASURED from `__TABLES__`; 2023's NOT_RES coverage went **0 → 4,357**. ⚠ The incident LIST "
  "comes from `basicincident`, which was never short, so \"+33,039 rows\" was never going to "
  "become +33,039 signals — the row count and the signal count are different quantities",
  "⚠ `property_class` is used rather than `non_residential`: NOT_RES is stated on only 18,560 of "
  "45,607 rows and gating on it would silently drop 59% as if residential"),
 ("`D8_exit_intent`", "⭐ **WIRED 2026-08-22b. 0 → 2,511 reached, 434 admitted** — it had never "
  "placed a single parcel",
  "G163(a) built `in_si_rezoning_placed` from `in_si_up_indy_rezoning`: `stnum`+`stdir`+`stname` "
  "against Marion County parcels (FIPS 18097). 9,727 addressed cases, 3,222 on exactly one parcel, "
  "781 of those within 10 years. **9,614 carry a PETITIONER NAME** — an owner name, on a signal "
  "family five backlog rows are blocked on for want of one",
  "⛔ **THE DOCUMENTED REASON FOR SKIPPING IT WAS WRONG.** §5 of this file said the dates run "
  "1990–2008 and ranked it second on that basis. True of the 142-row REDUCTION only — the clip's "
  "`decision_date` runs to **2026-06-17**, with 1,039 cases in the 2020s. ⛔ And the first build "
  "attempt failed instructively: the column named **`geometry_geojson` is ESRI JSON** "
  "(`{{\"rings\":...}}`) **in State Plane FEET**, so it parses to NULL on all 13,414 rows. "
  "*100% carrying geometry* was true and useless",
  "⚠ Severity = decided within 10 years, so 1,099 older cases are carried low-severity rather "
  "than dropped. ⛔ **OPEN FOR THE OPERATOR (G163):** a filed petition is a STATED intent, which "
  "is the declared-intent (I-code) family, not the inferred-distress family D8 sits in"),
 ("`D6_bankruptcy`", "⛔ **REFUSED, and the refusal is the finding. Still 0 parcels, correctly**",
  "measured every column of `in_ustp_ch7_tfr`: `region`, `state`, `office`, `month_closed`, "
  "`year_closed`, `days_open` and **70+ dollar totals**",
  "⛔ **IT IS AGGREGATE DATA — trustee final-report statistics BY OFFICE AND MONTH. There is no "
  "debtor, no case, no address, and no property.** The 33 → 76,010 clip repair was correct and "
  "worth keeping (it had been keyed on `ch7_state_tax_paid`, a DOLLAR column), but the expectation "
  "that it would feed D6 was never achievable. ⚠ Both the handoff and this file listed it as one "
  "of three *\"cheapest wins… what is missing is a source block\"*. No source block can place a "
  "county-month financial total on a parcel",
  "⭐ Record as **wrong_grain** under G163 rather than leaving it as an unbuilt zero. "
  "`in_si_up_bankruptcy` (90 rows, case name + filing date) is a separate question: a case name is "
  "a debtor, not a parcel, and would need an owner-name bridge we do not have"),
]

# ⚠ HAND-WRITTEN, AND LABELLED AS SUCH: what each widened clip is FOR. Everything else is queried.
WHY = {s[3]: s[4] for s in SOURCES}
WHY.update({t: w for t, _, _, w in REPAIRS})
WHY.update({t: w for t, _, _, w in YEAR_GAPS})


def q(sql):
    return list(client.query(sql).result())


print("measuring the signal system …", flush=True)
cov = q(f"""SELECT signal, corpus_rows, parcels_reached, parcels_admitted, parcels_ci,
                   first_event, last_event, corpus_keying
            FROM `{DS}.in_si_signal_coverage` ORDER BY parcels_admitted DESC, signal""")
intent = q(f"""SELECT signal, COUNT(DISTINCT parcel_key) parcels, COUNT(*) events,
                      ANY_VALUE(so_what) so_what
               FROM `{DS}.in_si_intent_signals` GROUP BY 1 ORDER BY parcels DESC""")
flags = q(f"""SELECT COUNTIF(has_si_signal) flagged,
                     COUNTIF(has_intent_signal) intent_parcels,
                     COUNTIF(has_si_signal AND si_last_event_date IS NULL
                             AND si_next_event_date IS NULL) undated,
                     COUNTIF(has_si_signal AND si_last_event_date IS NULL
                             AND si_next_event_date IS NULL
                             AND (si_first_event_date IS NOT NULL OR si_events_dated > 0)) still_false,
                     COUNTIF(si_next_event_date IS NOT NULL) scheduled
              FROM `{DS}.in_si_sites_flags_v2`""")[0]

print("measuring the upstream clips …", flush=True)
clips = []
for target in list(WHY):
    try:
        tb = client.get_table(f"{DS}.{target}")
    except Exception:
        continue
    clips.append((target, tb.num_rows, len(tb.schema)))
clips.sort(key=lambda r: -r[1])

# ================================================================================================
# ⛔ WHICH CLIPS ACTUALLY FEED SOMETHING A READER SEES — AND THIS USED TO BE WRONG.
#
# It read the text of exactly THREE scripts (build_si_signal_v2 + build_si_cmbs_signals +
# build_si_intent_signals) and asked whether the clip's NAME appeared anywhere in them. ⚠ That is
# a FALSE-NEGATIVE GENERATOR, because most clips do not reach the spine directly — they go through
# a PLACEMENT table:
#     in_si_up_sri_taxsale   -> in_si_sri_placed        -> spine   (D1/D4)
#     in_si_up_ibtr_appeals  -> in_si_ibtr_placed       -> spine   (D26)
#     in_si_up_indy_code     -> in_si_indy_code_widened -> spine   (D12/D21)
#     in_sba_foia_loans      -> in_si_addr_placed       -> spine   (D14)
#     in_nfirs_fireincident_*-> in_nfirs_structure_fires-> in_si_addr_placed -> spine (D16)
# Every one of those read "not yet" while feeding a live signal. ⛔ AND THIS COLUMN IS THE G156
# WORKLIST, so the largest open row in the backlog has been overstated by an instrument defect.
#
# ⭐ THE FIX IS TO FOLLOW THE CHAIN, not to add two more filenames to a list. Scan EVERY build
# script; for each, record which clips it mentions and which tables it writes; then a clip counts
# as feeding a signal if the spine mentions it directly, or mentions a table written by a script
# that mentions the clip. Two hops covers every route in the estate today, and a third hop is
# reported rather than silently missed.
# ================================================================================================
SCRIPTS_DIR = os.path.join(REPO, "scripts")


def _code_only(src):
    """⛔ STRIP COMMENTS AND DOCSTRINGS BEFORE ASKING WHETHER A TABLE IS READ.

    The chain-following version of this check produced FALSE POSITIVES the moment it shipped:
    `in_ustp_ch7_tfr` and `in_si_up_iocs_court` both reported *feeds a signal* while reaching ZERO
    parcels — because the spine names them in a COMMENT explaining why they are REFUSED. ⚠ A text
    scan cannot tell *this table is read* from *this table is discussed*, and the more carefully
    the refusals are documented the more tables look wired. Prose is not a dependency.
    """
    out, i, n = [], 0, len(src)
    while i < n:                                  # drop triple-quoted blocks whole
        for q in ('"""', "'''"):
            if src.startswith(q, i):
                j = src.find(q, i + 3)
                i = (j + 3) if j != -1 else n
                break
        else:
            out.append(src[i])
            i += 1
    text = "".join(out)
    keep = []
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("#") or s.startswith("--"):
            continue                              # whole-line Python / SQL comment
        keep.append(line.split(" -- ")[0])        # trailing SQL comment on a code line
    return "\n".join(keep)


spine = _code_only(io.open(os.path.join(SCRIPTS_DIR, "build_si_signal_v2.py"),
                           encoding="utf-8").read())

_writes = re.compile(r"CREATE\s+OR\s+REPLACE\s+TABLE\s+`?\{?[A-Za-z_]*\}?[.`]*\.?(\w+)`?", re.I)
_builders = []
for _fn in sorted(os.listdir(SCRIPTS_DIR)):
    if _fn.startswith("build_") and _fn.endswith(".py") and _fn != "build_si_signal_v2.py":
        _raw = io.open(os.path.join(SCRIPTS_DIR, _fn), encoding="utf-8", errors="replace").read()
        _src = _code_only(_raw)
        _builders.append((_fn, _src, set(_writes.findall(_src))))


# ================================================================================================
# ⛔ THIS COLUMN WAS WRONG THREE TIMES IN ONE SESSION, AND THE THIRD TIME IS THE LESSON.
#
#   1. Original: scan the text of THREE scripts for the clip's name. FALSE NEGATIVES — most clips
#      reach the spine through a placement table, so SRI, IBTR and Indy code all read "not yet"
#      while feeding live signals. ⛔ This column IS the G156 worklist, so the backlog's largest
#      open row was overstated by an instrument defect.
#   2. Chain-following over every builder. FALSE POSITIVES — `in_ustp_ch7_tfr` reported *feeds a
#      signal* while reaching ZERO parcels, because the spine names it in a COMMENT explaining the
#      refusal. **The better the refusals are documented, the more tables look wired.**
#   3. Strip comments first. FALSE NEGATIVES AGAIN, everywhere — in this codebase the SQL LIVES
#      inside triple-quoted strings, so removing docstrings removed the dependencies themselves.
#
# ⭐ THE CONCLUSION IS THAT A SOURCE-TEXT SCAN CANNOT ANSWER THIS QUESTION AT ALL. Lineage is
# DECLARED below, one line per clip, and every declaration is VERIFIED against the warehouse: the
# named placement table must exist and hold rows, and the named signal must admit parcels. A
# declaration that stops being true FAILS rather than quietly flipping to "not yet".
#
# ⚠ AND DECLARING IT SURFACED THE FINDING THE SCAN NEVER COULD. Three placement builders read
# `in_si_refresh_*` tables, NOT G152's `in_si_up_*` full-width clips — two parallel families. The
# refresh tables carry MORE ROWS and FEWER COLUMNS, and the columns the full-width clips add are
# `_source_url`, `pulled_at`, `county_name`, `geoid`, `publisher_state`, `si_signal`:
# **provenance and housekeeping, not one signal-bearing field.** So for the three biggest clips,
# switching would gain nothing and LOSE rows (SRI -1,572, IBTR -81). See G156.
# ================================================================================================
LINEAGE = {
    # clip                          -> (placement/derived table, signal it feeds, note)
    "in_si_up_cmbs":                ("in_si_cmbs_placed", "D28_cmbs_loan_distress", "G152"),
    "in_si_up_indy_landbank":       ("in_si_intent_signals", "I3_land_bank", "G133"),
    "in_si_up_indy_rezoning":       ("in_si_rezoning_placed", "D8_exit_intent", "G163a"),
    "in_sba_foia_loans":            ("in_si_addr_placed", "D14_sba_chargeoff", "G156a"),
    "in_nfirs_fireincident_2020":   ("in_si_addr_placed", "D16_structure_fire", "G156a"),
    "in_nfirs_fireincident_2021":   ("in_si_addr_placed", "D16_structure_fire", "G156a"),
    "in_nfirs_fireincident_2022":   ("in_si_addr_placed", "D16_structure_fire", "G156a"),
    "in_nfirs_fireincident_2023":   ("in_si_addr_placed", "D16_structure_fire", "G156a"),
    "in_nfirs_fireincident_2024":   ("in_si_addr_placed", "D16_structure_fire", "G156a"),
    "in_si_up_seized_auction":      ("in_si_up_seized_auction", "D3_seized_auction", "G163b, inline"),
}
# ⚠ these three feed a signal, but through the `refresh` SIBLING rather than the full-width clip.
# Recorded separately so the doc can say so instead of scoring them either "yes" or "not yet".
SIBLING_FED = {
    "in_si_up_ibtr_appeals":  ("in_si_refresh_ibtr_appeals", "in_si_ibtr_placed",
                               "D26_assessment_appeal", "+`_source_url` only"),
    "in_si_up_sri_taxsale":   ("in_si_refresh_sri_taxsale_in", "in_si_sri_placed",
                               "D1_tax_sale", "+`pulled_at`/`source_url`/`state_code` only"),
    "in_si_up_indy_code":     ("in_si_refresh_indy_code_enforcement", "in_si_indy_code_widened",
                               "D12_code_violation",
                               "+`_source_url`/`county_name`/`geoid`/`publisher_state`/`si_signal` only"),
}
# ⚠ TWO FAMILIES, TWO TABLES. in_si_signal_coverage carries the 27 DISTRESS signals; the
# declared-intent family (I-codes) lives in in_si_intent_signals and is not in coverage at all.
# The first version of this verifier looked only at coverage and declared I3_land_bank's lineage
# FALSE — the guard was right to fail, but it was failing on the verifier, not on the lineage.
_admits = {r.signal: r.parcels_admitted for r in client.query(
    f"SELECT signal, parcels_admitted FROM `{DS}.in_si_signal_coverage`")}
_admits.update({r.signal: r.n for r in client.query(
    f"SELECT signal, COUNT(DISTINCT parcel_key) n FROM `{DS}.in_si_intent_signals` GROUP BY 1")})


def _rows(tbl):
    try:
        return client.get_table(f"{DS}.{tbl}").num_rows
    except Exception:
        return None


def feeds_a_signal(clip):
    """Declared lineage, VERIFIED. Returns (verdict, route). Raises if a declaration is false."""
    if clip in LINEAGE:
        tbl, sig, note = LINEAGE[clip]
        n, adm = _rows(tbl), _admits.get(sig, 0)
        if n is None or n == 0 or adm == 0:
            raise SystemExit(
                f"⛔ DECLARED LINEAGE IS FALSE: {clip} -> {tbl} -> {sig}. "
                f"{tbl} holds {n}, {sig} admits {adm}. Either the build broke or the declaration "
                f"is stale — fix one of them, do not let this column lie.")
        return "yes", f"→ `{tbl}` → **{sig}** ({adm:,} parcels, {note})"
    if clip in SIBLING_FED:
        sib, tbl, sig, delta = SIBLING_FED[clip]
        adm = _admits.get(sig, 0)
        return "sibling", (f"the signal is fed by **`{sib}`**, not by this clip → `{tbl}` → "
                           f"{sig} ({adm:,} parcels). This clip adds {delta}")
    return "no", ""


downstream = spine  # kept: some call sites still test membership directly

L = []
w = L.append
w("# SI SIGNALS — the whole system, measured")
w("")
w("<!-- GENERATED by scripts/build_si_signals_doc.py. ⛔ DO NOT HAND-EDIT — edit the generator.")
w("     Every figure is a live query. The NEXT STEPS section is judgement and says so. -->")
w("")
w(f"> Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC. ⛔ **Nothing here is hand-typed "
  f"except the \"what it buys\" column and the next steps.**")
w("")
w("⛔ **WHY THIS FILE IS GENERATED.** The account of the SI signals lived across sixteen backlog "
  "rows, three handoffs and a dozen docstrings — and the one file that summarised it, "
  "`docs/SIGNAL_REALITY.json`, went **five days without regenerating** while on the required "
  "reading list, still reporting `D19_warn` at 2 parcels. A hand-written summary of a system this "
  "size decays from the moment it is saved.")
w("")
w("---")
w("")
w("## 1. THE HEADLINE")
w("")
w("| | |")
w("|---|---:|")
w(f"| parcels carrying a DISTRESS signal | **{flags.flagged:,}** |")
w(f"| parcels carrying a DECLARED-INTENT signal | **{flags.intent_parcels:,}** |")
w(f"| parcels with a SCHEDULED future event | **{flags.scheduled:,}** |")
w(f"| parcels the UI reports as undated | {flags.undated:,} |")
w(f"| …of those, how many we actually hold a date for | **{flags.still_false}** |")
w("")
w("⭐ **That last row is G145.** Before the fix, 8,573 parcels printed *\"date unknown\"* over a "
  "date we held, because the rollup read the last event **on or before today** and a scheduled tax "
  "auction is in the future. The honest residue is now the row above it, and every one of those "
  "says *\"the publisher does not date this record\"* rather than blaming our records.")
w("")
w("---")
w("")
w("## 2. EVERY DISTRESS SIGNAL — held → reached → admitted")
w("")
w("⚠ **A large drop is not a defect if it is stated.** We filter deliberately: C&I only, severity "
  "gates, 3+ violations. `scripts/audit_signal_display.py` fails only where a signal places far "
  "below what we hold **with no recorded reason**, and it currently reports zero.")
w("")
w("| signal | held | reached | admitted | C/I | date range |")
w("|---|---:|---:|---:|---:|---|")
for r in cov:
    rng = (f"{r.first_event} → {r.last_event}" if (r.first_event or r.last_event)
           else "the publisher dates none of these")
    held = f"{r.corpus_rows:,}" if r.corpus_rows is not None else "—"
    w(f"| `{r.signal}` | {held} | {r.parcels_reached:,} | **{r.parcels_admitted:,}** "
      f"| {r.parcels_ci:,} | {rng} |")
w("")
w("## 3. THE DECLARED-INTENT FAMILY — willingness STATED, not inferred")
w("")
w("⭐ Every D-code above INFERS willingness from distress. These REVEAL it, so they are counted "
  "separately and never folded into the flagged count.")
w("")
w("| signal | parcels | events | what it means |")
w("|---|---:|---:|---|")
for r in intent:
    w(f"| `{r.signal}` | **{r.parcels:,}** | {r.events:,} | {(r.so_what or '').strip()} |")
w("")
w("---")
w("")
w("## 4. THE FULL-WIDTH UPSTREAM CLIPS (G152)")
w("")
w("⛔ **THE PROBLEM THEY SOLVE.** `energy.si_signals` is **97,240,585 rows normalised to 13 "
  "columns**. Our clip of it was complete — 13 of 13 — so a column audit passed **on a reduction**. "
  "Everything the 19 upstream sources carry beyond those 13 was discarded before it reached us.")
w("")
w("⭐ **Operator ruling, 2026-08-21:** *\"Even if a source scrapes everything but one column, we "
  "still want to rescrape it for everything because that one field may contain something "
  "materially important.\"* So every source is clipped at FULL WIDTH with `SELECT *`, and the "
  "column count is asserted equal to the parent's at build time.")
w("")
w("| clip | rows | cols | feeds a signal? | what it buys |")
w("|---|---:|---:|:--:|---|")
for target, rows, cols in clips:
    _v, _route = feeds_a_signal(target)
    # ⭐ THREE STATES, NOT TWO. "sibling" is the case a yes/no column cannot express and
    # the one that was silently mis-scored: the source DOES feed a signal, through a
    # narrower sibling table, and this clip would add only provenance.
    feeds = {"yes": "⭐ yes", "sibling": "⚠ via sibling", "no": "not yet"}[_v]
    if _route:
        WHY[target] = (WHY.get(target, "") + f" **{_route}**").strip()
    why = WHY.get(target, "").replace("\n", " ").strip()
    if len(why) > 300:
        why = why[:297] + "…"
    w(f"| `{target}` | {rows:,} | {cols} | {feeds} | {why} |")
w("")
w(f"**{len(clips)} clips · {sum(r for _, r, _ in clips):,} Indiana rows held at full width.** "
  f"Guarded by `scripts/audit_si_upstream_width.py`, which is a checkpoint check.")
w("")
w("---")
w("")
w("## 4b. ⚠ WHAT WE DID TO EACH SIGNAL, HOW, AND WHY — HAND-WRITTEN, 2026-08-21/22")
w("")
w("⛔ **This section is a CHANGE LOG and cannot be generated** — the warehouse knows its current "
  "state, not its history or the reasoning. Everything above is measured; this is written.")
w("")
w("| signal | what we did | how | why | what is still outstanding |")
w("|---|---|---|---|---|")
for row in CHANGE_LOG:
    w("| " + " | ".join(row) + " |")
w("")
w("⛔ **THE THREE ROWS MARKED *not wired* ARE THE UNCOMFORTABLE PART.** We repaired those clips "
  "and the repairs are real — `in_sba_foia_loans` went from 5,135 rows to 39,948, the NFIRS "
  "fire-incident years recovered 33,039 rows, `in_ustp_ch7_tfr` went from 33 rows (none of them "
  "Indiana) to 76,010. **None of it reached a signal**, because D14, D16 and D6 are fed by the "
  "13-column `si_signals` corpus and not by these clips. ⚠ That is the standing rule biting: *the "
  "warehouse improves and no reader sees it.* It is **G156**, and these three are the sharpest "
  "instances of it because the better data is already sitting in `indiana_app`.")
w("")
w("---")
w("")
w("## 5. ⚠ NEXT STEPS — THIS SECTION IS JUDGEMENT, NOT MEASUREMENT")
w("")
w("⭐ **G156 is the largest open row, and the table above shows why:** most clips read *not yet* "
  "in the \"feeds a signal\" column. G152 widened them; four have now been turned into signals — "
  "CMBS (D28/D29), the Indianapolis land bank (I3), SBA + NFIRS (D14/D16, G156a) and the Indy "
  "rezoning layer (D8, G163a).")
w("")
w("⛔ **AND THE FIRST THING TO CARRY FORWARD IS THAT THIS SECTION WAS WRONG TWICE, 2026-08-22b.** "
  "Both errors were the same shape — *a property of a column asserted from its NAME rather than "
  "measured*:")
w("")
w("- It ranked `in_si_up_indy_rezoning` second and parked it on *\"dates run 1990–2008, so AGE is "
  "the open question\"*. **That is true only of the 142-row corpus REDUCTION.** The clip's own "
  "`decision_date` runs to **2026-06-17**, with 1,039 cases in the 2020s. D8 was built and now "
  "admits **434 parcels** where it admitted none.")
w("- It called that layer **100% carrying geometry**. True, and useless: the column named "
  "`geometry_geojson` holds **Esri JSON in Indiana State Plane FEET**, so `ST_GEOGFROMGEOJSON` "
  "returns NULL on all 13,414 rows. Placement went by address instead.")
w("")
w("1. ⭐ **`in_si_up_ibtr_appeals` is still first, and G162 sharpens why.** 10,071 rows, **100% "
  "carrying `stateParcelNumber`, `locationAddress` AND `petitionerName`** — a direct publisher "
  "key and an **owner name**, the thing G70, G71, G104, G90(b) and G147 are all blocked on. "
  "⛔ `in_si_ibtr_placed` currently holds **5,438 of those 10,071 (54.0%)** and **no rule is "
  "recorded for the missing 46%** — on a source where the key is direct, that is a failure until "
  "proven otherwise. It also carries `attachments`, per-record documents for G153.")
w("2. **`in_si_up_indy_taxsale`** — 62,368 Marion parcels with `deltaxpen`, `delsatax` and "
  "`minimumbid`: the DOLLAR SIZE of a delinquency that D1/D4 carry only as a flag. ⭐ Promoted "
  "above brownfield because D14 and D16 both proved the same point this session — the value of a "
  "full-width clip is usually the AMOUNT and the ADDRESS it adds, not extra rows.")
w("3. **`in_si_up_brownfield`** — EPA has already computed `ssdist`, `ssvoltage`, `transdist`, "
  "`tlkv` and `raildist` for 1,483 Indiana sites. Not a new signal: a cross-check on our own G29 "
  "distances, and possibly better ones.")
w("4. ⛔ **`in_si_up_sri_taxsale` needs a rule, not a build.** `in_si_sri_placed` holds 31,228 of "
  "81,975 (38.1%). Like IBTR, the shortfall may be correct — but nothing says so. G162.")
w("")
w("⛔ **ASSESS BEFORE BUILDING.** Each needs its own D-code, an admission rule and a written "
  "\"so what\" — and a source that cannot earn one is a refusal to record, not a signal to ship. "
  "That is the governing principle applied as a veto, which is how it is meant to be used.")
w("")
w("⚠ **AND TWO THINGS THAT ARE NOT NEXT STEPS, because they were measured and closed:**")
w("- **WARN cannot be improved by scraping.** The address exists only inside the filing PDF, and "
  "most Indiana notices have no PDF. The 363-column multi-state `warn_notices` union has **every "
  "address column NULL on all 1,220 Indiana rows**.")
w("- **Owner name and assessed value are not hiding in the SI corpus.** "
  "`energy.si_d5_vacancy_derived` carries `parcel_owner`, `assessed_value`, `land_use`, `zoning` "
  "and `year_built` columns that are **100% NULL on all 967,366 Indiana rows**. The DLGF Gateway "
  "purchase is the only route.")
w("")

io.open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
print(f"\n  docs/SI_SIGNALS.md written ({len(L)} lines)")
print(f"  {len(cov)} distress signals · {len(intent)} declared-intent · {len(clips)} full-width clips")
print("\nDONE")
