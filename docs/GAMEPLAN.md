# GAMEPLAN — from here to a finished application

**Written 2026-08-15. This is the running plan; HANDOFF.md is the running record.** Read this
to know what to do next; read HANDOFF §5b to know what has already been done and must not be
redone. When something new is noticed, add it to the right phase here rather than starting it
immediately — the point of this file is that the order survives a context refresh.

## Where we actually are (measured 2026-08-15, not recalled)

| | |
|---|---:|
| tables physically in `indiana_app` | 200 |
| registered in `_registry` | 199 |
| **reach a user-facing surface** | **196 of 199 (98%)** — 139 at Phase A start |
| reach nothing yet | 3, all deliberate: 1 meta table + 2 zero-row tables, each with a written waiver |
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

**A1 — openstates legislative family (9 tables). ✅ DONE 2026-08-15.** P7 preview live on
Community: 66 energy bills across sessions 2024/2025/2026, filterable by session, chamber,
data-centre relevance and free text; each bill opens a drill-down with abstract, sponsors,
every recorded vote with its **full member roll-call**, the action timeline and links to the
Indiana General Assembly's own pages. **8 tables wired, 1 waived:**
`in_openstates_energy_bills` (21) was measured a STRICT SUBSET of `_v2` (21 shared ids, 0
unique) — a superseded generation, waived per build spec §0.2 with the waiver stated on the page.
Measured and conserved: 66 bills · 7 naming data centres · 22 reaching a vote · 126 vote events ·
9,197 individual member votes · 811 actions · 300 sponsorships · 140 versions · 132 sources.
Referential integrity: **zero orphans** across all six child tables; every roll-call row reaches
one of the 126 vote events. Script: `scripts/export_legislature.py` → `data/legislature.json.gz`
(80 KB).
**`match_field` is carried to the screen** as "qualified on: …" — it is the subject-selection
instrument (abstract 44 · title+abstract 14 · title+subject+abstract 4 · title 3 ·
subject+abstract 1), and a bill matched on its abstract alone is a weaker claim to the subject
than one matching title AND subject AND abstract. The reader sees which.
**The 7 data-centre bills**, the reason this section exists: HB 1043 (DC water regulation),
HB 1189 (labor requirements for DC incentives), HB 1245 (IURC study of data centers), SB 257
(electricity rate increases due to data centers), SB 79 + SB 135 (DC development), SB 431
(construction by a foreign adversary — passed the Senate 48–0).
*Lesson recorded:* the first provenance line abbreviated the child tables (`_abstracts`,
`_actions`). That breaks the rule that every number carries its source table — a reader cannot
look up `_actions` — and it also made the wiring measurement under-count by 7. Write table names
in full on screen.

**A2 — context layers with no home. ✅ DONE 2026-08-15.** 20 tables routed; **147 → 165 of 196**.
*Six new map layers* (one shared 1 MB payload, fetched on FIRST TOGGLE rather than at boot):
OSM transmission ≥100 kV (5,013), OSM substation footprints (2,873), GHGRP emitters (263),
federal surplus property (1,552), schools (2,518), weather stations (2,108).
*Grid:* the generating fleet at the latest report date — existing 34,381 MW, retired 8,682,
proposed 4,639 — plus announced retirements from EIA-860M.
*Market:* delivered fuel cost per MMBtu, demand response with its denominator on screen, FERC
EQR filers. *Community:* FEMA disaster history and NOAA storm events. *SI Feed:* highest-vacancy
tracts (restricted to >200 units so tiny denominators cannot top the list) and SBA lending.
*Data:* PHMSA gas distribution operators, and a **waived-tables card** so nothing is dropped in
silence.
**Four value-reads changed the build:** `in_wind_turbines` was a FALSE ORPHAN (coords are
`xlong`/`ylat`; its 1,652 turbines were already on the map) → provenance line, not a layer.
`in_water_cwns_2022` is STRUCTURALLY EMPTY (404 rows, 0 with facid, 0 with latitude) → waived
with the measurement. `in_ghgrp_emitter_facilities` is a subset of `in_ghgrp_facilities` (246 of
246 ids shared) → facilities is the layer, emitter supplies year/NAICS. `in_osm_power_lines` is
ADDITIVE not duplicate — 5,013 lines ≥100 kV against 2,623 in `in_transmission_lines`.
**Two instrument failures caught mid-build:** OSM substations first exported **1 of 2,873**
because the query filtered on `latitude` and 2,872 are ways carrying a Polygon with no point at
all — now drawn as true footprints, since deriving a point would be a banned centroid. And FEMA
rolled up to **93 counties for a 92-county state**: `fipsCountyCode='000'` holds 'Statewide' and
a tribal TDSA, the same shape as the IOCS poison row — excluded from the roll-up and listed
separately.
*Third waiver added:* `in_data_centers_deduped` is superseded by `in_data_centers_located`.
*Tooling lesson, third time it has cost time:* Python's `SimpleHTTP` sends no `Cache-Control`,
so Chrome serves a stale `app.js` after an edit and neither a new tab nor a server restart
clears it. **The fix that works: `await fetch(f, {cache:"reload"})` for each changed asset, then
navigate.** A stale-JS symptom looks exactly like a code bug — `ensureContextLayers` undefined
while a function defined *after* it exists.

