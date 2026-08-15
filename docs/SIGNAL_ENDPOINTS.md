# Signal endpoints & loaders — read from the registry 2026-08-15

Every Indiana-relevant signal source the registry already knows, with its endpoint and the
command that loads it. This is the SI re-pull worklist: **no discovery is needed for any
row below** — the endpoint and loader are recorded.

Read MECHANICALLY: `registry_sources.source_id` is signal-prefixed, so this is a prefix
read, not a name match. The earlier "10 of 19 source_ids have no endpoint" figure came
**126 Indiana-relevant sources across 5 signals carry a registry entry.** Signals covered: D10, D12, D13, D17, unassigned.

from a token-overlap matcher and under-reported — the W17 rule exists for this reason.

## D10 — 1 source(s)

**`d10:state-tax-lien:in`** — D10 state tax lien - IN  
status `NOT ATTEMPTED - county-recorder-tier` · kind `NONE` · state `IN` · rows measured —  
**re-scrape:** `RE-SCRAPE COMMAND: n/a - NOT ATTEMPTED (county-recorder-tier; no statewide index)`  
loader: `lane_d3_d10_d13`  

## D12 — 2 source(s)

**`countysi_b:D12:IN:indy_marion_code_enforcement`** — D12 Marion IN - indy_marion_code_enforcement  
status `BUILT+LOADED (910,483 rows measured in BigQuery)` · kind `rest` · state `IN` · rows measured 910483  
endpoint: `https://gis.indy.gov/server/rest/services/OpenData/OpenData_NonSpatial/MapServer/1`  
tables: `si_d12_indy_marion_code_enforcement`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.load_county_si_b_bq --key indy_marion_code_enforcement`  
loader: `load_county_si_b_bq`  

**`si_countyb:d12:indy_marion_code_enforcement`** — Indianapolis / Marion County IN code enforcement  
status `DUPLICATE-OF-HELD - si_d12_indy_marion_code_enforcement (910,483 rows) is a re-acquisition of already-held agis_indy_code_enforcement` · kind `arcgis` · state `IN` · rows measured 910483  
endpoint: `https://gis.indy.gov/server/rest/services/OpenData/OpenData_NonSpatial/MapServer/1`  
tables: `agis_indy_code_enforcement, si_d12_indy_marion_code_enforcement`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.load_county_si_bq --only indy_marion_code_enforcement  # or the D12 loader --key form; BOTH tables refresh from this same endpoint`  
loader: `data-acquisition lane (dedup pass 2026-08-09)`  

## D13 — 1 source(s)

**`d13:federal-tax-lien:in`** — D13 federal tax lien - IN  
status `NOT ATTEMPTED - county-recorder-tier` · kind `NONE` · state `IN` · rows measured —  
**re-scrape:** `RE-SCRAPE COMMAND: n/a - NOT ATTEMPTED (county-recorder-tier per IRC 6323(f))`  
loader: `lane_d3_d10_d13`  

## D17 — 3 source(s)

**`d17courts:D17:IN:in_iocs_court_year`** — D17 eviction STATEWIDE IN - in_iocs_court_year  
status `BUILT+LOADED (1,543 rows measured in BigQuery)` · kind `file` · state `IN` · rows measured 1543  
endpoint: `https://www.in.gov/courts/iocs/files/rpts-ijs-2025-pending-incoming-disposed-miscellaneous.xlsx`  
tables: `si_d17_in_iocs_court_year`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.load_d17_courts_bq --key in_iocs_court_year --recreate`  
loader: `ingest/probe_scope_unknown.py`  

**`d17courts:D17:IN:in_iocs_court_year`** — D17 eviction STATEWIDE IN - in_iocs_court_year  
status `BUILT+LOADED (1,543 rows measured in BigQuery)` · kind `rest` · state `IN` · rows measured 1543  
endpoint: `https://www.in.gov/courts/iocs/files/rpts-ijs-2025-pending-incoming-disposed-miscellaneous.xlsx`  
tables: `si_d17_in_iocs_court_year`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.load_d17_courts_bq --key in_iocs_court_year --recreate`  
loader: `load_d17_courts_bq`  

**`d17courts:D17:IN:in_iocs_court_year`** — D17 eviction STATEWIDE IN - in_iocs_court_year  
status `BUILT+LOADED (1,543 rows measured in BigQuery)` · kind `rest` · state `IN` · rows measured 1543  
endpoint: `https://www.in.gov/courts/iocs/files/rpts-ijs-2025-pending-incoming-disposed-miscellaneous.xlsx`  
tables: `si_d17_in_iocs_court_year`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.load_d17_courts_bq --key in_iocs_court_year --recreate`  
loader: `load_d17_courts_bq`  

## unassigned — 119 source(s)

**`agis:indy_code_enforcement`** — ad-hoc  
status `BUILT+LOADED — auto-registered by loader in the same run` · kind `arcgis` · state `—` · rows measured 910483  
endpoint: `https://gis.indy.gov/server/rest/services/OpenData/OpenData_NonSpatial/MapServer/1`  
tables: `agis_indy_code_enforcement`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.load_arcgis_attr_bq --url "https://gis.indy.gov/server/rest/services/OpenData/OpenData_NonSpatial/MapServer/1" --key indy_code_enforcement`  
loader: `load_arcgis_attr_bq`  

**`auto_appeals_in_ibtr_determinations`** — appeals_in_ibtr_determinations (auto-registered)  
status `BUILT - registered retrospectively` · kind `HTTP` · state `—` · rows measured —  
tables: `appeals_in_ibtr_determinations`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.load_in_ibtr_appeals_bq`  
loader: `session_0fc0a2ca_reconstruction`  

**`csv:180`** — Duke Energy Indiana Grid Hosting Capacity  
status `BLOCKED` · kind `none` · state `IN (Duke)` · rows measured —  
**re-scrape:** `sandbox cannot fetch`  
loader: `migrate_registry_to_bq`  

**`csv:181`** — Phase-3 measured utility/IURC data (FERC 715 / PSS-E)  
status `CATALOGED-not-built` · kind `none` · state `IN` · rows measured —  
**re-scrape:** `manual request`  
loader: `migrate_registry_to_bq`  

**`csv:249`** — AEP Indiana Michigan Power (I&M)  
status `BUILT+LOADED (MI rows)` · kind `none` · state `utility/IN+MI (Midwest)` · rows measured —  
**re-scrape:** `item-resolve`  
loader: `migrate_registry_to_bq`  

**`csv:263`** — Duke Energy Grid Hosting Capacity (IN/OH)  
status `UNRESOLVED` · kind `none` · state `utility/IN+OH` · rows measured —  
**re-scrape:** `auto-resolve via parse_app_url() once URL obtained`  
loader: `migrate_registry_to_bq`  

