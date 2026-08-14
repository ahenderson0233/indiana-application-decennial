"""Indiana data-center news -> indiana_app.in_news_dc.

Google News RSS is robots-BLOCKED (news.google.com/robots.txt: 'User-agent: * / Disallow: /' with no
/rss Allow) — recorded, not worked around. Permitted replacements, robots-checked 2026-08-14:
  - Bing News RSS (www.bing.com/news/search?format=rss) — allowed for *
  - GDELT DOC 2.0 API (api.gdeltproject.org) — allowed; server instructs 1 request / 5 seconds (429 text)
De-dup on link. Observed date = published/seen date from the feed. I&M-territory counties run first
(ordering tiebreaker per operator), then the rest of the 92.
"""
import json, re, time, datetime, xml.etree.ElementTree as ET
from urllib.parse import quote
from bq_util import polite_get, save_scratch, load_rows, register, now_utc_iso
from google.cloud import bigquery

IM_FIRST = ["Allen", "St. Joseph", "Elkhart", "DeKalb", "Adams", "Wells", "Huntington", "Wabash",
            "Delaware", "Grant", "Blackford", "Randolph", "Jay", "Noble", "LaGrange", "Steuben",
            "Whitley", "Kosciusko", "Marshall", "Miami"]
PROMPT_COUNTIES = ["Marion", "Hendricks", "Boone", "Hamilton", "Vanderburgh", "Vigo", "Porter",
                   "LaPorte", "Madison", "Johnson"]
ALL92 = ["Adams","Allen","Bartholomew","Benton","Blackford","Boone","Brown","Carroll","Cass","Clark",
"Clay","Clinton","Crawford","Daviess","Dearborn","Decatur","DeKalb","Delaware","Dubois","Elkhart",
"Fayette","Floyd","Fountain","Franklin","Fulton","Gibson","Grant","Greene","Hamilton","Hancock",
"Harrison","Hendricks","Henry","Howard","Huntington","Jackson","Jasper","Jay","Jefferson","Jennings",
"Johnson","Knox","Kosciusko","LaGrange","Lake","LaPorte","Lawrence","Madison","Marion","Marshall",
"Martin","Miami","Monroe","Montgomery","Morgan","Newton","Noble","Ohio","Orange","Owen","Parke",
"Perry","Pike","Porter","Posey","Pulaski","Putnam","Randolph","Ripley","Rush","St. Joseph","Scott",
"Shelby","Spencer","Starke","Steuben","Sullivan","Switzerland","Tippecanoe","Tipton","Union",
"Vanderburgh","Vermillion","Vigo","Wabash","Warren","Warrick","Washington","Wayne","Wells","White","Whitley"]

CITY_QUERIES = [("New Carlisle data center", "St. Joseph"), ("Lebanon Indiana data center", "Boone"),
    ("Fort Wayne data center", "Allen"), ("Indianapolis data center", "Marion"),
    ("South Bend data center", "St. Joseph"), ("Evansville data center", "Vanderburgh"),
    ("Terre Haute data center", "Vigo"), ("Kokomo data center", "Howard"),
    ("Muncie data center", "Delaware"), ("Hobart data center", "Lake"),
    ("Michigan City data center", "LaPorte"), ("Valparaiso data center", "Porter"),
    ("Rochester Indiana data center", "Fulton"), ("Lafayette Indiana data center", "Tippecanoe"),
    ("Greenwood Indiana data center", "Johnson"), ("Anderson Indiana data center", "Madison"),
    ("Plainfield Indiana data center", "Hendricks"), ("Noblesville data center", "Hamilton")]

county_order = list(dict.fromkeys(IM_FIRST + PROMPT_COUNTIES + ALL92))
pulled = now_utc_iso()
rows_by_link = {}

def add(provider, query, county, title, link, source, pub_raw, pub_iso):
    if not link or link in rows_by_link:
        # keep first; append county attribution if new
        if link in rows_by_link and county and county not in (rows_by_link[link]["query_county"] or ""):
            rows_by_link[link]["query_county"] += "|" + county
        return
    rows_by_link[link] = {"provider": provider, "query": query, "query_county": county or "",
                          "title": (title or "").strip()[:500], "link": link, "source": source,
                          "published_raw": pub_raw, "published": pub_iso, "_pulled_at": pulled}

