# NEXT SESSION — paste everything below this line as your first message

Continue the Indiana siting-intelligence application.
Repo: `C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial`
(GitHub `ahenderson0233/indiana-application-decennial`, branch `main`)

---

## FIRST, IN THIS ORDER. Do not propose anything before you have.

```bash
python scripts/checkpoint.py
```

Tell me what it printed. **Expect it to FAIL on 2–3 checks and expect that to be correct:**

| failing check | why it is expected |
|---|---|
| `wiring census: 282 of 299` | new tables not yet on a surface. Standing state. |
| `honesty audit: 1 failure` + `1 unregistered` | **a PJM harvest table registers only when its run completes.** Registering it early would assert 0 rows. |

⛔ **Anything else failing is real.** In particular `shipped payload agrees with the warehouse`,
the five `D85` guards, `no shipped payload is older than the table it reads` and `no payload has
lost a key a surface depends on` must all PASS — they exist because each one already broke once.

Then read, in this order, and no further:

| # | file | what it is |
|---|---|---|
| 1 | `docs/SESSION_START.md` | standing rules and the governing principle |
| 2 | `docs/HANDOFF_2026-08-18.md` | **the session that just ended.** Its §1 lists what is still RUNNING |
| 3 | `docs/BACKLOG.md` | the **⚠ IN FLIGHT** row at the top of the index is the fastest orientation; then the G-index |
| 4 | `docs/RESUME_HARVESTS.md` | ⚠ **before touching ANY PJM table** |
| 5 | `scripts/tariff_adapters.py` | each utility's tariff conventions, in its own words — read before any tariff work |

---

## ⚠ RUNNING RIGHT NOW — CHECK BEFORE YOU START ANYTHING GRID-RELATED

```
Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -like '*pull_pjm_injection*' }
```

A **PJM case-23 WITHDRAWAL re-harvest** (`in_pjm_qs_c23sens_wd`) may still be running, with
INJECTION chained behind a poll-for-absence guard and a ≥1,500-bus landing check.

⛔ **NEVER start a second QueueScope process.** That rule was broken on 2026-08-18 by a chained job
whose `Wait-Process` failed open and launched injection 7 minutes into the withdrawal run.
⛔ **NEVER delete `data/`.** Checkpoint markers are keyed by **case+mode, not target table**, so a
re-run against existing markers resumes and harvests almost nothing. Archive, never delete.
⛔ Owner id for case 23 is **1568**, not 739. The wrong id loads 0 rows and **exits successfully**.

---

## ⭐ YOUR FIRST ACTION ITEM — fix the tariff rates that are still wrong

The Market page prices each rate schedule at a user-set MW and load factor, folds in every
applicable rider, prices **every service voltage separately**, and checks each figure against what
that utility's **industrial** customers actually pay (EIA-861). It works for most of the five IOUs.
**It is still wrong in specific, named places, and that is your first job.**

Reproduce the audit before changing anything — run it **through the shipped renderer in a browser**,
not by reimplementing the maths:

1. `python scripts/export_tariffs.py`
2. serve the repo and open `market.html`
3. iterate every IOU in the `#tf-util` selector, read each schedule's per-voltage rows, and compare
   the `vs actual` column against the benchmark in `#tf-count`

### A. Rows showing **$0 for an entire column** — these are the highest priority

A priced row whose **demand** or **energy** column is `$0` means a whole billing leg failed to match
that service class. Every costing bug found so far had this signature. The page now refuses to show
an effective rate for these (`not costable`) — **that guard is working; the underlying gap is not
fixed.**

| utility | schedule | symptom |
|---|---|---|
| **AES Indiana** | **PH** | demand `$0` — energy-only, so no rate is shown |
| **I&M** | **GS** (transmission) | demand `$0` |

Find which component *should* have matched and why it did not. It will almost certainly be a
class-key mismatch — the same family of defect as the nine already fixed.

### B. Schedules whose totals are wildly off

| utility | schedule | reads | benchmark | likely cause |
|---|---|---|---|---|
| **NIPSCO** | **631** | +52% / +69% | 6.10¢ | ⭐ Its **Tier 2 is day-ahead LMP** and **Tier 3 is MISO Asset Owner settlement** — market-indexed, not firm. We cost everything as all-firm, which overstates it. The firm/non-firm election moves a NIPSCO bill more than any rider. |
| **SIGECO** | LP, HLF | −36% / −34% | 9.02¢ | demand billed in **kVA**; PF 1.0 is assumed. Also HLF is demand-only with no base energy charge. |
| **I&M** | IP | −34% | 8.04¢ | may be legitimate — see the tolerance note below |
| **Duke** | **HLF** | **never verified** | 8.83¢ | excluded by a ceiling, so the multi-class fix that was supposed to repair its +402% error is **unproven, not proven** |

### C. The tolerance band itself is the wrong instrument

