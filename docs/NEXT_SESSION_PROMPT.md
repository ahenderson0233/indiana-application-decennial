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

**Ladder state at handoff (2026-08-20), measured by distinct buses out of 1,826:**
COMPLETE — injection 10 / 15 / 5000, withdrawal 10 / 15 / 25 / 5000. RUNNING — injection 50.
⛔ **Two rungs are SHORT and one registered anyway:** `inj_25` is 1,797 of 1,826 **with a registry
row**, and `wd_50` is 1,625 of 1,826 and unregistered. **Neither affects a shipped figure** —
`in_bus_capacity_tier0` reads the 5,000 rung only, and both 5,000 rungs audit CLEAN.

### 2. Start a web server, or every page hangs

```bash
python -m http.server 8123 --directory "C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
```

⚠ This is not optional housekeeping. On 2026-08-19b the operator's server died, the cached HTML
still drew the page, and the screener sat on "Loading sites…" — reported as a code bug, debugged
as a code bug, and it was a dead port. `common.js` now paints a banner naming the file instead of
hanging silently, but the server still has to be up.

### 3. Checkpoint and the two ledger audits

```bash
python scripts/checkpoint.py
python scripts/audit_backlog_state.py     # is the LEDGER coherent?
python scripts/audit_backlog_truth.py     # is an "open" item secretly finished?
python scripts/audit_handoff_docs.py      # are the numbers in the HANDOFF still true?
```

⭐ **Run all four before believing anything you read.** `audit_handoff_docs.py` re-measures every
load-bearing figure in the handoff, this prompt and the backlog — it was written because the
project's rule is *never quote a count from a document*, and it caught the handoff quoting a
figure that had gone stale within hours of being written. **18 checks, 0 failing at handoff.**

**Expect 3 checkpoint failures and expect them to be correct:**

| failing check | why |
|---|---|
| `wiring census: ~240 of 323` | G72/G80. ⚠ Read its note below before trusting the number |
| `honesty audit: 1 failure` | known |
| `2 unregistered tables` | the in-flight ladder rung **plus the short `wd_50`** |

⛔ **Anything else failing is real.** The five D85 guards, `no EXPORT reads energy`, payload-vs-
warehouse agreement, payload freshness and required keys must all PASS.

### 4. Read, in this order

| # | file | why |
|---|---|---|
| 1 | `docs/SESSION_START.md` | standing rules and the governing principle |
| 2 | ⭐ **`docs/HANDOFF_2026-08-20.md`** | **THE CURRENT ONE.** Everything below, in full |
| 3 | `docs/BACKLOG.md` | the **⚠ IN FLIGHT** row first, then the G-index (G1–G121) |
| 4 | ⭐ `docs/TABLE_PURPOSE_INDEX.md` | generated — the G72 worklist |
| 5 | `docs/FEATURE_INVENTORY.md` | every feature, how it works, its BigQuery table |
| 6 | `docs/BUILDABLE_AREA_BASIS.md` | what is and is not netted out of a parcel |
| 7 | `docs/REFERENCE_TOOL_GAP.md` | ⚠ **its #1 item is DECLINED** — read the ruling at the top |

⚠ `HANDOFF_2026-08-19b.md` and earlier are **HISTORY**. Read them for *how*, never for *what is
true now*. 19b is still correct on the PJM parity derivation and stale on everything else.

---

## ⭐ START HERE — the operator's own sequencing

The operator ruled that **G115 comes second-to-last and G105 comes LAST**. Both are now next.

**G115 — refresh every table to current state.** Rowcount drift is already 6 → 0, but
**295 of 320 registry rows carry NO `RE-SCRAPE COMMAND`** and 1 is orphaned. Run
`scripts/audit_registry_truth.py`.

**G105 — the full-scale audit of the tool, including every click and hover.**
> Operator: *"run a full-scale audit of the tool and fix anything that is not complete, including
> all of the clicking/hovering actions throughout the tool."*

⚠ **`scripts/audit_map_clicks.py` already exists — run it FIRST.** Its last run found **3 layers
drawn and unclickable**: `deeplink-pt`, `terr-label`, `terr-line`.
⭐ **And the map DOES boot headless now** — see §8 of the handoff and
`scripts/boot_map_harness.js`. Every front-end fix this session was verified that way.

Then the rest: **G72/G80** (the wiring sweep — but read the note below), **G120(b)(e)**,
**G70 · G71 · G104** (one purchase), **G75 · G87 · G79**.

---

## ⛔ FIVE THINGS THAT WILL MISLEAD YOU IF NOBODY SAYS THEM

**① The wiring census overstates what a "surface" is, and it was overstating by 60.** It counts an
object as reaching a surface if any page NAMES it. `app.js` used to carry `FEATURE_HOME`, a
dictionary naming 132 tables read by one dead modal; removing it dropped the census from 291/309
to 235/316. Nothing broke — a fake signal went away. ⚠ **Most of the ~80 still-unwired objects are
ladder rungs and working tables that CORRECTLY reach no surface.** The real list is short:
`in_water_parcel`, the NHD water geometry, `in_si_warn_normalised`, `in_gov_surplus_nces`,
`in_faa_obstacles`.