**A3 — SI source visibility. ✅ DONE 2026-08-15.** All 18 sources on SI Feed with what they hold,
what one row IS, the PUBLISHER'S event range and our pull date. **The find that made it work:**
seven of the eighteen date columns store **epoch milliseconds as strings** (`1656424281000` =
2022-06-28, the Esri/ArcGIS convention). A string-only parse reported all seven as unparseable and
would have shipped a freshness panel blind to the majority of our SI rows, including the 910,483-row
Indy code-enforcement set. Now: 9 parse cleanly, 4 partially, 4 hold no publisher date (said so
rather than substituting a pull stamp), 1 has an empty column. Seven are 2+ years stale.
**Duplicate resolved:** `in_si_refresh_warn_notices` and `in_si_state_warn_notices` both hold 1,220
notices sharing 1,104 company|city|date keys — same source twice; kept the one with `notice_pdf_urls`.

**A4 — NFIRS structure fires. ✅ DONE 2026-08-15 — WIRED, not waived.** `in_nfirs_structure_fires`
(16,264 rows) is a D16 candidate at ADDRESS grain, explicitly not claimed as parcel grain.
**Two defects fixed on the way in:**
· Only **~21% of NFIRS incidents are structure fires** (8,145 of 38,287 in 2020). The rest are gas
  leaks (412), downed power lines (444), rubbish (151), vehicle (131) and cooking fires (113).
  Admitting the raw tables would have inflated D16 roughly **fivefold**. Filtered to INC_TYPE 111–123.
· **`in_nfirs_fireincident_2024` IS NOT INDIANA-CLIPPED** — only 848 of 1,255 rows are `IN`;
  **407 (32%) belong to 43 other states** (IL 74, OH 49, KY 29, MI 25, TX 12 …). An `in_*` table
  carrying a third out-of-state rows breaks the clipped-at-the-border rule, so `STATE='IN'` is
  enforced on every input rather than trusting the prefix. 2020/2021 are clean.
Addresses are better than expected: 91% carry number+street, enough for a future parcel join, and
the keying quality rides on every row.

**A5 — housekeeping. ✅ DONE 2026-08-15.** `_indiana_census` registered (773 rows, meta table,
deliberately not rendered) so it stops tripping checkpoint invariant 3. The two zero-row FCC
tables were KEPT rather than dropped, each with a registry note explaining that they are empty
**by defect** — the `_st_pct` regex matched percentage columns like `mobilebb_4g_area_st_pct`, so
the clip filtered on the wrong field — and that both are superseded by working tables already
wired. A dropped table teaches nothing and the next census would rediscover the names as a gap.

