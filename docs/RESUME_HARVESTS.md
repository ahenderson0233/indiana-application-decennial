# RESUME THE PJM CASE-23 HARVESTS — after the 2026-08-17 reboot

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
