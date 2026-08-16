"""Indiana LOCAL data-centre zoning/ordinance text -- v2. ALL FIELDS, ALL VOCABULARIES.

THE PROBLEM THIS SOLVES. `in_ordinances_dc` holds FOUR rows for a 92-county state. Three
defects produced that number, and this loader tests all three rather than assuming any:

  1. ONE PUBLISHER. The v1 pull searched Municode only. Municode has 45 Indiana clients.
     American Legal Publishing has 230 Indiana clients -- 5x the footprint -- and its public
     client list is pulled here so the gap is a measured number, not a guess.

  2. ONE PHRASE. v1 searched the quoted phrases "data center"/"data centers". Measured on
     St. Joseph County: quoted "data center" = 2 hits, unquoted data center = 7. The quotes
     alone cost >3x recall on the one client we know has an ordinance. This loader sweeps 19
     vocabularies and records `phrase_mode` so precision and recall stay separable.

  3. A ZERO WAS READ AS SILENCE. Carmel returned 0 for "data center" -- and also 0 for
     "zoning", "building" and "ordinance", words that cannot be absent from a municipal code.
     Carmel hosts no searchable CODE product on Municode at all. SEVEN of the 45 clients are
     like this (Avon, Bluffton, Carmel, Linton, Milford, Parke County, Scottsburg). Without the
     calibration pass below, all seven would have been recorded as "no data-centre provision"
     -- i.e. as PERMISSIVE posture -- which is a fabricated signal. The calibration runs first
     and every later zero is qualified by it.

WHAT "OBSERVED DATE" MEANS HERE. Municode states its own currency per code product at
`/Jobs/latest/{productId}`: PublishDate, OnlineDate, and a BannerText reading e.g. "Codified
through Ordinance No. 48-25, enacted July 15, 2025. (Supp. No. 3)". That publisher sentence is
carried verbatim in `codified_through_text`. `_pulled_at` is this run's clock and is never
mixed with it.

POSTURE IS NOT SCORED. `posture_terms_found` lists which of the publisher's OWN phrases
("permitted by right", "special exception", "conditional use", "prohibited", "moratorium", ...)
appear in the hit, verbatim. No scale is invented; the fragment is kept whole so a human can
read the actual words.

Rules honoured: robots.txt read for every host before any request (see ORDINANCE_FINDINGS.md
for each verbatim wall); identifying User-Agent; >=1.1s between requests and a slow lane for
hosts that escalate; no account, no login, no API key, no CAPTCHA, no paywall circumvention;
a gated source is RECORDED, never worked around; ALL fields kept from every response; writes
only to energy-platfrom.indiana_app; `in_ordinances_dc` is left untouched so v1 stays
comparable; registered in the SAME run that writes.
"""
import datetime, json, re, sys, time, urllib.error, urllib.parse, urllib.request
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
MUNI = "https://api.municode.com"
AMLEGAL = "https://codelibrary.amlegal.com"
UA = {"User-Agent": "decennial-indiana-siting/1.0 (research; contact ahenderson@decennialgroup.com)"}
PAUSE = 1.1
PAGE = 25
PULLED = datetime.datetime.now(datetime.timezone.utc).isoformat()
client = bigquery.Client(project="energy-platfrom")

# ---------------------------------------------------------------- vocabularies
# (phrase, mode). exact = quoted, the defensible verbatim hit. loose = unquoted, higher recall
# and more noise; kept as its OWN rows so the recall gap is measurable rather than blended.
VOCAB = [
    ('"data center"', "exact"), ('"data centers"', "exact"), ('"datacenter"', "exact"),
    ('"data processing"', "exact"), ('"computer center"', "exact"),
    ('"computing facility"', "exact"), ('"high density computing"', "exact"),
    ('"server farm"', "exact"), ('"telecommunications facility"', "exact"),
    ('"technology park"', "exact"), ('"cryptocurrency mining"', "exact"),
    ('"cryptocurrency"', "exact"), ('"digital asset mining"', "exact"),
    ('"blockchain"', "exact"), ('"bitcoin"', "exact"), ('"colocation"', "exact"),
    ('"web hosting"', "exact"), ('"hyperscale"', "exact"),
    ("data center", "loose"),          # the measured recall gap against '"data center"'
]
CONTROLS = ["zoning", "building", "ordinance"]   # calibration: does this client host a CODE?

