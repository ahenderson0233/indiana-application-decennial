"""G88 + G89 - put the data-centre counts, the serving utility and the moratorium lapse date onto
the county surface.

    python scripts/build_county_dc_wiring.py

Merges two tables into `data/county_context.json` under each county's own entry:

    dc_posture      in_dc_county_posture   listed / approved / proposed / denied / withdrawn,
                                           the serving utility, and the city-precision caveat
    action_expiry   in_dc_action_expiry    when a moratorium or ban lapses, and on what basis

⚠ MERGE, DO NOT REWRITE. `county_context.json` is written by `export_signoff_payloads.py` and then
ADDED TO by several build scripts (`build_p36_wiring.py`, `build_t3_t4.py`). The checkpoint learned
this the hard way -- the file "lost iocs" once because a writer rebuilt it from scratch. So this
script loads, adds two keys per county, and writes back. It is idempotent and order-independent
with respect to the other mergers, as long as it runs AFTER the file exists.

⛔ THE TWO DATA-CENTRE COUNTS COME FROM DIFFERENT SOURCES AND MUST NOT BE SUMMED - see the header
of `build_dc_county_posture.py`. `dc_listed` is a directory listing; `dc_approved` is a verified
act of a county body. A county can have both, either, or neither, and adding them would count one
project twice.

⛔ `dc_listed` MUST NEVER RENDER WITHOUT `dc_listed_city_precision` beside it. 92 of 249 pins are
census-gazetteer city centroids and 32 of those sit on ONE point.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import json
import os
from google.cloud import bigquery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DS = "energy-platfrom.indiana_app"
CTX = os.path.join(REPO, "data", "county_context.json")
client = bigquery.Client(project="energy-platfrom")

with open(CTX, encoding="utf-8") as f:
    ctx = json.load(f)
before_keys = {k: sorted(v.keys()) for k, v in list(ctx["by_fips"].items())[:1]}
print(f"county_context.json: {len(ctx['by_fips'])} counties, sample keys {before_keys}")

n_posture = 0
for r in client.query(f"""
    SELECT county_geoid, county_name, dc_listed, dc_listed_city_precision,
           dc_listed_site_precision, dc_approved, dc_proposed, dc_denied, dc_withdrawn,
           primary_utility, primary_utility_pct, n_utilities, n_utilities_covering_half,
           operators, utilities
    FROM `{DS}.in_dc_county_posture`"""):
    ent = ctx["by_fips"].setdefault(r.county_geoid, {})
    ent["dc_posture"] = {
        "listed": r.dc_listed,
        "listed_city_precision": r.dc_listed_city_precision,
        "listed_site_precision": r.dc_listed_site_precision,
        "approved": r.dc_approved,
        "proposed": r.dc_proposed,
        "denied": r.dc_denied,
        "withdrawn": r.dc_withdrawn,
        "operators": list(r.operators) if r.operators else [],
        "primary_utility": r.primary_utility,
        "primary_utility_pct": r.primary_utility_pct,
        "n_utilities": r.n_utilities,
        "n_utilities_covering_half": r.n_utilities_covering_half,
        # keep only what a popup can show; the full list lives in the warehouse
        "utilities": [{"utility": u["utility"], "type": u["utility_type"],
                       "pct": u["pct_of_county"], "customers": u["customers"]}
                      for u in (r.utilities or [])][:6],
    }
    n_posture += 1

# G72/G80: severe-weather history, merged by the SAME writer rather than a second one. A second
# merger into this file is how the dc_posture block got silently wiped by export_grid_sentiment --
# one file, one merger, one self-heal to protect it.
n_wx = 0
for r in client.query(f"""
    SELECT county_geoid, tornado_all, tornado_since_2000, tornado_max_ef, tornado_ef3_plus,
           tornado_unrated, hail_all, hail_since_2000, wind_all, wind_since_2000,
           injuries, fatalities, first_year, last_year
    FROM `{DS}.in_severe_weather_county`"""):
    ent = ctx["by_fips"].setdefault(r.county_geoid, {})
    ent["severe_weather"] = {
        "tornado": r.tornado_all, "tornado_since_2000": r.tornado_since_2000,
        "tornado_max_ef": r.tornado_max_ef, "tornado_ef3_plus": r.tornado_ef3_plus,
        "tornado_unrated": r.tornado_unrated,
        "hail": r.hail_all, "hail_since_2000": r.hail_since_2000,
        "wind": r.wind_all, "wind_since_2000": r.wind_since_2000,
        "injuries": r.injuries, "fatalities": r.fatalities,
        "first_year": r.first_year, "last_year": r.last_year,
    }
    n_wx += 1

# ⚠ Keyed by county NAME, because in_dc_action_expiry carries the jurisdiction's county name
# rather than a geoid. The name->geoid map is built from the posture table, which was itself
# asserted to match on all 92, so nothing can silently fall on the floor here.
name_to_fips = {r.county_name: r.county_geoid for r in client.query(
    f"SELECT county_geoid, county_name FROM `{DS}.in_dc_county_posture`")}

n_exp, orphan = 0, []
for r in client.query(f"""
    SELECT county, jurisdiction, action_type, effective_from, expiry_date, expiry_basis,
           expiry_duration_label, expiry_condition_verbatim, expiry_note, is_expired,
           days_remaining, official_url
    FROM `{DS}.in_dc_action_expiry` ORDER BY county"""):
    fips = name_to_fips.get((r.county or "").strip())
    if not fips:
        orphan.append(r.county)
        continue
    ctx["by_fips"].setdefault(fips, {}).setdefault("action_expiry", []).append({
        "jurisdiction": r.jurisdiction,
        "action_type": r.action_type,
        "effective_from": str(r.effective_from) if r.effective_from else None,
        "expiry_date": str(r.expiry_date) if r.expiry_date else None,
        "expiry_basis": r.expiry_basis,
        "duration": r.expiry_duration_label,
        "condition": r.expiry_condition_verbatim,
        "note": r.expiry_note,
        "is_expired": r.is_expired,
        "days_remaining": r.days_remaining,
        "url": r.official_url,
    })
    n_exp += 1

if orphan:
    print(f"⛔ {len(orphan)} expiry rows matched no county: {orphan}")

with open(CTX, "w", encoding="utf-8") as f:
    json.dump(ctx, f, separators=(",", ":"))

print(f"  dc_posture written on   : {n_posture} counties")
print(f"  severe_weather written  : {n_wx} counties")
print(f"  action_expiry written on: {n_exp} actions")
print(f"  file size               : {os.path.getsize(CTX):,} bytes")

# prove the merge did not drop what other writers put there
sample = ctx["by_fips"]["18089"]
print(f"  Lake County keys        : {sorted(sample.keys())}")
print(f"  Lake dc_posture         : listed={sample['dc_posture']['listed']} "
      f"(city {sample['dc_posture']['listed_city_precision']}) "
      f"approved={sample['dc_posture']['approved']} "
      f"utility={sample['dc_posture']['primary_utility']}")
print("COUNTY DC WIRING COMPLETE")
