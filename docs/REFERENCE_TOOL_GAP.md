# What the operator's own two tools screen on, and what we do not — audited 2026-08-19

> Operator, 2026-08-19: *"audit what we currently have against the screening mechanisms that we
> hold in the following tools that I've built."*
>
> - `https://ahenderson0233.github.io/indiana-bus-analysis/` — **86 controls**
> - `https://ahenderson0233.github.io/illinois-analysis-map/` — **62 controls**
> - ours: map console **30 layer controls + 17 filters**, screener **39 controls**

Read live from both pages, not from memory. Every row below says whether the gap is **buildable
from data we already hold**, needs an **acquisition**, or is **not ours to copy**.

⛔ **The honest headline: the two reference tools screen on DIMENSIONS we do not have at all, not
just controls we have not drawn.** Upgrade tier, lead time, upgrade cost and upgrade risk are four
axes the bus tool filters on and our estate cannot answer today. That is a data gap wearing a UI
costume, and building the controls without the data would be worse than the gap.

---

## 1. ⭐ BUILDABLE NOW — we hold the data and simply never exposed it

| mechanism | where they have it | what we hold | verdict |
|---|---|---|---|
| **Radius search from a point** — click the map or type `39.80, -89.64`, set a radius in miles, screen inside it | Illinois `pickPt` / `ctrInput` / `radiusMi` | every parcel has `lat`/`lon`; buses and substations have coordinates; `ST_DISTANCE` is already the screener's method | ⭐ **the single biggest missing mechanism.** A developer with a target town cannot ask "what is within 20 miles of here". Pure front-end plus one distance test |
| **Add a site by map click / searched address / my location** | Illinois `mAddClick` / `mAddSearch` / `mAddLoc` | we accept a CSV upload only | buildable; the scoring path already exists (`enrichDistances` → `scoreSite`) |
| **Multi-select line voltage** — EHV≥230 / 161 / 138 / 115 / 69 / <50 / unknown as checkboxes | bus tool | we have `L-line-kv`, a **single**-select dropdown | trivial, and it matters: a siter wants 345 **and** 138, not one at a time |
| **Bus voltage ladder** (35/46/69/138/161/230/345/765 kV+) | bus tool `busV` | we now have a free kV number on the screener (G68) | ours is arguably better; add the ladder as a convenience, keep the free entry |
| **Substation network class** — transmission / distribution / other-undetermined | Illinois | `in_substations.substation_type` (SUBSTATION 2,394 · TAP 497 · DEAD END 29 · industrial 76 · distribution 31 · traction 21 · generation 17) | buildable today; we already hold a richer vocabulary than they filter on |
| **Excel export** at several levels | both tools | we export CSV | small |
| **Separate min-generation / min-load thresholds** | Illinois `minGen` / `minLoad` | we hold both directions per bus and a direction selector | buildable; ours fuses into one "MW available" once a direction is chosen |
| **Basemap switcher · site footprint drawing · save/load session** | Illinois | we have named workspaces (C4) but no basemap or footprint draw | small, cosmetic-to-medium |

## 2. ⚠ NEEDS AN ACQUISITION — the control is easy, the data is the problem

| mechanism | what it needs | status here |
|---|---|---|
| **Upgrade tier 0–4** — "what could this bus take if I paid for N upgrades" | the per-tier upgrade study | ⛔ **MISO's is CEII** (G7m, four sweeps, FERC ER24-2046). PJM: we hold `in_rtep_bus_join`, `in_rtep_bus_summary`, `in_pjm_rtep_cost_allocations` — a **PJM-only** tier-ish dimension is partly buildable, the vendor's ladder is not |
| **Lead time horizon** — Now / ≤3 yr / ≤5 yr / ~10 yr | `Min/Max Lead Time (Years)` | held by the vendor's cost file, **not by us**, for either RTO |
| **Upgrade cost + cost efficiency ($/MW), filtered by proxy size** | per-upgrade cost at a stated request MW | partial: `in_miso_dpp2025_ph1_project_costs` (202 projects, $29.52B; **21 Indiana projects, $1.7B**) and the PJM RTEP allocations. Not per-proxy-size |
| **Upgrade risk** (Low / Medium / High) | a modelled risk grade | vendor-derived. ⛔ Not ours to copy — G22 forbids fitting to their output |
| **Planned grid investments with status + location-uncertainty rings** | located plans | ⭐ **this is our G15**, and their tool is the reference implementation. We hold 618 rows with **county on 0** — blocked on re-extracting the IURC TDSIC workpapers |

## 3. ⚙ A METHOD WE WOULD HAVE TO DEFINE

| mechanism | why it is not a wiring job |
|---|---|
| **Substation headroom, coloured, with a BASIS** — N-1 firm / normal N-0 / emergency N-1+LTE, and a **summer/winter season** switch | we do not model substation headroom at all. This is an estimate their tool derives from ratings; defining it is a methodology question, not a control |
| **Load type** — peak-coincident / data centre (continuous) / off-peak storage | a modelling assumption that changes which demand figure applies. It pairs naturally with our existing use-case selector (DC vs BESS) and the tariff engine's load factor |
| **"Quick wins" — big single-upgrade gains** | needs the upgrade dimension above before it can mean anything |

## 4. ✅ WHERE WE ARE AHEAD

Worth stating, because the audit should not read as a deficit list.

- **Owner motivation.** Neither reference tool screens on it. We carry 25 signals, and since 2026-08-19 the screener filters on **which** signal, event counts in a 3/5/10-year window, and how the signal reached the parcel.
- **Parcels.** They screen buses and substations; we screen **3.55M parcels** with exact acreage, buildable-area basis and a use-case switch.
- **Tariffs.** 668 components across 73 utilities, 22 costed from their own books at every service voltage with riders. Neither tool prices power.
- **Community and regulatory posture.** County actions, ordinances, the legislature tracker — the layer no code library carries.
- **The dossier.** A four-page printable Power Plan. Neither reference tool produces a document.
- **Environmental gates and the exact-distance correction** (G29) — 41,986 parcels with a line physically on them.

---

## ⛔ OPERATOR RULING 2026-08-19 — RADIUS-FROM-A-POINT IS DECLINED

> Operator, 2026-08-19: *"We do NOT need radius from a point in this analysis."*

**This document ranked it #1 and starred it as the single biggest missing mechanism, and both the
handoff and the session prompt repeated that.** It is not wanted. Do not re-propose it, and do not
treat its absence as a gap when auditing us against the reference tools.

⚠ The ranked list below is left intact rather than silently rewritten, because the *reasoning* for
each item is still useful — but item 1 is dead. Everything else stands.

## THE ORDER I WOULD BUILD THEM IN

1. **Radius-from-a-point search** — biggest capability gap, zero acquisition, both tools have it and we have none.
2. **Multi-select line kV + substation class filter** — an hour, and both are already in the payloads.
3. **Add a site by click / address** — the scoring path exists.
4. **PJM upgrade cost dimension** from the RTEP tables — the only part of the tier/cost family we can honestly build.
5. **G15 planned investments** — their Illinois tool is the spec, including the uncertainty rings. Blocked on the IURC re-extraction.
6. **Substation headroom basis + load type** — only after the method is written down and validated.

⛔ **Do not build the upgrade-tier, lead-time or risk controls against vendor data.** G22 is binding: match the METHOD, never the output. An empty control is honest; one fed from a licensed file is not.
