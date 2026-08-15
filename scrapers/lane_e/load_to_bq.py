"""Lane E: load fetched EBB capacity JSONL to energy-platfrom.indiana_app and
register every table in indiana_app._registry IN THE SAME RUN.

All source columns kept verbatim as STRING (names sanitized for BQ);
_pulled_at TIMESTAMP; observed dates stay in the data's own columns.
NEVER touches dataset `energy` (read-only elsewhere)."""
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", r"C:\Users\ahend\bq-key.json")
from google.cloud import bigquery

SCRATCH = r"C:\Users\ahend\AppData\Local\Temp\claude\C--Users-ahend-Downloads-Decennial-Summer-Work-Remaking-Orennia-REBUILD-PLANNING\e2c5e15c-d0e5-487b-889b-f478a7c7d3d4\scratchpad\lane_e_out"
PROJECT = "energy-platfrom"
DATASET = "indiana_app"

client = bigquery.Client(project=PROJECT)

SOURCES = {  # slug -> (source string, method string, notes)
    "anr": (
        "TC eConnects infopost (public SSRS), https://www.tceconnects.com/infopost/ReportViewer.aspx?/InfoPost/OperationallyAvailableCapacityANR&pAssetNbr=3005",
        "SSRS URL-access CSV export (&rs:Format=CSV), same renderer as the page's own PDF button; current posting, all locations kept. RE-SCRAPE: python pull_ebb_capacity.py tce && python load_to_bq.py anr",
        "ANR Pipeline (TC Energy). NAESB OA posting: EffGasDay+Cycle+PostingDate in-row. Loc id+name+zone, no state/county -> joinable-identity. Old ebb.anrpl.com EBB is dead (expired TLS cert since migration to TC eConnects).",
    ),
    "crossroads": (
        "TC eConnects infopost (public SSRS), https://www.tceconnects.com/infopost/ReportViewer.aspx?/InfoPost/OperationallyAvailableCapacity&pAssetNbr=44",
        "SSRS URL-access CSV export (&rs:Format=CSV); current posting. RE-SCRAPE: python pull_ebb_capacity.py tce && python load_to_bq.py crossroads",
        "Crossroads Pipeline (XRD, TC Energy since CPG spinoff - NOT NiSource anymore). Schererville IN -> Cygnet OH. Loc id+name -> joinable-identity.",
    ),
    "northern_border": (
        "TC eConnects infopost (public SSRS), https://www.tceconnects.com/infopost/ReportViewer.aspx?/InfoPost/OperationallyAvailableCapacity&pAssetNbr=3029",
        "SSRS URL-access CSV export (&rs:Format=CSV); current posting. RE-SCRAPE: python pull_ebb_capacity.py tce && python load_to_bq.py northern_border",
        "Northern Border Pipeline (TC Energy). Only ~49km clips NW Indiana in held geometry. Loc id+name -> joinable-identity.",
    ),
    "panhandle_eastern": (
        "Energy Transfer Messenger ipost, https://peplmessenger.energytransfer.com/ipost/capacity/operationally-available-by-location?asset=PEPL (+by-segment)",
        "page's native CSV export (&f=csv&extension=csv&max=ALL); gasDay lookback attempted and honoured/refused per _requested_gas_day column. RE-SCRAPE: python pull_ebb_capacity.py et && python load_to_bq.py panhandle_eastern",
        "PEPL. CSV carries State+County+Operator+Miles per location -> strongest identity class short of coordinates (county-plottable). Gas day/cycle are page-state; _requested_gas_day records what was asked.",
    ),
    "trunkline": (
        "Energy Transfer Messenger ipost, https://tgcmessenger.energytransfer.com/ipost/capacity/operationally-available-by-location?asset=TGC (+by-segment)",
        "page's native CSV export (&f=csv&extension=csv&max=ALL); gasDay lookback attempted per _requested_gas_day column. RE-SCRAPE: python pull_ebb_capacity.py et && python load_to_bq.py trunkline",
        "Trunkline Gas Company. CSV carries State+County+Operator -> county-plottable identity.",
    ),
    "texas_gas": (
        "Boardwalk GasQuest anonymous reporting API, POST https://reporting.prod.bwpmlp.org/infopost/infopostdetails {infoPostId:1,tspId:100000} -> GET /infopost/postings?postingsDocumentId=<id>",
        "replicated the public SPA's own calls (no login, no cognito needed - endpoints answer anonymously); CSV files are base64-in-transit; last-7-days postings, all cycles. RE-SCRAPE: python pull_ebb_capacity.py texas_gas && python load_to_bq.py texas_gas",
        "Texas Gas Transmission (Boardwalk). infopost.bwpipelines.com now redirects to gasquest.com. NAESB CSV: LineCode+Segment+Loc+LocName+Zone, Effective Gas Day+Time+Post Date in-row -> joinable-identity.",
    ),
    "midwestern": (
        "DT Midstream Trellis PTMS public infopost, https://dtmidstream.trellisenergy.com/ptms/public/infopost/getInfoPostRpts.do?tspId=10&rptId=2 -> getInfoPostRptExportCsvFile.do?infoPostDataId=<id>",
        "public .do endpoints of the infopost UI (no auth); last-7-days postings, every cycle's CSV. RE-SCRAPE: python pull_ebb_capacity.py mgt && python load_to_bq.py midwestern",
        "Midwestern Gas Transmission - moved off oneok.com to DTM Trellis 2025-11-17 (DTM bought MGT/Guardian/Viking from ONEOK). tspId=10, rptId=2=OA capacity.",
    ),
    "vector": (
        "Vector Pipeline informational postings via vendor EBB https://www.gasnom.com/ip/vector/cap_operationally_available.cfm (iframed by vector-pipeline.com)",
        "HTML table parse, ?dt=<Month D, YYYY> for 7-day lookback; gasnom.com has no robots.txt (404); vector-pipeline.com robots allows all. RE-SCRAPE: python pull_ebb_capacity.py vector && python load_to_bq.py vector",
        "Vector Pipeline L.P. Per-row Eff Gas Day/Time + Cycle + Posting Date/Time. Loc id+name only -> joinable-identity.",
    ),
    "ngpl": (
        "Kinder Morgan DART infopost, https://pipeline2.kindermorgan.com/Capacity/OpAvailPoint.aspx?code=NGPL",
        "replicated the page's own EXCEL download button (WebForms postback, DownloadDDL=EXCEL), once per location purpose (Delivery+Receipt); current posting. robots.txt only disallows specific documents, capacity pages permitted. RE-SCRAPE: python pull_ebb_capacity.py ngpl && python load_to_bq.py ngpl",
        "NGPL (Kinder Morgan). Only a ~7km sliver clips Indiana in held geometry. Header block (gas day, cycle, posting time, meas basis) propagated onto every row as _hdr_* columns. Loc+LocName+Zone+Segment -> joinable-identity.",
    ),
}

