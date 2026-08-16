"""92-COUNTY SWEEP -- data-centre land-use actions on county/municipal OFFICIAL WEBSITES.

WHY THIS EXISTS. ORDINANCE_FINDINGS.md 2 proved Indiana's actual, current data-centre
regulation happens as commissioner MORATORIA and uncodified ordinances published on county
websites -- structurally invisible to every codified-code publisher. The prior run assessed
37 of 92 counties through the codified layer; this run sweeps the county-website layer for
all 92, via the web-search-engine index plus robots-checked fetches of official pages.

METHOD (per county): >=2 web-search queries with the data-centre vocabulary; any indicated
action verified at the county/city's OWN site where reachable (robots.txt read per host
BEFORE any fetch; a challenged robots.txt = BLOCKED, never crawled). Evidence grades:
  VERIFIED_AT_OFFICIAL_SOURCE -- fetched from the government's own site/PDF, quoted verbatim
  REPORTED_NEEDS_VERIFICATION -- carried by news/aggregator only; a WORKLIST, never a posture
Known-positive controls: Boone (Ordinance 2026-08) and Miami (recorded 2026-05-04) -- this
loader REFUSES to run if either is missing or unverified, because that means the instrument
is broken.

DATES ARE THE PUBLISHER'S OWN. observed_date/effective_from/effective_to come from the
source's stated adoption/effective/expiry dates; `expiry_condition_verbatim` carries
condition-based expiries (e.g. Miami: "until the Zoning Ordinance is amended"); `_pulled_at`
is the fetch timestamp and is never mixed with them.

Input: dc_actions_county_consolidated.json (built from the per-batch research JSONs).
Tables: in_dc_actions_county_v2 (action rows), in_dc_actions_coverage_v2 (one row per
county, all 92). Does NOT touch in_ordinances_dc*, and energy.* is read-only except the
append to energy.registry_sources.
"""
import datetime, json, pathlib, sys

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "dc_actions_county_consolidated.json"

ALL92 = {
    "Adams","Allen","Bartholomew","Benton","Blackford","Boone","Brown","Carroll","Cass","Clark",
    "Clay","Clinton","Crawford","Daviess","Dearborn","Decatur","DeKalb","Delaware","Dubois",
    "Elkhart","Fayette","Floyd","Fountain","Franklin","Fulton","Gibson","Grant","Greene",
    "Hamilton","Hancock","Harrison","Hendricks","Henry","Howard","Huntington","Jackson","Jasper",
    "Jay","Jefferson","Jennings","Johnson","Knox","Kosciusko","LaGrange","Lake","LaPorte",
    "Lawrence","Madison","Marion","Marshall","Martin","Miami","Monroe","Montgomery","Morgan",
    "Newton","Noble","Ohio","Orange","Owen","Parke","Perry","Pike","Porter","Posey","Pulaski",
    "Putnam","Randolph","Ripley","Rush","St. Joseph","Scott","Shelby","Spencer","Starke",
    "Steuben","Sullivan","Switzerland","Tippecanoe","Tipton","Union","Vanderburgh","Vermillion",
    "Vigo","Wabash","Warren","Warrick","Washington","Wayne","Wells","White","Whitley",
}
assert len(ALL92) == 92

ACTION_COLS = [
    "county","jurisdiction","state","action_type","instrument","posture_source_words",
    "observed_date","date_note","effective_from","effective_to","expiry_condition_verbatim",
    "verbatim_snippet","url","ordinance_pdf_url","doc_type","evidence_grade",
    "why_codified_misses_it","source_batch","raw_row","_pulled_at","_assembled_at",
]
COVER_COLS = [
    "county","status","county_site_host","queries_run","official_site_fetched","notes",
    "search_instrument","source_batch","raw_row","_pulled_at","_assembled_at",
]

payload = json.loads(SRC.read_text(encoding="utf-8"))
actions, coverage = payload["actions"], payload["coverage"]
ASSEMBLED = datetime.datetime.now(datetime.timezone.utc).isoformat()

