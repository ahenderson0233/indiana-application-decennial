"""Load the four official-source verification runs and resolve them against the sweep's leads.

WHAT CAME BACK. 86 verification rows over the 84 REPORTED_NEEDS_VERIFICATION leads (plus two
bonus discoveries): 50 VERIFIED_AT_OFFICIAL_SOURCE, 30 NOT_FOUND_AT_OFFICIAL_SOURCE,
2 CONTRADICTED, 4 BLOCKED.

WHY THIS MATTERS BEYOND THE COUNT. Three things are wrong on screen right now:
  * Brown County's lead is Brown County, WISCONSIN -- the cited coverage is Wisconsin media and
    the committee named is a Brown County WI body.
  * Clay County's "moratorium" is Clay County, FLORIDA. Clay County INDIANA has no county zoning
    ordinance at all.
  * Marion's moratorium is rendered as an action when Proposal No. 238 is still PENDING -- the
    MDC lists it for final action on 2026-08-19. The 23-1 council vote is news-reported only.
Two invented Indiana postures and one pending proposal shown as adopted.

THE JOIN IS NOT UNIQUE, so it is not assumed to be. (county, action_type) has 9 keys carrying
multiple rows on BOTH sides -- Marion has three approval-permissive rows, Allen three, Morgan
three. Matching on that key alone would silently attach a verification to the wrong instrument.
So: unambiguous keys join directly; ambiguous keys are resolved by best token overlap on the
instrument text, greedily and one-to-one, and every row carries how it was matched. A pairing
that cannot be made confidently is recorded as ambiguous rather than guessed.

NOTHING IS OVERWRITTEN. in_dc_actions_county_v2 keeps the sweep's raw output; the verification
lands as its own table (the second-instrument pattern already used by in_si_marion_route_check);
and in_dc_actions_resolved carries both claims side by side with a single boolean --
`posture_renderable` -- that the page uses to decide what may be shown as a county's position.

Writes only to energy-platfrom.indiana_app. energy.* is READ-ONLY.
"""
# stdout must survive its own output: this console is cp1252 and characters like U+2248/U+2192/U+2717 raise
# UnicodeEncodeError from print() itself. The honesty audit once crashed on its own
# FAILURE path for exactly this reason. Degrade the glyph, never the run.
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import datetime
import glob
import json
import os
import re

from google.cloud import bigquery

HERE = os.path.dirname(os.path.abspath(__file__))
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()

VERIFIED = "VERIFIED_AT_OFFICIAL_SOURCE"
STOP = {"the", "a", "of", "and", "for", "on", "to", "in", "county", "data", "center", "centers",
        "centre", "ordinance", "no", "an", "at", "by", "is", "it", "or", "with"}


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in STOP and len(w) > 2}


# ---- read every verification file -------------------------------------------------------------
vers, walls, sites = [], [], []
for f in sorted(glob.glob(os.path.join(HERE, "verify_group_*.json"))):
    d = json.loads(open(f, encoding="utf-8").read())
    g = d.get("group")
    for v in d.get("verifications", []):
        v["_group"] = g
        vers.append(v)
    for w in d.get("walls", []):
        w["_group"] = g
        walls.append(w)
    for s in d.get("county_sites", []):
        s["_group"] = g
        sites.append(s)

print(f"read {len(vers)} verifications · {len(walls)} walls · {len(sites)} county-site records")
by_verdict = {}
for v in vers:
    by_verdict[v.get("verdict")] = by_verdict.get(v.get("verdict"), 0) + 1
print(f"  verdicts: {by_verdict}")

# ---- the leads they were sent to resolve ------------------------------------------------------
leads = [dict(r) for r in client.query(f"""
SELECT county, jurisdiction, action_type, instrument, evidence_grade, url, observed_date
FROM `{DS}.in_dc_actions_county_v2`
WHERE evidence_grade = 'REPORTED_NEEDS_VERIFICATION'""")]
print(f"leads awaiting verification in the warehouse: {len(leads)}")

# ---- match: exact where the key is unique, token overlap where it is not ----------------------
from collections import defaultdict

lead_by_key, ver_by_key = defaultdict(list), defaultdict(list)
for x in leads:
    lead_by_key[(x["county"], x["action_type"])].append(x)
