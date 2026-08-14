"""Indiana data-center actions (moratoria/bans/rejections/withdrawals/approvals-despite-opposition)
-> indiana_app.in_dc_actions.

Sources (all robots-allowed, checked 2026-08-14):
  A. Data Center Watch quarterly report pages (datacenterwatch.org /report /q22025 /q3-q4-2025 /q1-2026)
  B. News headlines from in_news_dc pull (news_rows.json) where the headline itself states the action.
already_held compares against energy.dc_opposition_tracker (read-only) on normalized jurisdiction.
Observed date: A = date stated in report narrative (month-year grain often); B = article publish date
(publication is the observation event for a headline; the enacted date may differ - flagged in date_note).
"""
import json, os, re, datetime
from bq_util import polite_get, save_scratch, load_rows, register, now_utc_iso, query
from google.cloud import bigquery

SCRATCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_scratch")
pulled = now_utc_iso()
rows = []

MONTHS = {m: i + 1 for i, m in enumerate(
    ["january","february","march","april","may","june","july","august","september","october","november","december"])}

def parse_narrative_date(text):
    m = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(20\d{2})", text)
    if m:
        return datetime.date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2))).isoformat(), "day"
    m = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})", text)
    if m:
        return datetime.date(int(m.group(2)), MONTHS[m.group(1).lower()], 1).isoformat(), "month"
    m = re.search(r"\b(20\d{2})\b", text)
    if m:
        return datetime.date(int(m.group(1)), 1, 1).isoformat(), "year"
    return None, None

# census place->county
place2county = {}
txt = open(os.path.join(SCRATCH, "national_place_by_county2020.txt"), encoding="utf-8", errors="replace").read()
for line in txt.splitlines()[1:]:
    f = line.split("|")
    if len(f) >= 8 and f[0] == "IN":
        base = re.sub(r"\s+(city|town|CDP)$", "", f[6], flags=re.I).strip().lower()
        place2county.setdefault(base, set()).add(f[3])

def county_for(place):
    p = place.strip()
    if re.search(r"county$", p, re.I):
        return p
    cs = place2county.get(p.lower())
    if cs:
        return "|".join(sorted(cs)) if len(cs) > 1 else next(iter(cs))
    return None

# ---------- A. Data Center Watch ----------
PAGES = ["/report", "/q22025", "/q3-q4-2025", "/q1-2026"]
for pg in PAGES:
    u = "https://www.datacenterwatch.org" + pg
    try:
        r = polite_get(u)
        if r.status_code != 200:
            print(f"{pg} -> HTTP {r.status_code}")
            continue
        t = re.sub(r"<script[^>]*>.*?</script>", " ", r.text, flags=re.S)
        t = re.sub(r"<style[^>]*>.*?</style>", " ", t, flags=re.S)
        plain = re.sub(r"<[^>]+>", "\n", t)
        plain = plain.replace("&nbsp;", " ").replace("&amp;", "&").replace("’", "'")
        plain = re.sub(r"\n{2,}", "\n", plain)
        save_scratch("dcwatch" + pg.replace("/", "_") + ".txt", plain)
        lines = [l.strip() for l in plain.splitlines()]
        # entries look like: "3 - Chesterton, Indiana. $1.3 billion. Provident Realty Advisors."
        for i, line in enumerate(lines):
            m = re.match(r"^\d+\s*[–-]\s*(.+?),\s*Indiana\b(.*)$", line)
            if not m:
                # sometimes split: number line then "Place, Indiana...." on the next
                m2 = re.match(r"^\d+\s*[–-]\s*$", line)
                if m2 and i + 1 < len(lines):
                    m = re.match(r"^(.+?),\s*Indiana\b(.*)$", lines[i + 1])
                if not m:
                    continue
            place = m.group(1).strip()
            rest = m.group(2)
            block = " ".join(lines[i:i + 14])
            sm = re.search(r"[—-]\s*(Blocked|Delayed|Rejected|Withdrawn|Approved|Moratorium|Paused|Cancell?ed)[^&\n]*", block, re.I)
            action = (sm.group(0).strip(" —-") if sm else "listed in report").strip()
            inv = re.search(r"\$[\d.,]+\s*(billion|million)", block, re.I)
            date_iso, grain = parse_narrative_date(block)
            rows.append({
                "jurisdiction": place, "county": county_for(place), "state": "IN",
                "action": action[:200],
                "action_date": date_iso, "action_date_grain": grain,
                "date_note": "date parsed from report narrative" if date_iso else "no date stated in report entry",
                "company": None,
                "investment": inv.group(0) if inv else None,
                "evidence_title": ("DCW " + pg.strip("/") + ": " + line)[:400],
                "evidence_text": block[:1200],
                "source_url": u, "source_name": "Data Center Watch (10a Labs)",
                "method": "dcwatch_report_page",
                "already_held": None, "_pulled_at": pulled,
            })
    except Exception as e:
        print(f"{pg} FAILED: {e}")
