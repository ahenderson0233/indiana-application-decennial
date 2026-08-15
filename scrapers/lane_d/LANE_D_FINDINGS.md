# Lane D findings — Indiana SI-refresh (freshness re-pull) (2026-08-15)

Scope: FRESHNESS REFRESH of six already-mapped Indiana seller-intent sources (not new-source
discovery — that is Lane C). Rules honored: >=1 req/s/host; UA
`DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)`; robots.txt checked before any
HTML-site pull; outFields=* / all-columns on every source, paged to exhaustion and verified
against the publisher's own count; observed EVENT dates captured from the data, `_pulled_at`
stored separately; all writes to `energy-platfrom.indiana_app` only (`energy` never touched);
every table registered in `indiana_app._registry` in the same run as its load.

## Session resumed from

`06_sri_taxsale_in_refresh.py` had already completed (83,547 rows, registered) before this
session started. Scripts `03/04/05/07` had **also** already completed and registered —
confirmed directly against BigQuery (table existence + row counts + `_registry` rows), not
from the `_scratch/*.json` snapshots, which were present but not trusted as source of truth.
Only `02_indy_code_enforcement_refresh.py` had never successfully run: no table, no registry
row, no leftover `_stage_*.ndjson`. That script failed on **this** session's first attempt too —
see bugfix note below — then completed clean on retry.

| # | script | table | status at session start | outcome |
|---|---|---|---|---|
| 02 | indy_code_enforcement | `in_si_refresh_indy_code_enforcement` | never run | **ran this session** — 910,483 rows |
| 03 | ibtr_appeals | `in_si_refresh_ibtr_appeals` | done (prior) | confirmed, not re-run |
| 04 | warn_notices | `in_si_refresh_warn_notices` | done (prior) | confirmed, not re-run |
| 05 | iocs_eviction | `in_si_refresh_iocs_eviction` | done (prior) | confirmed, not re-run |
| 06 | sri_taxsale_in | `in_si_refresh_sri_taxsale_in` | done (prior, per task) | confirmed, not re-run |
| 07 | brownfield_epa_in | `in_si_refresh_brownfield_epa_in` | done (prior) | confirmed, not re-run |
| 08 | freshness_diff | `_scratch/08_freshness_diff.json` | ran once already (5 sources; script never covered D12) | re-run clean (read-only, no drift vs prior run) |

**6 tables, 1,013,404 rows total, all in `indiana_app`, all registered, all verified
table-count == publisher-count / full-corpus paging with no pagination alarms.**

## Bugfix made this session (`lane_d_util.py`)

`02_indy_code_enforcement_refresh.py` failed on first attempt at `resultOffset=303000` of
~910 (maxRecordCount=1000/page): `ArcGIS error ... {'code': 503, 'message': 'Error handling
service request :Wait timeout for the request exceeded.'}`. This is a transient server-load
error, not a wall — same endpoint, same params, no gating. Nothing had been written to BigQuery
yet (the failure was mid-pull, before `load_to_bq` runs), so the retry was safe. Added a bounded
retry (max 5 attempts, exponential backoff 4/8/16/32s) to `arcgis_pull_all()` in `lane_d_util.py`,
scoped only to codes 503/500/429 or a "timeout" message — any other ArcGIS error still raises
immediately, unchanged. Re-run completed clean with zero retries needed, publisher count matched
exactly (910,483 == 910,483, no PAGINATION ALARM).

## Per-source held vs. refreshed vs. remediated

