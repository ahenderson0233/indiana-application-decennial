# D10 / D13 Indiana Tax Lien Discovery — Findings

**Date:** 2026-08-15 · **Mode:** DISCOVERY ONLY — no corpus scraped, no BigQuery writes, no accounts created, no gates worked around.
**Method:** curl (UA `energy-platform-discovery/0.1 (public-records research; read-only)`, ≥1.2 s between same-host requests, read-only GETs), WebFetch for content extraction, one interactive browser session on Marion County's public search form (no search executed, no CAPTCHA touched — form inspection only).
**Registry rows examined:** `d10:state-tax-lien:in`, `d13:federal-tax-lien:in`, both currently `NOT ATTEMPTED - county-recorder-tier`.

---

## 1. Verdicts

### `d10:state-tax-lien:in` — **PARTIALLY VIABLE** (statewide index EXISTS; every route is registration- or fee-gated → BLOCKED under pure no-account/no-payment rules; VIABLE via cheap procurement)

**The registry premise is wrong in a useful way.** Indiana DOR tax warrants are **not county-recorder-tier and never were**. They are filed with the **circuit court clerk** of each county, who enters them on the county **Judgment Book** — and since the e-Tax Warrant project, that happens through a single statewide system (INcite, run by the Office of Judicial Administration). Per the OJA project page (secure.in.gov/courts/oja/tech/tax-warrants/): DOR provides *"an electronic file with tax warrants to be processed by Circuit Court Clerks. INcite picks up the file and creates an electronic Judgment Book record of the filing."*

So a **central statewide index exists**. Access routes, all gated:

| Route | Gate | Price |
|---|---|---|
| OJA **e-Tax Warrant Search** (INcite) | mailed User Agreement + subscription | **$600/yr** individual · $1,200/yr w/ reporting · $5,000/yr business (5 users); covers clerks of **79 counties** |
| **Doxpop Tax Warrants** (licensed reseller) | account + subscription | free tier $0 (6 searches/mo, account required) · paid from **$38/mo** (20 searches) to $7,500/mo (600k); covers **all 92 counties** (Marion back to 1970) |
| Indiana **DOR** | no public list at all | INTIME "Lien Balance Inquiry" is for the taxpayer/agents, not public |
| **MyCase** (public.courts.in.gov/mycase) | n/a | **tax warrants do not appear** — they are Judgment Book records, not court cases |
| County clerks individually | manual | no bulk/API anywhere found |

- **The prior "BLOCKED — public.courts.in.gov / mycase.in.gov" registry note could not be located in the repo** (searched `energy-platform/` for `mycase`, `courts.in.gov`, `BLOCKED`+`Indiana`). What exists is `data/_p3_fragment_courts.json`, which marks IN MyCase **free statewide, "one of the best in the country"** for MF/EV/ES case types, and V2-registry language marking *Tyler eCourts-type* portals ToS-No (other states). Whatever that block was, **it is moot for D10: tax warrants are not in MyCase at all.** MyCase robots.txt allows the landing/search shell but disallows case-detail paths (`/mycase/ca…`, `/mycase/pa…` etc.) and all `*.pdf`/`*.tif` — so MyCase was never programmatically crawlable for detail records anyway.
- No ToS-prohibited scraping was attempted anywhere; nothing free-and-bulk exists for this signal.

**Registry correction to carry back:** re-key `d10:state-tax-lien:in` from `county-recorder-tier` to **`county-clerk-tier with paid statewide index (INcite e-Tax Warrant / Doxpop reseller)`**, status **BLOCKED — fee/registration-gated; procurement candidate at $600–1,200/yr**. After ID ($30–125), this is the second-cheapest statewide state-tax-lien buy identified across all 51 geographies.

### `d13:federal-tax-lien:in` — **VIABLE** (via free IRS FOIA extract; recorder-tier scraping itself is BLOCKED)

