# LANE E — Indiana natural-gas pipeline CAPACITY (EBB operationally-available postings)

Run: 2026-08-15 (UTC). All tables in `energy-platfrom.indiana_app`, all registered in
`indiana_app._registry` in the same run. Dataset `energy` was touched read-only.

## Step 0 — held-vs-new verdict (measured before scraping)

**Already held (NOT re-acquired):**
- `energy.gas_eia_state_capacity` — 19,311 rows — EIA state-to-state design capacity
  (eia-statetostatecapacity.xlsx). Columns: year, pipeline, state_from/county_from,
  state_to/county_to, capacity_mmcfd. **The task's step-4 EIA target was therefore
  DONE-ALREADY-HELD** (coordinator confirmed mid-run and clipped held tables to IN himself).
- `energy.gas_eia_pipeline_projects` (142), `energy.gas_eia_176` (6,276), `energy.ng_prices_spot`
  (158,637), `energy.ng_production` (149,190), `energy.ng_storage_weekly` (6,896).
- Geometry: `energy.gas_pipelines` (EIA, 32,892), `energy.gas_pipelines_hifld` (33,806),
  `energy.natural_gas_pipelines` (33,806), compressor stations / storage / processing / LNG,
  `indiana_app.in_gas_pipelines` (215 = IN clip).

**Not held anywhere (verified in registry_sources + `__TABLES__` of both datasets): daily
OPERATIONALLY AVAILABLE capacity from pipeline EBBs.** That gap is what this lane filled.

## Interstate pipelines crossing Indiana (measured from `indiana_app.in_gas_pipelines`)

| operator (geometry) | km in IN | EBB platform | outcome |
|---|---|---|---|
| ANR Pipeline Co. | 850 | TC eConnects (SSRS) | **LANDED** 554 rows |
| Texas Gas Transmission Co. | 831 | Boardwalk GasQuest | **LANDED** 23,220 rows |
| Texas Eastern Transmission Co. | 465 | Enbridge infopost | **BLOCKED** (robots) |
| Panhandle Eastern Pipe Line Co. | 437 | ET Messenger ipost | **LANDED** 1,979 rows |
| Crossroads Pipeline Co. | 328 | TC eConnects (SSRS) | **LANDED** 24 rows |
| Trunkline Gas Co. | 309 | ET Messenger ipost | **LANDED** 1,231 rows |
| Rockies Express Pipeline | 249 | Tallgrass ASPX | **BLOCKED** (bot wall) |
| Midwestern Gas Transmission Co. | 185 | DTM Trellis PTMS | **LANDED** 3,367 rows |
| Vector Pipeline Co. | 168 | gasnom.com (vendor EBB) | **LANDED** 4,620 rows |
| Northern Border PL Co. | 49 | TC eConnects (SSRS) | **LANDED** 290 rows |
| Natural Gas PL Co. of Am (NGPL) | 7 | Kinder Morgan DART | **LANDED** 693 rows |
| West Ohio Gas Co. (Intrastate) | 49 | — | no FERC EBB duty (intrastate) |
| Heartland Pipeline Co. (Intrastate) | 42 | — | no FERC EBB duty (intrastate) |

Two pipelines beyond the prompt's likely-list were surfaced by the held geometry and handled:
**Texas Eastern** (blocked, below) and **Northern Border** (landed). NGPL's 7 km sliver landed too.

## Landed tables (all `energy-platfrom.indiana_app.*`, all-STRING verbatim + `_pulled_at` TIMESTAMP)