| source_id (held in `si_signals`) | held rows (IN) | held observed range | refreshed rows | status column sampled | remediated | still-open/active |
|---|---|---|---|---|---|---|
| `si_d1_sri_taxsale_listings` | 80,056 | 2000-03-27 .. 2026-10-20 | 83,547 | `saleStatusDescription` | 65,930 (78.9%) — Sold To Plaintiff / Cancelled / Sold To 3rd Party / COUNTY | 17,617 (21.1%) — DELINQUENT / Sale Active |
| `si_d12_indy_marion_code_enforcement` | 747,211 | 2010-03-29 .. 2024-02-27 | 910,483 | `CASE_STATUS` (91 distinct values) | 807,530 (88.7%) strict paid/closed/resolved-shaped **+** 60,785 (6.7%) publisher-specific resolved-in-spirit (Corrected/Abated/Complied/Cleaned/Void) = 868,315 (95.4%) combined | 21,931 (2.4%) explicitly open/overdue/pending/in-violation; 12,094 (1.3%) NULL; ~8,143 (0.9%) procedural/ambiguous (Collections, Legal Review, Hearing, Citation Issued, etc.) |
| `appeals_in_ibtr_determinations` | 6,953 | 2004-01-07 .. 2026-08-05 | 10,152 | `statusName` | 10,118 (99.7%) Closed + 34 (0.3%) Closed-appeal-pending | n/a — this endpoint publishes decisions, so it's ~all "closed" by construction |
| `warn_notices` | 1,039 | 1994-05-12 .. 2026-07-21 | 1,220 | `Notice_Type` + `LO_CL_Date` | 591 (48.4%) closure-shaped Notice Type; independently 942 (77.2%) have an LO/CL Date already in the past vs today | 416 (34.1%) plain layoff (LO) type; 8 rows still future-dated |
| `si_d17_in_iocs_court_year` | 370 | 2022-01-01 .. 2025-01-01 | 6,519 (all 19 sheets) | `EV` column per report sheet | Disposed (EV) sum 138,088 across 382 courts | Cases Pending 1/1/2025 (EV) 59,126; Cases Pending 12/31/25 (EV) 61,464 |
| `brownfield_epa_repowering` | 1,378 | n/a (STATE-class, no event date) | 1,483 (+105) | n/a — site characteristics, not case status | n/a | n/a |

Detail notes:
- **SRI / IBTR / WARN / IOCS / brownfield** numbers above are unchanged from the prior run of
  `08_freshness_diff.py` — re-ran it this session (read-only against BQ) and it reproduced
  identically, confirming no drift since those five tables were built.
- **SRI**: no stable id survives from `si_signals` (keyed on free-text `address_norm`) into the
  refreshed table (`propertyId`/`altPropertyId`), so this is a corpus-level comparison, not a
  row-level join — matches the standing rule against guessing an address-normalization function.
- **Code enforcement (D12) — the interrupted source — has a real staleness finding, not just a
  refresh**: the fresh full re-pull's `OPEN_DATE` spans **exactly** 2010-03-29 .. 2024-02-27,
  identical to the held `si_signals` max, and the row count (910,483) is an **exact** match to
  the separately-held `agis_indy_code_enforcement`/`si_d12` duplicate acquisition's 910,483. Zero
  net drift, zero rows with an `OPEN_DATE` past 2024-02-27. As of this pull (2026-08-15), the
  publisher's live `OpenData_NonSpatial/1` layer has not had a single new case opened in over
  2.5 years — either the case-management feed behind this specific export is frozen, or new
  cases are being routed elsewhere. This is the freshness answer for this source: **not stale
  data on our side, a stale layer on the publisher's side.** No status-change-date field exists
  on the layer (only `OPEN_DATE`), so a status's own transition date can't be recovered.
- **IBTR**: 3,199 determinations are new since the held snapshot (10,152 vs 6,953) — the real
  payoff here, since the closed/open split is meaningless for a decisions-only feed.
- **WARN**: the closure-vs-layoff *label* (48.4% closure-shaped) and the *calendar fact* that
  the layoff/closure date has already passed (77.2%) are reported separately because they answer
  different questions — a "LO" (layoff-only) notice whose date has passed is still a completed
  event even though its own Notice_Type never says "closure."

## New-signal candidate columns (report-only — not wired, not loaded anywhere new)

