"""F3 / F4 - apply a re-verification of a county data-centre action to in_dc_actions_resolved.

These are the CLOCK items: rows whose verdict was pending because a council had not voted yet.
F3 (Howard County, City of Elkhart) was scheduled 2026-08-17; F4 (Marion MDC, Proposal No. 238)
was scheduled 2026-08-19.

================================================================================================
WHY THIS IS A SCRIPT AND NOT A HAND-RUN UPDATE
================================================================================================
`in_dc_actions_resolved` was loaded by an agent sweep, not built by anything in scripts/, so there
is no build to re-run and a hand-typed UPDATE would leave no trace of WHY a row changed. The
findings below are declarative and live in git: a reader can see what was claimed, which government
document backed it, and when. Re-running is idempotent.

================================================================================================
THE RULES THAT GOVERN WHAT MAY BE WRITTEN HERE
================================================================================================
* `posture_renderable` is TRUE **only** for VERIFIED_AT_OFFICIAL_SOURCE. It is the gate that stops
  an unverified news lead reaching the map as a county action, and export_grid_sentiment.py filters
  on it. A NOT_FOUND or BLOCKED row is recorded and stays off the map.
* NEWS IS A LEAD, NEVER A VERIFICATION. `lead_url` may be a newspaper; `official_url` may not.
* ABSENCE OF EVIDENCE IS NOT EVIDENCE OF ABSENCE. A meeting we cannot find a record of is
  NOT_FOUND_AT_OFFICIAL_SOURCE - never "no action taken", and never a downgrade of what we already
  hold. A finding that says "unchanged" leaves the row exactly as it is.
* ⛔ NEVER INVENT AN EXPIRY DATE. If a moratorium states a DURATION but no end date, the duration
  goes in `expiry_condition_verbatim` and `verified_effective_to` stays NULL unless the document
  itself states the date. An open-ended pause given a date it does not have is worse than one with
  no date at all - see G89.
* A GATED SOURCE RECORDED AS BLOCKED, WITH ITS WALL QUOTED, IS A SUCCESS. City of Kokomo is
  already BLOCKED by its own robots.txt and is deliberately not re-probed.

RE-RUN: python scripts/apply_action_verification.py            (report only, changes nothing)
        python scripts/apply_action_verification.py --apply    (writes)
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import argparse
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
TABLE = f"{DS}.in_dc_actions_resolved"
client = bigquery.Client(project="energy-platfrom")

# ==============================================================================================
# FINDINGS. Filled in from the 2026-08-19 re-verification. Each entry MUST carry an official_url
# when its verdict is VERIFIED_AT_OFFICIAL_SOURCE; the script refuses to write one that does not.
#
# `county` + `jurisdiction_like` selects the row. jurisdiction_like is a LIKE pattern because the
# stored jurisdiction strings are long and some are truncated in places.
# ==============================================================================================
FINDINGS = []          # populated below by the F3/F4 pass


def add(**kw):
    FINDINGS.append(kw)


# ==============================================================================================
# F4 - MARION, MDC final action on Proposal No. 238 / 2026-AO-001 (Amended).
#
# NOT adopted. The MDC hearing is 2026-08-19 at 1:00 PM and had not convened; its meeting page
# carries an agenda, notices and a packet, and NO minutes, hearing results or video - unlike the
# 2026-08-05 meeting on the same portal, which does. Item 10 sits under "PETITIONS FOR PUBLIC
# HEARING": scheduled, not decided. So confirmed_action_type stays 'proposed'. (The VERDICT does
# not change - see the correction at the end of this block; it describes whether the instrument is
# verified at a government source, not whether its next milestone has happened.)
#
# ⭐ BUT THE RE-CHECK FOUND A REAL DEFECT IN WHAT WE ALREADY STORED, and it is G89's exact concern
# arriving live. We held verified_effective_to = '2027-12-31' as though it were a firm end date.
# Read from the ordinance text itself (verified independently, not taken from the agent):
#
#     "...regulations that shall be developed by staff after a moratorium ending NO LATER THAN
#      December 31, 2027, on the permitting or allowance of any and all data centers..."
#
# That is a CEILING, NOT A TERM. The moratorium ends when staff-developed regulations arrive;
# 2027-12-31 is merely the latest it may run. The DMD staff report uses the same hedge ("through
# no later than December 31, 2027"). Storing a flat date asserts a duration the document does not
# grant - so the date stays, because an outer bound is genuinely useful to a siter, but the
# VERBATIM CONDITION now travels with it and a date_note says plainly that it is a ceiling.
#
# Also verified from the same document, and worth recording because it is NOT what we held:
#   * "On August 10, 2026, the City-County Council approved an amendment to 2026-AO-001 (Amended)"
#     - our record had only the 2026-07-06 introduction.
#   * "SECTION 24. This ordinance shall be in effect from and after its passage by the Council..."
#     followed by "passed by the City-County Council this _____ day of __________, 2026" - the
#     passage date is BLANK, and the heading reads "CITY-COUNTY GENERAL ORDINANCE NO. , 2026" with
#     the number BLANK. No adopted, numbered, signed ordinance exists in the published record.
#     That is the strongest single reason this stays 'proposed'.
# ⛔ AND A MISTAKE MADE WHILE WRITING THIS, KEPT HERE BECAUSE IT IS THE EASY ONE TO REPEAT.
# The first version set verdict = NOT_FOUND_AT_OFFICIAL_SOURCE, reasoning "the MDC has not acted".
# That DOWNGRADED A ROW THAT ALREADY CARRIED A GENUINE VERIFICATION and, because posture_renderable
# follows the verdict, knocked a real county action off the map. The verdict describes whether THE
# INSTRUMENT IS VERIFIED AT A GOVERNMENT SOURCE - not whether the next step in its journey has
# happened. It is more verified than before: today its full text was read out of the MDC's own
# packet. What is pending belongs in confirmed_action_type ('proposed') and in the note.
# Rule restated for the next person: a re-check may CONFIRM or ADVANCE a row. It must never
# silently demote one because a later milestone is still in the future.
add(
    county="Marion",
    jurisdiction_like="%MDC final a%",
    verdict="VERIFIED_AT_OFFICIAL_SOURCE",
    confirmed_action_type="proposed",
    verified_instrument=(
        "City-County Council Proposal No. 238, 2026 = 2026-AO-001 (Amended). MDC agenda "
        "2026-08-19 item 10: 'PROPOSAL TO AMEND THE ZONING AND SUBDIVISION CONTROL ORDINANCE OF "
        "INDIANAPOLIS-MARION COUNTY, INDIANA: 2026-AO-001 (Amended)' - listed under PETITIONS FOR "
        "PUBLIC HEARING. Ordinance heading still reads 'CITY-COUNTY GENERAL ORDINANCE NO. , 2026' "
        "with the number blank."),
    expiry_condition_verbatim=(
        "SECTION 1, verbatim: 'Revised Code Section 742-109 sub part L of the Zoning Ordinance for "
        "Marion County, Indiana, shall be specifically reserved for data center regulations that "
        "shall be developed by staff after a moratorium ending no later than December 31, 2027, on "
        "the permitting or allowance of any and all data centers within the jurisdiction of the "
        "Metropolitan Planning Commission (MDC)...' SECTION 24, verbatim: 'This ordinance shall be "
        "in effect from and after its passage by the Council and compliance with Ind. Code "
        "36-3-4-14.'"),
    date_note=(
        "2027-12-31 IS A CEILING, NOT A TERM. The instrument says the moratorium ends 'no later "
        "than' that date; it ends when staff-developed regulations arrive. Do not render it as a "
        "firm end date. Effectiveness is keyed to passage, not to a calendar date, and the passage "
        "line in SECTION 24 is still blank."),
    verification_note=(
        "Re-checked 2026-08-19 for F4. MDC hearing is TODAY at 1:00 PM and had not convened; the "
        "meeting page holds agenda, notices and packet only - no minutes, no hearing results, no "
        "video, unlike the 2026-08-05 meeting on the same portal. NEW since our last capture and "
        "verified in the DMD staff report inside the MDC packet: 'On August 10, 2026, the "
        "City-County Council approved an amendment to 2026-AO-001 (Amended)', which struck the "
        "Special Use provisions the MDC had recommended on 2026-07-01 and replaced them with the "
        "bare moratorium. Carve-outs are stated officially for applications with vested rights: "
        "DC Blox, Metrobloks and Sabey. Watch for a '..._mdc_hearing_results_-_municode.pdf' on "
        "the meeting page - that is the artifact the 08/05 meeting produced."),
    official_url=("https://indianapolis-in.municodemeetings.com/bc-mdc-hearing-examiner/page/"
                  "metropolitan-development-commission-august-19-2026"),
    verbatim_snippet=(
        "MDC agenda 2026-08-19, item 10, under PETITIONS FOR PUBLIC HEARING: 'PROPOSAL TO AMEND "
        "THE ZONING AND SUBDIVISION CONTROL ORDINANCE OF INDIANAPOLIS-MARION COUNTY, INDIANA: "
        "2026-AO-001 (Amended)'. DMD staff report timeline: 'August 19, 2026 - Anticipated MDC "
        "vote of City-Council approved proposal'; recommendation 'Approve as amended'."),
    final_evidence_grade=(
        "instrument VERIFIED from the MDC's own packet (full ordinance text read); the MDC's FINAL "
        "ACTION is still pending - hearing is 2026-08-19 1:00 PM and no minutes or hearing results "
        "are posted"),
)


def preflight(f):
    """Refuse a finding that breaks one of the rules above, loudly, before anything is written."""
    problems = []
    v = f.get("verdict")
    if v not in ("VERIFIED_AT_OFFICIAL_SOURCE", "NOT_FOUND_AT_OFFICIAL_SOURCE", "BLOCKED"):
        problems.append(f"verdict {v!r} is not one of the three permitted values")
    if v == "VERIFIED_AT_OFFICIAL_SOURCE":
        if not f.get("official_url"):
            problems.append("VERIFIED with no official_url - a verification must name the document")
        if not f.get("verified_instrument"):
            problems.append("VERIFIED with no instrument quoted")
    if f.get("verified_effective_to") and not (
            f.get("expiry_condition_verbatim") or f.get("date_note")):
        problems.append("an effective_to with nothing quoted to justify it - see G89, do not "
                        "invent an expiry date")
    if v != "VERIFIED_AT_OFFICIAL_SOURCE" and f.get("posture_renderable"):
        problems.append("posture_renderable TRUE on a non-verified row - that is the gate that "
                        "keeps news off the map")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the changes (default: report only)")
    a = ap.parse_args()

    print("=" * 94)
    print("F3 / F4  RE-VERIFICATION OF PENDING COUNTY ACTIONS")
    print("=" * 94)

    before = {(r["county"], r["jurisdiction"]): dict(r) for r in client.query(f"""
        SELECT county, jurisdiction, verdict, confirmed_action_type, verified_effective_to,
               posture_renderable FROM `{TABLE}`
        WHERE county IN ('Howard', 'Elkhart', 'Marion')""")}
    print(f"\ncurrent state of the {len(before)} rows in scope:")
    for (cty, j), r in sorted(before.items()):
        print(f"   {cty:<9} {str(j)[:52]:<54} {str(r['verdict'])[:28]:<30} "
              f"{str(r['confirmed_action_type'])}")

    if not FINDINGS:
        print("\nNo findings loaded. Nothing to apply. (This is the report-only state.)")
        return

    bad = False
    for f in FINDINGS:
        for p in preflight(f):
            print(f"   REFUSED  {f.get('county')}/{f.get('jurisdiction_like')}: {p}")
            bad = True
    if bad:
        raise SystemExit("preflight failed - nothing written")

    for f in FINDINGS:
        sets, params = [], [
            bigquery.ScalarQueryParameter("cty", "STRING", f["county"]),
            bigquery.ScalarQueryParameter("jur", "STRING", f["jurisdiction_like"]),
        ]
        for col in ("verdict", "confirmed_action_type", "verified_instrument",
                    "verified_observed_date", "verified_effective_from", "verified_effective_to",
                    "expiry_condition_verbatim", "verbatim_snippet", "official_url",
                    "date_note", "verification_note", "final_evidence_grade"):
            if col in f:
                sets.append(f"{col} = @{col}")
                params.append(bigquery.ScalarQueryParameter(col, "STRING", f[col]))
        sets.append("posture_renderable = @pr")
        params.append(bigquery.ScalarQueryParameter(
            "pr", "BOOL", f["verdict"] == "VERIFIED_AT_OFFICIAL_SOURCE"))
        sets.append("_verified_at = CAST(CURRENT_TIMESTAMP() AS STRING)")

        sql = (f"UPDATE `{TABLE}` SET {', '.join(sets)} "
               f"WHERE county = @cty AND jurisdiction LIKE @jur")
        if a.apply:
            job = client.query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params))
            job.result()
            n_rows = job.num_dml_affected_rows
            verb = "APPLIED"
        else:
            # ⛔ THE FIRST VERSION OF THIS RAN THE UPDATE UNCONDITIONALLY and only gated the
            # registry insert on --apply, so "report only" silently WROTE. A dry run that writes
            # is worse than no dry run: it removes the one step where a mistake is still cheap.
            # Now the report path counts the target rows with a SELECT and touches nothing.
            n_rows = list(client.query(
                f"SELECT COUNT(*) n FROM `{TABLE}` WHERE county = @cty AND jurisdiction LIKE @jur",
                job_config=bigquery.QueryJobConfig(query_parameters=[
                    p for p in params if p.name in ("cty", "jur")])))[0].n
            verb = "WOULD APPLY"
        print(f"   {verb}  {f['county']:<9} "
              f"{f['jurisdiction_like'][:44]:<46} -> {f['verdict']} / "
              f"{f.get('confirmed_action_type', '(unchanged)')}   rows={n_rows}")

    if a.apply:
        n = list(client.query(f"SELECT COUNT(*) n FROM `{TABLE}`"))[0].n
        client.query(f"""INSERT `{DS}._registry`
          (table_name, source, method, n_rows, gb_scanned, built_at, notes)
          VALUES ('in_dc_actions_resolved',
                  'Indiana county/municipal government websites - F3/F4 clock re-verification',
                  'targeted UPDATE of rows whose vote had not yet happened at first sweep',
                  {n}, 0.01, CURRENT_TIMESTAMP(),
                  'F3 Howard + City of Elkhart (votes scheduled 2026-08-17) and F4 Marion MDC '
                  'Proposal No. 238 (scheduled 2026-08-19) re-checked. posture_renderable stays '
                  'FALSE on anything not verified at a government source. '
                  'RE-SCRAPE COMMAND: python scripts/apply_action_verification.py --apply')
        """).result()
        print("\nregistered.")
    else:
        print("\nreport only - re-run with --apply to write")


if __name__ == "__main__":
    main()
