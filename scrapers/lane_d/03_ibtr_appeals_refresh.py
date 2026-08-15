"""Lane D refresh: Indiana Board of Tax Review determinations (D26 assessment-appeal signal).

Feeds si_signals source_id = appeals_in_ibtr_determinations (6,953 IN rows held,
observed 2004-01-07 .. 2026-08-05). Registry-mapped endpoint (DevExtreme loadOptions
REST API, POST-only, no auth, no cookie, no token, BUILT+LOADED before):
  https://www.in.gov/ibtr/poplar/api/search/getsearchdata/determinations

THE TIME-SENSITIVITY PAYOFF FOR THIS SOURCE: an appeal determination carries its own
disposition (e.g. Denied/Granted/Dismissed/Settled/Withdrawn) in the publisher's own
vocabulary. Re-pulling tells us which of our held petitions have since been decided.

Full re-pull, ALL published fields (raw-first, nested structures JSON-serialized) ->
energy-platfrom.indiana_app.in_si_refresh_ibtr_appeals.
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lane_d_util as u

URL = "https://www.in.gov/ibtr/poplar/api/search/getsearchdata/determinations"
TABLE = "in_si_refresh_ibtr_appeals"
PAGE = 5000

u.ensure_dataset_and_registry()

if not u.robots_allowed(URL):
    raise SystemExit(f"BLOCKED: robots.txt disallows {URL}")

print(f"POSTing DevExtreme loadOptions body to {URL} ...")
rows, seen = [], set()
skip = 0

# lane_d_util.get()'s POST path sends `data=` as an urlencoded form; DevExtreme's
# loadOptions endpoint wants a JSON body. Post directly with requests, but still route
# every call through the shared rate limiter / UA for consistency with the rest of the lane.
import requests
session = requests.Session()
session.headers.update({"User-Agent": u.UA, "Content-Type": "application/json"})

while True:
    body = {"skip": skip, "take": PAGE, "requireTotalCount": True,
            "sort": [{"selector": "petitionNumber", "desc": False}]}
    u._throttle(URL)
    r = session.post(URL, json=body, timeout=300)
    r.raise_for_status()
    data = r.json().get("data") or []
    if not data:
        break
    new = 0
    for rec in data:
        k = (rec.get("petitionNumber"), rec.get("typeName"), rec.get("date"), rec.get("appealID"))
        if k in seen:
            continue
        seen.add(k)
        rows.append(rec)
        new += 1
    print(f"  skip={skip}: got {len(data)} records ({new} new), running total {len(rows)}")
    if len(data) > PAGE or new == 0 or len(data) < PAGE:
        break
    skip += PAGE
    time.sleep(0.5)  # additional politeness on top of the 1s/host throttle already paid

print(f"Pulled {len(rows)} total determination records")
if not rows:
    raise SystemExit("ABORT: zero rows pulled, refusing to load/register")

# raw-first: serialize nested structures, keep everything else as-is (load_to_bq stringifies)
clean_rows = []
for rec in rows:
    out = {}
    for k, v in rec.items():
        if isinstance(v, (list, dict)):
            out[k] = json.dumps(v, ensure_ascii=False)
        else:
            out[k] = v
    clean_rows.append(out)

n = u.load_to_bq(
    TABLE, clean_rows,
    source="www.in.gov IBTR DevExtreme determinations API",
    method="POST loadOptions, paged skip/take, publisher currently returns whole corpus per call",
    notes=(f"Lane D freshness refresh of appeals_in_ibtr_determinations "
           f"(6,953 IN rows held in si_signals, observed 2004-01-07..2026-08-05). "
           f"Pulled {len(rows)} determination records this run. ALL published fields captured "
           f"raw-first (nested structures JSON-serialized). Time-sensitivity payoff: compare "
           f"the publisher's own disposition/type/date fields against held rows to find "
           f"petitions that have since been decided."),
)
print(f"DONE: {n} rows loaded to {TABLE}")
