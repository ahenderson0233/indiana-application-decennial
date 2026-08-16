# NEXT SESSION — paste this as your first message

Continue the Indiana siting-intelligence application. Repo:
`C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial`
(GitHub: `ahenderson0233/indiana-application-decennial`, branch `main`)

---

## STEP 0 — read these IN THIS ORDER, then tell me what you read

| # | document | why, and how to read it |
|---|---|---|
| **1** | **`docs/PATH_TO_COMPLETE.md`** | **START HERE.** Every remaining task, why it is not done, what closes it. Read §0 (three commands to run first) and §2 (the finish line) in full |
| 2 | `docs/HANDOFF.md` | the RECORD. Read the **top checkpoint block in full** — it holds the session's lessons, the gaps, and the agents that were in flight |
| 3 | `docs/GAMEPLAN.md` | the PLAN. Read the state table at the top and the backlog; items 27–34 are the newest |
| 4 | `docs/CODE_CATALOG.md` | **GENERATED.** Every script, endpoint and the literal command that re-runs it. Never hand-edit — regenerate with `scripts/build_code_catalog.py` |
| 5 | `docs/SI_COVERAGE.md` | **GENERATED.** Per-signal coverage as FOUR separate numbers (held / reached / admitted / dated). Conflating them is how the D5 error happened |
| 6 | `docs/NATIONAL_HANDOVER.md` | **GENERATED.** The twelve errors this build made and the transferable rule each teaches. Read the error table even if you skip the rest |
| 7 | `docs/ACCEPTANCE_RUN.json` · `docs/HONESTY_AUDIT.json` | **GENERATED.** Current §13 acceptance state and the 12 honesty checks |
| 8 | `docs/GAP_REGISTER.md` · `docs/PLOTTABILITY.md` · `docs/SIGNAL_ENDPOINTS.md` | the measured evidence behind current state |
| 9 | `scrapers/lane_*/…FINDINGS.md` | acquisition results and **every wall quoted verbatim**. `ORDINANCE_FINDINGS.md`, `ORDINANCE_AMLEGAL_FINDINGS.md`, `COLO_ADDRESS_FINDINGS.md` are the newest |

Platform docs (another session owns them — READ ONLY): `energy-platform/CLAUDE.md`,
`REBUILD_PLANNING/METHODS.md`, `2_TECHNICAL_BUILD_SPEC.md` §11 + §13,
**`ANALYSIS_METHODOLOGY.md` — required before computing ANY siting or rate number**,
`FABLE5_PREAMBLE.md` (paste above any ad-hoc scrape brief).

Then run, and tell me what they print:
```bash
python scripts/audit_honesty.py && python scripts/audit_wiring_census.py && git log --oneline -25
```

---

## ⛔ THE WRITE BOUNDARY — the rule most at risk from agents

**`energy-platfrom.energy` is READ-ONLY.** It is the shared warehouse another session owns.

- **Never** create, drop, truncate or overwrite a table in `energy`.
- The **ONE** permitted write is **APPEND-only rows to `energy.registry_sources`**, tagged with a
  distinctive `updated_by`.
- **Everything we build goes to `energy-platfrom.indiana_app`.** Everything we write to disk goes
  to this repo. Nothing else.
- **Every table gets a `_registry` row IN THE SAME RUN that writes it.** An unregistered table
  blocks the other session's checkpoint invariant 3.

**Verified 2026-08-16: this project is compliant.** `indiana_app` holds 253 objects; **zero new
tables were created in `energy` by this project**, and our only `energy` writes are 86 append-only
`registry_sources` rows (`indiana-app-session-*`, `indiana-app-ordinances-agent`,
`lane_d8_d22`, `lane_f_b4_colo_resolution`). Re-verify with
`scratchpad/bq_compliance.py`-style checks if an agent run makes you unsure.

**When briefing ANY agent, restate this boundary in the brief itself.** Agents do not inherit it.
Today's agents complied because every brief carried it explicitly.

*Note: `energy.amlegal_dc_ordinances` (2,494 rows, created 2026-07-06) is a PRE-EXISTING
platform-side table, not ours — but it may be directly useful for the ordinance work. Read it,
never write it.*

---

## THE OTHER NON-NEGOTIABLE RULES — each earned by getting it wrong

- **A clean, perfect or alarming number is a claim about your INSTRUMENT first.** Check the join,
  then the filter, then the data. Nine of this session's findings came from doing exactly this.
- **NEVER guess a column name — read the schema first.** The most repeated failure in this project.
- **Unpublished is NULL, never 0.** And check your own code against the rule you just quoted — the
  rate engine flagged 95 "violations" that were absent rates treated as zero.
- **Assert the window you GOT, not the one you asked for.** A 12-month LMP filter returned 39 days.
- **Read the value vocabulary before trusting a count.** 95% of one "code enforcement" source is
  litter and weeds.
- **Never read a category off a mutually-exclusive ladder.** "0 high-priority violators" when 95
  exist.
- **A dead end in the tables you HOLD is not a dead end in the publisher's catalogue.**
- **Scrape only what a source PERMITS.** No CAPTCHA bypass, no UA/TLS spoofing, no account
  creation, no paywall circumvention. **A gated source recorded BLOCKED with its wall quoted
  verbatim is a SUCCESSFUL outcome.**
- **Indiana only, clipped at the border.** Cannot-assess renders as itself, never as 0 or blank.
  Estimates never style as published. **No centroid in distance math.**