# publisher's own posture words. Presence is recorded; nothing is scored or ranked.
POSTURE_TERMS = [
    "permitted by right", "by right", "permitted use", "permitted uses", "use permitted",
    "special exception", "special use", "conditional use", "conditionally permitted",
    "prohibited", "not permitted", "moratorium", "accessory use", "accessory structure",
    "planned unit development", "variance", "site plan review", "special land use",
]

# Municode client -> Indiana county. Municode names the county for county clients; for the
# municipalities this is the seat-of-county assignment, carried explicitly so it is auditable
# rather than inferred at query time.
COUNTY = {
    13311: "Hendricks", 13952: "Monroe", 18486: "Wells", 20600: "Elkhart", 13960: "Hamilton",
    18496: "Jackson", 16168: "Benton", 11765: "Johnson", 8694: "Lake", 11531: "Hamilton",
    2720: "Marion", 20514: "Dubois", 2815: "Noble", 2869: "Starke", 11916: "LaPorte",
    11312: "Tippecanoe", 2931: "Lake", 3036: "Greene", 11303: "Morgan", 9088: "Lake",
    3292: "LaPorte", 17788: "Kosciusko", 3333: "St. Joseph", 3446: "Delaware", 9164: "Lake",
    18876: "Noble", 18477: "St. Joseph", 7224: "Parke", 12022: "Porter", 7365: "Porter",
    12730: "Gibson", 4270: "Scott", 4389: "St. Joseph", 9682: "Marion", 14076: "St. Joseph",
    11933: "Kosciusko", 11579: "Tipton", 16864: "Ripley", 4769: "Wabash", 13522: "LaPorte",
    4808: "Kosciusko", 4888: "Tippecanoe", 9966: "Hamilton", 4944: "Lake", 10023: "Kosciusko",
}

TAG = re.compile(r"<[^>]+>")
# publisher's own ordinance citation inside the fragment: "(Ord. No. 48-25, § 2, 7-15-2025)"
ORD_CITE = re.compile(
    r"\(?\s*(Ord(?:inance)?\.?\s*(?:No\.?)?\s*[\w\-.]+[^)]{0,60}?"
    r"(\d{1,2}-\d{1,2}-\d{2,4}|\d{4}))\s*\)?", re.I)


def get(url, tries=5, slow=False):
    """Bounded retry on transient transport failures ONLY -- never on a refusal.

    A 401/403 is a wall and is returned as data so the caller can record it verbatim; retrying
    a refusal is how a scraper turns a 'no' into a rate-limit incident.
    """
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                body = r.read().decode("utf-8", "replace")
                try:
                    return {"_ok": True, "data": json.loads(body)}
                except json.JSONDecodeError:
                    return {"_ok": True, "data": None, "_raw": body[:2000]}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code in (500, 502, 503, 504, 429):
                last = f"HTTP {e.code}"
                time.sleep((6 if slow else 2) * (i + 1))
                continue
            wall = ("CLOUDFLARE_MANAGED_CHALLENGE: Enable JavaScript and cookies to continue"
                    if "Just a moment" in body else body[:400].replace("\n", " ").strip())
            return {"_ok": False, "http": e.code, "wall": wall}
        except Exception as e:
            last = str(e)[:120]
            time.sleep((6 if slow else 2) * (i + 1))
    return {"_ok": False, "http": None, "wall": f"gave up after {tries} attempts: {last}"}


def clean(s):
    return re.sub(r"\s+", " ", TAG.sub(" ", s or "")).strip()


