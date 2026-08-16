"""Give the parcel layer a REAL si_last_event_date, by bridging the address-keyed signal rows.

THE PROBLEM (already measured, not re-litigated here)
-----------------------------------------------------
`indiana_app.in_si_signals` splits cleanly by `keying`, and the split is pathological:
the parcel-keyed rows carry NO event date, and the dated rows are NOT parcel-keyed.

    keying         rows      parcel-keyed    dated
    parcel         945,896   945,896         0
    address_norm   854,840   0               854,006
    parcel_key       6,950   6,950           6,950
    address          6,464   0               4,859

Consequence: `in_sites.si_last_event_date` is populated for 2,985 of 847,410 signal-flagged
parcels (0.35%), so RECENCY CANNOT FILTER ANYTHING. A 2011 code violation and a 2026 tax sale
are indistinguishable to every downstream query.

THE BRIDGE — FOUND, NOT WRITTEN
-------------------------------
⛔ NO ADDRESS-NORMALISATION FUNCTION IS DEFINED IN THIS FILE, AND ITS ABSENCE IS THE POINT.
The standing project rule is that a hand-rolled regex chain plus a self-reported match rate is
worse than no bridge at all. So the first question was not "how do I normalise these" but
"who already did". The answer is `energy.mat_si_address_location`, which carries the SAME
`address_norm` string the signal rows carry, produced by the same upstream normaliser.

That this is genuinely the same normaliser is MEASURED, not assumed: exact string equality and
UPPER(TRIM()) equality both return 94,010 addresses. Delta = 0. There is no casing or whitespace
drift to "fix", which is precisely the evidence that no new normalisation belongs here.

`mat_si_address_location` maps address_norm -> (build_id, lat, lon). It does NOT carry a parcel
key, so it is half a bridge; the second half is `in_sites`, which carries both `build_id` and
`parcel_geog`. Two independent routes therefore exist, and BOTH are computed so they can check
each other:

    tier 1  build_id equality AND point-in-parcel agree   -> confidence high
    tier 2  build_id equality only                        -> confidence medium_high
    tier 3  point-in-parcel only                          -> confidence medium

⛔ THE SPATIAL ROUTE MATCHED 100.0% ON ITS FIRST RUN AND THAT WAS A DEFECT, NOT A TRIUMPH.
51,821/51,821 addresses matched, at a fan-out of 2.0. A perfect result is a claim about the
instrument (§6), and the instrument was lying: `in_sites` contains ONE parcel,
`parcels_in / 080500000047000018`, whose polygon is 196,936,707 sq miles — the whole Earth,
an inverted ring — and whose structure_count reads 3,377,472. It CONTAINS EVERY POINT ON THE
GLOBE, so it silently caught all 51,821 addresses. This is DISCOVERIES D85, still live and
unrepaired upstream. Excluding that single parcel drops the spatial match to 50,865 (98.2%) at
a fan-out of 1.015, which is what a healthy point-in-polygon join looks like. Every spatial
query below carries the exclusion, and it must stay until D85 is fixed at source.

WHAT IS NOT SOLVED, AND WHY THE CEILING IS 20.7%
------------------------------------------------
Of the 250,063 distinct address_norm values in the signal rows, only 94,010 (37.6%) appear in
`mat_si_address_location` at all, and only 51,821 (20.7%) are RESOLVED there — the other 44,146
sit in the table with location_method='unresolved'. The ceiling is therefore the coverage of the
upstream geocode, NOT the join, and NOT the normalisation. Tuning a matcher here cannot move it.
This is the metro-PoC scope showing through: the geocode was built for metros.

`mat_si_rooftop_geocode` was checked as an alternative and is WORSE, not better: its only 5,880
Indiana rows are all method_version='v1_INVALID_20260804_state_centroid_D37' — state centroids,
which the platform's own `vw_si_rooftop_geocode_valid` view filters out entirely. Indiana has
zero valid rows in it. `mat_si_building_in_parcel` holds only 5,222 Indiana addresses and carries
`parcel_source` WITHOUT `parcel_key`, so it cannot complete a parcel join at all.

FUTURE DATES ARE REAL HERE AND ARE NOT CLIPPED
----------------------------------------------
14,304 address-keyed rows carry observed_date > today (D1_tax_sale scheduled sale dates run to
2026-09-28; D20_loan_maturity runs to 2036-03-01). These are FORWARD-LOOKING events, not dirty
data — a scheduled tax sale is the strongest seller-intent signal there is. They are kept, but
`max_observed_date` and `max_past_observed_date` are carried SEPARATELY so that nobody reads
"2036-03-01" as evidence of recent activity.

Writes ONLY to energy-platfrom.indiana_app. `energy.*` is read-only.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")

# DISCOVERIES D85: the inverted full-globe parcel. Excluded from every spatial predicate.
GLOBE = "NOT (parcel_source='parcels_in' AND parcel_key='080500000047000018')"

# the resolved half-bridge: address_norm -> build_id/lat/lon, from the EXISTING normaliser
BRIDGE_SRC = f"""
  SELECT address_norm, build_id, lat, lon, precision_tier, location_method
  FROM `{EN}.mat_si_address_location`
  WHERE state='IN' AND location_method != 'unresolved'
