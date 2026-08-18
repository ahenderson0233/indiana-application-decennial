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