def safe(k):
    s = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in str(k))
    return ("_" + s) if (not s or s[0].isdigit()) else s


def muni_slug(name):
    """'Indianapolis - Marion County' -> 'indianapolis_marion_county'. Collapse runs of
    separators to ONE underscore: the naive replace chain produced 'indianapolis___marion_county'."""
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", name.lower())).strip("_")


# =============================================================== 1. CLIENT LIST
print("=== Municode: Indiana clients ===", flush=True)
r = get(f"{MUNI}/Clients/stateAbbr?stateAbbr=IN")
if not r["_ok"]:
    sys.exit(f"FATAL: client list unreachable: {r['wall']}")
clients = r["data"]
print(f"  {len(clients)} Indiana clients", flush=True)

# ============================================ 2. CALIBRATION -- is a CODE there?
print("\n=== CALIBRATION: which clients host a searchable CODE? ===", flush=True)
cal = {}
for c in clients:
    cid = c["ClientID"]
    counts, product = {}, None
    for w in CONTROLS:
        d = get(f"{MUNI}/search?clientId={cid}&searchText={urllib.parse.quote(w)}"
                f"&pageNum=1&pageSize=1&contentTypeId=CODES")
        if d["_ok"] and d["data"] is not None:
            counts[w] = d["data"].get("NumberOfHits", 0)
            for h in d["data"].get("Hits") or []:
                product = product or (h.get("Product") or {}).get("Id")
        else:
            counts[w] = None
        time.sleep(PAUSE)
    live = any(isinstance(v, int) and v > 0 for v in counts.values())
    cal[cid] = {"control_counts": counts, "code_searchable": live, "product_id": product}
    print(f"  {'CODE' if live else 'NONE'}  {cid:>6} {c['ClientName']:<28} {counts}", flush=True)

live_ids = [c["ClientID"] for c in clients if cal[c["ClientID"]]["code_searchable"]]
print(f"\n  searchable: {len(live_ids)} / {len(clients)}", flush=True)

# ================================== 3. PUBLISHER'S OWN CURRENCY DATE per product
print("\n=== Municode: publisher-stated code currency ===", flush=True)
jobs = {}
for cid in live_ids:
    pid = cal[cid]["product_id"]
    if not pid:
        continue
    d = get(f"{MUNI}/Jobs/latest/{pid}")
    if d["_ok"] and d["data"]:
        jobs[cid] = d["data"]
    time.sleep(PAUSE)
print(f"  currency captured for {len(jobs)} products", flush=True)

