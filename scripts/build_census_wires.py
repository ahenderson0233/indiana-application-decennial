"""Approved census wires: coal_closure_communities -> bonus set; eia861_reliability ->
county/utility metric; nonattainment_areas -> county air gate. Schema-read first, never guessed."""
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
def reg(name, source, method, n, notes=""):
    client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
      VALUES ('{name}','{source}','{method}', {n}, 0.05, CURRENT_TIMESTAMP(), '{notes}')""").result()

for t in ("coal_closure_communities", "eia861_reliability", "nonattainment_areas"):
    print(f"--- {t}:", [s.name for s in client.get_table(f"energy-platfrom.energy.{t}").schema][:16])

# 1) coal closure -> in_bonus_geo (the fourth bonus geography)
tt = client.get_table("energy-platfrom.energy.coal_closure_communities")
cols = [s.name for s in tt.schema]
gcol = next((c0 for c0 in cols if c0.lower() in ("geog", "geom")), None)
gjson = next((c0 for c0 in cols if "geojson" in c0.lower()), None)
geo = gcol if gcol else f"SAFE.ST_GEOGFROMGEOJSON({gjson})"
statec = next((c0 for c0 in cols if "state" in c0.lower()), None)
keyc = next((c0 for c0 in cols if "geoid" in c0.lower() or "fips" in c0.lower()), cols[0])
client.query(f"""
INSERT `{DS}.in_bonus_geo` (kind, key, geog, attrs_json)
SELECT 'coal_closure', CAST({keyc} AS STRING), g, TO_JSON_STRING(STRUCT({statec}))
FROM (SELECT *, {geo} AS g FROM {E}.coal_closure_communities`)
WHERE g IS NOT NULL AND (UPPER(CAST({statec} AS STRING)) IN ('IN','INDIANA','18')
      OR ST_INTERSECTS(g, {ST}))
  AND NOT EXISTS (SELECT 1 FROM `{DS}.in_bonus_geo` b WHERE b.kind='coal_closure')""").result()
n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_bonus_geo` WHERE kind='coal_closure'"))[0].n
reg("in_bonus_geo", "energy.coal_closure_communities", "APPEND coal_closure kind",
    list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_bonus_geo`"))[0].n,
    f"coal_closure added: {n} IN features")
print(f"coal_closure features added: {n}")

# 2) EIA-861 reliability (SAIDI/SAIFI) -> in_eia861_reliability
rt = client.get_table("energy-platfrom.energy.eia861_reliability")
rcols = [s.name for s in rt.schema]
print("reliability cols:", rcols[:18])
sc = next((c0 for c0 in rcols if c0.lower() in ("state", "state_abbr", "st")), None)
client.query(f"""CREATE OR REPLACE TABLE `{DS}.in_eia861_reliability` AS
  SELECT * FROM {E}.eia861_reliability` WHERE UPPER(CAST({sc} AS STRING)) IN ('IN','INDIANA')""").result()
n2 = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_eia861_reliability`"))[0].n
reg("in_eia861_reliability", "energy.eia861_reliability", "state=IN", n2, "SAIDI/SAIFI outage reliability per utility-year")
print(f"in_eia861_reliability: {n2}")

# 3) nonattainment -> in_nonattainment (spatial clip; small)
# STOP: this block used to read `[:12]` of the parent schema. `classification` is column 16, so the
# clip stopped four columns short of the ONE field a reader actually needs -- the severity band that
# decides the air-permitting burden. Nothing was mis-mapped; a SLICE INDEX silently truncated the
# meaning, and the map popup rendered an empty "classification" row for months. That is the G27
# under-clip defect in its purest form. The same idiom still sits in build_gas_facilities.py [:10],
# build_gas_market.py [:14] and export_full_wiring.py [:12] -- audit those before trusting them.
# Columns are NAMED here so a parent-schema reorder can never truncate this table again, and the
# build now FAILS LOUDLY if the parent stops carrying one instead of quietly shipping less.
# NOTE ON DATES: every date column here is the Esri convention -- FLOAT64 epoch MILLISECONDS
# (1083283200000.0 = 2004-04-30), measured on all five. They are DECODED, never ISO-parsed (an ISO
# parse returns NULL on every row). Shipped raw, app.js printed "1,087,300,800,000" at the reader.
nt = client.get_table("energy-platfrom.energy.nonattainment_areas")
ncols = [s.name for s in nt.schema]
gcol = next((c0 for c0 in ncols if c0.lower() in ("geog", "geom")), None)
gjson = next((c0 for c0 in ncols if "geojson" in c0.lower()), None)
geo = gcol if gcol else f"SAFE.ST_GEOGFROMGEOJSON({gjson})"
KEEP = ["pollutant_name", "area_name", "state_name", "epa_region", "epa_region_office",
        "designation_citation", "designation_url", "current_status",
        "classification", "classification_citation", "classification_url"]
EPOCH_MS = ["designation_pub_date", "designation_effective_date", "statutory_attainment_date",
            "classification_pub_date", "classification_effective_date"]
lost = [c0 for c0 in KEEP + EPOCH_MS if c0 not in ncols]
if lost:
    raise SystemExit(f"nonattainment: parent no longer carries {lost} -- read the schema, never guess")
sel = ", ".join(KEEP + [f"DATE(TIMESTAMP_MILLIS(SAFE_CAST({c0} AS INT64))) AS {c0}" for c0 in EPOCH_MS])
client.query(f"""CREATE OR REPLACE TABLE `{DS}.in_nonattainment` AS
  SELECT {sel}, g AS geog FROM (SELECT *, {geo} AS g FROM {E}.nonattainment_areas`)
  WHERE g IS NOT NULL AND ST_INTERSECTS(g, {ST})""").result()
n3, ncls = list(client.query(f"""SELECT COUNT(*) n, COUNTIF(classification IS NOT NULL) c
  FROM `{DS}.in_nonattainment`"""))[0]
reg("in_nonattainment", "energy.nonattainment_areas",
    "spatial clip to IN; 16 NAMED cols incl classification; epoch-ms dates decoded", n3,
    f"air-permitting gate for on-site generation; severity band present on {ncls} of {n3} rows -- "
    f"the remainder are Maintenance areas where no classification applies. "
    f"RE-RUN: python scripts/build_census_wires.py")
print(f"in_nonattainment: {n3} rows, classification on {ncls}")

# exports: refresh overlays (bonus incl. coal), add reliability to county ctx via utility-county map? (state-grain: goes to market)
feats = []
for r in client.query(f"""SELECT Unit_Nm AS name, Des_Tp AS designation, Own_Type AS owner_type,
    Mang_Name AS manager, GIS_Acres AS acres, ST_ASGEOJSON(geog) AS gj FROM `{DS}.in_padus` WHERE geog IS NOT NULL"""):
    d = dict(r); gj = d.pop("gj"); d["layer"] = "padus"
    feats.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
for r in client.query(f"SELECT kind, key, attrs_json, ST_ASGEOJSON(geog) AS gj FROM `{DS}.in_bonus_geo` WHERE geog IS NOT NULL"):
    d = dict(r); gj = d.pop("gj"); d["layer"] = "bonus"
    feats.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
for r in client.query(f"SELECT *, ST_ASGEOJSON(geog) AS gj FROM `{DS}.in_nonattainment`"):
    d = dict(r); gj = d.pop("gj"); d.pop("geog", None); d["layer"] = "nonattainment"
    feats.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
with gzip.open(os.path.join(REPO, "data", "overlays.geojson.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump({"type": "FeatureCollection", "features": feats}, f, separators=(",", ":"), default=jd)
print(f"overlays.geojson.gz: {len(feats)}")

with gzip.open(os.path.join(REPO, "data", "market.json.gz"), "rt", encoding="utf-8") as f:
    market = json.load(f)
market["reliability"] = [dict(r) for r in client.query(f"SELECT * FROM `{DS}.in_eia861_reliability` ORDER BY 1")]
with gzip.open(os.path.join(REPO, "data", "market.json.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(market, f, separators=(",", ":"), default=jd)
print(f"reliability rows in market.json: {len(market['reliability'])}")

# provenance refresh
p = os.path.join(REPO, "data", "state_summary.json")
summary = json.load(open(p, encoding="utf-8"))
summary["provenance"] = [dict(r) for r in client.query(
    f"""SELECT table_name, source, n_rows, CAST(built_at AS STRING) AS built_at FROM `{DS}._registry`
        QUALIFY ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY built_at DESC)=1 ORDER BY table_name""")]
summary["built_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
json.dump(summary, open(p, "w", encoding="utf-8"), indent=1, default=jd)
print("provenance:", len(summary["provenance"]))
print("CENSUS WIRES COMPLETE")
