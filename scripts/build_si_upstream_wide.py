"""G152: CLIP EVERY UPSTREAM SI SOURCE INDIANA-ONLY, AT FULL WIDTH, INTO indiana_app.

Operator, 2026-08-21: *"Even if a source scrapes everything but one column, we still want to
rescrape it for everything because that one field may contain something materially important
(e.g., an event time or another SI signal), so it is crucial that we have full visibility over
each dataset."*

================================================================================================
⭐ WHY `SELECT *` IS THE POINT, NOT LAZINESS
================================================================================================
Every clip below is `SELECT * FROM <parent> WHERE <indiana predicate>`. Naming columns is how a
clip narrows: `build_gas_facilities.py` sliced its parent schema at `[:10]` and silently dropped
operator, owner, status and county, because a positional cut keeps whatever the publisher happened
to put first. `SELECT *` cannot do that, and the assertion at the end of this script proves it —
our column count must EQUAL the parent's, or the build fails.

⚠ THE PREDICATE IS THE ONLY THING THAT NARROWS, AND IT IS APPLIED AT THE CLIP. Filtering after the
fact would rescan a 14.8 GB parent every run.

⛔ WRITE BOUNDARY. `energy-platfrom.energy` is READ-ONLY — this script only ever SELECTs from it.
Everything is written to `energy-platfrom.indiana_app`. The one permitted write to `energy` is an
APPEND to `energy.registry_sources`, which happens at the end.

⚠ COST. ~16 GB scanned on a full run (si_d5_vacancy_derived alone is 14.8 GB), about $0.08 at
on-demand pricing. Well under the $25-50 flag, but it is not free: run it when a parent reloads,
not on a loop. `--only <key>` rebuilds one source.

⚠ IDEMPOTENT: replace_safe. Every table is CREATE OR REPLACE from its parent. Re-running cannot
double-count — unlike the three append_only loaders named in docs/RESCRAPE_LEDGER.md.

RE-SCRAPE COMMAND: python scripts/build_si_upstream_wide.py
"""
import argparse
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.cloud import bigquery

from si_upstream_sources import REPAIRS, SOURCES, YEAR_GAPS

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")

RESCRAPE = (
    "RE-SCRAPE COMMAND: python scripts/build_si_upstream_wide.py "
    "⚠ IDEMPOTENT: replace_safe - CREATE OR REPLACE from the energy parent, so a re-run cannot "
    "double-count. ⛔ THE PARENT IS READ-ONLY: this is a wider CLIP, never an edit upstream. "
    "⭐ A FULL-WIDTH clip - SELECT *, asserted equal to the parent's column count at build time, "
    "because the operator's rule is that one unexamined column may hold an event time or a whole "
    "signal. CADENCE: whenever the energy parent reloads.")


def parent_shape(parent, pred):
    """Read the parent's width and its Indiana row count. ⛔ Never assumed - both are measured
    before the clip runs, so a parent that changed shape fails loudly instead of quietly."""
    cols = [f.name for f in client.get_table(f"{EN}.{parent}").schema]
    n = list(client.query(
        f"SELECT COUNT(*) AS n FROM `{EN}.{parent}` WHERE {pred}").result())[0]["n"]
    return cols, n


def control_probe(parent, cols):
    """⛔ WHY THIS EXISTS. `si_d1_sri_taxsale_listings` spells the state 'Indiana' where every other
    parent spells it 'IN'. The predicate was written as ='IN', matched zero rows, and the build
    PASSED - because the column assertion compared the clip against the predicate, and the row
    assertion compared the predicate against itself. Two checks agreeing on the same wrong
    assumption is not verification.

    ⭐ So a zero-row clip is now a FAILURE, and the failure prints the parent's actual state
    vocabulary, which is the fix. The project's own rule for a silent county applies to a silent
    clip: check a control word before recording anything as absent."""
    statish = [c for c in cols if c.lower() in
               ("state", "state_code", "propertystate", "source_state", "borrstate",
                "projectstate", "site_state", "publisher_state", "st")]
    if not statish:
        return "  (no state-like column to probe - check the predicate by hand)"
    lines = []
    for c in statish[:3]:
        rows = list(client.query(
            f"SELECT `{c}` AS v, COUNT(*) n FROM `{EN}.{parent}` "
            f"GROUP BY 1 ORDER BY n DESC LIMIT 8").result())
        vals = ", ".join(f"{r['v']!r}={r['n']:,}" for r in rows)
        lines.append(f"    {parent}.{c} top values: {vals}")
    return "\n".join(lines)


