# Indiana dataset backlog — measured census, 2026-08-15

Method: `energy.column_census` scanned for state-keyed columns whose sampled values include
Indiana (a FLOOR — spatial-only families and national series come on top of it). 52 tables
measured; integrated ones excluded below. Never wire by name — every candidate gets a
value-read first.

## Not yet integrated — named, prioritized

| table | what it adds | part |
|---|---|---|
| `eia861_reliability` | SAIDI/SAIFI outage reliability per utility — a DC developer screening metric | P2/P6 |
| `coal_closure_communities` | the FOURTH bonus-credit geography (missed from `in_bonus_geo`) | P4 benefit |
| `nonattainment_areas` | air-permitting gate for on-site generation | P4 |
| `utility_tariff_riders` | rider structures — the large-load rider story | P6 |
| `dc_eei_tariffs` | EEI typical-bill benchmark tariffs | P6 |
| `econ_gjf_megadeals` | economic-development megadeals (incentive context) | P5/P6 |
| `state_irp_catalog` | IRP references per utility | P2 plans |
| `gov_auction_gsa` | federal surplus auctions (A2 extension) | P1 |
| `nfirs_*_2024` | newer-vintage structure-fire incidents (D16 refresh) | P1 |
| `ustp_ch7_tfr` | Chapter-7 trustee final reports (D6 extension) | P1 |
| `queue_miso` | per-ISO queue vintage — diff against `interconnection_queue` before use | P2 |

## Spatial families still to clip/verify for Indiana (no state column)
`agis_*` zoning layers naming Indiana jurisdictions · `mat_structure_footprints` (building
polygons — tile pipeline) · `osm_power_*` · roads/rail/airports (logistics) · faa_obstacles ·
storm/tornado events · ghcn weather stations.

## National series applicable at Indiana grain (P6)
`iso_lmp_nodal_da` (MISO pnode list needed; PJM pnodes HELD — 23,711 rows) ·
`ferc714_*` demand · `eia923/930` fuel & operations · `ng_prices_spot` hubs ·
`eqr_*` (counterparty-keyed; bounded route only, per standing rule).

## Known non-integrations, deliberate
`orennia_*` (never renders — licensed) · `__snapshot/backup` generations (never read) ·
misnamed out-of-state parcel tables listed by the census (`parcels_ky_*` etc. holding IN
border slivers — geography-evidence class, handled by the spine already).
