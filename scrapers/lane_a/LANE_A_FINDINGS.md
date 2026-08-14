# LANE A FINDINGS — MISO POI identity + Indiana utility hosting-capacity maps + PJM RTEP
2026-08-14 · scripts in this folder · all loads to `energy-platfrom.indiana_app`, all registered in `indiana_app._registry` in the same run · UA `DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)` · >=1.1s/host throughout

## 1. WHAT LANDED

| table | rows | source | plottability |
|---|---|---|---|
| `indiana_app.in_miso_poi_identity` | 12,845 | MISO giqueue legacy viewer `/POI/api/pois` via held `energy.miso_poi_attributes` (registry-first: NOT re-scraped) | **DIRECTLY PLOTTABLE 9,981 rows** (publisher lat/lon; the other 2,864 are published at 0,0 = publisher's own "unknown", flagged `has_coordinates=FALSE`, never guessed). All rows JOINABLE (bus_number, bus_name, kV, area). |
| `indiana_app.in_pjm_rtep_upgrades` | 15,443 | PJM Project Status & Cost Allocation public export (POST `https://www.pjm.com/m/ProjectConst/ProjectConstructionUpgrades`, jsonModel GridName=CostAllocation, no filters, no login) | JOINABLE-IDENTITY only (no coords served): upgrade id, named substation endpoints in Location/Description, kV, TO, state. 932 rows name Indiana. Per-row TEAC PDF links in `teac_materials`. |
| `indiana_app.in_rto_expansion` | 2,034 | UNION: held MISO MTEP (`energy.txexp_miso_mtep_*`, IN token-match: 697 in-service + 328 facility-status + 77 under-evaluation) + PJM RTEP IN rows (932) | JOINABLE-IDENTITY on every row (named from/to endpoints e.g. "Attica 69"→"Attica 230", kV, owner, in-service date, cost with per-publisher units — MISO $ vs PJM $M, never fused). Nothing geocoded. |

**Indiana buses with coordinates gained this run:** `in_miso_poi_identity` gives lat/lon for MISO POIs footprint-wide including Indiana; it joins the held 904,486-row `energy.miso_poi_monitored_facilities` on `poi_name` at **11,820/11,820 = 100%** — the headroom table's identity gap (fr_bus/to_bus=0, lat/lon=0) is closed by this mapping, not by CartoVista. Vintage caveat: **DPP-2021-Cycle** (publisher's own disclaimer), NOT the 2025-11-11 vintage of the protected CartoVista layer; DPP2025 geometry-only locations are held at `energy.cartovista_miso_poi_locations` (8,219) with `energy.miso_poi_location_crosswalk` relating vintages.

## 2. TASK 1 — MISO CartoVista: BLOCKED (re-measured 2026-08-14, this run)

`cartovista_miso_probe.py` / `cartovista_miso_probe_results.json`. Map `59878415-54b3-4502-9429-bfd90c7ce3c5`, POI layer `b34ef6bd-fb8f-40a7-ab9a-c9552f1c3621`, POI table `da6949ad-2cf3-436f-bbe2-397c47c33da0` (MISO_POIs_2025-11-11, 19,223 rows declared).

| endpoint | status |
|---|---|
| `ferc.cartovista.com/api/settings/miso/ferc` | 200 (metadata) |
| `cloud.cartovista.com/miso/api/v2/maps/{map}/details` | 200 — 6 tables incl. POI 19,223 / TSA 691,523 / GIQueue 3,253 |
| `.../WebPortalServices/CartoVistaConfigFileGenerator.aspx` | 200 (layer GUIDs) |
| `.../api/v2/DataTable/{poi}/DataColumns` | 200 — columns BUS_ID, BUS_NAME, KV, KV_CLASS, LATITUDE, LONGITUDE, AREA CODE, AREA NAME, ENGLISH_NAME (schema public, data not) |
| `.../api/v2/Layer/{poi}/geojson` | **403, empty body** |
| `.../api/v2/DataTable/{poi}/DataRows` (POST startRow/rowCount) | **403, empty body** |
| `.../DataServices/dataQueryExecute` (POST, full 9-column contract) | **403, empty body** |
| `.../api/v2/Layer/{poi}/mvt/4/6/4.pbf` | 200 (81KB control — tile properties carry x/y only, per held work) |

