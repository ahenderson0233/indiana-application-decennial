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

⛔ **DO NOT TRUST ANY RUNG LIST IN A DOCUMENT — MEASURE IT.** The ladder advanced twice during the
2026-08-20d session and its PID changed with it. `python scripts/audit_handoff_docs.py` prints the
live complete/short split.

### 2. Start a web server, or every page hangs

```bash
python -m http.server 8123 --directory "C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
```

⚠ Not optional. A dead server looks exactly like a code bug — that has cost this project a
debugging session already.
⚠ **And hard-reload, with a cache-busting query if you must.** On 2026-08-20d a stale cached page
served `common.js?v=b6a36660` while disk held `9a0640f5`, and brand-new code was "missing" for
three probes.

### 3. The checkpoint and the ledger audits

```bash
python scripts/checkpoint.py
python scripts/audit_backlog_state.py
python scripts/audit_handoff_docs.py
python scripts/audit_registry_truth.py
```

**Expect 3 checkpoint failures and expect them to be correct:**

| failing check | why |
|---|---|
| `wiring census` fails | ⭐ **END STATE, not a gap.** Every unreached object carries a measured reason and the worklist is 0. ⛔ Do not chase the ratio — the durable check is `0 unclassified` |
| `honesty audit: 1 failure` | known; it is the unregistered-table count below, reported twice |
| `2 unregistered tables` | ladder rungs the running harvest created since the last registration pass |

⭐ **The checkpoint now runs TEN audits.** The two newest — `spelling` and `gate/preference
consistency` — must PASS. ⛔ **Anything else failing is real.**

### 4. Read, in this order

| # | file | why |
|---|---|---|
| 1 | `docs/SESSION_START.md` | standing rules and the governing principle |
| 2 | ⭐ **`docs/HANDOFF_2026-08-20d.md`** | **THE CURRENT ONE.** Six findings, §2b every parcel figure that moved, seven instrument failures, seven traps |
| 3 | ⭐ **`docs/BACKLOG.md`** | the **⚠ IN FLIGHT** row, then **WHERE EVERY UNFINISHED ROW STANDS**, then the G-index (G1–G129) |
| 4 | ⭐ **`docs/COMPARABLE_TOOLS.md`** | **the plan for what this product should look like.** §3 names the ONE question each page answers |
| 5 | ⭐ `docs/RESCRAPE_LEDGER.md` | **generated** — which loaders re-run, how often, safely, and what each clip drops |
| 6 | `docs/UNWIRED_CLASSIFICATION.md` | **generated** — why each unreached object is unreached |
| 7 | `docs/FEATURE_INVENTORY.md` | every feature, how it works, its BigQuery table |

⚠ `HANDOFF_2026-08-20b.md` and earlier are **HISTORY**. Read them for *how*, never for *what is
true now* — §2b of the current handoff lists nine figures they get wrong.

---

## ⛔ START HERE — THE PRIORITY BATCH IS CLOSED. WHAT IS LEFT IS ACQUISITION AND JUDGEMENT.

⭐ **G122–G129 are all done.** The pages have been reordered so the ANSWER precedes the WORKPAPER
(G128b, 38 blocks moved): `si.html` opens with *which owners might sell you land* instead of a
build diary, `market.html` opens with *what would power cost here* instead of statewide demand,
`community.html` opens with *county posture* instead of the receipts browser, and `grid.html`
needed only three moves.

**There is no large mechanical job left.** The three things that matter now are all things code
cannot decide:

### ① THE DLGF GATEWAY PURCHASE — the highest-value action left, and it is yours

Four rows unblock at once: **G70** (parcel owner), **G71** (zoning), **G104** (assessed value) and
**G90(b)**. All are 100% NULL for Indiana in both our clip and the national parent, which holds
40.8M assessed values for 43 other states. **Not a clip defect; re-clipping will not help.**
⭐ G70 has shrunk twice — its building-use half and its address half have both shipped — so what
is left really is just owner, and that is the purchase.

### ② THE DEFERRED SCRAPES

G102 (state surplus, likely IDOA) · G103 (water utilities, EPA SDWIS) · G114's remaining **1,464**
PJM bus coordinates · G15's cost re-extraction from the workpaper header row.
⭐ **Send to an Opus (non-Fable) agent** and brief it with the write boundary, no-CAPTCHA /
no-UA-spoof and BLOCKED-is-a-success, because **agents do not inherit them**.

### ③ TWO DECISIONS THAT ARE YOURS, NOT CODE'S

- ⚠ **G129 option (b)** — a per-filter GATE/PREFERENCE toggle instead of the fixed published
  classification that shipped. More honest and more work; a product decision, not a defect.
  Option (a) is live: 18 gates, 14 preferences, badged on screen, 259 near misses recovered.
