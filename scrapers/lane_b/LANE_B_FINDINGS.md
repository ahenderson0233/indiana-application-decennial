# LANE B FINDINGS — Indiana community-sentiment & regulatory pulls
Run date: 2026-08-14 (UTC). All writes to `energy-platfrom.indiana_app`; `energy` dataset touched read-only.
Every table load/append/correction registered in `energy-platfrom.indiana_app._registry` in the same run.
Rate limit ≥1.1s/host (GDELT 5.5s), research User-Agent per brief; robots.txt checked before every host.

## Operator amendments honored
1. **Grid upgrade plans** task inserted after IURC dockets → `in_grid_plans` (TDSIC + IRP; RTO MTEP/RTEP
   explicitly excluded — the transmission agent already holds `in_pjm_rtep_upgrades` 15,443 rows and
   `in_rto_expansion` 2,034 rows per `_registry`).
2. **I&M-first ordering** used as a tiebreaker only; statewide (92-county) scope kept.
3. Plottability rule: no geocoding anywhere; `location_status` ∈ directly-plottable / joinable / neither.

## I&M (Indiana Michigan Power / AEP) county list — recorded per operator instruction
Source: `energy-platfrom.energy.eia861_service_territory` (`utility_id_eia = 9324` — table has no
utility_name column; 9324 verified by county footprint). 40 IN counties after name-variant dedupe
(DeKalb/Dekalb/DeKalb County etc.), latest report_date 2024-01-01:
Adams, Allen, Blackford, DeKalb, Dearborn, Delaware, Elkhart, Fayette, Grant, Hamilton, Henry, Howard,
Huntington, Jay, Jefferson, Knox, LaGrange, LaPorte, Madison, Marion, Marshall, Miami, Montgomery, Noble,
Parke, Randolph, Ripley, Spencer, St. Joseph, Starke, Steuben, Sullivan, Tippecanoe, Tipton, Vermillion,
Wabash, Warrick, Wayne, Wells, Whitley.
(EIA-861 self-reported territory is broad; several SE-Indiana counties look over-inclusive but the list is
recorded verbatim from the specified source. Full list + per-county latest dates: `_scratch/im_counties_final.json`.)

## Tables built (BigQuery `energy-platfrom.indiana_app`)
| table | rows | what it is |
|---|---|---|
| `in_iurc_dockets` | 516 | IURC docketed cases from targeted sweeps: petition types LLC Project / Economic Development / TDSIC / TAR / EGR / SDC / Certificate of Need + Contract (electric industries), big-5 electric utilities × Rates/Rates&Financing/Tariff Matters (kept 2022+), and data-center party-name sweeps. Observed date = `iurc_petitiondate` (filing). `matched_terms` records sweep provenance; `relevance` tags (dc_party, large_load_type, grid_plan_tdsic, economic_development, special_contract, cpcn, big5_rate_case). |
| `in_grid_plans` | 618 | Grid upgrade plans. 391 `row_type='project'` rows parsed from public TDSIC plan documents (NIPSCO 2015 plan exhibit 321; AES/IPL 2019 TDSIC plan 63; IPL WP-6 xlsx 7); 227 `row_type='document'` rows = every plan-relevant public filing in the latest ≤3 electric TDSIC base dockets per utility **plus** utility IRP volumes from the IURC IRP page, each with URL, filed date (observed), and `extraction_status` (extracted / EXTRACTION-DEFERRED reason). |
| `in_ordinances_dc` | 4 | Exact-phrase "data center(s)" hits across all 45 Indiana Municode clients (public api.municode.com JSON API): Franklin (Johnson Co., zoning definitions), Michigan City (LaPorte Co.), St. Joseph County ×2 (land-use standards + definitions — county-level DC zoning language). Snippet-cited adoption dates parsed where shown (none shown → NULL). |
| `in_news_dc` | 283 | Unique-link news rows: 114 Bing News RSS queries (4 generic + every one of the 92 counties + 18 city terms incl. New Carlisle / Lebanon / Fort Wayne). Observed date = feed pubDate. `query_county` carries attribution; de-duped on link. |
| `in_dc_actions` | 79 | Indiana DC actions: 1 parsed Data Center Watch /report entry (Chesterton) + 78 headline-derived actions (moratorium/ban/reject/deny/withdraw/pause/opposition verbs + jurisdiction in title), county-mapped via Census 2020 place↔county. `already_held` flags overlap with `energy.dc_opposition_tracker` (50 IN rows, last_updated 2026-04-21); fresh value is the post-April-2026 items. Headline rows carry publication date with explicit `date_note` (enactment date may differ). |