Same per-table ProtectedData wall as 2026-08-02/03; nothing worked around. **The identity IS publicly served elsewhere** — MISO's own legacy viewer `giqueue.misoenergy.org/POI/api/pois` (single 2.9MB blob the viewer decrypts client-side for every visitor; key ships in the public JS bundle; held as `energy.miso_poi_attributes`, pulled 2026-08-02) — that is the source `in_miso_poi_identity` derives from.

## 3. TASK 2 — Indiana utility hosting/load-capacity maps

Context checks used everywhere: `energy.registry_sources` (queried first), DOE U.S. Atlas of HC Maps (updated **July 2025**: **zero Indiana utilities listed**).

| utility | verdict | evidence |
|---|---|---|
| **Indiana Michigan Power (I&M/AEP)** | **Map exists, Indiana NOT mapped.** Publisher: "Only Michigan is mapped at this time" (indianamichiganpower.com/company/about/hosting-capacity). Live service `services.arcgis.com/ZnwBsu4Q8SvSAofV/.../PROD_MI_HC_GRID/FeatureServer` layers 0=MAXLOAD, 1=MAXGEN, 118,735 cells each; STATE_ABBR×OPCO groupBy measured this run: I&M rows are **MI 12,972 / IN 0** (rest are AEP Ohio/CSP/Wheeling). Load+gen, feeder/xfmr ratings, queued capacity — rich schema, wrong state. Held copies `energy.hca_aep_im_mi_load/gen` match live counts exactly → NOT re-pulled (registry-first). Org also serves `Indiana_Michigan_EV_Eligibility` (570 IN census-tract polygons) — EV **rate eligibility**, not capacity; not pulled. |
| **Duke Energy Indiana** | **No Indiana map published.** Duke's AGOL org (`services3.arcgis.com/oX5r75R7mapdoI2F`, 76 services, enumerated this run) has GHC ONLY for: Carolinas (`Generation_Hosting_Capacity_November_2025`, 74,367 hexes; `Generation_Map_Publishing` "Carolinas May 2026", 73,970) and Ohio (`Ohio_Generation_Map` + `Ohio_Load_Map`, 7,451 hexes each, Cincinnati-area bbox). Indiana business pages (browser-verified: generate-your-own + utility-scale-interconnection, IN jurisdiction) link no map — only PowerClerk application portal (login; not touched). Resolves the old registry rows "Duke IN GHC — BLOCKED/never located": it does not exist for IN. |
| **NIPSCO** | **None found.** Searches: "NIPSCO hosting capacity map interconnection heatmap", site:nipsco.com hosting capacity; net-metering page inspected — no map referenced; absent from DOE atlas. |
| **AES Indiana (IPL)** | **None found.** Searches: "AES Indiana hosting capacity map ... heatmap 2025", site:aesindiana.com; aesindiana.com/interconnections inspected — application PDFs only, no map, no capacity spreadsheets; absent from DOE atlas. |
| **CenterPoint Energy Indiana (Vectren)** | **None found.** Searches incl. site:centerpointenergy.com; only a DG interconnection **application portal** `plus.anbetrack.com/cnp-dg/#/` (requires registration — gated, recorded, left alone); absent from DOE atlas. |

## 4. BLOCKED / GATED (exact walls)