- ⚠ **How aggressive should the G122 exclusion be?** 3,159 road and 1,861 rail corridors are gone.
  A further **28,187 parcels are ribbon-shaped with NO road along them** — creeks, pipeline
  easements, genuinely long narrow industrial land — and they are REPORTED, not excluded.
  ⛔ Widening the shape threshold until they disappear is how a heuristic eats its own corpus, so
  it was not done. If you want them out, that is a call, not a fix.

⚠ **If you do pick up front-end work,** the remaining piece of G123 is the **13 runtime `.sowhat`
blocks** that could not be relocated: each wraps a live `id` its own script writes a VALUE into
(`<div class="sowhat" id="wd-answer">measuring…</div>`). The value stays, the sentence around it
goes — a per-block edit, and moving them wholesale broke six pages on the first attempt.

---

## THE BACKLOG — 100 DONE · 16 PARTIAL · 8 OPEN

**Eight rows closed** across 2026-08-20d/e (G53, G122, G123, G124, G125, G127, G128, G129) and one
more answered and advanced (G126). ⭐ **OPEN halved, 16 → 8, and the operator's entire priority
batch G122–G129 is now closed.**

### ① THE DLGF GATEWAY PURCHASE — still the highest-value action left, and it is yours

It unblocks **four rows at once**: G70 (parcel owner), G71 (zoning), G104 (assessed value) and
G90(b). All five attribute columns are **100% NULL for Indiana** — 0 of 1,143,873 in our clip and 0
of 3,553,381 in the parent — while the parent holds 40.8M assessed values across 43 other states.
**Not a clip defect; re-clipping will not help.**
⭐ **G70 shrank on 2026-08-20d:** its building-use half shipped earlier, and its address half is now
done too — statewide, not Marion-only. What remains is owner, and that is the purchase.

### ② THE DEFERRED SCRAPES

G102 (state surplus, likely IDOA) · G103 (water utilities, EPA SDWIS) · G114's remaining **1,464**
PJM bus coordinates · G15's cost re-extraction from the workpaper header row.
⭐ **Scraping goes to an Opus (non-Fable) agent** — brief it with the write boundary,
no-CAPTCHA / no-UA-spoof and BLOCKED-is-a-success, because **agents do not inherit them**.

### ③ TWO DECISIONS THAT ARE YOURS, NOT CODE'S

- ⚠ **G129 option (b)** — a per-filter GATE/PREFERENCE toggle instead of the fixed published
  classification that shipped. More honest and more work; a product decision, not a defect.
  Option (a) is live: 18 gates, 14 preferences, badged on screen, 259 near misses recovered.
- ⚠ **How aggressive should the G122 exclusion be?** 3,159 road and 1,861 rail corridors are gone.
  A further **28,187 parcels are ribbon-shaped with NO road along them** — creeks, pipeline
  easements and genuinely long narrow industrial land — and they are REPORTED, not excluded.
  ⛔ Widening the shape threshold until they disappear is how a heuristic eats its own corpus, so
  it was not done. If you want them out, that is a call, not a fix.

---

## ⛔ SIX THINGS THAT WILL MISLEAD YOU

**① Every parcel figure in the estate moved.** G122 removed 1,368 right-of-way parcels, so
candidates are **531,325** (not 532,693), flagged parcels **23,766** (not 23,795), GRID binds
**189,807**, LAND binds **72,725**, substations-on-a-parcel **1,820**. §2b of the handoff carries
the full before/after. ⚠ Median substation distance **rose** 2.08 → **2.15 mi**, because the
parcels removed were corridors that hug infrastructure — a number moving the unhelpful way after a
correction is usually a sign the correction was real.

**② THE ADDRESS IS STATEWIDE.** Three documents said Marion-only. `energy.parcels_in` carries the
DLGF property address on **98.4% of Indiana parcels across all 92 counties**; the Marion-only
belief came from `in_si_address_parcel_bridge`, which is the address SEARCH crosswalk and a
different corpus doing a different job.

**③ "Ribbon parcels with a road" is now 25, not 184** — and that is the fix working. The other 159
were excluded as rights-of-way. The figure counts what SURVIVES the exclusion.

**④ The wiring census FAILING is correct** and is not work.

**⑤ "No structure" means "no building as of January 2020"** — and there is a second cause with the
same appearance: a geocode landing on the road. ⭐ G122 makes that far rarer, because the road
parcel itself is now excluded from the candidate set.

**⑥ The screener carries TWO capacity figures and they mean different things.** `mw_dc` is LAND;
`deliv_wd_mw` is GRID. Never collapse them.

---

## ⛔ OPERATOR RULINGS — DO NOT RE-LITIGATE (G107)

