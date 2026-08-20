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

**Ladder state at handoff (2026-08-20b), by distinct buses out of 1,826.** ⚠ It moved *during*
that session, so measure rather than trusting this line:
COMPLETE — injection 10 / 15 / 50 / 5000, withdrawal 10 / 15 / 25 / 5000.
SHORT — `inj_25` at **1,797**, `wd_50` at **1,625**, `wd_200` mid-harvest.
⛔ **Neither short rung affects a shipped figure** — `in_bus_capacity_tier0` reads the 5,000 rung
only. A session that repoints tier0 lower must finish them first.

### 2. Start a web server, or every page hangs

```bash
python -m http.server 8123 --directory "C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
```

⚠ Not optional housekeeping. On 2026-08-19b the operator's server died, the cached HTML still drew
the page, and the screener sat on "Loading sites…" — reported as a code bug, debugged as a code
bug, and it was a dead port.

### 3. The checkpoint and the ledger audits

```bash
python scripts/checkpoint.py
python scripts/audit_backlog_state.py     # is the LEDGER coherent?
python scripts/audit_handoff_docs.py      # are the numbers in the HANDOFF still true?
python scripts/audit_registry_truth.py    # can a stranger re-run every table?
```

**Expect 3 checkpoint failures and expect them to be correct:**

| failing check | why |
|---|---|
| `wiring census` fails | ⭐ **This is the END STATE, not a gap** — see §4 of the handoff. Every unreached object carries a measured reason and the worklist is 0. ⛔ **Do not chase the ratio:** the census counts an object as reached if any script NAMES it, so it moves whenever one does. The durable check is `0 unclassified` |
| `honesty audit: 1 failure` | known |
| `2 unregistered tables` | ladder rungs the running harvest created since the last registration pass |

⭐ **The checkpoint gained three checks on 2026-08-20b** — `map clicks`, `page controls` and
`schema truncation` — and all three should PASS. Each guards a defect that had already shipped.
⛔ **Anything else failing is real.**

### 4. Read, in this order

| # | file | why |
|---|---|---|
| 1 | `docs/SESSION_START.md` | standing rules and the governing principle |
| 2 | ⭐ **`docs/HANDOFF_2026-08-20b.md`** | **THE CURRENT ONE.** Six findings, five wrong audits, ten traps |
| 3 | `docs/BACKLOG.md` | the **⚠ IN FLIGHT** row first, then the G-index (G1–G121) |
| 4 | ⭐ `docs/UNWIRED_CLASSIFICATION.md` | **generated** — why each unreached object is unreached, with its measured reason |
| 5 | `docs/FEATURE_INVENTORY.md` | every feature, how it works, its BigQuery table |
| 6 | `docs/REFERENCE_TOOL_GAP.md` | ⚠ **its #1 item is DECLINED** — read the ruling at the top |

⚠ `HANDOFF_2026-08-20.md` and earlier are **HISTORY**. Read them for *how*, never for *what is
true now*.

---

## ⭐ START HERE — the non-scraping backlog is DONE

**80 DONE · 21 PARTIAL · 15 OPEN → 94 DONE · 14 PARTIAL · 8 OPEN.** Fourteen rows closed on 2026-08-20b, seven more advanced. What is left is not a list of tasks; it is three decisions and a scrape queue.

### ① THE DLGF GATEWAY PURCHASE — the highest-value action left, and it is yours, not code's

It unblocks **four rows at once**: G70 (parcel owner), G71 (parcel zoning), G104 (assessed value)
and G90(b) (making WARN notices reach a parcel). Each has been measured to death and each is
blocked on the same missing Indiana source. `mat_parcel_attrs` declares `assessed_value`,
`zoning`, `parcel_owner`, `land_use` and `year_built`, and **all five are 100% NULL for Indiana**
— 0 of 1,143,873 in our clip and 0 of 3,553,381 in the parent — while the parent holds 40.8M
assessed values across 43 other states. **It is not a clip defect and re-clipping will not help.**

### ② THE DEFERRED SCRAPES — the operator excluded these deliberately

G102 (state surplus, likely IDOA) · G103 (water utilities, EPA SDWIS) · G114's remaining ~1,500
PJM bus coordinates · G15's cost re-extraction from the workpaper header row.
⭐ **Scraping goes to an Opus (non-Fable) agent** — brief it with the write boundary,
no-CAPTCHA / no-UA-spoof and BLOCKED-is-a-success, because **agents do not inherit them**.

### ③ G96 NEEDS AN OPERATOR DECISION

When is a filter a **hard gate** (flood) and when a **preference** (acreage)? A ranking cannot
treat them alike, and no amount of code supplies the answer.

**Everything else PARTIAL is honest about its remainder:** G6 (visual polish — the structure is
done), G15 (cost), G21 (a standing principle, never "done"), G26 (the mitigated case is not
obtainable), G27 (closed in substance), G40 (owned by the parallel session), G45 (the ladder),
G46 (MISO placement is still borrowed), G51 (must stay evidence-driven), G55 (unpublished books),
G62 (an acquisition), G113 (cleanup is judgement), G114 (a scrape).

---

## ⛔ SIX THINGS THAT WILL MISLEAD YOU IF NOBODY SAYS THEM

**① The wiring census FAILING is CORRECT and is not work.** Every unreached
object carries a measured reason in `docs/UNWIRED_CLASSIFICATION.md`, and
`audit_unwired_classification.py` fails the checkpoint if one ever does not. The question is no
longer *how many are unwired* — which is unanswerable — but *is any object unwired without a
reason*, which is answerable and answered.

