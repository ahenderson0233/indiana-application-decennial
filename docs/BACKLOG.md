# BACKLOG — the running task ledger

**Maintained continuously. Nothing leaves this file except by being DONE or by being ruled
out with a reason.** Opened 2026-08-16.

> **Before starting ANY item, check it against the warehouse.** This session recommended work
> four times that was already done, already impossible, or misread — D4 was "NOT HELD" while
> 17,617 rows sat in the warehouse; owner data was "absent" while `in_marion_parcel_crosswalk`
> carried it on 346,919 parcels; D12 "admitted 228" conflated *admitted* with *reached* (10,370);
> and a bug was filed on `si.html` from a console polluted by my own probes.
> `docs/TABLE_INVENTORY.md` exists to stop the first two recurring. Read it first.

---

## NOW — in flight or next

| # | task | why | state |
|---|---|---|---|
| N1 | Load the 4 verification results | 50 verified; Brown/Clay out-of-state corrections; Marion downgraded to pending | ✅ **DONE** `8a5ee58` |
| N2 | Re-export + re-audit after N1 | standing ritual | ✅ **DONE** |
| N3 | D9 absentee + D18 for Marion | 340,765 parcels · 28,763 out-of-state · 7,194 non-residential · 272,606 named owners | ✅ **DONE** `2e76cab` |
| N4 | S1 D4 split out of D1 | 15,106 rows · 45 counties · 100% dated · 18 signals now reach a parcel | ✅ **DONE** `ff24c9e` |
| N5 | A2 operator alias table | found the TELCO regex was filing pinned Lumen colos as telephone exchanges | ✅ **DONE** `e7246d2` |
| N6 | **A3 upload parity** | the door DOES exist (`index.html:125`, my earlier doubt was wrong). Real defect found: uploads wrote `_sub_mi` while the scorer reads `_dsub_mi`, so **every uploaded row went unscored**, and line distance was never computed. Fixed by routing uploads through the same `enrichDistances` the map uses | **fix in, needs the round-trip test** |
| N7 | **Load the re-sweep** — 18 counties, 3 flipped to ACTION_FOUND | Henry (~1 GW Surge PUD) and Tipton (moratorium, CO-ZO-13-26) VERIFIED; Sullivan (~$65B Potentia/Heartland, no county zoning) REPORTED | ✅ **DONE** |
| N8 | Fold the re-sweep into the Community page + coverage | 3 counties currently render as "nothing found" when they are not | **next** |

## THE LAST SESSION'S OPEN LIST — `PATH_TO_COMPLETE.md` §2a, audited 2026-08-16

| # | task | audited state | effort |
|---|---|---|---|
| A1 | Fold county DC-action table into P5 | ✅ **DONE** — `in_dc_actions_county_v2` (107) + coverage (92) landed, wired to Community | done |
| A2 | **Alias table for the DC cross-check** | **CONFIRMED OPEN** — zero alias tables exist; `in_cloudscene_crosscheck` has 2 rows naming a renamed operator | small |
| A3 | **Upload parity test** | **CONFIRMED OPEN**, and worse than recorded: `app.js` has `parseCsv` but **no `FileReader`, no file input, no `accept=`**. §13(2) claims "the door exists" on a regex that matched `parseCsv`. Verify the door exists before testing parity | small |
| A4 | **C4 saved workspaces** | **CONFIRMED OPEN** — zero `localStorage`/`sessionStorage` in `app.js` | small, front-end |
| A5 | **D12 Indianapolis placement** | **PARTIALLY DONE** — 747,211 held · **10,370 reached** · 228 admitted. `in_si_indy_code_placed` (46,411) and `in_marion_address_crosswalk` (465,050) landed today | medium |
| A6 | **IDEM event dates** | **CONFIRMED OPEN** — 11 columns, no date column; `document_published` is `Y`/`N`. Routes: year embedded in `case_number` (2,164 of 22,565) or scrape the **20,728 rows carrying a `document_url`** | medium |

## PHASE COMPLETION — what stands between here and A–E at 100%

| phase | state | what remains |
|---|---|---|
| **A** wiring | ✅ **255 of 255**, measured | nothing |
| **B** integrity | ✅ complete | nothing |
| **C** functionality | C1 ✅ C2 ✅ C3 ✅ | **C4** (A4 above) · **C5 PMTiles BLOCKED** on a WSL/Docker install |
| **D** acquisition | ongoing | A5, A6, N3 |
| **E** hardening | E1 13/13 · E2 ✅ · E3 ✅ · E4 4 PASS / **3 PARTIAL** / 0 FAIL | the three PARTIALs below |

### The three §13 PARTIALs, and whether they can actually close

| criterion | closeable? | what it needs |
|---|---|---|
| §13(2) upload parity | **YES** | confirm the upload door exists, then one round-trip test |
| §13(5) golden path | **NO, not as specified** | the dossier half is met; the **AI docket summary** half needs an LLM feature this app does not have. Closing it means building a feature, not finishing one |
| §13(8) P6 acceptance | **NO** | no component-level Indiana tariff exists anywhere in the estate. Structural, not pending |

**So "A–E 100%, no fails" is already true of FAILs (0).** Two of three PARTIALs are structural.
An honest finish is: **A, B, C(-C5), D, E complete; §13(5) and §13(8) recorded as
NOT-ACHIEVABLE-AS-SPECIFIED with the reason**, rather than quietly restated as passes.

## SIGNALS — measured 2026-08-16, `docs/SIGNAL_REALITY.json`

