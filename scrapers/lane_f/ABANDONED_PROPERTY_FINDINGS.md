# Lane F findings — Indiana abandoned/vacant STRUCTURE signal, statewide discovery (2026-08-15)

DISCOVERY ONLY. Nothing written to BigQuery. No file edited except this one.

Scope: expand the D5 abandoned/vacant **building** signal beyond the 2 municipalities held
(`in_si_indy_abandoned_vacant` 7,120; `in_si_southbend_vacant_abandoned` 47 +
`in_si_southbend_chronic_problem` 7). Explicitly excluded: vacant **land** (already derived
from parcel footprints; not a seller-intent signal).

Method: read-only HTTPS GETs, >=1 request/sec/host by construction (sequential tool calls,
15-min response cache), robots.txt fetched and recorded per host where an HTML host was
touched. Nothing gated was worked around; every wall is recorded verbatim below.
Prior work honored: `lane_c/LANE_C_FINDINGS.md` (2026-08-14) already walled Fort Wayne,
enumerated hub.mph.in.gov, and pulled the 5 South Bend and 4 Evansville distress tables;
those findings are cited, not re-probed, except where a fresh check adds information.

---

## 1. The two sources we hold — re-verified today

| item | endpoint | status | finding |
|---|---|---|---|
| Indy/Marion registry | `https://gis.indy.gov/server/rest/services/OpenData/OpenData_Infrastructure/MapServer/2` | HTTP 200 | Live count **7,120 — byte-identical to held**. There is NO fuller version. Layer name is **"Abandoned and Vacant Houses"** — residential by name. Fields: PARCEL_I, address parts, STATUS ('Abandoned'/'Vacant'), geometry. **NO event-date field exists on the layer** (confirmed weakness; snapshot semantics only). robots.txt on gis.indy.gov: 404 (absent → unrestricted). |
| Indy hub catalog check | `data.indy.gov` search API (`/api/search/v1/collections/all/items`, q=abandoned/vacant/housing) | HTTP 200 | The feature layer has been **REMOVED from the data.indy.gov hub catalog** — only the 2003 Vacant Housing Inventory PDF and 2005 Abandoned Housing Framework PDF remain. All three former hub slugs 404 (`abandoned-and-vacant-housing`, `IndyGIS::…`, `abandoned-housing`). The gis.indy.gov REST layer is now the only public copy; treat hub disappearance as delisting risk and keep the REST URL pinned. robots.txt on data.indy.gov: allows datasets, **Crawl-delay: 60**, disallows /sites/ /admin/ /sessions/ /groups/ /people/ /workspace/. |
| Indy AGO copy | `https://services3.arcgis.com/gsb70S74SUlDakBS/…/Vacant_housing_Indy_WFL1/FeatureServer` | **HTTP 200, error 499 "Token Required" (SB_0006)** | Private. BLOCKED — left alone. Same for xmaps.indy.gov folders `OpenData` and `MapIndy` (499 Token Required); only the `Accela` folder (parcel/address MapServers) is open there. |
| South Bend V&A | `https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services/AllVacantandAbandonedProperties/FeatureServer/3` | HTTP 200 | Count **47 = held**. Service description says "currently labeled vacant and abandoned" while the hub title says "Historic / Non-Authoritative" — publisher's own labels conflict; the layer IS maintained (lastEditDate epoch 1745009040017 ≈ **2025-04-18**). **HAS event date**: `Added_to_V_A_on_` (Date), plus `Original_Outcome_Date…`, `Modified`. This is the model dataset for the signal. Note: `data.southbend.gov` is **NXDOMAIN** (old Socrata portal dead; the ArcGIS hub `data-southbend.opendata.arcgis.com` replaced it). `gis.southbendin.gov/arcgis/rest/services/OpenData` now lists **only police datasets** — the old `OpenData/VacantAbandoned/MapServer` is gone from the city server; the AGOL service above is the only live copy. robots: gis.southbendin.gov 404 (absent). |

**Answer to the task's Q5:** data.indy.gov does NOT publish a fuller or more current version.
7,120 is the complete current registry; no event date exists anywhere on the layer. The
event-date fix is §4.1 below (derive from the held 910k-row code corpus), not a new pull.

---

## 2. Per-source table — municipal registries, unsafe-building/demolition lists, land banks, statewide

