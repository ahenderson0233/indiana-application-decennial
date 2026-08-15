# GAMEPLAN — from here to a finished application

**Written 2026-08-15. This is the running plan; HANDOFF.md is the running record.** Read this
to know what to do next; read HANDOFF §5b to know what has already been done and must not be
redone. When something new is noticed, add it to the right phase here rather than starting it
immediately — the point of this file is that the order survives a context refresh.

## Where we actually are (measured 2026-08-15, not recalled)

| | |
|---|---:|
| tables physically in `indiana_app` | 198 |
| registered in `_registry` | 196 |
| **reach a user-facing surface** | **139 (71%)** |
| reach nothing yet | 57 |
| pages live | 6 (Map · Grid · Market · Community · SI Feed · Data) |
| parcels held / rendered class-union | 3,553,194 / 1,200,916 |

Shipped and verified: the map console with composable screener + four part presets, per-parcel
evidence with provenance, both-RTO headroom with direction disclosed, the upload door, composite
scoring with user weights, the tariff cost proxy, 249 located data centres with precision tiers.

**The measuring rule that keeps being earned:** a perfect score is a claim about the instrument.
The first wiring count said 196/196 because it counted each table's own build script as a
"feature". Check what the instrument is actually counting before believing a clean number.

---

## PHASE A — wire the 57 orphans (OPERATOR PRIORITY: before any front-end work)

The motto is one feature per table. 57 registered tables reach no screen. No new acquisition is
required for any of this — it is all held, clipped and registered already.

**A1 — openstates legislative family (9 tables).** `energy_bills`, `_v2`, `votes`,
`vote_people`, `actions`, `sponsorships`, `versions`, `sources`, `abstracts`. Build the P7
legislative preview section on **Community**: bill list → status → sponsors → vote roll, filtered
to Indiana energy/DC bills, joined to the existing IURC docket browser.
*Acceptance:* every one of the 9 tables feeds a column, filter or drill-down; each bill row
reaches its votes and its sponsors; provenance line per table.

**A2 — context layers with no home (19 tables).** storm_events · fema_disaster_declarations ·
weather_stations · wind_turbines · ghgrp_facilities + ghgrp_emitter_facilities · eia860_generators
+ eia860m_generators · eia861_demand_response · eia923_fuel_receipts_costs · water_cwns_2022 ·
sba_foia_loans · gov_surplus_frpp · acs_tract_vacancy · eqr_identity · gas_phmsa_distribution ·
candidate_sites_schools + _private_schools · osm_power_lines + osm_power_substations.
Route each to the page it belongs on (risk → Map overlays + county panel; generation → Grid;
market/demand → Market; surplus/vacancy → SI Feed; candidate sets → upload-door demo).
*Acceptance:* zero tables left in the orphan list except by written waiver; the Data page's
inventory shows a home for each.

**A3 — SI source visibility (20 tables).** The city-level sources (Evansville, Indy, South Bend)
and the six `si_refresh_*` sets feed `in_si_signals` upstream but no screen shows them. Build a
**source-level panel on SI Feed**: per source, rows held, last observed event, publisher staleness,
and which signal it feeds.
*Acceptance:* each of the 20 named with its row count and freshness; the Lane-D remediation
counts become visible rather than living only in a findings file.

**A4 — NFIRS structure-fire vintages (7 tables).** 2020/2021/2024 basic, fire and address sets.
Value-read before wiring — confirm what an "incident" row is at parcel grain before claiming D16.
*Acceptance:* either wired as a D16 candidate layer with its keying quality stated, or waived in
writing with the measurement that justified it.

**A5 — housekeeping (2 empty + 1 unregistered).**
`in_fcc_bdc_mobile_summary_by_geography` and `in_fcc_bdc_provider_summary_by_geography` hold **0
rows** — leftovers of the `_st_pct` instrument bug; drop them or record why an empty table is kept.
`_indiana_census` is unregistered — register it or move it out; an unregistered table trips the
other session's checkpoint invariant 3.
*Acceptance:* `indiana_app` has no empty table and no unregistered table.

> **Phase A target: 139/196 → ~196/196.** This is the single largest quality jump available and
> the operator has ruled it precedes front-end work.

---

## PHASE B — data-integrity debts (parallel; several are blocked upstream)

**B1 — `mat_parcel_attrs` is 100% NULL** on every attribute column across all 3,553,381 Indiana
rows. Blocks D18 and the whole owner-approach workflow. *Filed with the platform session; blocked
on them.*

