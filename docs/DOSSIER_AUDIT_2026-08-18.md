# DOSSIER AUDIT — the Power Plan, 2026-08-18

> Operator: *"this is not the only thing that doesn't connect from the application to the dossier,
> and the entire dossier should really be audited."*

The dossier is `renderPowerPlan()` in `app.js` (~1425–1755), reached from the map console's
**Dossier** button on a parcel panel. Four printed pages: verdict and takeaways, Figure 1
stakeholders, Figure 2 parcel diagram, Figure 3 path-to-power, Figure 4 interconnection checklist,
Figure 5 evidence held, scoring detail, and a stakeholder-meeting appendix.

**It is the only artefact a developer physically carries to a utility**, so a wrong figure here
costs more than a wrong figure anywhere else in the app. Every claim below was measured, not read.

⚠ **The map console does not boot in a headless sandbox** (environmental, confirmed three times —
`map` exists but `getStyle()` throws). So this audit reads the code and the data it consumes, and
verifies every checkable claim against the warehouse. **What it could NOT do is render the dossier
in a browser and read the output.** That gap is stated rather than papered over, and it is why the
findings below are about inputs and logic rather than layout.

---

## SUMMARY

| # | finding | severity |
|---|---|---|
| **D-1** | The dossier has **no tariff input at all** and prints two claims that are now false | ⛔ **critical** |
| **D-2** | Its PJM withdrawal figure comes from a **superseded case**, 229 placed buses of 1,826 held | ⛔ **critical** |
| **D-3** | A **hardcoded worked example** from another utility is printed as advice for every parcel | ⛔ **high** |
| **D-4** | The provenance block **cites tables it never reads and omits ones it does** | ⚠ medium |
| **D-5** | G51's three-state `row()` is used with **only two states**, in the evidence table | ⚠ medium |
| **D-6** | The "two directions agree on none" claim is **TRUE — and understated** | ✅ verified |
| **D-7** | `territoryAt()` **ignores polygon holes**, so a donut-hole parcel resolves wrongly | ⚠ medium |
| **D-8** | Figure 4's checklist is **eight hardcoded rows** that can never reflect real status | 🟡 low |
| **D-9** | "Planned transmission" matches on a **6-character string prefix** | ⚠ medium |
| **D-10** | The acceptance run still records the tariff as **impossible** | ⚠ medium |

---

## D-1 ⛔ THE DOSSIER HAS NO TARIFF INPUT, AND SAYS SO IN PRINT

**Measured:** `app.js` fetches 15 payloads. `data/tariffs.json.gz` — 40,595 bytes, built today — is
**not one of them**. The only occurrences of the word "tariff" in `app.js` are the prose strings
below.

The dossier prints, in Figure 3:

> *"No component-level Indiana tariff is held yet."*
> *"We deliberately do not print a $/kWh here: a blended county average would look precise and be
> wrong. This is open work."*

**Both are now false.** `in_utility_tariff_riders` holds **668 components across 73 utilities**;
**22 are costed from their own books** to an effective ¢/kWh at every service voltage with all
riders folded in, and **50 more carry a URDB floor**. The Market page has priced them all day.

⭐ The second sentence is the worse one, because its reasoning is now inverted. It refuses to print
a rate on the grounds that only a *blended county average* is available — but the whole point of
the rate engine is that we no longer have to blend. The dossier resolves the serving utility by
point-in-polygon; that utility's own schedules, riders and service-voltage spread are all in the
payload it does not load.

**To fix:** load `tariffs.json.gz`, join on `T.utility`, and print the same per-service-voltage
figures the Market page shows — with the same honesty furniture (`≥` floors for URDB-only
utilities, "not held" where riders are missing, the eligibility ceiling that excludes a schedule at
this load).

---

## D-2 ⛔ THE WITHDRAWAL FIGURE COMES FROM A SUPERSEDED CASE

The dossier's single most important number — *"Getting power (withdrawal)"* in Figure 3, and the
matching key takeaway — comes from `state.gridsiting.buses`, built from `in_bus_capacity_tier0`.

**Measured, `in_bus_capacity_tier0`:**

