# SI date keying — can the dated address rows reach a parcel?

**Measured 2026-08-15.** Build script: `scripts/build_si_date_keying.py`. All writes to
`energy-platfrom.indiana_app`; `energy.*` read-only throughout. Total scanned 2.99 GB.

**Answer in one line:** yes, a bridge exists and it is `energy.mat_si_address_location` — but it
carries **20.5% of the distinct addresses and 7.4% of the rows**, and it moves the parcel layer
from 2,985 dated parcels to 3,886. The ceiling is upstream geocode coverage, not the join, and
**not the normalisation**. The single largest signal block, `D12_code_violation` (747,122 rows),
matches **zero**, for a reason that is a loader defect and is documented below.

---

## 1. The bridge that exists

`energy.mat_si_address_location` — 5,549,105 rows nationally, **95,967 Indiana**.

| column | what it gives us |
|---|---|
| `address_norm` | **the same string the signal rows carry** |
| `build_id` | structure identity — joins to `in_sites.build_id` |
| `lat` / `lon` / `geog` | rooftop point — joins to `in_sites.parcel_geog` |
| `location_method` | `building_footprint_geocode` or `unresolved` |
| `precision_tier` | `rooftop_geocode` or `none` |
| `is_geocoded`, `usable_for_distance`, `match_count` | quality/confidence columns |

**It does not carry a parcel key.** It is half a bridge. The second half is `in_sites`, which
carries both `build_id` and `parcel_geog`.

Indiana splits exactly two ways, with no middle ground:

| location_method | precision_tier | rows | build_id | lat/lon |
|---|---|---:|---:|---:|
| `building_footprint_geocode` | `rooftop_geocode` | 51,821 | 51,821 | 51,821 |
| `unresolved` | `none` | 44,146 | 0 | 0 |

### No normalisation was written, and that is a measured claim, not a promise

The standing rule is that a hand-rolled regex chain plus a self-reported match rate is worse
than no bridge. So the question asked was *who already normalised these*, not *how do I*.

`in_si_signals.address_norm` and `mat_si_address_location.address_norm` come from the same
upstream normaliser. **Proof:** exact string equality yields 94,010 addresses; `UPPER(TRIM())`
equality yields 94,010. **Delta = 0.** There is no casing or whitespace drift to "fix" — which
is precisely the evidence that no new normalisation belongs anywhere in this build.

### Alternatives checked and rejected

| candidate | verdict |
|---|---|
| `energy.mat_si_rooftop_geocode` | **Worse.** Its only 5,880 Indiana rows are all `method_version='v1_INVALID_20260804_state_centroid_D37'` — state centroids. The platform's own `vw_si_rooftop_geocode_valid` filters to `v2_stem_backref_repaired_20260804`, so **Indiana has zero valid rows in it.** |
| `energy.mat_si_building_in_parcel` | Only 5,222 Indiana addresses, and it carries `parcel_source` **without** `parcel_key` — it cannot complete a parcel join at all. |
| `energy.mat_parcel_key_index` | Parcel-key *variant* index (`parcel_key_norm`). Nothing to do with addresses. |
| `energy.mat_si_date_resolved` + `vw_si_signals_dated` | Real, and it already back-fills dates onto signal rows — but via `join_key_addr`, i.e. it resolves *dates for addresses*, not *parcels for addresses*. Orthogonal to this problem. |

---

## 2. The instrument check that mattered

The spatial route matched **100.0%** on its first run — 51,821 of 51,821 addresses, at a
**fan-out of 2.0**. A perfect result is a claim about the instrument, so the instrument was
checked before the number was believed.

`in_sites` contains one parcel, **`parcels_in / 080500000047000018`**, whose polygon measures
**196,936,707 sq miles** — the surface area of the Earth, an inverted ring — and whose
`structure_count` reads **3,377,472**. It contains every point on the globe, so it silently
caught all 51,821 addresses. This is **DISCOVERIES D85, still live and unrepaired upstream.**

Excluding that single parcel:

| spatial join | matched addresses | join rows | fan-out |
|---|---:|---:|---:|
| as-is | 51,821 (100.0%) | 103,433 | 2.000 |
| **D85 globe parcel excluded** | **50,865 (98.2%)** | **51,612** | **1.015** |

Every spatial predicate in the build carries the exclusion. **It must stay until D85 is fixed at
source.** Any other spatial work against `in_sites` has the same exposure.

---

## 3. Measured yield

Denominator, measured directly (`keying IN ('address_norm','address')`): **861,304 rows**,
**858,865 dated**, **250,063 distinct `address_norm`**. (The brief quoted 861,551 / 250,016;
the small delta is denominator definition, not disagreement.)

### The ceiling — three sequential losses

| stage | addresses | % of 250,063 |
|---|---:|---:|
| distinct address_norm in signal rows | 250,063 | 100.0% |
| present in `mat_si_address_location` at all | 94,010 | 37.6% |
| **and resolved there** (has build_id + lat/lon) | **51,821** | **20.7%** |
| **and reaching a parcel** | **51,309** | **20.5%** |

**62.4% of the addresses are simply not in the geocode table.** No matcher tuning can reach them.

### Two routes to the parcel, cross-checked

| route | addresses matched |
|---|---:|
| `build_id` equality → `in_sites.build_id` | 41,927 |
| `ST_CONTAINS(in_sites.parcel_geog, point)` | 50,865 |
| union | **51,309** |
| both routes fired | 41,483 |
| **both fired AND agreed on the same parcel** | **34,676 (83.6%)** |

The 16.4% disagreement is carried, not hidden: it separates confidence tier 1 from tier 2.

### Overall yield

| measure | matched | source | rate |
|---|---:|---:|---:|
| address-keyed rows | 63,329 | 861,304 | **7.4%** |
| distinct addresses | 51,309 | 250,063 | **20.5%** |
| rows within 3 years | 11,791 | 37,601 | **31.4%** |

Row yield (7.4%) is far below address yield (20.5%) **entirely because of D12** — see §4.

### By signal

| signal | rows | matched | % | addresses | matched | % | 3y rows | matched |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `D12_code_violation` | 747,122 | **0** | **0.0%** | 156,053 | **0** | **0.0%** | 18,059 | 0 |
| `D2_foreclosure` | 62,447 | 40,330 | 64.6% | 45,836 | 29,595 | 64.6% | 8,402 | 6,173 |
| `D16_structure_fire` | 28,555 | 15,423 | 54.0% | 27,382 | 14,694 | 53.7% | 9,455 | 5,211 |
| `D1_tax_sale` | 17,601 | 4,725 | 26.8% | 15,705 | 4,480 | 28.5% | 1,484 | 278 |
| `D14_sba_chargeoff` | 3,774 | 2,056 | 54.5% | 3,523 | 1,909 | 54.2% | 179 | 113 |
| `D7_brownfield` | 1,371 | 555 | 40.5% | 1,371 | 555 | 40.5% | 0 | 0 |
| `D20_loan_maturity` | 407 | 222 | 54.5% | 401 | 218 | 54.4% | 1 | 1 |
| `D24_plant_delisting` | 13 | 10 | 76.9% | 13 | 10 | 76.9% | 13 | 10 |
| `A2_gov_surplus` | 8 | 6 | 75.0% | 8 | 6 | 75.0% | 5 | 4 |
| `D19_warn` | 4 | 2 | 50.0% | 4 | 2 | 50.0% | 1 | 1 |
| `D3_seized_auction` | 2 | 0 | 0.0% | 2 | 0 | 0.0% | 2 | 0 |

Excluding D12, the address-keyed block matches **63,329 / 114,182 rows = 55.5%**.

---

## 4. Why `D12_code_violation` is exactly zero

A measured zero is a claim about the instrument. The instrument was checked, and the zero is real
— but its cause is **not** the join, the geocode, or the normalisation.

Of D12's 156,053 distinct addresses, **0 are even *present* in `mat_si_address_location`** — not
"present but unresolved". Zero. That is a structural mismatch, and the shapes show it:

```
D12 (si_d12_indy_marion_code_enforcement) :  '<NUMBER> <STREET> <TYPE>'
every other source, and the bridge        :  '<NUMBER> <STREET> <TYPE> <CITY>'
```

