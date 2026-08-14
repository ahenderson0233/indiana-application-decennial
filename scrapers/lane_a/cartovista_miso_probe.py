"""Task 1 probe: re-measure the PUBLIC CartoVista API surface for MISO POI identity.

Prior state (energy-platfrom.energy.registry_sources, measured 2026-08-02/03):
  - Layer/{id}/geojson          -> 403  (MISO POI layer b34ef6bd-fb8f-40a7-ab9a-c9552f1c3621)
  - DataTable/{guid}/DataRows   -> 403
  - DataServices/dataQueryExecute -> 403 (even with the full join contract)
  - Layer/{id}/mvt/x/y/z.pbf    -> 200 but properties carry x/y ONLY
  - maps/details, DataColumns, config XMLs -> 200 (metadata public)
Registry note: "re-probe before assuming". This script re-measures every route read-only,
records exact status codes + first bytes of each body, and never works around a 403.

Boundaries: >=1.1s per host, identifying UA, GETs + query-POSTs only (a POST to a query
endpoint is a read), no accounts, no keys, nothing mutated.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"
MAP_ID = "59878415-54b3-4502-9429-bfd90c7ce3c5"  # MISO FERC O.2023 POI map (verified prior work)
ORG = "miso"
DELAY = 1.15
OUT = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_a\cartovista_miso_probe_results.json"

results = []
_last = [0.0]


def _throttle():
    dt = time.time() - _last[0]
    if dt < DELAY:
        time.sleep(DELAY - dt)
    _last[0] = time.time()


def probe(label, url, method="GET", body=None, keep=400):
    _throttle()
    headers = {"User-Agent": UA, "Accept": "*/*"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    rec = {"label": label, "url": url, "method": method}
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read(8_000_000)
            rec["status"] = r.status
            rec["bytes"] = len(raw)
            rec["body_head"] = raw[:keep].decode("utf-8", "replace")
            rec["_raw"] = raw
    except urllib.error.HTTPError as e:
        rec["status"] = e.code
        try:
            rec["body_head"] = e.read(400).decode("utf-8", "replace")
        except Exception:
            rec["body_head"] = ""
    except Exception as e:
        rec["status"] = None
        rec["body_head"] = f"{type(e).__name__}: {e}"
    results.append(rec)
    print(f"[{rec.get('status')}] {label}  ({rec.get('bytes', 0):,}b)  {url[:110]}")
    return rec


# 1. settings — is the POI map still declared public?
s = probe("settings", f"https://ferc.cartovista.com/api/settings/{ORG}/ferc")
if s.get("status") == 200:
    js = json.loads(s.pop("_raw"))
    print("   isPoiMapPublic:", js.get("isPoiMapPublic"),
          "| injection bounds:", js.get("minInjection"), "..", js.get("maxInjection"))
    s["isPoiMapPublic"] = js.get("isPoiMapPublic")

# 2. map details — enumerate dataTables (name, systemIdentifier GUID, rowCount)
d = probe("maps/details", f"https://cloud.cartovista.com/{ORG}/api/v2/maps/{MAP_ID}/details")
tables = []
if d.get("status") == 200:
    js = json.loads(d.pop("_raw"))
    for t in js.get("dataTables") or []:
        tables.append({"name": t.get("name"), "guid": t.get("systemIdentifier"),
                       "rows": t.get("rowCount") or 0})
        print(f"   table {t.get('rowCount') or 0:>9,}  {str(t.get('name'))[:44]:<46}"
              f"{t.get('systemIdentifier')}")
    d["tables"] = tables

# 3. map config XML — VectorLayer ids + layerSourceId/sourceId (the dqe id space)
import re
cfg = probe("config-xml", f"https://cloud.cartovista.com/{ORG}/WebPortalServices/"
                          f"CartoVistaConfigFileGenerator.aspx?type=Dynamic&mapId={MAP_ID}")
layers = []
if cfg.get("status") == 200:
    xml = cfg.pop("_raw").decode("utf-8", "replace")
    for m in re.finditer(r'<VectorLayer id="([^"]+)"', xml):
        alias = m.group(1)
        seg = xml[m.start():m.start() + 40000]
        w = re.search(r'<WebPortalConfiguration joinColumnId="([^"]+)" layerSourceId="([^"]+)" '
                      r'sourceId="([^"]+)"', seg)
        if w:
            layers.append({"alias": alias, "join_col": w.group(1),
                           "layer_src": w.group(2), "table_src": w.group(3)})
            print(f"   layer {alias:<42} layer_src={w.group(2)} table_src={w.group(3)}")
    cfg["layers"] = layers

poi = next((L for L in layers if "poi" in L["alias"].lower()), None)
poi_tbl_guid = next((t["guid"] for t in tables if "poi" in (t["name"] or "").lower()), None)
poi_tbl_rows = next((t["rows"] for t in tables if "poi" in (t["name"] or "").lower()), 0)

# 4. DataColumns for the POI table (metadata was public before)
cols = []
if poi:
    c = probe("DataColumns(POI)", f"https://cloud.cartovista.com/{ORG}/api/v2/DataTable/"
                                  f"{poi['table_src']}/DataColumns")
    if c.get("status") == 200:
        js = json.loads(c.pop("_raw"))
        items = js if isinstance(js, list) else (js.get("dataColumns") or js.get("items") or [])
        cols = [{"name": x.get("name"), "sid": x.get("systemIdentifier")}
                for x in items if x.get("systemIdentifier")]
        print(f"   {len(cols)} columns: {[x['name'] for x in cols]}")
        c["columns"] = [x["name"] for x in cols]

# 5. the previously-403 trio, re-measured
if poi:
    probe("Layer/geojson(POI)", f"https://cloud.cartovista.com/{ORG}/api/v2/Layer/"
                                f"{poi['layer_src']}/geojson", keep=300)
if poi_tbl_guid:
    probe("DataRows(POI,POST)", f"https://cloud.cartovista.com/{ORG}/api/v2/DataTable/"
                                f"{poi_tbl_guid}/DataRows",
          method="POST", body={"startRow": 0, "rowCount": 5}, keep=300)
if poi and cols:
    payload = [{"id": x["sid"], "dataTableId": poi["table_src"], "layerId": poi["layer_src"],
                "columnIdAlias": x["name"], "tableIdAlias": poi["alias"]} for x in cols]
    probe("dataQueryExecute(POI,POST)",
          f"https://cloud.cartovista.com/{ORG}/DataServices/dataQueryExecute",
          method="POST", body={
              "linkingIds": None, "linkingIdsForStats": None, "filterDataColumns": [],
              "sortDataColumns": [], "dataColumns": payload, "groupBy": None,
              "startIndex": 0, "maxCount": 5, "dataSamplingCount": 0,
              "searchCriteria": None, "excludeNotAvailableValue": False,
              "serverCacheEnabled": True, "statistics": None, "statisticsOnly": False,
              "sortOrders": None, "dataQueryFilters": None, "selectionStackParameters": None,
              "spatialFilter": None, "timeRange": None, "quadKeys": None, "fids": None,
              "aggregatedDataFilters": None}, keep=300)

# 6. MVT single-tile control (was 200) — z4 tile over Indiana
if poi:
    probe("MVT tile z4 (control)", f"https://cloud.cartovista.com/{ORG}/api/v2/Layer/"
                                   f"{poi['layer_src']}/mvt/4/6/4.pbf", keep=0)

for r in results:
    r.pop("_raw", None)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=1)
print(f"\nsaved {len(results)} probe records -> {OUT}")
