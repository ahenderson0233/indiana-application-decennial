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

# ⛔ THIS SCRIPT WAS NOT IDEMPOTENT AND EVERY RE-RUN DOUBLED ITS OWN LAYERS.
#    It APPENDS compressor / storage / processing / lng features to an existing payload it does
#    not own, and never removed what a previous run of itself had added. Measured the moment it
#    was re-run in 2026-08-20b: compressor 24 -> 48 features, storage 22 -> 44, for 24 and 22
#    warehouse rows. Every marker drawn twice, every count on the map overstated by exactly 2x,
#    and nothing errors - the payload is still valid GeoJSON.
# ⚠ Only the layers THIS script owns are dropped. The 213 pipeline features belong to another
#    exporter and must survive, which is why this filters by layer rather than truncating.
OWNED = {"compressor", "storage", "processing", "lng"}
_before = len(gasfc["features"])
gasfc["features"] = [f for f in gasfc["features"]
                     if f.get("properties", {}).get("layer") not in OWNED]
if _before != len(gasfc["features"]):
    print(f"  dropped {_before - len(gasfc['features'])} feature(s) this script had added "
          f"previously, so the re-run replaces rather than duplicates")

for tbl, layer in [("gas_compressor_stations", "compressor"), ("gas_storage", "storage"),
                   ("gas_processing_plants", "processing"), ("gas_lng_terminals", "lng")]:
    t = client.get_table(f"energy-platfrom.energy.{tbl}")
    cols = [s.name for s in t.schema]
    gcol = next((c for c in cols if c.lower() in ("geog", "geom")), None)
    gjson = next((c for c in cols if "geojson" in c.lower()), None)
    geo = gcol if gcol else f"SAFE.ST_GEOGFROMGEOJSON({gjson})"
    # ⛔ THE `[:10]` CUT THAT USED TO BE HERE WAS DROPPING THE MOST USEFUL COLUMNS IN THESE
    #    TABLES - G27's warning that "the same `[:N]` idiom is unaudited in this file" was
    #    justified, and `scripts/audit_schema_truncation.py` measured it:
    #      gas_compressor_stations  45 eligible columns, 35 dropped - including status, county,
    #                               latitude, longitude, operator
    #      gas_storage              41 eligible, 31 dropped - including owner, operator,
    #                               ownerpct, reservname, type, status
    #      gas_processing_plants    45 eligible, 35 dropped - including compname, operator,
    #                               plantflow  (moot in practice: 0 Indiana rows)
    #      gas_lng_terminals        41 eligible, 31 dropped - including owner, contype, opyear,
    #                               storcap    (moot in practice: 0 Indiana rows)
    #    A cut by POSITION keeps whatever the publisher happened to put first. HIFLD puts its
    #    identifiers first and everything a siter would want after column 10.
    # ⭐ KEEP THEM ALL. These clips hold 24 and 22 Indiana rows; the payload cost of forty
    #    columns on forty-six rows is nothing, and the whole point of the layer is the popup.
    keep = [c for c in cols if c not in (gcol, gjson) and not c.startswith("_")]
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
