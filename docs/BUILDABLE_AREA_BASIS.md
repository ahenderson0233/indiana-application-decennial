# BUILDABLE AREA — the documented basis (G28)

> **G28's open half is this document.** The display half shipped: `mwReality()` bands every derived
> MW and says it is gross land, and the wording moved from *"fits X MW"* to *"land supports up to
> X MW"* on the tooltip, the verdict line and the takeaways. What was missing was a written basis
> — *what, exactly, is netted out of a parcel before we call the remainder buildable*.
>
> Written 2026-08-19. Every figure below is measured, not assumed.

---

## 1. What we actually net out today, and what we only flag

| deduction | netted from the area? | how it is held | why |
|---|---|---|---|
| **Existing building footprints** | ✅ **YES** | `exact_outdoor_acres` = parcel polygon minus building footprints, measured against real footprints and never a centroid | This is the one deduction we can make honestly, because we hold the footprint geometry |
| Mapped flood hazard (SFHA) | ❌ flagged only | `sfha_flood` BOOLEAN per parcel | We hold *whether* a parcel touches an SFHA, not *how much of it* is inside |
| Wetland | ❌ flagged only | `wetland_on_parcel` BOOLEAN | Same: presence, not extent |
| Protected land overlap | ❌ flagged only | `protected_land` BOOLEAN | Same |
| Transmission right-of-way | ❌ flagged only | `line_on_parcel` BOOLEAN — **41,986 parcels have a conductor physically on them** | We hold the line as a LineString and the parcel as a polygon; we do not hold an easement width |
| Setbacks, internal roads, slope, easements of record | ❌ **not held at all** | — | Setbacks are per-ordinance and per-district; slope needs a DEM we have not clipped; easements are in the deed |

⭐ **So the honest one-line statement of the basis is:**

> **Data-centre basis** = the whole parcel polygon.
> **Battery basis** = the parcel polygon **minus existing building footprints** (`exact_outdoor_acres`).
> Nothing else is deducted. Flood, wetland, protected land and transmission RoW are **reported as
> flags beside the figure, never subtracted from it.**

That is what the application does, and it is now written down. The use-case split is deliberate and
was ruled by the operator: a data centre builds over or removes what is there, so its buildable
area is the whole parcel; a battery fits *around* existing buildings, so it uses open ground.

---

## 2. Why the flags are not silently subtracted

Subtracting a deduction we cannot measure would be worse than not subtracting it, in a specific and
familiar way. If a parcel is flagged `sfha_flood` and we docked it a guessed 30%, the resulting
acreage would look exactly like a measured figure and would be wrong by an unknown amount in an
unknown direction. That is the same defect shape as treating an unpublished tariff rate as zero,
which produced **95 false "below floor" violations**, and as printing "none" where we never looked.

⛔ **A flag beside a number is honest. A number quietly reduced by a guess is not.**

---

## 3. What the tail looks like, and why nothing is capped

Measured across the parcel corpus: median **94.4 MW**, p99 **710 MW**, and **2,204 parcels above
1,000 MW**, 368 above 2,000, maximum **25,428 MW**.

Those large figures are real land, not a bug — Indiana has genuinely enormous agricultural parcels.
They are **banded and labelled rather than capped**, because capping hides real land from a phased
campus, and a developer assembling 2,000 acres needs to see the 2,000-acre parcel.

⚠ **The MW figure is the reader's own assumption made visible**, not a measurement: it is
`acres × MW-per-acre`, and the MW-per-acre input is a control the user sets (4 for a data centre,
10 for batteries are common planning figures, not our findings).

---

## 4. What it would take to net the rest properly, and what that costs

The four flagged deductions are all **areas we could compute** — the geometry exists — but none is
cheap, and one is not merely expensive:

| deduction | route | measured obstacle |
|---|---|---|
| Flood extent | `ST_INTERSECTION(parcel_geog, in_flood.geog)` per parcel | `in_flood` is **803.8 MB**; a pairwise intersection against 532,868 parcels is a **cost-flag job under the $25–50 rule** — price it before running it |
| Wetland extent | same against `in_wetlands` | **1,319.6 MB**, same caveat and larger |
| Transmission RoW | buffer the conductor and intersect | ⛔ **We do not hold an easement width.** A RoW is a legal instrument, not a geometric one; a 345 kV line's easement is typically 150 ft but that is a rule of thumb, not this parcel's deed. Buffering by a rule of thumb produces a precise-looking number from an assumption |
| Setbacks | per-county, per-district | Needs the zoning corpus at district grain. **G71** is measuring what zoning we actually hold; this deduction is blocked behind it |

⭐ **Recommended order, and it is not the obvious one.** Do **transmission RoW last, not first**,
despite it affecting the most parcels (41,986). The other three yield a measurable area; RoW yields
an assumption dressed as one. Start with **flood**, because SFHA boundaries are authoritative, the
deduction is legally meaningful, and one costed query answers whether the whole family is affordable.

---

## 5. What a reader should take from a buildable-area figure today

- It is an **upper bound on gross land**, stated in the reader's own MW-per-acre assumption.
- For a battery it already excludes existing buildings; for a data centre it does not, by design.
- It has **not** been reduced for flood, wetland, protected land, transmission RoW, setbacks,
  internal roads or slope — and the flags for the first four sit next to it.
- Two acreage measures exist (recorded and measured) and they **agree** at a median 23.75 = 23.75
  acres, so the figure is not drifting; where they disagree the **smaller is used, never the larger**.

---

*Maintained with G28. If a deduction moves from "flagged" to "netted", change the table in §1 in the
same commit that changes the arithmetic — two descriptions of one basis will drift, and the loser is
invisible.*
