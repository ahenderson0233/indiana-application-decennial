"""MISO generator-interconnection queue, from MISO's OWN public JSON. Writes `in_miso_giqueue_projects`.

⭐ WHY THIS ENDPOINT MATTERS, and precisely what it is NOT.

Found 2026-08-17 while hunting the DPP-2025 study. It is the first **MISO-authored, unauthenticated,
current-cycle** route we hold:

    GET https://www.misoenergy.org/api/giqueue/getprojects      HTTP 200, ~2.24 MB, no auth, no params

⛔ **IT IS NOT BUS HEADROOM, AND MUST NEVER BE PRESENTED AS SUCH.** Its 23 fields are a QUEUE record.
There is no FCITC, no constraint, no contingency, no DFAX, no rating and no loading — so it cannot
produce the capacity table the benchmark publishes. The DPP-2025 POI capacity heatmap and its
691,523-row transfer study remain behind the CartoVista `ProtectedData` wall (see
`docs/MISO_DPP2025_ROUTE.md` for the full route matrix; do not re-probe it).

⭐ WHAT IT DOES GIVE US, which is genuinely new:
  1. **DPP-2025 vintage.** `studyCycle` carries MISO's own literal string "DPP-2025" — publisher
     provenance, not our inference. Our other MISO queue clip is DPP-2021-era.
  2. **Definitive Planning Phase decision MW** — `dp1ErisMw` / `dp1NrisMw` / `dp2ErisMw` /
     `dp2NrisMw`. We have these nowhere else. They are the study's ANSWER per project, and a 0.0
     is a real constraint finding: J3831 asked 215 MW at Noblesville-Fall Creek 345 kV and Phase 1
     returned dp1ErisMw = 0.0.
  3. **`poiName` joins to our POI tables** — so it says which connection points current-cycle
     projects are competing for. That is direct competitive intelligence for siting: a POI with
     headroom on paper and six queued projects ahead of you is not open capacity.

⚠ MEASURED QUIRKS, so nobody re-discovers them:
  - `?cycle=` / `?studyCycle=` params are **IGNORED** — the server returns the identical full array
    regardless. Filter client-side.
  - **There is no DPP-2024.** MISO's cycles run ... 2022, 2023, **2025**, 2026. A gap is not a
    missing scrape.
  - No lat/lon anywhere in the payload. Join on `poiName`, or `county` + `state`.
  - The feed is LIVE, not a snapshot: max queueDate observed 2026-07-15.

Indiana-clipped per the standing rule (Indiana only, clipped at the border). National counts are
recorded in the registry notes so the denominator is never lost.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import json
import urllib.request
from google.cloud import bigquery

URL = "https://www.misoenergy.org/api/giqueue/getprojects"
DS = "energy-platfrom.indiana_app"
TARGET = "in_miso_giqueue_projects"
UA = {"User-Agent": "Mozilla/5.0 (compatible; DecennialResearch/1.0)"}
client = bigquery.Client(project="energy-platfrom")

print(f"GET {URL}")
with urllib.request.urlopen(urllib.request.Request(URL, headers=dict(UA)), timeout=120) as r:
    raw = r.read()
    status = r.status
print(f"  HTTP {status}  {len(raw):,} bytes")
rows = json.loads(raw)
assert isinstance(rows, list) and rows, "expected a non-empty JSON array"
print(f"  {len(rows):,} national records, {len(rows[0])} fields")

# national context, kept for the registry note - the denominator must not be lost by clipping
nat_2025 = sum(1 for x in rows if x.get("studyCycle") == "DPP-2025")
nat_2026 = sum(1 for x in rows if x.get("studyCycle") == "DPP-2026")

IN = [x for x in rows if (x.get("state") or "").strip().upper() in ("IN", "INDIANA")]
in_2025 = [x for x in IN if x.get("studyCycle") == "DPP-2025"]
in_mw = sum(1 for x in in_2025 if x.get("dp1ErisMw") is not None or x.get("dp1NrisMw") is not None)
print(f"  Indiana: {len(IN):,} records; DPP-2025 {len(in_2025)}, of which {in_mw} carry Phase-1 MW")
assert IN, "zero Indiana rows - the state field or its vocabulary changed; do not write an empty table"

# NEVER GUESS A TYPE: build the schema from the payload's own value types, and keep the two
# timestamp-ish fields as STRING unless every value parses - a silent NULL on a bad parse is worse
# than an honest string. (queueDate looks like '2025-10-07T01:41:17+00:00'.)
NUM = {"id", "summerNetMW", "winterNetMW", "dp1ErisMw", "dp1NrisMw", "dp2ErisMw", "dp2NrisMw"}
TS = {"queueDate", "inService"}
fields = list(rows[0].keys())
schema = [bigquery.SchemaField(f, "FLOAT64" if f in NUM else ("TIMESTAMP" if f in TS else "STRING"))
          for f in fields] + [bigquery.SchemaField("_source_url", "STRING"),
                              bigquery.SchemaField("_pulled_at", "TIMESTAMP")]

def clean(rec):
    out = {}
    for f in fields:
        v = rec.get(f)
        if f in NUM:
            out[f] = None if v in ("", None) else float(v)
        elif f in TS:
            out[f] = v or None            # BigQuery parses the ISO-8601 offset form directly
        else:
            out[f] = None if v is None else str(v)
    out["_source_url"] = URL
    return out

payload = [clean(x) for x in IN]
job = client.load_table_from_json(
    payload, f"{DS}.{TARGET}",
    job_config=bigquery.LoadJobConfig(
        schema=schema, write_disposition="WRITE_TRUNCATE",
        # _pulled_at is set by the load, not by the publisher - keep them distinguishable
        ))
job.result()
client.query(f"UPDATE `{DS}.{TARGET}` SET _pulled_at = CURRENT_TIMESTAMP() WHERE _pulled_at IS NULL").result()

m = list(client.query(f"""
SELECT COUNT(*) n, COUNT(DISTINCT projectNumber) proj,
       COUNTIF(studyCycle='DPP-2025') c2025,
       COUNTIF(studyCycle='DPP-2025' AND (dp1ErisMw IS NOT NULL OR dp1NrisMw IS NOT NULL)) c2025_mw,
       COUNT(DISTINCT poiName) pois, COUNT(DISTINCT county) counties,
       FORMAT_TIMESTAMP('%F', MAX(queueDate)) newest
