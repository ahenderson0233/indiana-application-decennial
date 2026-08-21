# NEXT SESSION — paste everything below this line as your first message

Continue the Indiana siting-intelligence application.
Repo: `C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial`
(GitHub `ahenderson0233/indiana-application-decennial`, branch `main`)

---

## ⛔ DO THESE FOUR THINGS FIRST. Propose nothing before you have.

### 1. Is the PJM harvest alive?

```bash
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | Where-Object { $_.CommandLine -like '*pull_pjm*' } | ForEach-Object { 'PID ' + $_.ProcessId + ' :: ' + $_.CommandLine }"
```

⚠ **A count of 2 is almost always your own command self-matching.** Confirm by parentage.

**If nothing is running, resume. This one command resumes, continues AND repairs, and is safe to
run even while one is going** — it polls for the ABSENCE of a QueueScope process:

```bash
powershell -ExecutionPolicy Bypass -File scripts\run_pjm_ladder.ps1
```

⛔ **NEVER start a second QueueScope process.** ⛔ **NEVER delete `data/`** — the batch markers live
there and deleting them forces a duplicating re-harvest; **archive, never delete**. ⛔ **Owner is
1568, not 739** — 739 loads **0 rows and exits successfully**.

⛔ **DO NOT TRUST ANY RUNG LIST IN A DOCUMENT — MEASURE IT.** The ladder advanced four times during
the last session and its PID changed with it. `python scripts/audit_handoff_docs.py` prints the
live complete/short split.

### 2. Start a web server, or every page hangs

```bash
python -m http.server 8123 --directory "C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
```

⚠ A dead server looks exactly like a code bug. ⚠ **And hard-reload with a cache-busting query** — a
stale page served an old `common.js` last session and brand-new code was "missing" for three probes.

### 3. The checkpoint and the ledger audits

```bash
python scripts/checkpoint.py
python scripts/audit_backlog_state.py
python scripts/audit_backlog_truth.py
python scripts/audit_handoff_docs.py
python scripts/audit_handoff_consistency.py
```

**Expect 4 checkpoint failures and expect all four to be correct:** the **wiring census** (⭐ the
END STATE, not a gap — every unreached object carries a measured reason and the worklist is 0; the
durable check is `0 unclassified`), the **honesty audit's 1 known failure**, **unregistered ladder
rungs** the running harvest created since the last registration pass, and ⭐ **`signal display`, a
NEW audit that is red on purpose** — 6 SI signals carry no `corpus_rows`, so the loss between what
we hold and what we place cannot be computed for them. That is G150's remaining work and the
checkpoint is supposed to keep shouting about it until it is done.

⛔ **DO NOT SILENCE THE SIXTH.** `in_si_signal_coverage` already held these numbers for weeks and
nothing ever failed on them, which is exactly why the operator reported the problem twice and saw
no change. A figure in a table that no check reads is a note, not a control.

⭐ **The checkpoint runs ELEVEN audits.** The newest are `spelling`, `gate/preference
consistency` and `handoff consistency` — the last one checks that the ledger, this prompt and the
handoff tell the same story about the same G-row, and it caught G29 being listed as PARTIAL in two
documents while the ledger called it DONE. All three must PASS. ⛔ Anything else failing is real.

### 4. Read, in this order

| # | file | why |
|---|---|---|
| 1 | `docs/SESSION_START.md` | standing rules and the governing principle |
| 2 | ⭐ **`docs/HANDOFF_2026-08-21.md`** | **THE CURRENT ONE.** §1 is the unfinished work; §3 every parcel figure that moved; §4 the instrument failures |
| 3 | ⭐ **`docs/BACKLOG.md`** | **WHERE EVERY UNFINISHED ROW STANDS** opens with G130 and the seven things left in it |
| 4 | ⭐ `docs/COMPARABLE_TOOLS.md` | what this product should look like; §3 names the ONE question each page answers |
| 5 | ⭐ `docs/RESCRAPE_LEDGER.md` | **generated** — which loaders re-run, how often, safely, and what each clip drops |
| 6 | `docs/UNWIRED_CLASSIFICATION.md` | **generated** — why each unreached object is unreached |