"""

TOTAL_GB = 0.0


def dry(sql):
    return client.query(sql, job_config=bigquery.QueryJobConfig(
        dry_run=True, use_query_cache=False)).total_bytes_processed / 1e9


def go(sql, label, cap=50.0):
    """Dry-run, print the GB, refuse anything over the cap, then run."""
    global TOTAL_GB
    gb = dry(sql)
    print(f"  [dry-run {gb:7.3f} GB] {label}")
    if gb > cap:
        raise SystemExit(f"REFUSED: {label} would scan {gb:.1f} GB (cap {cap})")
    TOTAL_GB += gb
    return client.query(sql).result()


def one(sql, label, cap=50.0):
    return list(go(sql, label, cap))[0]


def rows(sql, label, cap=50.0):
    return list(go(sql, label, cap))


def register(table, source, method, n_rows, gb, notes):
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name=@t",
                 job_config=bigquery.QueryJobConfig(query_parameters=[
                     bigquery.ScalarQueryParameter("t", "STRING", table)])).result()
    client.query(f"""INSERT `{DS}._registry`
        (table_name, source, method, n_rows, gb_scanned, built_at, notes)
        VALUES (@t,@s,@m,@n,@g,CURRENT_TIMESTAMP(),@o)""",
                 job_config=bigquery.QueryJobConfig(query_parameters=[
                     bigquery.ScalarQueryParameter("t", "STRING", table),
                     bigquery.ScalarQueryParameter("s", "STRING", source),
                     bigquery.ScalarQueryParameter("m", "STRING", method),
                     bigquery.ScalarQueryParameter("n", "INT64", int(n_rows)),
                     bigquery.ScalarQueryParameter("g", "FLOAT64", float(gb)),
                     bigquery.ScalarQueryParameter("o", "STRING", notes)])).result()
    print(f"  registered {table}  n_rows={n_rows:,}")


# ---------------------------------------------------------------- 0. the ceiling, restated
print("\n" + "=" * 78 + "\n0. THE CEILING (why no matcher tuning can help)\n" + "=" * 78)
c = one(f"""
WITH a AS (SELECT DISTINCT address_norm FROM `{DS}.in_si_signals`
           WHERE keying IN ('address_norm','address') AND address_norm IS NOT NULL),
     m AS (SELECT address_norm, location_method
           FROM `{EN}.mat_si_address_location` WHERE state='IN')
SELECT (SELECT COUNT(*) FROM a) sig_addr,
       (SELECT COUNT(*) FROM a JOIN m USING(address_norm)) present,
       (SELECT COUNT(*) FROM a JOIN m USING(address_norm)
        WHERE m.location_method!='unresolved') resolved,
       (SELECT COUNT(DISTINCT a.address_norm) FROM a JOIN m
        ON UPPER(TRIM(a.address_norm))=UPPER(TRIM(m.address_norm))) upper_trim
