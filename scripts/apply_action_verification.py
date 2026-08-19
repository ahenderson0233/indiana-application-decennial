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


# ==============================================================================================
# F3a - HOWARD COUNTY. Board of Commissioners, two-year data-centre moratorium.
#
# NOT VERIFIED, and the re-check made our own record LESS certain rather than more - which is the
# useful outcome here. The county's own 2026-08-17 commissioners' packet lists no data-centre item
# under any heading; its only ordinances are a rezoning (2026-BCCO-29) and flood damage prevention
# (2026-BCCO-30). Howard publishes each meeting's minutes inside the FOLLOWING meeting's packet, so
# the 08-17 minutes are not due until September. NOT_FOUND is therefore expected, and it is NOT
# "no action was taken".
#
# ⚠ AND THERE IS NOW A DIRECT CONFLICT THAT OUR ROW WAS ASSERTING ITS WAY PAST.
# We stored "Two-year data-center moratorium". That figure came from a news lead, not a government
# source - the verdict has always been NOT_FOUND. A newer Kokomo Lantern piece, verified here by
# fetching it directly, says something different, verbatim:
#     "This is a temporary moratorium that lasts for ONE year"
#     "the county can lift the restriction earlier than one year should the commissioners develop
#      a regulatory ordinance in a shorter time period"
# reporting a unanimous Board of Commissioners vote on 2026-08-18 - a date on which the county's
# own published 2026 schedule has NO meeting (August has only the 3rd and the 17th).
#
# So we hold two UNVERIFIED and MUTUALLY INCONSISTENT durations. The honest state is that the
# duration is UNKNOWN pending the county's own minutes, and the instrument text is rewritten to
# say so rather than to keep repeating "two-year" as though we had it from the county.
# ⚠ The lead_url we hold is DEAD (HTTP 404). Replaced with the live article.
add(
    county="Howard",
    jurisdiction_like="Howard County%",
    verdict="NOT_FOUND_AT_OFFICIAL_SOURCE",
    confirmed_action_type="proposed",
    verified_instrument=(
        "Data-centre moratorium, DURATION UNKNOWN AND DISPUTED. Our earlier record said 'two-year' "
        "and a later news report says 'one year'; NEITHER is from a Howard County source. No "
        "data-centre instrument of any number appears in any published county record. For contrast "
        "the only ordinances on the 2026-08-17 agenda are 'Rezoning of Property - 3820 W 200 N - "
        "Ord. No. 2026-BCCO-29' and 'Updated Howard County Flood Damage Prevention - Ord. No. "
        "2026-BCCO-30'."),
    date_note=(
        "Do not record a duration or an expiry until the county's own minutes state one. The two "
        "figures in circulation (two-year, one-year) are both from news leads and they disagree."),
    verification_note=(
        "Re-checked 2026-08-19 for F3. The 2026-08-17 Board of Commissioners packet - a scanned PDF "
        "with no text layer - contains the agenda for that meeting and the minutes of 2026-08-03, "
        "and lists NO data-centre or moratorium item. Howard publishes minutes one meeting in "
        "arrears, so the 08-17 minutes are due in the September packet; that is the artifact to "
        "watch. CONFLICT: Kokomo Lantern 'County adopts data center moratorium' reports a unanimous "
        "vote on 2026-08-18 for a ONE-year moratorium liftable early - but the county's own 2026 "
        "schedule has no 08-18 meeting (August is the 3rd and the 17th only). Lead is unverified "
        "and its date is unexplained. Our previously held lead URL 404s and has been replaced. "
        "City of Kokomo remains BLOCKED by its own robots.txt and was deliberately not probed."),
    official_url=("https://www.in.gov/counties/howard/home/meetings,-minutes,-and-agendas/"
                  "meeting-and-agenda-docs/commissioners/2026/"
                  "08.17.2026-Commissioner-Meeting-Packet.pdf"),
    lead_url="https://kokomolantern.substack.com/p/county-adopts-data-center-moratorium",
    final_evidence_grade=(
        "county packet READ and contains no such item; minutes for the meeting in question are not "
        "yet published; a news lead conflicts with our own held duration"),
)