# ================================================== 4. VOCABULARY SWEEP -- HITS
print("\n=== VOCABULARY SWEEP ===", flush=True)
hits, coverage, shortfalls = [], [], []
for c in clients:
    cid, cname = c["ClientID"], c["ClientName"]
    if not cal[cid]["code_searchable"]:
        coverage.append({
            "jurisdiction": cname, "client_id": cid, "county": COUNTY.get(cid),
            "provider": "municode", "status": "NOT_REACHABLE_NO_SEARCHABLE_CODE",
            "detail": f"control words returned {cal[cid]['control_counts']} -- client exists in "
                      f"the Municode Indiana client list but hosts no searchable CODES product. "
                      f"This is NOT evidence of a permissive posture.",
            "n_hits": 0, "vocabularies_searched": 0})
        continue

    job = jobs.get(cid, {})
    per_vocab, total = {}, 0
    for phrase, mode in VOCAB:
        d = get(f"{MUNI}/search?clientId={cid}&searchText={urllib.parse.quote(phrase)}"
                f"&pageNum=1&pageSize={PAGE}&contentTypeId=CODES")
        time.sleep(PAUSE)
        if not d["_ok"] or d["data"] is None:
            per_vocab[phrase] = None
            continue
        expected = d["data"].get("NumberOfHits", 0)
        per_vocab[phrase] = expected
        if not expected:
            continue

        collected, page = [], 1
        while len(collected) < expected:
            dd = d if page == 1 else get(
                f"{MUNI}/search?clientId={cid}&searchText={urllib.parse.quote(phrase)}"
                f"&pageNum={page}&pageSize={PAGE}&contentTypeId=CODES")
            if page > 1:
                time.sleep(PAUSE)
            if not dd["_ok"] or dd["data"] is None:
                break
            batch = dd["data"].get("Hits") or []
            if not batch:
                break
            collected.extend(batch)
            page += 1
            if page > 40:
                break
        # SHORTFALL DETECTION against the publisher's own NumberOfHits
        if len(collected) < expected:
            shortfalls.append({"client": cname, "phrase": phrase,
                               "got": len(collected), "expected": expected})

        for h in collected:
            frag_raw = h.get("ContentFragment") or ""
            frag = clean(frag_raw)
            title = h.get("Title") or ""
            hay = f"{title} {frag}".lower()
            m = ORD_CITE.search(frag)
            anc = h.get("Ancestors") or []
            hits.append({
                "jurisdiction": cname,
                "county": COUNTY.get(cid),
                "state": "IN",
                "provider": "municode",
                "client_id": str(cid),
                "client_classification_id": str(c.get("ClassificationId") or ""),
                "client_pop_range_id": str(c.get("PopRangeId") or ""),
                "client_city": c.get("City"),
                "client_zip": str(c.get("ZipCode") or ""),
                "client_website": c.get("Website"),
                "product_id": str((h.get("Product") or {}).get("Id") or ""),
                "product_name": (h.get("Product") or {}).get("Name"),
                "content_type_id": h.get("ContentTypeId"),
                "code_section_id": h.get("NodeId"),
                "section_title": title,
                "snippet": frag,
                "snippet_html_raw": frag_raw,
                "ancestors_path": " > ".join(a.get("Title", "") for a in anc),
                "ancestors_json": json.dumps(anc),
                "relevance_score": str(h.get("RelevanceScore") or ""),
                "search_phrase": phrase,
                "phrase_mode": mode,
                # ---- the publisher's OWN dates. Never this run's clock.
                "codified_through_text": (job.get("BannerText") or "").replace("\r\n", " ").strip() or None,
                "publisher_publish_date": job.get("PublishDate"),
                "publisher_online_date": job.get("OnlineDate"),
                "publisher_online_post_date": job.get("OnlinePostDate"),
                "publisher_max_tracking_date": job.get("MaxTrackingDate"),
                "publisher_supplement_name": job.get("Name"),
                "publisher_job_id": str(job.get("Id") or ""),
                "observed_date_source": ("municode Jobs/latest BannerText + PublishDate"
                                         if job else None),
                "ordinance_citation_in_snippet": m.group(1).strip() if m else None,
                # ---- posture in the publisher's own words. No invented scale.
                "posture_terms_found": ", ".join(t for t in POSTURE_TERMS if t in hay) or None,
                # CONSTRUCTED, not publisher-supplied: Municode's search API returns no library
                # URL. library.municode.com is a SPA that answers HTTP 200 for ANY slug, so the
                # status code cannot validate this -- do not treat a 200 as proof the link
                # resolves. `client_id` + `code_section_id` (NodeId) are the authoritative
                # publisher identifiers and are carried in their own columns.
                "url": f"https://library.municode.com/in/{muni_slug(cname)}"
                       f"/codes/code_of_ordinances?nodeId={h.get('NodeId')}",
                "url_is_constructed": "yes -- slug derived from client name; verify via client_id",
                "raw_hit": json.dumps(h),
                "_pulled_at": PULLED,
                "_source_endpoint": f"{MUNI}/search",
            })
        total += len(collected)

    searched = sum(1 for v in per_vocab.values() if v is not None)
    coverage.append({
        "jurisdiction": cname, "client_id": cid, "county": COUNTY.get(cid),
        "provider": "municode",
        "status": "FOUND" if total else "SEARCHED_NONE_FOUND",
        "detail": json.dumps(per_vocab),
        "n_hits": total, "vocabularies_searched": searched})
    print(f"  {cname:<28} hits={total:<4} "
          f"{ {k: v for k, v in per_vocab.items() if v} }", flush=True)

