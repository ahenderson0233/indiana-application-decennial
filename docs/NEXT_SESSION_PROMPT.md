# SESSION START — paste everything below this line

Continue the Indiana siting-intelligence application.
Repo: `C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial`
(GitHub `ahenderson0233/indiana-application-decennial`, branch `main`)

---

## ⛔ DO THESE FOUR THINGS FIRST. Propose nothing before you have.

### 1. Is the PJM harvest alive?

```bash
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | ForEach-Object { 'PID ' + $_.ProcessId + ' PPID ' + $_.ParentProcessId + ' :: ' + $_.CommandLine }"
```

⚠ **Confirm by PARENTAGE, not by count** — your own command self-matches. A live harvest looks like `pull_pjm_injection.py --case 23 … --owner 1568` whose parent is `run_pjm_ladder.ps1`. ⭐ **It survived a machine restart on 2026-08-21 and kept advancing**, so check before assuming it died.

**If nothing is running, resume. This one command resumes, continues AND repairs, and is safe to run even while one is going** — it polls for the ABSENCE of a QueueScope process:

```bash
powershell -ExecutionPolicy Bypass -File scripts\run_pjm_ladder.ps1
```

⛔ **NEVER start a second QueueScope process.** ⛔ **NEVER delete `data/`** — the batch markers live there; **archive, never delete**. ⛔ **Owner is 1568, not 739** — 739 loads **0 rows and exits successfully**.

⛔ **DO NOT TRUST ANY RUNG LIST IN A DOCUMENT — MEASURE IT.** `python scripts/audit_handoff_docs.py` prints the live complete/short split.

### 2. Start a web server, or every page hangs

```bash
python -m http.server 8123 --directory "C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
```

⚠ A dead server looks exactly like a code bug. ⚠ **Hard-reload with a cache-busting query.**
⭐ The map does **not** boot in a hidden browser pane (Chrome pauses rAF). `scripts/boot_map_harness.js` exists for exactly that — paste it and `await bootMapHarness()`.

### 3. The checkpoint and the ledger audits

```bash
python scripts/checkpoint.py
```
```bash
python scripts/audit_backlog_state.py
```
```bash
python scripts/audit_handoff_docs.py
```
```bash
python scripts/audit_handoff_consistency.py
```

**Expect 3 checkpoint failures and expect all three to be correct:** the **wiring census** (⭐ the END STATE, not a gap — every unreached object carries a measured reason and the worklist is 0), the **honesty audit's 1 known failure**, and **unregistered ladder rungs** the running harvest created.

⭐ **The checkpoint runs SIXTEEN audits.** Four are new as of 2026-08-21/22, and every one exists because something shipped that nothing was looking at:
- **`si upstream width`** — every upstream SI source is clipped Indiana-wide at full width.
- **`signal reality`** — regenerates `docs/SIGNAL_REALITY.json`. ⛔ It exists because that file is on the required reading list, is labelled *generated*, and had gone **five days without regenerating** while still reporting `D19_warn` at 2 parcels.
- **`legend colours`** — every swatch the app draws resolves to a real colour.
- **`bus placement`** — no unplaceable bus binds a published figure, and no row above upgrade tier 0 claims to be tier 0.

### 4. Read, in this order

| # | file | why |
|---|---|---|
| 1 | `docs/SESSION_START.md` | standing rules and the governing principle |
| 2 | ⭐ **`docs/HANDOFF_2026-08-22.md`** | **THE CURRENT ONE.** §1 the two operator rulings; §3 five findings worth carrying; §4 my own instrument failures; §6 what is left |
| 3 | ⭐ **`docs/BACKLOG.md`** | the top section names every unfinished row and why |
| 4 | ⭐ `docs/COMPARABLE_TOOLS.md` | §3 names the ONE question each page answers |
| 5 | ⭐ `docs/RESCRAPE_LEDGER.md` | **generated** — which loaders re-run, safely, and what each clip drops |
| 6 | `docs/UNWIRED_CLASSIFICATION.md` | **generated** — why each unreached object is unreached |

⚠ `HANDOFF_2026-08-21c.md` and earlier are **HISTORY**. 21b's §1 — *"we read a reduction"* — is **CLOSED**; do not re-open it.

---

## ⭐ START HERE — **G158**, TIER 0 ONLY, WITH UPGRADES AS SOMETHING THE USER ADDS

**Operator, 2026-08-22, and this is the first task after the reading above:** *"I would like ONLY
tier 0 to display to the user, with the ability for the user to add in upgrades, or see what each
upgrade would cost and the amount of headroom it would add (either within the popup, the screener
display, or the map console)."*

⭐ **READ THE OPERATOR'S OWN REFERENCE TOOL FIRST:**
`https://ahenderson0233.github.io/indiana-bus-analysis/`

