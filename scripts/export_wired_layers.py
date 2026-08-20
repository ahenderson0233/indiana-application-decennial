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

# ---- 5. G15 / G87: future capacity, at the two grains we can honestly claim ------------------
# Operator (G87): *"maybe you should follow what we do on the Illinois map to better outline where
# the upgrades occur and where they may be located; the utilities often provide location estimates
# or regions where a project will take place."*
#
# ⭐ TWO TIERS, EXACTLY AS G15 PRESCRIBED, AND THE SPLIT IS THE HONEST PART.
#   TIER 1 - EXACT: 119 projects whose station resolves in the gazetteer get a real point.
#            ⭐ That was 100 this morning. `repair_substation_geometry.py` recovered 734
#            substations and 161 gazetteer names, and re-running the locator turned every one of
#            G109's "matched a substation with no county" rows into a located project: 19 -> 0.
#   TIER 2 - REGION: the other 499 name only a utility. Their uncertainty region is that
#            utility's SERVICE TERRITORY, which we hold - "somewhere in here", drawn as an area
#            rather than pretended into a point. That is the Illinois pattern the operator named.
#
# ⛔ THE UTILITY NAMES DO NOT MATCH AND ARE NOT FUZZY-MATCHED. The plans say "NIPSCO" and "AES
#   Indiana (IPL)"; the territory layer says "NORTHERN INDIANA PUB SERV CO" and "INDIANAPOLIS
#   POWER & LIGHT CO". A similarity match across 6 names would be a coin flip nobody could audit,
#   so the alias table is EXPLICIT and hand-checked against the territory list. An unmapped
#   utility is reported, never silently dropped.
UTIL_ALIAS = {
    "NIPSCO": "NORTHERN INDIANA PUB SERV CO",
    "AES Indiana (IPL)": "INDIANAPOLIS POWER & LIGHT CO",     # AES Indiana was IPL until 2021
    "Duke Energy Indiana": "DUKE ENERGY INDIANA, LLC",
    "CenterPoint Indiana South (SIGECO/Vectren)": "SOUTHERN INDIANA GAS & ELEC CO",
    "Indiana Michigan Power": "INDIANA MICHIGAN POWER CO",
    # ⚠ deliberately unmapped: 17 rows scraped from the IURC IRP page with no utility attributed.
    #   They have no region either, and saying so is the answer.
    "unattributed (IURC IRP page)": None,
}
n_gp = 0
for r in client.query(f"""
  SELECT utility, asset_name, asset_type, station_name, matched_substation, voltage_kv,
         in_service_year, county, location_method, lat AS la, lon AS lo
  FROM `{DS}.in_grid_plans_located` WHERE lat IS NOT NULL"""):
    d = dict(r)
    la, lo = d.pop("la"), d.pop("lo")
    d["layer"] = "gridplan"
    d["locate_tier"] = "exact"
    feats.append({"type": "Feature", "properties": d,
                  "geometry": {"type": "Point", "coordinates": [rc(lo), rc(la)]}})
    n_gp += 1
region = [dict(r) for r in client.query(f"""
  SELECT utility, COUNT(*) AS projects,
         COUNTIF(voltage_kv IS NOT NULL) AS with_kv,
         COUNTIF(in_service_year IS NOT NULL) AS with_year,
         ROUND(MAX(voltage_kv)) AS max_kv
  FROM `{DS}.in_grid_plans_located` WHERE lat IS NULL GROUP BY 1 ORDER BY projects DESC""")]
unmapped = [r["utility"] for r in region
            if r["utility"] not in UTIL_ALIAS]
print(f"  grid plans: {n_gp} exact points + "
      f"{sum(r['projects'] for r in region)} placed only to a utility region")
