"""G152: THE ONE MAP OF THE 19 UPSTREAM SI SOURCES, AT FULL WIDTH.

⛔ THIS FILE IS THE SINGLE COPY. `build_si_upstream_wide.py` builds from it and
`audit_si_upstream_width.py` audits against it. Two copies of one list is the defect this project
keeps paying for — if you add a source, add it HERE and both sides move together.

================================================================================================
WHY THIS EXISTS
================================================================================================
Operator, 2026-08-21: *"we have 31 SI signals, and I guarantee that they live in more than eight
sources, so this should be checked and audited for completeness."* And then, decisively:

  ⭐ *"Even if a source scrapes everything but one column, we still want to rescrape it for
     everything because that one field may contain something materially important (e.g., an event
     time or another SI signal), so it is crucial that we have full visibility over each dataset."*

That ruling REMOVES the judgement call. We do not rank columns and keep the good ones. Every
source is clipped at FULL WIDTH and the ranking governs only the ORDER we look at them in.

⛔ THE MEASURED PROBLEM. `energy.si_signals` is 97,240,585 rows NORMALISED TO 13 COLUMNS
(signal, state, county_fips, parcel_key, address_norm, owner_name, keying, flag, value_num,
observed_date, source_id, ingested_at, quality_mult). Our clip of THAT is complete — 13 of 13 —
which is why the previous column audit passed. It passed on a reduction. The 19 sources behind it
carry 10 to 363 columns each, and everything past those 13 is discarded before it reaches us.

⭐ HOW `pred` IS WRITTEN, AND WHY IT IS NOT GUESSED. Every predicate below names a column that was
read out of INFORMATION_SCHEMA and whose value vocabulary was measured before it was used. Two
existing clips are in this file precisely because that was NOT done for them:

  ⛔ `in_sba_foia_loans` was clipped on `cdc_state` — the state of the CERTIFIED DEVELOPMENT
     COMPANY, i.e. the lender's office, not the property. It holds 5,135 rows where the parent
     carries 39,889 Indiana-PROJECT loans. A 7.8x under-clip on a signal that reaches parcels.
  ⛔ `in_ustp_ch7_tfr` was clipped on `ch7_state_tax_paid` — a DOLLAR column. It holds 33 rows and
     ZERO of them are Indiana, against 76,010 in the parent. `docs/UNWIRED_CLASSIFICATION.md`
     classified it as "no_indiana_content", which recorded the symptom as the cause.

  ⚠ Both were found by comparing the clip's own predicate against the parent's value vocabulary.
    Neither would have been found by counting columns, because both are already FULL WIDTH.

RE-SCRAPE COMMAND: python scripts/build_si_upstream_wide.py
"""