# ---- VALIDATION GATES (a clean number is a claim about the instrument first) ----
cov_counties = [c["county"] for c in coverage]
dupes = {c for c in cov_counties if cov_counties.count(c) > 1}
assert not dupes, f"duplicate coverage rows: {dupes}"
missing = ALL92 - set(cov_counties)
extra = set(cov_counties) - ALL92
assert not extra, f"coverage rows for non-counties: {extra}"
# A PARTIAL MERGE MUST NOT LOAD SILENTLY. This gate is here because it was absent once and cost
# 13 counties: the consolidation ran at 13:24 while batch A was still sweeping, batch A landed at
# 13:37, and the file carried 79 of 92 with the shortfall printed to a console nobody re-read.
# The whole northwest quadrant -- Lake, LaPorte, Porter, Tippecanoe -- would have shipped as
# "not assessed" while Lake County Ordinance 2590 (data centres PROHIBITED in all business
# districts, verified at the county's own signature page) sat unread in a JSON file.
# An uncovered county rendered as silence is the exact inversion ORDINANCE_FINDINGS.md warns
# about, so this refuses to load rather than reporting the shortfall and continuing.
assert not missing, (
    f"REFUSING TO LOAD: coverage is {len(cov_counties)} of 92 counties; "
    f"{len(missing)} missing: {sorted(missing)}. A batch is absent from the consolidated file. "
    f"Merge it (see merge_batch_a_into_consolidated.py) before loading -- do NOT load a partial "
    f"sweep, because not-assessed renders as not-regulated.")
for a in actions:
    assert a["county"] in ALL92, f"action row for unknown county: {a['county']}"
# control gate: the two known positives must be present and VERIFIED, or the method is broken
for control in ("Boone", "Miami"):
    ok = [a for a in actions if a["county"] == control
          and a["evidence_grade"] == "VERIFIED_AT_OFFICIAL_SOURCE"
          and a["action_type"] == "moratorium"]
    assert ok, f"CONTROL FAILURE: {control} moratorium not present as VERIFIED -- do not load"
# no action may carry the pull date as its observed date unless the note says the source said so
for a in actions:
    od = a.get("observed_date") or ""
    if od[:10] == ASSEMBLED[:10] and "source" not in (a.get("date_note") or "").lower():
        raise AssertionError(f"suspicious observed_date == run date on {a['jurisdiction']}")

print(f"validated: {len(actions)} actions, {len(coverage)} coverage rows "
      f"({len(missing)} of 92 not covered: {sorted(missing) if missing else 'none'})")

client = bigquery.Client(project="energy-platfrom")

# ---- denominator gate: ALL92 must equal the warehouse's authoritative county list.
# A 93rd 'county' is exactly how a FEMA roll-up broke here (fipsCountyCode='000' = 'Statewide').
authoritative = {r.NAME for r in client.query(
    "SELECT NAME FROM `energy-platfrom.energy.county_boundaries` WHERE STATEFP='18'")}
assert authoritative == ALL92, (
    f"county denominator mismatch vs energy.county_boundaries: "
    f"only_here={sorted(ALL92-authoritative)} only_there={sorted(authoritative-ALL92)}")
print(f"denominator gate passed: {len(authoritative)} counties match energy.county_boundaries")