**The county-recorder premise is CONFIRMED by statute.** IC 36-2-11-25 (verbatim, via Justia 2025 Indiana Code): *"In order for a lien covered by this section to be perfected, notice of the lien must be filed in the office of the recorder of the county in which the real or personal property subject to the lien is located."* — covering *"any other federal lien on real property or any federal tax lien on personal property."* The recorder *"shall enter it appropriately in the entry book and in the miscellaneous record."* There is **no Indiana SOS/UCC route** for NFTLs (INBiz UCC holds UCC filings; SOS bulk is separately BLOCKED at $9,500+$500/mo and already formally rejected).

**But a national, free, government-published route exists that bypasses all 92 recorders:**

> IRS, **Automated Lien System (ALS) Database Listing** (irs.gov/privacy-disclosure/automated-lien-system-database-listing):
> *"A standard listing of business liens extracted quarterly from the IRS Automated Lien System database is available in pipe-delimited text format on compact disc (CD)."*
> *"Starting January 1, 2023, we'll no longer charge for FOIA requests seeking IRS Automated Lien System database listings."*
> Fields include: *"Lien ID Number, TP ID Number, TP Name and Address, Lien Status."*
> Caveat: *"The database from which this information was extracted doesn't represent the legal filings of notices of federal tax liens. The data, therefore, may be incomplete and, in some instances, inaccurate. For official purposes, confirm all data with the right local filing jurisdictions."*

- **Business liens only** — which matches this platform's commercial-parcels-only boundary exactly (no individual profiling by construction).
- It is a FOIA *request* (a letter), not an endpoint — a lawful procurement step, $0.
- Recorder-tier confirmation for any deal-critical parcel remains a manual per-parcel check (free at Fidlar Direct Search counties, interactively).

**Confirmed at county level:** Marion County's free Fidlar Direct Search exposes document types **`FEDERAL TAX LIEN`** and **`FEDERAL TAX LIEN RELEASE`** (observed in the live document-type list, 2026-08-15). No state-tax-warrant doc type exists at the recorder — consistent with warrants living at the clerk.

---

## 2. Per-county sample (10 of 92, largest first)

| County | Public online recorder search? | Vendor / platform | Free or gated | Bulk / API? | Evidence |
|---|---|---|---|---|---|
| **Marion** (Indianapolis) | YES | **Fidlar** — Direct Search (free) + Laredo (subscr.) + Tapestry (pay/search) | Free index search, **reCAPTCHA-gated**; images paid | **NO** — Angular SPA, undocumented backend, explicit anti-mining notice (quote §4) | `inmarion.fidlar.com/INMarion/DirectSearch/` HTTP 200 |
| **Lake** | YES per county materials, self-hosted | **Self-hosted** `lcrecorder.com` | reportedly free index | UNKNOWN — **site unreachable from this network** (connect timeout :443 and :80, HTTP 000) | `www.lcrecorder.com` timeout ×2; `inlake.fidlar.com` resolves but DirectSearch 404 |
| **Allen** (Fort Wayne) | YES | **Fidlar** — Direct Search (free, data from 1970) + Laredo + Tapestry | Free index; images paid | NO public API | `allencountyrecorder.us` 200; links `inallen.fidlar.com/INAllen/DirectSearch/#/search`; `inallen.fidlar.com/robots.txt` 404 (none declared) |
| **Hamilton** | YES | **Fidlar** — Laredo + Tapestry only | **Paid only** (Tapestry $8.75/search + $1/page; Laredo monthly from 100 min) | NO | `hamiltoncounty.in.gov/534` ; `inhamilton.fidlar.com/INHamilton/DirectSearch/` **404** (no free tier) |
| **St. Joseph** (South Bend) | YES | **Fidlar** — Laredo (subscr. + escrow) + Tapestry | Paid only | NO | `sjcindiana.gov/412/Land-Records-Search` 200; `instjoseph.fidlar.com/…/DirectSearch/` **404** (two app-name variants tried) |
| **Elkhart** | YES | **Fidlar** — Laredo + Tapestry | Paid only | NO | `elkhartcounty.com/en/all-departments/recorder/` 200 (curl; 403 to WebFetch) — page references Laredo/Tapestry/Fidlar |
| **Tippecanoe** (Lafayette) | YES | **Fidlar** — Laredo (monthly fee) + Tapestry ($8.95/search) | Paid only | NO | `tippecanoe.in.gov/343/Recorder` 200 |
| **Vanderburgh** (Evansville) | YES | **Fidlar Tapestry** (+ free in-office terminals only) | Paid online | NO | `evansvillegov.org/county/department/index.php?structureid=32` 200; Deeds.com corroborates; no fidlar subdomain (`invanderburgh.fidlar.com` NXDOMAIN) |
| **Porter** | YES | **Fidlar** — Direct Search (free, back to early 1978) + Laredo + Tapestry | Free index; images paid | NO | `portercountyin.gov/1898/Direct-Search` 200 → `inporter.fidlar.com/INPorter/DirectSearch/` (XSoft Engage link = assessor, not recorder) |
| **Hendricks** | YES | **Doxpop** | Account-gated; free tier 6 searches/mo; paid from $38/mo | NO ungated API | `co.hendricks.in.us/topic/index.php?topicid=92&structureid=20` 200 (curl; 403 to WebFetch) → doxpop.com + `watch.doxpop.com/property/` |

