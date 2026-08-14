"""Municode ordinance sweep: exact-phrase "data center(s)" across all Indiana Municode clients.

api.municode.com is robots-allowed (checked 2026-08-14); 1.1s/request; UA per spec.
AmLegal equivalent is Cloudflare-challenge-blocked today (recorded in findings/registry notes).
Loads -> energy-platfrom.indiana_app.in_ordinances_dc and registers in _registry same run.
Observed date = adoption/amendment date parsed from snippet citation where present; else NULL.
"""
import json, re, datetime
from bq_util import polite_get, save_scratch, load_rows, register, now_utc_iso
from google.cloud import bigquery

STATE_ID = 14  # Indiana per /States
PHRASES = ['"data center"', '"data centers"']

clients = json.load(open(r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_b\_scratch\municode_in_clients.json", encoding="utf-8"))
print(f"{len(clients)} IN clients")

# census place->county for IN
place2county = {}
try:
    txt = open(r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_b\_scratch\national_place_by_county2020.txt", encoding="utf-8", errors="replace").read()
    for line in txt.splitlines()[1:]:
        f = line.split("|")
        if len(f) >= 8 and f[0] == "IN":
            base = re.sub(r"\s+(city|town|CDP)$", "", f[6], flags=re.I).strip().lower()
            place2county.setdefault(base, set()).add(f[3])
except Exception as e:
    print("census map load failed:", e)
print(f"IN places mapped: {len(place2county)}")

def county_for(client_name):
    n = client_name.strip()
    if re.search(r"county$", n, re.I):
        return n if n.lower().endswith("county") else n + " County"
    cs = place2county.get(n.lower())
    if cs and len(cs) == 1:
        return next(iter(cs))
    if cs:
        return "|".join(sorted(cs))  # multi-county place, keep all
    return None

DATE_PAT = re.compile(r"(\d{1,2})-(\d{1,2})-(\d{2,4})")
def snippet_date(text):
    """Adoption date from citation like (Ord. 2023-12, passed 6-14-2023) — last date wins (amendment)."""
    dates = []
    for m in DATE_PAT.finditer(text or ""):
        mth, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000 if y <= 39 else 1900
        try:
            dates.append(datetime.date(y, mth, d))
        except ValueError:
            pass
    return max(dates).isoformat() if dates else None

pulled = now_utc_iso()
rows, sample_saved = [], False
for c in clients:
    cid, cname = c["ClientID"], c["ClientName"].strip()
    seen_ids = set()
    for phrase in PHRASES:
        page, total = 1, None
        while True:
            u = ("https://api.municode.com/search?clientId={cid}&stateId={sid}&contentTypeId=CODES"
                 "&searchText={q}&pageNum={p}&pageSize=25&sort=0&titlesOnly=false&fragmentSize=250"
                 "&isAdvanced=false&mode=CLIENTMODE").format(cid=cid, sid=STATE_ID, q=phrase.replace(" ", "%20").replace('"', "%22"), p=page)
            try:
                r = polite_get(u, headers={"Accept": "application/json"})
                if r.status_code != 200:
                    print(f"  {cname} [{phrase}] p{page} -> HTTP {r.status_code}")
                    break
                js = r.json()
            except Exception as e:
                print(f"  {cname} [{phrase}] p{page} FAILED: {e}")
                break
            total = js.get("NumberOfHits", 0)
            hits = js.get("Hits", [])
            if page == 1 and total:
                print(f"  {cname}: {total} hits [{phrase}]")
            if hits and not sample_saved:
                save_scratch("municode_hit_sample.json", json.dumps(hits[0], indent=1))
                sample_saved = True
            for h in hits:
                nid = str(h.get("Id") or h.get("NodeId") or h.get("DocId") or "")
                key = nid or json.dumps(h, sort_keys=True)[:80]
                if key in seen_ids:
                    continue
                seen_ids.add(key)
                title = re.sub(r"<[^>]+>", "", str(h.get("Title") or h.get("CatchLineOrTitle") or "")).strip()
                frag = re.sub(r"<[^>]+>", "", str(h.get("ContentFragment") or h.get("Fragment") or h.get("Content") or "")).strip()
                slug = re.sub(r"[^a-z0-9]+", "_", cname.lower()).strip("_")
                url = f"https://library.municode.com/in/{slug}/codes/code_of_ordinances?nodeId={nid}" if nid else f"https://library.municode.com/in/{slug}"
                rows.append({
                    "jurisdiction": cname,
                    "county": county_for(cname),
                    "state": "IN",
                    "provider": "municode",
                    "client_id": str(cid),
                    "code_section_id": nid or None,
                    "section_title": title or None,
                    "snippet": frag[:1500] or None,
                    "observed_date": snippet_date(frag),
                    "observed_date_note": "adoption/amendment date parsed from ordinance citation in snippet; NULL when snippet shows none",
                    "search_phrase": phrase,
                    "url": url,
                    "raw_hit": json.dumps(h)[:2500],
                    "_pulled_at": pulled,
                })
            if page * 25 >= (total or 0) or not hits or page >= 8:
                break
            page += 1

print(f"\ntotal hit rows: {len(rows)}")
save_scratch("municode_rows.json", json.dumps(rows, indent=1))

schema = [
    bigquery.SchemaField("jurisdiction", "STRING"),
    bigquery.SchemaField("county", "STRING"),
    bigquery.SchemaField("state", "STRING"),
    bigquery.SchemaField("provider", "STRING"),
    bigquery.SchemaField("client_id", "STRING"),
    bigquery.SchemaField("code_section_id", "STRING"),
    bigquery.SchemaField("section_title", "STRING"),
    bigquery.SchemaField("snippet", "STRING"),
    bigquery.SchemaField("observed_date", "DATE"),
    bigquery.SchemaField("observed_date_note", "STRING"),
    bigquery.SchemaField("search_phrase", "STRING"),
    bigquery.SchemaField("url", "STRING"),
    bigquery.SchemaField("raw_hit", "STRING"),
    bigquery.SchemaField("_pulled_at", "TIMESTAMP"),
]
n = load_rows("in_ordinances_dc", rows, schema)
n_j = len({r["jurisdiction"] for r in rows})
register("in_ordinances_dc",
         source="https://api.municode.com/search (public JSON API of library.municode.com)",
         method='exact-phrase search "data center"/"data centers", contentTypeId=CODES, all 45 IN clients, paged 25/page, 1.1s/request',
         n_rows=n, gb_scanned=0.0,
         notes=f"{n_j} jurisdictions with hits of 45 IN Municode clients. AmLegal (codelibrary.amlegal.com) BLOCKED today: Cloudflare JS challenge 403 on HTML+/api/search/ despite robots Allow; held energy.amlegal_dc_ordinances IN rows (183) are loose data/center mentions, not phrase hits. county from census 2020 place_by_county. Pulled {pulled}.")
print("DONE")