def sanitize(name):
    n = re.sub(r"[^0-9a-zA-Z_]", "_", name.strip())
    n = re.sub(r"_+", "_", n).strip("_").lower()
    if not n:
        n = "col"
    if n[0].isdigit():
        n = "c_" + n
    return n

def load_one(slug):
    path = os.path.join(SCRATCH, f"in_gas_capacity_{slug}.jsonl")
    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    if not rows:
        print(f"{slug}: 0 rows, skipping load but registering the outcome")
        register(slug, 0, note_prefix="EMPTY PULL - ")
        return
    # sanitize keys, union schema
    out = []
    keymap = {}
    for r in rows:
        d = {}
        for k, v in r.items():
            sk = keymap.setdefault(k, sanitize(k))
            if v is None:
                v = ""
            d[sk] = str(v)
        out.append(d)
    allkeys = sorted({k for d in out for k in d})
    schema = [bigquery.SchemaField(k, "TIMESTAMP" if k == "_pulled_at" else "STRING") for k in allkeys]
    table_id = f"{PROJECT}.{DATASET}.in_gas_capacity_{slug}"
    job = client.load_table_from_json(
        out, table_id,
        job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE"),
    )
    job.result()
    n = client.get_table(table_id).num_rows
    print(f"LOADED {table_id}: {n} rows ({len(allkeys)} cols)")
    register(slug, n)

def register(slug, n_rows, note_prefix=""):
    source, method, notes = SOURCES[slug]
    row = {
        "table_name": f"in_gas_capacity_{slug}",
        "source": source,
        "method": method,
        "n_rows": int(n_rows),
        "gb_scanned": 0.0,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "notes": note_prefix + notes,
    }
    errors = client.insert_rows_json(f"{PROJECT}.{DATASET}._registry", [row])
    if errors:
        raise RuntimeError(f"registry insert failed: {errors}")
    print(f"REGISTERED in_gas_capacity_{slug} ({n_rows} rows)")

if __name__ == "__main__":
    slugs = sys.argv[1:]
    if not slugs:
        slugs = [re.match(r"in_gas_capacity_(.+)\.jsonl", os.path.basename(p)).group(1)
                 for p in glob.glob(os.path.join(SCRATCH, "in_gas_capacity_*.jsonl"))]
    for s in slugs:
        load_one(s)
