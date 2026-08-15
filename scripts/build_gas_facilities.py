"""Clip held gas facilities + EIA state-to-state capacity to Indiana; extend gas.geojson.gz.
Adds: compressor stations, storage, processing plants, LNG (points) to the gas layer,
and an Indiana state-border capacity table into market.json.gz."""
import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
E = "`energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")
ST = "(SELECT state_geom FROM `bigquery-public-data.geo_us_boundaries.states` WHERE state='IN')"

def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)
def rc(x):
    if isinstance(x, float): return round(x, 6)
    if isinstance(x, list): return [rc(v) for v in x]
    return x

with gzip.open(os.path.join(REPO, "data", "gas.geojson.gz"), "rt", encoding="utf-8") as f:
    gasfc = json.load(f)
print(f"existing gas features: {len(gasfc['features'])}")

for tbl, layer in [("gas_compressor_stations", "compressor"), ("gas_storage", "storage"),
                   ("gas_processing_plants", "processing"), ("gas_lng_terminals", "lng")]:
    t = client.get_table(f"energy-platfrom.energy.{tbl}")
    cols = [s.name for s in t.schema]
    gcol = next((c for c in cols if c.lower() in ("geog", "geom")), None)
    gjson = next((c for c in cols if "geojson" in c.lower()), None)
    geo = gcol if gcol else f"SAFE.ST_GEOGFROMGEOJSON({gjson})"
    keep = [c for c in cols if c not in (gcol, gjson) and not c.startswith("_")][:10]
    sql = f"""CREATE OR REPLACE TABLE `{DS}.in_{tbl}` AS
      SELECT {', '.join(keep)}, g AS geog FROM (SELECT *, {geo} AS g FROM {E}.{tbl}`)
      WHERE g IS NOT NULL AND ST_INTERSECTS(g, {ST})"""
    dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
    gb = dry.total_bytes_processed / 1e9
    client.query(sql).result()
    n = list(client.query(f"SELECT COUNT(*) AS n FROM `{DS}.in_{tbl}`"))[0].n
    client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
      VALUES ('in_{tbl}','energy.{tbl}','spatial clip to IN', {n}, {gb:.3f}, CURRENT_TIMESTAMP(), NULL)""").result()
    for r in client.query(f"SELECT *, ST_ASGEOJSON(geog) AS gj FROM `{DS}.in_{tbl}`"):
        d = dict(r); gj = d.pop("gj"); d.pop("geog", None); d["layer"] = layer
        gasfc["features"].append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
    print(f"in_{tbl}: {n} rows")

with gzip.open(os.path.join(REPO, "data", "gas.geojson.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(gasfc, f, separators=(",", ":"), default=jd)
print(f"gas.geojson.gz now: {len(gasfc['features'])} features")

# EIA state-to-state capacity, Indiana borders (columns discovered, never guessed)
t = client.get_table("energy-platfrom.energy.gas_eia_state_capacity")
cols = [s.name for s in t.schema]
print("gas_eia_state_capacity columns:", cols)
statecols = [c for c in cols if "state" in c.lower()]
where = " OR ".join(f"UPPER(CAST({c} AS STRING)) IN ('IN','INDIANA')" for c in statecols) or "FALSE"
rows = [dict(r) for r in client.query(
    f"SELECT * FROM {E}.gas_eia_state_capacity` WHERE {where}")]
with gzip.open(os.path.join(REPO, "data", "market.json.gz"), "rt", encoding="utf-8") as f:
    market = json.load(f)
market["gas_state_capacity"] = rows
with gzip.open(os.path.join(REPO, "data", "market.json.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(market, f, separators=(",", ":"), default=jd)
n = len(rows)
client.query(f"""CREATE OR REPLACE TABLE `{DS}.in_gas_state_capacity` AS
  SELECT * FROM {E}.gas_eia_state_capacity` WHERE {where}""").result()
client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES ('in_gas_state_capacity','energy.gas_eia_state_capacity','IN-border filter', {n}, 0.01,
          CURRENT_TIMESTAMP(), 'EIA state-to-state DESIGN capacity - not operational availability')""").result()
print(f"in_gas_state_capacity: {n} rows; market.json.gz updated")
print("GAS FACILITIES COMPLETE")
