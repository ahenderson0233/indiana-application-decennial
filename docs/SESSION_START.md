# SESSION START — paste this as your first message

Continue the Indiana siting-intelligence application.
Repo: `C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial`
(GitHub `ahenderson0233/indiana-application-decennial`, branch `main`)

---

## FIRST: run the checkpoint. Do not read anything before you have.

```bash
python scripts/checkpoint.py
```

It runs every audit, re-measures the warehouse, regenerates the state block in
`docs/BACKLOG.md`, and **exits non-zero if anything drifted**. Tell me what it printed.

**If it fails, fix it before anything else.** A failing checkpoint means the documents and the
warehouse disagree, and every number you are about to read is suspect.

Then read, in this order — and no further than this, because it is enough:

| # | file | what it is |
|---|---|---|
| 1 | `docs/BACKLOG.md` | the ledger. The block at the top is **generated**; everything below is the plan, the operator rulings, and the rules earned by getting things wrong |
| 2 | `docs/TABLE_INVENTORY.md` | **generated.** All ~269 objects and, per object, whether it carries OWNER data, a real DATE, a STATUS vocabulary, coordinates or a parcel key |
| 2b | **`docs/FEATURE_INVENTORY.md`** | ⭐ **EVERY feature, what it does, how it works, and which BigQuery table it comes from.** The fastest way to get oriented |
| 3 | **`docs/HANDOFF_2026-08-18b.md`** | ⭐ **THE CURRENT ONE.** Tariffs, the dossier audit, the bus rebuild, and ⚠ **the PJM ladder harvest that may still be running** — with its resume command |
| 3b | `docs/HANDOFF_2026-08-17.md` | **the front-end revamp session.** ⚠ Lists the AGENTS that were still running, and every file/reference the operator supplied |
| 4 | `docs/SIGNAL_REALITY.json` | **generated.** Every SI signal classed as done / not-split / wrong-grain / blocked / awaiting-operator, so you stop re-recommending finished or impossible work |

`docs/PATH_TO_COMPLETE.md`, `docs/HANDOFF.md` and `docs/GAMEPLAN.md` are HISTORY. They contain
figures that were true when written and are not now. Read them for *how* something was done, never
for *what is true today*.

---

## ⭐ THE GOVERNING PRINCIPLE — everything on screen must answer "so what?"

Operator, 2026-08-17: *"The entire point of this application is really answering the 'so what'
question, so everything should be insightful and/or actionable that we display anywhere to the
user."*

The warehouse already **holds** Indiana's siting data. The application's job is to tell a
data-centre or BESS developer **what to do next, and why**. A figure that is correct, sourced,
freshly built and beautifully rendered still **fails** if the reader cannot say what it changes
about their decision.

Treat it as a **veto on new work**, not a polish step: nothing goes onto a page — map layer, table,
chart, screener column, dossier row — without its "so what" written at the same time, in the
reader's units, ordered so the good and bad ends are obvious. If a surface cannot earn one, it is
not a surface we build. See the governing-principle block and the G21 inventory in
`docs/BACKLOG.md`.

## ⛔ THE RULES, and the failure that earned each one

**Write boundary.** `energy-platfrom.energy` is READ-ONLY — another session owns it. The one
permitted write is APPEND-only rows to `energy.registry_sources`. Everything we build goes to
`energy-platfrom.indiana_app`, and **every table gets a `_registry` row in the same run that
writes it.** **Restate this in every agent brief — agents do not inherit it.**

**Newly scraped data updates BOTH registries, in the same run that writes it** (operator,
2026-08-17): a `_registry` row in `indiana_app` **and** an APPEND to `energy.registry_sources` with
the source name, endpoint, endpoint kind, access, status, re-scrape command, what it provides, the
object names and the measured row count. The append is the one permitted write to `energy`.

