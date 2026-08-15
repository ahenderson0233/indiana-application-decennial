# BigQuery Indiana-applicability census — generated 2026-08-15

Method: metadata classification of every populated, non-backup, non-licensed `energy.*`
table by how its Indiana slice is reachable. Classes A-E are directly filterable;
F holds national/series grain applicable AT Indiana (prices, ISO series, weather);
G needs a schema read. **A name is never trusted — wiring requires a value-read per table.**

## A state keyed holds IN — 50 tables
- `cems_hourly` (1,009,316,568)
- `nhd_flowline` (39,542,980)
- `socrata_cook_bor_appeals` (6,933,428)
- `parcels_in` (3,637,663)
- `nfirs_basicincident_2024` (2,410,457)
- `nfirs_incidentaddress_2024` (2,410,457)
- `socrata_chicago_licenses` (1,201,485)
- `socrata_chicago_biz_licenses` (1,200,971)
- `ustp_ch7_tfr` (1,194,652)
- `agis_indy_code_enforcement` (910,483)
- `si_d12_indy_marion_code_enforcement` (910,483)
- `socrata_chicago_permits` (841,641)
- `eia861_service_territory` (280,398)
- `openstates_energy_bill_vote_people` (233,210)
- `si_d1_sri_taxsale_listings` (217,226)
- `parcels_mi_berrien_county` (86,267)
- `parcels_mi` (84,728)
- `parcels_mi_muskegon` (84,728)
- `parcels_mi_jackson` (78,038)
- `parcels_ga_lowndes` (66,316)
- `parcels_ky_kenton` (64,179)
- `warn_notices` (61,879)
- `parcels_mi_emmet_county` (44,764)
- `epa_brownfields` (44,134)
- `brownfields` (37,026)
- `parcels_ky_bullitt_county` (36,177)
- `parcels_ky_campbell_county` (36,017)
- `parcels_ky_campbell` (36,015)
- `si_signals_d19_pre_widen_20260803` (27,573)
- `si_d25_stb_abandonment_state` (15,815)
- `txexp_pjm_rtep_upgrades` (15,440)
- `parcels_tn_humphreys_county` (13,719)
- `parcels_ky_webster` (13,255)
- `parcels_ky_henry_county` (9,449)
- `parcels_ky_pendleton` (9,020)
- `txexp_miso_mtep_appendix_a_in_service` (5,183)
- `parcels_mi_ingham_county` (4,989)
- `coal_closure_communities` (4,325)
- `queue_miso` (3,794)
- `googlenews_dc_state` (3,598)
- `txexp_miso_mtep_appendix_a_status` (3,211)
- `eia861_reliability` (968)
- `nonattainment_areas` (792)
- `txexp_miso_mtep_under_evaluation` (597)
- `econ_gjf_megadeals` (535)
- `bingnews_dc_state` (469)
- `dc_eei_tariffs` (105)
- `gov_auction_gsa` (68)
- `utility_tariff_riders` (40)
- `state_irp_catalog` (18)

