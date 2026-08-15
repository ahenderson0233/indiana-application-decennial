"""Lane E: pull OPERATIONALLY AVAILABLE CAPACITY postings from the public EBBs of
interstate pipelines crossing Indiana, and load to energy-platfrom.indiana_app.

Pipelines & platforms (walls recorded separately in LANE_E_FINDINGS.md):
  ANR Pipeline               TC eConnects SSRS  rs:Format=CSV
  Crossroads Pipeline        TC eConnects SSRS  rs:Format=CSV
  Northern Border Pipeline   TC eConnects SSRS  rs:Format=CSV
  Panhandle Eastern (PEPL)   ET Messenger ipost f=csv
  Trunkline (TGC)            ET Messenger ipost f=csv
  Texas Gas Transmission     GasQuest reporting API (anonymous JSON+CSV)
  Midwestern (MGT)           DTM Trellis PTMS public .do endpoints (JSON+CSV)
  Vector Pipeline            gasnom.com ColdFusion HTML table (dt param lookback)
  NGPL                       KM DART: replicate the page's own EXCEL download button
BLOCKED (not scraped): Rockies Express (Incapsula bot wall), Texas Eastern (robots.txt Disallow: /).

Politeness: >=1.1s per host, UA identifies us, GET/POST replicating only what the
public pages themselves do. No logins, no bot-wall bypasses.
"""
import base64
import csv
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"
SCRATCH = r"C:\Users\ahend\AppData\Local\Temp\claude\C--Users-ahend-Downloads-Decennial-Summer-Work-Remaking-Orennia-REBUILD-PLANNING\e2c5e15c-d0e5-487b-889b-f478a7c7d3d4\scratchpad\lane_e_out"
os.makedirs(SCRATCH, exist_ok=True)
PULLED_AT = datetime.now(timezone.utc).isoformat()
LOOKBACK_DAYS = 7

_last_hit = {}

