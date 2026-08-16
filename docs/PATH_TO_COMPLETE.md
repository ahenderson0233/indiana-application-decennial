# PATH TO 100% — every remaining task, why it is not done, and what closes it

**Written 2026-08-16 at session close.** This is the single document that answers "what is left".
`HANDOFF.md` is the record of what happened; `GAMEPLAN.md` is the running plan; this is the
finish line and the distance to it.

> **Do not quote a count from any document, including this one.** Two denominators moved several
> times in a single day — registered objects 226 → 242 → 252, counties assessed 37 → 68. Run
> `scripts/audit_wiring_census.py`, `scripts/audit_honesty.py` and `scripts/acceptance_run.py`
> and use what they print.

---

## 0. Do these three things first, before any new work

1. **`python scripts/audit_honesty.py`** — 12 adversarial checks. It failed once on 2026-08-16
   because a rebuild landed after an export and the map shipped a stale SI count. If check 2
   fails, run `scripts/export_sites_exact.py` and re-run the audit before trusting any on-screen
   number.
2. **`python scripts/audit_wiring_census.py`** — the wiring denominator moves on every build.
3. **Check the background agents' output** (§5 below).

---

## 1. What is DONE, and how it was done

| phase | state | how |
|---|---|---|
| **A — wire every object to a surface** | ✅ complete | census is a SCRIPT, not a number: builder vs consumer, plus registry-panel and derivative routes |
| **B — data-integrity debts** | ✅ complete | flag widened and severity-gated; three key namespaces bridged; D85 guarded everywhere; WARN deduped |
| **C1 dossier** | ✅ | P1–P6 verdict built from the SAME functions the screener uses, so it cannot disagree with the map |
| **C2 rate engine** | ✅ | four proxies + ≥1.75× wholesale floor; refuses to quote because no Indiana component tariff exists |
| **C3 RTEP→bus** | ✅ | name-matched with `match_confidence` on every row; bus hop goes through an already-resolved field, not a second name guess |
| **E1 honesty audit** | ✅ | adversarial: hunts the four errors this project actually made |
| **E2 refresh cadence** | ✅ | derived from publisher event dates; "cannot derive" where no date exists |
| **E3 handover pack** | ✅ | generated; leads with the errors because a national build repeats them at 50× |
| **E4 acceptance run** | ✅ run | §13: 4 PASS, 3 PARTIAL, 0 FAIL, 2 N/A |

---

## 2. What is LEFT — the actual finish line

### 2a. Buildable now, no blocker

| task | closes | effort | notes |
|---|---|---|---|
| **C4 saved workspaces** | §13 shortlist v2 | small | persist screener + weights + layers as a named workspace. Front-end (localStorage); operator deferred the front-end pass |
| **Upload parity test** | §13(2) | small | the door exists; run ONE round-trip with a real file and prove uploaded rows score identically to held rows |
| **Fold the county DC-action table into P5** | posture scoring | small | once the running agent lands `in_dc_actions_county_v2`, join it to `vw_county_dc_posture`'s replacement and surface moratorium EXPIRY on the dossier |
| **Alias table for the DC cross-check** | removes a false gap | small | B4 proved 5 of 8 "missing" colos were already pinned under another operator name (CenturyLink→Lumen, LightBound→DataBank, 365→Netrality) |
| **D12 Indianapolis placement** | 747,122 rows | medium | the address authority fixed Unsafe Buildings / Vacant Board Order; the wider corpus still matches zero |
| **IDEM event dates** | 22,565 actions | medium | dates live on per-case document pages; `document_published` is a Y/N flag, not a date |

### 2b. Blocked on an operator decision

| task | the decision | what it unlocks |
|---|---|---|
| **American Legal licence** | robots.txt grants `*`; the ICC terms forbid robots. Which governs? | **17 of the 55 unassessed counties** have an amlegal code as their ONLY codified source. Route: `license@iccsafe.org` |
| **robots-vs-terms standing policy** | 30+ hosts disallow `ClaudeBot` by name while serving the public freely | every future acquisition lane |
| **D10 state tax warrants** | $600/yr INCite or $38/mo Doxpop | a whole signal |
| **IRS ALS FOIA (D13)** | your fax; drafted in `docs/FOIA_IRS_ALS_REQUEST.md` | federal tax liens |
| **IEDC data request (A1)** | one email | commercial listings |
| **WSL or Docker install** | 10 minutes of your time | **C5 PMTiles** — fully scripted the moment either exists |

