# HANDOFF — Indiana Siting Intelligence (updated 2026-08-15, session closed clean)

**✅ RESOLVED 2026-08-15 — the exact-acres re-export is complete and consistent.** Rather than
splice the partial 44 counties from `0c9405c` onto the other 48 (two generations, one map —
the §AC partial-swap hazard), all 92 were rewritten from ONE query snapshot by the new
`scripts/export_sites_exact.py`, which refuses to write at all if `in_sites` lacks the exact
columns. Measured: 92 files, 1,200,916 features — **identical to the committed row count**, so
columns were added and no rows lost; all 92 carry all 7 exact-family fields; 8.5% of sampled
parcels differ materially from the legacy approximation (had it been ~0%, the columns would
have been a copy). Cost 2.2 GB ≈ $0.01. `0c9405c` no longer needs recovering.

**A defect the re-export exposed — read this before touching the acreage ladder.** Preferring
`exact_outdoor_acres` blindly is wrong for a measurable minority. Across the class union,
**126 of 1,200,924** parcels report an exact parcel area below half the recorded acreage, and
for **85** of them `footprints_intersecting` is ZERO. With nothing intersecting, outdoor area
*is* the parcel by arithmetic — so a smaller exact figure is the exact pipeline's geometry
disagreeing with the recorded acreage, not a measurement of buildings. The cost was concrete:
**23 parcels of 75+ acres (300 MW at 4 MW/acre) dropped out of the screener with no footprint
to blame**, on the exact use case this app exists for. Fixed by a single `acreageOf(p)` used by
the screener, the tooltip AND the panel (they could otherwise disagree about one parcel): when
nothing intersects, trust the parcel area, and say so. The example parcel `020406400005000062`
went from "fits 2 MW" to "fits 181 MW". Nothing is swallowed — the panel prints the exact figure
unchanged and a banner naming the disagreement. **Still open for the operator:** the other
41 shrunk parcels (footprints > 0, so a large building *might* explain them) and 107 parcels
where exact runs over 200% of legacy. Neither is auto-corrected.

**SESSION-CLOSE STATE:** roadmap T1–T8 all closed or operator-gated (T2 packet awaits
per-item sign-off; T7 awaits the WSL/Docker install; T8 cadence awaits venue choice).
Nothing running, nothing uncommitted, no open instrument questions. The next session
(Opus 5) starts at §5's roadmap — first action is T1's verification check, second is
processing whatever sign-offs the operator has returned from docs/SIGNOFF_PACKET.md.

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

**T3 — DONE 2026-08-15.** FCC county detail lives in data/county_context.json as
ctx.by_fips[fips].fcc {units, fiber_units, gig_units, cable_100_20_units} +
.fcc_mobile {pct_4g, pct_5g}; rendered in BOTH the parcel panel's county section and the
county panel (app.js). Grain lesson recorded: the fixed summary is geography×technology×
biz_res×area_data_type — the county slice is geography_type='County', area_data_type='Total',
biz_res='B', technology IN ('Fiber','Cable'). Script: scripts/build_t3_t4.py (replaces, never
accumulates). Verified: Marion = 297,517 of 480,853 business units fiber ≥100/20.

**T4 — DONE 2026-08-15.** si_by_signal {signal, n, counties, latest} in state_summary.json;
si.html renders the 17-row inventory with bars; totals conserve to 1,818,158 exactly.

**T5 — Gas OAC locations table on market.html.** From in_gas_capacity_panhandle_eastern +
_trunkline (State='IN'): location name, county, design capacity, OAC, gas day → new
data/gas_locations.json.gz + a Market card. Acceptance: 203 rows total, county column filled.

**T6 — Rate proxy (ONLY after reading energy-platform/ANALYSIS_METHODOLOGY.md end-to-end).**
Inputs: in_urdb_rates (demand + energy components), user MW + load factor + class. Output:
yearly cost band per tariff, labeled "proxy from published tariff structure — not a quote".
Add to market.html with adjustable inputs. Acceptance: CPS-style decomposition shown
(fixed/demand/energy) and every number carries the tariff's name.

**T2 — PACKET DELIVERED 2026-08-15:** docs/SIGNOFF_PACKET.md holds the measured vocabularies
for all 8 pending judgments (D11/D25/D27/MF/cloudscene/airports/queue_miso/DC-dedupe preview).
Await the operator's per-item APPROVE/REJECT/DEFER; wire only what is approved.

**T5 — DONE 2026-08-15:** data/gas_locations.json.gz (203 IN locations, PEPL+Trunkline,
design/OAC verbatim) rendered on market.html.