""", "ceiling + normaliser-identity check")
print(f"    distinct signal address_norm ......... {c.sig_addr:,}")
print(f"    present in mat_si_address_location ... {c.present:,} ({100*c.present/c.sig_addr:.1f}%)")
print(f"    ... and RESOLVED there ............... {c.resolved:,} ({100*c.resolved/c.sig_addr:.1f}%)  <- hard ceiling")
print(f"    exact-equality vs UPPER(TRIM) delta .. {c.upper_trim - c.present}  "
      f"(0 => same normaliser, nothing to 'fix')")

# ---------------------------------------------------------------- 1. the bridge table
print("\n" + "=" * 78 + "\n1. BUILD in_si_address_parcel_bridge\n" + "=" * 78)
BRIDGE_SQL = f"""
CREATE OR REPLACE TABLE `{DS}.in_si_address_parcel_bridge`
CLUSTER BY address_norm AS
WITH b AS ({BRIDGE_SRC}),
     -- structure-identity route: the address's building IS this parcel's principal structure
     sb AS (SELECT build_id, parcel_source, parcel_key FROM `{DS}.in_sites`
            WHERE build_id IS NOT NULL AND {GLOBE}),
     -- geometric route. D85 globe parcel excluded or this matches 100% and means nothing.
     sg AS (SELECT parcel_source, parcel_key, parcel_geog FROM `{DS}.in_sites`
            WHERE parcel_geog IS NOT NULL AND {GLOBE}),
     viaB AS (SELECT b.address_norm, b.build_id, b.lat, b.lon, b.precision_tier,
                     sb.parcel_source, sb.parcel_key, 'b' AS via
              FROM b JOIN sb USING(build_id)),
     viaS AS (SELECT b.address_norm, b.build_id, b.lat, b.lon, b.precision_tier,
                     sg.parcel_source, sg.parcel_key, 's' AS via
              FROM b JOIN sg ON ST_CONTAINS(sg.parcel_geog, ST_GEOGPOINT(b.lon, b.lat))),
     u AS (
       SELECT address_norm, parcel_source, parcel_key,
              ANY_VALUE(build_id) build_id, ANY_VALUE(lat) lat, ANY_VALUE(lon) lon,
              ANY_VALUE(precision_tier) precision_tier,
              LOGICAL_OR(via='b') has_build_id, LOGICAL_OR(via='s') has_spatial
       FROM (SELECT * FROM viaB UNION ALL SELECT * FROM viaS)
       GROUP BY 1,2,3)
SELECT address_norm, parcel_source, parcel_key, build_id, lat, lon, precision_tier,
       has_build_id, has_spatial,
       CASE WHEN has_build_id AND has_spatial THEN 1 WHEN has_build_id THEN 2 ELSE 3 END AS match_tier,
       CASE WHEN has_build_id AND has_spatial
              THEN 'mat_si_address_location.build_id = in_sites.build_id, CONFIRMED by ST_CONTAINS(in_sites.parcel_geog)'
            WHEN has_build_id
              THEN 'mat_si_address_location.build_id = in_sites.build_id (spatial route disagreed or absent)'
            ELSE 'ST_CONTAINS(in_sites.parcel_geog, geocoded rooftop point) [D85 globe parcel excluded]'
       END AS match_method,
       CASE WHEN has_build_id AND has_spatial THEN 'high'
            WHEN has_build_id THEN 'medium_high' ELSE 'medium' END AS match_confidence,
       'energy.mat_si_address_location (building_footprint_geocode / rooftop_geocode)' AS bridge_source,
       CURRENT_TIMESTAMP() AS built_at
FROM u
-- ONE parcel per address. Without this the tier-3 spatial rows fan an address onto every polygon
-- that contains it, and the signal counts downstream would be inflated by the duplication.
QUALIFY ROW_NUMBER() OVER (PARTITION BY address_norm ORDER BY match_tier, parcel_source, parcel_key) = 1
"""
gb_bridge = dry(BRIDGE_SQL)
go(BRIDGE_SQL, "CREATE in_si_address_parcel_bridge")

bs = one(f"""
SELECT COUNT(*) n, COUNT(DISTINCT address_norm) n_addr,
       COUNT(DISTINCT CONCAT(parcel_source,'|',parcel_key)) n_parcels,
       COUNTIF(match_tier=1) t1, COUNTIF(match_tier=2) t2, COUNTIF(match_tier=3) t3
FROM `{DS}.in_si_address_parcel_bridge`""", "bridge grain check")
print(f"    rows={bs.n:,}  distinct addresses={bs.n_addr:,}  distinct parcels={bs.n_parcels:,}")
assert bs.n == bs.n_addr, "GRAIN BROKEN: bridge is not one row per address_norm"
print(f"    tier1 both-agree={bs.t1:,}   tier2 build_id-only={bs.t2:,}   tier3 spatial-only={bs.t3:,}")

# agreement between the two independent routes, on the addresses where both fired
ag = one(f"""
WITH b AS ({BRIDGE_SRC}),
     sb AS (SELECT build_id, parcel_source, parcel_key FROM `{DS}.in_sites`
            WHERE build_id IS NOT NULL AND {GLOBE}),
     sg AS (SELECT parcel_source, parcel_key, parcel_geog FROM `{DS}.in_sites`
            WHERE parcel_geog IS NOT NULL AND {GLOBE}),
     viaB AS (SELECT DISTINCT b.address_norm, sb.parcel_source, sb.parcel_key FROM b JOIN sb USING(build_id)),
     viaS AS (SELECT DISTINCT b.address_norm, sg.parcel_source, sg.parcel_key FROM b
              JOIN sg ON ST_CONTAINS(sg.parcel_geog, ST_GEOGPOINT(b.lon, b.lat)))