- ⚠ **EXCLUDE `parcels_in/080500000047000018` from EVERY spatial join** — D85, an inverted
  whole-Earth polygon (196,936,707 sq mi) that silently matches everything. Live and unrepaired
  upstream. Prove your guard by measuring fan-out (~1.0, not ~2.0).
- **Public-data-only:** `orennia_*`, `be_ustest_*`, `*_vs_orennia`, `hifld_bus_features_v3` never
  render and never export.
- **Never `git add -A`.** Stage explicit paths, every time.
- **After ANY build touching `in_si_sites_flags_v2`: re-export sites, THEN re-run the honesty
  audit.** This failed once — the map shipped 11,117 while the warehouse held 23,140.
- Reserved words that have bitten: `rows`, `no`, `FULL`, `ROWS`. A doubled `''` in a BigQuery
  literal parses as two adjacent strings; **adjacent string literals in JS are a SyntaxError that
  once took the whole map down.**
- Python's `SimpleHTTP` sends no `Cache-Control`: `await fetch(f, {cache:"reload"})` then navigate.
- **Cost-flag anything above $25–50 before running it.** ⛔ NEVER run `ingest/build_hc_auto_adapters.py`.
- The project name misspelling **`energy-platfrom` is INTENTIONAL and permanent**.

---

## WHERE WE ARE, BY PHASE

| phase | state |
|---|---|
| **A — wire every object to a surface** | ✅ complete. The census is a SCRIPT; the denominator moved 226→242→252 in one day |
| **B — data-integrity debts** | ✅ complete. B2 flag, B3 acreage, B4 colo, B5 retired, D22, D85 guard, WARN dedupe, Lane D columns |
| **C — functionality** | C1 dossier ✅ · C2 rate engine ✅ · C3 RTEP→bus ✅ · **C4 workspaces NOT built** (front-end) · **C5 PMTiles BLOCKED** on a WSL/Docker install |
| **D — acquisition** | D22 ✅ · Marion + Indy crosswalks ✅ · Evansville Land Bank ✅ · **DLGF owner pull is the top remaining item** |
| **E — hardening** | E1 audit ✅ (12/12) · E2 cadence ✅ · E3 handover ✅ · E4 acceptance ✅ run: **4 PASS, 3 PARTIAL, 0 FAIL, 2 N/A** |

**Headline numbers — re-measure, do not quote:** SI flag **23,140** parcels (7,183 fit ≥5 MW BESS,
3,015 fit ≥25 MW DC); 253 objects in `indiana_app`; 92 counties, 1.2M parcels rendered.

---

## OPERATOR RULINGS ALREADY MADE — binding, do not re-litigate

1. SI is admitted at the **NON-RESIDENTIAL** level only.
2. **Severity gates every signal** — only distress that would plausibly move an owner to sell.
3. **Capability is separate from signal.** 69% of flagged parcels cannot host 5 MW; that is an
   expected, useful filter, not a defect.
4. Where two measures disagree beyond threshold, **take the SMALLER** and label it disputed.
5. **Vacancy is two things** — footprint absence is a land state, not intent. Vacant land stays in
   the app for BESS siting.
6. **Union-and-dedupe every duplicated subject.** Never two partial layers of one thing.
7. County active-queue MW counts as **SUPPLY**, not competing demand.
8. Hyperscale DC = **whole parcel**; BESS = **outdoor space**.
9. Municode's generic `Allow: /` governs — its 153-row corpus stands.
10. Schools and weather stations are **removed** from the app.

## AWAITING YOU — do not chase, just flag if relevant

**American Legal licence** (robots grants `*`, terms forbid robots — unlocks **17 counties**,
`license@iccsafe.org`) · **robots-vs-terms standing policy** (30+ hosts disallow `ClaudeBot` by
name) · **a WSL/Docker install** (C5 is fully scripted the moment it exists) · D10 procurement
($600/yr) · the IRS ALS FOIA fax · an IEDC email for A1 · the refresh-cadence venue.

---

## IN FLIGHT AT SESSION CLOSE — check before duplicating

A **county DC-action sweep** was merging seven regional batches (`batch_A…G.json` in the session
scratchpad) into `in_dc_actions_county_v2` + `scrapers/lane_f/COUNTY_DC_ACTION_FINDINGS.md`.

**Two warnings were relayed to it and MUST be verified in its output:**
1. A stale **`batch_MINE.json`** in the same folder — if the merge globbed `batch_*.json`,
   counties may be **DOUBLE-COUNTED**.
2. Its sub-agents could not reply to it (it identified by agent TYPE, not ID).

Per-batch counts if you need to rebuild: **A 20/13 · B 18/12 · C 12/13 · D 13/13 · E 20/12 ·
F 8/13 · G 13/14**.

**The finding that sweep exists to capture:** codified ordinance search CANNOT answer the county
posture question. Verified moratoria and bans sit on county websites — Marshall and Cass have
**permanent bans**; Grant has a 24-month moratorium; Indianapolis passed one 23-1 through
2027-12-31. **Jefferson County approved a 7.1M sq ft datacentre by administrative interpretation
under a code that never mentions data centres** — a plain-text search finds nothing. And **Fulton
County's moratorium is recorded as triggered by a 500 MW / 300-acre Decennial Group proposal.**

---

## START BY

Confirming what you read, what the three commands printed, whether the county-sweep agent landed
its table (and whether the double-count warning was handled), and your plan for the first item in
`PATH_TO_COMPLETE.md` §2a.
