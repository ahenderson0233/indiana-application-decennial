"""Locate current utility IRPs on IURC's site; append document rows to in_grid_plans (WRITE_APPEND).
IRP transmission-project appendices are EXTRACTION-DEFERRED unless trivially parseable now.
"""
import re, json
from bq_util import polite_get, allowed, save_scratch, load_rows, register, now_utc_iso
from google.cloud import bigquery

pulled = now_utc_iso()
CANDS = [
    "https://www.in.gov/iurc/research-policy-and-planning-division/",
]
page, page_url = None, None
for u in CANDS:
    ok, _ = allowed(u)
    if not ok:
        print("robots disallow", u)
        continue
    r = polite_get(u)
    print(u, "->", r.status_code, len(r.text))
    if r.status_code == 200 and re.search(r"integrated resource", r.text, re.I):
        page, page_url = r.text, u
        if "integrated-resource" in u:
            break
print("using:", page_url)
if page and "integrated-resource" not in (page_url or ""):
    m = re.search(r'href="([^"]*integrated-resource[^"]*)"', page, re.I)
    if m:
        u2 = m.group(1)
        if u2.startswith("/"):
            u2 = "https://www.in.gov" + u2
        r = polite_get(u2)
        print("followed ->", u2, r.status_code)
        if r.status_code == 200:
            page, page_url = r.text, u2

rows = []
if page:
    save_scratch("iurc_irp_page.html", page)
    links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, flags=re.S | re.I)
    UT = {"NIPSCO": r"nipsco|northern indiana", "Duke Energy Indiana": r"duke",
          "AES Indiana (IPL)": r"aes|indianapolis power|ipl", "Indiana Michigan Power": r"i&m|indiana michigan",
          "CenterPoint Indiana South (SIGECO/Vectren)": r"centerpoint|vectren|sigeco|southern indiana gas"}
    seen = set()
    for href, label in links:
        lab = re.sub(r"<[^>]+>", " ", label)
        lab = re.sub(r"\s+", " ", lab).strip()
        if not re.search(r"irp|integrated resource|resource plan", (href + " " + lab), re.I):
            continue
        if re.search(r"contact|about|sitemap", href, re.I):
            continue
        full = href if href.startswith("http") else "https://www.in.gov" + href
        if full in seen:
            continue
        seen.add(full)
        util = next((u for u, p in UT.items() if re.search(p, lab + " " + href, re.I)), None)
        yr = re.search(r"20\d{2}", lab + " " + href)
        rows.append({
            "row_type": "document", "utility": util or "IURC (general IRP page link)",
            "docket_number": None, "docket_url": page_url,
            "document_name": (lab or href.split("/")[-1])[:300], "document_desc": "IRP link on IURC IRP page",
            "filed_date": None, "filed_date_raw": (yr.group(0) if yr else None),
            "document_url": full,
            "extraction_status": "EXTRACTION-DEFERRED (IRP transmission-project appendix not parsed this run)",
            "project_name": None, "project_type": None, "location_text": None,
            "substation_names": None, "line_endpoints": None, "city": None, "county": None,
            "voltage_kv": None, "in_service_year": None, "cost_usd_m": None,
            "location_status": None, "location_grain": None, "raw_row": None,
            "source": "IURC IRP page " + (page_url or ""), "_pulled_at": pulled,
        })
    print(f"IRP link rows: {len(rows)}")
    for r_ in rows[:25]:
        print("  ", (r_["utility"] or "")[:40], "|", r_["document_name"][:80], "|", r_["document_url"][:90])

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
    register("in_grid_plans",
             source=page_url or "in.gov/iurc IRP page",
             method="APPEND: IRP document links per utility from IURC IRP page; robots-allowed; extraction deferred",
             n_rows=len(rows), gb_scanned=0.0,
             notes=f"append event; table total now {n}. IRP appendices (transmission project lists) deferred per operator PDF rule. Pulled {pulled}.")
print("DONE")