**T6 — DONE 2026-08-15 (cross-check grade, per ANALYSIS_METHODOLOGY §4 which was read first):**
yearly-cost proxy on market.html — MW/load-factor/sector inputs → per-tariff $/yr range +
effective ¢/kWh from URDB demand+energy maxima. URDB is FLATTENED (no riders/fixed/seasonal),
so this is explicitly a cross-check; the itemised rate engine (four-proxy rule, 1.75×
wholesale-floor gate, CPS_35MW_Rate_Model.xlsx shape) remains the full milestone.

**T7 — PMTiles (BLOCKED until the operator installs WSL or Docker — re-measured absent 2026-08-15).** Then: export
in_sites (all 3.55M, exact geometry) to GeoJSONL, tippecanoe -Z12 -z16 --no-feature-limit,
split files <100 MB, swap the per-county gz loader for a pmtiles source. Do not start
before the install exists.

**T8 — Refresh cadence (PROPOSED 2026-08-15, awaiting operator approval to schedule):**
| script | cadence | why |
|---|---|---|
| scrapers/lane_e/pull_ebb_capacity.py + load_to_bq.py | daily (gas day) | OAC changes every gas day |
| scrapers/lane_a/pull_miso_poi_300mw.py | quarterly | study-cycle vintage |
| scrapers/lane_d/0*.py (all six SI refreshes) | weekly | the P1 refresh commitment |
| lane_b 04_iurc_dockets + 09_news | weekly | new filings/news |
| scripts/build_* re-exports + provenance | after any refresh | payloads must match BQ |
| I&M PROD_MI_HC_GRID groupBy probe | quarterly | catch the day Indiana rows appear |
All idempotent; zero agent tokens; each refresh appends a registry row. Windows Task
Scheduler or a cloud cron both work — operator picks the venue.

**DO NOT (Opus-specific guardrails):** do not re-audit the estate (it is DONE — read the
verdicts); do not launch agents for anything a script in scripts/ or scrapers/ already
does; do not touch energy.* except reads + APPEND to registry_sources; do not read
SAMPLES_*.md whole (grep per table); do not re-derive headroom (both derivations are
final and documented — §2 above); do not change payload schemas without updating every
page that reads them (grep the field name across *.html and app.js first).

## 5b. COMPLETED AFTER THE ROADMAP WAS WRITTEN (do not redo)

- **T1 VERIFIED 2026-08-15 (Opus 5 session), both checks PASS + one defect fixed:**
  data.html reads **188 registered tables** / 3,553,194 parcels / built 2026-08-15T16:13Z
  (188 is the true count — "~190" in T1 was approximate, not a shortfall). Upload door:
  a 2-row lat/lon CSV returns *"2 placed · 0 outside Indiana · 0 cannot-place"*, and the
  placements are correct on inspection — Terre Haute→Vigo County (0.3 mi to substation),
  Fort Wayne→Allen County (0.45 mi).
  **DEFECT FOUND AND FIXED — the logistics layer never rendered.** `line-dasharray` is a
  data-CONSTANT property in MapLibre; app.js passed it a `["case", …]` expression, so
  `addLayer` rejected `log-lines` outright while the source loaded fine. The `L-log`
  checkbox therefore toggled a layer that did not exist and the `getLayer` guard swallowed
  it silently — 3,203 rail/road segments (shipped in a7a8a9b) had been invisible ever since.
  Fix: split into `log-lines` (roads, solid, filter `layer != rail`) and `log-lines-rail`
  (dashed, filter `layer == rail`); registry entry `L-log` now lists both ids. Verified
  after the fix: both layers exist and read `visible`, 392 road + 620 rail features
  rendered in-viewport, source holds all 3,203.
  **Lesson for the class:** a MapLibre paint property that rejects an expression fails
  SILENTLY behind a `getLayer` guard. When a toggle appears to do nothing, check
  `map.getLayer(id)` before suspecting the data.
  **Testing note:** Python's `SimpleHTTP` sends `Last-Modified` but no `Cache-Control`, so
  Chrome serves a stale app.js from memory cache after an edit; `location.reload(true)` is
  ignored. Open a NEW TAB to load edited JS — that worked deterministically every time.


