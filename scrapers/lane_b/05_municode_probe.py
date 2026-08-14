"""Discover Municode search API shape + fetch census place->county crosswalk for IN."""
import json
from bq_util import polite_get, allowed, save_scratch

# clients list (needed regardless)
r = polite_get("https://api.municode.com/Clients/stateAbbr?stateAbbr=IN", headers={"Accept": "application/json"})
clients = r.json()
print(f"IN municode clients: {len(clients)}")
save_scratch("municode_in_clients.json", json.dumps(clients, indent=1))
cid = clients[0]["ClientID"]
print("first client:", clients[0]["ClientName"], cid)

# probe search endpoint shapes
CAND = [
    f"https://api.municode.com/search?clientId={cid}&searchText=%22data+center%22&pageNum=1&pageSize=10",
    f"https://api.municode.com/Search?clientId={cid}&searchText=%22data+center%22&pageNum=1&pageSize=10",
    f"https://api.municode.com/search/client?clientId={cid}&searchText=%22data+center%22",
    f"https://api.municode.com/ClientContent/{cid}",
]
for u in CAND:
    try:
        r = polite_get(u, headers={"Accept": "application/json"})
        print(f"\nGET {u}\n -> {r.status_code} | {r.text[:500]}")
        if r.status_code == 200:
            save_scratch("municode_probe_" + str(abs(hash(u)) % 99999) + ".json", r.text)
    except Exception as e:
        print(f"{u} FAILED: {e}")

# census place->county crosswalk (public reference file)
u = "https://www2.census.gov/geo/docs/reference/codes2020/place_by_county/st18_in_place_by_county2020.txt"
ok, raw = allowed(u)
print("\ncensus robots allows:", ok)
if ok:
    r = polite_get(u)
    print("census file ->", r.status_code, len(r.text), "bytes")
    if r.status_code == 200:
        save_scratch("st18_in_place_by_county2020.txt", r.text)
        print(r.text[:300])