⚠ `HANDOFF_2026-08-20d.md` and earlier are **HISTORY**. Read them for *how*, never for *what is true
now* — §3 of the current handoff lists the figures they get wrong.

---

## ⛔ START HERE — THE SI SIGNALS ARE NOT SHOWING WHAT WE HOLD (G150)

**Operator, 2026-08-21:** *"Many of our SI signals still aren't representative of what we actually
hold… we should really extensively audit whether or not we are displaying all of the sites that we
have in BQ… this issue has been partially addressed in the past and I have seen no visible
changes."* Then, after the WARN work: *"we have the wrong grain on MANY of the SI signals, and we
should target those next."*

⭐ **G130 IS CLOSED** — planned upgrades shipped, verified in a browser, and the four documentation
errors it exposed are corrected. Do not reopen it.

### What was done on G150, and what it proves about the rest

⭐ **WARN went from 2 placed parcels to 51.** `in_si_warn_normalised` holds **1,220** Indiana
notices and **carries no address column at all** — so the signal was never *placeable*, not
"filtered down". The address is in the filing PDF. `extract_warn_addresses.py` reads them,
`build_warn_placement.py` joins them to parcels.

⛔ **AND THE METHOD IS THE POINT, because the operator had to correct me four times to get it:**
1. *"the addresses are seen in the actual filings"* — there is a source we were not reading.
2. *"the two addresses in the header are NOT the site location"* — the DWD address and the local
   **chief elected official** are in nearly every letter, and the second is in the RIGHT TOWN.
3. *"each WARN notice is published differently… Some may NOT even contain the address of the site"*
   — Block, Inc. files "Remote, Indiana 46032" and has no premises at all.
4. ⭐ *"you should probably manually explore a large sample of these PDFs before you write a
   one-size-fits-all code"* — **this is the instruction that mattered.** Reading 34 filings killed
   the first design: multi-site notices are common (Franciscan lists four hospitals, Head Start
   seven centres), rural addresses have no street suffix (`1501 County Road East 200 North`), and
   the facility phrase varies per FILER, not per county.

⚠ **Then measuring my own misses one at a time found MY normaliser was the bottleneck** — I had
folded three street suffixes and no directionals, so `Bluffton Road` never met `BLUFFTON RD`.
Fixing that took placement 21 → 37 → **51**.

### ⭐ DO THE SAME THING FOR THE OTHER SIGNALS — THAT IS THE JOB

`python scripts/audit_signal_display.py` is new, is in the checkpoint, and **fails on 6 signals**:

| what it says | why it matters |
|---|---|
| **6 signals carry NO `corpus_rows` at all** — D4_tax_delinquency, D5_unsafe_building, D5_vacant_board_order, D5_abandoned_building, D21_demolition_order, D22_environmental_violation | the loss between held and placed **cannot even be computed** for them. Fix the coverage build first, then measure |
| `D19_warn` still reads 2 | `in_si_signal_coverage` has not been rebuilt since the placement landed — rebuild it and it should read 51 |
| `D12_code_violation` 747,211 → 23,145 | ⭐ **CORRECT AND DELIBERATE.** Operator: *"we filtered down for C&I only, and require 3+ violations."* ⚠ But the artefact only confirms HALF: `excluded_residential` (16,295) and `excluded_low_severity` (4,741) are enforced; the **3+ minimum is NOT** — the admitted set runs `min_events = 1`. Resolve which is true |

⛔ **SELECTIVITY IS NOT THE DEFECT — SILENCE IS.** Operator: *"We filter down many of the SI
signals, and this should be known and understood throughout."* A signal that admits 2,109 of
747,211 is working as designed the moment somebody can say why. The audit only fails on rows where
nobody wrote the reason down.

⚠ **`in_si_warn_placed` is built and NOT yet consumed by the SI pipeline** — it is classified
`pending_pipeline_join`, deliberately, because a table that exists is not a table that reaches a
reader. Wiring it is the first concrete task.