23 signals wired; 17 reach and admit parcels. Of the rest:

| class | n | agent-actionable? |
|---|---:|---|
| ADMITTED | 17 | done |
| HELD_NOT_SPLIT | 2 | **yes** — D4 (17,617 rows), D23 |
| HELD_WRONG_GRAIN | 8 | no — owner/county/aggregate grain, or an operator exclusion |
| OPEN | 3 | **yes** — D9/D18 (one blocker), D22 IDEM dates |
| AWAITING_OPERATOR | 1 | no — D13 FOIA fax |
| BLOCKED_STRUCTURAL | 3 | **no — stop re-recommending**: A1 robots, D10 + D15 paywalled |

| # | task | note |
|---|---|---|
| S1 | **Split D4 out of D1_tax_sale** | 17,617 rows, 76 counties, 92% parcel-keyed, 16,325 auctions still upcoming, 10,178 non-residential. A split, not a scrape |
| S2 | **D9 absentee, Marion** | = N3 |
| S3 | D9 absentee statewide | needs the DLGF pull |
| S4 | D23 surplus split | low value; watch-list only |

## AWAITING THE OPERATOR — do not chase

| item | ask |
|---|---|
| American Legal licence | one email to `license@iccsafe.org`; unlocks **17 counties** whose only codified source is amlegal |
| robots-vs-terms standing policy | 30+ hosts disallow `ClaudeBot` by name while serving the public freely |
| WSL or Docker install | 10 minutes; **C5 is fully scripted the moment it exists** |
| D10 procurement | $600/yr INCite or $38/mo Doxpop |
| IRS ALS FOIA | your fax; drafted in `docs/FOIA_IRS_ALS_REQUEST.md` |
| IEDC data request | one email; the only lawful route to A1 |
| refresh-cadence venue | Task Scheduler vs cloud cron |

## FOLLOW-UPS RAISED AND NOT YET DONE

| # | task | source |
|---|---|---|
| F1 | Re-sweep the 4 single-query counties — Henry, Johnson, Union, Wayne | sweep fell below its own ≥2-query standard |
| F2 | Fetch the official site for the 18 negative counties where it was never reached | same |
| F3 | Re-check Howard + City of Elkhart — actions were scheduled for **2026-08-17** | group 2 verification |
| F4 | Re-check Marion — MDC final action **2026-08-19** | group 3 verification |
| F5 | Reconcile `in_dc_actions_nw_first_pass` (17 rows) against the verification results | two NW sweeps disagree; do NOT union them |
| F6 | Reconcile the ~90 m DataBank IND2 pin offset (baxtel vs PeeringDB) | `COLO_ADDRESS_FINDINGS.md` |
| F7 | `docs/CLOUDSCENE_GAP.md` "Lifeline West Henry → Lifeline Fort Wayne" match is wrong | same matcher defect as A2 |
| F8 | `si.html` MapLibre `ctx-osm-line` guard | **NOT A BUG** — verified clean on a fresh tab; a separate session was started on it in error |

## OPERATOR RULINGS — 2026-08-16, binding

**R1. KEEP EVERY PARCEL. Do not filter the rendered payload by occupancy class.**
The proposal was to drop parcels carrying a residential structure, on the grounds that a house
cannot host a hyperscale DC or a 5 MW BESS. Measured before acting, that cut would have removed
**165,003 parcels of which 160,669 fit a 25 MW datacentre** — because `occ_group` describes the
STRUCTURE, not the land, and 97.5% of them are **farmsteads**: 5–20 ac (87,541), 20–100 ac
(63,310), 100+ ac (9,953, largest **6,374 acres**), averaging 3–5 structures. A farmhouse on 200
acres classes residential and is exactly the site a developer wants.
Only 4,199 were genuine small lots — **0.35% of the 1.2M payload**, no meaningful performance win.
**Operator ruling: keep them all, because a 250 kW or 500 kW BESS may be installed later** and
needs a fraction of the land 5 MW does. Capability columns (`fits_min_bess_5mw`, `fits_dc_25mw`)
already filter on what the land can hold, which is the question that actually matters.

**R2. Vacant land stays** — 896,947 no-structure parcels, unchanged. (Restates the standing rule.)

## RULES EARNED THIS SESSION

1. **A completeness shortfall must be an `assert`, not a `print`.** The sweep loader reported "79 of 92" to a console nobody re-read and would have loaded anyway.
2. **An agent's deliverable is a file IT writes.** A parent collecting sub-agent replies lost 13 counties once and a whole NW pass entirely.
3. **For a scraper, "committed" and "safe" are different properties.** `.gitignore` excludes `scrapers/**/*.json` by design, so only the warehouse proves the second.
4. **A generated document must not carry hand-typed claims.** `SI_COVERAGE.md` asserted D4 absent for a whole session. Every NOT-HELD claim now carries a build-time probe; unprobed claims print as UNVERIFIED.
5. **Read the console in a fresh tab, or not at all.** A reused tab accumulates your own probes and reads as page defects.
6. **Check the state slice, not the national number.** `mat_parcel_attrs` has 69M owner names and **zero** for `parcel_source='parcels_in'`.
7. **Never assume a date format.** A `%Y-%m-%d` parse over `MM/DD/YYYY` reported "0 upcoming auctions" when 16,325 were upcoming; the corrected parse then threw on `00/00/0000` and needed `SAFE.PARSE_DATE`.
8. `r.keys` collides with `Row.keys()` — **third recorded occurrence**. Alias it `n_keys`.
