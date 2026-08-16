"""Generate docs/SI_COVERAGE.md — per-signal seller-intent coverage for Indiana.

GENERATED. Regenerate it rather than editing by hand, so it cannot drift from the tables.

It answers one question the operator asked directly: *what is our current coverage on each of the
SI signals?* Coverage is FOUR different numbers and conflating them is how the D5 mistake happened
in the first place, so all four are shown per signal:

  held        rows in the corpus / publisher table — says nothing about whether we can use them
  reached     parcels the signal can actually be joined to
  admitted    parcels that pass BOTH operator rulings (non-residential, and severity)
  dated       whether an event date exists, because a 1990s violation is not a lead

The signal taxonomy (D1..D27, A1, A2) is listed IN FULL, including the ones we hold nothing for —
an absent signal that is simply missing from a report reads as coverage.
"""
import datetime
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")


def rows(sql):
    return [dict(r) for r in client.query(sql)]


# The full taxonomy. `note` is the acquisition state for anything we cannot reach a parcel with.
TAX = {
 "D1_tax_sale": ("county tax sales (SRI statewide + Evansville)", ""),
 "D2_foreclosure": ("mortgage foreclosures", ""),
 "D3_seized_auction": ("seized-asset auctions", "2 rows held, aggregate grain only"),
 "D4_tax_delinquency": ("pre-sale delinquency lists",
    "HELD but NOT SPLIT OUT — 17,617 rows (saleStatusDescription DELINQUENT 15,860 + Sale Active "
    "1,757) sit inside in_si_refresh_sri_taxsale_in across 76 counties, 92% parcel-keyed and "
    "dated with 16,325 UPCOMING auctions. Currently admitted under D1_tax_sale. Needs a SPLIT, "
    "not a scrape — see the note in DELINQUENT_STATUSES below"),
 "D5_abandoned_building": ("abandoned/vacant STRUCTURE registries", ""),
 "D5_unsafe_building": ("Indy 'Unsafe Buildings' cases", "derived from the held code corpus"),
 "D5_vacant_board_order": ("Indy 'Vacant Board Order' cases", "derived from the held code corpus"),
 "D5_vacancy": ("footprint absence", "NOT A SIGNAL — operator ruling; kept as has_vacancy_signal and the BESS sizing basis"),
 "D6_bankruptcy": ("business bankruptcies", "held at aggregate/owner grain — cannot reach a parcel"),
 "D7_brownfield": ("brownfield sites", ""),
 "D8_exit_intent": ("stated exit intent", "aggregate grain only"),
 "D9_absentee": ("absentee/out-of-state owners", "NOT HELD — blocked on the DLGF Gateway owner pull (one acquisition, three unblocks)"),
 "D10_tax_warrant": ("state tax warrants", "BLOCKED — $600/yr INCite or $38/mo Doxpop; procurement decision"),
 "D11_entity_dissolution": ("dissolved/revoked entities", "983 admitted rows STAGED, not yet folded in"),
 "D12_code_violation": ("municipal code enforcement", ""),
 "D13_federal_tax_lien": ("IRS liens", "FOIA drafted and awaiting the operator's fax"),
 "D14_sba_chargeoff": ("SBA loan charge-offs", ""),
 "D15_mechanics_lien": ("mechanics liens", "BLOCKED — 92 recorders, all paywalled. A cheque, not a scraper"),
 "D16_structure_fire": ("NFIRS structure fires", "severity-gated upstream: 76,779 raw -> 469 SI-grade"),
 "D17_commercial_eviction": ("commercial evictions", "county-grain context only (operator sign-off 4)"),
 "D18_owner_contact": ("owner contact/approach data", "NOT HELD — mat_parcel_attrs is 100% NULL upstream"),
 "D19_warn": ("WARN layoff notices", "owner-name keyed; almost nothing reaches a parcel"),
 "D20_loan_maturity": ("CMBS loan maturity", ""),
 "D21_demolition_order": ("demolition orders and permits", ""),
 "D22_environmental_violation": ("EPA ECHO compliance violations", ""),
 "D22_facility_inactive": ("EPA ECHO ceased-operation facilities", "a shut plant with power and water is an opportunity, not a liability"),
 "D23_surplus_disposal": ("government surplus disposal", "low value — watch-list (IDOA RFBs)"),
 "D24_plant_delisting": ("FSIS plant delistings", ""),
 "D25_rail_abandonment": ("STB rail abandonments", "aggregate grain only"),
 "D26_assessment_appeal": ("IBTR assessment appeals", ""),
 "D27_ucc_lapse": ("UCC filing lapses", "156 admitted rows STAGED, not yet folded in"),
 "A1_market_listing": ("commercial listings", "BLOCKED — zoomprospector robots.txt disallows all; route is an IEDC data request"),
 "A2_gov_surplus": ("government surplus property", ""),
}

