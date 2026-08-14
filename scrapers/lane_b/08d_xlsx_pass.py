"""Pass 3: parse public XLSX workpapers from current TDSIC dockets (openpyxl) -> append project rows."""
import json, os, re
from bq_util import polite_get, save_scratch, load_rows, register, now_utc_iso
from google.cloud import bigquery

SCRATCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_scratch")
PDF_DIR = os.path.join(SCRATCH, "pdfs")
pulled = now_utc_iso()

docs = json.load(open(os.path.join(SCRATCH, "grid_plan_rows.json"), encoding="utf-8"))
xlsx = [d for d in docs if d["row_type"] == "document" and d["document_name"].lower().endswith(".xlsx")
        and not re.search(r"confidential", d["document_name"], re.I)]
print("xlsx candidates:", len(xlsx))
for d in xlsx:
    print("  ", d["docket_number"], "|", d["document_name"][:100])

HDR = ("project", "county", "description", "cost", "in-service", "in service", "year", "location", "kv", "voltage", "scope", "station", "line")
COUNTY_WORDS = re.compile(r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)?) County\b")
SUB_WORDS = re.compile(r"\b([A-Z][A-Za-z .'-]{2,30}?) (?:Substation|Sub\b|Station)\b")
TYPE_MAP = [(r"reconductor", "reconductor"), (r"rebuild", "rebuild"),
            (r"new .{0,20}(line|circuit)|line extension", "new line"),
            (r"new .{0,20}substation|substation.{0,20}(new|construct)", "new substation"),
            (r"transformer", "transformer addition"), (r"breaker|relay|recloser", "protection/switching"),
            (r"underground", "undergrounding"), (r"storage|battery", "storage"),
            (r"substation", "substation work"), (r"pole|structure", "structure replacement")]
def ctype(t):
    for p, l in TYPE_MAP:
        if re.search(p, t, re.I):
            return l
    return None

IN_COUNTIES = set("""Adams Allen Bartholomew Benton Blackford Boone Brown Carroll Cass Clark Clay Clinton Crawford
Daviess Dearborn Decatur DeKalb Delaware Dubois Elkhart Fayette Floyd Fountain Franklin Fulton Gibson Grant Greene
Hamilton Hancock Harrison Hendricks Henry Howard Huntington Jackson Jasper Jay Jefferson Jennings Johnson Knox
Kosciusko LaGrange Lake LaPorte Lawrence Madison Marion Marshall Martin Miami Monroe Montgomery Morgan Newton Noble
Ohio Orange Owen Parke Perry Pike Porter Posey Pulaski Putnam Randolph Ripley Rush Scott Shelby Spencer Starke
Steuben Sullivan Switzerland Tippecanoe Tipton Union Vanderburgh Vermillion Vigo Wabash Warren Warrick Washington
Wayne Wells White Whitley""".split())
IN_COUNTIES.add("St. Joseph")

