"""C3 — join the RTEP upgrades to the located buses and substations.

THE GAP. 932 Indiana RTEP upgrades and 375 cost allocations sit on the Grid page, and 1,475
located PJM buses sit beside them, with no way to get from a bus to the upgrade attached to it.
A developer looking at a bus wants one thing: what is PJM planning to build here, what does it
cost, and is it already driven by load growth.

THE ONLY AVAILABLE KEY IS A NAME, AND THAT IS A WEAKNESS TO STATE, NOT HIDE. RTEP publishes
`location` as free text — "Dumont", "Dequine - Westwood #2" — naming a substation or the two
endpoints of a line. W17 says endpoints are mechanical, not name-matched, and this project has
already been burned once by name-token overlap (the "10 of 19 signals have no endpoint" error).
So every row here carries `match_method` and `match_confidence`, an exact-normalised match is
distinguished from a token match, and the measured yield is reported rather than the join being
tuned until it looks good.

WHAT IS DELIBERATELY NOT DONE: no fuzzy/edit-distance matching, and no nearest-substation
fallback. A wrong bus attached to a $40M upgrade is worse than an unmatched upgrade, because it
reads as a fact about a site.

Line locations of the form "A - B" are SPLIT into two endpoint rows, because an upgrade on a line
between two substations is relevant at BOTH ends and collapsing it to one loses half the answer.

Writes, and registers in the same run:
  in_rtep_bus_join      upgrade -> substation/bus, with method, confidence and endpoint role
  in_rtep_bus_summary   per-bus roll-up: what is planned here, and what it is driven by
"""
import datetime
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")
BUILT = datetime.datetime.now(datetime.timezone.utc).isoformat()


def q1(sql): return list(client.query(sql))[0]


def run(sql, label):
    j = client.query(sql); j.result()
    print(f"  {label}: {j.total_bytes_processed/1e9:.2f} GB", flush=True)


NORM = "UPPER(REGEXP_REPLACE(x, r'[^A-Za-z0-9]', ''))"

