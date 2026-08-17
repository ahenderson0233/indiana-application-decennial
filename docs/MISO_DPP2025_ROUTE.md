# MISO DPP-2025-Cycle — public route audit

**Measured 2026-08-17** by `scripts/pull_miso_dpp2025.py`. Goal: a working PUBLIC route to MISO's
DPP-2025-Cycle POI analysis / transfer study, and a re-runnable loader for it.

**Bottom line up front.** The DPP-2025 case is published through the CartoVista FERC Order 2023
POI heatmap at `cloud.cartovista.com/miso`. Its **discovery and metadata routes are fully public
(200)**, and two small reference tables are readable, but the **three headline tables that carry
the bus-headroom data — POIs (19,223), the transfer study TSA (691,523) and the DPP-2025 GI queue
(3,253) — are HTTP 403 `ProtectedData`**, confirmed three independent ways. The one grid raster is
public metadata but serves only a **colorized thumbnail**, never numeric MW, and its own label is
"Peak - 2022". A parallel hunt for a **MISO-authored** route (giqueue DPP-2025, cdn.misoenergy.org,
the SPA content API, OASIS) is recorded in its own section below.

---

## 1. The two maps and everything on them (all metadata public, HTTP 200)

`GET https://ferc.cartovista.com/api/settings/miso/ferc` → **200**. Study
`83dffd45-9b06-4f67-8ff3-a53e466f79cd`, `studyTitle "DPP2025"`, `isPoiMapPublic: true`,
`isCurrentQueueMapPublic: true`, `maxInjection 5000`. It names two maps:

| map | id | `…/api/v2/maps/{id}/details` | dataTables | gridLayers |
|---|---|---|---|---|
| POI analysis | `59878415-54b3-4502-9429-bfd90c7ce3c5` | **200** | 6 | 1 |
| current queue | `6bf71952-3862-421b-a156-ed3d0a3ca98b` | **200** | 3 (subset) | 0 |

The current-queue map adds nothing new: its 3 tables (Counties, FootPrint, GIQueue) are a subset
of the POI map's 6. The `details` response exposes seven top-level keys —
`map, layers, dataTables, gridLayers, wmtsLayers, wmsLayers, permissions` — `wmtsLayers`,
`wmsLayers` and `permissions` are all empty.