- **ALL EIGHT SIGN-OFFS APPROVED AND WIRED 2026-08-15.** Operator approved the v2 recommendation
  table wholesale. `scripts/build_signoff_wiring.py` builds seven tables (each registered in the
  same run, each deleting its own prior registry row so re-runs cannot accumulate);
  `scripts/export_signoff_payloads.py` exports them. Both idempotent, both dry-run first, total
  cost under 0.01 GB.
  | # | table | rows | what was EXCLUDED, and why |
  |---|---|---:|---|
  | 1 | `in_si_d11_admitted` | 983 | 1,146 `withdrawn` — surrendered/reinstatable authority is weaker evidence a property is coming free |
  | 2 | `in_si_d25_admitted` | 127 | 747 procedural filings — a law firm's extension request is not an abandonment |
  | 3 | `in_si_d27_admitted` | 156 | nothing; all address-keyed at quality 0.8 |
  | 4 | `in_iocs_county_context` | 92 | the `STATE` total row and `nan` residue — **62% of the raw MF sum** |
  | 5 | `in_cloudscene_crosscheck` | 260 | nothing, but lat/lon are explicit NULLs so nothing can plot it |
  | 7 | `in_queue_miso_extras` | 456 | kept as a JOIN only — 452 ids duplicate interconnection_queue |
  | 8 | `in_data_centers_deduped` | 242 | 2 rows absorbed by 3 name-stem pairs (two pairs absorb the same OSM row) |
  Item 6 (airports) needed no table — the flag was closed as a false alarm.
  **Pages wired:** SI Feed gains an admitted-vs-source table (every count with its denominator
  and the rule that produced it) plus D11/D25/D27 browsers; Community gains county court activity;
  Data gains the cloudscene cross-check; Grid gains the MISO study-cycle table with a phase filter.
  **Two errors caught during this work, both mine:**
  · **A string date lied about a signal's vintage.** `filed_date` is a STRING `m/d/Y`, so my probe's
    `MIN/MAX` was LEXICOGRAPHIC — `'9/5/2019'` outranked `'1/23/2017'` on the leading character. I
    recorded "events run 2007-2019, treat as historic". Parsed properly the range is
    **2002-06-21 → 2026-01-05**, the newest being a Central Railroad of Indianapolis abandonment
    exemption. D25 is a CURRENT signal. The page now derives its own span from ISO dates and only
    warns when the newest event is genuinely over two years old. **Never aggregate a string date.**
  · **The Data page overstated the table count by 11%.** Early scripts INSERTed a registry row per
    re-run without clearing the old one, so `_registry` held 216 rows for 195 tables
    (`in_grid_plans` and `in_si_candidates` 4× each) and the management-facing "registered tables"
    stat read 216. Provenance now takes the latest row per table; the ledger keeps every build as
    an audit trail and the page explains the difference rather than hiding it.
  **And one that would have embarrassed us in a deck:** the cloudscene cross-check first read
  "254 of 260 not in our layer". Reading the names shows **229 are carrier central offices, 223 of
  them Frontier** — telecom plant, never data centres. The real question is the 31 genuine colo
  facilities, of which 6 match and **25 are worth investigating**. The card now splits them.
- **OPERATOR RULINGS 2026-08-15 — buildable area now depends on the use case.**
  *"C&I outdoor space is only for BESS, as a hyperscale DC would build over it or remove the
  structure."* So `acreageOf()` takes a use case: **DC = whole parcel** (the structure is
  demolition scope, not an obstacle), **BESS = outdoor space** (parcel − measured footprints).
  A `Use case` selector drives it and moves the density default 4↔10 — but only when the density
  is still one of those defaults, so a number the user typed is never silently overwritten.
  For vacant land the two bases are identical, so the ruling only moves parcels with structures.
  **Measured in Marion County: C&I parcels passing "fits ≥25 MW" go 853 → 1,099 (+29%);
  ≥300 MW goes 159 → 166.** The RANKING barely moves (P3 saturates at 2× target, so anything
  over ~12.5 ac already scored 100) — the ruling's effect is on ELIGIBILITY, not ordering. The
  parcel panel shows both bases side by side so the other use case is always one glance away.
  *Second ruling:* county active-queue MW **counts as supply** (favourable). The competing
  reading — those projects contend for the same interconnection capacity — was considered and
  rejected; the basis text now states it as a ruling, not an open assumption.
- **COMPOSITE SCORING SHIPPED 2026-08-15 (PLAN Phase 3 ②, spec §11).** 0–100 sub-scores each
  carrying a stated basis → six part scores → composite; **assessable-only averaging at every
  level** (a part we cannot measure leaves the denominator, never becomes a zero); six weight
  sliders with visible defaults; every ranked row opens a breakdown showing each part's score,
  its basis and its weight, plus a link into the full parcel evidence. All tunables live in one
  `SCORE_CFG` object — the "no hard-coded weights, config-driven" rule.
  **Two scales were invented and had to be replaced by measured ones — the §4 trap again:**
  · P5 first scored `opposition_intensity` linearly to a guessed ceiling of 8, and **every
    Marion County parcel came out 0**. The real distribution across 92 counties is min 0,
    median 0, p75 2, p90 4 — and then Marion alone at 25, three times the next county
    (Marshall, 8). A linear scale either flattens 90% of the state or zeroes its largest metro.
    P5 now scores the publisher's own posture vocabulary (quiet 61 counties / active_discussion
    22 / restricted 8 / contested 1), honours `has_local_restriction` as a hard floor, and
    reports intensity as context — with the caveat that intensity partly tracks news volume, so
    large metros read higher.
  · P6 saturated at a round 1,000 MW; it now uses the measured p90 of the 87 counties holding a
    queue figure (median 259, p75 700, **p90 1,493**, max 7,977).
  **§2.21 check (a ranked list dominated by one subgroup means ranking selects for the error),
  run on Marion's 43,086 parcels:** healthy. Top-100 median 18.7 ac against an overall max of
  1,286 ac — the saturating P3 stops the biggest polygon winning by default, which is the
  failure mode that lets an inverted full-globe parcel top a siting search. Zero disputed-acreage
  parcels reach the top 100. Composites spread 25–75 across 48 distinct values with no top tie.
  **Two honest limits to state to users:** P1 yields only two distinct values (0 or 65) because
  `si_signal_types` rarely exceeds 1, so it ranks has-signal vs not, nothing finer; and top-100
  is 88% `no_structure` against 70% overall, because a C&I parcel with a building on it has less
  buildable outdoor space — defensible, but C&I sites are structurally outranked and the operator
  should know before weighting.
  **Assumption flagged for the operator:** county active-queue MW is scored as FAVOURABLE
  (generation arriving nearby). It can be read the opposite way — those projects compete for the
  same interconnection capacity. Stated in the basis text rather than buried.
