"""Grid upgrade plans from IURC TDSIC dockets -> indiana_app.in_grid_plans.

Row types:
  row_type='document': every plan-relevant public filing found (metadata + URL + extraction_status)
  row_type='project':  a project row parsed from a machine-readable plan PDF table
Never geocodes. location_status: directly-plottable (explicit coords) / joinable (named substation,
line endpoints, city or county) / neither. County-grain rows are labelled location_grain='county'.
RTO plans (MISO MTEP / PJM RTEP) are out of scope per operator boundary.
"""
import json, os, re, time, datetime
from bq_util import SESSION, polite_get, save_scratch, load_rows, register, now_utc_iso
from google.cloud import bigquery

BASE = "https://zus1iurcprodd365companionappmaster-appservice.azurewebsites.net"
PORTAL = "https://iurc.portal.in.gov"
SCRATCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_scratch")
PDF_DIR = os.path.join(SCRATCH, "pdfs")
os.makedirs(PDF_DIR, exist_ok=True)

UTIL_PAT = {
    "NIPSCO": r"northern indiana",
    "Duke Energy Indiana": r"duke energy indiana",
    "AES Indiana (IPL)": r"indianapolis power|aes indiana",
    "Indiana Michigan Power": r"indiana michigan",
    "CenterPoint Indiana South (SIGECO/Vectren)": r"southern indiana gas|centerpoint|vectren",
}

raw = json.load(open(os.path.join(SCRATCH, "iurc_cases_raw.json"), encoding="utf-8"))
tds = []
for g, item in raw.items():
    if "pet:TDSIC" not in item["tags"]:
        continue
    r = item["row"]
    parties = (r.get("iurc_forpetionersearch") or "").replace("​", "")
    sub = (r.get("iurc_subdocketnumber") or "NONE").strip()
    ind = r.get("iurc_industry") or ""
    util = next((u for u, p in UTIL_PAT.items() if re.search(p, parties, re.I)), None)
    def pd(s):
        try:
            return datetime.datetime.strptime(s.strip(), "%m/%d/%Y").date()
        except Exception:
            return datetime.date(1900, 1, 1)
    tds.append({"guid": g, "docket": r.get("iurc_docketnumber"), "sub": sub, "industry": ind,
                "utility": util, "filed": pd(r.get("iurc_petitiondate") or ""), "parties": parties[:300]})

elec = [t for t in tds if t["utility"] and t["industry"].startswith("Electric") and t["sub"] in ("NONE", "")]
elec.sort(key=lambda t: t["filed"], reverse=True)
chosen, per_util = [], {}
for t in elec:
    if per_util.get(t["utility"], 0) < 3:
        chosen.append(t)
        per_util[t["utility"]] = per_util.get(t["utility"], 0) + 1
print("chosen TDSIC base dockets:")
for t in chosen:
    print(f'  {t["utility"]:45s} {t["docket"]} filed {t["filed"]} [{t["industry"]}]')

def post(path, pl, retries=2):
    for _ in range(retries + 1):
        time.sleep(1.1)
        try:
            r = SESSION.post(BASE + path, json=pl, timeout=60,
                             headers={"Accept": "application/json", "Content-Type": "application/json"})
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print("   post err:", e)
    return None

# ---- enumerate filings per chosen docket ----
def filings_for(guid):
    out, page = [], 1
    while page <= 30:
        js = post("/api/document/filings", {"txtPageNumber": str(page), "Id": " " + guid})
        if js is None:
            break
        out.extend(js.get("data", []))
        tp = js.get("PagerDetails", {}).get("TotalPages", 1) or 1
        if page >= tp:
            break
        page += 1
    return out

PLAN_PAT = re.compile(r"(7|seven)[\s-]*year|improvement plan|plan update|tdsic.{0,20}plan|appendix|attachment", re.I)
SKIP_PAT = re.compile(r"confidential|protective|proof of publication|notice of appearance|subpoena|fee ", re.I)

