"""Correction + deepening for in_grid_plans:
A) Remove the 152 IRP-page rows just appended (they include individual public commenters'
   named PDFs - not plan documents, and no individuals should be profiled). Re-append ONLY
   utility IRP plan volumes/attachments/executive summaries.
B) Second extraction pass on the newest TDSIC plan dockets (45894 CenterPoint, 45647 Duke,
   45557 NIPSCO): download next-best plan/appendix PDFs not tried in pass 1, parse tables,
   append project rows.
"""
import json, os, re, datetime
from bq_util import query, polite_get, save_scratch, load_rows, register, now_utc_iso, client, PROJECT, DATASET
from google.cloud import bigquery

SCRATCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_scratch")
PDF_DIR = os.path.join(SCRATCH, "pdfs")
pulled = now_utc_iso()

# ---------- A. delete bad append ----------
sql = f"DELETE FROM `{PROJECT}.{DATASET}.in_grid_plans` WHERE document_desc='IRP link on IURC IRP page'"
job = client().query(sql)
job.result()
print("deleted IRP-page rows:", job.num_dml_affected_rows)

page = open(os.path.join(SCRATCH, "iurc_irp_page.html"), encoding="utf-8", errors="replace").read()
links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, flags=re.S | re.I)
UT = {"NIPSCO": r"nipsco|northern indiana", "Duke Energy Indiana": r"duke|dei",
      "AES Indiana (IPL)": r"aes|indianapolis power|\bipl\b", "Indiana Michigan Power": r"i&m|indiana michigan|\bim\b",
      "CenterPoint Indiana South (SIGECO/Vectren)": r"centerpoint|vectren|sigeco|southern indiana"}
KEEP = re.compile(r"(integrated resource plan|irp)", re.I)
PLANDOC = re.compile(r"volume|attachment|appendix|executive summary|integrated resource plan|irp report|public advisory|director'?s final report", re.I)
DROP = re.compile(r"comments?\b|comment-|-comments", re.I)

rows, seen = [], set()
for href, label in links:
    lab = re.sub(r"<[^>]+>", " ", label)
    lab = re.sub(r"\s+", " ", lab).strip()
    blob = lab + " " + href
    if not KEEP.search(blob) or DROP.search(blob) or not PLANDOC.search(blob):
        continue
    full = href if href.startswith("http") else "https://www.in.gov" + href
    if full in seen:
        continue
    seen.add(full)
    util = next((u for u, p in UT.items() if re.search(p, blob, re.I)), None)
    yr = re.search(r"20\d{2}", blob)
    rows.append({
        "row_type": "document", "utility": util or "unattributed (IURC IRP page)",
        "docket_number": None, "docket_url": "https://www.in.gov/iurc/energy-division/electricity-industry/integrated-resource-plans",
        "document_name": (lab or href.split("/")[-1])[:300], "document_desc": "utility IRP plan document (IURC IRP page)",
        "filed_date": None, "filed_date_raw": (yr.group(0) if yr else None),
        "document_url": full,
        "extraction_status": "EXTRACTION-DEFERRED (IRP transmission-project appendix not parsed this run)",
        "project_name": None, "project_type": None, "location_text": None,
        "substation_names": None, "line_endpoints": None, "city": None, "county": None,
        "voltage_kv": None, "in_service_year": None, "cost_usd_m": None,
        "location_status": None, "location_grain": None, "raw_row": None,
        "source": "IURC IRP page (filtered: plan volumes only, comments excluded)", "_pulled_at": pulled,
    })
print(f"filtered IRP plan-doc rows: {len(rows)}")
for r_ in rows[:20]:
    print("  ", (r_["utility"] or "")[:42], "|", r_["document_name"][:90])

# ---------- B. second-pass TDSIC extraction ----------
import importlib.util as ilu
spec = ilu.spec_from_file_location("gp", os.path.join(os.path.dirname(os.path.abspath(__file__)), "08_iurc_grid_plans.py"))
# reuse parse_pdf by re-defining minimal pieces here instead of importing (08 executes on import)