**A6 — UNION-AND-DEDUPE EVERY DUPLICATED SUBJECT (operator ruling 2026-08-15).**
*"We want the full picture, not a partial picture — this should be recognised throughout the
website."* A2 shipped OSM transmission as a layer BESIDE the HIFLD spine, which leaves the user
to union two partial pictures in their head. That is the wrong shape. The right shape already
exists in this repo: the data-centre layer unions 5 sources, dedupes on a stated rule, and badges
each pin with where it came from. Apply that pattern to every subject we hold twice.
Known duplicated subjects to merge, each needing its own measured dedupe rule:
| subject | sources held | first question to measure |
|---|---|---|
| transmission lines | `in_transmission_lines` 2,623 · `in_osm_power_lines` 5,013 ≥100 kV | do they overlap geometrically, or cover different circuits? |
| substations | `in_substations` 3,858 · `in_osm_power_substations` 2,873 polygons | point-in-polygon and name match |
| generation | `in_eia_plants` 2,675 · `in_power_plants` 208 · `in_solar_pv_facilities` 114 · `in_wind_turbines` 1,652 | are plants and turbines the same rows at different grain? |
| gas pipelines | `in_gas_pipelines` 215 + the national duplicate flagged in spec §14 | keep `gas_pipelines_hifld`, confirm by fingerprint |
| brownfields | 3 programme tables — spec §14 says NOT duplicates | union with a `program_source` column, dedupe only exact registry_id |
| WARN notices | `in_si_refresh_warn_notices` 1,220 · `in_si_state_warn_notices` 1,220 | identical counts — same table twice? |
**Rules this must follow, all already earned here:** never merge on distance alone (it ate the
New Carlisle campus in testing); carry a `src` and a `match_method` per row; keep what cannot be
judged and label it rather than dropping it; state the coverage gain on screen ("N of M rows come
from OSM alone") so the merge is auditable, not magic.
*Acceptance:* for each subject, ONE layer with a source badge, a stated dedupe rule, and a
measured before/after count. The user should never have to toggle two layers to see one thing.

> **PHASE A — wiring COMPLETE and now MEASURED: 226 of 226 registered objects reach a surface**
> (`scripts/audit_wiring_census.py` → `docs/WIRING_CENSUS.md`). Do NOT quote that figure without
> re-running it: the denominator moves on every build that registers something.
>
> **A6 CLOSED 2026-08-16 — verified subject by subject, not assumed:**
> | subject | verdict |
> |---|---|
> | transmission | ✅ merged — `in_transmission_union`, OSM kept only where no HIFLD line within 100 m |
> | substations | ✅ merged upstream — `in_substations` was already a HIFLD+OSM union |
> | generation | ✅ merged — `in_generation_union` (283), FULL OUTER JOIN on plant code, EIA reduced to its latest row per plant first. **Was built and never shipped**; surfaced 2026-08-16 |
> | gas pipelines | ✅ **NOT a duplicate.** `in_gas_pipelines` (215) is the only pipeline-geometry table; the 9 `in_gas_capacity_*` tables are capacity SERIES per pipeline — different grain, nothing to merge |
> | brownfields | ✅ **NOT a duplicate.** Only one brownfield table is held in `indiana_app` (`in_si_refresh_brownfield_epa_in`, 1,483). The "3 programme tables" live in `energy.*` and were never clipped separately |
> | WARN pair | ⚠️ **GENUINE duplicate, still unresolved.** `in_si_refresh_warn_notices` and `in_si_state_warn_notices` both hold 1,220 rows sharing **1,104 of 1,178** company\|city\|date keys. A3 recorded a decision to keep the one with `notice_pdf_urls` (the `_state_` copy) — but that was a decision, not an action: both tables are still present and both are still read. See item 28 |

---

## ══ BACKLOG — the full queue, in order, as of the 2026-08-15 checkpoint ══

Phase A is COMPLETE. This is everything left to finish the tool. Ranked within each phase.

| # | item | phase | state | blocked by |
|---|---|---|---|---|
| 1 | D22 ECHO | B | ✅ **DONE 2026-08-16** — the REST county walk was arithmetically impossible (300/hr, 1,500/day quota vs ~25,000 requests at `responseset=5`), so **route 2, the bulk export**, was taken. 58,003 Indiana facilities, 100% located, 931+113 parcels admitted. See `MISSING_SIGNALS_FINDINGS.md` § D22 ACQUISITION RESULT | — |
| 1a | **recover IDEM's event dates** — 22,565 enforcement actions held with NO date (`document_published` is a Y/N flag); dates live on the per-case document pages | B/D | ready | — |
| 2 | SI date-keying: address → parcel | B | ✅ bridge done; objective met by 2a | — |
| 2a | **WIDEN `has_si_signal` beyond D5_vacancy** | B | ✅ **DONE 2026-08-16 — 847,410 → 9,383** non-residential, severity-gated, 92% dated. The blocker was THREE KEY NAMESPACES, not the flag definition | — |
| 2b | exclude `parcels_in/080500000047000018` (D85 whole-Earth polygon) from every spatial join | B | ✅ **DONE** in `build_si_signal_v2.py` and `build_d22_wiring.py`; fan-out measured at 1.008 to prove it. **Still to apply to any NEW spatial join** | — |
| 2e | **wire the last 3 unwired objects** — estate-census panel + "empty by defect" panel on Data | A-tail | ✅ **DONE 2026-08-16 — 199 of 199** | — |
| 2c | fix the `si_d12_indy_marion_code_enforcement` loader — its addresses lack a city suffix, so 747,122 rows match nothing | B | ready | — |
| 2d | geocode Indianapolis — the bridge holds only 2,713 resolved Indy addresses; this is the real ceiling | B/D | ready | — |
| 3 | abandoned-property registries beyond Indy/South Bend | B | **agent running** | — |
| 4 | wire the D5 split into `in_sites` (screener currently selects empty land) | B | ready | — |
| 5 | B5 `vw_county_dc_posture` 92/92 counter | B | ✅ **RETIRED 2026-08-16 — and the real finding is worse than the counter.** The view does not exist in `indiana_app` (404), so the 92/92 was a phantom. Underneath it: **`in_ordinances_dc` holds 4 rows** and `in_commission_posture` holds 1. County data-centre posture is **UNMEASURED**, not measured-and-suspect. A P4/P6 county-posture score cannot be built on 4 ordinances — see item 27 | — |
| 27 | **county ordinance corpus — 4 rows for 92 counties.** Municode/American Legal search was run once and never scaled. Needed before any county-posture score is credible | B/D | ready | — |
| 28 | **WARN pair still duplicated** — 1,104 of 1,178 shared keys across `in_si_refresh_warn_notices` and `in_si_state_warn_notices`. Pick one, waive the other with the measurement on the record | A-tail | ready, small | — |
| 29 | **Marion crosswalk ✅ DONE 2026-08-16 — 1.8% → 100%.** `sde_Parcel/MapServer/5` publishes `PARCEL_I` + `STATEPARCELNUMBER` for 347,049 parcels; 98.2% of its state pins exist in `in_sites`. D5_abandoned_building reach **168 → 7,147**, admitted **34 → 645**. The prior "Marion has no state key" was true of the tables we held, not of the world | B | ✅ | — |
| 30 | **place the remaining 198,754 unplaced signal addresses.** Routes measured 2026-08-16: Indy unit address points (`MapIndy/MapIndyProperty/0`, 157,018 with geometry) for the 747,122-row D12 corpus; Census Bureau batch geocoder (free, no key) statewide. This is the largest remaining coverage gain in the app | B/D | ready | — |
| 32 | **Back a credible address into the BUILDING when it will not join to a parcel** (operator suggestion 2026-08-16). Worth noting the existing bridge ALREADY does this for the rows it covers — its highest tier is literally `mat_si_address_location.build_id = in_sites.build_id`, i.e. address → USA Structures building → parcel, and that tier supplies 1,970 of the admitted parcels. The genuine gap is addresses **absent from `mat_si_address_location` altogether** (62.4% of signal addresses). For those, join the address to a USA Structures footprint directly, then the footprint to the parcel that contains it. Indy is being solved a better way (item 30 — the publisher's own address→parcel crosswalk, a published fact rather than a spatial inference); this route is for the other 91 counties | B/D | ready | — |
| 31 | ArcGIS `f=json` returns **Esri `rings`, not GeoJSON** — `ST_GEOGFROMGEOJSON` parsed 0 of 7,120. Re-pull with `f=geojson` if a geometry cross-check on Marion is wanted (the key crosswalk already places 100%, so this is verification, not coverage) | B | optional | — |
| 6 | **B1/D9/D18/D11/D27 — DLGF Gateway bulk owner data. ⭐ NOW THE HIGHEST-VALUE ITEM LEFT: one pull unblocks FIVE signals, not three.** `mat_parcel_attrs.parcel_owner` is NULL on all 3,553,381 Indiana parcels (re-measured 2026-08-16), and that single gap is what keeps D11 (983 dissolutions) and D27 (156 UCC lapses) at owner grain | B/D | ready | — |
| 7 | file the IRS ALS FOIA for D13 | D | **drafted, awaiting operator** | operator |
| 8 | B3 acreage disagreements: 41 shrunk (footprints>0) + 107 inflated >200% | B | needs a rule | operator |
| 9 | B4 the 7 unresolved Indianapolis colo facilities | B | needs address source | — |
| 10 | wire the 11 already-pulled-but-unwired Lane D columns | A-tail | ready, **cheapest coverage left** | — |
| 11 | fold staged D11/D21/D27 | A-tail | ✅ **DONE 2026-08-16.** D21 folded to parcel grain (377 admitted). **D11 + D27 CANNOT reach a parcel** — the address bridge matches 6 of 983 and 0 of 156, and these are business-registry addresses where a street match would often flag a registered agent's office. Wired at OWNER grain (`in_si_owner_signals`, 2,174 rows, 66/29 counties). **They join item 6, not item 10** | item 6 |
| 11a | **every registered object reaches a surface — 226 of 226**, measured by `scripts/audit_wiring_census.py` (`docs/WIRING_CENSUS.md`). The denominator MOVES on every build, so re-run it rather than quoting a past figure | A-tail | ✅ **DONE 2026-08-16** | — |
| 12 | recover `geometry_geojson` for brownfields (polygon, not location) | B | ready, it is a join | — |
| 13 | D4 tax delinquency (SRI pre-sale lists) | D | seasonal — July | calendar |
| 14 | A1 listings via an IEDC data request | D | **needs operator email** | operator |
| 15 | D23 surplus disposal (IDOA + land banks) | D | low value, watch-list | — |
| 16 | D10 state tax warrants — $600/yr INCite or $38/mo Doxpop | D | **procurement decision** | operator |
| 17 | D15 mechanics liens | D | **BLOCKED** — procurement, do not build | operator |
| 18 | C1 dossier v2 — the management deliverable | C | not started | Phase B |
| 19 | C2 itemised rate engine (four-proxy, 1.75× gate, CPS shape) | C | proxy only today | Phase B |
| 20 | C3 RTEP → bus drill-down join | C | table exists, join does not | — |
| 21 | C4 saved workspaces / shortlist v2 | C | not started | — |
| 22 | C5 PMTiles all-parcel rendering | C | **BLOCKED** on WSL/Docker install | operator |
| 23 | E1 honesty audit — 50 numbers traced to source + date | E | not started | Phases B/C |
| 24 | E2 refresh cadence scheduling | E | **deferred by operator** | operator |
| 25 | E3 national-baseline handover pack | E | not started | everything |
| 26 | E4 acceptance run against spec §13 | E | not started | everything |

**Operator decisions outstanding:** items 7, 8, 14, 16, 17, 22, 24.

### D22 is REQUIRED (operator) — the routes, if REST keeps throttling

ECHO's REST service refuses a statewide query (queryset limit, 127,266 rows) and rate-limits the
county walk with HTTP 429. It is not gated — no key, no account, no terms wall — so this is a
throughput problem, not a permission one, and there are four ways through. In preference order:

1. **Slow the county walk.** Raise the pause to 3–5 s and keep the bounded retry. 92 counties at
   ~3 s and a few pages each is roughly 20–40 minutes unattended. Cheapest, no new surface.
2. **ECHO's BULK CSV download files.** Lane F recorded an open bulk CSV directory alongside the
   REST service. A single state file avoids per-county paging entirely and is the sturdier
   long-term refresh path. **Try this before tuning the REST walk further.**
3. **`get_download` with `output=CSV`.** The same QID the REST call returns can be downloaded as
   CSV — the endpoint explicitly refuses JSON but accepts CSV/GEOJSOND. One request per county
   instead of N pages, so far fewer calls and far less 429 exposure.
4. **IDEM's own enforcement database** (`oe.idem.in.gov/idem_oe_order`) — public, 1995-present,
   all 92 counties, no registration. Not a substitute for ECHO's facility universe, but it is the
   Indiana-specific enforcement record and is worth holding either way.

None of these involves working around a gate; ECHO is open and simply slow.

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
