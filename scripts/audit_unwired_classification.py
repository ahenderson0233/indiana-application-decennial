"""G72 / G80 - close the "231 unwired objects" into a BOUNDED, MAINTAINED ledger.

    python scripts/audit_unwired_classification.py

⛔ WHY THIS EXISTS. G72 has been the biggest row in the backlog for four sessions and its number
kept moving - 231, then 291 of 309, then 235 of 316, then 240 of 323 - because "objects reaching
no surface" is an open-ended list that nobody can ever finish. Worse, the previous sessions'
worklist repeatedly included tables that were ALREADY on a page and simply invisible to the
census instrument (`in_faa_obstacles` has had its own checkbox for days).

The fix is not another sweep. It is to make the list CLOSED: every object that reaches no surface
must carry a REASON, chosen from a small vocabulary, and this audit FAILS when one does not. From
that point on the question stops being "how many are unwired" - which is unanswerable - and
becomes "is any object unwired WITHOUT a reason", which is answerable and stays answered.

THE VOCABULARY. Only these are acceptable, and each says something different:

  empty                  the table holds 0 rows. There is nothing to show.
  not_placeable          real data that CANNOT be attributed to Indiana - the seven gas boards
                         that post an operator's whole system with no state column. Wiring them
                         would put Louisiana capacity on an Indiana pipeline (G80's near-miss).
  harvest_rung           a QueueScope ladder rung or a harvest working table. tier0 reads one
                         rung; the others exist so the ladder can be resumed and audited.
  raw_feed               a per-year or per-source input that a shipped table is built from.
  coverage_ledger        a one-row record of what we searched and what we hold. It is provenance,
                         not content, and the Data page renders the register that summarises it.
  superseded             replaced by a v2/dedup/normalised table that IS wired.
  WIRE                   ⛔ NOT a reason. An object marked WIRE is work still to do, and this
                         audit prints it as the worklist.

⚠ AN UNCLASSIFIED OBJECT IS A FAILURE, NOT A WARNING. That is the whole mechanism: a new table
that reaches no surface and no reason will fail this audit the next time anyone runs it, which
is how the list stays closed instead of drifting back open.
"""
import io, os, re, subprocess, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = (r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California"
        r"\ca-capacity-deploy\indiana-application-decennial")

