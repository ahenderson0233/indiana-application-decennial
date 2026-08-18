# BUS PARITY — measured against the vendor extract, 2026-08-18

> **Yardstick only.** Per the binding operator ruling, the vendor CSVs are read to *derive the same
> numbers from our own sources*. Nothing in this file is loaded into a table or a `data/` payload.
> Every figure below is measured from the two files and from our own warehouse — none is inherited
> from a previous session's notes.

---

## ⭐ FINDING 1 — the "we overshoot the vendor" puzzle was an INSTRUMENT problem, not a rule problem

The brief carried forward a comparison that looked alarming: our permissive variants put **88–98%**
of buses above zero against the vendor's **39.3%**, i.e. we appeared *more generous* than the paid
product, which is the opposite of the old MISO complaint.

**That comparison was measuring two different populations.**

| the vendor's 19,846 Indiana rows | rows | share |
|---|---:|---:|
| **MISO** (`DPP-2025-Cycle_SUM_D_ERIS-mitigated_Final`) | 17,006 | **86%** |
| **PJM** (`Final_2024 Series RTEP 2028 SUM_BD_02052026_TC2_PHII_Final`) | 2,754 | 14% |
| SERC (`MMWG_2030SUM_2025Series_Final`) | 86 | <1% |

The 39.3% is an **all-Indiana, 86%-MISO, tier-0 injection** figure. Our 88–98% is **PJM/AEP
withdrawal**. They are not comparable in either ISO, direction, or study case.

### The like-for-like PJM baseline, measured

| vendor PJM tier 0 | buses | >0 MW | median | mean |
|---|---:|---:|---:|---:|
| **Withdrawal** — *the data-centre question* | 297 | **279 (93.9%)** | **220.0 MW** | 319.3 MW |
| Injection | 297 | 85 (28.6%) | 0.0 MW | 18.3 MW |

**Against that, our case-23 rules bracket the vendor rather than overshooting it:**

| our rule, PJM withdrawal | buses >0 | vs vendor 93.9% |
|---|---:|---|
| raw MIN | 0.0% | far too strict |
| exclude pre-existing overloads | 88.0% | **just under** |
| + DFAX ≥ 5% | 96.8% | **just over** |

The vendor sits **between our two candidate rules**. That is a good position: it means the remaining
work is choosing the constraint filter, not rebuilding the method.

⚠ **A second population mismatch remains and must be fixed before any per-bus comparison.** The
vendor's PJM slice is **297 buses**, clipped to Indiana. Our harvest is **1,826 AEP buses** across
the entire AEP footprint (Ohio, West Virginia, Kentucky, Virginia, Michigan). `Owner='AEP'` in the
vendor file is **100% PJM** (2,448 of 2,448 rows), so the owner is right — the geography is not.
`in_pjm_bus_locations_candidate` carries `lat`/`lon` but **no state or county column**, so the clip
needs a spatial test, and `in_county_rollup` has no geometry. **That join is the next step.**

### Direction asymmetry — real, and unexplained

| direction | vendor PJM tier 0 | our closest rule |
|---|---:|---|
| Withdrawal | 93.9% | exclude-overloads (88.0%) / +DFAX (96.8%) |
| Injection | 28.6% | **raw MIN (22.3%)** |

Their injection behaves like our *strictest* rule while their withdrawal behaves like our *most
permissive* one. Either their tier 0 treats the two directions differently, or the constraint set
that binds differs by direction. **Do not tune one rule to split the difference** — that would be
fitting to an answer key, which G22 forbids. The binding-constraint-name comparison is the
diagnostic that settles it.

---

## ⭐ FINDING 2 — MISO parity is NOT reachable, and the reason is precisely the CEII-gated input

Applying the **identical rule ladder** to `in_miso_facility_detail` (40,007 rows, 642 POIs,
`DPP-2021-Cycle`, 26.3% of rows already overloaded, average pre-loading **79.0%**):

