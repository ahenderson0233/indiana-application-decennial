# RTO directions and the request-size ladder

Injection vs withdrawal headroom for Indiana, across MISO and PJM, and what happens to each
when you change the size of the request.

Everything below was measured against BigQuery or a live publisher endpoint. Nothing is
estimated, and no proxy stands in for a direction we could not acquire.

---

## The headline, and it corrects the brief

> **Headroom is NOT a function of the request size — in either RTO.**
> A bigger ask does not shrink the published headroom. Both tools publish a
> request-INVARIANT headroom number plus request-DEPENDENT impact columns, and we
> proved it separately for each RTO.

The premise behind the ladder — *"a bus with 800 MW available to a 100 MW request may have far
less available to a 1,000 MW request"* — is **measurably false** for both publishers. What
actually changes with the ask is whether your project *fits* inside a fixed headroom, and that
is a comparison, not a re-scrape.

This matters in the operator's favour: it means one harvest per direction answers **every**
rung, and the ~22 hours of additional PJM scraping the full 6x2x2 grid would have required
buys literally zero new information in the headroom column.

### PJM — proven by re-running the same 25 buses at six sizes

Same 25 AEP buses, case 4, INJECTION, at 100 / 300 / 500 / 1000 / 2500 / 5000 MW.
Deduped 1:1 on (bus, facility, contingency) against the 100 MW rung:

| rung | rows compared | `available_mw` identical | `dfax` identical | `pre_loading_pct` identical | `impact_mw` identical | max delta in `available_mw` | `impact_mw` ratio vs 100 |
|---|---|---|---|---|---|---|---|
| 300 | 7,950 | **7,950** | 7,950 | 7,950 | 0 | **0.0** | 3.0 |
| 500 | 7,950 | **7,950** | 7,950 | 7,950 | 0 | **0.0** | 5.0 |
| 1000 | 7,950 | **7,950** | 7,950 | 7,950 | 0 | **0.0** | 10.0 |
| 2500 | 7,950 | **7,950** | 7,950 | 7,950 | 0 | **0.0** | 25.0 |
| 5000 | 7,950 | **7,950** | 7,950 | 7,950 | 0 | **0.0** | 50.0 |

`available_mw` is byte-identical at every size. `impact_mw` scales *exactly* linearly with the
ask. So `available_mw` **is** the headroom; `desired_mw` only sets how much of it you consume.

Bus-level headroom is unchanged across the whole ladder (avg 76.44 MW, min 19.0, max 307.0,
97 pre-existing overloads at every rung) — but the number of buses that **fit** the ask falls,
which is the real siting signal:

| request | buses that fit (of 25 probed) |
|---|---|
| 100 MW | 6 |
| 300 MW | 1 |
| 500 MW and above | 0 |

**No cap.** PJM accepted a 5,000 MW request without complaint.

### MISO — proven twice, including against data we already held

MISO's `pMaxValue` is a **reporting clamp**, not a study input:

```
PMax(pMaxValue = X)  ==  min(PMax_true, X)
```

1. **Live, one POI, facility by facility:** holds for **67/67** facilities at X=100 and X=300,
   zero violations. A *negative* `pMaxValue` floors at 0 — it does not model withdrawal.
2. **At scale, on two independent harvests we already hold:** `in_miso_poi_300mw`
   (`pMaxValue=300`) vs the Indiana subset of `energy.miso_poi_monitored_facilities`
   (`pMaxValue=99999`) — **38,381 of 38,381** distinct (POI, facility) keys satisfy the
   identity, **zero violations**. Unclamped values reach 80,752 MW.

> **Dedupe trap:** both sources carry an identical 1.042 duplicate-key factor. Joining without
> `MIN` per key manufactures 2,124 phantom disagreements that are pure join fanout. The first
> run of this check reported "2,124 violations, max deviation 300.0" and was wrong.

The publisher's own harvest metadata agrees, and had recorded this before us:

```
_invariant_columns       = ['mw_available','percent_dfax','percent_loading_before','derived_rating_mva']
_probe_dependent_columns = ['mw_impact','percent_impact','percent_loading_after']
_grain = "one row per (POI, monitored facility); mw_available is the injection MW that
          loads that facility to 100%, floored at 0"
```

Note the structural symmetry with PJM: in both RTOs the *available/headroom* column is
invariant and the *impact/post-loading* columns are probe-dependent.

---

## Request-size ladder

Rungs requested: 100, 300, 500, 1000, 2500, 5000 MW.

| RTO | direction | 100 | 300 | 500 | 1000 | 2500 | 5000 | how |
|---|---|---|---|---|---|---|---|---|
| **PJM** | **injection** | **LANDED** | **LANDED** | **LANDED** | **LANDED** | **LANDED** | **LANDED** | harvested at all six sizes for 25 AEP buses — that is what proves the invariance. The AEP footprint is being harvested at 100 MW, which by that proof **is** the headroom at every size; see the footprint caveat under Deliverable 1 |
| **PJM** | withdrawal | **HELD** | **VERIFIED** | derivable | derivable | derivable | derivable | already held as `in_pjm_queuescope_aep` (303,671 rows @ 100 MW). Invariance **measured in this direction too** — see below |
| **MISO** | **injection** | **LANDED** | **LANDED** | **LANDED** | **LANDED** | **LANDED** | **LANDED** | all six rungs materialised in `in_miso_poi_ladder` from one unbounded read via the clamp identity, verified 38,381/38,381 |
| **MISO** | withdrawal | **BLOCKED** | **BLOCKED** | **BLOCKED** | **BLOCKED** | **BLOCKED** | **BLOCKED** | MISO publishes no load/withdrawal direction at all — see below. The rung is irrelevant when the direction does not exist |

**No publisher capped the request size.** PJM accepted 5,000 MW; MISO accepts 99,999.

**Why no cell needed a 6x harvest:** because headroom is request-invariant in both RTOs, a
rung is a *comparison against* the harvested number (`headroom >= request`), not a separate
pull. Both ladder surfaces expose that comparison directly as `request_fits`.

### The withdrawal direction was measured too, not just argued

The six-rung proof above ran in INJECTION. Rather than *infer* that withdrawal behaves the same
way, it was measured directly — one batch at 300 MW compared against the same 25 buses in the
held 100 MW harvest:

```bash
python scripts/pull_pjm_injection.py --owner 739 --mode WITHDRAWAL --mw 300 \
       --max-batches 1 --table in_pjm_qs_withdrawal_rungcheck
```

| | result |
|---|---|
| rows compared (deduped 1:1) | 4,686 |
| `available_mw` identical | **4,686 / 4,686** |
| `dfax`, `pre_loading_pct` identical | 4,686 / 4,686 |
| `impact_mw` identical | 0 (ratio exactly **3.0**) |
| max delta in `available_mw` | **0.0** |
| bus headroom identical | **25 / 25** buses (avg 71.28 MW at both rungs) |

So the invariance is a property of the *tool*, not of one direction. Diagnostic table:
`in_pjm_qs_withdrawal_rungcheck` (4,686 rows) — kept as the evidence, not a production surface.

---

## Deliverable 1 — PJM INJECTION: **LANDED (direction acquired; footprint still filling)**

> **Read the footprint number before using this.** The INJECTION direction is acquired,
> proven, rolled up and registered — that part is done. The *coverage* of AEP's 1,524 POI buses
> is whatever the harvest has reached, because a full owner is a multi-hour sequential job.
>
> **`_registry.notes` for `in_pjm_queuescope_injection` and `in_pjm_bus_injection` carries a
> live `FOOTPRINT COMPLETE` / `FOOTPRINT PARTIAL - HARVEST INCOMPLETE: n of 1,524 (x%)` stamp**,
> written from a `COUNT(DISTINCT bus_number)` at registration time. Trust that stamp over any
> number written in prose here, including this document. To advance it, re-run the harvest
> command below and then `register_rto_directions.py`; it resumes from checkpoint and re-runs
> only the batches that never landed.