print("building in_rtep_bus_join …", flush=True)
run(f"""
CREATE OR REPLACE TABLE `{DS}.in_rtep_bus_join` AS
WITH
-- an upgrade location is either one substation or "A - B" naming a line's two endpoints.
-- SPLIT it: the upgrade matters at both ends, and collapsing to one loses half the answer.
ends AS (
  SELECT u.upgrade_id, u.task, u.equipment, u.driver, u.project_type, u.sub_region,
         u.description, u.criteria_violation, u.location AS raw_location,
         TRIM(part) AS endpoint_name,
         IF(ARRAY_LENGTH(SPLIT(u.location, ' - ')) > 1, 'line endpoint', 'single location') AS endpoint_role,
         off AS endpoint_index
  FROM `{DS}.in_pjm_rtep_upgrade_details` u,
       UNNEST(SPLIT(IFNULL(u.location, ''), ' - ')) AS part WITH OFFSET off
  WHERE u.location IS NOT NULL AND TRIM(u.location) != ''
),
e AS (
  SELECT *,
    -- strip a trailing circuit designator ("#2", "1") so "Westwood #2" matches "Westwood"
    UPPER(REGEXP_REPLACE(REGEXP_REPLACE(endpoint_name, r'\\s*#?\\d+\\s*$', ''), r'[^A-Za-z0-9]', '')) nk
  FROM ends WHERE TRIM(endpoint_name) != ''
),
subs AS (
  SELECT asset_id, substation_name, county, max_kv, min_kv, lat, lon, sources,
         UPPER(REGEXP_REPLACE(substation_name, r'[^A-Za-z0-9]', '')) nk
  FROM `{DS}.in_substations` WHERE substation_name IS NOT NULL
),
-- `bus_label` is a PSS/E name — '05PIPECK 138 kV (246763)' — truncated to eight characters with a
-- numeric area prefix. It can NEVER match RTEP's full substation text, and matching on it read
-- 0 of 1,475. Do not force it. The bus layer has ALREADY resolved 229 buses to a substation name
-- (`matched_substation_name`), so join through that instead: a mechanical hop through an existing
-- resolved field, not a second round of name guessing.
bus AS (
  SELECT bus_number, bus_label, bus_kv, lat AS bus_lat, lon AS bus_lon,
         matched_substation_name, match_confidence AS bus_loc_confidence,
         UPPER(REGEXP_REPLACE(matched_substation_name, r'[^A-Za-z0-9]', '')) nk
  FROM `{DS}.in_pjm_bus_locations_candidate`
  WHERE matched_substation_name IS NOT NULL
)
SELECT
  e.upgrade_id, e.task, e.equipment, e.driver, e.project_type, e.sub_region,
  e.description, e.criteria_violation,
  e.raw_location, e.endpoint_name, e.endpoint_role, e.endpoint_index,
  s.asset_id AS substation_id, s.substation_name, s.county AS substation_county,
  s.max_kv AS substation_max_kv, s.lat AS substation_lat, s.lon AS substation_lon, s.sources AS substation_sources,
  b.bus_number, b.bus_label, b.bus_kv, b.bus_lat, b.bus_lon, b.bus_loc_confidence,
  CASE WHEN s.nk IS NOT NULL AND b.nk IS NOT NULL THEN 'name matched BOTH a substation and a PJM bus'
       WHEN s.nk IS NOT NULL THEN 'name matched a substation only'
       WHEN b.nk IS NOT NULL THEN 'name matched a PJM bus only'
       ELSE 'no name match — the upgrade location is not a facility we hold' END AS match_method,
  -- evidence, not proof. A name match is a prompt to verify, never a placement.
  CASE WHEN s.nk IS NOT NULL AND b.nk IS NOT NULL THEN 'corroborated by two independent layers'
       WHEN s.nk IS NOT NULL OR b.nk IS NOT NULL THEN 'single-layer name match — verify before relying'
       ELSE 'unmatched' END AS match_confidence,
  TIMESTAMP('{BUILT}') AS built_at
FROM e
LEFT JOIN subs s ON s.nk = e.nk
LEFT JOIN bus  b ON b.nk = e.nk
""", "in_rtep_bus_join")

m = q1(f"""SELECT COUNT(*) rows_, COUNT(DISTINCT upgrade_id) upgrades,
  COUNT(DISTINCT IF(substation_id IS NOT NULL OR bus_number IS NOT NULL, upgrade_id, NULL)) matched_upgrades,
  COUNT(DISTINCT substation_id) subs, COUNT(DISTINCT bus_number) buses,
  COUNTIF(endpoint_role='line endpoint') line_ends
FROM `{DS}.in_rtep_bus_join`""")
tot = q1(f"SELECT COUNT(*) n FROM `{DS}.in_pjm_rtep_upgrade_details`").n
print(f"  {m.rows_:,} endpoint rows from {m.upgrades:,} upgrades ({tot:,} held; "
      f"{m.line_ends:,} rows are line endpoints)")
print(f"  MATCHED to a facility: {m.matched_upgrades:,} of {m.upgrades:,} upgrades "
      f"({100*m.matched_upgrades/max(m.upgrades,1):.1f}%) · "
      f"{m.subs:,} substations · {m.buses:,} PJM buses")
print("\n  by match method:")
for r in client.query(f"""SELECT match_method, COUNT(*) n, COUNT(DISTINCT upgrade_id) u
    FROM `{DS}.in_rtep_bus_join` GROUP BY 1 ORDER BY n DESC"""):
    print(f"    {r.match_method[:56]:56s} rows={r.n:>6,} upgrades={r.u:>5,}")

