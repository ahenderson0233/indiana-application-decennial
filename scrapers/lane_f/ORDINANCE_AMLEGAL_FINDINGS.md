# American Legal Publishing, Indiana — v3 permitted-route assessment — **BLOCKED**

**Run date 2026-08-16.** Loader: `pull_ordinances_amlegal_v3.py`. Evidence: `amlegal_v3_probe_log.json`
(11 requests, honest UA `decennial-indiana-siting/1.0`, 2.5–3s spacing, no challenge solved, no
fingerprint spoofed, no account, no browser driven at it, search endpoint not touched).
Tables: `energy-platfrom.indiana_app.in_ordinances_amlegal_v3` (230 rows) and
`in_ordinances_amlegal_v3_probes` (11 rows), both registered same-run; one BLOCKED observation
appended to `energy.registry_sources`.

---

## 1. The verdict, and what this run added over v2

**v2's BLOCKED verdict stands — and it is now stronger.** v2 recorded a technical wall (Cloudflare
challenge on `/api/search/`, plus unscopable search). This run went looking for a genuinely
different, permitted route, in the mandated order — permission files first, then individual
documents, then a public index — and found:

1. **A legal wall v2 never saw: the publisher's terms of use prohibit robot collection outright.**
   American Legal is an ICC company; its governing "User Agreement" is the ICC Terms of Use, which
   names American Legal Publishing as a covered entity and excludes "data mining, robots, or
   similar data gathering and extraction tools" from every license it grants (§2 below, verbatim).
   The ToU designates its own remedy: **license@iccsafe.org**.
2. **The technical route half-opens — and is not stable.** Document pages are fully server-side
   rendered (a client overview page carries the publisher's own currency sentence and the complete
   top-level TOC inside `window._redux_state`; `/regions/in` is a server-rendered index of exactly
   230 Indiana clients, matching the v2 inventory with zero drift). But the managed challenge fired
   on **2 of 7** code-library requests in this assessment — including on a **plain section HTML
   page** and on `/api/client-version/`, the very endpoint that (intermittently) served the v2 run
   hours earlier. A 2026-08-15 session independently recorded the challenge **on HTML and search
   both**. Three sessions, 28 hours, same wall.

Either ground alone is sufficient. Together: **there is no permitted automated route to this
content today.** Per the brief, that is a successful outcome, recorded honestly, worked around
nowhere.

## 2. Every wall, verbatim

### 2.1 robots.txt — readable, and it GRANTS the generic agent (both hosts, identical block)

`https://codelibrary.amlegal.com/robots.txt` and `https://www.amlegal.com/robots.txt`, HTTP 200,
unchallenged, 2026-08-16:

```
User-agent: *
Content-Signal: search=yes,ai-train=no,use=reference
Allow: /

User-agent: Amazonbot
Disallow: /
User-agent: Applebot-Extended
Disallow: /
User-agent: Bytespider
Disallow: /
User-agent: CCBot
Disallow: /
User-agent: ClaudeBot
Disallow: /
User-agent: CloudflareBrowserRenderingCrawler
Disallow: /
User-agent: Google-Extended
Disallow: /
User-agent: GPTBot
Disallow: /
User-agent: meta-externalagent
Disallow: /
```

The code-library file adds a second group (Amazonbot, SemrushBot, MJ12bot, ltx71, The Knowledge
AI, LieBaoFast, TurnitinBot, YandexBot): `Disallow: /` with `Crawl-delay: 5`. No `Sitemap:`
directive on either host; `/sitemap.xml` is 404.

### 2.2 The terms of use — the wall that decides it

