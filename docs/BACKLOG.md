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
| A4 | C4 saved workspaces | ✅ **DONE** `9569d12` — 40 controls enumerated dynamically + map view; round-trip verified in-browser | done |
| A5 | D12 Indianapolis placement | ✅ **DONE** — **admitted 228 → 2,109 parcels, reached 10,370 → 23,140.** The "matches nothing" diagnosis predated the Marion address crosswalk: **85.9% of distinct addresses match `FULL_ADDRESS` exactly.** Widened 2 case types → 7, gated on INTENT per the operator | done |
| A6 | **IDEM event dates** | **agent in flight** — found a bulk route (380 month-window POSTs, not 20,728 page fetches). **All 22,565 rows now at month precision**; enriching exact dates. `scrapers/lane_f/idem_dates.json`, NOT yet loaded | **load next** |

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
| F5 | Reconcile the two NW sweeps | ✅ **DONE** — `in_dc_actions_nw_reconciled`. **Both sweeps were wrong on Jasper PC-22-25**: the Plan Commission issued an unfavourable *recommendation* 2025-12-15 (advisory, not a denial) and the Commissioners **approved** it 2026-02-02 with nine commitments. "denied" was never true; "petition-pending" was true for seven weeks |
| F6 | DataBank IND2 pin offset | ✅ **DONE, and it was material, not cosmetic.** Tested all 6 resolved facilities by asking whether the two points land on the SAME PARCEL, not by how far apart they are. Five agree within 26 m. **IND2 was 96.8 m out and on the WRONG SIDE OF HENRY STREET** — our pin fell on `491111183001014101` (the 701/731/733 group, south side) when IND2 is 650 W Henry on the north side, parcel `491111138006000101`. A facility pinned to the wrong parcel corrupts every spatial join it takes part in. The layer build now lets a B4-resolved point override the held pin. Re-measured: **0 of 6 material** |
| F7 | `CLOUDSCENE_GAP.md` bad matches | ✅ **DONE, and worse than reported** — the matcher used operator tokens and PLACE NAMES alone. **8 fabricated matches**: three different Indianapolis Lifeline buildings all matched to *Fort Wayne*; three Global Access Point sites collapsed onto one via the acronym GAP; **"Indigital Fort Wayne" matched to "Google Fort Wayne Building 5"** — different companies, same city; "The Union 525" matched on the word *union*. A wrong match understates the gap and drops a site from follow-up. All flagged inline with a correction block |
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

**R3. STRUCTURAL DISTRESS MUST PLAUSIBLY PRODUCE INTENT. A minor incident does not.**
Operator, 2026-08-16. Applied to the 910,483-row Indianapolis code corpus as a two-tier gate
rather than a case-type list:
- **Tier 1, admitted on a single occurrence** — Unsafe Buildings, Vacant Board Order, Demolition.
  Each already means the building is unusable.
- **Tier 2, admitted only where chronic or unresolved** — Building violations, Repair orders,
  Environmental. Measured: **16,325 addresses have exactly one structural case; 2,176 have ten or
  more.** One citation is an incident; ten is an owner who has stopped maintaining the property.
- **Excluded outright regardless of type:** `Closed, No Violation` (60,449) and `Void` (13,987) —
  an inspector finding nothing is not distress, and counting it would be the "0 high-priority
  violators" error inverted.
- Also excluded, counted not dropped: High Weeds & Grass **363,844**, Trash 103,792, Zoning
  225,359, Vehicle 46,969. Admitting the corpus wholesale would have inflated D12 by ~750,000
  rows of lawn care — the South Bend error a third time.

## RULES EARNED THIS SESSION

1. **A completeness shortfall must be an `assert`, not a `print`.** The sweep loader reported "79 of 92" to a console nobody re-read and would have loaded anyway.
2. **An agent's deliverable is a file IT writes.** A parent collecting sub-agent replies lost 13 counties once and a whole NW pass entirely.
3. **For a scraper, "committed" and "safe" are different properties.** `.gitignore` excludes `scrapers/**/*.json` by design, so only the warehouse proves the second.
4. **A generated document must not carry hand-typed claims.** `SI_COVERAGE.md` asserted D4 absent for a whole session. Every NOT-HELD claim now carries a build-time probe; unprobed claims print as UNVERIFIED.
5. **Read the console in a fresh tab, or not at all.** A reused tab accumulates your own probes and reads as page defects.
6. **Check the state slice, not the national number.** `mat_parcel_attrs` has 69M owner names and **zero** for `parcel_source='parcels_in'`.
7. **Never assume a date format.** A `%Y-%m-%d` parse over `MM/DD/YYYY` reported "0 upcoming auctions" when 16,325 were upcoming; the corrected parse then threw on `00/00/0000` and needed `SAFE.PARSE_DATE`.
8. `r.keys` collides with `Row.keys()` — **third recorded occurrence**. Alias it `n_keys`.
