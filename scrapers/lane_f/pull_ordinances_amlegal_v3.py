"""American Legal Publishing, Indiana -- v3 PERMITTED-ROUTE ASSESSMENT. Verdict: BLOCKED.

WHY A THIRD PASS EXISTS. v2 recorded amlegal BLOCKED on two grounds: /api/search/ is
Cloudflare-challenged, and search scoping is broken (a clients:["carmel"] query returns
Michigan). 221 of 230 Indiana clients -- including 24 county governments -- were left
unassessed. This run's brief: find a genuinely different, PERMITTED route (robots.txt and
terms of use first, individual documents separately from search, a public index), or
confirm there is none. No challenge solving, no fingerprint spoofing, honest UA, >=1s
spacing, back off on 429.

WHAT WAS FOUND (2026-08-16, 11 requests, logged verbatim in amlegal_v3_probe_log.json):

1. THE TERMS OF USE PROHIBIT THIS -- the ground v2 never had. Neither codelibrary.amlegal.com
   (no terms link anywhere in its SPA bundle or SSR pages) nor www.amlegal.com hosts its own
   terms; the corporate footer's "User Agreement" resolves to the ICC Terms of Use
   (https://www.iccsafe.org/about/terms-of-use/, "Last revised: May 4, 2023"), whose sec. 1
   names "American Legal Publishing Corporation, American Legal Publishing, LLC, and their
   respective affiliates and subsidiaries" as covered entities and whose sec. 4 says,
   verbatim:

       "Unless expressly provided for herein, the licenses ICC grants to use our E-Content
        ... do not include any: resale or commercial use of any Service or E-Content;
        derivative use of any Service or E-Content; downloading, copying, distribution, or
        display of E-Content (or a portion thereof) or account information to, by, or for
        the benefit of any third party ...; or use of data mining, robots, or similar data
        gathering and extraction tools with any Service or E-Content. Please contact us at
        license@iccsafe.org to discuss additional licenses for further uses."

   Sec. 1 lists "eCode 360" -- a sibling public municipal code library -- as an example of
   E-Content, so the code library plainly falls under the clause. The permitted route the
   publisher designates is license@iccsafe.org, not a crawl.

2. THE TECHNICAL ROUTE HALF-OPENS AND IS NOT STABLE. Document pages are fully server-side
   rendered (an overview page carries the publisher's currency sentence and the whole
   top-level TOC in window._redux_state; /regions/in is an SSR index of exactly 230 Indiana
   clients, matching the v2 inventory with zero drift). But the Cloudflare managed challenge
   ("<title>Just a moment...</title>" / "Enable JavaScript and cookies to continue",
   header cf-mitigated: challenge) fired on 2 of 7 code-library requests in this assessment:
   on /api/client-version/ -- the endpoint that intermittently served the prior run hours
   earlier -- and on a plain section HTML page (TITLE XV: LAND USAGE, Adams County). A
   session on 2026-08-15 independently recorded the challenge on HTML AND /api/search/
   (energy.registry_sources, source_name='American Legal codelibrary'). That is not the
   "stable, unchallenged URL pattern" a permitted crawl requires; it is the same wall,
   observed from three sessions across 28 hours.

3. robots.txt, read first and quoted verbatim in the probe log, GRANTS the generic agent
   "User-agent: * / Content-Signal: search=yes,ai-train=no,use=reference / Allow: /" while
   name-disallowing bulk AI-training crawlers (ClaudeBot, GPTBot, CCBot, ...) and setting
   Crawl-delay: 5 for named SEO bots. The robots grant and the ToU robots exclusion point
   opposite ways; the restrictive intersection governs an honest agent, and the conflict is
   FLAGGED for the operator's ruling rather than resolved silently. No content crawl was run.

WHAT THIS SCRIPT DOES. Default: NO network. It loads the recorded assessment into BigQuery --
230 per-client rows (in_ordinances_amlegal_v3) + the 11-request evidence log
(in_ordinances_amlegal_v3_probes) -- registers both in indiana_app._registry in the same run,
and appends one BLOCKED observation to energy.registry_sources (append-only; never merged).
--reprobe re-runs the identical 11-request permission assessment live (5s spacing, honoring
the host's own posted Crawl-delay: 5; challenge = wall, recorded, never retried into, never
solved) and rewrites amlegal_v3_probe_log.json before loading. It never crawls content.

Rules honoured: no CAPTCHA/challenge solving, no fingerprint spoofing, no account, no paywall
circumvention; honest UA; energy.* read-only except the append to registry_sources; writes
only to energy-platfrom.indiana_app; ALL evidence fields carried; publisher dates verbatim and
separate from _pulled_at; no scoring scale invented.
"""
import datetime, json, os, re, sys, time, urllib.error, urllib.request
from google.cloud import bigquery

