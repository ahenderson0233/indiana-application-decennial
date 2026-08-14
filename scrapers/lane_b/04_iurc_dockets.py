"""IURC docket extraction via the public companion REST API (the advanced-search page's own backend).

Sweeps (each tagged, merged on iurc_legalcaseid):
  - petition types: LLC Project, Economic Development, TDSIC, TAR, EGR, SDC, Certificate of Need(Electric)
  - Contract petitions in Electric / Electric-Gas industries
  - big-five electric utilities x {Rates, Rates & Financing, Tariff Matters}
  - party-name sweeps for data-center actors
Loads matched cases -> energy-platfrom.indiana_app.in_iurc_dockets and registers in _registry.
Observed date = iurc_petitiondate (filing/petition date). _pulled_at = pull time.
"""
import json, re, time, datetime
from bq_util import SESSION, save_scratch, load_rows, register, now_utc_iso
from google.cloud import bigquery

BASE = "https://zus1iurcprodd365companionappmaster-appservice.azurewebsites.net"
URL = BASE + "/api/search/advanced"
DETAIL = "https://iurc.portal.in.gov/docketed-case-details/?id="

IND = {
    "Electric": "002a5051-0a08-e611-80f6-1458d04eabe0",
    "Electric-Gas": "2b0375e8-ae5e-ed11-9562-001dd80726a4",
    "Electric-Gas-Water-Sewer": "ab16a6a3-f7ef-e711-811b-1458d04e2938",
}
PET = {
    "LLC Project": "e298a697-0e43-f111-88b4-001dd80a623a",
    "Economic Development": "f3c7e1c3-d881-e611-8107-1458d04eabe0",
    "Contract": "a7c7e1c3-d881-e611-8107-1458d04eabe0",
    "TDSIC": "d357d9c9-d881-e611-8107-1458d04eabe0",
    "TAR": "43dd572d-dec3-f011-bbd3-001dd8084fd9",
    "EGR": "ee4ea991-0e43-f111-88b4-001dd80a623a",
    "SDC": "5cb64df1-0a4b-ed11-bba0-001dd8027b9e",
    "Certificate of Need": "75c7e1c3-d881-e611-8107-1458d04eabe0",
    "Rates": "bfc8e1c3-d881-e611-8107-1458d04eabe0",
    "Rates & Financing": "cbc8e1c3-d881-e611-8107-1458d04eabe0",
    "Tariff Matters": "f5c8e1c3-d881-e611-8107-1458d04eabe0",
}
UTIL = {
    "Duke Energy Indiana": "e41e61c1-0c08-e611-80ff-1458d04ea8b8",
    "Indiana Michigan Power": "c8e56498-0c08-e611-80f9-1458d04f0178",
    "Indianapolis Power & Light (AES Indiana)": "c78c3bdf-0c08-e611-80ff-1458d04ea8b8",
    "NIPSCO Electric": "ff1cd2d1-0c08-e611-80f9-1458d04f0178",
    "SIGECO/CenterPoint South Electric": "c30d92d6-0c08-e611-80f4-1458d04fc108",
}
PARTIES = ["data center", "Amazon", "Google", "Microsoft", "Meta Platforms", "AWS",
           "Data Center Coalition", "QTS", "Vantage", "Digital Crossroads", "Surge Development", "Stargate"]

def payload(**kw):
    base = {"txtCause": "", "txtSubDocket": "", "ddlPetitionType": "", "ddlCaseStatus": "",
            "ddlIndustry": "", "txtParties": "", "ddlUtilities": "",
            "txtDateBegin": "", "txtDateEnd": "", "txtFilingDateBegin": "", "txtFilingDateEnd": "",
            "txtOrderDateBegin": "", "txtOrderDateEnd": "", "txtPageNumber": "1"}
    base.update(kw)
    return base

def post(pl, retries=2):
    for i in range(retries + 1):
        time.sleep(1.1)
        try:
            r = SESSION.post(URL, json=pl, timeout=60,
                             headers={"Accept": "application/json", "Content-Type": "application/json"})
            if r.status_code == 200:
                return r.json()
            print(f"    HTTP {r.status_code}: {r.text[:120]}")
        except Exception as e:
            print(f"    post err: {e}")
    return None

def sweep(label, max_pages=80, **kw):
    """Run one paged sweep; returns dict guid->row."""
    out = {}
    first = post(payload(**kw))
    if first is None:
        print(f"[sweep] {label}: FAILED")
        return out
    total = first.get("TotalRecords", 0)
    pages = min(first.get("PagerDetails", {}).get("TotalPages", 1) or 1, max_pages)
    print(f"[sweep] {label}: {total} records / {pages} pages")
    def absorb(js):
        for row in js.get("data", []):
            out[row["iurc_legalcaseid"]] = row
    absorb(first)
    for p in range(2, pages + 1):
        js = post(payload(txtPageNumber=str(p), **kw))
        if js is None:
            break
        absorb(js)
    return out

cases = {}          # guid -> row
tags = {}           # guid -> set(labels)

def merge(label, found):
    for g, row in found.items():
        cases[g] = row
        tags.setdefault(g, set()).add(label)

