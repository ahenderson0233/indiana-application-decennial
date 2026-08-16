# Indiana local data-centre ordinance acquisition — findings

**Run date 2026-08-16.** Loader: `pull_ordinances_dc.py` (Municode), `pull_ordinances_dc_amlegal.py`
(American Legal), `pull_ordinances_dc_county_sites.py` (county websites).
Tables written: `energy-platfrom.indiana_app.in_ordinances_dc_v2` and five companions.
**`in_ordinances_dc` (v1, 4 rows) was not touched.**

---

## 1. The headline, stated honestly

| | v1 | v2 |
|---|---|---|
| rows | 4 | **153** |
| jurisdictions | 3 | 24 |
| counties with any evidence | 3 | **37 of 92 (40%)** |
| publishers searched | 1 | 2 searched, 2 recorded blocked |
| vocabularies | 2 | 19 |
| shortfalls vs publisher's own count | not checked | **0** |

**Do not read "153 rows" as "153 data-centre ordinances."** Of the 153, **7 rows actually contain
the string "data cent(er|re)" in the returned snippet; 146 matched adjacent vocabulary** —
"telecommunications facility", "data processing" — and are *candidate* provisions a human must
read. The row count measures recall of candidates, not confirmed regulation.

Reduced to distinct sections that genuinely name a data centre as a land use, the codified corpus
for the whole state is **three sections in two counties**:

| county | jurisdiction | section | what it says |
|---|---|---|---|
| St. Joseph | St. Joseph County | § 154.321 Definitions | *"Data center means a location housing one or more large computer systems and related equipment…"* |
| St. Joseph | St. Joseph County | § 154.319 Land use standards (**IEC: Indiana Enterprise Center Overlay**) | carries a `Data Center` row in the land-use table |
| Johnson | Franklin | 17.08.020 Definitions | *"…would likely include a telephone service exchange, a data center, and a server farm"* |

**And one false positive that was also in v1:** Michigan City (LaPorte County) § 22.09 matches on
*"Indiana Natural Heritage Data Center"* — an IDNR **database**, not a land use. v1's 4 rows were
therefore 3 real + 1 false. The county rollup still shows LaPorte as FOUND on the string match;
it should be read as **1 of 2** genuine counties, not 3.

**The real finding is the silence.** After sweeping 19 vocabularies across every searchable
Indiana Municode code, Indiana's *codified* local zoning is very nearly silent on data centres.
That is consistent with what Boone County says about its own ordinance: it was drafted in **1998**
and "did not include anything that was remotely close to what a data center now is." Silence here
is a real, permissive-by-default posture — and it is exactly why §2 below matters.

---

## 2. The thing that invalidates a codified-only corpus

**Indiana's actual data-centre regulation is happening right now, in 2026, as commissioner
moratoria published on county websites — and none of it is in any codified code.**

| county | instrument | publisher's own date | evidence |
|---|---|---|---|
| **Boone** | 1-year **moratorium**, unincorporated county | adopted **2026-06-15**, effective 2026-06-16 → 2027-06-15 | **verified at boonecounty.in.gov** |
| **Miami** | temporary **moratorium** on all data-centre applications/permits | adopted **2026-05-04** | **verified at miamicountyin.gov** |
| Marshall | reported **prohibition** (replaced a moratorium with a ban in the zoning ordinance) | reported 2026-04-20 | lead — not verified |
| Madison | reported 6-month moratorium | reported 2026-06 | lead — not verified |
| Fulton | reported 1-year moratorium | reported 2026-03-02 | lead — not verified |
| Starke | draft data-centre ordinance PDF on county site | 2025-11-12 | lead — not verified |

Boone County verbatim: *"temporarily pauses the filing, processing, review, and acceptance of
applications related to new data center facilities in unincorporated areas of the county."*

Boone is the **LEAP district** — the largest data-centre story in the state. It is invisible to
both publisher APIs because it is (a) not a Municode client, (b) an American Legal client behind
the Cloudflare wall, and (c) a June-2026 ordinance that is **not yet codified** regardless of
access. A product that reads only codified codes would render Boone County as *silent* — i.e.
permissive — when it is currently the most restrictive posture in Indiana. That inversion is the
single most important result of this run.

