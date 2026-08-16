# HANDOFF — Indiana Siting Intelligence

# ══ CHECKPOINT 2026-08-15 (late session) — READ THIS BLOCK FIRST ══

**Read `docs/GAMEPLAN.md` immediately after this file.** HANDOFF is the RECORD of what happened;
GAMEPLAN is the PLAN and the backlog. Everything below is measured, not recalled.

## Where the application stands

| | |
|---|---:|
| tables in `indiana_app` | 201 + 12 views |
| registered in `_registry` | 199 |
| **reaching a user-facing surface** | **196 of 199 (98%)** — was 139 when Phase A began |
| not reaching a surface | 3, all deliberate, each with a written waiver |
| pages live | 6 (Map · Grid · Market · Community · SI Feed · Data) |
| parcels held / class-union rendered | 3,553,194 / 1,200,916 |
| transmission after the HIFLD+OSM merge | 3,737 lines / 27,866 km |
| substations after the merge | 3,858 (2,925 points + 933 footprints) |
| data centres | 249 pins, 157 site-precision, 92 flagged city-centroid |

**PHASE A IS COMPLETE.** A1–A6 all closed. Phase B is under way.

## ⚠ STILL RUNNING AS THIS CHECKPOINT WAS WRITTEN — do not restart blindly

Three agents and one job were live. They survive a context refresh; check their outputs before
re-launching anything.

