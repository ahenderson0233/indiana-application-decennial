# GAP REGISTER — measured 2026-08-15

Every known gap, measured against BigQuery rather than recalled. Written before Phase B so
the operator can rule on each one. Nothing here is an estimate.

## 1. What `indiana_app` holds

| kind | n |
|---|---:|
| base table | 201 |
| registered in `_registry` | 200 |

The website reads 196 of these (98%); the 3 that do not reach a surface are deliberate
and carry written waivers (`_indiana_census` meta table + 2 zero-row FCC tables).

## 2. Indiana-positive tables in `energy` never clipped into `indiana_app`

_census columns: table_id, method, key_column, in_rows, total_rows, measured_at_

The census holds 773 rows. Per-table clip status:

Census: **308 of 773 tables carry Indiana rows.** 227 have no `in_` table of their own — but that headline is misleading, because most are reached through a derived table or were waived with a reason during the audit. Classified:

| class | tables |
|---|---:|
| spine internal (reached via a derived table) | 29 |
| other-state / owner-mailing-state (waived in audit) | 141 |
| reached through a pre-aggregated derivative | 5 |
| GENUINELY UNWIRED — needs an operator ruling | 52 |

### The 52 genuinely unwired, largest first

| table | indiana rows | of total | keyed by |
|---|---:|---:|---|
| `si_d5_struct_pts` | 3,377,472 | 135,338,769 | state |
| `nat_usa_structures` | 3,377,472 | 135,371,228 | state |
| `si_d5_addr_pts` | 2,149,657 | 52,082,602 | state |
| `si_scored_v3_variants` | 1,205,602 | 83,429,361 | state |
| `si_d5_vacancy_derived` | 967,366 | 22,295,965 | state |
| `si_d12_indy_marion_code_enforcement` | 910,483 | 910,483 | state |
| `agis_indy_code_enforcement` | 906,326 | 910,483 | state |
| `si_d1_sri_taxsale_listings` | 81,975 | 217,226 | state |
| `agis_indy_taxsale` | 62,368 | 62,368 | state |
| `si_d8_exit_intent` | 13,414 | 2,840,865 | state |
| `eia861_service_territory` | 10,928 | 280,398 | state |
| `land_padus` | 4,137 | 439,860 | state |
| `si_d11_entity_dissolution_v2` | 3,384 | 4,702,667 | state |
| `nat_substations_hifld` | 2,077 | 75,328 | state |
| `epa_brownfields` | 1,613 | 44,134 | state |
| `si_d17_in_iocs_court_year` | 1,543 | 1,543 | state |
| `brownfield_epa_repowering` | 1,483 | 190,976 | state |
| `brownfields` | 1,347 | 37,026 | state |
| `si_signals_d19_new_20260803` | 1,039 | 52,507 | state |
| `si_signals_d19_pre_widen_20260803` | 1,037 | 27,573 | state |
| `lbnl_interconnection_queue` | 948 | 38,201 | state |
| `interconnection_queue` | 948 | 38,201 | state |
| `txexp_pjm_rtep_upgrades` | 929 | 15,440 | state |
| `iso_interconnection_queue` | 888 | 24,030 | state |
| `txexp_miso_mtep_appendix_a_in_service` | 693 | 5,183 | state |
| `low_income_bonus_tracts` | 665 | 35,423 | geoid |
| `gas_eia_state_capacity` | 471 | 19,311 | state |
| `incentive_qct` | 337 | 15,727 | state |
| `coal_closure_communities` | 184 | 4,325 | state |
| `si_register` | 160 | 93,757 | state |
| `incentive_opportunity_zones` | 156 | 8,765 | state |
| `electric_retail_service_territories` | 114 | 2,931 | state |
| `googlenews_dc_state` | 97 | 3,598 | state |
| `county_boundaries` | 92 | 3,235 | state |
| `parcel_county_register` | 92 | 3,233 | state |
| `parcel_county_coverage` | 92 | 3,233 | state |
| `seismic_design` | 88 | 3,163 | state |
| `txexp_miso_mtep_under_evaluation` | 76 | 597 | state |
| `dc_opposition_tracker` | 50 | 1,342 | state |
| `nonattainment_areas` | 35 | 792 | state |
| `gas_storage_facilities` | 22 | 486 | state |
| `ut_tax_liens_v2` | 16 | 26,345 | state |
| `bingnews_dc_state` | 12 | 469 | state |
| `si_d27_ucc_lapse` | 10 | 529,266 | state |
| `energy_communities_msa` | 8 | 901 | state |
| `openstates_bulk_session_coverage` | 3 | 139 | state |
| `state_boundaries` | 1 | 56 | state |
| `appeals_tx_comptroller_arb_protests_2024` | 1 | 253 | state |
| `si_d17_ny_oca_landlord_tenant_cases` | 1 | 903,594 | state |
| `si_d2_md_statewide_forecl_by_county` | 1 | 177 | state |
| `airports` | 1 | 86 | state |
| `dc_bans` | 1 | 213 | state |