- **SI-RECENCY FILTER FIXED (same pass) — it was dropping 99.4% of SI parcels.** The test read
  `(p.si_last_event_date || "") < cutoff`, so a NULL date sorted below every cutoff and the parcel
  was silently excluded as if it were stale. Measured over 7 counties: **165,494 parcels carry an
  SI signal and only 935 (0.6%) carry an event date.** That penalised sites for OUR coverage gap —
  precisely what the spec's availability-normalisation rule forbids. Undated parcels now pass the
  recency filter and are COUNTED, with the count shown under the denominator as a cannot-assess
  line. Root cause is upstream: `si_last_event_date` is essentially unpopulated in `in_sites`;
  worth a data-ops question if recency is ever to be a real filter.
- **EXACT-ACRES RE-EXPORT CLOSED 2026-08-15** — see the ✅ block at the top of this file for the
  measurements, the `acreageOf()` fix and the two questions still open for the operator. Script:
  `scripts/export_sites_exact.py` (idempotent, guarded, one snapshot for all 92 counties).
- **CSV export fidelity fixed (same pass):** `export-csv` built its header from `rows[0]`'s keys,
  so a first row lacking the screener's per-parcel `_dsub_*`/`_dpoi_*` attachments would silently
  drop those columns for the whole file. Now a union of all rows' keys, matching what the upload
  export already did.
- **T2 PACKET REBUILT 2026-08-15 (v2) — v1 was not answerable.** Measured on open: items 1, 4
  and 7 were BigQuery *errors* (`status`, `case_type`, `q_id` — all guessed, none read first;
  the §4 worst practice, committed by the packet builder itself) and items 5-6 answered a
  different question than the one posed. `scripts/build_signoff_packet_v2.py` reads every
  schema before querying it. Five findings changed the questions themselves:
  · **D25** — the multi-state worry was minor (737 name one state, 137 name two). The real
    issue is that most of the 874 are *procedural paperwork about* an abandonment (Reply 185,
    Extension 150, Certificate Of Service 26); only **127** are event filings.
  · **IOCS MF** — unanswerable as posed. The table is a court-statistics WORKBOOK: one row per
    court, every case-type code is a COLUMN of counts. MF is a per-court aggregate, never a
    per-address event, so it cannot be a parcel-grain signal at any confidence. It also carries
    two poison rows — `County_Name='STATE'` (a statewide total, 21,300) and `'nan'` (10,235) —
    which is why the county list reads 94 for a 92-county state.
  · **cloudscene** — `market` is the state key (`<state>-regional` buckets across the table:
    illinois 322, texas 300, california 295 …), giving **260** Indiana rows. Checked rather than
    assumed, because Indiana County *Pennsylvania* is real. But cloudscene has NO coordinates —
    schema is slug/name/city/state/market/url — so it can never be a layer.
  · **airports** — the batch-4 "format-suspect" flag was WRONG. It is an 86-row curated national
    set; exactly one row is in Indiana geometrically (Indianapolis Intl) and `state` says `IN`.
    The instrument was right. Flag closed.
  · **queue_miso** — 452 of 456 Indiana ids also live in interconnection_queue (near-total
    duplicate), but it alone carries `studyphase`/`poiname`/DPP ERIS-NRIS MW. Waive as a layer,
    keep as a join.
  · **DC dedupe** — v1's preview showed proximity-only pairs, i.e. not the proposed rule. Applied
    properly, the name-stem rule collapses **3** pairs and correctly refuses to merge the New
    Carlisle campus buildings; the open judgment is OSM's 8 unnamed rows.
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
