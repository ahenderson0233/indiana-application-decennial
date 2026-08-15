"""Download GasQuest JS chunks and grep for the document-download endpoint."""
import re, os, time
import requests
from probe import get, OUT

r = requests.get("https://www.gasquest.com/informational-posting",
                 headers={"User-Agent": "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"}, timeout=30)
chunks = sorted(set(re.findall(r'(?:src|href)="(chunk-[A-Z0-9]+\.js)"', r.text)))
# also main entry scripts
mains = sorted(set(re.findall(r'(?:src|href)="((?:main|polyfills)[^"]*\.js)"', r.text)))
print("chunks:", len(chunks), "mains:", mains)
time.sleep(1.1)

hits = []
for name in mains + chunks:
    resp = get(f"gq_{name}", f"https://www.gasquest.com/{name}")
    if resp is None:
        continue
    txt = resp.content.decode("utf-8", errors="replace")
    for pat in [r'[a-zA-Z0-9./_-]*[Tt]racker[a-zA-Z0-9./_?=&{}$-]*',
                r'infopost/[a-zA-Z]+',
                r'https://[a-z.-]*bwpmlp[a-z.-]*org[a-zA-Z0-9./_-]*']:
        for m in set(re.findall(pat, txt)):
            hits.append((name, m))

for name, m in sorted(set(hits)):
    print(name, "|", m)