if unmapped:
    print(f"  ⛔ {len(unmapped)} utility name(s) with no territory alias - REPORTED, not dropped: "
          f"{unmapped}")

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

    # ⛔ `headroom_300` REMOVED 2026-08-20, AND NOT WIRED ANYWHERE. The table it came from holds
    #    642 rows covering EXACTLY the same 642 MISO points as in_miso_poi_state - measured, 642
    #    shared with no residue on either side - and grid.html already carries a "MISO POIs,
    #    injection detail @ a 300 MW request" card. Shipping a second 300 MW answer beside the
    #    first is the two-copies-drift defect, so it is recorded as a duplicate grain in
    #    audit_unwired_classification.py instead. An unused payload key is not free either: it
    #    is weight in every download and a future reader assumes something renders it.
    # ⚠ MOVED HERE FROM export_wired_batch2.py, 2026-08-20 — THE SECOND TIME THIS SESSION
    #   THAT RELATED KEYS LANDED IN DIFFERENT PAYLOADS. grid.html reads wired.json.gz and
    #   these were being written into wired2.json.gz, so three panels would have rendered
    #   empty forever. Both times audit_frontend.py caught it, because it compares every
    #   key a page READS against the keys the export WRITES.
    #   ⛔ The root cause is two sibling export scripts with no rule about which payload a
    #   key belongs in. The rule is now: a key goes in the payload the PAGE THAT RENDERS
    #   IT already loads — grid content in wired, market content in wired2.
    # MISO POI headroom and the facility that binds it. 642 points, 40,007 monitored facilities.
    "miso_poi": rows(f"""
        SELECT poi_name, bus_name, kv, area_name, ROUND(headroom_mw) AS headroom_mw,
               headroom_state, n_monitored_facilities, n_facilities_at_zero,
               n_facilities_overloaded_base, ROUND(binding_percent_loading_before, 1) AS pct_loaded,
               _vintage AS vintage
        FROM `{DS}.in_miso_poi_state`
        ORDER BY headroom_mw DESC LIMIT 300"""),
    # ⛔ `cont_name`, `fr_name` and `to_name` EXIST AND ARE 100% NULL on all 40,007 rows. Grouping
    #    on cont_name returned ZERO rows and a careless reading of that is "no contingency binds
    #    anything", which is the opposite of the truth. The endpoints are packed inside
    #    `monitored_facility` as a PSS/E branch string:
    #        '348067 7RAMSEY       345  348491 7HOLLAND      345  1'
    #        <-- from bus + name + kV --><-- to bus + name + kV --><ckt>
    #    so the facility is aggregated on that string and the from/to names are pulled out of it.
    "miso_binding": rows(f"""
        SELECT
          TRIM(REGEXP_EXTRACT(monitored_facility, r'^\\s*\\d+\\s+(\\S+)')) AS from_bus,
          TRIM(REGEXP_EXTRACT(monitored_facility, r'\\d+\\s+\\S+\\s+\\d+\\s+\\d+\\s+(\\S+)'))
            AS to_bus,
          COUNT(*) AS times_monitored,
          COUNT(DISTINCT poi_name) AS pois_affected,
          ROUND(AVG(percent_loading_before), 1) AS avg_pct_loaded_before,
          ROUND(MIN(mw_available)) AS min_mw_available
        FROM `{DS}.in_miso_facility_detail`
        WHERE monitored_facility IS NOT NULL
        GROUP BY 1, 2
        HAVING from_bus IS NOT NULL
        ORDER BY pois_affected DESC, times_monitored DESC LIMIT 40"""),
    "miso_facility_note": [{
        "held": 40007,
        "cont_name_populated": 0,
        "note": "cont_name, fr_name and to_name are held and 100% empty; the branch endpoints "
                "are parsed out of the monitored_facility PSS/E string instead. Reported so a "
                "later session does not read an empty GROUP BY as 'nothing binds'.",
    }],

    # G15/G87 tier 2: the projects we can place only to a utility's service territory.
    # The map shades that territory; the panel says how many projects and what is known of them.
    "grid_plan_regions": [
        {**r, "territory_utility": UTIL_ALIAS.get(r["utility"], None),
         "region_known": UTIL_ALIAS.get(r["utility"]) is not None}
        for r in region],
    "grid_plan_note": [{
        "exact": n_gp,
        "region_only": sum(r["projects"] for r in region),
        "note": "Two tiers. EXACT means the workpaper named a station the gazetteer holds, so the "
                "point is that station. REGION means the row names only a utility, and the "
                "uncertainty region is that utility's service territory - drawn as an area "
                "because that is the precision we have. 17 rows name no utility at all and have "
                "neither.",
    }],

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