for v in vers:
    ver_by_key[(v["county"], v["original_action_type"])].append(v)

pairs, unmatched_v, ambiguous = [], [], 0
for key, vlist in ver_by_key.items():
    llist = lead_by_key.get(key, [])
    if not llist:
        for v in vlist:
            unmatched_v.append(v)
        continue
    if len(vlist) == 1 and len(llist) == 1:
        pairs.append((llist[0], vlist[0], "unique_key"))
        continue
    # ambiguous: score every pairing on instrument-token overlap, take best first, one-to-one
    scored = []
    for vi, v in enumerate(vlist):
        for li, l in enumerate(llist):
            a, b = toks(v.get("instrument")), toks(l.get("instrument"))
            j = len(a & b) / max(len(a | b), 1)
            # jurisdiction agreement is a strong secondary signal
            j += 0.25 * (len(toks(v.get("jurisdiction")) & toks(l.get("jurisdiction"))) > 0)
            scored.append((j, vi, li))
    scored.sort(reverse=True)
    usedv, usedl = set(), set()
    for j, vi, li in scored:
        if vi in usedv or li in usedl:
            continue
        usedv.add(vi); usedl.add(li)
        how = "token_overlap" if j >= 0.15 else "ambiguous_positional"
        if how == "ambiguous_positional":
            ambiguous += 1
        pairs.append((llist[li], vlist[vi], how))
    for vi, v in enumerate(vlist):
        if vi not in usedv:
            unmatched_v.append(v)

# ASCII only in console output -- this console is cp1252 and a stray arrow has now crashed three
# scripts in one session, including the honesty audit's own failure path.
print(f"matched {len(pairs)} lead-to-verification pairs "
      f"({sum(1 for p in pairs if p[2]=='unique_key')} on a unique key, "
      f"{sum(1 for p in pairs if p[2]=='token_overlap')} by instrument overlap, "
      f"{ambiguous} could not be disambiguated and are flagged)")
print(f"verification rows with no lead (bonus discoveries): {len(unmatched_v)}")
for v in unmatched_v:
    print(f"   {v['county']} — {str(v.get('instrument'))[:70]}")

# ---- build the resolved rows ------------------------------------------------------------------
COLS = ["county", "jurisdiction", "lead_action_type", "lead_instrument", "lead_url",
        "verdict", "confirmed_action_type", "verified_instrument", "verified_observed_date",
        "verified_effective_from", "verified_effective_to", "expiry_condition_verbatim",
        "verbatim_snippet", "official_url", "date_note", "verification_note",
        "final_evidence_grade", "posture_renderable", "match_method", "verify_group",
        "_verified_at", "_assembled_at"]


def resolve(lead, v, how):
    verdict = v.get("verdict")
    if verdict == VERIFIED:
        grade, render = VERIFIED, True
    elif verdict == "CONTRADICTED":
        # an out-of-state misattribution must never reach a posture surface again
        grade, render = "CONTRADICTED_MISATTRIBUTED", False
    elif verdict == "BLOCKED":
        grade, render = "BLOCKED_AT_SOURCE", False
    else:
        # checked and not found is NOT the same as never checked -- say so
        grade, render = "REPORTED_VERIFICATION_ATTEMPTED_NOT_FOUND", False
    return {
        "county": (lead or v).get("county"),
        "jurisdiction": v.get("jurisdiction") or (lead or {}).get("jurisdiction"),
        "lead_action_type": (lead or {}).get("action_type") or v.get("original_action_type"),
        "lead_instrument": (lead or {}).get("instrument"),
        "lead_url": (lead or {}).get("url"),
        "verdict": verdict,
        "confirmed_action_type": v.get("confirmed_action_type"),
        "verified_instrument": v.get("instrument"),
        "verified_observed_date": v.get("observed_date"),
        "verified_effective_from": v.get("effective_from"),
        "verified_effective_to": v.get("effective_to"),
        "expiry_condition_verbatim": v.get("expiry_condition_verbatim"),
        "verbatim_snippet": v.get("verbatim_snippet"),
        "official_url": v.get("official_url"),
        "date_note": v.get("date_note"),
        "verification_note": v.get("verification_note"),
        "final_evidence_grade": grade,
        "posture_renderable": render,
        "match_method": how,
        "verify_group": v.get("_group"),
        "_verified_at": v.get("_pulled_at"),
        "_assembled_at": NOW,
    }