pulled = now_utc_iso()
doc_rows, candidates = [], []
for t in chosen:
    fl = filings_for(t["guid"])
    print(f'{t["utility"]} {t["docket"]}: {len(fl)} filings')
    for f in fl:
        desc = f.get("iurc_description") or ""
        link = f.get("iurc_documentLink") or ""
        fname = ""
        m = re.search(r"file=([^&]+)", link)
        if m:
            from urllib.parse import unquote
            fname = unquote(m.group(1))
        planish = bool(PLAN_PAT.search(desc + " " + fname)) and not SKIP_PAT.search(desc + " " + fname)
        if planish or re.search(r"petition|verified petition", desc, re.I):
            doc_rows.append({
                "row_type": "document", "utility": t["utility"], "docket_number": t["docket"],
                "docket_url": f"{PORTAL}/docketed-case-details/?id={t['guid']}",
                "document_name": fname or desc, "document_desc": desc,
                "filed_date": None, "filed_date_raw": f.get("iurc_datefiled"),
                "document_url": PORTAL + link if link.startswith("/") else link,
                "extraction_status": None,
                "project_name": None, "project_type": None, "location_text": None,
                "substation_names": None, "line_endpoints": None, "city": None, "county": None,
                "voltage_kv": None, "in_service_year": None, "cost_usd_m": None,
                "location_status": None, "location_grain": None, "raw_row": None,
                "source": "IURC companion API /api/document/filings", "_pulled_at": pulled,
            })
            try:
                fd = datetime.datetime.strptime((f.get("iurc_datefiled") or "").strip(), "%m/%d/%Y").date()
                doc_rows[-1]["filed_date"] = fd.isoformat()
            except Exception:
                fd = None
            if planish and fname.lower().endswith(".pdf"):
                candidates.append((t, doc_rows[-1]))

print(f"\nplan-relevant document rows: {len(doc_rows)}; pdf candidates: {len(candidates)}")
save_scratch("grid_doc_rows.json", json.dumps(doc_rows, indent=1, default=str))

# ---- download + parse a capped set of candidate PDFs ----
def score(c):
    n = (c[1]["document_name"] + " " + c[1]["document_desc"]).lower()
    s = 0
    if re.search(r"(7|seven)[\s-]*year", n): s += 5
    if "appendix" in n or "attachment" in n: s += 3
    if "plan" in n: s += 2
    if "project" in n: s += 3
    if "petition" in n: s += 1
    return -s

candidates.sort(key=score)
per_u_dl, picked = {}, []
for t, d in candidates:
    if per_u_dl.get(t["utility"], 0) >= 2:
        continue
    picked.append((t, d))
    per_u_dl[t["utility"]] = per_u_dl.get(t["utility"], 0) + 1

print("downloading:", [(d["document_name"][:70]) for _, d in picked])

COUNTY_WORDS = re.compile(r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)?) County\b")
SUB_WORDS = re.compile(r"\b([A-Z][A-Za-z .'-]{2,30}?) (?:Substation|Sub\b|Station)\b")
COORD = re.compile(r"[-+]?\d{1,2}\.\d{3,}[, ]\s*[-+]?\d{2,3}\.\d{3,}")
TYPE_MAP = [
    (r"reconductor", "reconductor"), (r"rebuild", "rebuild"),
    (r"new .{0,20}(line|circuit)|line extension", "new line"),
    (r"new .{0,20}substation|substation.{0,20}(new|construct)", "new substation"),
    (r"transformer", "transformer addition"), (r"breaker|relay|recloser", "protection/switching"),
    (r"underground", "undergrounding"), (r"storage|battery", "storage"),
    (r"substation", "substation work"), (r"pole|structure", "structure replacement"),
]
HDR_HINTS = ("project", "description", "county", "cost", "in-service", "in service", "year", "location", "kv", "voltage")

def classify_type(txt):
    for pat, lab in TYPE_MAP:
        if re.search(pat, txt, re.I):
            return lab
    return None