### 2c. Blocked upstream, not by us

| task | blocker |
|---|---|
| **DLGF Gateway owner pull** | ⭐ the highest-value acquisition left. `mat_parcel_attrs.parcel_owner` is NULL on all 3,553,381 Indiana parcels. One pull unblocks **five** signals: D9, D18, D11, D27 and IDEM |
| **P6 acceptance (§13(8))** | no component-level Indiana tariff exists anywhere in the estate. C2 compares four proxies and refuses to quote; closing this needs a tariff-book acquisition |
| **AI docket summary (§13(5))** | this app has no LLM feature. Half of the golden-path criterion is unmet and is not claimed |
| **HC v2 (§13(4))** | a platform deliverable, not this app |
| **Visual grammar review (§13(6))** | a human review, deferred with the front-end |
| **D4 tax delinquency** | seasonal — SRI publishes Jul–Oct |
| **D15 mechanics liens** | 92 recorders, all paywalled. A cheque, not a scraper |

---

## 3. Gaps that are LIVE in the app right now

A user can hit each of these today. None is hidden; each renders as itself.

- **68% of RTEP upgrades reach no facility** — reported as unmatched, never forced onto a bus.
- **The SI flag is 75% vacant land**, and 69% of flagged parcels cannot host even 5 MW. Ruled an
  expected filter, not a defect — capability is carried beside the flag.
- **9,767 flagged parcels carry no event date.** Correct: that is NULL, not zero, and recency
  does not penalise them.
- **Only 19 admitted ordinance sections in 9 jurisdictions.** The real regulation is county
  moratoria; the sweep is landing them.
- **P6 shows no per-parcel tariff, deliberately.** Putting the URDB proxy on a dossier would lend
  it precision it does not have.
- **D85** (`parcels_in/080500000047000018`) is still an inverted whole-Earth polygon upstream.
  Guarded in every spatial join here; **any NEW spatial join must exclude it**.

---

## 4. How to work on this codebase

- **Read the schema before every query.** The most repeated failure in this project.
- **A clean, perfect or alarming number is a claim about your INSTRUMENT first.** Check the join,
  then the filter, then the data. Nine of today's findings came from doing this.
- **Register in the same run that writes.** An unregistered table blocks another session's
  checkpoint.
- **Never `git add -A`.** Stage explicit paths.
- **After any build touching `in_si_sites_flags_v2`: re-export sites, then re-run the audit.**
- Reserved words that have bitten: `rows`, `no`, `FULL`, `ROWS`. In BigQuery a doubled `''`
  inside a literal parses as two adjacent strings; in JS adjacent string literals are a
  SyntaxError that once took the whole map down.
- Python's `SimpleHTTP` sends no `Cache-Control`, so Chrome serves a stale `app.js`. Fix:
  `await fetch(f, {cache:"reload"})` for each changed asset, THEN navigate.

---

## 5. In flight at session close

**County DC-action sweep** — seven regional batches written to the session scratchpad as
`batch_A…G.json`; the parent has merge, load and findings staged and will produce
`in_dc_actions_county_v2` and `scrapers/lane_f/COUNTY_DC_ACTION_FINDINGS.md`.

**Two warnings were relayed and must be verified in its output:**
1. A stale **`batch_MINE.json`** sits in the same folder. If the merge globs `batch_*.json` it
   will be swept in and counties may be DOUBLE-COUNTED. The agent was asked to name inputs
   explicitly or to dedupe and *report* the duplicates dropped.
2. Its sub-agents could not reply to it — it identified itself by agent TYPE (`general-purpose`)
   rather than by ID. Counts were relayed manually.

**If the parent failed**, every batch is recoverable from the JSON files, and the per-batch counts
are in the session transcript: A 20/13, B 18/12, C 12/13, D 13/13, E 20/12, F 8/13, G 13/14.
