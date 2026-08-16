"""What is ACTUALLY left on the seller-intent signals? Measured, not recalled.

WHY. The handoff said D4 was NOT HELD and seasonal, so a whole SRI acquisition was recommended --
while 17,617 delinquent rows sat in in_si_refresh_sri_taxsale_in across 76 counties, 92%
parcel-keyed, with 16,325 upcoming auctions. The note had been hand-typed into a GENERATED
document and never checked. That is almost certainly not the only one.

So this classifies every signal in the taxonomy into what it would actually take to close:

  ADMITTED            reaching parcels today; nothing to do
  HELD_NOT_SPLIT      the rows are in the warehouse under another signal's bucket. A SPLIT, not a
                      scrape. Cheapest work available.
  HELD_WRONG_GRAIN    held, but at owner/county/aggregate grain and structurally unable to reach a
                      parcel without a different acquisition. Not a defect.
  BLOCKED_STRUCTURAL  no lawful free route exists: paywall, procurement, robots/terms. Nothing an
                      agent can do. STOP RECOMMENDING THESE.
  AWAITING_OPERATOR   one human action away (a fax, an email, a licence, a cheque)
  OPEN                genuinely actionable acquisition still outstanding

The point is to stop re-recommending work that is done, impossible, or waiting on a person.
"""
import datetime
import json
import os

from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")


def n(sql):
    try:
        return list(client.query(sql))[0].n
    except Exception as e:
        return f"ERR {str(e)[:40]}"


# signal -> (classification, why, probe or None)
# Every BLOCKED/AWAITING claim names the WALL, because "we cannot" and "nobody looked" must not
# render the same way.
CLAIMS = {
 "A1_market_listing": ("BLOCKED_STRUCTURAL",
    "properties.zoomprospector.com robots.txt: 'User-agent: * / Disallow: /' — Google/Bing only. "
    "The data is state-published and free, but automated collection is refused to everyone else. "
    "Route is an IEDC data request, not a scraper.", None),
 "D10_tax_warrant": ("BLOCKED_STRUCTURAL",
    "INCite $600/yr or Doxpop $38/mo. A procurement decision, not an engineering one.", None),
 "D13_federal_tax_lien": ("AWAITING_OPERATOR",
    "IRS ALS FOIA drafted in docs/FOIA_IRS_ALS_REQUEST.md; needs the operator's fax.", None),
 "D15_mechanics_lien": ("BLOCKED_STRUCTURAL",
    "92 county recorders, every one behind Doxpop / Fidlar Tapestry ($8.75/search) / Laredo "
    "($30-300/month PER COUNTY). Zero open-data presence across four independent indices. "
    "A cheque, not a scraper — confirmed twice, nationally and for Indiana.", None),
 "D18_owner_contact": ("OPEN",
    "mat_parcel_attrs.parcel_owner is NULL on all 3,553,381 Indiana parcels (69M non-null "
    "NATIONALLY — the coverage is other states). Closed by the DLGF Gateway pull.",
    "SELECT COUNTIF(parcel_owner IS NOT NULL AND parcel_owner!='') n FROM "
    "`energy-platfrom.energy.mat_parcel_attrs` WHERE parcel_source='parcels_in'"),
 "D9_absentee": ("OPEN",
    "Same single blocker as D18: no owner mailing address anywhere in the estate. One DLGF pull "
    "unblocks D9, D18, D11, D27 and IDEM together.",
    "SELECT COUNTIF(parcel_owner IS NOT NULL AND parcel_owner!='') n FROM "
    "`energy-platfrom.energy.mat_parcel_attrs` WHERE parcel_source='parcels_in'"),
 "D4_tax_delinquency": ("HELD_NOT_SPLIT",
    "17,617 rows inside in_si_refresh_sri_taxsale_in (saleStatusDescription DELINQUENT 15,860 + "
    "Sale Active 1,757), 76 counties, 92% parcel-keyed, 16,325 auctions still upcoming. Admitted "
    "today under D1_tax_sale. A SPLIT, like the D5 split.",
    f"SELECT COUNT(*) n FROM `{DS}.in_si_refresh_sri_taxsale_in` "
    "WHERE saleStatusDescription IN ('DELINQUENT','Sale Active')"),
 "D11_entity_dissolution": ("HELD_WRONG_GRAIN",
    "983 admitted rows exist and are wired at OWNER grain in in_si_owner_signals. They cannot "
    "reach a parcel: the address bridge matches 6 of 983, and these are business-registry "
    "addresses where a street match often finds a registered agent's office. Needs owner data.",
    f"SELECT COUNT(*) n FROM `{DS}.in_si_d11_admitted`"),
 "D27_ucc_lapse": ("HELD_WRONG_GRAIN",
    "156 admitted rows, wired at OWNER grain. Address bridge matches 0 of 156. Same blocker as D11.",
    f"SELECT COUNT(*) n FROM `{DS}.in_si_d27_admitted`"),
 "D23_surplus_disposal": ("HELD_NOT_SPLIT",
    "Federal and school surplus already clipped; the Indiana-specific increment (IDOA state land "
    "RFBs) is a low-frequency watch-list, not a corpus.",
    f"SELECT (SELECT COUNT(*) FROM `{DS}.in_gov_surplus_frpp`) + "
    f"(SELECT COUNT(*) FROM `{DS}.in_gov_surplus_nces`) n"),
 "D6_bankruptcy": ("HELD_WRONG_GRAIN",
    "393 rows at aggregate/owner grain. A bankruptcy names a debtor, not a parcel.", None),
 "D8_exit_intent": ("HELD_WRONG_GRAIN", "142 rows, aggregate grain, newest event 2008.", None),
 "D25_rail_abandonment": ("HELD_WRONG_GRAIN",
    "215 STB filings at line/aggregate grain; 127 admitted as events. A rail line is not a parcel.",
    f"SELECT COUNT(*) n FROM `{DS}.in_si_d25_admitted`"),
 "D3_seized_auction": ("HELD_WRONG_GRAIN", "2 rows held, aggregate grain.", None),
 "D17_commercial_eviction": ("HELD_WRONG_GRAIN",
    "370 rows; operator sign-off 4 ruled these county-grain CONTEXT only.", None),
 "D5_vacancy": ("HELD_WRONG_GRAIN",
    "947,592 rows — but the operator ruled footprint absence is NOT a signal. Kept as "
    "has_vacancy_signal and as the BESS sizing basis. Deliberately excluded, not missing.", None),
 "D22_environmental_idem": ("OPEN",
    "22,565 IDEM enforcement actions held with NO event date — document_published carries exactly "
    "two values, N and Y, and is the only date-like column. Undated they cannot be recency-filtered "
    "or joined. Dates live on the per-case document pages; recovering them is a re-scrape of a "
    "source that is open and ungated.",
    f"SELECT COUNT(*) n FROM `{DS}.in_si_d22_idem_enforcement`"),
}

