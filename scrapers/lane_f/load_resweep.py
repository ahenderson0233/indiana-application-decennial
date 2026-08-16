"""Load the re-sweep of the counties whose "nothing found" was never earned.

WHY. The 92-county sweep recorded 39 counties SEARCHED_NONE_FOUND. Auditing it against its own
stated method found 18 where the county's official website was NEVER FETCHED -- only a
search-engine look -- which is a much weaker claim than reading the county's own minutes, and one
that must never be scored as "this county permits data centres".

(My framing of that set as "22" was wrong: I added 4 counties that ran a single query to 18 that
never fetched a site, and the 4 were already inside the 18. The re-sweep caught the double-count.
`official_site_fetched` is a STRING column holding "False", which is also why a boolean test on it
would have silently matched nothing.)

WHAT CAME BACK. Three of the 18 flipped to ACTION_FOUND -- the weak sweep had scored real actions
as nothing:

  Henry     approval-permissive, VERIFIED. Commissioners' own signed minutes, 2026-01-07 work
            session on the PUD for a proposed data centre at Knightstown (~1 GW Surge Development
            campus, I-70/SR-109). The 2026-01-28 approval vote is graded REPORTED because that
            meeting's official minutes are a textless scan.
  Tipton    proposed moratorium, VERIFIED. Plan Commission favourably recommended 2026-07-02,
            docket CO-ZO-13-26, certified 07-07, commissioners noticed for 07-13. Outcome not yet
            posted -- left open rather than assumed.
  Sullivan  approval-permissive, REPORTED. No county zoning exists at all; commissioners signed
            road-use and community-enhancement agreements with the Potentia/Heartland campus
            (~$65B, construction began 2026-04-23) and a 430 MW Fluidstack campus at New Lebanon.
            The county's online minutes end ~2020, so the agreements need a records request.

The other 15 are now honestly-earned negatives: every one had its official site actually fetched,
which was the defining defect, plus >=2 Indiana-qualified queries.

FOUR OF THE PRIOR WALLS DID NOT REPRODUCE. Montgomery, Tipton, Pike and Sullivan had been recorded
robots-403; all four served robots.txt this run with Crawl-delay: 300, which was honoured. A wall
is an observation at a point in time, not a permanent property of a host.

Writes only to energy-platfrom.indiana_app.
"""
import datetime
import json
import os

from google.cloud import bigquery

HERE = os.path.dirname(os.path.abspath(__file__))
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()

d = json.loads(open(os.path.join(HERE, "resweep_weak_counties.json"), encoding="utf-8").read())
actions, coverage, walls = d.get("actions", []), d.get("coverage", []), d.get("walls", [])
print(f"read {len(actions)} actions · {len(coverage)} coverage rows · {len(walls)} walls")

ACOLS = ["county", "jurisdiction", "action_type", "instrument", "observed_date", "effective_from",
         "effective_to", "expiry_condition_verbatim", "verbatim_snippet", "url", "evidence_grade",
         "date_note", "_pulled_at", "_assembled_at"]
CCOLS = ["county", "status", "county_site_host", "queries_run", "official_site_fetched",
         "search_instrument", "notes", "_assembled_at"]


def load(name, rows, cols, source, method, notes):
    out = [{c: (None if r.get(c) is None else str(r.get(c))) for c in cols} for r in rows]
    for o in out:
        o["_assembled_at"] = NOW
    client.load_table_from_json(
        out, f"{DS}.{name}",
        job_config=bigquery.LoadJobConfig(
            schema=[bigquery.SchemaField(c, "STRING") for c in cols],
            write_disposition="WRITE_TRUNCATE")).result()
    n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.{name}`"))[0].n
    print(f"loaded {n} rows -> {name}")
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{name}'").result()
    client.query(
        f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
        f"VALUES (@t,@s,@m,@n,0.0,CURRENT_TIMESTAMP(),@no)",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", name),
            bigquery.ScalarQueryParameter("s", "STRING", source),
            bigquery.ScalarQueryParameter("m", "STRING", method),
            bigquery.ScalarQueryParameter("n", "INT64", int(n)),
            bigquery.ScalarQueryParameter("no", "STRING", notes)])).result()
    print(f"registered {name}")


load("in_dc_actions_resweep", actions, ACOLS,
     "Indiana county government websites, second pass over the counties whose official site was "
     "never fetched in the first sweep",
     "robots.txt read per host BEFORE any fetch; Crawl-delay honoured up to 300s; honest UA; "
     ">=2 Indiana-qualified queries per county plus full-text reads of minutes/agendas/ordinance "
     "lists wherever the county publishes text.",
     "THREE counties flipped from SEARCHED_NONE_FOUND to ACTION_FOUND, so the original negatives "
     "were not earned. Henry (~1 GW Surge Development PUD, Knightstown) and Tipton (moratorium "
     "recommended, docket CO-ZO-13-26) are VERIFIED at the county's own source; Sullivan is "
     "REPORTED -- no county zoning exists there and its online minutes end ~2020, so the "
     "Potentia/Heartland (~$65B, construction began 2026-04-23) and Fluidstack 430 MW agreements "
     "need a records request. Tipton's 2026-07-13 outcome is NOT yet posted and is left open.")

load("in_dc_actions_resweep_coverage", coverage, CCOLS,
     "the 18 counties recorded SEARCHED_NONE_FOUND without their official site ever being fetched",
     "Each county's own website located and fetched, then searched for data-centre land-use "
     "action; >=2 Indiana-qualified queries; name collisions identified and discarded explicitly.",
     "The defining defect of these 18 was that a search-engine look had been recorded as a "
     "county-level negative. All 18 now have the official site fetched. Name collisions defeated "
     "this pass and named in the notes: Knox TN, Carroll GA/MD, Newton GA, Warren NC/MO, Henry IA, "
     "Union AR, plus Indianapolis's own Pike and Warren TOWNSHIPS -- which is the same trap that "
     "put Brown County WISCONSIN and Clay County FLORIDA into this app as Indiana postures.")

if walls:
    load("in_dc_actions_resweep_walls",
         [{"host": w.get("host"), "wall_verbatim": w.get("wall_verbatim"), "_assembled_at": NOW}
          for w in walls], ["host", "wall_verbatim", "_assembled_at"],
         "robots.txt and HTTP refusals during the re-sweep",
         "Quoted verbatim; no wall worked around.",
         "NOTE: four walls recorded in the first sweep (Montgomery, Tipton, Pike, Sullivan) did "
         "NOT reproduce -- all served robots.txt with Crawl-delay: 300 this run. A wall is an "
         "observation at a point in time, not a permanent property of a host, and a BLOCKED "
         "record should be re-tested before it is treated as final.")

print("\n=== what the re-sweep changed ===")
for r in client.query(f"""SELECT status, COUNT(*) n FROM `{DS}.in_dc_actions_resweep_coverage`
  GROUP BY 1 ORDER BY n DESC"""):
    print(f"  {r.status:26s} {r.n:>3}")
for r in client.query(f"""SELECT county, action_type, evidence_grade,
  SUBSTR(instrument,1,64) instr FROM `{DS}.in_dc_actions_resweep` ORDER BY county"""):
    print(f"  {r.county:12s} {r.action_type:22s} {r.evidence_grade:28s} {r.instr}")
