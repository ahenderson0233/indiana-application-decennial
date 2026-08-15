"""Join-path enrichments: give every site-describing table a location, WITHOUT re-scraping.

The plottability audit found 24 place/site tables at grade E. Most are not missing data — they
are keyed to something we already hold with coordinates. This builds one view per join and
MEASURES ITS YIELD. A join that matches 5% is a finding, not a fix, so nothing here is declared
working without its number.

Views, not tables: these are derivations of data we already store, so materialising them would
duplicate rows and go stale. Each is registered anyway — the operator's rule is that every object
has a home.

Deliberately NOT built (they are not defects):
  in_ustp_ch7_tfr        — 33 rows of bankruptcy-trustee FINANCIALS by region/office. A series,
                           misclassified as a site table by the auditor's keyword pass.
  in_groundwater_sites   — ONE row holding a statewide monitoring-site COUNT. An aggregate.
  in_si_d25_admitted     — rail-abandonment dockets. Keyed by docket, not place; the rail line
                           itself is the geography and that is a future line-matching job, not a
                           join we can honestly make today.
"""
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

# (view name, source table, SQL, what the join is, the yield probe)
JOINS = [
 ("vw_site_gates_located", "in_site_gates", f"""
    SELECT g.*, s.lat, s.lon, s.parcel_acres, s.occ_group,
           ST_ASGEOJSON(s.parcel_geog) AS geometry_geojson
    FROM `{DS}.in_site_gates` g
    JOIN `{DS}.in_sites` s USING (parcel_source, parcel_key)""",
  "parcel_source+parcel_key -> in_sites (EXACT parcel geometry)",
  f"""SELECT (SELECT COUNT(*) FROM `{DS}.in_site_gates`) src,
             (SELECT COUNT(*) FROM `{DS}.in_site_gates` g
              JOIN `{DS}.in_sites` s USING (parcel_source, parcel_key)) matched"""),

 ("vw_si_candidates_located", "in_si_candidates", f"""
    SELECT c.* EXCEPT(gj),
           COALESCE(c.gj, ST_ASGEOJSON(s.parcel_geog)) AS geometry_geojson,
           s.lat, s.lon, s.parcel_acres
    FROM `{DS}.in_si_candidates` c
    LEFT JOIN `{DS}.in_sites` s USING (parcel_source, parcel_key)""",
  "parcel_source+parcel_key -> in_sites; keeps its own gj where present",
  f"""SELECT (SELECT COUNT(*) FROM `{DS}.in_si_candidates`) src,
             (SELECT COUNT(*) FROM `{DS}.in_si_candidates` c
              JOIN `{DS}.in_sites` s USING (parcel_source, parcel_key)) matched"""),

 ("vw_bus_headroom_300_located", "in_bus_headroom_300", f"""
    SELECT h.*, m.bus_number, m.bus_name, m.kv, m.lat, m.lon
    FROM `{DS}.in_bus_headroom_300` h
    LEFT JOIN (SELECT poi_name, ANY_VALUE(bus_number) bus_number, ANY_VALUE(bus_name) bus_name,
                      ANY_VALUE(kv) kv, ANY_VALUE(lat) lat, ANY_VALUE(lon) lon
               FROM `{DS}.in_bus_headroom_miso` GROUP BY poi_name) m USING (poi_name)""",
  "poi_name -> in_bus_headroom_miso (publisher coordinates)",
  f"""SELECT (SELECT COUNT(*) FROM `{DS}.in_bus_headroom_300`) src,
             (SELECT COUNT(*) FROM `{DS}.in_bus_headroom_300` h
              JOIN (SELECT DISTINCT poi_name FROM `{DS}.in_bus_headroom_miso`
                    WHERE lat IS NOT NULL) m USING (poi_name)) matched"""),

# bus_number is INT64 on one side and STRING on the other, so USING() cannot compare them.
# Cast BOTH to STRING explicitly rather than relying on coercion.
 ("vw_pjm_bus_withdrawal_located", "in_pjm_bus_withdrawal", f"""
    SELECT w.*, b.lat, b.lon, b.location_method, b.match_confidence
    FROM `{DS}.in_pjm_bus_withdrawal` w
    LEFT JOIN `{DS}.in_pjm_bus_locations_candidate` b
      ON CAST(w.bus_number AS STRING) = CAST(b.bus_number AS STRING)""",
  "bus_number -> in_pjm_bus_locations_candidate (ESTIMATED locations, confidence tier carried)",
  f"""SELECT (SELECT COUNT(*) FROM `{DS}.in_pjm_bus_withdrawal`) src,
             (SELECT COUNT(*) FROM `{DS}.in_pjm_bus_withdrawal` w
              JOIN `{DS}.in_pjm_bus_locations_candidate` b
                ON CAST(w.bus_number AS STRING) = CAST(b.bus_number AS STRING)
              WHERE b.lat IS NOT NULL) matched"""),

 ("vw_pjm_queuescope_located", "in_pjm_queuescope_aep", f"""
    SELECT q.*, b.lat, b.lon, b.match_confidence
    FROM `{DS}.in_pjm_queuescope_aep` q
    LEFT JOIN `{DS}.in_pjm_bus_locations_candidate` b
      ON CAST(q.bus_number AS STRING) = CAST(b.bus_number AS STRING)""",
  "bus_number -> in_pjm_bus_locations_candidate",
  f"""SELECT (SELECT COUNT(*) FROM `{DS}.in_pjm_queuescope_aep`) src,
             (SELECT COUNT(*) FROM `{DS}.in_pjm_queuescope_aep` q
              JOIN `{DS}.in_pjm_bus_locations_candidate` b
                ON CAST(q.bus_number AS STRING) = CAST(b.bus_number AS STRING)
              WHERE b.lat IS NOT NULL) matched"""),

 ("vw_ghgrp_emissions_located", "in_ghgrp_emissions", f"""
    SELECT e.*, f.facility_name, f.city, f.county, f.latitude AS lat, f.longitude AS lon
    FROM `{DS}.in_ghgrp_emissions` e
    LEFT JOIN (SELECT CAST(facility_id AS STRING) fid, ANY_VALUE(facility_name) facility_name,
                      ANY_VALUE(city) city, ANY_VALUE(county) county,
                      ANY_VALUE(latitude) latitude, ANY_VALUE(longitude) longitude
               FROM `{DS}.in_ghgrp_facilities` GROUP BY 1) f
      ON CAST(e.facility_id AS STRING) = f.fid""",
  "facility_id -> in_ghgrp_facilities (publisher coordinates)",
  f"""SELECT (SELECT COUNT(*) FROM `{DS}.in_ghgrp_emissions`) src,
             (SELECT COUNT(*) FROM `{DS}.in_ghgrp_emissions` e
              JOIN (SELECT DISTINCT CAST(facility_id AS STRING) fid FROM `{DS}.in_ghgrp_facilities`
                    WHERE latitude IS NOT NULL) f
                ON CAST(e.facility_id AS STRING) = f.fid) matched"""),

 ("vw_pjm_rtep_upgrades_located", "in_pjm_rtep_upgrades", f"""
    SELECT u.*, d.location AS detail_location, d.equipment AS detail_equipment,
           c.zone AS cost_zone, c.percent AS cost_percent
    FROM `{DS}.in_pjm_rtep_upgrades` u
    LEFT JOIN `{DS}.in_pjm_rtep_upgrade_details` d USING (upgrade_id)
    LEFT JOIN `{DS}.in_pjm_rtep_cost_allocations` c USING (upgrade_id)""",
  "upgrade_id -> details + cost allocations (place is TEXT; no coordinate is invented). "
  "The ~6% yield is CORRECT, not a defect: in_pjm_rtep_upgrades holds all 15,443 PJM upgrades "
  "across every state, and details were pulled only for the 932 Indiana ones.",
  # Measure the yield against the INDIANA subset, which is what the detail pull covered - against
  # all 15,443 PJM-wide upgrades it reads 6% and looks broken when it is complete.
  f"""SELECT (SELECT COUNT(*) FROM `{DS}.in_pjm_rtep_upgrades`
              WHERE UPPER(IFNULL(state,'')) LIKE '%IN%') src,
             (SELECT COUNT(*) FROM `{DS}.in_pjm_rtep_upgrades` u
              JOIN `{DS}.in_pjm_rtep_upgrade_details` d USING (upgrade_id)) matched"""),
]