cov = {r["signal"]: r for r in rows(f"SELECT * FROM `{DS}.in_si_signal_coverage`")}

# COUNTY SPREAD. The denominator is MEASURED, never assumed — Indiana has 92 counties, and a
# 93rd is exactly how the FEMA roll-up broke (fipsCountyCode='000' is 'Statewide'). A signal
# concentrated in one or two counties is a PUBLISHING footprint, not statewide coverage, and
# ranking on it would select for wherever the data happens to come from (§2.21).
N_COUNTIES = rows(f"SELECT COUNT(DISTINCT county_fips) n FROM `{DS}.in_sites_county`")[0]["n"]
spread = {r["signal"]: r for r in rows(f"""
WITH pc AS (
  SELECT v.signal, v.parcel_key, v.si_admitted, sc.county_fips
  FROM `{DS}.in_si_parcel_signals_v2` v
  JOIN `{DS}.in_sites_county` sc USING (parcel_source, parcel_key))
SELECT signal,
  COUNT(DISTINCT IF(si_admitted, county_fips, NULL)) counties_admitted,
  COUNT(DISTINCT county_fips) counties_reached
FROM pc GROUP BY 1""")}
flag_spread = rows(f"""
SELECT COUNT(DISTINCT IF(f.has_si_signal, sc.county_fips, NULL)) co
FROM `{DS}.in_si_sites_flags_v2` f JOIN `{DS}.in_sites_county` sc
  USING (parcel_source, parcel_key)""")[0]["co"]
flags = rows(f"""SELECT COUNTIF(has_si_signal) flagged,
  COUNTIF(has_si_signal AND si_last_event_date IS NOT NULL) dated,
  COUNTIF(has_si_signal AND si_events_3y>0) r3,
  COUNTIF(has_si_signal AND si_events_5y>0) r5,
  COUNTIF(has_si_signal AND occ_group='ci') ci,
  COUNTIF(has_si_signal AND occ_group='other_nonres') other,
  COUNTIF(has_si_signal AND occ_group='agriculture') ag,
  COUNTIF(has_si_signal AND occ_group='no_structure') land
FROM `{DS}.in_si_sites_flags_v2`""")[0]
old = rows(f"""SELECT COUNTIF(has_si_signal) n,
  COUNTIF(has_si_signal AND occ_group='no_structure') land FROM `{DS}.in_sites`""")[0]
bridges = rows(f"""SELECT bridge_methods b, COUNT(*) n, COUNT(DISTINCT parcel_key) p
  FROM `{DS}.in_si_parcel_signals_v2` WHERE si_admitted GROUP BY 1 ORDER BY p DESC""")