| iso | direction | powerflow case | buses | **placed** |
|---|---|---|---:|---:|
| PJM | Withdrawal | **2027 RTEP Base Case (Summer Peak)** | 1,475 | **229** |
| MISO | Injection | DPP-2021-Cycle | 603 | 642 rows |

The shipped `gridsiting.json.gz` carries **229 withdrawal buses**, all stamped
`vintage: "2027 RTEP Base Case (Summer Peak)"`.

⛔ **That is case 4.** The vendor's case — and the one two multi-hour harvests were run to obtain —
is **case 23, "2028 TC2 Phase II Case (Summer Peak)"**, now landed at **1,826 of 1,826 buses** in
`in_pjm_qs_c23sens_wd`. **None of it reaches the dossier.**

Two consequences, both bad:

1. Sites are screened against a **stale study**, and the dossier says nothing about it — while
   being scrupulously honest about the MISO DPP-2021 vintage two rows below. The asymmetry is the
   tell: we disclose the staleness we know about and not the one we forgot.
2. Only **229 buses carry coordinates**, so most parcels fall back to *"Not published for this
   location"* — which the dossier attributes to **MISO not publishing withdrawal data**. For a PJM
   site that explanation is simply wrong; the data exists and we hold it.

⚠ **One thing to settle before rebuilding this** (it belongs to the bus work, not to the dossier):
taking `MIN(available_mw)` across constraint rows gives **0 MW on all 1,826 withdrawal buses**,
while the median *maximum* is 1,551 MW. Every bus has at least one fully-bound constraint. That is
the pre-existing-overload problem already recorded in **G26** — 26.3% of Indiana facility rows are
over their rating before any request exists — and the headroom method has to exclude those before
any figure goes in a document.

---

## D-3 ⛔ A HARDCODED EXAMPLE FROM ANOTHER UTILITY, PRINTED AS ADVICE

Next step 3 reads, for **every parcel in Indiana**:

> *"Service voltage materially changes the bill — on a worked 35 MW example, transmission-level
> service was about $210,000/yr cheaper than distribution primary."*

That figure comes from `CPS_35MW_Rate_Model.xlsx`, a **single worked example at one utility at 35
MW**. It is printed unconditionally: at 300 MW, in a county served by a different utility, next to
a verdict computed from this parcel's own acreage.

We can now compute the real thing. At 300 MW / 85% load factor the measured spread across service
voltages is, for example, **$33.91M a year (12.6% of the bill) at AES Indiana**, and the Market
page already names the cheapest and dearest class. The advice is right; the number is somebody
else's.

---

## D-4 ⚠ THE PROVENANCE BLOCK CITES WHAT IT DOES NOT READ

Figure 5 closes with *"Sources used in this document"*, built from a hardcoded list:

```js
const tables = ["in_sites", "in_si_sites_flags_v2", "in_site_gates", "in_substations",
                "in_transmission_union", "in_si_d22_echo_indiana"];
```

**Cited but never read by the dossier:** `in_substations`, `in_transmission_union`.
**Read but never cited:** `in_bus_capacity_tier0` (the withdrawal and injection figures),
`in_queue` (generation capacity), `in_dc_actions_resolved` (county posture), and MTEP (planned
transmission).

⚠ `in_mtep_projects` **is not in `_registry` at all**, so even if it were cited, `prov()` would
fall through to the bare table name with no row count or build date.

This fails **G16**'s test directly: *could a stranger re-run this from what the document states?*
Not from this list — it names two tables that contributed nothing and hides the four that produced
the headline numbers.

---

## D-5 ⚠ THE THREE-STATE HELPER IS USED WITH TWO STATES

**G51** split `row(k, v, absent)` into three states precisely so a surface could distinguish *a
value* / *measured and empty* / *not measurable here*. **Not one of the dossier's twelve `row()`
calls passes the third argument.**

The clearest casualty is in the evidence table:

```js
${row("Federal tax-credit zone", p.bonus_kinds)}
```

A parcel in **no** bonus zone has `bonus_kinds` empty — which is a **measured, published fact** —
and the dossier renders *"not measured here"*. That is a false statement about our own coverage, in
the table whose entire job is to say what we can show.

