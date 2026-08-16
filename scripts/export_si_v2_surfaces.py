"""Surface the SI v2 / D22 / owner-grain tables, and the one A6 leftover.

The wiring census (`scripts/audit_wiring_census.py`) read 217 of 226 after its instrument was
corrected — and 7 of the 9 unwired objects were built THIS session. Building a table and shipping
it are different acts; this script is the second one.

Surfaces:
  in_si_signal_coverage        -> SI Feed: per-signal coverage, four numbers each
  in_si_parcel_signals_v2      -> SI Feed: the evidence grain, top parcels by breadth
  in_si_owner_signals          -> SI Feed: the OWNER-grain block (D11/D27/D19), with the reason
                                  they are not parcel-keyed stated on screen
  in_si_owner_signals_county   -> SI Feed: per-county dissolutions / UCC lapses / WARN
  in_si_d22_county_rollup      -> SI Feed + Community: environmental posture per county
  in_si_d22_echo_indiana       -> MAP: 58,003 facilities as a lazily-loaded layer. All of them,
                                  not just the distressed ones — the operator asked for the full
                                  picture, and the distress grade rides on each point so the user
                                  filters rather than being handed a pre-filtered subset.
  in_generation_union          -> Grid: the A6 merge that was built and never shipped

Both D5 split tables reach the user THROUGH `in_si_parcel_signals_v2`, so surfacing v2 resolves
them too — that is the derivative route the census now models explicitly.
"""
import json, gzip, os, datetime
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")


def rows(sql):
    return [dict(r) for r in client.query(sql)]


