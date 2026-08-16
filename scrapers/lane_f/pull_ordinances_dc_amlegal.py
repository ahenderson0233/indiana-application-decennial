"""STAGE 2 of pull_ordinances_dc.py -- American Legal Publishing, the 230-client Indiana gap.

WHY THIS EXISTS. Municode has 45 Indiana clients. American Legal Publishing has 230, of which
33 are COUNTY governments -- including Greene and Hendricks, the two counties Municode cannot
assess at all because their only Municode client hosts no searchable code. Leaving amlegal at
"BLOCKED" would have understated Indiana coverage by design.

WHAT IS BLOCKED AND STAYS BLOCKED. amlegal's /api/search/ is unusable and is NOT worked around:
  * Cloudflare serves a managed JS challenge ("Enable JavaScript and cookies to continue")
    under automated access, and
  * the search cannot be scoped to Indiana at all -- includeRegions / includeClients / clients
    / regions each either return HTTP 500 or are silently ignored, returning national results.
    A scoped query is simply not expressible.
No challenge is solved, no fingerprint is spoofed, no browser is driven at it.

WHAT IS PERMITTED, AND IS USED HERE. amlegal's robots.txt grants `User-agent: * / Allow: /`,
and two READ endpoints are public, unauthenticated and un-challenged at a polite rate:
    /api/client-version/{slug}/latest/   -> currency_info + top-level table of contents
    /api/section-toc/{id}/               -> the chapters inside one title
`currency_info` is the PUBLISHER'S OWN sentence, e.g. "Current through Ord. 2023-18, passed
10-3-2023". That is the observed date the brief asks for; `_pulled_at` stays separate.

HONEST LIMIT OF THIS INSTRUMENT. This reads STRUCTURE (title and chapter names), not body text.
It finds a code that names data centres in a heading -- "CHAPTER 157: DATA CENTERS" -- and it
CANNOT see a data-centre line inside a zoning permitted-use table. So a null here is recorded
as TOC_SCANNED_NO_NAMED_CHAPTER, which is deliberately NOT the same claim as "this county is
silent on data centres". Only the Municode rows carry full-text evidence.

SAFETY. 4.5s between requests; exponential backoff on 403/429; and if the challenge rate
exceeds 20% of requests the run ABORTS and records the source BLOCKED rather than pushing.
"""
import datetime, json, re, sys, time, urllib.error, urllib.parse, urllib.request
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
AM = "https://codelibrary.amlegal.com"
UA = {"User-Agent": "decennial-indiana-siting/1.0 (research; contact ahenderson@decennialgroup.com)"}

# The first run at 4.5s tripped the >20% challenge guard after 9 clients and aborted, which is
# the designed behaviour. The correct response to a host pushing back is to go SLOWER and ask
# for LESS -- never to push harder or to defeat the challenge. So: `--pause 10 --counties-only`
# retries just the 33 county governments (the clients that map to a county with certainty)
# at more than double the spacing.
PAUSE = float(sys.argv[sys.argv.index("--pause") + 1]) if "--pause" in sys.argv else 4.5
COUNTIES_ONLY = "--counties-only" in sys.argv
PULLED = datetime.datetime.now(datetime.timezone.utc).isoformat()
client = bigquery.Client(project="energy-platfrom")

# same vocabulary as stage 1, matched against heading text
VOCAB_RE = re.compile(
    r"data\s*cent(er|re)|datacent(er|re)|data\s*processing|computer\s*cent(er|re)|"
    r"computing\s*facilit|high\s*density\s*computing|server\s*farm|telecommunications?\s*facilit|"
    r"technology\s*park|crypto|digital\s*asset|blockchain|bitcoin|colocation|co-location|"
    r"web\s*hosting|hyperscale|mining\s*facilit", re.I)
# which titles are worth descending into
LANDUSE_RE = re.compile(r"land\s*usage|zoning|planning|land\s*use|building|development", re.I)

stats = {"req": 0, "challenge": 0, "err": 0}


def get(url, tries=4):
    """Transient-only retry. A Cloudflare challenge is a WALL: counted, returned, never retried
    into and never circumvented."""
    last = None
    for i in range(tries):
        stats["req"] += 1
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return {"ok": True, "data": json.loads(r.read().decode("utf-8", "replace"))}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if "Just a moment" in body:
                stats["challenge"] += 1
                return {"ok": False, "wall": "CLOUDFLARE_MANAGED_CHALLENGE: "
                                             "Enable JavaScript and cookies to continue"}
            if e.code in (429, 500, 502, 503, 504):
                last = f"HTTP {e.code}"
                time.sleep(PAUSE * 2 * (i + 1))
                continue
            return {"ok": False, "wall": f"HTTP {e.code}: {body[:200]}".replace("\n", " ")}
        except Exception as e:
            last = str(e)[:120]
            time.sleep(PAUSE * 2 * (i + 1))
    stats["err"] += 1
    return {"ok": False, "wall": f"gave up after {tries}: {last}"}