def parse_pdf(path, t, d, max_pages=350):
    import pdfplumber
    rows = []
    try:
        with pdfplumber.open(path) as pdf:
            pages = pdf.pages[:max_pages]
            for pg in pages:
                try:
                    tables = pg.extract_tables()
                except Exception:
                    continue
                for tb in tables or []:
                    if not tb or len(tb) < 2:
                        continue
                    hdr = [str(c or "").strip().lower() for c in tb[0]]
                    hits = sum(1 for h in hdr for k in HDR_HINTS if k in h)
                    if hits < 2:
                        continue
                    def col(keys):
                        for i, h in enumerate(hdr):
                            if any(k in h for k in keys):
                                return i
                        return None
                    c_name = col(("project name", "project title", "project", "program"))
                    c_desc = col(("description", "scope", "work"))
                    c_cnty = col(("county", "counties"))
                    c_cost = col(("cost", "estimate", "$"))
                    c_year = col(("in-service", "in service", "year", "isd"))
                    c_kv   = col(("kv", "voltage"))
                    c_loc  = col(("location", "area", "city", "town"))
                    for tr in tb[1:]:
                        cells = [str(c or "").replace("\n", " ").strip() for c in tr]
                        if not any(cells):
                            continue
                        joined = " | ".join(cells)
                        name = cells[c_name] if c_name is not None and c_name < len(cells) else None
                        desc = cells[c_desc] if c_desc is not None and c_desc < len(cells) else None
                        base_txt = " ".join(x for x in [name, desc, joined] if x)
                        if not base_txt or len(base_txt) < 8:
                            continue
                        county = cells[c_cnty] if c_cnty is not None and c_cnty < len(cells) else None
                        if not county:
                            m = COUNTY_WORDS.search(base_txt)
                            county = (m.group(1) + " County") if m else None
                        subs = ";".join(dict.fromkeys(SUB_WORDS.findall(base_txt))) or None
                        endpoints = None
                        m = re.search(r"([A-Z][A-Za-z .'-]{2,25})\s*(?:-|to|–)\s*([A-Z][A-Za-z .'-]{2,25})\s*(?:\d+ ?kV|line)", base_txt)
                        if m:
                            endpoints = f"{m.group(1).strip()} - {m.group(2).strip()}"
                        kv = None
                        m = re.search(r"(\d{2,3}(?:\.\d)?)\s*kV", (cells[c_kv] if c_kv is not None and c_kv < len(cells) else base_txt), re.I)
                        if m:
                            kv = float(m.group(1))
                        yr = None
                        m = re.search(r"20\d{2}", cells[c_year] if c_year is not None and c_year < len(cells) else "")
                        if m:
                            yr = int(m.group(0))
                        cost = None
                        ctxt = cells[c_cost] if c_cost is not None and c_cost < len(cells) else ""
                        m = re.search(r"\$?\s*([\d,]+(?:\.\d+)?)", ctxt.replace(",", ""))
                        if m:
                            try:
                                v = float(m.group(1))
                                cost = round(v / 1e6, 3) if v > 100000 else v  # normalize to $M heuristically
                            except ValueError:
                                pass
                        loc_txt = cells[c_loc] if c_loc is not None and c_loc < len(cells) else None
                        if COORD.search(joined):
                            status = "directly-plottable"
                        elif subs or endpoints or county or loc_txt:
                            status = "joinable"
                        else:
                            status = "neither"
                        grain = "county" if (county and not subs and not endpoints and not loc_txt) else ("site" if (subs or endpoints or loc_txt) else None)
                        rows.append({
                            "row_type": "project", "utility": t["utility"], "docket_number": t["docket"],
                            "docket_url": f"{PORTAL}/docketed-case-details/?id={t['guid']}",
                            "document_name": d["document_name"], "document_desc": d["document_desc"],
                            "filed_date": d["filed_date"], "filed_date_raw": d["filed_date_raw"],
                            "document_url": d["document_url"], "extraction_status": "extracted",
                            "project_name": (name or desc or joined)[:300],
                            "project_type": classify_type(base_txt),
                            "location_text": (loc_txt or "")[:300] or None,
                            "substation_names": subs, "line_endpoints": endpoints,
                            "city": None, "county": county,
                            "voltage_kv": kv, "in_service_year": yr, "cost_usd_m": cost,
                            "location_status": status, "location_grain": grain,
                            "raw_row": joined[:1200],
                            "source": "pdfplumber table extraction", "_pulled_at": pulled,
                        })
    except Exception as e:
        print(f"   parse failed {os.path.basename(path)}: {e}")
    return rows