def _polite(url):
    from urllib.parse import urlparse
    host = urlparse(url).netloc
    wait = 1.1 - (time.time() - _last_hit.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.time()

session = requests.Session()
session.headers.update({"User-Agent": UA})

def get(url, **kw):
    _polite(url)
    r = session.get(url, timeout=kw.pop("timeout", 60), **kw)
    print(f"  GET {r.status_code} {len(r.content):>9,}B {url[:120]}")
    return r

def post(url, **kw):
    _polite(url)
    r = session.post(url, timeout=kw.pop("timeout", 90), **kw)
    print(f"  POST {r.status_code} {len(r.content):>9,}B {url[:120]}")
    return r

def csv_rows(text):
    text = text.lstrip("\ufeff")
    rdr = csv.DictReader(io.StringIO(text))
    out = []
    for row in rdr:
        out.append({(k or "").strip(): (v if v is not None else "") for k, v in row.items() if k is not None})
    return out

def finish(rows, pipeline, platform, url, extra=None):
    for r in rows:
        r["_pipeline"] = pipeline
        r["_platform"] = platform
        r["_source_url"] = url
        r["_pulled_at"] = PULLED_AT
        if extra:
            for k, v in extra.items():
                r.setdefault(k, v)
    return rows

# ---------------------------------------------------------------- TC eConnects
def fetch_tce():
    """ANR, Crossroads (XRD), Northern Border (NBPL) — SSRS CSV export, the same
    export the page's own LaunchPDF uses (rs:Format switched to CSV)."""
    jobs = [
        ("anr", "ANR Pipeline Company", "OperationallyAvailableCapacityANR", 3005),
        ("crossroads", "Crossroads Pipeline Company LLC", "OperationallyAvailableCapacity", 44),
        ("northern_border", "Northern Border Pipeline Company", "OperationallyAvailableCapacity", 3029),
    ]
    out = {}
    for slug, name, report, nbr in jobs:
        url = (f"https://www.tceconnects.com/infopost/ReportViewer.aspx?/InfoPost/"
               f"{report}&pAssetNbr={nbr}&rs:Format=CSV")
        r = get(url)
        rows = csv_rows(r.content.decode("utf-8-sig", errors="replace")) if r.ok else []
        out[slug] = finish(rows, name, "TC eConnects (SSRS infopost)", url)
    return out

# ------------------------------------------------------------- ET Messenger
def fetch_et():
    """PEPL + Trunkline (TGC). Native CSV export link of the public page.
    Lookback: gasDay param honoured?  Detected at runtime by comparing content."""
    jobs = [
        ("panhandle_eastern", "Panhandle Eastern Pipe Line Company, LP",
         "https://peplmessenger.energytransfer.com", "PEPL"),
        ("trunkline", "Trunkline Gas Company, LLC",
         "https://tgcmessenger.energytransfer.com", "TGC"),
    ]
    out = {}
    today = datetime.now(timezone.utc) - timedelta(hours=5)  # gas day is US-central-ish; label only
    for slug, name, host, asset in jobs:
        rows_all = []
        # prime the app session on that host (the CSV honours session state; the
        # index visit mirrors what a browser does)
        get(f"{host}/ipost/main/index?asset={asset}")
        base = f"{host}/ipost/capacity/operationally-available-by-location?asset={asset}&f=csv&extension=csv&max=ALL"
        cur = get(base)
        cur_text = cur.content.decode("utf-8-sig", errors="replace")
        rows = csv_rows(cur_text)
        rows = finish(rows, name, "Energy Transfer Messenger ipost", base,
                      {"_report": "by-location", "_requested_gas_day": "current"})
        rows_all.extend(rows)
        # lookback attempt
        ignored = False
        for d in range(1, LOOKBACK_DAYS):
            day = (today - timedelta(days=d)).strftime("%m/%d/%Y")
            url = base + "&gasDay=" + day.replace("/", "%2F")
            r = get(url)
            txt = r.content.decode("utf-8-sig", errors="replace")
            if txt == cur_text:
                ignored = True
                print(f"  [{slug}] gasDay param ignored (identical bytes) - keeping current posting only")
                break
            rows = csv_rows(txt)
            rows_all.extend(finish(rows, name, "Energy Transfer Messenger ipost", url,
                                   {"_report": "by-location", "_requested_gas_day": day}))
        # segment report (current)
        seg = f"{host}/ipost/capacity/operationally-available-by-segment?asset={asset}&f=csv&extension=csv&max=ALL"
        r = get(seg)
        if r.ok and b"," in r.content[:200]:
            rows = csv_rows(r.content.decode("utf-8-sig", errors="replace"))
            rows_all.extend(finish(rows, name, "Energy Transfer Messenger ipost", seg,
                                   {"_report": "by-segment", "_requested_gas_day": "current"}))
        out[slug] = rows_all
    return out

# ---------------------------------------------------------------- Texas Gas
def fetch_texas_gas():
    """GasQuest anonymous reporting API: postings list -> per-posting CSV."""
    name = "Texas Gas Transmission, LLC"
    api = "https://reporting.prod.bwpmlp.org/infopost/infopostdetails"
    r = post(api, json={"infoPostId": 1, "tspId": 100000, "pageNumber": 1, "pageSize": 80,
                        "sortBy": "datetimePostingEffective", "sortDescending": True})
    j = r.json()
    postings = j.get("postings", [])
    print(f"  texas_gas postings returned: {len(postings)} / total {j.get('totalPostingsCount')}")
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    keep = []
    for p in postings:
        try:
            eff = datetime.fromisoformat(p["datetimePostingEffective"])
        except Exception:
            continue
        if eff >= cutoff:
            keep.append(p)
    keep.sort(key=lambda p: p["datetimePostingEffective"], reverse=True)
    keep = keep[:60]
    print(f"  texas_gas postings in {LOOKBACK_DAYS}d window: {len(keep)}")
    rows_all = []
    for p in keep:
        csvs = [f for f in p.get("reportFiles", []) if f.get("infoPostDocumentTypeTitle") == "CSV Documents"]
        for f in csvs:
            tid = f["infoPostTrackerID"]
            url = f"https://reporting.prod.bwpmlp.org/infopost/postings?postingsDocumentId={tid}"
            rr = get(url)
            if not rr.ok:
                continue
            raw = rr.content
            # API returns base64-encoded CSV
            try:
                txt = base64.b64decode(raw).decode("utf-8-sig", errors="replace")
            except Exception:
                txt = raw.decode("utf-8-sig", errors="replace")
            rows = csv_rows(txt)
            rows_all.extend(finish(rows, name, "Boardwalk GasQuest (anonymous reporting API)", url,
                                   {"_posting_description": p.get("description", ""),
                                    "_posting_effective": p.get("datetimePostingEffective", ""),
                                    "_posting_file": f.get("fileName", "")}))
    return {"texas_gas": rows_all}

# ---------------------------------------------------------------- MGT Trellis
def fetch_mgt():
    """DTM Trellis PTMS: public jqGrid listing -> per-posting CSV export.
    tspId=10 (MGT), rptId=2 (Operationally Available Capacity)."""
    name = "Midwestern Gas Transmission Company"
    # establish the public session the infopost UI itself uses
    get("https://dtmidstream.trellisenergy.com/ptms/home/infopost/MGT")
    start = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime("%m/%d/%Y")
    end = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%m/%d/%Y")
    lst = (f"https://dtmidstream.trellisenergy.com/ptms/public/infopost/getInfoPostRpts.do?"
           f"tspId=10&rptId=2&cycleId=&startDate={start}&endDate={end}"
           f"&_search=false&rows=200&page=1&sidx=&sord=asc")
    _polite(lst)
    r = session.get(lst, timeout=60, headers={"X-Requested-With": "XMLHttpRequest",
                                              "Accept": "application/json, text/javascript, */*"})
    print(f"  GET {r.status_code} {len(r.content):>9,}B {lst[:120]}")
    j = r.json()
    rows_meta = j.get("rows", j if isinstance(j, list) else [])
    print(f"  mgt postings listed: {len(rows_meta)} (records={j.get('records')})")
    if rows_meta:
        print("  sample keys:", list(rows_meta[0].keys())[:15])
    rows_all = []
    for m in rows_meta[:80]:
        # the CSV export takes the grid row's `id` (observed in the UI's own call:
        # getInfoPostRptExportCsvFile.do?infoPostDataId=72259000000 == row id)
        did = None
        for k in ("id", "infoPostDataId", "infopostDataId", "dataId"):
            if isinstance(m, dict) and m.get(k):
                did = m[k]
                break
        if did is None:
            continue
        url = (f"https://dtmidstream.trellisenergy.com/ptms/public/infopost/"
               f"getInfoPostRptExportCsvFile.do?infoPostDataId={did}&tspId=")
        rr = get(url)
        ct = rr.headers.get("Content-Type", "")
        if not rr.ok or "html" in ct.lower():
            continue
        text = rr.content.decode("utf-8-sig", errors="replace")
        # Trellis CSV is two blocks: a 2-line posting-metadata block, a blank line,
        # then the location table (with a leading unnamed column).
        parts = re.split(r"\r?\n\s*\r?\n", text, maxsplit=1)
        meta = {}
        body = text
        if len(parts) == 2:
            mrows = csv_rows(parts[0])
            if mrows:
                meta = {f"_hdr_{k}": v for k, v in mrows[0].items() if k}
            body = parts[1]
        rows = csv_rows(body)
        for r_ in rows:
            r_.pop("", None)  # leading unnamed column
            r_.update(meta)
        keep_meta = {f"_list_{k}": str(m.get(k)) for k in ("gasDay", "cycleCode", "runDate", "id") if m.get(k) is not None}
        rows_all.extend(finish(rows, name, "DT Midstream Trellis PTMS (public infopost)", url, keep_meta))
    return {"midwestern": rows_all}

# ---------------------------------------------------------------- Vector
def fetch_vector():
    """gasnom.com HTML posting table; dt=<Month D, YYYY> gives prior gas days."""
    name = "Vector Pipeline L.P."
    rows_all = []
    for d in range(0, LOOKBACK_DAYS):
        day = datetime.now(timezone.utc) - timedelta(days=d)
        dt_param = day.strftime("%B %d, %Y").replace(" 0", " ")
        url = "https://www.gasnom.com/ip/vector/cap_operationally_available.cfm"
        r = get(url, params={"dt": dt_param}) if d else get(url)
        real_url = r.url
        soup = BeautifulSoup(r.text, "html.parser")
        txt = soup.get_text(" ", strip=True)
        m = re.search(r"TSP:\s*(\d+)", txt)
        tsp = m.group(1) if m else ""
        m = re.search(r"Date:\s*([0-9/]+)", txt)
        page_date = m.group(1) if m else ""
        tables = soup.find_all("table")
        if not tables:
            continue
        tbl = tables[-1]
        trs = tbl.find_all("tr")
        if not trs:
            continue
        hdr = [c.get_text(" ", strip=True) for c in trs[0].find_all(["td", "th"])]
        day_rows = []
        for tr in trs[1:]:
            cells = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)) for c in tr.find_all("td")]
            if len(cells) < 5:
                continue
            row = dict(zip(hdr, cells))
            row["_page_tsp"] = tsp
            row["_page_date"] = page_date
            day_rows.append(row)
        rows_all.extend(finish(day_rows, name, "gasnom.com EBB (Vector informational postings)", real_url))
    # de-dup identical rows (date pages can overlap postings)
    seen = set()
    uniq = []
    for r in rows_all:
        key = json.dumps(r, sort_keys=True)
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    return {"vector": uniq}