| rule | POIs > 0 MW | median |
|---|---:|---:|
| raw MIN (all facilities) | **1 of 642 — 0.2%** | 0.0 |
| exclude pre-existing overloads | **642 of 642 — 100.0%** | 51.5 MW |
| + DFAX ≥ 5% | 642 of 642 — 100.0% | 52.0 MW |
| **vendor, DPP-2025 ERIS-mitigated** | **40.8%** | 0.0 |

**Our two rules do not miss the vendor — they bracket it, and enormously.** The whole distance
between 0.2% and 100% is the treatment of pre-existing overloads, and the vendor sits at 40.8%
because **their case has some of those overloads MITIGATED and ours has none**:

- Including every overload assumes **nothing** gets mitigated → 0.2%.
- Excluding every overload assumes **everything** gets mitigated → 100%.
- ERIS-mitigated DPP-2025 is the measured middle → 40.8%.

**We cannot know WHICH facilities MISO mitigated without the DPP-2025 study, and four independent
sweeps established that study has no public route** (CartoVista rows 403 under the correct verb,
giqueue structurally DPP-2021, MISO's own API exposing only the queue endpoint, and FERC ER24-2046
establishing the data is owed publicly only as interactive query responses). The gap is therefore
**a missing input, not a defective method** — and it is the one input we are structurally barred
from obtaining.

⭐ **This is a defensible position rather than an embarrassment**, and it is the opposite of the
inherited worry that "our MISO numbers are stale". Our method reproduces the vendor's *shape* —
median 0.0 at raw MIN, matching theirs exactly — and the level difference is attributable to a named
and documented cause.

---

## ⭐ FINDING 3 — the real blocker on PJM parity is BUS GEOLOCATION, not the headroom rule

The Indiana clip was attempted and produced a number that looked wrong, which is a claim about the
instrument before it is a claim about the data. It was the instrument.

| our 1,826 case-23 AEP buses | count | share |
|---|---:|---:|
| `location_method = 'none'` — **no coordinates at all** | **1,225** | **67%** |
| never appear in `in_pjm_bus_locations_candidate` at all | ~374 | 20% |
| `substation_match_exact`, confidence high | 91 | 5% |
| `substation_match_prefix`, confidence med | 90 | 5% |
| `substation_match_exact`, confidence med | 33 | 2% |
| `rtep_bridge`, confidence med | 13 | <1% |
| **total actually placeable** | **~227** | **12%** |

Of those 227, the states they fall in are OH 64, **IN 42**, VA 35, WV 31, MI 24, KY 13, WI 5, PA 4,
TN 3, IL 3 — a plausible AEP footprint, which is evidence the placements we DO have are sound.

⭐ **The arithmetic says the buses are there and we simply cannot see them.** 42 of 227 placed buses
are in Indiana — **18.5%**. Applied to all 1,826, that projects **~338 Indiana AEP buses**, against
the vendor's ~264 AEP-owned Indiana buses. The populations are compatible. **We are not missing
buses; we are missing coordinates for 88% of them.**

**This reorders the work.** Tuning the constraint filter cannot produce a per-bus Indiana comparison
while seven out of eight buses have nowhere to sit. And unlike the MISO mitigation list, **this gap
is closable from public sources** — it is a substation-name matching problem against data we already
hold, not a CEII wall. `in_substations_dedup` and the RTEP bridge already place 227; the same
technique applied harder is the highest-value next move on the PJM side.

### ⭐ 3b — HOW the vendor placed them, and why the cheap fix does not work

Their file answers the question "if Orennia has coordinates, why can't we?" — and the answer is
reassuring: **they mostly do not have authoritative coordinates either.**

| their `Location Source` | rows | share |
|---|---:|---:|
| **`Estimated`** | 13,824 | **70%** |
| `ISO` | 5,626 | 28% |
| `Interpolated` | 384 | 2% |

**Only 28% come from the ISO.** The rest are derived — and the derivation is visible in the data:
bus `PJM_242865` and bus `PJM_243208` are both named `05JEFRSO` and carry **byte-identical
coordinates**. They match the bus NAME to a substation and reuse one coordinate for every bus there.
That is precisely our `substation_match_exact` method. Their advantage is coverage, not access.