def _load(name, rows, cols):
    out = []
    for r in rows:
        d = {k: r.get(k) for k in cols}
        d["_assembled_at"] = ASSEMBLED
        d.setdefault("state", None)
        out.append({k: (None if d.get(k) is None else str(d.get(k))) for k in cols})
    client.load_table_from_json(
        out, f"{DS}.{name}",
        job_config=bigquery.LoadJobConfig(
            schema=[bigquery.SchemaField(k, "STRING") for k in cols],
            write_disposition="WRITE_TRUNCATE")).result()
    n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.{name}`"))[0].n
    print(f"loaded {n} rows -> {name}")
    return n

for a in actions:
    a["state"] = "IN"
n_act = _load("in_dc_actions_county_v2", actions, ACTION_COLS)
n_cov = _load("in_dc_actions_coverage_v2", coverage, COVER_COLS)

# ---- registry: same-run registration, one row per table (upsert own rows only) ----
for name, n, src, meth, notes in [
    ("in_dc_actions_county_v2", n_act,
     "Indiana county/municipal government websites via web-search index + robots-checked official fetches",
     "92-county sweep for UNCODIFIED data-centre land-use actions: moratoria (with expiry), bans, "
     "adopted-but-uncodified ordinances, proposals, denials, withdrawals, permissive approvals. "
     ">=2 search queries per county; official .gov/.us pages fetched only after reading robots.txt; "
     "publisher's own dates; verbatim snippets; evidence-graded.",
     "READ evidence_grade BEFORE USING ANY ROW: only VERIFIED_AT_OFFICIAL_SOURCE rows are facts from "
     "the government's own site; REPORTED_NEEDS_VERIFICATION rows are a worklist and must never be "
     "rendered as posture. expiry: effective_to when date-based, expiry_condition_verbatim when "
     "condition-based. Controls Boone+Miami rediscovered and verified this run. Complements (does not "
     "modify) in_ordinances_dc_v2; distinct from in_dc_actions (news/DCWatch project tracker)."),
    ("in_dc_actions_coverage_v2", n_cov,
     "web-search-engine layer over all 92 Indiana county websites",
     "One row per county, all 92. status: ACTION_FOUND / SEARCHED_NONE_FOUND / NOT_SEARCHABLE / "
     "BLOCKED / NOT_REACHED. SEARCHED_NONE_FOUND required >=2 live county-relevant queries.",
     "SEARCHED_NONE_FOUND at the web-search layer is weaker than a full-text codified search: it means "
     "no data-centre action surfaced in the search index or county site, not that the code is silent. "
     "NOT_REACHED/BLOCKED must never be scored as permissive."),
]:
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{name}'").result()
    client.query(
        f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
        f"VALUES (@t,@s,@m,@n,0.0,CURRENT_TIMESTAMP(),@no)",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", name),
            bigquery.ScalarQueryParameter("s", "STRING", src),
            bigquery.ScalarQueryParameter("m", "STRING", meth),
            bigquery.ScalarQueryParameter("n", "INT64", int(n)),
            bigquery.ScalarQueryParameter("no", "STRING", notes)])).result()
    print(f"registered {name}")

client.query(
    "INSERT INTO `energy-platfrom.energy.registry_sources` "
    "(source_name, status, endpoint, endpoint_kind, acquisition_method, object_names, "
    " updated_by, geography_state, last_validated_at, notes) "
    "VALUES (@n,@s,@e,@k,@m,@o,'indiana-app-ordinances-agent','IN',CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("n", "STRING",
            "Indiana 92-county website sweep: uncodified data-centre land-use actions"),
        bigquery.ScalarQueryParameter("s", "STRING", "OK"),
        bigquery.ScalarQueryParameter("e", "STRING",
            "county .gov/.us sites via web-search index; robots.txt read per host before any fetch"),
        bigquery.ScalarQueryParameter("k", "STRING", "html+pdf"),
        bigquery.ScalarQueryParameter("m", "STRING",
            "search-engine discovery + robots-checked official-site verification; publisher's own "
            "dates; moratoria carry expiry (date or verbatim condition); evidence-graded; "
            "no walls worked around"),
        bigquery.ArrayQueryParameter("o", "STRING",
            ["in_dc_actions_county_v2", "in_dc_actions_coverage_v2"]),
        bigquery.ScalarQueryParameter("no", "STRING",
            "Controls: Boone (Ord 2026-08) and Miami (recorded 2026-05-04, instrument 20260521646) "
            "both rediscovered by the method and verified at the county's own site this run.")])).result()
print("appended to energy.registry_sources")
