# Measured Indiana data inventory

All figures below were **measured by live query on 2026-08-14** against
`energy-platfrom.energy` and clipped into `energy-platfrom.indiana_app`.
`indiana_app._registry` is the authoritative registry of what this app reads (source,
method, rows, GB scanned, built_at); this page mirrors it for readers without BigQuery
access. Denominators are stated with every coverage claim.

## The Indiana clips (indiana_app.*, built 2026-08-14, ~456 GB scanned ≈ $2.85 one-time)

| table | rows | source | note |
|---|---:|---|---|
| `in_sites` | 3,553,194 | `vw_parcel_sites` | ALL parcels, SI-agnostic. 2,284,133 with a building; 3,553,193 carry the parcel's own polygon (all but one); 511,715 fit ≥25 MW at the adjustable 4 MW/acre default |
| `in_si_signals` | 1,818,158 | `si_signals` | 17 of 29 weighted signal types (denominator: `si_weights.json`). Vacancy + code-violation are 93% of rows — the tail is thin and the app must show the denominator |
| `in_substations` | 3,858 | `mat_grid_substations` | HIFLD + OSM, deduped |
| `in_transmission_lines` | 2,623 | `transmission_lines` | spatial clip to the state polygon |
| `in_queue` | 948 | `interconnection_queue` | includes withdrawn (a deliberate signal) |
| `in_queue_counties` | 87 | `vw_grid_queue_counties` | county rollup; 87 of 92 counties |
| `in_pjm_queuescope_aep` | 303,671 | `pjm_queuescope_results` | AEP = the Indiana Michigan Power (PJM) sliver |
| `in_miso_poi` | **0** | `miso_poi_monitored_facilities` | ⚠ see defect note below |
| `in_water` | 2,415,369 | `nhd_flowline` | surface-water gate |
| `in_fcc_bdc` | 12,649,532 | `fcc_bdc_fixed_availability` | fibre gate; aggregate to block/tract before shipping to the app |
| `in_wetlands` | 453,995 | `nwi_wetlands` | |
| `in_flood` | 66,140 | `nfhl_flood_zones` | via `src_state` (the DFIRM prefix workaround was unnecessary) |
| `in_padus` | 4,736 | `padus` | protected land |
| `in_bonus_geo` | 836 | 4 tables unioned | energy communities (8) + LIC tracts (662) + opportunity zones (156, 0 geometry parse failures) + critical habitat (10) |
| `in_cems_monthly` | 50,132 | `cems_hourly` | plant-unit-month rollup of 36,034,944 IN hourly rows |

## Coverage verdicts per part (HAVE / PARTIAL / CANNOT-ASSESS)

- **P1 seller-intent: PARTIAL.** 17 of 29 signal types present; 8 of the 17 hold <500
  rows. Per-signal receipts and the availability-normalised score handle thinness; the
  missing 12 types are scrape lanes (see SCRAPE_LANES.md).
- **P2 grid: PARTIAL, transmission-first.** Substations, lines, queues, and the PJM/AEP
  bus results are solid. ⚠ **The feeder-level hosting-capacity layer contains zero
  Indiana utilities** (measured across all 54 utilities in `vw_hc_map`) — Indiana
  utilities publish no ICA-style maps we hold. ⚠ **Our MISO POI copy has degenerate
  identity columns**: `fr_bus`/`to_bus` = 0 and lat/lon = 0.0 on **all 904,486 rows**;
  only `poi_name` (11,820 POIs) and the MW metrics survived the harvest. Per-POI MISO
  headroom is computable but not yet placeable on a map. Re-acquisition lane opened.
- **P3 land: HAVE.** The strongest part; see `in_sites`.
- **P3b water/fibre: HAVE** (raw). Both need aggregation design before shipping.
- **P4 environmental: HAVE**, risk and benefit halves both present.
- **P5 sentiment: THIN — the priority scrape target.** ~400 Indiana receipt-grade rows
  total across all held sentiment tables (ordinances 183, state-keyed news 97+12,
  opposition tracker 50, reddit ~40 text-match floor, bans 1 state + 8 county rows,
  FERC large-load dockets 0, civic minutes 0, ballot measures 0). The county-posture
  view covers all 92 counties but one of its receipt counters reads >0 on 92/92 —
  suspected instrument defect, not rendered until verified.
- **P6 market: HAVE.** CEMS, MISO/PJM LMP (node→state mapping still needed to isolate
  Indiana nodes), EIA-861 (10,928 rows / 120 utility-county entries), URDB (969 Indiana
  tariff rows / 70 utilities). The existing rate-quote engine is reused, not rewritten.

## Standing cautions

- A table's name is not its subject; every table above was value-sampled before use.
- `cannot assess` rows are retained and labelled; they are never dropped or zeroed.
- Superseded/backup generations (`__snapshot`, `__pre_swap`, …) are never read.