HERE = os.path.dirname(os.path.abspath(__file__))
DS = "energy-platfrom.indiana_app"
AM = "https://codelibrary.amlegal.com"
UA = {"User-Agent": "decennial-indiana-siting/1.0 (research; contact via decennialgroup.com)"}
PULLED = datetime.datetime.now(datetime.timezone.utc).isoformat()
REPROBE = "--reprobe" in sys.argv
PAUSE = 5.0  # the host's own Crawl-delay for named crawlers; adopted as our floor

client = bigquery.Client(project="energy-platfrom")

# ----------------------------------------------------------------- verbatim walls
# Typographic quotes in the ICC page arrive mojibaked under its mis-declared encoding;
# they are normalized to ASCII here and that normalization is declared, not hidden.
TOU_URL = "https://www.iccsafe.org/about/terms-of-use/"
TOU_EXCLUSION = (
    "Unless expressly provided for herein, the licenses ICC grants to use our E-Content, as "
    "set forth in these Terms of Use and applicable E-Content Terms, do not include any: "
    "resale or commercial use of any Service or E-Content; derivative use of any Service or "
    "E-Content; downloading, copying, distribution, or display of E-Content (or a portion "
    "thereof) or account information to, by, or for the benefit of any third party (for "
    "example, a user other than You or any Additional Authorized User); or use of data "
    "mining, robots, or similar data gathering and extraction tools with any Service or "
    "E-Content. Please contact us at license@iccsafe.org to discuss additional licenses for "
    "further uses.")
TOU_SCOPE = (
    "ICC Terms of Use (Last revised: May 4, 2023), linked as 'User Agreement' from the "
    "www.amlegal.com footer; codelibrary.amlegal.com itself links no terms. Sec. 1: "
    "'...International Code Council, Inc., ..., American Legal Publishing Corporation, "
    "American Legal Publishing, LLC, and their respective affiliates and subsidiaries "
    "(collectively, \"We,\" \"Us,\" \"Our,\" \"ICC\") provide You limited rights of use and "
    "access to Our websites ... and Our online services, content, products, subscriptions, "
    "mobile applications, and software used in connection with any of the foregoing "
    "(collectively, \"E-Content\"). The Site and E-Content shall collectively be referred to "
    "as the \"Services.\"' Sec. 1 names 'eCode 360' -- a sibling public municipal code "
    "library -- as an example of E-Content. [typographic quotes normalized to ASCII]")
TOU_RESERVED = (
    "All rights not expressly granted to You in these Terms of Use or any applicable "
    "E-Content Terms are reserved and retained by ICC or its licensors. For the avoidance of "
    "doubt, unless expressly provided for herein, no Service, nor any part of any Service "
    "(including E-Content or any portion thereof), may be reproduced, displayed, distributed, "
    "transferred, sublicensed, sold or otherwise exploited: (i) on a third-party or "
    "government website, (ii) for the benefit of a third party, or (iii) for any commercial "
    "purpose without express written consent of ICC.")
WALL_CHALLENGE = (
    "Cloudflare managed challenge: HTTP 403, header 'cf-mitigated: challenge', body "
    "'<title>Just a moment...</title>' / 'Enable JavaScript and cookies to continue'. "
    "Observed 2026-08-16 on /api/client-version/ (the endpoint that intermittently served "
    "the v2 run hours earlier) and on a plain section HTML page "
    "(/codes/adamscountyin/latest/adamscounty_in/0-0-0-2700, TITLE XV: LAND USAGE): 2 of 7 "
    "code-library requests challenged at 2.5-3s spacing. Prior same-day run: 10 of 26 "
    "challenged at 10s spacing. 2026-08-15 session: 'Cloudflare JS-challenge 403 on HTML AND "
    "/api/search/ (re-measured)'. Never solved, never retried into.")