Robots column: "—" = ArcGIS REST API host where robots.txt is not served (services1.arcgis.com
returns 403 for robots.txt; www.arcgis.com robots.txt allows all with no disallows). ArcGIS
REST endpoints are published APIs intended for programmatic query.

| Jurisdiction | Endpoint | HTTP | robots | Reg/pay | Rows | Event date? | Structures vs land | Verdict |
|---|---|---|---|---|---|---|---|---|
| **Indianapolis/Marion** registry | gis.indy.gov …OpenData_Infrastructure/MapServer/2 (byte-identical copies at MapIndy/MapIndyProperty 11 & 16 — do not wire, per registry note) | 200 | absent→OK | no | 7,120 | **NO** | structures ("Houses") | HELD — current; **~100% RESIDENTIAL → low value for hyperscale** |
| **South Bend** V&A | services1.arcgis.com/0n2NelSAfR7gTkr1 …/FeatureServer/3 | 200 | — | no | 47 | **YES** (`Added_to_V_A_on_`) | structures | HELD — current (edited 2025-04) |
| South Bend demolition orders / chronic-problem / continuous-enforcement / code cases | same AGOL org (held tables, lane C 2026-08-14) | 200 | — | no | 80 / 7 / 241 / 20,414 | YES | structures | HELD |
| **Fort Wayne / Allen Co** | maps.cityoffortwayne.org/arcgis/rest/services | **403 Forbidden** | n/a | n/a | — | — | — | **BLOCKED** (lane C wall confirmed: acimap.us catch-alls every path incl. /arcgis/rest/services; gis.allencounty.us NXDOMAIN; assessor behind Beacon/Schneider ToS interstitial). New check this run: All In Allen comp-plan hub (`all-in-allen-hlplanning.hub.arcgis.com`) search q=vacant → **0 items**. Search-engine trap logged: `open-data-cfw.hub.arcgis.com` is Fort **Worth TX**, not Fort Wayne. No FW registry data exists publicly. |
| **Evansville** registry | evansvillegov.org (Building Commission administers; ordinance exists) + full REST sweep of maps.evansvillegis.com/arcgis_server/rest/services (27 folders: INSPECTORS, PROPERTY, BC, ECONOMIC_DEVELOPMENT… all enumerated) | 200 | 307→hub robots (OK) | no | 0 published | — | — | **NOTHING-PUBLISHED** — registry is paper/administrative; no V&A layer on the city server. (Held already from this host: foreclosures 5,758; taxsale 3,202+941; **4,190 'BUILDING WRECKING' demolition permits incl. 419 COMMERCIAL** — the strongest commercial-structure distress signal Evansville publishes.) |
| **Evansville Land Bank Corp** (IC 36-7-38) | services1.arcgis.com/iZyBOluseC8ffQc2/…/Landbank_Available_July2025/FeatureServer/208 (found via evvc-evvc.opendata.arcgis.com web-app config) | 200 | — | no | **123** | NO (snapshot "July2025" in name) | mix; city says "vast majority vacant lots"; no structure flag in schema (fields: NAME, StatePIN, prop_street, WEBURL only) | **VIABLE (marginal)** — 1 ArcGIS pull; availability-not-distress semantics (land bank = motivated seller); join StatePIN (82-…) to parcels to derive structure/land + class |
| **Gary** parcel survey (2014-15; 6,315 abandoned homes + **554 vacant businesses**) | garycounts.org | **TLS FAIL** — verbatim: `Hostname/IP does not match certificate's altnames: Host: garycounts.org. is not in the cert's altnames: DNS:*.github.com, DNS:github.com` (dangling GitHub Pages CNAME) | n/a | n/a | 0 reachable | had survey date | distinguished bldg vs land | **DEAD** |
| Gary survey map | garymaps.com | **NXDOMAIN** (`getaddrinfo ENOTFOUND`) | n/a | n/a | — | — | — | **DEAD** |
| Gary city-owned inventory | gary.gov/redevelopment → `gary-redevelopment.regrid.com/m/2025-city-of-gary-owned-parcels` | 200 (city page) | n/a | Regrid platform | ? | ? | ? | **BLOCKED** — inventory hosted on Regrid (third-party commercial platform; programmatic access governed by Regrid ToS). Recorded, not probed. City-owned semantics anyway (availability, not distress). |
| **Muncie** registry (ord. Dec 2021, annual registration w/ Building Commissioner) | muncie.in.gov/department/division.php?structureid=96 | **403 Forbidden** (bot-block; page is human-browsable) | n/a | no | 0 published | — | structures (by ordinance) | **BLOCKED (soft)** — no evidence any list is published; registry appears administrative-only. APRA request channel (§4.6). |
| **Muncie Land Bank** | muncielandbank.org/inventory-dashboard/ | **403 Forbidden** (bot-block) | n/a | no | ? (est. low hundreds) | ? | mix (acquires "abandoned and blighted property") | **BLOCKED (soft)** — browser-lane candidate |
| **Terre Haute** | terrehaute.in.gov / thredevelopment.com — condemnation via quarterly IC 36-7-9 hearings; ~200 properties identified 2024, 89 demolished | (searched) | n/a | no | 0 published | — | structures | **NOTHING-PUBLISHED** — paper trail is Board minutes + newspaper legal notices. (An AGO item `160729THDC_CONDITIONS_SURVEY` has layers "VACANT STOREFRONT"/"Vacant Building" — **0 records each**, jurisdiction unverified; worthless either way.) |
| **Anderson** | Board of Public Safety demolition awards (news/minutes; ~70-75/yr program) | (searched) | n/a | no | 0 published | — | structures | **NOTHING-PUBLISHED** |
| **Kokomo** | cityofkokomo.org code enforcement / CDBG blight removal | (searched) | n/a | no | 0 published | — | structures | **NOTHING-PUBLISHED** |
| **Lafayette** | (searched; no registry, no data portal surfaced) | — | — | — | 0 | — | — | NOTHING-FOUND |
| **Bloomington** | data.bloomington.in.gov (live Socrata) — discovery API q=vacant/abandoned/unsafe/demolition | 200 | n/a | no | **0 datasets** | — | — | **NOTHING-FOUND** — portal is live but has no V&A/unsafe dataset (uReport CRM has unsafe-building complaint tickets; complaint≠designation, skipped) |
| **Elkhart / Michigan City / Richmond / Marion / New Albany / Hammond / East Chicago** | (searched individually; Hammond publishes rental registration + city-owned land map only) | — | — | — | 0 | — | — | NOTHING-FOUND — no published registry/list in any of them. (Richmond & Marion were BEP demolition participants — program dead, see below.) |
| **Uplands Regional Land Bank** (Crawford, Daviess, Greene, Lawrence, Martin, Orange) | urlandbank.com → `public-sidc.epropertyplus.com/landmgmtpub/app/base/landing` | 200 | n/a | browse w/o login | ? (est. dozens) | ? | **residential + agricultural + COMMERCIAL** VAD properties | **BLOCKED (soft)** — ePropertyPlus Angular SPA, shell-only to a non-browser client; browser-lane candidate; only IN land bank explicitly listing commercial |
| **Renew Land Bank** (statewide TA org, Indianapolis) | renewlandbank.org | 200 | n/a | no | 0 | — | — | NOTHING — technical-assistance org, holds no public inventory. (Indy's own surplus/landbank inventory already held: `in_si_indy_surplus_parcels` 595.) |
| **IHCDA Blight Elimination Program** (statewide, Hardest Hit Fund, 2014–2019, ~3,000 demolitions) | inbep.org (impact report) | **NXDOMAIN** (`getaddrinfo ENOTFOUND www.inbep.org`) | n/a | n/a | 0 reachable | would be 2014-19 (stale) | residential structures only | **DEAD** — program ended, report site gone; property-level list never published as data. Skip. |
| **hub.mph.in.gov** (state CKAN) | (lane C, 2026-08-14: 67 datasets enumerated) | 200 | n/a | no | 0 relevant | — | — | NOTHING-FOUND — zero seller-intent subjects statewide. `data.in.gov` dead (TLS). |
| **DLGF / IndianaMap** | (assessed: parcels + assessment only) | — | — | — | — | — | property-class codes mark vacant LAND, not abandoned structures | NOT-APPLICABLE for this signal |
| **HUD/USPS vacancy** (only true statewide vacancy source) | huduser.gov/portal/datasets/usps.html | 200 (JS shell to non-browser client) | n/a | **registration required** | — | quarterly | address-level NOT public; census-tract aggregates only | **BLOCKED** — gated + aggregate; cannot key to parcels. Recorded, left alone. |

---

## 3. Estimate — total additional Indiana rows obtainable

**Open-web, immediately loadable: ~123 rows** (Evansville Land Bank). That is the entire
uncontested new-row inventory for this signal.

**Browser-lane recoverable (SPA/bot-block, still public/no-login): ~150–600 rows**
(Muncie Land Bank est. 100–400; Uplands est. 30–150) **plus Fort Wayne unknown** — if a
V&A/code layer sits behind acimap.us, city program scale suggests 500–3,000 rows, but its
existence is unconfirmed.

**Derivable from data already held (no acquisition, no scrape): the largest prize.**
`agis_indy_code_enforcement` / `si_d12_indy_marion_code_enforcement` (910,483 rows) contains
CASE_TYPE values **"Unsafe Buildings"** and **"Vacant Board Order"** with case dates
(lane_d/LANE_D_FINDINGS.md). Extracting those subsets yields an Indy unsafe/vacant-structure
signal WITH event dates — likely tens of thousands of case rows — and joining them to the
7,120 registry by PARCEL_I/address retro-fits the registry's missing designation dates.
South Bend's held 20,414 code cases offer the same derivation for St. Joseph County.

**Statewide open sources: zero.** The two-city concentration is a *publishing* gap, not a
search gap: Indiana municipalities run these programs on paper (IC 36-7-9 hearings, Board
minutes, newspaper legal notices), and the state's one blight program (BEP) is dead with no
data legacy. No amount of further endpoint hunting changes this; the remaining channels are
a browser session (3 targets) and public-records requests (registries exist by ordinance and
are disclosable under IC 5-14-3).

## Ranked acquisition order

1. **Derive, don't acquire** — GROUP BY CASE_TYPE on the held Indy 910k D12 corpus; extract
   Unsafe Buildings + Vacant Board Order subsets with dates; join to the 7,120 registry to
   add event dates. Zero requests. Fixes the known date weakness. (BQ work — out of scope
   for this discovery run.)
2. **Evansville Land Bank** — one ArcGIS pull (123 rows, layer 208 above); join StatePIN to
   parcels to split structures from lots. Note availability-semantics, snapshot-named layer
   (re-discover service name on refresh; "July2025" will rotate).
3. **Re-pull cadence on South Bend V&A** (47 rows, live-maintained, dated) — cheap, current,
   the only Indiana dataset with true designation dates.
4. **Browser session, one sitting, three targets**: (a) acimap.us network inspection to
   expose Fort Wayne/Allen's backing ArcGIS server (lane C's identified next step — highest
   variance), (b) muncielandbank.org dashboard, (c) Uplands ePropertyPlus portal (only
   land bank explicitly listing COMMERCIAL). All public, no login; the wall is JS, not auth.