## 3. Seller-intent signals present vs absent

**17 signals carry Indiana rows.**

| signal | rows | counties | latest event |
|---|---:|---:|---|
| D5_vacancy | 947,592 | 92 | 2024-01-01 |
| D12_code_violation | 747,211 | 0 | 2024-02-27 |
| D2_foreclosure | 62,451 | 0 | 2026-10-20 |
| D16_structure_fire | 28,581 | 0 | 2024-12-31 |
| D1_tax_sale | 17,605 | 0 | 2026-09-28 |
| D26_assessment_appeal | 6,953 | 0 | 2026-08-05 |
| D14_sba_chargeoff | 3,774 | 0 | 2026-06-23 |
| D7_brownfield | 1,378 | 0 | — |
| D19_warn | 1,039 | 0 | 2026-07-21 |
| D20_loan_maturity | 419 | 0 | 2036-03-01 |
| D6_bankruptcy | 393 | 0 | 2026-08-06 |
| D17_commercial_eviction | 370 | 92 | 2025-01-01 |
| D25_rail_abandonment | 215 | 0 | 2026-07-01 |
| D8_exit_intent | 142 | 0 | 2008-09-01 |
| A2_gov_surplus | 20 | 0 | 2024-09-30 |
| D24_plant_delisting | 13 | 0 | 2026-03-11 |
| D3_seized_auction | 2 | 0 | 2026-06-05 |

## 3a. TIMING — where event dates exist, and where they are lost

The operator's priority: *a code violation in the 1990s does not help us.* Per signal, how many rows carry an observed event date, and how recent are they?

| signal | rows | dated | span | last 3 yrs | last 1 yr |
|---|---:|---:|---|---:|---:|
| D5_vacancy | 947,592 | 1,696 (0%) | 2024-01-01 → 2024-01-01 | 1,696 | 0 |
| D12_code_violation | 747,211 | 747,211 (100%) | 2010-03-29 → 2024-02-27 | 18,372 | 0 |
| D2_foreclosure | 62,451 | 61,617 (99%) | 2000-03-27 → 2026-10-20 | 8,944 | 3,907 |
| D16_structure_fire | 28,581 | 28,581 (100%) | 2020-01-01 → 2024-12-31 | 9,465 | 0 |
| D1_tax_sale | 17,605 | 17,605 (100%) | 2021-10-22 → 2026-09-28 | 15,087 | 14,548 |
| D26_assessment_appeal | 6,953 | 6,953 (100%) | 2004-01-07 → 2026-08-05 | 1,082 | 517 |
| D14_sba_chargeoff | 3,774 | 3,774 (100%) | 1992-12-24 → 2026-06-23 | 179 | 53 |
| D7_brownfield | 1,378 | 0 (0%) | — → — | 0 | 0 |
| D19_warn | 1,039 | 981 (94%) | 1994-05-12 → 2026-07-21 | 111 | 34 |
| D20_loan_maturity | 419 | 185 (44%) | 2023-10-01 → 2036-03-01 | 185 | 184 |
| D6_bankruptcy | 393 | 393 (100%) | 2000-01-01 → 2026-08-06 | 109 | 85 |
| D17_commercial_eviction | 370 | 370 (100%) | 2022-01-01 → 2025-01-01 | 185 | 0 |
| D25_rail_abandonment | 215 | 215 (100%) | 2002-01-01 → 2026-07-01 | 9 | 5 |
| D8_exit_intent | 142 | 141 (99%) | 1990-09-01 → 2008-09-01 | 0 | 0 |
| A2_gov_surplus | 20 | 18 (90%) | 2013-10-01 → 2024-09-30 | 14 | 0 |
| D24_plant_delisting | 13 | 13 (100%) | 2023-09-13 → 2026-03-11 | 13 | 4 |
| D3_seized_auction | 2 | 2 (100%) | 2025-03-10 → 2026-06-05 | 2 | 1 |