## B state keyed IN unverified by census — 666 tables
- `mat_parcel_key_index` (678,542,895)
- `fcc_bdc_fixed_availability` (512,987,355)
- `mat_parcel_grid` (179,048,266)
- `mat_parcel_all_v2` (170,442,382)
- `mat_parcel_geo` (157,427,563)
- `nat_usa_structures` (135,371,228)
- `si_d5_struct_pts` (135,338,769)
- `mat_parcel_all` (132,206,336)
- `mat_parcel_structures` (129,844,449)
- `mat_siting_parcels` (120,660,571)
- `mat_parcel_geo_supplement` (118,832,291)
- `mat_parcel_attrs` (107,325,274)
- `mat_parcel_grid_pre20260802` (104,408,388)
- `mat_parcel_geo_pre20260802` (93,149,409)
- `mat_si_plottable` (83,429,361)
- `mat_si_scored_v3` (83,429,361)
- `si_scored_v3_variants` (83,429,361)
- `mat_si_county_resolved` (73,642,672)
- `mat_structure_addr` (52,082,602)
- `si_d5_addr_pts` (52,082,602)
- `nwi_wetlands` (40,575,843)
- `si_d18_absentee_v2` (37,091,278)
- `si_d18_absentee` (37,091,272)
- `mat_si_scored_v2` (31,931,655)
- `mat_parcel_backfill` (29,725,913)
- `mat_hc_auto` (29,595,084)
- `socrata_ny_assessment_roll` (23,580,051)
- `mat_si_building_in_parcel` (23,354,741)
- `si_d5_vacancy_derived` (22,295,965)
- `socrata_ny_corp_filing_addresses` (18,115,040)
- `si_wire_stage` (17,643,229)
- `si_wire_new` (15,575,113)
- `mat_hc_v2_probe` (15,297,677)
- `parcels_tx` (14,347,625)
- `si_d9_underutilization_v2` (14,210,758)
- `si_d9_underutilization` (14,210,677)
- `parcels_fl` (10,831,924)
- `nhd_waterbody` (10,431,981)
- `mat_si_buildings` (9,363,898)
- `mat_si_buildings_v2` (9,363,898)
- `mat_si_scored` (9,363,898)
- `parcels_pa` (8,711,170)
- `ferc714_state_demand` (8,493,483)
- `parcels_nc` (5,960,515)
- `nfhl_flood_zones` (5,554,986)
- `mat_si_address_location` (5,549,105)
- `si_d11_entity_dissolution_v2` (4,702,667)
- `agis_scag_socal_landuse_zoning` (4,558,859)
- `si_d11_entity_dissolution` (4,558,265)
- `socrata_ny_active_corps` (4,249,686)
- `socrata_pa_entities` (4,026,643)
- `socrata_nyc_dob_permits` (3,989,483)
- `parcels_sc_abbeville_county` (3,975,962)
- `mat_si_rooftop_geocode` (3,960,225)
- `parcels_ny` (3,827,530)
- `parcels_wi` (3,562,907)
- `parcels_nj` (3,478,727)
- `socrata_tx_franchise_taxpayers` (3,408,799)
- `parcels_tx_harris` (3,051,050)
- `si_d8_exit_intent` (2,840,865)
- `parcels_mn` (2,708,126)
- `si_d12_dallas_ce_activities` (2,632,424)
- `socrata_nyc_dob_now` (2,561,292)
- `nfirs_basicincident_2023` (2,451,836)
- `nfirs_incidentaddress_2023` (2,451,836)
- `nfirs_basicincident_2022` (2,370,774)
- `nfirs_incidentaddress_2022` (2,370,774)
- `socrata_austin_permits` (2,366,139)
- `sba_foia_loans` (2,190,504)
- `mat_si_national_buildings` (2,110,183)
- `socrata_co_ucc_debtors` (2,005,102)
- `parcels_ca_sandiego` (1,848,759)
- `parcels_az_maricopa` (1,759,389)
- `parcels_al_regional_al_residential_parcel` (1,643,979)
- `socrata_or_entities` (1,565,971)
- `si_d11_business_closure_city` (1,404,445)
- `parcels_ct` (1,290,196)
- `socrata_ct_entities` (1,287,080)
- `parcels_ne` (1,154,898)
- `water_cwns_2022` (1,118,786)
- `parcels_or` (1,088,187)
- `spc_severe_events` (1,014,963)
- `si_d17_ny_oca_landlord_tenant_cases` (903,594)
- `si_d12_detroit_wayne_blight_tickets` (897,919)
- `agis_detroit_blight_tickets` (896,806)
- `socrata_ct_ucc` (843,134)
- `si_d12_la_city_ce_closed` (820,433)
- `socrata_kc_violations` (799,671)
- `si_d17_md_district_court_evict` (737,313)
- `si_d21_demolition` (722,394)
- `parcels_tx_bexar` (710,772)
- `parcels_me` (704,638)
- `storm_events` (688,406)
- `hca_sce_ica_load_ssv` (667,107)
- `eia860_generators` (666,179)
- `ckan_boston_permits` (658,435)
- `padus` (652,827)
- `faa_obstacles` (652,596)
- `nfirs_fireincident_2023` (644,317)
- `nfirs_fireincident_2022` (642,258)
- `nfirs_fireincident_2024` (586,714)
- `socrata_ny_tax_warrants` (563,729)
- `si_d22_probate_ownership` (534,937)
- `si_d27_ucc_lapse_v2` (530,671)
- `si_d27_ucc_lapse` (529,266)
- `echo_cwa_facilities` (524,512)
- `si_d2_il_cook_recorder_foreclosures` (511,173)
- `socrata_cook_recorder_foreclosures` (511,173)
- `parcels_tx_dallascity` (496,810)
- `fcc_bdc_provider_summary_by_geography` (488,179)
- `parcels_al` (479,544)
- `entities_va` (465,855)
- `land_padus` (439,860)
- `si_d12_charlotte_meck_ce_all` (430,174)
- `agis_mem_code_community` (403,623)
- `parcels_mo_stlouiscounty` (401,404)
- `parcels_al_jefferson_county` (400,517)
- `parcels_al_jefferson` (400,456)
- `osm_power_lines` (392,489)
- `parcels_hi` (384,035)
- `parcels_id` (381,144)
- `socrata_sf_business_locations` (364,420)
- `parcels_sc_spartanburg` (341,978)
- `parcels_ok_oklahoma` (336,992)
- `parcels_sc_greenville` (322,194)
- `gov_surplus_frpp` (307,919)
- `parcels_ok_tulsa` (297,762)
- `si_d17_ct_evict_tract_weekly` (294,462)
- `socrata_atx_cert_occupancy` (290,782)
- `eqr_identity` (288,794)
- `parcels_ga_cobb` (283,363)
- `parcels_nc_v2` (281,772)
- `parcels_il_lake` (278,882)
- `parcels_sc_lexington` (272,652)
- `parcels_sc` (270,772)
- `agis_ict_permits` (268,689)
- `eia_plants` (251,851)
- `socrata_buf_violations` (249,047)
- `parcels_sc_greenwood_county` (235,399)
- `parcels_ca_sanmateo` (235,348)
- `parcels_ca_sanfrancisco` (226,396)
- `socrata_or_ucc_secured` (220,610)
- `parcels_la_east_baton_rouge_parish` (205,820)
- `parcels_sc_cherokee_county` (195,448)
- `brownfield_epa_repowering` (190,976)
- `parcels_sc_saluda_county` (182,966)
- `socrata_neworleans_violations` (180,913)
- `parcels_tn` (167,781)
- `si_d2_mi_wayne_treasurer_taxforecl` (163,043)
- `si_d12_syracuse_onondaga_code_viol` (150,340)
- `parcels_il_stclair` (147,877)
- `parcels_ga_cobb_county` (143,857)
- `parcels_sc_marion_county` (141,815)
- `si_d12_tarrant_fw_codeops_2006_2019` (138,559)
- `parcels_il_madison` (136,701)
- `ghgrp_facilities` (136,005)
- `weather_stations` (132,501)
- `parcels_sc_lexington_county` (130,978)
- `parcels_ca_sanluisobispo` (130,611)
- `parcels_sc_edgefield_county` (129,226)
- `parcels_ga_chatham` (125,326)
- `parcels_tn_claiborne_county_multi` (123,939)
- `mat_grid_substations` (122,527)
- `si_d4_az_maricopa_delinquent_tax_parcels` (120,216)
- `hca_aep_hc_grid_load_all` (118,735)
- `hca_aep_im_mi_gen` (118,735)
- `hca_aep_im_mi_load` (118,735)
- `parcels_la_lafayette_parish` (117,084)
- `parcels_or_deschutes_county` (112,374)
- `parcels_sc_berkeley_county` (109,448)
- `ghgrp_emitter_facilities` (107,329)
- `parcels_la` (106,535)
- `parcels_mo_jefferson` (106,464)
- `parcels_sc_beaufort_county` (104,904)
- `parcels_ga_henry` (102,988)
- `state_bulk_sd_business_inactive` (102,727)
- `candidate_sites_schools` (102,178)
- `gov_surplus_nces` (102,178)
- `parcels_al_chilton_commercial` (101,319)
- `parcels_al_montgomery_commercial` (101,319)
- `parcels_ma__staging` (98,964)
- `agis_gso_code_violations` (98,696)
- `state_bulk_cha_codeviol` (98,320)
- `parcels_mo_clay_county` (98,112)
- `si_coverage_matrix` (93,757)
- `si_register` (93,757)
- `parcels_la_rapides_parish` (92,506)
- `mat_si_owners` (91,909)
- `osm_power_substations` (91,022)
- `parcels_il_peoria_county` (90,340)
- `parcels_tn_sevier_county` (88,395)
- `parcels_ca_imperial` (85,918)
- `acs_tract_vacancy` (85,382)
- `census_tracts` (85,060)
- `si_d17_ma_trial_court_civil_filings` (84,996)
- `parcels_ok_canadian` (84,792)
- `parcels_ga_richmond` (84,575)
- `socrata_austin_violations` (82,577)
- `parcels_tn_johnson_county` (78,891)
- `si_d2_md_prince_georges_foreclosures` (78,657)
- `socrata_tx_tabc_licenses` (78,042)
- `parcels_tn_sullivan_county` (77,462)
- `hca_luma_incremental_apr25` (77,231)
- `parcels_ga_fayette_county` (76,106)
- `wind_turbines` (75,727)
- `nat_substations_hifld` (75,328)
- `substations` (75,328)
- `si_d12_tarrant_fw_code_violations_current` (75,172)
- `parcels_mi_dickinson_county_multi` (72,142)
- `parcels_ga_bibb_county` (68,731)
- `parcels_tn_blount_county` (67,312)
- `parcels_il_rockisland` (65,958)
- `parcels_mo` (65,577)
- `parcels_tn_cumberland_county` (65,395)
- `parcels_ca_nevada` (64,381)
- `parcels_sc_richland_county` (64,131)
- `parcels_ga_coweta` (64,060)
- `parcels_id_bonneville_county` (63,803)
- `si_d17_az_maricopa_evict_pts_2019` (63,673)
- `si_d17_az_maricopa_evict_pts_2018` (63,163)
- `agis_indy_taxsale` (62,368)
- `parcels_sc_orangeburg_county` (61,942)
- `parcels_al_stclair` (61,242)
- `parcels_ky_warren` (60,753)
- `fema_disaster_declarations` (60,624)
- `parcels_la_ascension_parish` (60,072)
- `si_d17_az_maricopa_evict_pts_2017` (59,939)
- `state_bulk_sd_business_active` (59,719)
- `parcels_mo_buchanan_county` (59,374)
- `agis_gso_demo_permits` (59,260)
- `si_d17_az_maricopa_evict_pts_2016` (58,427)
- `si_d17_az_maricopa_evict_pts_2015` (58,391)
- `parcels_ok_rogers_county` (57,197)
- `parcels_ga_douglas` (55,769)
- `carto_philly_tax_delinquency` (54,401)
- `parcels_tn_maury_county` (53,040)
- `si_d4_tx_harris_delinquent_parcels_2025` (52,863)
- `si_d4_tx_harris_delinquent_parcels_2025_points` (52,863)
- `parcels_ok_wagoner_county` (52,685)
- `si_signals_d19_new_20260803` (52,507)
- `socrata_sf_evictions` (48,734)
- `si_d2_oh_cuyahoga_property_status_current` (48,159)
- `parcels_ky_hardin_county` (48,129)
- `parcels_ky_daviess` (48,023)
- `parcels_ok_creek_county` (45,862)
- `parcels_id_bannock_county` (45,834)
- `si_d2_oh_cuyahoga_property_status` (45,689)
- `openstates_energy_bill_actions` (44,774)
- `parcels_ga_jackson` (44,769)
- `parcels_or_umatilla` (44,752)
- `parcels_la_st_martin_parish` (44,228)
- `si_d4_md_baltimore_city_taxlien_cert` (43,736)
- `si_d12_virginia_beach_ce_cases` (42,294)
- `parcels_or_josephine_county` (41,990)
- `parcels_ga_clarke` (41,989)
- `parcels_ga_clarke_county` (41,989)
- `parcels_la_desoto_parish` (41,956)
- `si_d2_co_denver_foreclosures` (41,840)
- `parcels_ks` (41,779)
- `agis_nor_vb_code_enforcement` (41,117)
- `parcels_ga_union` (40,901)
- `parcels_mo_stfrancois` (40,645)
- `agis_mem_code_environ` (39,901)
- `eia860m_generators` (39,517)
- `parcels_mo_capegirardeau` (39,359)
- `parcels_tn_anderson_county` (38,213)
- `interconnection_queue` (38,201)
- `lbnl_interconnection_queue` (38,201)
- `si_d17_or_landlord_tenant_county_daily` (37,400)
- `socrata_nola_biz_licenses` (37,365)
- `agis_sac_business_tax_lapsed` (37,308)
- `state_bulk_gwinnett_delinquent` (37,297)
- `si_d4_il_cook_ssmma_delinquent` (36,660)
- `mat_si_coord_reject_v2` (36,515)
- `parcels_ga_rockdale` (36,514)
- `mat_si_coord_reject` (36,355)
- `parcels_or_clatsop_county` (35,452)
- `parcels_tn_jefferson_county` (35,343)
- `parcels_ks_butler_county` (34,592)
- `si_d17_az_maricopa_evict_pts_2020` (34,316)
- `parcels_ga_effingham` (34,089)
- `si_wire_zip_county` (33,750)
- `si_d17_tx_oca_lt_2023_2026` (33,737)
- `agis_hfd_code_enforcement` (33,304)
- `si_d2_az_maricopa_foreclosures_monthly_points` (33,029)
- `parcels_tn_coffee_county` (32,198)
- `ckan_pgh_tax_delinquency` (31,908)
- `parcels_tn_mcminn_county` (31,430)
- `si_d12_baltimore_city_ce_citations` (31,008)
- `agis_baltimore_code` (30,987)
- `si_d12_lasvegas_clark_code_violations` (28,505)
- `si_d2_ga_fulton_tax_deed_activity` (28,499)
- `eia923_fuel_receipts_costs` (28,074)
- `si_d2_oh_stark_historic_foreclosures` (27,716)
- `si_d2_ca_alameda_foreclosures` (27,590)
- `socrata_kc_business_license` (26,646)
- `si_d4_tn_shelby_trustee_delinquent` (26,386)
- `ut_tax_liens_v2` (26,345)
- `parcels_tn_lawrence_county` (26,039)
- `parcels_al_lauderdale_commercial` (26,037)
- `parcels_al_lawrence_commercial` (26,037)
- `parcels_tn_giles_county` (26,037)
- `si_d4_oh_cuyahoga_certified_delinquent` (25,957)
- `parcels_mo_washington` (25,605)
- `parcels_ks_riley_county` (25,314)
- `parcels_tn_cocke_county` (25,311)
- `si_d12_pg_md_housing_viol` (25,204)
- `parcels_ok_pottawatomie_county` (24,756)
- `parcels_ga_thomas` (24,753)
- `parcels_il_boone` (24,379)
- `iso_interconnection_queue` (24,030)
- `parcels_sd_lawrence_county` (23,790)
- `parcels_ga_bryan_county` (22,965)
- `parcels_ky_franklin_county` (22,628)
- `candidate_sites_private_schools` (22,510)
- `parcels_tn_marion_county` (22,347)
- `si_d17_oh_fed_county_month` (22,313)
- `socrata_buf_rental_registry` (22,146)
- `parcels_or_curry_county` (21,918)
- `parcels_ga_baldwin` (21,876)
- `parcels_tn_hardeman_county_multi` (21,756)
- `fcc_bdc_mobile_summary_by_geography` (20,784)
- `gas_phmsa_distribution` (20,584)
- `si_d4_il_cook_ssmma_1yr_delinquent` (20,042)
- `openstates_energy_bill_sponsorships` (19,769)
- `ckan_mke_tax_delinquent_re` (19,639)
- `eia861_demand_response` (19,328)
- `gas_eia_state_capacity` (19,311)
- `si_d17_ga_clarke_dispossessory_papers` (18,976)
- `parcels_sd_codington` (18,456)
- `si_d2_az_maricopa_trustee_sales` (18,442)
- `agis_lou_code_enforcement_cases` (18,317)
- `si_d2_oh_hamilton_cincinnati_taxforecl` (18,226)
- `ut_tax_liens` (18,050)
- `parcels_ga_bryan` (17,984)
- `parcels_id_madison_county` (17,733)
- `parcels_la_allen_parish` (17,706)
- `parcels_ky_franklin` (17,415)
- `ckan_boston_violations` (17,378)
- `si_d4_oh_stark_certified_delinquent` (17,274)
- `si_d4_il_cook_ssmma_3yr_delinquent` (17,214)
- `parcels_sd_beadle` (16,889)
- `si_d17_az_jp_eviction_court_month` (16,739)
- `parcels_ca_trinity` (16,641)
- `parcels_tn_carroll_county_multi` (16,542)
- `si_d17_fl_osca_county_civil` (16,482)
- `parcels_ok_beckham_county` (16,445)
- `si_d4_va_virginiabeach_delinquent_re` (16,401)
- `si_d4_oh_mahoning_youngstown_tax_delinquent` (16,364)
- `parcels_al_hale_commercial` (16,346)
- `parcels_al_hale_county` (16,346)
- `parcels_ok` (15,741)
- `incentive_qct` (15,727)
- `parcels_ca_glenn` (15,167)
- `si_d4_il_cook_ssmma_taxsale_2019` (15,013)
- `parcels_id_teton_county` (14,920)
- `parcels_ca_mariposa` (14,276)
- `parcels_mo_perry` (14,198)
- `si_d17_montgomery_md_lt_disputes` (13,950)
- `si_d4_al_jefferson_tax_delinquent_2020` (13,925)
- `ckan_pgh_sheriff_sales` (13,452)
- `power_plants` (13,446)
- `parcels_ga_brantley_county` (13,301)
- `si_d17_az_maricopa_evictions_2023_monthly` (12,952)
- `miso_poi_headroom` (12,845)
- `agis_thirty34jb_zoning_z` (12,730)
- `parcels_la_cameron_parish` (11,918)
- `parcels_or_hood_river_county` (11,870)
- `si_d4_az_cochise_tax_lien_parcels` (11,643)
- `agis_wsnc_forecl` (11,564)
- `si_d4_pa_pittsburgh_delinquent_3yr` (11,423)
- `si_d12_hillsborough_fl_ce_active` (10,991)
- `parcels_or_harney_county` (10,935)
- `si_d4_md_baltimore_city_taxsale_props2` (10,921)
- `socrata_buf_demo_permits` (10,819)
- `agis_krivera_laurinburg_zoning_scotland_county_public_view_z` (10,632)
- `parcels_ga_cook_county` (10,432)
- `parcels_ga_brooks_county` (10,037)
- `openstates_energy_bill_versions` (9,949)
- `si_d4_ca_sonoma_defaulted_tax` (9,787)
- `socrata_sonoma_defaulted_tax` (9,787)
- `si_d4_nc_guilford_tax_delinquent` (9,749)
- `parcels_ky_bourbon_county` (9,537)
- `parcels_sd_yankton_county` (9,458)
- `si_d4_nc_pitt_delinquent_taxes` (9,143)
- `socrata_mo_asbestos_abatement_notif` (9,031)
- `incentive_opportunity_zones` (8,765)
- `tx_dc_documents` (8,755)
- `parcels_al_shelby_county` (8,717)
- `parcels_al_st_clair_commercial` (8,717)
- `socrata_buf_zoning_approvals` (8,616)
- `si_d1_ar_cosl_taxsale` (8,522)
- `parcels_mo_christian_county` (8,432)
- `ckan_pgh_business_licenses` (8,421)
- `si_d17_il_eviction_county_quarter` (8,160)
- `parcels_tn_dyer_county` (8,043)
- `si_d2_oh_cuyahoga_bor_forecl_eligible` (7,963)
- `si_d2_oh_cuyahoga_bor_foreclosure_eligible` (7,963)
- `si_d1_ms_sos_tax_forfeited` (7,349)
- `parcels_ga_dooly_county` (7,344)

