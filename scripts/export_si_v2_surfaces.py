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
# stdout must survive its own output: this console is cp1252 and characters like U+2248/U+2192/U+2717 raise
# UnicodeEncodeError from print() itself. The honesty audit once crashed on its own
# FAILURE path for exactly this reason. Degrade the glyph, never the run.
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
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

# A6: IDEM enforcement, finally dated. Undated this corpus was unusable — a 1997 NOV is not a
# lead and there was no way to tell it from a 2026 one. Two independent routes: month-window
# slicing of the publisher's own search (all 22,565) and printed signature dates from the case
# documents. date_precision is carried, because a window month is not a day.
out["idem_recency"] = rows(f"""
  SELECT CASE
    WHEN SAFE.PARSE_DATE('%Y-%m-%d', event_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 YEAR)
      THEN 'last 3 years'
    WHEN SAFE.PARSE_DATE('%Y-%m-%d', event_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 10 YEAR)
      THEN '3-10 years'
    ELSE 'older than 10 years' END AS band,
    COUNT(*) n, COUNTIF(date_precision='day') exact_day
  FROM `{DS}.in_si_d22_idem_dated` GROUP BY 1 ORDER BY 1""")
out["idem_summary"] = rows(f"""
  SELECT COUNT(*) rows_, COUNTIF(date_precision='day') day_precision,
         COUNTIF(date_precision='month') month_precision,
         COUNTIF(month_agrees_with_document='True') agree,
         COUNTIF(month_agrees_with_document='False') differ,
         MIN(event_date) first_event, MAX(event_date) last_event
  FROM `{DS}.in_si_d22_idem_dated`""")[0]
out["idem_note"] = (
    "All 22,565 IDEM enforcement actions now carry an event date, from TWO routes that check each "
    "other: month-window slicing of IDEM's own search form dates every row to MONTH precision, and "
    "the per-case documents give the printed signature date to DAY precision. Where both exist they "
    "agree on the month 97.5% of the time; the disagreements are kept and flagged, not reconciled. "
    "READ date_precision: a 'month' row sits on the 1st as a PLACEHOLDER and the day is not known. "
    "The finding this unlocked: 69% of the corpus is over ten years old. Undated it looked like "
    "22,565 leads; dated, the actionable slice is far smaller — which is the point. "
    "IDEM remains OWNER-KEYED and still cannot reach a parcel; dating makes it filterable context, "
    "not parcel-grain evidence.")

# D9 absentee + D18 owner contact, Marion only. Both signals were recorded NOT HELD statewide and
# both were wrong about Marion: the parcel crosswalk pulled for key-bridging carries the whole
# owner block. Absentee is graduated, because a landlord one suburb away and a fund in another
# country are not the same lead. NOT admitted into has_si_signal — absentee is approachability,
# not distress, and admission is the operator's call.
out["d9_classes"] = rows(f"""
  SELECT absentee_class, COUNT(*) parcels, COUNTIF(is_non_residential) non_resid,
         COUNTIF(occ_group='ci') ci,
         COUNTIF(is_non_residential AND IFNULL(mw_bess_10_per_acre,0) >= 5) fits_bess,
         COUNTIF(is_non_residential AND IFNULL(mw_datacenter_4_per_acre,0) >= 25) fits_dc
  FROM `{DS}.in_si_d9_absentee_marion` GROUP BY 1 ORDER BY parcels DESC""")
out["d9_summary"] = rows(f"""
  SELECT COUNT(*) parcels, COUNTIF(owner_name IS NOT NULL) named,
         COUNT(DISTINCT owner_name) distinct_owners,
         COUNTIF(is_absentee_out_of_state) out_of_state,
         COUNTIF(is_absentee_out_of_state AND is_non_residential) out_of_state_nonres
  FROM `{DS}.in_si_d9_absentee_marion`""")[0]
# the portfolio view: one owner holding many non-residential acres is a single conversation
out["d9_portfolios"] = rows(f"""
  SELECT owner_name, owner_state, owner_city, COUNT(*) parcels,
         ROUND(SUM(IFNULL(exact_parcel_acres, parcel_acres)), 1) acres,
         COUNTIF(occ_group='ci') ci_parcels,
         ROUND(MAX(IFNULL(mw_datacenter_4_per_acre, 0)), 1) best_dc_mw
  FROM `{DS}.in_si_d9_absentee_marion`
  WHERE is_absentee_out_of_state AND is_non_residential AND owner_name IS NOT NULL
  GROUP BY 1,2,3 HAVING acres > 5 ORDER BY acres DESC LIMIT 60""")