o = [f"# SI COVERAGE — per-signal, generated {datetime.date.today()}", "",
     "**GENERATED by `scripts/build_si_coverage_doc.py`** — regenerate rather than hand-edit.", "",
     "Coverage is four different numbers, and conflating them is exactly how the D5 mistake",
     "happened. All four are shown per signal:", "",
     "| | |", "|---|---|",
     "| **held** | rows in the corpus or publisher table — says nothing about usability |",
     "| **reached** | parcels the signal can actually be joined to |",
     "| **admitted** | parcels passing BOTH rulings: non-residential, and severity |",
     "| **dated** | whether an event date exists — a 1990s violation is not a lead |", "",
     "## The flag itself", "",
     f"| | |", "|---|---:|",
     f"| parcels flagged (v2) | **{flags['flagged']:,}** |",
     f"| …carrying an event date | {flags['dated']:,} ({100*flags['dated']/max(flags['flagged'],1):.0f}%) |",
     f"| …with an event inside 3 years | {flags['r3']:,} |",
     f"| …with an event inside 5 years | {flags['r5']:,} |",
     f"| C/I · other non-res · agriculture · vacant land | {flags['ci']:,} · {flags['other']:,} · "
     f"{flags['ag']:,} · {flags['land']:,} |",
     f"| **counties with ≥1 flagged parcel** | **{flag_spread} of {N_COUNTIES}** |",
     f"| **the flag before this build** | {old['n']:,}, of which {old['land']:,} "
     f"({100*old['land']/max(old['n'],1):.1f}%) was empty land |", "",
     "The old flag was a vacancy flag: its only parcel-keyed input was footprint absence.", "",
     f"**Indiana has {N_COUNTIES} counties, and that denominator is measured here rather than",
     "assumed** — a 93rd county is exactly how the FEMA roll-up broke (`fipsCountyCode='000'` is",
     "'Statewide', not a county). **County spread is the single most important column below.** A",
     "signal present in 1–2 counties is a PUBLISHING footprint, not statewide coverage; ranking",
     "sites on it would select for wherever the data happens to come from rather than for the",
     "best site (§2.21: a ranked list dominated by one subgroup means the ranking selects for the",
     "error).", "",
     "## Per signal", "",
     "| signal | what it is | held | reached | admitted | counties (adm/reach) | C/I | event range | excluded: resid / low-sev |",
     "|---|---|---:|---:|---:|:---:|---:|---|---|"]

for sig in sorted(TAX, key=lambda s: (-(cov.get(s, {}).get("parcels_admitted") or 0), s)):
    what, note = TAX[sig]
    c = cov.get(sig, {})
    held = c.get("corpus_rows")
    reached = c.get("parcels_reached") or 0
    adm = c.get("parcels_admitted") or 0
    ci = c.get("parcels_ci") or 0
    fe, le = c.get("first_event"), c.get("last_event")
    rng = f"{fe} → {le}" if fe or le else ("—" if adm == 0 else "no dates held")
    excl = f"{c.get('excl_residential') or 0:,} / {c.get('excl_low_severity') or 0:,}" if c else "—"
    label = what + (f" — *{note}*" if note else "")
    sp = spread.get(sig, {})
    ca, cr = sp.get("counties_admitted") or 0, sp.get("counties_reached") or 0
    # flag the metro-footprint signals explicitly rather than letting a small number pass quietly
    co = f"**{ca}**/{cr}" if ca > 8 else (f"⚠ **{ca}**/{cr}" if adm > 0 else "—")
    o.append(f"| `{sig}` | {label} | {held if held is not None else '—'} | {reached:,} | "
             f"**{adm:,}** | {co} | {ci:,} | {rng} | {excl} |")

o += ["", "## How each signal reaches a parcel — the bridges, and what each yields", "",
      "Three key namespaces had to be reconciled; a naive join across them reads zero.", "",
      "| bridge | admitted rows | admitted parcels |", "|---|---:|---:|"]
for b in bridges:
    o.append(f"| {str(b['b'])[:88]} | {b['n']:,} | {b['p']:,} |")

# ---- PROVE the "NOT HELD" claims before printing them ---------------------------------------
# This document is GENERATED, but its acquisition notes were hand-typed and never checked. That
# combination is worse than a hand-written doc, because it LOOKS measured. It shipped
# "D4_tax_delinquency — NOT HELD — seasonal, schedule Jul–Oct" while 17,617 delinquent rows sat in
# in_si_refresh_sri_taxsale_in across 76 counties, 92% parcel-keyed, with 16,325 upcoming auctions.
# A whole acquisition was recommended for data already in the warehouse.
#
# So every NOT-HELD claim now carries a PROBE. A claim with no probe is printed as UNVERIFIED
# rather than as fact — "we checked and it is absent" and "nobody ever looked" are different
# statements and must not render identically.
NOT_HELD_PROBES = {
    "D4_tax_delinquency": (
        "SELECT COUNT(*) n FROM `{DS}.in_si_refresh_sri_taxsale_in` "
        "WHERE saleStatusDescription IN ('DELINQUENT','Sale Active')"),
    "D9_absentee": (
        "SELECT COUNTIF(parcel_owner IS NOT NULL AND parcel_owner != '') n "
        "FROM `energy-platfrom.energy.mat_parcel_attrs` WHERE parcel_source = 'parcels_in'"),
    "D18_owner_contact": (
        "SELECT COUNTIF(parcel_owner IS NOT NULL AND parcel_owner != '') n "
        "FROM `energy-platfrom.energy.mat_parcel_attrs` WHERE parcel_source = 'parcels_in'"),
}

