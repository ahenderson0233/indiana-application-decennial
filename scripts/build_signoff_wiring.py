"""Wire the eight operator sign-offs (approved 2026-08-15, per docs/SIGNOFF_PACKET.md v2).

Every column referenced here was value-read first (scratch probe, results in HANDOFF §5b).
Each table gets its _registry row IN THE SAME RUN. Idempotent: CREATE OR REPLACE throughout,
and the registry insert deletes its own prior row rather than accumulating duplicates.

  1 D11  admit the 983 TERMINAL dissolutions; exclude the 1,146 'withdrawn'
  2 D25  admit the 127 event filings; exclude the 747 procedural rows
  3 D27  admit all 156 UCC lapse rows
  4 IOCS county-grain only, EXCLUDING the 'STATE' total row and the 'nan' residue
  5 cloudscene 260 IN rows as a completeness cross-check (no coordinates - never a layer)
  6 airports  flag closed, no table needed (86-row curated set, 1 IN row, correct)
  7 queue_miso joined for the columns interconnection_queue lacks; NOT a second layer
  8 DC dedupe name-stem rule; the 8 unnamed OSM rows stay separate and are labelled
"""
import sys
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")
DRY = "--dry-run" in sys.argv

def build(table, sql, source, method, notes):
    full = f"{DS}.{table}"
    ddl = f"CREATE OR REPLACE TABLE `{full}` AS\n{sql}"
    dry = client.query(ddl, job_config=bigquery.QueryJobConfig(dry_run=True))
    gb = dry.total_bytes_processed / 1e9
    print(f"\n[{table}] dry-run {gb:.2f} GB", flush=True)
    if DRY:
        return
    client.query(ddl).result()
    n = list(client.query(f"SELECT COUNT(*) n FROM `{full}`"))[0].n
    # registry: replace this table's row, never accumulate duplicates across reruns
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{table}'").result()
    client.query(f"""INSERT `{DS}._registry`
        (table_name, source, method, n_rows, gb_scanned, built_at, notes)
        VALUES (@t, @s, @m, @n, @g, CURRENT_TIMESTAMP(), @o)""",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", table),
            bigquery.ScalarQueryParameter("s", "STRING", source),
            bigquery.ScalarQueryParameter("m", "STRING", method),
            bigquery.ScalarQueryParameter("n", "INT64", n),
            bigquery.ScalarQueryParameter("g", "FLOAT64", round(gb, 4)),
            bigquery.ScalarQueryParameter("o", "STRING", notes)])).result()
    print(f"[{table}] {n:,} rows, registered", flush=True)

# ---- 1. D11: terminal dissolutions only -------------------------------------------------
build("in_si_d11_admitted", f"""
SELECT * EXCEPT(status_family), status_family,
       'D11_entity_dissolution' AS admitted_signal
FROM `{DS}.in_si_d11_entity_dissolution`
WHERE LOWER(status_family) IN ('dissolved','revoked','forfeited','void')""",
  "indiana_app.in_si_d11_entity_dissolution",
  "operator sign-off 2026-08-15: admit terminal status families only",
  "983 of 2,129. EXCLUDES status_family='withdrawn' (1,146) - 'Surrendered'/'Withdrawn - Can "
  "Reinstate' is an out-of-state entity giving up authority or a reinstatable lapse, which is "
  "weaker evidence that a property is coming free. Every admitted row carries an address.")

# ---- 2. D25: event filings only ---------------------------------------------------------
build("in_si_d25_admitted", f"""
SELECT *, SAFE.PARSE_DATE('%m/%d/%Y', filed_date) AS filed_date_parsed,
       'D25_rail_abandonment' AS admitted_signal
FROM `{DS}.in_si_d25_stb_abandonment_state`
WHERE filing_type IN ('Notice Of Exemption','Consummation Notice','Petition For Exemption')""",
  "indiana_app.in_si_d25_stb_abandonment_state",
  "operator sign-off 2026-08-15: admit abandonment EVENTS, not the paperwork about them",
  "127 of 874. EXCLUDES procedural filings (Reply 185, Request For Extension Of Time 150, "
  "Certificate Of Service 26, Modify/Supplement 30, Protest 22, ...) which are correspondence "
  "about a docket, not an abandonment. filed_date is a STRING m/d/Y upstream - parsed into "
  "filed_date_parsed, all 127 parsing cleanly. Range 2002-06-21 to 2026-01-05; the newest is a "
  "Central Railroad Company of Indianapolis abandonment exemption. NOTE for anyone reading this "
  "column: MIN/MAX on the raw STRING date is LEXICOGRAPHIC and lies - '9/5/2019' outranks "
  "'1/23/2017' on the leading character. Always aggregate filed_date_parsed.")

# ---- 3. D27: all 156 --------------------------------------------------------------------
build("in_si_d27_admitted", f"""
SELECT *, 'D27_ucc_lapse' AS admitted_signal FROM `{DS}.in_si_d27_ucc_lapse_v2`""",
  "indiana_app.in_si_d27_ucc_lapse_v2",
  "operator sign-off 2026-08-15: admit all rows as D27 candidates",
  "156 rows, all keying='address' at quality_mult 0.8, every one carrying address+zip. "
  "NOTE 154 distinct filing_id over 156 rows - two ids repeat; not deduped pending a rule.")