**`csv:276`** — IGIO statewide parcels (current)  
status `BUILT+LOADED` · kind `arcgis` · state `state (IN, 92 counties)` · rows measured —  
endpoint: `https://gisdata.in.gov/server/rest/services/Hosted/Parcel_Boundaries_of_Indiana_Current/FeatureServer/0/query`  
**re-scrape:** `where="dlgf_prop_class_code>='300' AND <'500'"; per-county paging via resultOffset; outFields=PARCEL_FIELDS; returnGeometry for centroid`  
loader: `migrate_registry_to_bq`  

**`csv:277`** — IGIO statewide parcels (2022)  
status `CATALOGED-not-built` · kind `arcgis` · state `state (IN)` · rows measured —  
endpoint: `https://gisdata.in.gov/server/rest/services/Hosted/Parcel_Boundaries_of_Indiana_2022/FeatureServer/0/query`  
**re-scrape:** `same as current; used only if current fails`  
loader: `migrate_registry_to_bq`  

**`csv:278`** — DLGF Real Property Assessment file  
status `BUILT+LOADED` · kind `page` · state `state (IN)` · rows measured —  
endpoint: `https://www.indianamap.org`  
**re-scrape:** `dlgf_to_csv.py: fixed-width offsets (owner 223:303, mail 303:433, land 468:480, imp 480:492, total 492:504, sale date 436:446, price ~730:742); merges multi-file per-field`  
loader: `migrate_registry_to_bq`  

**`csv:279`** — Marion County parcels (owner tier-1)  
status `CATALOGED-not-built` · kind `arcgis` · state `county (Marion)` · rows measured —  
endpoint: `https://services3.arcgis.com/hrGHbYKdjpN9Dagg/ArcGIS/rest/services/Parcels/FeatureServer/0/query`  
**re-scrape:** `COUNTY_PARCEL_ENDPOINTS map; owner field auto-detected; no Chrome`  
loader: `registry_hygiene_20260802`  

**`csv:280`** — USA Structures (FEMA/Oak Ridge)  
status `BUILT+LOADED` · kind `arcgis` · state `national` · rows measured —  
endpoint: `https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services/USA_Structures_View/FeatureServer/0/query`  
**re-scrape:** `POST bbox envelope per parcel; SQFEET attr; clipped to parcel; EPSG 5070 area`  
loader: `migrate_registry_to_bq`  

**`csv:281`** — IDEM Brownfields — sites  
status `BUILT+LOADED` · kind `arcgis` · state `state (IN)` · rows measured —  
endpoint: `https://gisdata.in.gov/server/rest/services/Hosted/Brownfields/FeatureServer/2020/query`  
**re-scrape:** `points; 50 m buffer join to parcel centroid; status A/I`  
loader: `migrate_registry_to_bq`  

**`csv:282`** — IDEM Brownfields — parcels  
status `BUILT+LOADED` · kind `arcgis` · state `state (IN)` · rows measured —  
endpoint: `https://gisdata.in.gov/server/rest/services/Hosted/Brownfields/FeatureServer/2021/query`  
**re-scrape:** `polygon overlay`  
loader: `migrate_registry_to_bq`  

**`csv:283`** — IndianaMap / EPA FRS brownfield fallback  
status `CATALOGED-not-built` · kind `arcgis` · state `state/national` · rows measured —  
endpoint: `https://gis.indiana.edu/arcgis/rest/services/Reference/IndianaMap/MapServer/52`  
**re-scrape:** `ordered fallback`  
loader: `migrate_registry_to_bq`  

**`csv:284`** — IURC Electric Service Territories  
status `BUILT+LOADED` · kind `arcgis` · state `state (IN)` · rows measured —  
endpoint: `https://gisdata.in.gov/server/rest/services/Hosted/IURC_Prod_Boundaries_View/FeatureServer/0/query`  
**re-scrape:** `spatial join parcel→territory; field 'utilityname'`  
loader: `migrate_registry_to_bq`  

**`csv:285`** — IU maps utility territories (fallback)  
status `CATALOGED-not-built` · kind `arcgis` · state `state (IN)` · rows measured —  
endpoint: `https://maps.indiana.edu/arcgis/rest/services/Infrastructure/Energy_Electric_Service_Territories/MapServer/0/query`  
**re-scrape:** `ordered fallback`  
loader: `migrate_registry_to_bq`  

**`csv:286`** — DWD WARN notices  
status `BUILT+LOADED` · kind `page` · state `state (IN)` · rows measured —  
endpoint: `https://www.in.gov/dwd/warn-notices/current-warn-notices/`  
**re-scrape:** `warn_clean_IN.py: DWD table → PDF site address → Census geocode → reverse-geocode point to parcel (no centroids)`  
loader: `migrate_registry_to_bq`  

**`csv:289`** — INBiz public business search  
status `BUILT+LOADED` · kind `page` · state `state (IN)` · rows measured —  
endpoint: `https://bsd.sos.in.gov/publicbusinesssearch`  
**re-scrape:** `inbiz_dissolution_IN.py: per-entity lookup over master's entity-named owners (--limit 500 default)`  
loader: `migrate_registry_to_bq`  

**`csv:290`** — INBiz Bulk Data Services  
status `REJECTED` · kind `page` · state `state (IN)` · rows measured —  
endpoint: `https://inbiz.in.gov/Inbiz/BulkDataServices`  
**re-scrape:** `INBiz account purchase`  
loader: `migrate_registry_to_bq`  

**`csv:292`** — Indianapolis MDC/Hearing-Examiner agendas (municode)  
status `WIRED-not-populating` · kind `page` · state `county (Marion/Indianapolis)` · rows measured —  
endpoint: `https://meetings.municode.com/adaHtmlDocument/index?cc=INDYMARION&me=`  
**re-scrape:** `permits_IN.py: parse petition blocks (case, address, from→to zoning); gzip-aware fetch; petitioner names dropped`  
loader: `migrate_registry_to_bq`  

**`csv:293`** — DMD meetings portal (agenda directory)  
status `BUILT+LOADED` · kind `page` · state `county (Marion)` · rows measured —  
endpoint: `https://indianapolis-in.municodemeetings.com/DMDmeetings`  
**re-scrape:** `regex adaHtmlDocument URLs; dedupe by meeting GUID (prefer ip=True)`  
loader: `migrate_registry_to_bq`  

**`csv:294`** — Indianapolis rezoning GIS (open data)  
status `REJECTED` · kind `arcgis` · state `county (Marion)` · rows measured —  
endpoint: `https://gis.indy.gov/server/rest/services/OpenData/OpenData_PlanningZoning/MapServer/8/query`  
**re-scrape:** `query by date`  
loader: `migrate_registry_to_bq`  

**`csv:295`** — data.indy.gov code enforcement (DCE)  
status `WIRED-not-populating` · kind `arcgis` · state `county (Marion)` · rows measured —  
endpoint: `https://gis.indy.gov/server/rest/services/OpenData/OpenData_NonSpatial/MapServer/1/query`  
**re-scrape:** `match by STREET_ADDRESS`  
loader: `migrate_registry_to_bq`  