SELECT (SELECT COUNT(DISTINCT address_norm) FROM viaB) b_addr,
       (SELECT COUNT(DISTINCT address_norm) FROM viaS) s_addr,
       (SELECT COUNT(DISTINCT address_norm) FROM viaB
        WHERE address_norm IN (SELECT address_norm FROM viaS)) both_addr,
       (SELECT COUNT(*) FROM viaB INNER JOIN viaS USING(address_norm,parcel_source,parcel_key)) agree
""", "two-route agreement")
print(f"    route yields: build_id={ag.b_addr:,}  spatial={ag.s_addr:,}  both fired={ag.both_addr:,}")
print(f"    routes AGREE on the same parcel for {ag.agree:,} of {ag.both_addr:,} "
      f"({100*ag.agree/ag.both_addr:.1f}%)")

register("in_si_address_parcel_bridge",
         f"{EN}.mat_si_address_location + {DS}.in_sites",
         "address_norm (EXISTING upstream normaliser, not re-derived) -> build_id -> in_sites.build_id; "
         "fallback ST_CONTAINS(in_sites.parcel_geog, rooftop point). D85 globe parcel excluded.",
         bs.n, gb_bridge,
         f"ADDRESS->PARCEL BRIDGE. NO normalisation written here: exact equality and UPPER(TRIM) "
         f"equality both yield {c.present:,} addresses (delta 0), proving in_si_signals.address_norm "
         f"and mat_si_address_location.address_norm come from the same normaliser. CEILING IS UPSTREAM "
         f"GEOCODE COVERAGE, NOT THE JOIN: of {c.sig_addr:,} distinct signal addresses only {c.present:,} "
         f"({100*c.present/c.sig_addr:.1f}%) exist in mat_si_address_location and only {c.resolved:,} "
         f"({100*c.resolved/c.sig_addr:.1f}%) are resolved there. Tiers: 1 both routes agree (high), "
         f"2 build_id only (medium_high), 3 spatial only (medium). "
         f"Two routes agree on {100*ag.agree/ag.both_addr:.1f}% of the {ag.both_addr:,} addresses where "
         f"both fire. D85: parcels_in/080500000047000018 is an inverted whole-Earth polygon "
         f"(196,936,707 sq mi) that made the raw spatial join match 100%; it is excluded here and is "
         f"STILL UNREPAIRED upstream.")

# ---------------------------------------------------------------- 2. the dated parcel signals
print("\n" + "=" * 78 + "\n2. BUILD in_si_signals_parcel_dated\n" + "=" * 78)
DATED_SQL = f"""
CREATE OR REPLACE TABLE `{DS}.in_si_signals_parcel_dated`
CLUSTER BY parcel_source, parcel_key, signal AS
WITH s AS (
  SELECT sig.signal, sig.address_norm, sig.observed_date, sig.source_id, sig.county_fips
  FROM `{DS}.in_si_signals` sig
  WHERE sig.keying IN ('address_norm','address') AND sig.address_norm IS NOT NULL),
j AS (SELECT s.*, b.parcel_source, b.parcel_key, b.match_tier
      FROM s JOIN `{DS}.in_si_address_parcel_bridge` b USING(address_norm))
