"""Shared BigQuery + HTTP helpers for Lane B (Indiana community-sentiment/regulatory pulls).

Hard rules encoded here:
- READ-ONLY on dataset `energy`. All writes go to `energy-platfrom.indiana_app`.
- Every table load registers a row in `energy-platfrom.indiana_app._registry` in the same run.
- HTTP: >=1s between requests per host, fixed research User-Agent, robots.txt checked first.
- Observed event dates are stored in their own columns; pull time goes to `_pulled_at`.
"""
import os, sys, time, json, datetime
from urllib.parse import urlparse

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", r"C:\Users\ahend\bq-key.json")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

PROJECT = "energy-platfrom"  # intentional spelling
DATASET = "indiana_app"
UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"

_client = None

def client():
    global _client
    if _client is None:
        _client = bigquery.Client(project=PROJECT)
    return _client

def now_utc_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def query(sql, timeout=180):
    """Run a query, return (rows_as_dicts, gb_scanned)."""
    job = client().query(sql)
    rows = [dict(r) for r in job.result(timeout=timeout)]
    gb = (job.total_bytes_processed or 0) / 1e9
    return rows, gb

def ensure_dataset():
    c = client()
    ref = f"{PROJECT}.{DATASET}"
    try:
        return c.get_dataset(ref).location
    except Exception:
        # match the location of the existing `energy` dataset
        loc = c.get_dataset(f"{PROJECT}.energy").location
        ds = bigquery.Dataset(ref)
        ds.location = loc
        c.create_dataset(ds)
        print(f"[bq] created dataset {ref} in {loc}")
        return loc

REGISTRY_SCHEMA = [
    bigquery.SchemaField("table_name", "STRING"),
    bigquery.SchemaField("source", "STRING"),
    bigquery.SchemaField("method", "STRING"),
    bigquery.SchemaField("n_rows", "INT64"),
    bigquery.SchemaField("gb_scanned", "FLOAT64"),
    bigquery.SchemaField("built_at", "TIMESTAMP"),
    bigquery.SchemaField("notes", "STRING"),
]

def load_rows(table_name, rows, schema, write_disposition="WRITE_TRUNCATE"):
    """Load list-of-dicts into indiana_app.<table_name> with an explicit schema."""
    ensure_dataset()
    c = client()
    table_id = f"{PROJECT}.{DATASET}.{table_name}"
    job_config = bigquery.LoadJobConfig(schema=schema, write_disposition=write_disposition)
    job = c.load_table_from_json(rows, table_id, job_config=job_config)
    job.result(timeout=300)
    n = c.get_table(table_id).num_rows
    print(f"[bq] loaded {len(rows)} rows -> {table_id} (table now {n} rows)")
    return int(n)

def register(table_name, source, method, n_rows, gb_scanned=0.0, notes=""):
    """Append a row to indiana_app._registry. MUST be called in the same run as the load."""
    ensure_dataset()
    c = client()
    table_id = f"{PROJECT}.{DATASET}._registry"
    row = {
        "table_name": table_name,
        "source": source,
        "method": method,
        "n_rows": int(n_rows),
        "gb_scanned": float(round(gb_scanned, 6)),
        "built_at": now_utc_iso(),
        "notes": notes[:1000],
    }
    job_config = bigquery.LoadJobConfig(schema=REGISTRY_SCHEMA, write_disposition="WRITE_APPEND")
    job = c.load_table_from_json([row], table_id, job_config=job_config)
    job.result(timeout=120)
    print(f"[bq] registered {table_name}: n_rows={n_rows} notes={notes[:120]}")

# ---------------- HTTP side ----------------
import requests
import urllib.robotparser

_last_hit = {}
_robots_cache = {}

def _session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    return s

SESSION = _session()

def robots_for(url):
    """Fetch+parse robots.txt for the url's host. Returns (parser_or_None, raw_text)."""
    host = urlparse(url).scheme + "://" + urlparse(url).netloc
    if host in _robots_cache:
        return _robots_cache[host]
    raw = ""
    rp = urllib.robotparser.RobotFileParser()
    try:
        r = polite_get(host + "/robots.txt", skip_robots=True)
        raw = r.text if r.status_code == 200 else f"(HTTP {r.status_code})"
        if r.status_code == 200:
            rp.parse(r.text.splitlines())
        elif 400 <= r.status_code < 500:
            rp.parse([])  # RFC 9309 2.3.1.3: 4xx (incl. 401/403) = no robots file = unrestricted
        else:
            rp = None  # 5xx/unreachable = assume complete disallow (RFC 9309 2.3.1.4)
    except Exception as e:
        raw = f"(robots fetch failed: {e})"
        rp = None
    _robots_cache[host] = (rp, raw)
    return rp, raw

def allowed(url):
    rp, raw = robots_for(url)
    if rp is None:
        return False, raw  # 401/403 on robots => assume disallowed, record
    ok = rp.can_fetch(UA, url) and rp.can_fetch("*", url) is not None and rp.can_fetch(UA, url)
    return ok, raw

def polite_get(url, min_interval=1.1, timeout=45, skip_robots=False, **kw):
    """GET with per-host >=1s spacing and research UA. Does NOT check robots (use allowed())."""
    host = urlparse(url).netloc
    wait = min_interval - (time.time() - _last_hit.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    r = SESSION.get(url, timeout=timeout, **kw)
    _last_hit[host] = time.time()
    return r

def save_scratch(name, content):
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_scratch")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    mode = "wb" if isinstance(content, bytes) else "w"
    with open(p, mode, encoding=None if isinstance(content, bytes) else "utf-8", errors=None if isinstance(content, bytes) else "replace") as f:
        f.write(content)
    return p
