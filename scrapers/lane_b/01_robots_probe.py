"""Robots.txt + landing-page probe for every host Lane B may touch. No crawling yet."""
import json
from bq_util import polite_get, allowed, robots_for, save_scratch, UA

HOSTS = [
    "https://iurc.portal.in.gov/",
    "https://www.in.gov/iurc/",
    "https://codelibrary.amlegal.com/",
    "https://library.municode.com/",
    "https://news.google.com/rss/search?q=test",
    "https://www.datacenterwatch.org/",
]

report = {}
for url in HOSTS:
    ok, raw = allowed(url)
    host = url.split("/")[2]
    report[host] = {"target_url": url, "allowed": ok, "robots_first_60_lines": "\n".join(raw.splitlines()[:60])}
    print(f"\n########## {host} -> can_fetch({url}) = {ok}")
    print("\n".join(raw.splitlines()[:40]))

save_scratch("robots_report.json", json.dumps(report, indent=1))

# Landing pages where allowed (1 request each)
for url, name in [
    ("https://iurc.portal.in.gov/", "iurc_home.html"),
    ("https://codelibrary.amlegal.com/regions/in", "amlegal_in_region.html"),
    ("https://www.datacenterwatch.org/", "dcwatch_home.html"),
]:
    ok, _ = allowed(url)
    if not ok:
        print(f"SKIP (robots disallow): {url}")
        continue
    try:
        r = polite_get(url)
        p = save_scratch(name, r.text)
        print(f"GET {url} -> {r.status_code}, {len(r.text)} bytes -> {p}")
    except Exception as e:
        print(f"GET {url} FAILED: {e}")
