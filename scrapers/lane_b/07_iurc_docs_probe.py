"""How does docketed-case-details load its document list? Fetch page for known case, grep endpoints, probe."""
import re, json
from bq_util import polite_get, save_scratch, SESSION

GUID = "b8cd5780-0546-ef11-8409-001dd803817e"  # cause 46097
u = f"https://iurc.portal.in.gov/docketed-case-details/?id={GUID}"
r = polite_get(u)
print("details page ->", r.status_code, len(r.text))
save_scratch("iurc_case_details.html", r.text)

txt = r.text
for pat in [r'portalCompanionUrl[^;]{0,120}', r"/api/[A-Za-z0-9/_-]+", r"_services[A-Za-z0-9/._-]*",
            r"documents?[A-Za-z]*\s*[:=][^,;]{0,80}", r"annotation[^\"']{0,80}"]:
    ms = list(dict.fromkeys(re.findall(pat, txt)))[:20]
    print(f"\n### /{pat}/")
    for m in ms:
        print("   ", str(m)[:160])