COUNTY_WORDS = re.compile(r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)?) County\b")
SUB_WORDS = re.compile(r"\b([A-Z][A-Za-z .'-]{2,30}?) (?:Substation|Sub\b|Station)\b")
COORD = re.compile(r"[-+]?\d{1,2}\.\d{3,}[, ]\s*[-+]?\d{2,3}\.\d{3,}")
TYPE_MAP = [(r"reconductor", "reconductor"), (r"rebuild", "rebuild"),
            (r"new .{0,20}(line|circuit)|line extension", "new line"),
            (r"new .{0,20}substation|substation.{0,20}(new|construct)", "new substation"),
            (r"transformer", "transformer addition"), (r"breaker|relay|recloser", "protection/switching"),
            (r"underground", "undergrounding"), (r"storage|battery", "storage"),
            (r"substation", "substation work"), (r"pole|structure", "structure replacement")]
HDR_HINTS = ("project", "description", "county", "cost", "in-service", "in service", "year", "location", "kv", "voltage")
def classify_type(txt):
    for pat, lab in TYPE_MAP:
        if re.search(pat, txt, re.I):
            return lab
    return None

def parse_pdf(path, meta, max_pages=350):
    import pdfplumber
    out = []
    try:
        with pdfplumber.open(path) as pdf:
            for pg in pdf.pages[:max_pages]:
                try:
                    tables = pg.extract_tables()
                except Exception:
                    continue
                for tb in tables or []:
                    if not tb or len(tb) < 2:
                        continue
                    hdr = [str(c or "").strip().lower() for c in tb[0]]
                    if sum(1 for h in hdr for k in HDR_HINTS if k in h) < 2:
                        continue
                    def col(keys):
                        for i, h in enumerate(hdr):
                            if any(k in h for k in keys):
                                return i
                        return None
                    c_name, c_desc = col(("project name", "project title", "project", "program")), col(("description", "scope", "work"))
                    c_cnty, c_cost = col(("county", "counties")), col(("cost", "estimate", "$"))
                    c_year, c_kv, c_loc = col(("in-service", "in service", "year", "isd")), col(("kv", "voltage")), col(("location", "area", "city", "town"))
                    for tr in tb[1:]:
                        cells = [str(c or "").replace("\n", " ").strip() for c in tr]
                        if not any(cells):
                            continue
                        joined = " | ".join(cells)
                        name = cells[c_name] if c_name is not None and c_name < len(cells) else None
                        desc = cells[c_desc] if c_desc is not None and c_desc < len(cells) else None
                        base = " ".join(x for x in [name, desc, joined] if x)
                        if len(base) < 8:
                            continue
                        county = cells[c_cnty] if c_cnty is not None and c_cnty < len(cells) else None
                        if not county:
                            m = COUNTY_WORDS.search(base)
                            county = (m.group(1) + " County") if m else None
                        subs = ";".join(dict.fromkeys(SUB_WORDS.findall(base))) or None
                        endpoints = None
                        m = re.search(r"([A-Z][A-Za-z .'-]{2,25})\s*(?:-|to|–)\s*([A-Z][A-Za-z .'-]{2,25})\s*(?:\d+ ?kV|line)", base)
                        if m:
                            endpoints = f"{m.group(1).strip()} - {m.group(2).strip()}"
                        kv = None
                        m = re.search(r"(\d{2,3}(?:\.\d)?)\s*kV", (cells[c_kv] if c_kv is not None and c_kv < len(cells) else base), re.I)
                        if m:
                            kv = float(m.group(1))
                        yr = None
                        m = re.search(r"20\d{2}", cells[c_year] if c_year is not None and c_year < len(cells) else "")
                        if m:
                            yr = int(m.group(0))
                        cost = None
                        ctxt = (cells[c_cost] if c_cost is not None and c_cost < len(cells) else "").replace(",", "")
                        m = re.search(r"\$?\s*(\d+(?:\.\d+)?)", ctxt)
                        if m:
                            try:
                                v = float(m.group(1))
                                cost = round(v / 1e6, 3) if v > 100000 else v
                            except ValueError:
                                pass
                        loc_txt = cells[c_loc] if c_loc is not None and c_loc < len(cells) else None
                        status = "directly-plottable" if COORD.search(joined) else ("joinable" if (subs or endpoints or county or loc_txt) else "neither")
                        grain = "county" if (county and not subs and not endpoints and not loc_txt) else ("site" if (subs or endpoints or loc_txt) else None)
                        out.append(dict(meta, row_type="project", extraction_status="extracted",
                                        project_name=(name or desc or joined)[:300], project_type=classify_type(base),
                                        location_text=(loc_txt or "")[:300] or None, substation_names=subs,
                                        line_endpoints=endpoints, city=None, county=county, voltage_kv=kv,
                                        in_service_year=yr, cost_usd_m=cost, location_status=status,
                                        location_grain=grain, raw_row=joined[:1200],
                                        source="pdfplumber table extraction (pass 2)", _pulled_at=pulled))
    except Exception as e:
        print("   parse fail:", e)
    return out