rows = []
import openpyxl
for d in xlsx[:4]:
    fn = re.sub(r"[^A-Za-z0-9._-]+", "_", d["document_name"])[:120]
    path = os.path.join(PDF_DIR, "x_" + d["docket_number"] + "_" + fn)
    try:
        r = polite_get(d["document_url"], timeout=240)
        if r.status_code != 200 or len(r.content) < 1000:
            print("DL fail", r.status_code, d["document_name"][:60])
            continue
        open(path, "wb").write(r.content)
        print(f'DL ok {d["document_name"][:80]} ({len(r.content)/1e6:.2f} MB)')
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        print("open fail:", e)
        continue
    found_doc = 0
    for ws in wb.worksheets:
        try:
            grid = [[("" if c is None else str(c)).strip() for c in row] for row in ws.iter_rows(values_only=True, max_row=3000)]
        except Exception:
            continue
        hdr_i = None
        for i, row in enumerate(grid[:60]):
            joined = " ".join(row).lower()
            score = sum(1 for k in HDR if k in joined)
            if score >= 3 and any("project" in c.lower() for c in row):
                hdr_i = i
                break
        if hdr_i is None:
            continue
        hdr = [c.lower() for c in grid[hdr_i]]
        def col(keys):
            for i, h in enumerate(hdr):
                if any(k in h for k in keys):
                    return i
            return None
        c_name = col(("project name", "project title", "project description", "project"))
        c_desc = col(("description", "scope", "work"))
        c_cnty = col(("county",))
        c_cost = col(("cost", "estimate", "capital"))
        c_year = col(("in-service", "in service", "isd", "year"))
        c_kv = col(("kv", "voltage"))
        c_loc = col(("location", "city", "town", "area"))
        got = 0
        for row in grid[hdr_i + 1:]:
            if not any(row):
                continue
            joined = " | ".join(x for x in row if x)
            name = row[c_name] if c_name is not None and c_name < len(row) else ""
            if not name or len(name) < 3 or name.lower() in ("total", "subtotal"):
                continue
            desc = row[c_desc] if c_desc is not None and c_desc < len(row) else ""
            base = " ".join([name, desc, joined])
            county = row[c_cnty] if c_cnty is not None and c_cnty < len(row) else ""
            if not county:
                m = COUNTY_WORDS.search(base)
                county = (m.group(1) + " County") if m else ""
            else:
                cw = county.strip().title()
                county = (cw + " County") if cw.replace(" County", "") in IN_COUNTIES or cw in IN_COUNTIES else county
            subs = ";".join(dict.fromkeys(SUB_WORDS.findall(base))) or None
            kv = None
            m = re.search(r"(\d{2,3}(?:\.\d)?)\s*kV", (row[c_kv] if c_kv is not None and c_kv < len(row) else base), re.I)
            if m:
                kv = float(m.group(1))
            yr = None
            m = re.search(r"20\d{2}", row[c_year] if c_year is not None and c_year < len(row) else "")
            if m:
                yr = int(m.group(0))
            cost = None
            ctx = (row[c_cost] if c_cost is not None and c_cost < len(row) else "").replace(",", "").replace("$", "")
            m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*$", ctx)
            if m:
                v = float(m.group(1))
                cost = round(v / 1e6, 3) if v > 100000 else v
            loc = row[c_loc] if c_loc is not None and c_loc < len(row) else ""
            status = "joinable" if (subs or county or loc) else "neither"
            grain = "county" if (county and not subs and not loc) else ("site" if (subs or loc) else None)
            rows.append({
                "row_type": "project", "utility": d["utility"], "docket_number": d["docket_number"],
                "docket_url": d["docket_url"], "document_name": d["document_name"],
                "document_desc": d["document_desc"] + f" [sheet: {ws.title}]",
                "filed_date": d["filed_date"], "filed_date_raw": d["filed_date_raw"],
                "document_url": d["document_url"], "extraction_status": "extracted",
                "project_name": name[:300], "project_type": ctype(base),
                "location_text": loc[:300] or None, "substation_names": subs, "line_endpoints": None,
                "city": None, "county": county or None, "voltage_kv": kv, "in_service_year": yr,
                "cost_usd_m": cost, "location_status": status, "location_grain": grain,
                "raw_row": joined[:1200], "source": "openpyxl xlsx extraction (pass 3)", "_pulled_at": pulled,
            })
            got += 1
        if got:
            print(f"   sheet '{ws.title}': {got} rows (hdr row {hdr_i})")
            found_doc += got
    print(f" -> {found_doc} rows from {d['document_name'][:60]}")

print(f"\nxlsx project rows: {len(rows)}")
if rows:
    schema = [bigquery.SchemaField(n, t) for n, t in [
        ("row_type", "STRING"), ("utility", "STRING"), ("docket_number", "STRING"), ("docket_url", "STRING"),
        ("document_name", "STRING"), ("document_desc", "STRING"), ("filed_date", "DATE"), ("filed_date_raw", "STRING"),
        ("document_url", "STRING"), ("extraction_status", "STRING"), ("project_name", "STRING"),
        ("project_type", "STRING"), ("location_text", "STRING"), ("substation_names", "STRING"),
        ("line_endpoints", "STRING"), ("city", "STRING"), ("county", "STRING"), ("voltage_kv", "FLOAT64"),
        ("in_service_year", "INT64"), ("cost_usd_m", "FLOAT64"), ("location_status", "STRING"),
        ("location_grain", "STRING"), ("raw_row", "STRING"), ("source", "STRING"), ("_pulled_at", "TIMESTAMP"),
    ]]
    n = load_rows("in_grid_plans", rows, schema, write_disposition="WRITE_APPEND")
    register("in_grid_plans", source="IURC TDSIC public XLSX workpapers (iurc.portal.in.gov filings)",
             method="APPEND pass-3: openpyxl extraction from public xlsx exhibits/workpapers of current TDSIC dockets",
             n_rows=len(rows), gb_scanned=0.0,
             notes=f"table total now {n}. Pulled {pulled}.")
    save_scratch("grid_xlsx_rows.json", json.dumps(rows, indent=1, default=str))
print("DONE")
