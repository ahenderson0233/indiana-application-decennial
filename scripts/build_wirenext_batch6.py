"""WIRE-NEXT batch 6 (eyeball-queue finds): existing-DC family (incl. the DCM coords the
gap register still calls pinless), FCC summaries, EIA operational series, GHGRP emissions,
workforce completions, generators, military bases, rail/roads/zctas, NFIRS 2020-21,
water stress/drought, NRC. Adaptive per-table mode: state col -> widened values;
geoid col -> '18' prefix; else geography -> state-polygon clip."""
import re
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
E = "`energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")
ST = "(SELECT state_geom FROM `bigquery-public-data.geo_us_boundaries.states` WHERE state='IN')"
WIDE = "'IN','INDIANA','18','IND','IND.','INDIANA ','IN '"

# sample-first: what is data_centers_datacentermap_coords?
for r in client.query(f"SELECT * FROM {E}.data_centers_datacentermap_coords` LIMIT 3"):
    print("DCM coords sample:", {k: str(v)[:40] for k, v in list(dict(r).items())[:10]})

TARGETS = ["data_centers", "data_centers_baxtel", "data_centers_cloudscene",
           "data_centers_datacentermap_coords", "data_centers_wikidata",
           "fcc_bdc_fixed_summary_by_geography", "fcc_bdc_mobile_summary_by_geography",
           "fcc_bdc_provider_summary_by_geography", "elec_power_operational",
           "ghgrp_emissions", "workforce_ipeds_cs_eng", "operating_generators",
           "nrc_reactors", "water_aqueduct", "drought_by_state",
           "nfirs_basicincident_2021", "nfirs_incidentaddress_2021", "nfirs_fireincident_2021",
           "nfirs_basicincident_2020", "nfirs_incidentaddress_2020", "nfirs_fireincident_2020",
           "land_military_bases", "railroads", "roads_primary", "roads_secondary", "zctas"]
STATE_COL = re.compile(r"(?:^|_)(state|st|src_state|state_abbr|state_code|state_usps|stusps|state_name|prov_st)(?:$|_)")
GEOID_COL = re.compile(r"geoid|geography_id|fips|tract|block")
for t in TARGETS:
    try:
        tt = client.get_table(f"energy-platfrom.energy.{t}")
    except Exception as ex:
        print(f"SKIP {t}: {str(ex)[:60]}"); continue
    cols = [s.name for s in tt.schema]
    statec = next((c for c in cols if STATE_COL.search(c.lower())), None)
    geoidc = next((c for c in cols if GEOID_COL.search(c.lower())), None)
    gcol = next((c for c in cols if c.lower() in ("geog", "geom")), None)
    gjson = next((c for c in cols if "geojson" in c.lower()), None)
    if statec:
        pred = f"UPPER(TRIM(CAST(`{statec}` AS STRING))) IN ({WIDE})"
        mode = f"state:{statec}"
        sql = f"CREATE OR REPLACE TABLE `{DS}.in_{t}` AS SELECT * FROM {E}.{t}` WHERE {pred}"
    elif geoidc:
        pred = f"STARTS_WITH(CAST(`{geoidc}` AS STRING), '18')"
        mode = f"geoid:{geoidc}"
        sql = f"CREATE OR REPLACE TABLE `{DS}.in_{t}` AS SELECT * FROM {E}.{t}` WHERE {pred}"
    elif gcol or gjson:
        geo = gcol if gcol else f"SAFE.ST_GEOGFROMGEOJSON({gjson})"
        mode = f"spatial:{gcol or gjson}"
        sql = (f"CREATE OR REPLACE TABLE `{DS}.in_{t}` AS SELECT * FROM "
               f"(SELECT *, {geo} AS _g FROM {E}.{t}`) WHERE _g IS NOT NULL AND ST_INTERSECTS(_g, {ST})")
    else:
        print(f"FLAG {t}: no state/geoid/geometry column — needs a value-read ({cols[:8]})")
        continue
    try:
        dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
        gb = dry.total_bytes_processed / 1e9
        if gb > 120:
            print(f"SKIP {t}: dry {gb:.0f} GB > guard"); continue
        client.query(sql).result()
        n = list(client.query(f"SELECT COUNT(*) AS n FROM `{DS}.in_{t}`"))[0].n
        client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
          VALUES ('in_{t}','energy.{t}','adaptive clip ({mode})', {n}, {gb:.3f},
                  CURRENT_TIMESTAMP(), 'WIRE-NEXT batch 6 (eyeball queue)')""").result()
        print(f"in_{t}: {n:,} ({mode}, {gb:.2f} GB)")
    except Exception as ex:
        print(f"ERROR {t}: {str(ex)[:120]}")
print("WIRE-NEXT BATCH 6 COMPLETE")
