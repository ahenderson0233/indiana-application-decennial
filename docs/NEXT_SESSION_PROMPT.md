# NEXT SESSION — paste everything below this line as your first message

Continue the Indiana siting-intelligence application.
Repo: `C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial`
(GitHub `ahenderson0233/indiana-application-decennial`, branch `main`, last commit `226bcb7`)

---

## ⛔ FIRST, IN THIS ORDER. Do not propose anything before you have.

### 1. Is the harvest still alive?

```bash
powershell -NoProfile -Command "@(Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | Where-Object { $_.CommandLine -like '*pull_pjm*' }).Count"
```

**A PJM MW-ladder harvest is running and has already survived one shutdown.** If that returns `0`
and the ladder is unfinished, resume it — this is the only command needed, and it is safe to run
even if one IS already going:

```bash
powershell -ExecutionPolicy Bypass -File scripts\run_pjm_ladder.ps1
```

State at handover: **5,000 MW WITHDRAWAL, 51 of ~74 batches, 321,283 rows, 1,275 of 1,826 buses**.
Queued behind it: 5,000 INJECTION, then 1,000 and 500 MW in both directions.

⛔ **NEVER start a second QueueScope process.** That rule was broken on 2026-08-18 by a chained job
whose `Wait-Process` failed open and launched injection 7 minutes into a withdrawal run. The runner
polls for the ABSENCE of a process instead.
⛔ **NEVER delete `data/`.** Progress lives in `data/_ckpt_pjm_qs_case23_{withdrawal,injection}/`.
The MW is IN the marker filename, so rungs cannot skip each other's work. Archive, never delete.
⛔ **Owner is 1568, not 739.** 739 is AEP in the *default* case: it loads 0 rows and exits
**successfully**.

### 2. Checkpoint

```bash
python scripts/checkpoint.py
```

**Expect exactly 3 failures and expect them to be correct:**

| failing check | why |
|---|---|
| `wiring census: 282 of 300` | new tables not yet on a surface. Standing state. |
| `honesty audit: 1 failure` + `1 unregistered` | **that unregistered table IS the running harvest.** It registers on completion; registering early would assert a moving row count. |

⛔ **Anything else failing is real.** In particular `shipped payload agrees with the warehouse`, the
five `D85` guards, `no shipped payload is older than the table it reads` and `no payload has lost a
key a surface depends on` must all PASS — each exists because it already broke once.

### 3. Read, in this order, and no further

| # | file | what it is |
|---|---|---|
| 1 | `docs/SESSION_START.md` | standing rules and the governing principle |
| 2 | **`docs/FEATURE_INVENTORY.md`** | ⭐ **EVERY feature, what it does, how it works, and its BigQuery table.** The fastest orientation in the repo |
| 3 | `docs/HANDOFF_2026-08-18b.md` | the session that just ended — §1 the harvest, §8 the status board, §9 the methodologies |
| 4 | `docs/BACKLOG.md` | the **⚠ IN FLIGHT** row first, then the G-index |
| 5 | `scripts/tariff_adapters.py` | each utility's tariff conventions in its own words — before any tariff work |

⚠ `docs/HANDOFF_2026-08-18.md` (no `b`) is the MORNING session and is marked SUPERSEDED. `GAMEPLAN`,
`HANDOFF`, `PATH_TO_COMPLETE` and `NATIONAL_HANDOVER` are HISTORY — read them for *how*, never for
*what is true now*.

---

## ⭐ YOUR FIRST ACTION ITEM — when the ladder lands, look for NEW FACILITIES, not new numbers

This is the single most important thing in this prompt.

**Measured:** a 1-batch probe at 5,000 MW matched the existing 100 MW harvest on **4,673 of 4,673
constraint keys, max delta 0.0**. `available_mw` does not vary with the requested MW. So the ladder
will NOT change the numbers on rows we already have.

**The operator's reasoning for running it anyway is sound and is what to test:** a larger request
may cause QueueScope to *report facilities* that a 100 MW request never binds. The evidence that
this matters:

- we monitor **89.5 facilities per bus**; the vendor reports **9.4**
- yet **146 of their 298 binding facilities are absent from our harvest entirely**
- 134 are present and pass our filters → a genuine ranking problem
- 18 are cut by our `|dfax| ≥ 0.05` filter

**Re-run the comparison when each rung lands.** If the new rungs surface those 146, PJM parity
follows. If they do not, the gap is the monitored-facility *scope* and needs a different attack.

---

## WHERE THE TWO OPEN BUS PROBLEMS STAND

### Capacity parity — the derivation is SOLVED, selection is open (G61)

Orennia's figure is `(rating − base flow) / |shift factor|` on the binding facility. Verified
against their own published row for bus 243209: 2844 MVA, 2550 MW, −0.0745 → **3,946 against their
3,943.59**. We do not ship the rating but can recover it:
`rating = impact_mw / ((post_loading_pct − pre_loading_pct) / 100)`.

| on the 283 shared buses | exact | within 20% | median ratio |
|---|---|---|---|
| `MIN(available_mw)` — what shipped that morning | 0 | 0 | **0.136** |
| the derived formula — shipped now | 1 | 84 | **1.010** |

Centred instead of seven times low. The binding rule, verified against them: **the tightest facility
that is not already over its rating**. They still report 0 when the whole bus is overloaded (147 of
their 152 flagged rows are exactly 0) — they drop the overloaded FACILITY from the choice, never the
bus.

### Placement — the method is PROVEN, the gazetteer is the ceiling (G62)

Bus label → substation name, stripping the AEP area prefix (`05EUGENE` → `EUGENE`) and the trailing
bus index (`05DELAWR1` → `DELAWR`), reproduces the vendor's coordinates at a **median 0.03 miles**.
Topology from the branch graph — every `transmission_facility` string names both endpoint buses —
adds a hop-1 tier at ~5.3 mi. **Hop-3 is junk at 33 mi and is not used.** Coverage 82 → **111 of
283**.

⛔ **The blocker is data, not code.** `in_substations` does not contain MODOC, FOWLER, STUDEBAKER,
BOUNDARY or ADAMS, while DELAWARE and SOUTH BEND are present and match cleanly. **Extending the
gazetteer is the unlock.**

⚠ **The denominator is 283, not 1,826.** Our harvest is owner=AEP, whose footprint spans Ohio, WV,
VA, KY and Michigan; `in_substations` is Indiana-only. Most non-matches are correctly non-Indiana.

---

## ⚠ THE ONE PLACE WE DEPEND ON A PRIVATE SOURCE

Operator: *"we want to use Orennia as a yardstick, and do not want to use their data verbatim, since
we ideally don't want to ever rely on a private source for our data."*

**MISO headroom is the deliberate exception.** MISO publishes no load-side figure anywhere and four
independent sweeps found no public route, so without the licensed proxy the tool cannot answer the
load question across two thirds of Indiana. Every such row carries
`provenance_class = 'vendor_licensed_proxy'`, the dossier says so in words, and **the licence lapses
late 2027** — after which those rows return to "not published".

**Nothing in PJM is theirs.** The capacity is our harvest through our own derivation; the placement
is our own name match; their file is only the scoring set.

---

## HOW TO WORK HERE — the seven moves that actually worked

1. **Probe before committing hours.** A 1-batch probe killed a multi-hour harvest that would have
   duplicated existing data.
2. **Measure the blast radius before changing shared logic.** *"Adding these two words changes
   exactly 1 of 31 eligibility rows"* is what made that edit safe to ship.
3. **Use the vendor as a scoring set, never a source.** Their file has a labelled answer per bus.
4. **A count is not a total.** `n_riders_attached` reported 8–13 riders correctly attached while
   every one contributed **$0**. That defect survived a full session of auditing.
5. **Render the document; do not read the code.** A parse check passed `esc is not defined`, which
   would have made the Dossier button do nothing.
6. **An alarming number is a claim about your INSTRUMENT first.** All three of that day's shocks
   were join bugs: "0 of 298 match" (int vs string), "1,419 of 1,826 agree" (mutual zeros), "max
   delta 1,841 MW" (fan-out).