⭐ **THE OPERATOR HAS APPROVED A READ-ONLY RESCRAPE REHEARSAL** (G140): *"Yes, it is fine to read
only first."* ⛔ Do not execute writes — 3 loaders are `append_only` and 2 read their own output,
so a naive re-run double-counts. Rehearse, report per loader, then ask.

---

## THE BACKLOG — 101 DONE · 16 PARTIAL · 29 OPEN

⚠ **OPEN JUMPED 8 → 29 AND THAT IS NOT A REGRESSION.** The operator opened **21 new rows** on
2026-08-21 in four batches — G131–G151. Nothing reopened; the surface of the work grew.

**Eight rows closed last session** — G53, G122, G123, G124, G125, G127, G128, G129 — every one
re-verified against the artefact on 2026-08-21. Two advanced with their question answered: G126 (the
bus gazetteer ceiling). ⭐ **G130 then CLOSED on 2026-08-21** — planned upgrades shipped and verified.
⭐ **G132, G133, G134 and G138 also closed on 2026-08-21**, and G150 advanced (WARN placement 2 → 51).

### AFTER G130, in priority order

**① THE DLGF GATEWAY PURCHASE — the highest-value action left, and it is yours, not code's.**
It unblocks **G70** (parcel owner), **G71** (zoning), **G104** (assessed value) and **G90(b)** at
once. All are 100% NULL for Indiana in both our clip and the national parent, which holds 40.8M
assessed values for 43 other states. **Not a clip defect; re-clipping will not help.** ⭐ G70 has
shrunk twice — its building-use half and its address half both shipped — so only OWNER remains.

**② THE DEFERRED SCRAPES.** G102 (state surplus, likely IDOA) · G103 (water utilities, EPA SDWIS) ·
G114's remaining ~1,464 PJM bus coordinates · G15's cost re-extraction from the workpaper header
row. ⭐ **Send to an Opus (non-Fable) agent** and brief it with the write boundary, no-CAPTCHA /
no-UA-spoof and BLOCKED-is-a-success, because **agents do not inherit them**.

**③ TWO DECISIONS THAT ARE YOURS, NOT CODE'S.**
- ⚠ **G129 option (b)** — a per-filter GATE/PREFERENCE toggle instead of the fixed published
  classification. More honest and more work. Option (a) is live: 18 gates, 14 preferences, badged,
  259 near misses recovered.
- ⚠ **How aggressive should the G122 exclusion be?** 3,159 road and 1,861 rail corridors are gone.
  A further **28,187 parcels are ribbon-shaped with NO road along them** — creeks, pipeline
  easements, genuinely long narrow industrial land — and they are REPORTED, not excluded.
  ⛔ Widening the shape threshold until they disappear is how a heuristic eats its own corpus.

**④ EVERYTHING ELSE PARTIAL is honest about its remainder** — G6, G15, G21, G26, G27, G40, G45,
G46, G51, G55, G62, G90, G106, G113, G114, plus G126 and G130 above. **Seventeen rows**, and
that is the whole PARTIAL set. The backlog table says what each still needs.

⚠ **One row to look at even though the ledger calls it DONE:** `audit_backlog_truth.py` probes
**G29** and reports that transmission, substation and water distances ship exact `ST_DISTANCE`
while the **BUS distance is still computed client-side on the map console**. The ledger says
DONE, the artefact says half. Decide which is right before relying on a bus distance from the map.

---

## ⛔ SIX THINGS THAT WILL MISLEAD YOU

**① Every parcel figure moved.** Candidates **531,325** (not 532,693), flagged **23,766** (not
23,795), GRID binds **189,807**, LAND binds **72,725**, substations-on-a-parcel **1,820**. ⚠ Median
substation distance **rose** 2.08 → **2.15 mi** because the parcels removed were corridors that hug
infrastructure — a number moving the unhelpful way after a correction usually means it was real.

**② THE ADDRESS IS STATEWIDE.** Three documents said Marion-only. `energy.parcels_in` carries the
DLGF property address on **98.4% of Indiana parcels across all 92 counties**.

**③ "Ribbon parcels with a road" is 25, not 184** — and that is the fix working. The other 159 were
excluded as rights-of-way.

