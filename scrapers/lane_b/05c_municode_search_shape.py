"""Pin down Municode /search params: save bundle, grep param names, try candidate URLs."""
import re
from bq_util import polite_get, save_scratch

r = polite_get("https://library.municode.com/dist/js/all/all.min.js?v=gUXDoekU9cWnsslmellecNm3GYzg8zvL1dlCklbdC-Q")
txt = r.text
save_scratch("municode_all_min.js", txt)
print("bundle", r.status_code, len(txt))

for pat in [r'api\.municode\.com[^"\']{0,120}', r'[\'"]/?search[^"\']{0,160}', r'searchParams[^;]{0,300}',
            r'(clientId|stateId|contentTypeId|titlesOnly|fragmentSize|isAdvanced|mode)[=:][^,;&"\']{0,40}[,&]']:
    ms = list(dict.fromkeys(re.findall(pat, txt)))[:15]
    print(f"\n### /{pat}/")
    for m in ms:
        print("   ", m[:200])

# candidate richer URLs
cands = [
    "https://api.municode.com/search?clientId=13311&stateId=14&contentTypeId=CODES&searchText=%22data%20center%22&pageNum=1&pageSize=25&sort=0&titlesOnly=false&fragmentSize=200&isAdvanced=false&mode=CLIENTMODE",
    "https://api.municode.com/search?clientId=13311&stateId=14&contentTypeIds=CODES&searchText=%22data%20center%22&pageNum=1&pageSize=25&sort=0&titlesOnly=false&fragmentSize=200&isAdvanced=false&mode=CLIENTMODE",
]
for u in cands:
    rr = polite_get(u, headers={"Accept": "application/json"})
    print(f"\nGET {u[:120]}... -> {rr.status_code} | {rr.text[:400]}")
    if rr.status_code == 200:
        save_scratch("municode_search_success.json", rr.text)
        break
