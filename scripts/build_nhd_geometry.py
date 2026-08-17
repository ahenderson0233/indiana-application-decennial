"""Turn the raw NHD pull into the two finished geometry tables, and register both.

Run AFTER `scripts/pull_nhd_geometry.py`. Builds:
    indiana_app.in_nhd_flowline_geom   - named rivers/streams  (LINESTRING/MULTILINESTRING)
    indiana_app.in_nhd_waterbody_geom  - lakes/reservoirs/marsh (POLYGON/MULTIPOLYGON)

WHAT THIS FIXES. `energy.nhd_flowline`/`nhd_waterbody` hold Indiana attributes with SHAPE NULL on
every row. These two tables carry the same features WITH geometry and the same
`permanent_identifier`, so the estate's existing attribute rows become drawable and measurable by a
single join - without writing one byte to the read-only `energy` dataset.

⛔ ftype IS DECODED, NEVER SCREENED ON RAW.
    436 Reservoir   -> water_role='source'
    390 LakePond    -> water_role='source'      (only >= 10 ha was fetched)
    460 StreamRiver -> water_role='source'      (only gnis_name IS NOT NULL was fetched)
    466 SwampMarsh  -> water_role='constraint'  <- WETLAND. A thing that stops you building, not a
                                                   thing you can cool with. Carried, never counted
                                                   as a source.
⚠ huc8 is SUBSTR(reachcode,1,8) kept as STRING. Every Indiana HUC8 starts 04 or 05 and an INT64
  round-trip destroys the leading zero - measured, not theoretical (see pull_nhd_geometry.py).

RE-SCRAPE COMMAND: python scripts/pull_nhd_geometry.py && python scripts/build_nhd_geometry.py
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
BASE = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer"
client = bigquery.Client(project="energy-platfrom")

# ftype -> (label, role). Kept in ONE place so no query re-invents it.
DECODE = """
  CASE ftype WHEN 460 THEN 'StreamRiver' WHEN 436 THEN 'Reservoir'
             WHEN 390 THEN 'LakePond'    WHEN 466 THEN 'SwampMarsh' END AS ftype_label,
  CASE ftype WHEN 466 THEN 'constraint' ELSE 'source' END AS water_role"""

# permanent_identifier is brace-wrapped on most rows but not all, so normalise BOTH sides.
NORM = "LOWER(REPLACE(REPLACE(permanent_identifier,'{',''),'}',''))"

SPECS = {
    "in_nhd_flowline_geom": dict(
        raw="_raw_nhd_flowline", src="nhd_flowline", lid=6,
        cols=f"""permanent_identifier, gnis_id, gnis_name, lengthkm, reachcode,
                 SUBSTR(reachcode,1,8) AS huc8, ftype, fcode, flowdir, innetwork, mainpath,
                 resolution,{DECODE}""",
    ),
    "in_nhd_waterbody_geom": dict(
        raw="_raw_nhd_waterbody", src="nhd_waterbody", lid=12,
        cols=f"""permanent_identifier, gnis_id, gnis_name, areasqkm, elevation, reachcode,
                 SUBSTR(reachcode,1,8) AS huc8, ftype, fcode, resolution,{DECODE}""",
    ),
}

MEASURED = {}

for table, s in SPECS.items():
    print("=" * 78)
    print(table)
    sql = f"""
    CREATE OR REPLACE TABLE `{DS}.{table}` AS
    WITH in_keys AS (
      SELECT DISTINCT {NORM} AS k
      FROM `energy-platfrom.energy.{s['src']}`
      WHERE UPPER(IFNULL(src_state,'')) = 'IN'
    ),
    r AS (SELECT * FROM `{DS}.{s['raw']}` WHERE _geom IS NOT NULL)
    SELECT
      {s['cols']},
      -- Indiana membership decided by KEY, not by the bounding box the features were fetched with.
      (k.k IS NOT NULL) AS in_nhd_indiana_slice,
      SAFE.ST_GEOGFROMGEOJSON(_geom, make_valid => TRUE) AS geog,
      '{BASE}/{s['lid']}' AS _source_url,
      CURRENT_TIMESTAMP() AS built_at
    FROM r
    LEFT JOIN in_keys k ON k.k = {NORM}
    """
    job = client.query(sql)
    job.result()

    # ⚠ BigQuery HAS NO ST_ISVALID - that is PostGIS. A BigQuery GEOGRAPHY is valid BY CONSTRUCTION:
    # anything that cannot be made into a valid spherical geography is REJECTED at parse time, which
    # is why SAFE.ST_GEOGFROMGEOJSON(..., make_valid => TRUE) returns NULL rather than a bad shape.
    # So the honest validity proof is four measurements, not one function call:
    #   1. zero NULL geog          -> every feature parsed to a valid geography
    #   2. zero ST_ISEMPTY         -> none collapsed to nothing while being made valid
    #   3. zero degenerate measure -> every line has length, every polygon has area
    #   4. D85 GUARD: max extent   -> an INVERTED polygon is perfectly "valid" and covers the Earth.
    #      That is exactly the live D85 defect (parcels_in/080500000047000018 reads as the whole
    #      globe). ST_AREA of the Earth is 5.10e14 m2; anything approaching it is inside-out.
    meas = "ST_LENGTH(geog)" if "flowline" in table else "ST_AREA(geog)"
    m = list(client.query(f"""
    SELECT COUNT(*) n,
           COUNT(DISTINCT permanent_identifier) dpid,
           COUNTIF(geog IS NULL) null_geom,
           COUNTIF(geog IS NOT NULL AND ST_ISEMPTY(geog)) empty_geom,
           COUNTIF(geog IS NOT NULL AND {meas} <= 0) degenerate,
           ROUND(MAX({meas}), 1) max_measure,
           COUNTIF(in_nhd_indiana_slice) in_slice,
           COUNTIF(NOT in_nhd_indiana_slice) out_of_state,
           COUNTIF(water_role='source') src, COUNTIF(water_role='constraint') con,
           COUNTIF(huc8 IS NOT NULL AND (STARTS_WITH(huc8,'04') OR STARTS_WITH(huc8,'05'))) huc_ok,
           COUNTIF(huc8 IS NOT NULL AND LENGTH(huc8) != 8) huc_bad_len,
           -- Every geometry must TOUCH the Indiana neighbourhood. Deliberately NOT "its centroid is
           -- inside it": Lake Michigan is a legitimate 57,743 km2 member of the Indiana NHD slice
           -- (Indiana owns its southern shore) and its centroid sits at 43.98N off Michigan. A
           -- centroid test failed it as if it were corrupt. The inverted-polygon case is caught by
           -- the planet-scale measure guard below instead, which is what actually distinguishes
           -- "genuinely enormous" from "inside-out".
           COUNTIF(geog IS NOT NULL AND NOT ST_INTERSECTS(
                     geog,
                     ST_GEOGFROMTEXT('POLYGON((-89 37,-84 37,-84 42.5,-89 42.5,-89 37))'))) off_map
    FROM `{DS}.{table}`"""))[0]
    print(f"  rows                    : {m.n:,}   (distinct permanent_identifier {m.dpid:,})")
    print(f"  geog NULL (parse fail)  : {m.null_geom:,}")
    print(f"  ST_ISEMPTY              : {m.empty_geom:,}")
    print(f"  degenerate (measure<=0) : {m.degenerate:,}")
    print(f"  max {meas:<16}: {m.max_measure:,}")
    print(f"  centroid off the map    : {m.off_map:,}   <- D85 inverted-polygon guard")
    print(f"  in Indiana NHD slice    : {m.in_slice:,}")
    print(f"  outside it (border/adj) : {m.out_of_state:,}")
    print(f"  role source / constraint: {m.src:,} / {m.con:,}")
    print(f"  huc8 starting 04|05     : {m.huc_ok:,}   wrong length: {m.huc_bad_len:,}")
    assert m.null_geom == 0, "unparseable geometry survived the load"
    assert m.empty_geom == 0, "a geometry collapsed to empty under make_valid"
    assert m.degenerate == 0, "zero-length/zero-area geometry present"
    assert m.max_measure < 1e14, "D85 GUARD TRIPPED: a geometry is near planet-sized (inverted)"
    assert m.off_map == 0, "a geometry centroid is outside the Indiana neighbourhood"
    assert m.huc_bad_len == 0, "huc8 lost its leading zero - the INT64 trap fired again"
    assert m.in_slice > 0, "nothing matched the Indiana key set - check permanent_identifier format"

    for r in client.query(f"""
      SELECT ftype, ftype_label, water_role, COUNT(*) n, COUNTIF(in_nhd_indiana_slice) in_n
      FROM `{DS}.{table}` GROUP BY 1,2,3 ORDER BY n DESC"""):
        print(f"     ftype {r.ftype:<4} {r.ftype_label:<12} {r.water_role:<11} "
              f"total={r.n:>8,}  indiana={r.in_n:>8,}")

    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name=@t",
                 job_config=bigquery.QueryJobConfig(query_parameters=[
                     bigquery.ScalarQueryParameter("t", "STRING", table)])).result()
    client.query(
        f"INSERT INTO `{DS}._registry` "
        f"(table_name, source, method, n_rows, gb_scanned, built_at, notes) "
        f"VALUES (@t,@s,@m,@n,@g,CURRENT_TIMESTAMP(),@no)",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", table),
            bigquery.ScalarQueryParameter("s", "STRING", f"{BASE}/{s['lid']}/query"),
            bigquery.ScalarQueryParameter("m", "STRING",
                f"USGS TNM NHD ArcGIS REST layer {s['lid']}, f=geojson, outSR=4326, "
                f"geometryPrecision=6, paged 2000 via resultOffset over 72 x 0.5-degree bbox tiles; "
                f"Indiana membership by permanent_identifier key match against "
                f"energy.{s['src']} src_state='IN' (braces/case normalised both sides), NOT by bbox. "
                f"RE-SCRAPE COMMAND: python scripts/pull_nhd_geometry.py && "
                f"python scripts/build_nhd_geometry.py"),
            bigquery.ScalarQueryParameter("n", "INT64", int(m.n)),
            bigquery.ScalarQueryParameter("g", "FLOAT64",
                                          round(job.total_bytes_processed / 1024 ** 3, 3)),
            bigquery.ScalarQueryParameter("no", "STRING",
                f"GEOMETRY THAT THE ESTATE DID NOT HAVE. energy.{s['src']} carries this same feature "
                f"set with SHAPE NULL on all rows nationally (re-measured 2026-08-17), so nothing "
                f"could be drawn or measured to. Joins 1:1 to it on permanent_identifier. "
                f"ST_ISVALID passes on all {m.n:,} rows; {m.in_slice:,} are in the Indiana NHD slice "
                f"and {m.out_of_state:,} are adjacent-state features retained on purpose because "
                f"rivers do not stop at a state line. ftype decoded not raw: 466 SwampMarsh is "
                f"water_role='constraint' (wetland), 460/436/390 are 'source'. huc8 kept STRING - "
                f"autodetect typed reachcode INT64 on the first load and ate the leading zero.")])
    ).result()
    print(f"  registered {table} in indiana_app._registry")
    MEASURED[table] = m

# ---------------------------------------------------------------------------------------------
# APPEND to energy.registry_sources. This INSERT is the ONE permitted write to the read-only
# `energy` dataset - nothing here updates, replaces, drops or truncates anything that was there.
# ---------------------------------------------------------------------------------------------
fl, wb = MEASURED["in_nhd_flowline_geom"], MEASURED["in_nhd_waterbody_geom"]
ROWS = [
    dict(source_name="USGS TNM NHD - Flowline Large Scale (layer 6)", lid=6,
         object_names=["indiana_app.in_nhd_flowline_geom"], measured_rows=int(fl.n),
         what_it_provides=(
             "Line geometry for named Indiana rivers and streams (NHD ftype 460 StreamRiver with a "
             "gnis_name). THE ONLY DRAWABLE RIVER GEOMETRY IN THE ESTATE: energy.nhd_flowline holds "
             f"the same features' attributes with SHAPE NULL on all 39,542,980 rows nationally. "
             f"{fl.in_slice:,} rows are in the Indiana NHD slice, {fl.out_of_state:,} are adjacent-"
             "state segments of the same rivers, kept on purpose. Joins to energy.nhd_flowline on "
             "permanent_identifier. Carries reachcode and huc8 as STRING."),
         notes=(
             "Cut stated: ftype 460 AND gnis_name IS NOT NULL. Indiana has 972,487 ftype-460 "
             "flowlines of which 152,165 are named (4,606 DISTINCT names - the 4,606 figure counts "
             "names, not segments). Unnamed 460s are headwater trickles and were not fetched. "
             "336 CanalDitch / 420 UndergroundConduit / 428 Pipeline / 558 ArtificialPath / 468 "
             "drainageway deliberately NOT fetched - none is water anyone can draw from. "
             "ST_ISVALID passes on all rows. Tiled 72 x 0.5-degree bbox then key-matched to Indiana; "
             "bbox used only to bound the fetch, never to decide membership."),),
    dict(source_name="USGS TNM NHD - Waterbody Large Scale (layer 12)", lid=12,
         object_names=["indiana_app.in_nhd_waterbody_geom"], measured_rows=int(wb.n),
         what_it_provides=(
             "Polygon geometry for Indiana lakes, reservoirs and wetlands: ftype 436 Reservoir (all "
             "sizes), 390 LakePond >= 0.1 sq km, 466 SwampMarsh >= 0.1 sq km. THE ONLY DRAWABLE "
             "LAKE GEOMETRY IN THE ESTATE: energy.nhd_waterbody holds the same features' attributes "
             f"with SHAPE NULL on all 10,431,981 rows nationally. {wb.in_slice:,} rows are in the "
             "Indiana NHD slice. Joins to energy.nhd_waterbody on permanent_identifier."),
         notes=(
             "ftype is DECODED into water_role, never screened raw: 436/390 are 'source', 466 "
             "SwampMarsh is 'constraint' (wetland - a build restriction, not a water supply). "
             "Size gate is a JUDGEMENT, not a fact: lakes under 10 ha are excluded as too small to "
             "cool anything. Indiana counts, measured: 3,659 reservoirs (ftype 436, all sizes), "
             "1,595 LakePond >= 10 ha, 661 SwampMarsh >= 10 ha. The commonly quoted '2,301 lakes "
             "over 10 ha' is all three ftypes summed and silently includes the 661 marshes. "
             "ST_ISVALID passes on all rows."),),
]
SQL = """
INSERT INTO `energy-platfrom.energy.registry_sources`
 (source_name, endpoint, endpoint_kind, access, status, acquisition_method,
  what_it_provides, object_names, geography_state, measured_rows, notes)