⛔ **This reverses the current selection rule.** `build_bus_capacity_tier0_v2.py` takes the lowest
NON-OVERLOADED tier, so **59% of injection buses and 69% of withdrawal buses publish above tier 0**,
and **54.1% of every parcel deliverable figure requires network upgrades**. G143 made that visible
with a caveat; the ruling is that it should not be the headline at all.
⚠ **Tier 0 is frequently 0 MW or already overloaded**, so the honest headline for many buses
becomes zero. That is the point, not a regression — say *"0 MW today; N MW at tier K"*.
⭐ **We already hold every tier** (`in_bus_headroom_miso_vendor`, one row per tier per direction);
only the SELECTION changes. ⛔ **But check the cost source before promising a price per upgrade
(G25)** — `in_miso_dpp2025_ph1_project_costs` and `in_pjm_rtep_cost_allocations` are not keyed to a
bus upgrade tier, so cost may only be answerable as a $/MW benchmark.

### Then, in the order I would take them

| # | row | why this order |
|---|---|---|
| ① | ⭐ **G156** — 16 of the 18 full-width clips are still unexploited | **the largest open row.** G152 clipped 18 sources and only two produced a signal. `in_si_up_ibtr_appeals` alone carries `stateParcelNumber`, `locationAddress` AND `petitionerName` on **10,071 parcels** — an OWNER NAME, which is the thing five other rows are blocked on |
| ② | **G155** — Indiana distribution-level substations | the operator says we hold them; I could not find them. Every Indiana source is transmission-level and the AEP hosting-capacity tables are **Ohio/Michigan only**. Search by content |
| ③ | ⛔ **G159** — floating buses are excluded from the calculation and INCLUDED in the display | **57,359 parcels** are told their nearest bus is one our own model cannot attach to a substation or a line. Not false — *unqualified*. Labelling it costs nothing and does not wait on G155 |
| ④ | **G157** — 93 bus names are shared by more than one bus | small and live: `wd_limiting_end` stores a NAME, so the screener's "Limited at" can be ambiguous. Carry `bus_id` beside it |
| ⑤ | **G140**'s non-SI half | 74 objects the rescrape ledger marks `unknown` idempotency, 49 unresolved. ⛔ 3 loaders are append-only and 2 read their own output |
| ⑥ | **G135** — Orennia bus coverage / FLOSM | ⚠ **its premise changed.** G143 showed our positions MATCH the vendor's to six decimals; only coverage remains, and FLOSM is the untried half |
| ⑦ | **G102 · G103** | acquisitions. ⭐ Send to an **Opus (non-Fable) agent**, briefed with the write boundary, no-CAPTCHA / no-UA-spoof and BLOCKED-is-a-success, because **agents do not inherit them** |

**Blocked on a purchase, not on engineering:** **G70 · G71 · G104 · G90(b) · G147.**
⭐ G152 *measured* this rather than repeating it: `energy.si_d5_vacancy_derived` carries `parcel_owner`, `assessed_value`, `land_use`, `zoning` and `year_built` columns that are **100% NULL on all 967,366 Indiana rows**. The DLGF Gateway purchase is confirmed as the only route.

### ⭐ The SI signals and the grid batch are BOTH done — do not re-open them

**Closed 2026-08-21/22:** G131, G136, G137, G141, G142, G143, G144, G145, G146, G148, G149, G150, G152, G153, G154. The spine carries **27 signals**, `audit_signal_display.py` reports **0 unexplained losses**, and `audit_si_upstream_width.py` proves **18 clips at full width, 2,221,637 Indiana rows**. ⛔ If you think a source is narrow, run the audit — do not re-derive the answer.

---

## THE BACKLOG — 121 DONE · 16 PARTIAL · 17 OPEN

---

## ⛔ EIGHT THINGS THAT WILL MISLEAD YOU

**① THE SI FIGURES ALL MOVED.** `D19_warn` **57** parcels reached / 43 admitted. Declared intent **865 parcels, 800 with no distress signal at all**. Two new signals — **D28_cmbs_loan_distress** and **D29_anchor_tenant_exit** — plus **I3_land_bank (691 parcels)**.
**② 54.1% OF EVERY DELIVERABLE CAPACITY FIGURE REQUIRES NETWORK UPGRADES.** The MISO source publishes one capacity per upgrade tier 0–4 and our rule takes the lowest non-overloaded one. It is now disclosed on the row; it was not before. A figure at tier 4 is not capacity available today.
**③ THE NEAREST LINE IS NOT THE BEST LINE.** The average parcel has **5.11** capacity-bearing lines within 3 miles, and **91,836 parcels cross 300 MW** on a line that is not their nearest.
**④ A GENERATED DOCUMENT CAN STILL BE STALE.** `SIGNAL_REALITY.json` was five days old and on the required reading list. Assume the same of anything labelled *generated* whose generator you cannot find in `checkpoint.py`.
**⑤ THE ADDRESS IS STATEWIDE** — 98.4% of Indiana parcels, all 92 counties.
**⑥ The wiring census FAILING is correct** and is not work.
**⑦ The screener carries TWO capacity figures.** `mw_dc` is LAND; `deliv_wd_mw` is GRID.
**⑧ DISTANCE TO THE NEAREST MILITARY SITE IS GONE (G146)** — control, both predicates, chip, detail row, badge, glossary and both payload columns. `in_land_gate_parcel` still computes it. The table is the record, the payload is the product, and they are allowed to differ.