out = {"built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}

out["coverage"] = rows(f"""
  SELECT signal, corpus_rows, parcels_reached, parcels_admitted, parcels_ci,
         excl_residential, excl_low_severity, first_event, last_event, keying, blocks
  FROM `{DS}.in_si_signal_coverage` ORDER BY parcels_admitted DESC, corpus_rows DESC""")

out["flag_summary"] = rows(f"""
  SELECT COUNTIF(has_si_signal) flagged,
    COUNTIF(has_si_signal AND si_last_event_date IS NOT NULL) dated,
    COUNTIF(has_si_signal AND si_events_3y>0) r3, COUNTIF(has_si_signal AND si_events_5y>0) r5,
    COUNTIF(has_si_signal AND occ_group='ci') ci,
    COUNTIF(has_si_signal AND occ_group='other_nonres') other_nonres,
    COUNTIF(has_si_signal AND occ_group='agriculture') ag,
    COUNTIF(has_si_signal AND occ_group='no_structure') land,
    SUM(si_excluded_residential) excl_resid, SUM(si_excluded_low_severity) excl_lowsev
  FROM `{DS}.in_si_sites_flags_v2`""")[0]

# the evidence grain: parcels carrying the most independent signals
out["top_evidence"] = rows(f"""
  SELECT f.parcel_key, f.occ_group, f.si_signal_types, f.si_signal_events, f.si_signals,
         f.si_first_event_date, f.si_last_event_date, f.si_events_3y, sc.county_fips
  FROM `{DS}.in_si_sites_flags_v2` f
  JOIN `{DS}.in_sites_county` sc USING (parcel_source, parcel_key)
  WHERE f.has_si_signal
  ORDER BY f.si_signal_types DESC, f.si_events_3y DESC, f.si_signal_events DESC
  LIMIT 120""")

out["owner_signals"] = rows(f"""
  SELECT signal, party, detail, event_date, city, county_fips, within_3y
  FROM `{DS}.in_si_owner_signals`
  ORDER BY event_date DESC NULLS LAST LIMIT 400""")
out["owner_county"] = rows(f"""
  SELECT county_fips, dissolutions, ucc_lapses, warn_notices, events_3y, events_total, last_event
  FROM `{DS}.in_si_owner_signals_county` ORDER BY events_total DESC""")
out["owner_note"] = (
  "D11 entity dissolutions, D27 UCC lapses and D19 WARN notices are OWNER-grain, not parcel-grain. "
  "Measured: the address bridge matches 6 of 983 (D11) and 0 of 156 (D27). These are BUSINESS "
  "REGISTRY addresses — a dissolved entity's address of record is often its registered agent's "
  "office, so a street match would frequently flag the wrong parcel. The route that would work is "
  "the OWNER NAME, and mat_parcel_attrs.parcel_owner is NULL on all 3,553,381 Indiana parcels "
  "(B1). These become parcel-reachable the moment the DLGF Gateway owner pull lands.")

out["d22_county"] = rows(f"""
  SELECT county_norm, county_fips, facilities, distress_facilities, significant_violations,
         high_priority_violators, inactive_facilities, total_penalties, major_facilities
  FROM `{DS}.in_si_d22_county_rollup` ORDER BY distress_facilities DESC, facilities DESC""")
out["d22_summary"] = rows(f"""
  SELECT COUNT(*) facilities, COUNTIF(is_distress) distress,
    COUNTIF(is_inactive_facility) inactive,
    COUNTIF(distress_class='significant_violation') sig_violation,
    -- from the flag itself: distress_class is a priority ladder and every Indiana HPV is also in
    -- significant violation, so reading HPV off the ladder reports 0 where 95 exist
    COUNTIF(CAA_HPV_FLAG='Y') hpv,
    ROUND(SUM(SAFE_CAST(FAC_TOTAL_PENALTIES AS FLOAT64))/1e9, 2) penalties_bn
  FROM `{DS}.in_si_d22_echo_indiana`""")[0]

out["generation_union"] = rows(f"""
  SELECT * FROM `{DS}.in_generation_union` LIMIT 400""")

# The D5 split, read from the two tables themselves. They were orphaned when build_si_signal_v2
# was rewritten to read the South Bend / Indy sources DIRECTLY, bypassing the union — so the
# split that produced the single biggest correction in this project had no surface at all.
out["d5_split"] = {
  "abandoned_buildings": rows(
      f"SELECT COUNT(*) n, COUNT(DISTINCT parcel_key) parcels, COUNT(DISTINCT source_id) srcs "
      f"FROM `{DS}.in_si_d5_abandoned_buildings`")[0],
  "vacant_land": rows(
      f"SELECT COUNT(*) n FROM `{DS}.in_si_d5_vacant_land_NOT_A_SIGNAL`")[0],
  "by_source": rows(
      f"SELECT source_id, COUNT(*) n, COUNTIF(parcel_key IS NOT NULL) keyed "
      f"FROM `{DS}.in_si_d5_abandoned_buildings` GROUP BY 1 ORDER BY n DESC"),
}

# Marion placement, checked by TWO instruments that share no mechanism: the publisher's own
# local->state key mapping, and ST_CONTAINS of the building's own polygon. Agreement is
# corroboration; the disagreements are shown rather than resolved by preference.
out["marion_check"] = rows(f"""
  SELECT verdict, COUNT(*) n FROM `{DS}.in_si_marion_route_check` GROUP BY 1 ORDER BY n DESC""")
out["marion_disagreements"] = rows(f"""
  SELECT parcel_local_id, address, city, crosswalk_key, spatial_key
  FROM `{DS}.in_si_marion_route_check` WHERE verdict='DISAGREE' ORDER BY address""")
out["marion_geom_rows"] = rows(
    f"SELECT COUNT(*) n, COUNTIF(geometry_json IS NOT NULL) with_geom "
    f"FROM `{DS}.in_si_indy_abandoned_vacant_spatial`")[0]

p = os.path.join(REPO, "data", "si_v2.json.gz")
with gzip.open(p, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(out, f, separators=(",", ":"), default=str)
print(f"data/si_v2.json.gz — {os.path.getsize(p)/1024:.0f} KB")

# ---- the ECHO facility map layer: ALL of them, with the grade riding on each point ------------
feats = []
for r in client.query(f"""
    SELECT REGISTRY_ID rid, FAC_NAME nm, FAC_CITY city, county_norm co, distress_class dc,
           is_distress d, is_inactive_facility inact, FAC_MAJOR_FLAG major,
           SAFE_CAST(FAC_TOTAL_PENALTIES AS FLOAT64) pen, FAC_NAICS_CODES naics,
           FAC_COMPLIANCE_STATUS status, lat, lon
    FROM `{DS}.in_si_d22_echo_indiana` WHERE lat IS NOT NULL AND lon IS NOT NULL"""):
    d = dict(r); lat, lon = d.pop("lat"), d.pop("lon")
    d["layer"] = "echo"
    feats.append({"type": "Feature",
                  "properties": {k: v for k, v in d.items() if v not in (None, "")},
                  "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]}})
p2 = os.path.join(REPO, "data", "echo_facilities.geojson.gz")
with gzip.open(p2, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump({"type": "FeatureCollection", "features": feats}, f,
              separators=(",", ":"), default=str)
print(f"data/echo_facilities.geojson.gz — {len(feats):,} facilities, "
      f"{os.path.getsize(p2)/1024/1024:.1f} MB")
print(f"  distress {sum(1 for x in feats if x['properties'].get('d'))}, "
      f"inactive {sum(1 for x in feats if x['properties'].get('inact'))}")
