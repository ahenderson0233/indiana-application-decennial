# SESSION START — paste everything below this line

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

⭐ **The checkpoint now runs FOURTEEN audits.** Two are new: **`si upstream width`** asserts every upstream SI source is clipped Indiana-wide at full width, and **`signal reality`** regenerates `docs/SIGNAL_REALITY.json`. ⛔ That second one exists because the file is on the required reading list, is labelled *generated*, and had gone **five days without regenerating** — it still said `D19_warn` admitted **2** parcels, the exact figure the operator complained about twice. **A generated document that no check reads is hand-written by whoever last ran the script.**

### 4. Read, in this order

| # | file | why |
|---|---|---|
| 1 | `docs/SESSION_START.md` | standing rules and the governing principle |
| 2 | ⭐ **`docs/HANDOFF_2026-08-21c.md`** | **THE CURRENT ONE.** §2 the four findings only full width could surface; §4 three format traps in one source; §6 my own instrument failures |
| 3 | ⭐ **`docs/BACKLOG.md`** | every unfinished row |
| 4 | ⭐ `docs/COMPARABLE_TOOLS.md` | §3 names the ONE question each page answers |
| 5 | ⭐ `docs/RESCRAPE_LEDGER.md` | **generated** — which loaders re-run, safely, and what each clip drops |
| 6 | `docs/UNWIRED_CLASSIFICATION.md` | **generated** — why each unreached object is unreached |

⚠ `HANDOFF_2026-08-21b.md` and earlier are **HISTORY**. 21b's §1 — *"we read a reduction"* — is **CLOSED**; do not re-open it.

---

## ⭐ START HERE — **G148**, THE 175 FLOATING BUSES

**G148** is first because G131 just handed it a named worklist. The operator asked me to fact-check
whether Orennia places its bus points on substations; measured across both substation corpora, the
median is **0.0 m** and 75.2% land within 50 m — but **175 of 1,731 (10.1%) are more than 2 km from
any substation**, and 1,730 of them are inside Indiana, so a cross-border artefact explains at most
one. Decide whether those 175 are a vendor artefact or a gap in our substation corpus, then make
the invariant an audit. ⭐ Our own placement is *better* where it exists: **89 of the 90 PJM buses
inside Indiana are within 250 m of a substation** — we have not placed worse, we have placed fewer.

⭐ **G131 and G149 closed 2026-08-21.** G131 is worth reading before touching the grid: three
operator rulings turned a correctness check into a 66% coverage gain, and the substation is a
BRIDGE (line → endpoint → substation → bus), never a validity test.

### Then the rest of the batch, in the order I would take it

| # | row | why this order |
|---|---|---|
| ① | **G131** — match buses to substations and transmission lines | a CORRECTNESS row: it asks whether the headroom we already publish is attached to the right asset. **G142 depends on it being right first** |
| ③ | **G148** — floating buses | ⭐ a testable invariant, so it should become an AUDIT: every placed bus within X metres of a substation or a line. ⚠ Measured: where a line end DOES resolve to a bus the median distance is **17 m**, so the matched ones are tight and the problem is the unmatched |
| ④ | **G143** — our MISO buses disagree with Orennia's **where we read Orennia's own table** | ⛔ sharper than G135: that is a defect in OUR derivation, not a coverage ceiling. Start from the named case, `16SUNNYS` |
| ⑤ | **G142** — all bus headrooms off BOTH ends of every nearby line | a real modelling correction; nearest-line is a bad proxy for interconnectable |
| ⑥ | **G141** — injection and withdrawal in the main popup | cheap, and it pairs with G29's open half (bus distance is still client-side on the map) |
| ⑦ | **G137** — MISO POI card to match the PJM load-headroom card | consistency, cheap |
| ⑧ | **G136** — Excel export on every table in three pages | ⚠ the aesthetic constraint is part of the requirement, so a button per table is probably the wrong answer. The screener's `s-export-xlsx` already works — generalise it |
| ⑨ | **G139** — community-sentiment decisions missed in the last few days | Howard and City of Elkhart votes (2026-08-17) and Marion MDC Proposal No. 238 (2026-08-19) are all now in the past |

### ⭐ The SI signals are DONE — do not re-open them

**All seven SI rows closed 2026-08-21: G144, G145, G146, G150, G152, G153, G154.** The spine now
carries **27 signals**, `audit_signal_display.py` reports **0 unexplained losses**, and
`audit_si_upstream_width.py` proves **18 upstream clips at full width, 2,221,269 Indiana rows**.
⛔ **DO NOT RE-OPEN THEM LOOKING FOR MORE COLUMNS.** The operator's ruling — *"even if a source
scrapes everything but one column, we still want to rescrape it for everything"* — has been
executed and is guarded by a checkpoint audit. If you think a source is narrow, run the audit.

**Blocked on a purchase, not on engineering:** G70 · G71 · G104 · G90(b) · **G147**.
⭐ G152 *measured* this rather than repeating it: `energy.si_d5_vacancy_derived` carries
`parcel_owner`, `assessed_value`, `land_use`, `zoning` and `year_built` columns that are **100%
NULL on all 967,366 Indiana rows**. The DLGF Gateway purchase is confirmed as the only route.

**Acquisitions, deferred:** G102 (state surplus) and G103 (water utilities). ⭐ Send to an **Opus
(non-Fable) agent**, briefed with the write boundary, no-CAPTCHA / no-UA-spoof and
BLOCKED-is-a-success, because **agents do not inherit them**.

