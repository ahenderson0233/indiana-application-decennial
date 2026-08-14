"""Export grid + sentiment artifacts for the console presets.

data/grid.geojson.gz      substations + transmission lines + MISO bus POIs (typed via props.layer)
data/county_context.json  per-county: DC posture, queue rollup, grid-plan counts, receipt counts
data/receipts.json.gz     every P5 receipt row (dockets, news, actions, ordinances), county-tagged
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

feats = []
# substations (points from lat/lon published by HIFLD/OSM)
for r in client.query(f"""
  SELECT substation_name, max_kv, min_kv, county, status, substation_type, line_count,
         operator, lat, lon
  FROM `{DS}.in_substations` WHERE lat IS NOT NULL AND lon IS NOT NULL"""):
    d = dict(r); lat, lon = d.pop("lat"), d.pop("lon")
    d["layer"] = "substation"
    feats.append({"type": "Feature", "properties": d,
                  "geometry": {"type": "Point", "coordinates": [rc(float(lon)), rc(float(lat))]}})
# transmission lines
for r in client.query(f"""
  SELECT owner, voltage, volt_class, status, sub_1, sub_2, ST_ASGEOJSON(geom) AS gj
  FROM `{DS}.in_transmission_lines` WHERE geom IS NOT NULL"""):
    d = dict(r); gj = d.pop("gj")
    d["layer"] = "line"
    feats.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
# MISO bus POIs (publisher coordinates only)
for r in client.query(f"""
  SELECT poi_name, bus_number, bus_name, kv, area_name, worst_mw, best_mw, median_mw,
         facilities_at_zero, monitored_facilities, worst_binding_facility, vintage, lat, lon
  FROM `{DS}.in_bus_headroom_miso` WHERE location_status='indiana'"""):
    d = dict(r); lat, lon = d.pop("lat"), d.pop("lon")
    d["layer"] = "bus_poi"
    feats.append({"type": "Feature", "properties": d,
                  "geometry": {"type": "Point", "coordinates": [rc(float(lon)), rc(float(lat))]}})
with gzip.open(os.path.join(REPO, "data", "grid.geojson.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump({"type": "FeatureCollection", "features": feats}, f, separators=(",", ":"), default=jd)
print(f"grid.geojson.gz: {len(feats)} features")

# county context: posture + queue + grid plans + receipts counts
ctx = {}
for r in client.query(f"""
  SELECT county_geoid, county_name, posture, opposition_intensity, has_local_restriction,
         local_moratoriums, local_bans, opp_actions, news_articles, news_avg_tone
  FROM {E}.vw_county_dc_posture` WHERE state_abbr='IN'"""):
    d = dict(r); ctx[d.pop("county_geoid")] = {"posture": d}
for r in client.query(f"SELECT geoid, projects, active_projects, active_mw, withdrawn_projects, total_mw FROM `{DS}.in_queue_counties`"):
    d = dict(r); g = d.pop("geoid")
    if g in ctx: ctx[g]["queue"] = d
# grid plans are county-NAME keyed (agent schema); emit a name-keyed dict for the app
gp = {}
for r in client.query(f"""
  SELECT UPPER(IFNULL(county,'(UNLOCATED)')) AS county_name, COUNT(*) AS n,
         COUNTIF(row_type='project') AS projects
  FROM `{DS}.in_grid_plans` GROUP BY 1"""):
    gp[r.county_name] = {"rows": r.n, "projects": r.projects}
with open(os.path.join(REPO, "data", "county_context.json"), "w", encoding="utf-8") as f:
    json.dump({"by_fips": ctx, "grid_plans_by_county_name": gp}, f, separators=(",", ":"), default=jd)
print(f"county_context.json: {len(ctx)} counties, {len(gp)} grid-plan county names")

# receipts: one gz file, county-NAME-tagged rows from all four P5 tables (types unified as STRING)
rec = []
for r in client.query(f"""
  SELECT 'iurc_docket' AS kind, CAST(NULL AS STRING) AS county, docket_number AS title,
         CONCAT(IFNULL(petition_type,''), ' - ', IFNULL(status,'')) AS detail,
         CAST(filed_date AS STRING) AS observed_date, url, matched_terms AS tags
  FROM `{DS}.in_iurc_dockets`
  UNION ALL SELECT 'news', query_county, title, source,
         CAST(published AS STRING), link, query FROM `{DS}.in_news_dc`
  UNION ALL SELECT 'dc_action', county, IFNULL(evidence_title, jurisdiction),
         CONCAT(IFNULL(action,''), IFNULL(CONCAT(' - ', company),'')),
         CAST(action_date AS STRING), source_url, CAST(already_held AS STRING)
  FROM `{DS}.in_dc_actions`
  UNION ALL SELECT 'ordinance', county, CONCAT(jurisdiction, ': ', IFNULL(section_title,'')),
         snippet, CAST(observed_date AS STRING), url, search_phrase
  FROM `{DS}.in_ordinances_dc`"""):
    rec.append(dict(r))
with gzip.open(os.path.join(REPO, "data", "receipts.json.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(rec, f, separators=(",", ":"), default=jd)
print(f"receipts.json.gz: {len(rec)} rows")
print("GRID+SENTIMENT EXPORT COMPLETE")