docs = json.load(open(os.path.join(SCRATCH, "grid_plan_rows.json"), encoding="utf-8"))
tried = {d["document_url"] for d in docs if d.get("extraction_status")}
TARGETS = {"45894", "45647", "45557"}
cand = [d for d in docs if d["row_type"] == "document" and d["docket_number"] in TARGETS
        and not d.get("extraction_status") and d["document_name"].lower().endswith(".pdf")
        and re.search(r"appendix|attachment|plan|project", d["document_name"] + " " + d["document_desc"], re.I)
        and not re.search(r"confidential", d["document_name"] + " " + d["document_desc"], re.I)]
def score(d):
    n = (d["document_name"] + " " + d["document_desc"]).lower()
    s = 0
    if re.search(r"(7|seven)[\s-]*year", n): s += 5
    if "appendix" in n or "attachment" in n: s += 3
    if "plan" in n: s += 3
    if "project" in n: s += 3
    if "testimony" in n: s += 1
    return -s
cand.sort(key=score)
per, picked = {}, []
for d in cand:
    if d["document_url"] in tried:
        continue
    if per.get(d["docket_number"], 0) >= 3:
        continue
    picked.append(d)
    per[d["docket_number"]] = per.get(d["docket_number"], 0) + 1
print(f"\npass-2 candidates: {len(picked)}")
proj = []
for d in picked:
    fn = re.sub(r"[^A-Za-z0-9._-]+", "_", d["document_name"])[:120]
    path = os.path.join(PDF_DIR, f'p2_{d["docket_number"]}_{fn}')
    try:
        rr = polite_get(d["document_url"], timeout=240)
        if rr.status_code != 200 or len(rr.content) < 2000 or len(rr.content) > 90_000_000:
            print(f'  DL skip {d["document_name"][:60]} ({rr.status_code}, {len(rr.content)/1e6:.1f}MB)')
            continue
        open(path, "wb").write(rr.content)
        print(f'  DL ok {d["document_name"][:70]} ({len(rr.content)/1e6:.1f} MB)')
    except Exception as e:
        print("  DL fail:", e)
        continue
    meta = {k: d[k] for k in ("utility", "docket_number", "docket_url", "document_name", "document_desc",
                              "filed_date", "filed_date_raw", "document_url")}
    got = parse_pdf(path, meta)
    print(f"   -> {len(got)} project rows")
    proj.extend(got)

allr = rows + proj
print(f"\nappending {len(rows)} IRP doc rows + {len(proj)} pass-2 project rows")
schema = [bigquery.SchemaField(n, t) for n, t in [
    ("row_type", "STRING"), ("utility", "STRING"), ("docket_number", "STRING"), ("docket_url", "STRING"),
    ("document_name", "STRING"), ("document_desc", "STRING"), ("filed_date", "DATE"), ("filed_date_raw", "STRING"),
    ("document_url", "STRING"), ("extraction_status", "STRING"), ("project_name", "STRING"),
    ("project_type", "STRING"), ("location_text", "STRING"), ("substation_names", "STRING"),
    ("line_endpoints", "STRING"), ("city", "STRING"), ("county", "STRING"), ("voltage_kv", "FLOAT64"),
    ("in_service_year", "INT64"), ("cost_usd_m", "FLOAT64"), ("location_status", "STRING"),
    ("location_grain", "STRING"), ("raw_row", "STRING"), ("source", "STRING"), ("_pulled_at", "TIMESTAMP"),
]]
if allr:
    n = load_rows("in_grid_plans", allr, schema, write_disposition="WRITE_APPEND")
    register("in_grid_plans",
             source="IURC IRP page (filtered) + TDSIC dockets 45894/45647/45557 pass-2 PDFs",
             method="CORRECTION: deleted 152 unfiltered IRP-page rows (individual public-comment PDFs excluded; no individuals profiled); re-appended utility IRP plan volumes only. Pass-2 pdfplumber extraction on newest TDSIC plan dockets.",
             n_rows=len(allr), gb_scanned=0.0,
             notes=f"table total now {n}. IRP doc rows {len(rows)} (EXTRACTION-DEFERRED), pass-2 project rows {len(proj)}. Pulled {pulled}.")
save_scratch("grid_pass2_rows.json", json.dumps(allr, indent=1, default=str))
print("DONE")