def safe(k):
    s = "".join(c if (c.isalnum() or c == "_") else "_" for c in str(k))
    return ("_" + s) if (not s or s[0].isdigit()) else s


# --------------------------------------------------------- Indiana client list
r = get(f"{AM}/api/clients-search/")
if not r["ok"]:
    sys.exit(f"FATAL: amlegal client list unreachable: {r['wall']}")
IN = [c for c in r["data"] if (c.get("region") or {}).get("slug") == "in"]
ALL_IN = len(IN)
if COUNTIES_ONLY:
    IN = [c for c in IN if c["name"].endswith(" County")]
print(f"amlegal Indiana clients: {ALL_IN}"
      f"{f' -- COUNTIES ONLY: {len(IN)}' if COUNTIES_ONLY else ''}  (pause {PAUSE}s)", flush=True)
time.sleep(PAUSE)

rows, cov = [], []
for i, c in enumerate(IN, 1):
    slug, name = c["slug"], c["name"]
    d = get(f"{AM}/api/client-version/{urllib.parse.quote(slug)}/latest/")
    time.sleep(PAUSE)
    if not d["ok"]:
        cov.append({"jurisdiction": name, "slug": slug, "status": "BLOCKED",
                    "detail": d["wall"], "currency_info": None, "n_named": 0, "_pulled_at": PULLED})
        print(f"  [{i}/{len(IN)}] {name:<26} BLOCKED {d['wall'][:60]}", flush=True)
        if stats["challenge"] > 0.20 * max(stats["req"], 1) and stats["req"] > 25:
            print("\n*** challenge rate >20% -- ABORTING rather than pushing. "
                  "Remaining clients recorded NOT_ATTEMPTED. ***", flush=True)
            for c2 in IN[i:]:
                cov.append({"jurisdiction": c2["name"], "slug": c2["slug"],
                            "status": "NOT_ATTEMPTED_RUN_ABORTED",
                            "detail": "run aborted after Cloudflare challenge rate exceeded 20%",
                            "currency_info": None, "n_named": 0, "_pulled_at": PULLED})
            break
        continue

    v = d["data"]
    currency = v.get("currency_info")
    named = []

    # top level: titles
    titles = []
    for t in v.get("toc") or []:
        for s in t.get("sections") or []:
            titles.append(s)
            if VOCAB_RE.search(s.get("title") or ""):
                named.append(("title", s))

    # descend only into land-use-ish titles -- the chapters are where a data-centre
    # chapter would be named
    for s in titles:
        if not s.get("has_children") or not LANDUSE_RE.search(s.get("title") or ""):
            continue
        dd = get(f"{AM}/api/section-toc/{s['id']}/")
        time.sleep(PAUSE)
        if not dd["ok"]:
            continue
        for ch in dd["data"].get("children") or []:
            if VOCAB_RE.search(ch.get("title") or ""):
                named.append(("chapter", ch))

    for kind, s in named:
        rows.append({
            "jurisdiction": name, "slug": slug, "state": "IN",
            "provider": "american_legal_publishing",
            "level": kind,
            "code_name": v.get("name"),
            "code_uuid": v.get("uuid"),
            "section_id": str(s.get("id") or ""),
            "doc_id": s.get("doc_id"),
            "section_title": s.get("title"),
            "has_children": str(s.get("has_children")),
            "currency_info": currency,          # PUBLISHER'S OWN DATE, verbatim
            "observed_date_source": "amlegal client-version currency_info",
            "url": f"{AM}/codes/{slug}/latest/{v.get('uuid')}/{s.get('doc_id')}",
            "raw": json.dumps(s),
            "evidence_level": "HEADING_ONLY -- structure scan, not full text",
            "_pulled_at": PULLED,
            "_source_endpoint": f"{AM}/api/client-version/ + /api/section-toc/",
        })

    cov.append({"jurisdiction": name, "slug": slug,
                "status": "NAMED_PROVISION_FOUND" if named else "TOC_SCANNED_NO_NAMED_CHAPTER",
                "detail": f"{len(titles)} titles scanned; heading-level scan only -- a "
                          f"permitted-use-table entry would not be visible here",
                "currency_info": currency, "n_named": len(named), "_pulled_at": PULLED})
    flag = f"  <-- {len(named)} NAMED" if named else ""
    print(f"  [{i}/{len(IN)}] {name:<26} {str(currency)[:52]:<52}{flag}", flush=True)

# municipalities deliberately not attempted in counties-only mode are recorded as such, so the
# coverage table never implies they were searched and found silent
if COUNTIES_ONLY:
    done = {c["slug"] for c in IN}
    for c2 in r["data"]:
        if (c2.get("region") or {}).get("slug") == "in" and c2["slug"] not in done:
            cov.append({"jurisdiction": c2["name"], "slug": c2["slug"],
                        "status": "NOT_ATTEMPTED_RATE_LIMITED",
                        "detail": "amlegal challenged automated access at 4.5s spacing; this run "
                                  "was narrowed to county governments at slower spacing rather "
                                  "than pushing harder. Municipality not searched.",
                        "currency_info": None, "n_named": 0, "_pulled_at": PULLED})

