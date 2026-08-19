# NEXT SESSION — paste everything below this line as your first message

Continue the Indiana siting-intelligence application.
Repo: `C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial`
(GitHub `ahenderson0233/indiana-application-decennial`, branch `main`)

---

## ⛔ DO THESE THREE THINGS FIRST. Propose nothing before you have.

### 1. Is the PJM harvest alive?

```bash
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | Where-Object { $_.CommandLine -like '*pull_pjm*' } | ForEach-Object { 'PID ' + $_.ProcessId + ' :: ' + $_.CommandLine }"
```

⚠ **A count of 2 is almost always your own command self-matching** — the filter string appears in
your own process's command line. Confirm by parentage before believing it.

**If nothing is running, resume. This one command resumes, continues AND repairs, and it is safe to
run even while one is going** — it polls for the ABSENCE of a QueueScope process rather than waiting
on a handle, which is the exact failure that once spawned a duplicate harvester:

```bash
powershell -ExecutionPolicy Bypass -File scripts\run_pjm_ladder.ps1
```

⛔ **NEVER start a second QueueScope process.** ⛔ **NEVER delete `data/`** — the markers live there
and deleting them forces a duplicating re-harvest; **archive, never delete**. ⛔ **Owner is 1568,
not 739** — 739 loads **0 rows and exits successfully**.

**As of 2026-08-19 ~13:00:** 8 rungs complete at 1,826/1,826 buses (5,000 · 10 · 15 · 100 MW, both
directions). Withdrawal 25 MW running. 25 inj, then 50 · 200 · 300 · 500 · 1000 · 1500 · 2000 · 3000
queued both ways.

### 2. Checkpoint

```bash
python scripts/checkpoint.py
```

**Expect 3 failures and expect them to be correct:**

| failing check | why |
|---|---|
| `wiring census: ~291 of 309` | new tables not yet on a surface. **G72 closes it** |
| `honesty audit: 1 failure` + `1 unregistered` | **the unregistered table IS whichever ladder rung is mid-flight.** It registers on completion |

⛔ **Anything else failing is real.** The five D85 guards, `no EXPORT reads energy`, `shipped payload
agrees with the warehouse`, payload freshness and required keys must all PASS.

### 3. Read, in this order

| # | file | why |
|---|---|---|
| 1 | `docs/SESSION_START.md` | standing rules and the governing principle |
| 2 | ⭐ **`docs/HANDOFF_2026-08-19b.md`** | **THE CURRENT ONE.** Everything below, in full |
| 3 | `docs/BACKLOG.md` | the **⚠ IN FLIGHT** row first, then the G-index (G1–G109) |
| 4 | ⭐ **`docs/TABLE_PURPOSE_INDEX.md`** | generated. 310 objects → purpose → the control. **The G72 worklist** |
| 5 | `docs/FEATURE_INVENTORY.md` | every feature, how it works, its BigQuery table |
| 6 | `docs/BUS_PARITY_2026-08-18.md` | the vendor comparison — ⚠ **§Finding 1 is superseded**, see the handoff |
| 7 | `docs/BUILDABLE_AREA_BASIS.md` | what is and is not netted out of a parcel (G28) |
| 8 | `docs/REFERENCE_TOOL_GAP.md` | ⚠ **its #1 item is now DECLINED** — read the ruling at the top |

⚠ `HANDOFF_2026-08-19.md` and every earlier handoff are **HISTORY**. Read them for *how*, never for
*what is true now*.

**Then run this before you believe any backlog row:**

```bash
python scripts/audit_backlog_truth.py
```

---

## ⭐ START WITH THIS — the operator's own instruction, and the one thing not begun

**G105 — a full-scale audit of the tool, including every clicking and hovering action.**

> Operator, 2026-08-19: *"run a full-scale audit of the tool and fix anything that is not complete,
> including all of the clicking/hovering actions throughout the tool."*

⚠ **`scripts/audit_map_clicks.py` already exists — run it FIRST** rather than starting by hand.
⚠ **The map does not boot headless**, so a click cannot be simulated by loading the page. Verify by
calling handler functions directly with a real feature — that is how every front-end fix on
2026-08-19 was checked, and it caught a garbage distance and two render throws.
⭐ **Precedent for what this finds:** the G65 sweep found four layers DRAWN and unclickable, and
three logistics layers with a hover and no click at all — visible for weeks, unexplainable.

Then **G106**: batch the remaining **non-scraping** backlog and work it.

---

## ⛔ OPERATOR RULINGS — DO NOT RE-LITIGATE (backlog G107)

- ⛔ **RADIUS-FROM-A-POINT SEARCH IS DECLINED.** *"We do NOT need radius from a point in this
  analysis."* `REFERENCE_TOOL_GAP.md` ranked it #1 and the previous prompt starred it. **It is dead.**
- ⭐ **Scraping goes to an Opus (non-Fable) agent**, stated twice, for token cost. **Brief it with
  the write boundary, no-CAPTCHA / no-UA-spoof, and BLOCKED-is-a-success — agents do not inherit
  them.**
- ⭐ **All 13 decimal places stay** on parcel coordinates (G30b). The 45% payload saving is refused.
- ⭐ **New items batch into the LAST group**, not a separate queue.