# ---------------------------------------------------------------- NGPL (KM DART)
def fetch_ngpl():
    """Replicates the public page's own EXCEL download button (WebForms postback),
    once for Delivery and once for Receipt locations."""
    name = "Natural Gas Pipeline Company of America LLC"
    url = "https://pipeline2.kindermorgan.com/Capacity/OpAvailPoint.aspx?code=NGPL"
    rows_all = []
    for purpose in ("rbDelivery", "rbReceipt"):
        r1 = get(url)
        soup = BeautifulSoup(r1.text, "html.parser")
        form = soup.find("form")
        data = {}
        for inp in form.find_all("input"):
            n = inp.get("name")
            if not n:
                continue
            t = (inp.get("type") or "").lower()
            if t in ("submit", "image", "button"):
                continue
            if t == "radio":
                continue
            data[n] = inp.get("value") or ""
        for sel in form.find_all("select"):
            n = sel.get("name")
            if not n:
                continue
            opt = sel.find("option", selected=True) or sel.find("option")
            data[n] = opt.get("value") if opt is not None else ""
        data["ctl00$WebSplitter1$tmpl1$ContentPlaceHolder1$location"] = purpose
        data["ctl00$WebSplitter1$tmpl1$ContentPlaceHolder1$HeaderBTN1$DownloadDDL"] = "EXCEL"
        data["ctl00$WebSplitter1$tmpl1$ContentPlaceHolder1$HeaderBTN1$btnDownload.x"] = "5"
        data["ctl00$WebSplitter1$tmpl1$ContentPlaceHolder1$HeaderBTN1$btnDownload.y"] = "5"
        data["ctl00$hdnIsDownload"] = "true"
        r2 = post(url, data=data)
        if "excel" not in (r2.headers.get("Content-Type") or "").lower():
            print(f"  ngpl {purpose}: no excel returned, skipping")
            continue
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(r2.content))
        ws = wb.worksheets[0]
        grid = [[("" if v is None else str(v)) for v in row] for row in ws.iter_rows(values_only=True)]
        # header block: row0 = meta names, row1 = meta values; then blank; then table hdr
        meta = {}
        if len(grid) >= 2:
            meta = {f"_hdr_{k.strip()}": v for k, v in zip(grid[0], grid[1]) if k.strip()}
        # find the data header row (starts with 'Loc')
        hi = None
        for i, row in enumerate(grid):
            if row and row[0].strip() == "Loc":
                hi = i
                break
        if hi is None:
            continue
        hdr = [h.strip() for h in grid[hi]]
        for row in grid[hi + 1:]:
            if not any(x.strip() for x in row):
                continue
            d = dict(zip(hdr, row))
            d.update(meta)
            rows_all.append(d)
        finish(rows_all, name, "Kinder Morgan DART infopost (page's own EXCEL export)", url)
    return {"ngpl": rows_all}

# ---------------------------------------------------------------- main
FETCHERS = {
    "tce": fetch_tce,
    "et": fetch_et,
    "texas_gas": fetch_texas_gas,
    "mgt": fetch_mgt,
    "vector": fetch_vector,
    "ngpl": fetch_ngpl,
}

if __name__ == "__main__":
    which = sys.argv[1:] or list(FETCHERS)
    results = {}
    for w in which:
        print(f"== {w}")
        try:
            results.update(FETCHERS[w]())
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  !! {w} failed: {e}")
    for slug, rows in results.items():
        path = os.path.join(SCRATCH, f"in_gas_capacity_{slug}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"WROTE {slug}: {len(rows)} rows -> {path}")