print(f"\nrequests={stats['req']} challenges={stats['challenge']} errors={stats['err']}", flush=True)
print(f"named-provision rows: {len(rows)}", flush=True)


def load(table, data, method):
    if not data:
        print(f"  (no rows for {table})", flush=True)
        return 0
    norm = [{safe(k): (None if v is None else str(v)) for k, v in r.items()} for r in data]
    keys = sorted({k for r in norm for k in r})
    client.load_table_from_json(
        [{k: r.get(k) for k in keys} for r in norm], f"{DS}.{table}",
        job_config=bigquery.LoadJobConfig(
            schema=[bigquery.SchemaField(k, "STRING") for k in keys],
            write_disposition="WRITE_TRUNCATE")).result()
    n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.{table}`"))[0].n
    print(f"  loaded {n:,} rows x {len(keys)} cols -> {table}", flush=True)
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{table}'").result()
    client.query(
        f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at, notes) "
        f"VALUES (@t,@s,@m,@n,CURRENT_TIMESTAMP(),@no)",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", table),
            bigquery.ScalarQueryParameter("s", "STRING", f"{AM}/api/client-version/"),
            bigquery.ScalarQueryParameter("m", "STRING", method),
            bigquery.ScalarQueryParameter("n", "INT64", int(n)),
            bigquery.ScalarQueryParameter("no", "STRING",
                "HEADING-LEVEL EVIDENCE ONLY. amlegal full-text search is Cloudflare-walled and "
                "unscopable, so this scans title/chapter NAMES. A null here means no NAMED "
                "chapter -- it is NOT evidence that the jurisdiction is silent on data centres. "
                "Do not merge with in_ordinances_dc_v2 (full-text) without carrying "
                "evidence_level.")])).result()
    print(f"    registered {table}", flush=True)
    return n


print("\n=== LOAD ===", flush=True)
n1 = load("in_ordinances_amlegal_named_v2", rows,
          "American Legal Publishing Indiana: heading-level scan for data-centre vocabulary "
          "across title and chapter names, via public /api/client-version/{slug}/latest/ and "
          "/api/section-toc/{id}/. Publisher's own currency_info carried verbatim. Full-text "
          "search NOT used: Cloudflare-walled and unscopable, recorded not circumvented.")
n2 = load("in_ordinances_amlegal_coverage_v2", cov,
          "Per-jurisdiction outcome of the amlegal heading scan, incl. the publisher's own "
          "currency_info for each of the Indiana clients reached. Statuses: "
          "NAMED_PROVISION_FOUND / TOC_SCANNED_NO_NAMED_CHAPTER / BLOCKED / "
          "NOT_ATTEMPTED_RUN_ABORTED.")

client.query(
    "INSERT INTO `energy-platfrom.energy.registry_sources` "
    "(source_name, status, endpoint, endpoint_kind, acquisition_method, object_names, "
    " updated_by, geography_state, last_validated_at) "
    "VALUES (@n,@s,@e,@k,@m,@o,'indiana-app-ordinances-agent','IN',CURRENT_TIMESTAMP())",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter(
            "n", "STRING", "American Legal Publishing Indiana codes -- heading scan (search walled)"),
        bigquery.ScalarQueryParameter("s", "STRING", "PARTIAL"),
        bigquery.ScalarQueryParameter("e", "STRING", f"{AM}/api/client-version/"),
        bigquery.ScalarQueryParameter("k", "STRING", "rest_json"),
        bigquery.ScalarQueryParameter(
            "m", "STRING",
            "public un-authenticated TOC endpoints at 4.5s spacing; heading-level evidence only; "
            "/api/search/ left untouched because it is Cloudflare-challenged AND unscopable"),
        bigquery.ArrayQueryParameter(
            "o", "STRING", ["in_ordinances_amlegal_named_v2", "in_ordinances_amlegal_coverage_v2"])])).result()

got_date = sum(1 for c in cov if c["currency_info"])
print(f"""
================= AMLEGAL RESULT =================
Indiana clients listed      : {len(IN)}
reached (TOC read)          : {sum(1 for c in cov if c['status'].startswith(('NAMED','TOC')))}
publisher date captured     : {got_date}
named data-centre headings  : {n1} rows across "
      "{len({r['jurisdiction'] for r in rows})} jurisdictions
blocked / not attempted     : {sum(1 for c in cov if c['status'] in ('BLOCKED','NOT_ATTEMPTED_RUN_ABORTED'))}
""")
json.dump(cov, open("amlegal_coverage.json", "w", encoding="utf-8"), indent=1)
