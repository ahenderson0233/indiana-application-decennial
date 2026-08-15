# Plottability audit — 2026-08-15

Operator rule: every table reaches a feature, and everything is plottable *to some extent*.
Graded, because 'to some extent' matters — a county-grain subject is honestly grade D and
should never be drawn as a pin.

| grade | meaning | tables |
|---|---|---:|
| **A** | GEOGRAPHY / geometry_geojson — draw the real shape | 37 |
| **B** | publisher lat/lon — draw their pin, never a derived one | 34 |
| **C** | street + city/zip — locatable later, no point invented | 29 |
| **D** | attributable to an area, never to a site | 50 |
| **E** | no geography of any kind held | 49 |

## Grade E, split by whether it MATTERS

**25 are series/aggregate tables — grade E is CORRECT for them.** A monthly price, a statewide demand curve or a utility's annual sales have no location to draw. Operator ruling: do not reload these chasing geometry.

**24 describe a place or a site and have no geography at all — these are the real defects.**

| table | columns |
|---|---:|
| `in_bus_headroom_300` | 5 |
| `in_ghgrp_emissions` | 6 |
| `in_groundwater_sites` | 2 |
| `in_nfirs_basicincident_2020` | 44 |
| `in_nfirs_basicincident_2021` | 44 |
| `in_nfirs_basicincident_2022` | 44 |
| `in_nfirs_basicincident_2023` | 44 |
| `in_nfirs_basicincident_2024` | 44 |
| `in_nfirs_fireincident_2020` | 83 |
| `in_nfirs_fireincident_2021` | 83 |
| `in_nfirs_fireincident_2022` | 83 |
| `in_nfirs_fireincident_2024` | 83 |
| `in_pjm_bus_withdrawal` | 8 |
| `in_pjm_queuescope_aep` | 18 |
| `in_pjm_rtep_cost_allocations` | 7 |
| `in_pjm_rtep_upgrade_details` | 14 |
| `in_pjm_rtep_upgrades` | 34 |
| `in_rto_expansion` | 24 |
| `in_si_candidates` | 10 |
| `in_si_d25_admitted` | 16 |
| `in_si_d25_stb_abandonment_state` | 14 |
| `in_site_gates` | 6 |
| `in_txexp_miso_mtep_appendix_a_status` | 29 |
| `in_ustp_ch7_tfr` | 81 |

<details><summary>Series/aggregate tables at grade E (correctly, no action)</summary>

| table |
|---|
| `in_cems_monthly` |
| `in_commission_posture` |
| `in_dc_docket_tracker` |
| `in_dc_eei_tariffs` |
| `in_drought_by_state` |
| `in_econ_gjf_megadeals` |
| `in_eia861_demand_response` |
| `in_eia861_reliability` |
| `in_eia861_sales` |
| `in_eia861_sales_ult_cust` |
| `in_eia923_fuel_receipts_costs` |
| `in_elec_power_operational` |
| `in_gas_capacity_midwestern` |
| `in_iurc_dockets` |
| `in_openstates_energy_bill_actions` |
| `in_openstates_energy_bill_sources` |
| `in_openstates_energy_bill_sponsorships` |
| `in_openstates_energy_bill_versions` |
| `in_openstates_energy_bill_vote_people` |
| `in_openstates_energy_bill_votes` |
| `in_openstates_energy_bills` |
| `in_openstates_energy_bills_v2` |
| `in_puc_state_access_ledger` |
| `in_state_irp_catalog` |
| `in_utility_tariff_riders` |

</details>

## D county/place only — 50 tables

| table | columns | subject |
|---|---:|---|
| `in_acs_county` | 8 | series/aggregate |
| `in_acs_tract_vacancy` | 22 | place or site |
| `in_cbp_county_industry` | 8 | series/aggregate |
| `in_county_fibre` | 5 | place or site |
| `in_county_flood` | 4 | place or site |
| `in_county_rollup` | 9 | place or site |
| `in_county_wetlands` | 3 | place or site |
| `in_data_centers_cloudscene` | 7 | place or site |
| `in_data_centers_datacentermap` | 7 | place or site |
| `in_dc_actions` | 16 | place or site |
| `in_eia861_territory` | 9 | series/aggregate |
| `in_fcc_bdc` | 17 | series/aggregate |
| `in_fcc_bdc_fixed_summary_by_geography` | 17 | series/aggregate |
| `in_fcc_bdc_mobile_summary` | 16 | series/aggregate |
| `in_fcc_bdc_mobile_summary_by_geography` | 16 | series/aggregate |
| `in_fcc_bdc_provider_summary` | 10 | series/aggregate |
| `in_fcc_bdc_provider_summary_by_geography` | 10 | series/aggregate |
| `in_fema_disaster_declarations` | 12 | series/aggregate |
| `in_fema_nri_counties` | 465 | series/aggregate |
| `in_ferc714_state_demand` | 4 | series/aggregate |
| `in_gas_capacity_anr` | 32 | series/aggregate |
| `in_gas_capacity_crossroads` | 36 | series/aggregate |
| `in_gas_capacity_ngpl` | 24 | series/aggregate |
| `in_gas_capacity_northern_border` | 36 | series/aggregate |
| `in_gas_capacity_panhandle_eastern` | 31 | series/aggregate |
| `in_gas_capacity_texas_gas` | 28 | series/aggregate |
| `in_gas_capacity_trunkline` | 31 | series/aggregate |
| `in_gas_capacity_vector` | 18 | series/aggregate |
| `in_gas_state_capacity` | 12 | series/aggregate |
| `in_grid_plans` | 25 | place or site |
| `in_iocs_county_context` | 6 | series/aggregate |
| `in_news_dc` | 9 | series/aggregate |
| `in_nrc_reactors` | 76 | place or site |
| `in_openstates_energy_bill_abstracts` | 8 | series/aggregate |
| `in_ordinances_dc` | 14 | place or site |
| `in_parcel_attrs` | 9 | place or site |
| `in_pjm_nucra_costs` | 19 | place or site |
| `in_qcew_county_labor` | 10 | series/aggregate |
| `in_queue` | 25 | place or site |
| `in_queue_miso` | 29 | place or site |
| `in_queue_miso_extras` | 21 | place or site |
| `in_si_evansville_demolition_permits` | 33 | place or site |
| `in_si_refresh_iocs_eviction` | 84 | series/aggregate |
| `in_si_refresh_warn_notices` | 11 | place or site |
| `in_si_state_warn_notices` | 11 | place or site |
| `in_sites_county` | 4 | place or site |
| `in_urdb_rates` | 23 | series/aggregate |
| `in_usa_structures_county` | 4 | series/aggregate |
| `in_water_use` | 141 | series/aggregate |
| `in_workforce_ipeds_cs_eng` | 9 | series/aggregate |