---

## ⛔ TRAPS

1. ⛔ **NEVER WRITE A REGEX THROUGH A SHELL HEREDOC. Nine occurrences.** Edit tool, module level, self-test. ⚠ Python heredocs also eat `\u` escapes.
2. ⛔ **BUILDS MAY READ `energy`; EXPORTS MAY NOT.**
3. ⛔ **A HARDCODED VERDICT IS NOT A PROBE — AND NEITHER IS A HARDCODED WINDOW.** `audit_legend_colours.py`'s first paint check read 400 characters after a match and found a different layer.
4. ⛔ **AN AUDIT REGISTERED BUT NOT DISPATCHED REPORTS NOTHING.**
5. ⛔ **A PINNED LITERAL TURNS A MEASUREMENT INTO A CONSTANT** — three times now.
6. ⛔ **`re.I` CANCELS A CASE-SENSITIVE GUARD.**
7. ⛔ **REMOVE A CONTROL AND ITS DATA IN ONE CHANGE** — G146 is the worked example.
8. ⛔ **A SAMPLE CANNOT SEE A SPARSE FIELD** — exports omit falsy keys, and an EMPTY ARRAY is neither `None` nor `False`, so it survives every "drop the null" filter.
9. ⛔ **COMPARE DECODED TEXT TO DECODED TEXT.**
10. ⛔ **TWO CHECKS AGREEING ON THE SAME WRONG ASSUMPTION IS NOT VERIFICATION.** A clip matched **zero rows and passed its own assertion**, because the predicate and the check both said `state='IN'` on a table that spells it `'Indiana'`. **A zero-row result is a broken instrument until proven otherwise.**
11. ⛔ **A WAREHOUSE CHECK THAT GREPS FOR THE NAME A SOURCE *OUGHT* TO HAVE IS NOT A WAREHOUSE CHECK.** We "held no land banks" for weeks; we held two, filed under `landbank` and `surplus`. ⚠ And **a table named for a utility is not a clip of that utility's home state** — `hca_aep_im_mi_*` is Ohio and Michigan.
12. ⛔ **AN UPLIFT MEASURED OVER THE WRONG POPULATION IS NOT AN UPLIFT.** G142's first build compared 3.55M parcels against a table covering 531,325 and reported 2.8M phantom gains.
13. ⛔ **A DEAD ARGUMENT LOOKS EXACTLY LIKE A WORKING ONE.** `row(k, v, absent)` silently swallowed a fourth argument; `${color}` on an undeclared name threw and killed a whole panel.
14. ⚠ **`reached > held` IS ALWAYS THE INSTRUMENT**, never the data.
15. ⚠ **NEVER KEY A BUS BY ITS NAME** — 93 names are shared by more than one bus (G157).

**A clean, alarming or UNCHANGED number is a claim about your INSTRUMENT first.**

---

## THE STANDING RULES

`energy-platfrom.energy` is **READ-ONLY**; everything goes to `energy-platfrom.indiana_app`. The one permitted write is an APPEND to `energy.registry_sources`. **Restate this in every agent brief — agents do not inherit it.** ⚠ **Builds may read `energy`; EXPORTS MAY NOT.**

**Every table gets a `_registry` row in the same run** with `source`, `method` and a verbatim `RE-SCRAPE COMMAND:`.
**⛔ Check the warehouse before you explore or scrape. Read the schema. Never guess a column name OR A VALUE VOCABULARY.**
**Unpublished is NULL, never 0** — a **stated** zero is a fact. ⚠ And a `0` can BE the null sentinel: CMBS occupancy publishes `0` for "not reported", which invented 705 distressed buildings before it was caught.
**⚠ EXCLUDE `parcels_in/080500000047000018`** from every spatial join (D85); prove it by fan-out.
**⛔ No centroid where a footprint exists.** G125's `map_lat`/`map_lon` are the quarantined exception.
**Vendor data is a yardstick, never a source** — the one exception is `in_bus_headroom_miso_vendor`, whose licence lapses **late 2027**.
**Never `git add -A`.** **Use a commit-message FILE.**

**After ANY front-end change:** `stamp_assets.py` → `audit_frontend.py` → `audit_js_duplicates.py` → `audit_page_controls.py` → `audit_spelling.py` → **hard-reload and verify in a browser**.
⭐ **After ANY build touching the spine: re-export sites, the screener AND si surfaces**, or the warehouse improves and no reader sees it.

---

**Start by** telling me whether the harvest is alive, what the checkpoint printed, and what the ledger audits printed — then what you read, then your plan.
⭐ **Lead with G139**, then G156, unless I say otherwise.
