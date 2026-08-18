"""Ordinance/board-route tariff harvest: Indiana municipals, REMCs, and the G&T/joint-agency
wholesalers -> in_utility_tariff_riders.  Source: the utilities' OWN publications (rate pages,
ordinance PDFs, municipal codes, board-approved tariff books, FERC filings) - because for these
utilities NO commission tariff exists to acquire.

WHY THE ORDINANCE ROUTE (the point of this loader)
--------------------------------------------------
Per the IURC's FY2025 Annual Report (pp. 37-38): of 79 Indiana municipal electrics only
Anderson, Auburn and Frankfort remain rate-jurisdictional (IC 8-1.5-3-9/-9.1); NO REMC remains
under Commission rate authority (IC 8-1-13-18.5); Hoosier Energy, WVPA and IMPA carry no
retail-rate jurisdiction.  Their rates are set by city ordinance / council resolution and by
co-op boards, published on the utility's own site or in the municipal code.  This loader is the
records-location answer to that census: 64 rows in in_utility_tariff_riders already record each
utility as not_held with the statute cite - THIS run replaces the placeholders it can with the
publisher's own numbers and upgrades the rest from "not held" to "measured records-location".

SCOPE GUARD (hard rule)
-----------------------
The five investor-owned utilities are DONE by other loaders and are NEVER touched here:
  Duke Energy Indiana Inc | Indiana Michigan Power Co (Indiana) | Indianapolis Power & Light Co
  | Northern Indiana Pub Serv Co | Southern Indiana Gas & Elec Co
The DELETE below is scoped to (utility IN my-utilities AND code IN my-codes), so a re-run can
never touch an IOU row, a jurisdictional-muni TRACKER row (AND-PPCAT-*/AUB-PPT-*/FRK-PPCAT-*),
or a JURISDICTION finding row (NONJURIS-*/-JURIS) - those belong to
scripts/load_tariff_books_iurc_duke_im_munis.py.
RE-RUN ORDER: if load_tariff_books_iurc_duke_im_munis.py is ever re-run, re-run THIS loader
afterwards - its DELETE is utility-scoped and will remove this harvest's rows for the shared
utilities (all munis/REMCs/G&Ts), then reinstate its placeholders.

HAZARDS HONOURED
----------------
  * UNPUBLISHED IS NULL, NEVER 0.  A published $0.000000 is a zero; an absent number is
    value_status='not_held' with NULL rate.  Structure/status facts stated without a number
    load as 'published' with NULL rate and the clause in basis/notes (house convention).
  * Utility strings match in_urdb_rates exactly (including URDB's own misspelling
    "Paulding-Putman").  Crawfordsville has NO URDB rows; its string follows the same pattern
    and the rows say so.
  * energy dataset is READ-ONLY; the only write there is the APPEND to energy.registry_sources.
  * Publisher vintage on every row: ordinance/resolution number and its OWN effective date,
    never our download timestamp.

BOUNDARIES: anonymous read-only HTTP GET of public documents, identifying User-Agent, >=1.2 s
between requests to the same host, no accounts, no CAPTCHA interaction, no UA spoofing.  A
gated source is recorded BLOCKED with its wall quoted verbatim (see docs/
TARIFF_HARVEST_MUNIS_COOPS.md) - nothing is loaded from a walled source.  ASCII-only console.

USAGE
-----
    python scripts/load_tariff_books_munis_coops.py --fetch        # download sources then verify+load
    python scripts/load_tariff_books_munis_coops.py                # use files already on disk
    python scripts/load_tariff_books_munis_coops.py --verify-only  # sentinel check, NO writes
    python scripts/load_tariff_books_munis_coops.py --dry-run      # everything except BigQuery writes
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
import urllib.parse
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOKS = os.path.join(REPO, "scrapers", "tariff_books", "munis_coops")

PROJECT = "energy-platfrom"                     # intentional, permanent spelling
DS = f"{PROJECT}.indiana_app"
EN = f"{PROJECT}.energy"                        # READ-ONLY except registry_sources APPEND
TABLE = f"{DS}.in_utility_tariff_riders"

UA = ("DecennialGroup-DataAudit/1.0 (read-only public tariff documents; "
      "contact ahenderson@decennialgroup.com)")

# The five IOUs, protected by construction (assert below, never in MY_UTILITIES)
IOUS = ("Duke Energy Indiana Inc", "Indiana Michigan Power Co (Indiana)",
        "Indianapolis Power & Light Co", "Northern Indiana Pub Serv Co",
        "Southern Indiana Gas & Elec Co")

# utility strings EXACTLY as in in_urdb_rates / in_utility_tariff_riders
AND_ = "City of Anderson, Indiana (Utility Company)"
AUB = "City of Auburn, Indiana (Utility Company)"
FRK = "City of Frankfort, Indiana (Utility Company)"
RICH = "City of Richmond, Indiana (Utility Company)"
LOGA = "City of Logansport, Indiana (Utility Company)"
MISH = "City of Mishawaka, Indiana (Utility Company)"
PERU = "City of Peru, Indiana (Utility Company)"
JASP = "City of Jasper, Indiana (Utility Company)"
LEBN = "City of Lebanon, Indiana (Utility Company)"
CRAW = "City of Crawfordsville, Indiana (Utility Company)"   # NOT in URDB; string follows pattern
COLC = "City of Columbia City, Indiana (Utility Company)"
TELL = "City of Tell City, Indiana (Utility Company)"
SEI = "Southeastern Indiana R E M C"
SIP = "Southern Indiana R E C, Inc"
SCI = "South Central Indiana REMC"
PPEC = "Paulding-Putman Elec Coop, Inc (Indiana)"            # URDB's own spelling, kept
HOOSIER = "Hoosier Energy Rural Electric Cooperative, Inc."
WVPA = "Wabash Valley Power Association, Inc. (d/b/a Wabash Valley Power Alliance)"
IMPA = "Indiana Municipal Power Agency"

# ------------------------------------------------------------------------------------------
# Source documents: (subdir, filename, exact URL).  kind inferred from extension:
# .pdf -> must start %PDF, text via pymupdf; .html/.txt -> sentinel check on decoded bytes.
# url=None -> derived/disk-only artifact (OCR text, API extraction): not re-fetchable at a
# stable URL; --fetch leaves it alone and verification runs against the copy on disk.
# ------------------------------------------------------------------------------------------
IURC = "https://iurc.portal.in.gov/_entity/sharepointdocumentlocation/"
LIB = "/bb9c6bba-fd52-45ad-8e64-a444aef13c39?file="
FILES = [
    # -- Anderson (jurisdictional; 30-day 50507 = Ordinance 9-22, approved 2022-06-08) ------
    ("anderson", "30day_50507_approved_tariff_20220608.pdf",
     IURC + "92e89349-4be7-ec11-bb3b-001dd8030bb1" + LIB + "50507%20-%20Tariff.pdf"),
    ("anderson", "46397_PENDING_petition_20260424.pdf",
     IURC + "12bd2cf2-1340-f111-88b3-001dd800b811" + LIB +
     "AMPL%20IURC%20Petition%20-%204-24-2026%20As-Filed%20(3).pdf"),
    ("anderson", "46397_PENDING_beauchamp_direct_MCB1-3_20260424.pdf", None),
    # -- Auburn (jurisdictional; 50523 = Rate Ordinance 2022-08, approved 2022-06-28) --------
    ("auburn", "30day_50523_approved_tariff_20220628.pdf",
     IURC + "0b7f376f-55f9-ec11-bb3b-001dd80097b5" + LIB + "50523%20-%20Tariff.pdf"),
    ("auburn", "45102_compliance_20181107.pdf",
     IURC + "1b9898be-aae2-e811-8146-1458d04e2938" + LIB +
     "45102%20City%20of%20Auburn%20Submission%20of%20Compliance%20Filing%20110718.pdf"),
    # -- Frankfort (jurisdictional; 50549 sheets eff 2022-07-01) -----------------------------
    ("frankfort", "30day_50549_tariff.pdf",
     IURC + "2cdfc9cc-b5f7-ec11-bb3b-001dd80095d7" + LIB + "50549+-+Tariff.pdf"),
    # -- Richmond (withdrew Nov 2022; book = 50559/Ord 26-2022, Phase 3 current) -------------
    ("richmond", "rpl_full_compliance_tariff_eff_2022-07-01.pdf",
     "https://www.rp-l.com/wp-content/uploads/2023/03/"
     "06032022-Richmond-Full-Compliance-Tariff-WITH-URT-removed1-compressed.pdf"),
    ("richmond", "rpl_full_compliance_tariff_eff_2022-07-01.OCR.txt", None),
    ("richmond", "rpl_eca_2026q3_legal_ad.pdf",
     "https://www.rp-l.com/wp-content/uploads/2026/06/rpl-3rd-qtr-2026-eca-legal-ad.pdf"),
    # -- Logansport (withdrew 2012-01-07; Ordinance 2025-02 + LMU Rate Guide 2025-2029) ------
    ("logansport", "lmu_rate_guide.pdf",
     "https://drive.google.com/uc?export=download&id=1cFSwzxs-1Cmvoi-6i_oA8v6U-g7JTPKE"),
    ("logansport", "ordinance_2025-02_electric_rates.pdf",
     "https://www.in.gov/cities/logansport/files/ordinances/2025/ORDINANCE-2025-02-APPROVING"
     "-A-CHANGE-IN-RATES-AND-CHARGES-OF-THE-LOGANSPORT-ELECTRIC-UTILITY.pdf"),
    ("logansport", "ordinance_2025-02_electric_rates.OCR.txt", None),
    # -- Mishawaka (HTML tariff pages; 2025 step posted, Ord 5954 2026 step NOT posted) ------
    ("mishawaka", "mishawaka_rate_I_industrial.html",
     "https://mishawaka.in.gov/government/departments/mishawaka-utilities/rates-and-charges/"
     "rate-i-industrial-power-service/"),
    ("mishawaka", "mishawaka_rates_index.html",
     "https://mishawaka.in.gov/government/departments/mishawaka-utilities/rates-and-charges"),
    # -- Peru (HTML tariff, eff 2026-06-01, + 36835-S3 tracker notice) -----------------------
    ("peru", "peru_electric_rates_page.html",
     "https://www.peruutilities.com/rates/electric-rates/"),
    # -- Jasper (Municode ch. 11.08/11.09 extraction; Ord 2022-8 figures) --------------------
    ("jasper", "jasper_municode_ch11.08_11.09_electric_rates.txt", None),
    # -- Lebanon (rates page HTML + Q3-2026 tracker; Ord 2022-21 recitals for lineage) -------
    ("lebanon", "lebanon_utilities_rates_page_20260818.html",
     "https://lebanon-utilities.com/rates/"),
    ("lebanon", "lebanon_2026_3rd_quarter_tracker.pdf",
     "https://lebanon-utilities.com/wp-content/uploads/2026/07/"
     "2026-Lebanon-3rd-Quarter-Tracker-Copy.pdf"),
    ("lebanon", "lebanon_ord_2022-21_nonrecurring_electric.pdf", None),
    # -- Crawfordsville CEL&P (compiled book 50561+50602; PENDING 2026 ordinance) ------------
    ("crawfordsville", "celp_tariff_with_ev_fast_charge_jan2025.pdf",
     "https://celp.com/wp-content/uploads/2025/01/"
     "50561-Tariff-With-EV-Fast-Charge-50602-Updated-Logo-Jan-2025.pdf"),
    ("crawfordsville", "celp_rate_hearing_legal_notice_july2026.pdf",
     "https://celp.com/wp-content/uploads/2026/07/"
     "2472_CELP_Hearing-Utility-Rates-and-Charges-Legal-Notice-July-2026.pdf"),
    # -- Columbia City (Ord 2026-5 image scan, visually transcribed; 2021 book for terms) ----
    ("columbia_city", "cc_ordinance_2026-5_electric_rates.pdf",
     "https://columbiacity.net/wp-content/uploads/2026/05/Ordinance-2026-5-Electric-Rates.pdf"),
    ("columbia_city", "cc_electric_tariff_2020_rates_phase_i.pdf", None),
    # -- Tell City (2022 booklet text-native + Q3-2026 tracker image, visually transcribed) --
    ("tell_city", "tell_city_2022_revised_rates_and_charges_booklet.pdf",
     "https://www.tellcityelectric.com/uploads/1/1/7/4/117410786/"
     "2022_revised_rates_and_charges_booklet_-_final.pdf"),
    ("tell_city", "tell_city_2026_3rd_qtr_tracker.pdf",
     "https://www.tellcityelectric.com/uploads/1/1/7/4/117410786/2026_3rd_qtr_tracker.pdf"),
    # -- Southeastern Indiana REMC (board sheets eff 2025-10-01 / 2025-10-20 + PCT) ----------
    ("sei_remc", "UIPS-1_Unbundled_Large_Industrial_Power_Service.pdf",
     "https://www.seiremc.com/_files/ugd/680e74_041149040c3d48fe927e3856745c3e2f.pdf"),
    ("sei_remc", "CPS-1_Commercial_Power_Service.pdf", None),
    ("sei_remc", "IPS-1_Industrial_Power_Service.pdf",
     "https://www.seiremc.com/_files/ugd/680e74_47026f1c629c49a4bacadeb01c636db1.pdf"),
    ("sei_remc", "IP-1_Industrial_Power_Service.pdf", None),
    ("sei_remc", "C-5_Large_Power_High_Load_Factor.pdf",
     "https://www.seiremc.com/_files/ugd/680e74_ad50c8468a59434faf370df1c274357c.pdf"),
    ("sei_remc", "C-5_Large_Power_Low_Load_Factor.pdf", None),
    ("sei_remc", "PCT_Q3_2026.pdf",
     "https://www.seiremc.com/_files/ugd/680e74_0018aa6c9d8d4e6ea282774401ae6d73.pdf"),
    # -- Southern Indiana Power (only residential published; C&I = records-location) ---------
    ("southern_indiana_power", "rates_charges_page.html",
     "https://www.southernindianapower.com/my-account/rates-charges/"),
    # -- South Central Indiana REMC (board sheets eff 2024-02-01) ----------------------------
    ("sci_remc", "Rate-33_IP_2024.pdf",
     "https://www.sciremc.com/wp-content/uploads/Rate-33-Rate-Schedule-IP-2024.pdf"),
    ("sci_remc", "Rate-34_LI_2024.pdf",
     "https://www.sciremc.com/wp-content/uploads/Rate-34-Rate-Schedule-LI-2024.pdf"),
    ("sci_remc", "Rate-39_LP_2024.pdf",
     "https://www.sciremc.com/wp-content/uploads/Rate-39-Rate-Schedule-LP-2024.pdf"),
    ("sci_remc", "Appendix_A_Purchased_Power_Tracker.pdf",
     "https://www.sciremc.com/wp-content/uploads/Appendix_A-1.pdf"),
    # -- Paulding-Putnam (2026.02 book; live URL dead post-migration; Wayback capture) -------
    ("paulding_putnam", "PPEC_Rate_Schedules_2026.02.pdf",
     "https://web.archive.org/web/20260515080132/https://ppec.coop/sites/default/files/"
     "PAULDING-PUTNAM%20ELECTRIC%20COOPERATIVE%20RATE%20SCHEDULES%202026.02.pdf"),
    ("paulding_putnam", "data_centers_page.html", None),
    # -- Hoosier Energy (jurisdiction + structure evidence) ----------------------------------
    ("hoosier", "FERC_171_61143_MISO_nonpublic_utility_order_2020.pdf",
     "https://www.ferc.gov/sites/default/files/2020-06/E-5-052120.pdf"),
    ("hoosier", "Hoosier_2023_IRP_Volume1_filed_040124.pdf",
     "https://www.in.gov/iurc/files/HoosierEnergy_IntegratedResourcePlan-Volume1-040124.pdf"),
    ("hoosier", "our_members_page.html", "https://www.hoosierenergy.com/our-members/"),
    ("hoosier", "data_centers_annual_meeting_2026-05-12.html", None),
    # -- WVPA ---------------------------------------------------------------------------------
    ("wvpa", "WVPA_2025_Audited_Financial_Statements.pdf",
     "https://www.wvpa.com/wp-content/uploads/2026/04/2025-Audited-Financial-Statements.pdf"),
    ("wvpa", "rate_options_page.html", "https://www.wvpa.com/for-site-selectors/rate-options/"),
    ("wvpa", "member_coops_page.html", "https://www.wvpa.com/who-we-are/member-co-ops/"),
    # -- IMPA ---------------------------------------------------------------------------------
    ("impa", "IMPA_2025_Year_End_Financials.pdf",
     "https://www.impa.com/wp-content/uploads/2025-Year-End-Financials-FINAL.pdf"),
    ("impa", "IMPA_2025_Annual_Report.pdf",
     "https://www.impa.com/wp-content/uploads/IMPA-REPORT-2025-web.pdf"),
]

# Image-only scans (no text layer): transcription was HUMAN-VISUAL from page renders
# (2026-08-18); the loader pins their SHA256 so a silently revised file fails the run
# instead of carrying stale numbers.  A hash mismatch means RE-READ the pages.
IMG_SHA256 = {
    "cc_ordinance_2026-5_electric_rates.pdf":
        "dfc5e035187ea8af75c6aa13547f3b9ea3a5d89d57218b831141d6b75c6672aa",
    "tell_city_2026_3rd_qtr_tracker.pdf":
        "4a6d2efd0cab27197eceda6247611da67cb329d525bbbfb9dc3cbc0c02e2aa40",
    "rpl_full_compliance_tariff_eff_2022-07-01.pdf":
        "fcc62b23d2019d5693be8c462d5b1d34c2e6c1b56ccbe3f4dfe042df71a490e4",
    "ordinance_2025-02_electric_rates.pdf":
        "5b5268ed5a380e690a0f7b3f1762721fb584af978bf1b68299adae7d68e95e89",
}

SENTINELS = {
    # Anderson: approved Ordinance 9-22 sheet values (all verified against the stamped copy)
    "30day_50507_approved_tariff_20220608.pdf": [
        "50507", "ORDINANCE 9-22", "$0.102243", "13.31", "31.55", "12.443", "49.30",
        "17.038", "98.60", "0.296", "49.95%", "$ 172.55", "2.958", "16.624", "$0.033524",
        "$0.034510", "10,000 kVA", "2.407", "34.5 kV", "0.061102", "36835-S3",
    ],
    "46397_PENDING_petition_20260424.pdf": ["46397", "12.58%"],
    "46397_PENDING_beauchamp_direct_MCB1-3_20260424.pdf":
        ["16.872", "0.03213", "$28.44", "12.58%"],
    # Auburn: 50523 approved values + 45102 structure
    "30day_50523_approved_tariff_20220628.pdf": [
        "50523", "17.10", "345.10", "0.031084", "246.50", "0.031855", "0.031246",
        "69.02", "0.047192", "0.047713", "59.16", "0.045892", "0.042833", "29.58",
        "0.046483", "6.90", "0.070306",
    ],
    "45102_compliance_20181107.pdf": [
        "30,000 kVA", "25,000 KVA", "5,000 KVA", "60%", "1.2 times", "1,500 kVA",
        "6,000 kVA", "200 kVA",
    ],
    # Frankfort 50549 sheets
    "30day_50549_tariff.pdf": [
        "50549", "JULY 1, 2022", "114.79", "591.48", "24.054", "0.028275", "18.137",
        "0.039978", "$0.34 per KVA", "ten (10) MVA", "5,000 kilovolt amperes", "7.89",
        "0.097615", "29.57", "0.096676", "25 kilovolt-amperes",
    ],
    # Richmond: image book (sha-pinned) + OCR artifact + text-native ECA ad
    "rpl_full_compliance_tariff_eff_2022-07-01.OCR.txt": [
        "50559", "36835-S3", "Transmission Service (TS)", "Industrial Service",
    ],
    "rpl_eca_2026q3_legal_ad.pdf": [
        "0.853292", "0.015869", "1.059137", "0.015862", "0.013826", "July 2026",
    ],
    # Logansport: born-digital rate guide (2026 column loaded) + ordinance OCR
    "lmu_rate_guide.pdf": [
        "Large Power", "Large Industrial", "Industrial Substation", "14.183", "0.049812",
        "0.048741", "0.047522", "17.686", "0.041727", "14.592", "0.045442", "32,500.00",
        "250.00", "86.00", "0.105500",
    ],
    "ordinance_2025-02_electric_rates.OCR.txt": [
        "2025-02", "NextEra", "0.03915", "2028", "Logansport Solar",
    ],
    # Mishawaka HTML pages (2025 step; Ord 5954 2026 step not posted)
    "mishawaka_rate_I_industrial.html": [
        "149", "18.35", "7.00", "6.25", "0.0769", "0.98", "0.39", "January 01, 2025",
    ],
    "mishawaka_rates_index.html": ["5954", "January 1, 2026"],
    # Peru HTML tariff (eff 2026-06-01)
    "peru_electric_rates_page.html": [
        "6.44", "7.11", "0.095074", "0.101105", "355.81", "50 kilowatts",
        "0.25 per kilowatt", "6,000 kilowatts", "0.06072", "June 1, 2026", "36835-S3",
        "0.001178", "1,000 kW", "1,500 kW",
    ],
    # Jasper Municode extraction
    "jasper_municode_ch11.08_11.09_electric_rates.txt": [
        "16.04", "4.5599", "89.61", "60 percent", "50 kVA", "9.3229", "10.67", "9.6926",
        "20.36", "2022-8", "2042", "tracking",
    ],
    # Lebanon
    "lebanon_utilities_rates_page_20260818.html": [
        "98.51", "17.38", "0.0358", "0.0310", "fifty (50) KVA", "7.88", "0.0952",
    ],
    "lebanon_2026_3rd_quarter_tracker.pdf": ["2.829798", "0.010946", "ILP", "(IMPA)"],
    "lebanon_ord_2022-21_nonrecurring_electric.pdf": ["50535", "44142", "2022-21"],
    # Crawfordsville compiled book + pending notice
    "celp_tariff_with_ev_fast_charge_jan2025.pdf": [
        "50561", "45420", "JULY 1, 2022", "295.77", "29.29", "0.027624", "591.62",
        "22.77", "0.026489", "138kV", "50%", "0.30 per KVA", "44.37", "88.73", "6.41",
        "0.071389", "14.79", "0.101720", "30,000",
    ],
    "celp_rate_hearing_legal_notice_july2026.pdf": ["2026"],
    # Columbia City: 2026-5 is image-only (sha-pinned, visually transcribed);
    # the 2021 book carries the class terms in text
    "cc_electric_tariff_2020_rates_phase_i.pdf": [
        "100 KW", "800 KW", "sixty percent (60%)", "General Service",
    ],
    # Tell City booklet (text) + tracker (image, sha-pinned)
    "tell_city_2022_revised_rates_and_charges_booklet.pdf": [
        "R220615A", "1190", "350.00", "26.45", "0.03757", "1,000.00", "3.00",
        "10,000 kVA", "97%", "36836-S3", "$0.12407", "11.04",
        "Indiana Municipal Power Agency",
    ],
    # SEI REMC
    "UIPS-1_Unbundled_Large_Industrial_Power_Service.pdf": [
        "5,000 kW", "$10.65", "$  9.50", "$  6.50", "$  3.35", "0.08015", "0.06515",
        "125.00", "October 20, 2025", "Standard Wholesale Tariff", "75 percent",
        "$0.01099", "$.18 per kW", "$0.93 per kVA",
    ],
    "CPS-1_Commercial_Power_Service.pdf": [
        "1,000 kW", "17.50", "13.10", "6.50", "0.08350", "0.06850", "October 20, 2025",
    ],
    "IPS-1_Industrial_Power_Service.pdf": [
        "1,000 kw", "$14.50", "0.08365", "0.06865", "October 1, 2025", "75 percent",
    ],
    "IP-1_Industrial_Power_Service.pdf": [
        "500 kW", "$15.00", "0.08800", "0.07300", "October 1, 2025", "preceding 11 months",
    ],
    "C-5_Large_Power_High_Load_Factor.pdf": [
        "75 kVA", "4000", "$15.50", "$13.50", "0.08350", "300 kWh/kW", "October 1, 2025",
    ],
    "C-5_Large_Power_Low_Load_Factor.pdf": [
        "$8.10", "$7.10", "0.10600", "0.09100", "0.10300", "October 1, 2025",
    ],
    "PCT_Q3_2026.pdf": ["0.00249", "0.00263", "May 18, 2026"],
    # Southern Indiana Power page (records-location + residential headline)
    "rates_charges_page.html": ["0.1214", "35.00", "0.00260"],
    # SCI REMC
    "Rate-33_IP_2024.pdf": [
        "500 KW", "394.40", ".06425", ".04904", "11.56", "11.81", "75%", "Hoosier Energy",
        "FEBRUARY 1, 2024", ".01009",
    ],
    "Rate-34_LI_2024.pdf": ["1,000", "394.40", ".05411", "7.42", "13.40", "1.75"],
    "Rate-39_LP_2024.pdf": ["300", "93.81", ".05411", "9.64", "13.03"],
    "Appendix_A_Purchased_Power_Tracker.pdf": ["0.0923", "F = A/B"],
    # PPEC book (2026.02) + data-centre page
    "PPEC_Rate_Schedules_2026.02.pdf": [
        "LPI", "$130.00", "$11.00", "0.10100", "0.08200", "0.05450", "90%",
        "Feb. 1, 2026", "$200.00", "$23.50", "0.05000", "$7.50", "0.09400", "0.06958",
    ],
    "data_centers_page.html": ["Buckeye Power", "March 2026", "data center"],
    # Hoosier
    "FERC_171_61143_MISO_nonpublic_utility_order_2020.pdf": [
        "Hoosier Energy Rural Electric Cooperative", "201(f)",
    ],
    "Hoosier_2023_IRP_Volume1_filed_040124.pdf": ["0.03705", "G&T"],
    "our_members_page.html": [
        "South Central Indiana REMC", "Southeastern Indiana REMC", "Southern Indiana Power",
    ],
    "data_centers_annual_meeting_2026-05-12.html": [
        "Consumer Directed Resource", "pay all costs",
    ],
    # WVPA
    "WVPA_2025_Audited_Financial_Statements.pdf": [
        "withdraw from FERC jurisdiction as of January 1, 2025", "Formula Rate Tariff",
        "December 2060", "21 rural electric membership corporations",
    ],
    "rate_options_page.html": ["Three-Year", "1,500", "34,999", "35,000", "61%"],
    "member_coops_page.html": ["Hendricks Power", "Carroll White", "Jasper County"],
    # IMPA
    # NOTE: the sentence 'Rates are not subject to state or federal regulation.' IS in
    # this PDF but the raw text layer line-breaks it after 'subject' - sentinel it in two
    # pieces that do not span the break.
    "IMPA_2025_Year_End_Financials.pdf": [
        "Rates are not subject", "to state or federal regulation", "110%", "budget rates",
    ],
    "IMPA_2025_Annual_Report.pdf": ["8.45 cents", "2.7%", "61 member"],
}


def fetch_all():
    last_host = {}
    for sub, fname, url in FILES:
        if url is None:
            print(f"  disk-only artifact (not re-fetchable): {fname}")
            continue
        d = os.path.join(BOOKS, sub) if sub else BOOKS
        os.makedirs(d, exist_ok=True)
        dest = os.path.join(d, fname)
        host = urllib.parse.urlparse(url).netloc
        wait = 1.2 - (time.time() - last_host.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=300) as r:
            blob = r.read()
        last_host[host] = time.time()
        if fname.lower().endswith(".pdf") and not blob.startswith(b"%PDF"):
            raise SystemExit(f"NOT A PDF: {fname} from {url[:120]} - first bytes {blob[:60]!r}")
        if fname in IMG_SHA256:
            import hashlib
            got = hashlib.sha256(blob).hexdigest()
            if got != IMG_SHA256[fname]:
                raise SystemExit(
                    f"IMAGE-SCAN REVISED AT SOURCE: {fname} sha256 {got} != pinned "
                    f"{IMG_SHA256[fname]}. The human-visual transcription below no longer "
                    f"matches the publisher's file - RE-READ the pages before loading.")
        with open(dest, "wb") as fh:
            fh.write(blob)
        print(f"  fetched {fname}: {len(blob):,} bytes")


def _file_text(path):
    if path.lower().endswith(".pdf"):
        import pymupdf
        return "".join(page.get_text() for page in pymupdf.open(path))
    with open(path, "rb") as fh:
        blob = fh.read()
    try:
        return blob.decode("utf-8", errors="replace")
    except Exception:
        return blob.decode("latin-1", errors="replace")


def verify_sentinels():
    import hashlib
    bad = 0
    for sub, fname, _url in FILES:
        p = os.path.join(BOOKS, sub, fname) if sub else os.path.join(BOOKS, fname)
        if not os.path.exists(p):
            print(f"  MISSING FILE: {p}  (run with --fetch)")
            bad += 1
            continue
        if fname in IMG_SHA256:
            got = hashlib.sha256(open(p, "rb").read()).hexdigest()
            if got != IMG_SHA256[fname]:
                bad += 1
                print(f"  SHA256 FAIL {fname}: {got} != pinned {IMG_SHA256[fname]}")
            else:
                print(f"  ok {fname} (image-only scan: sha256 pinned; numbers were "
                      f"transcribed by human-visual read of page renders 2026-08-18)")
            continue
        text = _file_text(p)
        missing = [s for s in SENTINELS.get(fname, []) if s not in text]
        if missing:
            bad += 1
            print(f"  SENTINEL FAIL {fname}: missing {missing}")
        else:
            print(f"  ok {fname} ({len(SENTINELS.get(fname, []))} sentinels)")
    if bad:
        raise SystemExit(
            f"\n{bad} file(s) failed sentinel verification. A publisher revised a document at "
            f"the same URL (or a link rotated). RE-READ the changed sheets and update the ROWS "
            f"below before loading - do NOT load transcriptions that no longer match their "
            f"source.")


# ------------------------------------------------------------------------------------------
# THE ROWS.  Transcribed by hand from the publisher documents cited on every row.
# Column semantics follow docs/TARIFF_SCRAPE_TARGETS.md OUTPUT SHAPE.
# ------------------------------------------------------------------------------------------
def R(utility, tariff_code, tariff_name, component_type, code, name, rate, unit, basis,
      applies_to, season, value_status, effective_date, source, source_url, notes):
    return dict(utility=utility, state="IN", tariff_code=tariff_code, tariff_name=tariff_name,
                component_type=component_type, code=code, name=name, rate=rate, unit=unit,
                basis=basis, applies_to=applies_to, season=season, value_status=value_status,
                effective_date=effective_date, source=source, source_url=source_url, notes=notes)


URL = {fname: url for _sub, fname, url in FILES}

# ==========================================================================================
# ANDERSON - base book = Ordinance 9-22 Exhibit A, IURC 30-Day Filing 50507 (approved by
# conference 2022-06-08; bills rendered from the July 2022 cycle).  Rate lineage: Cause
# 43411 (2008) -> Cause 44308 order 2014-03-26 (created IP + ISTP) -> Ord 9-22 URT decrease.
# ==========================================================================================
AND_SRC = ("Anderson Ordinance 9-22 Exhibit A = IURC 30-Day Filing No. 50507 approved tariff "
           "(commission conference 2022-06-08; HEA-1002 URT-repeal decrease of 1.4%); base "
           "schedule design per Cause 44308 order 2014-03-26")
AND_URL = URL["30day_50507_approved_tariff_20220608.pdf"]
E_AND = "2022-07-01"
AND_PENDING = ("PENDING CHANGE - Cause 46397 (filed 2026-04-24) proposes +12.58% system "
               "average; settlement hearing noticed 2026-09-21. Rates here are what is "
               "effective NOW; re-pull after the 46397 order.")

ANDERSON_ROWS = [
    R(AND_, "RS", "Residential Service", "base_charge", "AND-RS-CUST", "Customer charge",
      9.86, "$/month", "per meter per month", "residential single phase", "all", "published",
      E_AND, AND_SRC, AND_URL, None),
    R(AND_, "RS", "Residential Service", "energy", "AND-RS-EN-B1",
      "Energy charge - first 500 kWh", 0.102243, "$/kWh", "first 500 kWh per month",
      "residential", "all", "published", E_AND, AND_SRC, AND_URL, AND_PENDING),
    R(AND_, "RS", "Residential Service", "energy", "AND-RS-EN-B2",
      "Energy charge - over 500 kWh", 0.083090, "$/kWh", "all kWh above 500 per month",
      "residential", "all", "published", E_AND, AND_SRC, AND_URL, None),
    R(AND_, "GS", "General Service", "base_charge", "AND-GS-CUST-1PH",
      "Customer charge - single phase", 13.31, "$/month", "per meter per month",
      "single phase 120-480 V", "all", "published", E_AND, AND_SRC, AND_URL, None),
    R(AND_, "GS", "General Service", "energy", "AND-GS-EN-1PH-B1",
      "Energy charge single phase - first 1,000 kWh", 0.099793, "$/kWh",
      "first 1,000 kWh per month", "single phase", "all", "published", E_AND, AND_SRC,
      AND_URL, None),
    R(AND_, "GS", "General Service", "energy", "AND-GS-EN-1PH-B2",
      "Energy charge single phase - over 1,000 kWh", 0.085112, "$/kWh",
      "all kWh above 1,000 per month", "single phase", "all", "published", E_AND, AND_SRC,
      AND_URL, None),
    R(AND_, "GS", "General Service", "base_charge", "AND-GS-CUST-3PH",
      "Customer charge - three phase", 31.55, "$/month", "per meter per month",
      "three phase 120-480 V", "all", "published", E_AND, AND_SRC, AND_URL, None),
    R(AND_, "GS", "General Service", "energy", "AND-GS-EN-3PH-B1",
      "Energy charge three phase - first 2,000 kWh", 0.104851, "$/kWh",
      "first 2,000 kWh per month", "three phase", "all", "published", E_AND, AND_SRC,
      AND_URL, None),
    R(AND_, "GS", "General Service", "energy", "AND-GS-EN-3PH-B2",
      "Energy charge three phase - over 2,000 kWh", 0.090101, "$/kWh",
      "all kWh above 2,000 per month", "three phase", "all", "published", E_AND, AND_SRC,
      AND_URL, None),
    R(AND_, "SP", "Small Power Service", "base_charge", "AND-SP-CUST", "Customer charge",
      49.30, "$/month", "per meter per month", "three-phase power service", "all",
      "published", E_AND, AND_SRC, AND_URL, None),
    R(AND_, "SP", "Small Power Service", "demand", "AND-SP-DEM", "Maximum load charge",
      12.443, "$/kW/month", "15-minute monthly maximum; billing floor 20 kW", "all voltages",
      "all", "published", E_AND, AND_SRC, AND_URL, None),
    R(AND_, "SP", "Small Power Service", "energy", "AND-SP-EN-B1",
      "Energy charge - first 200 hours use of billing maximum load", 0.048413, "$/kWh",
      "hours-use block", "all voltages", "all", "published", E_AND, AND_SRC, AND_URL, None),
    R(AND_, "SP", "Small Power Service", "energy", "AND-SP-EN-B2",
      "Energy charge - over 200 hours use", 0.046973, "$/kWh", "hours-use block",
      "all voltages", "all", "published", E_AND, AND_SRC, AND_URL, None),
    R(AND_, "LP", "Large Power Service", "base_charge", "AND-LP-CUST", "Customer charge",
      98.60, "$/month", "per meter per month", "three-phase, adjacent to adequate line",
      "all", "published", E_AND, AND_SRC, AND_URL, None),
    R(AND_, "LP", "Large Power Service", "demand", "AND-LP-DEM", "Maximum load charge",
      17.038, "$/kVA/month", "15-min kW / avg lagging PF, floor 100 kVA; minimum monthly "
      "charge = customer charge + maximum load charge", "all voltages", "all", "published",
      E_AND, AND_SRC, AND_URL, None),
    R(AND_, "LP", "Large Power Service", "energy", "AND-LP-EN", "Energy charge", 0.034510,
      "$/kWh", "all kWh", "all voltages", "all", "published", E_AND, AND_SRC, AND_URL, None),
    R(AND_, "LP", "Large Power Service", "rider", "AND-LP-PRIMARY-MULT",
      "Delivery-voltage credit - primary metering", None, None,
      "when metered at the primary voltage of the supplying line, the maximum load AND "
      "energy charges are multiplied by 0.98 (2% credit)", "primary-metered customers",
      "all", "published", E_AND, AND_SRC, AND_URL, None),
    R(AND_, "LP", "Large Power Service", "rider", "AND-LP-SUBST-CRED",
      "Customer-owned substation credit", -0.296, "$/kVA/month",
      "customer furnishes complete substation and takes service at primary voltage",
      "customer-substation customers", "all", "published", E_AND, AND_SRC, AND_URL, None),
    R(AND_, "LP", "Large Power Service", "ratchet", "AND-LP-RATCHET",
      "Demand ratchet - NONE (monthly floor only)", None, None,
      "billing maximum load = current month max, floor 100 kVA; no multi-month ratchet "
      "clause on the sheet", "all voltages", "all", "published", E_AND, AND_SRC, AND_URL,
      "Off-Peak option (>=500 kVA): billing load = greatest of on-peak max, 49.95% of "
      "off-peak max, or 500 kVA; off-peak = 9pm-9am Mon-Fri + weekends + 6 holidays."),
    R(AND_, "IP", "Industrial Power Service", "eligibility", "AND-IP-FLOOR",
      "Eligibility floor", 10000.0, "kVA",
      "three-phase primary service with monthly billing demands exceeding 10,000 kVA; "
      "customer owns the complete substation; initial term >= 1 year", "primary", "all",
      "published", E_AND, AND_SRC, AND_URL,
      "Matches URDB's 10,000 kW floor for Anderson IP. " + AND_PENDING),
    R(AND_, "IP", "Industrial Power Service", "base_charge", "AND-IP-CUST",
      "Monthly service charge", 172.55, "$/month", "per metering point per month",
      "primary", "all", "published", E_AND, AND_SRC, AND_URL, None),
    R(AND_, "IP", "Industrial Power Service", "demand", "AND-IP-DEM-DIST",
      "Distribution demand charge", 2.958, "$/kVA/month",
      "distribution demand = monthly maximum load (15-min kW / avg lagging PF), floor "
      "10,000 kVA", "primary", "all", "published", E_AND, AND_SRC, AND_URL, None),
    R(AND_, "IP", "Industrial Power Service", "demand", "AND-IP-DEM-BILLED",
      "Billed demand charge", 16.624, "$/kW/month",
      "billed demand = the 60-minute kW in the SAME interval and day used by IMPA to bill "
      "Anderson (coincident-peak billing)", "primary", "all", "published", E_AND, AND_SRC,
      AND_URL,
      "DECISION-RELEVANT: the demand leg is billed on the IMPA-coincident hour, so load "
      "curtailed at the IMPA peak avoids the $16.624 leg entirely; only the $2.958 "
      "distribution leg rides the customer's own NCP."),
    R(AND_, "IP", "Industrial Power Service", "energy", "AND-IP-EN", "Energy charge",
      0.033524, "$/kWh", "all kWh", "primary", "all", "published", E_AND, AND_SRC, AND_URL,
      None),
    R(AND_, "ISTP", "Industrial Sub Transmission Power Service", "eligibility",
      "AND-ISTP-FLOOR", "Eligibility floor", 10000.0, "kVA",
      "maximum load >= 10,000 kVA at 34.5 kV delivery; customer furnishes the complete "
      "substation; initial term >= 1 year", "34.5 kV subtransmission", "all", "published",
      E_AND, AND_SRC, AND_URL, None),
    R(AND_, "ISTP", "Industrial Sub Transmission Power Service", "demand", "AND-ISTP-FAC",
      "Facilities charge", 2.407, "$/kVA/month",
      "per kVA of maximum demand (15-min, floor 10,000 kVA); the minimum monthly charge",
      "34.5 kV", "all", "published", E_AND, AND_SRC, AND_URL, None),
    R(AND_, "ISTP", "Industrial Sub Transmission Power Service", "rider", "AND-ISTP-PASS",
      "Demand + energy = IMPA wholesale pass-through", None, None,
      "billed demand $/kW and billed energy $/kWh equal the CURRENT wholesale demand- and "
      "energy-related rates of power purchased by AML&P, incl. adjustment factors "
      "(Appendix C prints the retail adders at $0.000/kW and $0.000000/kWh - published "
      "zeros); billed demand = 60-min IMPA-coincident interval", "34.5 kV", "all",
      "published", E_AND, AND_SRC, AND_URL,
      "In effect: at >=10 MVA and 34.5 kV, Anderson resells IMPA wholesale at cost plus "
      "$2.407/kVA facilities - the cleanest wholesale-pass-through rate in the muni set."),
    R(AND_, "CL", "Constant Load Service", "energy", "AND-CL-EN", "Energy charge",
      0.061102, "$/kWh", "constant 24-hr loads; customer charge $9.86/meter", "all", "all",
      "published", E_AND, AND_SRC, AND_URL, None),
    R(AND_, "PPCAT", "Purchased power tracker base", "fuel_base", "AND-PPCAT-BASE-KW",
      "Purchased-power base cost embedded in base rates - demand leg", 16.872, "$/kW",
      "the PPCAT tracker recovers changes vs a base demand cost of $16.872/kW (stated in "
      "Cause 46397, Petitioner's Exhibit 3, Beauchamp direct p.41, describing the CURRENT "
      "tracker)", "all tracked schedules", "all", "published", None,
      "Cause 46397 Petitioner's Exhibit 3 (Beauchamp direct, filed 2026-04-24), p.41",
      URL["46397_PENDING_petition_20260424.pdf"],
      "Omit this base and the PPCAT double-counts - same failure mode as omitting an IOU "
      "fuel base. 46397 proposes recalibrating it."),
    R(AND_, "PPCAT", "Purchased power tracker base", "fuel_base", "AND-PPCAT-BASE-KWH",
      "Purchased-power base cost embedded in base rates - energy leg", 0.03213, "$/kWh",
      "base energy cost the quarterly PPCAT tracks against (same source)",
      "all tracked schedules", "all", "published", None,
      "Cause 46397 Petitioner's Exhibit 3 (Beauchamp direct, filed 2026-04-24), p.41",
      URL["46397_PENDING_petition_20260424.pdf"], None),
    R(AND_, "BASE", "Anderson base rate status", "eligibility", "AND-46397-PENDING",
      "Pending rate case Cause 46397", None, None,
      "filed 2026-04-24: revenue requirement $95,699,757 = +12.58% system average, phased "
      ">12 months; proposed IP $250.00 + $6.56/kVA distribution + $28.44/kW billed + "
      "$0.04387/kWh; settlement hearing noticed 2026-09-21 (procedural schedule abated "
      "2026-07-28)", "all schedules", "all", "published", None,
      "Cause 46397 petition + corrected tariff pages 2026-06-03 + hearing notice 2026-08-14",
      "https://iurc.portal.in.gov/docketed-case-details/?id=cf9f09be-1240-f111-88b3-"
      "001dd800b811",
      "PROPOSED numbers - NOT effective. Re-run this loader after the final order."),
]

# ==========================================================================================
# AUBURN - current values = 50523 approved tariff (2022-06-28, Ordinance 2022-08 URT
# decrease); schedule design/floors = Cause 45102 compliance sheets (2018-11-07).
# ==========================================================================================
AUB_SRC = ("Auburn 30-Day Filing No. 50523 approved tariff Exhibit 7 (conference minutes "
           "2022-06-28; Rate Ordinance 2022-08, HEA-1002 URT decrease); structure per Cause "
           "45102 compliance sheets 2018-11-07 (rate case order 2018-09-12) and Cause 44472")
AUB_URL = URL["30day_50523_approved_tariff_20220628.pdf"]
AUB_STRUCT = ("Auburn Cause 45102 compliance tariff sheets, filed 2018-11-07")
AUB_STRUCT_URL = URL["45102_compliance_20181107.pdf"]
E_AUB = "2022-07-01"
AUB_EXIT = ("JURISDICTION PENDING CHANGE: Auburn announced 2026-04-01 it would leave IURC "
            "oversight; withdrawal Ordinance 2026-12 + rate Ordinance 2026-13 passed FIRST "
            "reading April 2026 (60-day remonstrance follows adoption); completion not "
            "confirmed as of 2026-08-18 - Auburn still filed tracker 50912 approved "
            "2026-06-24.")

AUBURN_ROWS = [
    R(AUB, "R", "Residential Service (Rate Code 10)", "base_charge", "AUB-R-CUST",
      "Charge per dwelling unit", 6.90, "$/month", "per dwelling unit", "residential",
      "all", "published", E_AUB, AUB_SRC, AUB_URL, None),
    R(AUB, "R", "Residential Service (Rate Code 10)", "energy", "AUB-R-EN", "Energy charge",
      0.070306, "$/kWh", "all kWh", "residential", "all", "published", E_AUB, AUB_SRC,
      AUB_URL, None),
    R(AUB, "SGS", "Commercial Three Phase (Rate Code 35)", "base_charge", "AUB-SGS35-CUST",
      "Customer charge", 29.58, "$/month", "per service location; class ceiling 50 kVA",
      "secondary, three phase", "all", "published", E_AUB, AUB_SRC, AUB_URL, None),
    R(AUB, "SGS", "Commercial Three Phase (Rate Code 35)", "energy", "AUB-SGS35-EN",
      "Energy charge", 0.087432, "$/kWh", "all kWh; energy-only class (no demand charge)",
      "secondary", "all", "published", E_AUB, AUB_SRC, AUB_URL, None),
    R(AUB, "LGS-3", "Commercial Three Phase (Rate Code 39)", "eligibility", "AUB-LGS-ELIG",
      "Class window", 50.0, "kVA", "monthly demand billing >50 kVA and <=200 kVA",
      "secondary", "all", "published", E_AUB, AUB_STRUCT, AUB_STRUCT_URL, None),
    R(AUB, "LGS-3", "Commercial Three Phase (Rate Code 39)", "base_charge", "AUB-LGS-CUST",
      "Customer charge", 29.58, "$/month", "per service location", "secondary", "all",
      "published", E_AUB, AUB_SRC, AUB_URL, None),
    R(AUB, "LGS-3", "Commercial Three Phase (Rate Code 39)", "demand", "AUB-LGS-DEM",
      "Demand charge", 17.10, "$/kVA/month", "15-min kW / avg monthly PF", "secondary",
      "all", "published", E_AUB, AUB_SRC, AUB_URL,
      "EVERY Auburn demand-metered class bills $17.10/kVA (was $17.34 pre-URT); the classes "
      "differ only in customer charge, energy rate, eligibility window and ratchet."),
    R(AUB, "LGS-3", "Commercial Three Phase (Rate Code 39)", "energy", "AUB-LGS-EN",
      "Energy charge", 0.046483, "$/kWh", "all kWh", "secondary", "all", "published",
      E_AUB, AUB_SRC, AUB_URL, None),
    R(AUB, "LGS-3", "Commercial Three Phase (Rate Code 39)", "ratchet", "AUB-LGS-RATCHET",
      "60% / 11-month ratchet", 60.0, "% of 11-month high",
      "monthly billing demand >= higher of 50 kVA or 60% of highest kVA billing demand in "
      "previous 11 months", "secondary", "all", "published", E_AUB, AUB_STRUCT,
      AUB_STRUCT_URL, None),
    R(AUB, "LP", "Primary/Secondary Large Power (Rate Codes 41-42)", "eligibility",
      "AUB-LP-ELIG", "Eligibility floor", 200.0, "kVA", "monthly demand billing >200 kVA",
      "primary or secondary", "all", "published", E_AUB, AUB_STRUCT, AUB_STRUCT_URL, None),
    R(AUB, "LP", "Primary/Secondary Large Power (Rate Codes 41-42)", "base_charge",
      "AUB-LP-CUST", "Customer charge", 69.02, "$/month", "per service location",
      "primary or secondary", "all", "published", E_AUB, AUB_SRC, AUB_URL, None),
    R(AUB, "LP", "Primary/Secondary Large Power (Rate Codes 41-42)", "demand", "AUB-LP-DEM",
      "Demand charge", 17.10, "$/kVA/month",
      "ratchet: >= higher of 200 kVA or 60% of 11-month high", "primary or secondary",
      "all", "published", E_AUB, AUB_SRC, AUB_URL, None),
    R(AUB, "LP", "Primary/Secondary Large Power (Rate Codes 41-42)", "energy",
      "AUB-LP-EN-PRI", "Energy charge - primary metering", 0.047192, "$/kWh", "all kWh",
      "primary (7,200/12,470 V metering)", "all", "published", E_AUB, AUB_SRC, AUB_URL,
      None),
    R(AUB, "LP", "Primary/Secondary Large Power (Rate Codes 41-42)", "energy",
      "AUB-LP-EN-SEC", "Energy charge - secondary metering", 0.047713, "$/kWh", "all kWh",
      "secondary", "all", "published", E_AUB, AUB_SRC, AUB_URL, None),
    R(AUB, "LPS", "Primary/Secondary Large Power (Rate Codes 43-44)", "eligibility",
      "AUB-LPS-ELIG", "Eligibility floor", 50.0, "kVA",
      "monthly demand billing >50 kVA; service at 7,200/12,470 V where the customer "
      "furnishes the substation", "customer-substation primary", "all", "published", E_AUB,
      AUB_STRUCT, AUB_STRUCT_URL, None),
    R(AUB, "LPS", "Primary/Secondary Large Power (Rate Codes 43-44)", "base_charge",
      "AUB-LPS-CUST", "Customer charge", 59.16, "$/month", "per service location",
      "primary or secondary", "all", "published", E_AUB, AUB_SRC, AUB_URL, None),
    R(AUB, "LPS", "Primary/Secondary Large Power (Rate Codes 43-44)", "demand",
      "AUB-LPS-DEM", "Demand charge", 17.10, "$/kVA/month",
      "ratchet: >= higher of 50 kVA or 60% of 11-month high; Rate Code 43 may elect "
      "COINCIDENT-PEAK billing demand (15-min kW in the hour of the wholesale supplier "
      "peak - the Industrial Demand Incentive Program)", "primary or secondary", "all",
      "published", E_AUB, AUB_SRC, AUB_URL,
      "The IDIP CP option is the demand-response lever: load absent at the I&M/AEP "
      "coincident hour escapes the demand charge (reverts to NCP if absent all month)."),
    R(AUB, "LPS", "Primary/Secondary Large Power (Rate Codes 43-44)", "energy",
      "AUB-LPS-EN-PRI", "Energy charge - primary", 0.045892, "$/kWh", "all kWh", "primary",
      "all", "published", E_AUB, AUB_SRC, AUB_URL, None),
    R(AUB, "LPS", "Primary/Secondary Large Power (Rate Codes 43-44)", "energy",
      "AUB-LPS-EN-SEC", "Energy charge - secondary", 0.042833, "$/kWh", "all kWh",
      "secondary", "all", "published", E_AUB, AUB_SRC, AUB_URL, None),
    R(AUB, "EHP", "High Voltage Large Power (Rate Code 45)", "eligibility", "AUB-EHP-ELIG",
      "Class window", 5000.0, "kVA",
      "monthly demand billing >5,000 kVA and <=30,000 kVA; 69,000 V service, customer "
      "furnishes complete substation metered at 69 kV; IDIP CP option available", "69 kV",
      "all", "published", E_AUB, AUB_STRUCT, AUB_STRUCT_URL, None),
    R(AUB, "EHP", "High Voltage Large Power (Rate Code 45)", "base_charge", "AUB-EHP-CUST",
      "Customer charge", 246.50, "$/month", "per service location", "69 kV", "all",
      "published", E_AUB, AUB_SRC, AUB_URL, None),
    R(AUB, "EHP", "High Voltage Large Power (Rate Code 45)", "demand", "AUB-EHP-DEM",
      "Demand charge", 17.10, "$/kVA/month",
      "ratchet: >= higher of 5,000 kVA or 60% of 11-month high", "69 kV", "all",
      "published", E_AUB, AUB_SRC, AUB_URL, None),
    R(AUB, "EHP", "High Voltage Large Power (Rate Code 45)", "energy", "AUB-EHP-EN",
      "Energy charge", 0.031855, "$/kWh", "all kWh", "69 kV", "all", "published", E_AUB,
      AUB_SRC, AUB_URL, None),
    R(AUB, "EHPT", "High Voltage Large Power (Rate Code 45T)", "eligibility",
      "AUB-EHPT-ELIG", "Class window", 5000.0, "kVA",
      "monthly billing demand >5,000 kVA and <=20,000 kVA; 69 kV, customer substation",
      "69 kV", "all", "published", E_AUB, AUB_STRUCT, AUB_STRUCT_URL, None),
    R(AUB, "EHPT", "High Voltage Large Power (Rate Code 45T)", "demand", "AUB-EHPT-DEM",
      "Demand charge - on-peak-based", 17.10, "$/kVA/month",
      "applied to the HIGHER of on-peak billing demand or off-peak demand capped at 1.2x "
      "on-peak; the 1.0-1.2x off-peak band is NOT billed; floor 5,000 kVA / 60% of "
      "11-month high", "69 kV", "all", "published", E_AUB, AUB_SRC, AUB_URL,
      "A 45T customer can run off-peak load up to 120% of its on-peak demand without "
      "increasing the demand bill."),
    R(AUB, "EHPT", "High Voltage Large Power (Rate Code 45T)", "energy", "AUB-EHPT-EN",
      "Energy charge", 0.031246, "$/kWh", "all kWh", "69 kV", "all", "published", E_AUB,
      AUB_SRC, AUB_URL, None),
    R(AUB, "EHV", "High Voltage Large Power (Rate Code 40)", "eligibility", "AUB-EHV-ELIG",
      "Eligibility floor", 30000.0, "kVA",
      "nominal monthly demand billing exceeds 30,000 kVA; 69,000 V, customer furnishes "
      "complete substation; IDIP CP option available", "69 kV", "all", "published", E_AUB,
      AUB_STRUCT, AUB_STRUCT_URL,
      "The largest muni retail class floor in Indiana - sized for a single very large "
      "industrial (or a data-centre campus). " + AUB_EXIT),
    R(AUB, "EHV", "High Voltage Large Power (Rate Code 40)", "base_charge", "AUB-EHV-CUST",
      "Customer charge", 345.10, "$/month", "per service location", "69 kV", "all",
      "published", E_AUB, AUB_SRC, AUB_URL, None),
    R(AUB, "EHV", "High Voltage Large Power (Rate Code 40)", "demand", "AUB-EHV-DEM",
      "Demand charge", 17.10, "$/kVA/month",
      "billing demand >= higher of 25,000 kVA or the highest monthly billing demand in the "
      "previous 11 months (100% ratchet with a 25 MVA floor)", "69 kV", "all", "published",
      E_AUB, AUB_SRC, AUB_URL,
      "HARSHEST ratchet in the muni set: a single peak month sets the bill floor for a "
      "year, and the floor never drops below 25,000 kVA (~$427,500/mo at $17.10)."),
    R(AUB, "EHV", "High Voltage Large Power (Rate Code 40)", "energy", "AUB-EHV-EN",
      "Energy charge", 0.031084, "$/kWh", "all kWh", "69 kV", "all", "published", E_AUB,
      AUB_SRC, AUB_URL, None),
    R(AUB, "IDIP", "Industrial Demand Control Incentive Program", "eligibility",
      "AUB-IDIP-ELIG", "CP-billing option floors", None, None,
      "open to Rate Codes 40/43/45 with customer-owned substation: minimum 1,500 kVA "
      "billing demand at 7,200/12,470 V or 6,000 kVA at 69,000 V; billing demand = 15-min "
      "kW in the hour coincident with Auburn's wholesale supplier peak (I&M/AEP)",
      "codes 40, 43, 45", "all", "published", E_AUB, AUB_STRUCT, AUB_STRUCT_URL, None),
    R(AUB, "TRACKERS", "Appendix A adjustment stack", "rider", "AUB-TRACKER-STACK",
      "Three-part tracker: PPCAT + supplier FCA + supplier System Sales", None, None,
      "Part I Purchased Power Cost Adjustment Tracking Factor (quarterly; current factor "
      "$0.034896/kWh all schedules per 30-day 50912, held on the AUB-PPT-ALL row); Part II "
      "Fuel Cost Adjustment tracking the supplier's (I&M/AEP) FAC - Auburn's own-fuel "
      "factor a published zero since 2011-10-01; Part III System Sales Clause tracking the "
      "supplier's SSC", "all schedules", "all", "published", E_AUB, AUB_SRC, AUB_URL,
      AUB_EXIT),
]

# ==========================================================================================
# FRANKFORT - current sheets = 30-Day Filing 50549 (conference minutes 2022-06-28), eff
# service on/after 2022-07-01; base design per Cause 44856 order 2017-07-05.
# ==========================================================================================
FRK_SRC = ("Frankfort City Light & Power 30-Day Filing No. 50549 stamped sheets (conference "
           "minutes 2022-06-28; 1st Revised A.1/B.1/C.1/PPL.1-3 + Original AB.1-2 Rate IP; "
           "HEA-1002 URT decrease), effective for service rendered on/after 2022-07-01; "
           "base rates from Cause 44856 order 2017-07-05 (+8.63%)")
FRK_URL = URL["30day_50549_tariff.pdf"]
E_FRK = "2022-07-01"

FRANKFORT_ROWS = [
    R(FRK, "A", "Residential Service", "base_charge", "FRK-A-CUST", "Customer charge",
      7.89, "$/month", "per meter per month", "residential single phase", "all",
      "published", E_FRK, FRK_SRC, FRK_URL, None),
    R(FRK, "A", "Residential Service", "energy", "FRK-A-EN", "Energy charge", 0.097615,
      "$/kWh", "all kWh", "residential", "all", "published", E_FRK, FRK_SRC, FRK_URL, None),
    R(FRK, "B", "Commercial Service", "base_charge", "FRK-B-CUST", "Customer charge",
      114.79, "$/month", "per meter per month, AS PRINTED on 1st Revised Sheet B.1",
      "commercial single phase", "all", "published", E_FRK, FRK_SRC, FRK_URL,
      "ANOMALY, transcribed as printed: the 2017 sheet was $15.00 and the URT factor "
      "(x0.9858, matching every other sheet) gives $14.79 - the published $114.79 is "
      "almost certainly a typo for $14.79, but the stamped sheet says $114.79. Verify "
      "with the utility before modelling a 1-phase commercial bill."),
    R(FRK, "B", "Commercial Service", "energy", "FRK-B-EN", "Energy charge", 0.101807,
      "$/kWh", "all kWh", "commercial single phase", "all", "published", E_FRK, FRK_SRC,
      FRK_URL, None),
    R(FRK, "C", "General Power Service", "base_charge", "FRK-C-CUST", "Customer charge",
      29.57, "$/month", "per meter per month", "any customer on adequate line", "all",
      "published", E_FRK, FRK_SRC, FRK_URL, None),
    R(FRK, "C", "General Power Service", "energy", "FRK-C-EN", "Energy charge", 0.096676,
      "$/kWh", "all kWh", "all voltages", "all", "published", E_FRK, FRK_SRC, FRK_URL,
      None),
    R(FRK, "PPL", "Primary Power and Light Service", "eligibility", "FRK-PPL-ELIG",
      "Eligibility floor", 25.0, "kVA",
      "contract for specified capacity >= 25 kVA; one-year term; adjacent to adequate "
      "line", "all voltages", "all", "published", E_FRK, FRK_SRC, FRK_URL, None),
    R(FRK, "PPL", "Primary Power and Light Service", "base_charge", "FRK-PPL-CUST",
      "Customer charge", 59.15, "$/month", "per meter per month", "all voltages", "all",
      "published", E_FRK, FRK_SRC, FRK_URL, None),
    R(FRK, "PPL", "Primary Power and Light Service", "demand", "FRK-PPL-DEM",
      "Maximum load charge", 18.137, "$/kVA/month",
      "30-min kW / avg lagging PF; billing floor 25 kVA; minimum charge = demand + "
      "customer charge", "all voltages", "all", "published", E_FRK, FRK_SRC, FRK_URL, None),
    R(FRK, "PPL", "Primary Power and Light Service", "energy", "FRK-PPL-EN",
      "Energy charge", 0.039978, "$/kWh", "all kWh", "all voltages", "all", "published",
      E_FRK, FRK_SRC, FRK_URL, None),
    R(FRK, "PPL", "Primary Power and Light Service", "rider", "FRK-PPL-METER",
      "Low-voltage metering adjustment", None, None,
      "metered at ~480 V or lower: demand and energy measurements increased 2% to primary "
      "equivalent", "secondary-metered", "all", "published", E_FRK, FRK_SRC, FRK_URL, None),
    R(FRK, "PPL", "Primary Power and Light Service", "rider", "FRK-PPL-SUBST-CRED",
      "Customer-owned substation credit", -0.34, "$/kVA/month",
      "customer furnishes complete substation taking service at line primary voltage",
      "customer-substation", "all", "published", E_FRK, FRK_SRC, FRK_URL, None),
    R(FRK, "PPL", "Primary Power and Light Service", "eligibility", "FRK-PPL-OFFPEAK",
      "Off-peak option - capped", None, None,
      "billing demand = greater of on-peak max or 50% of off-peak max, floor 500 kVA; "
      "off-peak 9pm-7am Mon-Fri + weekends/holidays; AVAILABILITY CAPPED at 5,000 kVA "
      "aggregate, first-come first-served", "PPL customers >=500 kVA", "all", "published",
      E_FRK, FRK_SRC, FRK_URL, None),
    R(FRK, "IP", "Industrial Power Service", "eligibility", "FRK-IP-FLOOR",
      "Eligibility floor", 10000.0, "kW",
      "minimum load requirement 10 MW or more, directly fed from the 69 kV transmission "
      "system; customer owns ALL transformation equipment (sheet AB.2 describes stepping "
      "down 'from 138kV' [sic]); adjacent to adequate transmission line", "transmission",
      "all", "published", E_FRK, FRK_SRC, FRK_URL,
      "NEW schedule created in the 2022 50549 filing (Original Sheets AB.1-2) - Frankfort "
      "built a 10 MW transmission-service on-ramp in 2022."),
    R(FRK, "IP", "Industrial Power Service", "base_charge", "FRK-IP-CUST",
      "Customer charge", 591.48, "$/month", "per meter per month", "transmission", "all",
      "published", E_FRK, FRK_SRC, FRK_URL, None),
    R(FRK, "IP", "Industrial Power Service", "demand", "FRK-IP-DEM", "Demand charge",
      24.054, "$/kVA/month",
      "15-min kVA peak; billing demand = greater of month peak or 10 MVA (monthly floor, "
      "no multi-month ratchet); metered <=13,800 V grossed +2%", "transmission", "all",
      "published", E_FRK, FRK_SRC, FRK_URL, None),
    R(FRK, "IP", "Industrial Power Service", "energy", "FRK-IP-EN", "Energy charge",
      0.028275, "$/kWh", "all kWh", "transmission", "all", "published", E_FRK, FRK_SRC,
      FRK_URL, None),
    R(FRK, "EDR", "Economic Development Rider", "eligibility", "FRK-EDR-LAPSED",
      "EDR - lapsed by its own terms", None, None,
      "the 44856-book EDR (PPL/IP customers, +1,000 kW increments, 60-month incentive) "
      "required applications 'prior to January 1, 2025' - no longer open", "PPL and IP",
      "all", "published", None,
      "Frankfort Cause 44856 compliance tariff sheets EDR.1.x, filed 2017-07-06",
      "https://iurc.portal.in.gov/_entity/sharepointdocumentlocation/c2f061ba-1463-e711-"
      "810c-1458d04e8ff8/bb9c6bba-fd52-45ad-8e64-a444aef13c39?file=44856_City%20of%20"
      "Frankfort_Submission%20of%20Compliance%20Filing_070617.pdf", None),
]

# ==========================================================================================
# RICHMOND P&L - book = full compliance tariff (30-Day 50559 conference 2022-06-01;
# Ordinance 26-2022; lineage Cause 45361 order 2021-01-20).  Phase 3 column (eff
# 2023-01-20) = CURRENT.  RP&L withdrew from IURC rate jurisdiction November 2022;
# rates council-set since; quarterly ECA continues via published legal ads.
# The book is an image scan: numbers below were verified by HUMAN-VISUAL reads of pages
# 11/15/19/23/27 (LPSS/LPSP/ISS/ISP/TS) on 2026-08-18; sha256 pinned; OCR text cached.
# ==========================================================================================
RICH_SRC = ("RP&L full compliance tariff eff 2022-07-01 (30-Day Filing 50559 approved by "
            "conference minutes 2022-06-01; Ordinance 26-2022; Cause 45361 settlement "
            "order 2021-01-20), Phase 3 column effective 2023-01-20 = current")
RICH_URL = URL["rpl_full_compliance_tariff_eff_2022-07-01.pdf"]
RICH_ECA_SRC = "RP&L Q3-2026 ECA legal ad (Cause 36835-S3 mechanism), bills from July 2026"
RICH_ECA_URL = URL["rpl_eca_2026q3_legal_ad.pdf"]
E_RICH = "2023-01-20"
RICH_IMG = ("Image-scan source; value verified by human-visual page read 2026-08-18 "
            "(sha256-pinned in the loader); OCR text cached alongside.")

RICHMOND_ROWS = [
    R(RICH, "TS", "Transmission Service", "eligibility", "RICH-TS-ELIG",
      "Eligibility floor", 10000.0, "kW",
      "maximum load requirement >=10,000 kW taking service at 69 kV or higher, adjacent "
      "to an adequate RP&L transmission line", "transmission (>=69 kV)", "all",
      "published", E_RICH, RICH_SRC, RICH_URL,
      "THE only muni transmission-voltage tariff URDB knew about - confirmed. " + RICH_IMG),
    R(RICH, "TS", "Transmission Service", "base_charge", "RICH-TS-FAC", "Facilities charge",
      192.56, "$/month", "per month", "transmission", "all", "published", E_RICH, RICH_SRC,
      RICH_URL, None),
    R(RICH, "TS", "Transmission Service", "demand", "RICH-TS-DEM", "Demand charge", 21.70,
      "$/kVA/month", "30-min kVA peak; billing demand = greater of month peak or 10,000 "
      "kVA (monthly floor, no multi-month ratchet); minimum charge = facilities + demand",
      "transmission", "all", "published", E_RICH, RICH_SRC, RICH_URL, RICH_IMG),
    R(RICH, "TS", "Transmission Service", "energy", "RICH-TS-EN", "Energy charge", 0.02710,
      "$/kWh", "all kWh", "transmission", "all", "published", E_RICH, RICH_SRC, RICH_URL,
      None),
    R(RICH, "ISP", "Industrial Service Primary", "eligibility", "RICH-ISP-ELIG",
      "Eligibility floor", 1000.0, "kW",
      "primary service, maximum load >=1,000 kW; customer furnishes complete substation "
      "and line equipment for delivery at <=15,000 V primary", "primary (<=15 kV)", "all",
      "published", E_RICH, RICH_SRC, RICH_URL, None),
    R(RICH, "ISP", "Industrial Service Primary", "base_charge", "RICH-ISP-FAC",
      "Facilities charge", 192.56, "$/month", "per month", "primary", "all", "published",
      E_RICH, RICH_SRC, RICH_URL, None),
    R(RICH, "ISP", "Industrial Service Primary", "demand", "RICH-ISP-DEM", "Demand charge",
      23.67, "$/kVA/month", "30-min kVA; floor 1,000 kVA", "primary", "all", "published",
      E_RICH, RICH_SRC, RICH_URL, RICH_IMG),
    R(RICH, "ISP", "Industrial Service Primary", "energy", "RICH-ISP-EN", "Energy charge",
      0.03324, "$/kWh", "all kWh", "primary", "all", "published", E_RICH, RICH_SRC,
      RICH_URL, None),
    R(RICH, "ISS", "Industrial Service Secondary", "eligibility", "RICH-ISS-ELIG",
      "Eligibility floor", 1000.0, "kW",
      "secondary service, maximum load >=1,000 kW; the Utility supplies ONE transformation "
      "to a standard voltage at its expense", "secondary", "all", "published", E_RICH,
      RICH_SRC, RICH_URL, None),
    R(RICH, "ISS", "Industrial Service Secondary", "base_charge", "RICH-ISS-FAC",
      "Facilities charge", 192.56, "$/month", "per month", "secondary", "all", "published",
      E_RICH, RICH_SRC, RICH_URL, None),
    R(RICH, "ISS", "Industrial Service Secondary", "demand", "RICH-ISS-DEM",
      "Demand charge", 24.66, "$/kVA/month", "30-min kVA; floor 1,000 kVA", "secondary",
      "all", "published", E_RICH, RICH_SRC, RICH_URL, RICH_IMG),
    R(RICH, "ISS", "Industrial Service Secondary", "energy", "RICH-ISS-EN", "Energy charge",
      0.03393, "$/kWh", "all kWh", "secondary", "all", "published", E_RICH, RICH_SRC,
      RICH_URL, None),
    R(RICH, "LPSS", "Large Power Service Secondary", "demand", "RICH-LPSS-DEM",
      "Demand charge", 24.66, "$/kVA/month",
      "class window 60-1,000 kW secondary; facilities $192.56/mo; 30-min kVA, floor 60 "
      "kVA; metered >=2,400 V decreased 2%", "secondary", "all", "published", E_RICH,
      RICH_SRC, RICH_URL, RICH_IMG),
    R(RICH, "LPSS", "Large Power Service Secondary", "energy", "RICH-LPSS-EN",
      "Energy charge", 0.03466, "$/kWh", "all kWh", "secondary", "all", "published",
      E_RICH, RICH_SRC, RICH_URL, None),
    R(RICH, "LPSP", "Large Power Service Primary", "demand", "RICH-LPSP-DEM",
      "Demand charge", 22.81, "$/kVA/month",
      "class window 60-1,000 kW primary; facilities $192.56/mo; 30-min kVA, floor 60 kVA",
      "primary", "all", "published", E_RICH, RICH_SRC, RICH_URL, RICH_IMG),
    R(RICH, "LPSP", "Large Power Service Primary", "energy", "RICH-LPSP-EN",
      "Energy charge", 0.03499, "$/kWh", "all kWh (Phase 3; Phase 2 was 0.03512)",
      "primary", "all", "published", E_RICH, RICH_SRC, RICH_URL, None),
    R(RICH, "R", "Residential Service", "energy", "RICH-R-EN", "Energy charge (headline)",
      0.10050, "$/kWh", "all kWh (Phase 3); facilities $12.08/mo", "residential", "all",
      "published", E_RICH, RICH_SRC, RICH_URL, RICH_IMG),
    R(RICH, "ECA", "Quarterly Wholesale Purchase Power/Energy Cost Adjustment", "rider",
      "RICH-ECA-IND-KVA", "ECA - demand-metered classes, demand leg", -0.853292,
      "$/kVA/month", "quarterly tracker per Cause 36835-S3 (order 1989-12-13); applies to "
      "ISS/ISP/LPSS/LPSP/TS", "demand-metered classes", "all", "published", "2026-07-01",
      RICH_ECA_SRC, RICH_ECA_URL,
      "Currently a demand-leg CREDIT plus an energy-leg charge - net adder ~+1.4 c/kWh at "
      "80% LF. RP&L publishes the quarterly factors as newspaper legal ads on rp-l.com."),
    R(RICH, "ECA", "Quarterly ECA", "rider", "RICH-ECA-IND-KWH",
      "ECA - demand-metered classes, energy leg", 0.015869, "$/kWh", "quarterly tracker",
      "demand-metered classes", "all", "published", "2026-07-01", RICH_ECA_SRC,
      RICH_ECA_URL, None),
    R(RICH, "ECA", "Quarterly ECA", "rider", "RICH-ECA-COIN-KW",
      "ECA - COIN (coincident-peak) variants, demand leg", -1.059137, "$/kW/month",
      "quarterly tracker", "COIN schedules", "all", "published", "2026-07-01",
      RICH_ECA_SRC, RICH_ECA_URL, None),
    R(RICH, "ECA", "Quarterly ECA", "rider", "RICH-ECA-COIN-KWH",
      "ECA - COIN variants, energy leg", 0.015862, "$/kWh", "quarterly tracker",
      "COIN schedules", "all", "published", "2026-07-01", RICH_ECA_SRC, RICH_ECA_URL, None),
    R(RICH, "ECA", "Quarterly ECA", "rider", "RICH-ECA-R-KWH", "ECA - residential",
      0.013826, "$/kWh", "quarterly tracker", "residential", "all", "published",
      "2026-07-01", RICH_ECA_SRC, RICH_ECA_URL, None),
    R(RICH, "COIN", "Optional Coincident Peak Service variants", "eligibility",
      "RICH-COIN-STATUS", "COIN option exists on LPSS/LPSP/ISS/ISP/TS", None, None,
      "COIN variants re-price demand onto coincident-peak kW plus a small T&D kVA leg "
      "(ISS-COIN Phase 3 prints $192.56 / $0.02464/kWh / $26.53/kW billing + $5.52/kVA "
      "T&D, min T&D demand 1,000 kVA, >=5% on->off-peak shift required, 96% PF clause - "
      "OCR-derived figures, not visually verified; treat as indicative)", "large classes",
      "all", "published", E_RICH, RICH_SRC, RICH_URL, None),
    R(RICH, "JURISDICTION", "Rate-setting status", "eligibility", "RICH-RATESET",
      "Council-set since November 2022", None, None,
      "RP&L withdrew from IURC rate jurisdiction in November 2022 (per OUCC); the 50559/"
      "45361 book remains the effective schedule; future changes come by Richmond Common "
      "Council ordinance", "all schedules", "all", "published", None,
      "OUCC statement + Ordinance 26-2022 (cached richmond_ordinance_26-2022_cause50559."
      "pdf)", "https://www.rp-l.com/updates-to-rates-charges/",
      "Complements the NONJURIS-MUNI census row - kept, both true."),
]

# ==========================================================================================
# LOGANSPORT - Ordinance 2025-02 (adopted 2025-02-03, 4-3 vote) + LMU Rate Guide with
# ANNUAL STEPS 2025-2029.  2026 column loaded as current.  No PCA/fuel tracker exists.
# Supplier: NextEra full-requirements PPA, fixed $0.03915/kWh, expires 2028.
# ==========================================================================================
LOGA_SRC = ("Logansport Ordinance 2025-02 (adopted 2025-02-03; Exhibit A = Baker Tilly "
            "COSS 2024-12-05) as published in the LMU Rate Guide annual-step tables "
            "2025-2029; 2026 column loaded")
LOGA_URL = URL["lmu_rate_guide.pdf"]
E_LOGA = "2026-01-01"
LOGA_STEP = ("Rates step ANNUALLY per the ordinance: 2027/2028/2029 columns are already "
             "adopted (see rate guide); no quarterly tracker exists.")

LOGANSPORT_ROWS = [
    R(LOGA, "IS", "Industrial Substation Service", "base_charge", "LOGA-IS-FLAT",
      "Monthly flat charge", 32500.0, "$/month", "2026 step (2025 $32,000 ... 2029 "
      "$35,000)", "customer substation service", "all", "published", E_LOGA, LOGA_SRC,
      LOGA_URL,
      "A $32,500/month FLAT charge is itself a ~2 MW-scale entry fee - this is the class "
      "URDB showed with a 10,000 kW floor (floor text lives in base Ordinance 2018-26, "
      "not online - see LOGA-FLOORS)."),
    R(LOGA, "IS", "Industrial Substation Service", "demand", "LOGA-IS-DEM", "Demand charge",
      14.592, "$/kVAD/month", "2026 step", "customer substation", "all", "published",
      E_LOGA, LOGA_SRC, LOGA_URL, LOGA_STEP),
    R(LOGA, "IS", "Industrial Substation Service", "energy", "LOGA-IS-EN", "Energy charge",
      0.045442, "$/kWh", "all kWh, 2026 step", "customer substation", "all", "published",
      E_LOGA, LOGA_SRC, LOGA_URL, None),
    R(LOGA, "LI", "Large Industrial Service", "base_charge", "LOGA-LI-FLAT",
      "Monthly flat charge", 250.0, "$/month", "2026 step", "large industrial", "all",
      "published", E_LOGA, LOGA_SRC, LOGA_URL, None),
    R(LOGA, "LI", "Large Industrial Service", "demand", "LOGA-LI-DEM", "Demand charge",
      17.686, "$/kW/month", "2026 step", "large industrial", "all", "published", E_LOGA,
      LOGA_SRC, LOGA_URL, None),
    R(LOGA, "LI", "Large Industrial Service", "energy", "LOGA-LI-EN", "Energy charge",
      0.041727, "$/kWh", "all kWh, 2026 step", "large industrial", "all", "published",
      E_LOGA, LOGA_SRC, LOGA_URL, None),
    R(LOGA, "LP", "Large Power Service", "base_charge", "LOGA-LP-FLAT",
      "Monthly flat charge", 86.0, "$/month", "2026 step", "large power", "all",
      "published", E_LOGA, LOGA_SRC, LOGA_URL, None),
    R(LOGA, "LP", "Large Power Service", "demand", "LOGA-LP-DEM", "Demand charge", 14.183,
      "$/kVAD/month", "2026 step; demand billed per kVA of demand (kVAD)", "large power",
      "all", "published", E_LOGA, LOGA_SRC, LOGA_URL, None),
    R(LOGA, "LP", "Large Power Service", "energy", "LOGA-LP-EN-B1",
      "Energy - first 200 kWh/kVAD", 0.049812, "$/kWh", "hours-use block, 2026 step",
      "large power", "all", "published", E_LOGA, LOGA_SRC, LOGA_URL, None),
    R(LOGA, "LP", "Large Power Service", "energy", "LOGA-LP-EN-B2",
      "Energy - next 100 kWh/kVAD", 0.048741, "$/kWh", "hours-use block, 2026 step",
      "large power", "all", "published", E_LOGA, LOGA_SRC, LOGA_URL, None),
    R(LOGA, "LP", "Large Power Service", "energy", "LOGA-LP-EN-B3",
      "Energy - over 300 kWh/kVAD", 0.047522, "$/kWh", "hours-use block, 2026 step",
      "large power", "all", "published", E_LOGA, LOGA_SRC, LOGA_URL, None),
    R(LOGA, "RES", "Residential (headline)", "energy", "LOGA-RES-EN-B1",
      "Energy - first 200 kWh", 0.105500, "$/kWh",
      "2026 step (flat through 2029); customer charge $5.00 inside city", "residential",
      "all", "published", E_LOGA, LOGA_SRC, LOGA_URL, None),
    R(LOGA, "TRACKER", "Power cost adjustment - NONE EXISTS", "rider", "LOGA-NO-TRACKER",
      "No PCA/fuel tracker", None, None,
      "no adjustment language exists in the rate guide or Ordinance 2025-02; cost changes "
      "are handled by the pre-adopted annual steps 2025-2029", "all schedules", "all",
      "published", E_LOGA, LOGA_SRC, LOGA_URL,
      "The only utility in this harvest with NO tracker of any kind - fixed-price "
      "schedule risk sits with LMU until the 2028 PPA expiry."),
    R(LOGA, "SUPPLY", "Wholesale supply", "eligibility", "LOGA-SUPPLY",
      "NextEra full-requirements PPA to 2028", None, None,
      "LMU purchases most requirements from NextEra Energy under a PPA at a set rate of "
      "$0.03915/kWh expiring 2028, plus a small Alchemy Renewable (Logansport Solar) PPA "
      "at $0.05/kWh and third-party MISO charges; purchased power = 77% of total expenses "
      "(Ordinance 2025-02 / Baker Tilly COSS, OCR text cached)", "system", "all",
      "published", "2025-02-03",
      "Logansport Ordinance 2025-02 Exhibit A (COSS 2024-12-05), OCR transcription cached",
      URL["ordinance_2025-02_electric_rates.pdf"],
      "DECISION-RELEVANT: any large new load lands on the post-2028 supply question; "
      "withdrew from IURC jurisdiction 2012-01-07 per the same ordinance."),
    R(LOGA, "FLOORS", "Class eligibility floors", "eligibility", "LOGA-FLOORS",
      "Floors not restated in the 2025 documents", None, None,
      "class eligibility definitions (incl. the 10,000 kW Industrial Substation floor "
      "URDB carries from 2014) trace to base Ordinance 2018-26 and LMU service rules - "
      "the city's online ordinance archive starts at 2021; records at the Logansport "
      "Clerk-Treasurer", "large classes", "all", "not_held", None,
      "Logansport Clerk-Treasurer ordinance book (records-location)",
      "https://www.logansportutilities.com/rates-requirements-reports",
      "Records-location finding, not a wall: the 2025 ordinance re-prices the classes "
      "without restating their availability text."),
]

# ==========================================================================================
# MISHAWAKA - HTML tariff pages effective 2025-01-01 (Ordinance 5729 plan); Ordinance 5954
# (adopted 2025-11-17) steps rates 2026-01-01 but its Exhibit A is NOT posted online.
# ==========================================================================================
MISH_SRC = ("Mishawaka Utilities posted electric schedules, each stamped 'Effective "
            "January 01, 2025' (comprehensive rate plan 2025-2030; prior adjustment "
            "2020-12-22 was -14%)")
MISH_URL = URL["mishawaka_rate_I_industrial.html"]
E_MISH = "2025-01-01"
MISH_STALE = ("KNOWN LIMIT: Ordinance No. 5954 (adopted 2025-11-17) adjusts rates from "
              "2026-01-01 and its Exhibit A is NOT posted online - these 2025-step values "
              "are the last published figures and are LOW by one step; see "
              "MISH-2026-EXHIBIT-A.")

MISHAWAKA_ROWS = [
    R(MISH, "I", "Rate I - Industrial Power Service", "eligibility", "MISH-I-ELIG",
      "Eligibility floor", 149.0, "kW",
      "all industrial customers through one three-phase meter with monthly billing demand "
      "greater than 149 kW; contracts >=1 year, self-renewing", "secondary or primary",
      "all", "published", E_MISH, MISH_SRC, MISH_URL, MISH_STALE),
    R(MISH, "I", "Rate I - Industrial Power Service", "base_charge", "MISH-I-CUST",
      "Customer charge", 18.35, "$/month", "per service location", "all", "all",
      "published", E_MISH, MISH_SRC, MISH_URL, None),
    R(MISH, "I", "Rate I - Industrial Power Service", "demand", "MISH-I-DEM",
      "Demand charge", 7.00, "$/kW/month",
      "billing demand = greater of 5 kW or month maximum (NO multi-month ratchet)", "all",
      "all", "published", E_MISH, MISH_SRC, MISH_URL,
      "The page ALSO prints: 'OR at the Utility's option: $6.25 per KW ... if ... monthly "
      "power factor is less than 85%' - quoted verbatim; the lower-rate-for-worse-PF "
      "ordering reads inverted; verify against the official ordinance before billing-"
      "grade use."),
    R(MISH, "I", "Rate I - Industrial Power Service", "energy", "MISH-I-EN",
      "Energy charge", 0.0769, "$/kWh", "all kWh", "all", "all", "published", E_MISH,
      MISH_SRC, MISH_URL, None),
    R(MISH, "I", "Rate I - Industrial Power Service", "rider", "MISH-I-PRIM-CRED",
      "Primary-voltage credit", -0.39, "$/kW/month",
      "customer takes service at primary voltage (customer-owned transformation); "
      "additionally, primary METERING multiplies measured demand+energy by 0.98", "primary",
      "all", "published", E_MISH, MISH_SRC, MISH_URL,
      "No transmission-voltage class exists at Mishawaka - primary with customer "
      "transformers is the top of the delivery ladder."),
    R(MISH, "P", "Rate P - Commercial Power Service (headline)", "demand", "MISH-P-DEM",
      "Demand charge", 7.90, "$/kW/month",
      "class <150 kW; customer charge $20.85; energy $0.0843/kWh; primary credit "
      "$0.44/kW", "all", "all", "published", E_MISH, MISH_SRC,
      "https://mishawaka.in.gov/government/departments/mishawaka-utilities/rates-and-"
      "charges/rate-p-commercial-power-service/", None),
    R(MISH, "C", "Rate C - Commercial Service (headline)", "energy", "MISH-C-EN",
      "Energy charge", 0.1377, "$/kWh", "all kWh; customer charge $6.00/mo",
      "small commercial", "all", "published", E_MISH, MISH_SRC,
      "https://mishawaka.in.gov/government/departments/mishawaka-utilities/rates-and-"
      "charges/rate-c-commercial-service/", None),
    R(MISH, "R", "Rate R - Residential (headline)", "energy", "MISH-R-EN-B1",
      "Energy - first 500 kWh", 0.1151, "$/kWh",
      "customer charge $6.00/dwelling; over-500 block $0.1059", "residential", "all",
      "published", E_MISH, MISH_SRC,
      "https://mishawaka.in.gov/government/departments/mishawaka-utilities/rates-and-"
      "charges/rate-r-residential-service/", None),
    R(MISH, "TRACKER", "Power cost adjustment - none posted", "rider", "MISH-NO-PCA",
      "No PCA/fuel adjustment on any posted electric schedule", None, None,
      "no adjustment mechanism appears on the posted schedules; the 2025-2030 plan bakes "
      "annual increases instead", "all schedules", "all", "published", E_MISH, MISH_SRC,
      MISH_URL, None),
    R(MISH, "BASE", "2026 rate step", "eligibility", "MISH-2026-EXHIBIT-A",
      "Ordinance 5954 Exhibit A (rates eff 2026-01-01) not published online", None, None,
      "the rates-and-charges index states rates adjust 2026-01-01 per Ordinance No. 5954 "
      "(adopted 2025-11-17), but the ordinance exhibit is not posted; official tariff via "
      "the Mishawaka Utilities Business Office (100 Lincolnway W) or the City Clerk",
      "all schedules", "all", "not_held", None,
      "Mishawaka rates-and-charges index (cached)", URL["mishawaka_rates_index.html"],
      "Records-location finding: the CURRENT (2026) numbers exist on paper, one step "
      "above the 2025 figures loaded here."),
    R(MISH, "SUPPLY", "Wholesale supply", "eligibility", "MISH-SUPPLY",
      "Wolverine contract; PJM market exposure 2030+", None, None,
      "2024 GM letter cites 'anticipated increases in our energy costs through 2030, "
      "particularly in our Wolverine contract rates'; the plan 'eliminates market "
      "volatility in years 2030 through 2035 in a liquid PJM market'; contract subject to "
      "renegotiation in 2030", "system", "all", "published", None,
      "Mishawaka Utilities rate-plan news + summary pages, 2024-05-08 (cached)",
      "https://mishawaka.in.gov/news/mishawaka-utilities-electric-rate-plan-summary/",
      None),
]

# ==========================================================================================
# PERU - HTML tariff effective 2026-06-01; quarterly 36835-S3 tracker; IMPA member since
# 1983 (full requirements).
# ==========================================================================================
PERU_SRC = "Peru Utilities electric rates page, schedules stamped 'Effective June 1, 2026'"
PERU_URL = URL["peru_electric_rates_page.html"]
E_PERU = "2026-06-01"

PERU_ROWS = [
    R(PERU, "PS", "Power Service", "eligibility", "PERU-PS-ELIG", "Eligibility floor",
      50.0, "kW", "maximum load requirement >=50 kW through one meter", "primary or "
      "secondary", "all", "published", E_PERU, PERU_SRC, PERU_URL, None),
    R(PERU, "PS", "Power Service", "demand", "PERU-PS-DEM-PRI", "Demand charge - primary",
      6.44, "$/kW/month", "15-min demand; billing floor 50 kW", "primary", "all",
      "published", E_PERU, PERU_SRC, PERU_URL, None),
    R(PERU, "PS", "Power Service", "demand", "PERU-PS-DEM-SEC", "Demand charge - secondary",
      7.11, "$/kW/month", "15-min demand; billing floor 50 kW", "secondary", "all",
      "published", E_PERU, PERU_SRC, PERU_URL, None),
    R(PERU, "PS", "Power Service", "energy", "PERU-PS-EN-PRI", "Energy charge - primary",
      0.095074, "$/kWh", "all kWh, in addition to demand charge", "primary", "all",
      "published", E_PERU, PERU_SRC, PERU_URL, None),
    R(PERU, "PS", "Power Service", "energy", "PERU-PS-EN-SEC", "Energy charge - secondary",
      0.101105, "$/kWh", "all kWh", "secondary", "all", "published", E_PERU, PERU_SRC,
      PERU_URL, None),
    R(PERU, "PS", "Power Service", "base_charge", "PERU-PS-MIN",
      "Minimum monthly charge - secondary", 355.81, "$/month", "stated minimum, secondary",
      "secondary", "all", "published", E_PERU, PERU_SRC, PERU_URL, None),
    R(PERU, "PS", "Power Service", "rider", "PERU-PS-SUBST-CRED",
      "Customer-owned substation credit", -0.25, "$/kW/month",
      "customer furnishes complete substation; >480 V metering also reduces demand+energy "
      "measurements 2%", "customer-substation", "all", "published", E_PERU, PERU_SRC,
      PERU_URL, None),
    R(PERU, "PS", "Power Service", "eligibility", "PERU-PS-OFFPEAK",
      "Off-peak option - capped at 6,000 kW aggregate", None, None,
      "billing demand = greater of on-peak kW or 50% of off-peak high, floor 500 kW; "
      "availability limited to an AGGREGATE 6,000 kW first-come first-served", "PS "
      "customers >=500 kW", "all", "published", E_PERU, PERU_SRC, PERU_URL, None),
    R(PERU, "PS", "Power Service", "rider", "PERU-PPCAT",
      "Quarterly purchased-power tracker (Cause 36835-S3) - cumulative factor", 0.001178,
      "$/kWh", "current cumulative PS factor (this quarter's change -0.000986); bills "
      "from the April 2026 cycle per the notice on the same page", "PS", "all",
      "published", "2026-04-01", PERU_SRC, PERU_URL, None),
    R(PERU, "ED", "Rider ED - Economic Development (Ordinance 12-2011)", "energy",
      "PERU-ED-EN", "ED rider energy rate", 0.06072, "$/kWh",
      "new/additional load 300-1,500 kW, term <=3 years; rate = average IMPA purchase "
      "cost May 2010-Apr 2011, trued up monthly to ACTUAL IMPA cost", "new loads 300-"
      "1,500 kW", "all", "published", E_PERU, PERU_SRC, PERU_URL,
      "Tops out at 1.5 MW - not a data-centre vehicle; the CP Reduction Credit "
      "(>=1,000 kW, curtail at the utility-signalled daily peak, credit = avoided "
      "contribution x supplier demand base rates) is the more interesting hook."),
    R(PERU, "RS", "Residential (headline)", "energy", "PERU-RS-EN-B1",
      "Energy - first 300 kWh", 0.12848, "$/kWh",
      "customer charge $10.29 in-city; blocks 0.11870 next 700 / 0.12207 above 1,000",
      "residential", "all", "published", E_PERU, PERU_SRC, PERU_URL, None),
    R(PERU, "SUPPLY", "Wholesale supply", "eligibility", "PERU-SUPPLY",
      "IMPA full-requirements member since 1983", None, None,
      "Peru became a full-requirements IMPA purchaser in 1983 (utility's own history "
      "PDF); generation heritage since 1885 but no self-supply today", "system", "all",
      "published", None, "Peru Utilities 'History of electric generation' (cached "
      "peru_history_electric_generation.pdf)",
      "https://www.peruutilities.com/wp-content/uploads/a8f4b5c0e9f19d1aa900de3524a1f9b4.pdf",
      None),
]

# ==========================================================================================
# JASPER - rates codified in Municipal Code ch. 11.08 (figures per Ord 2022-8, 2022-06-22);
# ch. 11.09 = IMPA Power Sales Contract to 2042 (rolling).  Municode extraction cached.
# ==========================================================================================
JASP_SRC = ("Jasper Municipal Code Title 11 ch. 11.08 (rate figures per Ord. No. 2022-8, "
            "adopted 2022-06-22), Municode Supplement 11 (content through 2026-06-09, "
            "posted 2026-06-15), API extraction cached")
JASP_URL = "https://library.municode.com/in/jasper/codes/code_of_ordinances"
E_JASP = "2022-06-22"

JASPER_ROWS = [
    R(JASP, "GSD", "General Service Demand", "eligibility", "JASP-GSD-ELIG",
      "Eligibility floor", 50.0, "kVA", "the only demand-billed class; >=50 kVA with no "
      "upper bound", "all voltages", "all", "published", E_JASP, JASP_SRC, JASP_URL,
      "Jasper has NO large-industrial class above GSD - a big load takes GSD or a "
      "contract."),
    R(JASP, "GSD", "General Service Demand", "base_charge", "JASP-GSD-FAC",
      "Monthly facilities charge", 89.61, "$/month", "per month", "all", "all",
      "published", E_JASP, JASP_SRC, JASP_URL, None),
    R(JASP, "GSD", "General Service Demand", "demand", "JASP-GSD-DEM",
      "Monthly demand charge", 16.04, "$/kVA/month",
      "billing demand grossed to 100% power factor (kW x 100/PF)", "all", "all",
      "published", E_JASP, JASP_SRC, JASP_URL,
      "100%-PF basis is stricter than the usual 90-97% clauses - at PF 0.95 the "
      "effective rate is $16.88/kVA."),
    R(JASP, "GSD", "General Service Demand", "energy", "JASP-GSD-EN",
      "Monthly energy charge", 0.045599, "$/kWh", "printed 4.5599 cents/kWh; metered at "
      "primary: kWh reduced 3%", "all", "all", "published", E_JASP, JASP_SRC, JASP_URL,
      None),
    R(JASP, "GSD", "General Service Demand", "ratchet", "JASP-GSD-RATCHET",
      "60% / 11-month ratchet", 60.0, "% of 11-month high",
      "billing demand >= 60% of highest billing demand in preceding 11 months, floor 50 "
      "kVA", "all", "all", "published", E_JASP, JASP_SRC, JASP_URL, None),
    R(JASP, "R", "Residential (headline)", "energy", "JASP-R-EN", "Energy charge",
      0.093229, "$/kWh", "printed 9.3229 cents; facilities $10.67/mo", "residential",
      "all", "published", E_JASP, JASP_SRC, JASP_URL, None),
    R(JASP, "GSS", "General Service Small (headline)", "energy", "JASP-GSS-EN",
      "Energy charge", 0.096926, "$/kWh", "class <50 kW avg demand; facilities $20.36/mo",
      "small commercial", "all", "published", E_JASP, JASP_SRC, JASP_URL, None),
    R(JASP, "PCA", "Power and energy cost adjustment (11.08.075)", "rider", "JASP-PCA",
      "Purchased power cost adjustment tracking factor", None, None,
      "code sec. 11.08.075: monthly tracking factor on changes in purchased power cost, "
      "applicable to R/GSS/GSD; current factor value published on bills, not online",
      "R, GSS, GSD", "all", "published", E_JASP, JASP_SRC, JASP_URL,
      "Current factor VALUE is a records-location item (utilities office); mechanism is "
      "published."),
    R(JASP, "SUPPLY", "Wholesale supply", "eligibility", "JASP-SUPPLY",
      "IMPA Power Sales Contract to 2042, rolling", None, None,
      "ch. 11.09 (Ord 2007-27): IMPA Power Sales Contract in effect until 2042-04-01, "
      "auto-extending one year annually beginning 2032-04-01 (rolling ~10-yr notice); "
      "former city power plant scrapped 2014 - no self-generation", "system", "all",
      "published", None, JASP_SRC, JASP_URL, None),
]

# ==========================================================================================
# LEBANON - rates published inline at lebanon-utilities.com/rates; base approved via
# 30-Day Filing 50535 (2022-06-28, URT) on the Cause 44142 (2012-09-12) book; Lebanon has
# since left IURC rate jurisdiction (FY2025 census).  LEAP-corridor muni.
# ==========================================================================================
LEBN_SRC = ("Lebanon Utilities rates page (captured 2026-08-18): PPL/ILP sheet text; "
            "lineage per Ordinance 2022-21 recitals - Cause 44142 order 2012-09-12 rates "
            "adjusted by IURC conference minutes 'Cause No. 50535' 2022-06-28 (URT)")
LEBN_URL = URL["lebanon_utilities_rates_page_20260818.html"]
E_LEBN = "2022-07-01"

LEBANON_ROWS = [
    R(LEBN, "PPL", "Primary Power and Light Service (tracker class 'ILP')", "eligibility",
      "LEBN-PPL-ELIG", "Eligibility floor", 50.0, "kVA",
      "contracted capacity not less than 50 kVA; one-year term", "all voltages", "all",
      "published", E_LEBN, LEBN_SRC, LEBN_URL, None),
    R(LEBN, "PPL", "Primary Power and Light Service", "base_charge", "LEBN-PPL-CUST",
      "Customer charge", 98.51, "$/month", "per month", "all", "all", "published", E_LEBN,
      LEBN_SRC, LEBN_URL, None),
    R(LEBN, "PPL", "Primary Power and Light Service", "demand", "LEBN-PPL-DEM",
      "Maximum load charge", 17.38, "$/kVA/month",
      "billing max load = greater of month max or 50 kVA (monthly floor; no multi-month "
      "ratchet stated); metered <=480 V: demand +1%, energy +1.5%", "all", "all",
      "published", E_LEBN, LEBN_SRC, LEBN_URL, None),
    R(LEBN, "PPL", "Primary Power and Light Service", "energy", "LEBN-PPL-EN-B1",
      "Energy - first 300 hours use of billing maximum load", 0.0358, "$/kWh",
      "hours-use block", "all", "all", "published", E_LEBN, LEBN_SRC, LEBN_URL, None),
    R(LEBN, "PPL", "Primary Power and Light Service", "energy", "LEBN-PPL-EN-B2",
      "Energy - over 300 hours use", 0.0310, "$/kWh", "hours-use block", "all", "all",
      "published", E_LEBN, LEBN_SRC, LEBN_URL, None),
    R(LEBN, "PPL", "Quarterly rate adjustment (Cause 36835-S3)", "rider",
      "LEBN-TRK-ILP-KVA", "Tracker - Rate ILP demand leg", 2.829798, "$/kVA/month",
      "Q3-2026 factor, applicable Jul-Sep 2026, bills from July 2026 cycle; supplier "
      "IMPA", "PPL/ILP class", "all", "published", "2026-07-01",
      "Lebanon 2026 3rd Quarter Tracker legal notice (cached PDF)",
      URL["lebanon_2026_3rd_quarter_tracker.pdf"],
      "A +$2.83/kVA tracker on a $17.38 base = +16% on the demand leg this quarter - "
      "Lebanon's IMPA cost flows disproportionately through the demand side."),
    R(LEBN, "PPL", "Quarterly rate adjustment", "rider", "LEBN-TRK-ILP-KWH",
      "Tracker - Rate ILP energy leg", 0.010946, "$/kWh", "Q3-2026 factor", "PPL/ILP",
      "all", "published", "2026-07-01",
      "Lebanon 2026 3rd Quarter Tracker legal notice",
      URL["lebanon_2026_3rd_quarter_tracker.pdf"], None),
    R(LEBN, "RS", "Residential (headline)", "energy", "LEBN-RS-EN-B1",
      "Energy - first 300 kWh", 0.0952, "$/kWh",
      "customer charge $7.88; blocks 0.0893 next 700 / 0.0819 over 1,000; Q3-2026 "
      "tracker +0.019214/kWh", "residential", "all", "published", E_LEBN, LEBN_SRC,
      LEBN_URL, None),
    R(LEBN, "EDR", "Economic development rider", "eligibility", "LEBN-EDR",
      "EDR (Res 2017-03 / Ord 2017-11) - mirrors the IMPA EDR", None, None,
      "qualifying load = new/additional demand >=1 MW at one delivery point plus >=$1M "
      "capital investment (source docs are image scans, cached)", "new large loads",
      "all", "published", "2017-06-01",
      "Lebanon Resolution 2017-03 + Ordinance 2017-11 (image scans, cached)",
      "https://lebanon-utilities.com/rates/", None),
    R(LEBN, "LEAP", "LEAP district electric rate", "eligibility", "LEBN-LEAP",
      "No LEAP-specific electric rate is published", None, None,
      "the LEAP-district ordinance posted on the rates page (2025-08 + Resolution "
      "2025-02) is WASTEWATER only; Lebanon publishes no electric rate specific to the "
      "LEAP corridor", "LEAP district", "all", "published", None, LEBN_SRC, LEBN_URL,
      "Decision-relevant absence: a LEAP-scale load would be negotiated (IMPA wholesale "
      "+ Lebanon delivery), not taken off the published PPL sheet."),
]

# ==========================================================================================
# CRAWFORDSVILLE CEL&P - compiled book = 30-Day 50561 (2022-06-01) + EV 50602, under Cause
# 45420 order 2021-04-21, URT-adjusted, eff 2022-07-01.  NOT IN URDB AT ALL.
# PENDING: amending rate ordinance introduced 2026-07-13, hearing 2026-08-10.
# ==========================================================================================
CRAW_SRC = ("CEL&P compiled tariff 'Tariff on File' (sheets stamped 30-Day Filing No. "
            "50561 approved conference minutes 2022-06-01, issued under IURC order "
            "2021-04-21 in Cause 45420 AND ADJUSTED FOR URT REPEAL, effective service "
            "on/after 2022-07-01; EV sheets 50602)")
CRAW_URL = URL["celp_tariff_with_ev_fast_charge_jan2025.pdf"]
E_CRAW = "2022-07-01"
CRAW_PEND = ("PENDING: proposed amending rate ordinance introduced 2026-07-13, public "
             "hearing 2026-08-10 (IC 8-1.5-3, legal notice cached) - re-pull after "
             "adoption.")

CRAWFORDSVILLE_ROWS = [
    R(CRAW, "PP", "Power Provider Service (PP)", "eligibility", "CRAW-PP-ELIG",
      "Eligibility floor", 50.0, "kW", "load >=50 kW", "all voltages", "all", "published",
      E_CRAW, CRAW_SRC, CRAW_URL,
      "Crawfordsville has NO rows in in_urdb_rates - this utility is NEW to the "
      "warehouse; utility string coined to match the house pattern. " + CRAW_PEND),
    R(CRAW, "PP", "Power Provider Service (PP)", "base_charge", "CRAW-PP-CUST",
      "Customer charge", 295.77, "$/month", "per meter per month", "all", "all",
      "published", E_CRAW, CRAW_SRC, CRAW_URL, None),
    R(CRAW, "PP", "Power Provider Service (PP)", "demand", "CRAW-PP-DEM", "Demand charge",
      29.29, "$/kVA/month", "monthly kVA billing demand", "all", "all", "published",
      E_CRAW, CRAW_SRC, CRAW_URL,
      "The HIGHEST demand rate in the muni set - but the energy rate (2.76 c) is near "
      "wholesale; CEL&P recovers almost everything on the demand leg."),
    R(CRAW, "PP", "Power Provider Service (PP)", "energy", "CRAW-PP-EN", "Energy charge",
      0.027624, "$/kWh", "all kWh", "all", "all", "published", E_CRAW, CRAW_SRC, CRAW_URL,
      None),
    R(CRAW, "PP", "Power Provider Service (PP)", "ratchet", "CRAW-PP-RATCHET",
      "50% / 12-month ratchet", 50.0, "% of 12-month high",
      "minimum monthly kW demand >= 50% of highest recorded kW over the prior 12 months; "
      "metered <=480 V grossed +2%; customer-substation credit $0.30/kVA", "all", "all",
      "published", E_CRAW, CRAW_SRC, CRAW_URL, None),
    R(CRAW, "PPOP", "PP Off-Peak rider", "eligibility", "CRAW-PPOP",
      "Off-peak rider - capped at 30,000 kW aggregate", None, None,
      "off-peak rider on PP with monthly billing-demand floor 100 kVA; program capped at "
      "30,000 kW aggregate", "PP customers", "all", "published", E_CRAW, CRAW_SRC,
      CRAW_URL, None),
    R(CRAW, "IP", "Industrial Power Service (IP)", "eligibility", "CRAW-IP-FLOOR",
      "Eligibility floor", 10000.0, "kW",
      "minimum load requirement 10 MW or more, directly fed from the Utility's 138 kV "
      "transmission system; customer owns all 138 kV transformation", "transmission "
      "(138 kV)", "all", "published", E_CRAW, CRAW_SRC, CRAW_URL,
      "One of only three Indiana muni schedules written for a 10 MW+ transmission-fed "
      "customer (with Frankfort IP and Richmond TS). " + CRAW_PEND),
    R(CRAW, "IP", "Industrial Power Service (IP)", "base_charge", "CRAW-IP-CUST",
      "Customer charge", 591.62, "$/month", "per meter per month", "transmission", "all",
      "published", E_CRAW, CRAW_SRC, CRAW_URL, None),
    R(CRAW, "IP", "Industrial Power Service (IP)", "demand", "CRAW-IP-DEM", "Demand charge",
      22.77, "$/kVA/month", "kVA of billing demand; ratchet 50% of 12-month high",
      "transmission", "all", "published", E_CRAW, CRAW_SRC, CRAW_URL, None),
    R(CRAW, "IP", "Industrial Power Service (IP)", "energy", "CRAW-IP-EN", "Energy charge",
      0.026489, "$/kWh", "all kWh", "transmission", "all", "published", E_CRAW, CRAW_SRC,
      CRAW_URL, None),
    R(CRAW, "GPL", "General Power Large (headline)", "demand", "CRAW-GPL-DEM",
      "Demand charge", 6.41, "$/kW/month",
      "class >10 to <=50 kW; customer charge $44.37 single-phase / $88.73 three-phase; "
      "energy $0.071389/kWh", "secondary", "all", "published", E_CRAW, CRAW_SRC, CRAW_URL,
      None),
    R(CRAW, "RS", "Residential (headline)", "energy", "CRAW-RS-EN", "Energy charge",
      0.101720, "$/kWh", "customer charge $14.79/mo", "residential", "all", "published",
      E_CRAW, CRAW_SRC, CRAW_URL, None),
    R(CRAW, "EDR", "Economic Development Rider - IMPA", "rider", "CRAW-EDR-IMPA",
      "IMPA wholesale credit passthrough", None, None,
      "qualifying: >=1 MW new demand + >=$1M investment; IMPA credit passed through in "
      "full on schedules IP and PP: 20% months 1-2 [sic, as printed], 15% months 13-24, "
      "10% months 25-35 [sic], 10% months 37-48, 5% months 49-60", "IP and PP", "all",
      "published", "2021-07-01", CRAW_SRC, CRAW_URL,
      "The printed month ranges contain typos (1-2, 25-35) - transcribed as printed."),
    R(CRAW, "APPX", "Appendix A/B tracking factors", "rider", "CRAW-PPCAT-CURRENT",
      "Current PPCAT factor values", None, None,
      "every schedule is 'Subject to the provisions of Appendix A and Appendix B', but "
      "the appendices' CURRENT factor values are not compiled into the published PDF and "
      "no separate tracker sheet is posted on celp.com", "all schedules", "all",
      "not_held", None, "CEL&P utility office (records-location)",
      "https://celp.com/services/",
      "A true not_held: the tracker mechanism is published, its current value is not."),
]

# ==========================================================================================
# COLUMBIA CITY - Ordinance 2026-5 (passed 2026-02-10; rates from the 2026-05-01 billing
# cycle; Phase I-2026 / II-2027 / III-2028).  Exhibit A is an IMAGE SCAN - values below
# were transcribed by human-visual page reads (sha256-pinned).  Class terms per the 2021
# O.W. Krohn tariff book (text-native).
# ==========================================================================================
COLC_SRC = ("Columbia City Ordinance 2026-5 'Electric Rates' Exhibit A (passed/adopted "
            "2026-02-10; rates start with the 2026-05-01 billing cycle; Phase I-2026 "
            "column loaded; prepared with Baker Tilly); class terms per the 2021 'Rates - "
            "Phase I' tariff book by O.W. Krohn & Associates")
COLC_URL = URL["cc_ordinance_2026-5_electric_rates.pdf"]
E_COLC = "2026-05-01"
COLC_IMG = ("Ordinance exhibit is an image scan: transcribed by human-visual page read "
            "2026-08-18, sha256-pinned in the loader.")

COLUMBIA_CITY_ROWS = [
    R(COLC, "GS-L", "General Service (Large)", "eligibility", "COLC-GSL-ELIG",
      "Eligibility threshold", 100.0, "kW",
      "billing capacity exceeds 100 kW for 3 consecutive months (2021 book definition)",
      "secondary", "all", "published", E_COLC, COLC_SRC, COLC_URL, None),
    R(COLC, "GS-L", "General Service (Large)", "base_charge", "COLC-GSL-CUST",
      "Customer charge", 100.36, "$/month", "Phase I-2026 (II-2027 $101.37, III-2028 "
      "$102.38)", "secondary", "all", "published", E_COLC, COLC_SRC, COLC_URL, COLC_IMG),
    R(COLC, "GS-L", "General Service (Large)", "demand", "COLC-GSL-DEM",
      "Maximum load charge", 7.51, "$/kVA/month",
      "per kVA of billing maximum load; billing minimum = 50% of transformer nameplate; "
      "ratchet (2021 book): >= 60% of highest monthly max in preceding 12 months",
      "secondary", "all", "published", E_COLC, COLC_SRC, COLC_URL, None),
    R(COLC, "GS-L", "General Service (Large)", "energy", "COLC-GSL-EN", "Energy charge",
      0.10154, "$/kWh", "all kWh, Phase I-2026", "secondary", "all", "published", E_COLC,
      COLC_SRC, COLC_URL, None),
    R(COLC, "GS-I", "General Service Industrial", "eligibility", "COLC-GSI-ELIG",
      "Eligibility threshold", 800.0, "kW",
      "billing capacity exceeds 800 kW for 3 consecutive months (2021 book definition)",
      "secondary or primary", "all", "published", E_COLC, COLC_SRC, COLC_URL, None),
    R(COLC, "GS-I", "General Service Industrial", "base_charge", "COLC-GSI-CUST",
      "Customer charge", 126.77, "$/month", "Phase I-2026 (II $128.03, III $129.31)",
      "all", "all", "published", E_COLC, COLC_SRC, COLC_URL, COLC_IMG),
    R(COLC, "GS-I", "General Service Industrial", "demand", "COLC-GSI-DEM",
      "Maximum load charge", 7.45, "$/kVA/month",
      "per kVA; 50%-of-nameplate minimum; 60%/12-month ratchet per the 2021 book; "
      "secondary-metered kWh x1.05", "all", "all", "published", E_COLC, COLC_SRC,
      COLC_URL, None),
    R(COLC, "GS-I", "General Service Industrial", "energy", "COLC-GSI-EN", "Energy charge",
      0.09872, "$/kWh", "all kWh, Phase I-2026 (II 0.09971, III 0.10954)", "all", "all",
      "published", E_COLC, COLC_SRC, COLC_URL, None),
    R(COLC, "R", "Residential (headline)", "energy", "COLC-R-EN-B1",
      "Energy - first 500 kWh", 0.13479, "$/kWh",
      "customer charge $15.85; over-500 block 0.12740; renewable-generation surcharge "
      "$50.00/month", "residential", "all", "published", E_COLC, COLC_SRC, COLC_URL, None),
    R(COLC, "ECA", "Energy Cost Adjustment Tracking Factor", "rider", "COLC-ECA-MECH",
      "Quarterly ECA - mechanism", None, None,
      "quarterly ECA applicable to all metered rates; legacy authority = IURC order "
      "1997-10-22 in Cause 40768; tracks changes from the 2020 IMPA Base Rates & Charges; "
      "an example factor $0.027609/kWh appears in Ord 2024-10 Exhibit B (image-only, not "
      "independently verified); CURRENT-quarter factor is published in ordinances/bills, "
      "not online", "all metered rates", "all", "published", E_COLC, COLC_SRC, COLC_URL,
      "Current ECA value = records-location item (clerk/utility office)."),
]

# ==========================================================================================
# TELL CITY - 2022 booklet (Electric Board Resolution R220615A 2022-06-15; Ordinance 1190
# adopted 2022-07-07, effective July 2022 consumption).  IMPA member.  E2 (>=10,000 kVA)
# passes IMPA Power Sales Rate Schedule 'B' through at cost + $3.00/kVA distribution.
# ==========================================================================================
TELL_SRC = ("Tell City Electric Dept 2022 Revised Rates and Charges Booklet (tariff rates "
            "approved by Electric Board Resolution R220615A 2022-06-15; Ordinance No. 1190 "
            "adopted 2022-07-07, effective July 2022 consumption; booklet approved by "
            "Resolution R220920A)")
TELL_URL = URL["tell_city_2022_revised_rates_and_charges_booklet.pdf"]
E_TELL = "2022-07-01"

TELL_CITY_ROWS = [
    R(TELL, "E", "Tariff E - Three Phase Large Power (400-2,000 kVA)", "eligibility",
      "TELL-E-ELIG", "Class window", 400.0, "kVA",
      "three-phase large power 400-2,000 kVA; written contract required", "secondary or "
      "primary", "all", "published", E_TELL, TELL_SRC, TELL_URL, None),
    R(TELL, "E", "Tariff E", "base_charge", "TELL-E-FAC", "Facility charge", 350.00,
      "$/month", "per month", "all", "all", "published", E_TELL, TELL_SRC, TELL_URL, None),
    R(TELL, "E", "Tariff E", "demand", "TELL-E-DEM", "Demand charge", 26.45,
      "$/kVA/month", "billing demand = greatest of coincident-hour 15-min max, 60% of "
      "highest monthly coincident peak in preceding 11 months, or contract minimum",
      "all", "all", "published", E_TELL, TELL_SRC, TELL_URL, None),
    R(TELL, "E", "Tariff E", "energy", "TELL-E-EN", "Energy charge - on peak all kWh",
      0.03757, "$/kWh", "all kWh", "all", "all", "published", E_TELL, TELL_SRC, TELL_URL,
      None),
    R(TELL, "E", "Tariff E", "rider", "TELL-PPT-E-KWH",
      "Purchased power tracker - Tariff E energy leg", 0.011564, "$/kWh",
      "Q3-2026 factor (consumption Jul-Sep 2026); mechanism cited in the booklet as PSCI "
      "order 1989-12-13 'Cause No. 36836-S3' [sic - other IMPA munis print 36835-S3]",
      "Tariff E", "all", "published", "2026-07-01",
      "Tell City 2026 3rd Quarter Tracker legal notice, dated 2026-05-27 (image scan, "
      "human-visual transcription, sha256-pinned)",
      URL["tell_city_2026_3rd_qtr_tracker.pdf"], None),
    R(TELL, "E", "Tariff E", "rider", "TELL-PPT-E-KVA",
      "Purchased power tracker - Tariff E demand leg", -2.89, "$/kVA/month",
      "Q3-2026 factor - currently a demand-leg CREDIT", "Tariff E", "all", "published",
      "2026-07-01", "Tell City 2026 3rd Quarter Tracker legal notice",
      URL["tell_city_2026_3rd_qtr_tracker.pdf"], None),
    R(TELL, "E2", "Tariff E2 - >=10,000 kVA Three Phase Large Power", "eligibility",
      "TELL-E2-ELIG", "Eligibility floor", 10000.0, "kVA",
      "three-phase large power >=10,000 kVA (booklet availability text: '(10,000 kW) "
      "service or greater'); written agreement; initial term >=1 year", "primary/"
      "transmission-fed", "all", "published", E_TELL, TELL_SRC, TELL_URL, None),
    R(TELL, "E2", "Tariff E2", "base_charge", "TELL-E2-FAC", "Facility charge", 1000.00,
      "$/month", "per month", "E2", "all", "published", E_TELL, TELL_SRC, TELL_URL, None),
    R(TELL, "E2", "Tariff E2", "demand", "TELL-E2-DEM-DIST",
      "Distribution demand charge - customer peak", 3.00, "$/kVA/month",
      "minimum distribution demand = customer contract or 10,000 kVA, whichever greater",
      "E2", "all", "published", E_TELL, TELL_SRC, TELL_URL, None),
    R(TELL, "E2", "Tariff E2", "rider", "TELL-E2-WHOLESALE-PASS",
      "Base demand/energy/reactive = IMPA Rate Schedule 'B' pass-through", None, None,
      "base charges include a Base Demand Charge, Base Energy Charge and Base Reactive "
      "Demand Charge based on IMPA Power Sales Rate Schedule 'B'; billed at the current "
      "wholesale rate(s) of power purchased for the most recent month; reactive billed "
      "above 97% PF", "E2", "all", "published", E_TELL, TELL_SRC, TELL_URL,
      "Same design as Anderson ISTP: at >=10 MVA Tell City resells IMPA at cost plus "
      "$3.00/kVA + $1,000/mo. The E2 tracker line in the Q3-2026 notice is folded into "
      "the wholesale pass-through."),
    R(TELL, "E1", "2,000-10,000 kVA band", "eligibility", "TELL-E1-GAP",
      "No printed schedule covers 2,000-10,000 kVA", None, None,
      "the booklet's classes step from Tariff E (400-2,000 kVA) to Tariff E2 (>=10,000 "
      "kVA); 'E1' is referenced once in the tracker section but has no schedule in the "
      "booklet - the band is evidently contract service", "2-10 MVA loads", "all",
      "published", E_TELL, TELL_SRC, TELL_URL, None),
    R(TELL, "F1", "Tariff F1 - 3-phase 50-400 kVA (headline)", "demand", "TELL-F1-DEM",
      "Demand charge", 11.04, "$/kVA/month", "facility charge $55.00/mo", "secondary",
      "all", "published", E_TELL, TELL_SRC, TELL_URL, None),
    R(TELL, "A", "Tariff A - Residential (headline)", "energy", "TELL-A-EN",
      "Energy charge", 0.12407, "$/kWh", "all kWh; facility charge $28.00/mo",
      "residential", "all", "published", E_TELL, TELL_SRC, TELL_URL, None),
]

# ==========================================================================================
# SOUTHEASTERN INDIANA REMC - board sheets approved 2025-06-16 eff 2025-10-01; UIPS-1 and
# CPS-1 revised/approved/effective 2025-10-20.  Supplier: Hoosier Energy (member).
# The URDB-era IPS-2/IPS-4 (5,000 kW) are SUPERSEDED by UIPS-1 in the current book.
# ==========================================================================================
SEI_SRC = ("Southeastern Indiana REMC board-approved rate schedules (seiremc.com/rates): "
           "core sheets approved 2025-06-16 effective 2025-10-01; UIPS-1/CPS-1 revised, "
           "approved and effective 2025-10-20")
E_SEI = "2025-10-01"
E_SEI2 = "2025-10-20"

SEI_ROWS = [
    R(SEI, "UIPS-1", "Unbundled Large Industrial Power Service", "eligibility",
      "SEI-UIPS1-ELIG", "Eligibility floor", 5000.0, "kW",
      "minimum demand requirement 5,000 kW monthly at a single location, served under "
      "Hoosier Energy's STANDARD WHOLESALE TARIFF", "all voltages", "all", "published",
      E_SEI2, SEI_SRC, URL["UIPS-1_Unbundled_Large_Industrial_Power_Service.pdf"],
      "This is the successor to the URDB-era IPS-2/IPS-4 5,000-kW schedules: the co-op "
      "now passes Hoosier's unbundled 4-part wholesale demand design straight through."),
    R(SEI, "UIPS-1", "Unbundled Large Industrial Power Service", "base_charge",
      "SEI-UIPS1-CUST", "Service charge", 125.00, "$/month", "per month", "all", "all",
      "published", E_SEI2, SEI_SRC,
      URL["UIPS-1_Unbundled_Large_Industrial_Power_Service.pdf"], None),
    R(SEI, "UIPS-1", "Unbundled Large Industrial Power Service", "demand",
      "SEI-UIPS1-DEM-SPROD", "Summer Production billing demand", 10.65, "$/kW/month",
      "Jun-Aug: clock-hour demand COINCIDENT with MISO's estimated system peak (during "
      "Hoosier-noticed Load Control Periods); Sep-Nov: average of the Jun-Aug coincident "
      "demands", "all", "all", "published", E_SEI2, SEI_SRC,
      URL["UIPS-1_Unbundled_Large_Industrial_Power_Service.pdf"],
      "A 4CP-style leg: load absent at the MISO peak hour pays zero on this leg."),
    R(SEI, "UIPS-1", "Unbundled Large Industrial Power Service", "demand",
      "SEI-UIPS1-DEM-WPROD", "Winter Production billing demand", 9.50, "$/kW/month",
      "Dec-Feb: MISO-coincident clock-hour demand; Mar-May: average of Dec-Feb", "all",
      "all", "published", E_SEI2, SEI_SRC,
      URL["UIPS-1_Unbundled_Large_Industrial_Power_Service.pdf"], None),
    R(SEI, "UIPS-1", "Unbundled Large Industrial Power Service", "demand",
      "SEI-UIPS1-DEM-TRANS", "Transmission billing demand", 6.50, "$/kW/month",
      "Mar-May + Sep-Nov: coincident with HOOSIER's system peak; Jun-Aug + Dec-Feb: "
      "coincident with MISO's estimated peak", "all", "all", "published", E_SEI2, SEI_SRC,
      URL["UIPS-1_Unbundled_Large_Industrial_Power_Service.pdf"], None),
    R(SEI, "UIPS-1", "Unbundled Large Industrial Power Service", "demand",
      "SEI-UIPS1-DEM-DLVY", "Delivery billing demand", 3.35, "$/kW/month",
      "highest 30-min demand during Peak Hours; RATCHET: never less than 75% of the "
      "highest billing demand in preceding periods or 5,000 kW", "all", "all",
      "published", E_SEI2, SEI_SRC,
      URL["UIPS-1_Unbundled_Large_Industrial_Power_Service.pdf"], None),
    R(SEI, "UIPS-1", "Unbundled Large Industrial Power Service", "energy",
      "SEI-UIPS1-EN-ON", "Energy charge - on-peak", 0.08015, "$/kWh",
      "on-peak = Jun-Aug and Dec-Feb defined windows (excl. holidays)", "all", "all",
      "published", E_SEI2, SEI_SRC,
      URL["UIPS-1_Unbundled_Large_Industrial_Power_Service.pdf"], None),
    R(SEI, "UIPS-1", "Unbundled Large Industrial Power Service", "energy",
      "SEI-UIPS1-EN-OFF", "Energy charge - off-peak", 0.06515, "$/kWh", "all other hours",
      "all", "all", "published", E_SEI2, SEI_SRC,
      URL["UIPS-1_Unbundled_Large_Industrial_Power_Service.pdf"],
      "kVARh charge $0.01099 above 95% avg PF; PF <97% at delivery demand grossed; "
      "minimum monthly charge >= $0.93/kVA of required transformer capacity; primary "
      "metering -1.5%; customer-owned transformation discount $0.18/kW."),
    R(SEI, "CPS-1", "Commercial Power Service", "demand", "SEI-CPS1-DEM-S",
      "Summer Power Supply demand", 17.50, "$/kW/month",
      "class floor 1,000 kW; bundled companion to UIPS-1 (Delivery leg $6.50/kW, Winter "
      "$13.10/kW)", "all", "all", "published", E_SEI2, SEI_SRC,
      URL["CPS-1_Commercial_Power_Service.pdf"], None),
    R(SEI, "CPS-1", "Commercial Power Service", "energy", "SEI-CPS1-EN-ON",
      "Energy charge - on-peak", 0.08350, "$/kWh", "off-peak $0.06850", "all", "all",
      "published", E_SEI2, SEI_SRC, URL["CPS-1_Commercial_Power_Service.pdf"], None),
    R(SEI, "IPS-1", "Industrial Power Service (1,000 kW)", "demand", "SEI-IPS1-DEM",
      "Retail billing demand charge", 14.50, "$/kW/month",
      "floor 1,000 kW; service charge $125/mo; 30-min peak-hours demand; ratchet 75% of "
      "preceding billing periods' high or 1,000 kW; subject to Hoosier's Industrial "
      "Power Tariff requirements", "all", "all", "published", E_SEI, SEI_SRC,
      URL["IPS-1_Industrial_Power_Service.pdf"], None),
    R(SEI, "IPS-1", "Industrial Power Service (1,000 kW)", "energy", "SEI-IPS1-EN-ON",
      "Energy - on-peak", 0.08365, "$/kWh", "off-peak $0.06865", "all", "all", "published",
      E_SEI, SEI_SRC, URL["IPS-1_Industrial_Power_Service.pdf"], None),
    R(SEI, "IP-1", "Industrial Power Service (500 kW)", "demand", "SEI-IP1-DEM",
      "Retail billing demand charge", 15.00, "$/kW/month",
      "floor 500 kW; service charge $125/mo; ratchet 75% of 11-month high or 500 kW",
      "all", "all", "published", E_SEI, SEI_SRC,
      URL["IP-1_Industrial_Power_Service.pdf"], None),
    R(SEI, "IP-1", "Industrial Power Service (500 kW)", "energy", "SEI-IP1-EN-ON",
      "Energy - on-peak", 0.08800, "$/kWh", "off-peak $0.07300", "all", "all", "published",
      E_SEI, SEI_SRC, URL["IP-1_Industrial_Power_Service.pdf"], None),
    R(SEI, "C-5", "Large Power Service High Load Factor", "demand", "SEI-C5H-DEM-SUM",
      "Demand charge - June through August", 15.50, "$/kW/month",
      "class: >=75 kVA transformer capacity, <4,000 kW, annual load factor >=300 kWh/kW "
      "(~41%); service access fee $125/mo; 15-min NCP", "all", "summer", "published",
      E_SEI, SEI_SRC, URL["C-5_Large_Power_High_Load_Factor.pdf"],
      "The FIRST seasonal demand split in the muni/co-op harvest (the five IOU books "
      "have none)."),
    R(SEI, "C-5", "Large Power Service High Load Factor", "demand", "SEI-C5H-DEM-NONSUM",
      "Demand charge - all other months", 13.50, "$/kW/month", "Sep-May", "all",
      "non_summer", "published", E_SEI, SEI_SRC,
      URL["C-5_Large_Power_High_Load_Factor.pdf"], None),
    R(SEI, "C-5", "Large Power Service High Load Factor", "energy", "SEI-C5H-EN",
      "Energy charge", 0.08350, "$/kWh", "all kWh", "all", "all", "published", E_SEI,
      SEI_SRC, URL["C-5_Large_Power_High_Load_Factor.pdf"], None),
    R(SEI, "C-5", "Large Power Service Low Load Factor", "demand", "SEI-C5L-DEM-SUM",
      "Demand charge - June through August", 8.10, "$/kW/month",
      "LLF fork (<300 kWh/kW); non-summer $7.10; energy blocks 0.10600 first 150 "
      "kWh/kW, 0.09100 next 150, 0.10300 over 300", "all", "summer", "published", E_SEI,
      SEI_SRC, URL["C-5_Large_Power_Low_Load_Factor.pdf"], None),
    R(SEI, "PCT", "Power Cost Tracker", "rider", "SEI-PCT-UIPS",
      "Power Cost Tracker - CPS-1/UIPS-1", 0.00249, "$/kWh",
      "Q3-2026 (Jul/Aug/Sep 2026; approved 2026-05-18): H.E. Tracker $0.00249 + "
      "adjustment $0.00000; explicit Hoosier Energy pass-through", "CPS-1 and UIPS-1",
      "all", "published", "2026-07-01", SEI_SRC + " - PCT Q3 2026", URL["PCT_Q3_2026.pdf"],
      None),
    R(SEI, "PCT", "Power Cost Tracker", "rider", "SEI-PCT-IP",
      "Power Cost Tracker - IP-1/IPS-1", 0.00263, "$/kWh",
      "Q3-2026: H.E. Tracker $0.00249 + tracker adjustment $0.00014", "IP-1 and IPS-1",
      "all", "published", "2026-07-01", SEI_SRC + " - PCT Q3 2026", URL["PCT_Q3_2026.pdf"],
      None),
]

# ==========================================================================================
# SOUTHERN INDIANA POWER (Southern Indiana REC) - only residential figures are published;
# C&I/large-power schedules exist at the co-op office (records-location).  Hoosier member.
# ==========================================================================================
SIP_SRC = ("Southern Indiana Power rates-charges page (captured 2026-08-18; page prints "
           "NO effective date)")
SIP_URL = URL["rates_charges_page.html"]

SIP_ROWS = [
    R(SIP, "GES", "General Electric Service (residential headline)", "energy",
      "SIP-GES-EN", "Energy charge", 0.1214, "$/kWh",
      "facility charge $35.00/month (raised from $32.50 after a cost-of-service study)",
      "residential/general", "all", "published", None, SIP_SRC, SIP_URL,
      "Page carries no effective date - captured state as of 2026-08-18."),
    R(SIP, "GES", "General Electric Service", "rider", "SIP-TRACKER",
      "Wholesale power cost tracker", 0.00260, "$/kWh",
      "page attributes the tracker to 'Hoosier Energy's variable costs'",
      "all published schedules", "all", "published", None, SIP_SRC, SIP_URL, None),
    R(SIP, "CI", "Commercial/industrial and large-power schedules", "eligibility",
      "SIP-CI-NOTPUB", "Not published online", None, None,
      "no C&I or large-power schedule appears anywhere on southernindianapower.com "
      "(sitemap enumerated; only a commercial service application exists); schedules "
      "exist at the co-op office, Tell City IN; 2023 financial page confirms Hoosier "
      "membership and RUS/CFC debt", "C&I classes", "all", "not_held", None,
      "Southern Indiana Power office, Tell City (records-location)", SIP_URL,
      "EIA-861 2023: industrial 309 GWh at a realized 7.18 c/kWh - the cheapest "
      "industrial c/kWh among the non-IOU utilities in this harvest, and its rate sheet "
      "is the one we cannot see. Worth a phone call."),
]

# ==========================================================================================
# SOUTH CENTRAL INDIANA REMC - board sheets effective 2024-02-01.  Supplier: Hoosier
# (IP tracker = 'the tracker billed to SCI REMC by Hoosier Energy').
# ==========================================================================================
SCI_SRC = "South Central Indiana REMC board rate schedules, effective 2024-02-01"
E_SCI = "2024-02-01"

SCI_ROWS = [
    R(SCI, "IP", "Industrial Power Service", "eligibility", "SCI-IP-ELIG",
      "Eligibility floor", 500.0, "kW",
      "minimum monthly demand 500 kW; availability at the SOLE DISCRETION of the "
      "Cooperative, with load characteristics it sets", "all", "all", "published", E_SCI,
      SCI_SRC, URL["Rate-33_IP_2024.pdf"],
      "Discretionary availability is itself decision-relevant: SCI can simply decline a "
      "load it cannot serve."),
    R(SCI, "IP", "Industrial Power Service", "base_charge", "SCI-IP-CUST", "Monthly charge",
      394.40, "$/month", "fixed cost", "all", "all", "published", E_SCI, SCI_SRC,
      URL["Rate-33_IP_2024.pdf"], None),
    R(SCI, "IP", "Industrial Power Service", "demand", "SCI-IP-DEM-PP",
      "Demand - purchased power leg", 11.56, "$/kW/month",
      "30-min max during peak hours (7am-11pm daily); RATCHET 75% of 11-month high, "
      "floor 500 kW", "all", "all", "published", E_SCI, SCI_SRC,
      URL["Rate-33_IP_2024.pdf"], None),
    R(SCI, "IP", "Industrial Power Service", "demand", "SCI-IP-DEM-DIST",
      "Demand - SCI distribution leg", 11.81, "$/kW/month", "same billing demand", "all",
      "all", "published", E_SCI, SCI_SRC, URL["Rate-33_IP_2024.pdf"],
      "Total IP demand = $23.37/kW-mo; the sheet unbundles wholesale vs distribution."),
    R(SCI, "IP", "Industrial Power Service", "energy", "SCI-IP-EN-ON",
      "Energy - purchased power, on-peak", 0.06425, "$/kWh",
      "TOU windows: Jun-Aug 12pm-10pm weekdays; Dec-Feb 7-10am + 6-9pm weekdays (excl. "
      "holidays)", "all", "all", "published", E_SCI, SCI_SRC, URL["Rate-33_IP_2024.pdf"],
      None),
    R(SCI, "IP", "Industrial Power Service", "energy", "SCI-IP-EN-OFF",
      "Energy - purchased power, off-peak", 0.04904, "$/kWh",
      "all other hours; excess net kVARh $0.01009 above 95% PF; PF <97% at max demand "
      "grossed to 97%", "all", "all", "published", E_SCI, SCI_SRC,
      URL["Rate-33_IP_2024.pdf"], None),
    R(SCI, "LI", "Large Industrial Service", "demand", "SCI-LI-DEM-PP",
      "Demand - purchased power leg", 7.42, "$/kW/month",
      "class: transformer capacity >1,000 kVA; monthly charge $394.40; 15-min NCP, NO "
      "multi-month ratchet; distribution leg $13.40/kW (total $20.82); minimum $1.75/kVA "
      "of installed transformer capacity", "all", "all", "published", E_SCI, SCI_SRC,
      URL["Rate-34_LI_2024.pdf"], None),
    R(SCI, "LI", "Large Industrial Service", "energy", "SCI-LI-EN", "Energy charge",
      0.05411, "$/kWh", "all kWh (no TOU)", "all", "all", "published", E_SCI, SCI_SRC,
      URL["Rate-34_LI_2024.pdf"], None),
    R(SCI, "LP", "Large Power Service (300-1,000 kVA headline)", "demand", "SCI-LP-DEM-PP",
      "Demand - purchased power leg", 9.64, "$/kW/month",
      "monthly charge $93.81; distribution leg $13.03/kW; energy $0.05411; min $1.75/kVA",
      "all", "all", "published", E_SCI, SCI_SRC, URL["Rate-39_LP_2024.pdf"], None),
    R(SCI, "PPT", "Purchased Power Tracker (Appendix A)", "fuel_base", "SCI-PPT-BASE",
      "Purchased-power base embedded in base rates", 0.0923, "$/kWh",
      "Appendix A formula: F = A/B - $0.0923 + R (A = projected purchased power $, B = "
      "projected retail kWh, R = prior-period true-up) - the $0.0923 subtractor IS the "
      "embedded base", "tracked schedules", "all", "published", E_SCI, SCI_SRC,
      URL["Appendix_A_Purchased_Power_Tracker.pdf"],
      "Same double-count hazard as an IOU fuel base. The IP class instead passes "
      "through 'the tracker billed to SCI REMC by Hoosier Energy' directly (Rate 33 "
      "text; Appendix B routes the wholesale tracker to IP-1/EDR-4)."),
]

# ==========================================================================================
# PAULDING-PUTNAM (Ohio co-op, Indiana service area) - 2026.02 board tariff book; the live
# URL died in a site migration, so the book is pinned to the Wayback capture of the
# then-live file.  Supplier: BUCKEYE POWER (Ohio G&T) - which board-approved a DATA CENTER
# rate schedule in March 2026.
# ==========================================================================================
PPEC_SRC = ("Paulding-Putnam Electric Cooperative Rate Schedules 2026.02 board tariff "
            "book (schedules stamped 'Effective: Feb. 1, 2026' or 'May 1, 2024'; issued "
            "by CEO/President; live ppec.coop URL 404s post-migration - book retrieved "
            "from Wayback capture 20260515080132 of the then-live file)")
PPEC_URL = URL["PPEC_Rate_Schedules_2026.02.pdf"]

PPEC_ROWS = [
    R(PPEC, "LPI", "Large Power Service - Indiana", "base_charge", "PPEC-LPI-CUST",
      "Service charge", 130.00, "$/month",
      "contracted-kVA class; minimum bill adds $0.50/kVA over 75 kVA contracted", "all",
      "all", "published", "2026-02-01", PPEC_SRC, PPEC_URL, None),
    R(PPEC, "LPI", "Large Power Service - Indiana", "demand", "PPEC-LPI-DEM",
      "Demand charge", 11.00, "$/kW/month",
      "15-min NCP; PF below 90% grossed (kW x 90/PF); 5-year contract, 1-yr "
      "self-renewals; optional primary delivery: -$9.00/mo and -$0.15/kW", "all", "all",
      "published", "2026-02-01", PPEC_SRC, PPEC_URL, None),
    R(PPEC, "LPI", "Large Power Service - Indiana", "energy", "PPEC-LPI-EN-B1",
      "Energy - first 200 kWh/kW", 0.10100, "$/kWh",
      "hours-use blocks: next 200 kWh/kW $0.08200, over 400 kWh/kW $0.05450", "all",
      "all", "published", "2026-02-01", PPEC_SRC, PPEC_URL, None),
    R(PPEC, "IND1", "Schedule IND1 - Indiana", "demand", "PPEC-IND1-DEM", "Demand charge",
      23.50, "$/kW/month",
      "service charge $200.00/mo; energy $0.05000 all kWh; minimum bill carries the "
      "trailing-12-month max billing demand (full ratchet in the minimum clause)", "all",
      "all", "published", "2024-05-01", PPEC_SRC, PPEC_URL, None),
    R(PPEC, "IND2", "Schedule IND2 - Indiana", "demand", "PPEC-IND2-DEM", "Demand charge",
      7.50, "$/kW/month", "service charge $200.00/mo; energy $0.09400 all kWh; same "
      "trailing-12-month minimum", "all", "all", "published", "2024-05-01", PPEC_SRC,
      PPEC_URL, None),
    R(PPEC, "WPCA", "Wholesale Power Cost Adjustment", "fuel_base", "PPEC-WPCA-BASE",
      "Wholesale power base embedded in base rates", 0.06958, "$/kWh",
      "Schedule W formula: WPCA = (PPC / kWh purchased) / (1 - loss factor) - $0.06958, "
      "applied monthly to all WPCA-billed tariffs", "all WPCA schedules", "all",
      "published", "2026-02-01", PPEC_SRC, PPEC_URL, None),
    R(PPEC, "SUPPLY", "G&T supply", "eligibility", "PPEC-SUPPLY",
      "Buckeye Power (Ohio G&T); Buckeye data-center rate exists (2026-03)", None, None,
      "PPEC's own data-centers page: 'your co-op is well-positioned with generation "
      "through Buckeye Power, we are part of a larger regional grid, PJM' and 'The "
      "Buckeye Power Board approved the new data center rate schedule in March 2026' "
      "which 'assigns the full cost of serving data centers directly to those customers'",
      "system", "all", "published", "2026-03-01",
      "PPEC data-centers page (cached data_centers_page.html)",
      "https://ppec.coop/data-centers/",
      "PPEC is NOT on an Indiana G&T - its wholesale path is Buckeye/PJM, and Buckeye "
      "already has a dedicated (unpublished) data-center schedule."),
]

# ==========================================================================================
# WHOLESALERS - Hoosier Energy, WVPA, IMPA.  The retail-rate jurisdiction rows (NONJURIS-*)
# from the IURC harvest remain; these rows add WHO SETS THE WHOLESALE RATE, under what
# instrument, feeding which members - the leverage the brief asked for.
# ==========================================================================================
HOOS_ROWS = [
    R(HOOSIER, "WHOLESALE", "Rate-setting status", "eligibility", "HOOS-FERC-STATUS",
      "NOT FERC rate-jurisdictional (FPA 201(f); RUS G&T borrower)", None, None,
      "FERC order 171 FERC 61,143 (2020-05-21, EL16-99-001 et al.) lists Hoosier among "
      "non-public-utility MISO transmission owners whose 'revenue requirements are "
      "recovered under the MISO Tariff' - its ONLY FERC touchpoint (dockets ER15-1297, "
      "ER16-1463, ER17-1265, ER18-1164, ER20-1279); the 2023 IRP (IURC-filed 2024-04-01) "
      "identifies Hoosier as an RUS G&T borrower, the 201(f) exemption trigger; no "
      "Hoosier wholesale tariff exists in FERC eTariff", "wholesale to members", "all",
      "published", None,
      "FERC 171 FERC 61,143 (cached) + Hoosier 2023 IRP Vol.1 (cached)",
      "https://www.ferc.gov/sites/default/files/2020-06/E-5-052120.pdf",
      "Board-approved wholesale rates; no public formula rate text."),
    R(HOOSIER, "WHOLESALE", "Wholesale rate structure (as visible through members)",
      "rider", "HOOS-RATE-STRUCTURE", "Standard Wholesale Tariff + Industrial Power "
      "Tariff + quarterly H.E. Tracker", None, None,
      "structure visible only via member tariffs: 'Standard Wholesale Tariff' = unbundled "
      "Summer/Winter Production CP (MISO-peak-coincident) + Transmission CP + Delivery "
      "NCP demand legs with on/off-peak energy (SEI REMC UIPS-1/CPS-1); 'Industrial "
      "Power Tariff' gates member 500 kW / 1,000 kW industrial classes (SEI IP-1/IPS-1, "
      "SCI IP); quarterly 'H.E. Tracker' pass-through ($0.00249/kWh in Q3-2026 via SEI "
      "PCT; SCI passes it through directly)", "member REMC retail tariffs", "all",
      "published", None,
      "SEI REMC UIPS-1/CPS-1/PCT sheets + SCI REMC Rate 33 (all cached)",
      "https://www.seiremc.com/rates",
      "The wholesale DESIGN is measured even though the wholesale PRICE SHEET is not "
      "public - production cost rides MISO-CP hours, which is what a flexible data "
      "centre can avoid."),
    R(HOOSIER, "WHOLESALE", "Member roster", "eligibility", "HOOS-MEMBERS",
      "17 member systems (feeds SCI REMC, SEI REMC, Southern Indiana Power + 14 more)",
      None, None,
      "hoosierenergy.com/our-members (2026-08-18): Bartholomew County REMC; Clark County "
      "REMC; Daviess-Martin County REMC; Decatur County REMC; Dubois REC; Harrison REMC; "
      "Henry County REMC; Jackson County REMC; Orange County REMC; RushShelby Energy; "
      "South Central Indiana REMC; Southeastern Indiana REMC; Southern Indiana Power; "
      "Utilities District of Western Indiana REMC; Wayne-White Counties Electric Coop "
      "(IL); WIN Energy REMC; Whitewater Valley REMC", "southern Indiana + SE Illinois",
      "all", "published", None, "hoosierenergy.com/our-members (cached HTML)",
      "https://www.hoosierenergy.com/our-members/",
      "JCREMC (Franklin) appears in the April-2024 IRP roster of 18 but not on the "
      "2026 page - membership now 17 per the 2026-05-12 annual-meeting piece."),
    R(HOOSIER, "WHOLESALE", "Large-load framework", "eligibility", "HOOS-LARGELOAD",
      ">50 MW loads leave the traditional tariffs entirely", None, None,
      "EDR via members: >=500 kW new demand, 30% first-year discount declining over six "
      "years; DATA CENTERS: 'Consumer Directed Resource Policy' for loads >50 MW - 'a "
      "data center would pay all costs to serve its load rather than operating under "
      "Hoosier Energy's traditional tariffs' (2026-05-12)", "loads via member REMCs",
      "all", "published", "2026-05-12",
      "hoosierenergy.com annual-meeting article 2026-05-12 + powering-site-selection "
      "page (cached)", "https://www.hoosierenergy.com/economic-development/"
      "powering-site-selection/",
      "DECISION-RELEVANT: in Hoosier territory (incl. SEI REMC's 5 MW class), anything "
      "data-centre-sized is a bespoke full-cost contract, not a tariff bill."),
]

WVPA_ROWS = [
    R(WVPA, "WHOLESALE", "Rate-setting status", "eligibility", "WVPA-FERC-STATUS",
      "FERC-governed through 2024-12-31; board self-regulated since 2025-01-01", None,
      None,
      "audited FY2025 statements: 'Wholesale rates for Wabash Valley Power were governed "
      "by the Federal Energy Regulatory Commission (FERC) under the Federal Power Act "
      "through December 31, 2024 ... The Company elected to withdraw from FERC "
      "jurisdiction as of January 1, 2025 and is now self-regulated by the Company's "
      "Board of Directors' - the Board 'adopted the formulary rate structure previously "
      "approved by FERC'; eTariff cancellations ER25-838/-842/-843 (eff 2025-01-01/-02)",
      "wholesale to members", "all", "published", "2025-01-01",
      "WVPA 2025 audited consolidated financial statements (cached PDF; auditor-dated "
      "2026-03-23)", URL["WVPA_2025_Audited_Financial_Statements.pdf"],
      "Pre-2025 formula rate text lives in FERC eLibrary under the cancelled dockets."),
    R(WVPA, "WHOLESALE", "Formula Rate Tariff", "rider", "WVPA-FORMULA",
      "Budget-based billing with subsequent-year true-up", None, None,
      "'Member billed revenues reflect estimated power supply costs based on the current "
      "year's board-approved operating budget. Per the Formula Rate Tariff approved by "
      "the Board, member bills are adjusted in the subsequent year to collect or refund "
      "the difference' - rates = revenue required to cover cost 'plus an appropriate "
      "margin'; over-collected $4,180k at 2025-12-31; member revenues $633.5M (2025)",
      "member REMC wholesale bills", "all", "published", "2025-01-01",
      "WVPA 2025 audited financial statements (cached)",
      URL["WVPA_2025_Audited_Financial_Statements.pdf"], None),
    R(WVPA, "WHOLESALE", "Member roster", "eligibility", "WVPA-MEMBERS",
      "21 member systems, northern Indiana + Illinois; contracts through December 2060",
      None, None,
      "wvpa.com member page (2026-08-18): Boone Power (Lebanon IN); Carroll White REMC; "
      "Corn Belt Energy (IL); EnerStar (IL); Fulton County REMC; Heartland REMC; "
      "Hendricks Power; Jasper County REMC; Jay County REMC; Kankakee Valley REMC; "
      "Kosciusko REMC; LaGrange County REMC; M.J.M. (IL); Marshall County REMC; "
      "Miami-Cass REMC; Newton County REMC; NineStar Connect; Noble REMC; Parke County "
      "REMC; Steuben County REMC; Warren County REMC; wholesale contracts 'extend "
      "through December 2060'; two members exited 2025-06-01 under FERC-approved "
      "agreements (one became a full-requirements customer, one partial)", "northern "
      "Indiana + IL", "all", "published", None,
      "wvpa.com/who-we-are/member-co-ops (cached HTML) + FY2025 statements",
      "https://www.wvpa.com/who-we-are/member-co-ops/", None),
    R(WVPA, "WHOLESALE", "Large-load rate menu (published)", "eligibility",
      "WVPA-LARGELOAD", "Tiered site-selector rate options up to 35,000+ kW", None, None,
      "wvpa.com rate-options page: Three-Year Discount Rate (300-3,000 kW); Five-Year "
      "Discount Flex Rate (1,500 kW+, 'ideal for universities, schools, data centers, "
      "and warehouses'); Unlimited Term Discount Rate (3,000-34,999 kW, minimum 61% load "
      "factor); Ten-Year Market Direct (5,000-34,999 kW, market-access pricing); "
      "Unlimited Term Market Rate (35,000+ kW, negotiated, customized supply portfolio)",
      "new loads via member systems", "all", "published", None,
      "wvpa.com/for-site-selectors/rate-options (cached HTML)",
      "https://www.wvpa.com/for-site-selectors/rate-options/",
      "The ONLY Indiana wholesaler publishing a named large-load menu - and it "
      "explicitly markets the 1.5 MW+ tier to data centres; 35 MW+ is negotiated "
      "market-priced supply."),
]

IMPA_ROWS = [
    R(IMPA, "WHOLESALE", "Rate-setting status", "eligibility", "IMPA-RATESET",
      "Board-set under the Bond Resolution; exempt from state and federal rate "
      "regulation", None, None,
      "audited FY2025 statements: 'IMPA sets rates in accordance with the Bond "
      "Resolution' requiring revenues to cover operating costs and 'at least 110% of "
      "the Agency's aggregate debt service ... Rates are not subject to state or "
      "federal regulation.' Members 'are billed using budget rates' with a tracker "
      "true-up; Power Sales Contracts extend through 2057 on a rolling basis; FPA "
      "201(f) political-subdivision exemption", "wholesale to 61 members", "all",
      "published", None,
      "IMPA 2025 year-end financial statements (cached; auditor-dated 2026-03-26)",
      URL["IMPA_2025_Year_End_Financials.pdf"], None),
    R(IMPA, "WHOLESALE", "Published wholesale price level", "energy", "IMPA-ACCRUED-2025",
      "Average accrued cost per kWh to members, 2025 - AGENCY METRIC, NOT A TARIFF RATE",
      0.0845, "$/kWh",
      "annual report MD&A: 'The average accrued cost per kWh for 2025 was 8.45 cents, an "
      "approximate 10.0% increase compared to 2024'; 2026 rate study approved by the "
      "Board in October 2025 at +2.7% average; 2025 kWh sales ~6,236 GWh, NCP ~1,248 MW",
      "all 61 members", "all", "published", "2025-12-31",
      "IMPA 2025 Annual Report (cached PDF)", URL["IMPA_2025_Annual_Report.pdf"],
      "A realized average, loaded because it is the publisher's own printed number and "
      "the only public IMPA price level; the actual Rate Schedule B price sheet is not "
      "public."),
    R(IMPA, "WHOLESALE", "Wholesale rate structure", "rider", "IMPA-STRUCTURE",
      "Power Sales Rate Schedule 'B': demand + energy + reactive legs", None, None,
      "evidence from member tariffs: Tell City Tariff E2 bases its Base Demand, Base "
      "Energy and Base Reactive Demand charges on 'Indiana Municipal Power Agency (IMPA) "
      "Power Sales Rate Schedule B'; Anderson ISTP passes through 'the current wholesale "
      "demand-related rate(s)' and bills on the IMPA-coincident 60-min interval; "
      "Anderson's tracker base ($16.872/kW + $0.03213/kWh) is the embedded IMPA cost in "
      "its base rates", "member pass-through tariffs", "all", "published", None,
      "Tell City 2022 booklet + Anderson Ordinance 9-22 (both cached)",
      URL["tell_city_2022_revised_rates_and_charges_booklet.pdf"],
      "Wholesale price sheet not public; structure and an embedded price point are."),
    R(IMPA, "WHOLESALE", "Member roster", "eligibility", "IMPA-MEMBERS",
      "61 members - incl. 9 of the 12 munis in this harvest", None, None,
      "FY2025 statements: 'IMPA serves 60 Indiana cities and towns and one Ohio village'; "
      "roster (2025 Annual Report map) includes Anderson, Frankfort, Richmond, Peru, "
      "Jasper, Lebanon, Crawfordsville, Columbia City, Tell City, Washington, Greenfield, "
      "Scottsburg, Rensselaer, Gas City, Huntingburg, Linton, Covington + 44 more; "
      "Auburn, Logansport and Mishawaka are NOT members (I&M/AEP, NextEra and Wolverine "
      "supplied respectively)", "member municipal systems", "all", "published", None,
      "IMPA 2025 Annual Report p.24 member map (cached)",
      URL["IMPA_2025_Annual_Report.pdf"], None),
    R(IMPA, "WHOLESALE", "Large-load intake", "eligibility", "IMPA-LARGELOAD",
      "Large User Intake process; member EDRs mirror an IMPA EDR", None, None,
      "impa.com carries a 'Large User Intake Form' and economic-development services "
      "(sites and buildings, rate design); member-level EDRs pass IMPA wholesale credits "
      "through (CEL&P EDR-IMPA: 20/15/10/10/5% credit over 60 months; Lebanon Ord "
      "2017-11 mirrors the IMPA EDR at >=1 MW + $1M investment)", "new large loads at "
      "member munis", "all", "published", None,
      "impa.com members/services pages + CEL&P tariff + Lebanon ordinance (cached)",
      "https://www.impa.com/", None),
]

ALL_ROWS = (ANDERSON_ROWS + AUBURN_ROWS + FRANKFORT_ROWS + RICHMOND_ROWS +
            LOGANSPORT_ROWS + MISHAWAKA_ROWS + PERU_ROWS + JASPER_ROWS + LEBANON_ROWS +
            CRAWFORDSVILLE_ROWS + COLUMBIA_CITY_ROWS + TELL_CITY_ROWS + SEI_ROWS +
            SIP_ROWS + SCI_ROWS + PPEC_ROWS + HOOS_ROWS + WVPA_ROWS + IMPA_ROWS)

# Placeholder rows from the IURC harvest that THIS run supersedes (deleted only because
# this loader now carries the replacement rows).  (utility, code) pairs.  The
# NONJURIS-*/-JURIS finding rows are NOT superseded - they stay.
SUPERSEDED = [
    (AND_, "AND-BASE"),   # base schedules now transcribed from Ordinance 9-22 / 50507
    (AUB, "AUB-BASE"),    # base schedules now transcribed from 50523 + 45102
    (FRK, "FRK-BASE"),    # base schedules now transcribed from 50549
]

MY_UTILITIES = sorted({r["utility"] for r in ALL_ROWS})
MY_CODES = sorted({r["code"] for r in ALL_ROWS} | {c for _u, c in SUPERSEDED})

RESCRAPE = ("RE-SCRAPE COMMAND: python scripts/load_tariff_books_munis_coops.py --fetch   "
            "(idempotent: DELETE WHERE utility IN (this harvest's munis/REMCs/G&Ts) AND code "
            "IN (this loader's codes + superseded placeholders) - IOU rows, jurisdictional-"
            "muni tracker rows and NONJURIS finding rows are untouchable by construction; "
            "then load-job APPEND; sentinel-verifies every document before any write; "
            "--verify-only for a no-write check).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="download the source documents first")
    ap.add_argument("--verify-only", action="store_true", help="sentinel check only, no writes")
    ap.add_argument("--dry-run", action="store_true", help="verify + row lint, no BigQuery writes")
    args = ap.parse_args()

    if args.fetch:
        print("fetching source documents (throttled >=1.2s per host) ...")
        fetch_all()

    print("\nverifying sentinels against the documents on disk ...")
    verify_sentinels()

    bad = []
    for i, r in enumerate(ALL_ROWS):
        if r["utility"] in IOUS:
            bad.append((i, "IOU UTILITY IN THIS HARVEST - FORBIDDEN", r["utility"]))
        if r["component_type"] not in ("base_charge", "demand", "energy", "rider",
                                       "eligibility", "ratchet", "fuel_base"):
            bad.append((i, "component_type", r["component_type"]))
        if r["season"] not in ("summer", "non_summer", "all"):
            bad.append((i, "season", r["season"]))
        if r["value_status"] not in ("published", "not_held"):
            bad.append((i, "value_status", r["value_status"]))
        if r["value_status"] == "not_held" and r["rate"] is not None:
            bad.append((i, "not_held row carries a rate", r["code"]))
    codes = [r["code"] for r in ALL_ROWS]
    for c in set(codes):
        if codes.count(c) > 1:
            bad.append(("dup", "duplicate code", c))
    protected = {"NONJURIS-MUNI", "NONJURIS-REMC", "NONJURIS-GT", "NONJURIS-JAA"}
    for c in set(MY_CODES) & protected:
        bad.append(("scope", "loader would touch a protected jurisdiction row", c))
    if bad:
        for b in bad:
            print(f"  ROW LINT FAIL: {b}")
        raise SystemExit("row lint failed - fix the ROWS above before loading")
    print(f"row lint ok: {len(ALL_ROWS)} rows across {len(MY_UTILITIES)} utilities; "
          f"{len(SUPERSEDED)} placeholder row(s) superseded")

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
    client.get_table(TABLE)  # must already exist

    print(f"\ndeleting prior rows for THIS harvest only: utility IN ({len(MY_UTILITIES)}) AND "
          f"code IN ({len(MY_CODES)}) - IOUs/trackers/jurisdiction rows untouched ...")
    client.query(
        f"DELETE FROM `{TABLE}` WHERE utility IN UNNEST(@u) AND code IN UNNEST(@c)",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ArrayQueryParameter("u", "STRING", MY_UTILITIES),
            bigquery.ArrayQueryParameter("c", "STRING", MY_CODES)])).result()

    print(f"loading {len(ALL_ROWS)} rows via load job (no streaming buffer) ...")
    job = client.load_table_from_json(
        ALL_ROWS, TABLE,
        job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_APPEND"))
    job.result()

    counts = {r.utility: r.n for r in client.query(
        f"SELECT utility, COUNT(*) n FROM `{TABLE}` GROUP BY 1")}
    total = sum(counts.values())
    print("live per-utility counts after load (this harvest's utilities):")
    for u in MY_UTILITIES:
        print(f"   {u[:58]:60s} {counts.get(u, 0):>4}")
    print(f"   TABLE TOTAL {total}")
    viol = list(client.query(
        f"SELECT COUNT(*) n FROM `{TABLE}` WHERE value_status='not_held' AND rate IS NOT NULL"))[0].n
    if viol:
        raise SystemExit(f"POST-LOAD CHECK FAILED: {viol} not_held rows carry a rate")
    print("post-load check ok: zero not_held-with-a-rate violations table-wide")

    _write_registries(client, counts, total)
    print("\nDONE")


def _write_registries(client, counts, total):
    from google.cloud import bigquery
    n_mine = len(ALL_ROWS)
    src = ("THREE harvests share this table. (1) utility-site books: AES/NIPSCO/"
           "CenterPoint (scripts/load_tariff_books_aes_nipsco_centerpoint.py). (2) IURC "
           "commission route: Duke + I&M + jurisdictional-muni trackers + jurisdiction "
           "census (scripts/load_tariff_books_iurc_duke_im_munis.py; docs/TARIFF_HARVEST_"
           "IURC_ALL_UTILITIES.md). (3) THIS RUN - ordinance/board route for munis, REMCs "
           "and wholesalers (scripts/load_tariff_books_munis_coops.py; docs/TARIFF_"
           "HARVEST_MUNIS_COOPS.md): Anderson Ord 9-22 via 30-day 50507 (approved "
           "2022-06-08) + pending Cause 46397; Auburn 50523 (2022-06-28) on Cause 45102 "
           "structure; Frankfort 50549 (2022-06-28, incl. NEW 10 MW Rate IP); Richmond "
           "50559/Ord 26-2022 Phase 3 (eff 2023-01-20, Cause 45361 lineage) + Q3-2026 "
           "ECA ad; Logansport Ordinance 2025-02 / LMU Rate Guide 2026 step; Mishawaka "
           "city tariff pages eff 2025-01-01 (Ord 5954 2026 Exhibit A NOT posted - "
           "records-location); Peru rate pages eff 2026-06-01; Jasper Municipal Code ch. "
           "11.08 (Ord 2022-8) via Municode; Lebanon rates page (50535-adjusted 44142 "
           "book) + Q3-2026 tracker; Crawfordsville CEL&P compiled tariff 50561/45420 "
           "(pending 2026 rate ordinance); Columbia City Ordinance 2026-5 Exhibit A "
           "(Phase I-2026, image scan visually transcribed); Tell City 2022 booklet (Res "
           "R220615A / Ord 1190) + Q3-2026 tracker (image, visually transcribed); SEI "
           "REMC board sheets eff 2025-10-01/-20 (UIPS-1 supersedes URDB-era IPS-2) + "
           "PCT Q3-2026; Southern Indiana Power page (C&I schedules NOT published - "
           "records-location, co-op office Tell City); SCI REMC sheets eff 2024-02-01; "
           "Paulding-Putnam 2026.02 book via Wayback 20260515080132 (live URL dead); "
           "Hoosier Energy (FERC 171 FERC 61,143 + 2023 IRP + member/DC-policy pages); "
           "WVPA FY2025 audited statements + member/rate-options pages; IMPA FY2025 "
           "statements + 2025 Annual Report.")
    method = (RESCRAPE + " || RE-RUN ORDER: if load_tariff_books_iurc_duke_im_munis.py "
              "re-runs, re-run THIS loader afterwards - its utility-scoped DELETE removes "
              "this harvest's rows for the shared munis/REMCs/G&Ts, then reinstates its "
              "placeholders. || WHY THE ORDINANCE/BOARD ROUTE: per the FY2025 IURC Annual "
              "Report only Anderson/Auburn/Frankfort remain rate-jurisdictional; no REMC "
              "is; Hoosier/WVPA/IMPA have no retail-rate jurisdiction - these rates are "
              "set by council ordinance and co-op/agency boards and published on utility "
              "sites, municipal codes, or not at all. || OBSERVED PUBLISHER VINTAGES "
              "(never pull dates): A/A/F + Richmond + Lebanon + CEL&P + Tell City books "
              "all trace to the June-2022 HEA-1002 URT-repeal 30-day filings (50507/"
              "50523/50549/50559/50535/50561/Ord 1190) on 2014-2021 rate-case bases; "
              "Logansport Ord 2025-02 (annual steps 2025-2029, 2026 column loaded); "
              "Mishawaka 2025-01-01 step (2026 step exists, unpublished); Peru "
              "2026-06-01; Columbia City Ord 2026-5 (2026-05-01 cycle, phases to 2028); "
              "SEI 2025-10; SCI 2024-02-01; PPEC 2026-02-01; trackers all Q3-2026 where "
              "quarterly. || VERIFICATION: sentinel strings asserted against every "
              "text-bearing document; image-only scans (Richmond book, Columbia City "
              "2026-5, Tell City tracker, Logansport ordinance) are sha256-PINNED and "
              "were transcribed by HUMAN-VISUAL page reads 2026-08-18 (Richmond pages "
              "11/15/19/23/27 read individually); OCR artifacts cached beside the scans. "
              "|| PENDING AT HARVEST: Anderson Cause 46397 (settlement hearing "
              "2026-09-21); Auburn IURC-withdrawal Ordinances 2026-12/-13 (first reading "
              "April 2026); CEL&P amending rate ordinance (hearing 2026-08-10); "
              "Mishawaka Ord 5954 2026 Exhibit A unpublished. || EXCLUDED AND WHY: "
              "lighting/EV/net-metering detail (not siting-relevant); COIN OCR-only "
              "figures carried in a status row, not rate columns; Columbia City ECA "
              "example value (image-only, unverified) named in basis only; 44 tiny munis "
              "keep census rows only (no large-load class exists to transcribe).")
    notes = (f"Ordinance/board-route harvest added {n_mine} rows across {len(MY_UTILITIES)} "
             f"utilities (incl. Crawfordsville, previously absent from URDB entirely); "
             f"replaced 3 not_held BASE placeholders (Anderson/Auburn/Frankfort); "
             f"jurisdiction finding rows kept. Data-centre-grade classes measured: "
             f"Anderson IP/ISTP (10 MVA, IMPA-CP billing + wholesale passthrough), "
             f"Frankfort IP (10 MW, 69 kV), Richmond TS (10 MW, >=69 kV), Crawfordsville "
             f"IP (10 MW, 138 kV), Tell City E2 (10 MVA, IMPA Rate-B passthrough), Auburn "
             f"EHV (30 MVA floor, 100% ratchet), SEI REMC UIPS-1 (5 MW, MISO-CP 4-part "
             f"demand), Logansport Industrial Substation ($32,500/mo flat). Wholesalers: "
             f"Hoosier board-set (201(f), >50 MW loads leave tariffs per Consumer "
             f"Directed Resource Policy), WVPA board formula rate (left FERC 2025-01-01; "
             f"published large-load menu to 35 MW+), IMPA board/Bond-Resolution (8.45 "
             f"c/kWh accrued 2025; +2.7% approved for 2026). UNPUBLISHED IS NULL, NEVER "
             f"0: zero not_held-with-a-rate violations table-wide (checked post-load). "
             f"Do not overwrite in_rate_component_gaps.")
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

    # ---- energy.registry_sources APPEND (the ONLY permitted write to energy) -------------
    reg_rows = [
        dict(sid="muni-tariff:ordinance-route:jurisdictional-base",
             sn="Anderson/Auburn/Frankfort BASE schedules - commission-stamped HEA-1002 "
                "URT 30-day tariffs on their rate-case bases",
             ep="https://iurc.portal.in.gov/search-thirtyday-cases/",
             epr="Stamped tariffs: 50507=" + URL["30day_50507_approved_tariff_20220608.pdf"]
                 + " ; 50523=" + URL["30day_50523_approved_tariff_20220628.pdf"]
                 + " ; 50549=" + URL["30day_50549_tariff.pdf"]
                 + " ; structure 45102=" + URL["45102_compliance_20181107.pdf"]
                 + " ; pending 46397 case id cf9f09be-1240-f111-88b3-001dd800b811",
             util="Anderson ML&P + Auburn Municipal Electric + Frankfort City L&P",
             what="Base energy/demand/customer charges for all three jurisdictional "
                  "municipals incl. Anderson IP (10 MVA, IMPA-coincident billed demand) "
                  "and ISTP (34.5 kV wholesale passthrough), Frankfort Rate IP (10 MW, "
                  "69 kV, new 2022), Auburn EHV/EHP/EHPT 69 kV classes ($17.10/kVA, EHV "
                  "25 MVA/100% ratchet); PPCAT base 16.872 $/kW + 0.03213 $/kWh",
             n=len(ANDERSON_ROWS) + len(AUBURN_ROWS) + len(FRANKFORT_ROWS),
             st="BUILT+LOADED - replaces the AND/AUB/FRK-BASE not_held placeholders; "
                "Anderson 46397 PENDING (settlement hearing 2026-09-21); Auburn "
                "IURC-withdrawal ordinances on first reading April 2026"),
        dict(sid="muni-tariff:ordinance-route:withdrawn-munis",
             sn="Withdrawn/never-jurisdictional municipal books - utility sites, "
                "municipal codes, council ordinances",
             ep="https://www.rp-l.com/updates-to-rates-charges/",
             epr="RP&L book=" + URL["rpl_full_compliance_tariff_eff_2022-07-01.pdf"]
                 + " ; RP&L ECA Q3-26=" + URL["rpl_eca_2026q3_legal_ad.pdf"]
                 + " ; LMU guide=" + URL["lmu_rate_guide.pdf"]
                 + " ; Mishawaka=" + URL["mishawaka_rate_I_industrial.html"]
                 + " ; Peru=" + URL["peru_electric_rates_page.html"]
                 + " ; Jasper=library.municode.com/in/jasper (api.municode.com job "
                 "483743, Supplement 11) ; Lebanon=" +
                 URL["lebanon_utilities_rates_page_20260818.html"]
                 + " ; CEL&P=" + URL["celp_tariff_with_ev_fast_charge_jan2025.pdf"]
                 + " ; Columbia City=" + URL["cc_ordinance_2026-5_electric_rates.pdf"]
                 + " ; Tell City=" +
                 URL["tell_city_2022_revised_rates_and_charges_booklet.pdf"],
             util="Richmond, Logansport, Mishawaka, Peru, Jasper, Lebanon, "
                  "Crawfordsville, Columbia City, Tell City",
             what="Industrial/large-power schedules with floors, ratchets, trackers: "
                  "Richmond TS 10 MW@69kV ($21.70/kVA + 2.71c), Logansport Industrial "
                  "Substation ($32,500/mo flat + $14.592/kVAD), Crawfordsville IP 10 "
                  "MW@138kV, Tell City E2 10 MVA IMPA passthrough, Mishawaka Rate I "
                  "(no ratchet), Peru PS, Jasper GSD, Lebanon PPL, Columbia City "
                  "GS-I; Crawfordsville is NEW to the warehouse (no URDB rows)",
             n=(len(RICHMOND_ROWS) + len(LOGANSPORT_ROWS) + len(MISHAWAKA_ROWS) +
                len(PERU_ROWS) + len(JASPER_ROWS) + len(LEBANON_ROWS) +
                len(CRAWFORDSVILLE_ROWS) + len(COLUMBIA_CITY_ROWS) + len(TELL_CITY_ROWS)),
             st="BUILT+LOADED - image-only sources sha256-pinned + human-visually "
                "transcribed; records-location not_helds: Mishawaka Ord 5954 Exhibit A, "
                "Logansport class floors (Ord 2018-26), CEL&P current tracker factors"),
        dict(sid="coop-tariff:board-route:remcs+wholesalers",
             sn="REMC board tariffs + G&T/JAA wholesale rate-setting instruments",
             ep="https://www.seiremc.com/rates",
             epr="SEI UIPS-1=" + URL["UIPS-1_Unbundled_Large_Industrial_Power_Service.pdf"]
                 + " ; SEI PCT Q3-26=" + URL["PCT_Q3_2026.pdf"]
                 + " ; SCI IP=" + URL["Rate-33_IP_2024.pdf"]
                 + " ; SIP=" + URL["rates_charges_page.html"]
                 + " ; PPEC book (Wayback)=" + URL["PPEC_Rate_Schedules_2026.02.pdf"]
                 + " ; Hoosier FERC status=" +
                 URL["FERC_171_61143_MISO_nonpublic_utility_order_2020.pdf"]
                 + " ; WVPA FY25 FS=" + URL["WVPA_2025_Audited_Financial_Statements.pdf"]
                 + " ; IMPA FY25 FS=" + URL["IMPA_2025_Year_End_Financials.pdf"],
             util="SEI REMC, Southern Indiana Power, SCI REMC, Paulding-Putnam + "
                  "Hoosier Energy, WVPA, IMPA",
             what="SEI UIPS-1 (5 MW, MISO-CP 4-part demand) + seasonal C-5; SCI "
                  "IP/LI/LP with unbundled wholesale/distribution legs + 0.0923 $/kWh "
                  "embedded base; PPEC LPI + WPCA base 0.06958 + Buckeye DC-rate "
                  "finding; wholesale rate-setting: Hoosier board (201(f), Standard "
                  "Wholesale Tariff structure, >50 MW Consumer Directed Resource "
                  "Policy), WVPA board Formula Rate Tariff (ex-FERC 2025-01-01, "
                  "large-load menu to 35 MW+), IMPA Bond Resolution (8.45 c/kWh "
                  "accrued 2025, members through 2057)",
             n=(len(SEI_ROWS) + len(SIP_ROWS) + len(SCI_ROWS) + len(PPEC_ROWS) +
                len(HOOS_ROWS) + len(WVPA_ROWS) + len(IMPA_ROWS)),
             st="BUILT+LOADED - SIP C&I schedules are a records-location not_held "
                "(co-op office, Tell City); Hoosier/IMPA wholesale price sheets not "
                "public (structure + level captured from member tariffs + audited FS)"),
    ]
    for r in reg_rows:
        client.query(
            f"""INSERT `{EN}.registry_sources`
                (source_id, source_name, endpoint, endpoint_raw, endpoint_kind, fmt,
                 utility, geography_state, measured_rows, last_source_count, status,
                 acquisition_method, what_it_provides, object_names, origin, updated_by,
                 validation, last_validated_at, notes)
                VALUES (@sid, @sn, @ep, @epr, 'web+pdf', 'pdf+html', @util, 'IN', @mr,
                        @lsc, @st, @acq, @wip, @objs, 'loader_auto_registration',
                        'load_tariff_books_munis_coops', 'OK_COUNTED',
                        CURRENT_TIMESTAMP(), @notes)""",
            job_config=bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("sid", "STRING", r["sid"]),
                bigquery.ScalarQueryParameter("sn", "STRING", r["sn"]),
                bigquery.ScalarQueryParameter("ep", "STRING", r["ep"]),
                bigquery.ScalarQueryParameter("epr", "STRING", r["epr"]),
                bigquery.ScalarQueryParameter("util", "STRING", r["util"]),
                bigquery.ScalarQueryParameter("mr", "INT64", int(r["n"])),
                bigquery.ScalarQueryParameter("lsc", "INT64", int(r["n"])),
                bigquery.ScalarQueryParameter("st", "STRING", r["st"]),
                bigquery.ScalarQueryParameter("acq", "STRING", RESCRAPE),
                bigquery.ScalarQueryParameter("wip", "STRING", r["what"]),
                bigquery.ArrayQueryParameter("objs", "STRING", ["in_utility_tariff_riders"]),
                bigquery.ScalarQueryParameter("notes", "STRING",
                    "Rows live in energy-platfrom.indiana_app.in_utility_tariff_riders "
                    "(energy dataset untouched beyond this append). Publisher vintage = "
                    "ordinance/resolution numbers + their own effective dates on every "
                    "row, never pull timestamps. Full narrative: docs/TARIFF_HARVEST_"
                    "MUNIS_COOPS.md.")])).result()
        print(f"appended energy.registry_sources: {r['sid']}")


if __name__ == "__main__":
    main()