**All layers enumerated (operator's "all layers" ask):** the POI map has **5 vector layers**
— FootPrint, Counties, POIs, GIQueue, Injection-mask — each `dataTableUniqueIdentifier` points at
one of the six dataTables in §2, plus the **1 gridLayer** in §3. So every layer is 1:1 with a
table already in the matrix; there is no layer with a data source outside it, and no WMTS/WMS
external-service layer. Nothing on either map is left unprobed.

### ⚠ The deployment's internal vintage labels disagree — do not trust one blindly

| where | label |
|---|---|
| settings `studyTitle` + publisher disclaimer | **DPP2025** / "currently using the models and inputs from the DPP-2025-Cycle" |
| `map.title` | "DPP **2023** - POI Analysis Map [Production]" |
| `map.vanityUrl` | "59878/DPP-**2023**-POI-Analysis-Map-Production" |
| `gridLayer.name` | "DPP**2022** - Capacity heatmap" |
| `gridSource.name` | "Peak - **2022**" |

The authoritative vintage for the POI/TSA **tabular** study is the publisher's DPP-2025 disclosure.
The **grid raster** carries its own 2022 label and must not be relabelled DPP-2025 (see §3).

---

## 2. Table × route × HTTP-status matrix (the core deliverable)

Row-level data comes from `POST cloud.cartovista.com/miso/api/v2/DataTable/{systemIdentifier}/DataRows`
with body `{"startRow":N,"rowCount":M}`. `DataColumns` is a sibling GET. Measured 2026-08-17:

| table (uniqueIdentifier) | systemIdentifier | declared rows | DataColumns | **DataRows** | verdict |
|---|---|---:|:---:|:---:|---|
| MISO_POIs_2025-11-11 | `da6949ad-…33da0` | 19,223 | 200 | **403** | BLOCKED ProtectedData |
| MISO_TSA_2025-11-11 | `d48a4a1b-…cb61aa` | 691,523 | 200 | **403** | BLOCKED ProtectedData |
| MISO_GIQueue-2025-11-11 | `8b40a6a0-…c8873f` | 3,253 | 200 | **403** | BLOCKED ProtectedData |
| MISO Counties [Production] | `98af4e3b-…20dbb8` | 1,003 | 200 | **200** | **OPEN** → loaded |
| MISO FootPrint [Production] | `421ee8c5-…8fed17` | 1 | 200 | **200** | **OPEN** → loaded |
| DPP2022 - Injection area mask | `ffcefe7e-…d8cf77` | 0 | 200 | **200** | OPEN, serves `[]` |

**The 403 wall, quoted verbatim** (identical body on all three protected tables):

```
{"code":"Forbidden","codeDetails":"ProtectedData","additionalInformation":[],
 "Message":"code: Forbidden; codeDetails: ProtectedData","Data":{},
 "InnerException":null,"HelpLink":null,"Source":"CartoVista.Server.Portal.Core",
 "HResult":-2146233088}
```

### Why the 403 is a real wall, not a missing parameter or missing session

The three protected tables were probed **three independent ways, all 403**:

1. **Raw unauthenticated POST** — prior session (2026-08-02/03) and again today.
2. **This script's probe** (`--matrix`).
3. **`fetch()` executed inside the LIVE VIEWER's own page** at
   `cloud.cartovista.com/miso/ferc/poi-analysis-map`, so it carried the anonymous session cookies
   **and** the correct same-origin referer. POIs, TSA and GIQueue each returned the identical
   403 `ProtectedData`. → A logged-in-looking session does **not** unlock them; the protection is
   server-side on the table itself.

The viewer renders these tables only through `POST DataServices/dataQueryExecute`, which **returns
200 in-session but its body is AES-encrypted** (`{"data":"<base64>"}`). The blob does **not** carry
the OpenSSL `Salted__` header, so it is **not** the giqueue scheme — it is a different cloud-side
CartoVista key. Recovering it is a separate reverse-engineering task (the viewer JS bundle
`cartovista.viewer.*.js` under `cloud.cartovista.com/assets/scripts/`), **not attempted here**.
Note the operator's earlier finding that `dataQueryExecute` is **403 for these tables when called
raw/unauthenticated with the join contract** — so even that route needs both the session and the
crypto. Recorded as a lead, not a route.

### DataColumns — full schemas captured (all 200, all six tables)

| table | columns |
|---|---|
| MISO_POIs | BUS_ID, BUS_NAME, KV, KV_CLASS, LATITUDE, LONGITUDE, AREA CODE, AREA NAME, ENGLISH_NAME |
| MISO_TSA | SCENARIO, YEAR, CONSTRAINT, FCITC, DFAX, RATING, BUS_ID, CONTINGENC, INI_LOAD, PER_LOADED |
| MISO_GIQueue | Project Number, Fuel Type, POI Name, Latitude, Longitude, County, State, Transmission Owner, In Service, In Service Year, Study Cycle, Study Group, Study Phase, Service Type, Summer Net Mw, Winter Net Mw, Application Status |
| MISO Counties | GEOID, State, State Name, County Name, County Name LSAD |
| MISO FootPrint | UID, Lmp_value, NAME, SHORTNAME, ISO |
| Injection area mask | ANALYSIS, BUS_ID, VALUE, KV |

The schemas confirm what is behind the wall: MISO_TSA is the transfer/constraint study
(FCITC / DFAX / RATING / % loaded per constraint × contingency × bus), i.e. exactly the headroom
driver, and MISO_GIQueue is the DPP-2025-cycle interconnection queue with Study Cycle/Group/Phase.

---

## 3. The grid raster (capacity heatmap) — public metadata, colorized image only

The POI map carries **one** gridLayer. Its metadata is fully public:

- `GET …/api/v2/GridLayer/3ed5bf8e-b0a3-4276-aaff-8ba79c47c181/details` → **200**
- `GET …/api/v2/GridLayer/3ed5bf8e-…/GridSources` → **200** — one source
  `4cf9cd31-62ea-4042-87fb-1a8d27f0e966`, **name "Peak - 2022"**, band 1, `units MW`,
  `noDataValue -999999999999999`, **minValue −77268.23, maxValue 3700.10**, `AREA_OR_POINT=Area`.
- `GET …/WebportalServices/Thumbnail.aspx?gridLayerId=3ed5bf8e-…` → **200, 107 KB image/png** —
  but **colorized** (the style gradient, not numbers).

**Every raw-value route 404s** (`CartoVista Server - Page Not Found`), tested 2026-08-17:
`/geotiff`, `/GeoTiff`, `/tiff`, `/download`, `/data`, `/source`, `/GridSource`, `/DataColumns`,
`/GridSource/{gsid}`, `GridSource/{gsid}` at top level, `/mvt/{x}/{y}/{z}.pbf`, `/tile|/image|
/raster/{z}/{x}/{y}.png`, and `WebportalServices/{GridData,GridLayer,GridLayerImage,Download,
Export,GetGrid}.aspx`. The client config XML
(`WebPortalServices/CartoVistaConfigFileGenerator.aspx?type=Dynamic&mapId=…`, itself **200**)
shows the `<GridLayer … renderingMode="color">` with an **empty `<GridSource><Src>`** — i.e. the
browser only ever receives colorized tiles, never the numeric grid.

**Verdict:** the numeric MW surface is **not retrievable** on this deployment, and the layer's own
name is "Peak - 2022", so it is **not confirmed DPP-2025**. We already hold the raw DPP-2021 MW
surface (`energy.miso_poi_capacity_surface_geotiff`, 3,390,912 px, from the giqueue self-hosted
`poi/api/gridLayer/mainGeoTiff`). Nothing is loaded from the cloud grid.

---

## 4. What was loaded (the OPEN cells), and how to re-run

`python scripts/pull_miso_dpp2025.py --load` landed the two reachable tables into
`energy-platfrom.indiana_app`, each with a `_registry` row in the same run:

| table | rows | note |
|---|---:|---|
| `in_miso_dpp2025_counties` | **1,000** of 1,003 | DataRows caps at 1,000 (startRow ignored — same cap prior sessions found on NYISO/TVA). All **92 Indiana counties** are within the 1,000 served. County identity reference (GEOID + names), **NOT** bus headroom. |
| `in_miso_dpp2025_footprint` | **1** | SERVED-COMPLETE. The single MISO outline row. |

These are boundary/reference layers of the DPP-2025 POI map, catalogued to complete the "all
tables" sweep — they are explicitly not headroom. Every provenance column
(`_source_datarows_url`, `_source_datatable_guid`, `_cartovista_map`, `_column_name_map`,
`_study_vintage_disclosed`, `_pulled_at`) is on each row so a stranger can refresh from the row
alone.

### Commands

```
python scripts/pull_miso_dpp2025.py --matrix          # probe every route, print the matrix, NO writes
python scripts/pull_miso_dpp2025.py --load            # load the OPEN tables + registry rows (~1,001 rows)
python scripts/pull_miso_dpp2025.py --load --smoke    # same, capped at 25 rows/table
python scripts/pull_miso_dpp2025.py --load --dry-run  # parse + show, do not touch BigQuery
```

Boundaries honoured: read-only GET / query-POST, identifying User-Agent, ≥1.15 s per host, no
accounts, no keys, no UA spoofing. A DataRows POST is a query; nothing on the server is mutated.

---

## 5. MISO-authored routes (CartoVista is the renderer, not the author)

**The `giqueue.misoenergy.org` avenue — the self-hosted DPP-2021 viewer, mined for a 2025 sibling —
is RESOLVED in §6 below: BLOCKED, and structurally so.**

**Measured 2026-08-17 (documents-and-filings sweep)** by `scripts/pull_miso_dpp2025_study.py`.
This section is the MISO-authored answer for documents, filings and dashboards. Short version:
**a public MISO route EXISTS and is loaded — the DPP-2025-Cycle Phase 1 study report — but MISO
designates the constraint-level appendices CEII.** On the heatmap itself, the FERC compliance
docket (§5.8) shows the tariff obliges MISO to serve the per-POI **metrics table publicly,
"without a password or a fee"** — but only as an interactive query response, **not as bulk
export**, which is exactly the shape of the 403 wall measured in §2. Every sub-avenue below
ends in either a load or a verbatim wall.

### 5.1 ⭐ THE OPEN ROUTE — MISO's document index + the DPP-2025 Phase 1 PUBLIC report

MISO's website document index is an **open Elasticsearch endpoint** (no cookies, no CSRF —
verified with plain anonymous `curl`, HTTP 200):

