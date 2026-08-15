"""Lane D shared utilities: polite fetching, ArcGIS/Socrata paging, BQ load+register.

Lane D = FRESHNESS REFRESH of already-mapped Indiana SI sources (not new-source discovery,
that is Lane C). Adapted from scrapers/lane_c/lane_c_util.py with the same rules:

- >=1s between requests to the same host (rate limiter)
- User-Agent DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)
- ArcGIS pulls use outFields=* and page to exhaustion, verified against returnCountOnly
- Socrata pulls take all fields, page to exhaustion via $offset
- Every BQ load registers into energy-platfrom.indiana_app._registry in the same run
- Writes go ONLY to energy-platfrom.indiana_app (NEVER energy - that dataset is read-only)
- Refresh staging tables are named in_si_refresh_<slug>
"""
import json
import os
import time
import urllib.parse
import urllib.robotparser

import requests

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", r"C:\Users\ahend\bq-key.json")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"
PROJECT = "energy-platfrom"
DATASET = "indiana_app"
READONLY_DATASET = "energy"  # NEVER write here

_last_hit = {}  # host -> monotonic time of last request
_robots_cache = {}  # host -> RobotFileParser or None


def _throttle(url):
    host = urllib.parse.urlparse(url).netloc
    now = time.monotonic()
    prev = _last_hit.get(host)
    if prev is not None:
        wait = 1.0 - (now - prev)
        if wait > 0:
            time.sleep(wait)
    _last_hit[host] = time.monotonic()


def robots_allowed(url):
    """Check robots.txt for HTML-site scraping / gating discovery."""
    host = urllib.parse.urlparse(url).netloc
    scheme = urllib.parse.urlparse(url).scheme
    if host not in _robots_cache:
        rp = urllib.robotparser.RobotFileParser()
        try:
            _throttle(f"{scheme}://{host}/robots.txt")
            r = requests.get(f"{scheme}://{host}/robots.txt",
                             headers={"User-Agent": UA}, timeout=30)
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
                _robots_cache[host] = rp
            else:
                _robots_cache[host] = None  # no robots -> allowed
        except Exception:
            _robots_cache[host] = None
    rp = _robots_cache[host]
    if rp is None:
        return True
    return rp.can_fetch(UA, url) or rp.can_fetch("*", url)


def get(url, params=None, timeout=60, as_json=True, check_robots=False, method="GET", data=None):
    if check_robots and not robots_allowed(url):
        raise PermissionError(f"robots.txt disallows {url}")
    _throttle(url)
    if method == "POST":
        r = requests.post(url, params=params, data=data, headers={"User-Agent": UA}, timeout=timeout)
    else:
        r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    return r.json() if as_json else r.text


def arcgis_layer_meta(layer_url):
    return get(layer_url, params={"f": "json"})


def arcgis_count(layer_url, where="1=1"):
    j = get(layer_url.rstrip("/") + "/query",
            params={"where": where, "returnCountOnly": "true", "f": "json"})
    return j.get("count")


def arcgis_pull_all(layer_url, where="1=1", want_geometry=False, page_size=None):
    """Page an ArcGIS layer to exhaustion with outFields=*. Returns (rows, publisher_count).
    Uses resultOffset paging; falls back to objectId windowing if unsupported."""
    meta = arcgis_layer_meta(layer_url)
    max_rec = meta.get("maxRecordCount") or 1000
    if page_size is None:
        page_size = min(max_rec, 2000)
    total = arcgis_count(layer_url, where)
    rows = []
    offset = 0
    while True:
        params = {
            "where": where, "outFields": "*", "f": "json",
            "resultOffset": offset, "resultRecordCount": page_size,
            "returnGeometry": "true" if want_geometry else "false",
        }
        if want_geometry:
            params["outSR"] = "4326"
        # Retry a handful of times on transient ArcGIS server errors (e.g. 503 "Wait
        # timeout for the request exceeded" under server load) before giving up. Not a
        # gating/permission issue -- same request, same params, just resent after a
        # backoff. Non-transient errors (bad field, bad where clause, etc.) still raise
        # immediately.
        attempt = 0
        while True:
            j = get(layer_url.rstrip("/") + "/query", params=params, timeout=180)
            if "error" not in j:
                break
            err = j["error"]
            transient = (err.get("code") in (503, 500, 429) or
                         "timeout" in str(err.get("message", "")).lower())
            attempt += 1
            if not transient or attempt >= 5:
                raise RuntimeError(f"ArcGIS error at offset {offset} (attempt {attempt}): {err}")
            wait = 2 ** attempt  # 4, 8, 16, 32s
            print(f"  transient ArcGIS error at offset {offset} (attempt {attempt}/5): "
                  f"{err} -- retrying in {wait}s")
            time.sleep(wait)
        feats = j.get("features", [])
        for f in feats:
            row = dict(f.get("attributes", {}))
            if want_geometry and f.get("geometry") is not None:
                row["_geometry_json"] = json.dumps(f["geometry"])
            rows.append(row)
        if not feats:
            break
        offset += len(feats)
        if not j.get("exceededTransferLimit", False) and len(feats) < page_size:
            break
        if total is not None and offset >= total and not j.get("exceededTransferLimit", False):
            break
    if total is not None and len(rows) != total:
        if abs(len(rows) - total) > max(20, total * 0.01):
            raise RuntimeError(f"PAGINATION ALARM {layer_url}: pulled {len(rows)} vs count {total}")
    return rows, total