**Totals: 869,755 of 1,818,158 SI rows (47.8%) carry an event date. Only 55,453 (3.0%) are from the last three years and 19,338 (1.1%) from the last one.**

So the SI corpus is mostly HISTORIC. Filtering to what would actually move an owner today collapses it hard — which is the honest answer, and the reason recency has to be a first-class filter rather than a nicety.

Separately, the date does NOT reach the parcel: `si_last_event_date` on `in_sites` is populated for ~0.6% of SI parcels (935 of 165,494 measured over 7 counties). The dates exist in `in_si_signals` but are lost in the join onto parcels — that propagation, not re-scraping, is the first fix.


County attribution is absent on 15 of 17 signals (only `D5_vacancy` carries `county_fips`). Operator ruling 2026-08-15: **lower priority, we can derive county ourselves** from the parcel or address geography. Noted, not chased.

The engine's weighted model defines 29 signals; the absent ones are the acquisition
backlog below.

## 4. Signal tables held but not feeding `in_si_signals`

| table | rows |
|---|---:|
| `in_si_candidates` | 3,841 |
| `in_si_d11_admitted` | 983 |
| `in_si_d11_entity_dissolution` | 2,129 |
| `in_si_d25_admitted` | 127 |
| `in_si_d25_stb_abandonment_state` | 874 |
| `in_si_d27_admitted` | 156 |
| `in_si_d27_ucc_lapse_v2` | 156 |
| `in_si_evansville_demolition_permits` | 4,190 |
| `in_si_evansville_foreclosures` | 5,758 |
| `in_si_evansville_taxsale` | 3,202 |
| `in_si_evansville_taxsale_transfers` | 941 |
| `in_si_indy_abandoned_vacant` | 7,120 |
| `in_si_indy_surplus_parcels` | 595 |
| `in_si_indy_taxsale_parcels` | 62,368 |
| `in_si_refresh_brownfield_epa_in` | 1,483 |
| `in_si_refresh_ibtr_appeals` | 10,152 |
| `in_si_refresh_indy_code_enforcement` | 910,483 |
| `in_si_refresh_iocs_eviction` | 6,519 |
| `in_si_refresh_sri_taxsale_in` | 83,547 |
| `in_si_refresh_warn_notices` | 1,220 |
| `in_si_signals` | 1,818,158 |
| `in_si_southbend_chronic_problem` | 7 |
| `in_si_southbend_code_enforcement` | 20,414 |
| `in_si_southbend_continuous_enforcement` | 241 |
| `in_si_southbend_demolition_orders` | 80 |
| `in_si_southbend_vacant_abandoned` | 47 |
| `in_si_state_warn_notices` | 1,220 |


## 5. Signals absent from the Indiana feed — the acquisition backlog

**12 of the 29 modelled signals carry no Indiana rows.** These need exploration or scraping. Per the operator's standing instruction, any pull takes **ALL columns**: an endpoint often carries more than one signal, and the Lane D pulls proved it (§6 below).

| signal | what it is |
|---|---|
| **A1** | market listing |
| **D10** | underutilisation |
| **D11** | entity dissolution |
| **D13** | utility shutoff |
| **D15** | lien filing |
| **D18** | owner age / estate |
| **D21** | demolition permit |
| **D22** | environmental violation |
| **D23** | public surplus disposal |
| **D27** | UCC lapse |
| **D4** | tax delinquency |
| **D9** | absentee owner |