## C iso rto keyed MISO or PJM — 5 tables
- `eia930_subregion_demand` (5,833,728)
- `iso_forecast` (1,037,917)
- `iso_shadow_prices` (852,497)
- `iso_capacity_prices` (10)
- `dc_large_load_indicators` (6)

## D county or geoid keyed — 79 tables
- `parcels_va` (4,170,691)
- `parcels_co` (3,659,520)
- `parcels_ar` (3,595,560)
- `parcels_wa` (3,321,859)
- `parcels_tx_collin` (851,692)
- `parcels_nd` (742,102)
- `socrata_tx_collin_cad_appeals` (635,845)
- `agis_wa_waza_statewide` (470,130)
- `socrata_nyc_storefront_vacancy` (414,884)
- `socrata_nyc_asbestos_acp7` (395,278)
- `parcels_tn_davidson_county` (286,829)
- `parcels_ca_ventura` (267,881)
- `workforce_ipeds_cs_eng` (264,810)
- `parcels_nm_l00` (255,181)
- `block_groups` (241,893)
- `socrata_nyc_hpd_litigations` (239,434)
- `parcels_nm_l32` (199,659)
- `agis_cle_citywide_property_survey_2022` (162,675)
- `parcels_la_acadia_parish` (153,939)
- `parcels_nm_l23` (149,777)
- `agis_tus_code_violations_hcd` (131,771)
- `socrata_nyc_evictions` (130,989)
- `parcels_nm_l16` (115,161)
- `parcels_nm_l07` (92,188)
- `parcels_nm_l26` (87,313)
- `socrata_hfd_evictions_ct` (78,660)
- `socrata_bdr_evictions_ct` (74,898)
- `dim_jurisdiction` (71,989)
- `socrata_stk_permits` (67,469)
- `parcels_gu` (67,119)
- `parcels_nm_l29` (61,148)
- `ckan_pittsburgh_violations` (53,123)
- `parcels_nm_l08` (52,868)
- `parcels_nm_l19` (50,323)
- `parcels_ok_muskogee_county` (49,123)
- `parcels_nm_l04` (47,584)
- `parcels_nm_l09` (44,779)
- `parcels_nm_l24` (44,690)
- `parcels_nm_l14` (38,607)
- `parcels_nm_l21` (37,926)
- `parcels_nm_l28` (36,101)
- `parcels_nm_l02` (35,727)
- `low_income_bonus_tracts` (35,423)
- `parcels_nm_l13` (32,096)
- `parcels_nm_l25` (29,545)
- `parcels_nm_l30` (29,043)
- `parcels_nm_l05` (26,067)
- `parcels_sd_minnehaha` (23,004)
- `parcels_nm_l03` (22,778)
- `agis_lou_pm_case_occupancy` (20,691)
- `parcels_ks_lyon_county` (17,248)
- `parcels_nm_l22` (14,580)
- `parcels_nm_l20` (14,518)
- `parcels_nm_l17` (12,945)
- `parcels_nm_l27` (12,178)
- `parcels_nm_l01` (11,776)
- `parcels_nm_l15` (8,552)
- `cbp_county_industry` (7,810)
- `parcels_nm_l18` (7,471)
- `parcels_nm_l12` (5,210)
- `socrata_nyc_aep_buildings` (4,387)
- `parcels_nm_l10` (3,800)
- `usa_structures_county` (3,235)
- `acs_county` (3,222)
- `parcels_nm_l31` (2,962)
- `agis_tylercreedle_gis_zoning_z` (2,323)
- `parcels_nm_l06` (1,638)
- `parcels_nm_l11` (1,074)
- `tribal_land` (858)
- `agis_fre_tent_subdiv` (623)
- `socrata_kc_mva_distress` (440)
- `agis_stpaul_vacant` (384)
- `persistent_poverty_counties` (318)
- `agis_lou_demolitions` (175)
- `agis_bna_blight_tracts` (171)
- `civic_client_county` (164)
- `agis_lv_blighted_properties` (118)
- `agis_lou_metro_foreclosure` (105)
- `agis_rva_city_evict` (66)