7. **Turn each fixed defect into a standing check.** `audit_tariff_costing.py` and
   `tariff_fingerprint.py` are exactly that.

⭐ **Per-utility adapters, never a generic rule** (tariffs). If you find yourself editing shared
logic to satisfy one publisher, stop. Run `python scripts/tariff_fingerprint.py` after any change —
it names which publishers moved, and a change to one adapter must move exactly one utility.

---

## ⛔ THE RULES, and the failure that earned each one

**Write boundary.** `energy-platfrom.energy` is **READ-ONLY**. Everything goes to
`energy-platfrom.indiana_app`. The one permitted write is an APPEND to `energy.registry_sources`.
**Restate this in every agent brief — agents do not inherit it.**

**Every table gets a `_registry` row in the same run**, carrying `source` AND `method`, with a
verbatim `RE-SCRAPE COMMAND:` sufficient for a stranger to re-run it.

**⛔ CHECK THE WAREHOUSE BEFORE YOU EXPLORE OR SCRAPE.** Enumerate `energy.__TABLES__` and
`indiana_app._registry` first. It has now paid for itself six times.

**Never quote a count from a document, including this one.** Run the checkpoint.

**Read the schema. Never guess a column name or type.** `bus_number` is a **STRING**; `rows` and
`nulls` are reserved words; `registry_sources.object_names` is `ARRAY<STRING>`; `in_substations` has
`lat`/`lon`, not `geog`.

**⚠ NEVER write a regex through a shell heredoc.** Three times now a pattern has reached disk
mangled — twice as literal backspace bytes, once with unbalanced parens — and `grep` showed the line
as clean. Write via the Write tool and self-test at import.

**Unpublished is NULL, never 0.**

**⚠ EXCLUDE `parcels_in/080500000047000018` from EVERY spatial join** — D85, an inverted whole-Earth
polygon, live upstream.

**⛔ No centroid where a footprint exists.** Acreage, asset distances and service territory all
measure against the polygon. The one exception — bus distance, because buses *are* points — is named
on the page.

**Never `git add -A`.** Stage explicit paths, and use a commit-message FILE.

**After ANY front-end change:** `python scripts/stamp_assets.py`, then
`python scripts/audit_frontend.py`, then verify in a browser, then check the deployed site at
`https://ahenderson0233.github.io/indiana-application-decennial/index.html` (~1 min for Pages).

⚠ **`app.js` is boot-critical** and the map console **does not boot in a headless sandbox** —
confirmed four times, including against the live site. Verify the dossier by populating `state` by
hand and calling `openDossier()` with a real parcel from `data/sites/{fips}.geojson.gz`. That is how
the two bugs introduced during the dossier fix were caught.

---

## WHAT IS DONE — do not re-do these

**G54** tariff costing (17 defects; right for the five IOUs) · **G56** per-utility adapters, proven
isolated · **G58** the silent cap · **G60** dossier audit (9 of 10 closed) · **G39** screener depth,
deep link, dossier link, map layer · **G63** the bus rebuild · **G64** the IOCS self-heal · **§13(8)**
which was recorded as impossible for months and is now closed.

## WHAT IS NOT STARTED

**G43** border clipping · **G48** existing-DC-reads-green · **G50** the dossier's "not resolved"
utility rows · **G51** caller sweep · **G52** map legend · **G53** withdrawn queue as a signal ·
**G57** two I&M rows with `rate = 0.0` marked `published` · **G59** retire the duplicate PJM pair
(~1.1M identical rows) · **G55** 50 utilities still on a URDB floor.

## DO NOT RE-LITIGATE

- **MISO parity is not publicly reachable.** DPP-2025 is CEII; four sweeps proved it. Do not
  re-probe CartoVista or giqueue, and do not buy a trial.
- **The G26 headroom method is settled** — pre-existing overloads are flagged and reported, not
  dropped. It is implemented.
- **The case-23 re-harvest produced byte-identical data** to `in_pjm_qs_tc2phii_*`. PJM did not
  refresh the powerflow file; the two pairs are duplicates (G59).

---

**Start by** telling me whether the harvest is alive and what the checkpoint printed, then what you
read, then your plan.
