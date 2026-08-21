"""G140: THE READ-ONLY RE-SCRAPE REHEARSAL — does the publisher have EVENTS we do not?

Operator, 2026-08-21: *"it may be beneficial to rescrape ALL of our datasets to ensure that they
continue to work… so we can set up a rescraping schedule."* Then, asked whether to do it read-only
first: *"Yes, it is fine to read only first."*

================================================================================================
⛔ WHY A REHEARSAL AND NOT JUST A RE-RUN
================================================================================================
A blanket re-run is not free and is not safe. From `docs/RESCRAPE_LEDGER.md`, measured:
  · 3 loaders are `append_only` - re-running ADDS rows. `build_gas_facilities.py` did exactly this
    and took compressor features 24 -> 48 on one re-run. Valid GeoJSON, no error, every count
    overstated exactly 2x.
  · 2 loaders READ THEIR OWN OUTPUT while replacing it. `build_land_gates.py` measured
    in_tribal_land.geom, then replaced that table with the column renamed `geog`, so every run
    after the first died on "Unrecognized name: geom" - unrunnable for a day while its registry
    row advertised a working command.
  · 74 have `unknown` idempotency, which means nobody has checked.

⭐ SO THIS ASKS THE PUBLISHER A QUESTION AND WRITES NOTHING. For every SI source that exposes a
count, it compares the LIVE record count against what we hold, and reports the delta. That turns
"should we re-scrape everything" into a list of the sources that actually have something new.

⚠ A DELTA IS NOT AUTOMATICALLY NEW EVENTS. Three honest reasons a count can differ:
  · the publisher added rows            -> a re-scrape gains them
  · our loader FILTERS (Indiana only, severity, date window) -> a smaller count is correct
  · the publisher re-keyed or re-published -> the count moved without new events
The delta is the SIGNAL TO LOOK, never the conclusion. Which is why this prints the filter each
loader applies beside the numbers.

⛔ READ-ONLY. Issues `returnCountOnly=true` metadata queries. Writes nothing, anywhere.

RE-SCRAPE COMMAND: python scripts/rehearse_si_rescrape.py
"""
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import requests
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
c = bigquery.Client(project="energy-platfrom")

# table, live endpoint, and what OUR loader filters to - so a smaller count reads as correct
SOURCES = [
    ("in_si_indy_abandoned_vacant",
     "https://gis.indy.gov/server/rest/services/OpenData/OpenData_Infrastructure/MapServer/2",
     "no filter - full layer"),
    ("in_si_refresh_indy_code_enforcement",
     "https://gis.indy.gov/server/rest/services/OpenData/OpenData_NonSpatial/MapServer/1",
     "no filter - full layer (910k rows; the SEVERITY gate is applied downstream, not at load)"),
    ("in_si_southbend_vacant_abandoned",
     "https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services/"
     "AllVacantandAbandonedProperties/FeatureServer/3", "no filter - full layer"),
    ("in_si_southbend_code_enforcement",
     "https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services/"
     "Code_Enforcement_Cases/FeatureServer/0", "no filter - full layer"),
    ("in_si_southbend_continuous_enforcement",
     "https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services/"
     "Continuous_Enforcement/FeatureServer/4", "no filter - full layer"),
    # ⛔ THIS ONE IS FILTERED AND THE FIRST VERSION OF THIS SCRIPT DID NOT SAY SO, which produced
    # the only "finding" in the whole rehearsal: held 4,190 vs live 153,909, +149,719. The layer is
    # ALL Evansville building permits; our loader takes the WRECKING ones. Applying the loader's own
    # predicate live returns 4,190 - exactly what we hold, and nothing to gain.
    # ⚠ A rehearsal that compares a filtered table against an unfiltered endpoint manufactures work.
    ("in_si_evansville_demolition_permits",
     "https://maps.evansvillegis.com/arcgis_server/rest/services/BC/"
     "BUILDING_COMMISSION_PERMITS/MapServer/0",
     "USER_Project_Activity LIKE 'BUILDING WRECKING%' - the layer holds ALL permit types"),
]
# multi-layer services: our table is the UNION of every layer
MULTI = [
    ("in_si_evansville_taxsale",
     "https://maps.evansvillegis.com/arcgis_server/rest/services/SITE_PROJECTS/TAX_SALE/MapServer",
     "union of every year layer"),
    ("in_si_evansville_foreclosures",
     "https://maps.evansvillegis.com/arcgis_server/rest/services/ASSESSOR/FORECLOSURES/MapServer",
     "union of every year layer"),
]


