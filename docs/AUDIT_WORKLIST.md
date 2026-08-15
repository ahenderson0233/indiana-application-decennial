# Table-by-table audit worklist — resumable, append-only

**Protocol** (any session continues from here): work the verified Indiana list
(BQ_INDIANA_CENSUS.md) top-down in batches of ~40, then the zero/spatial/national classes.
Per table: read its sample in SAMPLES_INDIANA.md / SAMPLES_ALL_PART2.md, judge the SUBJECT
from values (never the name), record a verdict here:
`WIRED (feature)` · `WIRE-NEXT (target feature/page)` · `WAIVE (reason)` · `FLAG (operator judgment)`.
A verdict written from census+prior evidence without its sample read is marked `(sample-check pending)`.

## Batch 1 — top of the verified list (2026-08-15)

| table | IN rows | verdict |
|---|---:|---|
| `cems_hourly` | 36.0M | WIRED (Market panel via in_cems_monthly) |
| `mat_parcel_key_index` | 13.9M | WAIVE (join infrastructure, serves the spine) |
| `fcc_bdc_fixed_availability` | 12.6M | WIRED (county fibre gates) |
| `mat_parcel_grid` / `mat_parcel_all(_v2)` / `mat_parcel_geo(_supplement)` | 3.6-4.1M | WAIVE (spine internals feeding vw_parcel_sites → in_sites) |
| `mat_parcel_attrs` | 3.55M | FLAG (IN slice 100% NULL upstream — question filed) |
| `mat_parcel_structures` / `mat_siting_parcels` | 3.55M | WIRED (the sites spine) |
| `nat_usa_structures` / `si_d5_struct_pts` | 3.38M | WIRE-NEXT (building footprints/points at parcel click; tile-pipeline for polygons) |
| `nhd_flowline` | 2.4M | WIRED (in_water; county grain pending tiles) |
| `mat_si_*` scored/plottable/county | 1.2-2.3M | WIRED (SI columns on sites) |
| `si_d5_vacancy_derived` / `si_wire_*` | 0.9-1.0M | WAIVE (engine internals of si_signals) |
| `si_d12_indy_marion_code_enforcement` / `agis_indy_code_enforcement` | 910k | WIRED (D12 in si_signals; refresh landed; publisher stale since 2024-02) |
| `nwi_wetlands` | 454k | WIRED (gates) |
| **`nhd_waterbody`** | **187k** | **WIRE-NEXT (water gate complement — lakes/reservoirs; cooling-water siting)** |
| **`ferc714_state_demand`** | **167k** | **WIRE-NEXT (Market page: Indiana demand curve — P6)** |
| `mat_si_address_location` | 96k | WAIVE (location ladder internal) |
| `si_d1_sri_taxsale_listings` | 82k | WIRED (D1; refreshed by Lane D) |
| `nfhl_flood_zones` | 66k | WIRED (gates) |
| `agis_indy_taxsale` | 62k | WIRED (D1 source; also staged Marion archive) |
| **`nfirs_*_2022/2023/2024`** | **40-50k/yr** | **WIRE-NEXT (D16 structure-fire vintages beyond current wiring; value-read first)** |
| **`parcels_fl` reporting 31,079 IN rows** | 31k | **FLAG (a Florida-named table with IN state values — misnamed-source class or mailing-state column; sample-read before any use)** |
| **`spc_severe_events`** | **25k** | **WIRE-NEXT (P4 risk: severe weather/tornado events at county grain)** |
| **`faa_obstacles`** | **16k** | **WIRE-NEXT (P4/logistics: obstacle proximity gate)** |
| `si_d8_exit_intent` | 13k | WIRED (D8) |
| **`echo_cwa_facilities`** | **13k** | **WIRE-NEXT (water-permit facilities — water context + SI-adjacent closure signal)** |

## Standing WIRE-NEXT queue (from earlier passes)
utility_tariff_riders · dc_eei_tariffs · econ_gjf_megadeals · state_irp_catalog ·
gov_auction_gsa · ustp_ch7_tfr · queue_miso (diff vs interconnection_queue first) ·
openstates energy bills (Indiana slice — the P7 preview with in_iurc_dockets + in_grid_plans) ·
gas OAC tables → Market page · MISO pnode list (registry check first) → LMP at IN nodes.

## Batch 2 — verified rows 46-130 (2026-08-15)

**CLIPPED + REGISTERED (25 tables, WIRE-NEXT batch 2):** eia860_generators (12,479 — Indiana
plants/generators, never wired), eia_plants, eia860m_generators, storm_events, osm_power_lines,
osm_power_substations (named — PJM bus-match fodder), openstates_energy_bill_{vote_people,
actions,sponsorships} (the P7 legislative preview), ghgrp_facilities + emitters, wind_turbines,
gov_surplus_frpp, fema_disaster_declarations, weather_stations, eia923_fuel_receipts_costs,
eia861_demand_response, water_cwns_2022 (wastewater capacity), sba_foia_loans, acs_tract_vacancy,
eqr_identity (2,635 IN-registered sellers — the BOUNDED route into eqr_*), gas_phmsa_distribution,
candidate_sites_schools ×2 (upload-door demo sets), nfirs_fireincident_2024. Plus incentive_qct
→ bonus set (337, fifth bonus kind).

**WAIVE — engine/spine internals:** mat_si_* buildings/scored/rooftop/building_in_parcel
(superseded or internal), si_wire_*, si_coverage_matrix, si_signals_d19_* snapshots,
dim_jurisdiction, block_groups, census_tracts (join spines).

**WAIVE — owner-mailing-state pattern (§D.8):** out-of-state parcels_* tables reporting "IN"
rows (sc_abbeville 2,045, mn 1,961, az_maricopa 1,584, tx 1,403, ny 698, pa 491, …) — the state
column is the OWNER's mailing state, not parcel location. Same class: socrata_cook_bor_appeals,
agis_detroit_blight_tickets, parcels_fl (batch-1 flag RESOLVED to this class). Reverse-absentee
context only.

**WIRED already:** eia861_service_territory, padus (+land_padus: duplicate-copy flag for dedupe),
substations/nat_substations_hifld (feed mat_grid_substations), interconnection_queue
(lbnl_/iso_ variants: same-source diff pending), txexp_*, si_d17_in_iocs_court_year,
brownfields family, gas_eia_state_capacity.

## Remaining batches
Batch 2+: rest of the 308 (rows 46-308) · then the 465 measured zeros (eyeball samples for
disguised Indiana) · then spatial-only via source identity + PARCEL_SOURCE_GEOGRAPHY ·
then national-grain page assignments · then class G (45 unread).
