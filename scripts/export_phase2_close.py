"""Phase-2 close: logistics layer (rail/roads), RTEP upgrade drill-down into pipeline.json,
gas-OAC summary into market.json."""
import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)
def rc(x):
    if isinstance(x, float): return round(x, 6)
    if isinstance(x, list): return [rc(v) for v in x]
    return x

# logistics: rail + primary/secondary roads
feats = []
for tbl, layer in [("in_railroads", "rail"), ("in_roads_primary", "road1"), ("in_roads_secondary", "road2")]:
    t = client.get_table(f"{DS}.{tbl}")
    cols = [s.name for s in t.schema]
    gg = next((c for c in cols if c.lower() in ("geog", "geom", "_g")), None)
    gj = next((c for c in cols if "geojson" in c.lower()), None)
    geo = gg if gg else f"SAFE.ST_GEOGFROMGEOJSON({gj})"
    keep = [c for c in cols if any(k in c.lower() for k in ("name", "fullname", "rttyp", "owner", "net"))][:4]
    sel = (", ".join(keep) + ", " if keep else "") + f"ST_ASGEOJSON({geo}) AS _gj"
    n = 0
    for r in client.query(f"SELECT {sel} FROM `{DS}.{tbl}` WHERE {geo} IS NOT NULL"):
        d = dict(r); g = d.pop("_gj"); d["layer"] = layer
        feats.append({"type": "Feature", "properties": {k: (None if v is None else str(v)) for k, v in d.items()},
                      "geometry": rc(json.loads(g))})
        n += 1
    print(f"{tbl}: {n}")
with gzip.open(os.path.join(REPO, "data", "logistics.geojson.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump({"type": "FeatureCollection", "features": feats}, f, separators=(",", ":"), default=jd)
print(f"logistics.geojson.gz: {len(feats)}")

# RTEP drill-down + cost allocations into pipeline.json
with gzip.open(os.path.join(REPO, "data", "pipeline.json.gz"), "rt", encoding="utf-8") as f:
    pl = json.load(f)
def rows(sql, cap=None):
    out = []
    for r in client.query(sql):
        out.append({k: (None if v is None else (float(v) if isinstance(v, decimal.Decimal) else str(v)))
                    for k, v in dict(r).items() if v is not None})
        if cap and len(out) >= cap: break
    return out
pl["rtep_details"] = rows(f"SELECT * FROM `{DS}.in_pjm_rtep_upgrade_details`")
pl["rtep_cost_allocations"] = rows(f"SELECT * FROM `{DS}.in_pjm_rtep_cost_allocations`")
with gzip.open(os.path.join(REPO, "data", "pipeline.json.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(pl, f, separators=(",", ":"), default=jd)
print(f"pipeline: +{len(pl['rtep_details'])} details, +{len(pl['rtep_cost_allocations'])} allocations")

# gas OAC summary into market.json (registry-driven + IN-county counts for the two county-keyed pipes)
with gzip.open(os.path.join(REPO, "data", "market.json.gz"), "rt", encoding="utf-8") as f:
    m = json.load(f)
oac = [dict(r) for r in client.query(f"""
  SELECT REPLACE(table_name,'in_gas_capacity_','') AS pipeline, n_rows,
         CAST(built_at AS STRING) AS pulled
  FROM `{DS}._registry` WHERE table_name LIKE 'in_gas_capacity_%'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY built_at DESC)=1 ORDER BY n_rows DESC""")]
for p, tbl in [("panhandle_eastern", "in_gas_capacity_panhandle_eastern"), ("trunkline", "in_gas_capacity_trunkline")]:
    try:
        cols = [s.name for s in client.get_table(f"{DS}.{tbl}").schema]
        sc = next((c for c in cols if c.lower() == "state"), None)
        cc = next((c for c in cols if "county" in c.lower()), None)
        if sc and cc:
            r = list(client.query(f"""SELECT COUNT(*) n, COUNT(DISTINCT `{cc}`) counties
                FROM `{DS}.{tbl}` WHERE UPPER(TRIM(CAST(`{sc}` AS STRING)))='IN'"""))[0]
            for o in oac:
                if o["pipeline"] == p:
                    o["indiana_locations"] = r.n; o["indiana_counties"] = r.counties
    except Exception as ex:
        print(f"{p}: {str(ex)[:80]}")
m["gas_oac"] = oac
with gzip.open(os.path.join(REPO, "data", "market.json.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(m, f, separators=(",", ":"), default=jd)
print(f"gas_oac pipelines: {len(oac)}")
print("PHASE2 CLOSE EXPORT COMPLETE")