# ---- 4. IOCS county context (the two poison rows excluded) ------------------------------
build("in_iocs_county_context", f"""
WITH agg AS (
  SELECT UPPER(TRIM(County_Name)) AS county_upper,
         SUM(SAFE_CAST(MF AS INT64)) AS mortgage_foreclosures,
         SUM(SAFE_CAST(EV AS INT64)) AS evictions,
         SUM(SAFE_CAST(SC AS INT64)) AS small_claims,
         COUNT(*) AS court_rows
  FROM `{DS}.in_si_refresh_iocs_eviction`
  WHERE County_Name IS NOT NULL AND UPPER(TRIM(County_Name)) NOT IN ('STATE','NAN')
  GROUP BY 1)
SELECT b.GEOID AS county_fips, b.NAME AS county_name, agg.* EXCEPT(county_upper)
FROM agg JOIN `{EN}.county_boundaries` b
  ON b.STATEFP='18' AND UPPER(TRIM(b.NAME)) = agg.county_upper""",
  "indiana_app.in_si_refresh_iocs_eviction x energy.county_boundaries",
  "operator sign-off 2026-08-15: COUNTY GRAIN ONLY, poison rows excluded",
  "MF is a per-court COLUMN of counts, never a per-address event, so it cannot be a "
  "parcel-grain signal at any confidence. EXCLUDES County_Name='STATE' (a statewide TOTAL row) "
  "and 'nan' - together they were 62% of the MF sum (83,446 -> 31,535) and 66% of EV "
  "(442,076 -> 151,986), which is why the raw county list read 94 names for a 92-county state. "
  "All 92 names join county_boundaries exactly.")

# ---- 5. cloudscene: completeness cross-check, never a layer -----------------------------
build("in_cloudscene_crosscheck", f"""
SELECT cloudscene_slug, name, city, market, url,
       CAST(NULL AS FLOAT64) AS lat, CAST(NULL AS FLOAT64) AS lon
FROM `{EN}.data_centers_cloudscene`
WHERE market IN ('indiana-regional','indianapolis','south-bend','fort-wayne','evansville')""",
  "energy.data_centers_cloudscene",
  "operator sign-off 2026-08-15: Data-page completeness cross-check only",
  "260 Indiana rows found via `market`, which IS cloudscene's state key (<state>-regional "
  "buckets run across the table). `state` is blank for 5,283 of 5,388 rows and is useless. "
  "THIS TABLE HAS NO COORDINATES - lat/lon are explicit NULLs so nothing can plot it by "
  "accident. Its only job is to answer 'how many cloudscene names do we already hold pinned?'")

# ---- 7. queue_miso: the columns interconnection_queue has no field for ------------------
build("in_queue_miso_extras", f"""
SELECT UPPER(TRIM(projectnumber)) AS project_key, projectnumber, county, state,
       poiname, studyphase, studygroup, studycycle, svctype, facilitytype, fueltype,
       dp1erismw, dp1nrismw, dp2erismw, dp2nrismw, summernetmw, winternetmw,
       applicationstatus, transmissionowner, queuedate, inservice
FROM `{EN}.queue_miso` WHERE UPPER(TRIM(state))='IN'""",
  "energy.queue_miso",
  "operator sign-off 2026-08-15: JOIN table, not a second queue layer",
  "456 Indiana rows; 452 of their project numbers already exist in interconnection_queue, so "
  "rendering both would double-count the queue on any map or total. Kept for the columns the "
  "other table has no field for: studyphase (442 filled), poiname (455 - joins to our bus "
  "work), and the DPP ERIS/NRIS MW split (456).")

# ---- 8. DC dedupe: name-stem rule, unnamed rows kept and labelled -----------------------
build("in_data_centers_deduped", f"""
WITH n AS (
  SELECT src, name, operator, lat, lon,
         REGEXP_REPLACE(LOWER(IFNULL(name,'')), r'[^a-z0-9]','') AS stem
  FROM `{DS}.in_data_centers_all`),
-- a row is absorbed when another SOURCE holds a name-stem that is a prefix of, or prefixed
-- by, this one within 500 m. Keep the row from the source that sorts first, deterministically.
absorbed AS (
  SELECT b.src, b.name, b.lat, b.lon
  FROM n a JOIN n b ON a.src < b.src
   AND ST_DWITHIN(ST_GEOGPOINT(a.lon,a.lat), ST_GEOGPOINT(b.lon,b.lat), 500)
  WHERE LENGTH(a.stem) > 3 AND LENGTH(b.stem) > 3
    AND (STARTS_WITH(a.stem, b.stem) OR STARTS_WITH(b.stem, a.stem)))
SELECT n.src, n.name, n.operator, n.lat, n.lon,
       n.name IS NULL AS unnamed_cannot_dedupe,
       CASE WHEN n.name IS NULL THEN 'kept - no name to match on'
            ELSE 'kept - distinct name-stem' END AS dedupe_note
FROM n
WHERE NOT EXISTS (SELECT 1 FROM absorbed x
                  WHERE x.src = n.src AND IFNULL(x.name,'') = IFNULL(n.name,'')
                    AND x.lat = n.lat AND x.lon = n.lon)""",
  "indiana_app.in_data_centers_all",
  "operator sign-off 2026-08-15: same name-stem within 500 m collapses to one row",
  "Rule applied honestly: it collapses exactly 3 pairs (Expedient Indianapolis 5 m; Digital "
  "Crossroad at 17 m and 127 m). It deliberately does NOT merge 'Amazon: New Carlisle II DC8' "
  "into OSM's generic 'Amazon AWS Data Center' - those are separate buildings on one campus, "
  "and a distance-only rule would have eaten the whole campus into a single pin. OSM's 8 "
  "UNNAMED rows cannot be judged by a name rule, so they are KEPT and flagged "
  "unnamed_cannot_dedupe - visible as possible duplicates rather than silently merged or "
  "silently dropped.")

print("\nSIGN-OFF WIRING COMPLETE" if not DRY else "\nDRY RUN ONLY - nothing written")