print(f"\n  total hits: {len(hits)}", flush=True)
if shortfalls:
    print(f"  *** {len(shortfalls)} SHORTFALL(S) vs publisher NumberOfHits: {shortfalls[:6]}")

# ======================================= 5. OTHER PUBLISHERS -- inventory + WALL
print("\n=== Other publishers ===", flush=True)
pubs = []

# American Legal Publishing: the client list endpoint is public; the SEARCH endpoint is not
# usable -- it cannot be scoped (every scoping key returns HTTP 500 or is ignored and returns
# national results) and Cloudflare serves a managed JS challenge under automated access.
# The challenge is a wall: it is RECORDED, not solved.
am = get(f"{AMLEGAL}/api/clients-search/", slow=True)
am_in = []
if am["_ok"] and am["data"]:
    am_in = [x for x in am["data"]
             if (x.get("region") or {}).get("slug") == "in"
             or (x.get("region") or {}).get("name") == "Indiana"]
    print(f"  amlegal: {len(am_in)} Indiana clients listed (public endpoint)", flush=True)
    for x in am_in:
        pubs.append({
            "publisher": "american_legal_publishing", "jurisdiction": x.get("name"),
            "slug": x.get("slug"), "region_slug": (x.get("region") or {}).get("slug"),
            "version_ct": str(x.get("version_ct") or ""),
            "status": "LISTED_SEARCH_BLOCKED",
            "wall_verbatim": "CLOUDFLARE_MANAGED_CHALLENGE on /api/search/: "
                             "'Enable JavaScript and cookies to continue'. Separately, every "
                             "scoping key (includeRegions / includeClients / clients / regions) "
                             "either returns HTTP 500 or is silently ignored and returns "
                             "national results, so an Indiana-only search cannot be expressed.",
            "endpoint": f"{AMLEGAL}/api/search/",
            "raw": json.dumps(x), "_pulled_at": PULLED})
else:
    print(f"  amlegal client list unreachable: {am.get('wall')}", flush=True)
time.sleep(3)

# auth wall, recorded verbatim, never worked around
alt = get(f"{AMLEGAL}/api/all-client-regions/", slow=True)
pubs.append({
    "publisher": "american_legal_publishing", "jurisdiction": None, "slug": None,
    "region_slug": "in", "version_ct": "",
    "status": "BLOCKED_AUTH" if not alt["_ok"] else "OPEN",
    "wall_verbatim": alt.get("wall") if not alt["_ok"] else None,
    "endpoint": f"{AMLEGAL}/api/all-client-regions/", "raw": None, "_pulled_at": PULLED})

for pub, ep, wall in [
    ("code_publishing", "https://www.codepublishing.com/robots.txt",
     "HTTP 403 + Cloudflare managed challenge served on robots.txt ITSELF: "
     "'Enable JavaScript and cookies to continue'. The permission file could not be read, so "
     "no crawl of this host can be justified. Recorded BLOCKED; not worked around."),
    ("general_code_ecode360", "https://ecode360.com/search",
     "robots.txt User-agent: * explicitly contains 'Disallow: /search' and 'Disallow: /search/'. "
     "The search interface is the only systematic route to provisions, and it is disallowed. "
     "No permitted enumeration path for Indiana clients was found (/IN returns an eCode360 "
     "error page). Recorded BLOCKED BY ROBOTS; not worked around."),
]:
    pubs.append({"publisher": pub, "jurisdiction": None, "slug": None, "region_slug": "in",
                 "version_ct": "", "status": "BLOCKED", "wall_verbatim": wall,
                 "endpoint": ep, "raw": None, "_pulled_at": PULLED})

