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
 "D4_tax_delinquency": ("pre-sale delinquency lists", "NOT HELD — SRI robots permits it; seasonal, schedule Jul–Oct"),
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
     f"| **the flag before this build** | {old['n']:,}, of which {old['land']:,} "
     f"({100*old['land']/max(old['n'],1):.1f}%) was empty land |", "",
     "The old flag was a vacancy flag: its only parcel-keyed input was footprint absence.", "",
     "## Per signal", "",
     "| signal | what it is | held | reached | admitted | C/I | event range | excluded: resid / low-sev |",
     "|---|---|---:|---:|---:|---:|---|---|"]

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
    o.append(f"| `{sig}` | {label} | {held if held is not None else '—'} | {reached:,} | "
             f"**{adm:,}** | {ci:,} | {rng} | {excl} |")

o += ["", "## How each signal reaches a parcel — the bridges, and what each yields", "",
      "Three key namespaces had to be reconciled; a naive join across them reads zero.", "",
      "| bridge | admitted rows | admitted parcels |", "|---|---:|---:|"]
for b in bridges:
    o.append(f"| {str(b['b'])[:88]} | {b['n']:,} | {b['p']:,} |")

o += ["", "## What is NOT held at all", "",
      "Listed so an absent signal is never mistaken for a covered one.", "",
      "| signal | state |", "|---|---|"]
for sig, (what, note) in sorted(TAX.items()):
    if sig not in cov and note:
        o.append(f"| `{sig}` | {note} |")

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