The project's `address_norm` convention **appends the city**. The D12 loader emits it without
one, so a D12 key can never equal a bridge key. **This is a defect in the D12 ingest, not in the
bridge.** Per the standing rule, no compensating normalisation was written here — the fix belongs
in the loader that produced `si_d12_indy_marion_code_enforcement`.

### But fixing D12's loader would recover almost nothing, and that is the more important finding

A deliberately generous **diagnostic** (prefix containment: does any bridge key start with the
D12 string plus a space?) was run purely to size the prize. **It is not shipped and is not built
into any table.**

| D12 distinct addresses | 156,053 |
|---|---:|
| with ≥1 prefix hit in the bridge | **1,593 (1.0%)** |
| unambiguous (exactly one city) | 1,552 |
| ambiguous (>1 city) | 41 |

Only **1.0%**. The binding constraint is not the missing city suffix — it is that
**the geocode barely covers Indianapolis**:

| `mat_si_address_location`, Indiana | count |
|---|---:|
| total rows | 95,967 |
| `address_norm` ending `INDIANAPOLIS` | 3,805 |
| …and resolved | **2,713** |

D12 is 747,211 rows of Indianapolis/Marion County code enforcement, against **2,713 resolved
Indianapolis addresses** in the bridge. Repairing the D12 loader is still correct and should be
done, but it is worth ~1,593 addresses. **The real prize is geocoding Indianapolis.**

---

## 5. What was built

Both tables registered in `indiana_app._registry` in the same run.

### `indiana_app.in_si_address_parcel_bridge` — 51,309 rows

One row per `address_norm` (grain asserted in the build, not assumed), resolving to 45,822
distinct parcels. Clustered by `address_norm`.

`address_norm, parcel_source, parcel_key, build_id, lat, lon, precision_tier, has_build_id,
has_spatial, match_tier, match_method, match_confidence, bridge_source, built_at`

A `QUALIFY ROW_NUMBER()` enforces one parcel per address — without it the tier-3 spatial rows fan
an address onto every polygon containing it and inflate every downstream count.

| tier | method | confidence | rows |
|---|---|---|---:|
| 1 | `build_id` equality **confirmed by** `ST_CONTAINS` | `high` | 34,602 |
| 2 | `build_id` equality only (spatial disagreed or absent) | `medium_high` | 7,325 |
| 3 | `ST_CONTAINS` only | `medium` | 9,382 |

### `indiana_app.in_si_signals_parcel_dated` — 46,790 rows

One row per `(parcel_source, parcel_key, signal)` — grain asserted. 45,822 parcels, 63,329 events.
Clustered by `parcel_source, parcel_key, signal`.

`parcel_source, parcel_key, signal, max_observed_date, max_past_observed_date, min_observed_date,
n_events, n_events_dated, n_events_3y, n_events_future, n_addresses, n_sources, match_tier,
match_method, match_confidence, built_at`

| signal | parcels | events | 3y | date range |
|---|---:|---:|---:|---|
| `D2_foreclosure` | 27,248 | 40,330 | 6,173 | 2006-01-01 … 2026-10-20 |
| `D16_structure_fire` | 12,544 | 15,423 | 5,211 | 2020-01-01 … 2024-12-31 |
| `D1_tax_sale` | 4,464 | 4,725 | 278 | 2022-03-03 … 2026-09-28 |
| `D14_sba_chargeoff` | 1,773 | 2,056 | 113 | 1992-12-24 … 2026-06-23 |
| `D7_brownfield` | 536 | 555 | 0 | undated at source |
| `D20_loan_maturity` | 207 | 222 | 1 | 2023-10-01 … 2036-03-01 |
| `D24_plant_delisting` | 10 | 10 | 10 | 2023-09-13 … 2026-03-11 |
| `A2_gov_surplus` | 6 | 6 | 4 | 2022-09-30 … 2024-09-30 |
| `D19_warn` | 2 | 2 | 1 | 2022-07-29 … 2023-09-29 |