rows = [resolve(l, v, how) for l, v, how in pairs]
rows += [resolve(None, v, "no_matching_lead") for v in unmatched_v]

# gate: the two known misattributions MUST come out non-renderable, or the load is wrong
bad = [r for r in rows if r["county"] in ("Brown", "Clay") and r["verdict"] == "CONTRADICTED"]
assert len(bad) == 2, f"expected Brown+Clay CONTRADICTED, got {[(b['county']) for b in bad]}"
assert all(not b["posture_renderable"] for b in bad), "a misattributed lead is still renderable"
print(f"\ngate passed: Brown and Clay are CONTRADICTED and non-renderable")


def load(name, data, cols, source, method, notes):
    out = [{c: (None if r.get(c) is None else
                (r.get(c) if isinstance(r.get(c), bool) else str(r.get(c)))) for c in cols}
           for r in data]
    schema = [bigquery.SchemaField(
        c, "BOOL" if c == "posture_renderable" else "STRING") for c in cols]
    client.load_table_from_json(
        out, f"{DS}.{name}",
        job_config=bigquery.LoadJobConfig(
            schema=schema, write_disposition="WRITE_TRUNCATE")).result()
    got = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.{name}`"))[0].n
    print(f"loaded {got:,} rows -> {name}")
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{name}'").result()
    client.query(
        f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
        f"VALUES (@t,@s,@m,@n,0.0,CURRENT_TIMESTAMP(),@no)",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", name),
            bigquery.ScalarQueryParameter("s", "STRING", source),
            bigquery.ScalarQueryParameter("m", "STRING", method),
            bigquery.ScalarQueryParameter("n", "INT64", int(got)),
            bigquery.ScalarQueryParameter("no", "STRING", notes)])).result()
    print(f"registered {name}")
    return got


n_res = load("in_dc_actions_resolved", rows, COLS,
    "Indiana county/municipal government websites — official-source verification of the sweep's "
    "REPORTED_NEEDS_VERIFICATION leads (4 agents, 46 counties)",
    "Each lead re-checked against the government's OWN site, minutes, agenda or ordinance PDF. "
    "robots.txt read per host before any fetch; crawl-delays honoured (up to 300s); honest UA. "
    "Verdicts: VERIFIED_AT_OFFICIAL_SOURCE / NOT_FOUND_AT_OFFICIAL_SOURCE / CONTRADICTED / BLOCKED.",
    "READ posture_renderable BEFORE RENDERING ANYTHING. It is TRUE only where a government "
    "source was actually fetched and quoted. CONTRADICTED rows are MISATTRIBUTED OUT-OF-STATE "
    "leads — Brown County's action belongs to Brown County WISCONSIN and Clay County's to Clay "
    "County FLORIDA; both were live in the app as Indiana postures. "
    "NOT_FOUND means checked-and-absent, which is NOT the same as never-checked and must not be "
    "scored as permissive. match_method records how each verification was tied to its lead: "
    "(county, action_type) is NOT unique — 9 keys carry multiple rows on both sides.")

# the walls are evidence for the operator's robots-vs-terms ruling; keep them addressable
wrows = [{"host": w.get("host"), "wall_verbatim": w.get("wall_verbatim"),
          "verify_group": w.get("_group"), "_assembled_at": NOW} for w in walls]
if wrows:
    load("in_dc_actions_verify_walls", wrows,
         ["host", "wall_verbatim", "verify_group", "_assembled_at"],
         "robots.txt and HTTP refusals encountered during official-source verification",
         "Every wall quoted verbatim; no wall worked around, no challenge solved, no UA spoofed.",
         "Evidence for the outstanding robots-vs-terms ruling: several hosts disallow ClaudeBot, "
         "Claude-Web and anthropic-ai BY NAME while serving the public freely in a browser.")

print("\n=== what changed ===")
for r in client.query(f"""SELECT final_evidence_grade, COUNT(*) n,
  COUNTIF(posture_renderable) renderable FROM `{DS}.in_dc_actions_resolved`
  GROUP BY 1 ORDER BY n DESC"""):
    print(f"  {r.final_evidence_grade:46s} {r.n:>3}  renderable={r.renderable}")