1. **CartoVista MISO POI/TSA tabular routes** — HTTP 403, empty body, on `Layer/{id}/geojson`, `DataTable/{guid}/DataRows`, `DataServices/dataQueryExecute` (URLs above; re-measured 2026-08-14). Per-table ProtectedData; metadata and MVT stay 200.
2. **duke-energy.com CDN** — HTTP 403 (Akamai bot wall) to scripted fetch of PDFs/pages, e.g. the GHC overview PDF `.../tsrg/meeting-25/ghc-external-map-overview-july-2024.pdf`. Pages were read in a real browser instead; the DATA (AGOL feature services) required no wall crossing.
3. **CenterPoint DG portal** `plus.anbetrack.com/cnp-dg/#/` — registration/login required; application system, not a data product. Not attempted.
4. **Duke PowerClerk (Indiana interconnection portal)** `midwest-interconnection.powerclerk.com` — login; not attempted.
5. (Context, not this lane: PJM Data Miner 2 needs a free-account API key per held registry — not attempted; the RTEP export needed no key.)

## 5. I&M (PJM-side) INDIANA COUNTIES — from `energy.eia861_service_territory` (utility_id_eia 9324 = Indiana Michigan Power Co; names via eia861_demand_response)

43 raw values, 40 distinct counties after spelling normalization (DeKalb ×3 spellings, LaGrange ×2):
Adams, Allen, Blackford, Dearborn, DeKalb, Delaware, Elkhart, Fayette, Grant, Hamilton, Henry, Howard, Huntington, Jay, Jefferson, Knox, LaGrange, LaPorte, Madison, Marion, Marshall, Miami, Montgomery, Noble, Parke, Randolph, Ripley, Spencer, St. Joseph, Starke, Steuben, Sullivan, Tippecanoe, Tipton, Vermillion, Wabash, Warrick, Wayne, Wells, Whitley.
(EIA-861 territory grain is county-level and generous; I&M's marketing claims 24 IN counties — treat the EIA list as the superset for screening.)

## 6. THREE MOST USEFUL NEXT ENDPOINTS

1. **`https://www.pjm.com/m/ProjectConst/UpgradeDetails` + `/UpgradeCostAllocations`** (same public POST family as the export) — per-upgrade detail/cost-allocation JSON for the 932 Indiana RTEP upgrades; would add milestone-level dates and TO cost splits keyed to `upgrade_id`.
2. **`https://services.arcgis.com/ZnwBsu4Q8SvSAofV/arcgis/rest/services/PROD_MI_HC_GRID/FeatureServer/{0,1}`** — re-check STATE_ABBR quarterly (one groupBy request): lastEditDate is actively maintained (was today) and I&M told MPSC staff the tool may expand; the day IN rows appear, the generic ArcGIS loader lands them (`outSR=4326`, page by OBJECTID_1).
3. **`https://giqueue.misoenergy.org/POI/api/pois`** — re-pull when MISO advances the viewer past DPP-2021-Cycle (watch the disclaimer in `PoiAnalysisConfig.xml`); a newer vintage would refresh `in_miso_poi_identity` and possibly populate the 2,864 coordinate-unknown POIs. (Duke Carolinas/Ohio GHC services are recorded above if scope ever widens beyond Indiana.)

## 7. PJM FOLLOW-UP (coordinator add-on, 2026-08-14 second pass)

### 7a. RTEP per-upgrade detail + cost-allocation fragments — LANDED (Indiana slice)
`pull_pjm_upgrade_details.py`. Public GETs, no login: `/m/ProjectConst/UpgradeDetails?upgradeId={id}` and `/m/ProjectConst/UpgradeCostAllocations?upgradeId={id}` (the page's own modal loaders).
- `indiana_app.in_pjm_rtep_upgrade_details` — **932 rows** (one per Indiana-naming upgrade id, 932/932 crawled, 0 errors): criteria_violation, description, type, driver, sub_region, location, task, equipment, related_materials (multi-link JSON: TEAC PDFs + proposal-window ids).
- `indiana_app.in_pjm_rtep_cost_allocations` — **375 rows**, one per (upgrade_id, share_type, zone, percent); upgrades absent here published no split (allocation fragment empty).
- SCOPE: the 932 Indiana-naming ids of 15,443 (INDIANA SLICE — full universe is ~9.4h at the rate limit; resumable script records the `--all` command). Fragments serve NO dates — milestone dates live in `in_pjm_rtep_upgrades`' own columns (that is the observed-date surface).
- ⚠ OVERLAP, recorded not hidden: held `energy.txexp_pjm_rtep_upgrades` (15,440 rows from the anonymous 25MB `projectCostUpgrades.xml`) ALREADY carries `costallocationpercent`/`costallocationpercentlrs` comma-strings, and my `in_pjm_rtep_upgrades` XLSX carries the same two columns — the cost-allocation crawl NORMALIZES that into rows; the genuinely NEW fields are `criteria_violation` and multi-link `related_materials`.

### 7b. Queue project → network upgrade cost $ — LANDED (NUCRA) + held + deferred
- **LANDED: `indiana_app.in_pjm_nucra_costs` — 55 rows** (the full posted-allocation universe), from the public XLSX export `POST /m/ProjectTransition/GenerateExcelNUCRAProjectsAll` (cycle-service-request-status page, no login). THE machine-readable mapping: network upgrade id → `Projects with Cost Allocation` (queue ids incl. MISO-J*/NYISO-Q* affected-system projects) → Cost($M) → TO → NUCRA PDF link → NUCRA status → in-service/cancellation dates. 1 row names Indiana in State (column is sparse; TO+queue-id joins are the reliable route).
- **ALREADY HELD (registry-first, not re-pulled):** `energy.txexp_pjm_tcic_upgrade_info` 9,936 rows (TCIC workbook: initial/latest TEAC $M, allocation type, useful life — upgrade-grain costs); `energy.txexp_pjm_rtep_upgrades` 15,440 (XML incl. costestimate + allocation strings); `energy.lbnl_interconnection_costs` (PJM queue-project costs through 2022); `energy.pjm_queuescope_results` 1.97M (per-bus headroom).
- **Probed, no cost fields:** `pjmfiles/media/planning/queues-data/transitionProjects.xml` (200 OK, 310 cycle projects, 28 IN) — status/MW/report-links only; `clusterReports.xml` (200, report URLs). `pub/planning/downloads/xml/NUCRA.xml` → 404 (JS-advertised path dead; the working surface is the export POST above).
- **EXTRACTION-DEFERRED (document-only):** per-project SIS/facilities-study costs live in per-project reports, systematic URLs published in transitionProjects.xml, pattern `pjm.com/pub/planning/project-queues/{cycle}/{phase}/{project}/..._imp_....htm|pdf`, and per-upgrade NUCRA agreement PDFs `pjm.com/pjmfiles/pub/planning/project-queues/Agreements/NUCRAs/{upgrade_id}_nucra.pdf` (links captured row-wise in in_pjm_nucra_costs). No OCR this run per instruction.

### 7c. COORDINATE EXPERIMENT — bus_label ↔ substation_name (REPORT ONLY, no table wired)
`coord_experiment.py`. Universe: 1,475 distinct AEP `bus_label` in `energy.pjm_queuescope_results` → 1,403 normalized names (labels are PSS/E-truncated: `05LEBANO 138 kV (242700)`); `indiana_app.in_substations` 3,010 assets, of which **1,992 (66%) are UNKNOWN#### placeholders** → 1,018 usable-named.

| join | buses matched | substations matched | bus→multi-sub collisions |
|---|---|---|---|
| exact (normalize: UPPER, strip punctuation + type suffixes) | **38/1,403 = 2.7%** | 41/1,018 = 4.0% | 3 (7.9% of matched) |
| prefix (truncation-aware, ≥5 chars) | **75/1,403 = 5.3%** | 88/1,018 = 8.6% | 12 (16.0% of matched) |

10 sample pairs for human review (prefix join; exact-equal flagged):
`05ALADDIN 138 kV↔ALADDIN (Alexandria/Madison, 138/138, exact)` · `05ROCKCR 138↔ROCK CREEK (Huntington, 138/138)` · `05DEQUIN 345↔DEQUINE (W. Lafayette/Tippecanoe, 345/345)` · `05MEADOW 138↔MEADOWBROOK (Anderson/Madison, 138/138)` · `05JACKSON 138↔JACKSON ROAD (South Bend/St. Joseph, **138 vs 345 kV mismatch**)` · `05KENDAL 138↔KENDALLVILLE (Kendallville/Noble, 138/138)` · `05GRABILL 138↔GRABILL (Grabill/Allen, 138/138, exact)` · `05FLOYD 138↔FLOYDS KNOBS (New Albany/Floyd, 138/138)` · `05BATTLE 138↔Battleground Station (no county/kv on sub)` · `05GRANT 138↔Grant Substation (no county/kv, exact)`.

**Verdict (measured):** name-join is NOT viable as a wired location source — ceiling 5.3% even truncation-aware, collisions triple exact→prefix, kV mismatches appear in samples, and the binding constraint is the 66% placeholder-name rate in in_substations, not the normalizer. If the operator wants a next step: constrain candidates to I&M counties + require kV agreement, or wait for a name-bearing substation refresh; nothing wired this run.

## 8. PJM BUS-LOCATION DEEP DIVE (operator escalation, 2026-08-14 third pass)

**The decision asked for: which path gives PJM buses coordinates, at what match rate, with what caveats.**

### Angle 1 — in-warehouse re-match (HIFLD + OSM replace the 66%-placeholder in_substations)
AEP QueueScope universe: 1,475 distinct buses (1,403 normalized names; PSS/E-truncated). Candidate pools: `energy.nat_substations_hifld` and `energy.osm_power_substations`, AEP-footprint states (IN,MI,OH,WV,VA,KY,TN) and IN-only panels. kV validator = bus_kv within station's [min,max] kV.

| panel | exact | exact kV-validated | prefix | prefix kV-validated |
|---|---|---|---|---|
| HIFLD AEP-states (2,603 named) | 8.0% | 6.1% (6 collisions) | 19.2% | 15.8% |
| OSM AEP-states (8,436 named) | 10.4% | 8.1% (12 collisions) | 22.9% | 18.8% |
| HIFLD IN-only (337 named) | 2.1% | 1.7% (**0 collisions**) | 4.6% | 3.6% |
| OSM IN-only (900 named) | 1.9% | 1.2% (1 collision) | 5.1% | 2.9% |

UNION wireable tier (exact + kV-validated, IN): **32 distinct buses**; 10 found in both layers, coordinates agree ≤~100m for 8/10; 3 multi-site cases flagged. Samples visually correct (DUMONT→North Liberty 345/765; CENTER→Indianapolis; BOSSERMAN→Michigan City). Denominator caveat: bus-side % is bounded by the unknown IN share of AEP's 7-state bus universe — IN-only panels understate the IN-conditional rate.

### Angle 2 — PJM's own GIS: LIVE public ArcGIS server found
`https://gis.pjm.com/arcgis/rest/services` (folders CTC, ESM, Interregional, Renewables, RTDMS, Utilities):
- **LANDED: `indiana_app.in_pjm_gis_queues` — 6,923 queue POINTS with PJM's own coordinates** (Renewables/Queue/MapServer/0; Query capability, anonymous; outFields=\*, outSR=4326; pulled complete, count-verified vs returnCountOnly). Columns: QUEUE_ID, FAC_ID (4-char facility code + state + kV, e.g. BERGNJ230), VOLTAGE, lat/lon. **DIRECTLY PLOTTABLE**; exact-keyed to queue data via QUEUE_ID.
- Walls (exact): `CTC/*` (Footprint, FuelTypes, Renewables, TO_Zones, TransmissionSystem) and `RTDMS/*` return HTTP 200 with in-body `{"error":{"code":500,"message":"Error handling service request :0x80004004 - Unidentified Error in 'esriCarto.MapServer'"}}` — the transmission-system layers exist but do not serve anonymously. `ESM` folder lists zero public services (the Enhanced System Map's layers are not exposed here). `Interregional/LMP` = 19 city points + zones (not buses).

### Angle 3 — the wired ladder: `indiana_app.in_pjm_bus_locations_candidate` (1,475 rows, one per AEP bus)
Registered twice: second row supersedes the first — the initial build's 4-char FAC gate produced FALSE HIGHS (FAC `CLIN` matched both CLINCHFLD and CLINTO; a WV bus landed on a MI `VALL` point). Rebuilt with ≥5-char overlap + unique-bus-family gate, which eliminated the tier entirely — **measured: every FAC_ID name part is a 4-char code, too weak for per-bus joins under the never-guess rule** (the queue points remain exact-keyed by QUEUE_ID instead).

Final per-method counts (tiers never blended; kV gate hard for high; collisions → method='none'):
| location_method | confidence | buses | coords |
|---|---|---|---|
| substation_match_exact | high (kV-validated) | 91 | 91 |
| substation_match_exact | med | 34 | 34 |
| substation_match_prefix | med | 91 | 91 |
| rtep_bridge | med | 13 | 13 |
| none (1,246; of which 186 saw only ambiguous matches) | — | 1,246 | 0 |

**Located: 229/1,475 = 15.5% of the whole AEP zone universe** (IN-conditional share is higher; denominator spans 7 states). Every row carries location_method, match_confidence, match_basis, kv_consistent, collision_count. Interpolation tier **SKIPPED-BY-MEASUREMENT**: QueueScope PSS/E bus_numbers (242,508–290,735) join `energy.bus_hifld` synthetic ids (1–75,328) at exactly **0/1,475** — recorded, not attempted.

### Angle 4 — CEII boundary (BLOCKED-CEII, do not re-chase)
PJM RAW/PSS-E powerflow cases, MMWG model files, and FERC Form 715 Parts 2–6 (base cases, maps, planning criteria) are CEII — bus-coordinate truth lives there and stays out of scope (matches `data/bus_headroom_sources.json` ceii_boundary). PJM DataMiner2 needs a registered API key (operator-declined earlier, unchanged). Nothing was attempted against any of these.

**Recommendation:** the defensible public path is the wired ladder (229 buses now, styled by method/confidence) + `in_pjm_gis_queues` for queue-facility siting (6,923 publisher points, exact QUEUE_ID key). The single highest-leverage upgrade would be a named refresh of the substation layer (replace UNKNOWN#### placeholders), which mechanically lifts the exact tier.

## 9. SCRIPTS
`registry_check.py` / `pjm_registry_check.py` (registry-first) · `cartovista_miso_probe.py` (+results json) · `build_in_miso_poi_identity.py` · `im_counties.py` · `check_aep_service.py` / `check_aep_states.py` / `check_aep_ev.py` / `resolve_aep_dashboard.py` · `pjm_page_inspect.py` / `pjm_js_inspect.py` / `pull_pjm_rtep_upgrades.py` (+`pjm_rtep_upgrades.xlsx`) · `build_in_rto_expansion.py` · `register_helper.py` · `agol_search_duke.py` / `agol_duke_org.py` / `duke_enumerate.py` / `duke_hc_inspect.py` · `pull_pjm_upgrade_details.py` (resumable; `_cache_pjm_details/`) · `pull_pjm_nucra.py` (+`pjm_nucra.xlsx`) · `coord_experiment.py` / `coord_experiment2.py` / `coord_experiment2b.py` (report-only) · `pjm_gis_probe.py` / `pjm_gis_enum.py` / `pjm_gis_queue_inspect.py` / `pull_pjm_gis_queues.py` · `tier4_gate2.py` (0% vocab measurement) · `build_bus_locations_candidate.py` (+`sanity_t0.py`) · `final_qa.py`