**② "No structure" means "no building as of January 2020".** `nat_usa_structures` has a newest
Indiana production date of **2020-01-27**. The join is sound (0 false positives in 6,341 tested
empty parcels) — the corpus is six years old. This bounds the BESS open-ground basis, the `f-vac`
filter, and G81's 99.4% figure.

**③ The flagged parcel count is 23,795, not 24,277.** G84 demoted plain ECHO `violation` (676
parcels, no defensible mechanism to a sale). One predicate reverses it.

**④ The screener now carries TWO capacity figures and they mean different things.** `mw_dc` is
LAND (acres × density); `deliv_wd_mw` is GRID (the lower of the two end-bus headrooms on the
nearest line). **The grid binds on 190,178 parcels and the land on 73,058.** Never collapse them.

**⑤ Nine gas capacity boards exist; only TWO can be placed in Indiana.** The other seven post the
operator's whole system with no state column. Wiring them would attach Louisiana capacity to an
Indiana pipeline.

---

## ⛔ OPERATOR RULINGS — DO NOT RE-LITIGATE (G107)

- ⛔ **RADIUS-FROM-A-POINT SEARCH IS DECLINED.**
- ⭐ **All 13 decimal places stay** on parcel coordinates (G30b).
- ⭐ **New items batch into the LAST group.**
- ⭐ **Scraping goes to an Opus (non-Fable) agent** — brief it with the write boundary,
  no-CAPTCHA / no-UA-spoof and BLOCKED-is-a-success, because **agents do not inherit them**.
- ⭐ **Min-of-both-ends** for deliverable capacity is the operator's rule and electrically right.
- ⛔ **Vendor data is a yardstick, never a source** — one exception,
  `in_bus_headroom_miso_vendor`, licence lapsing late 2027.

---

## ⛔ TRAPS THAT COST REAL TIME THIS SESSION

1. ⭐ **HARD-RELOAD (Ctrl+Shift+R) before debugging a front-end change.** `stamp_assets.py`
   versions the JS and CSS; the HTML cannot version itself, so a cached page runs the previous
   script and the fix looks dead.
2. ⭐ **A dead web server looks exactly like a code bug.** See §2.
3. ⭐ **Two features that pass separately can be fatal together.** G117 enumerated every input in
   the screener rail; G119 then put a FILE PICKER in that rail; setting `.value` on
   `<input type=file>` throws, before `render()`, so the page never booted. **Reload the affected
   page after any change to shared machinery.**
4. ⛔ **Never write a regex through a shell heredoc.** Broken again this session — inside the fix
   for a regex bug. Write tool, self-test at import.
5. ⛔ **A sentinel is not a value.** FEMA `-9999.0` BFE (97.4% of SFHA polygons), HIFLD `-999999`
   kV (335 lines), NOAA `mag = -9`.
6. ⛔ **A bounding box around Indiana contains Illinois** — the search guard flew to Chicago. Use
   `countyOf()`.
7. ⚠ **Measure fan-out after any LEFT JOIN.** One append fanned tier0 1,814 → 1,862 on an
   unchanged bus count.
8. ⚠ **Value vocabularies lie:** space-padded `'IN      '`, `'Indiana   '`, `prop_st` as a full
   state name, ECHO's `operator` being the SHIPPER not the pipeline.
9. ⛔ **An audit that cries wolf gets ignored — three of mine did.** Fix the instrument before
   acting on its output.

**The pattern: a clean, alarming or UNCHANGED number is a claim about your INSTRUMENT first.**

---

## THE STANDING RULES

**Write boundary.** `energy-platfrom.energy` is **READ-ONLY**; everything goes to
`energy-platfrom.indiana_app`. The one permitted write is an APPEND to `energy.registry_sources`.
**Restate this in every agent brief — agents do not inherit it.**
⚠ **Builds may read `energy`; EXPORTS MAY NOT.**

**Every table gets a `_registry` row in the same run**, with `source`, `method` and a verbatim
`RE-SCRAPE COMMAND:`. ⚠ **Update it when you repoint a build.**

**⛔ Check the warehouse before you explore or scrape.** **Read the schema. Never guess a column
name OR a value vocabulary.**
**Unpublished is NULL, never 0** — but a **stated** zero is a fact.
**⚠ EXCLUDE `parcels_in/080500000047000018`** from every spatial join (D85); prove it by fan-out.
**⛔ No centroid where a footprint exists.** **Never `git add -A`.** **Use a commit-message FILE.**

**After ANY front-end change:** `python scripts/stamp_assets.py` → `python scripts/audit_frontend.py`
→ `python scripts/audit_js_duplicates.py` → **hard-reload and verify in a browser**.

---

**Start by** telling me whether the harvest is alive, what the checkpoint printed, and what the two
ledger audits printed — then what you read, then your plan. **Lead with G115 then G105**, unless I
say otherwise.
