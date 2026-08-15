"""T2: the operator sign-off packet — measured value vocabularies for every pending
judgment. READ-ONLY queries; writes docs/SIGNOFF_PACKET.md. Nothing is wired here."""
import datetime
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
E = "`energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")
out = [f"# Operator sign-off packet — measured {datetime.date.today()}",
  "", "Each item shows the actual value vocabulary. Reply per item: APPROVE (with the",
  "mapping), REJECT, or DEFER. Nothing wires without your word.", ""]

def vocab(title, sql, note=""):
    out.append(f"## {title}")
    if note: out.append(f"_{note}_")
    try:
        for r in client.query(sql):
            out.append("- " + " | ".join(f"{k}={str(v)[:60]}" for k, v in dict(r).items()))
    except Exception as ex:
        out.append(f"- QUERY ERROR: {str(ex)[:140]}")
    out.append("")

vocab("1. D11 entity dissolution — first Indiana rows (2,129)",
  f"""SELECT status_norm, COUNT(*) n FROM (
      SELECT COALESCE(CAST(status AS STRING), CAST(entity_status AS STRING)) AS status_norm
      FROM `{DS}.in_si_d11_entity_dissolution`) GROUP BY 1 ORDER BY n DESC LIMIT 10""",
  "Question: which statuses count as DISSOLVED for the D11 signal?")
vocab("2. D25 rail abandonment — source rows (874) vs 215 wired",
  f"""SELECT column_name FROM `energy-platfrom.indiana_app`.INFORMATION_SCHEMA.COLUMNS
      WHERE table_name='in_si_d25_stb_abandonment_state' LIMIT 20""",
  "Columns first (schema); sample rows in SAMPLES docs. Question: admit all 874 as D25?")
vocab("3. D27 UCC lapse v2 — Indiana rows (156)",
  f"""SELECT column_name FROM `energy-platfrom.indiana_app`.INFORMATION_SCHEMA.COLUMNS
      WHERE table_name='in_si_d27_ucc_lapse_v2' LIMIT 20""",
  "Question: wire as D27 candidates for this app?")
vocab("4. IOCS 'MF' code — mortgage foreclosure inside the eviction workbook",
  f"""SELECT case_type, COUNT(*) n FROM (
      SELECT COALESCE(CAST(case_type AS STRING), CAST(type AS STRING)) AS case_type
      FROM `{DS}.in_si_refresh_iocs_eviction`) GROUP BY 1 ORDER BY n DESC LIMIT 10""",
  "Question: admit MF rows as a D2-family candidate?")
vocab("5. Cloudscene data centres — state vocabulary (why 'IN' matched 0)",
  f"""SELECT CAST(state AS STRING) AS state, COUNT(*) n FROM {E}.data_centers_cloudscene`
      GROUP BY 1 ORDER BY n DESC LIMIT 12""",
  "Question: which value means Indiana here?")
vocab("6. airports — why only 1 'IN' row (format flag)",
  f"""SELECT CAST(state AS STRING) AS state, COUNT(*) n FROM {E}.airports`
      GROUP BY 1 ORDER BY n DESC LIMIT 12""",
  "Question: what does this state column actually hold?")
vocab("7. queue_miso vs interconnection_queue — same source?",
  f"""SELECT 'queue_miso' AS t, COUNT(*) n, COUNT(DISTINCT CAST(q_id AS STRING)) ids
      FROM {E}.queue_miso`
      UNION ALL SELECT 'interconnection_queue IN', COUNT(*), COUNT(DISTINCT CAST(q_id AS STRING))
      FROM {E}.interconnection_queue` WHERE UPPER(state)='IN'""",
  "If id overlap is total, queue_miso is a duplicate slice - waive.")
vocab("8. DC dedupe preview — proposed rule: same name-stem within 500 m",
  f"""SELECT a.src, b.src, a.name, b.name,
        ROUND(ST_DISTANCE(ST_GEOGPOINT(a.lon,a.lat), ST_GEOGPOINT(b.lon,b.lat))) AS meters
      FROM `{DS}.in_data_centers_all` a JOIN `{DS}.in_data_centers_all` b
        ON a.src < b.src
       AND ST_DWITHIN(ST_GEOGPOINT(a.lon,a.lat), ST_GEOGPOINT(b.lon,b.lat), 500)
      ORDER BY meters LIMIT 20""",
  "Question: approve collapsing these cross-source pairs to one row each (sources listed)?")

open(f"{REPO}\\docs\\SIGNOFF_PACKET.md", "w", encoding="utf-8").write("\n".join(out))
print("SIGNOFF_PACKET.md written")
