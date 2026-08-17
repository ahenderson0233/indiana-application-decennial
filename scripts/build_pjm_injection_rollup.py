"""Per-bus PJM INJECTION headroom -- the mirror of scripts/build_pjm_withdrawal.py.

The rollup logic is COPIED from build_pjm_withdrawal.py, deliberately, so the two directions
are directly comparable rather than each carrying its own convention:
  MIN(available_mw) per bus over facilities the new resource meaningfully stresses
  (|dfax| >= 5%), EXCLUDING pre-existing overloads (pre_loading_pct >= 100), which are
  disclosed per bus in existing_overloads rather than silently dropped.

WHY THE desired_mw FILTER MATTERS
---------------------------------
in_pjm_queuescope_injection holds the full AEP footprint at desired_mw=100 PLUS a 25-bus
request-size ladder at 300/500/1000/2500/5000.  Rolling up without filtering would count
those 25 buses six times over in `facilities`.  available_mw itself is request-invariant
(verified: 7,950/7,950 rows identical across all six rungs, max delta 0.0), so filtering to
the 100 MW rung loses no headroom information -- it just keeps the facility counts honest.

    python scripts/build_pjm_injection_rollup.py
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
RUNG = 100
client = bigquery.Client(project="energy-platfrom")

client.query(f"""
CREATE OR REPLACE TABLE `{DS}.in_pjm_bus_injection` AS
SELECT bus_number,
       ANY_VALUE(bus_label) AS bus_label,
       ANY_VALUE(bus_kv) AS bus_kv,
       MIN(IF(ABS(dfax) >= 0.05 AND pre_loading_pct < 100, available_mw, NULL)) AS injection_mw,
       COUNTIF(pre_loading_pct >= 100) AS existing_overloads,
       COUNT(*) AS facilities,
       ARRAY_AGG(IF(ABS(dfax) >= 0.05 AND pre_loading_pct < 100, transmission_facility, NULL)
                 IGNORE NULLS ORDER BY available_mw ASC LIMIT 1)[OFFSET(0)] AS binding_facility,
       ANY_VALUE(case_label) AS case_label
FROM `{DS}.in_pjm_queuescope_injection`
WHERE operating_mode = 'INJECTION' AND desired_mw = {RUNG}
GROUP BY bus_number""").result()

# The request-size ladder at bus grain.  available_mw is request-invariant, so "does a
# 500 MW project fit here" is a comparison against one harvested number, not a re-harvest.
client.query(f"""
CREATE OR REPLACE VIEW `{DS}.vw_pjm_bus_injection_ladder` AS
SELECT bus_number, bus_label, bus_kv, injection_mw, existing_overloads, binding_facility,
       case_label, r AS request_mw, injection_mw >= CAST(r AS FLOAT64) AS request_fits
FROM `{DS}.in_pjm_bus_injection`, UNNEST([100, 300, 500, 1000, 2500, 5000]) AS r""").result()

st = list(client.query(f"""
    SELECT COUNT(*) buses, COUNTIF(injection_mw > 0) positive,
           COUNTIF(injection_mw IS NULL) null_headroom,
           ROUND(MIN(injection_mw), 1) min_mw, ROUND(MAX(injection_mw), 1) max_mw,
           ROUND(AVG(injection_mw), 2) avg_mw, SUM(existing_overloads) overloads
    FROM `{DS}.in_pjm_bus_injection`"""))[0]
print("in_pjm_bus_injection:", dict(st))

print("\nbus-level ladder (PJM INJECTION, AEP):")
for r in client.query(f"""
    SELECT request_mw, COUNTIF(request_fits) buses_that_fit, COUNT(*) buses
    FROM `{DS}.vw_pjm_bus_injection_ladder` GROUP BY 1 ORDER BY 1"""):
    print(f"   {r.request_mw:>5} MW: {r.buses_that_fit:,} of {r.buses:,} buses fit the request")

print("\ndirection comparison, buses present in BOTH directions:")
for r in client.query(f"""
    SELECT COUNT(*) buses_both,
           ROUND(AVG(i.injection_mw), 2) avg_injection, ROUND(AVG(w.withdrawal_mw), 2) avg_withdrawal,
           COUNTIF(i.injection_mw > w.withdrawal_mw) inj_gt_wd,
           COUNTIF(w.withdrawal_mw > i.injection_mw) wd_gt_inj,
           COUNTIF(i.injection_mw = w.withdrawal_mw) equal
    FROM `{DS}.in_pjm_bus_injection` i
    JOIN `{DS}.in_pjm_bus_withdrawal` w USING (bus_number)"""):
    print("  ", dict(r))
print("PJM INJECTION ROLLUP COMPLETE -- now run: python scripts/register_rto_directions.py")