# (key, energy parent, Indiana predicate, indiana_app target, what the widening buys)
# ⚠ `pred` is applied AT THE CLIP. energy.si_d5_vacancy_derived is 22.3M rows / 14.8 GB; filtering
#   afterwards would scan it whole every time.
SOURCES = [
    # ------------------------------------------------------------------ no clip existed at all
    ("edgar_abs_ee_cmbs", "edgar_abs_ee_cmbs", "UPPER(IFNULL(propertystate,''))='IN'",
     "in_si_up_cmbs",
     "153 columns on 19,187 Indiana rows covering 806 distinct commercial properties. Carries "
     "occupancy, DSCR, payment status, servicer workout strategy, largest tenant and its lease "
     "expiry, valuation and net rentable square feet. We admitted 419 rows of it for one signal."),

    ("si_d8_exit_intent", "agis_indy_rezoning", "TRUE",
     "in_si_up_indy_rezoning",
     "⭐ THE CLEAREST PROOF OF THE REDUCTION. si_signals carries 142 Indiana exit-intent rows with "
     "no address, no parcel key and no coordinate. Its actual parent is this layer: 13,414 "
     "Indianapolis rezoning cases, 100% carrying geometry, 8,499 a parcel number, 9,758 a street "
     "and 9,670 a petitioner name."),

    ("si_d17_in_iocs_court_year", "si_d17_in_iocs_court_year", "TRUE",
     "in_si_up_iocs_court",
     "67 columns of per-county, per-year case-type counts (mf = mortgage foreclosure, ev = "
     "eviction, ...). We admitted 370 rows of 1,543. County grain, so context not placement."),

    ("bankruptcy_dockets", "bankruptcy_dockets",
     "REGEXP_CONTAINS(LOWER(IFNULL(court,'')), r'ind')",
     "in_si_up_bankruptcy",
     "89 Indiana dockets with case name, filing and termination dates, nature of suit and the "
     "court's own URL. The URL is a per-record citation for G153."),

    ("si_d3_seized_auction_state", "si_d3_seized_auction_state", "UPPER(IFNULL(state,''))='IN'",
     "in_si_up_seized_auction",
     "17 columns on 2 Indiana rows. ⚠ Clipped for completeness, not for value — 2 rows is a "
     "footnote, and saying so is the point of measuring it."),

    # ------------------------------------------------- clipped, but only through the reduction
    ("warn_notices", "warn_notices", "UPPER(IFNULL(source_state,''))='IN'",
     "in_si_up_warn_multistate",
     "The 363-column multi-state WARN union. ⛔ MEASURED: every address-bearing column is NULL on "
     "all 1,220 Indiana rows — address, location_address, impacted_site_address, site_address, "
     "addressfull, address_line_1, address_1, location. This CONFIRMS the operator: Indiana "
     "publishes no site address in the listing, so the address can only come from the filing PDF, "
     "and most notices have no PDF. Clipped so the negative is auditable rather than remembered."),

    ("si_d5_vacancy_derived", "si_d5_vacancy_derived", "UPPER(IFNULL(state,''))='IN'",
     "in_si_up_vacancy_derived",
     "967,366 Indiana rows against 945,896 admitted. ⛔ Carries parcel_owner, assessed_value, "
     "land_use, zoning and year_built columns that are 100% NULL for Indiana — measured, so the "
     "DLGF purchase stays the route for owner and value and nobody re-checks this table hoping."),

    ("si_d12_indy_marion_code_enforcement", "si_d12_indy_marion_code_enforcement", "TRUE",
     "in_si_up_indy_code",
     "910,483 rows at 18 columns against 747,211 admitted through the reduction."),

    # ⛔ THE ODD ONE OUT, AND IT COST A SILENTLY EMPTY TABLE. Every other parent here spells the
    # state 'IN'; this one spells it 'Indiana' (alongside 'Louisiana', 'Colorado', 'Florida'). The
    # first version of this row said `UPPER(state)='IN'`, matched 0 rows, and the build PASSED its
    # own column assertion because both sides of the check used the same wrong predicate.
    # ⚠ That is the standing rule earning itself again: read the value vocabulary, never guess it.
    #   The guard in build_si_upstream_wide.py now refuses a zero-row clip for exactly this reason.
    ("si_d1_sri_taxsale_listings", "si_d1_sri_taxsale_listings",
     "UPPER(IFNULL(state,'')) IN ('IN','INDIANA')",
     "in_si_up_sri_taxsale",
     "81,975 Indiana rows at 34 columns, carrying ownerName1/ownerName2 and lat/lon."),

    ("appeals_in_ibtr_determinations", "appeals_in_ibtr_determinations", "TRUE",
     "in_si_up_ibtr_appeals",
     "⭐ 10,071 rows, and 100% of them carry stateParcelNumber, locationAddress AND petitionerName "
     "— a direct parcel key and an owner name, on a signal that admits 1,937 parcels today. Also "
     "carries `attachments` and `attachmentDescriptions`, which are per-record documents for "
     "G153."),

    ("brownfield_epa_repowering", "brownfield_epa_repowering", "UPPER(IFNULL(state,''))='IN'",
     "in_si_up_brownfield",
     "⭐ 58 columns on 1,483 Indiana sites, and EPA has already computed the siting answer: "
     "ssdist (distance to substation), ssvoltage, transdist, tlkv, tlstatus, raildist, rddist, "
     "acreage, estpvcap, estwindcap, plus latitude/longitude and geometry_geojson. Our clip is "
     "missing geometry_geojson, which is the location itself."),

    # ------------------------------------- held, but the clip is narrower than the parent by a
    #                                       column that is not provenance
    ("agis_indy_taxsale", "agis_indy_taxsale", "TRUE",
     "in_si_up_indy_taxsale",
     "62,368 Marion tax-sale parcels with the delinquent amounts (deltaxpen, delsatax, minimumbid). "
     "⛔ Our existing clip drops geometry_geojson — the parcel outline, i.e. the location."),

    ("agis_indy_landbank_surplus", "agis_indy_landbank_surplus", "TRUE",
     "in_si_up_indy_landbank",
     "⭐ 595 Indianapolis land-bank surplus parcels with parcelnumber, address, minimumbid, "
     "salestatus and saledate. G133 recorded land banks as 'a NEW acquisition we hold nothing "
     "for'. We hold two: this and in_si_evansville_landbank (1,660)."),
]