---

## ⭐ WHAT CHANGED ON 2026-08-19 THAT YOU MUST NOT UNDO

**The screener's bus headroom was reading two superseded sources.** `wd_mw` spanned 13–132 MW, so
nothing could reach the page's own 300 MW default, and **there was no MISO load-side data at all**.
Repointed at `in_bus_capacity_tier0`: **sites at ≥300 MW went 0 → 5,396.**

**PJM parity: the vendor's cutoff is not one number.** Their file's `Shift Factor Cutoff Ratio` is
**0.05 when the facility is healthy and 0.20 when it is already overloaded**, and an overloaded
binder means **ZERO**. We now match: >0 went 100.0% → **95.7%** against their 96.8%, median ratio
**1.056**, and *"they say 0 and we don't"* went **18 → 0**.
⭐ **Where we pick the same binding facility the ratio is median 1.001.** The remaining gap is that
**41.5% of their binding facilities are absent from our harvest** — not the maths.

**The ladder DOES surface constraints** — injection 5,000 vs 100 MW adds **443 keys** — but **0 new
facilities**, which is why it cannot close parity. `in_bus_capacity_tier0` now sources the 5,000 MW
rung: **986 of 1,814 injection buses changed, 466 tighter**.

**Of 227 located PJM buses only 42 are in Indiana.** The screener was silently matching 3,993 parcels
to two out-of-state buses; those rows now say **"Bus location: OUTSIDE INDIANA"**.

---

## ⭐ THE ONE ACQUISITION THAT UNBLOCKS FIVE BACKLOG ROWS

`mat_parcel_attrs` declares `assessed_value`, `zoning`, `parcel_owner`, `land_use`, `year_built` —
and **all five are 100% NULL for Indiana**, 0 of 3,553,381, while the same table holds **40.8M
assessed values across 43 states**. Not a clip defect; the vendor lacks Indiana.

**G104, G70, G71, G81 and G90's parcel half are one purchase** — the DLGF Gateway pull.

---

## ⛔ TRAPS THAT COST REAL TIME. Read these or repeat them.

1. **A `SHORT` line in the harvest log is NOT data loss.** Use `audit_pjm_short_reads.py`, never the
   log. Stopping a healthy harvest over one created a 25-bus gap that then had to be repaired.
2. **Killing the ladder supervisor kills its python child** seconds later.
3. **`nulls` and `rows` are BigQuery reserved words.**
4. **Never guess a column name OR A VALUE VOCABULARY.** 2026-08-19: `value` (it is `rate`), and
   `investor_owned` vs **`INVESTOR OWNED`** — which silently greyed out all 145 territories while
   looking deliberately coloured.
5. **Never write a regex through a shell heredoc.** Use the Write tool and self-test at import.
6. ⭐ **A dry run that writes is worse than no dry run.**
7. ⭐ **A re-check may CONFIRM or ADVANCE a row — never silently DEMOTE one.**
8. ⭐ **Do not sample one row and generalise.**
9. **`Number(null)` is 0, and 0 is finite.**
10. ⚠ **`fetchGz()` sends no cache-buster** (G101) — after a rebuild the browser serves the old
    payload, which **masquerades as a build failure**.

**The pattern: a clean, alarming or UNCHANGED number is a claim about your INSTRUMENT first.** Three
audits cried wolf or stayed silent on 2026-08-19 — G76's criterion, the G8 codename probe, and the
superseded-table check (**G108**, still open).

---

## THE STANDING RULES, each earned by getting it wrong

**Write boundary.** `energy-platfrom.energy` is **READ-ONLY**; everything goes to
`energy-platfrom.indiana_app`. The one permitted write is an APPEND to `energy.registry_sources`.
**Restate this in every agent brief — agents do not inherit it.**
⚠ **Builds may read `energy`; EXPORTS MAY NOT.**

**Every table gets a `_registry` row in the same run**, with `source`, `method` and a verbatim
`RE-SCRAPE COMMAND:`. ⚠ **Update it when you repoint a build** — on 2026-08-19 a registry row still
named two retired tables after the code had moved on.

**⛔ Check the warehouse before you explore or scrape.** **Read the schema. Never guess.**
**Unpublished is NULL, never 0** — but a **stated** zero is a fact, not a gap.
**⚠ EXCLUDE `parcels_in/080500000047000018`** from every spatial join (D85); prove it by measuring
fan-out (~1.0, not ~2.0).
**⛔ No centroid where a footprint exists.** **Never `git add -A`.** **Use a commit-message FILE.**

**After ANY front-end change:** `python scripts/stamp_assets.py` → `python scripts/audit_frontend.py`
→ verify in a browser. ⚠ **`app.js` is boot-critical and the map does NOT boot headless** — verify
by calling functions directly.
⚠ **`data/sites/` is ~224 MB of gzipped files and `git push` FAILS on it** (`SEC_E_MESSAGE_ALTERED`).

---

**Start by** telling me whether the harvest is alive and what the checkpoint printed, then what you
read, then your plan — and **lead with G105, the click/hover audit**, unless I say otherwise.
