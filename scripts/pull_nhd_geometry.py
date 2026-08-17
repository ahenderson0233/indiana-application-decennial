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

import json, os, time, threading, urllib.error, urllib.parse, urllib.request
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
    # ⭐ NHDArea, ftype 460. THE BIG RIVERS, AND WITHOUT THIS THEY ARE ALMOST ENTIRELY ABSENT.
    # NHD maps a river as a LINE only while it is narrow. Once it is wide enough to have two banks
    # worth drawing, the water becomes a POLYGON in NHDArea and the line through it degrades to
    # ftype 558 ArtificialPath. Measured on the Indiana slice:
    #     Wabash River       46 ftype-460 line segments vs 1,947 ArtificialPath
    #     White River        99 vs 1,921 · Tippecanoe 14 vs 1,274 · Mississinewa 11 vs 855
    # So a "named ftype 460" pull - exactly what was specified - captures about 2% of the Wabash.
    # Any "distance to the nearest river" built on lines alone is wrong for every major Indiana
    # river, and wrong in the dangerous direction: it reports the big reliable water as far away.
    # These polygons are the actual wetted surface and are the right thing to measure to.
    dict(lid=9, name="area", where="FTYPE=460",
         fields="OBJECTID,PERMANENT_IDENTIFIER,GNIS_ID,GNIS_NAME,AREASQKM,ELEVATION,"
                "FTYPE,FCODE,RESOLUTION"),
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
    # NHDArea has NO reachcode field, so there is no huc8 to cut from it.
    "area": [
        _S("objectid", "INT64"), _S("permanent_identifier", "STRING"), _S("gnis_id", "STRING"),
        _S("gnis_name", "STRING"), _S("areasqkm", "FLOAT64"), _S("elevation", "FLOAT64"),
        _S("ftype", "INT64"), _S("fcode", "INT64"), _S("resolution", "INT64"), _S("_geom", "STRING"),
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


# -------------------------------------------------------------------------------------------------
# BACKFILL BY EXPLICIT KEY. The tiled bbox is a fetch mechanism, not a definition of Indiana, and it
# proved incomplete: NHD's Indiana slice spills past the state line (a reservoir at latitude 41.906
# sits above the 41.90 box edge), so a first pass on the box alone captured 148,317 of 152,165 named
# flowlines and 4,900 of 5,915 waterbodies. Widening the box would be guessing at how far to widen.
# Instead ask BigQuery which permanent_identifiers of our cut are still missing and request exactly
# those by key - which is the operator's own rule: select by an explicit key list where you can.
# This makes the capture PROVABLY complete rather than probably complete.
# -------------------------------------------------------------------------------------------------
BACKFILL_SQL = {
    "flowline": """
      SELECT permanent_identifier FROM `energy-platfrom.energy.nhd_flowline`
      WHERE UPPER(IFNULL(src_state,'')) = 'IN' AND ftype = 460 AND gnis_name IS NOT NULL""",
    "waterbody": """
      SELECT permanent_identifier FROM `energy-platfrom.energy.nhd_waterbody`
      WHERE UPPER(IFNULL(src_state,'')) = 'IN'
        AND (ftype = 436 OR (ftype = 390 AND areasqkm >= 0.1) OR (ftype = 466 AND areasqkm >= 0.1))""",
}
KEYFIELD = {"flowline": "permanent_identifier", "waterbody": "PERMANENT_IDENTIFIER"}
# Flowline permanent_identifiers are 38-char brace-wrapped GUIDs, so 40 of them make a ~1.6 KB
# IN(...) clause. 100 of them (~4.1 KB) is past what the service accepts and comes back HTTP 500.
BATCH = 40


def post(lid, body, retry_5xx=True):
    """POST a query. retry_5xx=False when a 500 is EXPECTED and means 'that request was too big'.

    Retrying a deterministic 500 is pure latency: the service refuses an over-long IN(...) clause
    every time, so the three backoff sleeps burn 21 seconds before the caller can do the one thing
    that actually helps, which is send a shorter list.
    """
    for attempt in range(4):
        try:
            req = urllib.request.Request(f"{BASE}/{lid}/query",
                                         data=urllib.parse.urlencode(body).encode(), headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code < 500 or not retry_5xx or attempt == 3:
                raise
            time.sleep(2 ** attempt * 3)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt * 3)


def fetch_by_keys(lid, keyfield, fields, keys):
    """Ask for an explicit key list, halving the batch whenever the service refuses it.

    The service returns HTTP 500 - not a structured error - once the IN(...) clause gets too long.
    The exact ceiling is undocumented and there is no point guessing a magic constant that will rot,
    so back off by bisection until it answers, and never silently drop a key.
    """
    ids = "','".join(keys)
    try:
        d = post(lid, {"where": f"{keyfield} IN ('{ids}')", "outFields": fields,
                       "returnGeometry": "true", "outSR": "4326",
                       "geometryPrecision": str(GEOM_PRECISION), "f": "geojson"},
                 retry_5xx=(len(keys) == 1))
        return d.get("features", [])
    except urllib.error.HTTPError:
        if len(keys) == 1:
            raise
        mid = len(keys) // 2
        time.sleep(0.5)
        return (fetch_by_keys(lid, keyfield, fields, keys[:mid])
                + fetch_by_keys(lid, keyfield, fields, keys[mid:]))


def backfill(layer):
    client = bigquery.Client(project="energy-platfrom")
    name = layer["name"]
    path = os.path.join(OUT, f"{name}.ndjson")
    have = set()
    for line in open(path, encoding="utf-8"):
        pid = json.loads(line).get("permanent_identifier")
        if pid:
            have.add(pid.strip("{}").lower())
    want = {r.permanent_identifier for r in client.query(BACKFILL_SQL[name])}
    missing = sorted(p for p in want if p.strip("{}").lower() not in have)
    print(f"  [{name}] Indiana slice wants {len(want):,}; NDJSON already holds "
          f"{len(want) - len(missing):,}; fetching {len(missing):,} by key")
    if not missing:
        return 0
    got, t0 = 0, time.time()
    with open(path, "a", encoding="utf-8") as fh:
        for i in range(0, len(missing), BATCH):
            chunk = missing[i:i + BATCH]
            for f in fetch_by_keys(layer["lid"], KEYFIELD[name], layer["fields"], chunk):
                g = f.get("geometry")
                if not g:
                    continue
                props = {k.lower(): v for k, v in (f.get("properties") or {}).items()}
                props["_geom"] = json.dumps(g, separators=(",", ":"))
                fh.write(json.dumps(props, separators=(",", ":")) + "\n")
                got += 1
            if (i // BATCH) % 10 == 0:
                print(f"    ...{i + len(chunk):,}/{len(missing):,} requested, {got:,} returned "
                      f"({time.time() - t0:.0f}s)", flush=True)
            time.sleep(0.4)
    print(f"  [{name}] backfilled {got:,} of {len(missing):,} requested")
    return got


# -------------------------------------------------------------------------------------------------
# APPEND-MISSING. Closes the gap in an ALREADY-BUILT table without rebuilding it.
#
# `backfill()` above measures what is missing against the local NDJSON, which is only correct while
# the NDJSON and the built table are in step. They are not always: a session can stop between the
# fetch and the build, and then the NDJSON is ahead of - or behind - what BigQuery actually holds.
# Measured 2026-08-17 on the live tables, which is what prompted this function:
#
#     in_nhd_flowline_geom   148,317 of 152,165 of the Indiana cut =  97.47%   3,848 with no geometry
#     in_nhd_waterbody_geom    4,900 of   5,915 of the Indiana cut =  82.84%   1,015 with no geometry
#
# Those are exactly the bbox-sweep-only figures quoted at the head of build_nhd_geometry.py, so the
# by-key pass had not landed at all. The finished tables are the authority here, not the NDJSON, so
# this asks BigQuery which keys the TABLE is missing and requests precisely those.
#
# ⛔ It APPENDS. `CREATE OR REPLACE` would discard 160,128 rows that are already verified - zero null
#    geography, no planet-scale polygon, every feature touching Indiana - and re-earning that costs a
#    full multi-hour sweep against a public federal service we do not own.
# -------------------------------------------------------------------------------------------------
MISSING_AGAINST_TABLE_SQL = """
WITH want AS (
  SELECT DISTINCT permanent_identifier AS pid,
         LOWER(REPLACE(REPLACE(permanent_identifier,'{{','' ),'}}','')) AS k
  FROM `energy-platfrom.energy.{src}`
  WHERE UPPER(IFNULL(src_state,'')) = 'IN' AND ({cut})
),
got AS (
  SELECT DISTINCT LOWER(REPLACE(REPLACE(permanent_identifier,'{{',''),'}}','')) AS k
  FROM `energy-platfrom.indiana_app.{tbl}`
)
SELECT w.pid FROM want w LEFT JOIN got g USING (k) WHERE g.k IS NULL
"""
TARGET = {"flowline": "in_nhd_flowline_geom", "waterbody": "in_nhd_waterbody_geom"}
SRCTBL = {"flowline": "nhd_flowline", "waterbody": "nhd_waterbody"}
CUT = {
    "flowline": "ftype = 460 AND gnis_name IS NOT NULL",
    "waterbody": "ftype = 436 OR (ftype = 390 AND areasqkm >= 0.1) "
                 "OR (ftype = 466 AND areasqkm >= 0.1)",
}


def append_missing(layer):
    """Fetch the keys the BUILT table lacks and stage them for an APPEND. Never replaces anything."""
    client = bigquery.Client(project="energy-platfrom")
    name = layer["name"]
    sql = MISSING_AGAINST_TABLE_SQL.format(src=SRCTBL[name], cut=CUT[name], tbl=TARGET[name])
    missing = sorted({r.pid for r in client.query(sql)})
    print(f"  [{name}] {TARGET[name]} is missing {len(missing):,} keys of the Indiana cut")
    path = os.path.join(OUT, f"{name}_backfill.ndjson")

    # RESUME, because this pass is SLOW BY DESIGN. One key costs about a second against a public
    # federal service we do not own, so 3,848 of them run for an hour - longer than some shells will
    # hold a process. Measured 2026-08-17: a first run was killed at 3,600s having written 3,827
    # features to disk and loaded NONE of them. Re-requesting all 3,848 to recover 21 would be an
    # hour of someone else's bandwidth spent on data already sitting in the file, so whatever the
    # NDJSON already holds is kept, its keys come off the request list, and the file is APPENDED to.
    done = set()
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            pid = json.loads(line).get("permanent_identifier")
            if pid:
                done.add(pid.strip("{}").lower())
        missing = [p for p in missing if p.strip("{}").lower() not in done]
        print(f"  [{name}] resuming: {len(done):,} already on disk, {len(missing):,} still to ask for")

    got, t0, nogeom = 0, time.time(), 0
    if missing:
        with open(path, "a", encoding="utf-8") as fh:
            for i in range(0, len(missing), BATCH):
                chunk = missing[i:i + BATCH]
                for f in fetch_by_keys(layer["lid"], KEYFIELD[name], layer["fields"], chunk):
                    g = f.get("geometry")
                    if not g:                   # the publisher holds the attribute but no shape
                        nogeom += 1
                        continue
                    props = {k.lower(): v for k, v in (f.get("properties") or {}).items()}
                    props["_geom"] = json.dumps(g, separators=(",", ":"))
                    fh.write(json.dumps(props, separators=(",", ":")) + "\n")
                    got += 1
                if (i // BATCH) % 10 == 0:
                    print(f"    ...{i + len(chunk):,}/{len(missing):,} requested, {got:,} returned "
                          f"({time.time() - t0:.0f}s)", flush=True)
                time.sleep(0.4)
        print(f"  [{name}] publisher returned {got:,} of {len(missing):,} requested this pass "
              f"({nogeom:,} had attributes but no geometry)")
    staged = sum(1 for _ in open(path, encoding="utf-8")) if os.path.exists(path) else 0
    if not staged:
        print(f"  [{name}] nothing staged - the publisher returned no geometry for any key")
        return 0
    # Staged in its OWN table. The append into the finished table is build_nhd_geometry.py --append,
    # which is where the ftype decode and the huc8 STRING cut live - kept in one place on purpose.
    stage = f"{DS}._raw_nhd_{name}_backfill"
    with open(path, "rb") as fh:
        client.load_table_from_file(
            fh, stage, job_config=bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                schema=SCHEMAS[name], write_disposition="WRITE_TRUNCATE")).result()
    # And APPENDED to the raw sweep table, so a future full rebuild reproduces this capture rather
    # than silently regressing to the bbox-only result.
    with open(path, "rb") as fh:
        client.load_table_from_file(
            fh, f"{DS}._raw_nhd_{name}", job_config=bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                schema=SCHEMAS[name], write_disposition="WRITE_APPEND")).result()
    print(f"  [{name}] staged {staged:,} rows in {stage} and appended them to {DS}._raw_nhd_{name}")
    # The keys the publisher has NO geometry for. Recorded, not silently dropped: a gap you can name
    # is a finding, a gap you cannot is a hole in the table nobody will ever notice.
    have = {(json.loads(l).get("permanent_identifier") or "").strip("{}").lower()
            for l in open(path, encoding="utf-8")}
    still = [p for p in missing if p.strip("{}").lower() not in have]
    if still:
        print(f"  [{name}] PUBLISHER RETURNED NOTHING for {len(still):,} keys, e.g. {still[:5]}")
    return staged


if __name__ == "__main__":
    if "--append-missing" in _sys.argv:
        sel = [a for a in _sys.argv[1:] if not a.startswith("--")]
        for layer in LAYERS:
            if layer["name"] not in TARGET or (sel and layer["name"] not in sel):
                continue
            print(f"=== append-missing {layer['name']} (layer {layer['lid']})")
            append_missing(layer)
        print(f"totals: {_stats['req']} requests, {_stats['bytes']/1e6:.0f} MB transferred")
        raise SystemExit(0)

    only = _sys.argv[1] if len(_sys.argv) > 1 and not _sys.argv[1].startswith("--") else None
    for layer in LAYERS:
        if only and layer["name"] != only:
            continue
        print(f"=== pulling {layer['name']} (layer {layer['lid']}): {layer['where']}")
        path = os.path.join(OUT, f"{layer['name']}.ndjson")
        if ("--load-only" in _sys.argv or "--backfill" in _sys.argv) and os.path.exists(path):
            n = sum(1 for _ in open(path, encoding="utf-8"))
            print(f"  reusing {path} ({n:,} lines)")
        else:
            path, n = pull(layer)
        # NHDArea has no counterpart table in `energy` (the estate holds nhd_flowline and
        # nhd_waterbody only), so there is no authoritative key list to backfill against.
        if "--backfill" in _sys.argv and layer["name"] in BACKFILL_SQL:
            n += backfill(layer)
        assert n > 0, f"{layer['name']}: zero features - check the endpoint before believing this"
        got = load(path, f"_raw_nhd_{layer['name']}", layer["name"])
        print(f"  loaded {got:,} rows into {DS}._raw_nhd_{layer['name']}")
    print(f"totals: {_stats['req']} requests, {_stats['bytes']/1e6:.0f} MB transferred")
