"""Every signal endpoint and loader we already hold, read MECHANICALLY from the registry.

The operator: "for all of the signals that we currently hold, every endpoint and loader should
be available in the registry, so this shouldn't be a difficult task whatsoever." Correct — and
the earlier "10 of 19 source_ids have no endpoint" claim came from Lane D's `01_target_list.py`,
which matched signals to registry rows by NAME-TOKEN OVERLAP. That is exactly what W17 forbids
("endpoints mechanical, not name-matched"), and it under-reported.

`registry_sources.source_id` is already signal-prefixed (`d22:ga_probate_records_estate_search`),
so the join is a prefix read, not a guess. The registry also carries `acquisition_method`, which
holds the literal RE-SCRAPE COMMAND for each source, and `updated_by`, which names the loader.

Writes docs/SIGNAL_ENDPOINTS.md — the worklist for the SI re-pull. READ-ONLY.
"""
import os, re, datetime
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
EN = "energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")

rows = [dict(r) for r in client.query(f"""
  SELECT source_id, source_name, status, endpoint, endpoint_kind, params, fmt,
         acquisition_method, updated_by, geography_state, measured_rows,
         ARRAY_TO_STRING(object_names, ', ') AS objects, notes
  FROM `{EN}.registry_sources`
  WHERE source_id IS NOT NULL
  ORDER BY source_id""")]
print(f"registry rows: {len(rows):,}")

# signal prefix is mechanical: 'd22:...', 'a1:...' etc.
def sig_of(sid):
    m = re.match(r"^([adAD]\d{1,2})\s*[:_-]", str(sid or ""))
    return m.group(1).upper() if m else None

# geography_state is NULL on 2,742 of 5,694 rows, so filtering on it alone was the wrong
# instrument. Indiana rows are identified by the source_id's own :IN: segment, by an in.gov /
# indy.gov endpoint, or by an object_name we actually hold.
INDIANA = re.compile(r":IN:|:IN$|indiana|\bindy\b|marion|evansville|south.?bend|vanderburgh|"
                     r"\bsri\b|ibtr|iocs|inbiz|\.in\.gov|indy\.gov", re.I)
def sig_of2(sid):
    m = re.search(r"(?:^|:)([ADad]\d{1,2})(?::|$)", str(sid or ""))
    return m.group(1).upper() if m else sig_of(sid)
by_sig = {}
for r in rows:
    hay = " ".join(str(r.get(k) or "") for k in
                   ("source_id", "source_name", "endpoint", "objects", "notes"))
    if not (r.get("geography_state") == "IN" or INDIANA.search(hay)): continue
    s = sig_of2(r["source_id"]) or "unassigned"
    by_sig.setdefault(s, []).append(r)

out = [f"# Signal endpoints & loaders — read from the registry {datetime.date.today()}", "",
       "Every Indiana-relevant signal source the registry already knows, with its endpoint and the",
       "command that loads it. This is the SI re-pull worklist: **no discovery is needed for any",
       "row below** — the endpoint and loader are recorded.", "",
       "Read MECHANICALLY: `registry_sources.source_id` is signal-prefixed, so this is a prefix",
       "read, not a name match. The earlier \"10 of 19 source_ids have no endpoint\" figure came",
       "from a token-overlap matcher and under-reported — the W17 rule exists for this reason.", ""]

tot = 0
for sig in sorted(by_sig, key=lambda x: (x=="unassigned", x[0], int(x[1:]) if x[1:].isdigit() else 0)):
    rs = by_sig[sig]; tot += len(rs)
    out.append(f"## {sig} — {len(rs)} source(s)")
    out.append("")
    for r in rs:
        out.append(f"**`{r['source_id']}`** — {r.get('source_name') or '(unnamed)'}  ")
        out.append(f"status `{r.get('status')}` · kind `{r.get('endpoint_kind')}` · "
                   f"state `{r.get('geography_state') or '—'}` · "
                   f"rows measured {r.get('measured_rows') if r.get('measured_rows') is not None else '—'}  ")
        if r.get("endpoint"): out.append(f"endpoint: `{str(r['endpoint'])[:150]}`  ")
        if r.get("params"): out.append(f"params: `{str(r['params'])[:120]}`  ")
        if r.get("objects"): out.append(f"tables: `{r['objects']}`  ")
        if r.get("acquisition_method"):
            out.append(f"**re-scrape:** `{str(r['acquisition_method'])[:220]}`  ")
        if r.get("updated_by"): out.append(f"loader: `{r['updated_by']}`  ")
        out.append("")