---

## 3. Vendor concentration — the useful finding

**Two vendors + one state agency + one federal FOIA office cover essentially everything.**

1. **Fidlar Technologies** (Laredo / Tapestry / Direct Search) — **8 of the 10 largest counties sampled** (all except Lake self-hosted and Hendricks-Doxpop). Three product tiers: Laredo (pro subscription), Tapestry (registration + ~$8.75–8.95/search + $1/page), **Direct Search (free, no account — but reCAPTCHA-gated, wildcard-disabled, explicitly anti-data-mining, index-only, and only some counties license it: Marion/Allen/Porter yes; Hamilton/St. Joseph/Lake no)**. **No public ungated API.** No robots.txt on the fidlar county hosts (404 = nothing declared), but the in-page anti-mining statement and CAPTCHA are the operative gates — automation is out.
2. **Doxpop** — recorder module covers **44 (mostly small/mid) counties** (`doxpop.com/prod/in/recorderCounties.jsp`, verified 2026-08-15 — of our 10-county sample only Hendricks), court records ~90 counties, and — decisive for D10 — **statewide tax warrants for all 92 counties** (`doxpop.com/prod/in/taxWarrantCounties.jsp`) as a licensed INcite reseller. Everything account-gated; fee schedule verbatim: *"Price per month $0.00 $38.00 $68.00 $120.00 … Included searches per month 6 20 60 200 …"*, per-page images $2.10→$1.13, *"Access to all cases, documents, and tax warrants"* at every tier. **No ungated API.**
3. **OJA / INcite** — the single statewide D10 index (79 counties direct), $600–5,000/yr, mailed user agreement.
4. **IRS FOIA (ALS)** — the single national D13 business-lien extract, free.

So the "92 problems" reduce to: **one FOIA letter (D13) + one $600–1,200/yr subscription decision (D10)**. Recorder-by-recorder scraping is both unnecessary and blocked (CAPTCHA/anti-mining/paywalls).

Third-party aggregators surfaced in search (`indianaofficialrecords.com`, `ustitlerecords.com`, propertychecker etc.) are commercial paywalled lookup sites, not public feeds — not pursued.

---

## 4. Endpoint log (every endpoint touched)

