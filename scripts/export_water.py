"""Export the water payload: watershed boundaries, stress basins, and per-county water context.

WHAT SHIPS, and what deliberately does not.

  data/water.geojson.gz   76 HUC8 watershed polygons + 34 water-stress basin polygons
  data/water.json.gz      per-county water context + the per-watershed surface-water inventory

⛔ RIVERS AND LAKES ARE NOT IN THIS PAYLOAD, and that is a data fact rather than a choice.
`energy.nhd_flowline` and `energy.nhd_waterbody` carry a `SHAPE:GEOGRAPHY` column that is **NULL on
every one of their 50M rows, nationally** - they hold attributes with no geometry. So Indiana's
2,415,369 flowlines and 186,667 waterbodies can be COUNTED per watershed but cannot be DRAWN.
Shipping a "rivers" layer built from anything else would be inventing a line that is not in our data.
What we can honestly show is: which watershed a parcel sits in, how contested its water is, and how
many named rivers / reservoirs / lakes that watershed contains.

WHY WATERSHEDS AT ALL, when the user asked about water?
A watershed is the unit water is actually allocated and argued over in. Two parcels a mile apart in
different subbasins can face different objections, different low-flow constraints and different
permitting bodies. It is the honest grain for "how hard will water be here" - and, unlike the
basins, it is a boundary a reader recognises from the map.

READS indiana_app ONLY.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")


def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    if isinstance(o, decimal.Decimal):
        return float(o)
    return str(o)


def rc(x):
    if isinstance(x, float):
        return round(x, 5)
    if isinstance(x, list):
        return [rc(v) for v in x]
    return x


feats = []

# ---- watersheds, with their surface-water inventory computed FROM ATTRIBUTES ----
# The inventory is the point: no geometry is needed to count what a watershed contains, because
# reachcode's first 8 digits ARE the HUC8 and it is populated on all 2,415,369 Indiana flowlines.
# ⛔ READS indiana_app ONLY. The checkpoint caught an earlier version of this file querying
# energy.nhd_* directly: a BUILD script may read energy, an EXPORT may not, or the app cannot be
# rebuilt without the platform dataset. The per-watershed inventory is now the registered clip
# `in_watershed_inventory`.
for r in client.query(f"""
SELECT i.huc8, i.name, i.states, ROUND(i.area_sqkm) AS area_sqkm,
       i.river_segments, i.named_rivers, i.reservoirs, i.lakes_over_10ha,
       i.largest_waterbody_sqkm,
       -- simplified to ~120 m: watershed edges are administrative boundaries, not measurements,
       -- and at state zoom the full-resolution vertices cost 14 MB and show nothing.
       ST_ASGEOJSON(ST_SIMPLIFY(b.geog, 120)) AS gj
FROM `{DS}.in_watershed_inventory` i
JOIN `{DS}.in_huc8_boundaries` b USING (huc8)
WHERE b.geog IS NOT NULL"""):
    d = dict(r)
    gj = d.pop("gj")
    d["layer"] = "watershed"
    feats.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
n_ws = len(feats)

# ---- water-stress basins (WRI Aqueduct), kept at BASIN grain ----
for r in client.query(f"""
  SELECT basin_id, stress_score, stress_label, depletion_score, depletion_label,
         groundwater_decline_score, groundwater_decline_label,
         ST_ASGEOJSON(ST_SIMPLIFY(geog, 120)) AS gj
  FROM `{DS}.in_water_stress_basin_geo`"""):
    d = dict(r)
    gj = d.pop("gj")
    if not gj:
        continue
    d["layer"] = "stress_basin"
    feats.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
n_basin = len(feats) - n_ws

out_geo = os.path.join(REPO, "data", "water.geojson.gz")
with gzip.open(out_geo, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump({"type": "FeatureCollection", "features": feats}, f,
              separators=(",", ":"), default=jd)

# ---- per-county context ----
counties = [dict(r) for r in client.query(f"""
  SELECT county_fips, county_name, use_year, total_withdrawal_mgd, total_ground_mgd,
         total_surface_mgd, ground_share, public_supply_mgd, industrial_mgd, thermoelectric_mgd,
         treatment_facilities, existing_flow_mgd, design_flow_mgd, wastewater_headroom_mgd,
         industrial_flow_mgd, npdes_permits, npdes_design_flow_mgd, npdes_largest_permit_mgd,
         drought_annual_frequency, drought_hazard_rating
  FROM `{DS}.in_water_county` ORDER BY county_name""")]

payload = {
    "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "counties": counties,
    "notes": {
        "units": "All withdrawal and flow figures are Mgal/d (million gallons per day). A "
                 "hyperscale data centre with evaporative cooling runs roughly 1-5 Mgal/d.",
        "use_vintage": "USGS county water use is 2015, the most recent full national compilation. "
                       "It is context, not a current measurement.",
        "no_rivers": "Rivers and lakes are NOT drawn. The national hydrography tables hold "
                     "attributes with NO geometry on any of their 50M rows, so watercourses can be "
                     "counted per watershed but cannot be mapped.",
        "wastewater_headroom": "Design flow minus existing flow at the treatment works. NULL where "
                               "either side is unpublished - never read a NULL as unlimited.",
    },
}
out_json = os.path.join(REPO, "data", "water.json.gz")
with gzip.open(out_json, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(payload, f, separators=(",", ":"), default=jd)

print(f"water.geojson.gz : {n_ws} watersheds + {n_basin} stress basins "
      f"({os.path.getsize(out_geo):,} bytes)")
print(f"water.json.gz    : {len(counties)} counties ({os.path.getsize(out_json):,} bytes)")
print("WATER EXPORT COMPLETE - rivers/lakes deliberately absent, see the module docstring")
