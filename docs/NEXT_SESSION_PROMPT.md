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
```

**Expect 3 checkpoint failures and expect them to be correct:** the **wiring census** (⭐ the END
STATE, not a gap — every unreached object carries a measured reason and the worklist is 0; the
durable check is `0 unclassified`), the **honesty audit's 1 known failure**, and **unregistered
ladder rungs** the running harvest created since the last registration pass.

⭐ **The checkpoint runs TEN audits.** `spelling` and `gate/preference consistency` are the newest
and must PASS. ⛔ Anything else failing is real.

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

## ⛔ START HERE — FINISH G130. THE GRID UPGRADES ARE NOT DONE.

**Operator, 2026-08-21:** *"if you didn't FULLY complete the grid upgrades, finishing that should be
our top priority in the next session, and should be at the top of the backlog."*

⛔ **G130 was marked ✅ DONE and that was an over-claim**, caught by probing the artefact during the
handoff audit. It is the **fourth** row this project has closed while still carrying live work
(after G53, G90, G96). It is now 🟡 PARTIAL and it is the first job.

⭐ **What already works — do not rebuild it:** `in_planned_upgrades` unifies PJM RTEP, MISO MTEP and
the IURC utility grid plans into **1,878 projects, 700 placed (37.3%)**, each with an uncertainty
ring keyed on how well the LOCATION is known; 81 A-to-B rebuilds draw as corridors; the map layer is
violet / hollow / dashed so planned work never reads as existing steel; the grid page has a
generated coverage card; the screener carries the nearest future upgrade for **513,409 of 531,325
sites**. Verified live in a browser.

**What is left, in the order to do it:**

| # | do this | why |
|---|---|---|
| 1 | fold in **`in_pjm_rtep_cost_allocations`** (375 rows) | joins cleanly on `upgrade_id` — the cheapest win, and it is cost attribution we already hold |
| 2 | fold in **`in_miso_dpp2025_ph1_project_costs`** (202 rows) | **$29,522M across 56,043 MW, ~$527k per MW** — the best answer we hold to *what will interconnection cost*, and it reaches no surface. Needs a project→POI key |
| 3 | fold in **`in_rto_expansion`'s 774 MISO rows** | ⚠ a DENOMINATOR and COST gap, not new placements — those rows carry no endpoint. Including them honestly moves coverage from 700/1,878 to about **700/2,652**, and that is the truthful number |
| 4 | ⭐ **clip TIGER PLACE for Indiana** | `municipality_centroid` currently resolves against the 406 towns that happen to host a substation. A real place gazetteer makes every incorporated place matchable **and** gives a polygon to size the ring from instead of a flat 5 miles. `scripts/load_tiger_all_roads.py` is the template — 92 counties, 0 blocked, 82 seconds |
| 5 | the **518 unresolved RTEP location strings** | `TWIN BRANCH`, `EAST ELKHART`, `MAGLEY`, `BLUFF POINT` are real Indiana stations the gazetteer lacks under those exact strings; plus spelling variants (`RANDOLF`/`RANDOLPH`) and a comma form (`SOUTH BEND, TWIN BRANCH`) the splitter does not handle. ⛔ Refuse below a confidence threshold |
| 6 | **`county_centroid` fires 0 times** | wired and unfed — (4) or a county field from the filings feeds it |
| 7 | **499 of 618 utility grid plans unplaced** | 297 are rows the workpaper parser cannot read (that half is **G15**); 199 name a station the gazetteer does not hold (**G62**'s ceiling) |

⚠ **Four of my own defects were found by measurement while building this**, which is the reason to
distrust the first number it produces: a **unit error** (PJM publishes `cost_estimate` already in
$M; dividing by 1e6 made a fully populated column read "not published"), a **date error** (PJM ships
`M/D/YYYY`, MISO ships ISO, in one column), a corridor midpoint averaged from unmatched name
fragments, and a build whose summary contradicted its own export.

---

## THE BACKLOG — 100 DONE · 17 PARTIAL · 8 OPEN

**Eight rows closed last session** — G53, G122, G123, G124, G125, G127, G128, G129 — every one
re-verified against the artefact on 2026-08-21. Two advanced with their question answered: G126 (the
bus gazetteer ceiling) and G130 (above). ⭐ **OPEN halved, 16 → 8.**

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

**④ EVERYTHING ELSE PARTIAL is honest about its remainder** — G6, G15, G21, G26, G27, G29, G40,
G45, G46, G51, G55, G62, G90, G106, G113, G114. The backlog table says what each still needs.

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