**`csv:296`** — MapIndy Zoning  
status `WIRED-not-populating` · kind `arcgis` · state `county (Marion)` · rows measured —  
endpoint: `https://gis.indy.gov/server/rest/services/MapIndy/Zoning/MapServer`  
**re-scrape:** `polygon attribute join`  
loader: `migrate_registry_to_bq`  

**`csv:297`** — SRI tax-sale lists  
status `WIRED-not-populating` · kind `page` · state `county (per-county lists)` · rows measured —  
endpoint: `https://www.sriservices.com`  
**re-scrape:** `ingest per-county list (parcel/address); observability scoped by county`  
loader: `migrate_registry_to_bq`  

**`csv:298`** — SRI / Zeus auction calendar  
status `WIRED-not-populating` · kind `page` · state `state (IN)` · rows measured —  
endpoint: `https://properties.sriservices.com/auctionlist`  
**re-scrape:** `foreclosure_IN.py: render per-county property view; parse address/parcel/cause`  
loader: `migrate_registry_to_bq`  

**`csv:299`** — County sheriff sale pages (in.gov CMS)  
status `BUILT+LOADED` · kind `page` · state `county (Morgan live)` · rows measured —  
endpoint: `https://www.in.gov/sheriffs/morgan/services/sheriff-sales/`  
**re-scrape:** `foreclosure_props_IN.py: regex inline sale blocks; append-merge to foreclosure CSV; dedupe county+addr+date`  
loader: `migrate_registry_to_bq`  

**`csv:351`** — Indiana URC (EDS)  
status `BLOCKED (SPA)` · kind `none` · state `IN` · rows measured —  
**re-scrape:** `MS Power Pages`  
loader: `migrate_registry_to_bq`  

**`csv:407`** — (none - gap record)  
status `KNOWN-GAP-not-built` · kind `none` · state `16 states: MA VA IN WI WA UT IA WV NV NE ND ME NH DE RI HI` · rows measured —  
**re-scrape:** `-`  
loader: `migrate_registry_to_bq`  