`in_ordinances_dc_county_sites_v2.evidence_grade` separates `VERIFIED_AT_OFFICIAL_SOURCE` (2) from
`REPORTED_NEEDS_VERIFICATION` (4). **Leads must never be rendered as posture.**

---

## 3. Per-county coverage (all 92)

| status | n | counties |
|---|---|---|
| **FOUND — codified, names a data centre** | 3 | Johnson, LaPorte*, St. Joseph  (*LaPorte = the false positive above) |
| **FOUND — county-site moratorium, verified** | 2 | Boone, Miami |
| LEAD_UNVERIFIED — county site, needs confirmation | 4 | Fulton, Madison, Marshall, Starke |
| CANDIDATE_VOCAB_ONLY — hits need human triage | 12 | Delaware(3), Dubois(2), Hamilton(11), Kosciusko(4), Lake(18), Marion(13), Monroe(3), Morgan(1), Noble(3), Porter(9), Tippecanoe(2), Wabash(4) |
| SEARCHED_NONE_FOUND — full text, genuinely silent | 5 | Benton, Gibson, Jackson, Ripley, Tipton |
| SEARCHED_NONE_FOUND — full text + headings | 1 | Elkhart |
| HEADINGS_ONLY_NONE_FOUND — TOC scanned, body not searchable | 7 | Adams, Bartholomew, Clark, Daviess, Decatur, Greene, Hendricks |
| **NOT_REACHABLE — publisher hosts no searchable code** | 3 | Parke, Scott, Wells |
| **NOT_SEARCHED — no reachable publisher** | 55 | Allen, Blackford, Brown, Carroll, Cass, Clay, Clinton, Crawford, DeKalb, Dearborn, Fayette, Floyd, Fountain, Franklin, Grant, Hancock, Harrison, Henry, Howard, Huntington, Jasper, Jay, Jefferson, Jennings, Knox, LaGrange, Lawrence, Martin, Montgomery, Newton, Ohio, Orange, Owen, Perry, Pike, Posey, Pulaski, Putnam, Randolph, Rush, Shelby, Spencer, Steuben, Sullivan, Switzerland, Union, Vanderburgh, Vermillion, Vigo, Warren, Warrick, Washington, Wayne, White, Whitley |

**Assessed: 37 of 92 counties (40%). Not assessed: 55 (60%).**

Only the 6 rows in `SEARCHED_NONE_FOUND` are an honest "this county is silent" claim from full
text. `HEADINGS_ONLY_NONE_FOUND` means *no named chapter* — a data-centre line inside a
permitted-use table would not be visible. `NOT_REACHABLE` and `NOT_SEARCHED` are **not** evidence
of a permissive posture and must never be scored as one.

---

## 4. The calibration that prevented seven fabricated signals

Carmel returned 0 for `"data center"`. It also returned **0 for "zoning", "building" and
"ordinance"** — words that cannot be absent from a municipal code. Carmel hosts no searchable
CODES product on Municode at all.

**Seven of the 45 Indiana Municode clients are like this:** Avon, Bluffton, Carmel, Linton,
Milford, Parke County, Scottsburg. Without the control-word calibration that runs before the
sweep, all seven would have been recorded as "no data-centre provision found" — i.e. as
*permissive* — injecting seven fabricated postures. They are recorded
`NOT_REACHABLE_NO_SEARCHABLE_CODE` instead. Three counties (Parke, Scott, Wells) have **no other
Indiana publisher client at all**, so they are unassessable by this route entirely.

Two further instrument defects caught and corrected:

- **`stateId` is a dead parameter.** `api.municode.com/search?stateId=14&…` returns
  `NumberOfHits: 0` for every query, including controls. Only `clientId` scoping works. A
  state-wide sweep written against `stateId` would return a clean, confident, entirely false zero.
- **`library.municode.com` answers HTTP 200 for any slug.** It is a SPA, so a 200 cannot validate
  a constructed URL. The `url` column is marked `url_is_constructed`; `client_id` +
  `code_section_id` are the authoritative publisher identifiers.

---

