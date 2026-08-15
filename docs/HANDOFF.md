# HANDOFF — Indiana Siting Intelligence (updated 2026-08-15)

The single document a fresh session reads first. Everything is committed on `main` at
github.com/ahenderson0233/indiana-application-decennial; the operator pulls/pushes to
rebuild GitHub Pages. Total BigQuery spend across the whole build: ~$6.

## 0. REQUIRED READING, IN THIS ORDER

**This repo (the app's own context):**
1. `docs/HANDOFF.md` — this file
2. `docs/PLAN.md` — the locked plan (wire → pages → functionality)
3. `docs/AUDIT_WORKLIST.md` — every table's verdict, batch by batch, flags included
4. `docs/BQ_INDIANA_CENSUS.md` — the estate classification + verified per-table IN counts
5. `docs/AUDIT_CLASSES_REPORT.md` — zeros/spatial/national resolutions
6. `docs/DATA.md`, `docs/ARCHITECTURE.md`, `docs/SCRAPE_LANES.md`, `docs/DATA_BACKLOG.md`
7. `docs/SAMPLES_INDIANA.md` + `docs/SAMPLES_ALL_PART2.md` — 1-3 raw rows of every estate
   table (grep per table; never load whole — 2.3 MB combined)
8. `scrapers/lane_[a-e]/LANE_*_FINDINGS.md` — per-lane results, walls, next endpoints

**The platform (parent project — read-only reference, another session owns it):**
9. `energy-platform/CLAUDE.md` — the real one (repo-root and mirror copies are pointers);
   reading order, non-negotiables, the four things that mislead
10. `energy-platform/REBUILD_PLANNING/METHODS.md` §A-§AD — every rule was earned; §A tells,
    §V zeros, §Z multi-signal tables, §AB measure-the-pipeline-first are the big four
11. `REBUILD_PLANNING/1_SCOPE_AND_OBJECTIVES.md` + `2_TECHNICAL_BUILD_SPEC.md` — the seven
    parts, the golden path, §11 map/score/evidence contracts, §13 acceptance
12. `REBUILD_PLANNING/START_HERE.md` — TOP BLOCKS ONLY (orientation ≤10% of a context)
13. `REBUILD_PLANNING/DECISIONS_INDEX.md` → grep DECISIONS.md, never read linearly
14. `REBUILD_PLANNING/WASTED_WORK_LEDGER.md` — read before calling ANYTHING a gap
15. `REBUILD_PLANNING/FABLE5_PREAMBLE.md` — paste above any ad-hoc scrape request
16. `ANALYSIS_METHODOLOGY.md` — REQUIRED before computing any siting/rate/land NUMBER
    (not yet read by this workstream — counts only so far; read before rate-engine work)

**The registry (how sources are documented):**
- `energy.registry_sources` is the source-of-truth for source status — APPEND-only rows
  (never MERGE/TRUNCATE — D25), `object_names` is a REPEATED field, status vocabulary
  'done'/'blocked', walls recorded verbatim in notes, endpoints mechanical not name-matched
  (W17). This session appended 31 rows (updated_by='indiana-app-session-20260815').
- `indiana_app._registry` is the per-TABLE build ledger (source, method, n_rows, built_at,
  notes) — every table this workstream creates gets a row IN THE SAME RUN.
- Scrape rules: only what a source permits; no accounts/terms/CAPTCHA/paywalls; gated =
  BLOCKED with the exact wall; outFields=*/every layer; observed event dates never pull
  timestamps; ≥1s/host; UA identifies us; check registry + docs/SAMPLES before acquiring.

## 1. THE ENTIRE PLAN, START TO FINISH

- **P0 — bootstrap (DONE):** repo, `indiana_app` dataset, Indiana clips of the core estate,
  measured per-part coverage, architecture (static: BQ → gzipped payloads → Pages).
- **P1 — map spine (DONE):** county layer counting 100% of 3,553,194 parcels; 1.2M
  class-union parcels with exact geometry, lazy per county; screener composing
  class/MW-density/SI-recency/grid-distance/gates/county-sentiment; evidence panels with
  provenance; measure tool; shortlist; CSV; print dossier.
- **P2 — wire the estate + pages (DONE):** the full audit (2,161 tables classified, ~190
  registered Indiana tables), both-RTO headroom with direction disclosed, six-tab app
  (Map / Grid & Capacity / Market & Rates / Community & Regulatory / SI Feed / Data),
  layers for existing DCs/facilities/gas/logistics/territories/environmental.
- **P3 — functionality (CURRENT):** ① upload door (client-side CSV → same screener/evidence
  — the spec's first-class-citizen commitment); ② composite scoring with user weights
  (assessable-only averaging); ③ rate-engine proxy (yearly cost from tariff structures at
  the user's size/class — read ANALYSIS_METHODOLOGY first); ④ PMTiles all-parcel rendering
  (needs the ONE machine install: WSL or Docker for tippecanoe).
- **P4 — depth passes:** subject sign-offs graduating staged signals to candidates; DC
  dedupe rule; FCC fibre/mobile detail per county; gas-OAC per-location; SI inventory
  charts; RTEP drill-down joins to buses; dossier v2 (2-5 page P1-P6 verdict per site).
- **P5 — acquisition lanes still open:** MISO LOAD-direction headroom; owner data via
  county assessor rolls (statewide layer has NO owner — measured; unblocks D18 + the
  approach workflow); A1 listings; Vanderburgh child parcels; EBB history depth; scheduled
  refresh runs (scripts are idempotent — cron them, zero agent tokens).
- **P6 — handover to national:** everything here is the national baseline: the payload
  contract, the honesty grammar, per-source registries, the audit method, and the
  SPP/CartoVista/EBB findings already flagged for the national app.

## 2. WHAT WE'VE WORKED THROUGH (proof points, all measured)

Coverage per part measured day one and re-verified; parcels 3,553,194 (all but one with
geometry); the 308 Indiana-positive keyed tables audited one-by-one; PJM load headroom
per bus (all 1,475 positive after excluding pre-existing overloads — measured identity:
zeros==pre-overloads); MISO bounded 300MW harvest (641/642 zero injection — real,
injection-only disclosed); 244 existing DCs plotted (DCM "pinless" was stale); gas OAC
for 9 pipelines; Orennia yardstick run LOCALLY (our MISO coords == their ISO rows at 0 m;
their PJM locations are estimates like ours, 93 m median agreement) — Orennia data never
renders, never exports, never enters repo/warehouse.

## 3. BEST PRACTICES (earned here)

Measure before claiming; dry-run everything; value-read before wiring; denominators on
screen; cannot-assess rendered as itself; estimates styled apart; direction of headroom
disclosed; per-row match_method/confidence on any derived location; widened-predicate
re-tests before accepting zeros; source identity beats name inference; batch by emitted
SQL length; TABLESAMPLE on monsters; commit small with measured messages; scripts not
agents for refreshes; agents only for NEW sources with the FABLE5 rules embedded.

## 4. WORST PRACTICES (each cost us time THIS build — do not repeat)

Guessing column names (apn_key, area_name, PMax, listing_url — all bit us); reserved words
(`rows`, `FULL`); backticks/backslashes through shells (use Write + `-F`); `SELECT * LIMIT`
on monsters (bills full columns); short-token regexes (`_st_pct` matched as "state");
assuming ZCTA=FIPS; trusting a summary's claim that scripts "were pending" (verify against
BQ); MIN-over-facilities at an infinite probe; treating publisher 0,0 coords as locations;
letting a preset lock layers users need to compose.

## 5. THE OPUS 5 ROADMAP — do these IN ORDER, exactly as written

The next session runs on Opus 5. Follow this list top-down; do not invent new workstreams;
if a step's acceptance check fails, stop and report rather than improvising.

**Setup (every session):**
```
cd "C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
git pull
```
BigQuery from the platform venv, always with these env vars:
```
cd "C:\Users\ahend\Downloads\Decennial Summer Work\Remaking Orennia\energy-platform"
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\Users\ahend\bq-key.json"; $env:PYTHONIOENCODING="utf-8"
.venv\Scripts\python.exe <script>
```
Preview: the `.claude/launch.json` config `indiana-app` serves the repo at localhost:8123.
Commit style: explicit paths (never `git add -A`), message via `-F <file>` if it has
backticks, push after each completed task.

**T1 — Verify state (10 min).** Open localhost:8123 → data.html must show ~190 tables;
index.html → upload a 2-row lat/lon CSV → status must read "2 placed". If either fails,
diagnose before anything else (console errors first).

**T2 — Operator sign-off packet (read-only queries, present, wait).** For each of:
in_si_d11_entity_dissolution, in_si_d25_stb_abandonment_state, in_si_d27_ucc_lapse_v2,
in_data_centers_cloudscene, energy tables airports + queue_miso — run
`SELECT * FROM <table> LIMIT 10` plus a GROUP BY on the subject-looking column; show the
operator the value vocabulary; ask them to confirm each mapping. DO NOT wire without the
answer. For in_data_centers_all dedupe: propose "same name-stem within 500 m across
sources → keep one row, list sources"; implement ONLY after approval.

**T3 — FCC county detail into county evidence.** Data: indiana_app.in_fcc_bdc_fixed_summary_by_geography
(15,900) + in_fcc_bdc_mobile_summary (533). Read 5 rows first. Add per-county fields into
data/county_context.json (extend scripts/build_p36_wiring.py pattern: merge into
ctx["by_fips"][fips]["fcc"]) and render 2-3 rows in openCountyEvidence (app.js).
Acceptance: click Marion County → FCC rows appear with a prov() line.

**T4 — SI inventory chart on si.html.** One BQ export: signal × count from
indiana_app.in_si_signals GROUP BY signal → add to data/state_summary.json as
"si_by_signal"; render a table+bars on si.html. Acceptance: 17 rows, totals match 1,818,158.

**T5 — Gas OAC locations table on market.html.** From in_gas_capacity_panhandle_eastern +
_trunkline (State='IN'): location name, county, design capacity, OAC, gas day → new
data/gas_locations.json.gz + a Market card. Acceptance: 203 rows total, county column filled.

**T6 — Rate proxy (ONLY after reading energy-platform/ANALYSIS_METHODOLOGY.md end-to-end).**
Inputs: in_urdb_rates (demand + energy components), user MW + load factor + class. Output:
yearly cost band per tariff, labeled "proxy from published tariff structure — not a quote".
Add to market.html with adjustable inputs. Acceptance: CPS-style decomposition shown
(fixed/demand/energy) and every number carries the tariff's name.

**T7 — PMTiles (BLOCKED until the operator installs WSL or Docker).** Then: export
in_sites (all 3.55M, exact geometry) to GeoJSONL, tippecanoe -Z12 -z16 --no-feature-limit,
split files <100 MB, swap the per-county gz loader for a pmtiles source. Do not start
before the install exists.

**T8 — Refresh cadence.** All scrapers/lane_d + lane_e scripts are idempotent; propose a
weekly script-run schedule to the operator (zero agent tokens). Registry rows get a new
append per refresh.

**DO NOT (Opus-specific guardrails):** do not re-audit the estate (it is DONE — read the
verdicts); do not launch agents for anything a script in scripts/ or scrapers/ already
does; do not touch energy.* except reads + APPEND to registry_sources; do not read
SAMPLES_*.md whole (grep per table); do not re-derive headroom (both derivations are
final and documented — §2 above); do not change payload schemas without updating every
page that reads them (grep the field name across *.html and app.js first).

## 5b. COMPLETED AFTER THE ROADMAP WAS WRITTEN (do not redo)

- **T-upload (DONE, verified):** upload door live on index.html — client-side CSV,
  point-in-county, grid distances, county context, enriched export, cannot-place kept.
- **EXACT outdoor space (DONE):** the data-ops session shipped mat_parcel_outdoor_exact
  (117.4M; 3,552,799 IN) into vw_parcel_sites; in_sites RE-CLIPPED with
  exact_outdoor_acres/exact_bldg_acres/mw_*_exact (measured: ge25MW 511,715→511,665,
  avg delta 0.01 ac — aggregate honest, per-parcel shared-footprint overcounts fixed).
  Screener + parcel evidence now prefer exact; site files re-exported with the columns.
- **31 lane sources appended to energy.registry_sources** (script:
  scripts/register_lane_sources.py; updated_by indiana-app-session-20260815).
- **T3 DONE:** FCC county detail merged into county_context (all 92 counties: business
  broadband units + fiber/gig units + 5G area pct; scripts/build_t3_t4.py + fix_t3_fcc.py)
  and rendered in both county evidence panels.
- **T4 DONE:** SI-by-signal inventory in state_summary (17 signals, conserves to
  1,818,158 exactly) and charted on si.html.
- **docs/OPUS5_PROMPT.md** holds the paste-ready opening prompt for the next session.
- **Site-file re-export with exact columns:** launched this session; if data/sites/*.gz
  lack exact_outdoor_acres, rerun scripts/build_site_gates.py (idempotent) — check the
  latest commit message first.

## 6. CURRENTLY IN FLIGHT / AWAITING OPERATOR

Upload door being built now. Awaiting operator: D11/D25/D27 + MF subject sign-offs;
in_data_centers_all dedupe rule; cloudscene vocabulary; airports format flag;
queue_miso-vs-interconnection_queue diff; WSL/Docker install for PMTiles; the
mat_parcel_attrs NULL question filed upstream (data-ops session).
