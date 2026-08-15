"""Facilities payload: existing data centres (244, 4-source), power plants, solar, wind
as one typed GeoJSON for the map + the Grid page. Adaptive geometry per table."""
import json, gzip, os
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

def rc(x):
    if isinstance(x, float): return round(x, 6)
    if isinstance(x, list): return [rc(v) for v in x]
    return x

feats = []
def add_points(table, layer, keep, latc=None, lonc=None, geogc=None, gjson=None, where=""):
    sel = ", ".join(keep)
    if latc:
        q = (f"SELECT {sel}, SAFE_CAST({latc} AS FLOAT64) AS _la, SAFE_CAST({lonc} AS FLOAT64) AS _lo "
             f"FROM `{DS}.{table}` WHERE SAFE_CAST({latc} AS FLOAT64) IS NOT NULL {where}")
    elif geogc:
        q = f"SELECT {sel}, ST_Y({geogc}) AS _la, ST_X({geogc}) AS _lo FROM `{DS}.{table}` WHERE {geogc} IS NOT NULL {where}"
    else:
        q = (f"SELECT {sel}, ST_Y(SAFE.ST_GEOGFROMGEOJSON({gjson})) AS _la, "
             f"ST_X(SAFE.ST_GEOGFROMGEOJSON({gjson})) AS _lo FROM `{DS}.{table}` "
             f"WHERE SAFE.ST_GEOGFROMGEOJSON({gjson}) IS NOT NULL {where}")
    n = 0
    for r in client.query(q):
        d = dict(r); la, lo = d.pop("_la"), d.pop("_lo")
        if la is None or lo is None: continue
        d["layer"] = layer
        feats.append({"type": "Feature", "properties": {k: (None if v is None else str(v)) for k, v in d.items()},
                      "geometry": {"type": "Point", "coordinates": [rc(float(lo)), rc(float(la))]}})
        n += 1
    print(f"{table} -> {layer}: {n}")

add_points("in_data_centers_all", "dc", ["src", "name", "operator"], latc="lat", lonc="lon")

t = client.get_table(f"{DS}.in_eia_plants")
cols = [s.name.lower() for s in t.schema]
latc = next((c for c in cols if c in ("latitude", "lat")), None)
lonc = next((c for c in cols if c in ("longitude", "lon", "lng")), None)
keep = [c for c in cols if any(k in c for k in ("name", "capacity", "fuel", "technology", "county", "utility"))][:6] or [cols[0]]
if latc: add_points("in_eia_plants", "plant", keep, latc=latc, lonc=lonc)
else: print("in_eia_plants: no lat/lon — using power_plants only")

t = client.get_table(f"{DS}.in_power_plants")
cols = [s.name for s in t.schema]
gj = next((c for c in cols if "geojson" in c.lower()), None)
gg = next((c for c in cols if c.lower() in ("geog", "geom", "_g")), None)
keep = [c for c in cols if any(k in c.lower() for k in ("name", "mw", "fuel", "type", "oper"))][:6] or [cols[0]]
add_points("in_power_plants", "plant_hifld", keep, geogc=gg, gjson=gj)

for tbl, layer in [("in_solar_pv_facilities", "solar"), ("in_wind_turbines", "wind")]:
    t = client.get_table(f"{DS}.{tbl}")
    cols = [s.name for s in t.schema]
    latc = next((c for c in cols if c.lower() in ("latitude", "lat", "ylat", "lat_dd")), None)
    lonc = next((c for c in cols if c.lower() in ("longitude", "lon", "xlong", "long_dd", "lng")), None)
    gj = next((c for c in cols if "geojson" in c.lower()), None)
    gg = next((c for c in cols if c.lower() in ("geog", "geom", "_g")), None)
    keep = [c for c in cols if any(k in c.lower() for k in ("name", "mw", "capacity", "county", "oper", "proj"))][:6] or [cols[0]]
    if latc and lonc: add_points(tbl, layer, keep, latc=latc, lonc=lonc)
    elif gg or gj: add_points(tbl, layer, keep, geogc=gg, gjson=gj)
    else: print(f"{tbl}: no geometry found ({cols[:8]}) — FLAG")

with gzip.open(os.path.join(REPO, "data", "facilities.geojson.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump({"type": "FeatureCollection", "features": feats}, f, separators=(",", ":"))
print(f"facilities.geojson.gz: {len(feats)} features")