o += ["", "## What is NOT held at all", "",
      "Listed so an absent signal is never mistaken for a covered one. **Each NOT-HELD claim now "
      "carries a probe measured at build time** — this table once asserted D4 was absent while "
      "17,617 delinquent rows sat in the warehouse.", "",
      "| signal | state | probe |", "|---|---|---|"]
for sig, (what, note) in sorted(TAX.items()):
    if sig not in cov and note:
        probe = NOT_HELD_PROBES.get(sig)
        if probe:
            found = list(client.query(probe.format(DS=DS)))[0].n
            verdict = (f"measured **{found:,} rows** — the NOT-HELD claim is FALSE, fix it"
                       if found else "probed at build time: **0 rows**, genuinely absent")
            if found and "NOT HELD" in note.upper():
                print(f"  !! {sig}: note says NOT HELD but the probe found {found:,} rows")
        else:
            verdict = "⚠ **UNVERIFIED** — no probe defined; this is an assertion, not a measurement"
        o.append(f"| `{sig}` | {note} | {verdict} |")

o += ["", "## ⚠ The signals that are a metro footprint, not statewide coverage", "",
      "Marked ⚠ above. These reach so few counties that a statewide search should not weight them",
      "as if they were evenly available — their absence elsewhere is OUR coverage gap, not the",
      "absence of distress.", "",
      "| signal | counties | why |", "|---|---|---|"]
WHY = {
 "D12_code_violation": "South Bend only. Indy's 747,122-row corpus matches ZERO — its addresses "
                       "carry no city suffix, a loader defect. Geocoding Indianapolis is the fix",
 "D21_demolition_order": "Vanderburgh + St. Joseph — the only two jurisdictions publishing "
                         "demolition data as data",
 "D5_abandoned_building": "Indy + South Bend only, and Indy defers to address (125 of 7,120) "
                          "because Marion publishes no state parcel key",
 "D5_unsafe_building": "derived from the Indy corpus, so limited by the same address bridge",
 "D5_vacant_board_order": "derived from the Indy corpus, so limited by the same address bridge",
 "D19_warn": "owner-name keyed — a company HQ address is not its site",
 "A2_gov_surplus": "tiny source (20 rows held)",
 "D24_plant_delisting": "tiny source (13 rows held)",
}
for sig in sorted(TAX, key=lambda s: -(cov.get(s, {}).get("parcels_admitted") or 0)):
    adm = cov.get(sig, {}).get("parcels_admitted") or 0
    sp = spread.get(sig, {})
    ca = sp.get("counties_admitted") or 0
    if adm > 0 and ca <= 8:
        o.append(f"| `{sig}` | **{ca} of {N_COUNTIES}** | {WHY.get(sig, 'limited publisher footprint')} |")

o += ["", "## The two rulings encoded in `admitted`", "",
      "1. **Non-residential only.** A ~300 MW datacentre and a ~5 MW BESS both need land a house",
      "   does not have, so a residential parcel is not a candidate however distressed it is.",
      "   Residential rows are still built and kept with `admit_status='excluded_residential'`.",
      "2. **Severity.** Only distress that would plausibly move an owner to sell counts. South Bend",
      "   code enforcement is 95% litter, weeds and vegetation; Evansville demolition permits are",
      "   90% residential teardowns; being present in EPA ECHO is not distress at all. Each is",
      "   gated, and each exclusion is counted rather than silently dropped.", "",
      "Neither ruling deletes data. Both are one column, so both are auditable and reversible.", ""]

path = f"{REPO}\\docs\\SI_COVERAGE.md"
open(path, "w", encoding="utf-8").write("\n".join(o) + "\n")
print(f"docs/SI_COVERAGE.md — {len(TAX)} signals in the taxonomy, "
      f"{sum(1 for s in TAX if (cov.get(s, {}).get('parcels_admitted') or 0) > 0)} reaching a parcel, "
      f"{flags['flagged']:,} parcels flagged")
