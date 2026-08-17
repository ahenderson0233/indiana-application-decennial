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
# Substations: in_substations is ALREADY a HIFLD+OSM union (sources = HIFLD+OSM 2,354 matched at
# 0.5 m avg / OSM-only 933 / HIFLD-only 571). It was rendering without saying so, which hid both
# the merge and its coverage. `sources` now rides on every point so a user can see which layer a
# substation came from, and how many exist only because OSM was merged in.
# 933 of the 3,858 carry NO lat/lon - only a footprint polygon - and they are exactly the
# OSM-only ones. Filtering on lat/lon dropped 24% of the substations the warehouse holds, and
# precisely the ones OSM contributes uniquely. Emit a point where the publisher gives one and
# the FOOTPRINT where it does not: exact published geometry either way, and no centroid is
# derived to fake a point.
# READS THE DEDUPED TABLE. `in_substations` inherits 848 duplicate rows from upstream - 2,925
# located rows on only 2,077 distinct coordinates, with ROCKPORT STATION appearing three times on
# one point - so the map was drawing ~848 markers on top of each other and every "N substations"
# figure overstated by ~41%. `in_substations_dedup` also carries `asset_class`, because the table
# mixes 503 line TAPs and 27 DEAD ENDs in with real substations: neither is a place you can
# interconnect a data centre, and they must be separable rather than silently counted as stations.
n_pt = n_poly = 0
for r in client.query(f"""
  SELECT substation_name, max_kv, min_kv, county, status, substation_type, line_count,
         operator, sources, asset_class, duplicates_collapsed, lat, lon, footprint_geojson
  FROM `{DS}.in_substations_dedup`
  WHERE lat IS NOT NULL OR footprint_geojson IS NOT NULL"""):
    d = dict(r); lat, lon = d.pop("lat"), d.pop("lon"); fp = d.pop("footprint_geojson")
    d["layer"] = "substation"
    if lat is not None and lon is not None:
        d["geom_kind"] = "point"; n_pt += 1
        geom = {"type": "Point", "coordinates": [rc(float(lon)), rc(float(lat))]}
    else:
        try: geom = rc(json.loads(fp))
        except Exception: continue
        d["geom_kind"] = "footprint"; n_poly += 1
    feats.append({"type": "Feature", "properties": d, "geometry": geom})
print(f"  substations: {n_pt:,} points + {n_poly:,} footprint-only = {n_pt + n_poly:,}")
# Transmission: ONE layer from in_transmission_union, not HIFLD alone. OSM contributes 1,114
# lines / 2,706 km that no HIFLD line comes within 100 m of — an 11% length gain on the very
# layer the parcel screener measures "distance to transmission" against, so merging it changes
# real siting answers rather than only the picture.
# G13: reads the AUDITED voltage table, not the raw union. 335 lines carried kv=-999999 (HIFLD's
# not-available marker loaded as a number), which any colour ramp would have drawn as the
# lowest-voltage lines in the state; 65 of those had a recoverable band. And all 1,114 OSM lines had
# a NULL volt_class while carrying clean kv, so a class-based legend dropped 30% of the layer.
# `unknown` ships as its own value and must get its own colour, never the bottom of the scale.
for r in client.query(f"""
  SELECT src, owner, voltage_raw AS voltage, kv_clean AS kv, volt_class_clean AS volt_class,
         had_sentinel, status, sub_1, sub_2, osm_name, merge_note, km, ST_ASGEOJSON(geog) AS gj
  FROM `{DS}.in_transmission_voltage` WHERE geog IS NOT NULL"""):
    d = dict(r); gj = d.pop("gj")
    d["layer"] = "line"
    feats.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