SELECT parcel_source, parcel_key, signal,
       MAX(observed_date) AS max_observed_date,
       -- kept SEPARATE from max_observed_date: D1_tax_sale/D20_loan_maturity carry SCHEDULED
       -- future dates, and a 2036 maturity must never read as "recent activity".
       MAX(IF(observed_date <= CURRENT_DATE(), observed_date, NULL)) AS max_past_observed_date,
       MIN(observed_date) AS min_observed_date,
       COUNT(*) AS n_events,
       COUNTIF(observed_date IS NOT NULL) AS n_events_dated,
       COUNTIF(observed_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 3 YEAR)
                                 AND CURRENT_DATE()) AS n_events_3y,
       COUNTIF(observed_date > CURRENT_DATE()) AS n_events_future,
       COUNT(DISTINCT address_norm) AS n_addresses,
       COUNT(DISTINCT source_id) AS n_sources,
       MIN(match_tier) AS match_tier,
       CASE MIN(match_tier)
         WHEN 1 THEN 'mat_si_address_location.build_id = in_sites.build_id, CONFIRMED by ST_CONTAINS(in_sites.parcel_geog)'
         WHEN 2 THEN 'mat_si_address_location.build_id = in_sites.build_id (spatial route disagreed or absent)'
         ELSE 'ST_CONTAINS(in_sites.parcel_geog, geocoded rooftop point) [D85 globe parcel excluded]'
       END AS match_method,
       CASE MIN(match_tier) WHEN 1 THEN 'high' WHEN 2 THEN 'medium_high' ELSE 'medium' END AS match_confidence,
       CURRENT_TIMESTAMP() AS built_at
FROM j GROUP BY parcel_source, parcel_key, signal
"""
gb_dated = dry(DATED_SQL)
go(DATED_SQL, "CREATE in_si_signals_parcel_dated")

d = one(f"""
SELECT COUNT(*) n,
       COUNT(DISTINCT CONCAT(parcel_source,'|',parcel_key,'|',signal)) n_key,
       COUNT(DISTINCT CONCAT(parcel_source,'|',parcel_key)) n_parcels,
       SUM(n_events) ev, SUM(n_events_3y) ev3, SUM(n_events_future) evf,
       COUNTIF(max_past_observed_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 YEAR)) rows_3y
FROM `{DS}.in_si_signals_parcel_dated`""", "dated table grain check")
print(f"    rows={d.n:,}  distinct (source,key,signal)={d.n_key:,}  distinct parcels={d.n_parcels:,}")
assert d.n == d.n_key, "GRAIN BROKEN: not one row per (parcel_source,parcel_key,signal)"
print(f"    signal events carried={d.ev:,}  within 3y={d.ev3:,}  scheduled future={d.evf:,}")

register("in_si_signals_parcel_dated",
         f"{DS}.in_si_signals + {DS}.in_si_address_parcel_bridge",
         "address-keyed signal rows joined through in_si_address_parcel_bridge, aggregated to "
         "one row per (parcel_source, parcel_key, signal)",
         d.n, gb_dated,
         f"THE DATED PARCEL-SIGNAL LAYER. Carries MAX observed_date for signal rows that were "
         f"address-keyed and therefore invisible to the parcel layer. {d.n_parcels:,} parcels, "
         f"{d.ev:,} events. max_observed_date and max_past_observed_date are SEPARATE columns "
         f"because {d.evf:,} events are SCHEDULED FUTURE dates (D1_tax_sale sale dates, "
         f"D20_loan_maturity to 2036-03-01) - real forward-looking signals, but they must not read "
         f"as recent activity. match_confidence high/medium_high/medium names the bridge tier; "
         f"see in_si_address_parcel_bridge for the ceiling.")

# ---------------------------------------------------------------- 3. measured yield
print("\n" + "=" * 78 + "\n3. MEASURED YIELD\n" + "=" * 78)
y = one(f"""
WITH s AS (SELECT signal, address_norm, observed_date FROM `{DS}.in_si_signals`
           WHERE keying IN ('address_norm','address') AND address_norm IS NOT NULL)
SELECT COUNT(*) src_rows, COUNT(DISTINCT address_norm) src_addr,
       COUNTIF(b.address_norm IS NOT NULL) m_rows,
       COUNT(DISTINCT b.address_norm) m_addr,
       COUNTIF(s.observed_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 3 YEAR) AND CURRENT_DATE()) src_3y,
       COUNTIF(b.address_norm IS NOT NULL AND s.observed_date
               BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 3 YEAR) AND CURRENT_DATE()) m_3y
FROM s LEFT JOIN `{DS}.in_si_address_parcel_bridge` b USING(address_norm)""", "overall yield")
print(f"    address-keyed rows ...... {y.m_rows:,} / {y.src_rows:,} = {100*y.m_rows/y.src_rows:.1f}%")
print(f"    distinct addresses ...... {y.m_addr:,} / {y.src_addr:,} = {100*y.m_addr/y.src_addr:.1f}%")
print(f"    rows within 3y .......... {y.m_3y:,} / {y.src_3y:,} = {100*y.m_3y/y.src_3y:.1f}%")

print("\n    by signal:")
print(f"    {'signal':<24} {'rows':>9} {'matched':>9} {'pct':>6}   {'addr':>8} {'m_addr':>8} {'pct':>6}   {'3y':>7} {'m_3y':>7}")
for r in rows(f"""
WITH s AS (SELECT signal, address_norm, observed_date FROM `{DS}.in_si_signals`
           WHERE keying IN ('address_norm','address') AND address_norm IS NOT NULL)
