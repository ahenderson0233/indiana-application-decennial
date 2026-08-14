"""Second-round probes: I&M utility id, IURC advanced-search page, amlegal API, municode API, news fallbacks."""
import json
from bq_util import query, polite_get, allowed, save_scratch

# ---------- A. Resolve Indiana Michigan Power utility_id_eia ----------
print("### A. I&M utility id")
try:
    rows, _ = query("""
        SELECT table_id FROM `energy-platfrom.energy.__TABLES__`
        WHERE REGEXP_CONTAINS(LOWER(table_id), r'eia|utilit') ORDER BY table_id
    """)
    print("candidate tables:", [r["table_id"] for r in rows])
except Exception as e:
    print("table list failed:", str(e)[:200])

# eia861_service_territory: which utility ids serve IN, with county counts (small table)
try:
    rows, gb = query("""
        SELECT utility_id_eia, COUNT(DISTINCT county) n_counties,
               MAX(report_date) latest, STRING_AGG(DISTINCT county ORDER BY county LIMIT 8) sample_counties
        FROM `energy-platfrom.energy.eia861_service_territory`
        WHERE state='IN'
        GROUP BY 1 ORDER BY n_counties DESC LIMIT 25
    """)
    print(f"IN utilities by county coverage ({gb:.4f} GB):")
    for r in rows:
        print(" ", dict(r))
except Exception as e:
    print("territory agg failed:", str(e)[:300])

# ---------- B. IURC advanced-search page ----------
print("\n### B. IURC advanced-search")
ok, _ = allowed("https://iurc.portal.in.gov/advanced-search/")
print("robots allows /advanced-search/:", ok)
if ok:
    r = polite_get("https://iurc.portal.in.gov/advanced-search/")
    p = save_scratch("iurc_advanced_search.html", r.text)
    print("GET /advanced-search/ ->", r.status_code, len(r.text), "->", p)

# ---------- C. amlegal API ----------
print("\n### C. amlegal API probe")
for u in [
    "https://codelibrary.amlegal.com/api/search/?searchTerm=%22data%20center%22&region=in",
    "https://codelibrary.amlegal.com/api/regions/",
]:
    ok, _ = allowed(u)
    try:
        r = polite_get(u, headers={"Accept": "application/json"})
        body = r.text[:400].replace("\n", " ")
        print(f"allowed={ok} GET {u} -> {r.status_code} | {body}")
        if r.status_code == 200:
            save_scratch("amlegal_probe_" + u.split("/api/")[1][:12].replace("/", "_").replace("?", "_") + ".json", r.text)
    except Exception as e:
        print(f"GET {u} FAILED: {e}")

# ---------- D. municode API ----------
print("\n### D. municode API probe")
for u in [
    "https://api.municode.com/States",
    "https://api.municode.com/Clients/stateAbbr?stateAbbr=IN",
]:
    ok, raw = allowed(u)
    print(f"robots api.municode.com allows: {ok}")
    if not ok:
        print("robots raw (first 15):", "\n".join(raw.splitlines()[:15]))
        break
    try:
        r = polite_get(u, headers={"Accept": "application/json"})
        print(f"GET {u} -> {r.status_code} | {r.text[:300]}")
        if r.status_code == 200:
            save_scratch("municode_" + u.split(".com/")[1][:20].replace("/", "_").replace("?", "_") + ".json", r.text)
    except Exception as e:
        print(f"GET {u} FAILED: {e}")

# ---------- E. news fallbacks: GDELT + Bing ----------
print("\n### E. news fallbacks")
u = "https://api.gdeltproject.org/api/v2/doc/doc?query=%22data%20center%22%20indiana&mode=artlist&maxrecords=5&format=json"
ok, raw = allowed(u)
print("gdelt robots allows:", ok)
if ok:
    try:
        r = polite_get(u)
        print("GDELT ->", r.status_code, "|", r.text[:300].replace("\n", " "))
    except Exception as e:
        print("GDELT FAILED:", e)

u = "https://www.bing.com/news/search?q=indiana+data+center&format=rss"
ok, raw = allowed(u)
print("bing /news/search rss robots allows:", ok)
if not ok:
    hits = [l for l in raw.splitlines() if "news" in l.lower() or l.lower().startswith("user-agent")][:20]
    print("bing robots relevant lines:", hits)