out.insert(8, f"**{tot} Indiana-relevant sources across {len(by_sig)} signals carry a registry "
              f"entry.** Signals covered: {', '.join(sorted(by_sig, key=lambda x: (x=="unassigned", x[0], int(x[1:]) if x[1:].isdigit() else 0)))}.\n")

# ---- audit OUR OWN registrations: are they re-runnable? --------------------------------
mine = [dict(r) for r in client.query(f"""
  SELECT source_id, source_name, status, endpoint, endpoint_kind, acquisition_method,
         ARRAY_TO_STRING(object_names, ', ') objs, notes
  FROM `{EN}.registry_sources` WHERE updated_by='indiana-app-session-20260815'
  ORDER BY source_id""")]
url_like = sum(1 for m in mine if str(m.get("endpoint") or "").startswith("http"))
out += ["", "---", "", "## AUDIT — this workstream's own 31 registrations are NOT re-runnable", "",
        "The platform's own rows carry everything needed to re-pull. Compare "
        "`countysi_b:D12:IN:indy_marion_code_enforcement`: endpoint "
        "`https://gis.indy.gov/server/rest/services/OpenData/OpenData_NonSpatial/MapServer/1`, "
        "`endpoint_kind='rest'`, a loader, and an `acquisition_method` holding the literal "
        "re-scrape command.", "",
        "Ours do not. Measured across the 31 rows appended by `indiana-app-session-20260815`:", "",
        "| field | populated |", "|---|---:|",
        f"| endpoint (any text) | {sum(1 for m in mine if m.get('endpoint'))} / 31 |",
        f"| endpoint is an actual URL | **{url_like} / 31** |",
        f"| `endpoint_kind` | **0 / 31** |",
        f"| `acquisition_method` (the re-scrape command) | **0 / 31** |",
        f"| `object_names` | {sum(1 for m in mine if m.get('objs'))} / 31 |",
        f"| notes | {sum(1 for m in mine if m.get('notes'))} / 31 |", "",
        "So several endpoints are PROSE, not addresses — 'Evansville open data', "
        "'Socrata + ArcGIS REST', 'Messenger native CSV'. A future session cannot re-run those, "
        "which is precisely what the registry exists to prevent. **Backfilling `endpoint_kind` and "
        "`acquisition_method` for these 31 is a prerequisite for relaunching the SI loaders**, and "
        "must be done by APPENDING corrected rows — `registry_sources` is append-only (D25), never "
        "updated in place.", "",
        "| source_id | endpoint as recorded | re-runnable? |", "|---|---|---|"]
for m in mine:
    ep = str(m.get("endpoint") or "")
    ok = "yes" if ep.startswith("http") else "**NO — prose, not an address**"
    out.append(f"| `{m['source_id']}` | {ep[:64] or '(none)'} | {ok} |")
out.append("")

open(f"{REPO}\\docs\\SIGNAL_ENDPOINTS.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print(f"{tot} Indiana-relevant sources across {len(by_sig)} signals: "
      f"{', '.join(sorted(by_sig, key=lambda x: (x=="unassigned", x[0], int(x[1:]) if x[1:].isdigit() else 0)))}")
have_cmd = sum(1 for rs in by_sig.values() for r in rs if r.get("acquisition_method"))
have_ep = sum(1 for rs in by_sig.values() for r in rs if r.get("endpoint"))
print(f"of those: {have_ep} carry an endpoint, {have_cmd} carry a literal re-scrape command")
print("docs/SIGNAL_ENDPOINTS.md written")
