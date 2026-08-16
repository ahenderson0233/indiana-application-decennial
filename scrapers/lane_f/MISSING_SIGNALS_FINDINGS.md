# LANE F — MISSING INDIANA SELLER-INTENT SIGNALS: DISCOVERY FINDINGS

*Run 2026-08-15. DISCOVERY ONLY — no corpus scraped, no BigQuery writes, no files touched outside
`lane_f/`. Every endpoint below was touched at most 1–3 times, read-only, ≥1s per host, with an
identifying User-Agent (`OrenniaRebuild-discovery/1.0 (+decennialgroup.com; public-data source
discovery)`). Statuses are what THIS network saw on 2026-08-15; `000` = connection/DNS failure,
not an HTTP response. Tax liens (D10/D13) deliberately excluded — separate agent.*

**Scope note on numbering:** these six use the tasking's labels. They map onto the warehouse
registry as: A1 = `A1_actively_marketed`, D4 = `D4_tax_delinquent`, D9 absentee =
registry `D18_absentee`, D15 = `D15_mechanics_lien`, D22 environmental = new (registry `D22`
is probate — do not collide the ids when wiring), D23 surplus = registry `A2_gov_surplus`.

---

## 1. A1 — Market listings (commercial property listed for sale)

### VERDICT: PARTIALLY VIABLE — the data exists, is free, and is state-published, but the host's robots.txt disallows programmatic access for everyone except Googlebot/Bingbot.

**The Indiana instance exists and is official.** IEDC's homepage ("Find Sites" → "Featured
Sites") links directly to `https://properties.zoomprospector.com/statein` — the same GIS
Planning / ZoomProspector platform behind our national `zoomprospector_listings` table
(4,059 rows), and `STATEIN` is **already rostered** in
`energy-platform/data/si_p2_targets.json` (`targets.zoomprospector.statewide.IN = "STATEIN"`,
plus an `"indiana"` county-collective code and `NCIEDP` likely north-central-Indiana). The
loader `ingest/load_zoomprospector_bq.py` already supports `--code STATEIN`.

**The wall (verbatim).** `https://properties.zoomprospector.com/robots.txt` (HTTP 200):

```
User-agent: Googlebot
Disallow:

User-agent: Bingbot
Disallow:

User-agent: *
Disallow: /
```

That is a blanket disallow for any agent that is not Google/Bing. Consistent with it, the
sitemap route the loader walks (`/sitemap/STATEIN/properties/1`) returned **200 with a 0-byte
body** to our UA, while the client page `/STATEIN` returned 200 with a 376 KB React/Next.js SPA
(data served from `gisservices.zoomprospector.com`). Under our own rule — a source whose
robots/terms prohibit programmatic access is recorded and left alone — automated collection
from this host is **BLOCKED**, Indiana and national alike.

> ⚠ **Integrity flag beyond this lane:** the already-held national `zoomprospector_listings`
> table was loaded from this same robots-disallowed host. Worth an operator review; not
> actioned here.

**Endpoints touched:**