## E spatial only — 1012 tables
- `mat_hc_infrastructure` (37,972,692)
- `mat_hc_map` (25,321,913)
- `socrata_nyc_hpd_violations` (11,126,984)
- `parcels_oh` (6,313,610)
- `parcels_ca_losangeles` (4,843,940)
- `hca_lgeku_summary_table` (4,573,300)
- `parcels_ma` (4,374,510)
- `miso_poi_capacity_surface_geotiff` (3,390,912)
- `socrata_dallas_311` (3,071,651)
- `parcels_ut` (2,895,997)
- `parcels_ia` (2,450,589)
- `parcels_md` (2,288,725)
- `parcels_tn_statewide` (2,138,531)
- `socrata_chicago_violations` (2,018,902)
- `carto_philly_violations` (1,996,197)
- `hca_ameren_il_load_ev` (1,673,756)
- `hca_ameren_il` (1,673,535)
- `hca_ameren_il_hc_jul2026` (1,671,553)
- `hca_ameren_il_hc_refresh` (1,671,052)
- `parcels_wv` (1,401,628)
- `parcels_nv` (1,394,188)
- `hca_pge` (1,319,715)
- `hca_pge_drp_linedetail` (1,311,858)
- `parcels_ms_east` (1,127,050)
- `hca_phi_section_level_pv` (1,092,129)
- `state_bulk_sd_dev_approvals` (1,065,830)
- `parcels_il_cook` (1,055,344)
- `socrata_montgomerymd_violations` (951,152)
- `parcels_mt` (920,897)
- `hca_cmp_hc_ev_non3phase_prededup_bak` (905,986)
- `miso_poi_monitored_facilities` (904,486)
- `parcels_ca_riverside` (895,417)
- `parcels_ms` (878,999)
- `parcels_ca_sanbernardino` (835,910)
- `parcels_mi_wayne` (768,119)
- `hca_cmp_hc_ev_non3phase` (767,986)
- `socrata_cincinnati_violations` (762,578)
- `operating_generators` (755,532)
- `hca_pge_partial_pre20260803` (734,746)
- `hca_eversource_ct_dg` (729,527)
- `mat_si_coords` (728,805)
- `parcels_ca_orange` (707,542)
- `hca_sce_hosted_ica_layer_0` (676,467)
- `hca_sce_hosted_ica_layer_2` (676,467)
- `hca_sce` (667,107)
- `hca_sce_ica_load_thermal` (667,107)
- `hca_sce_ica_load_vv` (667,107)
- `hca_sce_ica_uniform_load` (665,107)
- `hca_eversource_ct_ev` (663,775)
- `hca_pge_drp_feeder_load_profile` (640,224)
- `agis_king_co_parcels` (638,777)
- `hca_sce_hosted_ica_layer_1` (636,356)
- `parcels_nh` (617,124)
- `fcc_bdc_fixed_summary_by_geography` (616,170)
- `hca_idaho_power_injection_line` (603,733)
- `hca_bge_pv_capacity_wfl1_l1` (598,521)
- `hca_bge_targeted_energy_storage_bess_suitability` (598,521)
- `hca_sce_ica_circuit_segments_ica_layer_3` (533,007)
- `parcels_sc_charleston_tri` (527,684)
- `hca_xcel_psco_conductors_gen` (526,305)
- `hca_sce_ica_circuit_segments_ica_layer_2` (524,522)
- `hca_avista_der_hosting_capacity` (508,514)
- `hca_dominion_residential_eb_2026` (503,597)
- `hca_dominion_residential_tx` (503,597)
- `hca_eversource_ma_east_dg` (502,075)
- `parcels_ca_sacramento` (502,074)
- `hca_sdg_e_generationcapacitygrids` (497,700)
- `hca_sdg_e_loadcapacitygrids` (497,700)
- `agis_cle_violation_status_history` (496,414)
- `parcels_mi_oakland_county` (490,652)
- `parcels_ca_alameda` (489,766)
- `hca_firstenergy_oh_xfmr` (478,146)
- `hca_natgrid_ny_nysdp_primary_hc` (452,496)
- `hca_national_grid_niagara_mo_ny_hc_nysdp_hosting_capacity_data_2` (452,496)
- `parcels_de` (450,684)
- `parcels_az_l10` (445,971)
- `gips_poi_studies` (437,998)
- `carto_philly_business_licenses` (432,860)
- `parcels_ca_kern` (421,684)
- `parcels_ak` (414,777)
- `hca_lgeku_poi_mw_violations` (405,005)
- `socrata_la_permits` (402,055)
- `agis_minneapolis_demo` (399,772)
- `parcels_ri` (394,167)
- `hca_eversource_nh_dg` (390,774)
- `parcels_tx_travis` (386,682)
- `parcels_wy` (373,666)
- `agis_fulton_parcels` (373,004)
- `parcels_ga_fulton` (373,004)
- `agis_minneapolis_code` (364,851)
- `hca_nyseg_rg_e_avangrid_pv` (356,211)
- `hca_nyseg_rg_e_avangrid_storage_bess` (352,874)
- `parcels_vt` (343,708)
- `parcels_il_dupage_county` (337,324)
- `parcels_il_dupage` (337,231)
- `parcels_mi_macomb` (332,795)
- `parcels_al_mobile_county` (329,383)
- `parcels_ga_gwinnett` (308,844)
- `hca_central_hudson_pv_stage_3` (306,419)
- `hca_central_hudson_storage_bess` (306,380)
- `hca_central_hudson_load_electrification` (306,359)
- `parcels_sc_horry` (300,582)
- `parcels_ca_fresno` (296,449)
- `parcels_mo_jackson` (295,982)
- `parcels_ky_jefferson` (293,209)
- `parcels_ky_anderson_county_multi` (292,993)
- `hca_smeco_circuits_2024` (292,971)
- `hca_pse_g_load_ev` (287,307)
- `hca_pse_g_solar` (284,726)
- `parcels_az_l11` (284,018)
- `parcels_sc_jasper_county` (282,789)
- `agis_lr_permits` (277,895)
- `agis_dc_business_license` (268,511)
- `parcels_az_l08` (266,190)
- `parcels_ca_sanjoaquin` (252,652)
- `mat_si_philly_parcels` (252,573)
- `parcels_ga_dekalb` (246,602)
- `socrata_seattle_code_complaints` (245,647)
- `socrata_seattle_violations` (245,093)
- `parcels_ks_sedgwick_county` (240,383)
- `parcels_mi_kent` (232,007)
- `hca_xcel_nsp_jun2026` (224,529)
- `parcels_sc_york` (220,536)
- `hca_jcp_l_pv` (218,655)
- `hca_heco_evload_oahu` (216,323)
- `parcels_al_mobile_commercial` (213,762)
- `hca_jcpl_ev_hosting` (213,068)
- `hca_ladwp_power_capacity` (211,078)
- `hca_jcp_l_load_ev` (210,397)
- `hca_peco_available_distribution_capacity_peco_available_distribution_capacity_map_1` (208,141)
- `hca_xcel_psco_conductors_load` (206,337)
- `parcels_al_madison` (205,887)
- `hca_central_maine_power_avan_me_queue` (204,541)
- `hca_central_maine_power_avangrid_pv_dg` (204,541)
- `hca_central_maine_power_load_ev` (200,482)
- `parcels_ga_camden` (200,217)
- `parcels_ca_placer` (199,545)
- `agis_miami_business_tax` (193,868)
- `socrata_seattle_permits` (191,598)
- `parcels_il_kane_county` (189,264)
- `parcels_ca_sonoma` (189,239)
- `parcels_il_kane_county_v2` (189,235)
- `socrata_nola_adjud_fines` (188,239)
- `parcels_az_l13` (186,960)
- `parcels_il` (185,393)
- `agis_mn_gov_owned_lands` (185,175)
- `hca_pge_drp_sub_load_profile` (183,984)
- `hca_peco_der_interconnect_viability_peco_der_interconnect_viability_hosted_3` (179,561)
- `hca_heco` (175,783)
- `hca_xcel_psco_gen_mar2026` (169,248)
- `parcels_ca_stanislaus` (168,657)
- `parcels_la_calcasieu_parish` (167,938)
- `hca_xcel_mn` (164,355)
- `parcels_ca_tulare` (164,055)
- `parcels_mo_st_charles_county` (161,860)
- `parcels_or_lane_county` (159,129)
- `parcels_la_jefferson_parish` (155,144)
- `hca_coned_structure_hcv` (154,883)
- `parcels_ca_solano` (153,287)
- `parcels_la_orleans_parish` (151,249)
- `socrata_parcels_la_orleans_parish` (151,249)
- `hca_bge_pv_capacity_wfl1` (150,222)
- `parcels_il_mchenry_county` (150,087)
- `agis_syr_codeviol` (150,077)
- `parcels_ga` (143,466)
- `hca_national_grid_ma_nodal_hosting_capacity_masdp_nodal_hosting_capacity_ma_2` (143,066)
- `hca_heco_evload_hawaii` (139,657)
- `hca_heco_evload_maui` (139,303)
- `parcels_dc` (137,400)
- `parcels_la_st_tammany_parish` (135,083)
- `parcels_mo_st_louis_city` (134,374)
- `parcels_ca_santabarbara` (132,504)
- `hca_o_r_reco_northern_nj_pv_oru_nodalhcv_prod_1` (129,875)
- `hca_orange_rockland_o_r_load_ev_oru_evm_feeders_prod_2` (129,875)
- `parcels_mi_washtenaw_county` (123,758)
- `agis_sac_code_violations` (123,709)
- `parcels_mo_greene` (123,685)
- `parcels_ca_monterey` (123,631)
- `parcels_az_l01` (122,935)
- `parcels_al_cullman` (119,959)
- `parcels_mi_ottawa` (118,105)
- `hca_heco_helco` (117,739)
- `parcels_sc_bamberg_county` (116,491)
- `parcels_or_marion_county` (115,870)
- `carto_philly_permits` (115,615)
- `parcels_sc_calhoun_county` (114,947)
- `agis_or_dlcd_statewide` (114,823)
- `parcels_ky_fayette` (114,295)
- `parcels_ca_eldorado` (113,595)
- `parcels_ga_forsyth` (105,152)
- `parcels_al_montgomery_county` (104,809)
- `parcels_ca_alpine` (104,332)
- `parcels_mo_greene_county` (103,295)
- `parcels_tn_houston_county_multi` (103,155)
- `hca_eversource_ma_west_dg` (100,979)
- `parcels_mi_kalamazoo` (100,505)
- `parcels_ga_berrien_county_multi` (100,028)
- `parcels_sc_allendale_county` (99,842)
- `hca_xcel_psco` (97,699)
- `parcels_ca_santacruz` (97,180)
- `parcels_ca_shasta` (97,156)
- `parcels_az_l14` (96,848)
- `agis_cle_rental_registrations` (96,561)
- `parcels_ca_marin` (96,235)
- `parcels_ca_butte` (95,858)
- `hca_potomac_edison_pv_md` (95,731)
- `hca_xcel_psco_load_mar2026` (94,887)
- `transmission_lines` (94,216)
- `hca_united_illuminating_bess_charging` (93,647)
- `hca_united_illuminating_load_ev` (93,647)
- `hca_united_illuminating_avangrid_dg_pv` (93,556)
- `hca_united_illuminating_bess_discharging` (91,867)
- `parcels_mi_lenawee_county` (90,426)
- `hca_orange_rockland_o_r_load_ev_oru_evm_feeders_prod_0` (90,400)
- `hca_orange_rockland_o_r_load_ev_oru_evm_feeders_prod_1` (90,400)
- `hca_orange_rockland_o_r_storage_bess_oru_ev_storage_prod_0` (90,400)
- `hca_orange_rockland_o_r_storage_bess_oru_ev_storage_prod_1` (90,400)
- `parcels_ca_merced` (89,549)
- `hca_o_r_reco_northern_nj_pv_oru_nodalhcv_prod_0` (88,930)
- `hca_oru_iedr_substation` (88,930)
- `subcap_oru_nodal` (88,930)
- `hurdat2_tracks` (87,631)
- `parcels_sc_laurens_county` (86,914)
- `parcels_az_l09` (86,380)
- `parcels_sd_custer_county` (85,094)
- `parcels_sd_pennington` (85,094)
- `railroads` (83,926)
- `hca_con_edison_nodal_substation_system_data_cecony_nodalhcv_prod_0` (82,810)
- `subcap_coned_nodal` (82,810)
- `hca_con_edison_cecony_load_ev_cecony_evm_feeders_prod_0` (82,809)
- `hca_con_edison_cecony_load_ev_cecony_evm_feeders_prod_1` (82,809)
- `hca_con_edison_cecony_storage_bess_cecony_ev_storage_prod_0` (82,809)
- `hca_con_edison_cecony_storage_bess_cecony_ev_storage_prod_1` (82,809)
- `parcels_sc_union_county` (81,538)
- `parcels_mo_jasper_county` (81,484)
- `parcels_al_morgan` (81,122)
- `state_bulk_sd_get_it_done` (80,027)
- `parcels_az_l02` (78,368)
- `parcels_al_etowah` (78,021)
- `agis_ict_codeviol` (77,338)
- `parcels_ks_shawnee_county` (76,979)
- `parcels_la_tangipahoa_parish` (76,235)
- `parcels_ga_bartow_county` (74,446)
- `hca_duke_carolinas_gen_nov2025` (74,367)
- `parcels_ca_mendocino` (74,086)
- `hca_duke_carolinas_gen` (73,970)
- `parcels_mo_boone` (73,814)
- `parcels_mi_eaton_county` (72,894)
- `parcels_ca_humboldt` (72,720)
- `parcels_sc_georgetown_county` (71,840)
- `parcels_ga_muscogee` (71,785)
- `socrata_br_ebr_blight_311` (71,715)
- `agis_kevin_hill_sumtercountygis_unincorporated_zoning_z` (70,923)
- `hca_firstenergy_oh_battery` (70,912)
- `hca_firstenergy_oh_gen` (70,912)
- `hca_firstenergy_oh_load` (70,912)
- `parcels_il_dekalb_county` (70,794)
- `hca_consumers_mi_res9` (69,500)
- `parcels_ga_bibb` (68,899)
- `parcels_or_douglas_county` (68,876)
- `water_aqueduct` (68,506)
- `parcels_ks_wyandotte_county` (67,922)
- `parcels_al_dekalb_county_multi` (67,832)
- `hca_duke_transmission` (66,359)
- `parcels_ca_yolo` (66,143)
- `parcels_ga_columbia` (66,097)
- `socrata_chicago_demo_permits` (65,945)
- `parcels_vi` (65,586)
- `parcels_sc_lancaster_county` (65,538)
- `parcels_sc_lee_county` (64,768)
- `ckan_pgh_demolition_permits` (64,029)
- `parcels_ca_lake` (63,858)
- `parcels_sc_dillon_county` (63,096)
- `parcels_ok_mccurtain_county_multi` (62,591)
- `parcels_la_st_landry_parish` (62,078)
- `parcels_or_klamath_county` (61,228)
- `hca_ladwp_fit_4_5kv` (60,588)
- `parcels_ok_cleveland` (60,250)
- `agis_lou_planning_applications` (58,376)
- `parcels_pr_ponce_municipio` (57,789)
- `parcels_az_l00` (57,679)
- `parcels_il_adams_county` (57,570)
- `parcels_ca_madera` (57,468)
- `parcels_al_talladega` (57,181)
- `parcels_il_macon` (57,044)
- `agis_zpemberton_zoning_z` (56,267)
- `parcels_ok_comanche_county` (56,109)
- `parcels_al_elmore` (55,750)
- `parcels_la_terrebonne_parish` (55,564)
- `parcels_al_lauderdale` (55,254)
- `parcels_ky_boone` (54,873)
- `parcels_or_linn_county` (54,600)
- `gips_duke_dec` (53,910)
- `parcels_ca_siskiyou` (53,566)
- `parcels_al_lauderdale_county_multi` (53,479)
- `parcels_tn_bradley_county` (53,161)
- `parcels_al_elmore_commercial` (52,831)
- `parcels_al_elmore_county` (52,831)
- `parcels_sd_custer_county_multi` (52,547)
- `parcels_ca_napa` (51,237)
- `parcels_al_limestone_county` (50,073)
- `parcels_ca_kings` (50,030)
- `parcels_al_baldwin_commercial` (48,789)
- `parcels_sc_darlington_county` (48,548)
- `parcels_mo_callaway_county_multi` (48,334)
- `parcels_sc_chester_county` (48,226)
- `agis_agol_data_publisher_zoning_classifications_z` (48,190)
- `parcels_mi_barry_county` (48,124)
- `parcels_al_jackson_commercial` (47,991)
- `parcels_mo_taney_county` (47,556)
- `parcels_or_lincoln_county` (46,852)
- `parcels_ga_glynn` (46,392)
- `parcels_mi_cheboygan_county` (45,200)
- `parcels_mo_platte` (45,150)
- `parcels_sc_clarendon_county` (45,126)
- `parcels_al_blount` (44,177)
- `hca_con_edison_cecony_load_ev_cecony_evm_feeders_prod_2` (43,657)
- `hca_con_edison_nodal_substation_system_data_cecony_nodalhcv_prod_1` (43,657)
- `hca_nyseg_nodal_hfs` (43,595)
- `parcels_ca_tuolumne` (43,589)
- `parcels_ca_calaveras` (43,450)
- `parcels_or_yamhill_county` (43,227)
- `parcels_az_l12` (43,189)
- `parcels_ca_tehama` (43,096)
- `parcels_or_coos_county` (42,056)
- `hca_peco_der_interconnect_viability_peco_der_interconnect_viability_hosted_5` (39,910)
- `parcels_az_l03` (39,656)
- `parcels_ky_madison` (39,129)
- `parcels_ok_payne_county_v2` (38,426)
- `parcels_ca_lassen` (38,319)
- `parcels_ga_dougherty` (38,007)
- `parcels_ga_dougherty_county` (38,005)
- `parcels_ga_bulloch` (37,968)
- `hca_bge_bge_hosting_capacity_agol_37` (37,704)
- `hca_bge_ev_substation_l4` (37,704)
- `hca_bge_load_ev_bge_ev_load_capacity_1` (37,704)
- `hca_bge_pv_hc_agol_45` (37,704)
- `parcels_or_benton_county` (37,694)
- `parcels_sc_colleton_county` (37,598)
- `parcels_tn_putnam_county` (37,134)
- `parcels_al_limestone` (36,870)
- `parcels_ca_yuba` (36,590)
- `parcels_il_whiteside` (36,530)
- `parcels_ca_sutter` (36,128)
- `hca_coned_iedr_substation` (35,888)
- `parcels_or_polk_county` (35,305)
- `parcels_sd_brookings_county` (34,764)
- `hca_pge_drp_known_load` (34,600)
- `parcels_la_st_charles_parish` (34,253)
- `parcels_mo_boone_county_multi` (34,167)
- `parcels_mo_cole` (34,167)
- `parcels_ga_troup` (33,879)
- `gas_pipelines_hifld` (33,806)
- `natural_gas_pipelines` (33,806)
- `hca_sdge_dupr_planned` (33,752)
- `agis_cityofedinburg_coe_zoning_districts_z` (33,685)
- `parcels_ok_payne_county` (33,322)
- `gas_pipelines` (32,892)
- `agis_mapdepartment_zoning_z` (32,691)
- `parcels_al_autauga_commercial` (32,341)
- `parcels_tn_carter_county` (32,246)
- `parcels_mo_newton_county` (32,162)
- `agis_kevin_hill_sumtercountygis_wildwood_zoning_z` (31,588)
- `parcels_sc_kershaw_county` (31,352)
- `roads_secondary` (30,891)
- `parcels_pr_toa_baja_municipio` (29,605)
- `parcels_mi_midland_county` (29,404)
- `parcels_mo_bollinger_county_multi` (29,174)
- `gips_duke_dep` (28,829)
- `gips_caiso` (28,633)
- `parcels_ga_liberty` (28,170)
- `hca_ameren_il_subt_1250` (27,674)
- `parcels_il_fulton` (27,610)
- `parcels_il_fulton_county` (27,610)
- `agis_mecklenburg_vacant` (26,997)
- `parcels_tn_hardin_county` (26,992)
- `hca_liberty_nh_25perc_demand` (26,979)
- `parcels_la_st_john_the_baptist_parish` (26,805)
- `disadvantaged_communities` (26,610)
- `agis_brisbaneopendata_city_plan_2014_zoning_overlay_z` (26,356)
- `parcels_id_valley_county` (26,326)
- `agis_brisbaneopendata_superseded_city_plan_2014_v29_00_2023_zonin` (26,211)
- `agis_brisbaneopendata_superseded_city_plan_2014_v26_00_2023_zonin` (26,189)
- `parcels_ca_sanbenito` (26,163)
- `parcels_ca_plumas` (25,841)
- `parcels_ky_adair_county_multi` (25,644)
- `hca_ameren_il_subt_2500` (25,618)
- `parcels_ky_scott` (25,589)
- `parcels_sc_chesterfield_county` (24,504)
- `socrata_seattle_mup` (24,503)
- `agis_jamie_cvg_new_zoning_z` (24,438)
- `agis_tus_code_cases` (24,393)
- `hca_national_grid_ri_hosting_capacity_all` (24,284)
- `parcels_ca_amador` (23,929)
- `agis_syr_permits` (23,603)
- `parcels_il_effingham_county` (23,475)
- `agis_aeroberts605_villagetownshipzoning_z` (23,434)
- `hca_nyseg_rge_hostingcapacity_dcirc_nyseg_rge_0` (23,344)
- `parcels_mo_scott` (23,263)
- `parcels_ga_ware` (23,094)

