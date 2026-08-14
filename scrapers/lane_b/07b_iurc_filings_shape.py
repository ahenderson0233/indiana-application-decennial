"""Probe /api/document/filings response shape for cause 46097."""
import json, time
from bq_util import SESSION, save_scratch

BASE = "https://zus1iurcprodd365companionappmaster-appservice.azurewebsites.net"
GUID = "b8cd5780-0546-ef11-8409-001dd803817e"

for variant in [{"txtPageNumber": "1", "Id": " " + GUID}, {"txtPageNumber": "1", "Id": GUID}]:
    time.sleep(1.2)
    r = SESSION.post(BASE + "/api/document/filings", json=variant, timeout=60,
                     headers={"Accept": "application/json", "Content-Type": "application/json"})
    print(f"POST filings Id={'space' if variant['Id'][0]==' ' else 'bare'} -> {r.status_code}, {len(r.text)}B")
    if r.status_code == 200:
        save_scratch("iurc_filings_46097.json", r.text)
        js = r.json()
        print("TotalRecords:", js.get("TotalRecords"), "| keys:", list(js.keys()))
        for d in js.get("data", [])[:3]:
            print(json.dumps(d, indent=1)[:900])
        break
