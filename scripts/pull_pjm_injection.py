"""Harvest the PJM QueueScope **INJECTION** direction into indiana_app.

WHY A WRAPPER AND NOT A NEW SCRAPER
-----------------------------------
`energy-platform/ingest/load_pjm_queuescope_bq.py` already encodes eight hard-won facts
about QueueScope's JSF/PrimeFaces flow (the change-behaviour that ungates btnLoadCase, the
one-selectRow-per-AJAX-round-trip pacing, the desiredMW shadow input, the rows-per-page
template).  Reimplementing that would reproduce the bugs.  But it hardcodes
DATASET="energy", which is READ-ONLY for this workstream, and `ingest/` may not be edited.
So we import it and rebind the three module globals that name the sink.  `main()` resolves
`fq = f'{PROJECT}.{DATASET}.{TABLE}'` at call time, so the rebinding takes.

Everything else -- flow, pacing, idempotent per-batch DELETE+append, checkpointing -- is the
loader's, unmodified.  Checkpoints go to a DIFFERENT directory from the withdrawal harvest so
the two runs cannot read each other's marks (the mark name embeds the mode, but the harvest
that produced `energy.pjm_queuescope_results` lives in energy-platform/data/ and we do not
write there).

    python scripts/pull_pjm_injection.py --owner 739 --max-batches 1     # validate
    python scripts/pull_pjm_injection.py --owner 739                     # full AEP, ~2h

Case 4 (2027 RTEP Base, Summer Peak) and 100 MW are chosen to MATCH the withdrawal harvest
already in `indiana_app.in_pjm_queuescope_aep`, so the two directions are comparable.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

import argparse
import pathlib
import sys

from google.cloud import bigquery

REPO = pathlib.Path(r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno"
                    r"\California\ca-capacity-deploy\indiana-application-decennial")
PLATFORM = pathlib.Path(r"C:\Users\ahend\Downloads\Decennial Summer Work\Remaking Orennia"
                        r"\energy-platform")
DS = "energy-platfrom.indiana_app"
TABLE = "in_pjm_queuescope_injection"


def registry(client, table, n_rows, note, method=None):
    """A _registry row in the SAME run that writes the table (checkpoint requires it)."""
    client.query(
        f"""DELETE FROM `{DS}._registry` WHERE table_name=@t""",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", table)])).result()
    client.query(
        f"""INSERT `{DS}._registry`
            (table_name, source, method, n_rows, gb_scanned, built_at, notes)
            VALUES (@t, @s, @m, @n, 0.0, CURRENT_TIMESTAMP(), @notes)""",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", table),
            bigquery.ScalarQueryParameter(
                "s", "STRING",
                "queuescope.pjm.com/queuescope/pages/public/evaluator.jsf"),
            bigquery.ScalarQueryParameter(
                "m", "STRING", method or
                "playwright JSF/PrimeFaces harvest via scripts/pull_pjm_injection.py "
                "(wraps ingest/load_pjm_queuescope_bq.py with DATASET rebound to indiana_app)"),
            bigquery.ScalarQueryParameter("n", "INT64", int(n_rows)),
            bigquery.ScalarQueryParameter("notes", "STRING", note)])).result()
    print(f"_registry row written for {table}: n_rows={n_rows:,}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", default="739", help="transmission-owner id(s); 739 = AEP")
    ap.add_argument("--case", default="4")
    ap.add_argument("--mw", default="100")
    ap.add_argument("--max-batches", type=int)
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--mode", default="INJECTION", choices=["INJECTION", "WITHDRAWAL"])
    ap.add_argument("--table", default=TABLE,
                    help="sink table in indiana_app (a WITHDRAWAL spot-check must not land "
                         "in the injection table)")
    ap.add_argument("--registry-only", action="store_true",
                    help="skip the harvest, just re-measure and rewrite the _registry row")
    a = ap.parse_args()

    table = a.table
    client = bigquery.Client(project="energy-platfrom")

    if not a.registry_only:
        sys.path.insert(0, str(PLATFORM))
        import ingest.load_pjm_queuescope_bq as qs

        # --- the only deviation from the loader as shipped: where it writes -------------
        assert (qs.PROJECT, qs.DATASET, qs.TABLE) == (
            "energy-platfrom", "energy", "pjm_queuescope_results"), (
            f"loader sink changed under us: {qs.PROJECT}.{qs.DATASET}.{qs.TABLE} -- "
            "re-read it before trusting this wrapper")
        qs.DATASET, qs.TABLE = "indiana_app", table
        qs.CKPT = REPO / "data" / f"_ckpt_pjm_qs_case{a.case}_{a.mode.lower()}"
        print(f"sink rebound to {qs.PROJECT}.{qs.DATASET}.{qs.TABLE}")
        print(f"checkpoints -> {qs.CKPT}")

        argv = ["load_pjm_queuescope_bq", "--case", a.case, "--mode", a.mode,
                "--mw", a.mw, "--owner", a.owner]
        if a.max_batches:
            argv += ["--max-batches", str(a.max_batches)]
        if a.headed:
            argv += ["--headed"]
        sys.argv = argv
        rc = qs.main()
        if rc:
            print(f"loader returned {rc}")
            return rc

    # --- verify from BigQuery, never from the loader's own running total ----------------
    try:
        st = list(client.query(f"""
            SELECT COUNT(*) n, COUNT(DISTINCT bus_number) buses,
                   COUNT(DISTINCT owner_label) owners,
                   STRING_AGG(DISTINCT operating_mode) modes,
                   STRING_AGG(DISTINCT case_label) cases,
                   MIN(_pulled_at) first_pull, MAX(_pulled_at) last_pull,
                   COUNTIF(available_mw IS NULL) null_avail
            FROM `{DS}.{table}`"""))[0]
    except Exception as e:
        print(f"table not readable: {e}")
        return 1
    print("LIVE:", dict(st))
    if st.n == 0:
        print("ZERO ROWS -- not writing a registry row for an empty table")
        return 1
    method_str = (
        f"playwright JSF/PrimeFaces harvest via scripts/pull_pjm_injection.py "
        f"(wraps ingest/load_pjm_queuescope_bq.py, DATASET rebound to indiana_app); "
        f"case {a.case}, mode {a.mode}, desired_mw {a.mw}, owner {a.owner}; "
        f"25-POI cap per submission. "
        f"RE-SCRAPE COMMAND: python scripts/pull_pjm_injection.py --case {a.case} "
        f"--mode {a.mode} --mw {a.mw} --owner {a.owner} --table {table}")
    registry(client, table, st.n,
             f"PJM QueueScope {st.modes} direction. "
             f"{st.buses} buses, owners={st.owners}, case={st.cases}. "
             f"OBSERVED VINTAGE: case label above is the publisher's own study-case name; "
             f"PJM publishes no separate file date on this tool. "
             f"PJM's own caveats ride along: THERMAL IMPACTS ONLY (no voltage, stability or "
             f"short-circuit) and 'results are not reflective of current PJM system "
             f"conditions'. desired_mw=100 is an INPUT, so available_mw is headroom measured "
             f"against a 100 MW test injection at that POI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