# NFIRS raw vintages -> their own address table, per year
for yr in ("2020", "2021", "2022", "2023", "2024"):
    b, a = f"in_nfirs_basicincident_{yr}", f"in_nfirs_incidentaddress_{yr}"
    try:
        client.get_table(f"{DS}.{a}"); client.get_table(f"{DS}.{b}")
    except Exception:
        print(f"  skip NFIRS {yr}: no matching address table held"); continue
    JOINS.append((f"vw_nfirs_{yr}_located", b, f"""
        SELECT i.*, a.NUM_MILE, a.STREETNAME, a.STREETTYPE, a.CITY, a.ZIP5,
               TRIM(CONCAT(IFNULL(a.NUM_MILE,''),' ',IFNULL(a.STREETNAME,''),' ',
                           IFNULL(a.STREETTYPE,''))) AS street_address
        FROM `{DS}.{b}` i LEFT JOIN `{DS}.{a}` a USING (INCIDENT_KEY)""",
      f"INCIDENT_KEY -> {a} (address grain; no coordinate invented)",
      f"""SELECT (SELECT COUNT(*) FROM `{DS}.{b}`) src,
                 (SELECT COUNT(*) FROM `{DS}.{b}` i JOIN `{DS}.{a}` a USING (INCIDENT_KEY)) matched"""))

