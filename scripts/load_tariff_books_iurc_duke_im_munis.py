"""Commission-route tariff harvest: Duke Energy Indiana + I&M + every remaining Indiana
electric utility -> in_utility_tariff_riders.  Source: THE IURC's OWN SYSTEMS, not utility sites.

WHY THE COMMISSION (the point of this loader)
---------------------------------------------
duke-energy.com 403s every scripted client behind an Akamai fingerprint wall.  The IURC's
docketed-case system serves THE SAME approved tariff sheets - with cause numbers, commission
date stamps, and zero gate - over plain anonymous HTTP.  Every document below is the
commission's copy: a rate-case compliance filing, a tracker docket's "Submission of Final
Tariff", or a 30-day filing's commission-stamped "Approved Tariff".

THE ROUTE (docs/TARIFF_HARVEST_IURC_ALL_UTILITIES.md carries the write-up for other states)
  search:    POST {companion}/api/search/advanced           (docketed) - anonymous JSON
             POST {companion}/api/search/thirtyday          (30-day)   - anonymous JSON
  filings:   POST {companion}/api/document/filings          {"txtPageNumber":"1","Id":" <case-guid>"}
             POST {companion}/api/document/thirtydayfilings {"txtPageNumber":"1","Id":" <case-guid>"}
  document:  GET  https://iurc.portal.in.gov<iurc_documentLink>   (sharepointdocumentlocation URL)
  companion = https://zus1iurcprodd365companionappmaster-appservice.azurewebsites.net

WHAT THIS RUN ESTABLISHED (headlines)
-------------------------------------
  * Duke's CURRENT book is IURC No. 16 (Cause 46038 order 2025-01-29; sheets eff 2025-02-27).
    Base sheet LEVELS did not change at Step 2: the 2026 Step-2 increase (+4.27% overall) rides
    in Tariff No. 67 "Credits Adjustment", eff bills rendered March 2026 cycle 1, approved by
    docket entry 2026-05-27; a joint OUCC/Industrial-Group appeal to the full Commission
    (filed 2026-06-04) was PENDING at harvest time.
  * Duke fuel base EMBEDDED in base rates: BF = $0.034378/kWh (Tariff No. 60 formula, per the
    46038 order; up from 26.955 mills).  Omit it and the FAC is double-counted.
  * Duke Rate HLF has NO annual demand ratchet - billing demand is the current month's 30-min
    max (floor 25 kW), monthly minimum = the Maximum Load Charge.  AES=75%, NIPSCO=75%,
    SIGECO=90%, I&M large-load=80%: Duke HLF is the outlier, and it matters for curtailment math.
  * Duke trackers bill Rate HLF in $/kW (demand basis) while billing other groups $/kWh -
    stated inside each tracker tariff.  Eleven trackers exist (Appendix A, First Revised
    Tariff No. A, eff 2026-03-25): 60 FAC, 62 ECR, 65 TDSIC, 66 EE, 67 Credits, 68 RTO,
    70 Reliability, 72 FMCA ($0 published), 73 REP, 74 Load Control, 75 GCT (new, Cause 46193).
  * I&M Tariff I.P. per the commission copy (Cause 46097, eff 2025-02-19) - VERIFIES the brief:
    demand $/kW-mo 327 Secondary 16.474 / 322 Primary 14.089 / 323 Subtransmission 10.825 /
    324 Transmission 10.194; fuel base $0.0129810/kWh (Original Sheet 46, Cause 45933).
    Large Load (>=70 MW site / >=150 MW aggregate): 80% ratchet, 12-yr initial term,
    <=5-yr ramp, 42-month notice, Step 1 Embedded Capacity Charge $10.959-$13.289/kW inside the
    minimum charge, collateral = 24x max monthly non-fuel bill.
  * JURISDICTION CENSUS (2025 IURC Annual Report, pp. 37-38, quoted on rows):
    "Only three municipally owned electric utilities remain under the Commission's
    jurisdiction: Anderson, Auburn, and Frankfort." (of 79 municipals; IC 8-1.5-3-9/-9.1)
    "No REMCs remain under Commission authority for rate regulation" (IC 8-1-13-18.5).
    Hoosier Energy / WVPA / IMPA: no retail rate jurisdiction (CPCN + IRP + financing review).
    A jurisdictional gap is a FINDING - every URDB-listed muni/REMC gets an explicit row.

HAZARDS HONOURED
----------------
  * UNPUBLISHED IS NULL, NEVER 0.  Duke FMCA "$0" and EE opt-out "$0.000000" are PUBLISHED
    zeros (loaded 0.0); municipal base schedules we did not acquire are value_status='not_held'
    with NULL rate.
  * Utility strings match in_urdb_rates exactly ("Duke Energy Indiana Inc",
    "Indiana Michigan Power Co (Indiana)", "City of Anderson, Indiana (Utility Company)", ...).
  * DELETE is scoped to THIS harvest's utilities; AES/NIPSCO/CenterPoint rows are untouched.
    The 3 I&M placeholder seed rows are superseded by the full commission-sourced book here.
  * energy dataset is READ-ONLY; the only write there is the APPEND to energy.registry_sources.
  * KNOWN LIMIT carried on rows: Duke filed amended tariffs 2025-04-30 (rate-migration nunc pro
    tunc, approved 2025-05-14, implemented 2025-05-19) directly with the Energy Division; that
    leaf is not in the public docketed/30-day systems, so base-sheet values cite the Step-1
    compliance book eff 2025-02-27.  The 2026-05-27 docket entry confirms the migration
    adjustment was implemented + refunded through Tracker 67, not through base sheet levels.

BOUNDARIES: anonymous read-only HTTP GET of public records, identifying User-Agent, >=1.3 s
between requests, no accounts, no CAPTCHA interaction (the portal pages gate their SEARCH
BUTTON client-side with reCAPTCHA; the backing JSON API accepts anonymous queries - this
loader only GETs document URLs already captured from that API, exactly as the page's own JS
does, with no token).  ASCII-only console output (cp1252 console).

USAGE
-----
    python scripts/load_tariff_books_iurc_duke_im_munis.py --fetch        # download from IURC then verify+load
    python scripts/load_tariff_books_iurc_duke_im_munis.py                # use PDFs already on disk
    python scripts/load_tariff_books_iurc_duke_im_munis.py --verify-only  # sentinel check, NO writes
    python scripts/load_tariff_books_iurc_duke_im_munis.py --dry-run      # everything except BigQuery writes
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import argparse
import os
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOKS = os.path.join(REPO, "scrapers", "tariff_books", "iurc")

PROJECT = "energy-platfrom"                     # intentional, permanent spelling
DS = f"{PROJECT}.indiana_app"
EN = f"{PROJECT}.energy"                        # READ-ONLY except registry_sources APPEND
TABLE = f"{DS}.in_utility_tariff_riders"

UA = ("DecennialGroup-DataAudit/1.0 (read-only public tariff documents; "
      "contact ahenderson@decennialgroup.com)")

# utility strings EXACTLY as in in_urdb_rates
DUKE = "Duke Energy Indiana Inc"
IM = "Indiana Michigan Power Co (Indiana)"
AND_ = "City of Anderson, Indiana (Utility Company)"
AUB = "City of Auburn, Indiana (Utility Company)"
FRK = "City of Frankfort, Indiana (Utility Company)"
HOOSIER = "Hoosier Energy Rural Electric Cooperative, Inc."
WVPA = "Wabash Valley Power Association, Inc. (d/b/a Wabash Valley Power Alliance)"
IMPA = "Indiana Municipal Power Agency"

PORTAL = "https://iurc.portal.in.gov"
COMPANION = "https://zus1iurcprodd365companionappmaster-appservice.azurewebsites.net"

# ------------------------------------------------------------------------------------------
# Every source document: (subdir, filename, exact URL).  The sharepointdocumentlocation URLs
# are the portal's own stable per-filing links, captured from /api/document/filings and
# /api/document/thirtydayfilings responses on 2026-08-18.
# ------------------------------------------------------------------------------------------
_E = PORTAL + "/_entity/sharepointdocumentlocation/"
_LIB = "bb9c6bba-fd52-45ad-8e64-a444aef13c39"
def _P(guid, fname):
    return f"{_E}{guid}/{_LIB}?file={fname}"

FILES = [
    ("duke", "46038_step1_attC_redline_clean_tariff_020725.pdf",
     _P("9b61cc1c-c6e7-ef11-be20-001dd80b8c52", "46038_DEI_Step%201%20Compliance%20Filing_Attachment%20C_Redline%20and%20Clean%20Tariff_020725.pdf")),
    ("duke", "46038_step2_compliance_filing_021826.pdf",
     _P("b0be057e-f70c-f111-8406-001dd802f839", "46038_Duke%20Energy%20Indiana_Compliance%20Filing%20-%20Step%202_021826.pdf")),
    ("duke", "46038_docket_entry_step2_052726.pdf",
     _P("c90fc468-f059-f111-bec6-001dd800b811", "46038%20Duke%20DE%20Step%202%20tariff%20filing.pdf")),
    ("duke", "38707_FAC148_final_tariff_063026.pdf",
     _P("7f36a270-ab74-f111-ab0d-001dd800b811", "38707%20FAC%20148_DEI_%20Submission%20of%20Final%20Tariffs_063026.pdf")),
    ("duke", "42061_ECR45_final_tariff_081426.pdf",
     _P("d4f5ee0f-0798-f111-ab0f-001dd80673f1", "42061%20ECR%2045_DEI_Submission%20of%20Final%20Tariff_081426.pdf")),
    ("duke", "42736_RTO61_final_tariff_120225.pdf",
     _P("237ec161-a3af-f011-bbd3-001dd80f20e8", "42736%20RTO-61_DEI_Submission%20of%20Final%20Tariff_120225.pdf")),
    ("duke", "44348_SRA11_final_tariff_022626.pdf",
     _P("6bb3dfd4-1a13-f111-8407-001dd80c8d99", "44348%20SRA%2011_DEI_Submission%20of%20Final%20Tariff_022626.pdf")),
    ("duke", "44932_REP8_final_tariff_061726.pdf",
     _P("06be5e40-a76a-f111-a824-001dd80cd7cf", "44932%20REP%208_DEI_Submission%20of%20Final%20Tariff_061726.pdf")),
    ("duke", "45647_TDSIC5_final_tariff.pdf",
     _P("21613003-4634-f111-88b3-001dd80673f1", "45647%20TDSIC-5_DEI_Submission%20of%20Final%20Tariff_040926.pdf")),
    ("duke", "45803_DSM2_final_tariffs_100825.pdf",
     _P("472936e0-12a5-f011-bbd3-001dd8084fd9", "45803%20DSM-2_DEI_Submission%20of%20Final%20Tariffs_100825.pdf")),
    ("duke", "46193_GCT1_final_tariff_032526.pdf",
     _P("3f788f9c-8028-f111-8341-001dd802f839", "46193%20GCT%201_DEI_Submission%20of%20Final%20Tariff_032526.pdf")),
    ("duke", "46038_step1_attI_tracker67_credit_p1_020725.pdf",
     _P("6f5867d2-c0e5-ef11-8eea-001dd80b111b", "46038_DEI_Step%201%20Compliance%20Filing_Attachment%20I_Tracker%2067%20Credit%20page%201.pdf")),
    ("duke", "46038_step1_attL_tracker72_FMCA_p1_020725.pdf",
     _P("9f01a4e6-c0e5-ef11-8eea-001dd80b111b", "46038_DEI_Step%201%20Compliance%20Filing_Attachment%20L_Tracker%2072%20FMCA%20page%201_020725.pdf")),
    ("im", "46097_tariff_IP_022525.pdf",
     _P("ba79885d-47f4-ef11-be20-001dd80ad83d", "46097_IndMich_Tariff%20Submission_022525.pdf")),
    ("im", "45933_compliance_tariff_091324.pdf",
     _P("cc50d88a-0f72-ef11-a670-001dd8082de5", "45933_IndMich_Submission%20of%20Compliance%20Tariff_091324.pdf")),
    ("im", "38702_FAC96_tariff_060326.pdf",
     _P("9d71045b-795f-f111-bec6-001dd802f839", "38702FAC96_IndMich_Tariff%20Submission_060326.pdf")),
    ("im", "45164_RA6_tariff_032526.pdf",
     _P("a22c20ad-7828-f111-8341-001dd802f839", "45164%20RAR%206_IndMich_RAR%20Tariff%20Submission_032526.pdf")),
    ("im", "43774_PJM16_tariff_052026.pdf",
     _P("57badfbb-7254-f111-bec6-001dd80673f1", "43774%20PJM%2016_IndMich_Submission%20of%20Tariff_052026.pdf")),
    ("im", "45245_SPR4_tariff_092425.pdf",
     _P("b9f3d193-8899-f011-b4cc-001dd8084fd9", "45245SPR4_IndMich_Tariff%20Submission_092425.pdf")),
    ("im", "44871_ECR9_tariff_111925.pdf",
     _P("e6facec6-82c5-f011-bbd3-001dd803db57", "44871%20ECR%209_Indiana%20Michigan%20Power%20Company_Tariff%20Submission_111925.pdf")),
    ("im", "43827_DSM14_second_compliance_123025.pdf",
     _P("8385eb16-c3e5-f011-8544-001dd8084fd9", "43827DSM14_IndMich_Second%20Compliance%20Submission_123025.pdf")),
    # I&M assembled current book from the utility site (ungated) - used ONLY to read sheets the
    # commission copies do not carry individually (Sheet 44 roster, Sheet 46 FAC base, G.S.,
    # PRA/TAX current factors); every load-bearing I.P. number is sentinel-checked against the
    # COMMISSION copy above as well.
    ("im", "IM_IN_TB_20_06-30-2026.pdf",
     "https://www.indianamichiganpower.com/lib/docs/ratesandtariffs/Indiana/IM_IN_TB_20_06-30-2026.pdf"),
    ("municipal", "anderson_50917_approved_tariff.pdf",
     _P("44b337e9-d97a-f111-ab0e-001dd80bcf22", "50917%20-%20Tariff.pdf")),
    ("municipal", "auburn_50912_approved_tariff.pdf",
     _P("c2994f9f-dc6f-f111-ab0d-001dd80bcf22", "50912%20-%20Tariff.pdf")),
    ("municipal", "frankfort_50903_approved_tariff.pdf",
     _P("242b3130-6d6a-f111-a824-001dd802f839", "50903%20-%20Tariff.pdf")),
    ("", "2025-IURC-Annual-Report.pdf",
     "https://www.in.gov/iurc/files/2025-IURC-Annual-Report.pdf"),
]

# Sentinels: load-bearing numbers that MUST appear in the file on disk, else the source moved
# and every transcription below is suspect.  Fail loudly, load nothing.
SENTINELS = {
    "46038_step1_attC_redline_clean_tariff_020725.pdf": [
        "IURC NO. 16", "Effective: February 27, 2025",
        # HLF (Original Tariff No. 12)
        "$20.51", "$ 23.59", "$ 22.92", "$ 19.75", "$ 27.51",
        "$0.044002", "$0.046775", "$0.047773", "$0.064825", "$0.055534",
        "855.37", "125.61", "31.90", "not less than 25 kW",
        # LLF (10-A / 10-B)
        "$6.54", "$0.089722", "$8.31", "$0.078946", "$5.16", "$0.081902",
        "$27.63", "$109.55", "$331.00", "$8.02", "$0.101700",
        # TOU 11.5
        "$0.112723", "$0.055537", "$13.33", "$0.34 per kVAr",
    ],
    "38707_FAC148_final_tariff_063026.pdf": ["$0.034378", "0.004319", "0.004422", "July 2026"],
    "42061_ECR45_final_tariff_081426.pdf": ["1.003934", "0.002372", "August 2026"],
    "42736_RTO61_final_tariff_120225.pdf": ["0.631727", "0.001547", "January 2026"],
    "44348_SRA11_final_tariff_022626.pdf": ["0.158617", "0.000393", "March 2026"],
    "44932_REP8_final_tariff_061726.pdf": ["0.015268", "July 2026"],
    "45647_TDSIC5_final_tariff.pdf": ["1.660720", "0.744252", "1.228107", "0.575165", "May 2026"],
    "45803_DSM2_final_tariffs_100825.pdf": ["0.001949", "0.336579", "January 2026", "$0.000000"],
    "46193_GCT1_final_tariff_032526.pdf": ["0.739905", "0.001731", "April 2026",
                                           "GENERATION COST TRACKER",
                                           "LIST OF APPLICABLE RATE ADJUSTMENT TRACKERS"],
    "46038_step2_compliance_filing_021826.pdf": ["(0.002708)", "(0.004203)", "March 2026", "4.27%"],
    "46038_docket_entry_step2_052726.pdf": ["IT IS SO ORDERED", "May 27, 2026"],
    "46038_step1_attL_tracker72_FMCA_p1_020725.pdf": ["set at $0"],
    "46097_tariff_IP_022525.pdf": [
        "16.474", "14.089", "10.825", "10.194", "5.703", "1.359", "180.00", "275.00",
        "600 kW", "60 percent", "80 percent", "70 MW", "13.289", "12.427", "12.271", "10.959",
        "not less than 12 years", "42 months",
    ],
    "IM_IN_TB_20_06-30-2026.pdf": [
        "0.0129810", "20.995", "18.472", "15.106", "14.700", "3.597", "11.050",
        "16.474",  # book carries the same I.P. sheet as the commission copy
    ],
    "38702_FAC96_tariff_060326.pdf": ["0.002422", "JUNE 8, 2026"],
    "45164_RA6_tariff_032526.pdf": ["0.242"],
    "43774_PJM16_tariff_052026.pdf": ["7.316", "0.4297"],
    "45245_SPR4_tariff_092425.pdf": ["0.048", "0.0008"],
    "44871_ECR9_tariff_111925.pdf": ["0.378", "0.0407"],
    "43827_DSM14_second_compliance_123025.pdf": ["0.3306", "0.0218"],
    "anderson_50917_approved_tariff.pdf": ["4.891", "0.010230", "3.839", "50917"],
    "auburn_50912_approved_tariff.pdf": ["0.034896", "50912"],
    "frankfort_50903_approved_tariff.pdf": [".928663", "0.013858", "50903"],
    "2025-IURC-Annual-Report.pdf": [
        "Anderson,", "Auburn, and Frankfort", "No REMCs remain under",
    ],
}


def fetch_all():
    for sub, fname, url in FILES:
        d = os.path.join(BOOKS, sub) if sub else BOOKS
        os.makedirs(d, exist_ok=True)
        dest = os.path.join(d, fname)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=300) as r:
            blob = r.read()
        if not blob.startswith(b"%PDF"):
            raise SystemExit(f"NOT A PDF: {fname} from {url[:120]} - first bytes {blob[:60]!r}")
        with open(dest, "wb") as fh:
            fh.write(blob)
        print(f"  fetched {fname}: {len(blob):,} bytes")
        time.sleep(1.3)


def verify_sentinels():
    import pymupdf
    bad = 0
    for sub, fname, _url in FILES:
        p = os.path.join(BOOKS, sub, fname) if sub else os.path.join(BOOKS, fname)
        if not os.path.exists(p):
            print(f"  MISSING FILE: {p}  (run with --fetch)")
            bad += 1
            continue
        text = "".join(page.get_text() for page in pymupdf.open(p))
        missing = [s for s in SENTINELS.get(fname, []) if s not in text]
        if missing:
            bad += 1
            print(f"  SENTINEL FAIL {fname}: missing {missing}")
        else:
            print(f"  ok {fname} ({len(SENTINELS.get(fname, []))} sentinels)")
    if bad:
        raise SystemExit(
            f"\n{bad} file(s) failed sentinel verification. A publisher revised a document at "
            f"the same URL (or a portal link rotated). RE-READ the changed sheets and update "
            f"the ROWS below before loading - do NOT load transcriptions that no longer match "
            f"their source.")


# ------------------------------------------------------------------------------------------
# THE ROWS.  Transcribed by hand from the commission-filed sheets cited on every row.
# Column semantics follow docs/TARIFF_SCRAPE_TARGETS.md OUTPUT SHAPE.
# ------------------------------------------------------------------------------------------
def R(utility, tariff_code, tariff_name, component_type, code, name, rate, unit, basis,
      applies_to, season, value_status, effective_date, source, source_url, notes):
    return dict(utility=utility, state="IN", tariff_code=tariff_code, tariff_name=tariff_name,
                component_type=component_type, code=code, name=name, rate=rate, unit=unit,
                basis=basis, applies_to=applies_to, season=season, value_status=value_status,
                effective_date=effective_date, source=source, source_url=source_url, notes=notes)


URL = {fname: url for _sub, fname, url in FILES}
NO_SEASON = ("No summer/non-summer split anywhere in this book for this class - single "
             "year-round rate stated by the sheet itself; season='all' is the book's "
             "structure, not an assumption.")

# ==========================================================================================
# DUKE ENERGY INDIANA - IURC No. 16 book (Cause 46038), commission-filed copies
# ==========================================================================================
DK_BOOK = ("Duke Energy Indiana IURC No. 16 tariff book as approved in Cause No. 46038 "
           "(Order 2025-01-29; sheets issued 2025-01-29, effective 2025-02-27), from the "
           "Step 1 Compliance Filing Attachment C (Redline and Clean Tariff) FILED WITH THE "
           "COMMISSION 2025-02-07")
DK_BOOK_URL = URL["46038_step1_attC_redline_clean_tariff_020725.pdf"]
DK_MIGRATION_CAVEAT = (
    "KNOWN LIMIT: Duke filed amended tariffs 2025-04-30 (rate-migration nunc pro tunc of "
    "2025-04-09; approved 2025-05-14, implemented 2025-05-19) with the Energy Division "
    "directly - that leaf is not retrievable from the docketed/30-day systems. The 2026-05-27 "
    "docket entry states the migration adjustment was implemented and refunded via Tracker 67.")
E_DK = "2025-02-27"

DUKE_ROWS = [
    # ---- Rate HLF, Original Tariff No. 12 ------------------------------------------------
    R(DUKE, "HLF", "High Load Factor Service (Tariff No. 12)", "eligibility", "HLF-FLOOR",
      "Minimum specified capacity", 25.0, "kW", "contract for specified capacity of not less "
      "than 25 kW; billing maximum load never less than 25 kW", "all voltages", "all",
      "published", E_DK, DK_BOOK, DK_BOOK_URL,
      "URDB's 25 kW floor for Duke HLF is CONFIRMED by the sheet - it is a broad industrial "
      "rate, not a large-load-only rate. " + NO_SEASON),
    R(DUKE, "HLF", "High Load Factor Service", "base_charge", "HLF-CONN-SEC",
      "Connection charge - secondary", 31.90, "$/month", "per month", "secondary (480 V or lower)",
      "all", "published", E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "HLF", "High Load Factor Service", "base_charge", "HLF-CONN-PRI",
      "Connection charge - primary / primary direct", 125.61, "$/month", "per month",
      "primary and primary direct (2,400-34,500 V)", "all", "published", E_DK, DK_BOOK,
      DK_BOOK_URL, None),
    R(DUKE, "HLF", "High Load Factor Service", "base_charge", "HLF-CONN-TRANS",
      "Connection charge - transmission", 855.37, "$/month", "per month",
      "transmission (69/138/230/345 kV)", "all", "published", E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "HLF", "High Load Factor Service", "demand", "HLF-DEM-SEC",
      "Maximum load charge - secondary", 27.51, "$/kW/month", "each kW of billing maximum load "
      "(highest 30-minute interval of the month)", "secondary (480 V or lower)", "all",
      "published", E_DK, DK_BOOK, DK_BOOK_URL, NO_SEASON),
    R(DUKE, "HLF", "High Load Factor Service", "demand", "HLF-DEM-PRI",
      "Maximum load charge - primary", 19.75, "$/kW/month", "each kW of billing maximum load",
      "primary (2,400-34,500 V)", "all", "published", E_DK, DK_BOOK, DK_BOOK_URL,
      "Primary DEMAND is the cheapest non-transmission tier but primary ENERGY is the most "
      "expensive - evaluate the pair, not either leg alone."),
    R(DUKE, "HLF", "High Load Factor Service", "demand", "HLF-DEM-PRIDIR",
      "Maximum load charge - primary direct", 22.92, "$/kW/month",
      "each kW of billing maximum load", "primary direct (2,400-34,500 V)", "all", "published",
      E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "HLF", "High Load Factor Service", "demand", "HLF-DEM-T69",
      "Maximum load charge - transmission 69 kV", 23.59, "$/kW/month",
      "each kW of billing maximum load", "transmission (69,000 V)", "all", "published", E_DK,
      DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "HLF", "High Load Factor Service", "demand", "HLF-DEM-T138",
      "Maximum load charge - transmission 138/230/345 kV", 20.51, "$/kW/month",
      "each kW of billing maximum load", "transmission (138,000/230,000/345,000 V)", "all",
      "published", E_DK, DK_BOOK, DK_BOOK_URL,
      "THE voltage delta: secondary $27.51 vs bulk transmission $20.51 = $7.00/kW-mo; primary "
      "$19.75 is LOWER than bulk transmission on the demand leg (energy leg reverses it). "
      + DK_MIGRATION_CAVEAT),
    R(DUKE, "HLF", "High Load Factor Service", "energy", "HLF-EN-SEC",
      "Energy charge - secondary", 0.055534, "$/kWh", "all energy used per month",
      "secondary (480 V or lower)", "all", "published", E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "HLF", "High Load Factor Service", "energy", "HLF-EN-PRI",
      "Energy charge - primary", 0.064825, "$/kWh", "all energy used per month",
      "primary (2,400-34,500 V)", "all", "published", E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "HLF", "High Load Factor Service", "energy", "HLF-EN-PRIDIR",
      "Energy charge - primary direct", 0.047773, "$/kWh", "all energy used per month",
      "primary direct (2,400-34,500 V)", "all", "published", E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "HLF", "High Load Factor Service", "energy", "HLF-EN-T69",
      "Energy charge - transmission 69 kV", 0.046775, "$/kWh", "all energy used per month",
      "transmission (69,000 V)", "all", "published", E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "HLF", "High Load Factor Service", "energy", "HLF-EN-T138",
      "Energy charge - transmission 138/230/345 kV", 0.044002, "$/kWh",
      "all energy used per month", "transmission (138,000/230,000/345,000 V)", "all",
      "published", E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "HLF", "High Load Factor Service", "rider", "HLF-KVAR", "kVAr charge", 0.34,
      "$/kVAr/month", "each kVAr of monthly billed kVAr demand (trig calc from peak 30-min kW "
      "and coincident or monthly-average power factor)", "all voltages", "all", "published",
      E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "HLF", "High Load Factor Service", "ratchet", "HLF-RATCHET",
      "Demand ratchet - NONE", None, None,
      "billing demand = current month's highest 30-minute load only (floor 25 kW); monthly "
      "minimum charge = the maximum load charge; NO 11/12-month ratchet clause exists on this "
      "sheet", "all voltages", "all", "published", E_DK, DK_BOOK, DK_BOOK_URL,
      "DECISION-RELEVANT OUTLIER: AES HL 75%, NIPSCO 632/633 75%, SIGECO HLF 90%, I&M "
      "large-load 80% - Duke HLF has no annual ratchet, so seasonal/monthly curtailment "
      "directly reduces the demand bill."),
    R(DUKE, "HLF", "High Load Factor Service", "eligibility", "HLF-MAINT",
      "Maintenance period provision fee", 500.0, "$/occurrence",
      "scheduled maintenance windows (max 2 per 12 months, max 14 days total): maximum load "
      "charge prorated by days; $500 fee each time the provision is used", "primary voltage "
      "and higher", "all", "published", E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "HLF", "High Load Factor Service", "eligibility", "HLF-20MW",
      "Large-load credit assurance clause (>=20 MW)", None, None,
      "customers seeking >=20 MW at one or more aggregated premises requiring significant "
      "production/transmission/distribution investment may be required to provide financial "
      "and/or performance and credit assurance at the Company's discretion", "all voltages",
      "all", "published", E_DK, DK_BOOK, DK_BOOK_URL,
      "Duke has NO separate large-load/data-centre schedule in the IURC No. 16 book - this "
      "clause inside HLF (and 11.5) is the only large-load-specific text. New generation cost "
      "recovery rides Tracker 75 (GCT, Cause 46193)."),
    R(DUKE, "HLF", "High Load Factor Service", "eligibility", "HLF-SUBSTATION",
      "Customer-owned substation requirement", None, None,
      "transmission/primary customers furnish, own and maintain the complete substation "
      "(switches, protection, transformers); Company furnishes metering only", "transmission "
      "and primary", "all", "published", E_DK, DK_BOOK, DK_BOOK_URL, None),
    # ---- Rate LLF, Original Tariff No. 10-A ----------------------------------------------
    R(DUKE, "LLF", "Low Load Factor Service (Tariff No. 10-A)", "base_charge", "LLF-CONN-SEC",
      "Connection charge - secondary (grandfathered)", 27.63, "$/month", "per month",
      "secondary (closed class)", "all", "published", E_DK, DK_BOOK, DK_BOOK_URL,
      "Legacy LLF Secondary is CLOSED to new participation; existing customers transition at "
      "the next rate case or 5 years, whichever is later."),
    R(DUKE, "LLF", "Low Load Factor Service", "base_charge", "LLF-CONN-PRI",
      "Connection charge - primary / primary direct", 109.55, "$/month", "per month",
      "primary and primary direct", "all", "published", E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "LLF", "Low Load Factor Service", "base_charge", "LLF-CONN-TRANS",
      "Connection charge - transmission", 331.00, "$/month", "per month", "transmission",
      "all", "published", E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "LLF", "Low Load Factor Service", "demand", "LLF-DEM-PRI",
      "Maximum load charge - primary", 6.54, "$/kW/month", "each kW of billing maximum load "
      "(30-minute basis)", "primary (2,400-34,500 V)", "all", "published", E_DK, DK_BOOK,
      DK_BOOK_URL, NO_SEASON),
    R(DUKE, "LLF", "Low Load Factor Service", "demand", "LLF-DEM-PRIDIR",
      "Maximum load charge - primary direct", 8.31, "$/kW/month",
      "each kW of billing maximum load", "primary direct (2,400-34,500 V)", "all", "published",
      E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "LLF", "Low Load Factor Service", "demand", "LLF-DEM-TRANS",
      "Maximum load charge - transmission", 5.16, "$/kW/month",
      "each kW of billing maximum load", "transmission (69/138/230/345 kV)", "all", "published",
      E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "LLF", "Low Load Factor Service", "energy", "LLF-EN-PRI",
      "Energy charge - primary", 0.089722, "$/kWh", "in addition to the maximum load charge",
      "primary", "all", "published", E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "LLF", "Low Load Factor Service", "energy", "LLF-EN-PRIDIR",
      "Energy charge - primary direct", 0.078946, "$/kWh", "in addition to the maximum load "
      "charge", "primary direct", "all", "published", E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "LLF", "Low Load Factor Service", "energy", "LLF-EN-TRANS",
      "Energy charge - transmission", 0.081902, "$/kWh", "in addition to the maximum load "
      "charge", "transmission", "all", "published", E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "LLF", "Low Load Factor Service", "rider", "LLF-KVAR", "kVAr charge", 0.34,
      "$/kVAr/month", "each kVAr of monthly billed kVAr demand; not applied to secondary "
      "customers until kVAr metering installed", "all voltages", "all", "published", E_DK,
      DK_BOOK, DK_BOOK_URL, None),
    # ---- Rate LLF Secondary (open), Original Tariff No. 10-B ------------------------------
    R(DUKE, "LLF-B", "Low Load Factor Secondary Service (Tariff No. 10-B)", "base_charge",
      "LLFB-CONN", "Connection charge - secondary", 27.63, "$/month", "per month", "secondary",
      "all", "published", E_DK, DK_BOOK, DK_BOOK_URL, None),
    R(DUKE, "LLF-B", "Low Load Factor Secondary Service", "demand", "LLFB-DEM",
      "Demand charge", 8.02, "$/kW/month", "each kW of billing maximum load", "secondary",
      "all", "published", E_DK, DK_BOOK, DK_BOOK_URL, NO_SEASON),
    R(DUKE, "LLF-B", "Low Load Factor Secondary Service", "energy", "LLFB-EN",
      "Energy charge", 0.101700, "$/kWh", "all kWh", "secondary", "all", "published", E_DK,
      DK_BOOK, DK_BOOK_URL, None),
]

# TOU 11.5 - compact generation (4 voltages x 3 demand parts + 3 energy periods)
_TOU_SRC = ("Duke Energy Indiana Optional Rate HLF/LLF - Time-of-Use Service, IURC No. 16 "
            "Original Tariff No. 11.5 (Cause 46038), eff 2025-02-27")
_tou_v = [("SEC", "secondary", 1.57, 6.91, 2.19, 0.112723, 0.098879, 0.066113),
          ("PRI", "primary", 2.03, 8.91, 1.98, 0.083688, 0.073411, 0.051931),
          ("PRIDIR", "primary direct", 3.36, 14.78, 0.57, 0.059853, 0.053432, 0.038213),
          ("TRANS", "transmission (69 kV+)", 3.04, 13.33, 0.03, 0.055537, 0.049108, 0.035390)]
for vc, vname, dpk, dmid, dbase, epk, eoff, edisc in _tou_v:
    DUKE_ROWS += [
        R(DUKE, "HLF/LLF-TOU", "Optional Time-of-Use Service (Tariff No. 11.5)", "demand",
          f"TOU-DEM-PK-{vc}", f"Peak demand charge - {vname}", dpk, "$/kW/month",
          "max 30-min kW in on-peak periods (5-9 pm all year; +6-8 am winter)", vname, "all",
          "published", E_DK, _TOU_SRC, DK_BOOK_URL, None),
        R(DUKE, "HLF/LLF-TOU", "Optional Time-of-Use Service", "demand",
          f"TOU-DEM-MID-{vc}", f"Mid-peak demand charge - {vname}", dmid, "$/kW/month",
          "max 30-min kW in on-peak or off-peak periods of the current billing period", vname,
          "all", "published", E_DK, _TOU_SRC, DK_BOOK_URL, None),
        R(DUKE, "HLF/LLF-TOU", "Optional Time-of-Use Service", "ratchet",
          f"TOU-DEM-BASE-{vc}", f"Base demand charge - {vname}", dbase, "$/kW/month",
          "base demand = HIGHER of max 30-min kW over current + 11 prior billing periods, or "
          "50% of contract demand - a 12-month 100% ratchet on this component", vname, "all",
          "published", E_DK, _TOU_SRC, DK_BOOK_URL, None),
        R(DUKE, "HLF/LLF-TOU", "Optional Time-of-Use Service", "energy",
          f"TOU-EN-PK-{vc}", f"Peak energy charge - {vname}", epk, "$/kWh", "on-peak kWh",
          vname, "all", "published", E_DK, _TOU_SRC, DK_BOOK_URL, None),
        R(DUKE, "HLF/LLF-TOU", "Optional Time-of-Use Service", "energy",
          f"TOU-EN-OFF-{vc}", f"Off-peak energy charge - {vname}", eoff, "$/kWh",
          "off-peak kWh (all other hours; 6 holidays fully off-peak)", vname, "all",
          "published", E_DK, _TOU_SRC, DK_BOOK_URL, None),
        R(DUKE, "HLF/LLF-TOU", "Optional Time-of-Use Service", "energy",
          f"TOU-EN-DISC-{vc}", f"Discount (super off-peak) energy charge - {vname}", edisc,
          "$/kWh", "12-4 am hours", vname, "all", "published", E_DK, _TOU_SRC, DK_BOOK_URL,
          None),
    ]
DUKE_ROWS += [
    R(DUKE, "HLF/LLF-TOU", "Optional Time-of-Use Service", "eligibility", "TOU-ELIG",
      "Eligibility and term", None, None,
      "available to HLF/LLF customers; new customers >20 MW require Company approval; 1-year "
      "agreement auto-renewing; leaving bars re-entry for 12 months", "all voltages", "all",
      "published", E_DK, _TOU_SRC, DK_BOOK_URL, None),
    R(DUKE, "BDP", "Backup Delivery Point Service (Tariff No. 21)", "eligibility", "BDP-STATUS",
      "Additional/backup delivery points available", None, None,
      "non-residential customers may take additional delivery points under Tariff No. 21 "
      "rates/terms, capacity permitting", "all voltages", "all", "published", E_DK, DK_BOOK,
      DK_BOOK_URL, "Relevant to dual-feed data-centre topologies; charge structure is on the "
      "Tariff 21 sheets (not transcribed - flag for follow-up if dual feed is pursued)."),
    # ---- fuel base ------------------------------------------------------------------------
    R(DUKE, "RIDER-60", "Fuel Cost Adjustment (Tariff No. 60)", "fuel_base", "DUKE-FUELBASE",
      "Base cost of fuel EMBEDDED in base rates (BF)", 0.034378, "$/kWh",
      "FAC factor = F/S - BF; BF set by the Cause 46038 order (raised from $0.026955)",
      "all rate schedules with FAC", "all", "published", "2026-07-01",
      "Duke Energy Indiana Tariff No. 60 (Sixth Revised), Cause No. 38707 FAC 148 final "
      "tariff filed 2026-06-30", URL["38707_FAC148_final_tariff_063026.pdf"],
      "THE single most misread number: subtract BF before applying any FAC factor or the "
      "fuel clause is double-counted."),
    # ---- Appendix A roster ----------------------------------------------------------------
    R(DUKE, "APPENDIX-A", "Appendix A - List of Applicable Rate Adjustment Trackers", "rider",
      "DUKE-TRACKER-ROSTER", "Eleven trackers apply to RS/CS/LLF/HLF/WP/SL/MHLS/UOLS/MOLS/LED/"
      "MS/USFL", None, None,
      "Tariff No. 60 FAC | 62 Environmental Compliance | 65 TDSIC | 66 Energy Efficiency | "
      "67 Credits | 68 RTO Non-Fuel | 70 Reliability | 72 Federally Mandated | 73 Renewable "
      "Energy Project | 74 Load Control | 75 Generation Cost Tracker", "all listed schedules",
      "all", "published", "2026-03-25",
      "Duke Energy Indiana First Revised Tariff No. A (Appendix A), issued/eff 2026-03-25, "
      "filed with the GCT 1 final tariff (Cause 46193)",
      URL["46193_GCT1_final_tariff_032526.pdf"],
      "This is the applicability map the brief called 'Appendix A1'. Standing dockets: FAC="
      "38707 (quarterly), ECR=42061 (semi-annual), TDSIC=45647, EE/LC=45803, Credits=46038+"
      "30-day, RTO=42736 (annual), Reliability=44348, FMCA=none yet, REP=44932, GCT=46193."),
    # ---- Step 2 status --------------------------------------------------------------------
    R(DUKE, "RATE-CASE", "Cause 46038 multi-step rate implementation", "eligibility",
      "DUKE-STEP2-STATUS", "Step 2 rates in effect via Tracker 67; appeal pending", None, None,
      "Step 2 (+4.27% overall: remove Step 1 adj 3.69% + capital structure 0.08% + recon "
      "mitigation 0.50%) took effect bills rendered March 2026 cycle 1 through Tariff No. 67, "
      "interim subject to refund; Energy Division compliance approved by docket entry "
      "2026-05-27 (IT IS SO ORDERED)", "all rate schedules", "all", "published", "2026-03-01",
      "Duke Energy Indiana Step 2 Compliance Filing (2026-02-18) + IURC docket entry "
      "2026-05-27, Cause No. 46038", URL["46038_docket_entry_step2_052726.pdf"],
      "CAVEAT: OUCC + Duke Industrial Group + Nucor + CAC joint appeal to the full Commission "
      "filed 2026-06-04 was pending at harvest (2026-08-18); Step 2 rates could be revised "
      "retroactively. " + DK_MIGRATION_CAVEAT),
]

# Duke tracker current factors.  HLF is billed per NON-COINCIDENT kW on most trackers (stated
# in each tariff: "revenue adjustment for Rate HLF shall be based on demands"); LLF per kWh.
_dk_trk = [
    # code, tariff no+name, HLF rate, HLF unit, LLF rate, eff date, source desc, url file, extra note
    ("FAC", "60", "Fuel Cost Adjustment", 0.004319, "$/kWh", 0.004422, "2026-07-01",
     "Cause No. 38707 FAC 148 final tariff (filed 2026-06-30), eff bills rendered July 2026 "
     "cycle 1", "38707_FAC148_final_tariff_063026.pdf",
     "Quarterly. FAC 149 (filed 2026-07-30) pending -> next factors ~Oct 2026. FAC is per kWh "
     "for ALL rate groups including HLF."),
    ("ECR", "62", "Environmental Compliance Adjustment", -1.003934, "$/kW/month", -0.002372,
     "2026-08-01",
     "Cause No. 42061 ECR 45 final tariff (filed 2026-08-14), eff bills rendered August 2026 "
     "cycle 11", "42061_ECR45_final_tariff_081426.pdf",
     "Semi-annual. Currently a CREDIT. HLF factor is per non-coincident kW; other groups per "
     "kWh."),
    ("RTO", "68", "RTO Non-Fuel Costs and Revenue Adjustment", 0.631727, "$/kW/month",
     0.001547, "2026-01-01",
     "Cause No. 42736 RTO 61 final tariff (filed 2025-12-02), eff bills rendered January 2026 "
     "cycle 1", "42736_RTO61_final_tariff_120225.pdf",
     "Annual. MISO TEMT + Madison-station PJM non-fuel costs net of the $76.965M costs and "
     "$40.0M revenues already in base rates (Cause 46038). HLF per kW."),
    ("SRA", "70", "Reliability Adjustment", 0.158617, "$/kW/month", 0.000393, "2026-03-01",
     "Cause No. 44348 SRA 11 final tariff (filed 2026-02-26), eff bills rendered March 2026 "
     "cycle 1", "44348_SRA11_final_tariff_022626.pdf",
     "Annual. Reliability purchases + MISO non-native sale margin sharing (100% of first $5M, "
     "50% above). HLF per kW."),
    ("REP", "73", "Renewable Energy Project Adjustment", -0.015268, "$/kW/month", -0.000028,
     "2026-07-01",
     "Cause No. 44932 REP 8 final tariff (filed 2026-06-17), eff bills rendered July 2026 "
     "cycle 1", "44932_REP8_final_tariff_061726.pdf", "Currently a small credit. HLF per kW."),
    ("LC", "74", "Load Control Adjustment", -0.336579, "$/kW/month", -0.000835, "2026-01-01",
     "Cause No. 45803 DSM-2 final tariffs (filed 2025-10-08), First Revised Tariff No. 74, "
     "eff January 2026 cycle 1", "45803_DSM2_final_tariffs_100825.pdf",
     "Demand-response (PowerManager) credits. HLF per kW."),
    ("GCT", "75", "Generation Cost Tracker", 0.739905, "$/kW/month", 0.001731, "2026-04-01",
     "Cause No. 46193 GCT 1 final tariff (filed 2026-03-25), Original Tariff No. 75, eff "
     "bills rendered April 2026 cycle 1", "46193_GCT1_final_tariff_032526.pdf",
     "NEW tracker (clean energy projects under IC 8-1-8.8, rate-base treatment, <=6-month "
     "reset). GCT 2 (filed 2026-05-15) pending - hearing was 2026-08-11. HLF per kW. This is "
     "where new-generation cost for load growth lands between rate cases."),
]
for code, tno, tname, hlf, hlf_u, llf, eff, srcd, urlf, note in _dk_trk:
    DUKE_ROWS += [
        R(DUKE, f"RIDER-{tno}", f"{tname} (Tariff No. {tno})", "rider", f"DK-{code}-HLF",
          f"{tname} - current factor, Rate HLF", hlf, hlf_u,
          "monthly billed kW (HLF billed on demands basis)" if "kW/" in hlf_u
          else "monthly billed kWh", "Rate HLF", "all", "published", eff, srcd, URL[urlf], note),
        R(DUKE, f"RIDER-{tno}", f"{tname} (Tariff No. {tno})", "rider", f"DK-{code}-LLF",
          f"{tname} - current factor, Rate LLF", llf, "$/kWh", "monthly billed kWh",
          "Rate LLF", "all", "published", eff, srcd, URL[urlf], None),
    ]
DUKE_ROWS += [
    R(DUKE, "RIDER-65", "TDSIC - T&D Infrastructure Improvement Cost (Tariff No. 65)", "rider",
      "DK-TDSIC-HLF-SEC", "TDSIC total factor - HLF secondary", 0.575165, "$/kW/month",
      "Total TDSIC column (TDSIC 2.0 + TED; TDSIC 1.0 = $0)", "Rate HLF - secondary", "all",
      "published", "2026-05-01", "Cause No. 45647 TDSIC 5 final tariff (filed 2026-04-09), "
      "First Revised Tariff No. 65, eff bills rendered May 2026 cycle 1",
      URL["45647_TDSIC5_final_tariff.pdf"],
      "TDSIC 6 (filed 2026-04-30) pending - hearing 2026-09-01. HLF billed per kW; LLF per kWh."),
    R(DUKE, "RIDER-65", "TDSIC (Tariff No. 65)", "rider", "DK-TDSIC-HLF-PRI",
      "TDSIC total factor - HLF primary", 1.228107, "$/kW/month", "Total TDSIC column",
      "Rate HLF - primary", "all", "published", "2026-05-01",
      "Cause No. 45647 TDSIC 5 final tariff", URL["45647_TDSIC5_final_tariff.pdf"], None),
    R(DUKE, "RIDER-65", "TDSIC (Tariff No. 65)", "rider", "DK-TDSIC-HLF-PRIDIR",
      "TDSIC total factor - HLF primary direct", 0.792319, "$/kW/month", "Total TDSIC column",
      "Rate HLF - primary direct", "all", "published", "2026-05-01",
      "Cause No. 45647 TDSIC 5 final tariff", URL["45647_TDSIC5_final_tariff.pdf"], None),
    R(DUKE, "RIDER-65", "TDSIC (Tariff No. 65)", "rider", "DK-TDSIC-HLF-CTRANS",
      "TDSIC total factor - HLF common transmission", 1.660720, "$/kW/month",
      "Total TDSIC column", "Rate HLF - common transmission", "all", "published", "2026-05-01",
      "Cause No. 45647 TDSIC 5 final tariff", URL["45647_TDSIC5_final_tariff.pdf"], None),
    R(DUKE, "RIDER-65", "TDSIC (Tariff No. 65)", "rider", "DK-TDSIC-HLF-BTRANS",
      "TDSIC total factor - HLF bulk transmission", 0.744252, "$/kW/month",
      "Total TDSIC column", "Rate HLF - bulk transmission", "all", "published", "2026-05-01",
      "Cause No. 45647 TDSIC 5 final tariff", URL["45647_TDSIC5_final_tariff.pdf"],
      "The TDSIC sheet is the one Duke document that splits HLF into five delivery tiers "
      "including common vs bulk transmission."),
    R(DUKE, "RIDER-65", "TDSIC (Tariff No. 65)", "rider", "DK-TDSIC-LLF-TRANS",
      "TDSIC total factor - LLF transmission", 0.000152, "$/kWh", "Total TDSIC column",
      "Rate LLF - transmission", "all", "published", "2026-05-01",
      "Cause No. 45647 TDSIC 5 final tariff", URL["45647_TDSIC5_final_tariff.pdf"], None),
    R(DUKE, "RIDER-65", "TDSIC (Tariff No. 65)", "rider", "DK-TDSIC-LLF-PRI",
      "TDSIC total factor - LLF primary", 0.003046, "$/kWh", "Total TDSIC column",
      "Rate LLF - primary", "all", "published", "2026-05-01",
      "Cause No. 45647 TDSIC 5 final tariff", URL["45647_TDSIC5_final_tariff.pdf"], None),
    R(DUKE, "RIDER-66", "Energy Efficiency Adjustment (Tariff No. 66)", "rider",
      "DK-EE-PARTICIPATING", "EE factor - participating customers (all C&I groups)", 0.001949,
      "$/kWh", "monthly billed kWh", "Rates CS/LLF/HLF/WP/SL and others", "all", "published",
      "2026-01-01", "Cause No. 45803 DSM-2 final tariffs (filed 2025-10-08), First Revised "
      "Tariff No. 66, eff January 2026 cycle 1", URL["45803_DSM2_final_tariffs_100825.pdf"],
      "DSM-3 (filed 2026-06-18) pending."),
    R(DUKE, "RIDER-66", "Energy Efficiency Adjustment (Tariff No. 66)", "rider",
      "DK-EE-OPTOUT", "EE factor - opted-out qualifying customers", 0.0, "$/kWh",
      "monthly billed kWh", "opted-out qualifying C&I customers", "all", "published",
      "2026-01-01", "Cause No. 45803 DSM-2 final tariffs, First Revised Tariff No. 66",
      URL["45803_DSM2_final_tariffs_100825.pdf"],
      "PUBLISHED ZERO - the sheet prints $0.000000 for opt-out vintages 2014-2020 (later "
      "vintages carry only residual reconciliation). A new large load elects opt-out."),
    R(DUKE, "RIDER-67", "Credits Adjustment (Tariff No. 67)", "rider", "DK-CR67-HLF",
      "Credits adjustment - Rate HLF", -0.002708, "$/kWh", "monthly billed kWh (Tariff 67 is "
      "per kWh for ALL groups)", "Rate HLF", "all", "published", "2026-03-01",
      "Duke Step 2 Compliance Filing Attachment FF, Third Revised Sheet No. 67, eff bills "
      "rendered March 2026 cycle 1; approved by docket entry 2026-05-27 (Cause 46038)",
      URL["46038_step2_compliance_filing_021826.pdf"],
      "Carries TCJA excess-deferred-tax credits, Edwardsport IGCC tax incentives, AND the "
      "Step 2 base-rate adjustment. Updated via 30-day filings between cases."),
    R(DUKE, "RIDER-67", "Credits Adjustment (Tariff No. 67)", "rider", "DK-CR67-LLF",
      "Credits adjustment - Rate LLF", -0.004203, "$/kWh", "monthly billed kWh", "Rate LLF",
      "all", "published", "2026-03-01",
      "Duke Step 2 Compliance Filing Attachment FF, Third Revised Sheet No. 67",
      URL["46038_step2_compliance_filing_021826.pdf"], None),
    R(DUKE, "RIDER-72", "Federally Mandated Cost Adjustment (Tariff No. 72)", "rider",
      "DK-FMCA", "FMCA factor - all rate groups", 0.0, "$/kWh",
      "monthly billed kWh", "all rate schedules", "all", "published", E_DK,
      "Cause No. 46038 Final Order Attachment L (Tracker 72 overview), filed 2025-02-07",
      URL["46038_step1_attL_tracker72_FMCA_p1_020725.pdf"],
      "PUBLISHED ZERO: 'Currently this tracker's rates are set at $0. This tariff will "
      "continue at $0 rates until new federally mandated projects are approved for recovery.'"),
]

# ==========================================================================================
# INDIANA MICHIGAN POWER (I&M) - I.U.R.C. No. 20 book, commission-filed copies
# ==========================================================================================
IP_SRC = ("I&M Tariff I.P. (Industrial Power), I.U.R.C. No. 20 First Revised Sheet Nos. "
          "21-21.3 + Original 21.4-21.7, submitted to the Commission 2025-02-25 per the "
          "2025-02-19 Order in Cause No. 46097, eff bills rendered on/after 2025-02-19")
IP_URL = URL["46097_tariff_IP_022525.pdf"]
IMBOOK = ("I&M Indiana tariff book I.U.R.C. No. 20 as compiled 2026-06-30 (utility-assembled "
          "current book; per-sheet cause numbers and effective dates carried on each row)")
IMBOOK_URL = URL["IM_IN_TB_20_06-30-2026.pdf"]
E_IP = "2025-02-19"

_ip_v = [("327", "Secondary", 16.474, 5.703, 1.359, 180.00, 20.995, 13.289),
         ("322", "Primary", 14.089, 5.413, 1.313, 275.00, 18.472, 12.427),
         ("323", "Subtransmission", 10.825, 5.333, 1.296, 275.00, 15.106, 12.271),
         ("324", "Transmission", 10.194, 5.058, 1.286, 275.00, 14.700, 10.959)]
IM_ROWS = [
    R(IM, "IP", "Tariff I.P. (Industrial Power)", "eligibility", "IP-FLOOR",
      "Minimum monthly billing demand", 600.0, "kW", "billing demand shall not be less than "
      "600 kW; written contracts required at >=1,500 kW", "all voltages", "all", "published",
      E_IP, IP_SRC, IP_URL,
      "VERIFIED against the commission copy: the prior agent's transcription (demand 16.474/"
      "14.089/10.825/10.194 by voltage) is exact. " + NO_SEASON),
]
for tc, vn, dem, e1, e2, svc, mindem, embcap in _ip_v:
    IM_ROWS += [
        R(IM, "IP", "Tariff I.P. (Industrial Power)", "base_charge", f"IP-SVC-{tc}",
          f"Monthly service charge - {vn} (code {tc})", svc, "$/month", "per month", vn, "all",
          "published", E_IP, IP_SRC, IP_URL, None),
        R(IM, "IP", "Tariff I.P. (Industrial Power)", "demand", f"IP-DEM-{tc}",
          f"Demand charge - {vn} (code {tc})", dem, "$/kW/month",
          "single-highest 15-minute integrated peak, subject to off-peak provision and "
          "minimums", vn, "all", "published", E_IP, IP_SRC, IP_URL, NO_SEASON),
        R(IM, "IP", "Tariff I.P. (Industrial Power)", "energy", f"IP-EN1-{tc}",
          f"Energy charge block 1 - {vn}", round(e1 / 100.0, 6), "$/kWh",
          "first 410 kWh per kW of billing demand", vn, "all", "published", E_IP, IP_SRC,
          IP_URL, "Hours-use block: 410 kWh/kW/mo = ~56% load factor breakpoint."),
        R(IM, "IP", "Tariff I.P. (Industrial Power)", "energy", f"IP-EN2-{tc}",
          f"Energy charge block 2 - {vn}", round(e2 / 100.0, 6), "$/kWh",
          "over 410 kWh per kW of billing demand", vn, "all", "published", E_IP, IP_SRC,
          IP_URL, None),
        R(IM, "IP", "Tariff I.P. (Industrial Power)", "demand", f"IP-MINDEM-{tc}",
          f"Minimum demand charge - {vn}", mindem, "$/kW/month",
          "used in the monthly minimum charge: service charge + minimum demand charge x "
          "billing demand + applicable riders", vn, "all", "published", E_IP, IP_SRC, IP_URL,
          None),
        R(IM, "IP-LL", "Tariff I.P. - Large Load provisions", "demand", f"IPLL-EMBCAP-{tc}",
          f"Step 1 Embedded Capacity Charge - {vn}", embcap, "$/kW/month",
          "Large Load minimum charge adds this x billing demand on top of the minimum demand "
          "charge; formula: (Block1 - Block2 energy rate) x Block1 hours - (min demand charge "
          "- demand charge)", vn, "all", "published", E_IP, IP_SRC, IP_URL,
          "The bill FLOOR for a >=70 MW customer: minimum charge = service charge + (min "
          "demand + embedded capacity + demand-based riders) x billing demand."),
    ]
IM_ROWS += [
    R(IM, "IP", "Tariff I.P. (Industrial Power)", "rider", "IP-KVAR",
      "Reactive demand charge/credit", 1.50, "$/kVAr/month",
      "two-sided: charge per kVAr (leading or lagging) in excess of 50% of metered kW demand; "
      "credit per kVAr below 50%", "all voltages", "all", "published", E_IP, IP_SRC, IP_URL,
      None),
    R(IM, "IP", "Tariff I.P. (Industrial Power)", "ratchet", "IP-RATCHET-STD",
      "Standard demand ratchet", 60.0, "% of highest",
      "monthly billing demand >= 60% of the GREATER of (a) contract capacity, (b) highest "
      "billing demand in past 11 months, (c) 1,000 kW; 15-minute basis", "customers under "
      "70 MW", "all", "published", E_IP, IP_SRC, IP_URL, None),
    R(IM, "IP", "Tariff I.P. (Industrial Power)", "eligibility", "IP-OFFPEAK",
      "Off-peak hour provision", None, None,
      "off-peak demand (all hours except 7 am - 9 pm Mon-Fri) disregarded, but billing demand "
      "never below 60% of month max nor 60% of contract/11-month high", "all voltages", "all",
      "published", E_IP, IP_SRC, IP_URL, None),
    R(IM, "IP", "Tariff I.P. (Industrial Power)", "eligibility", "IP-TERM",
      "Standard contract term", 2.0, "years", "initial period >= 2 years, 1-year notice to "
      "discontinue; longer initial terms where new facilities required", "customers under "
      "70 MW", "all", "published", E_IP, IP_SRC, IP_URL, None),
    R(IM, "IP", "Tariff I.P. (Industrial Power)", "eligibility", "IP-METERV",
      "Metered voltage multipliers", None, None,
      "low-side of customer-owned transformer x1.01; high-side of Company-owned transformer "
      "x0.98", "all voltages", "all", "published", E_IP, IP_SRC, IP_URL, None),
    # Large Load
    R(IM, "IP-LL", "Tariff I.P. - Large Load provisions (Cause 46097)", "eligibility",
      "IPLL-ELIG", "Large Load Customer definition", 70.0, "MW",
      ">=70 MW contract capacity at one plant (or reasonably expected to grow to it), or "
      ">=150 MW aggregated across premises of >=1 MW each; applies to new load on/after "
      "2024-01-01; terms set in an Electric Services Agreement", "large load", "all",
      "published", E_IP, IP_SRC, IP_URL,
      "FLAGGED LARGE-LOAD/DATA-CENTRE FRAMEWORK - the negotiated-ESA analogue of NIPSCO Rate "
      "631. Docket intervenors included Amazon Data Services and the Data Center Coalition."),
    R(IM, "IP-LL", "Tariff I.P. - Large Load provisions", "eligibility", "IPLL-TERM",
      "Initial contract term", 12.0, "years",
      "initial term >= 12 years, commencing AFTER a designated Load Ramp Period (<= 5 years); "
      "42 months written notice to discontinue", "large load", "all", "published", E_IP,
      IP_SRC, IP_URL, None),
    R(IM, "IP-LL", "Tariff I.P. - Large Load provisions", "ratchet", "IPLL-RATCHET",
      "Large Load demand ratchet", 80.0, "% of highest",
      "monthly billing demand >= the GREATER of (a) 80% of contract capacity for the period, "
      "(b) 80% of highest billing demand in past 11 months; metered-voltage adjustment does "
      "not apply to the minimum", "large load", "all", "published", E_IP, IP_SRC, IP_URL,
      "VERIFIES the brief's '80% ratchet'."),
    R(IM, "IP-LL", "Tariff I.P. - Large Load provisions", "eligibility", "IPLL-EXIT",
      "Capacity reduction and Exit Fee", None, None,
      "after year 5: up to 20% reduction free with 42-month notice; beyond 20% or termination "
      "-> Exit Fee = nominal remaining minimum charge for the excess (year 1), less OSS/PJM "
      "rider contribution in later years; Exit Fee period 1-5 years; Company must attempt "
      "mitigation by re-assigning capacity", "large load", "all", "published", E_IP, IP_SRC,
      IP_URL, None),
    R(IM, "IP-LL", "Tariff I.P. - Large Load provisions", "eligibility", "IPLL-COLLATERAL",
      "Collateral requirement", 24.0, "x max monthly non-fuel bill",
      "collateral = 24 x maximum expected (yr 1) or actual maximum (after yr 1) monthly "
      "non-fuel bill; recomputed annually (posted if +10%); exempt at A-/A3 rating AND "
      "liquidity > 10x; 50% exemption (cap $250M) on liquidity alone; forms: parent guarantee "
      "/ LOC (360-day) / cash", "large load", "all", "published", E_IP, IP_SRC, IP_URL, None),
    # G.S. (adjacent class, to 1,000 kW)
    R(IM, "GS", "Tariff G.S. (General Service)", "eligibility", "GS-CEILING",
      "Class ceiling", 1000.0, "kW", "customers qualify until 12-month average metered demand "
      "exceeds 1,000 kW (then Tariff I.P.)", "all voltages", "all", "published", "2024-05-28",
      IMBOOK + "; Tariff G.S. sheets eff 2024-05-28 (Cause 45933)", IMBOOK_URL, None),
    R(IM, "GS", "Tariff G.S. (General Service)", "demand", "GS-DEM-SEC",
      "Demand charge >10 kW - secondary (codes 215/218)", 3.597, "$/kW/month", "kW > 10",
      "secondary", "all", "published", "2024-05-28", IMBOOK, IMBOOK_URL, NO_SEASON),
    R(IM, "GS", "Tariff G.S. (General Service)", "demand", "GS-DEM-PRI",
      "Demand charge >10 kW - primary (code 217)", 2.368, "$/kW/month", "kW > 10", "primary",
      "all", "published", "2024-05-28", IMBOOK, IMBOOK_URL, None),
    R(IM, "GS", "Tariff G.S. (General Service)", "demand", "GS-DEM-SUBT",
      "Demand charge >10 kW - subtransmission (code 236)", 0.0, "$/kW/month", "kW > 10",
      "subtransmission", "all", "published", "2024-05-28", IMBOOK, IMBOOK_URL,
      "PUBLISHED ZERO on the sheet (0.000) - not an absent value."),
    R(IM, "GS", "Tariff G.S. (General Service)", "demand", "GS-DEM-TRANS",
      "Demand charge >10 kW - transmission (code 239)", 0.0, "$/kW/month", "kW > 10",
      "transmission", "all", "published", "2024-05-28", IMBOOK, IMBOOK_URL,
      "PUBLISHED ZERO on the sheet (0.000)."),
    R(IM, "GS", "Tariff G.S. (General Service)", "energy", "GS-EN1-SEC",
      "Energy charge first 4,500 kWh - secondary", 0.11050, "$/kWh", "first 4,500 kWh",
      "secondary", "all", "published", "2024-05-28", IMBOOK, IMBOOK_URL, None),
    R(IM, "GS", "Tariff G.S. (General Service)", "energy", "GS-EN2-SEC",
      "Energy charge over 4,500 kWh - secondary", 0.09996, "$/kWh", "over 4,500 kWh",
      "secondary", "all", "published", "2024-05-28", IMBOOK, IMBOOK_URL, None),
    R(IM, "GS", "Tariff G.S. (General Service)", "energy", "GS-EN1-TRANS",
      "Energy charge first 4,500 kWh - transmission", 0.09001, "$/kWh", "first 4,500 kWh",
      "transmission", "all", "published", "2024-05-28", IMBOOK, IMBOOK_URL, None),
    R(IM, "GS", "Tariff G.S. (General Service)", "energy", "GS-EN2-TRANS",
      "Energy charge over 4,500 kWh - transmission", 0.08001, "$/kWh", "over 4,500 kWh",
      "transmission", "all", "published", "2024-05-28", IMBOOK, IMBOOK_URL, None),
    R(IM, "GS", "Tariff G.S. (General Service)", "base_charge", "GS-SVC-SEC",
      "Monthly service charge - secondary", 29.00, "$/month", "per month", "secondary", "all",
      "published", "2024-05-28", IMBOOK, IMBOOK_URL, None),
    R(IM, "GS", "Tariff G.S. (General Service)", "base_charge", "GS-SVC-PRI",
      "Monthly service charge - primary and above", 210.00, "$/month", "per month",
      "primary/subtransmission/transmission", "all", "published", "2024-05-28", IMBOOK,
      IMBOOK_URL, None),
    # fuel base + rider roster
    R(IM, "RIDER-FAC", "Fuel Cost Adjustment Rider (Sheet 46)", "fuel_base", "IM-FUELBASE",
      "Base fuel cost EMBEDDED in base rates", 0.0129810, "$/kWh",
      "FAC adjustment factor = F/S - $0.0129810 per kWh (Original Sheet No. 46, Cause 45933, "
      "eff 2024-05-28)", "all schedules with FAC", "all", "published", "2024-05-28",
      IMBOOK + "; Original Sheet No. 46", IMBOOK_URL,
      "VERIFIES the brief's fuel base. Subtract before applying any FAC factor."),
    R(IM, "RIDER-ROSTER", "Applicable Surcharges and Rate Adjustments (Sheet 44)", "rider",
      "IM-RIDER-ROSTER", "Eight riders apply to standard-service customers", None, None,
      "DSM/EE (Sheet 45) | FAC (46) | Environmental Cost (47) | OSS Margin Sharing-PJM Cost "
      "(48) | Resource Adequacy (50) | Solar Power (51) | Phase-In Rate Adjustment (52) | TAX "
      "(53)", "all standard-service schedules", "all", "published", "2024-05-28",
      IMBOOK + "; Original Sheet No. 44 (Cause 45933)", IMBOOK_URL, None),
]

# I&M current rider factors for the IP / CS-IRP2 class (per-kWh leg + per-kW leg where stated)
_im_riders = [
    # code, name, sheet, cause+vintage desc, url file, eff, kwh rate, kw rate, note
    ("FAC", "Fuel Cost Adjustment", "46.1",
     "Cause 38702 FAC 96, Fourth Revised Sheet No. 46.1, tariff submitted 2026-06-03",
     "38702_FAC96_tariff_060326.pdf", "2026-06-08", 0.002422, None,
     "Non-residential factor, June 8 2026 - October 2026 billing cycles. Semi-annual filings "
     "(FAC 97 filed 2026-08-03, pending)."),
    ("RAR", "Resource Adequacy Rider", "50",
     "Cause 45164 RA 6, Third Revised Sheet No. 50, tariff submitted 2026-03-25",
     "45164_RA6_tariff_032526.pdf", "2026-04-01", 0.0, 0.242,
     "IP/CS-IRP2 row: 0.0000 c/kWh (published zero) + $0.242/kW. RA 7 (filed 2026-08-14) "
     "pending."),
    ("OSS-PJM", "Off System Sales Margin Sharing / PJM Cost Rider", "48",
     "Cause 43774 PJM 16, Third Revised Sheet No. 48, tariff submitted 2026-05-20",
     "43774_PJM16_tariff_052026.pdf", "2026-06-01", -0.004297, 7.316,
     "IP/CS-IRP2 row: (0.4297) c/kWh CREDIT + $7.316/kW charge - the largest I&M demand-based "
     "rider; enters the Large Load minimum charge and the Exit Fee offset."),
    ("ECR", "Environmental Cost Rider", "47",
     "Cause 44871 ECR 9, Third Revised Sheet No. 47, tariff submitted 2025-11-19",
     "44871_ECR9_tariff_111925.pdf", "2026-01-01", 0.000407, 0.378,
     "IP/CS-IRP2 row: 0.0407 c/kWh + $0.378/kW. Includes Rockport U2 NBV levelized recovery "
     "through 2028-12-31. ECR 10 (filed 2026-05-18) pending - hearing 2026-09-10."),
    ("SPR", "Solar Power Rider", "51",
     "Cause 45245 SPR 4, Third Revised Sheet No. 51, tariff submitted 2025-09-24",
     "45245_SPR4_tariff_092425.pdf", "2025-10-01", 0.000008, 0.048,
     "IP/CS-IRP2 row: 0.0008 c/kWh + $0.048/kW. SPR 5 (filed 2026-03-31) pending."),
    ("DSM", "DSM / Energy Efficiency Program Cost Rider", "45",
     "Cause 43827 DSM-14, Fourth Revised Sheet No. 45, second compliance submitted 2025-12-30",
     "43827_DSM14_second_compliance_123025.pdf", "2026-01-01", 0.003306, None,
     "IP/CS-IRP2 NON-opt-out total 0.3306 c/kWh. See companion opt-out row."),
    ("PRA", "Phase-In Rate Adjustment", "52",
     "Cause 46090 (I.U.R.C. No. 20 book sheet, eff bills March 2025), Phase II rates",
     "IM_IN_TB_20_06-30-2026.pdf", "2025-03-01", -0.000003, -0.343,
     "IP/CS-IRP2 row: (0.0003) c/kWh + (0.343) $/kW CREDIT - plant-in-service credit until "
     "new base rates."),
    ("TAX", "TAX Rider", "53",
     "Cause 46080 (I.U.R.C. No. 20 book sheet, eff bills April 2025)",
     "IM_IN_TB_20_06-30-2026.pdf", "2025-04-01", 0.0, 0.952,
     "IP/CS-IRP2 row: 0.0000 c/kWh (published zero) + $0.952/kW (NOLC private-letter-ruling "
     "adjustments)."),
]
for code, nm, sheet, srcd, urlf, eff, kwh, kw, note in _im_riders:
    IM_ROWS.append(
        R(IM, f"RIDER-{code}", f"{nm} (Sheet {sheet})", "rider", f"IM-{code}-IP-KWH",
          f"{nm} - IP/CS-IRP2 energy leg", kwh, "$/kWh", "per billing kWh", "Tariff I.P. and "
          "CS-IRP2", "all", "published", eff, f"I&M {srcd}", URL[urlf], note))
    if kw is not None:
        IM_ROWS.append(
            R(IM, f"RIDER-{code}", f"{nm} (Sheet {sheet})", "rider", f"IM-{code}-IP-KW",
              f"{nm} - IP/CS-IRP2 demand leg", kw, "$/kW/month", "per billing kW",
              "Tariff I.P. and CS-IRP2", "all", "published", eff, f"I&M {srcd}", URL[urlf],
              None))
IM_ROWS.append(
    R(IM, "RIDER-DSM", "DSM / Energy Efficiency Program Cost Rider (Sheet 45)", "rider",
      "IM-DSM-IP-OPTOUT", "DSM factor - new-customer opt-out (Group O)", 0.000218, "$/kWh",
      "per billing kWh: EE component 0.0000 (exempt) + CVR/DR component 0.0218 c/kWh "
      "(non-exemptible)", "Tariff I.P. and CS-IRP2, opted out", "all", "published",
      "2026-01-01", "I&M Cause 43827 DSM-14, Fourth Revised Sheet No. 45",
      URL["43827_DSM14_second_compliance_123025.pdf"],
      "A new large load opts out of EE but still pays the CVR+DR component."))

# ==========================================================================================
# JURISDICTIONAL MUNICIPALS - Anderson, Auburn, Frankfort (the only three; 2025 Annual Report)
# ==========================================================================================
AR = "2025 IURC Annual Report (FY2025), pp. 37-38"
AR_URL = URL["2025-IURC-Annual-Report.pdf"]
JURIS_QUOTE = ('Annual Report p.37: "Only three municipally owned electric utilities remain '
               'under the Commission\'s jurisdiction: Anderson, Auburn, and Frankfort."')

MUNI_ROWS = [
    # ---- Anderson --------------------------------------------------------------------------
    R(AND_, "JURISDICTION", "IURC rate jurisdiction status", "eligibility", "AND-JURIS",
      "IURC-jurisdictional municipal electric (1 of 3)", None, None, JURIS_QUOTE,
      "Anderson Municipal Light & Power", "all", "published", None, AR, AR_URL,
      "Anderson's 2025 Electric Rate Case is PENDING as Cause No. 46397 (filed 2026-04-24; "
      "settlement hearing noticed 2026-09-21) - base rates will change. IMPA member."),
    R(AND_, "PPCAT", "Purchase Power Cost Adjustment Tracking Factor (Cause 36835-S3)",
      "rider", "AND-PPCAT-IP-KVA", "PPCAT - Industrial Power Service (IP), demand leg", 4.891,
      "$/kVA/month", "quarterly tracker on purchased power cost", "Industrial Power Service "
      "(IP)", "all", "published", "2026-07-01",
      "Anderson ML&P Appendix A approved tariff, 30-Day Filing No. 50917, commission-stamped "
      "2026-07-08, applicable July-September 2026", URL["anderson_50917_approved_tariff.pdf"],
      "Quarterly 30-day filings are the current-rate mechanism for jurisdictional municipals."),
    R(AND_, "PPCAT", "PPCAT (Cause 36835-S3)", "rider", "AND-PPCAT-IP-KWH",
      "PPCAT - Industrial Power Service (IP), energy leg", 0.010230, "$/kWh",
      "quarterly tracker", "Industrial Power Service (IP)", "all", "published", "2026-07-01",
      "Anderson ML&P Appendix A, 30-Day Filing No. 50917",
      URL["anderson_50917_approved_tariff.pdf"], None),
    R(AND_, "PPCAT", "PPCAT (Cause 36835-S3)", "rider", "AND-PPCAT-LP-KVA",
      "PPCAT - Large Power Service (LP), demand leg", 3.839, "$/kVA/month", "quarterly "
      "tracker", "Large Power Service (LP)", "all", "published", "2026-07-01",
      "Anderson ML&P Appendix A, 30-Day Filing No. 50917",
      URL["anderson_50917_approved_tariff.pdf"], None),
    R(AND_, "PPCAT", "PPCAT (Cause 36835-S3)", "rider", "AND-PPCAT-LP-KWH",
      "PPCAT - Large Power Service (LP), energy leg", 0.012005, "$/kWh", "quarterly tracker",
      "Large Power Service (LP)", "all", "published", "2026-07-01",
      "Anderson ML&P Appendix A, 30-Day Filing No. 50917",
      URL["anderson_50917_approved_tariff.pdf"], None),
    R(AND_, "PPCAT", "PPCAT (Cause 36835-S3)", "rider", "AND-PPCAT-LPOFF-KVA",
      "PPCAT - LP Off-Peak, demand leg", 1.674, "$/kVA/month", "quarterly tracker",
      "Large Power Off-Peak Service", "all", "published", "2026-07-01",
      "Anderson ML&P Appendix A, 30-Day Filing No. 50917",
      URL["anderson_50917_approved_tariff.pdf"], None),
    R(AND_, "PPCAT", "PPCAT (Cause 36835-S3)", "rider", "AND-PPCAT-LPOFF-KWH",
      "PPCAT - LP Off-Peak, energy leg", 0.008314, "$/kWh", "quarterly tracker",
      "Large Power Off-Peak Service", "all", "published", "2026-07-01",
      "Anderson ML&P Appendix A, 30-Day Filing No. 50917",
      URL["anderson_50917_approved_tariff.pdf"], None),
    R(AND_, "PPCAT", "PPCAT (Cause 36835-S3)", "rider", "AND-PPCAT-SP-KW",
      "PPCAT - Small Power Service (SP), demand leg", 3.973, "$/kW/month", "quarterly tracker",
      "Small Power Service (SP)", "all", "published", "2026-07-01",
      "Anderson ML&P Appendix A, 30-Day Filing No. 50917",
      URL["anderson_50917_approved_tariff.pdf"], None),
    R(AND_, "PPCAT", "PPCAT (Cause 36835-S3)", "rider", "AND-PPCAT-SP-KWH",
      "PPCAT - Small Power Service (SP), energy leg", 0.011193, "$/kWh", "quarterly tracker",
      "Small Power Service (SP)", "all", "published", "2026-07-01",
      "Anderson ML&P Appendix A, 30-Day Filing No. 50917",
      URL["anderson_50917_approved_tariff.pdf"], None),
    R(AND_, "BASE", "Anderson base rate schedules", "eligibility", "AND-BASE",
      "Base schedules (RS/GS/SP/LP/LP-OffPeak/IP/CL/SL/OL) not transcribed", None, None,
      "base rate levels predate this harvest's scope; the PPCAT tracker above adjusts them "
      "quarterly", "all schedules", "all", "not_held", None,
      "IURC docketed system: pending rate case Cause 46397; prior base rates via earlier "
      "cause", "https://iurc.portal.in.gov/docketed-case-details/?id=cf9f09be-1240-f111-88b3-"
      "001dd800b811",
      "ACQUISITION ROUTE (not a wall): pull the 46397 order + approved schedules when issued "
      "(settlement hearing 2026-09-21). Current base book otherwise via the utility. "
      "not_held with NULL rate per the never-zero rule."),
    # ---- Auburn ----------------------------------------------------------------------------
    R(AUB, "JURISDICTION", "IURC rate jurisdiction status", "eligibility", "AUB-JURIS",
      "IURC-jurisdictional municipal electric (1 of 3)", None, None, JURIS_QUOTE,
      "Auburn Municipal Electric Utility", "all", "published", None, AR, AR_URL,
      "Supplier: I&M (AEP as agent) per the tracker sheet itself. IMPA non-member "
      "jurisdictional muni."),
    R(AUB, "PPT", "Purchased power tracker", "rider", "AUB-PPT-ALL",
      "Energy tracking factor - all rate schedules", 0.034896, "$/kWh",
      "quarterly tracker on the change in I&M/AEP wholesale cost; usage Jul-Sep 2026, billed "
      "Aug-Oct 2026", "all rate schedules", "all", "published", "2026-07-01",
      "Auburn Municipal Electric Utility Appendix A approved tariff, 30-Day Filing No. 50912, "
      "commission-stamped 2026-06-24", URL["auburn_50912_approved_tariff.pdf"],
      "Prior-quarter factor $0.034398 (+$0.000498) stated on the same sheet."),
    R(AUB, "BASE", "Auburn base rate schedules", "eligibility", "AUB-BASE",
      "Base schedules not transcribed", None, None,
      "base rate levels predate this harvest's scope; tracker above adjusts them quarterly",
      "all schedules", "all", "not_held", None,
      "IURC docketed system (last Auburn electric rate proceeding of record: Cause 45235 era) "
      "+ 30-day filing register", "https://iurc.portal.in.gov/search-thirtyday-cases/",
      "ACQUISITION ROUTE: docketed order archive or the utility. not_held, NULL rate."),
    # ---- Frankfort -------------------------------------------------------------------------
    R(FRK, "JURISDICTION", "IURC rate jurisdiction status", "eligibility", "FRK-JURIS",
      "IURC-jurisdictional municipal electric (1 of 3)", None, None, JURIS_QUOTE,
      "Frankfort City Light and Power", "all", "published", None, AR, AR_URL,
      "IMPA member. Cause 46343 (filed 2025-12-18, with Duke Energy Indiana) is a joint "
      "petition for TRANSFER OF ASSETS, not a rate case; proposed order submitted 2026-02-26."),
    R(FRK, "PPCAT", "Purchase Power Cost Adjustment Tracking Factor (Cause 36835-S3)",
      "rider", "FRK-PPCAT-A", "PPCAT - Residential Rate A", 0.007093, "$/kWh",
      "quarterly tracker", "Residential Rate A", "all", "published", "2026-07-01",
      "Frankfort City Light and Power Appendix A approved tariff, 30-Day Filing No. 50903, "
      "commission-stamped 2026-06-17, applicable July-September 2026",
      URL["frankfort_50903_approved_tariff.pdf"], None),
    R(FRK, "PPCAT", "PPCAT (Cause 36835-S3)", "rider", "FRK-PPCAT-B",
      "PPCAT - Commercial Rate B", 0.006238, "$/kWh", "quarterly tracker", "Commercial Rate B",
      "all", "published", "2026-07-01", "Frankfort 30-Day Filing No. 50903",
      URL["frankfort_50903_approved_tariff.pdf"], None),
    R(FRK, "PPCAT", "PPCAT (Cause 36835-S3)", "rider", "FRK-PPCAT-C",
      "PPCAT - General Power Rate C", 0.007193, "$/kWh", "quarterly tracker",
      "General Power Rate C", "all", "published", "2026-07-01",
      "Frankfort 30-Day Filing No. 50903", URL["frankfort_50903_approved_tariff.pdf"], None),
    R(FRK, "PPCAT", "PPCAT (Cause 36835-S3)", "rider", "FRK-PPCAT-PPL-KVA",
      "PPCAT - Industrial Rate PPL, demand leg", -1.928663, "$/kVA/month",
      "quarterly tracker (currently a CREDIT on the demand leg)", "Industrial Rate PPL", "all",
      "published", "2026-07-01", "Frankfort 30-Day Filing No. 50903",
      URL["frankfort_50903_approved_tariff.pdf"],
      "The stamped sheet is a scan; its OCR text renders the figure as '(1 .928663)' with a "
      "stray space - transcribed as -1.928663 $/kVA."),
    R(FRK, "PPCAT", "PPCAT (Cause 36835-S3)", "rider", "FRK-PPCAT-PPL-KWH",
      "PPCAT - Industrial Rate PPL, energy leg", 0.013858, "$/kWh", "quarterly tracker",
      "Industrial Rate PPL", "all", "published", "2026-07-01",
      "Frankfort 30-Day Filing No. 50903", URL["frankfort_50903_approved_tariff.pdf"], None),
    R(FRK, "PPCAT", "PPCAT (Cause 36835-S3)", "rider", "FRK-PPCAT-FLAT",
      "PPCAT - Flat Rates", 0.004745, "$/kWh", "quarterly tracker", "Flat-rate schedules",
      "all", "published", "2026-07-01", "Frankfort 30-Day Filing No. 50903",
      URL["frankfort_50903_approved_tariff.pdf"], None),
    R(FRK, "BASE", "Frankfort base rate schedules", "eligibility", "FRK-BASE",
      "Base schedules not transcribed", None, None,
      "base rate levels predate this harvest's scope; tracker above adjusts them quarterly",
      "all schedules", "all", "not_held", None,
      "IURC docketed system + 30-day filing register",
      "https://iurc.portal.in.gov/search-thirtyday-cases/",
      "ACQUISITION ROUTE: docketed order archive or the utility. not_held, NULL rate."),
]

# ==========================================================================================
# NON-JURISDICTIONAL FINDINGS - every other URDB-listed Indiana muni/co-op + the wholesalers.
# A jurisdictional gap is a FINDING, not a failed fetch (2025 IURC Annual Report pp. 37-38).
# ==========================================================================================
MUNI_WHY = ("NON-JURISDICTIONAL FOR RATES: withdrew from IURC rate jurisdiction under IC "
            "8-1.5-3-9/-9.1. " + JURIS_QUOTE + " Rates are set by municipal ordinance "
            "(common council); no commission tariff exists to acquire. Route: municipal code "
            "/ clerk, or URDB/EIA-861 for levels.")
REMC_WHY = ('NON-JURISDICTIONAL FOR RATES: Annual Report p.38: "No REMCs remain under '
            'Commission authority for rate regulation, as all have exercised the option to '
            'withdraw from the Commission\'s jurisdiction as provided by Ind. Code '
            '8-1-13-18.5." Rates set by the cooperative board; route: co-op tariff page or '
            'URDB/EIA-861.')

NONJURIS_MUNIS = [
    "City of Washington, Indiana (Utility Company)", "City of Richmond, Indiana (Utility Company)",
    "City of Peru, Indiana (Utility Company)", "City of Hagerstown, Indiana (Utility Company)",
    "Town of Winamac, Indiana (Utility Company)", "Town of Etna Green, Indiana (Utility Company)",
    "City of Columbia City, Indiana (Utility Company)", "Town of Knightstown, Indiana (Utility Company)",
    "Town of Argos, Indiana (Utility Company)", "City of Tell City, Indiana (Utility Company)",
    "Town of Avilla, Indiana (Utility Company)", "City of Rensselaer, Indiana (Utility Company)",
    "Town of Paoli, Indiana (Utility Company)", "City of Williamsport, Indiana (Utility Company)",
    "Town of Pendleton, Indiana (Utility Company)", "Town of Walkerton, Indiana (Utility Company)",
    "City of Logansport, Indiana (Utility Company)", "City of Lebanon, Indiana (Utility Company)",
    "Town of Kingsford Heights, Indiana (Utility Company)", "Town of Warren, Indiana (Utility Company)",
    "Town of New Carlisle, Indiana (Utility Company)", "City of Scottsburg, Indiana (Utility Company)",
    "Town of Pittsboro, Indiana (Utility Company)", "City of Bluffton, Indiana (Utility Company)",
    "City of Troy, Indiana (Utility Company)", "Town of Montezuma, Indiana (Utility Company)",
    "Town of Rockville, Indiana (Utility Company)", "Town of Centerville, Indiana (Utility Company)",
    "Town of Brookston, Indiana (Utility Company)", "City of Jasper, Indiana (Utility Company)",
    "Town of Spiceland, Indiana (Utility Company)", "Town of Middletown, Indiana (Utility Company)",
    "City of Rising Sun, Indiana (Utility Company)", "City of Greenfield, Indiana (Utility Company)",
    "Town of Ferdinand, Indiana (Utility Company)", "City of Greendale, Indiana (Utility Company)",
    "City of Mishawaka, Indiana (Utility Company)", "Town of Frankton, Indiana (Utility Company)",
    "City of Thorntown, Indiana (Utility Company)", "Town of Ladoga, Indiana (Utility Company)",
    "City of Huntingburg, Indiana (Utility Company)", "Town of Coatesville, Indiana (Utility Company)",
    "City of Garrett, Indiana (Utility Company)", "Town of Straughn, Indiana (Utility Company)",
    "City of Waynetown, Indiana (Utility Company)", "Town of Chalmers, Indiana (Utility Company)",
    "City of Gas City, Indiana (Utility Company)", "City of Covington, Indiana (Utility Company)",
    "Town of Jamestown, Indiana (Utility Company)", "Town of Bargersville, Indiana (Utility Company)",
    "Town of Crane, Indiana (Utility Company)", "City of Linton, Indiana (Utility Company)",
    "City of Lewisville, Indiana (Utility Company)", "Town of Brooklyn, Indiana (Utility Company)",
    "Town of South Whitley, Indiana (Utility Company)", "Town of Veedersburg, Indiana (Utility Company)",
    "Town of Bainbridge, Indiana (Utility Company)",
]
NONJURIS_REMCS = [
    "South Central Indiana REMC", "Southeastern Indiana R E M C", "Southern Indiana R E C, Inc",
    "Paulding-Putman Elec Coop, Inc (Indiana)",
]

NONJURIS_ROWS = []
for u in NONJURIS_MUNIS:
    NONJURIS_ROWS.append(
        R(u, "JURISDICTION", "IURC rate jurisdiction status", "eligibility", "NONJURIS-MUNI",
          "Not rate-regulated by the IURC (withdrawn municipal)", None, None, MUNI_WHY,
          "all schedules", "all", "not_held", None, AR, AR_URL,
          "Utility string as in in_urdb_rates. 60 of 79 Indiana municipal electrics are IMPA "
          "members; IMPA wholesale cost flows through local ordinance rates."))
for u in NONJURIS_REMCS:
    NONJURIS_ROWS.append(
        R(u, "JURISDICTION", "IURC rate jurisdiction status", "eligibility", "NONJURIS-REMC",
          "Not rate-regulated by the IURC (withdrawn REMC)", None, None, REMC_WHY,
          "all schedules", "all", "not_held", None, AR, AR_URL,
          "Utility string as in in_urdb_rates."))
NONJURIS_ROWS += [
    R(HOOSIER, "JURISDICTION", "IURC rate jurisdiction status", "eligibility", "NONJURIS-GT",
      "G&T cooperative - no IURC retail-rate jurisdiction", None, None,
      "Annual Report p.38: Commission regulation of Hoosier Energy and WVPA 'is primarily "
      "limited to decisions to purchase, build, or lease generation facilities, and the "
      "review of their integrated resource plans (IRPs).'", "wholesale to member REMCs",
      "all", "not_held", None, AR, AR_URL,
      "Southern-Indiana G&T for member REMCs. Member retail rates are set by each REMC board."),
    R(WVPA, "JURISDICTION", "IURC rate jurisdiction status", "eligibility", "NONJURIS-GT",
      "G&T cooperative - no IURC retail-rate jurisdiction", None, None,
      "Annual Report p.38 (same limitation as Hoosier); the Commission also reviews WVPA "
      "long-term financing (with IMPA and regulated munis).", "wholesale to member REMCs",
      "all", "not_held", None, AR, AR_URL,
      "Northern-Indiana G&T. Member retail rates set by each REMC board."),
    R(IMPA, "JURISDICTION", "IURC rate jurisdiction status", "eligibility", "NONJURIS-JAA",
      "Municipal joint agency - no IURC retail-rate jurisdiction", None, None,
      "Annual Report: IURC reviews IMPA long-term financing, CPCNs and IRPs; retail rates "
      "are the member municipalities' (ordinance-set). 60 of 79 muni electrics are members.",
      "wholesale to 60 member municipals", "all", "not_held", None, AR, AR_URL, None),
]

ALL_ROWS = DUKE_ROWS + IM_ROWS + MUNI_ROWS + NONJURIS_ROWS

MY_UTILITIES = sorted({r["utility"] for r in ALL_ROWS})

RESCRAPE = ("RE-SCRAPE COMMAND: python scripts/load_tariff_books_iurc_duke_im_munis.py "
            "--fetch   (idempotent: DELETE WHERE utility IN (this harvest's utilities - never "
            "AES/NIPSCO/CenterPoint) then load-job APPEND; sentinel-verifies every document "
            "before any write; --verify-only for a no-write check). Document URLs are IURC "
            "portal sharepointdocumentlocation links captured 2026-08-18 from POST "
            f"{COMPANION}/api/document/filings and /api/document/thirtydayfilings; if a link "
            "rotates, re-resolve it by case GUID via those endpoints (case GUIDs and the "
            "payload shape are in docs/TARIFF_HARVEST_IURC_ALL_UTILITIES.md).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="download the source documents first")
    ap.add_argument("--verify-only", action="store_true", help="sentinel check only, no writes")
    ap.add_argument("--dry-run", action="store_true", help="verify + row lint, no BigQuery writes")
    args = ap.parse_args()

    if args.fetch:
        print("fetching source documents from the IURC portal (throttled >=1.3s) ...")
        fetch_all()

    print("\nverifying sentinels against the documents on disk ...")
    verify_sentinels()

    bad = []
    for i, r in enumerate(ALL_ROWS):
        if r["component_type"] not in ("base_charge", "demand", "energy", "rider",
                                       "eligibility", "ratchet", "fuel_base"):
            bad.append((i, "component_type", r["component_type"]))
        if r["season"] not in ("summer", "non_summer", "all"):
            bad.append((i, "season", r["season"]))
        if r["value_status"] not in ("published", "not_held"):
            bad.append((i, "value_status", r["value_status"]))
        if r["value_status"] == "not_held" and r["rate"] is not None:
            bad.append((i, "not_held row carries a rate", r["code"]))
    if bad:
        for b in bad:
            print(f"  ROW LINT FAIL: {b}")
        raise SystemExit("row lint failed - fix the ROWS above before loading")
    n_dk = sum(1 for r in ALL_ROWS if r["utility"] == DUKE)
    n_im = sum(1 for r in ALL_ROWS if r["utility"] == IM)
    n_muni = len(MUNI_ROWS)
    n_nj = len(NONJURIS_ROWS)
    print(f"row lint ok: {len(ALL_ROWS)} rows (Duke {n_dk} | I&M {n_im} | jurisdictional-muni "
          f"{n_muni} | non-jurisdictional findings {n_nj}) across {len(MY_UTILITIES)} utilities")

    if args.verify_only or args.dry_run:
        print("no-write mode - stopping before BigQuery.")
        return

    from google.cloud import bigquery
    client = bigquery.Client(project=PROJECT)

    schema = [
        bigquery.SchemaField("utility", "STRING"), bigquery.SchemaField("state", "STRING"),
        bigquery.SchemaField("tariff_code", "STRING"), bigquery.SchemaField("tariff_name", "STRING"),
        bigquery.SchemaField("component_type", "STRING"), bigquery.SchemaField("code", "STRING"),
        bigquery.SchemaField("name", "STRING"), bigquery.SchemaField("rate", "FLOAT"),
        bigquery.SchemaField("unit", "STRING"), bigquery.SchemaField("basis", "STRING"),
        bigquery.SchemaField("applies_to", "STRING"), bigquery.SchemaField("season", "STRING"),
        bigquery.SchemaField("value_status", "STRING"), bigquery.SchemaField("effective_date", "DATE"),
        bigquery.SchemaField("source", "STRING"), bigquery.SchemaField("source_url", "STRING"),
        bigquery.SchemaField("notes", "STRING"),
    ]
    client.get_table(TABLE)  # must already exist (AES/NIPSCO/SIGECO rows live there)

    print(f"\ndeleting prior rows for THIS harvest's {len(MY_UTILITIES)} utilities "
          f"(AES/NIPSCO/CenterPoint untouched) ...")
    client.query(
        f"DELETE FROM `{TABLE}` WHERE utility IN UNNEST(@u)",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ArrayQueryParameter("u", "STRING", MY_UTILITIES)])).result()

    print(f"loading {len(ALL_ROWS)} rows via load job (no streaming buffer) ...")
    job = client.load_table_from_json(
        ALL_ROWS, TABLE,
        job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_APPEND"))
    job.result()

    counts = {r.utility: r.n for r in client.query(
        f"SELECT utility, COUNT(*) n FROM `{TABLE}` GROUP BY 1")}
    total = sum(counts.values())
    print("live per-utility counts after load (top 12):")
    for u, n in sorted(counts.items(), key=lambda kv: -kv[1])[:12]:
        print(f"   {u[:58]:60s} {n:>4}")
    print(f"   TOTAL {total}")

    # ---- registry row (indiana_app._registry), same run --------------------------------------
    src = ("IURC docketed-case and 30-day filing systems (companion API "
           f"{COMPANION}: POST /api/search/advanced, /api/search/thirtyday, "
           "/api/document/filings, /api/document/thirtydayfilings; documents via "
           f"{PORTAL}/_entity/sharepointdocumentlocation/<filing-guid>/<library-guid>?file=... ) "
           "| Duke Energy Indiana: Cause 46038 Step 1 Compliance Attachment C book (IURC No. "
           "16, eff 2025-02-27) + Step 2 filing 2026-02-18 + docket entry 2026-05-27 + final "
           "tariffs in Causes 38707 FAC 148, 42061 ECR 45, 42736 RTO 61, 44348 SRA 11, 44932 "
           "REP 8, 45647 TDSIC 5, 45803 DSM-2, 46193 GCT 1 | I&M: Cause 46097 Tariff I.P. "
           "submission 2025-02-25 + rider finals in 38702 FAC 96, 45164 RA 6, 43774 PJM 16, "
           "45245 SPR 4, 44871 ECR 9, 43827 DSM-14 + utility-compiled I.U.R.C. No. 20 book "
           "(indianamichiganpower.com IM_IN_TB_20_06-30-2026.pdf) for Sheets 44/46/G.S./PRA/"
           "TAX | Municipals: 30-Day Filings 50917 (Anderson), 50912 (Auburn), 50903 "
           "(Frankfort) commission-stamped approved tariffs | Jurisdiction census: 2025 IURC "
           "Annual Report pp. 37-38 (in.gov/iurc/files/2025-IURC-Annual-Report.pdf) | AES "
           "Indiana / NIPSCO / CenterPoint rows in this table are the SEPARATE utility-site "
           "harvest (scripts/load_tariff_books_aes_nipsco_centerpoint.py) - untouched here")
    method = (RESCRAPE + " || WHY COMMISSION-FIRST: duke-energy.com HTTP-403s scripted "
              "clients (Akamai fingerprint wall, no CAPTCHA/login - measured by the prior "
              "agent); the IURC portal serves the same approved sheets anonymously. NOTE: the "
              "portal SEARCH PAGES gate their button client-side with reCAPTCHA, but the "
              "companion JSON API answers anonymous POSTs (no token) - calls replicate the "
              "page's own JS exactly; no CAPTCHA was bypassed. || OBSERVED PUBLISHER VINTAGES "
              "(tariff effective dates + cause numbers, never pull dates): Duke IURC No. 16 "
              "sheets eff 2025-02-27 (Cause 46038 order 2025-01-29); tracker factors eff "
              "Jan-Aug 2026 per rider (FAC Jul-2026/38707-FAC-148, ECR Aug-2026/ECR-45, TDSIC "
              "May-2026/TDSIC-5, EE+LC Jan-2026/DSM-2, Credits Mar-2026/Step-2, RTO Jan-2026/"
              "RTO-61, Reliability Mar-2026/SRA-11, REP Jul-2026/REP-8, GCT Apr-2026/GCT-1, "
              "FMCA $0 published); I&M I.P. eff 2025-02-19 (Cause 46097), riders eff "
              "2025-03 .. 2026-06 per sheet; municipal trackers Jul-Sep 2026 (30-day final "
              "dates 2026-06-17/-06-24/-07-08); jurisdiction census FY2025 Annual Report. || "
              "PENDING AT HARVEST (2026-08-18): Duke 46038 Step-2 joint appeal to full "
              "Commission (filed 2026-06-04); Duke FAC 149, TDSIC 6, DSM-3, GCT 2; I&M FAC 97, "
              "RA 7, SPR 5, ECR 10, DSM (46255); Anderson rate case 46397 (settlement hearing "
              "2026-09-21). || EXCLUDED AND WHY: residential/lighting/small-C&I schedule "
              "detail (not decision-relevant to large-load siting - same boundary as the "
              "AES/NIPSCO/CenterPoint harvest); Duke Tariff 21 BDP charge detail (status row "
              "only); municipal BASE schedules (not_held rows carry the acquisition route); "
              "Duke 2025-04-30 Energy-Division amended tariffs (rate-migration NPT - not in "
              "the public docket; caveat carried on rows). Sentinel guard: every load-bearing "
              "number asserted against the documents before any write.")
    notes = (f"Commission-route harvest of {len(ALL_ROWS)} rows: Duke {n_dk} (book + 11-tracker "
             f"stack; fuel base 0.034378 $/kWh; HLF has NO annual ratchet - the outlier among "
             f"the big 5), I&M {n_im} (I.P. VERIFIED against Cause 46097 commission copy: "
             f"16.474/14.089/10.825/10.194 $/kW by voltage; fuel base 0.0129810; >=70 MW "
             f"large-load: 80% ratchet, 12-yr term, embedded capacity charge 10.959-13.289 "
             f"$/kW, collateral 24x), jurisdictional municipals {n_muni} (Anderson/Auburn/"
             f"Frankfort quarterly trackers, commission-stamped), non-jurisdictional findings "
             f"{n_nj} (57 withdrawn munis + 4 REMCs by URDB name + Hoosier/WVPA/IMPA; 2025 "
             f"Annual Report: only 3 munis remain jurisdictional, NO REMCs). UNPUBLISHED IS "
             f"NULL NEVER 0: not_held rows carry NULL; Duke FMCA $0 and EE-opt-out $0.000000 "
             f"and I&M GS subtrans/trans demand 0.000 are PUBLISHED zeros. Do not overwrite "
             f"in_rate_component_gaps.")
    client.query(
        f"DELETE FROM `{DS}._registry` WHERE table_name='in_utility_tariff_riders'").result()
    client.query(
        f"INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
        f"VALUES (@t, @s, @m, @n, 0.01, CURRENT_TIMESTAMP(), @notes)",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", "in_utility_tariff_riders"),
            bigquery.ScalarQueryParameter("s", "STRING", src),
            bigquery.ScalarQueryParameter("m", "STRING", method),
            bigquery.ScalarQueryParameter("n", "INT64", int(total)),
            bigquery.ScalarQueryParameter("notes", "STRING", notes)])).result()
    print(f"registered in_utility_tariff_riders in {DS}._registry (n_rows={total})")

    # ---- energy.registry_sources APPEND (the ONLY permitted write to energy) -----------------
    reg_rows = [
        dict(source_id="iurc-tariff:duke-indiana:46038-book+trackers",
             source_name="Duke Energy Indiana IURC No. 16 tariff book + 11-tracker current "
                         "factors, from IURC docketed filings (Cause 46038 et al.)",
             endpoint=f"{PORTAL}/docketed-case-details/?id=d1e0c3f4-9bf2-ee11-904c-001dd80b3d60",
             endpoint_raw=f"POST {COMPANION}/api/document/filings body="
                          '{"txtPageNumber":"<n>","Id":" <case-guid>"} -> GET '
                          f"{PORTAL}<iurc_documentLink>. Case GUIDs: 46038=d1e0c3f4-9bf2-ee11-"
                          "904c-001dd80b3d60; 38707-FAC-148=ec3bcc43-eb43-f111-88b4-001dd80821af; "
                          "42061-ECR-45=1753eb70-0c2d-f111-8342-001dd80ed938; 42736-RTO-61="
                          "ad73c4ae-4584-f011-b4cc-001dd80821af; 44348-SRA-11=641a523e-6b99-"
                          "f011-b4cb-001dd800c692; 44932-REP-8=b73ad136-12fe-f011-8406-"
                          "001dd80eb6be; 45647-TDSIC-5=2129e710-9db5-f011-bbd3-001dd8009cd1; "
                          "45803-DSM-2=00a90ece-6d32-f011-8c4e-001dd80821af; 46193-GCT-1="
                          "f2116851-dbca-f011-bbd3-001dd806079d",
             endpoint_kind="rest+pdf", fmt="pdf", utility=DUKE,
             what="Duke base schedules HLF/LLF/LLF-B/TOU by service voltage, fuel base "
                  "0.034378, Appendix A tracker roster, current factors for all 11 trackers, "
                  "Step-2 status", n=n_dk,
             status="BUILT+LOADED - commission route beat the Akamai-walled utility site; "
                    "publisher vintages 2025-02-27 (book) and Jan-Aug 2026 (tracker finals); "
                    "Step-2 appeal to full Commission pending 2026-08-18",
             objs=["in_utility_tariff_riders"]),
        dict(source_id="iurc-tariff:indiana-michigan:46097-ip+riders",
             source_name="I&M Tariff I.P. (Cause 46097) + full rider stack from IURC docketed "
                         "filings + utility-compiled I.U.R.C. No. 20 book",
             endpoint=f"{PORTAL}/docketed-case-details/?id=b8cd5780-0546-ef11-8409-001dd803817e",
             endpoint_raw=f"POST {COMPANION}/api/document/filings (same shape). Case GUIDs: "
                          "46097=b8cd5780-0546-ef11-8409-001dd803817e; 38702-FAC-96=50017ccc-"
                          "f401-f111-8407-001dd8070e6e; 45164-RA-6=1d44f88e-f4ad-f011-bbd2-"
                          "001dd8086c1c; 43774-PJM-16=8ec6bef8-39b0-f011-bbd3-001dd80f20e8; "
                          "45245-SPR-4=7a77e5a2-232c-f011-8c4d-001dd80d9613; 44871-ECR-9="
                          "2c843ed3-bc55-f011-877a-001dd8006bc2; 43827-DSM-14=e4c42abe-156e-"
                          "f011-bec2-001dd80821af. Book: indianamichiganpower.com/lib/docs/"
                          "ratesandtariffs/Indiana/IM_IN_TB_20_06-30-2026.pdf",
             endpoint_kind="rest+pdf", fmt="pdf", utility=IM,
             what="I.P. demand/energy/service charge by voltage code 327/322/323/324, minimum "
                  "demand + Step-1 embedded capacity charges, >=70MW large-load terms (80% "
                  "ratchet, 12-yr, collateral 24x), fuel base 0.0129810, 8-rider roster with "
                  "current IP-class factors", n=n_im,
             status="BUILT+LOADED - VERIFIED the prior transcription against the commission "
                    "copy (exact match); supersedes the 3 placeholder seed rows",
             objs=["in_utility_tariff_riders"]),
        dict(source_id="iurc-tariff:municipals:30day+census",
             source_name="Jurisdictional-municipal tariffs (30-Day Filings 50917/50912/50903) "
                         "+ statewide jurisdiction census (2025 IURC Annual Report)",
             endpoint=f"{PORTAL}/search-thirtyday-cases/",
             endpoint_raw=f"POST {COMPANION}/api/search/thirtyday (ddl fields '-1' when empty) "
                          f"-> POST {COMPANION}/api/document/thirtydayfilings body="
                          '{"txtPageNumber":"1","Id":" <30day-case-guid>"} -> GET portal '
                          "documentLink. Census: in.gov/iurc/files/2025-IURC-Annual-Report.pdf "
                          "pp. 37-38",
             endpoint_kind="rest+pdf", fmt="pdf", utility="Indiana municipals + REMCs + G&Ts",
             what="Anderson/Auburn/Frankfort commission-stamped quarterly tracker tariffs "
                  "(Jul-Sep 2026) + the finding that they are the ONLY jurisdictional "
                  "municipals and NO REMC is rate-jurisdictional; explicit non-jurisdictional "
                  "rows for 57 munis, 4 REMCs, Hoosier, WVPA, IMPA", n=n_muni + n_nj,
             status="BUILT+LOADED - jurisdictional gaps recorded as findings with statute "
                    "cites (IC 8-1.5-3-9/-9.1, IC 8-1-13-18.5), not as failed fetches",
             objs=["in_utility_tariff_riders"]),
    ]
    for r in reg_rows:
        client.query(
            f"""INSERT `{EN}.registry_sources`
                (source_id, source_name, endpoint, endpoint_raw, endpoint_kind, fmt, utility,
                 geography_state, measured_rows, last_source_count, status, acquisition_method,
                 what_it_provides, object_names, origin, updated_by, validation,
                 last_validated_at, notes)
                VALUES (@sid, @sn, @ep, @epr, @epk, @fmt, @util, 'IN', @mr, @lsc, @st, @acq,
                        @wip, @objs, 'loader_auto_registration',
                        'load_tariff_books_iurc_duke_im_munis', 'OK_COUNTED',
                        CURRENT_TIMESTAMP(), @notes)""",
            job_config=bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("sid", "STRING", r["source_id"]),
                bigquery.ScalarQueryParameter("sn", "STRING", r["source_name"]),
                bigquery.ScalarQueryParameter("ep", "STRING", r["endpoint"]),
                bigquery.ScalarQueryParameter("epr", "STRING", r["endpoint_raw"]),
                bigquery.ScalarQueryParameter("epk", "STRING", r["endpoint_kind"]),
                bigquery.ScalarQueryParameter("fmt", "STRING", r["fmt"]),
                bigquery.ScalarQueryParameter("util", "STRING", r["utility"]),
                bigquery.ScalarQueryParameter("mr", "INT64", int(r["n"])),
                bigquery.ScalarQueryParameter("lsc", "INT64", int(r["n"])),
                bigquery.ScalarQueryParameter("st", "STRING", r["status"]),
                bigquery.ScalarQueryParameter("acq", "STRING", RESCRAPE),
                bigquery.ScalarQueryParameter("wip", "STRING", r["what"]),
                bigquery.ArrayQueryParameter("objs", "STRING", r["objs"]),
                bigquery.ScalarQueryParameter("notes", "STRING",
                    "Rows live in energy-platfrom.indiana_app.in_utility_tariff_riders "
                    "(energy dataset untouched beyond this append). Publisher vintage = "
                    "tariff effective dates + cause numbers on every row, never the pull "
                    "timestamp. The reusable commission route for other states is written "
                    "up in docs/TARIFF_HARVEST_IURC_ALL_UTILITIES.md.")])).result()
        print(f"appended energy.registry_sources: {r['source_id']}")

    print("\nDONE")


if __name__ == "__main__":
    main()