5. **APRA (IC 5-14-3) records requests** for the unpublished-by-ordinance registries:
   Muncie, Evansville, Hammond, Terre Haute condemnation docket. Off-scraper channel;
   land banks are explicitly subject to public-records law (IC 36-7-38-13).
6. **Skip permanently**: Gary (both data hosts dead; Regrid ToS wall; 2014 survey stale
   anyway), IHCDA BEP (dead, residential-only, 2014-19), HUD USPS (gated tract aggregate),
   hub.mph.in.gov (enumerated empty), Bloomington Socrata (live but empty for this signal).

## Commercial/industrial value flags (the hyperscale lens)

- `in_si_indy_abandoned_vacant` (7,120) is titled **"Abandoned and Vacant Houses" — treat as
  100% RESIDENTIAL and mark LOW VALUE** for data-centre siting on its own; its value is as a
  neighborhood-distress density surface, not a target list.
- South Bend V&A/demolition: program is residential-dominant; individual commercial
  structures appear but are not flagged; low direct value, keep for density.
- **No open Indiana source delivers commercial/industrial abandoned structures at scale.**
  The commercial signal for Indiana lives in what is already held: Evansville's 419
  COMMERCIAL wrecking permits, the Indy D12 corpus filtered to commercial parcels (join
  assessor class), tax-sale (81,975 IN rows incl. commercial parcels), and WARN (1,220).
- Only Uplands Regional LB explicitly lists commercial VAD property — small, rural, browser-gated.
- Gary's 554 surveyed vacant businesses (2014) would have been exactly the right thing; both
  hosts are dead. If Gary ever republishes, acquire immediately.
