# =============================================================================================
# PJM case-23 harvest across the MW ladder. One process at a time. Fully resumable.
#
# Operator, 2026-08-18: "Let's run the 5000MW code for PJM now, and queue up the remaining
# scenarios that Orennia provides immediately after." And: "Make sure that this is fully
# resumable at any time, since I will need to leave the office at some point tonight and will
# shut down my computer."
#
# ============================== RESUMING AFTER A SHUTDOWN ====================================
# Run this again. Nothing else. It is safe to run at any time, including while one is already
# going - it waits rather than starting a second harvester.
#
#     powershell -ExecutionPolicy Bypass -File scripts\run_pjm_ladder.ps1
#
# Progress lives in data\_ckpt_pjm_qs_case23_{withdrawal,injection}\ as
#     23__<MODE>__<MW>__1568__<batch>.done
# ⭐ The MW is IN the marker name - verified before this was written - so each rung keeps its own
# progress and no rung can read another's marks and skip its work. Only COMPLETED batches are
# marked, so an interrupted batch retries rather than being lost.
#
# ⛔ NEVER START A SECOND QUEUESCOPE PROCESS. That rule was broken once, on 2026-08-18, by a
# chained job whose Wait-Process errored into its catch and launched injection 7 minutes into a
# withdrawal run. This polls for ABSENCE instead of waiting on a handle.
# ⛔ NEVER DELETE data\. Deleting the markers forces a from-scratch re-harvest that DUPLICATES
# everything already loaded. Archive, never delete.
# ⛔ OWNER 1568, not 739. 739 is AEP in the DEFAULT case: it loads 0 rows and exits SUCCESSFULLY.
#
# ⚠ ON WHAT THIS WILL AND WILL NOT CHANGE - measured, not assumed.
# A 1-batch probe at 5,000 MW was compared against our existing 100 MW harvest, joined on
# (bus, facility, contingency) after dedup: 4,673 of 4,673 keys identical, max delta 0.0, all 25
# buses identical headroom. On that evidence `available_mw` does not vary with the requested MW,
# and the gap to Orennia was the DERIVATION rather than the scenario - their capacity is
# (rating - base flow) / |shift factor|, which we now reproduce to a median ratio of 1.010.
# The operator has asked for the ladder anyway, which is reasonable: the probe covered 25 of
# 1,826 buses in one direction, and a larger request may surface FACILITIES that a 100 MW request
# never binds. That is the thing to look for when these land - new rows, not different numbers.
#
# RUNG ORDER is deliberate: 5000 first because it is the operator's ask and it is the rung that
# matches Orennia's own 5,000 MW solve ceiling. Then descending, so that if the night is cut short
# we still hold the widest-spread rungs.
# =============================================================================================

$ErrorActionPreference = "Continue"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$log = Join-Path $repo "data\_harvest_c23_ladder.log"

# Operator, 2026-08-19: the 5,000 MW pair, then every rung QueueScope offers, both
# directions. 26 harvests. Each rung is skipped on re-run once its markers are
# complete, so this list is a QUEUE, not a commitment -- stopping is free.
#
# 100 MW is already held as in_pjm_qs_c23sens_{wd,inj} (74 markers each, registered
# complete), so Test-RungComplete skips it. It is listed for completeness only.
$plan = @(
    @{ mw = 5000; mode = "WITHDRAWAL"; table = "in_pjm_qs_c23_wd_5000" },
    @{ mw = 5000; mode = "INJECTION";  table = "in_pjm_qs_c23_inj_5000" },
    @{ mw = 10; mode = "WITHDRAWAL"; table = "in_pjm_qs_c23_wd_10" },
    @{ mw = 10; mode = "INJECTION";  table = "in_pjm_qs_c23_inj_10" },
    @{ mw = 15; mode = "WITHDRAWAL"; table = "in_pjm_qs_c23_wd_15" },
    @{ mw = 15; mode = "INJECTION";  table = "in_pjm_qs_c23_inj_15" },
    @{ mw = 25; mode = "WITHDRAWAL"; table = "in_pjm_qs_c23_wd_25" },
    @{ mw = 25; mode = "INJECTION";  table = "in_pjm_qs_c23_inj_25" },
    @{ mw = 50; mode = "WITHDRAWAL"; table = "in_pjm_qs_c23_wd_50" },
    @{ mw = 50; mode = "INJECTION";  table = "in_pjm_qs_c23_inj_50" },
    @{ mw = 100; mode = "WITHDRAWAL"; table = "in_pjm_qs_c23_wd_100" },
    @{ mw = 100; mode = "INJECTION";  table = "in_pjm_qs_c23_inj_100" },
    @{ mw = 200; mode = "WITHDRAWAL"; table = "in_pjm_qs_c23_wd_200" },
    @{ mw = 200; mode = "INJECTION";  table = "in_pjm_qs_c23_inj_200" },
    @{ mw = 300; mode = "WITHDRAWAL"; table = "in_pjm_qs_c23_wd_300" },
    @{ mw = 300; mode = "INJECTION";  table = "in_pjm_qs_c23_inj_300" },
    @{ mw = 500; mode = "WITHDRAWAL"; table = "in_pjm_qs_c23_wd_500" },
    @{ mw = 500; mode = "INJECTION";  table = "in_pjm_qs_c23_inj_500" },
    @{ mw = 1000; mode = "WITHDRAWAL"; table = "in_pjm_qs_c23_wd_1000" },
    @{ mw = 1000; mode = "INJECTION";  table = "in_pjm_qs_c23_inj_1000" },
    @{ mw = 1500; mode = "WITHDRAWAL"; table = "in_pjm_qs_c23_wd_1500" },
    @{ mw = 1500; mode = "INJECTION";  table = "in_pjm_qs_c23_inj_1500" },
    @{ mw = 2000; mode = "WITHDRAWAL"; table = "in_pjm_qs_c23_wd_2000" },
    @{ mw = 2000; mode = "INJECTION";  table = "in_pjm_qs_c23_inj_2000" },
    @{ mw = 3000; mode = "WITHDRAWAL"; table = "in_pjm_qs_c23_wd_3000" },
    @{ mw = 3000; mode = "INJECTION";  table = "in_pjm_qs_c23_inj_3000" }
)