# ---- 1. petition-type sweeps (all industries, all time) ----
for pt in ["LLC Project", "Economic Development", "TDSIC", "TAR", "EGR", "SDC"]:
    merge(f"pet:{pt}", sweep(f"pet:{pt}", ddlPetitionType=PET[pt]))

# Certificate of Need + Contract restricted to electric industries
for indname in ["Electric", "Electric-Gas", "Electric-Gas-Water-Sewer"]:
    merge("pet:Certificate of Need", sweep(f"pet:CoN x {indname}",
          ddlPetitionType=PET["Certificate of Need"], ddlIndustry=IND[indname]))
    merge("pet:Contract", sweep(f"pet:Contract x {indname}",
          ddlPetitionType=PET["Contract"], ddlIndustry=IND[indname]))

# ---- 2. big-five recent rate cases ----
for uname, ug in UTIL.items():
    for pt in ["Rates", "Rates & Financing", "Tariff Matters"]:
        merge(f"big5:{uname}|{pt}", sweep(f"big5 {uname} x {pt}",
              ddlUtilities=ug, ddlPetitionType=PET[pt]))

# ---- 3. party sweeps ----
for pn in PARTIES:
    merge(f"party:{pn}", sweep(f"party:{pn}", txtParties=pn, max_pages=40))

print(f"\nmerged unique cases: {len(cases)}")
save_scratch("iurc_cases_raw.json", json.dumps({g: {"row": r, "tags": sorted(tags[g])} for g, r in cases.items()}, indent=1))

# ---- shape rows ----
DCPARTY = re.compile(r"data cent|amazon|google|microsoft|meta platforms|aws|digital crossroads|qts|vantage|surge dev|stargate", re.I)
def parse_date(s):
    if not s:
        return None
    s = s.strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return None

pulled = now_utc_iso()
rows = []
for g, r in cases.items():
    parties = (r.get("iurc_forpetionersearch") or "").replace("​", "").strip().strip(",").strip()
    filed = parse_date(r.get("iurc_petitiondate"))
    tagset = sorted(tags[g])
    # relevance filters: big5 rate-case sweeps keep only 2022+; everything else keeps all
    only_big5 = all(t.startswith("big5:") for t in tagset)
    if only_big5 and (filed is None or filed < "2022-01-01"):
        continue
    rel = []
    if DCPARTY.search(parties): rel.append("dc_party")
    if any(t.startswith("party:") for t in tagset): rel.append("party_sweep")
    pt = r.get("iurc_petitiontypeid") or ""
    if pt in ("LLC Project", "TAR", "EGR", "SDC"): rel.append("large_load_type")
    if pt == "TDSIC": rel.append("grid_plan_tdsic")
    if pt == "Economic Development": rel.append("economic_development")
    if pt == "Contract": rel.append("special_contract")
    if pt == "Certificate of Need": rel.append("cpcn")
    if any(t.startswith("big5:") for t in tagset) and pt in ("Rates", "Rates & Financing", "Tariff Matters"):
        rel.append("big5_rate_case")
    rows.append({
        "docket_number": r.get("iurc_docketnumber"),
        "subdocket_number": (r.get("iurc_subdocketnumber") or "").replace("NONE", "") or None,
        "industry": r.get("iurc_industry"),
        "petition_type": pt or None,
        "status": r.get("iurc_casestatustype"),
        "filed_date": filed,
        "filed_date_raw": r.get("iurc_petitiondate"),
        "parties": parties or None,
        "case_guid": g,
        "url": DETAIL + g,
        "matched_terms": ";".join(tagset),
        "relevance": ";".join(sorted(set(rel))) or None,
        "source": "IURC companion API (advanced-search backend)",
        "_pulled_at": pulled,
    })

print(f"rows to load: {len(rows)}")
schema = [
    bigquery.SchemaField("docket_number", "STRING"),
    bigquery.SchemaField("subdocket_number", "STRING"),
    bigquery.SchemaField("industry", "STRING"),
    bigquery.SchemaField("petition_type", "STRING"),
    bigquery.SchemaField("status", "STRING"),
    bigquery.SchemaField("filed_date", "DATE"),
    bigquery.SchemaField("filed_date_raw", "STRING"),
    bigquery.SchemaField("parties", "STRING"),
    bigquery.SchemaField("case_guid", "STRING"),
    bigquery.SchemaField("url", "STRING"),
    bigquery.SchemaField("matched_terms", "STRING"),
    bigquery.SchemaField("relevance", "STRING"),
    bigquery.SchemaField("source", "STRING"),
    bigquery.SchemaField("_pulled_at", "TIMESTAMP"),
]
n = load_rows("in_iurc_dockets", rows, schema)
register("in_iurc_dockets",
         source="https://iurc.portal.in.gov/advanced-search/ via companion API " + BASE,
         method="POST /api/search/advanced (anonymous public backend of the search page); sweeps by petition type (LLC Project/Econ Dev/TDSIC/TAR/EGR/SDC/CoN/Contract), big-5 electric utilities x rate petitions (kept 2022+), and data-center party names; 1.1s/request",
         n_rows=n, gb_scanned=0.0,
         notes=f"observed date=iurc_petitiondate (filing). No free-text title field exists in this API; relevance from petition_type+parties. matched_terms lists sweep provenance. Refutes registry 'Indiana URC (EDS) BLOCKED (SPA)'. Pulled {pulled}.")
print("DONE")
