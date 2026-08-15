"""Lane D step 3: freshness diff. Read-only against energy.si_signals (held) compared
to the Lane D staging tables in indiana_app.in_si_refresh_* (freshly re-pulled). Never
deletes or modifies anything held -- this produces a report only.
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lane_d_util as u

client = u.bq_client()


def q(sql):
    return [dict(r) for r in client.query(sql).result()]


report = {}

# ---------------------------------------------------------------------------
# 1. SRI tax-sale (D1) -- Indiana slice
# ---------------------------------------------------------------------------
held = q("""SELECT COUNT(*) n, MIN(observed_date) earliest, MAX(observed_date) latest
            FROM `energy-platfrom.energy.si_signals`
            WHERE source_id='si_d1_sri_taxsale_listings' AND state='IN'""")[0]
refreshed_n = q("""SELECT COUNT(*) n FROM
            `energy-platfrom.indiana_app.in_si_refresh_sri_taxsale_in`""")[0]["n"]
disp = q("""SELECT saleStatusDescription v, COUNT(*) n FROM
            `energy-platfrom.indiana_app.in_si_refresh_sri_taxsale_in`
            GROUP BY 1 ORDER BY n DESC""")
remediated_labels = {"Sold To Plaintiff", "Cancelled", "Sold To 3rd Party", "COUNTY"}
open_labels = {"DELINQUENT", "Sale Active"}
remediated_n = sum(d["n"] for d in disp if d["v"] in remediated_labels)
open_n = sum(d["n"] for d in disp if d["v"] in open_labels)
other_n = refreshed_n - remediated_n - open_n
report["si_d1_sri_taxsale_listings"] = {
    "held_rows": held["n"], "held_earliest": str(held["earliest"]), "held_latest": str(held["latest"]),
    "refreshed_rows": refreshed_n,
    "disposition_breakdown": disp,
    "remediated_n": remediated_n, "open_n": open_n, "other_n": other_n,
    "join_note": "si_signals keys D1 rows on address_norm (free text), not propertyId/altPropertyId "
                 "-- no stable id survives into the fact table, so a row-level held<->refreshed join "
                 "was not attempted (would require guessing the address-normalisation function, which "
                 "the project's own standing rule forbids). Reporting corpus-level freshness instead: "
                 "of the {} CURRENTLY LIVE Indiana SRI listings, {} ({:.1f}%) show a disposition the "
                 "publisher itself calls resolved (Sold To Plaintiff/Cancelled/Sold To 3rd Party/COUNTY) "
                 "and {} ({:.1f}%) are still open (DELINQUENT/Sale Active).".format(
                     refreshed_n, remediated_n, 100*remediated_n/refreshed_n,
                     open_n, 100*open_n/refreshed_n),
}

# ---------------------------------------------------------------------------
# 2. IBTR determinations (D26)
# ---------------------------------------------------------------------------
held = q("""SELECT COUNT(*) n, MIN(observed_date) earliest, MAX(observed_date) latest
            FROM `energy-platfrom.energy.si_signals`
            WHERE source_id='appeals_in_ibtr_determinations' AND state='IN'""")[0]
refreshed_n = q("""SELECT COUNT(*) n FROM
            `energy-platfrom.indiana_app.in_si_refresh_ibtr_appeals`""")[0]["n"]
status_disp = q("""SELECT statusName v, COUNT(*) n FROM
            `energy-platfrom.indiana_app.in_si_refresh_ibtr_appeals`
            GROUP BY 1 ORDER BY n DESC""")
type_disp = q("""SELECT typeName v, COUNT(*) n FROM
            `energy-platfrom.indiana_app.in_si_refresh_ibtr_appeals`
            GROUP BY 1 ORDER BY n DESC""")
date_range = q("""SELECT MIN(SAFE.PARSE_DATE('%Y-%m-%dT%H:%M:%S', SUBSTR(date,1,19))) mn,
                          MAX(SAFE.PARSE_DATE('%Y-%m-%dT%H:%M:%S', SUBSTR(date,1,19))) mx
                   FROM `energy-platfrom.indiana_app.in_si_refresh_ibtr_appeals`""")[0]
report["appeals_in_ibtr_determinations"] = {
    "held_rows": held["n"], "held_earliest": str(held["earliest"]), "held_latest": str(held["latest"]),
    "refreshed_rows": refreshed_n,
    "refreshed_date_range": [str(date_range["mn"]), str(date_range["mx"])],
    "status_breakdown": status_disp,
    "type_breakdown": type_disp,
    "note": ("This IBTR endpoint publishes DETERMINATIONS (decisions), so nearly all rows are "
             "'Closed' by construction ({} of {} = {:.1f}%) -- the time-sensitivity payoff here is "
             "the {} NEW determinations issued since our held snapshot (refreshed {} vs held {}), "
             "not a closed-vs-open split. typeName shows the decision shape: settlements, dismissals, "
             "remands and board determinations, all previously undifferentiated in the held signal."
             .format(next((d['n'] for d in status_disp if d['v']=='Closed'), 0), refreshed_n,
                     100*next((d['n'] for d in status_disp if d['v']=='Closed'), 0)/refreshed_n,
                     refreshed_n - held["n"], refreshed_n, held["n"])),
}

# ---------------------------------------------------------------------------
# 3. WARN notices (D19)
# ---------------------------------------------------------------------------
held = q("""SELECT COUNT(*) n, MIN(observed_date) earliest, MAX(observed_date) latest
            FROM `energy-platfrom.energy.si_signals`
            WHERE source_id='warn_notices' AND state='IN'""")[0]
refreshed_n = q("""SELECT COUNT(*) n FROM
            `energy-platfrom.indiana_app.in_si_refresh_warn_notices`""")[0]["n"]
type_disp = q("""SELECT Notice_Type v, COUNT(*) n FROM
            `energy-platfrom.indiana_app.in_si_refresh_warn_notices`
            GROUP BY 1 ORDER BY n DESC""")
closure_n = sum(d["n"] for d in type_disp if d["v"] and "CL" in d["v"].upper())
layoff_n = sum(d["n"] for d in type_disp if d["v"] and d["v"].upper() in ("LO", "L/O"))
past_lo_cl = q("""SELECT COUNTIF(SAFE.PARSE_DATE('%m/%d/%Y', LO_CL_Date) < CURRENT_DATE()) past_n,
                          COUNTIF(SAFE.PARSE_DATE('%m/%d/%Y', LO_CL_Date) >= CURRENT_DATE()) future_n,
                          COUNTIF(SAFE.PARSE_DATE('%m/%d/%Y', LO_CL_Date) IS NULL) unparsed_n
                   FROM `energy-platfrom.indiana_app.in_si_refresh_warn_notices`""")[0]
report["warn_notices"] = {
    "held_rows": held["n"], "held_earliest": str(held["earliest"]), "held_latest": str(held["latest"]),
    "refreshed_rows": refreshed_n,
    "notice_type_breakdown": type_disp,
    "closure_type_n": closure_n, "layoff_only_type_n": layoff_n,
    "lo_cl_date_vs_today": past_lo_cl,
    "note": ("{} of {} refreshed notices ({:.1f}%) carry a CLOSURE-shaped Notice Type; "
             "{} carry a plain layoff (LO) type. Independently, {} of {} rows have an LO/CL Date "
             "(layoff/closure date) already IN THE PAST as of today (2026-08-14) -- i.e. the "
             "predicted event has now actually happened at the publisher, vs {} still in the future."
             .format(closure_n, refreshed_n, 100*closure_n/refreshed_n, layoff_n,
                     past_lo_cl["past_n"], refreshed_n, past_lo_cl["future_n"])),
}

# ---------------------------------------------------------------------------
# 4. IOCS statewide eviction/court stats (D17)
# ---------------------------------------------------------------------------
held = q("""SELECT COUNT(*) n, MIN(observed_date) earliest, MAX(observed_date) latest
            FROM `energy-platfrom.energy.si_signals`
            WHERE source_id='si_d17_in_iocs_court_year' AND state='IN'""")[0]
ev_by_sheet = q("""SELECT _src_sheet sheet, SUM(SAFE_CAST(EV AS INT64)) ev_sum, COUNT(*) n_courts
            FROM `energy-platfrom.indiana_app.in_si_refresh_iocs_eviction`
            WHERE EV IS NOT NULL
            GROUP BY 1 ORDER BY ev_sum DESC""")
report["si_d17_in_iocs_court_year"] = {
    "held_rows": held["n"], "held_earliest": str(held["earliest"]), "held_latest": str(held["latest"]),
    "refreshed_rows_all_sheets": q("""SELECT COUNT(*) n FROM
                `energy-platfrom.indiana_app.in_si_refresh_iocs_eviction`""")[0]["n"],
    "EV_column_by_report_sheet": ev_by_sheet,
    "note": ("The held signal (370 rows) is a thin slice of one column (EV = eviction case type) "
             "from one sheet of a 19-sheet, 57-column statewide workbook. The refresh captured ALL "
             "sheets/columns; EV_column_by_report_sheet shows the eviction-code count for 'Cases "
             "Pending 1/1/2025' (STILL OPEN at year start) vs 'Disposed' (RESOLVED during 2025) vs "
             "'Cases Pending 12/31/25' (STILL OPEN at year end) -- the direct open-vs-remediated split "
             "this lane is looking for, at statewide grain (no 2026 file exists yet under this naming "
             "pattern; probed and 404d)."),
}

# ---------------------------------------------------------------------------
# 5. EPA brownfield RE-Powering (STATE-class signal, no observed_date expected)
# ---------------------------------------------------------------------------
held = q("""SELECT COUNT(*) n FROM `energy-platfrom.energy.si_signals`
            WHERE source_id='brownfield_epa_repowering' AND state='IN'""")[0]
refreshed_n = q("""SELECT COUNT(*) n FROM
            `energy-platfrom.indiana_app.in_si_refresh_brownfield_epa_in`""")[0]["n"]
report["brownfield_epa_repowering"] = {
    "held_rows": held["n"], "refreshed_rows": refreshed_n,
    "note": ("STATE-class signal (site characteristics, no event date) -- freshness here is row-count "
             "drift only: {} held vs {} refreshed ({:+d}).".format(held["n"], refreshed_n, refreshed_n - held["n"])),
}

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_scratch", "08_freshness_diff.json")
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False, default=str)
print(f"Wrote {out_path}\n")

for src, d in report.items():
    print(f"=== {src} ===")
    print(json.dumps(d, indent=2, ensure_ascii=False, default=str))
    print()