def held(t):
    try:
        return c.get_table(f"{DS}.{t}").num_rows
    except Exception:
        return None


def live_count(url, where="1=1"):
    """⚠ `where` MUST mirror what the loader filters to. Comparing our filtered table against the
    publisher's unfiltered count is not a measurement, it is a category error - see the Evansville
    permits note above."""
    try:
        r = requests.get(url.rstrip("/") + "/query",
                         params={"where": where, "returnCountOnly": "true", "f": "json"},
                         timeout=90)
    except Exception as e:
        return None, f"BLOCKED: {type(e).__name__}: {e}"
    if r.status_code != 200:
        return None, f"BLOCKED: HTTP {r.status_code} {r.reason}"
    try:
        j = r.json()
    except Exception:
        return None, "BLOCKED: response is not JSON"
    if "error" in j:
        return None, f"BLOCKED: {str(j['error'])[:70]}"
    if "count" not in j:
        return None, "layer does not return a count"
    return j["count"], None


def layers_of(url):
    try:
        j = requests.get(url.rstrip("/") + "?f=json", timeout=90).json()
        return [l["id"] for l in j.get("layers", [])]
    except Exception:
        return []


print("=" * 100)
print("G140 - READ-ONLY RE-SCRAPE REHEARSAL, SI SIGNAL SOURCES")
print("=" * 100)
print("⛔ WRITES NOTHING. Asks each publisher for a record count and compares it to what we hold.\n")
print(f"{'source':40} {'held':>9} {'live':>9} {'delta':>9}  note")
print("-" * 100)

gains, blocked, same = [], [], 0
for t, url, filt in SOURCES:
    h = held(t)
    # if the filter note IS a predicate, apply it live
    where = filt.split(" - ")[0] if re.search(r"[=<>]|LIKE", filt.split(" - ")[0]) else "1=1"
    n, note = live_count(url, where)
    if n is None:
        blocked.append((t, note))
        print(f"{t:40} {h if h is None else format(h, ',>9')} {'—':>9} {'—':>9}  {note}")
        continue
    d = n - (h or 0)
    if d > 0:
        gains.append((t, h, n, d, filt))
    elif d == 0:
        same += 1
    print(f"{t:40} {h:>9,} {n:>9,} {d:>+9,}  {filt}")

for t, url, filt in MULTI:
    h = held(t)
    ids = layers_of(url)
    tot, bad = 0, 0
    for i in ids:
        n, note = live_count(f"{url.rstrip('/')}/{i}")
        if n is None:
            bad += 1
        else:
            tot += n
    if not ids:
        blocked.append((t, "service root unreadable"))
        continue
    d = tot - (h or 0)
    if d > 0:
        gains.append((t, h, tot, d, filt))
    elif d == 0:
        same += 1
    print(f"{t:40} {h:>9,} {tot:>9,} {d:>+9,}  {filt}; {len(ids)} layers"
          + (f", {bad} unreadable" if bad else ""))

# the WARN page is HTML, not ArcGIS - counted by its own re-scrape
try:
    wp = c.get_table(f"{DS}.in_si_warn_page").num_rows
    wn = c.get_table(f"{DS}.in_si_warn_normalised").num_rows
    print(f"{'in_si_warn_normalised':40} {wn:>9,} {wp:>9,} {wp - wn:>+9,}  "
          f"live count from in_si_warn_page (refresh_warn_page.py); no archive page exists")
    if wp - wn > 0:
        gains.append(("in_si_warn_normalised", wn, wp, wp - wn, "HTML listing"))
    else:
        same += 1
except Exception:
    pass

print("\n" + "=" * 100)
print(f"{same} source(s) unchanged · {len(gains)} with MORE rows live than we hold · "
      f"{len(blocked)} blocked")
print("=" * 100)
if gains:
    print("\n⭐ THESE HAVE SOMETHING NEW. Re-run the named loader for each - and read it first if")
    print("   docs/RESCRAPE_LEDGER.md marks it append_only or unknown.")
    for t, h, n, d, filt in gains:
        print(f"   {t}: held {h:,} -> live {n:,}  (+{d:,})   [{filt}]")
else:
    print("\n⭐ NOTHING TO GAIN: every comparable SI source holds what the publisher currently "
          "offers.")
for t, why in blocked:
    print(f"\n⚠ {t}: {why}")
print("\n⛔ NOTHING WAS WRITTEN. This is a rehearsal; executing is a separate, explicit step.")