- ⛔ **RADIUS-FROM-A-POINT SEARCH IS DECLINED.**
- ⭐ **All 13 decimal places stay** on parcel coordinates (G30b).
- ⭐ **New items batch into the LAST group.**
- ⭐ **Scraping goes to an Opus (non-Fable) agent.**
- ⭐ **Min-of-both-ends** for deliverable capacity is the operator's rule and electrically right.
- ⛔ **Vendor data is a yardstick, never a source** — one exception,
  `in_bus_headroom_miso_vendor`, licence lapsing late 2027.

---

## ⛔ TRAPS — read §4 and §5 of the handoff in full

1. ⛔ **NEVER WRITE A REGEX THROUGH A SHELL HEREDOC. SEVENTH occurrence on 2026-08-20d.** And it
   fails a second way: a heredoc edit silently applied HALF of a two-part change, widening a
   lookup table but not the regex feeding it, leaving a check that passes by default.
2. ⛔ **BUILDS MAY READ `energy`; EXPORTS MAY NOT.** The checkpoint enforces it and caught an
   address join placed inside an export.
3. ⛔ **THE INSTRUMENT IS WRONG BEFORE THE CODE IS — seven times in one session.** A join on the
   wrong key reported "99% carry no class code" against a column 97.8% populated. `re.split` with
   a two-group regex wrote `</script>scriptscript` into eight pages and **no audit could see it**.
   A regex cannot parse a template nested inside another template's `${...}`, which is how nearly
   every rendered string here is written — the fixer missed six and the audit then reported ZERO.
   **An audit registered but not dispatched runs and reports nothing.**
4. ⛔ **A LOOKALIKE IS SOMETIMES A KEY.** `fits_mw_datacentre_at_4_per_acre` is a CSV column name;
   `circle-color` and 91 siblings are MapLibre paint properties.
5. ⛔ **A PRESENTATION POLICY MUST NOT DEPEND ON THE TAB BEING VISIBLE** — rAF does not fire in a
   tab that is not compositing.
6. ⛔ **AN `id` IS USUALLY ON THE BLOCK, NOT INSIDE IT.**
7. ⚠ **Two audits that count different populations will disagree forever.**
8. ⚠ **Cumulative categories are not buckets** (Drought D0 means "D0 or worse").
9. ⚠ **A value vocabulary lies:** FRPP `state_code` is `'18'`; WARN `notice_class` is UPPER-CASE;
   `nearestBus` wants lower-case; roads use `geom`; `territoryAt` returns `utility`.
10. ⚠ **A statistic true of 98% of the corpus tells a siter nothing.**

**The pattern behind all of them: a clean, alarming or UNCHANGED number is a claim about your
INSTRUMENT first.**

---

## THE STANDING RULES

**Write boundary.** `energy-platfrom.energy` is **READ-ONLY**; everything goes to
`energy-platfrom.indiana_app`. The one permitted write is an APPEND to `energy.registry_sources`.
**Restate this in every agent brief — agents do not inherit it.**
⚠ **Builds may read `energy`; EXPORTS MAY NOT.**

**Every table gets a `_registry` row in the same run**, with `source`, `method` and a verbatim
`RE-SCRAPE COMMAND:`. ⭐ `docs/RESCRAPE_LEDGER.md` now also records, per object, whether re-running
is **safe** (replace_safe / append_only / unknown), how often the PUBLISHER changes, and which
parent columns the clip drops.

**⛔ Check the warehouse before you explore or scrape. Read the schema. Never guess a column name
OR A VALUE VOCABULARY.**
**Unpublished is NULL, never 0** — but a **stated** zero is a fact.
**⚠ EXCLUDE `parcels_in/080500000047000018`** from every spatial join (D85); prove it by fan-out.
**⛔ No centroid where a footprint exists.** ⚠ The G125 display coordinate is the one exception and
it is quarantined: `map_lat`/`map_lon` are for the reader's eye and the imagery link, and **nothing
measures with them**.
**Never `git add -A`.** **Use a commit-message FILE.**

**After ANY front-end change:** `python scripts/stamp_assets.py` → `audit_frontend.py` →
`audit_js_duplicates.py` → `audit_page_controls.py` → `audit_spelling.py` → **hard-reload and
verify in a browser**. ⭐ The map boots headless via `scripts/boot_map_harness.js`.

---

**Start by** telling me whether the harvest is alive, what the checkpoint printed, and what the
ledger audits printed — then what you read, then your plan.
⭐ **Lead with G128(b)** — the page re-ordering — unless I say otherwise. It is the largest
remaining win, it is what "it looks like an intern made this" was actually about, and every
mechanical prerequisite for it is now done.