# ==============================================================================================
# F3b - CITY OF ELKHART. Common Council, temporary moratorium.
#
# VERIFIED at the city's own documents, and the answer is NOT ADOPTED - it advanced from FIRST
# READING and final action is set for a special meeting on 2026-08-27.
#
# ⭐ THIS IS THE ONE ROW THE RE-CHECK GENUINELY ADVANCED. We previously held only "a proposed
# ordinance from Mayor Rod Roberson", with no number and no text. We now have the number, the full
# title, and the operative expiry clause.
#
# ⚠ AND IT CORRECTS AN ASSUMPTION BEFORE IT COULD BE MADE: effective_to stays NULL. December 31,
# 2027 appears in this ordinance too - but as the LAST OF THREE ALTERNATIVE TRIGGERS in Section 7,
# whichever comes first, and the ordinance is not adopted so nothing is fixed. Writing 2027-12-31
# here would repeat, in a second county, exactly the error found in Marion this morning.
#
# HOW FAR THIS WAS INDEPENDENTLY CONFIRMED, stated rather than implied:
#   CONFIRMED HERE - the three documents exist at the cited paths on the city's own SharePoint,
#   are reachable with no login, and match their descriptions: "8.17.26 VOTING RECORD" is 2 pages,
#   and a document titled "Agenda & Packet 8.27 meeting" exists, which is itself corroboration
#   that a 2026-08-27 special meeting is scheduled.
#   NOT CONFIRMABLE BY EXTRACTION - all of them are SCANNED IMAGES with no text layer (fetched and
#   checked: 0 inflatable streams, 0 extractable characters), so the ordinance number, the Section
#   7 wording and the 9-0 vote tallies rest on a visual read of those images, not on text this
#   session could pull. Graded accordingly below.
add(
    county="Elkhart",
    jurisdiction_like="City of Elkhart%",
    verdict="VERIFIED_AT_OFFICIAL_SOURCE",
    confirmed_action_type="proposed",
    verified_instrument=(
        "PROPOSED ORDINANCE 26-O-32, 'AN ORDINANCE OF THE COMMON COUNCIL OF THE CITY OF ELKHART, "
        "INDIANA ESTABLISHING A TEMPORARY MORITORIUM ON THE ACCEPTANCE AND PROCESSING OF NEW "
        "APPLICATIONS FOR DATA CENTERS AND BATTERY ENERGY STORAGE FACILITIES, AND DIRECTING IMPACT "
        "STUDIES TO INFORM FUTURE LAND-USE STANDARDS' [the agenda's spelling 'MORITORIUM' is "
        "verbatim; the ordinance text spells it 'MORATORIUM']. The ordinance caption still reads "
        "'ORDINANCE NO. ________' - blank, no number assigned, because it is not adopted."),
    verified_observed_date="2026-08-17",
    expiry_condition_verbatim=(
        "Section 7. Duration; Expiration. This temporary moratorium shall commence upon the "
        "effective date of this Ordinance and shall automatically expire on the earliest of: "
        "(a) Council action lifting or terminating the moratorium; (b) The completion of all "
        "studies identified in Section 4 and the development of appropriate standards for "
        "consideration of permit applications for Data Centers and BESS (including presentation of "
        "draft text to the Plan Commission); or (c) December 31, 2027. -- Section 10. Effective "
        "Date. This Ordinance shall be in full force and effect from and after its passage by the "
        "Common Council and approval as required by law."),
    date_note=(
        "effective_to is deliberately NULL. December 31, 2027 is only the LAST OF THREE "
        "ALTERNATIVE triggers in Section 7, whichever comes first, and the ordinance is not "
        "adopted, so no date is fixed. Recording it as an end date would repeat the Marion error."),
    verification_note=(
        "Re-checked 2026-08-19 for F3. NOT adopted on 2026-08-17: the council's own agenda places "
        "26-O-32 under 'New Business / Ordinances on First Reading', while that same agenda uses a "
        "separate 'Ordinances on Second-Third Reading' heading for a different ordinance. The "
        "council's own 'VOTING RECORD FOR AUGUST 17, 2026' records exactly two final actions, both "
        "9-0 - Ordinance No. 6098 (Proposed Ordinance 26-O-30, an alley vacation) and Resolution "
        "No. 26-R-41 - and 26-O-32 does not appear on it at all. FINAL ACTION IS SET FOR A SPECIAL "
        "MEETING ON 2026-08-27, where 26-O-32 is the single item of business. Whether the text was "
        "amended at first reading is unknown: the 08-17 minutes are not yet published (that "
        "meeting was still approving the 07-27 minutes). NOTE THE SCOPE - this ordinance covers "
        "BATTERY ENERGY STORAGE as well as data centres, which is broader than our other rows."),
    official_url=("https://elkhartin.sharepoint.com/sites/TestSite/Shared%20Documents/"
                  "Voting%20Records/8.17.26%20VOTING%20RECORD.pdf"),
    final_evidence_grade=(
        "city's OWN documents, publicly reachable with no login, and their existence, page counts "
        "and titles were re-confirmed independently this session. They are SCANNED IMAGES with no "
        "text layer, so the ordinance number, Section 7 text and vote tallies come from a visual "
        "read rather than extracted text"),
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
                    # lead_url is settable because a LEAD can rot: Howard's held lead 404s.
                    # It is still only ever a lead - it can never satisfy official_url.
                    "lead_url",
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