A flat ±20% flags correct answers as failures. A **300 MW customer at 85% load factor should sit
below** an average that includes small industrials — so I&M IP at −34% may be right. **Make the
tolerance scale with load** relative to the average customer, rather than tuning rates to hit a
fixed band. ⛔ Never tune a rate to match the benchmark; match the **method**, then let the number
land where it lands.

---

## HOW TO MAKE TARIFF CHANGES — this is the part that matters

⭐ **Per-utility adapters, never a generic rule.** `scripts/tariff_adapters.py` holds one
declarative adapter per utility. **Nine costing defects were found on 2026-08-18 and every single
one was a generic rule meeting a house convention**, and several fixes for one utility broke
another:

- **I&M** writes `Tariff I.P.` **with periods** → tokenised to `I` and `P`, never `IP`, so **all
  eight of its riders (~+8.6 $/kW-month) silently failed to attach**
- **AES** publishes a separate **low-load-factor transmission** service → summed with plain
  transmission it read **20.64¢, dearer than secondary**, and an inverted price ladder is always
  the tell
- **Duke** splits transmission into two **kV bands**, splits primary into `direct`/not, writes
  multi-class strings like `transmission and primary`, and states a **floor** in a basis containing
  the word **"maximum"** — read as a ceiling it excluded the schedule and **hid** its +402% error
- **NIPSCO** joins classes with a **slash** (`transmission/subtransmission`) → a $35.74/kW-month
  demand charge bound to sub-transmission alone and the transmission row showed **DEMAND $0**
- **SIGECO** bills demand in **kVA**

**So: put a utility's quirk in that utility's adapter.** If you find yourself editing shared logic
to satisfy one publisher, stop — that is how the previous nine defects were introduced and
re-introduced.

⭐ **Keep the leg guard.** A row missing a whole billing leg must never show an effective rate. It
is the only reason those defects were findable.

**Other invariants in the costing, all learned the hard way:**
- `fuel_base` is **embedded in the energy charge** — never add it as a line; the billable item is
  the FAC difference
- **block ladders are alternatives**, allocated across slices — summing them put NIPSCO at 57.94¢
- **TOU is costable** for a flat 24/7 load: energy splits by the tariff's own stated period hours,
  and **every** time-differentiated demand charge bills full kW because a constant load peaks in
  every period
- **eligibility has a ceiling as well as a floor.** NIPSCO 624 is named "General Service — **Large**"
  and carries a **25,000 kW maximum** — a data centre cannot take it. The name is never the
  eligibility; only the numbers are
- **a large-load framework rides on a parent** (I&M `IP-LL` → `IP`) and inherits its legs *and* its
  riders

---

## ⚠ THE TARIFF WORK IS NOT FINISHED — the 19 municipals are loaded but NEVER VALIDATED

`in_utility_tariff_riders` holds **668 rows across 73 utilities**: the five IOUs (334 rows) plus
**252 municipal / co-op rows across 19 utilities**. Zero `not_held`-with-a-rate violations.

⛔ **Not one of those 252 rows has been through the costing audit.** They are **19 separate
publishers** against five, **none has an adapter**, so all fall back to the generic path that
produced nine defects on five utilities — and **most have no EIA-861 industrial benchmark at all**,
so the reconciliation gate that caught every IOU error **does not exist for them**. A different
check has to be designed. This is **BACKLOG G55**, the largest remaining tariff item.

⚠ **Operational dependency, carried in both registries: if the IURC loader is re-run,
`scripts/load_tariff_books_munis_coops.py` MUST be re-run after it** — the IURC loader's
utility-scoped DELETE would remove those 252 rows.

---

## ⛔ THE RULES, and the failure that earned each one

**Write boundary.** `energy-platfrom.energy` is **READ-ONLY**. Everything we build goes to
`energy-platfrom.indiana_app`. The one permitted write to `energy` is an **APPEND** to
`energy.registry_sources`. **Restate this in every agent brief — agents do not inherit it.**

**Every table gets a `_registry` row in the same run that writes it**, and that row **must carry
both `source` AND `method`** — an incomplete row failed the honesty audit's provenance check on
2026-08-18. Per G16 it must be enough for a stranger to **re-run** the work: exact parameterised
URL, endpoint kind, the loader command verbatim as `RE-SCRAPE COMMAND: …`, the publisher's own
vintage (never your pull timestamp), and what was excluded and why.

**⛔ CHECK THE WAREHOUSE BEFORE YOU EXPLORE OR SCRAPE.** Enumerate `energy.__TABLES__` and
`indiana_app._registry` for the subject first. It costs one query and has now paid five times.

**Never quote a count from a document, including this one.** Run the checkpoint and use what it
prints.

**A clean, perfect or alarming number is a claim about your INSTRUMENT first.** Check the join, then
the filter, then the data. *Transmission dearer than secondary* was the tell that found a real bug;
*13.77¢/kWh* was the tell that found three more.