1. **D22 ECHO pull** — `scrapers/lane_f/pull_d22_environmental.py`, background job. Walks 92
   counties (statewide is refused: *"Rows Returned would be 127266. Queryset Limit would be
   exceeded"*). **Now hitting HTTP 429 — ECHO is RATE-LIMITING us at 1.1 s/request.** Two things
   to fix before trusting a run: raise the pause (try 3–5 s) and add SHORTFALL detection — Adams
   returned 825 of 928 on a short page and that was silently accepted. The script's file is
   MODIFIED and UNCOMMITTED.
2. **SI date-keying agent** — building `scripts/build_si_date_keying.py` (present, untracked) and
   `docs/SI_DATE_KEYING.md`. Task: match the dated address-only SI rows to parcels using an
   EXISTING normalisation (`energy.mat_si_address_location`, 95,967 IN rows) — explicitly told
   NOT to invent an address-normalisation function.
3. **Abandoned-property agent** — writing `scrapers/lane_f/ABANDONED_PROPERTY_FINDINGS.md`.
   Task: find abandoned/vacant STRUCTURE registries beyond Indy and South Bend across the other
   90 counties.
   **WHEN IT FINISHES, do this:** read its verdict table; for every source marked VIABLE, write an
   ALL-COLUMNS loader in `scrapers/lane_f/` following the pattern of
   `pull_d22_environmental.py` (bounded retry on 500/502/503/429 only, publisher-count check,
   register in the same run, `_pulled_at` stored separately from the publisher's event date).
   Load into `indiana_app` as `in_si_d5_abandoned_<jurisdiction>`, then UNION them into
   `in_si_d5_abandoned_buildings` (currently 7,174 rows, Indy + South Bend only). Prioritise any
   source that (a) carries an EVENT DATE — ours currently do not, which is their main weakness —
   and (b) includes COMMERCIAL structures; a 100%-residential registry is low value because a
   house cannot host a hyperscale DC. Record every BLOCKED source in `registry_sources` with its
   wall verbatim.
   **BOTH AGENTS HAVE NOW FINISHED.** Date-keying result is in the B2 section below; the
   abandoned-property result is here:

### Abandoned-property discovery — RESULT (`scrapers/lane_f/ABANDONED_PROPERTY_FINDINGS.md`)

**The two-city concentration is a PUBLISHING gap, not a search gap.** Of 15 cities checked, 13
publish no registry, unsafe-building or demolition list as data at all — Muncie, Evansville and
Hammond run registries on paper; Terre Haute, Anderson and Kokomo condemn via board minutes and
newspaper notices. Statewide, nothing exists (IHCDA's BEP is dead, DLGF marks vacant *land* only,
HUD/USPS vacancy is registration-gated tract aggregate).

**⭐ THE BIGGEST WIN NEEDS NO SCRAPING — do this first.** The 910,483-row Indy code-enforcement
corpus we already hold contains `CASE_TYPE` values **"Unsafe Buildings"** and **"Vacant Board
Order"** — *with OPEN_DATE*. Deriving those subsets both **extends** the abandoned-building signal
and **retro-fits the event dates the 7,120-row registry lacks**. Free, immediate, already in
BigQuery.

Other findings:
- **Indy's registry is titled "Abandoned and Vacant HOUSES"** — residential, so low hyperscale
  value on its own, and it has **no event-date field**. It has also been **delisted from
  data.indy.gov**; the `gis.indy.gov` REST layer is the last public copy. Re-verified at exactly
  7,120 rows — no fuller version exists.
- **South Bend (47) is the only Indiana dataset with a true designation date** (`Added_to_V_A_on_`)
  and is live-maintained (edited 2025-04).
- **One genuinely new viable source: Evansville Land Bank, 123 parcels via a public FeatureServer.**
- Muncie LB and Uplands Regional LB (the only one listing COMMERCIAL) are public but bot-blocked
  SPAs → browser-lane candidates, not scriptable.
- Fort Wayne walled (403s, Beacon ToS); Gary dead (both domains) with its inventory now on Regrid
  — recorded as a ToS wall, not probed.
- Realistic new-row ceiling from the open web: **~123 now, ~150–600 more via a browser session.**
- Search trap recorded: `open-data-cfw` is Fort **Worth**, not Fort Wayne.

**Acquisition order:** derive-from-held (Unsafe Buildings + Vacant Board Order) → Evansville Land
Bank → South Bend refresh cadence → browser lane → APRA public-records requests.

## The five findings from this session that change what the app claims

1. **52% of the SI corpus was not a seller-intent signal.** `D5_vacancy` was 947,592 rows, of
   which 945,896 (99.8%) were *footprint absence* — a parcel with no building, which is a land
   state we already carry as `occ_group='no_structure'`, not intent to sell. **840,819 of 847,410
   signal-flagged parcels (99.2%) were empty land**, so the screener's "Requires seller-intent
   signal" filter has been selecting vacant land. Split into
   `in_si_d5_abandoned_buildings` (7,174 — the real signal) and
   `in_si_d5_vacant_land_NOT_A_SIGNAL` (945,896). **Vacant land REMAINS in the app** as a screener
   class and as the BESS sizing basis; it simply stops counting as intent.
2. **Removing that non-signal repaired the date picture.** The corpus becomes 872,262 rows, of
   which **869,755 are dated (99.7%)**, not the 47.8% previously reported — that figure was itself
   an artifact of counting 945,896 undated rows as a signal. 55,453 events fall in the last 3 years.
3. **92 of 242 data-centre pins were census CITY CENTROIDS** rendered as facility locations
   (`datacentermap` publishes `precision='city'`), with 32 stacked on one point near New Carlisle
   including Microsoft Mishawaka ~15 km away. Now tiered and drawn apart. **National scope: 4,370
   rows sit in stacks of 5+, worst 251** — filed to the platform session's backlog.
4. **The map was drawing 2,925 of 3,858 substations.** The missing 933 carry no lat/lon, only a
   footprint polygon — and they are exactly the OSM-only ones. Now drawn as real footprints, and
   the screener's distance index grew 2,925 → 8,219 entries by binning polygon vertices.
5. **NFIRS needed three filters, not one.** Only ~21% of incidents are structure fires; of those,
   78% report zero property loss; and most are residential. The funnel is 76,779 raw → 16,264
   structure fires → 3,082 non-residential → **469 SI-grade** (non-residential, ≥$10k loss).

## B2 RESULT — the parcel layer is blind to 44,806 real dated distress signals

The date-keying agent finished. `in_si_address_parcel_bridge` (51,309 addresses → 45,822 parcels)
and `in_si_signals_parcel_dated` (46,790 rows, 63,329 events) are built and registered.

**The headline is not the yield, it is what the yield exposed.** Only **1,016 of the 45,822
newly-dated parcels are flagged `has_si_signal`** — meaning **44,806 parcels carry a real, dated
distress signal that the application cannot currently see.** The cause is the D5 problem from the
other direction: the parcel-keyed block is ONE signal (945,896 rows of `D5_vacancy`, which has zero
dates), so `has_si_signal` has been functioning as a vacancy flag, and `si_last_event_date` could
never have been populated from it. **Widening `has_si_signal` beyond D5 is now the single highest-
value fix in the app** — bigger than any acquisition.

Measured, and deliberately not dressed up:
- bridge yield **20.5%** of distinct addresses (51,309 of 250,063), **7.4%** of rows, **31.4%** of
  rows within 3 years. The ceiling is UPSTREAM GEOCODE COVERAGE, not the join: only 37.6% of the
  signal addresses are present in `mat_si_address_location` at all, and only 20.7% are resolved.
- before/after on the flagged population is small and honest: **2,985 → 3,886 dated (+901)**.
- **`D12_code_violation` (747,122 rows) matched exactly ZERO.** Its addresses carry no city suffix
  while the bridge and every other source do, so none are even present. That is a loader defect in
  `si_d12_indy_marion_code_enforcement`. The agent correctly did NOT write a compensating regex —
  and a generous diagnostic shows fixing it would recover only 1,593 addresses (1.0%), because the
  bridge holds just 2,713 resolved Indianapolis addresses. **Geocoding Indianapolis is the real fix.**
  Excluding D12, the address block matches 55.5%.

**D85 CONFIRMED LIVE AND UNREPAIRED.** The spatial join matched 100% on its first run — which was
the defect, not success. `parcels_in/080500000047000018` is an inverted whole-Earth polygon
(196,936,707 sq mi, `structure_count` 3,377,472) that swallowed all 51,821 points. Excluded, the
match is 50,865 (98.2%) and fan-out drops 2.0 → 1.015. **Any spatial join against `in_sites` must
exclude that parcel until it is fixed upstream.**

Also recorded: 14,304 rows carry LEGITIMATE future dates (scheduled tax sales, loan maturity to
2036-03-01), so the build keeps `max_observed_date` and `max_past_observed_date` as separate
columns rather than treating a future date as an error.

## Operator rulings issued this session — all binding

- **Buildable area depends on use case.** Hyperscale DC = WHOLE PARCEL (a structure is demolition
  scope); BESS = OUTDOOR SPACE. Moved C&I parcels passing "fits ≥25 MW" from 853 → 1,099 in Marion.
- **County active-queue MW counts as SUPPLY** (favourable), not as competing demand.
- **SI only counts at the NON-RESIDENTIAL level**, and only where severity would plausibly move an
  owner to sell — a contained fire or a gas leak is not seller intent.
- **Union-and-dedupe every duplicated subject**; never show two partial layers of one thing.
- **Market/series tables do NOT need geometry** and must not be reloaded chasing it.
- **Vacancy is two distinct things**; only the abandoned BUILDING is a signal.
- **Schools and weather stations removed** from the app (schools were an Illinois experiment).
- Vacant land stays in the app for BESS siting, just not as an SI signal.

## Instrument failures caught this session — the pattern to keep repeating

Every one of these produced a confident wrong number before being caught. **A clean or alarming
result is a claim about the instrument first.**

| what it read | what was true |
|---|---|
| "196 of 196 tables wired" | counted each table's own build script as a feature; truth 139 |
| "79 tables not locatable" | exact-name column matching missed `faclong`, `latitude_raw`, `lstreet1`; truth 49 |
| "362 columns missing from WARN" | case-sensitive comparison — `CASE_TYPE` vs `case_type` counted twice |
| "RTEP join yields 6%" | measured 932 Indiana rows against 15,443 PJM-wide; truth 100% |
| "OSM substations: 1 of 2,873" | filtered on `latitude`; 2,872 are polygons with no point |
| "D25 runs 2007–2019, historic" | MIN/MAX on a STRING date is lexicographic; truth 2002 → 2026-01-05 |
| "10 of 19 signals have no endpoint" | Lane D matched by name-token overlap (W17 forbids it); truth 96 of 126 carry one |
| "brownfields cannot be plotted" | they carry Latitude/Longitude; what is missing is the POLYGON |
| "SI is 47.8% dated" | inflated by 945,896 undated non-signal rows; truth 99.7% |

## Every document, and what it is for

**Read in this order.** 1–3 orient you; 4–9 are the measured evidence behind the current state;
10–12 are acquisition; the rest is the older record.

| # | document | what it holds |
|---|---|---|
| 1 | `docs/HANDOFF.md` | this file — the RECORD of what happened and why |
| 2 | `docs/GAMEPLAN.md` | the PLAN: all phases + the 26-item backlog in priority order |
| 3 | `docs/CODE_CATALOG.md` | **GENERATED** — every script, every endpoint with its type, and the literal command that re-runs it. Regenerate with `scripts/build_code_catalog.py`; never hand-edit |
| 4 | `docs/GAP_REGISTER.md` | every known gap, classified: what is genuinely unwired vs waived vs reached via a derivative |
| 5 | `docs/PLOTTABILITY.md` | every table graded A–E for whether it can be drawn, with series tables excluded by ruling |
| 6 | `docs/SIGNAL_ENDPOINTS.md` | endpoints + loaders read mechanically from the registry, and the audit of our own thin rows |
| 7 | `docs/SIGNOFF_PACKET.md` | the 8 operator judgments, all APPROVED and wired |
| 8 | `docs/AUDIT_WORKLIST.md` | per-table verdicts from the estate audit — the audit is COMPLETE, never re-run it |
| 9 | `docs/CLOUDSCENE_GAP.md` | the DC completeness cross-check, per facility |
| 10 | `docs/FOIA_IRS_ALS_REQUEST.md` | ready-to-send D13 request, verified routes, what arrives |
| 11 | `scrapers/lane_f/D10_D13_TAX_LIEN_FINDINGS.md` | tax-lien routes: D13 viable free, D10 a $600/yr decision |
| 12 | `scrapers/lane_f/MISSING_SIGNALS_FINDINGS.md` | the other 6 missing signals, ranked D22→D9→D4→A1→D23→D15 |
| 13 | `scrapers/lane_f/ABANDONED_PROPERTY_FINDINGS.md` | **agent may still be writing this** |
| 14 | `docs/SI_DATE_KEYING.md` | **agent may still be writing this** |
| 15 | `scrapers/lane_[a-e]/LANE_*_FINDINGS.md` | per-lane acquisition results and walls |
| 16 | `docs/BQ_INDIANA_CENSUS.md`, `docs/AUDIT_CLASSES_REPORT.md`, `docs/DATA.md`, `docs/ARCHITECTURE.md` | the earlier estate work |
| 17 | `docs/SAMPLES_INDIANA.md`, `docs/SAMPLES_ALL_PART2.md` | 1–3 raw rows per estate table — **grep per table, never load whole (2.3 MB)** |

Platform docs (another session owns them, read-only): `energy-platform/CLAUDE.md`,
`REBUILD_PLANNING/METHODS.md`, `2_TECHNICAL_BUILD_SPEC.md` §11 + §13, `ANALYSIS_METHODOLOGY.md`
(required before computing any siting/rate NUMBER), `FABLE5_PREAMBLE.md` (paste above any ad-hoc
scrape request — both Lane F agents used it).

## Where to resume

`docs/GAMEPLAN.md` Phase B. The immediate queue is in its backlog table. First actions:
check the three background outputs above, fix the D22 rate limit, then B5 (verify or retire the
`vw_county_dc_posture` 92/92 counter) and B1 (the DLGF Gateway owner-data pull, which unblocks
B1 + D9 + D18 in one acquisition).

---

# (historical record below — the pre-checkpoint handoff)


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
1. `docs/HANDOFF.md` — this file (the RECORD: what has been done, and must not be redone)
2. **`docs/GAMEPLAN.md` — the PLAN: every phase from here to completion, in working order.**
   Phase A (wire the 57 orphan tables) is the operator's stated priority and precedes front-end
   work. Add newly-noticed work to the right phase there rather than starting it immediately.
3. `docs/PLAN.md` — the earlier phase plan (wire → pages → functionality); GAMEPLAN supersedes
   its ordering and carries the measured state
4. `docs/AUDIT_WORKLIST.md` — every table's verdict, batch by batch, flags included
5. `docs/BQ_INDIANA_CENSUS.md` — the estate classification + verified per-table IN counts
6. `docs/AUDIT_CLASSES_REPORT.md` — zeros/spatial/national resolutions
7. `docs/DATA.md`, `docs/ARCHITECTURE.md`, `docs/SCRAPE_LANES.md`, `docs/DATA_BACKLOG.md`
8. `docs/SAMPLES_INDIANA.md` + `docs/SAMPLES_ALL_PART2.md` — 1-3 raw rows of every estate
   table (grep per table; never load whole — 2.3 MB combined)
9. `docs/CLOUDSCENE_GAP.md` — the DC completeness cross-check, per facility
10. `scrapers/lane_[a-e]/LANE_*_FINDINGS.md` — per-lane results, walls, next endpoints

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


- **CLOUDSCENE GAP INVESTIGATED 2026-08-15 — and it exposed a far worse defect in our own map.**
  Chasing the 25 unmatched colo facilities turned up something bigger than the gap itself.
  **⚠ 92 of our (then) 242 data-centre pins were census-gazetteer CITY CENTROIDS rendered as
  facility locations.** `data_centers_datacentermap_coords` carries `method` and `precision`
  columns nobody had read. In the Indiana bbox: **119 of 149 rows are
  `method='census_gazetteer', precision='city'`, collapsed onto 11 distinct points; only 3 are
  `precision='site'`.** The visible consequence: **32 facilities stacked on ONE point** near New
  Carlisle — including Microsoft Mishawaka, drawn ~15 km from where it is. This broke two
  standing rules at once (*city-precision coordinates never in distance math*; *estimated
  locations never style as published ones*) and a census city point is a centroid, which the
  project bans outright. Fixed by `scripts/fix_dc_location_precision.py` →
  `in_data_centers_located`: every pin carries `location_precision` (site/city/unknown),
  `precision_method` and `pins_at_this_point`. The map now draws the tiers apart — solid blue
  for a published site coordinate, **hollow amber sized by stack depth** for a city centroid —
  and the panel says plainly that it is not the facility's location. **Nothing city-precision
  may enter distance math.** The DCM tail is national, not Indiana-only: 4,370 rows sit in
  coordinate stacks of 5+, worst 251 — **flag this for the national app.**
  **peeringdb was never merged.** The DC union was OSM + Baxtel + Wikidata + DCM-via-coords;
  peeringdb had been clipped as a separate "connectivity layer", so 19 Indiana facilities with
  real SITE-precision coordinates never reached the map while 92 city centroids did. Merged
  (150 m / name-stem dedupe), adding **7**: SITCO Evansville, IUPUI ICT Complex, Wintek, INdigital,
  Ligonier CO, Lagrange CO, Aunalytics South Bend. Layer is now **249 pins, 157 site-precision**.
  **The gap itself is small and mostly illusory.** Of 260 cloudscene Indiana rows, 229 are
  carrier central offices (223 Frontier) — telecom plant, never data centres. Of the 31 real
  colo facilities, ~20 were already on the map, ~4 were recoverable from peeringdb/baxtel, and
  **7 remain unaccounted for, all in Indianapolis**. Cloudscene publishes no address, and
  Indianapolis colo is concentrated in the Indy Telcom carrier-hotel campus (701/733 W Henry —
  peeringdb reports 21 and 41 network presences there), so the likeliest reading is that these
  are **provider presences inside buildings we already hold**, not missing buildings. Resolving
  them properly needs an address source; cloudscene's own pages were NOT scraped (permission
  unchecked — ask before acquiring). `docs/CLOUDSCENE_GAP.md` has the per-facility table.
  **Matcher caveat, stated because it matters:** the name matcher is triage, not proof. It was
  wrong three ways before settling (missed `GAP` = Global Access Point until acronyms were
  added; let a useless "indianapolis" overlap outrank a real one until place tokens were
  stripped from scoring; and it still puts IUPUI at the Bloomington coordinate). Treat its
  counts as approximately right, not exact.
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
