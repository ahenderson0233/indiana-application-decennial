"""Export everything remaining into the site:
  data/overlays.geojson.gz   PAD-US protected land + bonus-credit geographies (P4)
  data/pjm.geojson.gz        PJM bus-location candidates (estimates!) + PJM queue points
  data/pipeline.json.gz      grid plans (TDSIC), RTO expansion, queue projects, NUCRA costs
  data/county_context.json   now with fibre / flood / wetlands county stats merged
  data/state_summary.json    provenance refreshed from _registry (every table)
"""
import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
E = "`energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")

def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)
def rc(x):
    if isinstance(x, float): return round(x, 6)
    if isinstance(x, list): return [rc(v) for v in x]
    return x
def gzwrite(name, obj):
    with gzip.open(os.path.join(REPO, "data", name), "wt", encoding="utf-8", compresslevel=6) as f:
        json.dump(obj, f, separators=(",", ":"), default=jd)

# ---- overlays: padus + bonus geographies ----
feats = []
for r in client.query(f"""SELECT Unit_Nm AS name, Des_Tp AS designation, Own_Type AS owner_type,
    Mang_Name AS manager, GIS_Acres AS acres, ST_ASGEOJSON(geog) AS gj
    FROM `{DS}.in_padus` WHERE geog IS NOT NULL"""):
    d = dict(r); gj = d.pop("gj"); d["layer"] = "padus"
    feats.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
for r in client.query(f"""SELECT kind, key, attrs_json, ST_ASGEOJSON(geog) AS gj
    FROM `{DS}.in_bonus_geo` WHERE geog IS NOT NULL"""):
    d = dict(r); gj = d.pop("gj"); d["layer"] = "bonus"
    feats.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
gzwrite("overlays.geojson.gz", {"type": "FeatureCollection", "features": feats})
print(f"overlays: {len(feats)}")

# ---- pjm: bus candidates (ESTIMATES) + queue points (schema read dynamically) ----
feats = []
for r in client.query(f"""SELECT bus_number, bus_label, bus_kv, location_method, match_confidence,
    matched_substation_name, kv_consistent, collision_count, lat, lon
    FROM `{DS}.in_pjm_bus_locations_candidate` WHERE lat IS NOT NULL AND lon IS NOT NULL"""):
    d = dict(r); la, lo = d.pop("lat"), d.pop("lon"); d["layer"] = "bus_candidate"
    feats.append({"type": "Feature", "properties": d,
                  "geometry": {"type": "Point", "coordinates": [rc(float(lo)), rc(float(la))]}})
t = client.get_table(f"{DS}.in_pjm_gis_queues")
cols = [s.name for s in t.schema]
geogcol = next((c for c in cols if c.lower() in ("geog", "geom", "geometry")), None)
latc = next((c for c in cols if "lat" in c.lower()), None)
lonc = next((c for c in cols if "lon" in c.lower() or "lng" in c.lower()), None)
keep = [c for c in cols if c not in (geogcol, latc, lonc)][:12]
if geogcol:
    q = f"SELECT {', '.join(keep)}, ST_ASGEOJSON({geogcol}) AS gj FROM `{DS}.in_pjm_gis_queues` WHERE {geogcol} IS NOT NULL"
    for r in client.query(q):
        d = dict(r); gj = d.pop("gj"); d["layer"] = "queue_point"
        feats.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
elif latc and lonc:
    q = f"SELECT {', '.join(keep)}, {latc} AS la, {lonc} AS lo FROM `{DS}.in_pjm_gis_queues` WHERE {latc} IS NOT NULL"
    for r in client.query(q):
        d = dict(r); la, lo = d.pop("la"), d.pop("lo"); d["layer"] = "queue_point"
        feats.append({"type": "Feature", "properties": d,
                      "geometry": {"type": "Point", "coordinates": [rc(float(lo)), rc(float(la))]}})
gzwrite("pjm.geojson.gz", {"type": "FeatureCollection", "features": feats})
print(f"pjm: {len(feats)}")

# ---- pipeline: grid plans, rto expansion, queue projects, nucra ----
def rows(sql, drop=()):
    out = []
    for r in client.query(sql):
        d = {k: v for k, v in dict(r).items() if k not in drop and v is not None}
        out.append(d)
    return out
pipeline = {
    "grid_plans": rows(f"""SELECT utility, row_type, project_name, project_type, location_text,
        substation_names, county, voltage_kv, in_service_year, cost_usd_m, docket_number,
        document_url, filed_date, location_status FROM `{DS}.in_grid_plans`
        ORDER BY utility, in_service_year"""),
    "rto_expansion": rows(f"SELECT * FROM `{DS}.in_rto_expansion`", drop=("raw_row",)),
    "queue_projects": rows(f"""SELECT project_name, county, status, capacity_mw, resource_type,
        queue_date, wd_date, on_date, utility, entity FROM `{DS}.in_queue` ORDER BY county"""),
    "nucra_costs": rows(f"SELECT * FROM `{DS}.in_pjm_nucra_costs`"),
}
gzwrite("pipeline.json.gz", pipeline)
print("pipeline:", {k: len(v) for k, v in pipeline.items()})

# ---- county_context: merge gate stats ----
with open(os.path.join(REPO, "data", "county_context.json"), encoding="utf-8") as f:
    ctx = json.load(f)
for tbl, key in [("in_county_fibre", "fibre"), ("in_county_flood", "flood"), ("in_county_wetlands", "wetlands")]:
    try:
        for r in client.query(f"SELECT * FROM `{DS}.{tbl}`"):
            d = dict(r); fips = d.pop("county_fips")
            if fips in ctx["by_fips"]: ctx["by_fips"][fips][key] = d
    except Exception as ex:
        print(f"skip {tbl}: {ex}")
with open(os.path.join(REPO, "data", "county_context.json"), "w", encoding="utf-8") as f:
    json.dump(ctx, f, separators=(",", ":"), default=jd)
print("county_context merged")

# ---- refresh provenance in state_summary ----
p = os.path.join(REPO, "data", "state_summary.json")
with open(p, encoding="utf-8") as f: summary = json.load(f)
summary["provenance"] = [dict(r) for r in client.query(
    f"""SELECT table_name, source, n_rows, CAST(built_at AS STRING) AS built_at FROM `{DS}._registry`
        QUALIFY ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY built_at DESC)=1 ORDER BY table_name""")]
summary["built_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
with open(p, "w", encoding="utf-8") as f: json.dump(summary, f, indent=1, default=jd)
print(f"provenance: {len(summary['provenance'])} tables")
print("FULL WIRING EXPORT COMPLETE")
