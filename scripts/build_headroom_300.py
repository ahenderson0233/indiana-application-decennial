"""Fold the bounded 300MW harvest into the bus layer: per-POI headroom at a 300MW-class
request (MIN over facilities — meaningful at a bounded request), joined onto
in_bus_headroom_miso, re-exported to the grid payload. Column names detected, not guessed."""
import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

cols = [s.name for s in client.get_table(f"{DS}.in_miso_poi_300mw").schema]
print("300mw cols:", cols[:20])
avail = next((c for c in cols if "available" in c.lower()), None)
poic = "_poi_name_requested"
fac = next((c for c in cols if "monitored" in c.lower() or c.lower() == "facility"), None)
assert avail, f"no available-MW column found in {cols}"

client.query(f"""
CREATE OR REPLACE TABLE `{DS}.in_bus_headroom_300` AS
SELECT {poic} AS poi_name,
       MIN(SAFE_CAST({avail} AS FLOAT64)) AS headroom300_mw,
       COUNT(*) AS facilities_300,
       {f"ARRAY_AGG({fac} ORDER BY SAFE_CAST({avail} AS FLOAT64) ASC LIMIT 1)[OFFSET(0)]" if fac else "CAST(NULL AS STRING)"} AS binding_300
FROM `{DS}.in_miso_poi_300mw` GROUP BY 1""").result()
stats = list(client.query(f"""
SELECT COUNT(*) AS pois, COUNTIF(headroom300_mw > 0) AS positive,
       APPROX_QUANTILES(headroom300_mw, 4) AS q
FROM `{DS}.in_bus_headroom_300`"""))[0]
print("headroom300:", dict(stats))
client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES ('in_bus_headroom_300','in_miso_poi_300mw','MIN({avail}) per POI at pMax=300',
          {stats.pois}, 0.01, CURRENT_TIMESTAMP(),
          'THE single representative number: headroom for a 300MW-class request, per operator ruling')""").result()

def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)
def rc(x):
    if isinstance(x, float): return round(x, 6)
    if isinstance(x, list): return [rc(v) for v in x]
    return x

# regenerate the bus features inside grid.geojson.gz with headroom300 attached
p = os.path.join(REPO, "data", "grid.geojson.gz")
with gzip.open(p, "rt", encoding="utf-8") as f: fc = json.load(f)
fc["features"] = [ft for ft in fc["features"] if ft["properties"].get("layer") != "bus_poi"]
n = 0
for r in client.query(f"""
  SELECT b.poi_name, b.bus_number, b.bus_name, b.kv, b.area_name, h.headroom300_mw,
         h.binding_300, b.worst_mw, b.best_mw, b.median_mw, b.monitored_facilities,
         b.worst_binding_facility, b.vintage, b.lat, b.lon
  FROM `{DS}.in_bus_headroom_miso` b
  LEFT JOIN `{DS}.in_bus_headroom_300` h USING (poi_name)
  WHERE b.location_status='indiana'"""):
    d = dict(r); lat, lon = d.pop("lat"), d.pop("lon"); d["layer"] = "bus_poi"
    fc["features"].append({"type": "Feature", "properties": d,
      "geometry": {"type": "Point", "coordinates": [rc(float(lon)), rc(float(lat))]}})
    n += 1
with gzip.open(p, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(fc, f, separators=(",", ":"), default=jd)
print(f"grid.geojson.gz: {n} bus POIs re-emitted with headroom300")
print("HEADROOM300 WIRING COMPLETE")