---

## THE BACKLOG — 109 DONE · 16 PARTIAL · 24 OPEN

---

## ⛔ SEVEN THINGS THAT WILL MISLEAD YOU

**① THE SI FIGURES ALL MOVED.** `D19_warn` **57** parcels reached / 43 admitted (was 43/32).
Declared intent **865 parcels, 800 with no distress signal at all** (was 174/167). Two new signals:
**D28_cmbs_loan_distress** and **D29_anchor_tenant_exit**. **I3_land_bank: 691 parcels.**
**② A GENERATED DOCUMENT CAN STILL BE STALE.** `SIGNAL_REALITY.json` was five days old and on the
required reading list. It is now a checkpoint audit. Assume the same of anything else labelled
*generated* whose generator you cannot find in `checkpoint.py`.
**③ THE ADDRESS IS STATEWIDE** — 98.4% of Indiana parcels, all 92 counties.
**④ The wiring census FAILING is correct** and is not work.
**⑤ `IS` / `M4 - Project in Service` is ALREADY BUILT** and is not future capacity. Off by default.
**⑥ The screener carries TWO capacity figures.** `mw_dc` is LAND; `deliv_wd_mw` is GRID.
**⑦ DISTANCE TO THE NEAREST MILITARY SITE IS GONE (G146)** — control, both predicates, chip,
detail row, badge, glossary and both payload columns. `in_land_gate_parcel` still computes it. The
table is the record, the payload is the product, and they are allowed to differ.

---

## ⛔ TRAPS

1. ⛔ **NEVER WRITE A REGEX THROUGH A SHELL HEREDOC. Nine occurrences.** Edit tool, module level, self-test.
2. ⛔ **BUILDS MAY READ `energy`; EXPORTS MAY NOT.**
3. ⛔ **A HARDCODED VERDICT IS NOT A PROBE.**
4. ⛔ **AN AUDIT REGISTERED BUT NOT DISPATCHED REPORTS NOTHING.**
5. ⛔ **A PINNED LITERAL TURNS A MEASUREMENT INTO A CONSTANT** — three times now.
6. ⛔ **`re.I` CANCELS A CASE-SENSITIVE GUARD.**
7. ⛔ **REMOVE A CONTROL AND ITS DATA IN ONE CHANGE** — G146 is the worked example.
8. ⛔ **A SAMPLE CANNOT SEE A SPARSE FIELD** — exports omit falsy keys, and an EMPTY ARRAY is neither `None` nor `False`, so it survives every "drop the null" filter.
9. ⛔ **COMPARE DECODED TEXT TO DECODED TEXT.**
10. ⭐ **NEW, AND THE MOST EXPENSIVE ONE THIS SESSION: TWO CHECKS AGREEING ON THE SAME WRONG ASSUMPTION IS NOT VERIFICATION.** A clip matched **zero rows and passed its own assertion**, because the predicate and the check both said `state='IN'` on a table that spells it `'Indiana'`. **A zero-row result is a broken instrument until proven otherwise.**
11. ⭐ **A WAREHOUSE CHECK THAT GREPS FOR THE NAME A SOURCE *OUGHT* TO HAVE IS NOT A WAREHOUSE CHECK.** We "held no land banks" for weeks; we held two, filed under `landbank` and `surplus`.
12. ⚠ **`reached > held` IS ALWAYS THE INSTRUMENT**, never the data.

**A clean, alarming or UNCHANGED number is a claim about your INSTRUMENT first.**

---

## THE STANDING RULES

`energy-platfrom.energy` is **READ-ONLY**; everything goes to `energy-platfrom.indiana_app`. The one permitted write is an APPEND to `energy.registry_sources`. **Restate this in every agent brief — agents do not inherit it.** ⚠ **Builds may read `energy`; EXPORTS MAY NOT.**

**Every table gets a `_registry` row in the same run** with `source`, `method` and a verbatim `RE-SCRAPE COMMAND:`.
**⛔ Check the warehouse before you explore or scrape. Read the schema. Never guess a column name OR A VALUE VOCABULARY** — trap 10 is that rule earning itself again.
**Unpublished is NULL, never 0** — a **stated** zero is a fact. ⚠ And a `0` can BE the null sentinel: CMBS occupancy publishes `0` for "not reported", which invented 705 distressed buildings before it was caught.
**⚠ EXCLUDE `parcels_in/080500000047000018`** from every spatial join (D85); prove it by fan-out.
**⛔ No centroid where a footprint exists.** G125's `map_lat`/`map_lon` are the quarantined exception.
**Never `git add -A`.** **Use a commit-message FILE.**

**After ANY front-end change:** `stamp_assets.py` → `audit_frontend.py` → `audit_js_duplicates.py` → `audit_page_controls.py` → `audit_spelling.py` → **hard-reload and verify in a browser**. ⭐ The map boots headless via `scripts/boot_map_harness.js`.
⭐ **After ANY build touching the spine: re-export sites, the screener AND si surfaces**, or the warehouse improves and no reader sees it.

---

**Start by** telling me whether the harvest is alive, what the checkpoint printed, and what the ledger audits printed — then what you read, then your plan.
⭐ **Lead with G149** — the bus legend regression — unless I say otherwise.
