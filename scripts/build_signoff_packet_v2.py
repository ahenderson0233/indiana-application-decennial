"""Sign-off packet v2 — REPLACES docs/SIGNOFF_PACKET.md.

v1 asked BigQuery for columns nobody had read: `status` (D11), `case_type` (IOCS),
`q_id` (queue_miso). Three of eight items came back as query errors and two more answered
a different question than the one posed. This version reads every schema first and picks
subject columns by VALUE, which is the standing rule the v1 builder skipped.

READ-ONLY. Writes one markdown file. Nothing wires here — wiring waits on the operator.
"""
import datetime
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")

out = [f"# Operator sign-off packet v2 — measured {datetime.date.today()}",
       "",
       "Supersedes v1, in which items 1, 4 and 7 were BigQuery errors (columns guessed, never",
       "read) and 5-6 answered a different question than the one asked. Every column below was",
       "read from the schema first.",
       "",
       "**Reply per item: APPROVE (with the mapping) / REJECT / DEFER.** Nothing wires without it.",
       ""]

def sec(title, note=""):
    out.append(f"## {title}")
    if note: out.append(f"_{note}_")
    out.append("")

def q(sql, label=None, indent="- "):
    if label: out.append(f"**{label}**")
    try:
        rows = list(client.query(sql))
        if not rows:
            out.append(f"{indent}(no rows — this is itself an answer: the predicate matched nothing)")
        for r in rows:
            out.append(indent + " · ".join(f"{k}={str(v)[:70]}" for k, v in dict(r).items()))
    except Exception as ex:
        out.append(f"{indent}QUERY ERROR: {str(ex)[:200]}")
    out.append("")

# ---------------------------------------------------------------- 1. D11
sec("1. D11 entity dissolution — 2,129 Indiana rows",
    "The subject column is `raw_status` (publisher's words) normalised into `status_family`. "
    "v1 asked for `status`, which does not exist. QUESTION: which families count as DISSOLVED?")
q(f"""SELECT status_family, COUNT(*) n, COUNT(DISTINCT raw_status) distinct_raw,
        STRING_AGG(DISTINCT raw_status, ' | ' ORDER BY raw_status LIMIT 6) example_raw_values
      FROM `{DS}.in_si_d11_entity_dissolution` GROUP BY 1 ORDER BY n DESC""",
  "status_family → raw_status vocabulary")
q(f"""SELECT CAST(MIN(observed_date) AS STRING) earliest, CAST(MAX(observed_date) AS STRING) latest,
        COUNT(DISTINCT city) cities, COUNTIF(address_line IS NOT NULL) with_address
      FROM `{DS}.in_si_d11_entity_dissolution`""", "plottability + date range")

# ---------------------------------------------------------------- 2. D25
sec("2. D25 rail abandonment — 874 source rows vs 215 wired",
    "`state_count_in_docket` is the crux: a docket naming many states should not count wholly "
    "to Indiana. QUESTION: admit all 874, or only single-state / Indiana-primary dockets?")
q(f"""SELECT state_count_in_docket, COUNT(*) n, COUNT(DISTINCT docket) dockets
      FROM `{DS}.in_si_d25_stb_abandonment_state`
      GROUP BY 1 ORDER BY SAFE_CAST(state_count_in_docket AS INT64)""",
  "how many states each docket names")
q(f"""SELECT state_parse_rule, COUNT(*) n FROM `{DS}.in_si_d25_stb_abandonment_state`
      GROUP BY 1 ORDER BY n DESC LIMIT 8""", "how the state was parsed out (the instrument)")
q(f"""SELECT filing_type, COUNT(*) n FROM `{DS}.in_si_d25_stb_abandonment_state`
      GROUP BY 1 ORDER BY n DESC LIMIT 10""", "filing_type vocabulary")

# ---------------------------------------------------------------- 3. D27
sec("3. D27 UCC lapse v2 — 156 Indiana rows",
    "QUESTION: wire as D27 candidates? `keying`/`quality_mult` say how confidently each row "
    "reaches an address.")
q(f"""SELECT raw_filing_type, COUNT(*) n FROM `{DS}.in_si_d27_ucc_lapse_v2`
      GROUP BY 1 ORDER BY n DESC LIMIT 10""", "filing type vocabulary")
q(f"""SELECT keying, ROUND(quality_mult,3) quality_mult, COUNT(*) n,
        COUNTIF(address_line IS NOT NULL) with_address, COUNTIF(zip IS NOT NULL) with_zip
      FROM `{DS}.in_si_d27_ucc_lapse_v2` GROUP BY 1,2 ORDER BY n DESC""",
  "keying quality → how many are actually placeable")

# ---------------------------------------------------------------- 4. IOCS MF
sec("4. IOCS 'MF' — the question as posed cannot be answered, and here is why",
    "v1 asked to 'admit MF rows'. There are no MF rows. `in_si_refresh_iocs_eviction` is a "
    "court-statistics WORKBOOK: one row per court, and every case-type code (MR, CF, EV, MF, …) "
    "is a COLUMN holding a count. So MF is a per-court aggregate, not a per-address event — it "
    "cannot become a parcel-level SI signal at any confidence. QUESTION: admit it as COUNTY-GRAIN "
    "context on the Community page instead, or drop it?")
