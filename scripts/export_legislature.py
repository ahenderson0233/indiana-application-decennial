"""A1 — export the openstates legislative family for the P7 preview on Community.

Measured first (nothing here is assumed):
  · `in_openstates_energy_bills` (21) is a STRICT SUBSET of `_v2` (66): shared 21, only-in-v1 0.
    v1 is superseded, so it takes a logged WAIVER rather than a feature — the pattern the build
    spec §0.2 names explicitly ("the successor must be wired and the waiver logged").
  · Referential integrity is total: 0 orphans across actions/votes/sponsorships/versions/
    abstracts/sources, and all 9,197 roll-call rows reach one of the 126 vote events.
  · `match_field` is the SUBJECT-SELECTION INSTRUMENT — how a bill was judged to be an energy
    bill (abstract 44 · title,abstract 14 · title,subject,abstract 4 · title 3 · subject,abstract 1).
    It is carried to the screen: a bill matched only on its abstract is a weaker claim to the
    subject than one matching title AND subject AND abstract, and the reader should see which.

Read-only. Writes data/legislature.json.gz. Idempotent.
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
import json, gzip, os, ast, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)
def rows(sql): return [dict(r) for r in client.query(sql)]

def pylist(s):
    """openstates stores list columns as a Python repr string: "['bill']". Parse, don't regex."""
    if not s: return []
    try:
        v = ast.literal_eval(s)
        return [str(x) for x in v] if isinstance(v, (list, tuple)) else [str(v)]
    except (ValueError, SyntaxError):
        return [str(s)]

# BigQuery cannot de-correlate a `LIMIT 1` subquery over another table, so pre-aggregate the
# one-per-bill picks and LEFT JOIN them instead.
bills = rows(f"""
  WITH abs AS (
    SELECT bill_id, ANY_VALUE(abstract) AS abstract
    FROM `{DS}.in_openstates_energy_bill_abstracts` GROUP BY bill_id),
  src AS (
    SELECT bill_id, MIN(url) AS source_url
    FROM `{DS}.in_openstates_energy_bill_sources` WHERE url IS NOT NULL GROUP BY bill_id)
  SELECT b.id, b.identifier, b.title, b.session, b.organization_classification AS chamber,
         b.match_field, b.subject, b.classification, abs.abstract, src.source_url
  FROM `{DS}.in_openstates_energy_bills_v2` b
  LEFT JOIN abs ON abs.bill_id = b.id
  LEFT JOIN src ON src.bill_id = b.id
  ORDER BY b.session DESC, b.identifier""")
for b in bills:
    b["subject"] = pylist(b.pop("subject"))
    b["classification"] = pylist(b.pop("classification"))
    b["match_on"] = (b.pop("match_field") or "").split(",")

def group(sql, key="bill_id"):
    out = {}
    for r in rows(sql):
        out.setdefault(r.pop(key), []).append(r)
    return out

actions = group(f"""
  SELECT bill_id, description, CAST(date AS STRING) date, classification, SAFE_CAST(`order` AS INT64) ord
  FROM `{DS}.in_openstates_energy_bill_actions` ORDER BY bill_id, SAFE_CAST(`order` AS INT64)""")
for lst in actions.values():
    for a in lst: a["classification"] = pylist(a.get("classification"))

sponsors = group(f"""
  SELECT bill_id, name, classification, `primary` AS is_primary, entity_type
  FROM `{DS}.in_openstates_energy_bill_sponsorships`
  ORDER BY bill_id, `primary` DESC, name""")

versions = group(f"""
  SELECT bill_id, note, CAST(date AS STRING) date, link_urls, link_media_types
  FROM `{DS}.in_openstates_energy_bill_versions` ORDER BY bill_id, note""")

sources = group(f"""
  SELECT bill_id, url, note FROM `{DS}.in_openstates_energy_bill_sources` ORDER BY bill_id""")

votes = rows(f"""
  SELECT id, bill_id, motion_text, motion_classification, CAST(start_date AS STRING) start_date,
         -- `no` is a BigQuery reserved word (same trap as `rows` and `FULL`); alias it away
         result, SAFE_CAST(count_yes AS INT64) yea, SAFE_CAST(count_no AS INT64) nay,
         SAFE_CAST(count_other AS INT64) other_ct, session
  FROM `{DS}.in_openstates_energy_bill_votes` ORDER BY start_date""")
for v in votes: v["motion_classification"] = pylist(v.pop("motion_classification"))
votes_by_bill = {}
for v in votes: votes_by_bill.setdefault(v["bill_id"], []).append(v)

# the roll call: 9,197 rows. Keep name + option only; that is what a reader needs.
rollcall = {}
for r in rows(f"""
    SELECT vote_event_id, voter_name, option FROM `{DS}.in_openstates_energy_bill_vote_people`
    ORDER BY vote_event_id, option, voter_name"""):
    rollcall.setdefault(r["vote_event_id"], []).append([r["voter_name"], r["option"]])

DC_RE = ("data cent", "data-cent", "large load", "server farm")
for b in bills:
    hay = (str(b["title"]) + " " + " ".join(b["subject"])).lower()
    b["is_dc"] = any(k in hay for k in DC_RE)

payload = {
    "bills": bills, "actions": actions, "sponsors": sponsors, "versions": versions,
    "sources": sources, "votes_by_bill": votes_by_bill, "rollcall": rollcall,
    "counts": {"bills": len(bills), "dc_bills": sum(1 for b in bills if b["is_dc"]),
               "votes": len(votes), "rollcall_rows": sum(len(v) for v in rollcall.values()),
               "actions": sum(len(v) for v in actions.values()),
               "sponsors": sum(len(v) for v in sponsors.values()),
               "versions": sum(len(v) for v in versions.values()),
               "sources": sum(len(v) for v in sources.values()),
               "bills_with_votes": len(votes_by_bill)},
    "waiver": {"table": "in_openstates_energy_bills",
               "reason": "superseded by in_openstates_energy_bills_v2 — measured a STRICT SUBSET "
                         "(21 of 66 ids, 0 ids unique to v1). Build spec §0.2: the successor is "
                         "wired and the waiver is logged."},
}
p = os.path.join(REPO, "data", "legislature.json.gz")
with gzip.open(p, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(payload, f, separators=(",", ":"), default=jd)
print(f"legislature.json.gz {os.path.getsize(p)/1024:.0f} KB · " +
      " · ".join(f"{k} {v}" for k, v in payload["counts"].items()))