| | |
|---|---|
| **Raw table** | `energy-platfrom.indiana_app.in_pjm_queuescope_injection` |
| **Rollup** | `energy-platfrom.indiana_app.in_pjm_bus_injection` |
| **Ladder view** | `energy-platfrom.indiana_app.vw_pjm_bus_injection_ladder` |
| **Direction** | INJECTION (the counterpart to the withdrawal we already held) |
| **Observed vintage** | `2027 RTEP Base Case (Summer Peak)` — the publisher's own study-case label. PJM publishes no separate file date on this tool. |
| **Endpoint** | `https://queuescope.pjm.com/queuescope/pages/public/evaluator.jsf` — `endpoint_kind=html_page` (JSF/PrimeFaces, browser automation; no REST, and the XLSX export is `ui-state-disabled` for Guest) |
| **Slice** | `case_id=4`, `owner_id=739` (AEP / Indiana Michigan Power), `operating_mode=INJECTION`, `desired_mw` carried as a column |

**Re-run:**

```bash
python scripts/pull_pjm_injection.py --owner 739 --mw 100          # full AEP footprint
python scripts/pull_pjm_injection.py --owner 739 --mw 300 --max-batches 1   # a ladder rung
python scripts/build_pjm_injection_rollup.py                        # per-bus rollup + ladder view
python scripts/register_rto_directions.py                           # refresh _registry
```

Resume-safe: checkpointed per `(case, mode, mw, owner, batch)` under
`data/_ckpt_pjm_queuescope_injection/`. **Run sequentially — never two QueueScope instances at
once.** ~2 minutes per 25-bus batch; the 1,524-bus AEP footprint is ~61 batches.

**How it was built without touching `ingest/`:** `energy-platform/ingest/load_pjm_queuescope_bq.py`
already encodes eight hard-won facts about QueueScope's flow, but it hardcodes
`DATASET="energy"`, which is read-only for this workstream. `scripts/pull_pjm_injection.py`
imports it and rebinds `DATASET`/`TABLE`/`CKPT`; `main()` resolves the sink at call time, so the
rebinding takes. The wrapper asserts the loader's sink is still what it expects and refuses to
run if that changed underneath it. **`ingest/` is not edited.**

**Rollup logic** — copied verbatim from `scripts/build_pjm_withdrawal.py` so the directions are
comparable: `MIN(available_mw)` per bus where `ABS(dfax) >= 0.05` and `pre_loading_pct < 100`.
Pre-existing overloads are **excluded and counted** in `existing_overloads`, never silently
dropped. The 5% DFax screen is *our* convention, not PJM's.

**PJM's own caveats ride along:** thermal impacts **only** (no voltage, stability or
short-circuit), and *"results are not reflective of current PJM system conditions"*.

### A defect found in the data we already held

Mid-investigation I asserted that "AEP offers 1,524 POI buses in INJECTION but 1,475 in
WITHDRAWAL, so the bus lists differ by direction." **That was wrong, and measuring it is how it
got caught.** When the withdrawal probe ran, QueueScope reported `owner AEP (739) - 1,524 buses`
in WITHDRAWAL mode as well.

The POI list is **1,524 buses in both directions.** So:

> **`in_pjm_queuescope_aep` (and therefore `in_pjm_bus_withdrawal`, 1,475 buses) is an
> INCOMPLETE harvest — it is missing 49 of AEP's 1,524 POI buses, about 3.2%.**

That is a gap in previously-landed data, not a property of the withdrawal direction. Those 49
buses are silently absent from every withdrawal answer the application gives today. Re-running
the withdrawal harvest would close it; the loader is checkpointed per batch, so it would only
re-do the batches that never landed.