FROM `{DS}.{TARGET}`"""))[0]
print(f"{TARGET}: {m.n:,} Indiana rows / {m.proj:,} distinct projects")
print(f"  DPP-2025            : {m.c2025} ({m.c2025_mw} with Phase-1 decision MW)")
print(f"  distinct POI names  : {m.pois}   counties: {m.counties}")
print(f"  newest queue date   : {m.newest}")
assert m.n == len(IN), "row count changed between clip and load"

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{TARGET}'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
    f"VALUES (@t,@s,@m,@n,0.0,CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", TARGET),
        bigquery.ScalarQueryParameter("s", "STRING", URL),
        bigquery.ScalarQueryParameter("m", "STRING",
            f"Single unauthenticated GET of {URL} (json_api); JSON array of {len(rows):,} national "
            f"records, clipped client-side to state IN. ?cycle= params are IGNORED by the server - "
            f"the identical full array is returned regardless, so filtering MUST be client-side. "
            f"RE-SCRAPE COMMAND: python scripts/pull_miso_giqueue_projects.py"),
        bigquery.ScalarQueryParameter("n", "INT64", int(m.n)),
        bigquery.ScalarQueryParameter("no", "STRING",
            f"PUBLISHER VINTAGE: studyCycle carries MISO's own literal cycle string; Indiana holds "
            f"{m.c2025} DPP-2025 rows ({m.c2025_mw} with Phase-1 decision MW). National context, "
            f"kept so clipping does not lose the denominator: {nat_2025} DPP-2025 and {nat_2026} "
            f"DPP-2026 records across {len(rows):,} total. "
            f"⛔ THIS IS THE QUEUE, NOT BUS HEADROOM - no FCITC, constraint, contingency, DFAX, "
            f"rating or loading, so it cannot produce a capacity table and must never be rendered "
            f"as one. The DPP-2025 transfer study stays behind CartoVista ProtectedData 403. "
            f"NOTE there is no DPP-2024 cycle: MISO runs 2022, 2023, 2025, 2026. "
            f"No lat/lon in the payload - join via poiName or county+state.")])).result()
print(f"registered {TARGET} in indiana_app._registry")

tb = client.get_table("energy-platfrom.energy.registry_sources")
cols = {f.name for f in tb.schema}
row = {k: v for k, v in {
    "source_name": "MISO generator-interconnection queue (misoenergy.org giqueue JSON)",
    "endpoint": URL,
    "endpoint_kind": "json_api",
    "access": "public - unauthenticated GET, no params, no cookies",
    "status": f"BUILT+LOADED ({m.n:,} Indiana of {len(rows):,} national; DPP-2025 {m.c2025})",
    "acquisition_method": "RE-SCRAPE COMMAND: python scripts/pull_miso_giqueue_projects.py",
    "what_it_provides": "per-project interconnection queue with MISO's own studyCycle label and the "
                        "Definitive Planning Phase decision MW (dp1/dp2 ERIS and NRIS); the first "
                        "MISO-authored DPP-2025-vintage route obtained. NOT bus headroom.",
    "object_names": [TARGET],
    "geography_state": "IN",
    "measured_rows": int(m.n),
    "notes": "Found 2026-08-17 during the DPP-2025 hunt. The POI capacity heatmap and 691,523-row "
             "transfer study for the same cycle remain 403 ProtectedData on CartoVista; this "
             "endpoint does not carry them. Written by the indiana_app workstream; APPEND-only.",
}.items() if k in cols}
errs = client.insert_rows_json("energy-platfrom.energy.registry_sources", [row])
print(f"appended to energy.registry_sources: {errs if errs else 'ok'}")