# ⛔ TABLES THAT ARE ALREADY FULL WIDTH BUT WERE CLIPPED ON THE WRONG COLUMN. These are REPAIRED IN
# PLACE rather than given a second table — a second copy of one clip is how the figures drift.
REPAIRS = [
    ("in_sba_foia_loans", "sba_foia_loans",
     "UPPER(IFNULL(projectstate,''))='IN' OR UPPER(IFNULL(borrstate,''))='IN'",
     "was clipped on cdc_state (the lender's office) — 5,135 rows against 39,889 Indiana-project "
     "loans in the parent"),
    ("in_ustp_ch7_tfr", "ustp_ch7_tfr", "UPPER(IFNULL(state,''))='IN'",
     "was clipped on ch7_state_tax_paid, a DOLLAR column — 33 rows, none of them Indiana, against "
     "76,010 in the parent"),
]

# ⛔ NOT A WIDTH GAP — A ROW GAP, AND IT WAS SILENT. The NFIRS fire-incident detail table (83
# columns: cause of ignition, area of origin, structure status, property loss) is the depth behind
# D16_structure_fire. Measured 2026-08-21, Indiana rows available vs held:
#     2020  9,652 / 9,652 ok      2021  9,798 / 9,798 ok
#     2022 10,548 / 1,221  SHORT  2023 13,006 / ABSENT  2024 11,961 / 1,255 SHORT
# ⚠ 1,221 and 1,255 are not a filter, they are two loads that STOPPED. 33,039 Indiana fire records
#   missing, on a signal that admits 1,680 parcels. `basicincident` and `incidentaddress` are
#   complete for all five years, which is why nothing downstream ever failed.
YEAR_GAPS = [
    ("in_nfirs_fireincident_2022", "nfirs_fireincident_2022", "UPPER(IFNULL(STATE,''))='IN'",
     "held 1,221 of 10,548 Indiana rows - a load that stopped, not a filter"),
    ("in_nfirs_fireincident_2023", "nfirs_fireincident_2023", "UPPER(IFNULL(STATE,''))='IN'",
     "not clipped at all; 13,006 Indiana rows available"),
    ("in_nfirs_fireincident_2024", "nfirs_fireincident_2024", "UPPER(IFNULL(STATE,''))='IN'",
     "held 1,255 of 11,961 Indiana rows - a load that stopped, not a filter"),
]


def all_targets():
    """Every indiana_app object this workstream writes from the map above."""
    return ([t for _, _, _, t, _ in SOURCES]
            + [t for t, _, _, _ in REPAIRS]
            + [t for t, _, _, _ in YEAR_GAPS])