proj_rows = []
for t, d in picked:
    url = d["document_url"]
    fn = re.sub(r"[^A-Za-z0-9._-]+", "_", d["document_name"])[:120] or "doc.pdf"
    path = os.path.join(PDF_DIR, f'{t["docket"]}_{fn}')
    try:
        rr = polite_get(url, timeout=180)
        if rr.status_code != 200 or len(rr.content) < 2000:
            d["extraction_status"] = f"download-failed HTTP {rr.status_code}"
            print(f"  DL FAIL {url[:120]} -> {rr.status_code}")
            continue
        if len(rr.content) > 90_000_000:
            d["extraction_status"] = "EXTRACTION-DEFERRED (file >90MB)"
            continue
        open(path, "wb").write(rr.content)
        print(f"  DL ok {os.path.basename(path)} ({len(rr.content)/1e6:.1f} MB)")
    except Exception as e:
        d["extraction_status"] = f"download-failed {e}"
        continue
    got = parse_pdf(path, t, d)
    if got:
        d["extraction_status"] = f"extracted ({len(got)} project rows)"
        proj_rows.extend(got)
    else:
        # text check: machine-readable at all?
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                sample = "".join((p.extract_text() or "") for p in pdf.pages[:5])
            d["extraction_status"] = "EXTRACTION-DEFERRED (no project tables found; text present)" if len(sample) > 200 \
                                     else "EXTRACTION-DEFERRED (image-only scan)"
        except Exception as e:
            d["extraction_status"] = f"EXTRACTION-DEFERRED (unreadable: {e})"
    print(f'   -> {d["extraction_status"]}')

all_rows = doc_rows + proj_rows
print(f"\ndocument rows {len(doc_rows)}, project rows {len(proj_rows)}, total {len(all_rows)}")
save_scratch("grid_plan_rows.json", json.dumps(all_rows, indent=1, default=str))

schema = [bigquery.SchemaField(n, t) for n, t in [
    ("row_type", "STRING"), ("utility", "STRING"), ("docket_number", "STRING"), ("docket_url", "STRING"),
    ("document_name", "STRING"), ("document_desc", "STRING"), ("filed_date", "DATE"), ("filed_date_raw", "STRING"),
    ("document_url", "STRING"), ("extraction_status", "STRING"), ("project_name", "STRING"),
    ("project_type", "STRING"), ("location_text", "STRING"), ("substation_names", "STRING"),
    ("line_endpoints", "STRING"), ("city", "STRING"), ("county", "STRING"), ("voltage_kv", "FLOAT64"),
    ("in_service_year", "INT64"), ("cost_usd_m", "FLOAT64"), ("location_status", "STRING"),
    ("location_grain", "STRING"), ("raw_row", "STRING"), ("source", "STRING"), ("_pulled_at", "TIMESTAMP"),
]]
n = load_rows("in_grid_plans", all_rows, schema)
register("in_grid_plans",
         source="IURC TDSIC dockets via companion API + public filing PDFs (iurc.portal.in.gov)",
         method="TDSIC base dockets (latest<=3/electric utility) -> /api/document/filings -> plan/appendix PDFs (<=2/utility, confidential skipped) -> pdfplumber table extraction; no geocoding; location_status classifies plottability",
         n_rows=n, gb_scanned=0.0,
         notes=f"row_type=document ({len(doc_rows)}) = plan-relevant filings w/ URLs+dates+extraction_status; row_type=project ({len(proj_rows)}) = parsed upgrade projects. Observed date=iurc_datefiled. RTO (MTEP/RTEP) excluded per scope boundary. IRP project lists deferred (see findings). Pulled {pulled}.")
print("DONE")