ROBOTS_GRANT = (
    "User-agent: * / Content-Signal: search=yes,ai-train=no,use=reference / Allow: / "
    "-- identical Cloudflare-managed block on codelibrary.amlegal.com and www.amlegal.com; "
    "named Disallow: / groups for Amazonbot, Applebot-Extended, Bytespider, CCBot, ClaudeBot, "
    "CloudflareBrowserRenderingCrawler, Google-Extended, GPTBot, meta-externalagent; second "
    "group (SemrushBot, MJ12bot, YandexBot, ...) gets Crawl-delay: 5.")
ROBOTS_VS_TERMS = (
    "CONFLICT FLAGGED FOR OPERATOR RULING: robots.txt expressly permits generic-agent "
    "collection for search/reference (Content-Signal search=yes, use=reference) while the ICC "
    "ToU sec. 4 excludes 'use of data mining, robots, or similar data gathering and "
    "extraction tools with any Service or E-Content' and sec. 4/5 reserve all rights not "
    "granted, excluding commercial use without written consent. The restrictive intersection "
    "was taken: no content crawl. The publisher's own designated channel for further uses is "
    "license@iccsafe.org.")
PERMITTED_ROUTE = (
    "Publisher-designated: 'Please contact us at license@iccsafe.org to discuss additional "
    "licenses for further uses' (ICC ToU sec. 4). One license would cover all 230 Indiana "
    "clients incl. the 33 county governments. Interim permitted lane for county POSTURE (not "
    "codified text): official county .gov sites -- see in_ordinances_dc_county_sites_v2, "
    "which already carries verified 2026 moratoria invisible to every codified corpus.")
ACCESS_STATUS = "BLOCKED_BY_TERMS_AND_CHALLENGE"

# ----------------------------------------------------------------- optional live reprobe
PROBES = [
    ("codelibrary_robots", f"{AM}/robots.txt"),
    ("www_robots", "https://www.amlegal.com/robots.txt"),
    ("codelibrary_sitemap", f"{AM}/sitemap.xml"),
    ("www_home", "https://www.amlegal.com/"),
    ("terms_of_use", "https://www.amlegal.com/terms-of-use/"),
    ("spa_bundle", f"{AM}/assets/main.f0cf9ff473f9b94fb761.js"),
    ("adams_overview", f"{AM}/codes/adamscountyin/latest/overview"),
    ("adams_clientversion", f"{AM}/api/client-version/adamscountyin/latest/"),
    ("adams_title15", f"{AM}/codes/adamscountyin/latest/adamscounty_in/0-0-0-2700"),
    ("regions_in", f"{AM}/regions/in/"),
    ("icc_tou", TOU_URL),
]


def fetch(url, tries=4):
    """Bounded retry on transient codes only. A challenge is a WALL: recorded, returned,
    never retried into, never solved."""
    last = None
    for i in range(tries):
        time.sleep(PAUSE)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return {"status": r.status, "n_bytes": len(r.read()),
                        "cf_mitigated": r.headers.get("cf-mitigated"), "challenged": False}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            chal = (e.headers.get("cf-mitigated") == "challenge") or \
                   (e.code == 403 and "Just a moment" in body)
            if chal:
                return {"status": e.code, "n_bytes": len(body),
                        "cf_mitigated": e.headers.get("cf-mitigated"), "challenged": True}
            if e.code in (429, 500, 502, 503, 504):
                last = f"HTTP {e.code}"
                time.sleep(PAUSE * 2 * (i + 1))
                continue
            return {"status": e.code, "n_bytes": len(body), "cf_mitigated": None,
                    "challenged": False}
        except Exception as e:
            last = str(e)[:120]
    return {"status": None, "n_bytes": 0, "cf_mitigated": None, "challenged": False,
            "error": f"gave up after {tries}: {last}"}


if REPROBE:
    print(f"=== REPROBE: {len(PROBES)} permission/reachability requests at {PAUSE}s ===",
          flush=True)
    fresh = []
    for i, (name, url) in enumerate(PROBES, 1):
        r = fetch(url)
        host = re.match(r"https?://([^/]+)/", url).group(1)
        fresh.append({"seq": i, "url": url, "host": host, "purpose": name,
                      "http_status": r["status"], "cf_mitigated": r["cf_mitigated"],
                      "challenged": r["challenged"], "n_bytes": r["n_bytes"],
                      "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      "user_agent": UA["User-Agent"], "spacing_s": PAUSE,
                      "verbatim_excerpt": None})
        print(f"  [{i}/{len(PROBES)}] {r['status']} challenged={r['challenged']} {name}",
              flush=True)
    with open(os.path.join(HERE, "amlegal_v3_probe_log.json"), "w", encoding="utf-8") as f:
        json.dump(fresh, f, indent=1)