## F national or other grain — 304 tables
- `eqr_transactions` (3,552,703,481)
- `iso_lmp_nodal_da` (181,543,485)
- `eia930_generation_by_fuel` (116,575,070)
- `si_scored_entity_signals_v3` (75,361,835)
- `si_scored_entity_signals` (63,176,004)
- `weather_ghcn_daily` (52,776,828)
- `eia930_interchange` (29,287,039)
- `hc_app_features` (28,728,039)
- `socrata_nyc_acris_legals` (22,688,577)
- `socrata_co_txn_history` (21,421,122)
- `socrata_ny_corp_filings` (20,743,412)
- `ferc714_hourly_demand` (18,750,056)
- `iso_ancillary` (17,465,999)
- `socrata_nyc_acris_master` (17,036,716)
- `eqr_contracts` (9,470,941)
- `eia930_hourly_operations` (6,123,842)
- `mat_si_parcel_all` (4,726,495)
- `socrata_nyc_acris_pp_master` (4,541,520)
- `socrata_nyc_acris_pp_legals` (3,974,335)
- `eia923_generation_fuel` (3,350,030)
- `socrata_co_entities` (3,084,693)
- `socrata_il_cook_ptax_declarations` (2,923,932)
- `socrata_nj_permits_statewide` (2,755,796)
- `socrata_co_ucc` (2,574,693)
- `socrata_nyc_dob_violations` (2,475,641)
- `mat_si_parcel_spatial` (2,470,033)
- `mat_si_parcel` (2,256,462)
- `pjm_queuescope_results` (1,969,606)
- `socrata_nyc_ecb_violations` (1,826,025)
- `eia923_boiler_fuel` (1,803,271)
- `socrata_la_businesses` (1,700,274)
- `socrata_co_ucc_collateral` (1,696,873)
- `hca_lgeku_tr_lim_calc` (1,505,000)
- `state_bulk_cha_codeactivity` (1,497,516)
- `eia_generators_by_ownership` (1,413,786)
- `si_scored_bridge` (1,410,399)
- `socrata_sf_permits` (1,292,407)
- `subcap_sce_load_historical_circuit_load_` (1,236,956)
- `socrata_ct_real_estate_sales` (1,141,722)
- `socrata_orlando_permits` (1,104,928)
- `socrata_co_delinquency_cure` (1,073,504)
- `elec_power_operational` (909,982)
- `recorder_publicsearch_d15_mechanics_lien` (737,287)
- `si_wire_dallas_addr` (712,998)
- `socrata_dallas_violations` (712,998)
- `edgar_abs_ee_cmbs` (670,373)
- `socrata_sf_violations` (515,307)
- `mat_si_date_resolved` (505,787)
- `state_bulk_va_scc_lien_details` (471,115)
- `gips_flowgates` (432,008)
- `agis_charlotte_code` (430,244)
- `socrata_nyc_tc_appeals` (393,620)
- `socrata_nyc_tc_appeals_b` (393,620)
- `ckan_hou_code_violations` (376,092)
- `ferc1_income_statements` (374,418)
- `agis_mem_vac_mlgw` (360,304)
- `ghgrp_emissions` (346,683)
- `ferc1_balance_sheet_assets` (315,834)
- `agis_cmh_code_enforcement_cases` (306,190)
- `agis_lv_planning_cases_approved` (275,595)
- `socrata_nyc_lien_sale` (264,142)
- `agis_miami_permits` (262,188)
- `socrata_orlando_violations` (255,243)
- `subcap_sce_load_historical_substation_lo` (235,872)
- `agis_dc_itspe` (221,400)
- `socrata_cook_tax_sale` (200,915)
- `agis_miami_code_violations` (181,394)
- `socrata_kc_dangerous_bldg` (174,999)
- `ng_prices_spot` (158,637)
- `ng_production` (149,190)
- `socrata_dallas_permits` (126,840)
- `socrata_orlando_btr` (118,438)
- `retail_rates` (113,088)
- `socrata_tx_collin_cad_permits` (106,845)
- `agis_dc_zoning_cases` (105,941)
- `socrata_la_evictions` (99,832)
- `ckan_allegheny_appeals` (96,713)
- `appeals_oh_bta_docket` (92,845)
- `format_census` (90,522)
- `branch_hifld` (88,704)
- `ckan_pgh_tax_liens` (87,971)
- `spp_hct_poi_headroom` (83,383)
- `wv_sao_cts_delinquent_land` (81,586)
- `agis_dur_permits` (77,723)
- `caiso_curtailment` (77,705)
- `socrata_king_personal_property_tax` (76,413)
- `bus_hifld` (75,328)
- `hifld_bus_features_v3` (75,328)
- `socrata_norfolk_violations` (74,136)
- `agis_aug_codeviol` (73,492)
- `agis_phoenix_permits` (70,791)
- `ferc1_all_plants` (62,529)
- `socrata_br_ebr_adjudicated_property` (52,056)
- `mat_inventory_columns` (50,299)
- `carto_philly_appeals` (43,210)
- `socrata_br_ebr_business_license_lapse` (43,047)
- `agis_denver_business_licenses` (42,001)
- `ckan_pgh_mortgage_foreclosure` (40,585)
- `socrata_reading_violations` (40,251)
- `appeals_nj_tax_court_local` (38,960)
- `urdb_rates` (38,730)
- `socrata_cook_suburban_demo` (38,512)
- `zctas` (33,791)
- `socrata_nyc_zap_projects` (32,931)
- `agis_dsm_codecase` (31,049)
- `agis_phoenix_code` (29,347)
- `socrata_la_code_violations` (28,902)
- `socrata_nor_norfolk_delinquent_taxes` (28,617)
- `agis_rva_hen_cases` (26,273)
- `agis_minneapolis_rental_licenses` (24,949)
- `iso_pnodes_pjm` (23,711)
- `agis_dur_devcases` (22,535)
- `socrata_orlando_planning` (22,376)
- `appeals_mo_stc_open` (21,569)
- `iso_pnodes_nyiso_load` (18,469)
- `state_bulk_ne_delinquent_realprop` (18,416)
- `agis_dsm_rental` (15,751)
- `stb_abandonment` (15,045)
- `stb_abandonment_v2` (15,045)
- `agis_cmh_building_compliance_cases` (14,245)
- `agis_wsnc_taxdelq` (14,238)
- `agis_baltimore_foreclosure` (14,142)
- `miso_poi_mf_crawl_status` (12,845)
- `legistar_rezoning` (12,746)
- `socrata_mo_asbestos_demo` (12,314)
- `si_d1_tn_shelby_chancery_taxsale` (11,738)
- `agis_baltimore_vacant` (11,574)
- `socrata_nyc_assessment_actions` (11,075)
- `agis_hillsborough_code` (10,991)
- `appeals_nj_tax_court_judgments` (10,773)
- `state_bulk_stl_lra_inventory` (10,345)
- `appeals_in_ibtr_determinations` (10,071)
- `txexp_pjm_tcic_upgrade_info` (9,936)
- `agis_denver_demo_permits` (9,688)
- `iso_renewable_curtailment` (8,352)
- `appeals_or_tax_court` (8,275)
- `socrata_rva_city_business` (7,983)
- `agis_sj_sanjose_code_violations` (7,874)
- `spp_hct_poi_buses` (7,874)
- `ng_storage_weekly` (6,896)
- `gdelt_dc_articles` (6,766)
- `agis_portland_demo` (6,496)
- `agis_rva_city_sup` (6,327)
- `gas_eia_176` (6,276)
- `txexp_isone_proposed_plan_applications` (5,906)
- `agis_cmh_building_permits_demo` (5,561)
- `agis_phoenix_evictions` (5,492)
- `drought_by_state` (5,355)
- `agis_sanantonio_demo_permits` (5,351)
- `bankruptcy_dockets` (5,082)
- `cartovista_nyiso_tsa_agg_by_poi` (4,781)
- `socrata_mo_asbestos_courtesy_notif` (4,628)
- `sec_ft_sec_8k_closure` (4,430)
- `agis_baltimore_demolitions` (4,273)
- `zoomprospector_listings` (4,059)
- `agis_abq_zoning_cases_legacy` (4,030)
- `agis_hillsborough_demo` (3,963)
- `socrata_neworleans_permits` (3,940)
- `socrata_rva_city_taxdelq` (3,864)
- `fcc_bdc_fixed_provider_summary` (3,764)
- `socrata_riverside_power_to_sell_2017` (3,696)
- `civilview_sales` (3,623)
- `agis_wsnc_permits` (3,059)
- `agis_dur_demo` (2,868)
- `fcc_bdc_provider_list` (2,858)
- `eqr_index` (2,846)
- `state_bulk_stl_excise_licenses` (2,571)
- `socrata_howard_md_tax_sales` (2,542)
- `socrata_la_foreclosure_registry` (2,508)
- `amlegal_dc_ordinances` (2,494)
- `agis_grr_vacant_lots` (2,460)
- `agis_grr_vacant_buildings` (2,364)
- `socrata_vt_ptt_town_2019` (2,291)
- `reddit_dc_posts` (2,252)
- `txexp_ercot_tpit_projects` (2,127)
- `zoning_nza_ny_li` (2,126)
- `si_d1_ar_cosl_postsale` (2,093)
- `table_verdict` (2,061)
- `puc_ma_dockets` (1,976)
- `socrata_nyc_dob_jobs` (1,963)
- `tax_delinquent_fl` (1,797)
- `socrata_nola_sheriff_sales` (1,771)
- `puc_ma_dc` (1,752)
- `zoning_nza_nh` (1,726)
- `queue_nyiso` (1,717)
- `mat_inventory_objects` (1,682)
- `socrata_clermont_delinquent_tax` (1,682)
- `ckan_milwaukee_vacant` (1,660)
- `queue_ercot` (1,528)
- `agis_lou_abc_active_licenses` (1,375)
- `subcap_pge_load_gnasubstationarea_peakfa` (1,300)
- `endpoint_truth` (1,281)
- `ckan_mke_liquor_licenses` (1,264)
- `subcap_pge_load_dfsubstationarea_peakfac` (1,236)
- `state_bulk_stl_es_inspections` (1,174)
- `agis_fre_abc_licenses` (1,079)
- `civic_legistar_dc` (1,075)
- `appeals_ia_paab_historical` (1,062)
- `agis_oma_code_violations` (1,057)
- `subcap_avangrid_ny_distribution_capacity` (1,049)
- `cartovista_nyiso_tsa` (1,000)
- `cartovista_pnm_cv_load_study` (1,000)
- `cartovista_tva_tsa` (1,000)
- `agis_shelby_envcourt_housing_cases` (968)
- `agis_baltimore_tax_sale` (933)
- `agis_ral_raleigh_assessment_liens` (865)
- `agis_sj_sanjose_vacant_blight` (757)
- `state_bulk_bhm_demolition_permits` (751)
- `socrata_la_vacant_bldg` (746)
- `subcap_pge_load_edsubstations` (704)
- `socrata_mesa_vacancy` (697)
- `submarine_cables` (695)
- `gov_auction_treasury` (678)
- `gov_auction_treasury_v2` (678)
- `agis_shelby_envcourt_npa_cases` (672)
- `socrata_pvd_entertainment_licenses` (654)
- `si_d1_tn_hamilton_chancery_taxsale` (625)
- `agis_bna_dev_tracker_cases` (607)
- `agis_indy_landbank_surplus` (595)
- `agis_knx_devprojects_d8` (542)
- `socrata_marin_violations` (526)
- `si_d1_nm_ptd_auctions` (510)
- `ferc_dc_documents` (483)
- `googlenews_dc` (454)
- `agis_sanantonio_foreclosures` (447)
- `appeals_ia_paab_current` (425)
- `agis_lv_abandoned_registry` (413)
- `cartovista_pnm_cv_generator_cluster13_study_agg` (384)
- `cartovista_pnm_cv_generator_cluster13_study_subset_agg` (384)
- `cartovista_pnm_cv_generator_cluster14_study_agg` (384)
- `cartovista_pnm_cv_load_study_agg` (384)
- `zoning_nza_hi` (359)
- `agis_sj_sanjose_planning_cases` (353)
- `state_bulk_va_scc_filing_details` (322)
- `socrata_co_dola_foreclosure_filings` (320)
- `ferc_dc_filings` (318)
- `socrata_nola_nora_inventory` (318)
- `iso_curtailment` (288)
- `tax_delinquent_ca_top500_pit` (286)
- `socrata_alb_demolition_permits` (276)
- `zoning_nza_co` (272)
- `ckan_hou_res_permits` (264)
- `peeringdb_ix` (212)
- `state_bulk_okc_county_owned_resale` (202)
- `agis_rva_city_vacparcel` (190)
- `state_bulk_stl_lcra_inventory` (190)
- `appeals_ut_stc_decisions` (188)
- `storage_cost_estimate` (188)
- `si_d1_nc_kania_taxforeclosure` (186)
- `ckan_mke_tax_delinquent_brownfields` (163)
- `subcap_pge_load_substationprojects` (157)
- `appeals_nc_ptc_decisions` (153)
- `recorder_publicsearch_rendered` (150)
- `socrata_king_foreclosure` (145)
- `agis_bak_cob_zoning_cases_cup` (131)
- `ballotpedia_dc` (131)
- `agis_tol_demo` (121)
- `gdelt_dc_tone` (116)
- `agis_tus_demolition_permits` (112)
- `agis_lv_planning_cases_scheduled` (105)
- `txexp_ercot_tpit_rtp_projects` (89)
- `rggi_auction_prices` (84)
- `tax_delinquent_ca_top500_corp` (84)
- `agis_bna_bza_cases` (80)
- `subcap_avangrid_ny_transmission_capacity` (80)
- `agis_sac_demolition_permits` (79)
- `zoning_nza_mt` (79)
- `source_catalog` (78)
- `socrata_atx_repeat_offender_reg` (76)
- `taxsale_mi` (73)
- `appeals_fl_dr529_vab_2025` (70)
- `tradepress_dc` (70)
- `avert_emission_rates` (62)
- `work_backlog` (61)
- `agis_shelby_envcourt_npa_receivership` (56)
- `egrid_state` (52)
- `si_d1_tn_davidson_chancery_taxsale` (52)
- `bingnews_dc` (45)
- `agis_rva_city_vacbldg` (41)
- `civic_civicclerk_deep_dc` (39)
- `primegov_meetings` (39)
- `methods` (37)
- `state_bulk_stl_demolition` (31)
- `queue_ercot_largeload` (29)
- `free_source_catalog` (28)
- `agis_sj_sanjose_demolition_permits` (27)
- `egrid_subregion` (27)
- `weekend_scope` (26)
- `iso_pnodes_isone` (20)
- `competitor_gap_matrix` (17)
- `rescrape_schedule` (16)
- `si_d2_tn_anchor_posting_foreclosure` (15)
- `scrape_gap_targets` (12)
- `agis_jax_vacant_commercial` (10)
- `agis_sanantonio_tax_foreclosures` (10)
- `ga_largeload_reports` (9)
- `pjm_capacity_prices` (9)
- `state_bulk_bhm_new_business_licenses` (9)
- `appeals_ia_paab_current_residual` (7)
- `gov_auction_irs` (6)
- `raster_catalog` (5)
- `deletion_log` (3)
- `ercot_large_load` (1)
- `socrata_pvd_business_licenses` (1)

