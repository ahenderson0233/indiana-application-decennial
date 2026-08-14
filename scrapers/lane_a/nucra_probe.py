import json, sys, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"
model = {
    "GridName": "ProjectTransition", "ItemType": 0,
    "Items": [{"ItemType": 1, "FilterName": "ReportType", "IsSingleItem": True, "Filter": "NUCRA"}],
    "Paginator": {"ItemType": 7, "CurrentItmsPerPageValue": "100", "CurrentPageIndex": "1"},
    "Sort": "", "SortDirection": "", "RelatedGridsFilters": "",
}
body = urllib.parse.urlencode({"jsonModel": json.dumps(model)}).encode()
req = urllib.request.Request("https://www.pjm.com/m/ProjectTransition/ProjectTransitionResetGrdBody",
                             data=body, method="POST",
                             headers={"User-Agent": UA,
                                      "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
with urllib.request.urlopen(req, timeout=120) as r:
    html = r.read(20_000_000).decode("utf-8", "replace")
print("status 200,", f"{len(html):,}b")
import re
heads = re.findall(r"<th[^>]*>\s*(?:<[^>]+>)*([^<]{2,60})", html)
print("headers:", [h.strip() for h in heads][:25])
rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S)
print(f"{len(rows)} <tr> rows")
for tr in rows[1:4]:
    cells = [re.sub(r"<[^>]+>", " ", c).strip()[:40] for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
    print("  ", cells)
