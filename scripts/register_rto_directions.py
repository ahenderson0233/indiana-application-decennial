"""Rich, re-runnable `_registry` rows for every table in the RTO-direction workstream.

The estate's rule: `_registry` alone must answer "where did this come from and how do I
refresh it", without asking the session that built it.  So every row below carries the full
parameterised endpoint, the endpoint TYPE, a literal `RE-SCRAPE COMMAND:`, the request
parameters that define the slice (RTO, direction, request MW), the OBSERVED publisher
vintage (never a pull timestamp), the live row count, and what was excluded and why.

Idempotent: DELETE-then-INSERT per table, row counts re-measured live from BigQuery.
Skips any table that does not exist yet rather than inventing a row for it.

    python scripts/register_rto_directions.py
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

QS_URL = ("https://queuescope.pjm.com/queuescope/pages/public/evaluator.jsf"
          "  [form params: selStudyCase=4 (2027 RTEP Base Case, Summer Peak); "
          "selBusArea=739 (AEP); selOperatingMode=INJECTION; desiredMW=<request_mw>; "
          "availablePoiBuses paged 25 POIs per submission]")
MISO_URL = ("https://giqueue.misoenergy.org/POI/api/poi_mf"
            "?poiName={poi_name}&pMaxValue=99999   [paging: one GET per POI; "
            "642 Indiana POIs enumerated from indiana_app.in_bus_headroom_miso "
            "WHERE location_status='indiana']")

ROWS = [
    dict(
        table="in_pjm_queuescope_injection",
        source=f"PJM Queue Scope | endpoint_kind=html_page (JSF/PrimeFaces, browser "
               f"automation; no REST, no export affordance for Guest) | {QS_URL}",
        method=(
            "RE-SCRAPE COMMAND: python scripts/pull_pjm_injection.py --owner 739 --mw 100"
            "   (rungs: --mw 300|500|1000|2500|5000; validate first with --max-batches 1; "
            "resume-safe, checkpointed per (case,mode,mw,owner,batch) under "
            "data/_ckpt_pjm_queuescope_injection/) "
            "|| RTO=PJM; direction=INJECTION; request param desired_mw (carried as a COLUMN); "
            "case_id=4; owner_id=739 (AEP/Indiana Michigan Power). "
            "|| The loader is energy-platform/ingest/load_pjm_queuescope_bq.py, imported and "
            "monkeypatched (DATASET->indiana_app) by the wrapper; ingest/ is NOT edited. "
            "RUN SEQUENTIALLY - never two QueueScope instances at once."),
        notes=(
            "PJM INJECTION, the counterpart to in_pjm_queuescope_aep (WITHDRAWAL). "
            "OBSERVED VINTAGE (publisher payload, not pull time): case_label = "
            "'2027 RTEP Base Case (Summer Peak)'. "
            "|| MEASURED, CONTRADICTS THE REQUEST-SIZE PREMISE: available_mw is INVARIANT to "
            "desired_mw. Same 25 AEP buses at 100/300/500/1000/2500/5000 MW give byte-identical "
            "available_mw (7,950/7,950 rows per rung, max delta 0.0), identical dfax and "
            "pre_loading_pct; only impact_mw and post_loading_pct move, and impact_mw scales "
            "EXACTLY linearly (ratio 3.0/5.0/10.0/25.0/50.0 vs the 100 MW rung). available_mw IS "
            "the headroom; desired_mw only sets how much of it you consume. One rung therefore "
            "answers every rung. No cap: PJM accepted 5000 MW. "
            "|| EXCLUSIONS: none at raw grain - every constraint row PJM returned is kept, "
            "including pre-existing overloads, which are filtered (and counted) only at rollup. "
            "|| PJM's own caveats: thermal impacts ONLY (no voltage/stability/short-circuit) and "
            "'results are not reflective of current PJM system conditions'. "
            "|| AEP offers 1,524 POI buses in INJECTION vs 1,475 in WITHDRAWAL - the bus lists "
            "differ by direction, so the two tables are NOT a 1:1 bus join."),
    ),
    dict(
        table="in_pjm_bus_injection",
        source=f"rollup of indiana_app.in_pjm_queuescope_injection | endpoint_kind=bq_clip | "
               f"upstream {QS_URL}",
        method=(
            "RE-SCRAPE COMMAND: python scripts/build_pjm_injection_rollup.py"
            "   (rebuilds from in_pjm_queuescope_injection; re-harvest that first with "
            "python scripts/pull_pjm_injection.py --owner 739 --mw 100) "
            "|| RTO=PJM; direction=INJECTION; request_mw=100; case_id=4; owner_id=739. "
            "|| MIN(available_mw) per bus over materially-affected facilities."),
        notes=(
            "Per-bus PJM INJECTION headroom. Rollup logic COPIED from "
            "scripts/build_pjm_withdrawal.py so the two directions are directly comparable: "
            "MIN(available_mw) per bus WHERE ABS(dfax)>=0.05 AND pre_loading_pct<100. "
            "|| EXCLUDED AND WHY: (a) facilities with ABS(dfax)<0.05 - a new resource barely "
            "moves them, so they are not a real limit; the 5% screen is OUR convention, not "
            "PJM's. (b) facilities already at pre_loading_pct>=100 - a pre-existing violation is "
            "not headroom the new project consumes; these are COUNTED per bus in "
            "existing_overloads rather than silently dropped. "
            "|| OBSERVED VINTAGE: 2027 RTEP Base Case (Summer Peak). "
            "|| request_mw=100 is not a limitation: available_mw is request-invariant (proven "
            "across 6 rungs, max delta 0.0), so this single number is the headroom at ANY ask. "
            "To ask 'does a 500 MW load fit', compare injection_mw >= 500 - do NOT re-harvest."),
    ),
    dict(
        table="in_pjm_qs_withdrawal_rungcheck",
        source=f"PJM Queue Scope | endpoint_kind=html_page | {QS_URL.replace('INJECTION', 'WITHDRAWAL')}",
        method=(
            "RE-SCRAPE COMMAND: python scripts/pull_pjm_injection.py --owner 739 "
            "--mode WITHDRAWAL --mw 300 --max-batches 1 "
            "--table in_pjm_qs_withdrawal_rungcheck "
            "|| RTO=PJM; direction=WITHDRAWAL; request_mw=300; case_id=4; owner_id=739; "
            "one 25-bus batch only."),
        notes=(
            "DIAGNOSTIC, NOT A PRODUCTION SURFACE. Exists to answer one question: is PJM's "
            "available_mw request-invariant in the WITHDRAWAL direction too, or only in "
            "INJECTION where we proved it across six rungs? "
            "|| ANSWER, MEASURED: invariant. Against the same 25 buses in the held 100 MW "
            "harvest (in_pjm_queuescope_aep), deduped 1:1 -- available_mw identical on "
            "4,686/4,686 rows (max delta 0.0), dfax and pre_loading_pct identical, impact_mw "
            "identical on 0 rows with a ratio of exactly 3.0, and bus-level headroom identical "
            "for 25/25 buses (avg 71.28 MW at both rungs). The invariance is a property of the "
            "TOOL, not of one direction. "
            "|| INCIDENTAL DEFECT FOUND: running this proved QueueScope offers 1,524 AEP POI "
            "buses in WITHDRAWAL mode, the same as INJECTION. in_pjm_queuescope_aep holds only "
            "1,475 -- so that harvest is INCOMPLETE by 49 buses (3.2%), which had been "
            "mistaken for a direction difference. See docs/RTO_DIRECTIONS.md. "
            "|| OBSERVED VINTAGE: 2027 RTEP Base Case (Summer Peak)."),
    ),
    dict(
        table="in_miso_poi_ladder",
        source=f"MISO giqueue POI transfer analysis | endpoint_kind=json_api | {MISO_URL} "
               f"|| materialised in this repo from the read-only clip "
               f"energy.miso_poi_monitored_facilities (pMaxValue=99999 harvest)",
        method=(
            "RE-SCRAPE COMMAND: python scripts/build_miso_injection_ladder.py"
            "   (derives all rungs from the unbounded read; to re-pull MISO itself: "
            "python scrapers/lane_a/pull_miso_poi_300mw.py with PMAX edited, or GET "
            "https://giqueue.misoenergy.org/POI/api/poi_mf?poiName=<POI>&pMaxValue=99999 "
            "per POI at >=1.15s throttle with an identifying User-Agent) "
            "|| RTO=MISO; direction=INJECTION; request param pMaxValue, carried as the COLUMN "
            "request_mw with rungs 100/300/500/1000/2500/5000."),
        notes=(
            "MISO INJECTION request-size ladder, Indiana POIs, facility grain "
            "(one row per POI x monitored facility x request_mw). "
            "|| OBSERVED VINTAGE (publisher payload): DPP-2021-Cycle. "
            "|| MEASURED, CONTRADICTS THE REQUEST-SIZE PREMISE: pMaxValue is a REPORTING CLAMP, "
            "not a study input. PMax(X) == min(PMax_true, X) verified 38,381/38,381 distinct "
            "(POI,facility) keys with ZERO violations, comparing two INDEPENDENT harvests we "
            "already hold (in_miso_poi_300mw at pMaxValue=300 vs the Indiana subset of "
            "energy.miso_poi_monitored_facilities at 99999); and 67/67 facilities live at 100 "
            "and 300. Headroom never FALLS as the ask grows - a bigger ask only un-censors it. "
            "|| DEDUPE REQUIRED: both sources carry a 1.042 duplicate-key factor; joining "
            "without MIN-per-key manufactures 2,124 phantom disagreements. "
            "|| Rungs are DERIVED by clamping, not re-scraped - every row carries "
            "_rung_provenance saying which. The publisher's own harvest metadata agrees: "
            "_invariant_columns=['mw_available','percent_dfax','percent_loading_before',"
            "'derived_rating_mva'], _probe_dependent_columns=['mw_impact','percent_impact',"
            "'percent_loading_after']. "
            "|| INJECTION ONLY - see in_bus_headroom_miso_ladder notes for the withdrawal wall."),
    ),
    dict(
        table="in_bus_headroom_miso_ladder",
        source=f"rollup of indiana_app.in_miso_poi_ladder | endpoint_kind=bq_clip | "
               f"upstream {MISO_URL}",
        method=(
            "RE-SCRAPE COMMAND: python scripts/build_miso_injection_ladder.py"
            "   (builds in_miso_poi_ladder and this rollup in one run) "
            "|| RTO=MISO; direction=INJECTION; request_mw rungs 100/300/500/1000/2500/5000; "
            "POI grain. MIN(allowable_injection_mw) across facilities per (POI, request_mw)."),
        notes=(
            "Per-POI MISO INJECTION headroom at each request size. "
            "MIN(min(true_i,X)) == min(MIN(true_i),X), so the rollup is exact at every rung. "
            "|| OBSERVED VINTAGE: DPP-2021-Cycle. "
            "|| MEASURED HEADLINE: 641 of 642 Indiana POIs read ZERO injection headroom at EVERY "
            "rung including 100 MW. Exactly one POI is non-zero (~815 MW true), so it fits a 100, "
            "300 or 500 MW ask but not 1000 MW. The ladder does not rescue Indiana MISO injection; "
            "it confirms the constraint is structural, not an artifact of the 300 MW probe. "
            "|| EXCLUDED: nothing - zero-headroom POIs are RETAINED, because a zero that means "
            "'a facility is already at its rating' is a real answer and must not be confused with "
            "'not evaluated'. facilities_at_zero is carried per POI. "
            "|| WITHDRAWAL IS BLOCKED, NOT MISSING: MISO publishes no load/withdrawal direction. "
            "Measured: negative pMaxValue floors at 0; eight candidate direction parameters "
            "(direction/type/studyType/transferType/isLoad/loadFlag/dcType/pMinValue) are all "
            "silently ignored with byte-identical output; only /POI/api/pois and /POI/api/poi_mf "
            "exist (poi_lf, poi_load, swagger all 404). MISO's Large Load framework is still "
            "being designed - see docs/RTO_DIRECTIONS.md for the verbatim publisher wall."),
    ),
]


AEP_POI_BUSES = 1524   # what QueueScope offers for owner 739, observed in BOTH directions


def exists(t):
    try:
        client.get_table(f"{DS}.{t}")
        return True
    except Exception:
        return False


def footprint(t, col="bus_number", where="desired_mw = 100"):
    """How much of AEP's 1,524-bus POI list this table actually covers.

    A partial harvest that reads as complete is worse than no harvest, so the completeness
    is measured live and stamped into the registry note rather than described in prose.
    """
    try:
        b = list(client.query(
            f"SELECT COUNT(DISTINCT {col}) b FROM `{DS}.{t}` WHERE {where}"))[0].b
    except Exception:
        b = list(client.query(f"SELECT COUNT(DISTINCT {col}) b FROM `{DS}.{t}`"))[0].b
    pct = 100.0 * b / AEP_POI_BUSES
    state = "COMPLETE" if b >= AEP_POI_BUSES else "PARTIAL - HARVEST INCOMPLETE"
    return (f" || FOOTPRINT {state}: {b:,} of {AEP_POI_BUSES:,} AEP POI buses ({pct:.1f}%). "
            f"Resume with the RE-SCRAPE COMMAND above; it is checkpointed per batch and will "
            f"only re-run what never landed.")


for r in ROWS:
    t = r["table"]
    if not exists(t):
        print(f"SKIP {t}: does not exist yet (no row invented for it)")
        continue
    n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.{t}`"))[0].n
    if t == "in_pjm_queuescope_injection":
        r = dict(r, notes=r["notes"] + footprint(t))
    elif t == "in_pjm_bus_injection":
        r = dict(r, notes=r["notes"] + footprint(t, where="TRUE"))
    if n == 0:
        print(f"SKIP {t}: zero rows - refusing to register an empty table")
        continue
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name=@t",
                 job_config=bigquery.QueryJobConfig(query_parameters=[
                     bigquery.ScalarQueryParameter("t", "STRING", t)])).result()
    client.query(
        f"""INSERT `{DS}._registry`
            (table_name, source, method, n_rows, gb_scanned, built_at, notes)
            VALUES (@t, @s, @m, @n, @gb, CURRENT_TIMESTAMP(), @notes)""",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", t),
            bigquery.ScalarQueryParameter("s", "STRING", r["source"]),
            bigquery.ScalarQueryParameter("m", "STRING", r["method"]),
            bigquery.ScalarQueryParameter("n", "INT64", int(n)),
            bigquery.ScalarQueryParameter("gb", "FLOAT64", 0.05),
            bigquery.ScalarQueryParameter("notes", "STRING", r["notes"])])).result()
    print(f"registered {t}: {n:,} rows")

print("\n--- verification: every workstream table has exactly one registry row ---")
for r in client.query(f"""
    SELECT table_name, n_rows, LENGTH(source) src_len, LENGTH(method) meth_len,
           LENGTH(notes) notes_len, COUNT(*) OVER (PARTITION BY table_name) dupes
    FROM `{DS}._registry`
    WHERE table_name IN ({','.join(repr(x['table']) for x in ROWS)})
    ORDER BY table_name"""):
    flag = "  <-- DUPLICATE" if r.dupes > 1 else ""
    print(f"   {r.table_name:32s} n_rows={r.n_rows:>9,}  source={r.src_len}c "
          f"method={r.meth_len}c notes={r.notes_len}c{flag}")
