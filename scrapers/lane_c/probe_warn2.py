import sys, re
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get

html = get("https://www.in.gov/dwd/warn-notices/", as_json=False)
# all links
links = sorted(set(re.findall(r'href="([^"]+)"', html)))
warn_links = [l for l in links if "warn" in l.lower()]
print("warn-ish links:")
for l in warn_links: print("  ", l)
# check for iframes / js data
for pat in [r'<iframe[^>]+src="([^"]+)"', r'(https?://[^"\']+\.json[^"\']*)', r'datawrapper|tableau|powerbi|airtable|sharepoint']:
    m = re.findall(pat, html, re.I)
    if m: print(pat[:30], "->", m[:10])
# main content text around 'WARN'
body = re.sub(r"<script.*?</script>", "", html, flags=re.S)
body = re.sub(r"<[^>]+>", " ", body)
body = re.sub(r"\s+", " ", body)
i = body.lower().find("warn notice")
print("\ncontext:", body[max(0,i-200):i+1500])