```
POST https://www.misoenergy.org/api/find/Optics_Models_Find_RemoteHostedContentItem/_search
Content-Type: application/json
{"query":{"query_string":{"query":"DPP AND 2025"}},"size":300}
```

Hits carry `ObjectId$$number` (the cdn filename suffix), `FileName$$string`, `ContentType`,
and publisher metadata: `Properties.studycycle`, `studygroup`, `processstage`, `studystatus`,
and the full `ProjectNumber` (J-number) list each document covers. **cdn URL construction rule**
(measured): `https://cdn.misoenergy.org/{FileName stem}{ObjectId}.{ext}` — the FileName-based
form returns 200; the `Name`-with-spaces form returns CloudFront 403.

The index holds ~140 GI documents (every DPP cycle 2016→2025). For DPP-2025 exactly **one** SIS
artifact exists (2026-08-17):

```
GET https://cdn.misoenergy.org/GI-DPP-2025-ALL_SIS_Ph1_FINAL_v1.0_PUBLIC_20260324748615.zip
→ HTTP 200, application/zip, 284,571 bytes, Last-Modified: Wed, 01 Apr 2026 21:18:55 GMT
```

| zip member | size | what it is |
|---|---:|---|
| `GI DPP 2025 Cycle 1 SIS Phase 1 Final Report.pdf` | 290,503 | 7-page summary report, "March 24th, 2026", v1.0 |
| `Appendix I - Executive Project and Upgrade Cost Summary/Executive Cost Summary.xlsx` | 28,879 | **202 rows: J-number, Fuel Type, ERIS MW, NRIS MW, Service Type, Total DPP-2025 Phase 1 Network Upgrade Cost ($)** |