def socrata_pull_all(domain, dataset_id, page_size=10000):
    """Page a Socrata dataset to exhaustion. Returns list of dict rows (all fields)."""
    url = f"https://{domain}/resource/{dataset_id}.json"
    rows = []
    offset = 0
    while True:
        j = get(url, params={"$limit": page_size, "$offset": offset, "$order": ":id"})
        rows.extend(j)
        if len(j) < page_size:
            break
        offset += page_size
    return rows


def epoch_ms_to_date(v):
    """ArcGIS dates are epoch ms."""
    if v in (None, ""):
        return None
    try:
        return time.strftime("%Y-%m-%d", time.gmtime(int(v) / 1000.0))
    except (ValueError, OSError, OverflowError):
        return None


def load_to_bq(table_name, rows, source, method, notes, pulled_at=None):
    """Load list-of-dicts to energy-platfrom.indiana_app.<table_name> (replace) and
    register in _registry IN THE SAME RUN. All values stringified except None (schemaless
    sources vary types row to row; keep verbatim strings, consumers cast).
    Lane D tables must be named in_si_refresh_<slug> (freshness re-pulls, distinct from
    Lane C's in_si_<slug> new-signal staging tables)."""
    import datetime
    from google.cloud import bigquery

    assert table_name.startswith("in_si_refresh_"), "lane D tables must be in_si_refresh_*"
    pulled_at = pulled_at or datetime.datetime.now(datetime.timezone.utc).isoformat()

    keys = []
    seen = set()
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k)
                keys.append(k)

    def clean(k):
        s = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in str(k))
        if not s or s[0].isdigit():
            s = "f_" + s
        return s[:128]

    colmap = {}
    used = set()
    for k in keys:
        c = clean(k)
        base, i = c, 2
        while c.lower() in used:
            c = f"{base}_{i}"
            i += 1
        used.add(c.lower())
        colmap[k] = c

    client = bigquery.Client(project=PROJECT)
    table_id = f"{PROJECT}.{DATASET}.{table_name}"
    ndjson_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               f"_stage_{table_name}.ndjson")
    with open(ndjson_path, "w", encoding="utf-8") as fh:
        for r in rows:
            out = {}
            for k, v in r.items():
                if v is None:
                    continue
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, ensure_ascii=False)
                out[colmap[k]] = str(v)
            out["_pulled_at"] = pulled_at
            fh.write(json.dumps(out, ensure_ascii=False) + "\n")

    schema = [bigquery.SchemaField(colmap[k], "STRING") for k in keys]
    schema.append(bigquery.SchemaField("_pulled_at", "STRING"))
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    with open(ndjson_path, "rb") as fh:
        job = client.load_table_from_file(fh, table_id, job_config=job_config)
    job.result()
    n = client.get_table(table_id).num_rows
    os.remove(ndjson_path)

    reg_row = {
        "table_name": table_name,
        "source": source,
        "method": method,
        "n_rows": int(n),
        "gb_scanned": 0.0,
        "built_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "notes": notes,
    }
    errors = client.insert_rows_json(f"{PROJECT}.{DATASET}._registry", [reg_row])
    if errors:
        raise RuntimeError(f"registry insert failed: {errors}")
    print(f"LOADED {table_id}: {n} rows; REGISTERED.")
    return n


def bq_client():
    from google.cloud import bigquery
    return bigquery.Client(project=PROJECT)


def ensure_dataset_and_registry():
    """Make sure indiana_app dataset and _registry table exist (idempotent)."""
    from google.cloud import bigquery
    client = bq_client()
    ds_id = f"{PROJECT}.{DATASET}"
    try:
        client.get_dataset(ds_id)
    except Exception:
        ds = bigquery.Dataset(ds_id)
        ds.location = "US"
        client.create_dataset(ds)
        print(f"Created dataset {ds_id}")

    reg_id = f"{ds_id}._registry"
    try:
        client.get_table(reg_id)
    except Exception:
        schema = [
            bigquery.SchemaField("table_name", "STRING"),
            bigquery.SchemaField("source", "STRING"),
            bigquery.SchemaField("method", "STRING"),
            bigquery.SchemaField("n_rows", "INTEGER"),
            bigquery.SchemaField("gb_scanned", "FLOAT64"),
            bigquery.SchemaField("built_at", "TIMESTAMP"),
            bigquery.SchemaField("notes", "STRING"),
        ]
        t = bigquery.Table(reg_id, schema=schema)
        client.create_table(t)
        print(f"Created registry table {reg_id}")