print("\nbuilding in_rtep_bus_summary …", flush=True)
run(f"""
CREATE OR REPLACE TABLE `{DS}.in_rtep_bus_summary` AS
SELECT
  COALESCE(bus_label, substation_name) AS facility,
  ANY_VALUE(bus_number) bus_number, ANY_VALUE(substation_id) substation_id,
  ANY_VALUE(substation_county) county,
  ANY_VALUE(COALESCE(bus_kv, substation_max_kv)) kv,
  ANY_VALUE(COALESCE(bus_lat, substation_lat)) lat,
  ANY_VALUE(COALESCE(bus_lon, substation_lon)) lon,
  COUNT(DISTINCT upgrade_id) upgrades,
  COUNT(DISTINCT IF(project_type='Baseline', upgrade_id, NULL)) baseline_upgrades,
  COUNT(DISTINCT IF(project_type='Supplemental', upgrade_id, NULL)) supplemental_upgrades,
  -- a LOAD-GROWTH driver at a bus is the signal a siter actually wants
  COUNT(DISTINCT IF(REGEXP_CONTAINS(LOWER(IFNULL(driver,'')), r'load growth'), upgrade_id, NULL))
    AS load_growth_upgrades,
  STRING_AGG(DISTINCT equipment ORDER BY equipment LIMIT 6) equipment_types,
  STRING_AGG(DISTINCT driver ORDER BY driver LIMIT 4) drivers,
  ANY_VALUE(match_confidence) match_confidence,
  TIMESTAMP('{BUILT}') AS built_at
FROM `{DS}.in_rtep_bus_join`
WHERE substation_id IS NOT NULL OR bus_number IS NOT NULL
GROUP BY facility
""", "in_rtep_bus_summary")

s = q1(f"""SELECT COUNT(*) facilities, SUM(upgrades) up,
  COUNTIF(load_growth_upgrades > 0) load_growth_facilities,
  COUNTIF(lat IS NOT NULL) located
FROM `{DS}.in_rtep_bus_summary`""")
print(f"  {s.facilities:,} facilities carrying {s.up:,} upgrade-links · "
      f"{s.load_growth_facilities:,} have a LOAD-GROWTH driver · {s.located:,} are located")
print("\n  busiest facilities:")
for r in client.query(f"""SELECT facility, county, kv, upgrades, load_growth_upgrades, equipment_types
    FROM `{DS}.in_rtep_bus_summary` ORDER BY upgrades DESC LIMIT 8"""):
    print(f"    {str(r.facility)[:26]:26s} {str(r.county or '-')[:12]:12s} {str(r.kv or '-'):>6} kV "
          f"upgrades={r.upgrades:>3} load-growth={r.load_growth_upgrades:>3} "
          f"{str(r.equipment_types)[:34]}")

for name, n, src, method in [
 ("in_rtep_bus_join", int(m.rows_),
  f"{DS}.in_pjm_rtep_upgrade_details + in_substations + in_pjm_bus_locations_candidate",
  "C3: RTEP upgrades joined to substations and PJM buses by NORMALISED NAME — the only key RTEP "
  "publishes. Line locations ('A - B') are split into two endpoint rows because an upgrade "
  "matters at both ends. Trailing circuit designators are stripped. NO fuzzy matching and NO "
  "nearest-substation fallback: a wrong bus attached to an upgrade reads as a fact about a site. "
  "Every row carries match_method and match_confidence; a single-layer name match is labelled "
  "'verify before relying' and a two-layer match 'corroborated'."),
 ("in_rtep_bus_summary", int(s.facilities), f"{DS}.in_rtep_bus_join",
  "per-facility roll-up: how many upgrades attach here, how many are Baseline vs Supplemental, "
  "and how many carry a LOAD GROWTH driver — the last being the signal a siter actually wants."),
]:
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{name}'").result()
    client.query(
        f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at) "
        f"VALUES (@t,@s,@m,@n,CURRENT_TIMESTAMP())",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", name),
            bigquery.ScalarQueryParameter("s", "STRING", src),
            bigquery.ScalarQueryParameter("m", "STRING", method),
            bigquery.ScalarQueryParameter("n", "INT64", n)])).result()
    print(f"registered {name} ({n:,})")
print("\nDONE")