## G not in column census — 45 tables
- `mat_structure_footprints` (135,370,228)
- `nat_usa_structures_pt` (135,338,769)
- `nat_usa_structures_ptc` (135,338,769)
- `mat_parcel_outdoor_exact` (117,375,019)
- `si_signals` (96,633,328)
- `mat_si_sites` (83,428,941)
- `iso_lmp` (28,931,138)
- `socrata_nyc_acris_pp_parties` (11,020,142)
- `socrata_nyc_acris_pp_references` (7,721,440)
- `mat_parcel_geom_esri` (5,409,155)
- `mat_si_building_county` (5,302,698)
- `nfirs_basicincident_2020` (2,181,870)
- `nfirs_incidentaddress_2020` (2,181,870)
- `nfirs_basicincident_2021` (2,109,645)
- `nfirs_incidentaddress_2021` (2,109,645)
- `agis_fw_development_permits__staging` (1,605,987)
- `appeals_il_ptab_dockets` (1,274,512)
- `nfirs_fireincident_2021` (558,385)
- `nfirs_fireincident_2020` (542,192)
- `agis_dc_corporate_registration` (502,172)
- `socrata_nyc_acris_pp_remarks` (493,897)
- `ckan_sanantonio_permits_issued_2020_2024` (368,297)
- `ckan_sanantonio_permits_issued_current` (133,985)
- `ga_probate_estates` (103,617)
- `socrata_mesa_violations` (80,042)
- `column_census` (65,932)
- `parcels_al_elmore_geom` (55,773)
- `ckan_sanantonio_permit_applications` (47,820)
- `agis_atl_building_permits_2019_2024` (38,107)
- `agis_atl_building_permit_latest` (36,115)
- `parcels_ks_butler_county_geom` (34,576)
- `parcels_ga_liberty_geom` (28,170)
- `recorder_publicsearch_dallas_tx_rp_mechanics_family` (26,597)
- `agis_atl_building_permit_tracker` (22,778)
- `agis_atl_building_permits_2009_2014` (21,545)
- `registry_sources` (5,608)
- `decisions` (629)
- `start_here` (185)
- `state_snapshot` (142)
- `headroom_v3_bt` (8)
- `headroom_v3_linreg` (8)
- `headroom_v2_bt` (7)
- `headroom_v2_linreg` (7)
- `headroom_bt` (5)
- `headroom_linreg` (5)