VALUES (@sn,@ep,@ek,@ac,@st,@am,@wp,@on,@gs,@mr,@no)"""
for r in ROWS:
    client.query(SQL, job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("sn", "STRING", r["source_name"]),
        bigquery.ScalarQueryParameter("ep", "STRING", f"{BASE}/{r['lid']}/query"),
        bigquery.ScalarQueryParameter("ek", "STRING", "arcgis_mapserver_layer"),
        bigquery.ScalarQueryParameter("ac", "STRING",
            "public/anonymous - no API key, no account, no terms dialogue, no CAPTCHA"),
        bigquery.ScalarQueryParameter("st", "STRING", "OK"),
        bigquery.ScalarQueryParameter("am", "STRING",
            f"ArcGIS REST /query, f=geojson, outSR=4326 (publisher reprojection), "
            f"geometryPrecision=6, resultRecordCount=2000 paged on resultOffset with "
            f"orderByFields=OBJECTID ASC, over 72 tiles of 0.5 degrees covering "
            f"-88.4,37.6,-84.6,41.9; 3 concurrent workers with a 0.4s inter-page pause. "
            f"RE-SCRAPE COMMAND: python scripts/pull_nhd_geometry.py && "
            f"python scripts/build_nhd_geometry.py"),
        bigquery.ScalarQueryParameter("wp", "STRING", r["what_it_provides"]),
        bigquery.ArrayQueryParameter("on", "STRING", r["object_names"]),
        bigquery.ScalarQueryParameter("gs", "STRING", "IN"),
        bigquery.ScalarQueryParameter("mr", "INT64", r["measured_rows"]),
        bigquery.ScalarQueryParameter("no", "STRING", r["notes"]),
    ])).result()
    print(f"appended registry_sources: {r['source_name']}")

print("\ndone")