| # | URL | HTTP | robots.txt permits? | Login/reg/pay required? | Wall quote (verbatim) |
|---|---|---|---|---|---|
| 1 | `https://www.in.gov/robots.txt` | 200 | n/a | no | — (`/sos/` disallowed; `/dor/…/tax-warrants/` and `/courts/…` paths allowed) |
| 2 | `https://www.in.gov/dor/i-am-a/software-professionals/tax-warrants/` | 200 | yes | no | no public warrant list; ATWS/Sheriff Portal are for county officials/agents |
| 3 | `https://secure.in.gov/courts/oja/tech/tax-warrants/` | 200 | yes | no (info page) | *"INcite picks up the file and creates an electronic Judgment Book record of the filing."* |
| 4 | `https://secure.in.gov/courts/oja/tech/tax-warrants/search/` | 200 | yes | service = mailed agreement + fee | *"With a subscription to the Tax Warrant Application on INcite … users can get secure access to tax warrant information maintained by the Clerks of Court in 79 Indiana counties."* Tiers: $600 / $1,200 / $5,000 per yr |
| 5 | `https://public.courts.in.gov/robots.txt` | 200 | n/a | — | landing allowed; `/mycase/{ca,at,us,er,pa}…`, `/portal`, `/docket`, `*.pdf`, `*.tif` disallowed |
| 6 | `https://public.courts.in.gov/mycase/` | 200 | landing: yes; detail paths: **no** | no (search shell) | tax warrants absent (Judgment Book records, not cases) |
| 7 | `https://www.in.gov/courts/public-records/` | 200 | yes | no | *"Requests for bulk court data are governed by Administrative Rule 9(F)."* (written request to Office of Court Services) |
| 8 | `https://www.in.gov/courts/help/mycase/search-tips/` | 200 | yes | no | no tax-warrant record type listed |
| 9 | `https://www.doxpop.com/robots.txt` | 200 | n/a | — | court ViewCaseDetails/calendar paths disallowed; recorder/JSP pages allowed |
| 10 | `https://www.doxpop.com/prod/recorder/` | 200 | yes | account for any search | JS SPA shell |
| 11 | `https://www.doxpop.com/prod/in/taxWarrantCounties.jsp` | 200 | yes | data behind account | coverage = all 92 counties (Marion from Jan 1970) |
| 12 | `https://www.doxpop.com/prod/in/recorderCounties.jsp` | 200 | yes | data behind account | 44 counties listed |
| 13 | `https://www.doxpop.com/prod/info/fees.jsp` | 200 | yes | n/a (public price list) | *"Price per month $0.00 $38.00 $68.00 $120.00 $218.00 …"*; free tier = 6 searches/mo, account required |
| 14 | `https://elkhartcounty.com/en/all-departments/recorder/` | 200 (curl) / 403 (WebFetch UA) | no robots block found | n/a | references Laredo/Tapestry (Fidlar) |
| 15 | `https://www.co.hendricks.in.us/topic/index.php?topicid=92&structureid=20` | 200 (curl) / 403 (WebFetch UA) | no robots block found | n/a | links doxpop.com, watch.doxpop.com |
| 16 | `https://www.lcrecorder.com/` | **000 — connect timeout (:443, :80)** | unknown | unknown | Lake Co. self-hosted index; unreachable from this network — mark VERIFY-FROM-OTHER-NETWORK, not BLOCKED |
| 17 | `https://www.allencountyrecorder.us/searching-and-printing-documents` | 200 | yes | Direct Search free; Laredo/Tapestry paid | links `inallen.fidlar.com/INAllen/DirectSearch/#/search` |
| 18 | `https://www.portercountyin.gov/1898/Direct-Search` | 200 | yes | Direct Search free | links `inporter.fidlar.com/INPorter/DirectSearch/` |
| 19 | `https://www.sjcindiana.gov/412/Land-Records-Search` | 200 | yes | Laredo/Tapestry only | Laredo requires agreement + escrow account |
| 20 | `https://www.tippecanoe.in.gov/343/Recorder` | 200 | yes | Laredo/Tapestry only | Tapestry $8.95/search |
| 21 | `https://www.evansvillegov.org/county/department/index.php?structureid=32` | 200 | yes | Tapestry only online | free public terminals in office only |
| 22 | `https://inmarion.fidlar.com/INMarion/DirectSearch/` | 200 | robots.txt 404 (none declared) | free, **reCAPTCHA on search** | *"Security enhancements are included to prevent data mining and ensure document integrity. Therefore, party name information must be searched exactly as the documents are indexed, the 'wildcard' option is not available. … Document information is available five days after recording. In compliance with IC 36-1-8.5 regarding restricted addresses, parcel number search is not available."* Doc types observed: FEDERAL TAX LIEN, FEDERAL TAX LIEN RELEASE |
| 23 | `https://inhamilton.fidlar.com/INHamilton/DirectSearch/` | 404 | — | — | county has no Direct Search license |
| 24 | `https://instjoseph.fidlar.com/INStJoseph/DirectSearch/` (+`INSaintJoseph` variant) | 404 | — | — | same |
| 25 | `https://inlake.fidlar.com/INLake/DirectSearch/` | 404 | — | — | same |
| 26 | `inelkhart|intippecanoe|invanderburgh.fidlar.com` | DNS NXDOMAIN | — | — | no Fidlar-hosted free tier |
| 27 | `https://tapestry.fidlar.com/TapestryEON/TapestryEON.WebSite/login` | 200 | — | **login + pay-per-search** | login SPA ("Tapestry EON"); registration required before any search |
| 28 | `https://www.irs.gov/privacy-disclosure/automated-lien-system-database-listing` | 200 | yes | FOIA request (free) | see §1 D13 quotes |
| 29 | `https://law.justia.com/codes/indiana/title-36/article-2/chapter-11/section-36-2-11-25/` | 200 (curl) / 403 (WebFetch UA) | yes | no | statute text quoted in §1 |