Neither `codelibrary.amlegal.com` (no terms link anywhere in its SPA bundle or rendered pages) nor
`www.amlegal.com` hosts terms of its own (`/terms-of-use/` → 404). The corporate footer links
**"User Agreement" → `https://www.iccsafe.org/about/terms-of-use/`** — the ICC Terms of Use,
**"Last revised: May 4, 2023"** (the publisher's own date; pulled 2026-08-16). Verbatim, with
typographic quotes normalized to ASCII:

**§1 Acceptance of Terms — scope covers American Legal by name:**

> "Pursuant to these Terms of Use, International Code Council, Inc., International Accreditation
> Service, Inc., ICC Evaluation Service, LLC, Solar Rating and Certification Corporation, General
> Code, LLC, ICC Community Development Solutions, LLC, ICC NTA, LLC, S. K. Ghosh Associates, LLC,
> Alliance for National & Community Resilience, Inc., ICC PEI, LLC, **American Legal Publishing
> Corporation, American Legal Publishing, LLC**, and their respective affiliates and subsidiaries
> (collectively, "We," "Us," "Our," "ICC") provide You limited rights of use and access to Our
> websites, including https://www.iccsafe.org/ and other websites where these Terms of Use are
> posted (together, the "Site"), and Our online services, content, products, subscriptions, mobile
> applications, and software used in connection with any of the foregoing (collectively,
> "E-Content"). The Site and E-Content shall collectively be referred to as the "Services.""

**§1 — a sibling public municipal code library is expressly an example of E-Content:**

> "ICC offers a wide range of E-Content, and additional terms may apply to certain E-Content. When
> you use E-Content (for example, Digital Codes Premium, cdpACCESS, MyICC App, **eCode 360**), You
> also will be subject to the guidelines, terms and agreements applicable to that particular
> E-Content ("E-Content Terms")."

**§1 — use is acceptance:**

> "EACH TIME YOU USE THE SERVICES, YOUR USE INDICATES YOUR FULL ACCEPTANCE OF AND AGREEMENT TO
> ABIDE BY THE TERMS OF USE IN ITS THEN CURRENT FORM."

**§4 Licenses — the grant:**

> "Subject to your compliance with these Terms of Use and any applicable E-Content Terms, and your
> payment of any applicable fees, ICC grants You a limited, non-exclusive, non-transferable,
> non-sublicensable, revocable license to access and make personal, internal business, and
> non-commercial use of the Services..."

**§4 — the exclusion that blocks this task:**

> "Unless expressly provided for herein, the licenses ICC grants to use our E-Content, as set
> forth in these Terms of Use and applicable E-Content Terms, do not include any: resale or
> commercial use of any Service or E-Content; derivative use of any Service or E-Content;
> downloading, copying, distribution, or display of E-Content (or a portion thereof) or account
> information to, by, or for the benefit of any third party (for example, a user other than You or
> any Additional Authorized User); or **use of data mining, robots, or similar data gathering and
> extraction tools with any Service or E-Content**. Please contact us at **license@iccsafe.org**
> to discuss additional licenses for further uses."

**§5-adjacent reservation:**

> "All rights not expressly granted to You in these Terms of Use or any applicable E-Content Terms
> are reserved and retained by ICC or its licensors. For the avoidance of doubt, unless expressly
> provided for herein, no Service, nor any part of any Service (including E-Content or any portion
> thereof), may be reproduced, displayed, distributed, transferred, sublicensed, sold or otherwise
> exploited: (i) on a third-party or government website, (ii) for the benefit of a third party, or
> (iii) for any commercial purpose without express written consent of ICC."

### 2.3 The Cloudflare managed challenge — still live, still intermittent

Verbatim interstitial (HTTP 403, response header `cf-mitigated: challenge`):

> `<title>Just a moment...</title>` — "Enable JavaScript and cookies to continue"

Observed this run on `/api/client-version/adamscountyin/latest/` and on the plain section page
`/codes/adamscountyin/latest/adamscounty_in/0-0-0-2700` (TITLE XV: LAND USAGE): 2 of 7
code-library requests. Same-day earlier run (v2): 10 of 26 at 10s spacing. Prior day
(`energy.registry_sources`, 2026-08-15, verbatim): *"Cloudflare JS-challenge 403 on HTML AND
/api/search/ (re-measured); held 183 IN rows are loose mentions."* No challenge was solved or
retried into, in any session.

### 2.4 Carried from v2 (not retested — no reason to touch a known wall)

> `/api/search/`: `CLOUDFLARE_MANAGED_CHALLENGE: Enable JavaScript and cookies to continue`; and
> every scoping key — `includeRegions`, `includeClients`, `clients`, `regions` — either returns
> `HTTP 500 Server Error` or is silently ignored and returns national results (a `clients:
> ["carmel"]` query returned Williamstown Township, Michigan).
> `/api/all-client-regions/`: `{"detail":"Authentication credentials were not provided."}` — 401.

## 3. The probe log (all 11 requests; full copies in `in_ordinances_amlegal_v3_probes`)

| # | host | request | result |
|---|---|---|---|
| 1 | codelibrary | `/robots.txt` | 200 clean — grant quoted in §2.1 |
| 2 | www.amlegal | `/robots.txt` | 200 clean — identical block |
| 3 | codelibrary | `/sitemap.xml` | 404 — no sitemap exists |
| 4 | www.amlegal | `/` (locate ToU) | 200 clean — footer: "User Agreement" → ICC ToU |
| 5 | www.amlegal | `/terms-of-use/` | 404 — no local terms; ICC's govern |
| 6 | codelibrary | `/assets/main.f0cf9ff…js` | 200 — endpoint inventory: `api/render-doc/`, `api/section-toc/`, `api/toc/`, `api/search/`, `api/client-regions/`, … |
| 7 | codelibrary | `/codes/adamscountyin/latest/overview` | 200 clean — **SSR**: `<div class="currency-info">Current through Ord. 2023-18, passed 10-3-2023</div>` + full top-level TOC in `window._redux_state` |
| 8 | codelibrary | `/api/client-version/adamscountyin/latest/` | **403 cf-mitigated: challenge** — v2's "public" endpoint, now walled |
| 9 | codelibrary | `/codes/…/adamscounty_in/0-0-0-2700` (TITLE XV: LAND USAGE) | **403 cf-mitigated: challenge** — a plain document page |
| 10 | codelibrary | `/regions/in/` | 200 clean — SSR index, **exactly 230** `/codes/{slug}/latest/overview` links; matches v2 inventory, zero drift |
| 11 | iccsafe.org | `/about/terms-of-use/` | 200 — the governing ToU, §2.2 |

## 4. The route that technically half-opens, and why it was not taken

The brief's hoped-for outcome exists mechanically: overview pages SSR the publisher's currency
sentence and complete TOC; `/regions/in` is a permitted-index-shaped listing of all 230 clients;
the bundle names `api/render-doc/` for body text. Had only robots.txt governed, a counties-first
crawl at ≥5s (the host's own posted Crawl-delay) with the 20% challenge-rate abort guard would
have been defensible.

It was not run, because:

1. **The ToU forbids it in terms** ("robots, or similar data gathering and extraction tools"),
   covers American Legal by name, treats sibling code libraries as E-Content, excludes commercial
   use and third-party display without written consent — and this corpus feeds a commercial siting
   product. Reading the terms first was the point of reading the terms first.
2. **"Stable, unchallenged" is empirically false.** 1 of 2 document-page fetches drew the
   challenge; the JSON endpoint that answered in the morning was walled by evening; the 8/15
   session saw HTML challenged. Building a 230-client crawl on a wall that flickers is pushing,
   not permission.
3. **The publisher names the permitted route itself**: license@iccsafe.org.

## 5. robots.txt vs terms of use — conflict flagged, not silently resolved

The operator publishes both a machine-readable **grant** (`Content-Signal:
search=yes,ai-train=no,use=reference` + `Allow: /` for `*`, with only named AI-training bots
disallowed) and a contractual **prohibition** (§4: no robots/data-mining tools, all rights
reserved). These point opposite ways for an honest self-identified research agent doing
reference retrieval. **The restrictive intersection was taken; no content was crawled.** This
mirrors the Municode `ClaudeBot` flag in `ORDINANCE_FINDINGS.md` §6.4 — both are recorded for the
operator's ruling rather than decided silently. If the operator reads the Content-Signal grant as
controlling for reference use, that reading should be confirmed with the publisher through the
license contact anyway — it is one email either way.

## 6. Per-jurisdiction coverage, and the honest county arithmetic

**This run searched no content, so no jurisdiction moves between posture categories.** All 230
clients: `access_status = BLOCKED_BY_TERMS_AND_CHALLENGE`, `dc_content_status =
NOT_ASSESSED_ACCESS_BLOCKED`. Zero FOUND, zero SEARCHED_NONE_FOUND, zero NOT_SEARCHABLE — those
categories require content access, and rendering any of them from this run would fabricate a
posture. **Not-assessed must never be rendered as silent/permissive.**

Of Indiana's 92 counties, via American Legal specifically:

| state of knowledge | n | counties |
|---|---|---|
| heading-level structure only, captured by v2 in the hours `/api/client-version/` answered (publisher currency sentence on file; body text never seen) | 9 | Adams, Bartholomew, Boone, Clark, Daviess, Decatur, Elkhart, Greene, Hendricks |
| county-government client never reached at all — 7 walled mid-run + 17 behind the abort | 24 | Cass, Dearborn, Dubois, Floyd, Hancock, Howard, Jennings + Knox, Lake, LaPorte, Lawrence, Marshall, Morgan, Owen, Perry, Pulaski, Putnam, Ripley, Spencer, Switzerland, Tippecanoe, Warrick, Wayne, White |
| full-text assessed via amlegal | **0** | — |

**Fraction of Indiana's 92 counties this source could be assessed for data-centre provisions
under the current verdict: 0/92 full-text (9/92 at heading level, inherited from v2).** The
statewide rollup is unchanged from `ORDINANCE_FINDINGS.md` §3: **37 of 92 counties assessed in
some form, 55 untouched.**

The number that matters for prioritization: **17 of the 55 never-assessed counties have an
American Legal county-government client as their nearest (often only) codified source** — Cass,
Dearborn, Floyd, Hancock, Howard, Jennings, Knox, Lawrence, Owen, Perry, Pulaski, Putnam, Spencer,
Switzerland, Warrick, Wayne, White. One license conversation unlocks all 17, plus full text for
Greene and Hendricks (heading-only today, unreachable via any other publisher), plus the ~197
municipal clients.

## 7. Vocabularies

**None were run against American Legal content — zero queries, zero hits, zero non-hits.** The
vocabulary table in `ORDINANCE_FINDINGS.md` §5 is Municode-only evidence. Any per-vocabulary
number attributed to amlegal from this run would be fabricated, so none is reported.

## 8. Control-word calibration

**Not applicable — the instrument never touched searchable text.** No client is recorded
NOT_SEARCHABLE (that claim needs a live search returning 0 on control words); no client is
recorded silent (that claim needs full text returning 0 on the sweep after controls pass). The
only claims made are about ACCESS, and each carries its wall verbatim.

## 9. Tables written (all registered same-run in `indiana_app._registry`)

| table | rows | what |
|---|---|---|
| `in_ordinances_amlegal_v3` | 230 | per-client access assessment: walls verbatim (ToU §1/§4/reservation, challenge, robots grant + conflict note), permitted route, v2 carryover incl. the publisher's own `currency_info` where captured, `_pulled_at` separate |
| `in_ordinances_amlegal_v3_probes` | 11 | the request-level evidence log: URL, status, `cf-mitigated`, challenged flag, bytes, timestamps, verbatim excerpts |

One row appended to `energy.registry_sources` (status **BLOCKED**, both walls quoted,
`updated_by='indiana-app-ordinances-agent'`); `energy.*` otherwise untouched.
`in_ordinances_dc`, `in_ordinances_dc_v2`, `in_ordinances_dc_v2_triage` untouched.

## 10. What to do instead, in order

1. **Send the license email.** The ToU's own channel (license@iccsafe.org) with a specific ask:
   read access or a bulk feed for the codified ordinances of the 230 Indiana jurisdictions, for
   internal siting research. It is the publisher-designated route and covers Municode-unreachable
   Greene and Hendricks in the same stroke.
2. **Sweep the 24 unreached counties' official `.gov` sites** (already the proven
   decision-relevant lane: Boone and Miami's 2026 moratoria live there, not in any codified code).
   County sites publishing their own ordinances are the issuing governments' channels, not ICC
   E-Content.
3. **Do not re-run automated pulls against codelibrary.amlegal.com** — including the previously
   "public" TOC endpoints, which are now behind the same challenge — unless the operator obtains
   the license or rules that the robots.txt Content-Signal grant controls (§5).
4. Keep treating v2's 9-county heading data as heading-level only; its publisher currency
   sentences remain valid observations of record.