**Vintage proof (the verification that matters):** the publisher's own index tag is
`Properties.studycycle = "2025 Cycle"`; the report title is *MISO DPP 2025 Phase 1 Final
Report*, revision history "Version 1.0 Initial Posting 03/24/2026"; the report's Executive
Summary states Phase 1 analyzed **351 interconnection requests, 58,730.20 MW ERIS /
56,458.40 MW NRIS**. Under the new consolidated process there are no per-region reports —
one "ALL" report per phase (same for DPP-2023: `GI-DPP-2023-ALL_Ph1_SIS-Report_…_PUBLIC_20251203730460.zip`).

**Loaded (with `_registry` in the same run):** `indiana_app.in_miso_dpp2025_ph1_project_costs`
— 202 rows, 202 distinct J-numbers, $29.52 B total Phase-1 network-upgrade cost, 195 NRIS /
7 ERIS-only. This is the **project × upgrade-cost dimension** (which we previously lacked
entirely), **not** bus/constraint headroom.

### 5.2 ⛔ The constraint-level tables are CEII — the wall, in MISO's own words

The Phase 1 report's appendix list marks **every results appendix (CEII)**; only Appendix I is
public. The report sentence that names the wall:

> "The full list of constraints identified in the ERIS and NRIS analysis are detailed in
> **Appendix C (CEII) – ERIS Results** and **Appendix D (CEII) – NRIS (Deliverability)
> Results**."

Appendices: A (CEII) Cost Allocation & Milestone Payments, B (CEII) Network Upgrade Summary,
C (CEII) ERIS Results, D (CEII) NRIS Results, E (CEII) Local Planning Criteria Results,
F (CEII) Study Assumptions, G (CEII) JTIQ Expanded Scope Results, H (CEII) Shared Network
Upgrade Results, **I (public) Executive Cost Summary**. MISO's NDA instructions
(cdn `Non Disclosure Agreement Types and Instructions68054.pdf`) define the gate:

> "CEII NDA is required for disclosure of CEII. … Examples of CEII Required Access are:
> • MTEP and PROMOD ShareFile Access • Power Flow Models • MISO Extranet and Closed
> Committees …"

Cross-check on the sibling cycle: the DPP-2023 ALL Ph1 PUBLIC zip (282,023 bytes) contains
**only** the summary PDF — no appendix at all. So DPP-2025's public zip is the *more* generous
of the two. CEII acquisition was **not attempted** (rule). BLOCKED for FCITC/DFAX/constraint
rows via study reports.

### 5.3 Schedule — what exists now vs later (so a re-runner is not surprised)

Per the **July 2026 IPWG DPP Study Schedule** (cdn `20260721 IPWG Item 03b DPP Study
Schedule769072.pdf`, "Current DPP Schedule version: 7/1/2026"): DPP-2025-Cycle DPP started
1/5/2026, **DPP-1 completed 4/14/2026**, **DPP-2 completion moved to 4/28/2027** (the January
deck had said 7/13/2026 — a ~9.5-month slip), DPP-3 7/8/2027, GIA stage 11/20/2027. **The Phase 1
report is therefore the only DPP-2025 SIS artifact until ~April 2027.**
`--discover` re-lists the index at any time.

### 5.4 Stakeholder committee decks — heatmap policy found; no data attachments

MISO's Order 2023 workshop deck (cdn `20240221 Order 2023 Workshop Presentation631823.pdf`,
38 pp) states MISO's compliance posture verbatim:

> "**Heatmap:** Order requires Transmission Providers to maintain a **visual representation**
> of available transmission capacity • MISO already utilizes a heat map*" … "Assessment:
> 1. Accept the pro-forma (update MISO process) a. Already compliant, add language pointing
> to BPM for implementation details"

i.e. MISO reads the obligation as the **picture, not the table** — consistent with the
CartoVista 403s in §2. Index sweeps for data attachments came back empty: `CartoVista` 0 hits,
`heatmap`/`Heat` 0, `POI AND analysis` 0, and every constraint-named public file
(`constraint OR constraints OR FCITC OR DFAX`, 57 hits) is market-side (TCDC demand curves,
top-10 congestion, NCA constraint lists) — none is a GI/DPP results table.

### 5.5 OASIS — probed, wrong product class

MISO's OASIS is OATI-hosted. `https://www.oasis.oati.com/MISO/index.html` (200) is a frameset
to `webSmartOASIS/HomePage?ProviderName=MISO`; the document tree
`https://www.oasis.oati.com/woa/docs/MISO/MISOdocs/` answers **200 with 0 bytes** (no listing).
Known files there are transmission-service docs (e.g. `TP-OP-005 Available Transfer Capability
Implementation Document`). OASIS is the ATC/TSR channel; MISO's GI study artifacts live on
misoenergy.org (proven in §5.1). Verdict: **not the publication channel** for POI/TSA data —
closed, nothing further to mine here.

### 5.6 Power BI — probed, queue-only