SELECT s.signal, COUNT(*) n, COUNTIF(b.address_norm IS NOT NULL) m,
       COUNT(DISTINCT s.address_norm) a, COUNT(DISTINCT b.address_norm) ma,
       COUNTIF(s.observed_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 3 YEAR) AND CURRENT_DATE()) n3,
       COUNTIF(b.address_norm IS NOT NULL AND s.observed_date
               BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 3 YEAR) AND CURRENT_DATE()) m3
FROM s LEFT JOIN `{DS}.in_si_address_parcel_bridge` b USING(address_norm)
GROUP BY 1 ORDER BY n DESC""", "yield by signal"):
    print(f"    {r.signal:<24} {r.n:>9,} {r.m:>9,} {100*r.m/r.n:>5.1f}%   "
          f"{r.a:>8,} {r.ma:>8,} {100*r.ma/r.a:>5.1f}%   {r.n3:>7,} {r.m3:>7,}")

# ---------------------------------------------------------------- 4. before / after
print("\n" + "=" * 78 + "\n4. EFFECT ON THE PARCEL LAYER (before/after)\n" + "=" * 78)
ba = one(f"""
WITH p AS (SELECT parcel_source, parcel_key, has_si_signal, si_last_event_date
           FROM `{DS}.in_sites` WHERE {GLOBE}),
     n AS (SELECT parcel_source, parcel_key,
                  MAX(max_observed_date) md, MAX(max_past_observed_date) mpd
           FROM `{DS}.in_si_signals_parcel_dated` GROUP BY 1,2)
SELECT
  COUNTIF(p.has_si_signal) flagged,
  COUNTIF(p.has_si_signal AND p.si_last_event_date IS NOT NULL) before_dated,
  COUNTIF(p.has_si_signal AND p.si_last_event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 YEAR)) before_3y,
  COUNTIF(p.has_si_signal AND (p.si_last_event_date IS NOT NULL OR n.md IS NOT NULL)) after_dated,
  COUNTIF(p.has_si_signal AND p.si_last_event_date IS NULL AND n.md IS NOT NULL) gained,
  COUNTIF(p.has_si_signal AND GREATEST(IFNULL(p.si_last_event_date,'1900-01-01'),
          IFNULL(n.mpd,'1900-01-01')) >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 YEAR)) after_3y,
  COUNTIF(NOT IFNULL(p.has_si_signal,FALSE) AND n.md IS NOT NULL) net_new_unflagged,
  COUNTIF(n.md IS NOT NULL) total_touched
FROM p LEFT JOIN n USING(parcel_source, parcel_key)""", "before/after on in_sites")
print(f"    signal-flagged parcels ................... {ba.flagged:,}")
print(f"    BEFORE  with si_last_event_date .......... {ba.before_dated:,}  ({100*ba.before_dated/ba.flagged:.2f}%)")
print(f"    BEFORE  dated within 3y .................. {ba.before_3y:,}")
print(f"    AFTER   with a real event date ........... {ba.after_dated:,}  ({100*ba.after_dated/ba.flagged:.2f}%)")
print(f"    ...of which NEWLY dated by this build .... {ba.gained:,}")
print(f"    AFTER   dated within 3y .................. {ba.after_3y:,}")
print(f"    parcels dated but NOT has_si_signal ...... {ba.net_new_unflagged:,}")
print(f"    total parcels touched by the new table ... {ba.total_touched:,}")

print("\n    tier mix of the newly-dated parcels:")
for r in rows(f"""
SELECT match_confidence, COUNT(DISTINCT CONCAT(parcel_source,'|',parcel_key)) n_parcels,
       SUM(n_events) ev
FROM `{DS}.in_si_signals_parcel_dated` GROUP BY 1 ORDER BY n_parcels DESC""", "tier mix"):
    print(f"      {r.match_confidence:<14} parcels={r.n_parcels:>8,}  events={r.ev:>9,}")

print(f"\n{'='*78}\nDONE. total scanned {TOTAL_GB:.2f} GB. "
      f"2 tables built and registered in {DS}._registry\n{'='*78}")
