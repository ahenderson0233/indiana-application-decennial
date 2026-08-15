"""Utility service territories (P2, operator-named gap): clip vw_grid_territories to Indiana,
export data/territories.geojson.gz, refresh provenance, and correct the in_parcel_attrs record
(its IN slice is 100% NULL on every attribute column - upstream defect, question filed)."""
import json, gzip, os, shutil, datetime, decimal
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
    if isinstance(x, float): return round(x, 5)
    if isinstance(x, list): return [rc(v) for v in x]
    return x

sql = f"""CREATE OR REPLACE TABLE `{DS}.in_territories` AS
SELECT territory_id, utility, utility_type, holding_company, regulated, control_area,
       customers, summer_peak_mw, retail_mwh, data_year,
       ST_INTERSECTION(geom, {ST}) AS geog
FROM {E}.vw_grid_territories`
WHERE ST_INTERSECTS(geom, {ST})"""
dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
client.query(sql).result()
n = list(client.query(f"SELECT COUNT(*) AS n FROM `{DS}.in_territories`"))[0].n
client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES ('in_territories','energy.vw_grid_territories','spatial clip+intersection to IN', {n},
          {dry.total_bytes_processed/1e9:.3f}, CURRENT_TIMESTAMP(),
          'clipped to state boundary for payload; source polygons uncut in energy.*')""").result()
print(f"in_territories: {n}")

feats = []
for r in client.query(f"SELECT *, ST_ASGEOJSON(geog) AS gj FROM `{DS}.in_territories`"):
    d = dict(r); gj = d.pop("gj"); d.pop("geog", None); d["layer"] = "territory"
    feats.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
with gzip.open(os.path.join(REPO, "data", "territories.geojson.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump({"type": "FeatureCollection", "features": feats}, f, separators=(",", ":"), default=jd)
print(f"territories.geojson.gz: {len(feats)}")

# correct the attrs record + remove the all-null export
client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES ('in_parcel_attrs','energy.mat_parcel_attrs x in_sites','CORRECTION',
          (SELECT COUNT(*) FROM `{DS}.in_parcel_attrs`), 0,
          CURRENT_TIMESTAMP(),
          'DEFECT: the IN slice of mat_parcel_attrs is 100 pct NULL on owner/zoning/land_use/year_built/assessed_value (all 3,553,381 rows) - upstream build gap, question filed with operator; keys join at 95.2 pct so the wiring is ready when values land')""").result()
attrs_dir = os.path.join(REPO, "data", "attrs")
if os.path.isdir(attrs_dir):
    shutil.rmtree(attrs_dir)
    print("data/attrs removed (all-null payload not shipped)")

# refresh provenance to the full current registry
p = os.path.join(REPO, "data", "state_summary.json")
with open(p, encoding="utf-8") as f: summary = json.load(f)
summary["provenance"] = [dict(r) for r in client.query(
    f"""SELECT table_name, source, n_rows, CAST(built_at AS STRING) AS built_at FROM `{DS}._registry`
        QUALIFY ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY built_at DESC)=1 ORDER BY table_name""")]
summary["built_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
with open(p, "w", encoding="utf-8") as f: json.dump(summary, f, indent=1, default=jd)
print(f"provenance: {len(summary['provenance'])} tables")
print("TERRITORIES COMPLETE")