# ----------------------------------------------------------------- build rows
probes = json.load(open(os.path.join(HERE, "amlegal_v3_probe_log.json"), encoding="utf-8"))
cov_v2 = json.load(open(os.path.join(HERE, "amlegal_coverage.json"), encoding="utf-8"))
print(f"inputs: {len(probes)} probe records, {len(cov_v2)} v2 client records", flush=True)

cl = [p for p in probes if p["host"] == "codelibrary.amlegal.com"]
n_chal = sum(1 for p in cl if p["challenged"])
print(f"code-library challenge rate in evidence: {n_chal}/{len(cl)}", flush=True)

rows = []
for c in cov_v2:
    is_cty = c["jurisdiction"].endswith(" County")
    rows.append({
        "slug": c["slug"], "jurisdiction": c["jurisdiction"], "state": "IN", "region": "in",
        "provider": "american_legal_publishing",
        "is_county_government": str(is_cty),
        "county": c["jurisdiction"][:-len(" County")] if is_cty else None,
        "access_status": ACCESS_STATUS,
        "dc_content_status": "NOT_ASSESSED_ACCESS_BLOCKED",
        "wall_terms_verbatim": TOU_EXCLUSION,
        "wall_terms_scope": TOU_SCOPE,
        "wall_terms_reserved_rights": TOU_RESERVED,
        "wall_terms_url": TOU_URL,
        "wall_challenge_verbatim": WALL_CHALLENGE,
        "robots_grant_verbatim": ROBOTS_GRANT,
        "robots_vs_terms_note": ROBOTS_VS_TERMS,
        "permitted_route": PERMITTED_ROUTE,
        "overview_url": f"{AM}/codes/{c['slug']}/latest/overview",
        "url_source": "listed on /regions/in SSR index 2026-08-16 (230 links; matches v2 "
                      "inventory exactly, zero drift)",
        "prior_run_status": c.get("status"),
        "prior_run_detail": c.get("detail"),
        "prior_run_currency_info": c.get("currency_info"),  # PUBLISHER'S OWN sentence, verbatim
        "prior_run_pulled_at": c.get("_pulled_at"),
        "publisher_client_count": "230",
        "_pulled_at": PULLED,
        "_evidence_table": "in_ordinances_amlegal_v3_probes",
    })

probe_rows = [dict(p, _pulled_at=PULLED) for p in probes]


def safe(k):
    s = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in str(k))
    return ("_" + s) if (not s or s[0].isdigit()) else s


def load(table, data, source, method, notes):
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
        f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, "
        f"built_at, notes) VALUES (@t,@s,@m,@n,0.0,CURRENT_TIMESTAMP(),@no)",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", table),
            bigquery.ScalarQueryParameter("s", "STRING", source),
            bigquery.ScalarQueryParameter("m", "STRING", method),
            bigquery.ScalarQueryParameter("n", "INT64", int(n)),
            bigquery.ScalarQueryParameter("no", "STRING", notes)])).result()
    print(f"    registered {table}", flush=True)
    return n


print("\n=== LOAD ===", flush=True)
n1 = load(
    "in_ordinances_amlegal_v3", rows, f"{AM} + {TOU_URL}",
    "v3 permitted-route assessment of American Legal Publishing's 230 Indiana clients. "
    "robots.txt and terms of use read FIRST and quoted verbatim; individual-document SSR "
    "route and /regions/in index tested with 11 logged requests at honest UA; NO content "
    "crawled. Verdict: BLOCKED_BY_TERMS_AND_CHALLENGE -- ICC ToU sec. 4 excludes robots/"
    "data-mining tools (AMLP is a named covered entity) and the Cloudflare managed challenge "
    "fires intermittently on HTML and API paths (3 sessions, 28h). Search endpoint untouched "
    "this run (walled + unscopable per v2).",
    "ACCESS ASSESSMENT ONLY -- carries NO ordinance content and NO posture claims. "
    "dc_content_status=NOT_ASSESSED_ACCESS_BLOCKED for all 230 rows must never be rendered "
    "as silence/permissive. prior_run_currency_info is the publisher's own sentence where "
    "the v2 run captured it (9 counties); _pulled_at is separate. The permitted route is the "
    "publisher's own licensing channel (license@iccsafe.org). Do not modify "
    "in_ordinances_dc / _v2 / _v2_triage.")
