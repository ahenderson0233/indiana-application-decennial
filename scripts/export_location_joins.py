"""Surface the 12 location-join views in the app.

Two jobs:
  1. Every view gets a FEATURE — the operator's rule applies to views as well as tables. The Data
     page gains a card listing each view, what it joins, and its MEASURED yield, so the enrichment
     is auditable rather than asserted.
  2. The joins that add something a user can act on are pushed into the surfaces that use them:
     · GHGRP emitters on the map gain their actual CO2e — the layer previously showed only a pin
     · MISO 300 MW headroom gains publisher coordinates, so it can be read per POI on Grid
     · NFIRS incidents gain their street address on SI Feed

Read-only. Writes data/joins.json.gz and extends data/context.geojson.gz's ghgrp features.
"""
import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)
def rows(sql): return [dict(r) for r in client.query(sql)]

out = {}

# ---- 1. the join register itself, straight from _registry so it cannot drift ----
out["joins"] = rows(f"""
  SELECT table_name, source, method, n_rows, notes
  FROM (SELECT table_name, ANY_VALUE(source) source, ANY_VALUE(method) method,
               ANY_VALUE(n_rows) n_rows, ANY_VALUE(notes) notes
        FROM `{DS}._registry` WHERE STARTS_WITH(table_name, 'vw_') GROUP BY table_name)
  ORDER BY table_name""")

# ---- 2. GHGRP emitters: the map showed a pin with no emissions on it ----
out["ghgrp"] = rows(f"""
  SELECT facility_name, city, county, lat, lon,
         MAX(year) latest_year,
         ROUND(SUM(IF(year = (SELECT MAX(year) FROM `{DS}.vw_ghgrp_emissions_located`),
                      co2e_emission, 0))) co2e_latest
  FROM `{DS}.vw_ghgrp_emissions_located`
  WHERE lat IS NOT NULL AND facility_name IS NOT NULL
  GROUP BY facility_name, city, county, lat, lon
  HAVING co2e_latest > 0 ORDER BY co2e_latest DESC""")

# ---- 3. MISO 300MW headroom with publisher coordinates ----
out["headroom300"] = rows(f"""
  SELECT poi_name, bus_number, bus_name, kv, lat, lon,
         ROUND(headroom300_mw,1) headroom_mw, ROUND(headroom300_dfax5_mw,1) headroom_dfax5_mw,
         facilities_300, binding_300
  FROM `{DS}.vw_bus_headroom_300_located`
  WHERE lat IS NOT NULL ORDER BY headroom300_mw DESC""")

# ---- 4. NFIRS at address grain, most recent vintage held ----
out["nfirs_addr"] = rows(f"""
  SELECT CAST(SAFE.PARSE_DATE('%m%d%Y', INC_DATE) AS STRING) d, INC_TYPE inc_type,
         street_address, CITY city, ZIP5 zip
  FROM `{DS}.vw_nfirs_2024_located`
  WHERE STATE='IN' AND street_address IS NOT NULL AND TRIM(street_address) != ''
  ORDER BY INC_DATE DESC LIMIT 200""")

p = os.path.join(REPO, "data", "joins.json.gz")
with gzip.open(p, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(out, f, separators=(",", ":"), default=jd)
print(f"joins.json.gz {os.path.getsize(p)/1024:.0f} KB · " +
      " · ".join(f"{k} {len(v)}" for k, v in out.items()))

# ---- 5. put the emissions ONTO the map's existing ghgrp features ----
gp = os.path.join(REPO, "data", "context.geojson.gz")
fc = json.loads(gzip.decompress(open(gp, "rb").read()).decode())
emis = {(round(float(r["lat"]), 5), round(float(r["lon"]), 5)): r for r in out["ghgrp"]}
hit = 0
for ft in fc["features"]:
    if ft["properties"].get("layer") != "ghgrp": continue
    lon, lat = ft["geometry"]["coordinates"]
    m = emis.get((round(lat, 5), round(lon, 5)))
    if m:
        ft["properties"]["co2e_latest"] = m["co2e_latest"]
        ft["properties"]["co2e_year"] = m["latest_year"]
        hit += 1
with gzip.open(gp, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(fc, f, separators=(",", ":"), default=jd)
print(f"context.geojson.gz: emissions attached to {hit} of "
      f"{sum(1 for x in fc['features'] if x['properties'].get('layer')=='ghgrp')} ghgrp pins")