The GI Queue page embeds four public `app.powerbigov.us/view?r=…` dashboards: **Active Queue
Overview**, **Queue Cap Tracker**, **C.O.D. dashboard**, **JTIQ Dashboard**. Content verified on
Queue Cap Tracker: DPP-2026 cycle **application-cap tracking** (regional GW caps — West 18.1,
Central 28.2, South 23.1, East(ATC) 8.7, East(ITC) 11.4 "Cap Hit"; submissions by fuel; "Data is
current as of 8/7/2026"). Queue/cap material only — **no constraint, POI, or capacity-surface
data on any of the four**. Verdict: closed, nothing to load that we do not already hold in
`in_queue_miso`.

### 5.7 MTEP-25 powerflow models — BLOCKED (CEII NDA), not attempted

The gate is the CEII NDA quoted in §5.2 ("Power Flow Models" are on its example list), plus
MISO website login + FTP/ShareFile access. Recorded and stopped per rule.

### 5.8 FERC eLibrary — docket ER24-2046: what the tariff actually obliges (and does not)

Full public-docket sweep (eLibrary API, read-only). Proceeding map: MISO compliance filing
**2024-05-16** (accession 20240516-5164, heatmap at transmittal pp. 22–24) → FERC order on
compliance **191 FERC ¶ 61,229** (2025-06-26, 20250626-3050, "Public Interconnection
Information" at P 26) → MISO second compliance filing **2025-08-25** (20250825-5178, pp. 14–15)
→ FERC order **194 FERC ¶ 61,203** (2026-03-19, 20260319-3037, PP 12–13) accepting the heatmap
language, closing the issue. No protest in the docket engaged the heatmap.

**The operative tariff text — MISO GIP (Attachment X) Section 6.1.1**, as accepted 2026-03-19,
verbatim (excerpted):

> "6.1.1 Publicly Posted Interconnection Information. Transmission Provider shall maintain and
> make publicly available: (1) an interactive visual representation of the estimated incremental
> injection capacity (in megawatts) available at each point of interconnection … under N-1
> conditions, and (2) **a table of metrics** concerning the estimated impact of a potential
> Generating Facility … based on a user-specified addition of a particular number of megawatts
> at a particular voltage level at a particular point of interconnection. At a minimum, for each
> transmission facility impacted …: (1) the **distribution factor**; (2) the **megawatt impact**;
> (3) the **percentage impact** on each impacted transmission facility (based on … the facility
> rating); (4) the percentage of power flow … **before** the injection …; (5) the percentage
> power flow … **after** the injection … These metrics must be updated within thirty (30)
> Calendar Days after the completion of each Preliminary or Final System Impact Study, only for
> the most recent Definitive Planning Phase cycle and excluding earlier cycles. **This
> information must be publicly posted, without a password or a fee.**"

**What this means for the 403 wall in §2:**

1. The per-POI numbers (available injection MW; DFAX / MW impact / % of rating / % loading
   before & after per impacted facility) are **tariff-required to be public, no password, no
   fee** — CEII is NOT a lawful basis for gating them: the tariff's CEII/password gating sits in
   **GIP 2.3 (Base Case Data)** — power-flow/short-circuit/stability models on a
   password-protected site behind an NDA — and **no CEII qualifier appears in 6.1.1 or in either
   FERC order's heatmap discussion** (zero CEII hits in both orders).
2. **But the obligation is an interactive visual + a query-response metrics table — NOT bulk or
   raw table export.** Blocking REST access to the backing tables (POIs / TSA / GIQueue) while
   the viewer UI still answers per-POI queries is not facially a tariff violation. That is
   precisely the shape MISO ships: `dataQueryExecute` 200-with-AES in-session (§2), raw
   `DataRows` 403.
3. Update cadence pins the vintage: metrics refresh ≤30 days after each Preliminary/Final SIS,
   most-recent-cycle only — consistent with the tables' `2025-11-11` stamps (DPP-2025 models)
   and the DPP-2025 Ph1 SIS completing 4/14/2026.
4. Neither the tariff nor the orders name a URL; the location is delegated to **BPM-015**
   (public, r33 effective 2026-07-01). BPM-015 §3.1.1 also publishes the **methodology recipe**:
   contour of incremental injection capability under first-contingency conditions, transfer
   simulated from each bus, **FCITC analysis, 3% distribution-factor cutoff, injection capacity
   decremented by existing and queued generation** — i.e. the spec for modelling the surface
   ourselves from public inputs if licensing is declined.

Verdict for this avenue: **no additional data artifact** (eLibrary attaches no data files), but
it settles the legal frame: per-POI metrics are public-by-right through the viewer UI; bulk
tables are not owed. The legitimate residual routes to the numbers are (a) the viewer's own
per-POI query responses (AES lead in §2, not attempted), or (b) rebuilding per BPM-015 §3.1.1.

### 5.9 Commands (this sweep's loader)

```
python scripts/pull_miso_dpp2025_study.py --discover        # list DPP-2025 docs in MISO's index, NO writes
python scripts/pull_miso_dpp2025_study.py --load --dry-run  # download + parse, no BigQuery
python scripts/pull_miso_dpp2025_study.py --load --smoke    # load capped at 25 rows + registry row
python scripts/pull_miso_dpp2025_study.py --load            # load Appendix I (202 rows) + registry row
```

Boundaries honoured: anonymous read-only GET/POST of public documents, identifying User-Agent,
≥1.15 s per host, no accounts, no credentials, no CEII, ASCII-only console output.

---

## 6. giqueue.misoenergy.org — the DPP-2021 viewer, read at the source-code level (BLOCKED)

**Measured 2026-08-17** by `scripts/pull_miso_giqueue_dpp2025.py`. Operator's hypothesis: the
DPP-2025 data is "hidden in and around the same location" as the DPP-2021 viewer at
`giqueue.misoenergy.org/PoiAnalysis`. **Method: stop guessing sibling URLs; fetch and read the
application's own client code and every config it loads, and enumerate the authoritative endpoint
list from the code itself.** That was done in full. **Verdict: the viewer is a static, single-
deployment CartoVista 6.2.2 app hard-wired to DPP-2021. It has no cycle/case concept anywhere in
its code, its config, or its data layers — so there is no "same location" for a 2025 case to hide
in. giqueue serves DPP-2021 and only DPP-2021.** This ends the giqueue search.

### 6.1 What was fetched (verbatim HTTP evidence, all read-only GET, ≥1.2 s apart)

| URL | HTTP | bytes | Last-Modified | what it is |
|---|---|---:|---|---|
| `/PoiAnalysis/index.html` | 200 | 9,793 | 2024-03-12 | app shell; `data-main="scripts/main"`, `data-cv-configfile="map/MISO_DEMOConfig.xml"` |
| `/PoiAnalysis/scripts/require.js` | 200 | 17,790 | 2020-06-15 | RequireJS 2.3.1 loader |
| `/PoiAnalysis/scripts/main.js` | 200 | 2,695 | 2021-01-21 | `require.config({paths})` — names every module |
| `/PoiAnalysis/scripts/PublicGenerationInterconnectionToolApp.min.js` | 200 | 103,615 | 2023-05-05 | **the entire MISO app** (12 AMD modules) |
| `/PoiAnalysis/PoiAnalysisConfig.xml` | 200 | 3,208 | 2023-05-05 | app config — the 4 `/POI/api/*` routes + disclaimer |
| `/PoiAnalysis/map/MISO_DEMOConfig.xml` | 200 | 15,750 | 2021-04-02 | CartoVista map config — layers, grid source, tiles |
| `/PoiAnalysis/map/MISO_DEMOThematic.xml` | 200 | 4,043 | 2020-12-22 | data config — `DataTableLocal` static JSON only |
| `/PoiAnalysis/map/MISO_DEMOPrintTemplates.xml` | 200 | 1,345 | 2019-09-13 | print layout (no data) |
| `/PoiAnalysis/scripts/…App.min.js.map` | **404** | — | — | no source map deployed |
| `/robots.txt` | **404** | — | — | absent |
| `/sitemap.xml` | **404** | — | — | absent |

Server on every response: `Microsoft-IIS/10.0`, `X-Powered-By: ASP.NET`. The map config's
`<LicenseKey domain="misogiqueue.azurewebsites.net">` shows the deployment is an Azure App Service.
No `X-AspNet-Version` or directory listing leaked. (`/` and `/PoiAnalysis/map/` return 403 as
directories, but every **named** file under them serves 200 — that is how the configs above were
read despite the 403 on the folder.)

### 6.2 The complete endpoint surface, extracted from the code (not guessed)

`main.js` declares exactly two app code files — the CartoVista vendor engine
(`cartovista.viewer.min.js`) and the MISO bundle (`PublicGenerationInterconnectionToolApp.min.js`);
everything else in `paths` is a library (jquery, kendo, jszip, introjs, html2canvas). Reading the
MISO bundle module-by-module, **every dynamic server call the application can make**:

| # | route | method | params the client sends | in code |
|---|---|---|---|---|
| 1 | `/POI/api/pois` | GET | **none** (bare GET, then AES-decrypt) | `GiDataBroker.fetchData`: `$.ajax({url:e,type:"GET"})` |
| 2 | `/POI/api/poi_mf` | GET | **`poiName`, `pMaxValue` — only these two** | `ClientDataConnector.fetchMonitoredFacilities`: `e+"?poiName="+encodeURIComponent(t.value)`, then `+="&pMaxValue="+i` |
| 3 | `/POI/api/generateUserGridLayer` | POST | `{userGridLayerUniqueId, poisName, intersectPoisName, mwRequest, overwrite}` | `ClientDataConnector.recalculateUserGridLayer` — **WRITE, never called read-only** |
| 4 | `/POI/api/deleteUserGridLayer` + `{uniqueId}` | GET | user grid id appended | `ClientDataConnector.deleteUserGridLayerFromServer` — **WRITE** |
| 5 | `/poi/api/gridLayer/mainGeoTiff` | GET | **none** — one fixed grid source | `MISO_DEMOConfig.xml` `<GridSource id="mainGeoTiff"><Src>` |

Routes 1–4 come from `PoiAnalysisConfig.xml` (`<MapPointsUrl>`, `<CalculationServiceBaseUrl>`,
`<CalculationUserGridLayerBaseUrl>`, `<DeleteUserGridLayerBaseUrl>`). Route 5 is the raster we
already hold as `energy.miso_poi_capacity_surface_geotiff`. **There is no other dynamic route in
the entire bundle** — no `/cycles`, no `/cases`, no metadata/list endpoint, no XHR/`fetch`/`getJSON`
beyond jQuery `$.ajax` to routes 1–4. Static resources the map loads are all baked-in files:
`map/MISO_AreaBounds.json`, `map/MISO_Random_POI_FULL.json`,
`map/thematic-data/t_MISO_POI.json`, `map/thematic-data/t_MISO_AreaBounds.json` — `DataTableLocal`
(local/static), not a server query, Last-Modified 2019–2021.

### 6.3 Why a DPP-2025 case cannot hide here — three independent proofs from the code

1. **No cycle/case/year token exists in the application.** A full scan of the 103,615-byte bundle
   for `cycle | Cycle | DPP | case | Case | 2021 | 2022 | 2023 | 2025 | vintage` returns **only
   JavaScript `switch…case` statements** (`switch(i.interactiveLayer.id){case this.areasLayer.id…}`
   and style selection `case 1/3 → MISO_POI_BLUE/RED`). The client has no variable, parameter, UI
   control, or config key for a study cycle. It cannot request one because the concept does not
   exist in the code.

2. **The config parser reads a fixed element set with no cycle field.** `PoiAnalysisConfigurationParser.parseConfiguration()`
   reads exactly: `AreasLayer`, `POIsLayer`, `CalculationServiceBaseUrl`,
   `CalculationUserGridLayerBaseUrl`, `DeleteUserGridLayerBaseUrl`, `MapPointsUrl`, `AdminHelpUrl`,
   `WelcomeTitle/SubTitle/StartButton`, `ExcelDisclaimer`, and `GridLayers`
   (`Legend/Colors`, `BufferDistancePct`, `MainGridLayerId`, `UserGridLayer`). **The string
   "DPP-2021-Cycle" appears only inside `<WelcomeSubTitle>` — human-readable disclaimer text that is
   rendered into the welcome dialog and never parsed into any request.** Even if the server offered
   a cycle, the client would not read or send it. The app loads exactly one config file, always:
   `D.loadXML("PoiAnalysisConfig.xml", …)` — no cycle-suffixed sibling is ever requested.

3. **This is why `?cycle=`/`?case=` were already found to be IGNORED** (established §pre-work). The
   `poi_mf` URL is built as `…?poiName=…&pMaxValue=…` and nothing else; `pois` is a bare GET. The
   server app was never written to read a cycle parameter, so appending one is inert — confirmed
   byte-identical earlier, and now explained at the source level. The **only two knobs** that change
   a `poi_mf` response are `poiName` (which POI) and `pMaxValue` (the MW request ceiling).

### 6.4 Vintage is DPP-2021 everywhere it is stamped

- `PoiAnalysisConfig.xml` `<WelcomeSubTitle>`: *"The tool is currently using the models and inputs
  from the DPP-2021-Cycle."* (live 2026-08-17).
- `MISO_DEMOConfig.xml` grid source `mainGeoTiff` and app-config `userGeoTiff` both carry
  `timeStamp="2021-01-04 11:18:32"`.
- The static POI/area JSON data tables are Last-Modified 2020-12-22 / 2021-04-02.
- App version string `PoiAnalysisVersion` = **1.0.212**.

Unlike the CartoVista cloud deployment (§1, whose labels self-contradict DPP2025/2023/2022), giqueue
is internally consistent: **every** vintage marker says 2021. No corroboration issue — it is DPP-2021.

### 6.5 The GeoTIFF raster route (operator's point 5) — one layer, no cycle knob

The map config declares a single `<GridLayer id="mainGridLayer">` with a single
`<GridSource id="mainGeoTiff"><Src>/poi/api/gridLayer/mainGeoTiff</Src>` (commented-out server
origin `http://dbxserver30/MISO/data/production/mainGeoTiff.tif`). The only other grid is
`userGridLayer`/`userGeoTiff`, which is **generated per-session from a visitor's own analysis** via
the WRITE route `generateUserGridLayer` — it is not a published alternate cycle. `mainGeoTiff` takes
no parameter in the config or the code, and no second published grid layer id exists. A cycle
parameter on this route would behave exactly as `?cycle=` does on `/pois` (ignored) — the backend is
the same single-cycle app. **We already hold this exact surface as
`energy.miso_poi_capacity_surface_geotiff` (DPP-2021); nothing new is retrievable here.** Guessing
sibling raster names (e.g. `mainGeoTiff2025`) is the rule-14 path-guessing the operator forbade and
was not attempted.

### 6.6 What would have to be true for giqueue to serve DPP-2025 (and why it isn't)

The data does not live in the client — it lives in whatever the `/POI/api/*` backend and the baked
static JSON read, i.e. server-side `../backend/data/production/` and the internal
`dbxserver30/MISO/data/production/` referenced (commented) in the configs. Neither is web-reachable.
For giqueue to serve 2025, MISO would have to **overwrite that backend data in place** (in which case
the same URLs would silently start returning 2025 — the `_pulled_at` on our DPP-2021 tables is the
only guard, so a periodic re-hash of `/POI/api/pois` would detect it) **or stand up a new deployment**
(a new host/path that, by the operator's own rule, must be discovered from a link, not guessed). As
of 2026-08-17 the live config still says DPP-2021 and the app has no cycle switch. **BLOCKED.**

### 6.7 Re-run

```
python scripts/pull_miso_giqueue_dpp2025.py --probe       # re-fetch client code + configs, re-verify the surface + verdict (NO writes)
python scripts/pull_miso_giqueue_dpp2025.py --register     # additionally APPEND the BLOCKED verdict to energy.registry_sources
```

Boundaries honoured: read-only GET, identifying User-Agent, ≥1.2 s per host, no accounts, no keys,
no UA spoofing, nothing mutated. No new BigQuery table is created because giqueue serves only the
DPP-2021 data already held in `energy.miso_poi_*`; a BLOCKED avenue recorded with its walls quoted
is the deliverable.