Two consequences for anything joining the directions: the injection and withdrawal tables are
still **not** guaranteed 1:1 today (because of this gap, not by design), so use an outer join
and surface the asymmetry rather than dropping rows.

---

## Deliverable 2 — MISO WITHDRAWAL: **BLOCKED**

MISO publishes **no bus-level load/withdrawal headroom product**. Recorded as BLOCKED, with no
proxy and no derivation from injection.

### The wall, quoted verbatim

MISO's own **Large Load Interconnection Reliability Requirements** page (initiative
`LLWG-2026-3`, status **Active**, next update **Q3 2026**):

> "Existing Tariff provisions and Business Practices do not provide a consistent or transparent
> framework to evaluate the reliability impacts associated with these emerging load types."

> "Transmission Owners, Load-Serving Entities, and interconnection customers face uncertainty
> regarding applicable criteria, study assumptions, data requirements, and post-interconnection
> obligations."

> "MISO proposes to work with stakeholders through the established stakeholder process to
> develop a clear and consistent Large Load Reliability Requirements Framework."

> "The solution will define which new load additions require enhanced reliability review and
> identify the minimum criteria needed to reliably integrate those loads into the MISO
> transmission system."

The framework that would *produce* a load-direction answer is still being **designed**. There is
nothing to harvest yet, publicly or otherwise.

And MISO's own description of the only bus-level tool it does publish
(knowledge-base article KA-01166) scopes it to the generator side:

> "The MISO Points of Interconnection (POI) tool helps Interconnection Customers pre-screen for
> potential constraints associated with existing POIs."

### What we measured ourselves, so this is not taken on trust

Against `https://giqueue.misoenergy.org/POI/api/poi_mf`:

| probe | result |
|---|---|
| `pMaxValue=-300`, `-100` (a negative injection would be a withdrawal) | 200 OK, **every `PMax` returns 0.0** — the API floors at zero; it does not model withdrawal |
| `&direction=WITHDRAWAL`, `&type=LOAD`, `&studyType=LOAD`, `&transferType=WITHDRAWAL`, `&isLoad=true`, `&loadFlag=true`, `&dcType=LOAD`, `&pMinValue=300` | all 200 OK with **byte-identical output** (67 rows, max 300.000) — every candidate direction parameter is silently ignored |
| endpoint enumeration | only `/POI/api/pois` and `/POI/api/poi_mf` exist. `/POI/api/poi_lf`, `/POI/api/poi_load`, `/POI/api/swagger` all **404** |
| the payload's own semantics | `mw_available` is *"the **injection** MW that loads that facility to 100%, floored at 0"* |

**No wall was worked around.** No CAPTCHA, no UA spoofing, no account, no paywall. Parameter
exploration on a public REST endpoint is the only technique used, and it returned a clean
negative.

### Why we did not substitute anything

Injection headroom is **not** a weaker form of withdrawal headroom — it is the answer to a
different question. Generation injection pushes power onto the network; load withdrawal pulls
it off. They stress different facilities in different directions, and the binding constraint is
frequently not the same one.

**This is now measured, not asserted.** PJM is the one RTO where we hold *both* directions for
the same buses, which makes it the control experiment for whether one may ever stand in for the
other. Across the AEP buses harvested in both directions:

| | at 150 buses | at 200 buses |
|---|---|---|
| average INJECTION headroom | 107.98 MW | 106.71 MW |
| average WITHDRAWAL headroom | 73.19 MW | 68.35 MW |
| buses where injection > withdrawal | 95 | 129 |
| buses where withdrawal > injection | 55 | 71 |
| **buses where the two are equal** | **0** | **0** |

(Two snapshots as the injection harvest advanced — rerun
`scripts/build_pjm_injection_rollup.py` for the current figure.)

