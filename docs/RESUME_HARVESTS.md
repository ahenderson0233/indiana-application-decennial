# PJM CASE-23 HARVESTS

> ## ✅ WITHDRAWAL IS DONE — 🟡 INJECTION IS RUNNING (2026-08-18 afternoon)
>
> **✅ `in_pjm_qs_c23sens_wd` — WITHDRAWAL, COMPLETE.** **462,654 rows, 1,826 of 1,826 buses,
> 0 null `available_mw`, one `case_label`.** That is landing-sequence step 1 below, passed in full.
>
> **🟡 `in_pjm_qs_c23sens_inj` — INJECTION, RUNNING.** Case 23, owner **1568**, 100 MW, started
> 11:36 by the chained poll-for-absence guard, which did its job: it waited for withdrawal to
> finish rather than launching alongside it. At **1,600 of 1,826 buses** late afternoon, and it is
> the **only** QueueScope process.
>
> ⚠ **It registers only on completion.** The honesty audit reporting **1 unregistered table** is
> the expected mid-flight state — registering early would assert a row count that is still moving.
>
> ⛔ **DO NOT START A SECOND QUEUESCOPE PROCESS.** Check first:
> ```
> Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -like '*pull_pjm_injection*' }
> ```
> Log: `data/_harvest_c23sens_wd.log`
>
> ### Why a re-harvest, and why into a NEW table
>
> **PJM refreshed the powerflow file inside case 23, and it was proven by measurement, not
> assumed.** The vendor's 2026-06-23 export carries powerflow case
> `Final_2024 Series RTEP 2028 SUM_BD_02052026_TC2_PHII_Final`; their 2026-08-18 export carries
> `Final_2024 Series RTEP 2028 SUM_BD_05282026_TC2_PHII_SENS_Topo`. The QueueScope **case number is
> unchanged** — 23 is still "2028 TC2 Phase II Case (Summer Peak)" — so this is PJM swapping the
> underlying study inside the same slot, not a new case.
>
> ⭐ **Confirmed with a 1-batch probe before committing to a multi-hour run:** re-harvesting 25 buses
> returned the same constraints but **1,094 rows with a CHANGED `available_mw`**. Our existing
> `in_pjm_qs_tc2phii_wd` / `_inj` are therefore a *superseded study*, not merely an older pull.
>
> ⚠ **Our harvest schema records `case_label` only — the QueueScope case NAME — and NOT the
> underlying powerflow filename.** That is why the refresh was invisible to us and had to be found by
> diffing values. **Add the powerflow-case string to the harvest schema**, or the next refresh will
> be just as silent.
>
> ### Two traps that were hit and handled; hit them and you lose hours
>
> 1. **The checkpoint markers are keyed by case+mode, not by target table.** Re-running case 23
>    against the existing markers resumes and harvests almost nothing. They were **archived, never
>    deleted** — `data/_ARCHIVED_*_ckpt_pjm_qs_case23_*`. Deleting `data/` forces a duplicating
>    re-harvest; renaming is reversible.
> 2. **The probe itself consumed checkpoint entries for its 25 buses.** Its marker was archived too,
>    otherwise the full run would have silently skipped those buses and produced a table quietly
>    missing 25 of 1,826.
>
> ### Landing sequence when it finishes
>
> 1. Verify: 1,826 buses, 0 null `available_mw`, one `case_label`.
> 2. Then `--mode INJECTION --table in_pjm_qs_c23sens_inj`. **One at a time.**
> 3. Only after BOTH land, retire `in_pjm_qs_tc2phii_wd` / `_inj` as the superseded study.
>    Do not delete them until the replacements are verified.
> 4. Owner id is **1568** for case 23. **739 is AEP in the default case and loads 0 rows while
>    exiting successfully** — the `--list` output shows 739 because it lists the default case.

---

# (historical) RESUME THE PJM CASE-23 HARVESTS — after the 2026-08-17 reboot

Both harvests were interrupted by a network drop (not a code fault). **Both are cleanly resumable.**
The data is safe in BigQuery; the on-disk checkpoint markers track which batches are done.

## State at interruption

| harvest | table | rows landed | buses | batches done | status |
|---|---|---:|---|---|---|
| WITHDRAWAL | `in_pjm_qs_tc2phii_wd` | 384,366 | 1,525 / 1,826 (83.5%) | 61 / ~74 | stopped |
| INJECTION | `in_pjm_qs_tc2phii_inj` | 420,859 | 1,183 / 1,826 (64.8%) | 47 / ~74 | stopped |

## Resume commands — RUN ONE AT A TIME, not both at once

⛔ **Standing rule: never two QueueScope instances at once.** Run withdrawal to completion, THEN
injection. Each re-run skips the batches already marked `.done` and continues from where it stopped.

```bash
python scripts/pull_pjm_injection.py --case 23 --mode WITHDRAWAL --mw 100 --owner 1568 --table in_pjm_qs_tc2phii_wd
```
then, after it finishes:
```bash
python scripts/pull_pjm_injection.py --case 23 --mode INJECTION --mw 100 --owner 1568 --table in_pjm_qs_tc2phii_inj
```

## The three things that make this safe (verified 2026-08-17)

1. **Checkpoint markers persist on disk**: `data/_ckpt_pjm_qs_case23_withdrawal/` and
   `…_injection/` hold one `{case}__{mode}__{mw}__{owner}__{batch}.done` file per completed batch.
   The loader checks `mark.exists()` before each batch and skips it. A reboot does not touch them.
2. **Only successful batches are marked done** — the interrupted batch has no marker, so it retries
   rather than being skipped. Worst case is ~one batch (~25 buses) re-run and duplicated, which
   dedupes cleanly on (bus_number, transmission_facility, contingency_type).
3. **The rows are in BigQuery**, which survives the reboot entirely.

## ⛔ DO NOT

- **Do not delete `data/`** or the `_ckpt_pjm_qs_case23_*` directories. They are gitignored
  (local-only) — a reboot keeps them, but deleting them forces a from-scratch re-harvest that would
  **duplicate** everything already loaded.
- **Do not pass `--owner 739`.** Owner ids are renumbered per case; **AEP is `1568` in case 23**.
  739 loads 0 rows and exits *successfully* (silent failure).
- **Do not start a second QueueScope process** while one is running.

## ⚠ Registry note

`in_pjm_qs_tc2phii_inj` currently carries a **PROVISIONAL** `_registry` row (hand-written so the
checkpoint's "every table registered" invariant passes mid-harvest). The wrapper overwrites it with
the final count when the injection harvest completes. `in_pjm_qs_tc2phii_wd` carries a stale
smoke-test row (11,191) that the wrapper likewise refreshes on completion.

## When BOTH finish

Rebuild `in_bus_capacity_tier0` to use case 23 for PJM (it currently holds stale case-4 PJM), attach
the DPP-2025 cost join, and benchmark against the vendor file. See `HANDOFF_2026-08-17c.md` §2 and
`BACKLOG.md` §G7h/G7m.