function Write-Log($msg) {
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Write-Output $line
    Add-Content -Path $log -Value $line -Encoding utf8
}

function Wait-ForNoQueueScope {
    # Poll for ABSENCE. Never Wait-Process: if the handle is gone or errors, the catch fires and a
    # second harvester launches on top of the first. That is the exact failure this guards.
    for ($i = 0; $i -lt 5760; $i++) {              # 5760 x 15s = 24 hours
        $p = @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
               Where-Object { $_.CommandLine -like '*pull_pjm*' })
        if ($p.Count -eq 0) { return $true }
        if ($i % 40 -eq 0) { Write-Log ("waiting: {0} QueueScope process(es) running" -f $p.Count) }
        Start-Sleep -Seconds 15
    }
    Write-Log "GAVE UP after 24h - something is still running. Not starting another."
    return $false
}

# ⚠ FIXED 2026-08-19. Re-running the ladder replayed COMPLETED rungs. The loader skips each marked
# batch, so no data was duplicated and nothing was lost -- but it still walked all ~74 of them one
# at a time, which cost about an hour of wall clock before the runner reached the rung that
# actually needed work. Measured live: the 5,000 MW withdrawal table sat unchanged at 462,654 rows
# the whole time, which is how we knew it was walking rather than re-harvesting.
#
# A rung is DONE when its marker count has stopped short of nothing -- i.e. it has at least as many
# markers as the largest rung already recorded for that mode. Cheap, on-disk, and it needs no
# network call. Skipping is logged, never silent: a rung that vanishes from the log without a
# reason is indistinguishable from one that failed.
function Test-RungComplete($mode, $mw) {
    $dir = Join-Path $repo ("data\_ckpt_pjm_qs_case23_" + $mode.ToLower())
    if (-not (Test-Path $dir)) { return $false }
    $mine  = @(Get-ChildItem $dir -Filter ("23__" + $mode + "__" + $mw + "__1568__*.done")).Count
    # the reference is the fullest rung we have ever completed in this direction
    $best = 0
    foreach ($f in Get-ChildItem $dir -Filter "*.done") {
        if ($f.Name -match ("^23__" + $mode + "__(\d+)__1568__")) {
            $n = @(Get-ChildItem $dir -Filter ("23__" + $mode + "__" + $Matches[1] + "__1568__*.done")).Count
            if ($n -gt $best) { $best = $n }
        }
    }
    return ($mine -gt 0 -and $mine -ge $best)
}

Write-Log "=== run_pjm_ladder invoked. Safe to re-run: finished batches are skipped. ==="
foreach ($step in $plan) {
    if (Test-RungComplete $step.mode $step.mw) {
        Write-Log ("SKIP  {0} {1} MW -> {2} (all batches already marked done)" -f $step.mode, $step.mw, $step.table)
        continue
    }
    if (-not (Wait-ForNoQueueScope)) { break }
    Write-Log ("START {0} {1} MW -> {2}" -f $step.mode, $step.mw, $step.table)
    & python scripts\pull_pjm_injection.py --case 23 --mode $step.mode --mw $step.mw `
        --owner 1568 --table $step.table 2>&1 |
        ForEach-Object { Add-Content -Path $log -Value $_ -Encoding utf8 }
    Write-Log ("FINISH {0} {1} MW exit={2}" -f $step.mode, $step.mw, $LASTEXITCODE)
}
Write-Log "=== ladder complete (or interrupted - re-run to continue where it stopped) ==="