The two directions disagree on **every single bus**, and neither dominates — injection is
larger on roughly two thirds and smaller on the rest. There is no offset, no ratio, and no
conservative direction to round toward. Any attempt to derive one from the other would be
wrong on 100% of buses, in an unpredictable direction and by an unpredictable amount.

Presenting injection as if it were withdrawal would therefore corrupt every siting answer in
the majority of Indiana that sits in MISO. The cell stays empty.

### Where a withdrawal answer will eventually come from

Not a recommendation to act on now, just the watch-list: the `LLWG-2026-3` framework (next
update Q3 2026), the **Firm Service Step Up** process — *"MISO is proposing a new process to
enable large load interconnection customers to obtain firm service at reduced levels prior to
the completion of necessary infrastructure improvements"* — and MTEP models. None of these is a
public bus-level dataset **today**.

---

## Tables landed

Row counts are live from BigQuery. Every table has exactly one `_registry` row carrying the
parameterised endpoint, the endpoint kind, a literal `RE-SCRAPE COMMAND:`, the slice
parameters, the observed vintage, and what was excluded and why.

| table | grain | direction | request_mw | rows | re-run |
|---|---|---|---|---|---|
| `in_pjm_queuescope_injection` | bus x facility x contingency x request | INJECTION | 100 (full AEP) + 300/500/1000/2500/5000 (25-bus ladder) | see `_registry` | `python scripts/pull_pjm_injection.py --owner 739 --mw 100` |
| `in_pjm_bus_injection` | bus | INJECTION | 100 (invariant) | see `_registry` | `python scripts/build_pjm_injection_rollup.py` |
| `vw_pjm_bus_injection_ladder` | bus x request | INJECTION | 100/300/500/1000/2500/5000 | VIEW | rebuilt by the rollup script |
| `in_miso_poi_ladder` | POI x facility x request | INJECTION | 100/300/500/1000/2500/5000 | 230,286 | `python scripts/build_miso_injection_ladder.py` |
| `in_bus_headroom_miso_ladder` | POI x request | INJECTION | 100/300/500/1000/2500/5000 | 3,852 | `python scripts/build_miso_injection_ladder.py` |

`in_miso_poi_ladder` labels every row with `_rung_provenance`, so a derived rung can never be
mistaken for an independently harvested one.

> **Count `in_pjm_queuescope_injection` with `COUNT(*)`, never with metadata.** It is populated
> by `insert_rows_json`, so rows sit in the streaming buffer and
> `energy.__TABLES__.row_count` / `get_table().num_rows` read **0** for a table that is
> demonstrably full. This is the same trap as `num_rows` being 0 for every VIEW — metadata is
> not emptiness.

### The MISO injection result is worth reading before wiring any page

**641 of 642 Indiana MISO POIs read ZERO injection headroom at every rung, including 100 MW.**
Exactly one POI is non-zero — `J1724 POI 138`, true headroom **815.34 MW** across 2 monitored
facilities — so it fits a 100, 300 or 500 MW ask and fails at 1,000 MW and above.

The ladder does not rescue Indiana MISO injection — it confirms the constraint is **structural**
rather than an artifact of the original 300 MW probe, which is precisely what the ladder was
commissioned to find out. Zero-headroom POIs are **retained**, not filtered: a zero meaning
*"a monitored facility is already at its rating"* is a real answer and must never be collapsed
with *"not evaluated"*. `facilities_at_zero` is carried per POI so the two stay distinguishable.

---

## Scope note: what is deliberately NOT here

- **Wider PJM injection beyond AEP.** The brief made it a bonus, not a requirement. Each
  additional transmission owner is a multi-hour sequential harvest (DVP alone is 1,046 buses).
- **PJM withdrawal at additional rungs.** Not harvested, because the invariance proof makes it
  redundant — the held 100 MW harvest already answers every rung.
- **Any MISO withdrawal number, of any kind.** Blocked, and left blocked.