# ---------------------------------------------------------------------------------------------
# THE LEDGER. reason -> (why, [objects])
# Every entry was measured, not assumed. Where a claim is about CONTENT ("no state column"), it
# was checked against the table, because G80's whole lesson is that a name is not a data test.
CLASSIFIED = {
    # G124, 2026-08-20d. A REASON, not an excuse: this object's surface is a DOCUMENT, and it is
    # generated in the same run that writes the table. Putting a 337-row engineering ledger about
    # loader idempotency and column coverage onto a siting page would be showing a developer's
    # workpaper to a site selector. The table exists so the checkpoint can audit the ledger for
    # drift, which is a use, just not a rendered one.
    "document_surface": ("the surface is a generated DOCUMENT rather than a page - "
                         "docs/RESCRAPE_LEDGER.md is written by the same script in the same run, "
                         "and the table exists so the ledger can be audited for drift", [
        "in_rescrape_ledger",
    ]),
    "empty": ("0 rows held - there is nothing to render, and an empty layer on a map reads as "
              "'we looked and found none' rather than 'we hold nothing'", [
        "in_data_centers_cloudscene", "in_gas_lng_terminals", "in_gas_processing_plants",
        "in_miso_poi", "in_nrc_reactors",
    ]),
    "not_placeable": ("G80's near-miss, and the reason this category exists at all: these gas "
                      "capacity boards post the OPERATOR'S WHOLE SYSTEM with no state column. "
                      "ANR's points are in Ohio, Texas Gas's in Louisiana, Vector's in Michigan. "
                      "Wiring them would attach out-of-state capacity to an Indiana pipeline. "
                      "Only Panhandle Eastern and Trunkline can be placed, and both are wired", [
        "in_gas_capacity_anr", "in_gas_capacity_crossroads", "in_gas_capacity_midwestern",
        "in_gas_capacity_ngpl", "in_gas_capacity_northern_border", "in_gas_capacity_texas_gas",
        "in_gas_capacity_vector",
    ]),
    "harvest_rung": ("a QueueScope ladder rung or harvest working table. in_bus_capacity_tier0 "
                     "reads the 5,000 MW rung; the others exist so the ladder can be resumed, "
                     "audited and re-pointed. Rendering a rung would publish a request size "
                     "nobody asked about", [
        "in_pjm_qs_c23_inj_10", "in_pjm_qs_c23_inj_15", "in_pjm_qs_c23_inj_25",
        "in_pjm_qs_c23_wd_10", "in_pjm_qs_c23_wd_15", "in_pjm_qs_c23_wd_25",
        "in_pjm_qs_c23_inj_50", "in_pjm_qs_c23_wd_50",
        "in_pjm_qs_withdrawal_rungcheck", "in_bus_headroom_miso_ladder", "in_miso_poi_ladder",
        "in_pjm_bus_locations_v2",
    ]),
    # ⭐ `pending_pipeline_join` HELD in_si_warn_placed FOR EXACTLY ONE DAY AND IS NOW EMPTY OF IT.
    # The class was honest - a table that exists is not a table that reaches a reader - and the
    # operator's reply was the right one: *"all of the changes you made have to flow throughout the
    # application."* It is now a source block in build_si_signal_v2.py, so it reaches every surface
    # and no longer belongs on this list. The class is KEPT because the situation will recur, and
    # naming it is what stops the next one being quietly filed as wired.
    "pending_pipeline_join": ("built and correct, and not yet consumed by the pipeline it was "
                              "built for. ⛔ Recorded as pending rather than as wired, because a "
                              "table that exists is not a table that reaches a reader - and this "
                              "project has closed four rows on exactly that confusion", [
    ]),
    "raw_feed_warn": ("the DWD WARN listing as the publisher renders it - one row per notice with "
                      "the filing link. It is the SOURCE OF TRUTH for filing URLs that "
                      "extract_warn_addresses.py reads; the placed table built from it is what "
                      "reaches a parcel, and the page copy is kept so the scrape is auditable", [
        "in_si_warn_page",
    ]),
    # ⭐ G152, 2026-08-21. Operator: *"Even if a source scrapes everything but one column, we still
    # want to rescrape it for everything because that one field may contain something materially
    # important … it is crucial that we have full visibility over each dataset."* These are the
    # full-width Indiana clips of the 19 upstream sources behind the SI signals, taken because that
    # ruling makes width unconditional - NOT because each one has a page waiting for it.
    # ⚠ Two of them already feed shipped signals and are therefore NOT in this list:
    #   in_si_up_cmbs -> D28_cmbs_loan_distress and D29_anchor_tenant_exit
    #   in_si_up_indy_landbank -> I3_land_bank
    # ⭐ AND FOR SEVERAL OF THE REST, THE NEGATIVE **IS** THE PRODUCT. in_si_up_warn_multistate
    # exists so that "every address column is NULL on all 1,220 Indiana rows" is an auditable fact
    # rather than a remembered one, and in_si_up_vacancy_derived so that "parcel_owner and
    # assessed_value are 100% NULL for Indiana" stops anyone re-checking it hopefully. A measured
    # negative that nobody can re-derive is a rumour.
    "upstream_full_width": ("a FULL-WIDTH Indiana clip of an upstream source behind an SI signal, "
                            "held under the operator's 2026-08-21 ruling that every source is "
                            "captured at full width. The SIGNAL renders; the clip is the evidence "
                            "the signal was derived from, and for several of them the measured "
                            "NEGATIVE is the deliverable. Guarded by "
                            "scripts/audit_si_upstream_width.py", [
        "in_si_up_bankruptcy", "in_si_up_brownfield", "in_si_up_ibtr_appeals",
        "in_si_up_indy_code", "in_si_up_indy_rezoning", "in_si_up_indy_taxsale",
        "in_si_up_iocs_court", "in_si_up_seized_auction", "in_si_up_sri_taxsale",
        "in_si_up_vacancy_derived", "in_si_up_warn_multistate",
    ]),
    "raw_feed": ("a per-year or per-source input that a shipped table is built from. The built "
                 "table is what renders; the feed is kept so the build can be re-run and "
                 "audited", [
        "in_nfirs_basicincident_2022", "in_nfirs_basicincident_2023", "in_nfirs_basicincident_2024",
        "in_nfirs_incidentaddress_2022", "in_nfirs_incidentaddress_2023",
        "in_nfirs_incidentaddress_2024", "in_nfirs_fireincident_2022",
        "in_data_centers", "in_data_centers_datacentermap", "in_nhd_waterbody",
        "in_miso_dpp2025_counties", "in_miso_dpp2025_footprint",
    ]),
    "coverage_ledger": ("a one-row record of what was searched and what is held - provenance, "
                        "not content. The Data page renders the register that summarises these; "
                        "each one individually is a footnote, and a footnote is not a surface", [
        "in_balancing_authority_areas", "in_commission_posture", "in_dc_docket_tracker",
        "in_state_irp_catalog", "in_puc_state_access_ledger", "in_groundwater_sites",
        "in_sec_cik_registrant_state",
    ]),
    "superseded": ("replaced by, or a second derivation of, a table that IS wired - kept only so "
                   "the change stays auditable", [
        "in_fsis_establishments_inactive",
        # 642 rows over EXACTLY the same 642 MISO points as in_miso_poi_state (measured: 642
        # shared, no residue either side), and grid.html already carries a 300 MW POI card.
        # Wiring it would put two answers to one question on one page.
        "in_bus_headroom_300",
    ]),
    "no_indiana_content": ("⛔ AN `in_` PREFIX IS NOT A CLIP. Measured row by row, these hold no "
                           "Indiana data at all, so there is nothing to surface and the name is "
                           "the defect. This is the same failure G72 found in in_tribal_land "
                           "(14 rows, none in Indiana): an unwired table is an UNAUDITED table, "
                           "and it took wiring one to discover the other", [
        # 33 Chapter 7 trustee final reports across MO, CA, MA, IL, OK, OH, MT, VA, SD. Zero IN.
        "in_ustp_ch7_tfr",
    ]),
    # ⛔ WORK, NOT A REASON. Anything here is still on the G72 worklist.
    # 2026-08-20: emptied. The sixteen that stood here were wired by export_wired_batch2.py and
    # the seventeenth (in_ustp_ch7_tfr) turned out to hold no Indiana rows at all.
    "WIRE": ("still genuinely unwired and worth a surface - this is the remaining G72 worklist", [
    ]),
}