`_registry` received 10 rows this run: 5 build rows + 3 `in_grid_plans` append/correction rows + 2
correction-note rows (news provider outcome; dcwatch quarterly wall).

## BLOCKED / walls (exact, measured this run — recorded, not worked around)
1. **Google News RSS** (`news.google.com/rss/search`): robots.txt `User-agent: *` → `Disallow: /` with an
   Allow list that does NOT include `/rss` → disallowed. (Also explicitly disallows anthropic-ai/ClaudeBot.)
   Task brief assumed RSS was permitted; the measured file says otherwise. Replaced with permitted providers.
2. **American Legal** (`codelibrary.amlegal.com`): robots allows `*`, but every request (HTML *and* the
   registry's proven REST endpoint `/api/search/`) returns **HTTP 403 Cloudflare JS challenge ("Just a
   moment…")**. Bot-challenge = hard wall (no challenge-solving permitted). NOTE: the July loader
   (`ingest.load_amlegal_ordinances_bq`, registry `BUILT+LOADED` 2026-07-31) built 183 IN rows — the
   challenge is new or network-dependent. Held IN rows are loose `data OR center` mentions (flood data,
   personnel data), NOT phrase hits, so a phrase re-run remains valuable when the wall lifts.
3. **GDELT DOC 2.0 API**: robots-allowed, but **HTTP 429 on every call even at 5.5s spacing** (server text
   demands 1/5s). 0 rows this run; likely shared-IP throttling. Retry later or from another egress.
4. **Data Center Watch quarterly pages** (`/q22025`, `/q3-q4-2025`, `/q1-2026`): content renders
   client-side from `/api/*` which robots.txt **disallows**; served HTML contains zero "Indiana" strings.
   Original `/report` IS server-rendered and was parsed (its 2nd IN entry, Burns Harbor, uses a split-line
   format my parser missed — already held in `dc_opposition_tracker`, so not re-added).
5. **in.gov site search** (`/search`) robots-disallowed — not needed (direct page URLs used).

## Registry refutation (positive finding)
`energy.registry_sources` row "Indiana URC (EDS) — BLOCKED (SPA), MS Power Pages" is **refuted**:
the public advanced-search page ships a plain **anonymous companion REST API**
`https://zus1iurcprodd365companionappmaster-appservice.azurewebsites.net`
— `POST /api/search/advanced` (form-shaped JSON: txtCause/ddlPetitionType(GUID)/ddlIndustry(GUID)/
ddlUtilities(GUID)/ddlCaseStatus/txtParties/txtFilingDateBegin/End, txtPageNumber; PageSize fixed 10),
`GET /api/list/{industrytypes|petitiontypes|statustypes|utilitytypes}`,
`POST /api/document/{filings|orders|exhibits|appeals}` + `/api/list/{parties|services|officers|hearings}`
with `{txtPageNumber, Id:" <case-guid>"}`. Document links: `iurc.portal.in.gov/_entity/sharepointdocumentlocation/...`
(anonymous download). Case page: `iurc.portal.in.gov/docketed-case-details/?id={guid}`. Its robots.txt
returns 403 → RFC 9309 §2.3.1.3 treats 4xx as no-restrictions; the host is the page's own XHR backend.
GUID lists saved in `_scratch/iurc_list_*.json`. **Limitation:** the search API exposes NO case title/free
text — relevance must come from petition_type + parties (recorded in registry notes).

## Notable substance (for the siting narrative)
- **Cause 46097** (I&M, Tariff Matters, filed 2024-07-19, Decided): large-load tariff settlement with
  Amazon Data Services, Microsoft, Google, Data Center Coalition as parties (matches held dc_docket_tracker).
- **Cause 46301** (EGR, filed 2025-09-26, Decided): I&M economic-growth rider with Amazon Data Services AND
  Steel Dynamics as parties — the follow-on rate mechanism to 46097.
- **Cause 46394** (LLC Project, AES Indiana, filed 2026-04-22, **Pending**): first case under the brand-new
  "LLC Project" (large-load customer) petition type; CAC intervened.
- **TDSIC cadence 2026**: current electric plan dockets all active — CenterPoint 45894 (latest filing
  2026-08-03), AES/IPL 45264 (2026-06-11), NIPSCO 45557 (2026-06-09, one order **Appealed** 2025-12-09),
  Duke 45647 (2026-05-14). **I&M has no electric TDSIC since its 2014 filings (44542/44543)** — its Indiana
  grid-plan visibility therefore lives in PJM processes (out of scope here) and its IRP (deferred docs listed).
- Municode phrase hits show **St. Joseph County already has "data center" land-use standards in its code**
  (§154.319/§154.321) — the only county-level codified DC zoning among Indiana's 45 Municode clients.

## County receipts (of Indiana's 92)
- **Strict receipts — county (or a city in it) named in the item itself, or a county-attributed
  ordinance/action/grid-project row: 55/92**:
  Adams, Allen, Boone, Brown, Carroll, Cass, Clark, Clay, Daviess, DeKalb, Delaware, Elkhart, Fayette,
  Franklin, Fulton, Gibson, Grant, Hamilton, Hancock, Harrison, Hendricks, Henry, Huntington, Jackson,
  Jefferson, Johnson, Knox, LaPorte, Lake, Madison, Marion, Marshall, Martin, Miami, Monroe, Montgomery,
  Morgan, Parke, Pike, Porter, Posey, Pulaski, Putnam, Randolph, Rush, St. Joseph, Steuben, Sullivan,
  Union, Vanderburgh, Vermillion, Warren, Warrick, Washington, White.
- **Weak (query-attributed only — a Bing county query returned items, but the county isn't named in the
  title): the remaining 37**: Bartholomew, Benton, Blackford, Clinton, Crawford, Dearborn, Decatur, Dubois,
  Floyd, Fountain, Greene, Howard, Jasper, Jay, Jennings, Kosciusko, LaGrange, Lawrence, Newton, Noble,
  Ohio, Orange, Owen, Perry, Ripley, Scott, Shelby, Spencer, Starke, Switzerland, Tippecanoe, Tipton, Vigo,
  Wabash, Wayne, Wells, Whitley.
  (All 92 have at least weak coverage. Note Howard/Starke/Kosciusko DO have known actions in the HELD
  `dc_opposition_tracker` — strict counts only this run's new tables.)
Details: `_scratch/county_coverage.json`, `_scratch/county_coverage_strict.json`.

## Caveats & honest limits
- `in_iurc_dockets.matched_terms` keeps raw sweep provenance; IURC party search substring-matches
  (e.g. "Vantage" sweep returned 1990s "Advantage…" telecom cases). `relevance='dc_party'` was
  re-labelled with word boundaries after load (registry-noted); matched_terms intentionally unchanged.
- Grid project rows skew to the 2015/2019 plan vintages that parsed cleanly; the 2021-2026 cycle plan
  documents are cataloged (URLs + filed dates) with `extraction_status='EXTRACTION-DEFERRED …'` —
  Duke's "Public Appendix A" (45647) is a Copperleaf methodology deck, not the project list; the real
  current-cycle project tables live in exhibits my table-detector didn't match this run.
- Grid `location_status`: 377 project rows 'neither', 14 'joinable' (named substations/counties), 0
  'directly-plottable' — utilities do not publish coordinates in these filings; per the plottability rule
  nothing was geocoded or guessed.
- Ordinance coverage is honest-but-thin (4 rows): most Indiana codes live on AmLegal (walled today), and
  the 2025-26 county DC ordinances/moratoria (Marshall, White, Miami, Putnam…) are mostly NOT yet codified
  online — they surface in `in_dc_actions`/held tracker instead.
- Headline-action rows: `action_date` = publication date (flagged per-row in `date_note`).
- `in_news_dc` includes items Bing returned for county queries whose titles don't name the county —
  filter with `query_county` vs title-mention depending on use.

## Next-run pointers
- Retry AmLegal (`/api/search/`, phrase queries) from a different egress; if it opens, extend
  `in_ordinances_dc` (the held 183-row table's method is registered under `ingest.load_amlegal_ordinances_bq`).
- Retry GDELT at >5.5s spacing or via BigQuery public `gdelt-bq` (mind scan costs).
- Current-cycle TDSIC appendices: pull per-docket "Petitioner's Exhibit" attachments (not only
  appendix/plan-named files) and OCR-free parse; the filings metadata needed to target them is already in
  `in_grid_plans` document rows.
- IRP appendix extraction (26 IRP volumes cataloged, EXTRACTION-DEFERRED).
- Add Burns Harbor split-format row from DCW /report if wanted (currently only in held tracker).

## Scripts (this directory)
`bq_util.py` (shared: BQ loads/registry, robots RFC-9309, 1.1s/host politeness) ·
`00*_registry*` (registry-first) · `01*_robots/im_counties` · `02_probes` · `03/07*_iurc probes` ·
`04_iurc_dockets` · `05*_municode probes` · `06_municode_ordinances` · `08*_grid plans (4 passes)` ·
`09_news` · `10_dcwatch_probe` · `11_dc_actions` · `12*_coverage` · `13*_sanity+fix` ·
`14_registry_corrections`. Raw evidence in `_scratch/` (API captures, robots report, PDFs/XLSX, row dumps).