Note: D11, D21, D27 already have Indiana rows STAGED and admitted by operator sign-off (`in_si_d11_admitted` 983, `in_si_candidates` D21, `in_si_d27_admitted` 156) but have not been folded back into `in_si_signals` itself. Those are a wiring step, not an acquisition.

## 6. Already pulled, never wired — extra signals inside endpoints we already have

Lane D pulled all columns from six sources and found signal-bearing columns nobody had asked for. **These need no scraping — the data is already in BigQuery.** From `scrapers/lane_d/LANE_D_FINDINGS.md`:

| table | column | what it carries |
|---|---|---|
| `in_si_refresh_sri_taxsale_in` | `saleTypeDescription` | Foreclosure 62,760 · Tax Sale 15,860 · Certificate Sale 4,851 · Deed Sale 76 — a finer subtype than the open/resolved split |
| `in_si_refresh_sri_taxsale_in` | `latitude`/`longitude` | 29,955 of 83,547 (35.9%) — **direct plotting**, no geocoding needed |
| `in_si_refresh_indy_code_enforcement` | `CASE_TYPE` | a full violation taxonomy — Unsafe Buildings, Vacant Board Order, Illegal Dumping, Zoning, Environmental — not one 'code enforcement' bucket |
| `in_si_refresh_indy_code_enforcement` | `LINK` | 910,483/910,483 (100%) direct Accela case-detail URLs — a free verification drilldown on every row |
| `in_si_refresh_indy_code_enforcement` | `TOWNSHIP` | free sub-county geography on every row (watch the doubled `'CENTER,CENTER'` publisher artifact) |
| `in_si_refresh_warn_notices` | `NAICS` | 6-digit industry code on all but 204 rows — lets WARN be filtered to industries that own real estate |
| `in_si_refresh_warn_notices` | `col_8__href` | 172 direct links to the WARN letter PDF |
| `in_si_refresh_ibtr_appeals` | `appealTypeName` | Form 131/133/132/139 petition types, never surfaced |
| `in_si_refresh_ibtr_appeals` | `attachmentDescriptions` | document-type breadcrumb finer than `statusName` |
| `in_si_refresh_brownfield_epa_in` | `Program` | BROWNFIELDS 1,247 · RCRA 127 · LANDFILL METHANE 54 · SUPERFUND 53 |
| `in_si_refresh_brownfield_epa_in` | `Landfill` / `AML` | binary flags, 83 and 4 respectively |
| `in_si_refresh_iocs_eviction` | `MF` | mortgage foreclosure — **WIRED 2026-08-15** as county context |

Eleven of the twelve remain unwired. This is the cheapest coverage available: no scraping, no new source, no permission question.

## 7. Scrape status — where the SI re-pull actually stands

`scrapers/lane_d/LANE_D_FINDINGS.md`, verified against BigQuery rather than its own scratch files:

- **All six Lane D scripts COMPLETED** — 6 tables, 1,013,404 rows, all columns, all registered. Only `02_indy_code_enforcement` had never run; it ran and returned 910,483 rows matching the publisher count exactly.
- **A publisher-side staleness finding, not ours:** Indy code enforcement's `OPEN_DATE` spans exactly 2010-03-29 → 2024-02-27 with zero rows after. The publisher's layer has not opened a case in 2.5 years — re-pulling it again changes nothing.
- **10 of 19 Indiana-feeding `si_signals` source_ids have NO live endpoint identified at all**, including the largest signal, `si_d5_vacancy_derived` (945,896 rows), which is derived and has no endpoint of its own. Those need discovery before any re-pull.
- **One paywall, standing:** `si_d25` InBiz bulk data — $9,500 + $500/mo, rejected. Recorded BLOCKED with the exact wall; not re-probed.
- The IOCS 2026 workbook 404s: the publisher has not posted it yet. Not a wall.