print("=" * 100)
print("SIGNAL REALITY AUDIT — what is actually left")
print("=" * 100)

cov = {r.signal: r for r in client.query(
    f"SELECT signal, parcels_admitted, parcels_reached FROM `{DS}.in_si_signal_coverage`")}

buckets, out = {}, []
for sig, (cls, why, probe) in sorted(CLAIMS.items()):
    measured = n(probe.format(DS=DS)) if probe else None
    adm = cov.get(sig).parcels_admitted if sig in cov else 0
    if adm:
        cls = "ADMITTED"
    buckets.setdefault(cls, []).append(sig)
    out.append({"signal": sig, "class": cls, "admitted_parcels": adm,
                "measured_rows_held": measured, "why": why})

for sig, r in sorted(cov.items(), key=lambda x: -(x[1].parcels_admitted or 0)):
    if sig not in CLAIMS and (r.parcels_admitted or 0) > 0:
        buckets.setdefault("ADMITTED", []).append(sig)
        out.append({"signal": sig, "class": "ADMITTED",
                    "admitted_parcels": r.parcels_admitted,
                    "measured_rows_held": None, "why": "reaching parcels today"})

ORDER = ["ADMITTED", "HELD_NOT_SPLIT", "HELD_WRONG_GRAIN", "OPEN",
         "AWAITING_OPERATOR", "BLOCKED_STRUCTURAL"]
for cls in ORDER:
    sigs = sorted(set(buckets.get(cls, [])))
    if not sigs:
        continue
    print(f"\n### {cls}  ({len(sigs)})")
    for s in sigs:
        rec = next(x for x in out if x["signal"] == s)
        held = rec["measured_rows_held"]
        bits = []
        if rec["admitted_parcels"]:
            bits.append(f"{rec['admitted_parcels']:,} parcels admitted")
        if isinstance(held, int):
            bits.append(f"{held:,} rows held")
        print(f"  {s:28s} {' · '.join(bits)}")
        if cls != "ADMITTED":
            print(f"       {rec['why'][:150]}")

actionable = [c for c in ("HELD_NOT_SPLIT", "OPEN") if buckets.get(c)]
print("\n" + "=" * 100)
print("WHAT AN AGENT CAN ACTUALLY DO:")
for c in actionable:
    for s in sorted(set(buckets[c])):
        print(f"  [{c}] {s}")
print("\nNOT actionable by us — stop re-recommending these:")
for c in ("BLOCKED_STRUCTURAL", "AWAITING_OPERATOR", "HELD_WRONG_GRAIN"):
    for s in sorted(set(buckets.get(c, []))):
        print(f"  [{c}] {s}")

path = os.path.join(REPO, "docs", "SIGNAL_REALITY.json")
json.dump({"audited_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "signals": out}, open(path, "w", encoding="utf-8"), indent=1, default=str)
print(f"\nwritten: docs/SIGNAL_REALITY.json")