**Future dates are real and are not clipped.** 14,304 address-keyed rows carry
`observed_date > today` — D1_tax_sale *scheduled sale dates* to 2026-09-28, D20_loan_maturity to
2036-03-01. These are forward-looking events, and a scheduled tax sale is the strongest
seller-intent signal there is. They are kept, but `max_observed_date` and
`max_past_observed_date` are **separate columns** so that "2036-03-01" can never be read as
evidence of recent activity. 4,565 such events are carried.

---

## 6. Before / after on the parcel layer

| | before | after | change |
|---|---:|---:|---:|
| signal-flagged parcels (`has_si_signal`) | 847,410 | 847,410 | — |
| …with a real `si_last_event_date` | **2,985 (0.35%)** | **3,886 (0.46%)** | **+901** |
| …dated within 3 years | 837 | 1,028 | +191 |

**That is the honest headline, and it is a small number.** Recency still cannot filter the
flagged-parcel population.

### But the flagged population is the wrong population, and that is the real finding

The new table dates **45,822 parcels**. Only **1,016 of them are `has_si_signal` at all.**
**44,806 are not flagged** — they carry a real, dated distress signal and the parcel layer does
not know it.

The cause is that `has_si_signal` was set from the parcel-keyed block, and that block is
**one signal**:

| keying | rows | distinct keys | distinct signals | signal |
|---|---:|---:|---:|---|
| `parcel` | 945,896 | 945,896 | **1** | `D5_vacancy` |
| `parcel_key` | 6,950 | 6,504 | **1** | `D26_assessment_appeal` |

So `in_sites.has_si_signal` is, in practice, **a `D5_vacancy` flag** — and D5_vacancy carries
**zero dates**. `si_last_event_date` could never have been populated from it. The two populations
barely intersect because they are different signals about different properties, not because a
join failed.

**The gain from this build is therefore not "+901 dated flagged parcels". It is 44,806 parcels
that should be flagged and dated and currently are neither.** Acting on that requires changing
how `has_si_signal` is derived, which is a decision about signal policy, not a data repair, and
is left to the operator.

---

## 7. What remains unsolved

1. **Geocode coverage is the whole ceiling.** 62.4% of signal addresses (156,053) are absent from
   `mat_si_address_location`; a further 44,146 Indiana rows sit there `unresolved`. Everything
   else in this document is downstream of that one number.
2. **Indianapolis is the specific hole.** 2,713 resolved Indianapolis addresses against 747,211
   Marion County code-violation rows. This is the single highest-value geocoding target in the
   state and it is where the platform is thinnest.
3. **D12's loader omits the city suffix**, so it cannot key against anything. Fix belongs in the
   `si_d12_indy_marion_code_enforcement` loader. Worth ~1,593 addresses on its own — do it, but
   do not expect it to move the headline.
4. **D85 is live.** `parcels_in / 080500000047000018` is an inverted whole-Earth polygon with
   `structure_count = 3,377,472`. Every spatial query against `in_sites` must exclude it or
   silently match everything. This build excludes it; nothing upstream does.
5. **`has_si_signal` means `D5_vacancy`.** Until that is widened, the parcel layer's own notion
   of "has a signal" cannot see foreclosure, structure fire, tax sale, or SBA charge-off.
6. **The two bridge routes disagree on 16.4%** of the addresses where both fire (6,807 of
   41,483). Carried as tier 2 rather than adjudicated — a building straddling a parcel line and
   a mis-assigned principal structure are indistinguishable from here.
7. **`D7_brownfield` is undated at source** (1,371 rows, 0 dated), so its 536 bridged parcels get
   a parcel link but still no date.
8. **Key-format note, not a defect:** `in_si_signals.parcel_key` carries an `IN:` prefix
   (`'IN:280509222024000023'`) while `in_sites.parcel_key` does not
   (`'010413400001000007'`). A raw join yields 0. The platform's existing normaliser
   (`REGEXP_REPLACE(parcel_key, r'^[A-Za-z]+:', '')`, as used in `energy.vw_si_parcel_enriched`)
   handles it. Anyone joining these tables must apply the existing one — and must not write a new one.