print(f"dcwatch rows: {len(rows)}")

# ---------- B. headline-derived ----------
ACTION_PAT = re.compile(
    r"\b(moratorium|moratoriums|ban\b|bans\b|banned|halt|halts|halted|pause|paused|pauses|"
    r"reject|rejects|rejected|denies|denied|deny|withdraw|withdraws|withdrawn|withdrawal|"
    r"overturn|repeal|blocks|blocked|kills|scraps|shelves|no recommendation|opposition|protest)\b", re.I)
COUNTY_IN_TITLE = re.compile(r"\b([A-Z][a-zA-Z.]+(?: [A-Z][a-zA-Z.]+)?) County\b")
news_path = os.path.join(SCRATCH, "news_rows.json")
if os.path.exists(news_path):
    news = json.load(open(news_path, encoding="utf-8"))
    seen = set()
    for a in news:
        title = a.get("title") or ""
        if not ACTION_PAT.search(title):
            continue
        if not re.search(r"data center", title, re.I):
            continue
        jur = None
        m = COUNTY_IN_TITLE.search(title)
        if m:
            jur = m.group(1) + " County"
        else:
            for pl in place2county:
                if len(pl) > 3 and re.search(r"\b" + re.escape(pl) + r"\b", title, re.I):
                    jur = pl.title()
                    break
        if jur is None and a.get("query_county"):
            jur = a["query_county"].split("|")[0] + " County (from query)"
        if jur is None:
            continue
        key = (jur.lower(), title.lower()[:80])
        if key in seen:
            continue
        seen.add(key)
        pub = (a.get("published") or "")[:10] or None
        rows.append({
            "jurisdiction": jur.replace(" (from query)", ""), "county": county_for(jur.replace(" (from query)", "")),
            "state": "IN",
            "action": ("headline: " + ACTION_PAT.search(title).group(1).lower()),
            "action_date": pub, "action_date_grain": "day" if pub else None,
            "date_note": "publication date of article (event date may differ)",
            "company": None, "investment": None,
            "evidence_title": title[:400], "evidence_text": None,
            "source_url": a.get("link"), "source_name": a.get("source"),
            "method": "news_headline(" + a.get("provider", "") + ")",
            "already_held": None, "_pulled_at": pulled,
        })
    print(f"with headline rows: {len(rows)}")
else:
    print("news_rows.json missing - run 09 first; headline rows skipped")

# ---------- already_held vs dc_opposition_tracker ----------
try:
    held, gb = query("SELECT jurisdiction, county, date FROM `energy-platfrom.energy.dc_opposition_tracker` WHERE state='IN'")
    held_j = {re.sub(r"[^a-z]+", "", (h["jurisdiction"] or "").lower()): str(h["date"]) for h in held}
    for r in rows:
        k = re.sub(r"[^a-z]+", "", (r["jurisdiction"] or "").lower())
        r["already_held"] = any(k and (k in hj or hj in k) for hj in held_j if hj)
    print(f"held IN tracker rows: {len(held)} ({gb:.4f} GB)")
except Exception as e:
    print("held comparison failed:", str(e)[:200])

save_scratch("dc_action_rows.json", json.dumps(rows, indent=1))
schema = [bigquery.SchemaField(n, t) for n, t in [
    ("jurisdiction", "STRING"), ("county", "STRING"), ("state", "STRING"), ("action", "STRING"),
    ("action_date", "DATE"), ("action_date_grain", "STRING"), ("date_note", "STRING"),
    ("company", "STRING"), ("investment", "STRING"), ("evidence_title", "STRING"),
    ("evidence_text", "STRING"), ("source_url", "STRING"), ("source_name", "STRING"),
    ("method", "STRING"), ("already_held", "BOOL"), ("_pulled_at", "TIMESTAMP")]]
n = load_rows("in_dc_actions", rows, schema)
register("in_dc_actions",
         source="datacenterwatch.org report pages (/report,/q22025,/q3-q4-2025,/q1-2026) + headlines from in_news_dc providers",
         method="report-page text parse (numbered 'Place, Indiana' entries) + action-verb headline extraction with census place->county mapping; already_held matched against energy.dc_opposition_tracker (read-only)",
         n_rows=n, gb_scanned=0.0,
         notes=f"Held tracker covers 50 IN rows to 2026-04-21; fresh value is post-April-2026 headlines. dcwatch pages are freely readable (no paywall). Dates: report rows carry narrative-date grain; headline rows use publication date (flagged). Pulled {pulled}.")
print("DONE")
