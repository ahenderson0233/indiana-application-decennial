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

## 7. SCRIPTS
`registry_check.py` (registry-first) · `cartovista_miso_probe.py` (+results json) · `build_in_miso_poi_identity.py` · `im_counties.py` · `check_aep_service.py` / `check_aep_states.py` / `check_aep_ev.py` / `resolve_aep_dashboard.py` · `pjm_page_inspect.py` / `pjm_js_inspect.py` / `pull_pjm_rtep_upgrades.py` (+`pjm_rtep_upgrades.xlsx`) · `build_in_rto_expansion.py` · `register_helper.py` · `agol_search_duke.py` / `agol_duke_org.py` / `duke_enumerate.py` / `duke_hc_inspect.py` · `final_qa.py`