⚠ **But the cheap version of that does not work, and this was measured rather than assumed.**
Our `bus_label` already contains the same name in the same form — `05AMOS 765 kV (242508)` parses
cleanly to `05AMOS` on **all 1,826 buses, 0 unparseable**. Matching those against
`in_substations_dedup.substation_name` (with and without the two-digit area prefix) yields:

| | buses |
|---|---:|
| placed today | 227 |
| label matches an Indiana substation name exactly | 35 |
| **newly placeable this way** | **13** |

Thirteen. The reason is legible in the names themselves: `05GRNGST`, `05CLYTR1`, `05BRADL1`,
`05CHATFLD_BP` are **PJM's 8-character internal abbreviations**, and an abbreviation does not
exact-match a full substation name. Closing this needs **abbreviation expansion or fuzzy matching
with a confidence gate**, which is real work with a real false-positive risk — placing a bus at the
wrong substation is worse than leaving it unplaced, because a wrong coordinate silently pollutes
every distance and every county rollup downstream. It is not a join away.

**Scoped honestly, this is a half-day task, not a one-hour one**, and it is the single highest-value
item on the PJM side because everything per-bus is behind it.

### ⭐ 3c — THE JOIN KEY EXISTS, and the cutoff rule is DECODED, but parity is NOT yet reached

**No fuzzy matching is needed to identify the Indiana buses.** Their `Bus ID` is `PJM_242865` and our
`bus_number` is `242865`. Stripping the prefix joins **282 of their 297 PJM buses (94.9%)** to our
harvest on an exact key. (My earlier "0 overlap" was a bug: the CSV has **two columns both named
`Bus ID`**, so `DictReader` silently kept the second one. Read that file positionally.)

**Their tier-0 filter rule is decoded, and it is a perfect 1:1:**

| `Shift Factor Cutoff Ratio` | `Existing Overload Flag` | rows |
|---|---|---:|
| **0.05** | false | 339 |
| **0.20** | true | 255 |

The cutoff is **not** direction-based, it is **overload-based**: a bus with no pre-existing overload
is evaluated at a 5% shift-factor floor, an already-overloaded bus at 20%. This also explains the
direction asymmetry with no need for a second rule — withdrawal buses are 94% NOT overloaded
(279/297) while injection buses are 80% overloaded (237/297). **One rule, two populations.**

⚠ **Our `dfax` is a FRACTION (min 0.02, median 0.043, max 1.0), not a percentage.** An earlier rule
written as `ABS(dfax) >= 5` matched zero rows and **silently dropped out of the comparison** rather
than erroring — the same partial-enumeration failure mode as the `[:12]` clip. **60% of our constraint
rows sit below their 0.05 floor**, and those low-shift-factor rows dominate the MIN, which is why our
medians were an order of magnitude low.

**Applying their decoded rule still does NOT reproduce their numbers:**

| | vendor | ours, their rule | exact (<1 MW) | within 10% |
|---|---:|---:|---:|---:|
| Withdrawal (n=176) | 96.8% >0, median 227.5 | 58.2% >0, median 99.5 | **5.1%** | 13.1% |
| Injection (n=271) | 28.8% >0, median 0.0 | 64.4% >0, median 100.0 | **27.7%** | 31.4% |

⛔ **The percentage-above-zero agreement reported earlier was COINCIDENTAL and must not be read as
parity.** At the aggregate level `dfax>=0.20` puts withdrawal at 93.2% against their 93.9% — but
per bus the median error is still ~103 MW. Two distributions can share a shape and disagree on almost
every row.

### The actual blocker: WE ARE NOT BINDING ON THE SAME FACILITIES

**Binding-constraint name agreement is 6% on withdrawal and 0% on injection**, and the overload flag
agrees on only 3.2% of withdrawal buses. No filter over our constraint set can reproduce a MIN taken
over a *different* constraint set. Two candidate causes, both testable and neither yet tested:

1. **`desired_mw = 100` is OUR request size.** Headroom per constraint is request-invariant (G7b),
   but the **set of constraints QueueScope returns is not necessarily** — their cost file carries a
   `Proxy Interconnection Capacity` column, implying a different probe size.
2. **`Local Transfer Capacity` caps their answer and we do not harvest it at all.** It is populated
   on all 594 tier-0 rows (median 392 MW), and on **55 of them the reported capacity EQUALS it
   exactly** — the no-binding-constraint case. We have no equivalent column.

**Until the constraint sets agree, tuning filters is fitting to an answer key.** The next test is to
re-harvest a small sample of buses at a different `desired_mw` and see whether the returned
constraint set moves toward theirs.

### ⭐ PLOTTING THE BUSES WITHOUT THEM — the post-subscription path

The subscription lapses late 2027 and their data cannot remain in the tools. The placement problem is
nonetheless solvable **using them as a yardstick now and keeping only what we derive**:

- Their coordinates are **70% `Estimated`** — derived by substation-name match, the same technique we
  already use. There is no privileged coordinate source to lose.
- Their 282 joinable buses are therefore a **labelled validation set**: build our own
  bus-name → substation matcher, score it against those 282 known-good placements, and tune until it
  is accurate.
- **What persists is the MATCHER and a crosswalk whose coordinates come from `in_substations_dedup`
  (HIFLD/OSM), not from them.** Nothing of theirs ships or remains. That is squarely the permitted
  yardstick use, and it is the one window in which we have ground truth to calibrate against.

**Do this while the subscription is live.** After it lapses we would be building the same matcher with
no way to score it.

### ⭐ 3d — THE MATCHER, BUILT AND SCORED (scripts/score_bus_substation_matcher.py)

Scored against the 282 vendor-placed buses as a labelled truth set. **Their coordinates score our
matcher; the coordinates it OUTPUTS come from our own substation tables.**

**First run used `in_substations_dedup` (2,077 Indiana rows) and that was the wrong universe** — AEP
spans OH/WV/VA/KY/MI, so most buses had no candidate by construction. Re-scored against
`energy.mat_grid_substations` clipped to the 12 AEP-footprint states (29,798 substations):

| strategy | matched of 282 | ambiguous | median err | ≤1 mi | coverage of all 1,826 |
|---|---:|---:|---:|---:|---:|
| exact name | 39 (13.8%) | 14 | 0.06 mi | 56% | **8.6%** (was 1.9%) |
| consonant skeleton | 55 (19.5%) | 23 | 0.75 mi | 53% | **12.7%** (was 2.8%) |
| 5-char prefix | 141 (50.0%) | 88 | 1.88 mi | 49% | **40.3%** (was 10.5%) |

⭐ **Where a name matches cleanly the placement is essentially exact** — median 0.06 mi on exact
match, i.e. the same physical point. The matcher's problem is not accuracy, it is **coverage and
ambiguity**: `prefix5` reaches 40% of buses but 88 of its 141 scoreable matches are ambiguous, and
precision falls to 49% within a mile.

**The next lever is voltage, and we already hold it on both sides.** Our harvest carries `bus_kv`
(STRING) and the substation tables carry `max_kv`/`min_kv` (FLOAT). A name+voltage match should
collapse most of those 88 ambiguities — `05CLYTR1 138 kV` cannot be a 345 kV substation. County is a
second discriminator once a bus has any provisional placement.

⛔ **Do not ship `prefix5` unguarded.** At 49% within a mile it would place half the buses at the
wrong substation, and a wrong coordinate silently corrupts every distance, every county rollup and
every screener filter downstream. **Unplaced is honest; misplaced is not.** Ship exact+skeleton
(precise, ~13% coverage) and gate prefix matches behind a voltage agreement test.

### ⚠ 3e — THE MATCHER GOT WORSE WHEN I "IMPROVED" IT, and the reason is the useful part

Re-scored against a far larger truth set — the **1,731 vendor-placed MISO buses** now in
`in_bus_headroom_miso_vendor`, alongside PJM's 297.

**Reading the MISO names revealed three real parsing traps**, none of which are guesses:

| form | what it is |
|---|---|
| `07VIC161`, `07APOLLO161` | trailing digits are the **kV**, not part of the name |
| `07SUL_TP`, `07RHILTP`, `07LYLESTATN` | `TP`/`TAP` = tap, `STATN` = station — **facility markers, not places** |
| `O7RATTS161` | begins with the **letter O, not a zero** — a typo in the publisher's own data |

The normaliser now handles all three (`07VIC161` → `VIC`, `O7RATTS161` → `RATTS`,
`07SUL_TP` → `SUL`). **And the match got measurably WORSE:**

| strategy | before parsing fix | after |
|---|---|---|
| exact | 6.0% matched, median **1.20 mi** | 2.3% matched, median **147 mi** |
| skeleton | 10.9%, median 120 mi | 6.5%, median 184 mi |
| prefix5 | 18.5%, median 99 mi | 10.7%, median 153 mi |

⭐ **A median error of 100-180 MILES is not a near-miss, it is the wrong state.** And better parsing
made it worse for a reason that should have been obvious in advance: **shorter, cleaner names match
MORE things, not better things.** `VIC` collides with Victoria, Vicksburg and Victor across a
12-state candidate pool of 29,798 substations. The voltage gate did not rescue it either — it
removed a few candidates and moved nothing.

**The missing ingredient is not a better string algorithm, it is a GEOGRAPHIC PRIOR**, and we
already hold one that is entirely ours: **the two-digit area prefix encodes region.** Every `07`
bus in the truth set sits in southwest Indiana — Gibson, Pike, Knox, Spencer, Sullivan, Dubois,
Harrison, Orange — and `05` is the AEP footprint. That is in OUR bus labels, not the vendor's.

**The design that should work, in order:**
1. Learn `area prefix → region` from the buses we can already place with high confidence.
2. Constrain candidates to that region **before** any name comparison.
3. Only then match on name, with the voltage gate as a tiebreak among survivors.
4. Ship nothing below a measured precision bar. **Unplaced is honest; misplaced is not** — a bus at
   the wrong substation silently corrupts every distance, county rollup and screener filter.

⚠ **Do not read the PJM result as transferable.** PJM exact matches scored a median of 0.06 mi
because PJM bus names ARE substation names. MISO's are abbreviations of them. **The two ISOs need
the same pipeline but not the same confidence thresholds**, and a single blended accuracy figure
across both would hide that.

### ⭐⭐ 3f — WE DO NOT OWN A PLACEMENT METHODOLOGY FOR EITHER ISO. We mirror one and lack the other.

⛔ **OPERATOR CORRECTION, 2026-08-18, and it corrects MY framing:** *"these are NOT our
coordinates, and we will have to determine and define a placement methodology."* An earlier draft of
this section called MISO placement "solved". **It is not solved. It is BORROWED**, and the
distinction is the whole point.

**What is actually true about MISO.** `in_bus_headroom_miso` carries real coordinates for **9,608 of
11,155 buses (86%)**, sourced from `in_miso_poi_identity` — which is **MISO's OWN published POI
location data**. Checked against the vendor on the same `bus_number`:

| | |
|---|---:|
| buses placed by BOTH | **570** |
| **median disagreement** | **0.0 mi** |
| same point to within 0.1 mi | 512 (**89.8%**) |
| more than 25 mi apart | **1** |

⭐ **The agreement proves SHARED PROVENANCE, not competence.** Their file shows **571 MISO buses
with `Location Source = 'ISO'`** against our 570 matches at a 0.0 mi median. We are not
independently arriving at the same answer — **we are both copying MISO's published coordinates.**
Reading that as "our method works" would be measuring a mirror and calling it a measurement.

⚠ **So MISO is a DEPENDENCY, not a capability.** If MISO changes the publication, restricts it, or
retires the POI layer, we are in exactly the position PJM is in now — with the added risk that the
failure would be silent, because the table would simply stop refreshing rather than error.

**And PJM shows what that position looks like: nobody has coordinates, including the vendor.**

