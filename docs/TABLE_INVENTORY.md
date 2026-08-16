# TABLE INVENTORY — `energy-platfrom.indiana_app`

**GENERATED 2026-08-16 by `scripts/build_table_inventory.py`. Do not hand-edit.**

256 objects. This exists because this project has repeatedly asserted it did not hold data that was sitting in the warehouse. It lists not just what each object IS but what it CARRIES — owner fields, real dates, status vocabularies, coordinates and parcel keys — because every one of those misses was a column nobody looked at.

**How to read the flags:** `OWNER` = carries owner name or mailing address (D9/D18 input). `GEO` = placeable without a bridge. `KEY` = can join to the parcel spine. `DATE` = has a date-bearing column. `STATUS` = low-cardinality vocabulary, i.e. **a possible hidden signal split** — this is how D4 was found hiding inside D1.

## SELLER-INTENT: the flag and its inputs

| object | rows | flags | what it is |
|---|---:|---|---|
| `in_si_signals` | 1,818,158 | **OWNER** KEY DATE | energy.si_signals |
| `in_si_parcel_signals_v2` | 116,660 | KEY DATE **STATUS** | indiana_app.in_si_signals + in_si_signals_parcel_dated + in_si_southbend_* + in_si_evansville_*  |
| `in_si_sites_flags_v2` | 102,444 | KEY DATE **STATUS** | indiana_app.in_si_parcel_signals_v2 |
| `in_si_signals_parcel_dated` | 46,790 | KEY DATE | energy-platfrom.indiana_app.in_si_signals + energy-platfrom.indiana_app.in_si_address_parcel_bri |
| `in_si_owner_signals` | 2,174 | KEY DATE | indiana_app.in_si_d11_admitted + in_si_d27_admitted + in_si_signals(D19_warn) |
| `in_si_owner_signals_county` | 67 | DATE | indiana_app.in_si_owner_signals |
| `in_si_signal_coverage` | 23 | KEY DATE | indiana_app.in_si_signals + in_si_parcel_signals_v2 |

## SELLER-INTENT: acquired source corpora

