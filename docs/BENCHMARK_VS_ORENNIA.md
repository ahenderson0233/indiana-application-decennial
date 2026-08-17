# Benchmark — our grid assets vs a licensed vendor extract

> ⛔ **The vendor data in this comparison is a YARDSTICK ONLY. It is never used in the tool.**
> Operator, 2026-08-17: *"we should never use Orennia data within our tools, but we should use
> it as a comparison measurement to gain how close we are to the truth, and understand how we
> should calculate/measure our assets within our tool."* This report writes nothing to
> BigQuery and nothing to `data/` — by design there is no path from here to a rendered page.

Generated 2026-08-17 15:18 UTC by `scripts/benchmark_vs_orennia.py`. Vendor extract dated 2026-06-23.

## ⚠ 0. READ THIS BEFORE TRUSTING ANY AGREEMENT FIGURE BELOW

**2,925 of 2,925 matches sit at a distance of 0.0 m** (maximum observed: 0.1 m). That is not two sources agreeing — that is **one source compared with itself**. Their file records `Location Source: Public Source`; ours is a HIFLD+OSM union. Both descend from the same public asset data.

**Consequence: this comparison does NOT independently validate our substation locations or voltages.** A 99%+ voltage agreement between two copies of one source is arithmetic, not corroboration, and quoting it as accuracy would be the two-instrument fallacy in reverse — agreement is only evidence when the instruments are actually independent.

What the vendor extract IS independent on, and therefore worth benchmarking against, is its **derived analytics** — interconnection capacity by direction, upgrade tiers, lead times, cost and risk level. Those are modelled outputs we do not hold and cannot trivially reproduce. The asset layers are not.

### So the question this report actually answers is COMPLETENESS, not accuracy

Operator, 2026-08-17: *"Orennia uses some of the same sources as we use to derive their tables, so it would make sense if much of it is the same — however, we should strive to have AT LEAST the same completeness as them for our application, so we may need to rescope how close we are to complete visibility based on their numbers."* Agreed, and that is the right frame: shared provenance makes value-agreement uninformative and makes **coverage** the real test.

**Substation completeness, measured footprint-aware:**

| | count | share of theirs |
|---|---:|---:|
| their Indiana substations | 2,751 | 100% |
| no POINT of ours within 1000 m | 538 | 19.6% |
| …but falling in/near one of our 933 footprint-only polygons | 496 | |
| **genuinely absent from our data** | **42** | **1.5%** |

**We hold 98.5% of their substation coverage.** The naive figure is 538 missing, and it is wrong: 933 of our substations carry a footprint POLYGON instead of a point (they are the OSM-only contributions), and excluding them from a match makes our coverage look a fifth worse than it is. Any completeness claim that ignores the footprint rows is measuring our schema, not our data.

The genuinely-absent ones skew small: <100 kV 25, 100-344 kV 5, unknown 11, >=345 kV 1 by voltage. For a 300 MW campus a sub-100 kV omission is close to irrelevant, so **the high-voltage absences are the only ones worth chasing** — everything else is noise against this application's purpose.

## 1. Coverage — do we hold the same substations?

| | count |
|---|---:|
| their Indiana substations (with coordinates) | 2,751 |
| ours (with coordinates) | 2,925 |
| **matched within 1000 m** | **2,925** |
| ours with no counterpart | 0 (0.0%) |
| theirs with no counterpart | 674 (24.5%) |

Matching requires **proximity**, not name similarity. Name-only matching is what fabricated eight bad data-centre matches in `CLOUDSCENE_GAP.md` (F7), including two different companies matched because they shared a city.

### 🔴 THE REAL FINDING — our substation table holds duplicates

2,925 of our located rows collapse onto **2,077 distinct points** — 661 of those points are claimed by more than one of our rows, up to 3 rows on a single coordinate.

Measured directly against `in_substations`: **3,858 rows, 933 footprint-only, and only 2,077 distinct coordinates among the 2,925 located ones — so 848 located rows share a coordinate with another row.** They carry the same name, the same `sources` value and the same voltage; `ROCKPORT STATION` appears three times at one point.

**This is a defect in our merge, not in theirs, and it was found by accident.** Impact: the map draws ~848 redundant markers, and any COUNT of substations overstates by about 41%. Nearest-substation DISTANCE is unaffected — the nearest of three identical points is still the nearest — so the screener's distances are correct while its counts are not. De-duplicate on coordinate + name before any figure of the form "N substations" is shown again.

## 2. Voltage — where we both hold a substation, do we agree?

**This is the G13 audit list.** `in_substations.max_kv` already feeds the screener's "substation of at least N kV" filter, so a wrong voltage is a wrong screening result today.

| | count |
|---|---:|
| matched pairs where both state a voltage | 2,089 |
| **agree (within 0.5 kV)** | **2,081 (99.6%)** |
| **disagree** | **8 (0.4%)** |
| we hold no voltage, they do | 657 |
| they hold no voltage, we do | 0 |

### Largest disagreements — start here

| substation | county | ours (kV) | theirs (kV) | gap | distance |
|---|---|---:|---:|---:|---:|
| REYNOLDS | WHITE | 345 | 765 | 420 | 0 m |
| UNKNOWN122724 | LAPORTE | 138 | 345 | 207 | 0 m |
| UNKNOWN122724 | LAPORTE | 138 | 345 | 207 | 0 m |
| UNKNOWN125389 | FLOYD | 138 | 230 | 92 | 0 m |
| UNKNOWN125389 | FLOYD | 138 | 230 | 92 | 0 m |
| UNKNOWN124478 | HENRY | 69 | 138 | 69 | 0 m |
| UNKNOWN124056 | WAYNE | 69 | 138 | 69 | 0 m |
| UNKNOWN124903 | RIPLEY | 69 | 115 | 46 | 0 m |

⚠ A disagreement does not automatically mean **we** are wrong — it means at least one of us is, and it is not a tie to break by preference (rule 12). Resolve each against the publisher, not against whichever number is more convenient.

## 3. How they band voltage — a modelling reference, not data to copy

Their transmission file carries both a numeric `Voltage (kV)` and a categorical `Voltage Class`. The banding is worth knowing because G13 must colour lines by class, and **an unknown voltage needs its own band rather than the bottom of the scale**:

| their voltage class | lines (national) |
|---|---:|
| 100-161 | 47,988 |
| UNDER 100 | 39,393 |
| 220-287 | 9,508 |
| NOT AVAILABLE | 5,253 |
| 345 | 3,453 |
| 500 | 1,207 |
| 735 AND ABOVE | 289 |
| DC | 35 |
| (blank) | 2 |

Note `NOT AVAILABLE` on 5,253 lines — they carry unknown voltage as an explicit category rather than as zero or null-coerced-to-low. Ours must do the same.

## What to do with this

1. Work the disagreement table above as the **G13 voltage audit**, resolving each at the publisher.
2. Treat their class banding as a **design reference** for our own colour scale.
3. **Do not import any of it.** If a figure from this file ever appears on a page, that is a defect, not a shortcut.
