"""PJM's own GIS queue-point layer -> indiana_app.in_pjm_gis_queues.

https://gis.pjm.com/arcgis/rest/services/Renewables/Queue/MapServer/0 — public (Query cap),
6,923 point features: QUEUE_ID (queue position), FAC_ID (facility code: ~5-char name prefix +
2-char state + kV, e.g. BERGNJ230), VOLTAGE, geometry. Publisher coordinates for queue
facilities — the top rung of the bus-location ladder. outFields=*, outSR=4326 (publisher
reprojection), ordered paging by QUEUE_KEY; maxRecordCount 10,000 covers all rows in one page
but paging loop is kept + truncation alarm.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ahend\bq-key.json"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"
LAYER = "https://gis.pjm.com/arcgis/rest/services/Renewables/Queue/MapServer/0"
_last = [0.0]


def get(url):
    dt = time.time() - _last[0]
    if dt < 1.1:
        time.sleep(1.1 - dt)
    _last[0] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read(60_000_000).decode("utf-8", "replace"))


declared = get(f"{LAYER}/query?where=1%3D1&returnCountOnly=true&f=json")["count"]
print(f"declared count: {declared:,}")

rows, offset = [], 0
while True:
    q = urllib.parse.urlencode({
        "where": "1=1", "outFields": "*", "outSR": "4326", "f": "json",
        "orderByFields": "QUEUE_KEY", "resultOffset": offset, "resultRecordCount": 2000})
    js = get(f"{LAYER}/query?{q}")
    feats = js.get("features", [])
    if not feats:
        break
    for f_ in feats:
        r = dict(f_.get("attributes") or {})
        g = f_.get("geometry") or {}
        r["lon"], r["lat"] = g.get("x"), g.get("y")
        rows.append(r)
    print(f"  +{len(feats)} (total {len(rows):,})")
    offset += len(feats)
    if not js.get("exceededTransferLimit") and len(feats) < 2000:
        break

print(f"pulled {len(rows):,} / declared {declared:,}")
if len(rows) != declared:
    raise RuntimeError(f"TRUNCATION ALARM: pulled {len(rows)} != declared {declared}")
dk = len({r.get("QUEUE_KEY") for r in rows})
print(f"distinct QUEUE_KEY: {dk:,}")

stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
for r in rows:
    r["_pulled_at"] = stamp
    r["_source_url"] = LAYER
from google.cloud import bigquery  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from register_helper import register  # noqa: E402

c = bigquery.Client(project="energy-platfrom")
DEST = "energy-platfrom.indiana_app.in_pjm_gis_queues"
c.load_table_from_json(rows, DEST, job_config=bigquery.LoadJobConfig(
    write_disposition="WRITE_TRUNCATE", autodetect=True)).result()
n = list(c.query(f"SELECT COUNT(*) n FROM `{DEST}`").result())[0].n
print(f"loaded {n:,} -> {DEST}")
if n != len(rows):
    raise RuntimeError(f"ROW CONSERVATION FAILED {len(rows)} -> {n}")
n_in = list(c.query(
    f"SELECT COUNT(*) n FROM `{DEST}` WHERE REGEXP_CONTAINS(FAC_ID, r'IN[0-9]+$')").result())[0].n
register(
    "in_pjm_gis_queues", f"PJM public GIS queue-point layer {LAYER} (folder Renewables, "
    "anonymous Query capability; discovered behind pjm.com map pages)",
    "ArcGIS REST query, outFields=*, outSR=4326 (publisher reprojection), ordered paging by "
    "QUEUE_KEY, truncation alarm vs returnCountOnly; all rows in-session",
    int(n), 0.0,
    f"{n:,} queue POINTS with PJM's own coordinates. FAC_ID encodes facility name-prefix + "
    f"state + kV (e.g. BERGNJ230); {n_in:,} rows have FAC_ID ending IN+kV (Indiana facilities). "
    f"QUEUE_ID gives the queue position. PLOTTABILITY: DIRECTLY PLOTTABLE (publisher points, "
    f"EPSG:4326). This is the top rung for in_pjm_bus_locations_candidate: PJM-published "
    f"coordinates keyed by facility code. VOLTAGE column is the facility kV.")