| URL | HTTP | robots permits? | registration/payment |
|---|---|---|---|
| `https://properties.zoomprospector.com/robots.txt` | 200 | — | none |
| `https://properties.zoomprospector.com/STATEIN` | 200 (376,263 B SPA) | **NO** (`User-agent: * Disallow: /`) | none |
| `https://properties.zoomprospector.com/sitemap/STATEIN/properties/1` | 200, 0 bytes | NO | none |
| `https://statein.zoomprospector.com/robots.txt` | 503 | n/a | n/a |
| `https://unitedstates.zoomprospector.com/robots.txt` | 200 (only googlebot restricted on `/common/services/`, `/common/helpers/`) | partial | none |
| `https://www.zoomprospector.com/robots.txt` | 404 (no robots) | yes by default | none |
| `https://iedc.in.gov/` | 200 | `iedc.in.gov/robots.txt` → 404 (no robots) | none |
| `https://iedc.in.gov/indiana-ssi-sites` | 200 | yes | none |
| `https://indianasiteselection.com/` | 000 — **NXDOMAIN** | n/a | n/a |
| `https://hoosiersites.com/` | 000 — DNS resolves (67.55.91.27) but no HTTP/HTTPS service | n/a | n/a |
| `https://www.locationindiana.com/` (Duke Energy's Indiana ED portal per its own press releases) | 000 — unreachable | n/a | n/a |

**What else IEDC publishes:** the Strategic Sites Inventory page (`/indiana-ssi-sites`) gives
program stats — **1,811 sites identified, 235,402 acres, 490 sites ranked 4.0+, 70 potential
mega-sites, 74 counties reviewed** — but NO public database; access is "Featured Sites"
(→ ZoomProspector) or an email-a-site-specialist request form. A `/plug-in-ready-sites` page
also exists (not fetched this pass).

**One row would represent:** one actively-marketed commercial site or building (address,
acreage/sq-ft, price, utilities, broker).
**Estimated Indiana rows:** low hundreds on STATEIN (IEDC features a curated subset of the
1,811-site SSI universe; national table averages ~35 rows/code but statewide codes run larger).
**Acquisition effort:** technically trivial (loader exists) but robots-blocked. Lawful routes:
(a) ask IEDC/GIS Planning for the inventory export — IEDC explicitly offers site-search
fulfillment; (b) treat Googlebot-only cloaking as a hard stop and skip. Recommend (a).

---

## 2. D4 — Tax delinquency (pre-sale treasurer/auditor lists)

### VERDICT: VIABLE — seasonal, via SRI's free public lists + county statutory advertisements. No year-round statewide delinquency roll exists.

**Structure of the signal in Indiana:** there is no continuously-published "all delinquent
parcels" roll. Delinquency becomes bulk-public at certification for tax sale (IC 6-1.1-24):
the auditor/treasurer certify the list, it is advertised, and the sale vendor posts the parcel
list publicly ~1 month before each sale (sales cluster Aug–Oct). So D4-Indiana is inherently a
**seasonal pre-sale snapshot**, one step earlier in distress than the tax-SALE results we hold.

**Primary route — SRI Incorporated** (vendor for the large majority of Indiana's 92 counties):

| URL | HTTP | robots permits? | registration/payment |
|---|---|---|---|
| `https://www.sriservices.com/robots.txt` | 200 — `User-agent: * / Disallow:` (empty) | **YES, all allowed** | none |
| `https://www.sriservices.com/` | 200 — React SPA: "You need to enable JavaScript to run this app." | yes | none to view lists |
| `https://www.sriservices.com/sitemap.xml` | 200 but returns the SPA HTML, not XML | yes | none |
| `https://properties.sriservices.com/auctionlist` (URL cited in SRI's own help KB) | 000 — **NXDOMAIN** (stale doc) | n/a | n/a |
| `https://tsm.sriservices.com/tsm/` | 000 — unreachable | n/a | n/a |
| `https://www.zeusauction.com/robots.txt` | 404 (no robots) | yes by default | account required **to bid only** |

SRI's knowledge base states lists are public: "A complete property list may be obtained at
www.sriservices.com" — and the only registration language found applies to bidding, not
viewing: "you will first need to create an account on https://www.zeusauction.com … select
'Click to Register'." We would never register: lists, not bids.

**Secondary routes (all open):** GUTS (`https://www.g-uts.com/tax-sale-information/`) vends a
minority of counties; counties post the statutory advertisement directly — verified examples:
Hamilton `https://www.hamiltoncounty.in.gov/452/Real-Property-Tax-Sale` and a live
auditor delinquency page (`hamiltoncountyauditor.org/textonly/tax_delinquent.asp`), Allen
County DocumentCenter PDFs (`allencounty.in.gov/DocumentCenter/View/11291/25TSINFO`), LaPorte
(`laporteco.in.gov/.../LaPorte-County-2025-Certificate-Sale-Advertisement.docx`), Decatur,
Henry (PDFs). Marion (largest sale in the state by parcel count) exposes a "Tax Sale Viewer"
via indy.gov.

**One row would represent:** one parcel certified delinquent and eligible for an upcoming tax
sale (parcel number, owner-of-record name as published, situs, minimum bid = taxes owed).
**Estimated Indiana rows:** ~15k–30k parcels per annual cycle statewide (estimate: Marion
alone typically runs thousands; 92 counties × hundreds each). Parcel-keyed 1.0 — lists carry
the 18-digit state parcel number that matches our `parcels_in` spine key (98.2% keyed).
**Acquisition effort:** moderate. SRI's SPA needs the Playwright render recipe the project
already owns (`load_spa_render_bq`); robots explicitly permits. County-PDF harvest for
non-SRI counties is grind work. Seasonal: schedule Jul–Oct.

---

## 3. D9 — Absentee ownership

### VERDICT: VIABLE — but NOT derivable from data we hold. One statewide bulk file closes it.

**Derivability check (done first, as tasked):** our `parcels_in` (3,637,663 rows, 37 cols) is
the IndianaMap statewide layer. Field list pulled live from
`https://gisdata.in.gov/server/rest/services/Hosted/Parcel_Boundaries_of_Indiana_Current/FeatureServer/0?f=json`
(HTTP 200): `parcel_id, state_parcel_id, local_id, nguid, county_fips, county_id,
prop_add, prop_city, prop_state, prop_zip, dlgf_prop_address, dlgf_prop_address_city,
dlgf_prop_address_state, dlgf_prop_address_zip, dlgf_prop_class_code, tax_* , latitude,
longitude, loaddate, source_*` — **situs address and property-class only. NO owner name, NO
owner mailing address.** The 2022 vintage layer was checked too: same absence. **D9 is not
derivable from current holdings.**

**The acquisition route — DLGF/Gateway statewide assessment roll.** Indiana counties must
submit a `PARCEL` file whose layout is fixed by regulation. 50 IAC 26-20-4 (verified at
law.cornell.edu) requires: **"Owner Name" (cols 224–303), "Owner Street Address or P.O. Box"
(304–363), "Owner Address City" (364–393), "Owner Address State or Province or Territory"
(394–423), "Owner Address ZIP Code" (424–433)** — exactly the fields absentee derivation
needs, plus the same 18-digit parcel number our spine uses.

| URL | HTTP | robots permits? | registration/payment |
|---|---|---|---|
| `https://gateway.ifionline.org/public/download.aspx` (Gateway "Download Data": Real Property, Personal Property, Adjustments bulk files) | 200 | yes | **none stated** |
| `https://www.indianamap.org/documents/4e0b94a421404f3ea5be65058bd85edd` ("Download DLGF Real Property Assessment Tables 2022 – Geodatabase Format") | 200 | yes | none |
| `https://gisdata.in.gov/server/rest/services/Hosted/Parcel_Boundaries_of_Indiana_Current/FeatureServer/0?f=json` | 200 | robots.txt → 301 redirect (REST API; export formats include csv/geojson, maxRecordCount 2000) | none |
| `https://data.indy.gov/datasets/IndyGIS::parcels-w-owner-information-assessed-values/about` (Marion-only fallback, owner info in title) | 200 | yes | none |

**One unresolved detail, stated honestly:** the Gateway download page itself does not enumerate
columns, and one automated read of it suggested the *public* Real Property export may strip
owner fields even though the regulated submission format contains them. **First acquisition
step is therefore a 30-minute verification: download one small county's Real Property file and
inspect the header.** If stripped, the fallback is the DLGF data team's published bulk-request
address (`Data@dlgf.in.gov`, a role account) and the IndianaMap geodatabase edition.

**One row would represent:** one Indiana parcel scored `absentee = owner mailing
state/zip ≉ situs state/zip` (with distance graduation).
**Estimated Indiana rows:** ~3.6M scored; the commercially-classed subset (via
`dlgf_prop_class_code` we already hold) is the deliverable.
**Acquisition effort:** LOW — one statewide annual file (or 92 county files from one portal),
no registration, joins on `state_parcel_id` at our measured 98.2% key rate.

---

## 4. D15 — Lien filings (mechanics/construction)

### VERDICT: BLOCKED — Indiana specifics confirm the prior national finding: a procurement problem, not a scraping problem.

The weekend lane (`lane_county_d12_d17_d15.md`) already concluded nationally: "NO.
Structurally unavailable as free public bulk data… Treat D15 like A1: a real signal with no
lawful free route." Indiana's recorder landscape is exactly that shape:

| Route | Status | Wall |
|---|---|---|
| Doxpop — `https://www.doxpop.com/prod/recorder` | 200 (JS shell, 787 B) | 47 Indiana counties, ~25M documents; free *name* search only, document access and any volume use behind paid subscription. robots.txt (200) disallows only SemrushBot and court-calendar paths — but the free tier exposes no bulk surface to crawl. |
| Fidlar **Tapestry** (per LaGrange/Gibson/St. Joseph county pages) | vendor pages 200 | pay-per-search, $8.75/search |
| Fidlar **Laredo** | vendor pages 200 | county-priced subscription, ~$30–$300/month **per county** |
| GovOS `publicsearch.us` | no Indiana counties identified this pass | (Dallas TX instance previously measured: CAPTCHA + login) |
| Socrata / ArcGIS / open-data presence | 0 datasets (prior lane: four independent indices × zero) | — |
| `mycase.in.gov` (Odyssey courts) | not probed this pass | would only yield lien *foreclosure suits*, a lagging subset — and is interactive-search-only |

**No Indiana county recorder was found publishing a bulk or API-accessible lien index for
free.** With 92 recorders, per-county subscriptions would be 92 separate paid/registered
relationships — squarely against the boundaries.

**One row would have represented:** one recorded mechanics-lien instrument (debtor, claimant,
amount, legal description/parcel).
**Estimated Indiana rows:** unknown; not determinable without paid access.
**Acquisition effort / recommendation:** do not scrape. If the 9 signal points are ever wanted:
(a) an APRA (Indiana Access to Public Records Act) request to a handful of large-county
recorders for a periodic lien-index export, or (b) commercial procurement (Doxpop bulk). Both
are operator decisions, not agent work. **Not worth pursuing in this rebuild phase.**

---

## 5. D22 — Environmental violations

### VERDICT: VIABLE — the easiest signal of the six. Two independent open sources, zero gates.

**Federal — EPA ECHO.** The REST API answered instantly, no key, no registration:

```
GET https://echodata.epa.gov/echo/echo_rest_services.get_facilities?output=JSON&p_st=IN&p_act=Y
HTTP 200 — QueryRows 25,330 · SVRows (significant violators) 372 · CVRows 1,423 ·
V3Rows (3+ qtrs in violation) 4,083 · FEARows (formal enforcement, 5 yr) 962 ·
INSPRows 4,606 · TotalPenalties $1,855,474,334
```

Bulk alternative: `https://echo.epa.gov/files/echodownloads/` is an **open Apache directory
index of CSVs** (HTTP 200; `AFS_ACTIONS.csv` etc. visible at top). `echo.epa.gov/robots.txt`
(200) is a standard Drupal file that does not disallow the downloads or REST paths.

**State — IDEM.** Two findings:

| URL | HTTP | robots permits? | registration/payment |
|---|---|---|---|
| `https://oe.idem.in.gov/idem_oe_order` — "Monthly Actions and Orders" enforcement database | 200 | robots.txt (200) contains **no Disallow directives at all** (only Cloudflare content-signals commentary) | **none** — public form |
| `https://gisdata.in.gov/server/rest/services/IDEM?f=json` | 200 body = `{"error":{"code":499,"message":"Token Required","details":[]}}` | n/a | **GATED — recorded, left alone** |
| `https://www.in.gov/robots.txt` | 200 — limited disallows, IDEM paths permitted | yes | none |

The `oe.idem.in.gov` database is searchable by company/person, case number, **county (all
92)**, media (Air / Water / Hazardous Waste / Solid Waste-UST), action type (**Notice of
Violation, Agreed Order, Commissioner's Order, Emergency Order**), and date range **1995 →
present**, with an "All Records" output option and hyperlinked documents. No registration.
(The one gated thing — IDEM's ArcGIS folder — is a FINDING, not a problem: the enforcement DB
and ECHO carry the signal without it.)

**One row would represent:** one facility-level violation/enforcement event, keyed by FRS
registry ID + lat/lon (point-in-parcel join to `parcels_in`), or one IDEM order document
(company, county, media, action type, date).
**Estimated Indiana rows:** 25,330 active-facility slice; ~1.4–4k in current violation; 962
formal enforcement actions (5 yr); IDEM order corpus 1995→present plausibly 5–15k documents
(not precisely determinable without enumerating).
**Acquisition effort:** LOW. ECHO bulk CSV filtered to IN is an afternoon; IDEM DB is a
form-POST enumeration by county × year at polite rates, or county-by-county "All Records"
pulls. Signal value for DC siting is dual: distress indicator on the owner AND environmental
screening on the parcel itself.

---

## 6. D23 — Public surplus disposal

### VERDICT: PARTIALLY VIABLE — everything found is open, but the Indiana-specific increment over what we hold is small.

Already held: `gov_surplus_nces` (102,178), `gov_surplus_frpp` (307,919 federal), Indianapolis.
New Indiana findings:

| Source | URL | HTTP | robots | gate |
|---|---|---|---|---|
| **IDOA Real Estate Sales** (statute-driven disposition of state land; sealed-bid RFBs + RFIs) | `https://www.in.gov/idoa/state-resource-management/state-and-federal-surplus/real-estate-sales/` and `.../surplus-real-estate/` | 200 | yes (in.gov robots) | none to view |
| **IndianaStateSurplus.com** (live auctions incl. real estate) | `https://www.indianastatesurplus.com/` | 200 | robots.txt 200 — only `/buyers/profile/` disallowed | account for bidding only |
| **State Land Office property map** (state-owned inventory, disposition context) | linked from IDOA pages | not fetched | — | none stated |
| **Evansville Land Bank Corp** | `https://evvc-evvc.opendata.arcgis.com/api/feed/dcat-us/1.1.json` — DCAT feed contains "Evansville Land Bank Corp- New App" dataset | 200 | yes | none — ArcGIS Hub open data |
| Fort Wayne / South Bend surplus or land-bank open datasets | searched, none found this pass | — | — | — |

**One row would represent:** one government property offered for disposition (owner agency,
county, acreage, description, bid/auction reference).
**Estimated Indiana rows:** small — state RFB/RFI lists run in the tens per year; Evansville
land-bank inventory is hundreds of (mostly residential) lots.
**Acquisition effort:** trivial (static pages + one ArcGIS Hub feed). **Honest value note:**
land-bank stock is residential infill — near-zero DC-siting value. The IDOA state-land RFBs
are few but occasionally *exactly* our quarry (large-acreage former institutional sites with
existing utility service), so this is a low-cost watch-list, not a corpus.

---

## RANKED RECOMMENDATION — (value to DC-siting) × (ease of lawful acquisition)

| rank | signal | verdict | why |
|---|---|---|---|
| **1** | **D22 environmental** | VIABLE | Zero gates, two redundant open sources (ECHO REST/bulk + IDEM DB), facility lat/lon → parcel join, dual use (owner distress + site screening). Cheapest points on the board. |
| **2** | **D9 absentee** | VIABLE | One free statewide bulk file (Gateway/DLGF) closes a 3.6M-parcel signal at our existing 98.2% spine-key rate. Single 30-min verification step (owner columns in the public export) before committing. |
| **3** | **D4 tax delinquency** | VIABLE (seasonal) | SRI robots explicitly permits; lists are free and parcel-keyed; needs the Playwright SPA recipe we already own + county-PDF mop-up. Schedule Jul–Oct; it is a snapshot signal, not a roll. |
| **4** | **A1 market listings** | PARTIALLY VIABLE | The data is public and state-published, but `properties.zoomprospector.com` robots.txt disallows all non-Google/Bing agents — under our own rules that is a stop. Route is a *request to IEDC*, not a scraper. Also flags a compliance review of the held national table from the same host. |
| **5** | **D23 surplus** | PARTIALLY VIABLE | Open and easy but tiny increment; keep as a low-frequency watch-list (IDOA RFBs), skip land banks for DC siting. |
| **6** | **D15 mechanics liens** | BLOCKED | 92 recorders, all behind Doxpop/Tapestry/Laredo paywalls or per-county subscriptions; zero open-data presence (confirms prior national lane). Procurement/APRA or nothing. **Not worth pursuing now.** |

**Blunt bottom line:** spend the next effort-hours on D22 and D9 — together they are perhaps
two days of work for two full statewide signals. D4 is a calendar entry for July. A1 is one
email to IEDC. D23 is a bookmark. D15 is a cheque, not a scraper, and shouldn't be written
this phase.
