"""Load the codified-ordinance sweep of the 55 counties no publisher could reach.

THE GAP THIS CLOSES. Municode assessed 37 of Indiana's 92 counties. American Legal hosts 230
Indiana jurisdictions but is BLOCKED — its robots.txt grants access while the ICC terms forbid
"data mining, robots, or similar data gathering and extraction tools", so 55 counties had never
been searched for a codified data-centre provision at all. Those 55 were recorded NOT_SEARCHED and
were never, at any point, to be read as silent.

This went to the counties themselves rather than to a publisher — a county's own website is the
issuing government's channel, not ICC E-Content. All 55 attempted, all 55 recorded.

THE RESULT, and it is the same shape the county-website sweep found: THREE counties name a data
centre, ALL via 2026 instruments on their own sites, NONE visible to any code publisher. Hancock
Ordinance 2026-6E amends the codified county code with a 'Data Center' definition (server farms,
AI training, cloud), permits it P2 in Industrial General ONLY, and creates a Data Center Overlay
District requiring both declaratory and confirmatory commissioner resolutions.

THE CONTROL CHECK IS WHY THE NEGATIVES ARE WORTH ANYTHING. Before recording "no data-centre
provision" for a county, the agent searched a word that cannot be absent from a zoning code —
zoning, building, setback. A county whose control returns nothing has a broken instrument, not a
silent code, and is recorded NOT_SEARCHABLE. Skipping that check injected seven fabricated
postures in an earlier run.

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

d = json.loads(open(os.path.join(HERE, "county_codified_ordinances.json"), encoding="utf-8").read())
cov, prov, walls = d.get("coverage", []), d.get("provisions", []), d.get("walls", [])
print(f"read {len(cov)} coverage rows · {len(prov)} provisions · {len(walls)} walls")

CCOLS = ["county", "code_host", "code_url", "status", "control_words_tested", "control_passed",
         "codified_through_text", "vocabularies_run", "notes", "_pulled_at", "_assembled_at"]
PCOLS = ["county", "jurisdiction", "section", "snippet", "url", "search_phrase",
         "posture_terms_found", "_pulled_at", "_assembled_at"]
WCOLS = ["host", "wall_verbatim", "_assembled_at"]


def load(name, rows, cols, source, method, notes):
    out = []
    for r in rows:
        rec = {}
        for c in cols:
            v = r.get(c)
            if isinstance(v, (list, dict)):
                v = json.dumps(v, ensure_ascii=False)
            rec[c] = None if v is None else str(v)
        rec["_assembled_at"] = NOW
        out.append(rec)
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


load("in_ordinances_county_codified", cov, CCOLS,
     "the 55 Indiana counties' OWN websites — the counties no code publisher could reach",
     "Municode covers 37 of 92; American Legal is BLOCKED by its terms. These 55 went to the "
     "issuing governments directly. robots.txt read per host before any fetch; crawl-delays "
     "honoured; vocabularies limited to the three that produced hits statewide (data center, "
     "data processing, telecommunications facility) because crypto/blockchain/server farm/"
     "colocation/hyperscale returned ZERO across the entire state.",
     "READ control_passed BEFORE TRUSTING A NEGATIVE. A county is only 'silent' if a control word "
     "that cannot be absent from a zoning code (zoning, building, setback) returned results and "
     "the data-centre vocabulary did not. control_passed=None means no search ran — BLOCKED or "
     "NOT_REACHABLE — and those must NEVER be scored as permissive. Omitting this check injected "
     "seven fabricated postures in an earlier run.")

if prov:
    load("in_ordinances_county_codified_provisions", prov, PCOLS,
         "county websites — the codified sections that actually name a data centre",
         "Verbatim snippet plus the publisher's own currency sentence where stated.",
         "THREE counties, ALL via 2026 instruments on their own sites, NONE visible to any code "
         "publisher — the same finding the county-website sweep produced, now confirmed on the "
         "codified side. Hancock Ordinance 2026-6E defines 'Data Center' (server farms, AI "
         "training, cloud), permits it P2 in Industrial General ONLY, and creates a Data Center "
         "Overlay District requiring declaratory AND confirmatory commissioner resolutions.")

if walls:
    load("in_ordinances_county_codified_walls", walls, WCOLS,
         "robots.txt and HTTP refusals during the 55-county codified sweep",
         "Quoted verbatim; nothing worked around.",
         "More evidence for the outstanding robots-vs-terms ruling.")

print("\n=== coverage of the 55 ===")
for r in client.query(f"""SELECT status, COUNT(*) n,
  COUNTIF(control_passed = 'True') control_ok
FROM `{DS}.in_ordinances_county_codified` GROUP BY 1 ORDER BY n DESC"""):
    print(f"  {r.status:26s} {r.n:>3}  (control passed on {r.control_ok})")

print("\n=== statewide codified coverage, before and after ===")
print("  before: 37 of 92 counties assessed, 55 NOT_SEARCHED")
print("  after : 92 of 92 attempted — but read the status: a BLOCKED or NOT_REACHABLE county")
print("          is still NOT a silent one, and 17 of these 55 ran no search at all")