## 5. Vocabularies: what actually produced hits

| vocabulary | rows | verdict |
|---|---|---|
| `data center` (unquoted, loose) | **66** | highest recall — but stems/OR-matches, so it also catches "community **center**", "child care **center**" |
| `"telecommunications facility"` | **43** | highest exact-phrase yield; mostly cell-tower siting, needs triage |
| `"data processing"` | **34** | the productive near-synonym in older Indiana codes |
| `"data center"` | 4 | the v1 phrase — 4 rows statewide |
| `"technology park"` | 3 | |
| `"web hosting"` | 2 | |
| `"server farm"` | 1 | |
| `"data centers"`, `"datacenter"`, `"computer center"`, `"computing facility"`, `"high density computing"`, `"cryptocurrency mining"`, `"cryptocurrency"`, `"digital asset mining"`, `"blockchain"`, `"bitcoin"`, `"colocation"`, `"hyperscale"` | **0** | **produced nothing anywhere in Indiana's Municode corpus** |

Two conclusions worth carrying:

1. **The v1 phrase was the problem it was suspected to be.** `"data center"` alone yields 4 rows;
   the vocabulary sweep yields 153 candidates. Quoting also costs recall directly — on St. Joseph
   County, `"data center"` quoted = 2 hits, unquoted = 7.
2. **The entire crypto/blockchain vocabulary is absent from Indiana's codified codes.** Zero hits
   for cryptocurrency, digital asset mining, blockchain, bitcoin across all 38 searchable clients.
   That is a real negative finding, not a gap in the search — the control words prove the
   instrument was live on every one of those clients.
3. `"data centers"` returning 0 while `"data center"` returns 4 shows Municode stems plurals — the
   plural form is redundant, not missing.

---

## 6. BLOCKED sources — verbatim walls, none worked around

### 6.1 American Legal Publishing — `codelibrary.amlegal.com` — **230 Indiana clients, search blocked**

The largest single gap. amlegal hosts **230 Indiana jurisdictions, 33 of them county
governments** — five times Municode's footprint — including Greene and Hendricks, the two
counties Municode cannot reach at all.

`/api/search/` is unusable for two independent reasons:

> `CLOUDFLARE_MANAGED_CHALLENGE: Enable JavaScript and cookies to continue`

> Every scoping key — `includeRegions`, `includeClients`, `clients`, `regions` — either returns
> `HTTP 500 Server Error` or is silently ignored and returns **national** results. A query scoped
> to Indiana is not expressible: a search for `clients:["carmel"]` returns Williamstown Township,
> Michigan.

`/api/all-client-regions/` is auth-gated:

> `{"detail":"Authentication credentials were not provided."}` — HTTP 401

**No challenge was solved, no fingerprint spoofed, no browser driven at it, no account created.**

What *was* permitted and used: amlegal's robots.txt grants `User-agent: * / Allow: /`, and two
read endpoints are public and unauthenticated — `/api/client-version/{slug}/latest/` and
`/api/section-toc/{id}/`. These yield the **publisher's own currency sentence** (e.g. Adams
County: *"Current through Ord. 2023-18, passed 10-3-2023"*) plus title/chapter names.

**Both attempts hit the wall and aborted by design.** The loader stops when the challenge rate
exceeds 20% rather than pushing:

- attempt 1 — all 230 clients at 4.5s spacing → aborted after 9 clients
- attempt 2 — 33 county clients only at **10s** spacing, after a 2-minute cooldown → aborted after
  16, `requests=26 challenges=10`

Responding to pushback by asking for *less, slower* is the correct move; it still failed, so
amlegal is recorded **BLOCKED**. 9 counties were read before the wall; **221 of 230 Indiana
clients remain unassessed.**

### 6.2 Code Publishing — `codepublishing.com` — **BLOCKED**

> HTTP 403 with a Cloudflare managed challenge served on **robots.txt itself**:
> `Enable JavaScript and cookies to continue`

The permission file could not be read, so no crawl of this host can be justified. Not attempted.

### 6.3 General Code eCode360 — `ecode360.com` — **BLOCKED BY ROBOTS**

> `User-agent: *`
> `Disallow: /search`
> `Disallow: /search/`