## C address-keyable — 29 tables

| table | columns | subject |
|---|---:|---|
| `in_eqr_identity` | 15 | series/aggregate |
| `in_gas_phmsa_distribution` | 753 | series/aggregate |
| `in_gov_surplus_nces` | 67 | place or site |
| `in_nfirs_incidentaddress_2020` | 20 | place or site |
| `in_nfirs_incidentaddress_2021` | 20 | place or site |
| `in_nfirs_incidentaddress_2022` | 20 | place or site |
| `in_nfirs_incidentaddress_2023` | 20 | place or site |
| `in_nfirs_incidentaddress_2024` | 20 | place or site |
| `in_nfirs_structure_fires` | 19 | place or site |
| `in_sba_foia_loans` | 53 | series/aggregate |
| `in_sec_cik_registrant_state` | 17 | place or site |
| `in_si_d11_admitted` | 17 | place or site |
| `in_si_d11_entity_dissolution` | 16 | place or site |
| `in_si_d27_admitted` | 17 | place or site |
| `in_si_d27_ucc_lapse_v2` | 16 | place or site |
| `in_si_evansville_foreclosures` | 456 | place or site |
| `in_si_evansville_taxsale` | 93 | place or site |
| `in_si_evansville_taxsale_transfers` | 83 | place or site |
| `in_si_indy_abandoned_vacant` | 13 | place or site |
| `in_si_indy_surplus_parcels` | 16 | place or site |
| `in_si_indy_taxsale_parcels` | 32 | place or site |
| `in_si_refresh_ibtr_appeals` | 19 | place or site |
| `in_si_refresh_indy_code_enforcement` | 13 | place or site |
| `in_si_signals` | 13 | place or site |
| `in_si_southbend_chronic_problem` | 7 | place or site |
| `in_si_southbend_code_enforcement` | 13 | place or site |
| `in_si_southbend_continuous_enforcement` | 22 | place or site |
| `in_si_southbend_demolition_orders` | 23 | place or site |
| `in_si_southbend_vacant_abandoned` | 24 | place or site |

## Seller-intent tables specifically

27 SI tables. Grade spread:

| grade | n |
|---|---:|
| B published point | 2 |
| C address-keyable | 18 |
| D county/place only | 4 |
| E NOT LOCATABLE | 3 |

| table | grade |
|---|---|
| `in_si_refresh_brownfield_epa_in` | B published point |
| `in_si_refresh_sri_taxsale_in` | B published point |
| `in_si_d11_admitted` | C address-keyable |
| `in_si_d11_entity_dissolution` | C address-keyable |
| `in_si_d27_admitted` | C address-keyable |
| `in_si_d27_ucc_lapse_v2` | C address-keyable |
| `in_si_evansville_foreclosures` | C address-keyable |
| `in_si_evansville_taxsale` | C address-keyable |
| `in_si_evansville_taxsale_transfers` | C address-keyable |
| `in_si_indy_abandoned_vacant` | C address-keyable |
| `in_si_indy_surplus_parcels` | C address-keyable |
| `in_si_indy_taxsale_parcels` | C address-keyable |
| `in_si_refresh_ibtr_appeals` | C address-keyable |
| `in_si_refresh_indy_code_enforcement` | C address-keyable |
| `in_si_signals` | C address-keyable |
| `in_si_southbend_chronic_problem` | C address-keyable |
| `in_si_southbend_code_enforcement` | C address-keyable |
| `in_si_southbend_continuous_enforcement` | C address-keyable |
| `in_si_southbend_demolition_orders` | C address-keyable |
| `in_si_southbend_vacant_abandoned` | C address-keyable |
| `in_si_evansville_demolition_permits` | D county/place only |
| `in_si_refresh_iocs_eviction` | D county/place only |
| `in_si_refresh_warn_notices` | D county/place only |
| `in_si_state_warn_notices` | D county/place only |
| `in_si_candidates` | E NOT LOCATABLE |
| `in_si_d25_admitted` | E NOT LOCATABLE |
| `in_si_d25_stb_abandonment_state` | E NOT LOCATABLE |