n2 = load(
    "in_ordinances_amlegal_v3_probes", probe_rows,
    f"{AM}, https://www.amlegal.com, {TOU_URL}",
    "The 11-request evidence log behind the v3 BLOCKED verdict: robots.txt x2, sitemap test, "
    "ToU discovery + ICC ToU, SPA-bundle endpoint inventory, one overview SSR page, one "
    "/api/client-version/ re-test, one section SSR page, /regions/in index. 2.5-3s spacing, "
    "UA 'decennial-indiana-siting/1.0'. 2 of 7 code-library requests drew the managed "
    "challenge; challenges recorded, never retried into, never solved.",
    "Instrument-calibration evidence. verbatim_excerpt carries the walls and grants word for "
    "word (robots Content-Signal grant; ICC ToU sec. 1 scope + sec. 4 robots exclusion; the "
    "challenge interstitial). Timestamps are request times (_pulled_at separate).")

client.query(
    "INSERT INTO `energy-platfrom.energy.registry_sources` "
    "(source_name, status, endpoint, endpoint_kind, acquisition_method, object_names, "
    " updated_by, geography_state, last_validated_at, notes, access, what_it_provides, "
    " domain, category) "
    "VALUES (@n,@s,@e,@k,@m,@o,'indiana-app-ordinances-agent','IN',CURRENT_TIMESTAMP(),"
    "@no,@a,@w,'codelibrary.amlegal.com','ordinances')",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter(
            "n", "STRING",
            "American Legal Publishing Indiana codes -- v3 permitted-route assessment"),
        bigquery.ScalarQueryParameter("s", "STRING", "BLOCKED"),
        bigquery.ScalarQueryParameter("e", "STRING", AM),
        bigquery.ScalarQueryParameter("k", "STRING", "html_ssr+rest_json"),
        bigquery.ScalarQueryParameter(
            "m", "STRING",
            "robots.txt + ToU read first; SSR document pages and /regions/in index probed "
            "(11 requests, honest UA, 2.5-3s spacing); no content crawled; no challenge "
            "solved; search endpoint not touched (walled + unscopable per v2)"),
        bigquery.ArrayQueryParameter(
            "o", "STRING", ["in_ordinances_amlegal_v3", "in_ordinances_amlegal_v3_probes"]),
        bigquery.ScalarQueryParameter(
            "no", "STRING",
            "BLOCKED on two independent grounds, each sufficient: (1) ICC ToU sec. 4 "
            "(AMLP a named covered entity): '...do not include any: ... use of data mining, "
            "robots, or similar data gathering and extraction tools with any Service or "
            "E-Content. Please contact us at license@iccsafe.org...'; (2) Cloudflare managed "
            "challenge ('Just a moment...' / cf-mitigated: challenge) intermittent on HTML "
            "and API paths -- 2/7 this run, 10/26 v2 run, HTML+search per 2026-08-15 "
            "session. robots.txt * grant (Content-Signal search=yes,use=reference) conflicts "
            "with the ToU; restrictive intersection taken; conflict flagged for operator "
            "ruling. SSR route exists (overview pages carry currency + full TOC in "
            "window._redux_state; /regions/in lists all 230 IN clients) but is neither "
            "permitted by the ToU nor stably unchallenged."),
        bigquery.ScalarQueryParameter(
            "a", "STRING",
            "blocked -- ToU excludes robots/data-mining; managed challenge intermittent; "
            "publisher's designated route: license@iccsafe.org"),
        bigquery.ScalarQueryParameter(
            "w", "STRING",
            "230 Indiana jurisdictions incl. 33 county governments -- codified ordinances "
            "(access assessment only; no content pulled)")])).result()
print("  appended 1 row -> energy.registry_sources (append-only)", flush=True)

n_cty = sum(1 for r in rows if r["is_county_government"] == "True")
print(f"""
================= AMLEGAL V3 RESULT =================
verdict                      : BLOCKED (terms + challenge; each ground sufficient)
clients assessed for access  : {n1} (all 230; {n_cty} county governments)
content newly searched       : 0 clients, 0 counties -- no permitted route exists
publisher's own client count : 230 (/regions/in SSR index; matches inventory, zero drift)
evidence rows                : {n2}
permitted route              : license@iccsafe.org (ICC ToU sec. 4, publisher-designated)
""", flush=True)