q(f"""SELECT COUNT(*) courts, COUNTIF(SAFE_CAST(MF AS INT64) > 0) courts_with_mf,
        SUM(SAFE_CAST(MF AS INT64)) total_mf_filings,
        SUM(SAFE_CAST(EV AS INT64)) total_ev_evictions,
        COUNT(DISTINCT County_Name) counties
      FROM `{DS}.in_si_refresh_iocs_eviction`""", "what MF actually contains")
q(f"""SELECT County_Name, SUM(SAFE_CAST(MF AS INT64)) mortgage_foreclosures,
        SUM(SAFE_CAST(EV AS INT64)) evictions
      FROM `{DS}.in_si_refresh_iocs_eviction`
      WHERE County_Name IS NOT NULL GROUP BY 1
      HAVING mortgage_foreclosures > 0 ORDER BY mortgage_foreclosures DESC LIMIT 10""",
  "top counties by MF (county grain is the only honest grain here)")

# ---------------------------------------------------------------- 5. cloudscene
sec("5. Cloudscene — `state` is empty for 98% of rows, so it is the wrong key",
    "5,283 of 5,388 rows have a blank state; the populated handful are other states. Indiana has "
    "to be found through `city`/`market`. QUESTION: approve city/market matching (list below), "
    "or leave cloudscene out — we already hold 244 Indiana DCs with coordinates?")
q(f"""SELECT country, COUNT(*) n, COUNTIF(state IS NULL OR TRIM(state)='') blank_state
      FROM `{EN}.data_centers_cloudscene` GROUP BY 1 ORDER BY n DESC LIMIT 6""",
  "country split (is this even a US-centric table?)")
q(f"""SELECT market, city, COUNT(*) n FROM `{EN}.data_centers_cloudscene`
      WHERE REGEXP_CONTAINS(LOWER(CONCAT(IFNULL(market,''),' ',IFNULL(city,''))),
        r'indiana|indianapolis|fort wayne|south bend|evansville|hammond|carmel|fishers|bloomington|lafayette|munster|elkhart|new carlisle')
      GROUP BY 1,2 ORDER BY n DESC LIMIT 25""", "candidate Indiana rows via city/market")

# ---------------------------------------------------------------- 6. airports
sec("6. airports — 86 rows nationally, and it carries GEOMETRY",
    "The table is a curated 86-row set, not a full airport list, and it has a `geom` GEOGRAPHY "
    "column — so `state` never needed to be trusted. Spatial clip is the answer. QUESTION: "
    "approve clipping by geometry (results below) and using it as an obstruction/airspace "
    "context layer?")
q(f"""SELECT COUNT(*) total_rows, COUNTIF(geom IS NOT NULL) with_geometry,
        COUNTIF(UPPER(IFNULL(state,''))='IN') state_says_IN
      FROM `{EN}.airports`""", "the instrument")
q(f"""SELECT a.name, a.servcity, a.state, a.type_code, a.operstatus,
        a.latitude, a.longitude   -- publisher's own strings; nothing derived
      FROM `{EN}.airports` a
      JOIN `{EN}.state_boundaries` s ON s.STUSPS='IN' AND ST_INTERSECTS(a.geom, s.geom)
      ORDER BY a.name""", "rows whose GEOMETRY falls in Indiana (clipped to the state polygon)")
q(f"""SELECT a.state, COUNT(*) n FROM `{EN}.airports` a
      JOIN `{EN}.state_boundaries` s ON s.STUSPS='IN' AND ST_INTERSECTS(a.geom, s.geom)
      GROUP BY 1 ORDER BY n DESC""",
  "…and what the `state` column claims for those same Indiana rows (the format flag)")

# ---------------------------------------------------------------- 7. queue_miso
sec("7. queue_miso vs interconnection_queue — is one a duplicate slice of the other?",
    "v1 asked queue_miso for `q_id`; its key is `projectnumber` (interconnection_queue uses "
    "`q_id`). Compared properly below. QUESTION: if the Indiana project numbers overlap "
    "substantially, waive queue_miso as a duplicate — or keep it for the columns the other lacks "
    "(studyphase, poiname, dp1/dp2 ERIS+NRIS MW)?")
q(f"""SELECT 'queue_miso (all states)' src, COUNT(*) n, COUNT(DISTINCT projectnumber) ids FROM `{EN}.queue_miso`
      UNION ALL SELECT 'queue_miso (state=IN)', COUNT(*), COUNT(DISTINCT projectnumber)
        FROM `{EN}.queue_miso` WHERE UPPER(TRIM(state))='IN'
      UNION ALL SELECT 'interconnection_queue (state=IN)', COUNT(*), COUNT(DISTINCT q_id)
        FROM `{EN}.interconnection_queue` WHERE UPPER(TRIM(state))='IN'
      UNION ALL SELECT 'interconnection_queue (IN, MISO region)', COUNT(*), COUNT(DISTINCT q_id)
        FROM `{EN}.interconnection_queue` WHERE UPPER(TRIM(state))='IN' AND UPPER(IFNULL(region,'')) LIKE '%MISO%'""",
  "row and id counts")