| object | rows | flags | what it is |
|---|---:|---|---|
| `in_si_d5_vacant_land_NOT_A_SIGNAL` | 945,896 | KEY | indiana_app.in_si_signals WHERE source_id='si_d5_vacancy_derived' |
| `in_si_refresh_indy_code_enforcement` | 910,483 | **OWNER** DATE **STATUS** | gis.indy.gov OpenData_NonSpatial/MapServer/1 (Indianapolis/Marion County code enforcement) |
| `in_si_refresh_sri_taxsale_in` | 83,547 | GEO KEY DATE **STATUS** | sriservicesusermgmtprod.azurewebsites.net (SRI Services tax-sale platform, IN slice only) |
| `in_si_indy_taxsale_parcels` | 62,368 | KEY DATE **STATUS** | https://gis.indy.gov/server/rest/services/TaxSaleViewer/TaxSaleParcels_BuildingBlocks/MapServer/ |
| `in_si_d22_echo_facilities` | 58,021 | GEO DATE **STATUS** | https://echo.epa.gov/files/echodownloads/echo_exporter.zip |
| `in_si_d22_echo_indiana` | 58,003 | GEO DATE **STATUS** | indiana_app.in_si_d22_echo_facilities (https://echo.epa.gov/files/echodownloads/echo_exporter.zi |
| `in_si_address_parcel_bridge` | 51,309 | GEO KEY DATE | energy-platfrom.energy.mat_si_address_location + energy-platfrom.indiana_app.in_sites |
| `in_si_indy_code_placed` | 46,411 | **OWNER** KEY DATE **STATUS** | indiana_app.in_si_refresh_indy_code_enforcement + in_marion_address_crosswalk |
| `in_si_d22_parcel_join` | 34,116 | GEO KEY DATE **STATUS** | indiana_app.in_si_d22_echo_indiana + in_sites |
| `in_si_sri_placed` | 31,228 | GEO KEY DATE **STATUS** | energy-platfrom.indiana_app.in_si_refresh_sri_taxsale_in + in_sites |
| `in_si_d22_idem_enforcement` | 22,565 | DATE **STATUS** | https://oe.idem.in.gov/idem_oe_order |
| `in_si_southbend_code_enforcement` | 20,414 | KEY DATE **STATUS** | https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services/Code_Enforcement_Cases/Featur |
| `in_si_refresh_ibtr_appeals` | 10,152 | KEY DATE **STATUS** | www.in.gov IBTR DevExtreme determinations API |
| `in_si_d5_abandoned_buildings` | 7,174 | KEY **STATUS** | indiana_app.in_si_indy_abandoned_vacant + in_si_southbend_vacant_abandoned + _chronic_problem |
| `in_si_indy_abandoned_vacant` | 7,120 | KEY DATE **STATUS** | https://gis.indy.gov/server/rest/services/OpenData/OpenData_Infrastructure/MapServer/2 |
| `in_si_indy_abandoned_vacant_spatial` | 7,120 | GEO KEY DATE **STATUS** | https://gis.indy.gov/server/rest/services/MapIndy/MapIndyProperty/MapServer/11 |
| `in_si_marion_route_check` | 7,120 | KEY DATE **STATUS** | indiana_app.in_marion_parcel_crosswalk + in_si_indy_abandoned_vacant_spatial + in_sites |
| `in_si_refresh_iocs_eviction` | 6,519 | DATE | www.in.gov/courts/iocs (Indiana Office of Court Services statewide case statistics XLSX) |
| `in_si_evansville_foreclosures` | 5,758 | **OWNER** KEY DATE **STATUS** | https://maps.evansvillegis.com/arcgis_server/rest/services/ASSESSOR/FORECLOSURES/MapServer |
| `in_si_ibtr_placed` | 5,438 | KEY DATE **STATUS** | energy-platfrom.indiana_app.in_si_refresh_ibtr_appeals + in_sites |
| `in_si_evansville_demolition_permits` | 4,190 | **OWNER** KEY DATE **STATUS** | https://maps.evansvillegis.com/arcgis_server/rest/services/BC/BUILDING_COMMISSION_PERMITS/MapSer |
| `in_si_candidates` | 4,170 | **OWNER** KEY DATE | in_si_evansville_demolition_permits x in_sites |
| `in_si_evansville_taxsale` | 3,202 | **OWNER** KEY DATE **STATUS** | https://maps.evansvillegis.com/arcgis_server/rest/services/SITE_PROJECTS/TAX_SALE/MapServer |
| `in_si_d11_entity_dissolution` | 2,129 | DATE **STATUS** | energy.si_d11_entity_dissolution |
| `in_si_evansville_landbank` | 1,660 | **OWNER** KEY DATE **STATUS** | https://services1.arcgis.com/iZyBOluseC8ffQc2/arcgis/rest/services/('Landbank_January2023', '202 |
| `in_si_refresh_brownfield_epa_in` | 1,483 | GEO DATE **STATUS** | EPA RE-Powering Mapper Sites 2022 ArcGIS FeatureServer, State='IN' slice of a national layer |
| `in_si_refresh_warn_notices` | 1,220 | DATE **STATUS** | www.in.gov/dwd/warn-notices/current-warn-notices/ (Indiana DWD WARN notices, full history table) |
| `in_si_state_warn_notices` | 1,220 | DATE **STATUS** | https://www.in.gov/dwd/warn-notices/current-warn-notices/ |
| `in_si_d11_admitted` | 983 | DATE **STATUS** | indiana_app.in_si_d11_entity_dissolution |
| `in_si_evansville_taxsale_transfers` | 941 | **OWNER** KEY DATE **STATUS** | https://maps.evansvillegis.com/arcgis_server/rest/services/ASSESSOR/TAX_SALES/MapServer |
| `in_si_d25_stb_abandonment_state` | 874 | DATE **STATUS** | energy.si_d25_stb_abandonment_state |
| `in_si_indy_surplus_parcels` | 595 | KEY DATE | https://gis.indy.gov/server/rest/services/SurplusProperties/SurplusPropertiesFeatures2/MapServer |
| `in_si_lane_d_enrichment` | 509 |  | six in_si_refresh_* tables |
| `in_si_southbend_continuous_enforcement` | 241 | KEY DATE **STATUS** | https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services/Continuous_Enforcement/Featur |
| `in_si_d27_admitted` | 156 | DATE **STATUS** | indiana_app.in_si_d27_ucc_lapse_v2 |
| `in_si_d27_ucc_lapse_v2` | 156 | DATE **STATUS** | energy.si_d27_ucc_lapse_v2 |
| `in_si_d25_admitted` | 127 | DATE **STATUS** | indiana_app.in_si_d25_stb_abandonment_state |
| `in_si_d22_county_rollup` | 112 | DATE | indiana_app.in_si_d22_echo_indiana |
| `in_si_southbend_demolition_orders` | 80 | DATE | https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services/Active_Demolition_Orders/Feat |
| `in_si_southbend_vacant_abandoned` | 47 | KEY DATE **STATUS** | https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services/AllVacantandAbandonedProperti |
| `in_si_southbend_chronic_problem` | 7 | DATE | https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services/Chronic_Problem_Properties_Li |

## PARCEL SPINE & capability gates

| object | rows | flags | what it is |
|---|---:|---|---|
| `in_sites` | 3,553,194 | GEO KEY DATE **STATUS** | energy.vw_parcel_sites (all parcels, SI-agnostic) |
| `in_sites_county` | 3,553,186 | KEY | in_sites x geo_us_boundaries.counties, greatest-intersection |
| `in_site_gates` | 1,200,923 | KEY **STATUS** | in_sites x in_flood/in_wetlands/in_padus/in_bonus_geo |
| `in_parcel_attrs` | 1,143,873 | KEY DATE | energy.mat_parcel_attrs x in_sites |
| `in_marion_address_crosswalk` | 465,050 | GEO KEY DATE **STATUS** | https://gis.indy.gov/server/rest/services/sde_Addressing/sde_Addressing/MapServer/0 |
| `in_marion_parcel_crosswalk` | 347,049 | **OWNER** KEY DATE **STATUS** | https://gis.indy.gov/server/rest/services/sde_Parcel/sde_Parcel/MapServer/5 |
| `in_county_rollup` | 92 | KEY **STATUS** | in_sites + in_sites_county |

## DATA CENTRES & competitive landscape

| object | rows | flags | what it is |
|---|---:|---|---|
| `in_cloudscene_crosscheck` | 260 | GEO | energy.data_centers_cloudscene |
| `in_data_centers_located` | 249 | GEO KEY | indiana_app.in_data_centers_deduped x energy.data_centers_datacentermap_coords |
| `in_data_centers_all` | 244 | GEO | data_centers + baxtel + wikidata + datacentermap(+coords slug-join) |
| `in_data_centers_deduped` | 242 | GEO | indiana_app.in_data_centers_all |
| `in_data_centers_datacentermap` | 157 |  | energy.data_centers_datacentermap |
| `in_dc_actions_county_v2` | 107 | DATE **STATUS** | Indiana county/municipal government websites via web-search index + robots-checked official fetc |
| `in_dc_actions_coverage_v2` | 92 | DATE **STATUS** | web-search-engine layer over all 92 Indiana county websites |
| `in_dc_actions` | 79 | DATE **STATUS** | CORRECTION note (no data change) |
| `in_data_centers_peeringdb` | 20 | GEO | energy.data_centers_peeringdb |
| `in_peeringdb_facilities` | 19 | GEO | energy.peeringdb_facilities |
| `in_dc_actions_nw_first_pass` | 17 | DATE **STATUS** | NW Indiana county websites, first sweep pass — recovered from the agent transcript |
| `in_data_centers` | 13 | GEO **STATUS** | energy.data_centers |
| `in_dc_colo_resolved` | 8 | GEO KEY DATE **STATUS** | operator sites (live + Wayback) + PeeringDB public API + operator press releases + baxtel pages  |
| `in_dc_eei_tariffs` | 5 | **STATUS** | energy.dc_eei_tariffs |
| `in_dc_docket_tracker` | 1 | DATE | energy.dc_docket_tracker |
| `in_data_centers_cloudscene` | 0 |  | energy.data_centers_cloudscene |

## ORDINANCES & county posture

| object | rows | flags | what it is |
|---|---:|---|---|
| `in_ordinances_amlegal_coverage_v2` | 230 | DATE **STATUS** | https://codelibrary.amlegal.com/api/client-version/ |
| `in_ordinances_amlegal_v3` | 230 | DATE **STATUS** | https://codelibrary.amlegal.com + https://www.iccsafe.org/about/terms-of-use/ |
| `in_ordinances_dc_v2` | 153 | DATE **STATUS** | https://api.municode.com/search ; https://codelibrary.amlegal.com/api/clients-search/ |
| `in_ordinances_dc_v2_triage` | 115 | DATE **STATUS** | energy-platfrom.indiana_app.in_ordinances_dc_v2 (not modified) |
| `in_ordinances_dc_coverage_v2` | 45 | **STATUS** | https://api.municode.com/search ; https://codelibrary.amlegal.com/api/clients-search/ |
| `in_ordinances_amlegal_v3_probes` | 11 | DATE **STATUS** | https://codelibrary.amlegal.com, https://www.amlegal.com, https://www.iccsafe.org/about/terms-of |
| `in_ordinances_dc_county_sites_v2` | 6 | DATE **STATUS** | Indiana county government websites |
| `in_ordinances_dc` | 4 | DATE | https://api.municode.com/search (public JSON API of library.municode.com) |
| `in_ordinances_publisher_inventory_v2` | 3 | DATE **STATUS** | https://api.municode.com/search ; https://codelibrary.amlegal.com/api/clients-search/ |
| `in_commission_posture` | 1 |  | energy.commission_posture |

## GRID: queues, buses, headroom, RTEP

| object | rows | flags | what it is |
|---|---:|---|---|
| `in_pjm_queuescope_aep` | 303,671 | **OWNER** DATE **STATUS** | energy.pjm_queuescope_results (AEP = the I&M sliver) |
| `in_miso_poi_300mw` | 40,007 | GEO | giqueue.misoenergy.org POI/api/poi_mf?pMaxValue=300 |
| `in_pjm_rtep_upgrades` | 15,443 | **OWNER** DATE **STATUS** | PJM Project Status & Cost Allocation (RTEP upgrades) - public grid export at https://www.pjm.com |
| `in_miso_poi_identity` | 12,845 | GEO DATE | MISO giqueue legacy POI viewer https://giqueue.misoenergy.org/POI/api/pois (via held energy.miso |
| `in_bus_headroom_miso` | 11,820 | GEO DATE **STATUS** | energy.miso_poi_monitored_facilities x indiana_app.in_miso_poi_identity |
| `in_pjm_gis_queues` | 6,923 | GEO DATE | PJM public GIS queue-point layer https://gis.pjm.com/arcgis/rest/services/Renewables/Queue/MapSe |
| `in_substations` | 3,858 | GEO DATE **STATUS** | energy.mat_grid_substations (HIFLD+OSM deduped) |
| `in_transmission_union` | 3,737 | **OWNER** GEO **STATUS** | indiana_app.in_transmission_lines + in_osm_power_lines (>=100 kV) |
| `in_transmission_lines` | 2,623 | **OWNER** GEO DATE **STATUS** | energy.transmission_lines (HIFLD), spatial clip |
| `in_rto_expansion` | 2,034 | **OWNER** DATE **STATUS** | MISO MTEP (held energy.txexp_miso_mtep_appendix_a_in_service/_status/_under_evaluation, cdn.miso |
| `in_pjm_bus_locations_candidate` | 1,475 | GEO DATE | DERIVED ladder over: indiana_app.in_pjm_gis_queues (PJM-published points), energy.nat_substation |
| `in_pjm_bus_withdrawal` | 1,475 |  | in_pjm_queuescope_aep |
| `in_rtep_bus_join` | 1,229 | GEO DATE **STATUS** | energy-platfrom.indiana_app.in_pjm_rtep_upgrade_details + in_substations + in_pjm_bus_locations_ |
| `in_queue` | 948 | DATE **STATUS** | energy.interconnection_queue |
| `in_pjm_rtep_upgrade_details` | 932 | DATE **STATUS** | PJM RTEP upgrade detail fragments (public GET, no login) https://www.pjm.com/m/ProjectConst/Upgr |
| `in_bus_headroom_300` | 642 |  | in_miso_poi_300mw |
| `in_grid_plans` | 618 | DATE **STATUS** | IURC IRP page (filtered) + TDSIC dockets 45894/45647/45557 pass-2 PDFs |
| `in_iurc_dockets` | 516 | DATE **STATUS** | https://iurc.portal.in.gov/advanced-search/ via companion API https://zus1iurcprodd365companiona |
| `in_queue_miso` | 456 | **OWNER** DATE **STATUS** | energy.queue_miso |
| `in_queue_miso_extras` | 456 | **OWNER** DATE **STATUS** | energy.queue_miso |
| `in_pjm_rtep_cost_allocations` | 375 | DATE **STATUS** | PJM RTEP per-upgrade cost-allocation splits (public GET, no login) https://www.pjm.com/m/Project |
| `in_txexp_miso_mtep_appendix_a_status` | 328 | **OWNER** DATE **STATUS** | energy.txexp_miso_mtep_appendix_a_status |
| `in_territories` | 145 | GEO DATE **STATUS** | energy.vw_grid_territories |
| `in_queue_counties` | 87 | GEO **STATUS** | energy.vw_grid_queue_counties |
| `in_rtep_bus_summary` | 79 | GEO DATE **STATUS** | energy-platfrom.indiana_app.in_rtep_bus_join |
| `in_pjm_nucra_costs` | 55 | **OWNER** DATE **STATUS** | PJM NUCRA (Network Upgrade Cost Responsibility Allocation) - public XLSX export of the cycle-ser |
| `in_miso_poi` | 0 | DATE | energy.miso_poi_monitored_facilities (points in IN polygon) |

## GENERATION & emissions

| object | rows | flags | what it is |
|---|---:|---|---|
| `in_cems_monthly` | 50,132 |  | energy.cems_hourly aggregated to plant-unit-month |
| `in_elec_power_operational` | 15,178 | **STATUS** | energy.elec_power_operational |
| `in_eia860_generators` | 12,479 | GEO KEY DATE **STATUS** | energy.eia860_generators |
| `in_operating_generators` | 11,795 | GEO KEY DATE **STATUS** | energy.operating_generators |
| `in_eia861_territory` | 10,928 | KEY DATE | energy.eia861_service_territory |
| `in_ghgrp_emissions` | 9,310 | DATE | energy.ghgrp_emissions x in_ghgrp_facilities |
| `in_ghgrp_facilities` | 3,391 | GEO DATE **STATUS** | energy.ghgrp_facilities |
| `in_ghgrp_emitter_facilities` | 2,882 | GEO DATE | energy.ghgrp_emitter_facilities |
| `in_eia_plants` | 2,675 | **OWNER** GEO DATE **STATUS** | energy.eia_plants |
| `in_wind_turbines` | 1,652 | DATE | energy.wind_turbines |
| `in_eia923_fuel_receipts_costs` | 880 | DATE **STATUS** | energy.eia923_fuel_receipts_costs |
| `in_eia861_demand_response` | 660 | DATE **STATUS** | energy.eia861_demand_response |
| `in_eia860m_generators` | 648 | GEO DATE **STATUS** | energy.eia860m_generators |
| `in_generation_union` | 283 | GEO DATE | indiana_app.in_eia_plants + in_power_plants |
| `in_power_plants` | 208 | GEO | energy.power_plants |
| `in_solar_pv_facilities` | 114 | DATE **STATUS** | energy.solar_pv_facilities |
| `in_solar_potential` | 92 | GEO | energy.solar_potential |
| `in_eia861_sales_ult_cust` | 51 | **OWNER** DATE **STATUS** | energy.eia861_sales_ult_cust |
| `in_eia861_sales` | 50 | **OWNER** DATE **STATUS** | energy.eia861_sales |
| `in_eia861_reliability` | 36 | **OWNER** DATE | energy.eia861_reliability |
| `in_nrc_reactors` | 0 | DATE | energy.nrc_reactors |

## GAS

| object | rows | flags | what it is |
|---|---:|---|---|
| `in_gas_capacity_texas_gas` | 23,220 | DATE | Boardwalk GasQuest anonymous reporting API, POST https://reporting.prod.bwpmlp.org/infopost/info |
| `in_gas_capacity_vector` | 4,620 | DATE | Vector Pipeline informational postings via vendor EBB https://www.gasnom.com/ip/vector/cap_opera |
| `in_gas_capacity_midwestern` | 3,367 | DATE | DT Midstream Trellis PTMS public infopost, https://dtmidstream.trellisenergy.com/ptms/public/inf |
| `in_gas_capacity_panhandle_eastern` | 1,979 | DATE | Energy Transfer Messenger ipost, https://peplmessenger.energytransfer.com/ipost/capacity/operati |
| `in_gas_capacity_trunkline` | 1,231 | DATE | Energy Transfer Messenger ipost, https://tgcmessenger.energytransfer.com/ipost/capacity/operatio |
| `in_gas_state_capacity` | 1,017 | DATE | energy.gas_eia_state_capacity |
| `in_gas_capacity_ngpl` | 693 | DATE | Kinder Morgan DART infopost, https://pipeline2.kindermorgan.com/Capacity/OpAvailPoint.aspx?code= |
| `in_gas_capacity_anr` | 554 | DATE | TC eConnects infopost (public SSRS), https://www.tceconnects.com/infopost/ReportViewer.aspx?/Inf |
| `in_gas_capacity_northern_border` | 290 | DATE | TC eConnects infopost (public SSRS), https://www.tceconnects.com/infopost/ReportViewer.aspx?/Inf |
| `in_gas_phmsa_distribution` | 266 | DATE **STATUS** | energy.gas_phmsa_distribution |
| `in_gas_pipelines` | 215 | GEO **STATUS** | energy.gas_pipelines_hifld |
| `in_gas_capacity_crossroads` | 24 | DATE | TC eConnects infopost (public SSRS), https://www.tceconnects.com/infopost/ReportViewer.aspx?/Inf |
| `in_gas_compressor_stations` | 24 | GEO | energy.gas_compressor_stations |
| `in_gas_storage` | 22 | GEO | energy.gas_storage |
| `in_gas_lng_terminals` | 0 | GEO | energy.gas_lng_terminals |
| `in_gas_processing_plants` | 0 | GEO | energy.gas_processing_plants |

## RATES & market

| object | rows | flags | what it is |
|---|---:|---|---|
| `in_ferc714_state_demand` | 166,554 | KEY DATE | energy.ferc714_state_demand |
| `in_eqr_identity` | 2,635 | DATE **STATUS** | energy.eqr_identity |
| `in_urdb_rates` | 969 | DATE **STATUS** | energy.urdb_rates |
| `in_news_dc` | 283 | DATE | CORRECTION note (no data change) |
| `in_rate_proxies` | 132 | DATE | energy-platfrom.indiana_app.in_urdb_rates + in_eia861_sales + in_rate_wholesale_floor + energy-p |
| `in_econ_gjf_megadeals` | 26 | DATE | energy.econ_gjf_megadeals |
| `in_utility_tariff_riders` | 3 | DATE **STATUS** | energy.utility_tariff_riders |
| `in_rate_component_gaps` | 2 | DATE **STATUS** | energy-platfrom.indiana_app.in_utility_tariff_riders |
| `in_rate_wholesale_floor` | 2 | DATE | energy-platfrom.energy.iso_lmp (MISO + PJM day-ahead, trailing 12 months) |
| `in_rate_eligibility` | 1 | DATE | energy-platfrom.indiana_app.in_utility_tariff_riders WHERE component_type='eligibility' |

## ENVIRONMENT & hazard

| object | rows | flags | what it is |
|---|---:|---|---|
| `in_water` | 2,415,369 | GEO DATE **STATUS** | energy.nhd_flowline |
| `in_wetlands` | 453,995 | GEO **STATUS** | energy.nwi_wetlands |
| `in_nhd_waterbody` | 186,667 | GEO DATE **STATUS** | energy.nhd_waterbody |
| `in_flood` | 66,140 | GEO | energy.nfhl_flood_zones |
| `in_spc_severe_events` | 24,716 | DATE | energy.spc_severe_events |
| `in_echo_cwa_facilities` | 13,209 | KEY DATE | energy.echo_cwa_facilities |
| `in_storm_events` | 12,460 | GEO DATE **STATUS** | energy.storm_events |
| `in_padus` | 4,736 | GEO DATE **STATUS** | energy.padus |
| `in_fema_disaster_declarations` | 1,442 | DATE **STATUS** | energy.fema_disaster_declarations |
| `in_water_cwns_2022` | 404 | GEO DATE | energy.water_cwns_2022 |
| `in_drought_by_state` | 105 | DATE | energy.drought_by_state |
| `in_fema_nri_counties` | 92 |  | energy.fema_nri_counties |
| `in_water_use` | 92 | DATE | energy.water_use |
| `in_seismic` | 88 | GEO | energy.seismic_design |
| `in_nonattainment` | 62 | GEO DATE **STATUS** | energy.nonattainment_areas |
| `in_water_aqueduct` | 56 | GEO DATE **STATUS** | energy.water_aqueduct |
| `in_land_faa_sua` | 19 | GEO DATE **STATUS** | energy.land_faa_sua |
| `in_land_military_bases` | 13 | GEO DATE **STATUS** | energy.land_military_bases |

## COMMUNITY, LABOUR, LEGISLATURE

| object | rows | flags | what it is |
|---|---:|---|---|
| `in_nfirs_incidentaddress_2024` | 49,895 | KEY DATE **STATUS** | energy.nfirs_incidentaddress_2024 |
| `in_nfirs_basicincident_2024` | 49,811 | DATE **STATUS** | energy.nfirs_basicincident_2024 |
| `in_nfirs_basicincident_2023` | 46,748 | DATE **STATUS** | energy.nfirs_basicincident_2023 |
| `in_nfirs_incidentaddress_2023` | 46,717 | KEY DATE **STATUS** | energy.nfirs_incidentaddress_2023 |
| `in_nfirs_incidentaddress_2022` | 40,091 | KEY DATE **STATUS** | energy.nfirs_incidentaddress_2022 |
| `in_nfirs_basicincident_2022` | 40,044 | DATE **STATUS** | energy.nfirs_basicincident_2022 |
| `in_nfirs_basicincident_2021` | 38,492 | DATE **STATUS** | energy.nfirs_basicincident_2021 |
| `in_nfirs_incidentaddress_2021` | 38,492 | KEY DATE **STATUS** | energy.nfirs_incidentaddress_2021 |
| `in_nfirs_basicincident_2020` | 38,287 | DATE **STATUS** | energy.nfirs_basicincident_2020 |
| `in_nfirs_incidentaddress_2020` | 38,287 | KEY DATE **STATUS** | energy.nfirs_incidentaddress_2020 |
| `in_nfirs_structure_fires` | 16,264 | DATE **STATUS** | indiana_app.in_nfirs_basicincident_2020/2021 x in_nfirs_incidentaddress_* x in_nfirs_fireinciden |
| `in_nfirs_fireincident_2021` | 9,798 | DATE **STATUS** | energy.nfirs_fireincident_2021 |
| `in_nfirs_fireincident_2020` | 9,652 | DATE **STATUS** | energy.nfirs_fireincident_2020 |
| `in_openstates_energy_bill_vote_people` | 9,197 | DATE | energy.openstates_energy_bill_vote_people |
| `in_sba_foia_loans` | 5,135 | DATE **STATUS** | energy.sba_foia_loans |
| `in_workforce_ipeds_cs_eng` | 4,830 | DATE | energy.workforce_ipeds_cs_eng |
| `in_candidate_sites_schools` | 1,928 | GEO DATE **STATUS** | energy.candidate_sites_schools |
| `in_acs_tract_vacancy` | 1,696 | DATE | energy.acs_tract_vacancy |
| `in_nfirs_fireincident_2024` | 1,255 | DATE **STATUS** | energy.nfirs_fireincident_2024 |
| `in_nfirs_fireincident_2022` | 1,221 | DATE **STATUS** | energy.nfirs_fireincident_2022 |
| `in_openstates_energy_bill_actions` | 811 | DATE **STATUS** | energy.openstates_energy_bill_actions |
| `in_candidate_sites_private_schools` | 590 | GEO KEY DATE **STATUS** | energy.candidate_sites_private_schools |
| `in_openstates_energy_bill_sponsorships` | 300 | DATE **STATUS** | energy.openstates_energy_bill_sponsorships |
| `in_cbp_county_industry` | 234 | DATE | energy.cbp_county_industry |
| `in_candidate_sites_colleges` | 151 | GEO DATE **STATUS** | energy.candidate_sites_colleges |
| `in_openstates_energy_bill_versions` | 140 | DATE **STATUS** | energy.openstates_energy_bill_versions |
| `in_openstates_energy_bill_sources` | 132 | DATE | energy.openstates_energy_bill_sources |
| `in_openstates_energy_bill_votes` | 126 | DATE | energy.openstates_energy_bill_votes |
| `in_workforce_ipeds_directory` | 112 | GEO DATE **STATUS** | energy.workforce_ipeds_directory |
| `in_acs_county` | 92 | DATE | energy.acs_county |
| `in_iocs_county_context` | 92 |  | indiana_app.in_si_refresh_iocs_eviction x energy.county_boundaries |
| `in_qcew_county_labor` | 92 | DATE | energy.qcew_county_labor |
| `in_openstates_energy_bill_abstracts` | 66 | DATE | energy.openstates_energy_bill_abstracts |
| `in_openstates_energy_bills_v2` | 66 | DATE **STATUS** | energy.openstates_energy_bills_v2 |
| `in_openstates_energy_bills` | 21 |  | energy.openstates_energy_bills |

## INFRASTRUCTURE & context

| object | rows | flags | what it is |
|---|---:|---|---|
| `in_fcc_bdc` | 12,649,532 | DATE | energy.fcc_bdc_fixed_availability |
| `in_fcc_bdc_fixed_summary_by_geography` | 15,900 | GEO DATE **STATUS** | energy.fcc_bdc_fixed_summary_by_geography |
| `in_faa_obstacles` | 15,638 | DATE **STATUS** | energy.faa_obstacles |
| `in_fcc_bdc_provider_summary` | 12,196 | GEO DATE **STATUS** | energy.fcc_bdc_provider_summary_by_geography |
| `in_railroads` | 2,117 | **OWNER** GEO | energy.railroads |
| `in_roads_secondary` | 861 | GEO **STATUS** | energy.roads_secondary |
| `in_zctas` | 807 | GEO | energy.zctas |
| `in_fcc_bdc_mobile_summary` | 533 | GEO DATE **STATUS** | energy.fcc_bdc_mobile_summary_by_geography |
| `in_roads_primary` | 225 | GEO | energy.roads_primary |
| `in_usa_structures_county` | 92 |  | energy.usa_structures_county |
| `in_tribal_land` | 14 | GEO **STATUS** | energy.tribal_land |
| `in_fcc_bdc_mobile_summary_by_geography` | 0 | GEO DATE | energy.fcc_bdc_mobile_summary_by_geography |
| `in_fcc_bdc_provider_summary_by_geography` | 0 | GEO DATE | energy.fcc_bdc_provider_summary_by_geography |

## VIEWS & derived location joins

| object | rows | flags | what it is |
|---|---:|---|---|
| `vw_bus_headroom_300_located` | 0 | GEO _view_ | indiana_app.in_bus_headroom_300 |
| `vw_ghgrp_emissions_located` | 0 | GEO DATE _view_ | indiana_app.in_ghgrp_emissions |
| `vw_nfirs_2020_located` | 0 | DATE _view_ | indiana_app.in_nfirs_basicincident_2020 |
| `vw_nfirs_2021_located` | 0 | DATE _view_ | indiana_app.in_nfirs_basicincident_2021 |
| `vw_nfirs_2022_located` | 0 | DATE _view_ | indiana_app.in_nfirs_basicincident_2022 |
| `vw_nfirs_2023_located` | 0 | DATE _view_ | indiana_app.in_nfirs_basicincident_2023 |
| `vw_nfirs_2024_located` | 0 | DATE _view_ | indiana_app.in_nfirs_basicincident_2024 |
| `vw_pjm_bus_withdrawal_located` | 0 | GEO _view_ | indiana_app.in_pjm_bus_withdrawal |
| `vw_pjm_queuescope_located` | 0 | GEO DATE _view_ | indiana_app.in_pjm_queuescope_aep |
| `vw_pjm_rtep_upgrades_located` | 0 | DATE _view_ | indiana_app.in_pjm_rtep_upgrades |
| `vw_si_candidates_located` | 0 | GEO KEY DATE _view_ | indiana_app.in_si_candidates |
| `vw_site_gates_located` | 0 | GEO KEY _view_ | indiana_app.in_site_gates |
| `vw_warn_notices_union` | 0 | DATE _view_ | indiana_app.in_si_refresh_warn_notices + in_si_state_warn_notices |

## META / audit

| object | rows | flags | what it is |
|---|---:|---|---|
| `_indiana_census` | 773 | DATE | energy.INFORMATION_SCHEMA + per-table Indiana counts |
| `_registry` | 276 | DATE |  |

## ⚠ Objects carrying OWNER data — the D9/D18 inputs we already hold

Absentee ownership is *owner mailing state/zip ≠ situs*. Every input below is already in the warehouse; none of it required a new acquisition.

| object | column | populated |
|---|---|---:|
| `in_si_refresh_indy_code_enforcement` | `OWNER` | 893,878 |
| `in_marion_parcel_crosswalk` | `FULLOWNERNAME` | 347,049 |
| `in_marion_parcel_crosswalk` | `OWNERCITY` | 347,026 |
| `in_marion_parcel_crosswalk` | `OWNERADDRESS` | 346,781 |
| `in_pjm_queuescope_aep` | `owner_id` | 303,671 |
| `in_pjm_queuescope_aep` | `owner_label` | 303,671 |
| `in_si_indy_code_placed` | `owner_name` | 46,387 |
| `in_pjm_rtep_upgrades` | `transmission_owner` | 15,398 |
| `in_si_signals` | `owner_name` | 6,725 |
| `in_si_evansville_demolition_permits` | `USER_Owner` | 4,190 |
| `in_si_candidates` | `owner` | 4,170 |
| `in_transmission_union` | `owner` | 3,025 |
| `in_eia_plants` | `transmission_distribution_owner_id` | 2,675 |
| `in_eia_plants` | `transmission_distribution_owner_name` | 2,675 |
| `in_eia_plants` | `transmission_distribution_owner_state` | 2,675 |
| `in_transmission_lines` | `owner` | 2,623 |
| `in_railroads` | `rrowner1` | 2,117 |
| `in_railroads` | `rrowner2` | 55 |
| `in_rto_expansion` | `owner` | 2,032 |
| `in_si_evansville_foreclosures` | `OWNER1` | 1,688 |
| `in_si_evansville_foreclosures` | `Current_Parcels_OWNER1` | 370 |
| `in_si_evansville_foreclosures` | `Current_Parcels_OwnerName` | 370 |
| `in_si_evansville_taxsale` | `OwnerName` | 1,101 |
| `in_si_evansville_taxsale` | `Owner_Name_2` | 956 |
| `in_si_evansville_taxsale` | `OWNER_NAMES` | 628 |
| `in_si_evansville_landbank` | `OWNER1` | 876 |
| `in_si_evansville_landbank` | `OwnerName` | 686 |
| `in_si_evansville_landbank` | `Propety_Owner` | 27 |
| `in_si_evansville_taxsale_transfers` | `owner1_2` | 795 |
| `in_si_evansville_taxsale_transfers` | `OWNER1` | 146 |
| `in_si_evansville_taxsale_transfers` | `OwnerName` | 146 |
| `in_queue_miso` | `transmissionowner` | 453 |
| `in_queue_miso_extras` | `transmissionowner` | 453 |
| `in_txexp_miso_mtep_appendix_a_status` | `facility_owner_s` | 198 |
| `in_lbnl_interconnection_costs` | `transmission_owner` | 116 |
| `in_pjm_nucra_costs` | `transmission_owner` | 55 |
| `in_eia861_sales_ult_cust` | `ownership` | 49 |
| `in_eia861_sales` | `ownership` | 48 |
| `in_eia861_reliability` | `ownership` | 36 |
| `in_osm_power_substations` | `owner` | 3 |

## ⚠ STATUS vocabularies — where a hidden signal split can live

`saleStatusDescription` hid **D4 tax delinquency** inside D1_tax_sale for a whole session. `CASE_TYPE` hid unsafe-building and vacant-board-order inside D12. Read the vocabulary before trusting any count taken over one of these.

- **`in_bonus_geo`.`kind`** — low_income_tract 662 · qct 337 · coal_closure 221 · opportunity_zone 156 · critical_habitat 10 · energy_community 8
- **`in_bus_headroom_miso`.`location_status`** — outside_indiana 8,966 · joinable_no_coords 2,212 · indiana 642
- **`in_candidate_sites_colleges`.`CBSATYPE`** — 1 124 · 2 24 · 0 3
- **`in_candidate_sites_private_schools`.`CBSATYPE`** — 1 414 · 2 128 · N 48
- **`in_candidate_sites_schools`.`CBSATYPE`** — 1 1,390 · 2 356 · 0 182
- **`in_county_rollup`.`class_union`** — 6439 1 · 2183 1 · 5973 1 · 15360 1 · 5584 1 · 6653 1 · 6515 1
- **`in_data_centers`.`osm_type`** — way 11 · node 2
- **`in_dc_actions`.`action`** — headline: moratorium 46 · headline: pause 8 · headline: opposition 5 · headline: rejects 4 · headline: moratoriums 3 · headline: halt 3 · headline: ban 3
- **`in_dc_actions`.`action_date`** — 2026-06-22 5 · 2026-06-09 5 · 2026-07-28 5 · 2026-06-15 4 · 2026-06-23 4 · 2026-08-10 4 · 2026-07-14 3
- **`in_dc_actions`.`action_date_grain`** — day 78 · month 1
- **`in_dc_actions_county_v2`.`action_type`** — proposed 29 · moratorium 24 · approval-permissive 22 · adopted-uncodified-ordinan 8 · petition-pending 7 · denied 7 · withdrawn 6
- **`in_dc_actions_county_v2`.`doc_type`** — news article 72 · ordinance PDF 9 · aggregator 8 · minutes 5 · county webpage 5 · agenda 3 · news release 2
- **`in_dc_actions_county_v2`.`evidence_grade`** — REPORTED_NEEDS_VERIFICATIO 84 · VERIFIED_AT_OFFICIAL_SOURC 23
- **`in_dc_actions_coverage_v2`.`status`** — ACTION_FOUND 53 · SEARCHED_NONE_FOUND 39
- **`in_dc_actions_nw_first_pass`.`action_type`** — moratorium 5 · approval-permissive 3 · adopted-uncodified-ordinan 3 · proposed 2 · withdrawn 2 · petition-pending 1 · denied 1
- **`in_dc_actions_nw_first_pass`.`doc_type`** — news article 5 · minutes 4 · ordinance PDF 3 · county webpage 3 · agenda 1 · aggregator 1
- **`in_dc_actions_nw_first_pass`.`evidence_grade`** — VERIFIED_AT_OFFICIAL_SOURC 11 · REPORTED_NEEDS_VERIFICATIO 6
- **`in_dc_colo_resolved`.`verdict`** — RESOLVED 5 · SAME_BUILDING_AS 2 · NOT_FOUND 1
- **`in_dc_colo_resolved`.`source_type`** — operator site + PeeringDB 2 · directories + PeeringDB AP 1 · operator site (archived) + 1 · operator site + PeeringDB  1 · operator site (archived +  1 · directories (baxtel page f 1 · directories (baxtel page f 1
- **`in_dc_eei_tariffs`.`customer_type`** — Google / Data Center 2 · AWS / Data Center 1 · Meta / Data Center 1 · Microsoft / Data Center 1
- **`in_eia860_generators`.`operational_status`** — existing 9,055 · proposed 1,966 · retired 1,453 · None 5
- **`in_eia860_generators`.`fuel_type_code_pudl`** — gas 4,762 · coal 2,191 · oil 1,676 · waste 1,430 · solar 1,286 · hydro 555 · wind 429
- **`in_eia860_generators`.`fuel_type_count`** — 1 9,134 · 2 2,503 · 3 804 · 4 26 · 0 12
- **`in_eia860m_generators`.`status`** — (OP) Operating 414 · None 184 · (SB) Standby/Backup: avail 11 · (P) Planned for installati 10 · (T) Regulatory approvals r 9 · (OS) Out of service and NO 6 · (V) Under construction, mo 5
- **`in_eia861_demand_response`.`customer_class`** — industrial 165 · transportation 165 · commercial 165 · residential 165
- **`in_eia861_sales`.`data_type_o_observed_i_imputed`** — O 48 · I 2
- **`in_eia861_sales_ult_cust`.`data_type`** — O 49 · I 2
- **`in_eia923_fuel_receipts_costs`.`fuel_type_code_pudl`** — gas 386 · coal 292 · oil 202
- **`in_eia_plants`.`ash_impoundment_status`** — None 2,459 · OP 160 · OS 54 · OA 2
- **`in_eia_plants`.`ferc_cogen_status`** — false 2,609 · true 63 · None 3
- **`in_eia_plants`.`regulatory_status_code`** — RE 1,415 · NR 1,260
- **`in_elec_power_operational`.`fueltypeid`** — ALL 676 · NG 676 · FOS 676 · NGO 676 · PEL 658 · PET 658 · DFO 658
- **`in_elec_power_operational`.`fuelTypeDescription`** — biomass 1,092 · natural gas 676 · natural gas & other gases 676 · all fuels 676 · fossil fuels 676 · petroleum liquids 658 · petroleum 658
- **`in_eqr_identity`.`transactions_reported_to_index_price_publishers`** — false 2,631 · true 4
- **`in_faa_obstacles`.`verified_status`** — O 8,674 · U 6,964
- **`in_faa_obstacles`.`type`** — T-L TWR            4,067 · TOWER              3,892 · POLE               2,339 · WINDMILL           1,816 · BLDG               1,606 · UTILITY POLE       604 · FENCE              267
- **`in_faa_obstacles`.`action`** — A 11,684 · C 3,954
- **`in_fcc_bdc_fixed_summary_by_geography`.`area_data_type`** — Total 4,170 · Rural 4,170 · Nontribal 3,750 · Urban 3,240 · Tribal 570
- **`in_fcc_bdc_fixed_summary_by_geography`.`geography_type`** — County 10,560 · CBSA (MSA) 2,820 · Tribal 1,260 · Congressional District 1,110 · State 150
- **`in_fcc_bdc_mobile_summary`.`area_data_type`** — Rural 140 · Total 140 · Nontribal 125 · Urban 108 · Tribal 20
- **`in_fcc_bdc_mobile_summary`.`geography_type`** — County 352 · CBSA (MSA) 94 · Tribal 45 · Congressional District 37 · State 5
- **`in_fcc_bdc_provider_summary`.`geography_type`** — Census Place 9,179 · County 1,890 · CBSA (MSA) 454 · Congressional District 379 · Tribal 180 · State 114
- **`in_fcc_bdc_provider_summary`.`data_type`** — Fixed Broadband 9,703 · Mobile Broadband 2,493
- **`in_fema_disaster_declarations`.`declarationType`** — DR 981 · EM 461
- **`in_fema_disaster_declarations`.`incidentType`** — Severe Storm 668 · Flood 192 · Snowstorm 185 · Biological 185 · Hurricane 92 · Winter Storm 92 · Severe Ice Storm 26
- **`in_gas_phmsa_distribution`.`report_submission_type`** — INITIAL 228 · SUPPLEMENTAL 38
- **`in_gas_phmsa_distribution`.`operator_type`** — None 188 · Municipal Owned 40 · Investor Owned 24 · Privately Owned 12 · Cooperative 2
- **`in_gas_pipelines`.`typepipe`** — Interstate 210 · Intrastate 5
- **`in_ghgrp_facilities`.`emission_classification_code`** — CU_ONLY 1,214 · CU_OTHERS 1,135 · DEFAULT 1,042
- **`in_ghgrp_facilities`.`facility_types`** — Direct Emitter 2,593 · None 340 · Supplier 169 · Supplier, LDC - Direct Emi 152 · Supplier, Direct Emitter 105 · SF6 from Elec. Equip. 16 · Supplier, SF6 from Elec. E 12
- **`in_ghgrp_facilities`.`reported_industry_types`** — C 1,041 · C,HH 354 · None 336 · C,D 248 · D 154 · NN-LDC,W-LDC 152 · NN-LDC 141
- **`in_gov_surplus_frpp`.`real_property_type`** — Structure 792 · Building 684 · Land 118
- **`in_gov_surplus_frpp`.`real_property_type_code`** — 40 792 · 35 684 · 20 118
- **`in_gov_surplus_frpp`.`asset_status`** — Current Mission Need 1,540 · Disposed 26 · Future Mission Need 11 · Report of Excess Submitted 9 · Determination to Dispose 8
- **`in_gov_surplus_nces`.`sy_status`** — 1 1,884 · 3 33 · 2 9 · 5 2
- **`in_gov_surplus_nces`.`sy_status_text`** — Open 1,884 · New 33 · Closed 9 · Changed Boundary/Agency 2
- **`in_gov_surplus_nces`.`updated_status`** — 1 1,884 · 3 33 · 2 9 · 5 2
- **`in_grid_plans`.`row_type`** — project 391 · document 227
- **`in_grid_plans`.`extraction_status`** — extracted 391 · None 191 · EXTRACTION-DEFERRED (IRP t 26 · EXTRACTION-DEFERRED (no pr 8 · extracted (63 project rows 1 · extracted (321 project row 1
- **`in_grid_plans`.`project_type`** — protection/switching 298 · None 270 · transformer addition 40 · structure replacement 4 · rebuild 3 · undergrounding 1 · new line 1
- **`in_iurc_dockets`.`petition_type`** — TDSIC 186 · Contract 126 · Certificate of Need 81 · Tariff Matters 65 · Economic Development 25 · SDC 14 · Rates 8
- **`in_iurc_dockets`.`status`** — Decided 487 · Pending 22 · Appealed 5 · New 2
- **`in_land_faa_sua`.`type_code`** — MOA 13 · R 6
- **`in_land_military_bases`.`siteoperationalstatus`** — act 10 · clsd 3
- **`in_lbnl_interconnection_costs`.`study_type`** — System Impact 59 · SIS 41 · Interconnection Service Ag 11 · Addendum 4 · Interim Interconnection Se 1
- **`in_lbnl_interconnection_costs`.`service_type`** — Capacity 71 · NRIS 39 · ERIS 4 · None 1 · NRIS Only 1
- **`in_lbnl_interconnection_costs`.`request_status`** — Active 62 · Complete 37 · Withdrawn 17
- **`in_marion_address_crosswalk`.`PLACE_TYPE`** — None 465,046 ·   4
- **`in_marion_address_crosswalk`.`TYPE`** — BUILDING 281,892 · UNIT 156,757 · PARCEL 26,401
- **`in_marion_address_crosswalk`.`UNIT_TYPE`** — None 345,322 · APT 98,678 · CONDO 14,791 · LOT 3,718 · SUITE 2,072 · ROOM 465 ·   4
- **`in_marion_parcel_crosswalk`.`PROPERTY_CLASS`** — RESIDENTIAL 317,315 · COMMERCIAL 17,052 · EXEMPT 7,213 · INDUSTRIAL 3,804 · AGRICULTURAL 874 · UTILITIES-REAL 783 · MINERAL 8
- **`in_marion_parcel_crosswalk`.`PROPERTY_SUB_CLASS`** — 510 248,177 · 500 19,186 · 550 18,969 · 511 16,032 · 520 9,120 · 501 2,448 · 599 2,396
- **`in_marion_parcel_crosswalk`.`PROPERTY_SUB_CLASS_DESCRIPTION`** — RES ONE FAMILY PLATTED LOT 248,177 · VACANT PLATTED LOT-500 19,186 · CONDO PLATTED-550 18,969 · RES ONE FAMILY UNPLAT 0-9. 16,032 · RES TWO FAMILY PLATTED LOT 9,120 · RES VAC 0-9.99 UNPLATTED-5 2,448 · OTHER RES STRUCTURE-599 2,396
- **`in_nfirs_basicincident_2020`.`INC_TYPE`** — 111 5,130 · 412 3,821 · 444 3,163 · 151 2,167 · 561 2,162 · 424 1,797 · 131 1,719
- **`in_nfirs_basicincident_2021`.`INC_TYPE`** — 111 5,336 · 412 4,647 · 444 3,564 · 151 2,163 · 131 1,744 · 424 1,736 · 561 1,536
- **`in_nfirs_basicincident_2022`.`INC_TYPE`** — 111 5,893 · 412 4,848 · 444 3,341 · 131 1,985 · 151 1,979 · 142 1,830 · 424 1,695
- **`in_nfirs_basicincident_2023`.`INC_TYPE`** — 111 6,678 · 412 5,456 · 444 3,934 · 151 2,901 · 131 2,237 · 561 2,108 · 424 1,988
- **`in_nfirs_basicincident_2024`.`INC_TYPE`** — 111 6,835 · 412 6,229 · 444 4,600 · 151 3,044 · 131 2,375 · 561 2,177 · 424 2,027
- **`in_nfirs_fireincident_2020`.`TYPE_MAT`** — None 5,599 · UU 1,367 · 00 358 · 99 264 · 41 258 · 71 232 · 63 203
- **`in_nfirs_fireincident_2020`.`MOB_TYPE`** — None 7,594 · 11 882 · 10 582 · 65 80 · 20 73 · 23 67 · 21 45
- **`in_nfirs_fireincident_2020`.`STRUC_TYPE`** — None 6,959 · 1 2,362 · 0 141 · 2 120 · 3 56 · 6 7 · 8 7
- **`in_nfirs_fireincident_2021`.`TYPE_MAT`** — None 5,680 · UU 1,352 · 00 338 · 41 286 · 99 265 · 63 250 · 71 245
- **`in_nfirs_fireincident_2021`.`MOB_TYPE`** — None 7,683 · 11 916 · 10 599 · 20 94 · 23 86 · 65 57 · 71 43
- **`in_nfirs_fireincident_2021`.`STRUC_TYPE`** — None 6,779 · 1 2,708 · 0 132 · 2 112 · 3 45 · 6 11 · 8 11
- **`in_nfirs_fireincident_2022`.`TYPE_MAT`** — None 695 · UU 272 · 00 37 · 23 36 · 99 33 · 41 33 · 51 21
- **`in_nfirs_fireincident_2022`.`MOB_TYPE`** — 11 573 · 10 281 · 23 157 · 20 78 · 21 30 · 14 18 · 15 11
- **`in_nfirs_fireincident_2022`.`STRUC_TYPE`** — None 1,206 · 1 9 · 2 4 · 0 2
- **`in_nfirs_fireincident_2024`.`TYPE_MAT`** — None 784 · UU 225 · 41 40 · 00 39 · 23 28 · 51 25 · 99 23
- **`in_nfirs_fireincident_2024`.`MOB_TYPE`** — 11 636 · 10 241 · 23 139 · 20 95 · 21 31 · 22 18 · 14 15
- **`in_nfirs_fireincident_2024`.`STRUC_TYPE`** — None 1,209 · 1 41 · 2 4 · 0 1
- **`in_nfirs_incidentaddress_2020`.`LOC_TYPE`** — 1 30,676 · 2 4,098 · 4 1,413 · 3 997 · 5 641 · 6 410 · 7 30
- **`in_nfirs_incidentaddress_2020`.`STREETTYPE`** — None 11,590 · ST 9,532 · RD 4,984 · AVE 4,164 · DR 3,614 · CT 872 · LN 864
- **`in_nfirs_incidentaddress_2021`.`LOC_TYPE`** — 1 30,496 · 2 4,109 · 4 1,645 · 3 1,176 · 5 691 · 6 352 · 7 23
- **`in_nfirs_incidentaddress_2021`.`STREETTYPE`** — None 10,234 · ST 9,794 · RD 5,021 · AVE 4,535 · DR 4,079 · LN 1,028 · CT 937
- **`in_nfirs_incidentaddress_2022`.`LOC_TYPE`** — 1 31,527 · 2 4,311 · 4 1,797 · 3 1,270 · 5 766 · 6 401 · 7 19
- **`in_nfirs_incidentaddress_2022`.`STREETTYPE`** — None 11,750 · ST 9,494 · RD 5,449 · DR 4,201 · AVE 4,076 · LN 1,109 · CT 972
- **`in_nfirs_incidentaddress_2023`.`LOC_TYPE`** — 1 36,630 · 2 4,897 · 4 2,294 · 3 1,471 · 5 1,015 · 6 386 · 7 24
- **`in_nfirs_incidentaddress_2023`.`STREETTYPE`** — None 13,223 · ST 12,073 · AVE 5,620 · RD 5,478 · DR 4,857 · LN 1,147 · CT 1,075
- **`in_nfirs_incidentaddress_2024`.`LOC_TYPE`** — 1 39,021 · 2 5,171 · 4 2,647 · 3 1,598 · 5 994 · 6 428 · 7 36
- **`in_nfirs_incidentaddress_2024`.`STREETTYPE`** — None 14,765 · ST 12,336 · RD 6,009 · AVE 5,655 · DR 5,199 · LN 1,305 · CT 1,121
- **`in_nfirs_structure_fires`.`inc_type`** — 111 10,466 · 113 2,231 · 118 2,063 · 112 614 · 114 444 · 121 154 · 122 84
- **`in_nfirs_structure_fires`.`property_class`** — residential 8,890 · unknown 4,292 · non-residential 3,082
- **`in_nhd_waterbody`.`ftype`** — 390 163,469 · 466 19,539 · 436 3,659
- **`in_nonattainment`.`current_status`** — Maintenance (NAAQS revoked 40 · Maintenance 18 · Nonattainment 3 · Nonattainment (NAAQS revok 1
- **`in_nonattainment`.`classification_pub_date`** — None 32 · 1083326400000 16 · 1104926400000 7 · 1337601600000 5 · 1401710400000 2
- **`in_openstates_energy_bill_actions`.`classification`** — [] 282 · ['amendment-failure', 'fai 109 · ['reading-1', 'referral-co 88 · ['passage'] 60 · ['committee-passage'] 46 · ['passage', 'reading-3', ' 43 · ['reading-2'] 43
- **`in_openstates_energy_bill_sponsorships`.`classification`** — coauthor 120 · author 93 · cosponsor 53 · sponsor 34
- **`in_openstates_energy_bill_versions`.`link_media_types`** — application/pdf 131 · application/pdf|applicatio 8 · application/pdf|applicatio 1
- **`in_openstates_energy_bills_v2`.`organization_classification`** — lower 35 · upper 31
- **`in_operating_generators`.`status`** — OP 11,153 · SB 401 · OS 144 · OA 97
- **`in_operating_generators`.`statusDescription`** — Operating 11,153 · Standby/Backup: available  401 · Out of service and NOT exp 144 · Out of service but expecte 97
- **`in_ordinances_amlegal_coverage_v2`.`status`** — NOT_ATTEMPTED_RATE_LIMITED 197 · NOT_ATTEMPTED_RUN_ABORTED 17 · TOC_SCANNED_NO_NAMED_CHAPT 9 · BLOCKED 7
- **`in_ordinances_amlegal_v3`.`prior_run_status`** — NOT_ATTEMPTED_RATE_LIMITED 197 · NOT_ATTEMPTED_RUN_ABORTED 17 · TOC_SCANNED_NO_NAMED_CHAPT 9 · BLOCKED 7
- **`in_ordinances_amlegal_v3_probes`.`http_status`** — 200 7 · 404 2 · 403 2
- **`in_ordinances_dc_county_sites_v2`.`evidence_grade`** — REPORTED_NEEDS_VERIFICATIO 4 · VERIFIED_AT_OFFICIAL_SOURC 2
- **`in_ordinances_dc_coverage_v2`.`status`** — FOUND 24 · SEARCHED_NONE_FOUND 14 · NOT_REACHABLE_NO_SEARCHABL 7
- **`in_ordinances_dc_v2`.`client_classification_id`** — 2 98 · 4 29 · 6 14 · 3 12
- **`in_ordinances_dc_v2_triage`.`verdict`** — NOT_RELEVANT 88 · RELEVANT 19 · NEEDS_FULL_TEXT 8
- **`in_ordinances_publisher_inventory_v2`.`status`** — BLOCKED 2 · BLOCKED_AUTH 1
- **`in_osm_power_substations`.`osm_type`** — way 2,872 · node 1
- **`in_padus`.`FeatClass`** — Fee 3,298 · Easement 1,393 · Designation 30 · Proclamation 15
- **`in_padus`.`Category`** — Fee 3,294 · Easement 1,393 · Designation 30 · Proclamation 15 · Other 4
- **`in_padus`.`Own_Type`** — LOC 2,142 · PVT 1,345 · STAT 574 · NGO 407 · UNK 212 · DESG 28 · FED 18
- **`in_pjm_nucra_costs`.`upgrade_id`** — n6260.1 1 · n6249 1 · n6605 1 · n6639.2 1 · n6872 1 · n6639.4 1 · n7553 1
- **`in_pjm_nucra_costs`.`upgrade_name`** — Replace the Pontiac 345 kV 1 · Replace the wave trap on t 1 · Wreck and rebuild 0.99 mil 1 · Replace existing 345kV lin 1 · Wreck and rebuild 15.09 mi 1 · 1)_x0009_Upgrade 345kV sta 1 · Replace Northern Neck 115/ 1
- **`in_pjm_nucra_costs`.`status`** — EP 38 · Pending 10 · UC 6 · IS 1
- **`in_pjm_queuescope_aep`.`contingency_type`** — Single 121,286 · Breaker 114,483 · Tower 36,145 · Bus 31,757
- **`in_pjm_rtep_cost_allocations`.`share_type`** — Load Ratio Share 189 · Non-Load Ratio Share 186
- **`in_pjm_rtep_cost_allocations`.`upgrade_id`** — b1659.14 25 · b4068.2 24 · b4068.1 24 · b3847.3 24 · b1659.13 23 · b2973 22 · b2971 22
- **`in_pjm_rtep_upgrade_details`.`upgrade_id`** — b0117 1 · TOI427 1 · b0839 1 · b0840 1 · b1039 1 · b0840.1 1 · b1039.1 1
- **`in_pjm_rtep_upgrade_details`.`project_type`** — Supplemental 471 · Network 263 · Baseline 198
- **`in_pjm_rtep_upgrades`.`upgrade_id`** — b0002 1 · b0001 1 · b0003 1 · b0004 1 · b0006 1 · b0005 1 · b0007 1
- **`in_pjm_rtep_upgrades`.`project_type`** — Supplemental 6,347 · Baseline 5,637 · Network 3,459
- **`in_pjm_rtep_upgrades`.`status`** — IS 9,163 · EP 3,540 · Cancelled 847 · Active 834 · UC 535 · On Hold 282 · PL 230
- **`in_queue`.`status`** — withdrawn 579 · active 289 · operational 69 · suspended 11
- **`in_queue`.`project_type`** — Generation 945 · Upgrade 3
- **`in_queue`.`resource_type`** — Solar 383 · Battery 183 · Wind 167 · Solar+Battery 106 · Gas 57 · Other 25 · Coal 15
- **`in_queue_counties`.`resource_types`** — Battery, Solar, Solar+Batt 13 · Battery, Solar, Wind 8 · Battery, Solar 8 · Battery, Gas, Solar, Solar 5 · Solar 4 · Solar, Wind 4 · Solar, Solar+Battery 3
- **`in_queue_miso`.`svctype`** — NRIS 428 · ERIS 16 · SIS 6 ·  3 · NRIS-Only 3
- **`in_queue_miso`.`fueltype`** — Solar 221 · Battery Storage 114 · Hybrid 68 · Wind 38 · Gas 12 · Combined Cycle 2 ·  1
- **`in_queue_miso`.`facilitytype`** — Photovoltaic 222 · Battery Storage 113 · Solar/Battery 64 · Wind Turbine 39 · Combined Cycle 10 · Combustion Turbine (Simple 7 ·  1
- **`in_queue_miso_extras`.`svctype`** — NRIS 428 · ERIS 16 · SIS 6 ·  3 · NRIS-Only 3
- **`in_queue_miso_extras`.`facilitytype`** — Photovoltaic 222 · Battery Storage 113 · Solar/Battery 64 · Wind Turbine 39 · Combined Cycle 10 · Combustion Turbine (Simple 7 ·  1
- **`in_queue_miso_extras`.`fueltype`** — Solar 221 · Battery Storage 114 · Hybrid 68 · Wind 38 · Gas 12 · Combined Cycle 2 ·  1
- **`in_rate_component_gaps`.`component_type`** — rider 1 · base_charge 1
- **`in_refresh_cadence`.`kind`** — table 251 · si_signal 17
- **`in_roads_secondary`.`pretypeabr`** — US Hwy 859 · US Rte 2
- **`in_rtep_bus_join`.`upgrade_id`** — b1420.1 6 · s3148.1 5 · n4056.1 5 · b1951.1 4 · b1951.2 4 · n9068.0 4 · n7092 4
- **`in_rtep_bus_join`.`project_type`** — Supplemental 560 · Network 371 · Baseline 298
- **`in_rtep_bus_summary`.`upgrades`** — 1 22 · 2 16 · 5 8 · 3 7 · 4 5 · 8 3 · 26 3
- **`in_rtep_bus_summary`.`baseline_upgrades`** — 0 39 · 1 18 · 3 7 · 2 6 · 4 4 · 20 3 · 5 1
- **`in_rtep_bus_summary`.`supplemental_upgrades`** — 1 26 · 2 18 · 0 14 · 4 9 · 5 5 · 3 4 · 6 3
- **`in_rto_expansion`.`project_type`** — Supplemental 471 · Network 263 · Local Reliability 257 · Baseline 198 · Age and Condition 168 · Substation 142 · BRP 111
- **`in_rto_expansion`.`status`** — M4 - Project in Service 699 · IS 549 · M2 - Appendix A Approved 333 · EP 244 · Active 79 · M1 - Proposed 56 · On Hold 26
- **`in_sba_foia_loans`.`businesstype`** — CORPORATION 4,576 · None 273 · INDIVIDUAL 225 · PARTNERSHIP 61
- **`in_sba_foia_loans`.`loanstatus`** — PIF 2,609 · EXEMPT 1,388 · CANCLD 695 · CHGOFF 276 · NOT FUNDED 158 · CLOSED 9
- **`in_si_d11_admitted`.`raw_status`** — Voluntarily Dissolved 348 · Revoked 293 · INACTIVE   / Automatically 95 · Cancelled 63 · INACTIVE   / Automatically 59 · Dissolved 22 · Administratively Dissolved 21
- **`in_si_d11_admitted`.`status_family`** — dissolved 493 · revoked 470 · forfeited 19 · void 1
- **`in_si_d11_entity_dissolution`.`raw_status`** — Withdrawn 1,019 · Voluntarily Dissolved 348 · Revoked 293 · INACTIVE   / Automatically 95 · INACTIVE   / Withdrawn - C 69 · Cancelled 63 · INACTIVE   / Automatically 59
- **`in_si_d11_entity_dissolution`.`status_family`** — withdrawn 1,146 · dissolved 493 · revoked 470 · forfeited 19 · void 1
- **`in_si_d22_echo_facilities`.`FAC_DATE_LAST_INFORMAL_ACTION`** — None 45,220 · 03/10/1995 208 · 03/08/1996 116 · 04/18/1994 100 · 04/05/1994 73 · 04/26/2010 70 · 01/14/2026 63
- **`in_si_d22_echo_facilities`.`FAC_FORMAL_ACTION_COUNT`** — 0 57,059 · 1 484 · 2 317 · 3 95 · 4 30 · 6 11 · 5 8
- **`in_si_d22_echo_facilities`.`FAC_DATE_LAST_FORMAL_ACTION`** — None 52,591 · 07/19/2006 157 · 04/17/2006 75 · 07/14/1997 54 · 08/07/2006 46 · 06/02/1997 40 · 10/17/2022 20
- **`in_si_d22_echo_indiana`.`FAC_DATE_LAST_INFORMAL_ACTION`** — None 45,207 · 03/10/1995 208 · 03/08/1996 116 · 04/18/1994 100 · 04/05/1994 73 · 04/26/2010 70 · 01/06/2026 63
- **`in_si_d22_echo_indiana`.`FAC_FORMAL_ACTION_COUNT`** — 0 57,041 · 1 484 · 2 317 · 3 95 · 4 30 · 6 11 · 5 8
- **`in_si_d22_echo_indiana`.`FAC_DATE_LAST_FORMAL_ACTION`** — None 52,577 · 07/19/2006 157 · 04/17/2006 75 · 07/14/1997 54 · 08/07/2006 46 · 06/02/1997 40 · 10/17/2022 20
- **`in_si_d22_idem_enforcement`.`type_of_action_order`** — NOTICE OF VIOLATION SIGNED 10,951 · AGREED ORDER (AO) ADOPTED  10,747 · COMMISSIONER'S ORDER ISSUE 542 · AMENDED AO ADOPTED (Signed 170 · AMENDED NOV SIGNED 141 · EMERGENCY ORDER ISSUED (Si 13 · AMENDED EMERGENCY ORDER IS 1
- **`in_si_d22_parcel_join`.`distress_class`** — no_distress_marker 27,248 · facility_inactive 5,584 · violation 768 · significant_violation 262 · penalised 254
- **`in_si_d22_parcel_join`.`formal_action_count`** — 0 33,546 · 1 300 · 2 170 · 3 59 · 4 18 · 6 7 · 5 5
- **`in_si_d22_parcel_join`.`last_formal_action`** — None 30,715 · 2006-07-19 128 · 2006-04-17 51 · 2020-03-02 38 · 1997-07-14 35 · 2006-08-07 34 · 2000-11-07 24
- **`in_si_d25_admitted`.`filing_type`** — Notice Of Exemption 53 · Consummation Notice 50 · Petition For Exemption 24
- **`in_si_d25_stb_abandonment_state`.`filing_type`** — Reply 185 · Request For Extension Of T 150 · Trail Use Request 53 · Notice Of Exemption 53 · Consummation Notice 50 · Motion/Petition/Request 31 · Modify/Supplement Prior Fi 30
- **`in_si_d27_admitted`.`raw_filing_type`** — UCC financing statement 146 · ORIG FIN STMT 10
- **`in_si_d27_ucc_lapse_v2`.`raw_filing_type`** — UCC financing statement 146 · ORIG FIN STMT 10
- **`in_si_d5_abandoned_buildings`.`status`** — Abandoned 5,709 · Vacant 1,411 · Vacant/Abandoned 47 · Chronic problem property 7
- **`in_si_evansville_demolition_permits`.`USER_App_Status`** — ACTIVE 1,988 · COMPLETE 1,745 · EXPIRED 437 · WITHDRAWN 12 · ENTERED IN ERROR 8
- **`in_si_evansville_demolition_permits`.`USER_User_Status`** — ACTIVE 3,095 · CLOSED 659 · EXPIRED 436
- **`in_si_evansville_foreclosures`.`Current_Parcels_SUBTYPE`** — None 5,385 · 1 373
- **`in_si_evansville_foreclosures`.`Current_Parcels_property_class`** — None 5,388 · 510 297 · 511 21 · 509 11 · 101 7 · 520 5 · 550 5
- **`in_si_evansville_foreclosures`.`Current_Parcels_land_type1`** — None 5,388 · F 308 · 9 41 · 11 7 · 91 6 · 4 5 · 13 2
- **`in_si_evansville_landbank`.`SUBTYPE`** — None 1,188 · 1 472
- **`in_si_evansville_landbank`.`grade`** — None 974 ·   198 · D 148 · N/A 130 · D+1 74 · D-1 58 · D+2 39
- **`in_si_evansville_landbank`.`grade_fact`** — None 974 · 0 328 · 80 148 · 85 74 · 70 58 · 90 39 · 100 12
- **`in_si_evansville_taxsale`.`property_class`** — None 2,604 · 510 347 · 500 63 · 511 36 · 509 23 · 520 23 · 400 17
- **`in_si_evansville_taxsale`.`land_type1`** — None 2,604 · F 471 · 11 43 · 9 40 · 13 19 · 91 11 · 12 5
- **`in_si_evansville_taxsale`.`grade`** — None 2,604 · D 170 ·  164 · D+1 104 · D-1 50 · D+2 34 · C-1 29
- **`in_si_evansville_taxsale_transfers`.`property_class`** — 510 289 · 500 206 · 620 196 · 640 148 · 520 22 · 400 13 · 699 12
- **`in_si_evansville_taxsale_transfers`.`land_type1`** — None 795 · F  134 · 11 4 · 9  3 · 13 2 · 91 1 · 74 1
- **`in_si_evansville_taxsale_transfers`.`grade`** — None 795 · D 35 · D-1 31 · N/A 27 · D+1 21 · D+2 19 · C 5
- **`in_si_ibtr_placed`.`appeal_type`** — Form 131 4,511 · Form 132 472 · Form 133 443 · Form 139 12
- **`in_si_ibtr_placed`.`status_name`** — Closed 5,407 · Closed - appeal pending 31
- **`in_si_indy_abandoned_vacant`.`STATUS`** — Abandoned 5,709 · Vacant 1,411
- **`in_si_indy_abandoned_vacant_spatial`.`STATUS`** — Abandoned 5,709 · Vacant 1,411
- **`in_si_indy_code_placed`.`case_status`** — Closed 23,088 · Closed - Fees Due 13,260 · Closed, VBO 4,931 · Closed, RNH 2,670 · Closed, RWH 1,258 · Closed, DEM 574 · Void 488
- **`in_si_indy_taxsale_parcels`.`RECORDTYPE`** — A 61,440 · C 919 · B 9
- **`in_si_indy_taxsale_parcels`.`STATUSID`** — 8 23,767 · 15 13,298 · 4 12,660 · 6 2,239 · 0 2,209 · 24 2,186 · 14 1,859
- **`in_si_indy_taxsale_parcels`.`STATUSNAME`** — Satisfied 23,767 · Deed Issued 13,298 · Owner Redeemed 12,660 · On List 2,239 · Unknown 2,209 · Payment Plan 2,186 · Removed - Treasurer 1,859
- **`in_si_marion_route_check`.`status`** — Abandoned 5,709 · Vacant 1,411
- **`in_si_marion_route_check`.`verdict`** — AGREE 7,104 · DISAGREE 9 · crosswalk only 7
- **`in_si_parcel_signals_v2`.`admit_status`** — excluded_residential 85,800 · admitted 24,629 · excluded_low_severity 6,231
- **`in_si_refresh_brownfield_epa_in`.`TLStatus`** — IN SERVICE 1,438 · NOT AVAILABLE 45
- **`in_si_refresh_ibtr_appeals`.`appealTypeName`** — Form 131 7,282 · Form 133 1,871 · Form 132 977 · Form 139 22
- **`in_si_refresh_ibtr_appeals`.`statusName`** — Closed 10,118 · Closed - appeal pending 34
- **`in_si_refresh_ibtr_appeals`.`typeName`** — Board Determination 8,976 · Settlement - stipulation 517 · Settlement - withdrawal 474 · Dismissal - defective 98 · Remand 69 · Dismissal - failure to app 10 · Board Determination Rehear 8
- **`in_si_refresh_indy_code_enforcement`.`CASE_TYPE`** — Enforcement/Investigation/ 211,794 · Enforcement/Violation/High 152,050 · Enforcement/Investigation/ 145,521 · Enforcement/Investigation/ 78,437 · Enforcement/Violation/Buil 45,787 · Enforcement/Violation/Zoni 30,166 · Enforcement/Investigation/ 29,108
- **`in_si_refresh_indy_code_enforcement`.`CASE_STATUS`** — Closed 297,798 · Case Closed 137,735 · Closed, Reactive HWG 120,817 · Closed, No Violation 60,449 · Closed, VIO 60,397 · VIO-Closed 42,206 · Violation(s) Corrected 30,056
- **`in_si_refresh_sri_taxsale_in`.`saleType`** — F 62,760 · A 15,860 · C 4,851 · D 76
- **`in_si_refresh_sri_taxsale_in`.`saleTypeDescription`** — Foreclosure 62,760 · Tax Sale 15,860 · Certificate Sale 4,851 · Deed Sale 76
- **`in_si_refresh_sri_taxsale_in`.`saleStatusCode`** — FR-SPF 26,860 · FR-C 25,829 · D 15,860 · FR-STY 8,314 · C 4,927 · FR-SP 1,757
- **`in_si_refresh_warn_notices`.`Notice_Type`** — CL 564 · LO 415 · N/A 204 · Potential Closure 22 · RH 4 · TR 4 · CL -Relocating 1
- **`in_si_sites_flags_v2`.`si_signal_types`** — 0 79,304 · 1 21,922 · 2 959 · 3 248 · 4 10 · 5 1
- **`in_si_southbend_code_enforcement`.`Record_Type`** — Litter 9,382 · Grass and Weeds 7,710 · Vegetation 2,293 · Sub-standard Housing 619 · Secure Property 252 · Sub-standard Housing (lega 107 · Graffiti 51
- **`in_si_southbend_code_enforcement`.`Status`** — Closed 13,555 · Review Case for Collection 3,558 · Billed 1,268 · Notice Sent to Owner 1,009 · Abatement Pending 159 · None 107 · In Violation 100
- **`in_si_southbend_code_enforcement`.`Record_Status_Date`** — 1593388800000 487 · 1592784000000 369 · 1592870400000 365 · 1592179200000 353 · 1591056000000 330 · 1591660800000 324 · 1592265600000 302
- **`in_si_southbend_continuous_enforcement`.`ORDER_TYPE`** — HEARING 110 · Hearing 102 · Continuous Enforcement 23 ·  2 · hearing 2 · HEARNG 1 · Environmental Hearing 1
- **`in_si_southbend_vacant_abandoned`.`State_ID_LU_OutcomeStatus_Calc`** —  40 · Repaired 5 · Demolished 2
- **`in_si_sri_placed`.`sale_type`** — Tax Sale 15,106 · Foreclosure 11,991 · Certificate Sale 4,131
- **`in_si_sri_placed`.`sale_status`** — DELINQUENT 15,106 · Cancelled 5,506 · COUNTY 4,131 · Sold To 3rd Party 2,833 · Sold To Plaintiff 2,502 · Sale Active 1,150
- **`in_si_state_warn_notices`.`Notice_Type`** — CL 564 · LO 415 · N/A 204 · Potential Closure 22 · RH 4 · TR 4 · CL -Relocating 1
- **`in_site_gates`.`bonus_kinds`** — None 627,444 · coal_closure 156,035 · low_income_tract 88,606 · energy_community 62,814 · critical_habitat 29,037 · low_income_tract,qct 19,642 · qct,low_income_tract 19,605
- **`in_sites`.`site_kind`** — building 2,284,133 · no_structure 1,269,061
- **`in_sites`.`si_signal_types`** — 0 2,705,784 · 1 846,462 · 2 948
- **`in_sites`.`geom_kind`** — parcel_polygon 3,553,193 · none 1
- **`in_solar_pv_facilities`.`p_type`** — greenfield 110 · superfund 2 · PCSC 1 · landfill 1
- **`in_solar_pv_facilities`.`p_sys_type`** — ground 106 · rooftop 7 · canopy,rooftop 1
- **`in_storm_events`.`event_type`** — Thunderstorm Wind 4,669 · Hail 1,626 · Winter Weather 1,114 · Flood 755 · Winter Storm 621 · Flash Flood 531 · Tornado 401
- **`in_storm_events`.`cz_type`** — C 8,091 · Z 4,369
- **`in_storm_events`.`magnitude_type`** — None 7,071 · EG 4,708 · MG 680 · ES 1
- **`in_substations`.`substation_type`** — SUBSTATION 2,394 · None 738 · TAP 497 · industrial 76 · distribution 31 · DEAD END 29 · traction 21
- **`in_substations`.`status`** — IN SERVICE 2,890 · Status not published 968
- **`in_territories`.`utility_type`** — NOT AVAILABLE 74 · COOPERATIVE 40 · INVESTOR OWNED 17 · MUNICIPAL 14
- **`in_transmission_lines`.`volt_class`** — UNDER 100 1,124 · 100-161 982 · NOT AVAILABLE 270 · 345 190 · 220-287 47 · 735 AND ABOVE 10
- **`in_transmission_lines`.`type`** — AC; OVERHEAD 2,081 · OVERHEAD 510 · NOT AVAILABLE 30 · UNDERGROUND 1 · AC; UNDERGROUND 1
- **`in_transmission_lines`.`status`** — IN SERVICE 2,379 · NOT AVAILABLE 244
- **`in_transmission_union`.`volt_class`** — UNDER 100 1,124 · None 1,114 · 100-161 982 · NOT AVAILABLE 270 · 345 190 · 220-287 47 · 735 AND ABOVE 10
- **`in_transmission_union`.`status`** — IN SERVICE 2,379 · None 1,114 · NOT AVAILABLE 244
- **`in_tribal_land`.`classfp`** — D8 5 · D5 5 · D2 4
- **`in_txexp_miso_mtep_appendix_a_status`.`project_type`** — Other 170 · MVP 85 · BRP 49 · GIP 24
- **`in_txexp_miso_mtep_appendix_a_status`.`planning_status`** — M2 - Appendix A Approved 314 · M3 - Under Construction 14
- **`in_txexp_miso_mtep_appendix_a_status`.`facility_type`** — Substation 142 · Line Upgrade 86 · Line New 48 · Transformer 37 · Misc. 11 · Voltage Device 4
- **`in_urdb_rates`.`voltagecategory`** — None 561 · Secondary 172 · Primary 159 · Transmission 77
- **`in_urdb_rates`.`rate_type`** — flat 452 · tiered 329 · TOU 188
- **`in_utility_tariff_riders`.`component_type`** — eligibility 1 · rider 1 · base_charge 1
- **`in_utility_tariff_riders`.`value_status`** — not_held 2 · published 1
- **`in_water`.`ftype`** — 460 972,487 · 468 906,321 · 558 273,871 · 336 160,191 · 334 47,914 · 428 43,633 · 420 10,008
- **`in_water_aqueduct`.`w_awr_def_tot_weight_fraction`** — 0.836734693877551 54 · 0.9999999999999999 2
- **`in_water_aqueduct`.`w_awr_agr_tot_weight_fraction`** — 0.865546218487395 54 · 1 2
- **`in_water_aqueduct`.`w_awr_che_tot_weight_fraction`** — 0.9238095238095239 54 · 1 2
- **`in_wetlands`.`WETLAND_TYPE`** — Freshwater Pond 167,362 · Freshwater Forested/Shrub  108,313 · Riverine 89,906 · Freshwater Emergent Wetlan 84,364 · Lake 2,471 · Other 1,579
- **`in_workforce_ipeds_directory`.`inst_status`** — 1 102 · 5 8 · 8 1 · 4 1
- **`in_workforce_ipeds_directory`.`inst_category`** — 2 51 · 6 34 · -2 9 · 4 9 · 1 5 · 3 4
- **`in_workforce_ipeds_directory`.`cbsa_type`** — 1 89 · 2 20 · -2 3