def parse_rfc822(s):
    try:
        return datetime.datetime.strptime(s.strip(), "%a, %d %b %Y %H:%M:%S %Z").strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        try:
            import email.utils as eu
            d = eu.parsedate_to_datetime(s)
            return d.astimezone(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            return None

# ---------------- Bing News RSS ----------------
def bing(query, county):
    u = f"https://www.bing.com/news/search?q={quote(query)}&format=rss"
    try:
        r = polite_get(u)
        if r.status_code != 200:
            print(f"  bing [{query}] HTTP {r.status_code}")
            return 0
        root = ET.fromstring(r.content)
        n = 0
        for item in root.iter("item"):
            title = item.findtext("title")
            link = item.findtext("link")
            pub = item.findtext("pubDate")
            src = ""
            m = re.search(r"[?&]url=([^&]+)", link or "")
            if m:
                from urllib.parse import unquote
                link = unquote(m.group(1))
            if link:
                src = re.sub(r"^www\.", "", (re.findall(r"https?://([^/]+)", link) or [""])[0])
            add("bing_news_rss", query, county, title, link, src, pub, parse_rfc822(pub or ""))
            n += 1
        return n
    except Exception as e:
        print(f"  bing [{query}] FAILED: {e}")
        return 0

queries = [("Indiana data center", None), ("Indiana data center moratorium", None),
           ("Indiana data center rezoning", None), ("Indiana data center opposition", None)]
queries += [(f"{c} County Indiana data center", c) for c in county_order]
queries += CITY_QUERIES

print(f"BING: {len(queries)} queries")
for q, c in queries:
    bing(q, c)
print(f"after bing: {len(rows_by_link)} unique links")

# ---------------- GDELT DOC API (1 per 5.5s) ----------------
GDELT_LAST = [0.0]
def gdelt(query, county, timespan="18months"):
    wait = 5.5 - (time.time() - GDELT_LAST[0])
    if wait > 0:
        time.sleep(wait)
    u = ("https://api.gdeltproject.org/api/v2/doc/doc?query=" + quote(query) +
         f"&mode=artlist&maxrecords=100&timespan={timespan}&format=json&sort=datedesc")
    try:
        r = polite_get(u, min_interval=0.0, timeout=60)
        GDELT_LAST[0] = time.time()
        if r.status_code != 200:
            print(f"  gdelt [{query}] HTTP {r.status_code}: {r.text[:90]}")
            return 0
        js = r.json() if r.text.strip().startswith("{") else {}
        arts = js.get("articles", [])
        for a in arts:
            sd = a.get("seendate", "")
            iso = None
            m = re.match(r"(\d{4})(\d{2})(\d{2})T?(\d{2})?(\d{2})?", sd or "")
            if m:
                iso = f"{m.group(1)}-{m.group(2)}-{m.group(3)} {(m.group(4) or '00')}:{(m.group(5) or '00')}:00 UTC"
            add("gdelt_doc", query, county, a.get("title"), a.get("url"), a.get("domain"), sd, iso)
        return len(arts)
    except Exception as e:
        print(f"  gdelt [{query}] FAILED: {e}")
        return 0

# GDELT: generic + priority counties only (5.5s each; keep to ~40 calls)
gq = [('"data center" Indiana moratorium', None), ('"data center" Indiana rezoning', None),
      ('"data center" Indiana opposition', None), ('"data center" Indiana zoning', None)]
gq += [(f'"data center" "{c} County" Indiana', c) for c in list(dict.fromkeys(IM_FIRST + PROMPT_COUNTIES))[:32]]
print(f"GDELT: {len(gq)} queries (5.5s spacing)")
for q, c in gq:
    gdelt(q, c)
print(f"after gdelt: {len(rows_by_link)} unique links")

rows = list(rows_by_link.values())
# keep only Indiana-relevant rows: query mentioned a county/city (already IN-scoped) or title mentions Indiana
generic_mask = lambda r: (r["query_county"] or re.search(r"indiana|hoosier", (r["title"] or "") + " " + r["query"], re.I))
rows = [r for r in rows if generic_mask(r)]
print(f"rows to load: {len(rows)}")
save_scratch("news_rows.json", json.dumps(rows, indent=1))

schema = [bigquery.SchemaField(n, t) for n, t in [
    ("provider", "STRING"), ("query", "STRING"), ("query_county", "STRING"), ("title", "STRING"),
    ("link", "STRING"), ("source", "STRING"), ("published_raw", "STRING"), ("published", "TIMESTAMP"),
    ("_pulled_at", "TIMESTAMP")]]
n = load_rows("in_news_dc", rows, schema)
n_c = len({c for r in rows for c in (r["query_county"] or "").split("|") if c})
register("in_news_dc",
         source="Bing News RSS (www.bing.com/news/search?format=rss) + GDELT DOC 2.0 API (api.gdeltproject.org)",
         method=f"Bing: {len(queries)} queries (generic+92 counties+18 cities) 1.1s spacing; GDELT: {len(gq)} queries 5.5s spacing per server 429 instruction; de-dup on link; observed date=feed pubDate/GDELT seendate",
         n_rows=n, gb_scanned=0.0,
         notes=f"GOOGLE NEWS RSS BLOCKED by robots.txt (User-agent:* Disallow:/ without /rss Allow) - recorded, replaced by permitted providers. {n_c} counties carried query attribution. Pulled {pulled}.")
print("DONE")