No gate was circumvented. No account was created. No CAPTCHA was solved or submitted. The Marion Direct Search session inspected the public form and its document-type dropdown only; no search was executed.

---

## 5. Recommended acquisition route + honest effort estimate

### D13 federal tax liens — do this first
1. **File the IRS ALS FOIA request** for the quarterly business-lien listing (free since 2023-01-01). One letter/portal submission; media arrives as pipe-delimited text (on CD — budget for that annoyance). **Effort: ~1 hr to file; typically weeks–months of waiting; ~0.5–1 day to write the loader** (same shape as existing state_bulk loaders: `(lien_id, tp_name, tp_address, lien_status)` → filter IN → match name/address to commercial parcels, quality_mult 0.6 owner-keyed; address present → geocode → parcel join per the strict IN warn_clean method).
2. Deal-critical parcels only: manual interactive confirmation at the county recorder (free at Marion/Allen/Porter Direct Search; $8.75/search Tapestry elsewhere). Never automated.
3. Note ALS covers **business** liens only — for this platform that is the whole target universe, not a gap.

### D10 state tax warrants — a procurement decision, not an engineering one
1. **If $600–1,200/yr is acceptable:** OJA e-Tax Warrant individual (+reporting) subscription is the canonical statewide source (79 counties of clerks' judgment books). Doxpop ($38–120/mo) is the licensed-reseller alternative with all-92-county coverage and a nicer UI, but per-search metering makes it a lookup tool, not a feed. Check the OJA user agreement's redistribution clause before purchase — it may constrain warehouse storage (assume clause exists until read; the agreement PDF is mailed, not published).
2. **If no budget:** record `BLOCKED — fee/registration-gated statewide index (INcite $600/yr; Doxpop reseller $38/mo); no free public route; DOR publishes no list; not in MyCase; county clerks have no bulk export`. That is the honest terminal state under current rules.
3. Either way, **fix the registry tier label** (county-CLERK, not county-recorder) and note the mycase-BLOCKED entry could not be found in the repo and is moot for this signal.

### Explicitly NOT recommended
- Scraping Fidlar Direct Search (reCAPTCHA + verbatim anti-data-mining notice = double no under project rules).
- Creating Doxpop free-tier accounts to search programmatically (account creation is out of bounds; 6 searches/mo is useless for a corpus anyway).
- Any per-county crawl of 92 recorders/clerks — unnecessary given the two central routes above.