**② "No structure" means "no building as of January 2020"** — `nat_usa_structures` has a newest
Indiana production date of **2020-01-27**. ⭐ **And there is now a SECOND cause with the same
appearance:** an address that geocodes onto the road selects the road right-of-way, which
genuinely has no building, so the tool answers correctly about the **wrong parcel**. The screener
names which one is in play. Do not conflate them.

**③ The flagged parcel count is 23,795, not 24,277.** G84 demoted plain ECHO `violation`.

**④ The screener carries TWO capacity figures and they mean different things.** `mw_dc` is LAND
(acres × density); `deliv_wd_mw` is GRID (the lower of the two end-bus headrooms on the nearest
line). **The grid binds on 190,178 parcels and the land on 73,058.** Never collapse them.

**⑤ Substation distance moved for every parcel in the corpus on 2026-08-20b.** 734 substations
gained a position from footprints already in our own table, and the distance builds now measure to
the **footprint**. Median distance from a candidate parcel to the nearest substation went
**2.56 → 2.08 miles**, and on-parcel substations 871 → **1,846**. If you are comparing against an
older figure, that is why.

**⑥ Nine gas capacity boards exist; only TWO can be placed in Indiana.** Thirteen operators cross
the state. ⛔ **The gap is ATTRIBUTION, not acquisition** — seven of the nine boards post the
operator's whole system with no state column, so scraping four more would mostly add four more
unplaceable boards.

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

## ⛔ TRAPS THAT COST REAL TIME — read §5 and §6 of the handoff in full

The short version, because these repeat:

1. ⛔ **NEVER write a regex through a shell heredoc.** Broken for the **sixth** time on
   2026-08-20b, inside an audit. Write tool, module level, self-test at import.
2. ⛔ **THE INSTRUMENT IS WRONG BEFORE THE CODE IS. Five audits misled me in one session** —
   `audit_map_clicks`, `audit_registry_truth`, `audit_js_duplicates`, `audit_page_controls` and
   `audit_schema_truncation`. One reported a clean all-clear while measuring the wrong tables;
   one reported 231 correct rows as broken; one crying-wolf fix of mine produced 249 false
   findings and was deleted rather than shipped. **Fix the instrument before acting on it, and
   prove it on an injected regression.**
3. ⛔ **A value vocabulary lies.** Five times in one session: FRPP's `state_code` is the numeric
   FIPS `'18'`; WARN's `notice_class` is UPPER-CASE; `nearestBus` filters on a **lower-case**
   direction; the roads tables use `geom` not `geog`; `territoryAt` returns `utility` not `name`.
4. ⛔ **Cumulative categories are not buckets.** The Drought Monitor's D0 means "D0 **or worse**",
   so summing them double-counts — it reported 91.5% where the truth was 50.2%.
5. ⛔ **HARD-RELOAD before debugging a front-end change.** `stamp_assets.py` versions the JS and
   CSS; the HTML cannot version itself.
6. ⛔ **A dead web server looks exactly like a code bug.**
7. ⛔ **Two changes that are each fine can be fatal together.** Removing a checkbox while a layer
   registry still named it threw during boot, before the map existed, so the page rendered nothing.
8. ⚠ **A key in the wrong payload renders empty forever.** `audit_frontend.py` caught it twice.
9. ⚠ **An in-place repair that reads its own output is not idempotent**, and **a build that
   appends to a payload it does not own will double itself** — compressor 24 → 48 features.
10. ⚠ **A statistic true of 98% of the corpus tells a siter nothing.** Narrow it or drop it.

**The pattern behind all of them: a clean, alarming or UNCHANGED number is a claim about your
INSTRUMENT first.**

---

## THE STANDING RULES

**Write boundary.** `energy-platfrom.energy` is **READ-ONLY**; everything goes to
`energy-platfrom.indiana_app`. The one permitted write is an APPEND to `energy.registry_sources`.
**Restate this in every agent brief — agents do not inherit it.**
⚠ **Builds may read `energy`; EXPORTS MAY NOT.**

**Every table gets a `_registry` row in the same run**, with `source`, `method` and a verbatim
`RE-SCRAPE COMMAND:`. ⚠ **Update it when you repoint a build.** ⭐ As of 2026-08-20b **every
registered object carries one** — 136 runnable here, 131 delegated to the platform session, 13
ladder, 49 honestly unresolved. ⛔ **The 49 are visible on purpose:** a plausible command that
does not run is worse than an absent one.

**⛔ Check the warehouse before you explore or scrape.** **Read the schema. Never guess a column
name OR a value vocabulary.**
**Unpublished is NULL, never 0** — but a **stated** zero is a fact.
**⚠ EXCLUDE `parcels_in/080500000047000018`** from every spatial join (D85); prove it by fan-out.
**⛔ No centroid where a footprint exists.** **Never `git add -A`.** **Use a commit-message FILE.**

**After ANY front-end change:** `python scripts/stamp_assets.py` → `python scripts/audit_frontend.py`
→ `python scripts/audit_js_duplicates.py` → `python scripts/audit_page_controls.py` →
**hard-reload and verify in a browser**. ⭐ The map boots headless via
`scripts/boot_map_harness.js`.

---

**Start by** telling me whether the harvest is alive, what the checkpoint printed, and what the
ledger audits printed — then what you read, then your plan. **The non-scraping backlog is done**,
so unless I say otherwise, tell me which of the three remaining decisions you want from me first.