**`csv:464`** — Parcel manifest: data/county_parcel_backfill_2026_07.json [part 1 of 2]  
status `BUILT+LOADED` · kind `arcgis` · state `AL, GA, IL, KY, LA, MI, MO, SC, SD (see per-entry note)` · rows measured 10249756  
endpoint: `https://smpesri.scdot.org/arcgis/rest/services/GISMapping/SC_Parcels/MapServer/0`  
tables: `parcels_al_dekalb_county_multi, parcels_al_hale_county, parcels_al_montgomery_county, parcels_al_regional_al_residential_parcel, parcels_ga_bartow_county, parcels_ga_berrien_county_multi, parcels_ga_coffee_county, parcels_ga_fayette_county, parcels_il_adams_county, parcels_il_dekalb_county, parcels_il_effingham_county, parcels_il_hancock_county, parcels_ky_adair_county_multi, parcels_ky_allen_county, parcels_ky_anderson_county_multi, parcels_la_acadia_parish, parcels_la_east_baton_rouge_parish, parcels_mi_barry_county, parcels_mi_cheboygan_county, parcels_mi_dickinson_county_multi, parcels_mi_eaton_county, parcels_mi_emmet_county, parcels_mi_lenawee_county, parcels_mi_midland_county, parcels_mo_bollinger_county_multi, parcels_mo_buchanan_county, parcels_mo_clay_county, parcels_mo_jasper_county, parcels_sc_abbeville_county, parcels_sc_aiken_county, parcels_sc_allendale_county, parcels_sc_anderson_county, parcels_sc_bamberg_county, parcels_sc_barnwell_county, parcels_sc_beaufort_county, parcels_sc_berkeley_county, parcels_sc_calhoun_county, parcels_sc_charleston_county, parcels_sc_cherokee_county, parcels_sc_chester_county, parcels_sc_chesterfield_county, parcels_sc_clarendon_county, parcels_sc_colleton_county, parcels_sc_darlington_county, parcels_sc_dillon_county, parcels_sc_dorchester_county, parcels_sc_edgefield_county, parcels_sc_fairfield_county, parcels_sc_georgetown_county, parcels_sc_greenwood_county, parcels_sc_jasper_county, parcels_sc_kershaw_county, parcels_sc_lancaster_county, parcels_sc_laurens_county, parcels_sc_lee_county, parcels_sc_marion_county, parcels_sc_mccormick_county, parcels_sc_newberry_county, parcels_sc_orangeburg_county, parcels_sc_richland_county, parcels_sc_saluda_county, parcels_sc_union_county, parcels_sc_williamsburg_county, parcels_sd_lawrence_county`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.national_scrape --manifest data/county_parcel_backfill_2026_07.json --all --workers 6   (one county/state: --only <id>; --dry-run first to confirm the layer index and maxRecordCount; -`  
loader: `registry_hygiene_20260802`  

**`dcpuc_in`** — dcpuc_in  
status `blocked` · kind `none` · state `IN` · rows measured —  
loader: `migrate_registry_to_bq`  

**`der_in_duke_energy_indiana`** — der_in_duke_energy_indiana  
status `blocked` · kind `page` · state `IN` · rows measured —  
endpoint: `https://www.duke-energy.com/Business/Products/Renewables/Generate-Your-Own/Utility-Scale-Interconnection/Grid-Hosting-Capacity`  
**re-scrape:** `sandbox cannot fetch JS map → paste app URL`  
loader: `migrate_registry_to_bq`  

**`der_in_indiana_michigan_power_aep_i_m`** — der_in_indiana_michigan_power_aep_i_m  
status `done` · kind `page` · state `IN` · rows measured —  
endpoint: `https://www.indianamichiganpower.com/company/about/hosting-capacity`  
loader: `migrate_registry_to_bq`  

**`der_in_indianamap_iurc_regulator`** — der_in_indianamap_iurc_regulator  
status `pending` · kind `page` · state `IN` · rows measured —  
endpoint: `https://www.indianamap.org/datasets/INMap::electric-service-territories-iurc/about`  
**re-scrape:** `download`  
loader: `migrate_registry_to_bq`  

**`der_mi_indiana_michigan_power_aep`** — der_mi_indiana_michigan_power_aep  
status `done` · kind `page` · state `MI` · rows measured —  
endpoint: `https://aepgis.maps.arcgis.com/apps/dashboards/268618e992264d14a552f70a43c7afa3`  
loader: `migrate_registry_to_bq`  

**`derived:si-d5-vacancy/footprint-absence/IN`** — SI D5 vacancy (IN) -- parcel-grade footprint-absence derivation from held parcel + structure geometry  
status `BUILT+LOADED (IN) -- 967,366 no_structure_footprint rows measured in BigQuery over 3,631,384 testable parcels (26.64%); structure_without_addr_point=0` · kind `DERIVED` · state `IN` · rows measured 967366  
tables: `_d5_state_bbox, si_d5_addr_pts, si_d5_struct_pts, si_d5_vacancy_derived`  
**re-scrape:** `Pure in-warehouse derivation, no publisher contact. Semi-join of mat_parcel_geo (IN) against nat_usa_structures footprint centroids with ST_DWITHIN(10 m), computed POSITIVELY via INNER JOIN and differenced with EXCEPT DI`  
loader: `lane_d5_states_20260803`  

**`hca_aep_im_ev_eligibility`** — hca_aep_im_ev_eligibility  
status `done` · kind `arcgis` · state `IN,MI` · rows measured 1  
endpoint: `https://services.arcgis.com/ZnwBsu4Q8SvSAofV/arcgis/rest/services/Indiana_Michigan_EV_Eligibility/FeatureServer/0`  
tables: `hca_aep_im_ev_eligibility`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.load_arcgis_hc_bq --url "https://services.arcgis.com/ZnwBsu4Q8SvSAofV/arcgis/rest/services/Indiana_Michigan_EV_Eligibility/FeatureServer/0" --table hca_aep_im_ev_eligibility --refresh`  
loader: `ingest/register_fable5_rescrape_commands.py`  

**`hca_aep_im_ev_eligibility`** — hca_aep_im_ev_eligibility  
status `done` · kind `arcgis` · state `IN,MI` · rows measured 1  
endpoint: `https://services.arcgis.com/ZnwBsu4Q8SvSAofV/arcgis/rest/services/Indiana_Michigan_EV_Eligibility/FeatureServer/0`  
tables: `hca_aep_im_ev_eligibility`  
loader: `migrate_registry_to_bq`  

**`hca_aep_im_ev_map`** — hca_aep_im_ev_map  
status `done` · kind `arcgis` · state `IN,MI` · rows measured 1  
endpoint: `https://services.arcgis.com/ZnwBsu4Q8SvSAofV/arcgis/rest/services/Indiana_Michigan_EV_Map_WFL1/FeatureServer/0`  
tables: `hca_aep_im_ev_map`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.load_arcgis_hc_bq --url "https://services.arcgis.com/ZnwBsu4Q8SvSAofV/arcgis/rest/services/Indiana_Michigan_EV_Map_WFL1/FeatureServer/0" --table hca_aep_im_ev_map --refresh`  
loader: `ingest/register_fable5_rescrape_commands.py`  

**`hca_aep_im_ev_map`** — hca_aep_im_ev_map  
status `done` · kind `arcgis` · state `IN,MI` · rows measured 1  
endpoint: `https://services.arcgis.com/ZnwBsu4Q8SvSAofV/arcgis/rest/services/Indiana_Michigan_EV_Map_WFL1/FeatureServer/0`  
tables: `hca_aep_im_ev_map`  
loader: `migrate_registry_to_bq`  

**`inapp_1183196574`** — Evansville/Vanderburgh portal  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `Evansville open data`  
tables: `indiana_app.in_si_evansville_demolition_permits, in_si_evansville_foreclosures, in_si_evansville_taxsale, in_si_evansville_taxsale_transfers`  
loader: `indiana-app-session-20260815`  

**`inapp_1478845856`** — PJM RTEP Project Status & Cost Allocation  
status `done` · kind `None` · state `—` · rows measured —  
endpoint: `https://www.pjm.com/planning/m/project-construction (POST family incl. UpgradeDetails, UpgradeCostAllocations, GenerateExcelNUCRAProjectsAll)`  
tables: `indiana_app.in_pjm_rtep_upgrades, in_pjm_rtep_upgrade_details, in_pjm_rtep_cost_allocations, in_pjm_nucra_costs`  
loader: `indiana-app-session-20260815`  

**`inapp_1848041168`** — Midwestern Gas Transmission EBB (DTM Trellis)  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `Trellis public .do CSV`  
tables: `indiana_app.in_gas_capacity_midwestern`  
loader: `indiana-app-session-20260815`  

**`inapp_2222632007`** — IURC EDS docket system - anonymous companion REST  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `IURC advanced-search companion API (search, lists, per-case docs, anonymous SharePoint downloads)`  
tables: `indiana_app.in_iurc_dockets, in_grid_plans`  
loader: `indiana-app-session-20260815`  

**`inapp_2291730723`** — I&M/AEP hosting capacity map (PROD_MI_HC_GRID)  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `AGOL FeatureServer PROD_MI_HC_GRID`  
loader: `indiana-app-session-20260815`  

**`inapp_2551924229`** — PJM public GIS (gis.pjm.com) - queue points  
status `done` · kind `None` · state `—` · rows measured —  
endpoint: `https://gis.pjm.com (ArcGIS REST, previously uncataloged)`  
tables: `indiana_app.in_pjm_gis_queues`  
loader: `indiana-app-session-20260815`  

**`inapp_2833956263`** — Indiana MPH open data (CKAN)  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `hub.mph.in.gov CKAN API`  
loader: `indiana-app-session-20260815`  

**`inapp_3438777686`** — GDELT  
status `blocked` · kind `None` · state `IN` · rows measured —  
endpoint: `gdelt API`  
loader: `indiana-app-session-20260815`  

**`inapp_3538980013`** — MISO CartoVista POI heatmap  
status `blocked` · kind `None` · state `IN` · rows measured —  
endpoint: `https://cloud.cartovista.com/miso/ferc`  
loader: `indiana-app-session-20260815`  

**`inapp_3899289149`** — Fort Wayne / Allen County GIS  
status `blocked` · kind `None` · state `IN` · rows measured —  
endpoint: `maps.cityoffortwayne.org / acimap.us`  
loader: `indiana-app-session-20260815`  

**`inapp_4303697183`** — mycase.in.gov (court records)  
status `blocked` · kind `None` · state `IN` · rows measured —  
endpoint: `https://public.courts.in.gov / mycase.in.gov`  
loader: `indiana-app-session-20260815`  

**`inapp_4377878765`** — ANR / Northern Border / Crossroads EBBs (TC eConnects)  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `SSRS &rs:Format=CSV`  
tables: `indiana_app.in_gas_capacity_anr, in_gas_capacity_northern_border, in_gas_capacity_crossroads`  
loader: `indiana-app-session-20260815`  

**`inapp_499530815`** — Panhandle Eastern EBB (ET Messenger)  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `Messenger native CSV (gasDay param)`  
tables: `indiana_app.in_gas_capacity_panhandle_eastern`  
loader: `indiana-app-session-20260815`  

**`inapp_5059183828`** — Trunkline EBB (ET Messenger)  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `Messenger native CSV`  
tables: `indiana_app.in_gas_capacity_trunkline`  
loader: `indiana-app-session-20260815`  

**`inapp_5110135108`** — Indiana DWD WARN page  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `in.gov/dwd WARN listing`  
tables: `indiana_app.in_si_state_warn_notices, in_si_refresh_warn_notices`  
loader: `indiana-app-session-20260815`  

**`inapp_559912801`** — Indy/Marion open data (data.indy.gov + city ArcGIS)  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `Socrata + ArcGIS REST`  
tables: `indiana_app.in_si_indy_taxsale_parcels, in_si_indy_abandoned_vacant, in_si_indy_surplus_parcels`  
loader: `indiana-app-session-20260815`  

**`inapp_5856593259`** — MISO giqueue POI viewer - identity API  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `https://giqueue.misoenergy.org/POI/api/pois`  
tables: `indiana_app.in_miso_poi_identity`  
loader: `indiana-app-session-20260815`  

**`inapp_5957770580`** — MISO giqueue POI transfer analysis - bounded 300MW  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `https://giqueue.misoenergy.org/POI/api/poi_mf?poiName=<n>&pMaxValue=300`  
tables: `indiana_app.in_miso_poi_300mw, in_bus_headroom_300`  
loader: `indiana-app-session-20260815`  

**`inapp_6332459100`** — SRI tax-sale platform (Indiana)  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `sriservices/zeusauction public lists`  
tables: `indiana_app.in_si_refresh_sri_taxsale_in`  
loader: `indiana-app-session-20260815`  

**`inapp_6456593347`** — Duke Indiana / NIPSCO / AES Indiana / CenterPoint IN hosting-capacity maps  
status `blocked` · kind `None` · state `IN` · rows measured —  
loader: `indiana-app-session-20260815`  

**`inapp_7679664468`** — Bing News RSS  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `bing.com/news RSS`  
tables: `indiana_app.in_news_dc`  
loader: `indiana-app-session-20260815`  

**`inapp_7687539877`** — Google News RSS  
status `blocked` · kind `None` · state `IN` · rows measured —  
endpoint: `https://news.google.com/rss/search`  
loader: `indiana-app-session-20260815`  

**`inapp_7903260330`** — Texas Eastern EBB (Enbridge infopost)  
status `blocked` · kind `None` · state `IN` · rows measured —  
endpoint: `https://infopost.enbridge.com`  
loader: `indiana-app-session-20260815`  

**`inapp_8007185453`** — NGPL EBB (KM DART)  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `DART EXCEL export replicated`  
tables: `indiana_app.in_gas_capacity_ngpl`  
loader: `indiana-app-session-20260815`  

**`inapp_822052902`** — Data Center Watch quarterlies  
status `blocked` · kind `None` · state `IN` · rows measured —  
endpoint: `datacenterwatch /report`  
tables: `indiana_app.in_dc_actions`  
loader: `indiana-app-session-20260815`  

**`inapp_8582940784`** — South Bend open data (DCAT)  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `South Bend DCAT catalog`  
tables: `indiana_app.in_si_southbend_code_enforcement, in_si_southbend_demolition_orders, in_si_southbend_vacant_abandoned, in_si_southbend_continuous_enforcement, in_si_southbend_chronic_problem`  
loader: `indiana-app-session-20260815`  

**`inapp_863731809`** — Municode library - Indiana clients  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `library.municode.com public search`  
tables: `indiana_app.in_ordinances_dc`  
loader: `indiana-app-session-20260815`  

**`inapp_8676709877`** — Rockies Express EBB (Tallgrass)  
status `blocked` · kind `None` · state `IN` · rows measured —  
endpoint: `https://pipeline.tallgrassenergylp.com`  
loader: `indiana-app-session-20260815`  

**`inapp_8904137052`** — Texas Gas Transmission EBB (Boardwalk GasQuest)  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `GasQuest anonymous API`  
tables: `indiana_app.in_gas_capacity_texas_gas`  
loader: `indiana-app-session-20260815`  

**`inapp_909590806`** — American Legal codelibrary  
status `blocked` · kind `None` · state `IN` · rows measured —  
endpoint: `https://codelibrary.amlegal.com`  
loader: `indiana-app-session-20260815`  

**`inapp_9727329258`** — Vector Pipeline EBB (gasnom.com)  
status `done` · kind `None` · state `IN` · rows measured —  
endpoint: `gasnom.com vendor EBB HTML`  
tables: `indiana_app.in_gas_capacity_vector`  
loader: `indiana-app-session-20260815`  

**`openstates_bulk_IN`** — OpenStates bulk session CSV - Indiana  
status `BUILT+LOADED (66 distinct energy/large-load bills of 3423 bills published across 3 session archives; 10772 child records) - measured in BigQuery` · kind `file` · state `IN` · rows measured 66  
endpoint: `https://data.openstates.org/csv/latest/IN_2026_csv_34NNPgndSJPs7FknCjXeXu.zip`  
tables: `openstates_energy_bills_v2, openstates_energy_bill_abstracts, openstates_energy_bill_actions, openstates_energy_bill_sponsorships, openstates_energy_bill_sources, openstates_energy_bill_versions, openstates_energy_bill_votes, openstates_energy_bill_vote_people, openstates_bulk_session_coverage`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.load_openstates_deep_bq`  
loader: `weekend_20260802_lane_openstates`  

**`openstates_bulk_IN`** — OpenStates bulk session CSV - Indiana  
status `BUILT+LOADED (66 distinct energy/large-load bills of 3423 bills published across 3 session archives; 10772 child records) - measured in BigQuery` · kind `file` · state `IN` · rows measured 66  
endpoint: `https://data.openstates.org/csv/latest/IN_2026_csv_34NNPgndSJPs7FknCjXeXu.zip`  
tables: `openstates_energy_bills_v2, openstates_energy_bill_abstracts, openstates_energy_bill_actions, openstates_energy_bill_sponsorships, openstates_energy_bill_sources, openstates_energy_bill_versions, openstates_energy_bill_votes, openstates_energy_bill_vote_people, openstates_bulk_session_coverage`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.load_openstates_deep_bq`  
loader: `weekend_20260802_lane_openstates`  

**`openstates_bulk_IN`** — OpenStates bulk session CSV - Indiana  
status `BUILT+LOADED (66 distinct energy/large-load bills of 3423 bills published across 3 session archives; 10772 child records) - measured in BigQuery` · kind `file` · state `IN` · rows measured 66  
endpoint: `https://data.openstates.org/csv/latest/IN_2026_csv_34NNPgndSJPs7FknCjXeXu.zip`  
tables: `openstates_energy_bills_v2, openstates_energy_bill_abstracts, openstates_energy_bill_actions, openstates_energy_bill_sponsorships, openstates_energy_bill_sources, openstates_energy_bill_versions, openstates_energy_bill_votes, openstates_energy_bill_vote_people, openstates_bulk_session_coverage`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.load_openstates_deep_bq`  
loader: `weekend_20260802_lane_openstates`  

**`parcels:parcels_tn_marion_county`** — county Marion County; ~22,347 parcels (parcels_tn_marion_county)  
status `BUILT+LOADED — county parcel backfill 2026-08-02; held 22,347 rows vs expected 22,347.` · kind `arcgis` · state `—` · rows measured 22347  
endpoint: `https://services8.arcgis.com/wdIYdjK0MpdHUMcM/arcgis/rest/services/Parcels_Joined_372025/FeatureServer/0`  
tables: `parcels_tn_marion_county`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.national_scrape --manifest data/county_parcel_backfill_2026_07.json --only parcels_tn_marion_county`  
loader: `fable5_parcel_backfill`  

**`parcels_in`** — parcels_in  
status `done` · kind `arcgis` · state `IN` · rows measured —  
endpoint: `https://gisdata.in.gov/server/rest/services/Hosted/Parcel_Boundaries_of_Indiana_2022/FeatureServer/0`  
tables: `parcels_in`  
loader: `migrate_registry_to_bq`  

**`parcels_or_marion`** — parcels_or_marion  
status `done` · kind `arcgis` · state `—` · rows measured 1088187  
endpoint: `https://gis.co.marion.or.us/arcgis/rest/services/Public/Parcels/MapServer/0`  
tables: `parcels_or`  
loader: `migrate_registry_to_bq`  

**`recov_parcels_or_marion_county`** — Marion County, OR parcels (ArcGIS)  
status `ACQUIRED` · kind `arcgis_layer` · state `OR` · rows measured 115870  
endpoint: `https://gis.co.marion.or.us/arcgis/rest/services/Public/Parcels/MapServer/0`  
tables: `parcels_or_marion_county`  
**re-scrape:** `RE-SCRAPE COMMAND: cd energy-platform && export GOOGLE_APPLICATION_CREDENTIALS=C:/Users/ahend/bq-key.json && export PYTHONIOENCODING=utf-8 && python -m ingest.national_scrape --manifest data/parcels_or_la_mo_recovery.jso`  
loader: `parcel_recovery_lane`  

**`recov_parcels_or_marion_county`** — Marion County, OR parcels (ArcGIS)  
status `ACQUIRED` · kind `arcgis_layer` · state `OR` · rows measured 115870  
endpoint: `https://gis.co.marion.or.us/arcgis/rest/services/Public/Parcels/MapServer/0`  
tables: `parcels_or_marion_county`  
**re-scrape:** `RE-SCRAPE COMMAND: cd energy-platform && export GOOGLE_APPLICATION_CREDENTIALS=C:/Users/ahend/bq-key.json && export PYTHONIOENCODING=utf-8 && python -m ingest.national_scrape --manifest data/parcels_or_la_mo_recovery.jso`  
loader: `parcel_recovery_lane`  

**`recov_parcels_or_marion_county`** — Marion County, OR parcels (ArcGIS)  
status `ACQUIRED` · kind `arcgis_layer` · state `OR` · rows measured 115870  
endpoint: `https://gis.co.marion.or.us/arcgis/rest/services/Public/Parcels/MapServer/0`  
tables: `parcels_or_marion_county`  
**re-scrape:** `RE-SCRAPE COMMAND: cd energy-platform && export GOOGLE_APPLICATION_CREDENTIALS=C:/Users/ahend/bq-key.json && export PYTHONIOENCODING=utf-8 && python -m ingest.national_scrape --manifest data/parcels_or_la_mo_recovery.jso`  
loader: `parcel_recovery_lane`  

**`recov_parcels_or_marion_county`** — Marion County, OR parcels (ArcGIS)  
status `ACQUIRED` · kind `arcgis_layer` · state `OR` · rows measured 115870  
endpoint: `https://gis.co.marion.or.us/arcgis/rest/services/Public/Parcels/MapServer/0`  
tables: `parcels_or_marion_county`  
**re-scrape:** `RE-SCRAPE COMMAND: cd energy-platform && export GOOGLE_APPLICATION_CREDENTIALS=C:/Users/ahend/bq-key.json && export PYTHONIOENCODING=utf-8 && python -m ingest.national_scrape --manifest data/parcels_or_la_mo_recovery.jso`  
loader: `parcel_recovery_lane`  

**`si_absentee_owner`** — si_absentee_owner  
status `pending` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`si_bankruptcy`** — si_bankruptcy  
status `pending` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`si_brownfield`** — si_brownfield  
status `planned` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`si_cand_in_indy_code_enforcement`** — Indianapolis/Marion County Code Enforcement Violations and Investigations  
status `CATALOGED-not-built` · kind `arcgis` · state `IN` · rows measured —  
endpoint: `https://gis.indy.gov/server/rest/services/OpenData/OpenData_NonSpatial/MapServer/1`  
**re-scrape:** `probe: MapServer/1 /query returnCountOnly -> 910,483 (2026-08-02)`  
loader: `lane_si_breadth (Fable 5 weekend)`  

**`si_cand_in_indy_code_enforcement`** — Indianapolis/Marion County Code Enforcement Violations and Investigations  
status `CATALOGED-not-built` · kind `arcgis` · state `—` · rows measured —  
endpoint: `https://gis.indy.gov/server/rest/services/OpenData/OpenData_NonSpatial/MapServer/1`  
**re-scrape:** `probe: MapServer/1 /query returnCountOnly -> 910,483 (2026-08-02)`  
loader: `lane_si_breadth (Fable 5 weekend)`  

**`si_certified_sites`** — si_certified_sites  
status `pending` · kind `page` · state `US` · rows measured —  
endpoint: `https://siteselection.com/the-directory-of-due-diligence/`  
loader: `migrate_registry_to_bq`  

**`si_code_violation`** — si_code_violation  
status `pending` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`si_d11:IN`** — D11 IN - state SoS business/UCC registry  
status `BLOCKED - fee-gated ($9,500 + $500/mo (rejected))` · kind `HTTP` · state `IN` · rows measured —  
endpoint: `https://inbiz.in.gov/Inbiz/BulkDataServices/Index`  
**re-scrape:** `RE-SCRAPE COMMAND: none - fee-gated. If a free route ever opens: python -m ingest.load_state_bulk_file_bq --key in_entity --url <bulk file URL>`  
loader: `sos_registry_lane_20260803`  

**`si_d19_warn_in`** — WARN notices - IN  
status `BUILT+LOADED (1220 rows measured in BigQuery for source_state=IN; 1039 D19 rows in si_signals)` · kind `HTTP_FILE` · state `IN` · rows measured 1220  
endpoint: `https://www.in.gov/dwd/warn-notices/current-warn-notices/`  
tables: `warn_notices`  
**re-scrape:** `RE-SCRAPE COMMAND: warn-scraper --data-dir <d> --cache-dir <c> in && python -m ingest.load_warn_state_bq bln --dir <d> --states in`  
loader: `lane_d19_warn_completion`  

**`si_d1_sri_taxsale_listings`** — SRI Services - active tax-sale property listings (multi-state vendor aggregator)  
status `BUILT+LOADED (217226 rows measured in BigQuery). AL: 0 rows across 0 of 1 roster counties | CO: 34186 rows across 17 of 19 roster counties | FL: 13257 rows across 1 of 1 roster counties | IN: 81975 rows across 80 of 91 roster counties | LA: 87644 rows across 30 of 47 roster counties | MI: 164 rows across 2 of 2 roster counties | TN SKIPPED (owned by the TN lane)` · kind `json_api_public_embedded_key` · state `IN (+active AL/CO/FL/LA/MI as served; TN excluded)` · rows measured 217226  
endpoint: `https://sriservicesusermgmtprod.azurewebsites.net/api/property/carddetail`  
tables: `si_d1_sri_taxsale_listings`  
**re-scrape:** `x-api-key from the publisher's own public JS bundle (served to every anonymous visitor, no account); GET /states + /countylistbystate, POST /carddetail per county with recordCount=50000. Statewide county='' times out - M`  
loader: `d1_acquisition_lane_20260809`  

**`si_d1_sri_taxsale_listings`** — SRI Services - active tax-sale property listings (multi-state vendor aggregator)  
status `BUILT+LOADED (217226 rows measured in BigQuery). AL: 0 rows across 0 of 1 roster counties | CO: 34186 rows across 17 of 19 roster counties | FL: 13257 rows across 1 of 1 roster counties | IN: 81975 rows across 80 of 91 roster counties | LA: 87644 rows across 30 of 47 roster counties | MI: 164 rows across 2 of 2 roster counties | TN SKIPPED (owned by the TN lane)` · kind `json_api_public_embedded_key` · state `IN (+active AL/CO/FL/LA/MI as served; TN excluded)` · rows measured 217226  
endpoint: `https://sriservicesusermgmtprod.azurewebsites.net/api/property/carddetail`  
tables: `si_d1_sri_taxsale_listings`  
**re-scrape:** `x-api-key from the publisher's own public JS bundle (served to every anonymous visitor, no account); GET /states + /countylistbystate, POST /carddetail per county with recordCount=50000. Statewide county='' times out - M`  
loader: `d1_acquisition_lane_20260809`  

**`si_d26_in_ibtr_determinations`** — Indiana Board of Tax Review determinations (DevExtreme API)  
status `BUILT+LOADED` · kind `rest` · state `IN` · rows measured 10071  
endpoint: `https://www.in.gov/ibtr/poplar/api/search/getsearchdata/determinations`  
tables: `appeals_in_ibtr_determinations`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.load_in_ibtr_appeals_bq  # LOADER ADDED 2026-08-09. POST-only (do not GET-probe). Publisher currently ignores skip/take and returns the whole corpus in one POST; loader tolerates both`  
loader: `d26_lane_20260809`  

**`si_d26_in_ibtr_determinations`** — IN Board of Tax Review — determinations JSON API  
status `CATALOGED-not-built` · kind `rest` · state `IN` · rows measured —  
endpoint: `https://www.in.gov/ibtr/poplar/api/search/getsearchdata/determinations`  
**re-scrape:** `RE-SCRAPE COMMAND: POST https://www.in.gov/ibtr/poplar/api/search/getsearchdata/determinations with a DevExtreme loadOptions body {skip, take, requireTotalCount:true, sort} — NO auth, NO cookie, NO token. Page on skip/ta`  
loader: `endpoint_registration_lane_20260803`  

**`si_d27:IN`** — D27 IN - state SoS business/UCC registry  
status `BLOCKED - fee-gated` · kind `HTTP` · state `IN` · rows measured —  
endpoint: `https://inbiz.in.gov/Inbiz/BulkDataServices/Index`  
**re-scrape:** `RE-SCRAPE COMMAND: none - fee-gated. If a free route ever opens: python -m ingest.load_state_bulk_file_bq --key in_ucc --url <bulk file URL>`  
loader: `sos_registry_lane_20260803`  

**`si_entity_dissolution`** — si_entity_dissolution  
status `pending` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`si_exit_intent_rezoning`** — si_exit_intent_rezoning  
status `pending` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`si_foreclosure_lispendens`** — si_foreclosure_lispendens  
status `pending` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`si_gov_surplus`** — si_gov_surplus  
status `pending` · kind `page` · state `US` · rows measured —  
endpoint: `https://catalog.data.gov/dataset?q=federal+real+property+public+data+set`  
loader: `migrate_registry_to_bq`  

**`si_listings_marketplaces`** — si_listings_marketplaces  
status `pending` · kind `page` · state `US` · rows measured —  
endpoint: `https://www.crexi.com/properties`  
loader: `migrate_registry_to_bq`  

**`si_loan_maturity`** — si_loan_maturity  
status `pending` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`si_owner_type_multiplier`** — si_owner_type_multiplier  
status `planned` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`si_parcel_universe`** — si_parcel_universe  
status `planned` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`si_skip_trace_contact`** — si_skip_trace_contact  
status `planned` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`si_state_sites_marketed`** — si_state_sites_marketed  
status `pending` · kind `page` · state `US` · rows measured —  
endpoint: `https://unitedstates.zoomprospector.com/`  
loader: `migrate_registry_to_bq`  

**`si_substation_power_parity`** — si_substation_power_parity  
status `planned` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`si_tax_delinquent`** — si_tax_delinquent  
status `pending` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`si_tax_sale`** — si_tax_sale  
status `pending` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`si_underutilization`** — si_underutilization  
status `pending` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`si_vacant_land`** — si_vacant_land  
status `pending` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`si_warn_closure`** — si_warn_closure  
status `pending` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`si_wire2::si_d17_in_iocs_court_year`** — si_signals wiring wave 2: si_d17_in_iocs_court_year -> D17_commercial_eviction  
status `ACTIVE` · kind `bigquery_table` · state `—` · rows measured 370  
endpoint: `bq://energy-platfrom.energy.si_d17_in_iocs_court_year`  
tables: `si_signals`  
**re-scrape:** `bq_sql_transform`  
loader: `ingest/build_si_wire_bq.py --apply (wave 2, 2026-08-03)`  

**`si_year_built`** — si_year_built  
status `pending` · kind `none` · state `—` · rows measured 0  
tables: `master_seller_intent_<market>`  
loader: `migrate_registry_to_bq`  

**`swept:https://gis.indy.gov/server/rest/services/opendata/opendata_planningzoning/mapserver/8`** — gis.indy.gov (recovered from arcgis_attr_datasets.json)  
status `BUILT+LOADED — linked to producing endpoint via loader manifest arcgis_attr_datasets.json, live-verified 2026-08-02` · kind `arcgis` · state `—` · rows measured 13414  
endpoint: `https://gis.indy.gov/server/rest/services/OpenData/OpenData_PlanningZoning/MapServer/8`  
tables: `agis_indy_rezoning`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.load_arcgis_attr_bq --manifest data/arcgis_attr_datasets.json --only indy_rezoning`  
loader: `link_agis_endpoints`  

**`swept:https://gis.indy.gov/server/rest/services/surplusproperties/surpluspropertiesfeatures2/mapserver/7`** — gis.indy.gov (recovered from arcgis_attr_datasets.json)  
status `BUILT+LOADED — linked to producing endpoint via loader manifest arcgis_attr_datasets.json, live-verified 2026-08-02` · kind `arcgis` · state `—` · rows measured 595  
endpoint: `https://gis.indy.gov/server/rest/services/SurplusProperties/SurplusPropertiesFeatures2/MapServer/7`  
tables: `agis_indy_landbank_surplus`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.load_arcgis_attr_bq --manifest data/arcgis_attr_datasets.json --only indy_landbank_surplus`  
loader: `link_agis_endpoints`  

**`swept:https://gis.indy.gov/server/rest/services/taxsaleviewer/taxsaleparcels_buildingblocks/mapserver/0`** — gis.indy.gov (recovered from arcgis_attr_datasets.json)  
status `BUILT+LOADED — linked to producing endpoint via loader manifest arcgis_attr_datasets.json, live-verified 2026-08-02` · kind `arcgis` · state `—` · rows measured 62368  
endpoint: `https://gis.indy.gov/server/rest/services/TaxSaleViewer/TaxSaleParcels_BuildingBlocks/MapServer/0`  
tables: `agis_indy_taxsale`  
**re-scrape:** `RE-SCRAPE COMMAND: python -m ingest.load_arcgis_attr_bq --manifest data/arcgis_attr_datasets.json --only indy_taxsale`  
loader: `link_agis_endpoints`  

**`swept:https://services8.arcgis.com/vpef77dvopjhhuuq/arcgis/rest/services/marion_sequatchie_parcelsforweb/featureserver/0`** — Marion_Sequatchie_ParcelsForWeb (recovered from county_parcel_discovery_TN.json)  
status `SOURCE-MOVED/GONE - AGOL 400 Invalid URL (service not found), confirmed 2x 2026-08-02` · kind `arcgis` · state `—` · rows measured —  
endpoint: `https://services8.arcgis.com/vpef77DvopJHHuuQ/ArcGIS/rest/services/Marion_Sequatchie_ParcelsForWeb/FeatureServer/0`  
loader: `lane_endpoint_residue_20260802`  

**`swept:https://services8.arcgis.com/wdiydjk0mpdhumcm/arcgis/rest/services/marionparcels10042021/featureserver/0`** — MarionParcels10042021 (recovered from county_parcel_discovery_TN.json)  
status `SOURCE-MOVED/GONE - AGOL 400 Invalid URL (service not found), confirmed 2x 2026-08-02` · kind `arcgis` · state `—` · rows measured —  
endpoint: `https://services8.arcgis.com/wdIYdjK0MpdHUMcM/arcgis/rest/services/MarionParcels10042021/FeatureServer/0`  
loader: `lane_endpoint_residue_20260802`  

**`swept:https://smpesri.scdot.org/arcgis/rest/services/gismapping/sc_parcels/mapserver/32`** — smpesri.scdot.org (recovered from county_parcel_backfill_2026_07.json)  
status `RECOVERED-UNVALIDATED - endpoint found in internal material (full-tree sweep 2026-08-01); liveness NOT yet proven` · kind `arcgis` · state `—` · rows measured —  
endpoint: `https://smpesri.scdot.org/arcgis/rest/services/GISMapping/SC_Parcels/MapServer/32`  
tables: `parcels_sc_marion_county`  
loader: `registry_hygiene_20260802`  


---

## AUDIT — this workstream's own 31 registrations are NOT re-runnable

The platform's own rows carry everything needed to re-pull. Compare `countysi_b:D12:IN:indy_marion_code_enforcement`: endpoint `https://gis.indy.gov/server/rest/services/OpenData/OpenData_NonSpatial/MapServer/1`, `endpoint_kind='rest'`, a loader, and an `acquisition_method` holding the literal re-scrape command.

Ours do not. Measured across the 31 rows appended by `indiana-app-session-20260815`:

| field | populated |
|---|---:|
| endpoint (any text) | 30 / 31 |
| endpoint is an actual URL | **10 / 31** |
| `endpoint_kind` | **0 / 31** |
| `acquisition_method` (the re-scrape command) | **0 / 31** |
| `object_names` | 20 / 31 |
| notes | 26 / 31 |

So several endpoints are PROSE, not addresses — 'Evansville open data', 'Socrata + ArcGIS REST', 'Messenger native CSV'. A future session cannot re-run those, which is precisely what the registry exists to prevent. **Backfilling `endpoint_kind` and `acquisition_method` for these 31 is a prerequisite for relaunching the SI loaders**, and must be done by APPENDING corrected rows — `registry_sources` is append-only (D25), never updated in place.

| source_id | endpoint as recorded | re-runnable? |
|---|---|---|
| `inapp_1183196574` | Evansville open data | **NO — prose, not an address** |
| `inapp_1478845856` | https://www.pjm.com/planning/m/project-construction (POST family | yes |
| `inapp_1848041168` | Trellis public .do CSV | **NO — prose, not an address** |
| `inapp_2222632007` | IURC advanced-search companion API (search, lists, per-case docs | **NO — prose, not an address** |
| `inapp_2291730723` | AGOL FeatureServer PROD_MI_HC_GRID | **NO — prose, not an address** |
| `inapp_2551924229` | https://gis.pjm.com (ArcGIS REST, previously uncataloged) | yes |
| `inapp_2833956263` | hub.mph.in.gov CKAN API | **NO — prose, not an address** |
| `inapp_3438777686` | gdelt API | **NO — prose, not an address** |
| `inapp_3538980013` | https://cloud.cartovista.com/miso/ferc | yes |
| `inapp_3899289149` | maps.cityoffortwayne.org / acimap.us | **NO — prose, not an address** |
| `inapp_4303697183` | https://public.courts.in.gov / mycase.in.gov | yes |
| `inapp_4377878765` | SSRS &rs:Format=CSV | **NO — prose, not an address** |
| `inapp_499530815` | Messenger native CSV (gasDay param) | **NO — prose, not an address** |
| `inapp_5059183828` | Messenger native CSV | **NO — prose, not an address** |
| `inapp_5110135108` | in.gov/dwd WARN listing | **NO — prose, not an address** |
| `inapp_559912801` | Socrata + ArcGIS REST | **NO — prose, not an address** |
| `inapp_5856593259` | https://giqueue.misoenergy.org/POI/api/pois | yes |
| `inapp_5957770580` | https://giqueue.misoenergy.org/POI/api/poi_mf?poiName=<n>&pMaxVa | yes |
| `inapp_6332459100` | sriservices/zeusauction public lists | **NO — prose, not an address** |
| `inapp_6456593347` | (none) | **NO — prose, not an address** |
| `inapp_7679664468` | bing.com/news RSS | **NO — prose, not an address** |
| `inapp_7687539877` | https://news.google.com/rss/search | yes |
| `inapp_7903260330` | https://infopost.enbridge.com | yes |
| `inapp_8007185453` | DART EXCEL export replicated | **NO — prose, not an address** |
| `inapp_822052902` | datacenterwatch /report | **NO — prose, not an address** |
| `inapp_8582940784` | South Bend DCAT catalog | **NO — prose, not an address** |
| `inapp_863731809` | library.municode.com public search | **NO — prose, not an address** |
| `inapp_8676709877` | https://pipeline.tallgrassenergylp.com | yes |
| `inapp_8904137052` | GasQuest anonymous API | **NO — prose, not an address** |
| `inapp_909590806` | https://codelibrary.amlegal.com | yes |
| `inapp_9727329258` | gasnom.com vendor EBB HTML | **NO — prose, not an address** |