| table | rows | scope pulled | observed-date columns (data's own) |
|---|---|---|---|
| `in_gas_capacity_anr` | 554 | current posting, all locations | EffGasDay, Cycle, PostingDate |
| `in_gas_capacity_crossroads` | 24 | current posting | EffGasDay, Cycle, PostingDate |
| `in_gas_capacity_northern_border` | 290 | current posting | EffGasDay, Cycle, PostingDate |
| `in_gas_capacity_panhandle_eastern` | 1,979 | 7 gas days (gasDay param honoured) + by-segment | `_requested_gas_day` (CSV itself is location-table; gas day is page state) |
| `in_gas_capacity_trunkline` | 1,231 | 7 gas days + by-segment | `_requested_gas_day` |
| `in_gas_capacity_texas_gas` | 23,220 | last-7-days postings, all cycles (60 posting files) | Effective Gas Day, Effective Time, Post Date/Time (+ `_posting_*`) |
| `in_gas_capacity_midwestern` | 3,367 | last-7-days postings, every cycle (37 posting files) | `_hdr_Eff Gas Day`, `_hdr_CycleDesc`, `_hdr_Posting Date/Time` |
| `in_gas_capacity_vector` | 4,620 | 7 gas-day pages (dt param) | Eff Gas Day/Time, Cycle Desc, Posting Date/Time |
| `in_gas_capacity_ngpl` | 693 | current posting, Delivery + Receipt purposes | `_hdr_Eff Gas Day/Eff Time`, `_hdr_CycleDesc`, `_hdr_Post Date/Post Time` |

Total: **35,978 rows across 9 pipelines.** Design capacity + operating capacity (OPC) +
total scheduled (TSQ) + operationally available (OAC) present in every table (naming varies
per publisher; kept verbatim). Indiana filtering deliberately NOT applied — postings are
system-wide and location-keyed; IN slicing happens downstream.

## Plottability classification (operator's standing priority)

- **County-plottable identity (strongest, no coordinates published):**
  `in_gas_capacity_panhandle_eastern`, `in_gas_capacity_trunkline` — the ET CSVs carry
  **State + County + Operator + Miles** per location (PEPL: 154 IN rows across 11 named IN
  counties; TGC: 49 IN rows across ELKHART/JASPER/ST JOSEPH measured post-load).
- **Joinable-identity (loc id + name + zone/segment, no state/county):**
  `anr`, `crossroads`, `northern_border` (Location id + LocationName),
  `texas_gas` (LineCode + Segment + Loc + Loc Name + Loc Zn),
  `midwestern` (Loc + Loc Prop + Loc Name), `vector` (Location + Location Name),
  `ngpl` (Loc + Loc Name + Loc Zn + Loc (Segment)).
  Join paths: pipeline location masters on the same EBBs (Locations pages exist on every
  platform), or name-match to held geometry/compressor stations. **No geocoding was done and
  none guessed**, per instruction.
- **Directly-plottable:** none — no EBB publishes coordinates in the OA posting itself.

## BLOCKED walls (exact)

1. **Texas Eastern Transmission (Enbridge)** — `https://infopost.enbridge.com/robots.txt` is
   `User-agent: * / Disallow: / / Crawl-delay: 10` — a blanket robots disallow on the entire
   public info-posting host. The alternative host `link.enbridge.com` is a login portal
   (LINK credentials). Recorded BLOCKED-robots; not scraped. (NAESB directory lists
   link.enbridge.com as TE's posting URL; the public postings live on the robots-disallowed
   infopost host.)
2. **Rockies Express (Tallgrass)** — `https://pipeline.tallgrassenergylp.com/` (NAESB-listed
   info-posting host, incl. `Pages/Point.aspx?pipeline=501&type=OA`) serves an
   **Imperva/Incapsula JavaScript bot-challenge stub** (`/_Incapsula_Resource...`) to
   non-browser clients on every path; robots.txt itself 404s. Not bypassed. Recorded
   BLOCKED-bot-wall.

**Pipelines crossing Indiana with NO permitted public capacity surface: Texas Eastern and
Rockies Express** (both publish OA postings but behind the walls above). Every other
interstate pipeline in the held IN geometry now has capacity landed.

## Platform intelligence (for re-scrapes; all verified live 2026-08-15)

- **TC eConnects** (ANR asset 3005 / Crossroads 44 / Northern Border 3029; asset tree at
  `infopost/webmethods/Scenario_ListCapabilitiesTreeView.aspx?SID=67`): SSRS URL-access is
  enabled — append `&rs:Format=CSV` to any `ReportViewer.aspx?/InfoPost/...` report. The
  page's own PDF button does exactly this with Format=PDF. `Historical OAC` by-date-range
  reports exist (`OperationallyAvailableCapacityByDateRange[ANR]`) if a deep lookback is
  ever wanted. Old `ebb.anrpl.com` is dead (expired TLS cert).
- **ET Messenger** (peplmessenger/tgcmessenger.energytransfer.com): native CSV at
  `/ipost/capacity/operationally-available-by-location?asset=PEPL|TGC&f=csv&extension=csv&max=ALL`,
  `&gasDay=MM/DD/YYYY` honoured for lookback. `pipelines.energytransfer.com/ipost/<X>` slugs
  404 (asset-not-found) — the per-pipeline Messenger hosts are the live ones.
- **Boardwalk GasQuest** (Texas Gas tspId=100000, infoPostId=1=Operational Capacity):
  `infopost.bwpipelines.com` now redirects to `gasquest.com`. Anonymous JSON API:
  `POST https://reporting.prod.bwpmlp.org/infopost/infopostdetails`
  `{infoPostId,tspId,pageNumber,pageSize,sortBy:"datetimePostingEffective",sortDescending:true}`
  → `GET .../infopost/postings?postingsDocumentId=<infoPostTrackerID>` (CSV, base64 in
  transit). Also serves Gulf South (tspId=1) etc. if ever needed.
- **DTM Trellis** (MGT tspId=10, rptId=2): needs the public session cookie from
  `GET /ptms/home/infopost/MGT` first; then `getInfoPostRpts.do` (jqGrid JSON; use row `id`,
  e.g. 72259000000, not `infoPostDataId`) → `getInfoPostRptExportCsvFile.do?infoPostDataId=<id>`.
  CSVs are two-block (posting metadata, blank line, location table). MGT moved from
  oneok.com 2025-11-17 (ONEOK→DT Midstream sale); Guardian (GPL) and Viking (VGT) live on the
  same host if ever relevant.
- **gasnom.com** (Vector): plain HTML posting table at
  `/ip/vector/cap_operationally_available.cfm`, `?dt=<Month D, YYYY>` for prior gas days;
  no robots.txt (404); vector-pipeline.com iframes this vendor and its robots allow all.
- **KM DART** (NGPL): the OA grid is client-rendered; the **page's own EXCEL download button**
  is a WebForms postback (DownloadDDL=EXCEL + btnDownload.x/y + hdnIsDownload=true + radio
  `ctl00$WebSplitter1$tmpl1$ContentPlaceHolder1$location` = rbDelivery|rbReceipt). robots.txt
  disallows only specific /Documents/* files — capacity pages are permitted.

## Compliance notes

- UA `DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)` on every request;
  >=1.1 s per host enforced by a shared limiter; no logins, no accounts, no terms dialogues,
  no CAPTCHA/bot-wall bypasses. robots.txt checked per host before pulling.
- Everything replicated is something the public page itself does for anonymous visitors
  (SSRS export URLs, native CSV links, the page's own download buttons, anonymous JSON APIs).
- Observed dates are the postings' own gas-day/cycle/posting-time fields, kept verbatim;
  `_pulled_at` is separate.

## Scripts (this directory)

- `step0_inventory.py`, `step0b_operators.py` — registry/warehouse verification (read-only).
- `probe.py`, `probe2.py`, `probe3.py`, `probe_gq_js.py`, `probe_km_export.py` — endpoint
  discovery probes (responses in scratchpad `probes/`).
- `pull_ebb_capacity.py` — production fetcher (per-platform fetchers; JSONL to scratchpad).
- `load_to_bq.py` — loads JSONL → `indiana_app.in_gas_capacity_<slug>` (WRITE_TRUNCATE) and
  registers in `_registry` in the same run.
- RE-SCRAPE (full): `python pull_ebb_capacity.py && python load_to_bq.py`

## Registry corrections in this run

- `in_gas_capacity_midwestern`: first load (3,441 rows) had the two-block Trellis CSV parsed
  as one table; reloaded same-run as 3,367 clean location rows. The later registry row
  supersedes; table content is the corrected parse (WRITE_TRUNCATE).
