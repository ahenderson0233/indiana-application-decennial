"""Load the UNCOLLECTED first NW sweep as a SECOND INSTRUMENT — not as a merge.

WHY THIS IS A SEPARATE TABLE AND NOT A MERGE. Northwest Indiana was swept twice. The re-sweep
wrote `batch_A.json`, which is what reached `in_dc_actions_county_v2`. The FIRST pass returned its
results in its final message, the parent never collected them, and they were recovered from the
agent transcript by `salvage_agent_results.py`.

The two disagree, and not in a way inspection can settle:

    Jasper County rezone petition Cause #PC-22-25 (NIPSCO, ~5 parcels Ag->I-2, Kankakee Township)
      first pass : denied            graded VERIFIED_AT_OFFICIAL_SOURCE
      re-sweep   : petition-pending  graded VERIFIED_AT_OFFICIAL_SOURCE

Merging would force a choice between two agents that both claim to have read the official record,
which is exactly the move this project forbids. Measured overall, neither dominates: the first
pass carries 17 actions with 11 verified, the re-sweep 20 with 9. The first verified more in
Jasper, Lake and Starke; the re-sweep verified more in Tippecanoe and found Fountain at all.

So this lands beside the primary table as a corroborating/conflicting instrument, the same shape
as `in_si_marion_route_check` (7,104 agree / 9 disagree). The reconciliation happens against fresh
official-source verification, not against the other agent.

The `scrapers/**/*.json` gitignore rule means the salvaged file is a working artifact, not a
record. This puts the data in the system of record so nothing depends on an ignored file.

Writes ONLY to `energy-platfrom.indiana_app`. `energy-platfrom.energy` is READ-ONLY; the single
permitted write there is the append to `registry_sources`, which this does not need since the
sweep's source is already registered.
"""
import datetime
import json
import pathlib

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "nw_sweep_first_pass_salvaged.json"
TABLE = "in_dc_actions_nw_first_pass"

payload = json.loads(SRC.read_text(encoding="utf-8"))
actions, coverage = payload["actions"], payload["coverage"]
ASSEMBLED = datetime.datetime.now(datetime.timezone.utc).isoformat()

client = bigquery.Client(project="energy-platfrom")

# ---- the comparison is the point, so measure it BEFORE loading ---------------------------
primary = {(r.county, r.action_type): r.evidence_grade for r in client.query(
    f"SELECT county, action_type, evidence_grade FROM `{DS}.in_dc_actions_county_v2` "
    f"WHERE source_batch = 'A'")}

V = "VERIFIED_AT_OFFICIAL_SOURCE"
agree = disagree = only_here = 0
notes = []
for a in actions:
    k = (a["county"], a["action_type"])
    if k not in primary:
        only_here += 1
        notes.append(f"{a['county']}/{a['action_type']}: present in first pass only")
    elif primary[k] != a["evidence_grade"]:
        disagree += 1
        notes.append(f"{a['county']}/{a['action_type']}: grade differs — "
                     f"first={a['evidence_grade']} resweep={primary[k]}")
    else:
        agree += 1

print(f"first pass: {len(actions)} actions ({sum(1 for a in actions if a['evidence_grade']==V)} verified), "
      f"{len(coverage)} coverage rows")
print(f"vs the loaded re-sweep: {agree} agree · {disagree} grade-differ · {only_here} only in the first pass")
for n in notes:
    print(f"   {n}")

COLS = ["county", "jurisdiction", "action_type", "instrument", "posture_source_words",
        "observed_date", "date_note", "effective_from", "effective_to", "verbatim_snippet",
        "url", "doc_type", "evidence_grade", "why_codified_misses_it", "_pulled_at",
        "_instrument_label", "_conflicts_with_primary"]

out = []
for a in actions:
    d = {k: a.get(k) for k in COLS}
    d["_pulled_at"] = a.get("_pulled_at") or a.get("pulled_at")
    d["_instrument_label"] = "NW_SWEEP_FIRST_PASS_uncollected"
    k = (a["county"], a["action_type"])
    d["_conflicts_with_primary"] = str(k in primary and primary[k] != a["evidence_grade"])
    out.append({c: (None if d.get(c) is None else str(d.get(c))) for c in COLS})

client.load_table_from_json(
    out, f"{DS}.{TABLE}",
    job_config=bigquery.LoadJobConfig(
        schema=[bigquery.SchemaField(c, "STRING") for c in COLS],
        write_disposition="WRITE_TRUNCATE")).result()
n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.{TABLE}`"))[0].n
print(f"loaded {n} rows -> {TABLE}")

# ---- register in the SAME RUN that writes (checkpoint invariant 3) ------------------------
client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{TABLE}'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
    f"VALUES (@t,@s,@m,@n,0.0,CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", TABLE),
        bigquery.ScalarQueryParameter("s", "STRING",
            "NW Indiana county websites, first sweep pass — recovered from the agent transcript"),
        bigquery.ScalarQueryParameter("m", "STRING",
            "SECOND INSTRUMENT, not a merge. Northwest Indiana was swept twice; the re-sweep is "
            "what reached in_dc_actions_county_v2 (source_batch='A'). This first pass returned its "
            "results in its final message and was never collected by the parent; recovered by "
            "scrapers/lane_f/salvage_agent_results.py from the subagent transcript."),
        bigquery.ScalarQueryParameter("n", "INT64", int(n)),
        bigquery.ScalarQueryParameter("no", "STRING",
            "DO NOT UNION THIS WITH in_dc_actions_county_v2 — it is a comparison instrument. The "
            "two passes CONTRADICT on Jasper Cause #PC-22-25 (NIPSCO Ag->I-2, Kankakee Twp): this "
            "pass says 'denied', the loaded re-sweep says 'petition-pending', BOTH graded "
            "VERIFIED_AT_OFFICIAL_SOURCE. Neither pass dominates: 17 actions/11 verified here vs "
            "20/9 in the re-sweep; this pass verified more in Jasper, Lake and Starke, the re-sweep "
            "more in Tippecanoe and found Fountain at all. Resolve against fresh official-source "
            "verification, never by picking between the two agents. See "
            "scrapers/lane_f/COUNTY_DC_ACTION_FINDINGS.md §6.")])).result()
print(f"registered {TABLE}")