**④ The wiring census FAILING is correct** and is not work.

**⑤ `IS` / `M4 - Project in Service` is ALREADY BUILT** — 9,163 of 15,443 PJM RTEP rows — and is
**not** future capacity. It is off by default on the map.

**⑥ The screener carries TWO capacity figures.** `mw_dc` is LAND; `deliv_wd_mw` is GRID. Never
collapse them.

---

## ⛔ TRAPS — read §4 and §5 of the handoff in full

1. ⛔ **NEVER WRITE A REGEX THROUGH A SHELL HEREDOC. NINE occurrences, several last session.** `\n`
   became a literal newline; `\b` became literal backspace bytes inside a live JS regex; and one
   heredoc edit silently applied HALF of a two-part change. ⭐ Edit tool, module level, self-test.
2. ⛔ **BUILDS MAY READ `energy`; EXPORTS MAY NOT.** The checkpoint enforces it.
3. ⛔ **A HARDCODED VERDICT IS NOT A PROBE.** `audit_backlog_truth.py` called G53 OPEN for two
   sessions after it shipped, because that branch printed a verdict it had already decided.
4. ⛔ **AN AUDIT REGISTERED BUT NOT DISPATCHED RUNS AND REPORTS NOTHING.**
5. ⛔ **A PINNED LITERAL TURNS A MEASUREMENT INTO A CONSTANT** — an audit asserted `== 184` and
   failed when the thing it measures was correctly fixed.
6. ⛔ **A LOOKALIKE IS SOMETIMES A KEY** — `fits_mw_datacentre_at_4_per_acre` is a CSV column name;
   `circle-color` and 91 siblings are MapLibre paint properties.
7. ⛔ **REMOVE A CONTROL AND ITS REGISTRY ENTRY IN ONE CHANGE.**
8. ⚠ **A value vocabulary lies** — FRPP `state_code` is `'18'`; WARN `notice_class` is UPPER-CASE;
   `nearestBus` wants lower-case; roads use `geom`; and **PJM dates are `M/D/YYYY` while MISO's are
   ISO, in one column**.
9. ⚠ **Cumulative categories are not buckets** (Drought D0 means "D0 or worse").
10. ⚠ **A statistic true of 98% of the corpus tells a siter nothing.**

**A clean, alarming or UNCHANGED number is a claim about your INSTRUMENT first.**

---

## THE STANDING RULES

`energy-platfrom.energy` is **READ-ONLY**; everything goes to `energy-platfrom.indiana_app`. The one
permitted write is an APPEND to `energy.registry_sources`. **Restate this in every agent brief —
agents do not inherit it.** ⚠ **Builds may read `energy`; EXPORTS MAY NOT.**

**Every table gets a `_registry` row in the same run** with `source`, `method` and a verbatim
`RE-SCRAPE COMMAND:`. ⭐ `docs/RESCRAPE_LEDGER.md` also records, per object, whether re-running is
**safe** (replace_safe / append_only / unknown), how often the PUBLISHER changes, and which parent
columns the clip drops.

**⛔ Check the warehouse before you explore or scrape. Read the schema. Never guess a column name OR
A VALUE VOCABULARY.**
**Unpublished is NULL, never 0** — but a **stated** zero is a fact.
**⚠ EXCLUDE `parcels_in/080500000047000018`** from every spatial join (D85); prove it by fan-out.
**⛔ No centroid where a footprint exists.** ⚠ The G125 display coordinate is the one exception and
is quarantined: `map_lat`/`map_lon` are for the reader's eye and feed no distance.
**Never `git add -A`.** **Use a commit-message FILE.**

**After ANY front-end change:** `python scripts/stamp_assets.py` → `audit_frontend.py` →
`audit_js_duplicates.py` → `audit_page_controls.py` → `audit_spelling.py` → **hard-reload and verify
in a browser**. ⭐ The map boots headless via `scripts/boot_map_harness.js`.

---

**Start by** telling me whether the harvest is alive, what the checkpoint printed, and what the
ledger audits printed — then what you read, then your plan.
⭐ **Lead with G130** — finishing the grid upgrades — unless I say otherwise.