# MISO bus POIs (publisher coordinates only)
for r in client.query(f"""
  SELECT poi_name, bus_number, bus_name, kv, area_name, headroom_mw, worst_mw, best_mw,
         median_mw, facilities_at_zero, monitored_facilities, worst_binding_facility,
         vintage, lat, lon
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

# ---------------------------------------------------------------------------------------------
# G11 — THE VERIFIED COUNTY ACTIONS NEVER REACHED THE MAP.
#
# Measured 2026-08-17: 33 counties carry a VERIFIED data-centre action, and the map called 13 of
# them "quiet" — including CASS, which has a **ban**, and FLOYD, HUNTINGTON and WHITLEY, which have
# **moratoriums**, all with has_local_restriction = False. Meanwhile 10 counties have *approved* a
# data centre — the most actionable positive signal a siter can have — and the map had no way to
# show it at all.
#
# The cause is that the map read only `posture`, a 4-value summary (quiet / active_discussion /
# restricted / contested) derived elsewhere, while the Community page read the 9-value verified
# action vocabulary. Same estate, two surfaces, different answers. That is the same defect as the
# receipts feed showing 4 ordinances while 107 county actions existed.
#
# Gated on posture_renderable, so an unverified news lead can never reach the map as an action.
name_to_fips = {}
for g, v in ctx.items():
    nm = (v.get("posture") or {}).get("county_name")
    if nm:
        name_to_fips[nm.upper().replace(" COUNTY", "").strip()] = g

ACTION_TONE = {          # what a siter should DO about each, not merely what it is called
    "ban-prohibition":              ("blocking", "a ban is on the books — do not spend diligence here without counsel"),
    "moratorium":                   ("blocking", "development is paused; find the expiry date before committing"),
    "expired-moratorium":           ("watch",    "the pause has lapsed — check whether a permanent rule replaced it"),
    "denied":                       ("watch",    "a project was refused here; understand why before repeating it"),
    "adopted-uncodified-ordinance": ("watch",    "a rule exists that no code library carries — read the ordinance itself"),
    "proposed":                     ("watch",    "a rule is moving; timing risk, not a block"),
    "petition-pending":             ("watch",    "a decision is live right now"),
    "withdrawn":                    ("neutral",  "a petition was pulled; the county has no standing rule from it"),
    "approval-permissive":          ("open",     "this county has APPROVED a data centre — precedent exists"),
}
n_act = 0
for r in client.query(f"""
  SELECT county, confirmed_action_type AS action, jurisdiction, verified_instrument AS instrument,
         CAST(COALESCE(verified_effective_from, verified_observed_date) AS STRING) AS observed,
         official_url
  FROM `{DS}.in_dc_actions_resolved`
  WHERE posture_renderable AND county IS NOT NULL"""):
    g = name_to_fips.get(r.county.upper().replace(" COUNTY", "").strip())
    if not g:
        continue
    tone, why = ACTION_TONE.get(r.action, ("watch", "recorded action"))
    ctx[g].setdefault("actions", []).append({
        "action": r.action, "tone": tone, "why": why, "jurisdiction": r.jurisdiction,
        "instrument": r.instrument, "observed": r.observed, "url": r.official_url})
    n_act += 1

# one rolled-up verdict per county so the map can shade and filter on it. Worst tone wins: a county
# that has both approved one project and banned another is NOT "open".
TONE_RANK = {"blocking": 3, "watch": 2, "neutral": 1, "open": 0}
for g, v in ctx.items():
    acts = v.get("actions") or []
    if acts:
        worst = max(acts, key=lambda a: TONE_RANK.get(a["tone"], 0))
        v["action_summary"] = {"n": len(acts), "tone": worst["tone"],
                               "headline": worst["action"], "why": worst["why"],
                               "approved": any(a["action"] == "approval-permissive" for a in acts)}
print(f"county actions attached to the map: {n_act} rows across "
      f"{sum(1 for v in ctx.values() if v.get('actions'))} counties "
      f"(the map previously showed a 4-value posture only)")
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
  -- THE RECEIPTS FEED WAS SHOWING FOUR ORDINANCES. It read `in_ordinances_dc`, the v1 table, which
  -- holds 4 rows and one of those is a false positive (Michigan City matched on "Indiana Natural
  -- Heritage Data Center", an IDNR database, not a land use). Meanwhile v2 holds 153 candidates,
  -- triage admits 19 sections as genuinely regulating a data centre, and the 92-county sweep holds
  -- 107 land-use actions of which 73 are verified at a government source. None of it reached this
  -- feed, so the map's county receipts understated the corpus by an order of magnitude.
  --
  -- TRIAGE GATES THE CODIFIED SIDE. Shipping all 153 would be the opposite error: only 7 of them
  -- contain "data cent(er|re)" at all and the rest matched adjacent vocabulary like
  -- "telecommunications facility", which is a cell tower. Admit what triage admitted.
  UNION ALL SELECT 'ordinance', t.county,
         CONCAT(t.jurisdiction, ': ', IFNULL(t.section_title,'')),
         CONCAT(t.verdict, ' - ', IFNULL(t.reason,'')),
         CAST(ANY_VALUE(v.observed_date_source) AS STRING), t.url, ANY_VALUE(v.search_phrase)
  FROM `{DS}.in_ordinances_dc_v2_triage` t
  LEFT JOIN `{DS}.in_ordinances_dc_v2` v ON v.code_section_id = t.code_section_id
  WHERE t.verdict IN ('RELEVANT','NEEDS_FULL_TEXT')
  GROUP BY t.county, t.jurisdiction, t.section_title, t.verdict, t.reason, t.url

  -- and the layer no code library carries: adopted moratoria, bans and uncodified ordinances,
  -- gated on posture_renderable so an unverified news lead can never reach the map as a receipt
  UNION ALL SELECT 'county_action', county,
         CONCAT(jurisdiction, ': ', IFNULL(confirmed_action_type,'')),
         IFNULL(verified_instrument, ''),
         CAST(COALESCE(verified_effective_from, verified_observed_date) AS STRING),
         official_url, confirmed_action_type
  FROM `{DS}.in_dc_actions_resolved` WHERE posture_renderable"""):
    rec.append(dict(r))
with gzip.open(os.path.join(REPO, "data", "receipts.json.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(rec, f, separators=(",", ":"), default=jd)
print(f"receipts.json.gz: {len(rec)} rows")
print("GRID+SENTIMENT EXPORT COMPLETE")