**A registry row must be enough to RE-RUN the work** (operator, 2026-08-17). A row that merely
exists is not compliant: it must carry the **exact parameterised URL** (not the site's home page),
the **endpoint type** (`arcgis_feature_layer` / `json_api` / `html_page` / `xlsx_download` /
`bq_clip`), the **loader command verbatim** (`RE-SCRAPE COMMAND: …`), the **parameters that define
the slice**, the **publisher's own vintage** rather than your pull timestamp, and **what was
excluded and why**. Test: *could a stranger refresh this table from the registry row alone?*
`in_grid_plans` fails this today — its registry row says 7 rows while the table holds 618.

**⛔ CHECK THE WAREHOUSE BEFORE YOU EXPLORE OR SCRAPE ANYTHING.** Operator rule, 2026-08-17,
binding for the project's duration: before proposing an acquisition, a loader, a paid trial or an
agent, enumerate `energy.__TABLES__` and `indiana_app._registry` for the subject. It costs one
query. On 2026-08-17 a CartoVista loader was recommended as the top grid priority while the estate
**already held** `cartovista_miso_poi_locations`, `miso_poi_capacity_surface_geotiff` (3.4M pixels),
`miso_poi_monitored_facilities` and `miso_poi_headroom`. The same session queued F1/F2 as open work
that had already been done. The failure is always the same shape: **a plan built on what you
remember instead of on what you hold.**

**Never quote a count from a document, including this one.** Run the checkpoint and use what it
prints. "199 of 199 wired" was stale within the hour; `SI_COVERAGE.md` asserted D4 was NOT HELD
while 17,617 delinquent rows sat in the warehouse.

**A clean, perfect or alarming number is a claim about your INSTRUMENT first.** Check the join,
then the filter, then the data. A cross-check reported five "missing" data centres that were all
already pinned under a predecessor operator name.

**Read the schema. Read the value vocabulary. Never guess a column name.** This cost four separate
zero-result queries in one session — `ADDRESS_ID` for `FULL_ADDRESS`, `geog` for `lat`/`lon`, and
two different name joins that could never match. And 40% of Indy's code corpus is High Weeds &
Grass; admitting it whole would have inflated D12 by ~750,000 rows of lawn care.

**A status column is where a hidden signal lives.** `saleStatusDescription` hid D4 inside D1 for a
whole session; `CASE_TYPE` hid unsafe-building inside D12. `TABLE_INVENTORY.md` flags all 137
objects that carry one.

**Dates lie in specific ways.** Epoch milliseconds in a string is the Esri convention and appears
on at least eight columns here — an ISO parse returns NULL on every row. `MM/DD/YYYY` is not ISO.
`00/00/0000` is a null sentinel; use `SAFE.PARSE_DATE`.

**Unpublished is NULL, never 0.** Treating absent rates as zero produced 95 false "below floor"
violations. **Assert the window you GOT, not the one you asked for** — a 12-month LMP filter
returned 39 days.

**Scrape only what a source PERMITS.** No CAPTCHA bypass, no UA spoofing, no account creation.
**A gated source recorded BLOCKED with its wall quoted verbatim is a SUCCESS.** But a wall is an
observation, not a property of a host: four robots-403 walls did not reproduce on re-test.

**Absence of evidence is not evidence of absence.** NOT_SEARCHED, NOT_REACHABLE and BLOCKED must
never render as permissive. Check a control word before recording any county as silent.

**⚠ EXCLUDE `parcels_in/080500000047000018` from EVERY spatial join** — D85, an inverted
whole-Earth polygon, live and unrepaired upstream. Prove the guard by measuring fan-out (~1.0, not
~2.0). The checkpoint checks five tables for it; add yours.

**Indiana only, clipped at the border. Cannot-assess renders as itself. Estimates never style as
published. No centroid in distance math.** `orennia_*`, `be_ustest_*`, `*_vs_orennia`,
`hifld_bus_features_v3` never render and never export.

**Never `git add -A`.** Stage explicit paths — staging directories swept a scratch `.bak` into a
commit. **Use a commit-message FILE**; backticks and quotes in `-m` get eaten by the shell.

**After ANY build touching `in_si_sites_flags_v2`: re-export sites, THEN run the checkpoint.** The
audit failed once for exactly this — the map shipped 11,117 while the warehouse held 23,140.

**ASCII in console output.** cp1252 cannot encode `≈ → ✗ ↔ ⚠`; three scripts died on their own
`print()`, including the honesty audit crashing on its FAILURE path.

**Cost-flag anything above $25–50 before running it.** ⛔ NEVER run `ingest/build_hc_auto_adapters.py`.
The project-name misspelling **`energy-platfrom` is INTENTIONAL and permanent.**

---

## ⚠ HOW TO TREAT THE PREVIOUS SESSION'S CLAIMS — verify, do not inherit

The documents are generated and audited. **The reasoning in them is not.** In the 2026-08-16/17
session the author's own errors included:

- **Four assertions that we did not hold data we held** — D4 "NOT HELD" (17,617 rows), owner data
  "absent" (346,919 Marion parcels carry it), D12 "228 in one county" (that is *admitted*; 10,370
  were *reached*), and a bug filed against `si.html` from a console polluted by the author's own
  probes.
- **A front-end audit that opened with 56 findings and roughly zero real ones**, reporting the
  entire scoring UI as dead because it could not see ids built from template literals.
- **A "fix" shipped on a wrong diagnosis** — the map's boot was blamed on two CDNs; a test then
  showed an empty style with no external URLs also fails, so it was the browser. Reverted.
- **Four separate zero-result queries from guessed column names**, twice repeating a defect the
  same author had fixed an hour earlier.

**Every one was caught by a check or by the operator, none by the author on first pass.**
Re-measure anything load-bearing before building on it.

---

## WHAT IS ACTUALLY LEFT

Run the checkpoint first; then `docs/BACKLOG.md`. As of the last close:

- **Blocked on a clock:** Howard and City of Elkhart council votes (**2026-08-17**), Marion MDC
  final action on Proposal No. 238 (**2026-08-19**).
- **Blocked on you:** the American Legal licence (`license@iccsafe.org`, unlocks 17 counties), the
  robots-vs-terms standing policy, a WSL/Docker install (**C5 PMTiles is fully scripted the moment
  it exists**), D10 procurement, the IRS FOIA fax, an IEDC email.
- **Cannot close as specified, not defects:** §13(5) needs an AI docket summary and this app has no
  LLM feature. ✅ **§13(8) IS NOW CLOSED and this line was wrong from 2026-08-18** — a
  component-level Indiana tariff DOES exist in the estate: `in_utility_tariff_riders`, **668
  components across 73 utilities**, 22 of them costed from their own books at every service voltage
  with every applicable rider, plus a labelled URDB floor for 50 more. The Market page prices them
  and the dossier quotes the parcel's own utility.
- **Deferred by the operator:** the front-end pass.

---

## START BY

Telling me what the checkpoint printed, what you read, and your plan for the first open item in
`docs/BACKLOG.md`. If the checkpoint failed, tell me that instead and fix it first.