✅ The flood, wetland and protected-land rows are correct: they test `=== undefined` before
choosing, so a measured `false` prints *"clear (measured)"*. That is the pattern the other rows
need.

---

## D-6 ✅ VERIFIED TRUE — AND THE DOSSIER UNDERSTATES IT

Figure 3 prints:

> *"It is not a substitute for the withdrawal figure — measured on 200 buses, the two directions
> agreed on none of them."*

**Re-tested on case 23, 1,826 buses in both directions:**

| | buses |
|---|---:|
| present in both directions | 1,826 |
| zero in both | 1,419 |
| **either direction non-zero** | **407** |
| of those, exact agreement | **0** |
| of those, within 5% | **0** |
| non-zero on withdrawal only | 0 |
| non-zero on injection only | 407 |

⭐ The claim holds, on **nine times** the sample. It is also *understated*: every non-zero headroom
in the case is on the injection side. Update `200` → `1,826` when the bus rebuild lands, and the
sentence gets stronger, not weaker.

⚠ **Do not quote the naive 1,419-of-1,826 "agreement"** — that is mutual zeros, and reporting it as
agreement would be a claim about the instrument, not the grid.

---

## D-7 ⚠ POINT-IN-POLYGON IGNORES HOLES

```js
for (const poly of polys) if (poly.length && inRing(poly[0])) return f.properties;
```

Only `poly[0]` — the outer ring — is tested. GeoJSON rings after the first are **holes**. A parcel
sitting in a territory's donut hole (a municipal utility enclosed by an IOU is the common Indiana
case) resolves to the enclosing IOU.

This decides **all four rows of Figure 1**, the regulated/market wording, both "not resolved"
fallbacks, and next step 1 — *"Engage X to confirm service territory"*. Naming the wrong utility is
worse than naming none.

Fix is small: test the outer ring, then reject if the point also falls in any subsequent ring.

---

## D-8 🟡 FIGURE 4 IS EIGHT HARDCODED ROWS

Every milestone prints `Not started` from a literal array. For a prospecting document that is the
honest answer and the prov note says so plainly. But it is **static markup**, so the checklist can
never reflect a study that does exist, and nothing distinguishes *"not started"* from *"we do not
track this"*. Low priority — flagged so it is a decision rather than an oversight.

---

## D-9 ⚠ "PLANNED TRANSMISSION" MATCHES ON SIX CHARACTERS

```js
const mtepNear = (G.mtep || []).filter((m) =>
  String(m.from_sub || "").toUpperCase().includes(String(wdBus.name || "~~").toUpperCase().slice(0, 6)));
```

A **6-character prefix substring** decides whether a MISO expansion project is "near" this site.
It will over-match (any station sharing six leading characters) and under-match (any naming
variation in the first six). It also silently degrades to matching `"~~"` when there is no bus.

The row already reports the statewide count honestly; it is the *"N referencing the nearest
station"* clause that is unreliable. Either join on a real key or drop the clause.

---

## D-10 ⚠ THE ACCEPTANCE RUN STILL CALLS THE TARIFF IMPOSSIBLE

`docs/ACCEPTANCE_RUN.json` records:

> *"P6 132 rate proxies (no Indiana component-level tariff exists, so P6 cannot be closed)"*

`SESSION_START.md` carries the same ruling under §13(8). Both were **true when written** and are
now false: 668 components across 73 utilities, 22 costed from their own books. P6 should be
re-evaluated rather than left recorded as not-achievable.

---

## FIX ORDER

1. **D-1** — load the tariff payload and print the real rate. Largest gap, and the data is ready.
2. **D-2** — rebuild `in_bus_capacity_tier0` on case 23. ⚠ **Blocked on the headroom method** (the
   pre-existing-overload question in G26), which is the bus work the operator has queued next. Until
   then the dossier should at minimum **disclose the PJM vintage** the way it discloses MISO's.
3. **D-3, D-5, D-4** — small, self-contained, no dependencies.
4. **D-7, D-9** — correctness fixes in two helpers.
5. **D-10** — re-run acceptance once D-1 lands.
6. **D-8** — decide, then either derive or say we do not track it.
