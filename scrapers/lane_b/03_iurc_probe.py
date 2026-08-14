"""IURC companion-API probe: robots, list endpoints, one known-cause POST to learn response shape.

The public page https://iurc.portal.in.gov/advanced-search/ POSTs the serialized form to
<companion>/api/search/advanced anonymously (no token). We replicate exactly that call.
"""
import json
from bq_util import polite_get, allowed, save_scratch, SESSION, UA

BASE = "https://zus1iurcprodd365companionappmaster-appservice.azurewebsites.net"

ok, raw = allowed(BASE + "/api/list/industrytypes")
print("companion robots can_fetch:", ok, "| robots head:", raw.splitlines()[:5])

for name in ["industrytypes/all", "petitiontypes", "statustypes", "utilitytypes"]:
    u = f"{BASE}/api/list/{name}"
    try:
        r = polite_get(u, headers={"Accept": "application/json"})
        print(f"\nGET {name} -> {r.status_code}, {len(r.text)}B")
        print(r.text[:600])
        if r.status_code == 200:
            save_scratch(f"iurc_list_{name.replace('/','_')}.json", r.text)
    except Exception as e:
        print(f"{name} FAILED: {e}")

# form-shaped payload exactly as the page's objectifyForm produces (all fields present, empty strings)
def payload(**kw):
    base = {
        "txtCause": "", "txtSubDocket": "", "ddlPetitionType": "", "ddlCaseStatus": "",
        "ddlIndustry": "", "txtParties": "", "ddlUtilities": "",
        "txtDateBegin": "", "txtDateEnd": "", "txtFilingDateBegin": "", "txtFilingDateEnd": "",
        "txtOrderDateBegin": "", "txtOrderDateEnd": "", "txtPageNumber": "1",
    }
    base.update(kw)
    return base

import time
u = BASE + "/api/search/advanced"
for label, pl in [
    ("known cause 46097", payload(txtCause="46097")),
    ("electric 2026 window p1", payload(ddlIndustry="Electric", txtFilingDateBegin="01/01/2026", txtFilingDateEnd="08/14/2026")),
]:
    try:
        time.sleep(1.2)
        r = SESSION.post(u, json=pl, timeout=60, headers={"Accept": "application/json", "Content-Type": "application/json"})
        print(f"\nPOST advanced [{label}] -> {r.status_code}, {len(r.text)}B")
        print(r.text[:1500])
        if r.status_code == 200:
            save_scratch(f"iurc_search_{label.split()[0]}_{label.split()[-1]}.json", r.text)
    except Exception as e:
        print(f"POST [{label}] FAILED: {e}")
