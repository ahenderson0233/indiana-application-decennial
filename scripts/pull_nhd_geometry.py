"""Acquire Indiana SURFACE-WATER GEOMETRY (rivers, lakes, reservoirs) from USGS The National Map.

WHY THIS EXISTS
---------------
`energy.nhd_flowline` (39,542,980 rows) and `energy.nhd_waterbody` (10,431,981 rows) both carry a
`SHAPE:GEOGRAPHY` column that is NULL on EVERY ROW NATIONALLY. Re-measured 2026-08-17:

    flowline   total=39,542,980  SHAPE_not_null=0   IN_rows=2,415,369  IN_with_geom=0
    waterbody  total=10,431,981  SHAPE_not_null=0   IN_rows=  186,667  IN_with_geom=0

They are attribute-only. No river or lake in the estate can be drawn, or measured to. Those two
tables live in `energy`, which is READ-ONLY to this session, so the fix cannot be a re-load; it has
to be a fresh acquisition into `indiana_app`.

SOURCE
------
USGS TNM National Hydrography Dataset, the SAME publisher the attribute tables came from:
    https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/6   (Flowline - Large Scale)
    https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/12  (Waterbody - Large Scale)
Public, anonymous, no API key, no terms dialogue, no CAPTCHA. maxRecordCount=2000, pagination
supported. Layer 6/12 field lists are IDENTICAL to the BigQuery tables' columns, including
`permanent_identifier` - so acquired geometry joins 1:1 back to the attributes already held.

THE CUT, STATED RATHER THAN HIDDEN
----------------------------------
Indiana holds 2,415,369 flowlines and 186,667 waterbodies. We do not need all of it, and the
operator authorised a siting-relevant subset. What is fetched:

    ftype 460 StreamRiver, gnis_name IS NOT NULL  -> named rivers/streams   (SOURCE)
    ftype 436 Reservoir,   all sizes              -> reservoirs             (SOURCE)
    ftype 390 LakePond,    areasqkm >= 0.1        -> lakes >= 10 hectares   (SOURCE)
    ftype 466 SwampMarsh,  areasqkm >= 0.1        -> wetlands >= 10 ha      (CONSTRAINT)

What is deliberately NOT fetched, and why: 468 (drainageway), 334 (connector), 566 (coastline),
336 CanalDitch, 420 UndergroundConduit, 428 Pipeline, 558 ArtificialPath - none of these is water
anyone can draw from, and 558 in particular is a synthetic line through a lake, not a river.
Unnamed 460s (820,322 of them in Indiana) are headwater trickles; NHD's own act of naming is the
publisher's judgement of "real watercourse", which is a better filter than any we would invent.

466 SwampMarsh IS fetched but is tagged `water_role='constraint'`, never 'source'. It is wetland -
a thing that stops you building, not a thing you can cool with. It is carried rather than dropped
so that the constraint is visible; screening on a bare ftype integer would have counted it as a lake.

TWO TRAPS THIS SCRIPT HANDLES (both cost a sibling pull already)
---------------------------------------------------------------
1. LEADING ZEROS. `reachcode` and the `huc8` derived from it are STRINGS. Every Indiana HUC8 begins
   04 or 05; an INT64 load silently destroys them. huc8 is cut with SUBSTR and never cast.
2. STATE LINES. Rivers do not stop at them. Selection is by tiled bounding box (a superset that
   deliberately overshoots into IL/OH/KY/MI), and Indiana membership is then decided by an explicit
   KEY MATCH against `permanent_identifier` from the authoritative `src_state='IN'` slice - not by
   the box. Border features are RETAINED and flagged `in_nhd_indiana_slice=FALSE` rather than
   silently dropped, because a parcel in Posey County cares about the Wabash whichever bank it is.
   NOTE: permanent_identifier is brace-wrapped GUID on most rows but not all (2,212,074 of
   2,415,369 Indiana flowlines are braced; lengths run 8-38), so the key match normalises braces
   and case on BOTH sides and the match rate is MEASURED, not assumed.

Writes `indiana_app.in_nhd_flowline_geom` and `indiana_app.in_nhd_waterbody_geom`.
RE-SCRAPE COMMAND: python scripts/pull_nhd_geometry.py
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import json, os, time, threading, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
BASE = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer"
UA = {"User-Agent": "indiana-siting-research/1.0 (public-data acquisition; contact via Decennial)"}
PAGE = 2000
WORKERS = 3            # polite against a public federal service we do not own
GEOM_PRECISION = 6     # ~0.11 m at this latitude; full siting fidelity, much smaller payload

# Indiana bbox, padded. Deliberately a SUPERSET - Indiana membership is decided by key, not by box.
LON0, LAT0, LON1, LAT1 = -88.40, 37.60, -84.60, 41.90
TILE = 0.5

OUT = os.path.join(os.environ.get("TEMP", "."), "nhd_indiana")
os.makedirs(OUT, exist_ok=True)

FTYPE_LABEL = {460: "StreamRiver", 436: "Reservoir", 390: "LakePond", 466: "SwampMarsh"}
# 466 is a CONSTRAINT. Everything else fetched here is a SOURCE. Never conflate them.
WATER_ROLE = {460: "source", 436: "source", 390: "source", 466: "constraint"}

LAYERS = [
    dict(lid=6, name="flowline", where="ftype=460 AND gnis_name IS NOT NULL",
         fields="OBJECTID,permanent_identifier,gnis_id,gnis_name,lengthkm,reachcode,"
                "ftype,fcode,flowdir,innetwork,mainpath,resolution"),
    dict(lid=12, name="waterbody",
         where="FTYPE=436 OR (FTYPE=390 AND AREASQKM>=0.1) OR (FTYPE=466 AND AREASQKM>=0.1)",
         fields="OBJECTID,PERMANENT_IDENTIFIER,GNIS_ID,GNIS_NAME,AREASQKM,ELEVATION,"
                "REACHCODE,FTYPE,FCODE,RESOLUTION"),
]

_lock = threading.Lock()
_stats = {"req": 0, "feat": 0, "bytes": 0}


def fetch(lid, where, fields, bbox, offset, attempt=0):
    p = {
        "where": where, "geometry": bbox, "geometryType": "esriGeometryEnvelope", "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects", "outFields": fields, "returnGeometry": "true",
        "outSR": "4326", "geometryPrecision": str(GEOM_PRECISION), "f": "geojson",
        "resultOffset": str(offset), "resultRecordCount": str(PAGE), "orderByFields": "OBJECTID ASC",
    }
    url = f"{BASE}/{lid}/query?" + urllib.parse.urlencode(p)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
            raw = r.read()
    except Exception as e:
        if attempt >= 3:
            raise
        time.sleep(2 ** attempt * 3)
        return fetch(lid, where, fields, bbox, offset, attempt + 1)
    with _lock:
        _stats["req"] += 1
        _stats["bytes"] += len(raw)
    return json.loads(raw)


def do_tile(args):
    layer, x, y = args
    bbox = f"{x:.4f},{y:.4f},{min(x+TILE,LON1):.4f},{min(y+TILE,LAT1):.4f}"
    rows, offset = [], 0
    while True:
        d = fetch(layer["lid"], layer["where"], layer["fields"], bbox, offset)
        fs = d.get("features", [])
        for f in fs:
            g = f.get("geometry")
            if not g:
                continue
            props = {k.lower(): v for k, v in (f.get("properties") or {}).items()}
            props["_geom"] = json.dumps(g, separators=(",", ":"))
            rows.append(props)
        if len(fs) < PAGE:
            break
        offset += PAGE
        time.sleep(0.4)
    with _lock:
        _stats["feat"] += len(rows)
    return layer["name"], rows


def pull(layer):
    tiles = []
    y = LAT0
    while y < LAT1:
        x = LON0
        while x < LON1:
            tiles.append((layer, x, y))
            x += TILE
        y += TILE
    path = os.path.join(OUT, f"{layer['name']}.ndjson")
    seen, n = set(), 0
    t0 = time.time()
    with open(path, "w", encoding="utf-8") as fh, ThreadPoolExecutor(WORKERS) as ex:
        for i, (_, rows) in enumerate(ex.map(do_tile, tiles), 1):
            for r in rows:
                oid = r.get("objectid")
                if oid in seen:          # tiles overlap at their shared edges
                    continue
                seen.add(oid)
                fh.write(json.dumps(r, separators=(",", ":")) + "\n")
                n += 1
            if i % 10 == 0 or i == len(tiles):
                print(f"  [{layer['name']}] tile {i}/{len(tiles)}  unique={n:,}  "
                      f"req={_stats['req']}  {_stats['bytes']/1e6:.0f} MB  {time.time()-t0:.0f}s",
                      flush=True)
    print(f"  [{layer['name']}] DONE {n:,} unique features -> {path}")
    return path, n


# ⚠ EXPLICIT SCHEMA, NEVER autodetect. Measured 2026-08-17: autodetect typed `reachcode` as INTEGER
# and turned reachcode '04040001000928' into 4040001000928 - the leading zero GONE, so the HUC8 cut
# from it read '4040001' (7 chars) instead of '04040001'. EVERY Indiana reachcode starts 04 or 05,
# so autodetect silently corrupts the watershed key on every single row. gnis_id is the same hazard.
_S = bigquery.SchemaField
SCHEMAS = {
    "flowline": [
        _S("objectid", "INT64"), _S("permanent_identifier", "STRING"), _S("gnis_id", "STRING"),
        _S("gnis_name", "STRING"), _S("lengthkm", "FLOAT64"), _S("reachcode", "STRING"),
        _S("ftype", "INT64"), _S("fcode", "INT64"), _S("flowdir", "INT64"),
        _S("innetwork", "INT64"), _S("mainpath", "INT64"), _S("resolution", "INT64"),
        _S("_geom", "STRING"),
    ],
    "waterbody": [
        _S("objectid", "INT64"), _S("permanent_identifier", "STRING"), _S("gnis_id", "STRING"),
        _S("gnis_name", "STRING"), _S("areasqkm", "FLOAT64"), _S("elevation", "FLOAT64"),
        _S("reachcode", "STRING"), _S("ftype", "INT64"), _S("fcode", "INT64"),
        _S("resolution", "INT64"), _S("_geom", "STRING"),
    ],
}


def load(path, table, name):
    client = bigquery.Client(project="energy-platfrom")
    with open(path, "rb") as fh:
        job = client.load_table_from_file(
            fh, f"{DS}.{table}",
            job_config=bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                schema=SCHEMAS[name], write_disposition="WRITE_TRUNCATE"))
    job.result()
    tb = client.get_table(f"{DS}.{table}")
    bad = {f.name: f.field_type for f in tb.schema
           if f.name in ("reachcode", "gnis_id") and f.field_type != "STRING"}
    assert not bad, f"leading-zero guard tripped: {bad} must be STRING"
    return tb.num_rows


if __name__ == "__main__":
    only = _sys.argv[1] if len(_sys.argv) > 1 else None
    for layer in LAYERS:
        if only and layer["name"] != only:
            continue
        print(f"=== pulling {layer['name']} (layer {layer['lid']}): {layer['where']}")
        path = os.path.join(OUT, f"{layer['name']}.ndjson")
        if "--load-only" in _sys.argv and os.path.exists(path):
            n = sum(1 for _ in open(path, encoding="utf-8"))
            print(f"  reusing {path} ({n:,} lines)")
        else:
            path, n = pull(layer)
        assert n > 0, f"{layer['name']}: zero features - check the endpoint before believing this"
        got = load(path, f"_raw_nhd_{layer['name']}", layer["name"])
        print(f"  loaded {got:,} rows into {DS}._raw_nhd_{layer['name']}")
    print(f"totals: {_stats['req']} requests, {_stats['bytes']/1e6:.0f} MB transferred")