q(f"""WITH m AS (SELECT DISTINCT UPPER(TRIM(projectnumber)) k FROM `{EN}.queue_miso`
                 WHERE UPPER(TRIM(state))='IN' AND projectnumber IS NOT NULL),
        i AS (SELECT DISTINCT UPPER(TRIM(q_id)) k FROM `{EN}.interconnection_queue`
              WHERE UPPER(TRIM(state))='IN' AND q_id IS NOT NULL)
      SELECT (SELECT COUNT(*) FROM m) miso_in_ids, (SELECT COUNT(*) FROM i) icq_in_ids,
             (SELECT COUNT(*) FROM m JOIN i USING (k)) shared_ids""",
  "identity overlap on the Indiana slice (the actual duplicate test)")
q(f"""SELECT studyphase, COUNT(*) n FROM `{EN}.queue_miso`
      WHERE UPPER(TRIM(state))='IN' GROUP BY 1 ORDER BY n DESC LIMIT 8""",
  "what queue_miso adds that interconnection_queue has no column for")

# ---------------------------------------------------------------- 8. DC dedupe
sec("8. DC dedupe — the proposed rule, actually applied",
    "v1's preview listed every cross-source pair within 500 m REGARDLESS of name, so it showed "
    "what proximity alone would collapse, not what the rule would. Applied here: normalise the "
    "name (lowercase, alphanumeric only) and require one to be a prefix of the other. "
    "QUESTION: approve this rule? Note the NULL-name problem in the third block.")
NORM = "REGEXP_REPLACE(LOWER(IFNULL({c}.name,'')), r'[^a-z0-9]', '')"
pair = f"""
  FROM `{DS}.in_data_centers_all` a JOIN `{DS}.in_data_centers_all` b
    ON a.src < b.src
   AND ST_DWITHIN(ST_GEOGPOINT(a.lon,a.lat), ST_GEOGPOINT(b.lon,b.lat), 500)
  WHERE a.name IS NOT NULL AND b.name IS NOT NULL
    AND LENGTH({NORM.format(c='a')}) > 3 AND LENGTH({NORM.format(c='b')}) > 3"""
q(f"""SELECT a.src, b.src src_b, a.name, b.name name_b,
        ROUND(ST_DISTANCE(ST_GEOGPOINT(a.lon,a.lat), ST_GEOGPOINT(b.lon,b.lat))) meters
      {pair} AND (STARTS_WITH({NORM.format(c='a')}, {NORM.format(c='b')})
                  OR STARTS_WITH({NORM.format(c='b')}, {NORM.format(c='a')}))
      ORDER BY meters LIMIT 25""",
  "WOULD COLLAPSE (name-stem matches) — check these are genuinely one facility")
q(f"""SELECT a.src, b.src src_b, a.name, b.name name_b,
        ROUND(ST_DISTANCE(ST_GEOGPOINT(a.lon,a.lat), ST_GEOGPOINT(b.lon,b.lat))) meters
      {pair} AND NOT (STARTS_WITH({NORM.format(c='a')}, {NORM.format(c='b')})
                      OR STARTS_WITH({NORM.format(c='b')}, {NORM.format(c='a')}))
      ORDER BY meters LIMIT 15""",
  "WOULD STAY SEPARATE despite being within 500 m — check none of these are one facility")
q(f"""SELECT a.src, b.src src_b, a.name a_name, b.name b_name,
        COUNT(*) pairs, ROUND(MIN(ST_DISTANCE(ST_GEOGPOINT(a.lon,a.lat), ST_GEOGPOINT(b.lon,b.lat)))) nearest_m
      FROM `{DS}.in_data_centers_all` a JOIN `{DS}.in_data_centers_all` b
        ON a.src < b.src
       AND ST_DWITHIN(ST_GEOGPOINT(a.lon,a.lat), ST_GEOGPOINT(b.lon,b.lat), 500)
      WHERE a.name IS NULL OR b.name IS NULL
      GROUP BY 1,2,3,4 ORDER BY pairs DESC LIMIT 12""",
  "THE GAP: pairs where one source has NO NAME — a name-stem rule cannot judge these, so they "
  "stay as duplicate pins unless you approve a distance-only fallback")
q(f"""SELECT src, COUNT(*) n, COUNTIF(name IS NULL) unnamed
      FROM `{DS}.in_data_centers_all` GROUP BY 1 ORDER BY n DESC""",
  "source composition of the 244")

open(f"{REPO}\\docs\\SIGNOFF_PACKET.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print(f"SIGNOFF_PACKET.md rewritten — {len(out)} lines")
