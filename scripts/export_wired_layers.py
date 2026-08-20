"""G72 / G80 / G97 / G98 - export the objects that reached NO surface, as surfaces.

    python scripts/export_wired_layers.py

Writes:
  data/wired.geojson.gz        four new map layers (see below)
  data/county_context.json     eight county-grain objects merged in (in_county_context_extras)
  data/wired.json.gz           the non-spatial additions: WARN closures, grid upgrade costs,
                               implied industrial power price, 300 MW headroom

⭐ EVERY LAYER HERE HAS TO EARN ITS "SO WHAT" (the governing principle is a veto, not a polish
step). What each one changes about a decision, in the reader's units:

  WATER GEOMETRY (in_nhd_waterbody_geom 7,430 · in_nhd_flowline_geom 163,976)
    A 100 MW evaporative-cooled campus consumes roughly 1-2 million gallons a day of make-up
    water. The question is not "is there water nearby" but "is there a body big enough to permit
    an intake against". Named rivers and bodies over 12 acres ship; a farm pond does not, because
    drawing it would answer the question wrongly in the reassuring direction.
    ⚠ 163,976 flowlines cannot ship - 7,202 that are NAMED and at least 1 km long do. An unnamed
    500 m ditch is not an intake.

  FAA OBSTACLES (in_faa_obstacles 15,638)
    ⭐ The useful half is not the airspace: 1,816 of them are WINDMILLS. An existing turbine is
    proof that this specific ground already cleared landowner consent, an interconnection and a
    local permit. That is a siting signal, not scenery. The other half is real too - 4,591
    structures stand 200 ft or more above ground, and a site inside an approach path with tall
    obstacles already studied is a very different FAA conversation from one with none.
    ⚠ `type` is SPACE-PADDED ('TOWER             ') - another value vocabulary that lies.

  FEDERAL SURPLUS (in_si_gov_surplus_v2)
    ⛔ AND THIS ONE CORRECTS A SHIPPED LABEL. The map already had a checkbox reading "Federal
    surplus property" drawing 1,594 points, of which 1,540 are `Current Mission Need`. The layer
    was named for something true of 17 of its points. It is now split: the property layer keeps
    every point and says what each one IS, and the 20 that are genuinely declared surplus or
    unutilised become their own OWNER-MOTIVATION signal, which is where G97 says they belong.

  WITHDRAWN QUEUE (in_si_queue_withdrawn)
    A landowner who signed an interconnection agreement already consented to host energy
    infrastructure and now has a studied grid position with no project on it. 195 of them carry a
    published coordinate. ⚠ The point is the INTERCONNECTION point, not the generator parcel.

⛔ EXPORTS MAY NOT READ `energy`. Everything here reads indiana_app.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = (r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California"
        r"\ca-capacity-deploy\indiana-application-decennial")
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
        return round(x, 6)
    if isinstance(x, list):
        return [rc(v) for v in x]
    return x


def gzwrite(name, obj):
    p = os.path.join(REPO, "data", name)
    with gzip.open(p, "wt", encoding="utf-8", compresslevel=6) as f:
        json.dump(obj, f, separators=(",", ":"), default=jd)
    return os.path.getsize(p)


feats = []

# ---- 1. water geometry -----------------------------------------------------------------------
# ⚠ ST_SIMPLIFY at 30 m. Below that the payload is unusable in a browser; above it, small ponds
#    collapse. 30 m is well under the width of anything we are shipping.
n_wb = 0
for r in client.query(f"""
  SELECT gnis_name AS name, ftype_label AS kind, water_role,
         ROUND(areasqkm, 3) AS sqkm, ROUND(areasqkm * 247.105, 1) AS acres,
         ST_ASGEOJSON(ST_SIMPLIFY(geog, 30)) AS gj
  FROM `{DS}.in_nhd_waterbody_geom`
  WHERE geog IS NOT NULL AND (areasqkm >= 0.05 OR gnis_name IS NOT NULL)"""):
    d = dict(r)
    gj = d.pop("gj")
    if not gj:
        continue
    d["layer"] = "waterbody"
    feats.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
    n_wb += 1

n_fl = 0
for r in client.query(f"""
  SELECT gnis_name AS name, ftype_label AS kind, ROUND(lengthkm, 2) AS km, huc8,
         ST_ASGEOJSON(ST_SIMPLIFY(geog, 60)) AS gj
  FROM `{DS}.in_nhd_flowline_geom`
  WHERE geog IS NOT NULL AND gnis_name IS NOT NULL AND lengthkm >= 1.0"""):
    d = dict(r)
    gj = d.pop("gj")
    if not gj:
        continue
    d["layer"] = "flowline"
    feats.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
    n_fl += 1
print(f"  water: {n_wb:,} bodies + {n_fl:,} named flowlines")

# ---- 2. FAA obstacles: NOT EXPORTED HERE, AND THAT IS THE POINT --------------------------------
# ⛔ The first version of this script shipped an obstacle layer. `gates.geojson.gz` ALREADY
#    carries all 4,590 of them behind the "Tall obstructions >=200 ft" checkbox, with a click
#    handler. Two copies of one layer is the §2.15c defect: they drift, and the loser is
#    invisible. The census listed in_faa_obstacles as unwired, which is what prompted the
#    duplicate - and that was an INSTRUMENT false negative, now fixed in audit_wiring_census.py.
# ⭐ The one thing the new draft had that the shipped layer lacked survived: 1,816 of the 4,590
#    are WINDMILLS, and a standing turbine is a siting SIGNAL, not an obstruction. app.js now
#    colours them green on the existing layer.
n_ob = 0
print("  obstacles: 0 exported here - already shipped in gates.geojson.gz (see the note above)")

# ---- 3. federal property, correctly classified -----------------------------------------------
n_fp = 0
for r in client.query(f"""
  SELECT agency, real_property_type AS ptype, real_property_use AS use, asset_status,
         utilization, surplus_class, is_si_signal, assets_at_point, city_name AS city,
         county_name AS county, years_underutilized,
         CAST(excess_date AS STRING) AS excess_date, acres, lat AS la, lon AS lo
  FROM `{DS}.in_si_gov_surplus_v2` WHERE lat IS NOT NULL"""):
    d = dict(r)
    la, lo = d.pop("la"), d.pop("lo")
    d["layer"] = "fedprop"
    feats.append({"type": "Feature", "properties": d,
                  "geometry": {"type": "Point", "coordinates": [rc(lo), rc(la)]}})
    n_fp += 1
print(f"  federal property: {n_fp:,}")

# ---- 4. withdrawn queue projects -------------------------------------------------------------
n_wq = 0
for r in client.query(f"""
  SELECT project_id, iso, poi_name, county_text AS county, ROUND(capacity_mw) AS mw,
         resource_type, counterparty, CAST(wd_date AS STRING) AS wd_date,
         years_since_withdrawal, placement_grain, location_method,
         parcel_key, parcel_acres, lat AS la, lon AS lo
  FROM `{DS}.in_si_queue_withdrawn` WHERE lat IS NOT NULL"""):
    d = dict(r)
    la, lo = d.pop("la"), d.pop("lo")
    d["layer"] = "withdrawn"
    feats.append({"type": "Feature", "properties": d,
                  "geometry": {"type": "Point", "coordinates": [rc(lo), rc(la)]}})
    n_wq += 1
print(f"  withdrawn queue: {n_wq:,}")

size = gzwrite("wired.geojson.gz", {"type": "FeatureCollection", "features": feats})
print(f"  data/wired.geojson.gz  {len(feats):,} features, {size:,} bytes")

# ---- 5. merge the county extras into county_context.json -------------------------------------
p = os.path.join(REPO, "data", "county_context.json")
with open(p, encoding="utf-8") as f:
    ctx = json.load(f)
merged = 0
for r in client.query(f"SELECT * FROM `{DS}.in_county_context_extras`"):
    d = {k: v for k, v in dict(r).items() if v is not None}
    fips = d.pop("county_fips", None)
    d.pop("built_at", None)
    d.pop("county_name", None)
    if fips in ctx["by_fips"]:
        ctx["by_fips"][fips]["extras"] = d
        merged += 1
with open(p, "w", encoding="utf-8") as f:
    json.dump(ctx, f, separators=(",", ":"), default=jd)
print(f"  county_context.json: extras merged into {merged} counties")

# ---- 6. the non-spatial additions ------------------------------------------------------------
def rows(sql):
    return [{k: v for k, v in dict(r).items() if v is not None} for r in client.query(sql)]


wired = {
    "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),

    # G90(a): the closures, which were being read as layoff data. in_si_warn_normalised held
    # 1,220 rows and reached no surface.
    "warn_summary": rows(f"""
        SELECT notice_class, COUNT(*) AS notices, SUM(affected_workers) AS workers,
               COUNTIF(vacates_site) AS vacating, COUNTIF(site_kind = 'industrial') AS industrial,
               COUNTIF(event_is_future) AS future_dated
        FROM `{DS}.in_si_warn_normalised` GROUP BY 1 ORDER BY notices DESC"""),
    # ⭐ a FUTURE-dated closure is the scarcest thing in the whole signal estate: a site that is
    #    known to be vacating on a known date.
    "warn_future": rows(f"""
        SELECT company, city, industry, notice_class, affected_workers,
               CAST(event_date AS STRING) AS event_date, event_date_precision, site_kind
        FROM `{DS}.in_si_warn_normalised`
        WHERE event_is_future ORDER BY event_date"""),
    "warn_recent_closures": rows(f"""
        SELECT company, city, industry, affected_workers,
               CAST(event_date AS STRING) AS event_date, site_kind, naics2
        FROM `{DS}.in_si_warn_normalised`
        WHERE vacates_site AND event_date IS NOT NULL
        ORDER BY event_date DESC LIMIT 60"""),
    "warn_precision": rows(f"""
        SELECT event_date_precision, COUNT(*) AS n
        FROM `{DS}.in_si_warn_normalised` GROUP BY 1 ORDER BY n DESC"""),

    # ⭐ WHAT AN INTERCONNECTION UPGRADE ACTUALLY COSTS. in_miso_dpp2025_ph1_project_costs held
    #    202 projects and $29.5bn of network upgrades and reached no surface. This is the single
    #    hardest number for a developer to estimate, and we had it and did not show it.
    "miso_upgrade_costs": rows(f"""
        SELECT fuel_type, service_type, COUNT(*) AS projects,
               ROUND(SUM(total_dpp_2025_phase_1_network_upgrade_cost) / 1e6, 1) AS cost_musd,
               ROUND(SUM(nris_mw)) AS nris_mw, ROUND(SUM(eris_mw)) AS eris_mw,
               ROUND(SAFE_DIVIDE(SUM(total_dpp_2025_phase_1_network_upgrade_cost),
                                 NULLIF(SUM(nris_mw), 0)) / 1000, 1) AS usd_k_per_nris_mw
        FROM `{DS}.in_miso_dpp2025_ph1_project_costs`
        GROUP BY 1, 2 ORDER BY cost_musd DESC"""),

    # in_bus_headroom_300 held 642 rows and reached no surface. tier0 answers at one request size;
    # this answers at 300 MW, which is a realistic hyperscale ask.
    "headroom_300": rows(f"""
        SELECT poi_name, ROUND(headroom300_mw) AS mw, ROUND(headroom300_dfax5_mw) AS mw_dfax5,
               facilities_300 AS facilities, binding_300 AS binding
        FROM `{DS}.in_bus_headroom_300`
        WHERE headroom300_mw IS NOT NULL ORDER BY headroom300_mw DESC LIMIT 250"""),

    # G97/G98 summaries for si.html
    "surplus_summary": rows(f"""
        SELECT surplus_class, COUNT(*) AS assets,
               COUNT(DISTINCT FORMAT('%.5f|%.5f', lat, lon)) AS points
        FROM `{DS}.in_si_gov_surplus_v2` GROUP BY 1 ORDER BY assets DESC"""),
    "surplus_leads": rows(f"""
        SELECT surplus_class, agency, city_name AS city, frpp_county AS county,
               real_property_use AS use, CAST(excess_date AS STRING) AS excess_date,
               years_underutilized, parcel_key, parcel_acres
        FROM `{DS}.in_si_gov_surplus_parcel` ORDER BY surplus_class, city_name"""),
    "withdrawn_summary": rows(f"""
        SELECT placement_grain, iso, COUNT(*) AS requests,
               ROUND(SUM(capacity_mw)) AS mw, COUNT(DISTINCT parcel_key) AS parcels
        FROM `{DS}.in_si_queue_withdrawn` GROUP BY 1, 2 ORDER BY 1, 2"""),
    "withdrawn_recency": rows(f"""
        SELECT CASE WHEN years_since_withdrawal <= 2  THEN '0-2 years'
                    WHEN years_since_withdrawal <= 5  THEN '3-5 years'
                    WHEN years_since_withdrawal <= 10 THEN '6-10 years'
                    WHEN years_since_withdrawal IS NULL THEN 'no date held'
                    ELSE 'over 10 years' END AS band,
               COUNT(*) AS requests, ROUND(SUM(capacity_mw)) AS mw
        FROM `{DS}.in_si_queue_withdrawn` GROUP BY 1
        ORDER BY MIN(IFNULL(years_since_withdrawal, 999))"""),

    # G120(b)/(e) corpus-level figures, so si.html can state the size of each defect
    "attribution": rows(f"""
        SELECT rowlike_confidence, COUNT(*) AS parcels,
               COUNTIF(nearest_structured_key IS NOT NULL) AS redirectable,
               COUNTIF(sliver_neighbours > 0) AS with_sliver
        FROM `{DS}.in_parcel_assembly` GROUP BY 1
        ORDER BY CASE rowlike_confidence WHEN 'high' THEN 1 WHEN 'shape_only' THEN 2
                 WHEN 'possible' THEN 3 ELSE 4 END"""),
}
size = gzwrite("wired.json.gz", wired)
print(f"  data/wired.json.gz  {size:,} bytes  "
      f"{ {k: len(v) for k, v in wired.items() if isinstance(v, list)} }")
print("WIRED LAYERS EXPORT COMPLETE")
