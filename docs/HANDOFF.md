# HANDOFF — Indiana Siting Intelligence (written 2026-08-15, end of the Phase-2 session)

**Read this first, then PLAN.md, then AUDIT_WORKLIST.md.** Everything below is committed on
`main` at github.com/ahenderson0233/indiana-application-decennial. The operator pulls/pushes
to rebuild GitHub Pages. Session cost across the whole build: ~$5-6 of BigQuery.

## What this is

A self-contained, static, Indiana-only siting app (P1–P6 + a scope-limited P7 preview),
serving two goals: live hyperscale/BESS siting (~300 MW class, statewide, PJM emphasized as
an ordering tiebreaker only) and the working baseline for the national application.
GitHub Pages, no backend: BigQuery → gzipped GeoJSON/JSON payloads in `data/` → committed.

## Warehouse facts

- Everything lives in **`energy-platfrom.indiana_app`** (spelling intentional). `energy.*` is
  READ-ONLY to this workstream; another session owns it and `energy-platform/ingest/`.
- **`indiana_app._registry` is the authority**: 188+ tables, each with source, method, rows,
  gb_scanned, built_at, notes. `data/state_summary.json` mirrors it for the app.
- `_indiana_census` holds the per-table Indiana verification (773 keyed tables measured;
  308 Indiana-positive; zeros re-tested with widened predicates).
- Rebuild anything by re-running its script in `scripts/` (all idempotent, dry-run-guarded,
  registered-in-run). Refreshes are SCRIPT runs, never agent runs.

## The audit (COMPLETE — docs/AUDIT_WORKLIST.md has every verdict)

All 2,161 usable estate tables classified: verified-308 (batches 1–4), zeros re-test
(80 disguised finds → 6 genuine clips + mailing-state waivers), spatial by source identity,
national by page assignment, 151-table eyeball queue (batches 5–6b). Instrument bugs the
audit itself caught are recorded (\_st_pct regex, ZCTA prefix, LIMIT-vs-TABLESAMPLE).
**Standing rule: a name is never a subject — value-read before wiring; no-state-column
never means not-applicable.**

## The app (Phase 2 SHIPPED)

Six pages sharing `common.js` + nav: **index** (map console: 4 part-presets framing, all
layers composable; screener composes class/MW-density/SI-recency/grid-distance/gates/
sentiment; measure tool; shortlist; dossier print; CSV export), **grid.html** (PJM LOAD
headroom table + MISO 300MW injection + plans + RTEP drill-down + queue), **market.html**
(demand/CEMS charts, reliability, gas design + OAC, tariffs), **community.html** (receipts
browser + posture), **si.html** (signal state 17/29, acquisitions, freshness), **data.html**
(188-table provenance + honesty ledger).

Map layers: 1.2M class-union parcels (exact geometry, county-lazy gz), counties (100% of
3,553,194 parcels counted), substations/lines/MISO POIs/PJM buses+queue points/gas/
territories/protected/bonus(5 kinds)/nonattainment/candidates/**244 existing DCs**/
plants·solar·wind/logistics. Estimates always style apart (hollow red = estimated location).

## THE headroom story (decision-grade, both directions disclosed)

- **PJM/I&M = the DC direction.** `in_pjm_bus_withdrawal`: per-bus LOAD headroom, 2027 RTEP
  Summer Peak, MIN(available_mw) over |dfax|≥5% facilities, pre-existing overloads EXCLUDED
  and counted (measured identity: every zero row was a pre-overload). All 1,475 buses
  positive (q: 2/31/52/132 MW). No bus clears 300 MW without upgrades — the upgrade/cost
  answer is in in_pjm_rtep_* + in_pjm_nucra_costs.
- **MISO public viewer = INJECTION-only.** Bounded 300 MW re-harvest
  (scrapers/lane_a/pull_miso_poi_300mw.py): 641/642 IN POIs read 0 — real, DPP-2021 vintage.
  **Open lane: a MISO LOAD-direction source.** Bus locations solved: in_miso_poi_identity
  (9,981 publisher coords).
- Orennia yardstick (LOCAL ONLY, never rendered/committed): our MISO coords == their
  ISO-sourced rows (median 0 m); their PJM locations are all estimates too (median 93 m
  agreement with ours). in_pjm_bus_locations_candidate: 229 located (91 high), methods on
  every row.

## Open items, in the order the operator set

1. Subject sign-offs (operator): D21 candidates done; pending — D11/D25/D27 first-rows,
   IOCS `MF` foreclosure code, cloudscene state vocabulary, in_data_centers_all dedupe rule,
   `airports` format flag, queue_miso-vs-interconnection_queue diff.
2. Phase-2 leftovers: FCC mobile/fibre detail into county evidence; gas-OAC per-location
   section; SI inventory chart on si.html.
3. Phase 3: upload door (client-side CSV → same screener), composite scoring with user
   weights, rate-engine port (tariff-structure yearly-cost proxy per site size/class),
   PMTiles all-parcel rendering (needs WSL or Docker install — the one machine prerequisite).
4. Acquisition lanes open: MISO load-direction; owner data via county assessor rolls
   (statewide layer has NO owner — measured; unblocks D18 + approach workflow); A1 listings;
   Vanderburgh child parcels; EBB history depth.
5. Upstream questions filed: mat_parcel_attrs IN slice 100% NULL (all attribute columns,
   all 3.55M rows); vw_county_dc_posture ordinance counter reads 92/92 (suspect).

## Traps this project already paid for (do not re-earn)

Backticks/backslashes through shells → Write/Edit files. BigQuery reserved words (rows).
`SELECT * LIMIT` bills full columns → TABLESAMPLE on monsters. A zero is an instrument claim
(suspect JOIN → FILTER → DATA). MIN-over-facilities collapses at infinite probes — bound the
request or gate by dfax + pre-overload. Owner-mailing-state columns masquerade as location.
ZCTA codes are not FIPS. Never `git add -A`; never commit another session's in-flight files.