The search interface is the only systematic route to provisions and it is explicitly disallowed,
so it was not used. No permitted enumeration path was found either — `/IN` returns an
"eCode360 Error" page despite HTTP 200. Not crawled.

### 6.4 Municode — permitted, **but read this**

Municode's robots.txt grants the generic agent full access:

> `User-agent: *`
> `Content-Signal: search=yes,ai-train=no,use=reference`
> `Allow: /`

It separately disallows a named list of bulk AI crawlers — `Amazonbot`, `Applebot-Extended`,
`Bytespider`, `CCBot`, **`ClaudeBot`**, `CloudflareBrowserRenderingCrawler`, `Google-Extended`,
`GPTBot`, `meta-externalagent`.

**Flagging this for your ruling rather than deciding it silently.** This run used a
self-identifying research agent string (`decennial-indiana-siting/1.0`), which falls under the
`*` group (`Allow: /`), and the use is reference retrieval of short publisher-supplied search
fragments — matching `search=yes` / `use=reference` and not `ai-train`. The disallow list is
precisely the set of bulk *training* crawlers. On that reading, access is permitted. A stricter
reading — that `ClaudeBot` covers any Anthropic-operated agent — would make this source
off-limits. The corpus is small and cheaply rebuilt if you take the stricter view; nothing about
the pipeline depends on retaining it.

---

## 7. Tables written (all registered in the same run)

| table | rows | what |
|---|---|---|
| `in_ordinances_dc_v2` | **153** | Municode hits, 36 columns, ALL hit fields + `raw_hit` JSON |
| `in_ordinances_dc_coverage_v2` | 45 | per-jurisdiction FOUND / SEARCHED_NONE_FOUND / NOT_REACHABLE |
| `in_ordinances_publisher_inventory_v2` | 3 | publisher-level walls, verbatim |
| `in_ordinances_amlegal_coverage_v2` | 230 | every Indiana amlegal client + status + publisher currency |
| `in_ordinances_dc_county_sites_v2` | 6 | moratoria/bans, evidence-graded (2 verified, 4 leads) |

`in_ordinances_amlegal_named_v2` was **not created** — the heading scan found no named
data-centre chapter in the 9 counties reached before the wall, and the loader does not create
empty tables. Its absence means "zero named chapters in 9 of 230 clients", not "not run".

`_registry` row written for each; one row per source appended (never merged) to
`energy.registry_sources` with `updated_by='indiana-app-ordinances-agent'` — 7 rows, in which the
amlegal heading-scan appears **twice** because it was attempted twice (4.5s, then 10s). Both
attempts are kept: the registry is append-only and each row is a distinct observation of the wall.
`energy-platfrom.energy` was otherwise read-only. Nothing was dropped or truncated.

**Dates:** every one of the 153 rows carries the publisher's own currency sentence
(`codified_through_text`, e.g. *"Codified through Ordinance No. 48-25, enacted July 15, 2025"*)
plus `publisher_publish_date` / `publisher_online_date`. `_pulled_at` is a separate column and is
never mixed with them. Posture is carried as the publisher's own words in `posture_terms_found`
(`permitted use` 7, `accessory use` 5, `special use` 3, `special exception` 2, `prohibited` 1) —
no scale was invented.

---

## 8. What I would do next, in priority order

1. **Triage the 146 candidate rows.** Human reads of the `"data processing"` and
   `"telecommunications facility"` hits will decide whether Hamilton(11), Lake(18), Marion(13) and
   Porter(9) actually regulate data centres. This is the cheapest large gain available.
2. **Verify the 4 county-site leads** (Marshall's reported *ban* first — a prohibition is the
   strongest siting signal in the set) and sweep the remaining 86 county `.gov` sites for 2025–26
   moratoria. §2 shows this route carries the decision-relevant posture and the codified route
   does not.
3. **Resolve amlegal.** 221 Indiana clients including 24 county governments are one access
   decision away. The polite options are a contact to American Legal for permitted bulk/API
   access, or a licensed feed — not a technical workaround.
4. Do **not** treat the 55 `NOT_SEARCHED` counties as silent anywhere in the product.