def clip(target, parent, pred, why, kind):
    cols, avail = parent_shape(parent, pred)

    # ⛔ A ZERO-ROW CLIP IS A BROKEN PREDICATE UNTIL PROVEN OTHERWISE. Never a quiet empty table:
    # an empty layer reads as "we looked and found none", which is a claim we have not earned.
    if avail == 0:
        raise SystemExit(
            f"⛔ {target}: the predicate matches ZERO rows in {parent}.\n"
            f"    predicate: {pred}\n"
            f"{control_probe(parent, cols)}\n"
            f"    ⚠ Fix the predicate in scripts/si_upstream_sources.py. If the parent genuinely "
            f"holds no Indiana rows, say so in the map and remove the source.")

    before = None
    try:
        before = client.get_table(f"{DS}.{target}").num_rows
    except Exception:
        pass

    job = client.query(
        f"CREATE OR REPLACE TABLE `{DS}.{target}` AS "
        f"SELECT * FROM `{EN}.{parent}` WHERE {pred}")
    job.result()
    gb = (job.total_bytes_processed or 0) / 1e9

    got = client.get_table(f"{DS}.{target}")
    ours = [f.name for f in got.schema]

    # ⛔ THE ASSERTION THAT MAKES THIS A CLIP AND NOT A SAMPLE. If SELECT * ever stops meaning
    # every column - a view behind the parent, a policy, a rename - this fails rather than
    # shipping a narrower table that looks fine.
    missing = [c for c in cols if c not in ours]
    if missing:
        raise SystemExit(f"⛔ {target}: clip is NARROWER than {parent} - missing {missing}")
    if got.num_rows != avail:
        raise SystemExit(f"⛔ {target}: clipped {got.num_rows:,} but the predicate matches "
                         f"{avail:,} in {parent}")

    delta = "" if before is None else f"  (was {before:,})"
    print(f"  [{kind}] {target:32} {got.num_rows:>9,} rows x {len(ours):>3} cols{delta}")
    print(f"          {why}")
    return {"table": target, "parent": parent, "pred": pred, "rows": got.num_rows,
            "cols": len(ours), "gb": gb, "before": before, "why": why, "kind": kind}


def register(r):
    """⛔ G16: a registry row must be enough for a STRANGER to re-run the work. So it carries the
    parent, the exact predicate, the measured row count and the verbatim command."""
    method = (f"full-width Indiana clip: SELECT * FROM energy.{r['parent']} WHERE {r['pred']} "
              f"-- {r['cols']} columns, asserted equal to the parent. {r['why']} {RESCRAPE}")
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name=@t",
                 job_config=bigquery.QueryJobConfig(query_parameters=[
                     bigquery.ScalarQueryParameter("t", "STRING", r["table"])])).result()
    client.query(
        f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at) "
        f"VALUES (@t,@s,@m,@n,@g,CURRENT_TIMESTAMP())",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", r["table"]),
            bigquery.ScalarQueryParameter("s", "STRING", f"energy.{r['parent']}"),
            bigquery.ScalarQueryParameter("m", "STRING", method),
            bigquery.ScalarQueryParameter("n", "INT64", r["rows"]),
            bigquery.ScalarQueryParameter("g", "FLOAT64", round(r["gb"], 4))])).result()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="rebuild one target table only")
    a = ap.parse_args()

    print("=" * 96)
    print("G152 - EVERY UPSTREAM SI SOURCE, INDIANA-ONLY, AT FULL WIDTH")
    print("=" * 96)
    print("⛔ energy is READ-ONLY. Every table below is written to indiana_app.\n")

    plan = ([(t, p, pr, why, "new") for _, p, pr, t, why in SOURCES]
            + [(t, p, pr, why, "repair") for t, p, pr, why in REPAIRS]
            + [(t, p, pr, why, "yeargap") for t, p, pr, why in YEAR_GAPS])
    if a.only:
        plan = [x for x in plan if x[0] == a.only]
        if not plan:
            raise SystemExit(f"no target named {a.only}")

    built, gb = [], 0.0
    for target, parent, pred, why, kind in plan:
        r = clip(target, parent, pred, why, kind)
        register(r)
        built.append(r)
        gb += r["gb"]

    print("\n" + "=" * 96)
    print(f"{len(built)} table(s) built and registered · {gb:.1f} GB scanned "
          f"(about ${gb * 0.005:.2f})")
    gained = [r for r in built if r["before"] is not None and r["rows"] > r["before"]]
    if gained:
        print("\n⭐ ROWS RECOVERED BY FIXING A CLIP THAT WAS ALREADY 'FULL WIDTH':")
        for r in gained:
            print(f"   {r['table']}: {r['before']:,} -> {r['rows']:,} "
                  f"(+{r['rows'] - r['before']:,})")

    # the one permitted write to energy: an APPEND recording what we clipped and from where
    cols = {s.name for s in client.get_table(f"{EN}.registry_sources").schema}
    row = {"source_name": "SI upstream sources, Indiana clips at FULL WIDTH (G152)",
           "status": "done",
           "endpoint": f"bq://{EN}",
           "endpoint_kind": "bq_clip",
           "acquisition_method":
               "scripts/build_si_upstream_wide.py - SELECT * per parent with an Indiana "
               "predicate, column count asserted equal to the parent. Replaces reading the 19 "
               "sources through energy.si_signals, which normalises 97,240,585 rows to 13 "
               "columns.",
           "what_it_provides":
               "full-width Indiana clips of the upstream tables behind the SI signals",
           "object_names": [r["table"] for r in built],
           "measured_rows": sum(r["rows"] for r in built),
           "geography_state": "IN",
           "updated_by": "indiana-app-session-20260821-g152"}
    use = {k: v for k, v in row.items() if k in cols}
    errs = client.insert_rows_json(f"{EN}.registry_sources", [use])
    print(f"\nappended energy.registry_sources: {'OK' if not errs else errs}")
    print("\nDONE")


if __name__ == "__main__":
    main()