## VERIFIED per-table Indiana counts — measured 2026-08-15

773 tables measured one-by-one: **308 hold Indiana rows**, 465 measured zero, 0 errored (named in `indiana_app._indiana_census`).

| table | IN rows | total |
|---|---:|---:|
| `cems_hourly` | 36,034,944 | 1,009,316,568 |
| `mat_parcel_key_index` | 13,931,736 | 678,542,895 |
| `fcc_bdc_fixed_availability` | 12,649,532 | 512,987,355 |
| `mat_parcel_grid` | 4,090,786 | 179,048,266 |
| `mat_parcel_all_v2` | 3,637,663 | 170,442,382 |
| `mat_parcel_all` | 3,637,663 | 132,206,336 |
| `mat_parcel_geo` | 3,637,317 | 157,427,563 |
| `mat_parcel_attrs` | 3,553,381 | 107,325,274 |
| `mat_parcel_structures` | 3,553,194 | 129,844,449 |
| `mat_siting_parcels` | 3,553,193 | 120,660,571 |
| `mat_parcel_geo_supplement` | 3,553,193 | 118,832,291 |
| `si_d5_struct_pts` | 3,377,472 | 135,338,769 |
| `nat_usa_structures` | 3,377,472 | 135,371,228 |
| `nhd_flowline` | 2,415,369 | 39,542,980 |
| `mat_si_county_resolved` | 2,284,133 | 73,642,672 |
| `mat_structure_addr` | 2,149,657 | 52,082,602 |
| `si_d5_addr_pts` | 2,149,657 | 52,082,602 |
| `mat_si_plottable` | 1,205,602 | 83,429,361 |
| `mat_si_scored_v3` | 1,205,602 | 83,429,361 |
| `si_scored_v3_variants` | 1,205,602 | 83,429,361 |
| `si_d5_vacancy_derived` | 967,366 | 22,295,965 |
| `mat_si_scored_v2` | 951,913 | 31,931,655 |
| `si_wire_stage` | 920,554 | 17,643,229 |
| `si_d12_indy_marion_code_enforcement` | 910,483 | 910,483 |
| `agis_indy_code_enforcement` | 906,326 | 910,483 |
| `si_wire_new` | 754,164 | 15,575,113 |
| `nwi_wetlands` | 453,995 | 40,575,843 |
| `nhd_waterbody` | 186,667 | 10,431,981 |
| `ferc714_state_demand` | 166,554 | 8,493,483 |
| `mat_si_address_location` | 95,967 | 5,549,105 |
| `si_d1_sri_taxsale_listings` | 81,975 | 217,226 |
| `nfhl_flood_zones` | 66,140 | 5,554,986 |
| `agis_indy_taxsale` | 62,368 | 62,368 |
| `nfirs_incidentaddress_2024` | 49,895 | 2,410,457 |
| `nfirs_basicincident_2024` | 49,811 | 2,410,457 |
| `nfirs_basicincident_2023` | 46,748 | 2,451,836 |
| `nfirs_incidentaddress_2023` | 46,717 | 2,451,836 |
| `nfirs_incidentaddress_2022` | 40,091 | 2,370,774 |
| `nfirs_basicincident_2022` | 40,044 | 2,370,774 |
| `parcels_fl` | 31,079 | 10,831,924 |
| `spc_severe_events` | 24,716 | 1,014,963 |
| `faa_obstacles` | 15,638 | 652,596 |
| `parcels_ga_lowndes` | 13,480 | 66,316 |
| `si_d8_exit_intent` | 13,414 | 2,840,865 |
| `echo_cwa_facilities` | 13,209 | 524,512 |
| `eia860_generators` | 12,479 | 666,179 |
| `storm_events` | 12,460 | 688,406 |
| `socrata_cook_bor_appeals` | 10,956 | 6,933,428 |
| `eia861_service_territory` | 10,928 | 280,398 |
| `osm_power_lines` | 10,906 | 392,489 |
| `openstates_energy_bill_vote_people` | 9,197 | 233,210 |
| `socrata_ny_corp_filing_addresses` | 8,483 | 18,115,040 |
| `socrata_ny_assessment_roll` | 7,120 | 23,580,051 |
| `mat_si_rooftop_geocode` | 5,880 | 3,960,225 |
| `block_groups` | 5,287 | 241,893 |
| `mat_si_building_in_parcel` | 5,222 | 23,354,741 |
| `sba_foia_loans` | 5,135 | 2,190,504 |
| `padus` | 4,736 | 652,827 |
| `socrata_ct_ucc` | 4,683 | 843,134 |
| `land_padus` | 4,137 | 439,860 |
| `mat_grid_substations` | 3,858 | 122,527 |
| `socrata_chicago_licenses` | 3,645 | 1,201,485 |
| `socrata_chicago_biz_licenses` | 3,644 | 1,200,971 |
| `ghgrp_facilities` | 3,391 | 136,005 |
| `si_d11_entity_dissolution_v2` | 3,384 | 4,702,667 |
| `mat_si_scored` | 3,288 | 9,363,898 |
| `mat_si_buildings` | 3,288 | 9,363,898 |
| `mat_si_buildings_v2` | 3,288 | 9,363,898 |
| `ghgrp_emitter_facilities` | 2,882 | 107,329 |
| `osm_power_substations` | 2,873 | 91,022 |
| `eia_plants` | 2,675 | 251,851 |
| `si_coverage_matrix` | 2,668 | 93,757 |
| `eqr_identity` | 2,635 | 288,794 |
| `socrata_or_ucc_secured` | 2,428 | 220,610 |
| `weather_stations` | 2,108 | 132,501 |
| `dim_jurisdiction` | 2,080 | 71,989 |
| `substations` | 2,077 | 75,328 |
| `nat_substations_hifld` | 2,077 | 75,328 |
| `parcels_sc_abbeville_county` | 2,045 | 3,975,962 |
| `parcels_mn` | 1,961 | 2,708,126 |
| `candidate_sites_schools` | 1,928 | 102,178 |
| `acs_tract_vacancy` | 1,696 | 85,382 |
| `census_tracts` | 1,693 | 85,060 |
| `wind_turbines` | 1,652 | 75,727 |
| `epa_brownfields` | 1,613 | 44,134 |
| `gov_surplus_frpp` | 1,594 | 307,919 |
| `parcels_az_maricopa` | 1,584 | 1,759,389 |
| `si_d17_in_iocs_court_year` | 1,543 | 1,543 |
| `socrata_or_entities` | 1,526 | 1,565,971 |
| `parcels_mi_berrien_county` | 1,495 | 86,267 |
| `brownfield_epa_repowering` | 1,483 | 190,976 |
| `fema_disaster_declarations` | 1,442 | 60,624 |
| `parcels_tx` | 1,403 | 14,347,625 |
| `brownfields` | 1,347 | 37,026 |
| `nfirs_fireincident_2024` | 1,255 | 586,714 |
| `parcels_tx_harris` | 1,253 | 3,051,050 |
| `si_signals_d19_new_20260803` | 1,039 | 52,507 |
| `si_signals_d19_pre_widen_20260803` | 1,037 | 27,573 |
| `lbnl_interconnection_queue` | 948 | 38,201 |
| `interconnection_queue` | 948 | 38,201 |
| `txexp_pjm_rtep_upgrades` | 929 | 15,440 |
| `iso_interconnection_queue` | 888 | 24,030 |
| `eia923_fuel_receipts_costs` | 880 | 28,074 |
| `socrata_co_ucc_debtors` | 851 | 2,005,102 |
| `openstates_energy_bill_actions` | 811 | 44,774 |
| `si_wire_zip_county` | 807 | 33,750 |
| `parcels_ny` | 698 | 3,827,530 |
| `txexp_miso_mtep_appendix_a_in_service` | 693 | 5,183 |
| `parcels_ok_tulsa` | 692 | 297,762 |
| `low_income_bonus_tracts` | 665 | 35,423 |
| `eia861_demand_response` | 660 | 19,328 |
| `eia860m_generators` | 648 | 39,517 |
| `candidate_sites_private_schools` | 590 | 22,510 |
| `parcels_tn_sevier_county` | 580 | 88,395 |
| `parcels_pa` | 491 | 8,711,170 |
| `parcels_tn_claiborne_county_multi` | 474 | 123,939 |
| `gas_eia_state_capacity` | 471 | 19,311 |
| `agis_detroit_blight_tickets` | 466 | 896,806 |
| `parcels_mo_stlouiscounty` | 459 | 401,404 |
| `queue_miso` | 456 | 3,794 |
| `parcels_tn_cumberland_county` | 422 | 65,395 |
| `socrata_ny_active_corps` | 404 | 4,249,686 |
| `water_cwns_2022` | 404 | 1,118,786 |
| `socrata_ny_tax_warrants` | 370 | 563,729 |
| `incentive_qct` | 337 | 15,727 |
| `parcels_sc_cherokee_county` | 322 | 195,448 |
| `openstates_energy_bill_sponsorships` | 300 | 19,769 |
| `parcels_al` | 297 | 479,544 |
| `parcels_ca_sanfrancisco` | 294 | 226,396 |
| `gas_phmsa_distribution` | 266 | 20,584 |
| `cbp_county_industry` | 234 | 7,810 |
| `parcels_sc_beaufort_county` | 227 | 104,904 |
| `parcels_sc_berkeley_county` | 226 | 109,448 |
| `parcels_sc` | 220 | 270,772 |
| `parcels_ky_webster` | 212 | 13,255 |
| `power_plants` | 208 | 13,446 |
| `parcels_mi_jackson` | 193 | 78,038 |
| `parcels_mi_dickinson_county_multi` | 191 | 72,142 |
| `coal_closure_communities` | 184 | 4,325 |
| `si_register` | 160 | 93,757 |
| `data_centers_datacentermap` | 157 | 5,661 |
| `socrata_sf_business_locations` | 157 | 364,420 |
| `incentive_opportunity_zones` | 156 | 8,765 |
| `candidate_sites_colleges` | 151 | 6,605 |
| `openstates_energy_bill_versions` | 140 | 9,949 |
| `openstates_energy_bill_sources` | 132 | 6,261 |
| `parcels_ok_oklahoma` | 131 | 336,992 |
| `openstates_energy_bill_votes` | 126 | 5,820 |
| `parcels_or` | 125 | 1,088,187 |
| `parcels_sc_greenville` | 122 | 322,194 |
| `socrata_kc_business_license` | 118 | 26,646 |
| `lbnl_interconnection_costs` | 116 | 5,486 |
| `mat_grid_territories` | 114 | 2,931 |
| `solar_pv_facilities` | 114 | 6,611 |
| `electric_retail_service_territories` | 114 | 2,931 |
| `workforce_ipeds_directory` | 112 | 6,256 |
| `parcels_ky_pendleton` | 105 | 9,020 |
| `parcels_tn_blount_county` | 98 | 67,312 |
| `googlenews_dc_state` | 97 | 3,598 |
| `parcels_sc_spartanburg` | 95 | 341,978 |
| `county_boundaries` | 92 | 3,235 |
| `solar_potential` | 92 | 3,235 |
| `acs_county` | 92 | 3,222 |
| `usa_structures_county` | 92 | 3,235 |
| `fema_nri_counties` | 92 | 3,232 |
| `qcew_county_labor` | 92 | 3,224 |
| `water_use` | 92 | 3,223 |
| `parcel_county_register` | 92 | 3,233 |
| `parcel_county_coverage` | 92 | 3,233 |
| `fsis_establishments` | 90 | 7,225 |
| `seismic_design` | 88 | 3,163 |
| `parcels_tn_jefferson_county` | 88 | 35,343 |
| `parcels_ky_bullitt_county` | 86 | 36,177 |
| `parcels_sc_greenwood_county` | 83 | 235,399 |
| `parcels_ga_union` | 80 | 40,901 |
| `parcels_sc_saluda_county` | 79 | 182,966 |
| `txexp_miso_mtep_under_evaluation` | 76 | 597 |
| `parcels_tn_cocke_county` | 76 | 25,311 |
| `parcels_ky_campbell_county` | 72 | 36,017 |
| `parcels_ky_campbell` | 71 | 36,015 |
| `parcels_ga_richmond` | 69 | 84,575 |
| `openstates_energy_bill_abstracts` | 66 | 2,399 |
| `openstates_energy_bills_v2` | 66 | 4,394 |
| `parcels_ky_kenton` | 65 | 64,179 |
| `state_bulk_gwinnett_delinquent` | 58 | 37,297 |
| `parcels_id` | 57 | 381,144 |
| `state_bulk_ar_cosl_excess` | 57 | 5,081 |
| `parcels_sc_orangeburg_county` | 56 | 61,942 |
| `parcels_tn_anderson_county` | 53 | 38,213 |
| `parcels_ca_sanluisobispo` | 53 | 130,611 |
| `eia861_sales_ult_cust` | 51 | 2,815 |
| `dc_opposition_tracker` | 50 | 1,342 |
| `eia861_sales` | 50 | 2,823 |
| `parcels_ok_creek_county` | 50 | 45,862 |
| `parcels_ga_coweta` | 48 | 64,060 |
| `parcels_tn_humphreys_county` | 46 | 13,719 |
| `parcels_ky_henry_county` | 46 | 9,449 |
| `socrata_nola_biz_licenses` | 46 | 37,365 |
| `parcels_sc_richland_county` | 45 | 64,131 |
| `parcels_tn_marion_county` | 44 | 22,347 |
| `parcels_ga_cobb` | 43 | 283,363 |
| `parcels_tn_maury_county` | 42 | 53,040 |
| `parcels_or_deschutes_county` | 41 | 112,374 |
| `parcels_mo_jefferson` | 41 | 106,464 |
| `parcels_tn_johnson_county` | 39 | 78,891 |
| `state_bulk_sd_business_active` | 38 | 59,719 |
| `parcels_ga_bibb_county` | 38 | 68,731 |
| `parcels_ca_imperial` | 36 | 85,918 |
| `eia861_reliability` | 36 | 968 |
| `nonattainment_areas` | 35 | 792 |
| `parcels_tn_coffee_county` | 34 | 32,198 |
| `parcels_al_stclair` | 33 | 61,242 |
| `ustp_ch7_tfr` | 33 | 1,194,652 |
| `parcels_tn_hardeman_county_multi` | 32 | 21,756 |
| `parcels_ok_canadian` | 30 | 84,792 |
| `parcels_ky_franklin_county` | 30 | 22,628 |
| `parcels_mo_stfrancois` | 29 | 40,645 |
| `socrata_tx_tabc_licenses` | 28 | 78,042 |
| `socrata_or_ucc_recent` | 27 | 5,743 |
| `parcels_al_hale_county` | 27 | 16,346 |
| `parcels_ks_riley_county` | 27 | 25,314 |
| `parcels_al_hale_commercial` | 27 | 16,346 |
| `econ_gjf_megadeals` | 26 | 535 |
| `agis_mem_code_environ` | 26 | 39,901 |
| `parcels_id_teton_county` | 26 | 14,920 |
| `gas_compressor_stations` | 24 | 1,768 |
| `parcels_ga_cobb_county` | 24 | 143,857 |
| `parcels_il_boone` | 23 | 24,379 |
| `parcels_al_lauderdale_commercial` | 23 | 26,037 |
| `parcels_tn_giles_county` | 23 | 26,037 |
| `parcels_al_lawrence_commercial` | 23 | 26,037 |
| `gas_storage_facilities` | 22 | 486 |
| `parcels_mo_capegirardeau` | 22 | 39,359 |
| `gas_storage` | 22 | 486 |
| `state_bulk_sd_business_inactive` | 21 | 102,727 |
| `openstates_energy_bills` | 21 | 2,890 |
| `data_centers_peeringdb` | 20 | 1,380 |
| `parcels_ga_clarke` | 20 | 41,989 |
| `parcels_tn_mcminn_county` | 20 | 31,430 |
| `parcels_ga_clarke_county` | 20 | 41,989 |
| `land_faa_sua` | 19 | 1,542 |
| `peeringdb_facilities` | 19 | 1,355 |
| `parcels_id_bannock_county` | 17 | 45,834 |
| `parcels_ok_wagoner_county` | 16 | 52,685 |
| `ut_tax_liens_v2` | 16 | 26,345 |
| `carto_philly_tax_delinquency` | 15 | 54,401 |
| `parcels_ks` | 14 | 41,779 |
| `parcels_la_lafayette_parish` | 14 | 117,084 |
| `tribal_land` | 14 | 858 |
| `fsis_establishments_inactive` | 13 | 932 |
| `parcels_ga_thomas` | 13 | 24,753 |
| `agis_sac_business_tax_lapsed` | 12 | 37,308 |
| `parcels_ok_pottawatomie_county` | 12 | 24,756 |
| `bingnews_dc_state` | 12 | 469 |
| `agis_mcallen_business_list` | 11 | 5,746 |
| `si_d27_ucc_lapse` | 10 | 529,266 |
| `ckan_boston_violations` | 10 | 17,378 |
| `ckan_mke_tax_delinquent_re` | 10 | 19,639 |
| `parcels_ga_baldwin` | 10 | 21,876 |
| `parcels_ga_effingham` | 10 | 34,089 |
| `parcels_tn_dyer_county` | 9 | 8,043 |
| `parcels_ga_bryan` | 9 | 17,984 |
| `parcels_ga_bryan_county` | 9 | 22,965 |
| `parcels_ga_jackson` | 9 | 44,769 |
| `sec_cik_registrant_state` | 8 | 1,045 |
| `energy_communities_msa` | 8 | 901 |
| `parcels_mo_perry` | 7 | 14,198 |
| `parcels_ga_dooly_county` | 6 | 7,344 |
| `parcels_mi_ingham_county` | 6 | 4,989 |
| `parcels_mo_buchanan_county` | 6 | 59,374 |
| `parcels_or_harney_county` | 6 | 10,935 |
| `agis_baltimore_code` | 5 | 30,987 |
| `parcels_ok_beckham_county` | 5 | 16,445 |
| `dc_eei_tariffs` | 5 | 105 |
| `parcels_ga_cook_county` | 5 | 10,432 |
| `parcels_sd_beadle` | 5 | 16,889 |
| `parcels_or_clatsop_county` | 4 | 35,452 |
| `socrata_nyc_dob_permits` | 4 | 3,989,483 |
| `agis_campus_planning_zoning_z` | 4 | 4,889 |
| `parcels_ky_warren` | 4 | 60,753 |
| `socrata_grand_junction_vacant_ci` | 4 | 4,611 |
| `parcels_al_shelby_county` | 4 | 8,717 |
| `parcels_ga_brooks_county` | 3 | 10,037 |
| `openstates_bulk_session_coverage` | 3 | 139 |
| `utility_tariff_riders` | 3 | 40 |
| `parcels_ga_brantley_county` | 3 | 13,301 |
| `agis_mecklenburg_permits` | 3 | 1,526 |
| `parcels_la_cameron_parish` | 3 | 11,918 |
| `gov_auction_gsa` | 2 | 68 |
| `parcels_sd_codington` | 2 | 18,456 |
| `socrata_pa_entities` | 2 | 4,026,643 |
| `dc_bans` | 1 | 213 |
| `parcels_mo_christian_county` | 1 | 8,432 |
| `airports` | 1 | 86 |
| `commission_posture` | 1 | 50 |
| `balancing_authority_areas` | 1 | 71 |
| `state_irp_catalog` | 1 | 18 |
| `puc_state_access_ledger` | 1 | 51 |
| `groundwater_sites` | 1 | 50 |
| `dc_docket_tracker` | 1 | 39 |
| `si_d2_md_statewide_forecl_by_county` | 1 | 177 |
| `agis_gso_forecl` | 1 | 3,119 |
| `agis_cle_cuyahoga_delinquent_parcels` | 1 | 4,277 |
| `appeals_tx_comptroller_arb_protests_2024` | 1 | 253 |
| `state_boundaries` | 1 | 56 |
| `si_d17_ny_oca_landlord_tenant_cases` | 1 | 903,594 |
| `socrata_alb_vacant_registry` | 1 | 1,814 |
| `parcels_mi_emmet_county` | 1 | 44,764 |