# ---------------------------------------------------------------------------------------------
out = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "audit_wiring_census.py")],
                     capture_output=True, text=True, cwd=REPO,
                     encoding="utf-8", errors="replace").stdout or ""
m = re.search(r"NOT reaching a surface: (\d+)(.*?)(?:\ndocs/|\Z)", out, re.S)
if not m:
    print("⛔ could not read the census output - run scripts/audit_wiring_census.py by hand")
    sys.exit(1)
unwired = re.findall(r"^\s{2}(in_[a-z0-9_]+|_[a-z0-9_]+)\s+rows=", m.group(2), re.M)
reached = re.search(r"REACHING A SURFACE: (\d+) of (\d+)", out)

# ⛔ PATTERN RULES, added 2026-08-20c because the name-by-name list was a maintenance trap I
#    built myself. The PJM ladder creates a new rung table every few hours while it harvests, and
#    each one arrived UNCLASSIFIED and failed the checkpoint - three of them within a day
#    (inj_200, wd_200, wd_300). A checklist that a running process invalidates on its own
#    schedule is not a closed list, it is a recurring false alarm, and a check that cries wolf
#    gets ignored. A ladder rung is identifiable by SHAPE, so match the shape.
PATTERNS = [
    (re.compile(r"^in_pjm_qs_c23_(inj|wd)_\d+$"), "harvest_rung"),
    (re.compile(r"^in_nfirs_(basicincident|incidentaddress|fireincident)_\d{4}$"), "raw_feed"),
]

known = {t: k for k, (_, ts) in CLASSIFIED.items() for t in ts}
print("=" * 92)
print(f"UNWIRED CLASSIFICATION — {len(unwired)} objects reach no surface "
      f"({reached.group(1)} of {reached.group(2)} do)")
print("=" * 92)

by_reason, unclassified = {}, []
for t in unwired:
    k = known.get(t)
    if k is None:
        # fall through to the SHAPE rules before declaring an object unaccounted for
        k = next((reason for pat, reason in PATTERNS if pat.match(t)), None)
    if k is None:
        unclassified.append(t)
    else:
        by_reason.setdefault(k, []).append(t)

for k, (why, _) in CLASSIFIED.items():
    got = sorted(by_reason.get(k, []))
    if not got and k != "WIRE":
        continue
    tag = "⛔ WORKLIST" if k == "WIRE" else "accounted for"
    print(f"\n{k.upper():18s} {len(got):>3}  [{tag}]")
    print(f"    {why}")
    for t in got:
        print(f"      · {t}")

# an object classified but NOW WIRED is not an error - it is progress. Report it so the ledger
# can be trimmed rather than growing stale, which is how a list like this rots.
stale = sorted(t for t in known if t not in unwired)
if stale:
    print(f"\nNO LONGER UNWIRED — trim these from the ledger ({len(stale)}):")
    for t in stale:
        print(f"      · {t}   (was: {known[t]})")

print("\n" + "=" * 92)
lines = [
    "# UNWIRED CLASSIFICATION — generated by `scripts/audit_unwired_classification.py`",
    "",
    "> ⛔ **DO NOT HAND-EDIT.** Edit the ledger in the script, then re-run it.",
    "",
    f"**{reached.group(1)} of {reached.group(2)} registered objects reach a surface.** "
    f"The other {len(unwired)} are listed below, each with a reason. An object with no reason "
    "FAILS `audit_unwired_classification.py`, which is what keeps this list closed.",
    "",
]
for k, (why, _) in CLASSIFIED.items():
    got = sorted(by_reason.get(k, []))
    if not got:
        continue
    lines += [f"## {k} — {len(got)}", "", why + ".", ""]
    lines += [f"- `{t}`" for t in got] + [""]
if unclassified:
    lines += ["## ⛔ UNCLASSIFIED — this is a FAILURE", ""] + \
             [f"- `{t}`" for t in unclassified] + [""]
io.open(os.path.join(REPO, "docs", "UNWIRED_CLASSIFICATION.md"), "w",
        encoding="utf-8").write("\n".join(lines))
print("docs/UNWIRED_CLASSIFICATION.md written")

if unclassified:
    print(f"\n⛔ {len(unclassified)} UNCLASSIFIED object(s) — every one is a FAILURE:")
    for t in unclassified:
        print(f"      · {t}")
    print("\n   Add each to CLASSIFIED in this script with a measured reason, or wire it.")
    sys.exit(1)
print(f"\n0 unclassified. {len(by_reason.get('WIRE', []))} object(s) remain on the G72 worklist.")