**Read the schema. Never guess a column name or type.** `registry_sources` has `what_it_provides`
(not `provides`) and its `object_names` is `ARRAY<STRING>`; `nulls` and `rows` are reserved words in
BigQuery. Guessing cost four zero-result queries in one session.

**⚠ NEVER write a regex through a shell heredoc.** Twice on 2026-08-18 a `\b` word boundary reached
disk as a literal **backspace byte (0x08)**, matched nothing silently, and **`grep` displayed the
line as clean** because the terminal ate the control character. Compile patterns at module level
with **import-time self-tests**.

**Unpublished is NULL, never 0.** Treating absent rates as zero produced 95 false "below floor"
violations. **Assert the window you GOT, not the one you asked for.**

**⚠ EXCLUDE `parcels_in/080500000047000018` from EVERY spatial join** — D85, an inverted
whole-Earth polygon, live and unrepaired upstream. Prove the guard by measuring fan-out (~1.0).

**Indiana only, clipped at the border. Cannot-assess renders as itself. Estimates never style as
published.** `row(k, v, absent)` has **three** states: a value, measured-empty (caller passes
`absent`), and not-measurable (the default, "not measured here"). Never let silence become a claim.

**Vendor data is a YARDSTICK, not a source** — with one operator-authorised exception:
`in_bus_headroom_miso_vendor` (MISO headroom only), isolated, stamped
`provenance_class='vendor_licensed_proxy'`, and removable in one commit. The licence lapses late
2027. `benchmark_vs_orennia.py` still writes markdown only.

**Never `git add -A`.** Stage explicit paths. **Use a commit-message FILE** — backticks and quotes
in `-m` get eaten by the shell.

**After ANY front-end change:** `python scripts/stamp_assets.py`, then `python
scripts/audit_frontend.py`, then verify in a real browser, then **audit the deployed site** at
`https://ahenderson0233.github.io/indiana-application-decennial/index.html` (allow ~1 min for Pages;
a false negative is usually cache — re-fetch with no-cache).

⚠ **`app.js` is boot-critical** — a top-level throw kills the entire map console, and this repo has
a recorded instance. **Parse-verify it in a browser BEFORE pushing.** The map does **not** boot in a
headless sandbox (environmental, confirmed twice); `map` exists but `getStyle()` throws. Test what
you can without it — `PRESET_GAPS`, `METRIC_LEGEND`, `row()` — and say plainly what you could not.

---

## WHERE THE OTHER WORKSTREAMS STAND — do not re-litigate these

**Bus parity (G40/G45/G46).** PJM case 23 is the vendor's exact case. The old "we overshoot the
vendor 88–98% vs 39.3%" alarm was **a mismatched population**, not a rule error — like-for-like the
vendor's PJM tier-0 withdrawal is 93.9%, median 220 MW. **The real blocker is placement:** only ~227
of 1,826 AEP buses can be placed. **Nobody has PJM coordinates, including the vendor** — 0 of 298
PJM buses are ISO-sourced and they estimate 91.9%. MISO placement is **borrowed, not solved**: 9,608
buses come from MISO's own published POI data, and the 0.0 mi agreement with the vendor proves
**shared provenance, not competence**. G46 has the method to build, ordered by trustworthiness:
queue-generator coincidence (a join), breaker-branch topology, then gated string matching.

**MISO parity is not reachable** — DPP-2025 is CEII and four independent sweeps proved no public
route. Do **not** re-probe CartoVista or giqueue, and do not buy a trial.

**Open UI items:** G39 (screener → map deep-link and dossier dropdown), G43 (layers not clipped at
the border), G48 (an existing data centre should read green — groundwork measured: opposition is 0
in 61 of 92 counties), G50 (the MISO bus data reaches no surface; the dossier still says "not
resolved" for the serving utility), G52 (map legend), G53 (withdrawn queue as a seller-intent
signal).

---

## HOW I WANT YOU TO WORK

- **Verify, do not inherit.** The 2026-08-18 session disproved several inherited claims *and two of
  its own*: "Duke HLF is correctly excluded on its ceiling" (a floor misread as a ceiling, which
  hid a real error) and "IP-LL is the best-behaved schedule" (its energy leg was $0).
- **Measure before you change, and re-measure after.** Report the numbers, not the intention.
- **Say what you could not verify.** An honest gap beats a confident guess every time.
- **Commit in small, described steps**, and update `docs/BACKLOG.md` in the same commit — the index
  is the contract, and an item that exists only in prose is invisible in practice.
- **Checkpoint after each completed item**, and push.
- If you find a defect in something I asked for, **tell me the measurement**, not just the
  conclusion.

**Start by** telling me what the checkpoint printed, what you read, and your plan for action item A
— the schedules showing `$0` for an entire column.
