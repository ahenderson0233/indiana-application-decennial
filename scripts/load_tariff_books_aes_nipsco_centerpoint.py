"""Tariff-book harvest: AES Indiana (IPL), NIPSCO, CenterPoint/SIGECO -> in_utility_tariff_riders.

WHAT THIS IS (targets #3, #4, #5 of docs/TARIFF_SCRAPE_TARGETS.md, harvested 2026-08-18)
----------------------------------------------------------------------------------------
urdb_rates is FLATTENED: no customer charge, no rider stack, no fuel base, no ratchet.  This
loader closes that gap for three utilities from the utilities' OWN tariff books (public PDFs,
no gate, no account):

  AES Indiana / IPL      IURC No. E-20, Cause 46258 book,   effective 2026-07-27
  NIPSCO                 IURC Electric Service Tariff, Original Volume No. 16, eff 2025-07-01,
                         charge sheets Second Revised eff 2026-03-01 (the 2025 rate case book;
                         the 8xx series URDB cites is CANCELLED - rates renumbered to 6xx)
  CenterPoint / SIGECO   CEI South IURC No. E-14 (Cause 45990 era), sheets eff 2025-02-13
                         through 2026-08-01 (per-sheet vintages carried on every row)

HEADLINE FINDINGS (the reason this harvest matters)
---------------------------------------------------
  * NIPSCO Rate 631 "Industrial Power Service - Large" IS a purpose-built large-load tariff:
    >=10,000 kW contract demand at transmission/subtransmission, three service TIERS
    (Tier 1 firm $35.74/kW-mo + $0.030977/kWh; Tier 2 non-firm at Day-Ahead LMP; Tier 3
    non-firm third-party/MISO Asset Owner), a $0.014689/kWh transmission charge on ALL
    tiers, 5-year minimum contract, and MISO LMR curtailment mechanics.  This is the class
    a data centre takes service under.
  * AES HL demand charge by voltage: $34.30 primary vs $25.00 transmission per kW-mo.
    The $9.30/kW-mo delta is ~$3.9M/yr on 35 MW - the number weighed against owning the
    step-down substation.
  * Fuel bases embedded in base rates (omit these and the FAC is double-counted):
    AES $0.043811/kWh (Rider 6) | NIPSCO $0.025032/kWh (Rider 670) |
    SIGECO LP $0.040254 / HLF $0.039170 per kWh (stated as the schedules' own Fuel Charge
    lines and confirmed as "Base Fuel" in Appendix A).
  * NONE of the three books has a summer/non-summer split on these C&I base rates.  The
    only seasonal boundary any book states is NIPSCO's maintenance-service exclusion of
    June-September.  Season is 'all' on every row BY THE BOOK, not by assumption.

HAZARDS HONOURED
----------------
  * UNPUBLISHED IS NULL, NEVER 0.  A stated $0.000000 factor (e.g. NIPSCO FAC at
    2026-08-01) is a PUBLISHED zero and is loaded as 0.0; a component the book does not
    state is value_status='not_held' with rate NULL.
  * Formula-priced components (DA-LMP energy, PF multiplier tables, negotiated CSC) carry
    rate NULL with value_status='published' and the formula in basis/notes - the book does
    publish them, just not as one number.
  * NEVER GUESS: NIPSCO 631 Tier 1's billing determinant (contract vs measured kW) is NOT
    stated on Sheet 80; the ratchet row says so instead of assuming.  AES HL1/HL2/HL3
    subclass mapping in Rider 28 is not defined in the book; the rows say so.
  * energy dataset is READ-ONLY; the only write there is the APPEND to registry_sources.

SENTINEL GUARD
--------------
Before any BigQuery write, every source PDF on disk is text-extracted and checked for
sentinel strings (the load-bearing numbers).  A changed PDF at the same URL fails the run
LOUDLY instead of loading rows that no longer match their source.

BOUNDARIES: anonymous read-only GET of public tariff PDFs, identifying User-Agent,
>=1.3 s between requests per host, no accounts, no CAPTCHA, no UA spoofing.
ASCII-only console output (cp1252 console).

USAGE
-----
    python scripts/load_tariff_books_aes_nipsco_centerpoint.py --fetch          # download PDFs then verify+load
    python scripts/load_tariff_books_aes_nipsco_centerpoint.py                  # use PDFs already on disk
    python scripts/load_tariff_books_aes_nipsco_centerpoint.py --verify-only    # sentinel check, NO writes
    python scripts/load_tariff_books_aes_nipsco_centerpoint.py --dry-run        # everything except BigQuery writes
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
BOOKS = os.path.join(REPO, "scrapers", "tariff_books")

PROJECT = "energy-platfrom"                       # intentional, permanent spelling
DS = f"{PROJECT}.indiana_app"
EN = f"{PROJECT}.energy"                          # READ-ONLY except registry_sources APPEND
TABLE = f"{DS}.in_utility_tariff_riders"

UA = ("DecennialGroup-DataAudit/1.0 (read-only public tariff documents; "
      "contact ahenderson@decennialgroup.com)")

AES = "Indianapolis Power & Light Co"             # utility strings EXACTLY as in in_urdb_rates
NIP = "Northern Indiana Pub Serv Co"
SIG = "Southern Indiana Gas & Elec Co"

AES_DIR = os.path.join(BOOKS, "aes")
NIP_DIR = os.path.join(BOOKS, "nipsco")
SIG_DIR = os.path.join(BOOKS, "centerpoint")

AES_BASE = "https://www.aesindiana.com/sites/aesvault.com/files/2026-07"
NIP_BASE = ("https://www.nipsco.com/docs/librariesprovider11/rates-and-tariffs/"
            "electric-rates/2025-to-current")
SIG_BASE = "https://www.centerpointenergy.com/en-us/Documents/RatesandTariffs/Indiana/Southwest"

# (local dir, filename, url) for every source document this loader depends on.
FILES = [
    (AES_DIR, "Rate-HL-High-Load-Factor--Primary-Distrib-Sub-Trans-and-Trans-Voltages-46258-Effectve-07-27-26.pdf",
     f"{AES_BASE}/Rate-HL-High-Load-Factor--Primary-Distrib-Sub-Trans-and-Trans-Voltages-46258-Effectve-07-27-26.pdf"),
    (AES_DIR, "Rate-PL-Primary-Service-Large-46258-Effectve-07-27-26.pdf",
     f"{AES_BASE}/Rate-PL-Primary-Service-Large-46258-Effectve-07-27-26.pdf"),
    (AES_DIR, "Rate-SL-Secondary-Service-Large-46258-Effectve-07-27-26.pdf",
     f"{AES_BASE}/Rate-SL-Secondary-Service-Large-46258-Effectve-07-27-26.pdf"),
    (AES_DIR, "Large-Commercial-and-Industrial-Rates-46258-Effectve-07-27-26.pdf",
     f"{AES_BASE}/Large-Commercial-and-Industrial-Rates-46258-Effectve-07-27-26.pdf"),
    (AES_DIR, "Rate-CSC-Customer-Specific-Contracts-46258-Effectve-07-27-26.pdf",
     f"{AES_BASE}/Rate-CSC-Customer-Specific-Contracts-46258-Effectve-07-27-26.pdf"),
    (AES_DIR, "Contract-Riders_All_Effective_07-27-26.pdf",
     f"{AES_BASE}/Contract-Riders_All_Effective_07-27-26.pdf"),
    (AES_DIR, "Rider-6-FAC-46258-Effective-07-27-26.pdf",
     f"{AES_BASE}/Rider-6-FAC-46258-Effective-07-27-26.pdf"),
    (AES_DIR, "Contract-Rider-Sheet-07-24-26.pdf",
     f"{AES_BASE}/07-24-26%20Contract%20Rider%20Sheet_0.pdf"),
    (NIP_DIR, "Electric-Service-Tariff-Entire-Book.pdf",
     f"{NIP_BASE}/Electric-Service-Tariff-Entire-Book.pdf"),
    (NIP_DIR, "appendix-a.pdf", f"{NIP_BASE}/appendix-a.pdf"),
    (NIP_DIR, "appendix-b.pdf", f"{NIP_BASE}/appendix-b.pdf"),
    (NIP_DIR, "appendix-c.pdf", f"{NIP_BASE}/appendix-c.pdf"),
    (NIP_DIR, "appendix-f.pdf", f"{NIP_BASE}/appendix-f.pdf"),
    (NIP_DIR, "appendix-g.pdf", f"{NIP_BASE}/appendix-g.pdf"),
    (NIP_DIR, "appendix-h.pdf", f"{NIP_BASE}/appendix-h.pdf"),
    (NIP_DIR, "appendix-i.pdf", f"{NIP_BASE}/appendix-i.pdf"),
    (NIP_DIR, "appendix-j.pdf", f"{NIP_BASE}/appendix-j.pdf"),
    (NIP_DIR, "appendix-k.pdf", f"{NIP_BASE}/appendix-k.pdf"),
    (NIP_DIR, "appendix-l.pdf", f"{NIP_BASE}/appendix-l.pdf"),
    (SIG_DIR, "in-south-electric-tariff.pdf", f"{SIG_BASE}/in-south-electric-tariff.pdf"),
]

# Sentinels: load-bearing numbers that MUST appear in the fetched PDF, else the source moved
# under us and every transcribed row below is suspect.  Fail loudly, load nothing.
SENTINELS = {
    "Rate-HL-High-Load-Factor--Primary-Distrib-Sub-Trans-and-Trans-Voltages-46258-Effectve-07-27-26.pdf":
        ["Effective July 27, 2026", "$34.30", "$25.20", "$25.00", "$500.00", "5.0079",
         "4.9885", "seventy-five percent (75%)", "Five years"],
    "Rate-PL-Primary-Service-Large-46258-Effectve-07-27-26.pdf":
        ["$30.98", "$133.00", "5.1710", "sixty percent (60%)", "Three years"],
    "Rate-SL-Secondary-Service-Large-46258-Effectve-07-27-26.pdf":
        ["$28.50", "$128.00", "4.9723"],
    "Large-Commercial-and-Industrial-Rates-46258-Effectve-07-27-26.pdf":
        ["RATE PH", "$1,275.00", "11.2363", "9.7587"],
    "Rate-CSC-Customer-Specific-Contracts-46258-Effectve-07-27-26.pdf":
        ["minimum contract demand of 2000 kilowatts"],
    "Contract-Riders_All_Effective_07-27-26.pdf":
        ["(0.00265)", "(1.52)", "(0.00270)", "(1.81)", "one and sixty-five hundredths"],
    "Rider-6-FAC-46258-Effective-07-27-26.pdf":
        ["$0.043811", "$(0.000801)"],
    "Contract-Rider-Sheet-07-24-26.pdf":
        ["Updated 07/24/26", "$0.010889", "$0.001505", "$0.003599", "$0.001796",
         "$0.000693", "-$0.000801", "$0.000272"],
    "Electric-Service-Tariff-Entire-Book.pdf":
        ["$35.74", "$0.030977", "$0.014689", "0.025032", "not be less than 10,000 kWs",
         "$16.73", "$0.076305", "$0.276692", "$24.72", "$0.062933", "$20.48", "$19.66",
         "$1,566.00", "$0.002332", "five (5) Contract Years"],
    "appendix-b.pdf": ["$0.000000", "August 1, 2026"],
    "appendix-c.pdf": ["$0.003275", "$0.001752", "$0.002626", "$0.004468"],
    "appendix-f.pdf": ["$0.000786", "$0.000549", "$0.000670"],
    "appendix-g.pdf": ["$0.004775", "$0.003155"],
    "appendix-h.pdf": ["$0.003363"],
    "appendix-i.pdf": ["FEDERALLY MANDATED", "$0.000000"],
    "appendix-j.pdf": ["$0.000203", "$0.000085", "$0.000184"],
    "appendix-k.pdf": ["$0.001901", "$0.001592", "$0.002634"],
    "appendix-l.pdf": ["$0.001429", "$0.001007", "$0.001649"],
    "in-south-electric-tariff.pdf":
        ["$16.150", "$2.563", "$0.034582", "$0.040254", "$150.00", "$35.465", "$0.039170",
         "$122,773.50", "4,500 kVa", "$0.005613", "$0.005491", "$2.055", "$0.007281",
         "$0.000732", "$0.000448", "$0.005270", "$0.004000", "$0.064", "$0.065",
         "$0.004428", "$0.003223", "$0.376", "$0.197", "(1.628)", "(1.328)"],
}


def fetch_all():
    for d, fname, url in FILES:
        os.makedirs(d, exist_ok=True)
        dest = os.path.join(d, fname)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=120) as r:
            blob = r.read()
        with open(dest, "wb") as fh:
            fh.write(blob)
        print(f"  fetched {fname}: {len(blob):,} bytes")
        time.sleep(1.3)


def verify_sentinels():
    import pymupdf
    bad = 0
    for d, fname, _url in FILES:
        p = os.path.join(d, fname)
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
            f"\n{bad} file(s) failed sentinel verification. The publisher likely revised the "
            f"book at the same URL. RE-READ the changed sheets and update the ROWS below "
            f"before loading - do NOT load transcriptions that no longer match their source.")


# ------------------------------------------------------------------------------------------
# THE ROWS.  Transcribed by hand from the sheets cited in each comment; sentinel-guarded.
# Column semantics follow docs/TARIFF_SCRAPE_TARGETS.md OUTPUT SHAPE.
# ------------------------------------------------------------------------------------------
def R(utility, tariff_code, tariff_name, component_type, code, name, rate, unit, basis,
      applies_to, season, value_status, effective_date, source, source_url, notes):
    return dict(utility=utility, state="IN", tariff_code=tariff_code, tariff_name=tariff_name,
                component_type=component_type, code=code, name=name, rate=rate, unit=unit,
                basis=basis, applies_to=applies_to, season=season, value_status=value_status,
                effective_date=effective_date, source=source, source_url=source_url, notes=notes)


NO_SEASON = ("No summer/non-summer split anywhere in this book for this class - single "
             "year-round rate stated by the sheet itself; season='all' is the book's "
             "structure, not an assumption.")

# ---- AES Indiana ---------------------------------------------------------------------------
AES_SRC = "AES Indiana (IPL) tariff book IURC No. E-20, issued pursuant to Cause No. 46258"
AES_HL_URL = f"{AES_BASE}/Rate-HL-High-Load-Factor--Primary-Distrib-Sub-Trans-and-Trans-Voltages-46258-Effectve-07-27-26.pdf"
AES_PL_URL = f"{AES_BASE}/Rate-PL-Primary-Service-Large-46258-Effectve-07-27-26.pdf"
AES_SL_URL = f"{AES_BASE}/Rate-SL-Secondary-Service-Large-46258-Effectve-07-27-26.pdf"
AES_LCI_URL = f"{AES_BASE}/Large-Commercial-and-Industrial-Rates-46258-Effectve-07-27-26.pdf"
AES_CSC_URL = f"{AES_BASE}/Rate-CSC-Customer-Specific-Contracts-46258-Effectve-07-27-26.pdf"
AES_RIDERS_URL = f"{AES_BASE}/Contract-Riders_All_Effective_07-27-26.pdf"
AES_FAC_URL = f"{AES_BASE}/Rider-6-FAC-46258-Effective-07-27-26.pdf"
AES_FACT_URL = f"{AES_BASE}/07-24-26%20Contract%20Rider%20Sheet_0.pdf"
E0727 = "2026-07-27"
E0724 = "2026-07-24"

AES_PF_BASIS = ("Multiplier on (demand charge + energy charge); 1.0000 at 85% lagging PF, "
                "0.951 at PF=1.00, 1.3335 at PF=0.50; no credit for leading PF")

AES_ROWS = [
    # -- Rate HL (Original Nos. 58-60) --
    R(AES, "HL", "High Load Factor (Primary Distribution, Sub-Transmission and Transmission Voltages)",
      "eligibility", "HL-FLOOR", "Minimum contract demand", 2000.0, "kW",
      "minimum contract demand", "all voltages", "all", "published", E0727, AES_SRC, AES_HL_URL,
      "Existing transmission customers with annual avg billing load factor <15% are moved to the "
      "low-load-factor transmission rate (defined on the same sheet)."),
    R(AES, "HL", "High Load Factor", "eligibility", "HL-TERM", "Standard contract term", 5.0, "years",
      "standard term", "all voltages", "all", "published", E0727, AES_SRC, AES_HL_URL, None),
    R(AES, "HL", "High Load Factor", "base_charge", "HL-CUST-PRI", "Customer charge - primary distribution",
      150.00, "$/month", "per delivery point", "primary distribution (4,160/13,200 V)", "all",
      "published", E0727, AES_SRC, AES_HL_URL, None),
    R(AES, "HL", "High Load Factor", "base_charge", "HL-CUST-SUBT", "Customer charge - sub-transmission",
      215.00, "$/month", "per delivery point", "sub-transmission (34,500 V)", "all",
      "published", E0727, AES_SRC, AES_HL_URL, None),
    R(AES, "HL", "High Load Factor", "base_charge", "HL-CUST-TRANS", "Customer charge - transmission",
      500.00, "$/month", "per delivery point", "transmission (138,000/345,000 V)", "all",
      "published", E0727, AES_SRC, AES_HL_URL, None),
    R(AES, "HL", "High Load Factor", "base_charge", "HL-CUST-LLFT", "Customer charge - low-load-factor transmission",
      520.20, "$/month", "per delivery point", "low-load-factor transmission (<15% annual LF)", "all",
      "published", E0727, AES_SRC, AES_HL_URL, None),
    R(AES, "HL", "High Load Factor", "demand", "HL-DEM-PRI", "Demand charge - primary distribution",
      34.30, "$/kW/month", "all kW of billing demand", "primary distribution (4,160/13,200 V)", "all",
      "published", E0727, AES_SRC, AES_HL_URL, NO_SEASON),
    R(AES, "HL", "High Load Factor", "demand", "HL-DEM-SUBT", "Demand charge - sub-transmission",
      25.20, "$/kW/month", "all kW of billing demand", "sub-transmission (34,500 V)", "all",
      "published", E0727, AES_SRC, AES_HL_URL,
      "Voltage delta vs primary: -9.10 $/kW-mo."),
    R(AES, "HL", "High Load Factor", "demand", "HL-DEM-TRANS", "Demand charge - transmission",
      25.00, "$/kW/month", "all kW of billing demand", "transmission (138,000/345,000 V)", "all",
      "published", E0727, AES_SRC, AES_HL_URL,
      "THE decision number: -9.30 $/kW-mo vs primary = ~$3.9M/yr on 35 MW, weighed against "
      "customer-owned step-down (Customer owns everything past the POD on this rate)."),
    R(AES, "HL", "High Load Factor", "demand", "HL-DEM-LLFT", "Demand charge - low-load-factor transmission",
      15.42, "$/kW/month", "all kW of billing demand", "low-load-factor transmission (<15% annual LF)",
      "all", "published", E0727, AES_SRC, AES_HL_URL, None),
    R(AES, "HL", "High Load Factor", "energy", "HL-EN-PRI", "Energy charge - primary distribution",
      0.050079, "$/kWh", "all kWh, single block", "primary distribution", "all",
      "published", E0727, AES_SRC, AES_HL_URL, "Book states 5.0079 cents net per KWH. " + NO_SEASON),
    R(AES, "HL", "High Load Factor", "energy", "HL-EN-SUBT", "Energy charge - sub-transmission",
      0.050527, "$/kWh", "all kWh, single block", "sub-transmission", "all",
      "published", E0727, AES_SRC, AES_HL_URL, "5.0527 cents/kWh."),
    R(AES, "HL", "High Load Factor", "energy", "HL-EN-TRANS", "Energy charge - transmission",
      0.049885, "$/kWh", "all kWh, single block", "transmission", "all",
      "published", E0727, AES_SRC, AES_HL_URL, "4.9885 cents/kWh."),
    R(AES, "HL", "High Load Factor", "energy", "HL-EN-LLFT", "Energy charge - low-load-factor transmission",
      0.076468, "$/kWh", "all kWh, single block", "low-load-factor transmission", "all",
      "published", E0727, AES_SRC, AES_HL_URL, "7.6468 cents/kWh."),
    R(AES, "HL", "High Load Factor", "ratchet", "HL-RATCHET", "Billing demand ratchet",
      75.0, "% of highest billing demand, preceding 11 months",
      "billing demand = avg of 3 highest 15-min interval demands in month; not less than 75% of "
      "highest billing demand in preceding 11 months; never below 2,000 kW",
      "all voltages", "all", "published", E0727, AES_SRC, AES_HL_URL,
      "Quasi-fixes the demand leg: winter curtailment saves at most 25% of the demand charge."),
    R(AES, "HL", "High Load Factor", "rider", "HL-PF", "Power factor adjustment",
      None, "multiplier", AES_PF_BASIS, "all voltages", "all", "published", E0727, AES_SRC,
      AES_HL_URL, "Full table printed in the PDF (PF 0.50-1.00). A rate NULL here means "
      "'published as a table, not one number' - see basis."),

    # -- Rate PL (Original Nos. 53-55) --
    R(AES, "PL", "Primary Service (Large)", "eligibility", "PL-FLOOR", "Minimum contract demand",
      500.0, "kW", "minimum contract demand", "primary distribution", "all", "published",
      E0727, AES_SRC, AES_PL_URL, None),
    R(AES, "PL", "Primary Service (Large)", "eligibility", "PL-TERM", "Standard contract term",
      3.0, "years", "standard term", "primary distribution", "all", "published", E0727,
      AES_SRC, AES_PL_URL, None),
    R(AES, "PL", "Primary Service (Large)", "base_charge", "PL-CUST", "Customer charge",
      133.00, "$/month", "per delivery point", "primary distribution", "all", "published",
      E0727, AES_SRC, AES_PL_URL, None),
    R(AES, "PL", "Primary Service (Large)", "demand", "PL-DEM", "Demand charge",
      30.98, "$/kW/month", "all kW of billing demand", "primary distribution", "all",
      "published", E0727, AES_SRC, AES_PL_URL, NO_SEASON),
    R(AES, "PL", "Primary Service (Large)", "energy", "PL-EN", "Energy charge",
      0.051710, "$/kWh", "all kWh, single block", "primary distribution", "all",
      "published", E0727, AES_SRC, AES_PL_URL, "5.1710 cents/kWh."),
    R(AES, "PL", "Primary Service (Large)", "ratchet", "PL-RATCHET", "Billing demand ratchet",
      60.0, "% of highest billing demand, preceding 11 months",
      "avg of 3 highest 15-min demands; >=60% of highest billing demand in preceding 11 months; "
      "never below 500 kW", "primary distribution", "all", "published", E0727, AES_SRC,
      AES_PL_URL, None),
    R(AES, "PL", "Primary Service (Large)", "rider", "PL-PF", "Power factor adjustment",
      None, "multiplier", AES_PF_BASIS, "primary distribution", "all", "published", E0727,
      AES_SRC, AES_PL_URL, None),

    # -- Rate SL (Original Nos. 50-52) --
    R(AES, "SL", "Secondary Service (Large)", "eligibility", "SL-FLOOR", "Minimum contract demand",
      50.0, "kW", "minimum contract demand", "secondary", "all", "published", E0727, AES_SRC,
      AES_SL_URL, None),
    R(AES, "SL", "Secondary Service (Large)", "eligibility", "SL-TERM", "Standard contract term",
      3.0, "years", "standard term", "secondary", "all", "published", E0727, AES_SRC,
      AES_SL_URL, None),
    R(AES, "SL", "Secondary Service (Large)", "base_charge", "SL-CUST", "Customer charge",
      128.00, "$/month", "per delivery point", "secondary", "all", "published", E0727,
      AES_SRC, AES_SL_URL, None),
    R(AES, "SL", "Secondary Service (Large)", "demand", "SL-DEM", "Demand charge",
      28.50, "$/kW/month", "all kW of billing demand", "secondary (120/240-277/480 V; Company-owned "
      "transformation)", "all", "published", E0727, AES_SRC, AES_SL_URL, NO_SEASON),
    R(AES, "SL", "Secondary Service (Large)", "energy", "SL-EN", "Energy charge",
      0.049723, "$/kWh", "all kWh, single block", "secondary", "all", "published", E0727,
      AES_SRC, AES_SL_URL, "4.9723 cents/kWh."),
    R(AES, "SL", "Secondary Service (Large)", "ratchet", "SL-RATCHET", "Billing demand ratchet",
      60.0, "% of highest billing demand, preceding 11 months",
      "avg of 3 highest 15-min demands; >=60% of 11-month high; never below 50 kW",
      "secondary", "all", "published", E0727, AES_SRC, AES_SL_URL, None),

    # -- Rate PH (Original Nos. 56-57, in the combined LCI book) --
    R(AES, "PH", "Process Heating", "eligibility", "PH-FLOOR", "Minimum contract demand",
      100.0, "kW", "minimum contract demand; manufacturing process heating only", "secondary/primary",
      "all", "published", E0727, AES_SRC, AES_LCI_URL, None),
    R(AES, "PH", "Process Heating", "base_charge", "PH-CUST", "Customer charge",
      1275.00, "$/month", "per delivery point", "all", "all", "published", E0727, AES_SRC,
      AES_LCI_URL, None),
    R(AES, "PH", "Process Heating", "energy", "PH-EN-B1", "Energy charge - first block",
      0.112363, "$/kWh", "first 250 hours use of billing demand per month", "all", "all",
      "published", E0727, AES_SRC, AES_LCI_URL,
      "Energy-only design - this schedule has NO demand charge (affirmative structure, not a gap)."),
    R(AES, "PH", "Process Heating", "energy", "PH-EN-B2", "Energy charge - tail block",
      0.097587, "$/kWh", "all additional kWh", "all", "all", "published", E0727, AES_SRC,
      AES_LCI_URL, None),
    R(AES, "PH", "Process Heating", "ratchet", "PH-RATCHET", "Billing demand ratchet",
      60.0, "% of highest billing demand, preceding 11 months",
      "avg of 3 highest 15-min demands; >=60% of 11-month high; never below 100 kW", "all",
      "all", "published", E0727, AES_SRC, AES_LCI_URL, None),

    # -- Rate CSC (Original Nos. 61-62) --
    R(AES, "CSC", "Customer Specific Contracts", "eligibility", "CSC-FLOOR", "Minimum contract demand",
      2000.0, "kW", "minimum contract demand; written application; conditions 1-4 (non-standard, "
      "specialized, at-risk new load, or competitive alternative)", "all", "all", "published",
      E0727, AES_SRC, AES_CSC_URL,
      "AES has NO dedicated large-load/data-centre schedule in the 46258 book (roster: SL, PL, PH, "
      "HL, CSC). CSC negotiated contracts are the vehicle for very large loads; submissions go to "
      "the IURC under I.C. 8-1-2-24/25."),
    R(AES, "CSC", "Customer Specific Contracts", "energy", "CSC-RATES", "All charges",
      None, "per contract", "all charges are those contained in the Company-Customer contract",
      "all", "all", "published", E0727, AES_SRC, AES_CSC_URL,
      "Published as a negotiation framework, not numbers. Compensation must exceed the Company's "
      "incremental cost of performance."),

    # -- Fuel base + FAC (Rider 6, Original Nos. 157-158) --
    R(AES, "Rider 6", "Fuel Cost Adjustment", "fuel_base", "FAC-BASE",
      "Fuel base embedded in base rates", 0.043811, "$/kWh",
      "FAC adjustment factor = F/S - 0.043811 (3-month estimated fuel expense over sales)",
      "Rates RS, UW, CW, SS, MD, SH, OES, SL, PL, PH, HL, MU-1, APL, EVX", "all", "published",
      E0727, AES_SRC, AES_FAC_URL,
      "THE most misread number: the base rates already recover 4.3811 c/kWh of fuel. Model fuel "
      "as base energy + (actual fuel - this base), never base + full fuel cost."),
    R(AES, "Rider 6", "Fuel Cost Adjustment", "rider", "R6-FAC", "FAC factor now in effect",
      -0.000801, "$/kWh", "billed kWh; factor in effect ~3 months until superseded",
      "all applicable rates incl. SL, PL, PH, HL", "all", "published", E0727, AES_SRC,
      AES_FAC_URL, "Sheet D states $(0.000801) - a CREDIT. Cause 38703/45258 compliance; "
      "matches the Jul-Sep row of the 07/24/26 factor sheet."),

    # -- Rider factors now in effect (07-24-26 Contract Rider Sheet; per-class columns) --
    R(AES, "Rider 3", "TDSIC", "rider", "R3-TDSIC-HL-PL", "TDSIC factor - HL and PL classes",
      0.000272, "$/kWh", "billed kWh; sheet period Jul-Nov 2026 (Cause 45258 compliance filing)",
      "HL (all voltages), PL", "all", "published", E0724, AES_SRC, AES_FACT_URL,
      "Transmission, Distribution and Storage System Improvement Charge."),
    R(AES, "Rider 3", "TDSIC", "rider", "R3-TDSIC-SL-PH", "TDSIC factor - SL and PH classes",
      0.000233, "$/kWh", "billed kWh; sheet period Jul-Nov 2026", "SL, PH", "all", "published",
      E0724, AES_SRC, AES_FACT_URL, None),
    R(AES, "Rider 20", "Environmental Compliance Cost Recovery", "rider", "R20-ECR-HL-PL",
      "ECR factor - HL and PL classes", 0.001505, "$/kWh",
      "billed kWh; sheet period Jul-Dec 2026 (Cause 42170/45258)", "HL (all voltages), PL", "all",
      "published", E0724, AES_SRC, AES_FACT_URL, None),
    R(AES, "Rider 20", "Environmental Compliance Cost Recovery", "rider", "R20-ECR-SL-PH",
      "ECR factor - SL and PH classes", 0.001661, "$/kWh", "billed kWh; Jul-Dec 2026", "SL, PH",
      "all", "published", E0724, AES_SRC, AES_FACT_URL, None),
    R(AES, "Rider 22", "Demand-Side Management Adjustment", "rider", "R22-DSM-LGCI",
      "DSM factor - large C&I default", 0.010889, "$/kWh",
      "billed kWh; sheet period Jul-Dec 2026 (Cause 43623/45258)", "SL, PL, PH and HL classes",
      "all", "published", E0724, AES_SRC, AES_FACT_URL,
      "LARGEST single rider. Qualifying C&I may OPT OUT: sheet lists Opt-Out group factors "
      "'1' -0.000403, '2' 0, '3' 0, '4' +0.002811, '5' +0.005646, '6' +0.005804 $/kWh "
      "(HL column, Jul-Dec row). A large new load would elect opt-out; model both cases."),
    R(AES, "Rider 24", "Capacity Adjustment", "rider", "R24-CAP-HL-PL",
      "CAP factor - HL and PL classes", 0.001796, "$/kWh", "billed kWh; Jul-Dec 2026 (Cause 44795/45258)",
      "HL (all voltages), PL", "all", "published", E0724, AES_SRC, AES_FACT_URL, None),
    R(AES, "Rider 24", "Capacity Adjustment", "rider", "R24-CAP-SL-PH",
      "CAP factor - SL and PH classes", 0.000979, "$/kWh", "billed kWh; Jul-Dec 2026", "SL, PH",
      "all", "published", E0724, AES_SRC, AES_FACT_URL, None),
    R(AES, "Rider 25", "Off-System Sales Margin Adjustment", "rider", "R25-OSS-HL-PL",
      "OSS factor - HL and PL classes", 0.003599, "$/kWh", "billed kWh; Jul-Dec 2026 (Cause 44795/45258)",
      "HL (all voltages), PL", "all", "published", E0724, AES_SRC, AES_FACT_URL, None),
    R(AES, "Rider 25", "Off-System Sales Margin Adjustment", "rider", "R25-OSS-SL-PH",
      "OSS factor - SL and PH classes", 0.004533, "$/kWh", "billed kWh; Jul-Dec 2026", "SL, PH",
      "all", "published", E0724, AES_SRC, AES_FACT_URL, None),
    R(AES, "Rider 26", "Regional Transmission Organization Adjustment", "rider", "R26-RTO-HL-PL",
      "RTO factor - HL and PL classes", 0.000693, "$/kWh", "billed kWh; sheet period Jul-Oct 2026 "
      "(Cause 44808/45258)", "HL (all voltages), PL", "all", "published", E0724, AES_SRC,
      AES_FACT_URL, None),
    R(AES, "Rider 26", "Regional Transmission Organization Adjustment", "rider", "R26-RTO-SL-PH",
      "RTO factor - SL and PH classes", 0.000824, "$/kWh", "billed kWh; Jul-Oct 2026", "SL, PH",
      "all", "published", E0724, AES_SRC, AES_FACT_URL, None),
    R(AES, "Rider 21", "Green Power Initiative", "rider", "R21-GPR", "GPR factor (voluntary)",
      0.001800, "$/kWh", "billed kWh; VOLUNTARY participation only; Jul-Sep 2026 (Cause 44121/45258)",
      "participating customers, all classes", "all", "published", E0724, AES_SRC, AES_FACT_URL,
      "Exclude from a default bill build-up unless the customer elects green power."),

    # -- Rider 28 Phase-In Rate Adjustment (PRA) - credits, per class, kWh AND kW leg --
    R(AES, "Rider 28", "Phase-In Rate Adjustment", "rider", "R28-PRA-SL-KWH", "PRA credit - SL, energy leg",
      -0.00265, "$/kWh", "Phase I; per billing kWh", "SL", "all", "published", E0727, AES_SRC,
      AES_RIDERS_URL, "Plant-in-Service credit until next base rates; negative = credit."),
    R(AES, "Rider 28", "Phase-In Rate Adjustment", "rider", "R28-PRA-SL-KW", "PRA credit - SL, demand leg",
      -1.52, "$/kW/month", "Phase I; per billing kW", "SL", "all", "published", E0727, AES_SRC,
      AES_RIDERS_URL, None),
    R(AES, "Rider 28", "Phase-In Rate Adjustment", "rider", "R28-PRA-PL-KWH", "PRA credit - PL, energy leg",
      -0.00270, "$/kWh", "Phase I; per billing kWh", "PL", "all", "published", E0727, AES_SRC,
      AES_RIDERS_URL, None),
    R(AES, "Rider 28", "Phase-In Rate Adjustment", "rider", "R28-PRA-PL-KW", "PRA credit - PL, demand leg",
      -1.61, "$/kW/month", "Phase I; per billing kW", "PL", "all", "published", E0727, AES_SRC,
      AES_RIDERS_URL, None),
    R(AES, "Rider 28", "Phase-In Rate Adjustment", "rider", "R28-PRA-HL1-KWH", "PRA credit - HL1, energy leg",
      -0.00264, "$/kWh", "Phase I; per billing kWh", "HL1", "all", "published", E0727, AES_SRC,
      AES_RIDERS_URL, "The book does NOT define the HL1/HL2/HL3 subclass-to-voltage mapping on "
      "this sheet; sequence matches the HL voltage order (primary, sub-trans, transmission) but "
      "that is UNVERIFIED - do not treat the mapping as fact."),
    R(AES, "Rider 28", "Phase-In Rate Adjustment", "rider", "R28-PRA-HL1-KW", "PRA credit - HL1, demand leg",
      -1.81, "$/kW/month", "Phase I; per billing kW", "HL1", "all", "published", E0727, AES_SRC,
      AES_RIDERS_URL, None),
    R(AES, "Rider 28", "Phase-In Rate Adjustment", "rider", "R28-PRA-HL2-KWH", "PRA credit - HL2, energy leg",
      -0.00270, "$/kWh", "Phase I; per billing kWh", "HL2", "all", "published", E0727, AES_SRC,
      AES_RIDERS_URL, None),
    R(AES, "Rider 28", "Phase-In Rate Adjustment", "rider", "R28-PRA-HL2-KW", "PRA credit - HL2, demand leg",
      -1.35, "$/kW/month", "Phase I; per billing kW", "HL2", "all", "published", E0727, AES_SRC,
      AES_RIDERS_URL, None),
    R(AES, "Rider 28", "Phase-In Rate Adjustment", "rider", "R28-PRA-HL3-KWH", "PRA credit - HL3, energy leg",
      -0.00264, "$/kWh", "Phase I; per billing kWh", "HL3", "all", "published", E0727, AES_SRC,
      AES_RIDERS_URL, None),
    R(AES, "Rider 28", "Phase-In Rate Adjustment", "rider", "R28-PRA-HL3-KW", "PRA credit - HL3, demand leg",
      -1.32, "$/kW/month", "Phase I; per billing kW", "HL3", "all", "published", E0727, AES_SRC,
      AES_RIDERS_URL, None),

    # -- Rider 4: the transformation / step-down adder --
    R(AES, "Rider 4", "Additional Charge for Transformers and Other Facilities", "rider", "R4-XFMR",
      "Company-furnished transformation adder", 1.65, "% of installed equipment cost per month",
      "1.65% net of the installed cost of Company-furnished equipment beyond normal service, "
      "monthly, from a revisable inventory", "SS, OES, SL, PL, CSC, HL", "all", "published",
      E0727, AES_SRC, AES_RIDERS_URL,
      "AES's step-down adder is percent-of-cost, NOT $/kW - do not model it as a kW rate."),

    # -- Situational riders with no always-on factor --
    R(AES, "Riders 2/5/8/9/13/14/16/17/19/23/27", "Situational and participation riders", "rider",
      "R-SITUATIONAL", "Stand-by, Short Term, Off-Peak, Net Metering, ACLM, Interruptible Power, "
      "EDG, Curtailment Energy, Interruptible DR, Market-Based DR, Economic Development",
      None, "various", "participation- or contract-specific; no always-on published factor on the "
      "07/24/26 factor sheet", "large C&I as listed per schedule", "all", "not_held", E0727,
      AES_SRC, AES_RIDERS_URL,
      "Each rider sheet publishes mechanics (credits/eligibility) but no flat factor; a bill "
      "build-up without electing any of them needs no line for them. Rider 14/19 interruptible "
      "credits are contract-quantity based - read the rider sheets before modelling them."),
]

# ---- NIPSCO --------------------------------------------------------------------------------
NIP_SRC = ("NIPSCO IURC Electric Service Tariff, Original Volume No. 16 (eff 2025-07-01; "
           "cancels all prior tariffs incl. the 8xx series URDB cites)")
NIP_URL = f"{NIP_BASE}/Electric-Service-Tariff-Entire-Book.pdf"
NIP_PAGE = "https://www.nipsco.com/our-company/about-us/regulatory-information/electric-rates"

NIP_KVAR = ("kVAR computed monthly at 85% lagging PF on peak-period max demand; $0.32 x kVAR "
            "above that level ADDED, below it DEDUCTED; leading kVAR ignored; off-peak = "
            "weekdays 22:00-06:00 CST, weekends, NERC holidays")

NIP_ROWS = [
    # ================= RATE 631 - THE LARGE-LOAD TARIFF (Sheets 72-84) =================
    R(NIP, "631", "Industrial Power Service - Large", "eligibility", "631-FLOOR",
      "Minimum contract demand", 10000.0, "kW",
      "contract demand >=10,000 kW; Transmission or Subtransmission voltage only; premises "
      "adjacent to existing facilities with sufficient capacity; multi-premise aggregation "
      "allowed for common ownership/affiliates if one IDR meter held >=10,000 kW for 12 months",
      "transmission/subtransmission", "all", "published", "2025-07-01", NIP_SRC, NIP_URL,
      "FLAGGED: this is Indiana's purpose-built large-load tariff structure - the class a data "
      "centre takes service under at NIPSCO. Supersedes the 15,000 kW Rate 832 floor URDB shows."),
    R(NIP, "631", "Industrial Power Service - Large", "eligibility", "631-T1-DEFAULT",
      "Tier 1 firm contract demand default election", 30000.0, "kW",
      "default Tier 1 election 30,000 kW, electable above or down to 10,000 kW", "Tier 1", "all",
      "published", "2025-07-01", NIP_SRC, NIP_URL, None),
    R(NIP, "631", "Industrial Power Service - Large", "eligibility", "631-TERM",
      "Minimum contract term", 5.0, "years",
      "initial period not less than five (5) Contract Years; Tier 1 increases need 5 years' "
      "notice + new 5-year term; reductions (premise closure) need 12 months' notice, floor "
      "10,000 kW; Tier 2/3 elections movable quarterly", "all tiers", "all", "published",
      "2025-07-01", NIP_SRC, NIP_URL, None),
    R(NIP, "631", "Industrial Power Service - Large", "demand", "631-T1-DEM", "Tier 1 demand charge",
      35.74, "$/kW/month", "per kW per month, Tier 1 firm service",
      "transmission/subtransmission; Tier 1", "all", "published", "2026-03-01", NIP_SRC, NIP_URL,
      "Second Revised Sheet No. 80. " + NO_SEASON),
    R(NIP, "631", "Industrial Power Service - Large", "energy", "631-T1-EN", "Tier 1 energy charge",
      0.030977, "$/kWh", "all kWh used in the month under Tier 1", "Tier 1", "all", "published",
      "2026-03-01", NIP_SRC, NIP_URL, None),
    R(NIP, "631", "Industrial Power Service - Large", "energy", "631-T2-EN", "Tier 2 energy price",
      None, "$/kWh", "Day-Ahead LMP at the Company Load Zone (NIPS.NIPS) for kWh above Tier 1 "
      "firm contract demand, plus the Transmission Charge", "Tier 2 (non-firm market price)",
      "all", "published", "2025-07-01", NIP_SRC, NIP_URL,
      "Market-priced by formula - published, but not a fixed number. Tier 2 firm only to the "
      "extent customer-procured capacity covers it; otherwise registered as MISO LMR, curtailable "
      "with >=2 hours notice."),
    R(NIP, "631", "Industrial Power Service - Large", "energy", "631-T3-EN", "Tier 3 energy price",
      None, "$/kWh", "MISO settlement charges as Asset Owner (DA demand bids, RT imbalance, "
      "uplift, admin fee) for kWh above Tier 1+Tier 2, plus the Transmission Charge",
      "Tier 3 (non-firm third-party generation)", "all", "published", "2025-07-01", NIP_SRC,
      NIP_URL, "Customer registered as MISO Asset Owner with own CP Node; NIPSCO stays Market "
      "Participant. 5-year Tier 3 disqualification for market-manipulation violations."),
    R(NIP, "631", "Industrial Power Service - Large", "energy", "631-TRANS-CHG", "Transmission charge",
      0.014689, "$/kWh", "gross energy consumed at each IDR, netted by premise; applies to "
      "Tier 1, Tier 2 AND Tier 3", "all tiers", "all", "published", "2026-03-01", NIP_SRC, NIP_URL,
      "The wires leg of the three-part rate; kWh-denominated, not kW."),
    R(NIP, "631", "Industrial Power Service - Large", "energy", "631-AAQF-TRANS",
      "Adjacent affiliate qualifying-facility premise transmission charge", 0.004407, "$/kWh",
      "gross energy transferred from a premise with behind-the-meter generation to an adjacent "
      "commonly-owned/affiliate premise", "aggregated premises with BTM generation", "all",
      "published", "2026-03-01", NIP_SRC, NIP_URL,
      "Rate 732 premises grandfathered on 2018-10-31 net rather than gross."),
    R(NIP, "631", "Industrial Power Service - Large", "base_charge", "631-CUST", "Customer charge",
      None, "$/month", "Sheet 79 defines a THREE-part rate (Demand + Energy + Transmission) "
      "plus riders; no customer-charge line exists in this schedule", "all tiers", "all",
      "not_held", "2025-07-01", NIP_SRC, NIP_URL,
      "Recorded not_held/NULL per the never-zero rule. The omission appears structural (the rate "
      "is defined as three parts), but the book nowhere states 'no customer charge', so this row "
      "does not claim zero. Customer pays installed cost of metering/telemetry/software per the "
      "COMMUNICATIONS section."),
    R(NIP, "631", "Industrial Power Service - Large", "ratchet", "631-T1-DETERMINANT",
      "Tier 1 billing determinant", None, "% of contract demand",
      "Sheet 80 states $35.74 per kW per month WITHOUT naming the billing determinant; Sheet 72 "
      "requires contracting for a 'definite amount' of demand", "Tier 1", "all", "not_held",
      "2026-03-01", NIP_SRC, NIP_URL,
      "Whether Tier 1 bills on contract demand or measured maximum is NOT stated on the rate "
      "sheet. Contract-demand billing is implied but unverified - confirm before modelling "
      "partial-utilization scenarios. Demand measured as 2x max half-hour kWh."),
    R(NIP, "631", "Industrial Power Service - Large", "rider", "631-KVAR", "Reactive demand adjustment",
      0.32, "$/kVAR/month", NIP_KVAR, "all tiers", "all", "published", "2025-07-01", NIP_SRC,
      NIP_URL, None),

    # Rider factors now in effect for 631 Tier 1 (Appendices B,C,F,G,H,I,J,K,L)
    R(NIP, "Rider 670", "Cost of Fuel (FAC)", "fuel_base", "FAC-BASE",
      "Fuel base embedded in base rates", 0.025032, "$/kWh",
      "FAC adjustment factor = (F/S) - 0.025032; F = 3-month est. fuel + purchased power + "
      "fuel-related MISO charge types; S = 3-month kWh sales forecast", "all FAC-applicable "
      "rates incl. 624, 626, 631 Tier 1, 632, 633", "all", "published", "2026-03-01", NIP_SRC,
      NIP_URL, "Second Revised Sheet No. 144. Base rates already recover 2.5032 c/kWh of fuel."),
    R(NIP, "Rider 670", "Cost of Fuel (FAC)", "rider", "R670-FAC", "FAC factor now in effect",
      0.0, "$/kWh", "per kWh; Appendix B", "all FAC-applicable rates", "all", "published",
      "2026-08-01", NIP_SRC, f"{NIP_BASE}/appendix-b.pdf",
      "A PUBLISHED zero (Sixth Revised Sheet 226: 'A charge of $0.000000 per kWh'), not an "
      "absent value."),
    R(NIP, "Rider 671", "RTO Adjustment", "rider", "R671-RTO-631T1", "RTO factor - Rate 631 Tier 1",
      0.003275, "$/kWh", "per kWh used; Appendix C", "Rate 631 Tier 1", "all", "published",
      "2026-05-01", NIP_SRC, f"{NIP_BASE}/appendix-c.pdf",
      "Recovers net non-fuel MISO/RTO costs. Tier 2 has its own factor (separate row); Tier 3 "
      "pays RTO costs through MISO settlements instead."),
    R(NIP, "Rider 671", "RTO Adjustment", "rider", "R671-RTO-631T2", "RTO factor - Rate 631 Tier 2",
      0.001752, "$/kWh", "per kWh used; Appendix C", "Rate 631 Tier 2", "all", "published",
      "2026-05-01", NIP_SRC, f"{NIP_BASE}/appendix-c.pdf", None),
    R(NIP, "Rider 674", "Resource Adequacy", "rider", "R674-RA-631T1", "RA factor - Rate 631 Tier 1",
      -0.000786, "$/kWh", "per kWh used; Appendix F; capacity purchases/sales", "Rate 631 Tier 1",
      "all", "published", "2026-05-01", NIP_SRC, f"{NIP_BASE}/appendix-f.pdf",
      "Currently a CREDIT."),
    R(NIP, "Rider 683", "DSM Adjustment", "rider", "R683-DSMA-631T1", "DSMA factor - Rate 631 Tier 1",
      0.0, "$/kWh", "per kWh used; Appendix G", "Rate 631 Tier 1", "all", "published",
      "2026-03-01", NIP_SRC, f"{NIP_BASE}/appendix-g.pdf",
      "Published $0.000000 for 631 Tier 1 (large industrials broadly opted out; opt-out group "
      "tables on App G sheets 2-6)."),
    R(NIP, "Rider 686", "Green Power Rider", "rider", "R686-GPR", "GPR rate (voluntary)",
      0.003363, "$/kWh", "per kWh; VOLUNTARY participation; Appendix H", "participating "
      "customers, all rates", "all", "published", "2026-07-01", NIP_SRC,
      f"{NIP_BASE}/appendix-h.pdf", None),
    R(NIP, "Rider 687", "Federally Mandated Costs", "rider", "R687-FMCA", "FMCA factor",
      0.0, "$/kWh", "per kWh used; Appendix I", "all applicable rates incl. 631 Tier 1, 632, 633",
      "all", "published", "2026-02-01", NIP_SRC, f"{NIP_BASE}/appendix-i.pdf",
      "Published $0.000000 for every rate schedule at this vintage."),
    R(NIP, "Rider 688", "TDSIC", "rider", "R688-TDSIC-631T1", "TDSIC factor - Rate 631 Tier 1",
      0.000203, "$/kWh", "per kWh used; Appendix J", "Rate 631 Tier 1", "all", "published",
      "2026-03-01", NIP_SRC, f"{NIP_BASE}/appendix-j.pdf", None),
    R(NIP, "Rider 694", "Environmental Cost Tracker", "rider", "R694-ECT-631T1",
      "ECT factor - Rate 631 Tier 1", 0.001901, "$/kWh", "per kWh used; Appendix K",
      "Rate 631 Tier 1", "all", "published", "2026-07-01", NIP_SRC,
      f"{NIP_BASE}/appendix-k.pdf", None),
    R(NIP, "Rider 695", "Generation Costs Tracker", "rider", "R695-GCT-631T1",
      "GCT factor - Rate 631 Tier 1", 0.001429, "$/kWh", "per kWh used; Appendix L",
      "Rate 631 Tier 1", "all", "published", "2026-05-01", NIP_SRC,
      f"{NIP_BASE}/appendix-l.pdf", None),

    # ================= RATE 632 - IPS Small, 15-25 MW (Sheets 85-94) =================
    R(NIP, "632", "Industrial Power Service - Small", "eligibility", "632-FLOOR",
      "Minimum contract capacity", 15000.0, "kW", "contract >=15,000 kW; transmission/"
      "subtransmission voltage", "transmission/subtransmission", "all", "published",
      "2025-07-01", NIP_SRC, NIP_URL,
      "This is the schedule URDB still lists as 'Industrial Power Service' (old Rate 832)."),
    R(NIP, "632", "Industrial Power Service - Small", "eligibility", "632-CEILING",
      "Maximum contract capacity", 25000.0, "kW", "contract shall not exceed 25,000 kW "
      "(Rate 732 premises grandfathered)", "transmission/subtransmission", "all", "published",
      "2025-07-01", NIP_SRC, NIP_URL,
      "A >25 MW load cannot take this schedule - it lands on Rate 631."),
    R(NIP, "632", "Industrial Power Service - Small", "eligibility", "632-TERM",
      "Minimum contract term", 1.0, "years", "initial period >=1 Contract Year, then month-to-"
      "month up to 5 Contract Years; 60 days' termination notice", "all", "all", "published",
      "2025-07-01", NIP_SRC, NIP_URL, None),
    R(NIP, "632", "Industrial Power Service - Small", "demand", "632-DEM", "Demand charge",
      16.73, "$/kW/month", "per kW of Billing Demand", "transmission/subtransmission", "all",
      "published", "2026-03-01", NIP_SRC, NIP_URL, "Second Revised Sheet No. 87. " + NO_SEASON),
    R(NIP, "632", "Industrial Power Service - Small", "energy", "632-EN-B1",
      "Energy charge - first block", 0.076305, "$/kWh", "first 450 hours use of Billing Demand "
      "per month", "all", "all", "published", "2026-03-01", NIP_SRC, NIP_URL,
      "Blocks are hours-use of demand, and they are INVERTED (price RISES with load factor)."),
    R(NIP, "632", "Industrial Power Service - Small", "energy", "632-EN-B2",
      "Energy charge - second block", 0.155863, "$/kWh", "over 450 up to 500 hours use", "all",
      "all", "published", "2026-03-01", NIP_SRC, NIP_URL, None),
    R(NIP, "632", "Industrial Power Service - Small", "energy", "632-EN-B3",
      "Energy charge - tail block", 0.276692, "$/kWh", "over 500 hours use of Billing Demand",
      "all", "all", "published", "2026-03-01", NIP_SRC, NIP_URL,
      "27.7 c/kWh tail: the book prices >68% load factor OUT of this schedule - a high-load-"
      "factor customer belongs on 633 or 631, and this block is why."),
    R(NIP, "632", "Industrial Power Service - Small", "ratchet", "632-RATCHET", "Billing demand",
      75.0, "% (two-sided: contract and 11-month high)",
      "Billing Demand = GREATEST of (1) 75% of Contract Demand, (2) max on-peak half-hour demand, "
      "(3) max off-peak half-hour demand net of Surplus Capacity and B/M/T capacity, (4) 75% of "
      "highest Billing Demand in preceding 11 months (pro-rated on obligation changes)", "all",
      "all", "published", "2025-07-01", NIP_SRC, NIP_URL, None),
    R(NIP, "632", "Industrial Power Service - Small", "base_charge", "632-CUST", "Customer charge",
      None, "$/month", "two-part rate (Demand + Energy) plus riders; no customer-charge line in "
      "the schedule", "all", "all", "not_held", "2025-07-01", NIP_SRC, NIP_URL,
      "not_held/NULL per the never-zero rule; structural omission, but the book does not say "
      "'zero'."),
    R(NIP, "632", "Industrial Power Service - Small", "rider", "632-KVAR", "Reactive demand adjustment",
      0.32, "$/kVAR/month", NIP_KVAR, "all", "all", "published", "2025-07-01", NIP_SRC, NIP_URL, None),
    R(NIP, "632", "Industrial Power Service - Small", "rider", "632-BACKUP-EN",
      "Back-up service energy adder", 0.002332, "$/kWh",
      "Back-up energy bills at Real-Time LMP PLUS this non-fuel adder, first-through-the-meter",
      "back-up service (cogeneration customers)", "all", "published", "2025-07-01", NIP_SRC,
      NIP_URL, "Same adder applies to buy-through temporary energy."),
    R(NIP, "632", "Industrial Power Service - Small", "rider", "632-MAINT-WINTER",
      "Maintenance service demand charge - deep winter months", 0.62, "$/kW/day",
      "confirmed maintenance capacity, Jan/May/Dec; NOT AVAILABLE June-September; 20 days' "
      "notice; max 60 days per rolling 12 months", "maintenance service", "non_summer",
      "published", "2025-07-01", NIP_SRC, NIP_URL,
      "The June-September exclusion here is the ONLY seasonal boundary this book states for "
      "industrial service - the de facto 'summer' is Jun-Sep, defined by exclusion, not by "
      "seasonal base rates."),
    R(NIP, "632", "Industrial Power Service - Small", "rider", "632-MAINT-SHOULDER",
      "Maintenance service demand charge - shoulder months", 0.35, "$/kW/day",
      "confirmed maintenance capacity, Feb/Mar/Apr/Oct/Nov", "maintenance service", "non_summer",
      "published", "2025-07-01", NIP_SRC, NIP_URL, None),
    R(NIP, "Rider 671", "RTO Adjustment", "rider", "R671-RTO-632", "RTO factor - Rate 632",
      0.002626, "$/kWh", "per kWh used; Appendix C", "Rate 632", "all", "published",
      "2026-05-01", NIP_SRC, f"{NIP_BASE}/appendix-c.pdf", None),
    R(NIP, "Rider 674", "Resource Adequacy", "rider", "R674-RA-632", "RA factor - Rate 632",
      -0.000549, "$/kWh", "per kWh used; Appendix F", "Rate 632", "all", "published",
      "2026-05-01", NIP_SRC, f"{NIP_BASE}/appendix-f.pdf", None),
    R(NIP, "Rider 683", "DSM Adjustment", "rider", "R683-DSMA-632", "DSMA factor - Rate 632",
      0.004775, "$/kWh", "per kWh used; Appendix G (default; opt-out tables on sheets 2-6)",
      "Rate 632", "all", "published", "2026-03-01", NIP_SRC, f"{NIP_BASE}/appendix-g.pdf", None),
    R(NIP, "Rider 688", "TDSIC", "rider", "R688-TDSIC-632", "TDSIC factor - Rate 632",
      0.000085, "$/kWh", "per kWh used; Appendix J", "Rate 632", "all", "published",
      "2026-03-01", NIP_SRC, f"{NIP_BASE}/appendix-j.pdf", None),
    R(NIP, "Rider 694", "Environmental Cost Tracker", "rider", "R694-ECT-632", "ECT factor - Rate 632",
      0.001592, "$/kWh", "per kWh used; Appendix K", "Rate 632", "all", "published",
      "2026-07-01", NIP_SRC, f"{NIP_BASE}/appendix-k.pdf", None),
    R(NIP, "Rider 695", "Generation Costs Tracker", "rider", "R695-GCT-632", "GCT factor - Rate 632",
      0.001007, "$/kWh", "per kWh used; Appendix L", "Rate 632", "all", "published",
      "2026-05-01", NIP_SRC, f"{NIP_BASE}/appendix-l.pdf", None),

    # ================= RATE 633 - IPS Small HLF, 10-25 MW (Sheets 95-104) =================
    R(NIP, "633", "Industrial Power Service - Small - HLF", "eligibility", "633-FLOOR",
      "Minimum contract capacity", 10000.0, "kW", "contract >=10,000 kW; transmission/"
      "subtransmission voltage", "transmission/subtransmission", "all", "published",
      "2025-07-01", NIP_SRC, NIP_URL,
      "URDB's 'High Load Factor Industrial' (old Rate 833). The high-load-factor schedule a "
      "sub-25MW data centre would price against 631."),
    R(NIP, "633", "Industrial Power Service - Small - HLF", "eligibility", "633-CEILING",
      "Maximum contract capacity", 25000.0, "kW", "contract shall not exceed 25,000 kW",
      "transmission/subtransmission", "all", "published", "2025-07-01", NIP_SRC, NIP_URL, None),
    R(NIP, "633", "Industrial Power Service - Small - HLF", "eligibility", "633-TERM",
      "Minimum contract term", 1.0, "years", "initial period >=1 Contract Year, then month-to-"
      "month up to 5 Contract Years; 60 days' notice", "all", "all", "published", "2025-07-01",
      NIP_SRC, NIP_URL, None),
    R(NIP, "633", "Industrial Power Service - Small - HLF", "demand", "633-DEM", "Demand charge",
      24.72, "$/kW/month", "per kW of Billing Demand", "transmission/subtransmission", "all",
      "published", "2026-03-01", NIP_SRC, NIP_URL, "Second Revised Sheet No. 97. " + NO_SEASON),
    R(NIP, "633", "Industrial Power Service - Small - HLF", "energy", "633-EN-B1",
      "Energy charge - first block", 0.062933, "$/kWh", "first 600 hours use of Billing Demand "
      "per month", "all", "all", "published", "2026-03-01", NIP_SRC, NIP_URL,
      "Declining blocks (normal direction, unlike 632)."),
    R(NIP, "633", "Industrial Power Service - Small - HLF", "energy", "633-EN-B2",
      "Energy charge - second block", 0.057642, "$/kWh", "over 600 up to 660 hours use", "all",
      "all", "published", "2026-03-01", NIP_SRC, NIP_URL, None),
    R(NIP, "633", "Industrial Power Service - Small - HLF", "energy", "633-EN-B3",
      "Energy charge - tail block", 0.056060, "$/kWh", "over 660 hours use of Billing Demand",
      "all", "all", "published", "2026-03-01", NIP_SRC, NIP_URL, None),
    R(NIP, "633", "Industrial Power Service - Small - HLF", "ratchet", "633-RATCHET", "Billing demand",
      75.0, "% (two-sided: contract and 11-month high)",
      "same greatest-of structure as Rate 632: 75% contract demand / max on-peak half-hour / "
      "max off-peak half-hour net of surplus / 75% of 11-month high (Sheet 100)", "all", "all",
      "published", "2025-07-01", NIP_SRC, NIP_URL, None),
    R(NIP, "633", "Industrial Power Service - Small - HLF", "base_charge", "633-CUST",
      "Customer charge", None, "$/month", "two-part rate plus riders; no customer-charge line",
      "all", "all", "not_held", "2025-07-01", NIP_SRC, NIP_URL, None),
    R(NIP, "633", "Industrial Power Service - Small - HLF", "rider", "633-KVAR",
      "Reactive demand adjustment", 0.32, "$/kVAR/month", NIP_KVAR, "all", "all", "published",
      "2025-07-01", NIP_SRC, NIP_URL, None),
    R(NIP, "633", "Industrial Power Service - Small - HLF", "rider", "633-BACKUP-EN",
      "Back-up service energy adder", 0.002332, "$/kWh", "Real-Time LMP plus this non-fuel adder",
      "back-up service", "all", "published", "2025-07-01", NIP_SRC, NIP_URL, None),
    R(NIP, "Rider 671", "RTO Adjustment", "rider", "R671-RTO-633", "RTO factor - Rate 633",
      0.004468, "$/kWh", "per kWh used; Appendix C", "Rate 633", "all", "published",
      "2026-05-01", NIP_SRC, f"{NIP_BASE}/appendix-c.pdf", None),
    R(NIP, "Rider 674", "Resource Adequacy", "rider", "R674-RA-633", "RA factor - Rate 633",
      -0.000670, "$/kWh", "per kWh used; Appendix F", "Rate 633", "all", "published",
      "2026-05-01", NIP_SRC, f"{NIP_BASE}/appendix-f.pdf", None),
    R(NIP, "Rider 683", "DSM Adjustment", "rider", "R683-DSMA-633", "DSMA factor - Rate 633",
      0.003155, "$/kWh", "per kWh used; Appendix G (default)", "Rate 633", "all", "published",
      "2026-03-01", NIP_SRC, f"{NIP_BASE}/appendix-g.pdf", None),
    R(NIP, "Rider 688", "TDSIC", "rider", "R688-TDSIC-633", "TDSIC factor - Rate 633",
      0.000184, "$/kWh", "per kWh used; Appendix J", "Rate 633", "all", "published",
      "2026-03-01", NIP_SRC, f"{NIP_BASE}/appendix-j.pdf", None),
    R(NIP, "Rider 694", "Environmental Cost Tracker", "rider", "R694-ECT-633", "ECT factor - Rate 633",
      0.002634, "$/kWh", "per kWh used; Appendix K", "Rate 633", "all", "published",
      "2026-07-01", NIP_SRC, f"{NIP_BASE}/appendix-k.pdf", None),
    R(NIP, "Rider 695", "Generation Costs Tracker", "rider", "R695-GCT-633", "GCT factor - Rate 633",
      0.001649, "$/kWh", "per kWh used; Appendix L", "Rate 633", "all", "published",
      "2026-05-01", NIP_SRC, f"{NIP_BASE}/appendix-l.pdf", None),

    # ================= RATE 624 - General Service Large, <=25 MW (Sheets 58-62) =================
    R(NIP, "624", "General Service - Large", "eligibility", "624-FLOOR", "Minimum billing demand",
      50.0, "kW", "minimum Billing Demand 50 kW", "secondary/primary/transmission", "all",
      "published", "2025-07-01", NIP_SRC, NIP_URL, None),
    R(NIP, "624", "General Service - Large", "eligibility", "624-CEILING", "Maximum demand supplied",
      25000.0, "kW", "Company shall not supply demand in excess of 25,000 kW under this schedule",
      "all", "all", "published", "2025-07-01", NIP_SRC, NIP_URL, None),
    R(NIP, "624", "General Service - Large", "base_charge", "624-DEM-B1",
      "First demand block (fixed leg)", 1566.00, "$/month",
      "for the first 50 kW or less of Billing Demand per month - the schedule's de facto fixed "
      "charge", "all", "all", "published", "2026-03-01", NIP_SRC, NIP_URL,
      "Second Revised Sheet No. 59. Recorded as base_charge because it is a flat monthly amount; "
      "it is technically the first demand block."),
    R(NIP, "624", "General Service - Large", "demand", "624-DEM-B2", "Demand charge - second block",
      20.48, "$/kW/month", "next 1,950 kW of Billing Demand", "all", "all", "published",
      "2026-03-01", NIP_SRC, NIP_URL, NO_SEASON),
    R(NIP, "624", "General Service - Large", "demand", "624-DEM-B3", "Demand charge - tail block",
      19.66, "$/kW/month", "all over 2,000 kW of Billing Demand", "all", "all", "published",
      "2026-03-01", NIP_SRC, NIP_URL, None),
    R(NIP, "624", "General Service - Large", "demand", "624-DED-PRI", "Primary service deduction",
      -1.18, "$/kW/month", "service at 11,500/12,500 V with customer-owned transformation: "
      "deducted from the monthly demand charge", "primary voltage delivery", "all", "published",
      "2026-03-01", NIP_SRC, NIP_URL,
      "The voltage delta on this schedule is a DEDUCTION, not a separate rate column."),
    R(NIP, "624", "General Service - Large", "demand", "624-DED-TRANS",
      "Subtransmission/transmission service deduction", -1.46, "$/kW/month",
      "service at 34,500 V or above with customer-owned transformation", "subtransmission/"
      "transmission delivery", "all", "published", "2026-03-01", NIP_SRC, NIP_URL, None),
    R(NIP, "624", "General Service - Large", "energy", "624-EN-B1", "Energy charge - block 1",
      0.132014, "$/kWh", "first 30,000 kWh per month", "all", "all", "published", "2026-03-01",
      NIP_SRC, NIP_URL, "Primary/transmission metering deducts 3% of kWh before billing."),
    R(NIP, "624", "General Service - Large", "energy", "624-EN-B2", "Energy charge - block 2",
      0.120090, "$/kWh", "next 70,000 kWh", "all", "all", "published", "2026-03-01", NIP_SRC,
      NIP_URL, None),
    R(NIP, "624", "General Service - Large", "energy", "624-EN-B3", "Energy charge - block 3",
      0.114593, "$/kWh", "next 900,000 kWh", "all", "all", "published", "2026-03-01", NIP_SRC,
      NIP_URL, None),
    R(NIP, "624", "General Service - Large", "energy", "624-EN-B4", "Energy charge - tail block",
      0.109019, "$/kWh", "all over 1,000,000 kWh per month", "all", "all", "published",
      "2026-03-01", NIP_SRC, NIP_URL, None),
    R(NIP, "624", "General Service - Large", "ratchet", "624-RATCHET-SMALL",
      "Monthly minimum - customers under 3,000 kW", 80.0, "% of highest billing demand, "
      "preceding 12 months", "monthly minimum = demand charge on 80% of the 12-month high, "
      "never below $1,566.00 + riders", "customers <3,000 kW", "all", "published", "2025-07-01",
      NIP_SRC, NIP_URL, None),
    R(NIP, "624", "General Service - Large", "ratchet", "624-RATCHET-LARGE",
      "Monthly minimum - contract demand 3,000 kW or more", 20.39, "$/kW of contract demand",
      "monthly minimum charge = $20.39 x contract demand + riders", "customers >=3,000 kW",
      "all", "published", "2026-03-01", NIP_SRC, NIP_URL,
      "At >=3,000 kW the minimum is effectively the full tail-block demand charge on 104% of "
      "contract demand - demand leg is quasi-fixed."),
    R(NIP, "Rider 671", "RTO Adjustment", "rider", "R671-RTO-624", "RTO factor - Rate 624",
      0.004994, "$/kWh", "per kWh used; Appendix C", "Rate 624", "all", "published",
      "2026-05-01", NIP_SRC, f"{NIP_BASE}/appendix-c.pdf", None),
    R(NIP, "Rider 674", "Resource Adequacy", "rider", "R674-RA-624", "RA factor - Rate 624",
      -0.001120, "$/kWh", "per kWh used; Appendix F", "Rate 624", "all", "published",
      "2026-05-01", NIP_SRC, f"{NIP_BASE}/appendix-f.pdf", None),
    R(NIP, "Rider 683", "DSM Adjustment", "rider", "R683-DSMA-624", "DSMA factor - Rate 624",
      0.005782, "$/kWh", "per kWh used; Appendix G (default)", "Rate 624", "all", "published",
      "2026-03-01", NIP_SRC, f"{NIP_BASE}/appendix-g.pdf", None),
    R(NIP, "Rider 688", "TDSIC", "rider", "R688-TDSIC-624", "TDSIC factor - Rate 624",
      0.001730, "$/kWh", "per kWh used; Appendix J", "Rate 624", "all", "published",
      "2026-03-01", NIP_SRC, f"{NIP_BASE}/appendix-j.pdf", None),
    R(NIP, "Rider 694", "Environmental Cost Tracker", "rider", "R694-ECT-624", "ECT factor - Rate 624",
      0.002458, "$/kWh", "per kWh used; Appendix K", "Rate 624", "all", "published",
      "2026-07-01", NIP_SRC, f"{NIP_BASE}/appendix-k.pdf", None),
    R(NIP, "Rider 695", "Generation Costs Tracker", "rider", "R695-GCT-624", "GCT factor - Rate 624",
      0.002414, "$/kWh", "per kWh used; Appendix L", "Rate 624", "all", "published",
      "2026-05-01", NIP_SRC, f"{NIP_BASE}/appendix-l.pdf", None),
]

# ---- CenterPoint / SIGECO --------------------------------------------------------------------
SIG_SRC = ("Southern Indiana Gas & Electric d/b/a CenterPoint Energy Indiana South (CEI South), "
           "Tariff for Electric Service, IURC No. E-14")
SIG_URL = f"{SIG_BASE}/in-south-electric-tariff.pdf"

SIG_OFFPEAK = ("off-peak demands (Saturdays, Sundays, Company holidays, and 20:00-07:00 daily) "
               "disregarded in billing demand, but billing demand never below 50% of the "
               "month's maximum whenever it occurred")

SIG_ROWS = [
    # ================= RATE LP (Sheet 17) =================
    R(SIG, "LP", "Large Power Service", "eligibility", "LP-FLOOR", "Minimum qualifying demand",
      300.0, "kVA", "Prior Year Maximum Demand of 300 kVA or greater; primary or transmission "
      "voltage", "primary or transmission", "all", "published", "2026-03-05", SIG_SRC, SIG_URL,
      "NOTE THE UNIT: this book bills demand in kVA, not kW - power factor is priced through "
      "the kVA basis rather than a separate PF clause."),
    R(SIG, "LP", "Large Power Service", "eligibility", "LP-TERM", "Minimum contract term",
      3.0, "years", "initial term >=3 years (longer if unusual Company expenditure); renews "
      "annually; 1 year cancellation notice", "all", "all", "published", "2025-02-13", SIG_SRC,
      SIG_URL, None),
    R(SIG, "LP", "Large Power Service", "base_charge", "LP-CUST", "Customer facilities charge",
      150.00, "$/month", "per month", "all", "all", "published", "2026-03-05", SIG_SRC, SIG_URL, None),
    R(SIG, "LP", "Large Power Service", "demand", "LP-DEM", "Demand charge",
      16.150, "$/kVA/month", "all kVA of Billing Demand", "primary (4160/2400, 12470/7200 V) "
      "or transmission", "all", "published", "2026-03-05", SIG_SRC, SIG_URL,
      "Third Revised Page 1 of 3. " + NO_SEASON),
    R(SIG, "LP", "Large Power Service", "demand", "LP-TVD", "Transmission voltage discount",
      -2.563, "$/kVA/month", "all kVA of Billing Demand, for delivery at 69 kV or higher",
      "transmission delivery (69/138 kV)", "all", "published", "2026-03-05", SIG_SRC, SIG_URL,
      "The voltage delta on this schedule: transmission-delivered LP pays 13.587 $/kVA-mo net."),
    R(SIG, "LP", "Large Power Service", "energy", "LP-EN", "Energy charge (non-fuel)",
      0.034582, "$/kWh", "all kWh used per month", "all", "all", "published", "2026-03-05",
      SIG_SRC, SIG_URL, None),
    R(SIG, "LP", "Large Power Service", "fuel_base", "LP-FUEL-BASE", "Fuel charge (base fuel)",
      0.040254, "$/kWh", "all kWh used per month; confirmed as the line-loss-adjusted 'Base "
      "Fuel' for LP in Appendix A (FAC = F/S/(1-LLF) - this base; LP line loss 4.272206%)",
      "all", "all", "published", "2026-03-05", SIG_SRC, SIG_URL,
      "Unlike AES/NIPSCO this book UNBUNDLES the fuel base as its own schedule line - do not "
      "add it to the energy charge AND treat FAC as full fuel."),
    R(SIG, "LP", "Large Power Service", "energy", "LP-VPC", "Variable production charge",
      0.001652, "$/kWh", "all kWh used per month", "all", "all", "published", "2026-03-05",
      SIG_SRC, SIG_URL, None),
    R(SIG, "LP", "Large Power Service", "ratchet", "LP-RATCHET", "Billing demand ratchet",
      60.0, "% of highest prior-year maximum demand",
      "Billing Demand = max demand, but >=60% of highest Maximum Demand of the Prior Year and "
      ">=300 kVA; " + SIG_OFFPEAK, "all", "all", "published", "2026-07-01", SIG_SRC, SIG_URL, None),

    # LP rider factors now in effect
    R(SIG, "Appendix A", "Fuel Adjustment Clause", "rider", "APXA-FAC-LP", "FAC factor - LP",
      0.005613, "$/kWh", "per kWh; Aug-Oct 2026 window; Cause 38708-FAC151", "Rate LP", "all",
      "published", "2026-08-01", SIG_SRC, SIG_URL, None),
    R(SIG, "Appendix A", "Fuel Adjustment Clause", "rider", "APXA-NGPPS-LP",
      "Natural gas power plant pipeline service - LP", 2.239, "$/kVA/month",
      "demand-adjusted allocation of gas pipeline service costs, part of the FAC appendix",
      "Rate LP", "all", "published", "2026-08-01", SIG_SRC, SIG_URL,
      "A demand-denominated fuel-side adder - easy to miss because it lives inside Appendix A."),
    R(SIG, "Appendix B", "Demand Side Management Adjustment", "rider", "APXB-DSMA-LP-KW",
      "DSMA charge - LP demand leg", 2.055, "$/kVA/month", "participating customers "
      "(LP/BAMP row); >1 MW customers may opt out", "Rate LP participants", "all", "published",
      "2026-01-01", SIG_SRC, SIG_URL,
      "Opt-out groups pay only small reconciliation trickles (e.g. 2014 group LP $0.004/kVA + "
      "$0.000074/kWh). A new >1 MW customer can opt out immediately on signing."),
    R(SIG, "Appendix B", "Demand Side Management Adjustment", "rider", "APXB-DSMA-LP-KWH",
      "DSMA charge - LP energy leg", 0.007281, "$/kWh", "participating customers", "Rate LP "
      "participants", "all", "published", "2026-01-01", SIG_SRC, SIG_URL, None),
    R(SIG, "Appendix C", "Clean Energy Cost Adjustment", "rider", "APXC-CECA-LP", "CECA - LP",
      0.000732, "$/kWh", "per kWh; 4CP allocation 32.6662%", "Rate LP", "all", "published",
      "2026-06-01", SIG_SRC, SIG_URL, None),
    R(SIG, "Appendix E", "Environmental Cost Adjustment", "rider", "APXE-ECA-LP", "ECA - LP",
      0.000286, "$/kWh", "per kWh", "Rate LP", "all", "published", "2026-03-05", SIG_SRC,
      SIG_URL, None),
    R(SIG, "Appendix F", "Securitization of Coal Plants", "rider", "APXF-SCP-LP", "SCP - LP",
      0.005270, "$/kWh", "per kWh; securitization charges for retired coal plant balances",
      "Rate LP", "all", "published", "2026-07-01", SIG_SRC, SIG_URL, None),
    R(SIG, "Appendix G", "Securitization Rate Reduction", "rider", "APXG-SRR", "SRR (suspended)",
      0.0, "$/kWh", "SUSPENDED - published at $0.000000 for all schedules", "all rates", "all",
      "published", "2026-03-05", SIG_SRC, SIG_URL, None),
    R(SIG, "Appendix H", "Securitization ADIT Credit", "rider", "APXH-SAC-LP", "SAC - LP",
      -0.000555, "$/kWh", "per kWh credit", "Rate LP", "all", "published", "2026-07-01",
      SIG_SRC, SIG_URL, None),
    R(SIG, "Appendix I", "MISO Cost and Revenue Adjustment", "rider", "APXI-MCRA-LP", "MCRA - LP",
      0.064, "$/kVA/month", "DEMAND-adjusted for LP (energy-adjusted only for small classes); "
      "allocation 30.5749%", "Rate LP", "all", "published", "2026-01-08", SIG_SRC, SIG_URL, None),
    R(SIG, "Appendix J", "Reliability Cost and Revenue Adjustment", "rider", "APXJ-RCRA-LP",
      "RCRA - LP", 0.004428, "$/kWh", "per kWh; non-fuel purchased power, interruptible credits, "
      "emission allowances, net of wholesale margin", "Rate LP", "all", "published",
      "2025-11-01", SIG_SRC, SIG_URL, None),
    R(SIG, "Appendix K", "TDSIC", "rider", "APXK-TDSIC-LP", "TDSIC - LP", 0.376, "$/kVA/month",
      "DEMAND-based for LP", "Rate LP", "all", "published", "2026-06-01", SIG_SRC, SIG_URL, None),
    R(SIG, "Appendix K", "TDSIC", "rider", "APXK-TDSIC-LP-TVD", "TDSIC - LP transmission voltage",
      -0.234, "$/kVA/month", "TDSIC credit for LP transmission-voltage delivery (LP-TVD row)",
      "Rate LP at transmission voltage", "all", "published", "2026-06-01", SIG_SRC, SIG_URL, None),
    R(SIG, "Appendix L", "Tax Adjustment Rider", "rider", "APXL-TAR-LP", "TAR - LP",
      -1.628, "$/kVA/month", "demand-based CREDIT", "Rate LP", "all", "published", "2026-03-11",
      SIG_SRC, SIG_URL, None),

    # ================= RATE HLF (Sheet 18) =================
    R(SIG, "HLF", "High Load Factor Service", "eligibility", "HLF-FLOOR", "Minimum contract demand",
      4500.0, "kVA", "single point of delivery; Contract Demand >=4,500 kVA; TRANSMISSION "
      "voltage only (69,000/138,000 V)", "transmission only", "all", "published", "2026-07-01",
      SIG_SRC, SIG_URL,
      "Not available where an alternate power source is used, for resale, or as supplement to "
      "another schedule."),
    R(SIG, "HLF", "High Load Factor Service", "eligibility", "HLF-TERM", "Minimum contract term",
      5.0, "years", "initial term >=5 years; renews for equal successive terms; 3 years' "
      "cancellation notice", "all", "all", "published", "2025-02-13", SIG_SRC, SIG_URL, None),
    R(SIG, "HLF", "High Load Factor Service", "demand", "HLF-DEM", "Demand charge",
      35.465, "$/kVA/month", "all kVA of Billing Demand", "transmission (69/138 kV)", "all",
      "published", "2026-07-01", SIG_SRC, SIG_URL,
      "Fourth Revised Page 1 of 2. Demand-heavy design: this single charge carries the non-fuel "
      "revenue - there is NO base energy charge on HLF. " + NO_SEASON),
    R(SIG, "HLF", "High Load Factor Service", "demand", "HLF-MIN", "Minimum monthly charge floor",
      122773.50, "$/month", "minimum monthly charge = the Demand Charge, but never less than "
      "this amount (= 35.465 x ~3,462 kVA)", "all", "all", "published", "2026-07-01", SIG_SRC,
      SIG_URL, None),
    R(SIG, "HLF", "High Load Factor Service", "energy", "HLF-EN", "Base energy charge",
      None, "$/kWh", "NO base energy charge exists on this schedule - energy cost enters only "
      "through the Fuel Charge, Variable Production Charge and Appendix adjustments", "all",
      "all", "published", "2026-07-01", SIG_SRC, SIG_URL,
      "Affirmative design (the RATES AND CHARGES section lists Demand, Fuel and Variable "
      "Production only), recorded so the model does not hunt for a missing number."),
    R(SIG, "HLF", "High Load Factor Service", "fuel_base", "HLF-FUEL-BASE", "Fuel charge (base fuel)",
      0.039170, "$/kWh", "all kWh; confirmed as HLF 'Base Fuel' in Appendix A (line loss "
      "1.681546%)", "all", "all", "published", "2026-07-01", SIG_SRC, SIG_URL, None),
    R(SIG, "HLF", "High Load Factor Service", "energy", "HLF-VPC", "Variable production charge",
      0.001608, "$/kWh", "all kWh used per month", "all", "all", "published", "2026-07-01",
      SIG_SRC, SIG_URL, None),
    R(SIG, "HLF", "High Load Factor Service", "ratchet", "HLF-RATCHET", "Billing demand ratchet",
      90.0, "% of highest prior-year billing demand (plus 75% contract-demand floors)",
      "Billing Demand = HIGHEST of (1) Maximum Demand, (2) 90% of highest Billing Demand of the "
      "Prior Year, (3) 75% of Contract Demand, (4) 75% of highest Billing Demand during the "
      "contract term; " + SIG_OFFPEAK, "all", "all", "published", "2025-02-13", SIG_SRC, SIG_URL,
      "The strongest ratchet of the three utilities - 90% year-round; winter curtailment saves "
      "almost nothing on the demand leg."),
    R(SIG, "HLF", "High Load Factor Service", "base_charge", "HLF-CUST", "Customer charge",
      None, "$/month", "no customer/facilities charge line in this schedule (LP has one; HLF "
      "does not)", "all", "all", "not_held", "2026-07-01", SIG_SRC, SIG_URL,
      "not_held/NULL per the never-zero rule; the $122,773.50 minimum monthly charge is the "
      "de facto fixed leg."),

    # HLF rider factors now in effect
    R(SIG, "Appendix A", "Fuel Adjustment Clause", "rider", "APXA-FAC-HLF", "FAC factor - HLF",
      0.005491, "$/kWh", "per kWh; Aug-Oct 2026 window; Cause 38708-FAC151", "Rate HLF", "all",
      "published", "2026-08-01", SIG_SRC, SIG_URL, None),
    R(SIG, "Appendix A", "Fuel Adjustment Clause", "rider", "APXA-NGPPS-HLF",
      "Natural gas power plant pipeline service - HLF", 2.388, "$/kVA/month",
      "demand-adjusted; part of the FAC appendix", "Rate HLF", "all", "published", "2026-08-01",
      SIG_SRC, SIG_URL, None),
    R(SIG, "Appendix B", "Demand Side Management Adjustment", "rider", "APXB-DSMA-HLF",
      "DSMA charge - HLF", 0.0, "$/kWh", "published $0.000000 / $0.000 per kVA - the HLF class "
      "carries 0.0000% of DSM program cost", "Rate HLF", "all", "published", "2026-01-01",
      SIG_SRC, SIG_URL, "A PUBLISHED zero, not an absent value."),
    R(SIG, "Appendix C", "Clean Energy Cost Adjustment", "rider", "APXC-CECA-HLF", "CECA - HLF",
      0.000448, "$/kWh", "per kWh; 4CP allocation 0.8569%", "Rate HLF", "all", "published",
      "2026-06-01", SIG_SRC, SIG_URL, None),
    R(SIG, "Appendix E", "Environmental Cost Adjustment", "rider", "APXE-ECA-HLF", "ECA - HLF",
      0.000433, "$/kWh", "per kWh", "Rate HLF", "all", "published", "2026-03-05", SIG_SRC,
      SIG_URL, None),
    R(SIG, "Appendix F", "Securitization of Coal Plants", "rider", "APXF-SCP-HLF", "SCP - HLF",
      0.004000, "$/kWh", "per kWh", "Rate HLF", "all", "published", "2026-07-01", SIG_SRC,
      SIG_URL, None),
    R(SIG, "Appendix H", "Securitization ADIT Credit", "rider", "APXH-SAC-HLF", "SAC - HLF",
      -0.000399, "$/kWh", "per kWh credit", "Rate HLF", "all", "published", "2026-07-01",
      SIG_SRC, SIG_URL, None),
    R(SIG, "Appendix I", "MISO Cost and Revenue Adjustment", "rider", "APXI-MCRA-HLF", "MCRA - HLF",
      0.065, "$/kVA/month", "DEMAND-adjusted; allocation 0.8020%", "Rate HLF", "all",
      "published", "2026-01-08", SIG_SRC, SIG_URL, None),
    R(SIG, "Appendix J", "Reliability Cost and Revenue Adjustment", "rider", "APXJ-RCRA-HLF",
      "RCRA - HLF", 0.003223, "$/kWh", "per kWh", "Rate HLF", "all", "published", "2025-11-01",
      SIG_SRC, SIG_URL, None),
    R(SIG, "Appendix K", "TDSIC", "rider", "APXK-TDSIC-HLF", "TDSIC - HLF", 0.197, "$/kVA/month",
      "DEMAND-based", "Rate HLF", "all", "published", "2026-06-01", SIG_SRC, SIG_URL, None),
    R(SIG, "Appendix L", "Tax Adjustment Rider", "rider", "APXL-TAR-HLF", "TAR - HLF",
      -1.328, "$/kVA/month", "demand-based CREDIT", "Rate HLF", "all", "published", "2026-03-11",
      SIG_SRC, SIG_URL, None),

    # Interruptible riders - status only
    R(SIG, "Rider IP-2", "Interruptible Power Service", "rider", "IP2-STATUS",
      "Interruptible power credit", None, "various",
      "CLOSED CLASS: applicable only to DGS/OSS/LP/HLF customers with >=200 kW interruptible "
      "demand who were taking service under this Rider during September 1997", "legacy "
      "customers only", "all", "not_held", "2025-02-13", SIG_SRC, SIG_URL,
      "Not available to a new data centre. Riders IC (Interruptible Contract) and IO "
      "(Interruptible Option) are the open interruptible paths; their credits are "
      "contract-specific with no flat published factor."),
]

ALL_ROWS = AES_ROWS + NIP_ROWS + SIG_ROWS

RESCRAPE = ("RE-SCRAPE COMMAND: python scripts/load_tariff_books_aes_nipsco_centerpoint.py "
            "--fetch   (idempotent: DELETE WHERE utility IN (the 3 harvested utilities) then "
            "load-job APPEND; sentinel-verifies every PDF before any write; --verify-only for "
            "a no-write check)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="download the source PDFs first")
    ap.add_argument("--verify-only", action="store_true", help="sentinel check only, no writes")
    ap.add_argument("--dry-run", action="store_true", help="verify + row lint, no BigQuery writes")
    args = ap.parse_args()

    if args.fetch:
        print("fetching source PDFs (throttled >=1.3s) ...")
        fetch_all()

    print("\nverifying sentinels against the PDFs on disk ...")
    verify_sentinels()

    # row lint: enums, unit presence, the never-zero rule
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
    n_aes = sum(1 for r in ALL_ROWS if r["utility"] == AES)
    n_nip = sum(1 for r in ALL_ROWS if r["utility"] == NIP)
    n_sig = sum(1 for r in ALL_ROWS if r["utility"] == SIG)
    print(f"row lint ok: {len(ALL_ROWS)} rows (AES {n_aes} | NIPSCO {n_nip} | CenterPoint {n_sig})")

    if args.verify_only or args.dry_run:
        print("no-write mode - stopping before BigQuery.")
        return

    from google.cloud import bigquery
    client = bigquery.Client(project=PROJECT)

    # table must exist (it does - the I&M seed rows live there); create only if a fresh estate
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
    try:
        client.get_table(TABLE)
    except Exception:
        print(f"creating {TABLE} (fresh estate)")
        client.create_table(bigquery.Table(TABLE, schema=schema))

    print(f"\ndeleting prior rows for the 3 harvested utilities (other utilities untouched) ...")
    client.query(
        f"DELETE FROM `{TABLE}` WHERE utility IN (@a, @n, @s)",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("a", "STRING", AES),
            bigquery.ScalarQueryParameter("n", "STRING", NIP),
            bigquery.ScalarQueryParameter("s", "STRING", SIG)])).result()

    print(f"loading {len(ALL_ROWS)} rows via load job (no streaming buffer) ...")
    job = client.load_table_from_json(
        ALL_ROWS, TABLE,
        job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_APPEND"))
    job.result()

    counts = {r.utility: r.n for r in client.query(
        f"SELECT utility, COUNT(*) n FROM `{TABLE}` GROUP BY 1")}
    total = sum(counts.values())
    print("live per-utility counts after load:")
    for u, n in sorted(counts.items()):
        print(f"   {u:45s} {n:>4}")

    # ---- registry row (indiana_app._registry), same run --------------------------------------
    src = ("Utility tariff books (public PDFs, ungated): AES Indiana/IPL IURC E-20 Cause 46258 "
           "(aesindiana.com/rates-tariffs -> /large-commercial-and-industrial-rates, "
           "/contract-riders, /aes-indiana-rider-factors) | NIPSCO IURC Electric Service Tariff "
           f"Original Volume No. 16 ({NIP_PAGE}) | CenterPoint CEI South IURC E-14 "
           "(centerpointenergy.com/en-us/corporate/about-us/rates-tariffs/indiana) | "
           "endpoint_kind=pdf | parameterised PDF endpoints: "
           f"{AES_BASE}/<sheet>.pdf ; {NIP_BASE}/<sheet>.pdf ; {SIG_URL} | plus I&M seed rows "
           "from dc_docket_tracker (IURC 46097) predating this harvest")
    method = (RESCRAPE + " || Duke Energy Indiana and I&M are a SEPARATE harvest (other agent); "
              "this run neither wrote nor deleted their rows. || OBSERVED PUBLISHER VINTAGES "
              "(tariff effective dates, not pull dates): AES Cause 46258 sheets eff 2026-07-27, "
              "rider factor sheet updated 2026-07-24; NIPSCO Volume 16 eff 2025-07-01 with "
              "Second Revised charge sheets eff 2026-03-01 and factor appendices Feb-Aug 2026; "
              "CEI South E-14 sheets eff 2025-02-13 .. 2026-08-01 (per-row effective_date "
              "carries each sheet's own date). || EXCLUDED AND WHY: residential/lighting/small-"
              "C&I schedules (not decision-relevant to large-load siting); AES situational "
              "riders 2/5/8/9/13/14/16/17/19/23/27 carried as one not_held row (participation "
              "riders, no always-on factor); NIPSCO rates 611-626 except 624, and 641-665 "
              "(municipal/lighting/EV/FIT); SIGECO residential/SGS/DGS/lighting and Rate BAMP "
              "detail; SIGECO Rider IP-2 carried as CLOSED-CLASS status row (Sept-1997 legacy "
              "only). Sentinel guard: every load-bearing number is asserted against the PDFs "
              "before any write.")
    notes = (f"Long-format component register: one row per (schedule x component x voltage/tier "
             f"x block). Live counts this run: AES {counts.get(AES, 0)}, NIPSCO "
             f"{counts.get(NIP, 0)}, CenterPoint {counts.get(SIG, 0)}, I&M seed "
             f"{counts.get('Indiana Michigan Power Co (Indiana)', 0)}. HEADLINES: NIPSCO Rate "
             f"631 IS a purpose-built large-load tariff (>=10 MW, 3 tiers, T1 $35.74/kW-mo + "
             f"$0.030977/kWh + $0.014689/kWh transmission on all tiers, 5-yr term, MISO LMR "
             f"curtailment for T2/T3). AES HL voltage delta $9.30/kW-mo (primary $34.30 vs "
             f"transmission $25.00). FUEL BASES EMBEDDED IN BASE RATES - subtract before adding "
             f"any FAC: AES $0.043811, NIPSCO $0.025032, SIGECO LP $0.040254 / HLF $0.039170 "
             f"per kWh. NO seasonal split exists in any of the three books for these classes; "
             f"NIPSCO's Jun-Sep maintenance exclusion is the only stated seasonal boundary. "
             f"UNPUBLISHED IS NULL NEVER 0: not_held rows carry NULL; stated $0.000000 factors "
             f"(NIPSCO FAC/DSMA-631/FMCA, SIGECO SRR/DSMA-HLF) are PUBLISHED zeros. Do not "
             f"overwrite in_rate_component_gaps - it is the before-picture this harvest closes.")
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
        dict(source_id="tariff-book:aes-indiana:e20-46258",
             source_name="AES Indiana (IPL) electric tariff book, IURC No. E-20, Cause 46258",
             endpoint="https://www.aesindiana.com/rates-tariffs",
             endpoint_raw=f"{AES_BASE}/<sheet>.pdf  [sheets: Rate-HL/PL/SL/CSC, "
                          "Large-Commercial-and-Industrial-Rates, Contract-Riders_All, "
                          "Rider-6-FAC, 07-24-26 Contract Rider Sheet]",
             endpoint_kind="pdf", fmt="pdf", utility="Indianapolis Power & Light Co",
             measured_rows=int(counts.get(AES, 0)), last_source_count=int(counts.get(AES, 0)),
             status="BUILT+LOADED - customer/demand/energy by voltage, fuel base 0.043811, "
                    "rider stack with current factors, ratchets, terms; publisher vintage "
                    "2026-07-27 (Cause 46258) + factor sheet 2026-07-24"),
        dict(source_id="tariff-book:nipsco:vol16",
             source_name="NIPSCO IURC Electric Service Tariff, Original Volume No. 16",
             endpoint=NIP_PAGE,
             endpoint_raw=f"{NIP_BASE}/Electric-Service-Tariff-Entire-Book.pdf  [+ appendix-a..l "
                          ".pdf for current rider factors]",
             endpoint_kind="pdf", fmt="pdf", utility="Northern Indiana Pub Serv Co",
             measured_rows=int(counts.get(NIP, 0)), last_source_count=int(counts.get(NIP, 0)),
             status="BUILT+LOADED - FLAGGED: Rate 631 Industrial Power Service-Large is a "
                    "purpose-built large-load tariff (>=10 MW, 3 tiers, MISO LMR). Book eff "
                    "2025-07-01; charge sheets Second Revised eff 2026-03-01; URDB's 8xx series "
                    "is CANCELLED by this volume"),
        dict(source_id="tariff-book:cei-south:e14",
             source_name="CenterPoint Energy Indiana South (SIGECO/Vectren) Tariff for Electric "
                         "Service, IURC No. E-14",
             endpoint="https://www.centerpointenergy.com/en-us/corporate/about-us/rates-tariffs/indiana",
             endpoint_raw=SIG_URL,
             endpoint_kind="pdf", fmt="pdf", utility="Southern Indiana Gas & Elec Co",
             measured_rows=int(counts.get(SIG, 0)), last_source_count=int(counts.get(SIG, 0)),
             status="BUILT+LOADED - LP + HLF with kVA-based demand, unbundled fuel bases "
                    "(LP 0.040254 / HLF 0.039170), full appendix factor stack; sheets eff "
                    "2025-02-13 .. 2026-08-01 (per-sheet vintages on rows)"),
    ]
    for r in reg_rows:
        client.query(
            f"""INSERT `{EN}.registry_sources`
                (source_id, source_name, endpoint, endpoint_raw, endpoint_kind, fmt, utility,
                 geography_state, measured_rows, last_source_count, status, acquisition_method,
                 origin, updated_by, validation, last_validated_at, notes)
                VALUES (@sid, @sn, @ep, @epr, @epk, @fmt, @util, 'IN', @mr, @lsc, @st, @acq,
                        'loader_auto_registration', 'load_tariff_books_aes_nipsco_centerpoint',
                        'OK_COUNTED', CURRENT_TIMESTAMP(), @notes)""",
            job_config=bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("sid", "STRING", r["source_id"]),
                bigquery.ScalarQueryParameter("sn", "STRING", r["source_name"]),
                bigquery.ScalarQueryParameter("ep", "STRING", r["endpoint"]),
                bigquery.ScalarQueryParameter("epr", "STRING", r["endpoint_raw"]),
                bigquery.ScalarQueryParameter("epk", "STRING", r["endpoint_kind"]),
                bigquery.ScalarQueryParameter("fmt", "STRING", r["fmt"]),
                bigquery.ScalarQueryParameter("util", "STRING", r["utility"]),
                bigquery.ScalarQueryParameter("mr", "INT64", r["measured_rows"]),
                bigquery.ScalarQueryParameter("lsc", "INT64", r["last_source_count"]),
                bigquery.ScalarQueryParameter("st", "STRING", r["status"]),
                bigquery.ScalarQueryParameter("acq", "STRING", RESCRAPE),
                bigquery.ScalarQueryParameter("notes", "STRING",
                    "Rows live in energy-platfrom.indiana_app.in_utility_tariff_riders (energy "
                    "dataset untouched beyond this append). Publisher vintage = tariff effective "
                    "dates carried per row, never the pull timestamp.")])).result()
        print(f"appended energy.registry_sources: {r['source_id']}")

    print("\nDONE")


if __name__ == "__main__":
    main()