**B2 — `si_last_event_date` is 0.6% populated** (165,494 SI parcels, 935 dated across 7 counties).
Any recency filter built on it measures our coverage, not the signal. The screener now keeps
undated parcels and says so. *Real fix is upstream; filed.*

**B3 — the acreage disagreements we did not auto-correct.** 41 parcels where exact < half of
recorded acreage *with* footprints present (a large building might genuinely explain it), and 107
where exact exceeds 200% of recorded. Neither is silently fixed. Decide a rule or leave flagged.

**B4 — the 7 unresolved Indianapolis colo facilities.** OPERATOR APPROVED to pursue. Needs an
address source. **Check cloudscene's terms and robots before any scrape — if gated, record BLOCKED
with the exact wall and stop.** Likeliest truth is that they are provider presences inside the Indy
Telcom carrier hotel (701/733 W Henry), not missing buildings.

**B5 — `vw_county_dc_posture` ordinance counter reads 92/92.** Suspected instrument defect; not
rendered anywhere. Verify or retire.

**B6 — DCM city-centroid defect, national scope.** 4,370 rows nationally in stacks of 5+, worst
251. Fixed for Indiana. *Sent to the platform session for their BACKLOG, non-urgent by operator
ruling.* Note: centroids are not banned outright here — they are LABELLED. A city point answers
"which town" and must never answer "how far".

---

## PHASE C — functionality (after Phase A)

**C1 — Dossier v2. The management-facing deliverable.** 2–5 page per-site P1–P6 verdict: land &
size, grid access with headroom direction, environmental gates, community posture with receipts,
market/cost band, SI history — every number with source and build date, every cannot-assess shown
as itself. *Acceptance: one dossier generated end-to-end for a real shortlisted site, printable.*

**C2 — Itemised rate engine.** Replaces the flattened-URDB cross-check now on Market. Four-proxy
rule, ≥1.75× wholesale floor gate, CPS-style fixed/demand/energy/fuel decomposition, MW-floor
eligibility. Read `ANALYSIS_METHODOLOGY.md` §4 again before starting.
*Acceptance: parity with the CPS 35 MW test case; every figure carries its tariff name.*

**C3 — RTEP → bus drill-down.** The 932 upgrades and 375 cost allocations exist on Grid but do not
join to the located buses. Join them so an upgrade cost is reachable from the bus it attaches to.

**C4 — Shortlist / saved workspaces v2.** Persist screener + weights + layers as a named workspace;
the spec's "user-saved custom workspaces" line.

**C5 — PMTiles all-parcel rendering. ⛔ BLOCKED** on a WSL or Docker install for tippecanoe
(re-measured absent 2026-08-15). Fully scripted the moment either exists — do not start before.

---

## PHASE D — acquisition lanes (opportunistic, agent work, FABLE5 rules embedded)

D1 MISO LOAD-direction headroom (we hold injection only) · D2 county assessor owner rolls
(unblocks B1/D18 without waiting on upstream) · D3 A1 listings · D4 Vanderburgh child parcels ·
D5 EBB history depth. Each: check the registry and `docs/SAMPLES_*` first; scrape only what a
source permits; a gated source is recorded BLOCKED with its exact wall, never worked around.

---

## PHASE E — hardening and handover

**E1 — Honesty audit.** Sample 50 on-screen numbers, trace each to source table + build date;
zero cannot-assess rendered as 0 or blank. Spec §13(3).
**E2 — Refresh cadence.** The T8 table is written and *deferred by the operator*; schedule it when
they pick a venue (Task Scheduler vs cloud cron).
**E3 — National-baseline handover.** This app is the national app's baseline: payload contract,
honesty grammar, per-source registry, the audit method, and the findings already flagged for it
(SPP headroom harvest, DCM centroids, EBB gas).
**E4 — Acceptance run** against `2_TECHNICAL_BUILD_SPEC.md` §13, part by part.

---

## Working order

```
A1 → A2 → A3 → A4 → A5     (wiring; operator priority, no acquisition needed)
   ↘ B3, B4, B5 in parallel  (B1, B2, B6 wait on the platform session)
C1 → C2 → C3 → C4          (C5 whenever the install lands)
D anywhere an agent is free
E last, then ship
```

**Standing rules that bind every phase:** value-read before wiring · dry-run every query ·
register in the same run · Indiana-clipped · cannot-assess renders as itself · estimates never
style as published · every number carries source + build date · no centroid in distance math ·
never `git add -A` · scripts not agents for anything already scripted.
