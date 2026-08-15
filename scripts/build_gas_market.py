"""Gas pipelines (held HIFLD geometry) clipped to Indiana + market (CEMS) export.
  BQ: indiana_app.in_gas_pipelines (registered)
  data/gas.geojson.gz    Indiana gas pipeline segments (P2/P6 gas layer)
  data/market.json.gz    statewide CEMS monthly series + top plants (P6)
"""
import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
E = "`energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")
ST = ("(SELECT state_geom FROM `bigquery-public-data.geo_us_boundaries.states` WHERE state='IN')")

def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)
def rc(x):
    if isinstance(x, float): return round(x, 6)
    if isinstance(x, list): return [rc(v) for v in x]
    return x

# discover the geometry + attr columns of the held HIFLD gas layer (never guess)
t = client.get_table("energy-platfrom.energy.gas_pipelines_hifld")
cols = [s.name for s in t.schema]
print("gas_pipelines_hifld columns:", cols[:25])
gcol = next((c for c in cols if c.lower() in ("geog", "geom")), None)
gjson = next((c for c in cols if "geojson" in c.lower()), None)
keep = [c for c in cols if c not in (gcol, gjson) and not c.startswith("_")][:14]
geo_expr = gcol if gcol else f"SAFE.ST_GEOGFROMGEOJSON({gjson})"

sql = f"""
CREATE OR REPLACE TABLE `{DS}.in_gas_pipelines` AS
SELECT {', '.join(keep)}, g AS geog
FROM (SELECT *, {geo_expr} AS g FROM {E}.gas_pipelines_hifld`)
WHERE g IS NOT NULL AND ST_INTERSECTS(g, {ST})"""
dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
gb = dry.total_bytes_processed / 1e9
client.query(sql).result()
n = list(client.query(f"SELECT COUNT(*) AS n FROM `{DS}.in_gas_pipelines`"))[0].n
parse_fail = list(client.query(
    f"SELECT COUNTIF({geo_expr} IS NULL) AS f, COUNT(*) AS t FROM {E}.gas_pipelines_hifld`"))[0] if gjson else None
client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES ('in_gas_pipelines','energy.gas_pipelines_hifld','spatial clip to IN', {n}, {gb:.3f},
          CURRENT_TIMESTAMP(), 'geometry parse failures disclosed in export log')""").result()
print(f"in_gas_pipelines: {n} rows ({gb:.2f} GB)" + (f" | national parse failures: {parse_fail.f}/{parse_fail.t}" if parse_fail else ""))

feats = []
for r in client.query(f"SELECT *, ST_ASGEOJSON(geog) AS gj FROM `{DS}.in_gas_pipelines`"):
    d = dict(r); gj = d.pop("gj"); d.pop("geog", None); d["layer"] = "gas"
    feats.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
with gzip.open(os.path.join(REPO, "data", "gas.geojson.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump({"type": "FeatureCollection", "features": feats}, f, separators=(",", ":"), default=jd)
print(f"gas.geojson.gz: {len(feats)}")

# market: statewide monthly + top plants (P6, closes the in_cems_monthly waiver)
series = [dict(r) for r in client.query(f"""
  SELECT month, ROUND(SUM(gross_load_mwh),0) AS gross_load_mwh, ROUND(SUM(co2_tons),0) AS co2_tons
  FROM `{DS}.in_cems_monthly` GROUP BY 1 ORDER BY 1""")]
plants = [dict(r) for r in client.query(f"""
  SELECT plant_id_epa, ROUND(SUM(gross_load_mwh),0) AS gross_load_mwh, ROUND(SUM(co2_tons),0) AS co2_tons,
         MIN(month) AS first_month, MAX(month) AS last_month
  FROM `{DS}.in_cems_monthly` GROUP BY 1 ORDER BY gross_load_mwh DESC LIMIT 25""")]
with gzip.open(os.path.join(REPO, "data", "market.json.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump({"monthly": series, "top_plants": plants}, f, separators=(",", ":"), default=jd)
print(f"market.json.gz: {len(series)} months, {len(plants)} plants")
print("GAS+MARKET COMPLETE")