| table | column | top values / coverage |
|---|---|---|
| `in_si_refresh_sri_taxsale_in` | `saleTypeDescription` | Foreclosure 62,760; Tax Sale 15,860; Certificate Sale 4,851; Deed Sale 76 — subtype finer than the open/resolved split |
| `in_si_refresh_sri_taxsale_in` | `latitude`/`longitude` | 29,955 / 83,547 (35.9%) populated — partial direct-plot upgrade over address-only geocoding |
| `in_si_refresh_ibtr_appeals` | `attachmentDescriptions` | "Final Determination - Findings and Conclusions" 8,574; "Notice of Settlement" 18; multi-value strings also carry "Notice of Withdrawal of Petition" — a document-type breadcrumb finer-grained than `statusName` |
| `in_si_refresh_ibtr_appeals` | `appealTypeName` | Form 131: 7,282; Form 133: 1,871; Form 132: 977; Form 139: 22 — petition-type code, never surfaced before |
| `in_si_refresh_warn_notices` | `NAICS` | 6-digit industry code populated on all but the 204 N/A rows; top codes 311812, 326199, 452112, 622110, 493110... — lets a consumer filter WARN notices by industry |
| `in_si_refresh_warn_notices` | `col_8__href` | 172/1,220 (14.1%) populated direct links to the WARN letter PDF (e.g. `/dA/.../<Company>-WARN-Notice...pdf`) |
| `in_si_refresh_iocs_eviction` | `MF` (mortgage-foreclosure case-type code) | New Filings 21,170; Disposed 20,374; Pending 1/1/2025 19,262; Pending 12/31/25 20,284 — same statewide-by-court shape as the held `EV` (eviction) signal, across all 382 courts, **never previously wired**; a genuine second D2-adjacent signal sitting in the same workbook |
| `in_si_refresh_brownfield_epa_in` | `Program` | BROWNFIELDS 1,247; RCRA 127; LANDFILL METHANE OUTREACH PROGRAM 54; SUPERFUND 53; AML 2 |
| `in_si_refresh_brownfield_epa_in` | `Landfill` / `AML` flags | Landfill='Y': 83 of 1,483; AML='Y': 4 of 1,483 (blank otherwise) — small but a clean binary filter |
| `in_si_refresh_indy_code_enforcement` | `CASE_TYPE` | "Enforcement/Investigation/High Weeds & Grass/NA" 211,794; ".../Violation/High Weeds & Grass/NA" 152,050; ".../Investigation/Zoning/NA" 145,521; ".../Investigation/Trash/NA" 78,437; ".../Violation/Building/NA" 45,787 (+ Unsafe Buildings, Vacant Board Order, Illegal Dumping, Environmental, Infrastructure...) — a full violation-subject taxonomy, not just "code enforcement" as one bucket |
| `in_si_refresh_indy_code_enforcement` | `LINK` | 910,483/910,483 (100%) populated — direct Accela case-detail URL (`permitsandcases.indy.gov/citizenaccess/Cap/CapDetail.aspx...`) for every row, a free drilldown/verification link |
| `in_si_refresh_indy_code_enforcement` | `TOWNSHIP` | CENTER 416,507; WAYNE 129,676; WARREN 86,640; WASHINGTON 78,955; PERRY 56,174; LAWRENCE 38,314; PIKE 31,439; FRANKLIN 24,769; DECATUR 18,989 — free sub-county geography on every row (data-quality note: a small number of rows carry a doubled value like `'CENTER,CENTER'`, a publisher formatting artifact, not a real second township) |

## BLOCKED walls

1. **`si_d25_stb_abandonment_state` (215 IN rows held, STB rail-abandonment-analog signal)** —
   endpoint `https://inbiz.in.gov/Inbiz/BulkDataServices/Index`, registry status recorded
   **fee-gated: $9,500 + $500/mo (rejected)**. Standing decision from before this session;
   not re-probed (no new terms to accept, nothing has changed). The only currently-held
   Indiana-feeding source in the target-list cross-reference whose wall is a paywall rather
   than a missing endpoint.
2. **No new walls inside the 6 scripts actually run this lane (02–07).** All six targeted
   endpoints were pre-vetted live and ungated before this session — two ArcGIS
   Map/FeatureServer layers, one POST-only DevExtreme JSON API, one public HTML table
   (robots.txt allowed), one direct XLSX download, and one public JSON API with an anonymous
   key already shipped to every visitor's browser. None required an account, CAPTCHA, ToS
   click-through, or paywall.
3. **Not a wall, but adjacent**: the IOCS 2026 workbook
   (`rpts-ijs-2026-pending-incoming-disposed-miscellaneous.xlsx`) 404s — the publisher simply
   hasn't posted a 2026 file yet under that naming pattern; the 2025 file remains current and
   was re-pulled anyway in case it had been revised in place (it had not — row/column shape
   unchanged from the prior pull).

## Scope note (not a wall — a coverage gap worth flagging)

The `01_target_list.py` cross-reference left **10 of 19** Indiana-feeding `si_signals`
source_ids with no matched live registry endpoint at all (`match_token_overlap = 0` or no
endpoint), including the single **largest** Indiana signal by row count,
`si_d5_vacancy_derived` (945,896 rows) — a derived signal with no endpoint of its own to
re-pull. These were correctly out of scope for this lane's 6 built-and-registered scripts
(which only targeted sources with a known, live, ungated endpoint) but are flagged here as
candidates for a future lane if a source endpoint can be identified for them.
