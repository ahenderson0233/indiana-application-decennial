"""Lane D refresh: SRI Services active tax-sale listings, INDIANA SLICE ONLY (D1 signal).

Feeds si_signals source_id = si_d1_sri_taxsale_listings (80,056 IN rows held, observed
2000-03-27 .. 2026-10-20 -- note future dates are scheduled auction dates, expected).
Registry-mapped endpoint (public JSON API, embedded anonymous key shipped to every
visitor's browser -- no account, no login -- BUILT+LOADED before across 5 states):
  https://sriservicesusermgmtprod.azurewebsites.net/api/property/carddetail

This is the "multi-state source with an Indiana slice" case handled per the ENDPOINT's
OWN state parameter (state=IN in the request body), not by guessing a column -- the
publisher's API natively scopes by state and county. Per Lane C's 2026-08-14 registry
pre-check, this source was already fully re-acquired for all 5 active states via
`python -m ingest.load_sri_taxsale_bq --force` and NOT re-pulled by Lane C. Lane D
re-pulls the INDIANA SLICE ONLY (not the other 4 states -- out of scope for this lane)
into our OWN staging table so the freshness diff is measured independently, without
touching (or depending on the freshness of) the shared `energy.si_d1_sri_taxsale_listings`
table.

Mechanism (read from energy-platform/ingest/load_sri_taxsale_bq.py, itself unmodified --
read-only reference; this script is an independent implementation writing only to
indiana_app):
  GET  /api/property/countylistbystate?stateCode=IN
  POST /api/property/carddetail {county:<id>, state:'IN', recordCount:50000, ...}
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lane_d_util as u
import requests

BASE = "https://sriservicesusermgmtprod.azurewebsites.net/api/property"
API_KEY = "9f8fd9fe5160294175e1c737567030f495d838a7922a678bc06e0a093910"
TABLE = "in_si_refresh_sri_taxsale_in"
PAGE = 50000

u.ensure_dataset_and_registry()

session = requests.Session()
session.headers.update({"User-Agent": u.UA, "x-api-key": API_KEY,
                        "Content-Type": "application/json", "Accept": "application/json"})

u._throttle(BASE)
counties = session.get(BASE + "/countylistbystate", params={"stateCode": "IN"}, timeout=60).json()
print(f"Indiana counties on SRI roster: {len(counties)}")

pulled_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
all_rows = []
n_counties_with_rows = 0
for cty in counties:
    body = {"auctionDateRange": "", "auctionStyle": "", "county": cty["id"],
            "propertySaleType": "", "recordCount": PAGE, "saleStatus": "",
            "searchText": "", "startIndex": 0, "state": "IN"}
    u._throttle(BASE)
    r = session.post(BASE + "/carddetail", json=body, timeout=180)
    r.raise_for_status()
    props = r.json().get("properties") or []
    if props:
        if len(props) >= PAGE:
            raise RuntimeError(f"PAGINATION ALARM IN/{cty['id']}: {len(props)} rows == recordCount cap")
        for p in props:
            row = dict(p)
            row["roster_county_id"] = cty["id"]
            row["roster_county_name"] = cty.get("name", "")
            all_rows.append(row)
        n_counties_with_rows += 1
        print(f"  IN/{cty.get('name', cty['id'])[:20]:<20} {len(props)} rows")

print(f"Total IN rows: {len(all_rows)} across {n_counties_with_rows} of {len(counties)} roster counties")
if not all_rows:
    raise SystemExit("ABORT: zero rows pulled, refusing to load/register")

n = u.load_to_bq(
    TABLE, all_rows,
    source="sriservicesusermgmtprod.azurewebsites.net (SRI Services tax-sale platform, IN slice only)",
    method="POST carddetail per IN county, recordCount=50000, state='IN' param scoped by the endpoint itself",
    notes=(f"Lane D freshness refresh of si_d1_sri_taxsale_listings/D1, INDIANA SLICE ONLY "
           f"(80,056 IN rows held in si_signals, observed 2000-03-27..2026-10-20). Pulled "
           f"{len(all_rows)} rows across {n_counties_with_rows} of {len(counties)} IN roster "
           f"counties this run. Other 4 active states (AL/CO/FL/LA/MI) deliberately NOT "
           f"re-pulled here -- Lane C's 2026-08-14 registry pre-check already re-acquired the "
           f"full multi-state corpus (217,226 rows total) via the existing loader; this is an "
           f"independent Indiana-only measurement for the freshness diff, not a duplicate of "
           f"that acquisition. saleTypeDescription/saleStatusCode/Description carry the "
           f"remediation signal (Redemption/Adjudicated/etc. vs an active upcoming sale)."),
)
print(f"DONE: {n} rows loaded to {TABLE}")