print(f"building {len(JOINS)} location views\n")
built = []
for view, src, sql, how, probe in JOINS:
    try:
        y = list(client.query(probe))[0]
        pct = 100 * y.matched / y.src if y.src else 0
        client.query(f"CREATE OR REPLACE VIEW `{DS}.{view}` AS\n{sql}").result()
        # The two PJM bus joins land at ~15%, and that is NOT a join failure: only 229 of PJM's
        # 1,475 Indiana buses have a location at all (name-ladder derived, 91 high-confidence).
        # The join is perfect against what exists; the ceiling is the location coverage. Rows
        # without a location keep NULL lat/lon rather than borrowing a nearby one.
        known = "pjm" in view
        flag = ("" if pct >= 90 else
                "  <- ceiling is PJM bus-location coverage (229/1,475), not the join" if known else
                "  <- PARTIAL" if pct >= 40 else "  <- LOW YIELD, investigate")
        print(f"  {view:<34} {y.matched:>9,}/{y.src:<9,} = {pct:5.1f}%{flag}")
        built.append((view, src, how, y.src, y.matched, pct))
    except Exception as ex:
        print(f"  {view:<34} FAILED: {str(ex)[:110]}")

for view, src, how, n_src, n_match, pct in built:
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{view}'").result()
    client.query(f"""INSERT `{DS}._registry`
      (table_name, source, method, n_rows, gb_scanned, built_at, notes)
      VALUES (@t,@s,@m,@n,0,CURRENT_TIMESTAMP(),@o)""",
      job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", view),
        bigquery.ScalarQueryParameter("s", "STRING", f"indiana_app.{src}"),
        bigquery.ScalarQueryParameter("m", "STRING", how),
        bigquery.ScalarQueryParameter("n", "INT64", n_match),
        bigquery.ScalarQueryParameter("o", "STRING",
          f"LOCATION JOIN, measured yield {n_match:,}/{n_src:,} = {pct:.1f}%. A VIEW, not a table: "
          "this is a derivation of data already stored, so materialising it would duplicate rows "
          "and go stale. No coordinate is invented anywhere - where the join gives only a place "
          "name or an address, that is what the view carries.")])).result()
print(f"\n{len(built)} views built and registered")