| `Location Source`, distinct buses | PJM (298) | MISO (1,731) |
|---|---:|---:|
| **`ISO`** | **0 — none** | 571 (33.0%) |
| `Estimated` | **274 (91.9%)** | 1,138 (65.7%) |
| `Breaker Branch Coincidence` | 10 | — |
| `Queue Generator Coincidence` | 8 | 3 |
| `Interpolated` / blank | 6 | 19 |

**PJM publishes no bus coordinates to anyone.** The vendor estimates 92% of its PJM buses, so our
227 substation-matched buses are **the same class of artefact as their 274 estimates** — not an
inferior stand-in for a feed we failed to find. Parity on PJM locations is a question of
**estimation quality, not acquisition.**

### THE METHODOLOGY WE HAVE TO DEFINE — required for both ISOs, urgent for neither today

It must be **ours**: reproducible from sources we control, scored against something, and carrying a
per-bus confidence we are willing to publish. Ordered by how much each step can be trusted:

1. **Exact joins first.** `Queue Generator Coincidence` is a JOIN, not a guess — a queue project
   interconnects at a named bus, so the project's coordinates place it. **We already hold the PJM
   queue** (`in_queue_*`, rendered as the `pjm-queue` layer). Highest confidence, build first.
2. **Topology second.** `Breaker Branch Coincidence` — buses joined by a breaker are the same
   physical station, so one placed bus places its neighbours, and **each placement seeds the next**.
   Our harvest's `transmission_facility` carries from/to bus identifiers on every constraint row,
   which is the graph needed to walk it.
3. **String similarity LAST, and gated** — with the area-prefix geographic prior from 3e, because
   without a regional constraint name matching returns the wrong state (median 100-180 mi).
4. **Publish a confidence per bus and refuse to place below a threshold.** **Unplaced is honest;
   misplaced is not** — a wrong coordinate silently corrupts every distance, county rollup and
   screener filter downstream, and unlike a missing one it never announces itself.

⭐ **Do this while the subscription is live.** The vendor's 2,029 placed buses are the only
labelled truth set we will ever have to score steps 1-3 against. After it lapses we would be
building the same methodology blind.

## RECOMMENDATION

| region | verdict | what to ship |
|---|---|---|
| **PJM** | **Parity is reachable and nearly there.** Vendor 93.9% sits between our 88.0% and 96.8%. | **Our own numbers.** Finish the Indiana spatial clip, then settle the constraint filter with the binding-constraint-name diagnostic. |
| **MISO** | **Parity is NOT reachable** — the differentiator is the mitigation list, which is CEII. | Either ship the **bracket** (0.2%–100%, honestly labelled as a mitigation-dependent range), or use the **vendor value as a labelled proxy** per the operator's 2026-08-18 ruling. |

⚠ **If the vendor proxy is used for MISO**, it must be isolated so it can be removed in one commit
when a public DPP-2025 route appears: its own table, its own `provenance_class` value, never blended
into a column that also carries publicly-derived numbers, and rendered with its source named on the
face of the surface rather than in a footnote. **Confirm the licence permits redistribution in a
client-facing product before it ships** — paying for a data product licenses use, which is not
automatically the same as embedding derived values in something shown outside the company.

---

## WHAT IS NOT YET DONE

1. **The Indiana spatial clip of our 1,826 AEP buses** — blocking any per-bus comparison.
2. **The binding-constraint-name diagnostic** — compare our `transmission_facility` at the argmin
   against the vendor's `Primary Limiting Constraint` for the same bus. This is the column that
   reveals which constraint class their tier 0 keeps and we drop, and it settles the direction
   asymmetry.
3. **`in_bus_capacity_tier0` still holds STALE case-4 PJM** and must be rebuilt on case 23.
4. Their cost file (331,383 rows) carries **Min/Max Lead Time (Years)** and per-upgrade costs. We
   hold neither for PJM. We *do* hold the MISO equivalent — `in_miso_dpp2025_ph1_project_costs`,
   202 projects, $29.52B — from MISO's own open find→CDN route.