out["d9_note"] = (
    "MARION ONLY — 1 of 92 counties, so this is a PUBLISHING footprint, not statewide coverage. "
    "Its absence elsewhere is our gap, not the absence of absentee owners, and a statewide "
    "ranking must not weight it as though it were evenly available. Statewide D9 still needs the "
    "DLGF Gateway owner pull. "
    "These parcels are NOT flagged as seller-intent: absentee ownership is APPROACHABILITY, not "
    "distress, and the standing ruling admits only distress that would plausibly move an owner "
    "to sell. Whether to admit it is an open question for the operator.")

# Evansville Land Bank — NINE snapshots of one inventory, which is what makes disposals visible:
# a parcel present in 2021 and absent by 2026 was sold. Availability semantics, not distress.
PIN = "COALESCE(STATE_PIN, StatePIN, State_PIN_2)"
out["landbank_snapshots"] = rows(f"""
  SELECT _snapshot_date snapshot, COUNT(*) n, COUNT(DISTINCT {PIN}) parcels
  FROM `{DS}.in_si_evansville_landbank` GROUP BY 1 ORDER BY 1""")
out["landbank_summary"] = rows(f"""
  WITH mx AS (SELECT MAX(_snapshot_date) d FROM `{DS}.in_si_evansville_landbank`),
  cur AS (SELECT DISTINCT {PIN} p FROM `{DS}.in_si_evansville_landbank`, mx
          WHERE _snapshot_date = mx.d),
  allp AS (SELECT DISTINCT {PIN} p FROM `{DS}.in_si_evansville_landbank`),
  placed AS (
    SELECT COUNTIF(s.parcel_key IS NOT NULL) placed,
           COUNTIF(s.occ_group='no_structure') vacant_lots,
           COUNTIF(s.occ_group IN ('ci','other_nonres','agriculture')) nonres_structure,
           COUNTIF(s.occ_group='residential') residential, COUNT(*) pins
    FROM allp LEFT JOIN `{DS}.in_sites` s
      ON s.parcel_key = REGEXP_REPLACE(allp.p, r'[^0-9]',''))
  SELECT (SELECT COUNT(*) FROM allp) ever, (SELECT COUNT(*) FROM cur) still_held,
         (SELECT COUNT(*) FROM allp WHERE p NOT IN (SELECT p FROM cur)) disposed,
         (SELECT d FROM mx) latest_snapshot, p.* FROM placed p""")[0]

# CAPABILITY, not just evidence. A signal says an owner may sell; it says nothing about whether
# the parcel can host anything. 69% of flagged parcels cannot hold even a 5 MW BESS — that is a
# useful filter, not a defect, and it belongs on screen next to the flag rather than buried.
out["capability"] = rows(f"""
  SELECT COUNTIF(has_si_signal) flagged,
    COUNTIF(has_si_signal AND fits_min_bess_5mw) fits_bess,
    COUNTIF(has_si_signal AND fits_dc_25mw) fits_dc,
    COUNTIF(has_si_signal AND NOT fits_min_bess_5mw) too_small,
    ROUND(APPROX_QUANTILES(IF(has_si_signal, parcel_acres, NULL), 100)[OFFSET(50)], 2) median_ac
  FROM `{DS}.in_si_sites_flags_v2`""")[0]

# the Lane D columns that were pulled and never wired — their measured vocabularies
out["lane_d"] = rows(f"""
  SELECT src, col, val, n, n_located FROM `{DS}.in_si_lane_d_enrichment`
  WHERE val IS NOT NULL AND val != ''
  ORDER BY src, col, n DESC LIMIT 120""")
out["lane_d_summary"] = rows(f"""
  SELECT src, col, COUNT(*) distinct_values, SUM(n) rows_covered, SUM(n_located) located
  FROM `{DS}.in_si_lane_d_enrichment` GROUP BY 1,2 ORDER BY rows_covered DESC""")

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
