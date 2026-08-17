"""Acquire HUC8 (subbasin) boundaries for Indiana from the USGS Watershed Boundary Dataset.

WHY. `energy.nhd_flowline` and `nhd_waterbody` carry NO geometry - the `SHAPE:GEOGRAPHY` column is
NULL on all 50M rows nationally - so rivers and lakes cannot be measured to. But they DO carry
`reachcode`, whose first 8 digits are the HUC8 subbasin, populated on **all 2,415,369 Indiana
flowlines with zero missing**, across 77 subbasins.

So the missing link is one polygon layer. With HUC8 boundaries we can:
  * place every parcel in a subbasin (spatial, cheap - 77 polygons)
  * inventory rivers, named rivers, lakes and reservoirs per subbasin **from attributes alone**
  * answer "what surface water is in this parcel's watershed" without a single NHD geometry

That is a far smaller acquisition than re-loading 39.5M NHD geometries, which is the alternative.

SOURCE. USGS The National Map, WBD MapServer layer 4 ("8-digit HU (Subbasin)"):
    https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/4/query
Public, anonymous, no key, no terms dialogue. Paged with resultOffset, geometry in EPSG:4326 by
publisher reprojection (outSR=4326) rather than anything we derive.

⚠ Indiana subbasins are selected by INTERSECTION WITH THE STATE, not by a name match: a watershed
does not respect a state line, and several of Indiana's 77 drain into Ohio, Michigan or Illinois.
Selecting on name would silently drop the border basins, which are exactly the ones where a siting
question is most likely to cross a jurisdiction.

Writes `indiana_app.in_huc8_boundaries` and registers it in the same run.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import json, time, urllib.parse, urllib.request
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
LAYER = "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/4/query"
# Indiana bounding box, slightly padded so border subbasins are captured whole
BBOX = "-88.4,37.6,-84.6,41.9"
PAGE = 200
client = bigquery.Client(project="energy-platfrom")


def fetch(offset):
    params = {
        "where": "1=1",
        "geometry": BBOX,
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "huc8,name,areaacres,areasqkm,states,loaddate",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
        "resultOffset": str(offset),
        "resultRecordCount": str(PAGE),
    }
    url = LAYER + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "indiana-siting-research/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


feats, offset = [], 0
while True:
    d = fetch(offset)
    got = d.get("features", [])
    feats.extend(got)
    print(f"  offset {offset}: {len(got)} features (total {len(feats)})", flush=True)
    if len(got) < PAGE:
        break
    offset += PAGE
    time.sleep(0.6)          # polite; this is a public service we do not own

assert feats, "no features returned - check the endpoint before assuming Indiana has no subbasins"

rows = []
for f in feats:
    p = f.get("properties") or {}
    g = f.get("geometry")
    if not g:
        continue
    rows.append({
        "huc8": p.get("huc8"),
        "name": p.get("name"),
        "states": p.get("states"),
        "area_sqkm": p.get("areasqkm"),
        "area_acres": p.get("areaacres"),
        "load_date": str(p.get("loaddate")) if p.get("loaddate") is not None else None,
        "geom_geojson": json.dumps(g),
        "_source_url": LAYER,
    })
print(f"parsed {len(rows)} subbasin polygons")

job = client.load_table_from_json(
    rows, f"{DS}.in_huc8_raw",
    job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"))
job.result()

client.query(f"""
CREATE OR REPLACE TABLE `{DS}.in_huc8_boundaries` AS
SELECT huc8, name, states, area_sqkm, area_acres, load_date, _source_url,
       SAFE.ST_GEOGFROMGEOJSON(geom_geojson, make_valid => TRUE) AS geog,
       CURRENT_TIMESTAMP() AS built_at
FROM `{DS}.in_huc8_raw`
WHERE huc8 IS NOT NULL
""").result()
client.query(f"DROP TABLE IF EXISTS `{DS}.in_huc8_raw`").result()

m = list(client.query(f"""
SELECT COUNT(*) n, COUNT(DISTINCT huc8) d, COUNTIF(geog IS NULL) bad_geom,
       COUNTIF(states LIKE '%IN%') touching_indiana,
       ROUND(SUM(area_sqkm)) total_sqkm
FROM `{DS}.in_huc8_boundaries`"""))[0]
print(f"in_huc8_boundaries: {m.n} rows, {m.d} distinct HUC8, {m.bad_geom} unparseable geometries")
print(f"  listing Indiana among their states: {m.touching_indiana}")
print(f"  total area: {m.total_sqkm:,} sq km")
assert m.n == m.d and m.bad_geom == 0, "duplicate or unparseable subbasins"

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_huc8_boundaries'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
    f"VALUES (@t,@s,@m,@n,0.0,CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "in_huc8_boundaries"),
        bigquery.ScalarQueryParameter("s", "STRING", LAYER),
        bigquery.ScalarQueryParameter("m", "STRING",
            f"ArcGIS REST, layer 4 (8-digit HU / Subbasin), envelope {BBOX} intersect, outSR=4326 "
            f"publisher reprojection, paged at {PAGE} via resultOffset. "
            f"RE-SCRAPE COMMAND: python scripts/pull_huc8_boundaries.py"),
        bigquery.ScalarQueryParameter("n", "INT64", int(m.n)),
        bigquery.ScalarQueryParameter("no", "STRING",
            "endpoint_kind=arcgis_mapserver_layer, public/anonymous, no key and no terms dialogue. "
            "Acquired because NHD flowline/waterbody geometry is NULL nationally, while reachcode "
            "(first 8 digits = HUC8) is populated on all 2,415,369 Indiana flowlines. These 77-odd "
            "polygons are the bridge that lets parcels be placed in a watershed and rivers to be "
            "inventoried per watershed FROM ATTRIBUTES ALONE. Selected by INTERSECTION with the "
            "state envelope, not by name: watersheds cross state lines and a name filter would "
            "silently drop the border basins.")])).result()
print("registered in_huc8_boundaries")