# ==================================================================== 6. LOAD
def load(table, rows, desc):
    if not rows:
        print(f"  (no rows for {table})", flush=True)
        return 0
    norm, renames = [], {}
    for r in rows:
        out = {}
        for k, v in r.items():
            sk = safe(k)
            if sk != k:
                renames[k] = sk
            out[sk] = None if v is None else str(v)
        norm.append(out)
    keys = sorted({k for r in norm for k in r})
    job = client.load_table_from_json(
        [{k: r.get(k) for k in keys} for r in norm], f"{DS}.{table}",
        job_config=bigquery.LoadJobConfig(
            schema=[bigquery.SchemaField(k, "STRING") for k in keys],
            write_disposition="WRITE_TRUNCATE"))
    job.result()
    n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.{table}`"))[0].n
    print(f"  loaded {n:,} rows x {len(keys)} cols -> {table}", flush=True)
    if renames:
        print(f"    renamed for BigQuery legality (none dropped): {renames}", flush=True)

    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{table}'").result()
    client.query(
        f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at, notes) "
        f"VALUES (@t,@s,@m,@n,CURRENT_TIMESTAMP(),@no)",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", table),
            bigquery.ScalarQueryParameter("s", "STRING", f"{MUNI}/search ; {AMLEGAL}/api/clients-search/"),
            bigquery.ScalarQueryParameter("m", "STRING", desc),
            bigquery.ScalarQueryParameter("n", "INT64", int(n)),
            bigquery.ScalarQueryParameter("no", "STRING",
                "v1 table in_ordinances_dc (4 rows) deliberately left untouched for comparison. "
                "Zeros are only meaningful where coverage.status='SEARCHED_NONE_FOUND'; "
                "'NOT_REACHABLE_NO_SEARCHABLE_CODE' must never be read as a permissive posture."),
        ])).result()
    print(f"    registered {table}", flush=True)
    return n


print("\n=== LOAD ===", flush=True)
n_hits = load("in_ordinances_dc_v2", hits,
              f"Indiana local data-centre ordinance provisions. Municode /search per clientId "
              f"({len(live_ids)} of {len(clients)} Indiana clients host a searchable CODES "
              f"product), {len(VOCAB)} vocabularies (18 quoted exact + 1 unquoted loose to "
              f"measure the recall gap), full pagination with shortfall detection against the "
              f"publisher's own NumberOfHits. ALL hit fields kept + raw_hit JSON. Publisher's "
              f"own currency date from Jobs/latest BannerText/PublishDate; _pulled_at separate. "
              f"Posture carried as the publisher's own words in posture_terms_found, unscored. "
              f"Public endpoint, no key, no login.")
n_cov = load("in_ordinances_dc_coverage_v2", coverage,
             "Per-jurisdiction search outcome for the Municode sweep. Distinguishes FOUND / "
             "SEARCHED_NONE_FOUND / NOT_REACHABLE_NO_SEARCHABLE_CODE. The last is the "
             "calibration result: the client exists but hosts no searchable code, so a zero "
             "there is an instrument limit, NOT a permissive local posture.")
n_pub = load("in_ordinances_publisher_inventory_v2", pubs,
             "Publisher-level inventory and access walls for Indiana ordinance sources. "
             "Carries American Legal Publishing's 230 listed Indiana clients (public "
             "clients-search endpoint) each marked LISTED_SEARCH_BLOCKED, plus the verbatim "
             "wall for amlegal auth, Code Publishing (Cloudflare on robots.txt) and eCode360 "
             "(robots Disallow: /search). No wall was worked around.")

# ============================================ 7. registry_sources -- APPEND ONLY
print("\n=== registry_sources (append only) ===", flush=True)
SOURCES = [
    ("Municode Indiana local codes -- data-centre vocabulary sweep", "OK",
     f"{MUNI}/search", "rest_json",
     f"per-clientId exact-phrase + loose search across {len(VOCAB)} vocabularies, "
     f"contentTypeId=CODES, paged {PAGE}/page at {PAUSE}s, shortfall-checked against "
     f"NumberOfHits; calibrated with control words first",
     ["in_ordinances_dc_v2", "in_ordinances_dc_coverage_v2"]),
    ("American Legal Publishing Indiana clients (search BLOCKED)", "BLOCKED",
     f"{AMLEGAL}/api/search/", "rest_json",
     "client list readable at /api/clients-search/ (230 Indiana clients captured); SEARCH "
     "blocked by Cloudflare managed challenge and unscopable (every scoping key 500s or is "
     "ignored); /api/all-client-regions/ requires auth. Not worked around.",
     ["in_ordinances_publisher_inventory_v2"]),
    ("Code Publishing Indiana codes (BLOCKED)", "BLOCKED",
     "https://www.codepublishing.com/", "html",
     "Cloudflare managed challenge returned on robots.txt itself (HTTP 403); permission file "
     "unreadable, so no crawl attempted.", ["in_ordinances_publisher_inventory_v2"]),
    ("General Code eCode360 Indiana codes (BLOCKED BY ROBOTS)", "BLOCKED",
     "https://ecode360.com/search", "html",
     "robots.txt User-agent:* contains 'Disallow: /search'; the search interface is the only "
     "systematic route and is disallowed. Not crawled.",
     ["in_ordinances_publisher_inventory_v2"]),
]
for name, status, ep, kind, method, objs in SOURCES:
    client.query(
        "INSERT INTO `energy-platfrom.energy.registry_sources` "
        "(source_name, status, endpoint, endpoint_kind, acquisition_method, object_names, "
        " updated_by, geography_state, last_validated_at) "
        "VALUES (@n,@s,@e,@k,@m,@o,'indiana-app-ordinances-agent','IN',CURRENT_TIMESTAMP())",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("n", "STRING", name),
            bigquery.ScalarQueryParameter("s", "STRING", status),
            bigquery.ScalarQueryParameter("e", "STRING", ep),
            bigquery.ScalarQueryParameter("k", "STRING", kind),
            bigquery.ScalarQueryParameter("m", "STRING", method),
            bigquery.ArrayQueryParameter("o", "STRING", objs)])).result()
    print(f"  appended: {name} [{status}]", flush=True)

# ==================================================================== 8. REPORT
v1 = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_ordinances_dc`"))[0].n
cty_found = sorted({c["county"] for c in coverage if c["status"] == "FOUND" and c["county"]})
cty_none = sorted({c["county"] for c in coverage if c["status"] == "SEARCHED_NONE_FOUND" and c["county"]})
cty_assessed = sorted(set(cty_found) | set(cty_none))
by_vocab = {}
for h in hits:
    by_vocab[h["search_phrase"]] = by_vocab.get(h["search_phrase"], 0) + 1

print(f"""
================= RESULT =================
v1 in_ordinances_dc         : {v1} rows (untouched)
v2 in_ordinances_dc_v2      : {n_hits} rows
   coverage rows            : {n_cov}
   publisher inventory rows : {n_pub}

Municode clients            : {len(clients)}  (searchable code: {len(live_ids)})
Counties with a FINDING     : {len(cty_found)}  {cty_found}
Counties searched, none     : {len(cty_none)}  {cty_none}
Counties ASSESSED           : {len(cty_assessed)} of 92  ({100*len(cty_assessed)/92:.0f}%)
amlegal IN clients walled   : {len(am_in)}
shortfalls                  : {len(shortfalls)}

vocabulary productivity:""")
for p, m in VOCAB:
    print(f"   {by_vocab.get(p, 0):>4}  {p}  [{m}]")
json.dump({"coverage": coverage, "by_vocab": by_vocab, "shortfalls": shortfalls,
           "amlegal_indiana": am_in, "calibration": {str(k): v for k, v in cal.items()}},
          open("ordinance_run_summary.json", "w", encoding="utf-8"), indent=1)
print("\nwrote ordinance_run_summary.json")
