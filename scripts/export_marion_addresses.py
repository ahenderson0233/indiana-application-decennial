"""G121b - make ADDRESS search actually work, for the one county where we can do it honestly.

    python scripts/export_marion_addresses.py

The map search bar (G121) declines street addresses, and the reason is sound: this application has
no geocoder, an address resolves to a street CENTRELINE, and a centreline is not a parcel.

⭐ BUT THAT IS AN ARGUMENT AGAINST GEOCODING, NOT AGAINST ADDRESSES. Marion County publishes its
own address-to-parcel crosswalk, and we already hold it - 347,049 rows, 342,155 of them carrying a
street number. Matching a typed address against the COUNTY'S OWN RECORD is not geocoding; it is
looking up the answer the assessor already published. No centreline is involved at any point.

⛔ MARION ONLY, AND THE BOX SAYS SO. There is no equivalent crosswalk for the other 91 counties -
this is the same gap that caps G82 at 342 of 1,139 owner-grain rows and blocks G70/G71/G104, and
the DLGF Gateway pull is what closes it. An address outside Marion returns the explanation, never
a silent miss.

⚠ 98.2% of the crosswalk's state parcel numbers resolve to a parcel we hold (340,231 of 346,515).
The remainder are dropped rather than shipped as dead keys - a search result that flies nowhere is
worse than an honest "not found".

⭐ THE INDEX SHIPS KEYS, NOT COORDINATES. Once an address yields a parcel key, the search bar hands
it to the route G39 already built (`?fips=&parcel=`), which loads the county, fits the parcel's own
OUTLINE and opens its evidence panel. So the address lands on the parcel, not on a point near it -
which is the whole difference between this and a geocoder.

⚠ Normalisation is deliberately IDENTICAL to `build_si_address_to_parcel.py` (G82). Two different
normalisers over the same corpus would silently disagree about which addresses exist.

Loaded ON FIRST ADDRESS SEARCH, never at boot.
READS indiana_app ONLY.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import json
import gzip
import os
import re
import datetime
from google.cloud import bigquery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

DIRS = r"(?:N|S|E|W|NE|NW|SE|SW|NORTH|SOUTH|EAST|WEST)"
SUFFIX = (r"(?:STREET|ST|AVENUE|AVE|ROAD|RD|DRIVE|DR|LANE|LN|BOULEVARD|BLVD|COURT|CT|PLACE|PL|"
          r"CIRCLE|CIR|PARKWAY|PKWY|TERRACE|TER|WAY|TRAIL|TRL|HIGHWAY|HWY|PIKE|SQUARE|SQ)")
UNIT = r"(?:SUITE|STE|UNIT|APT|APARTMENT|FLOOR|FL|BLDG|BUILDING|ROOM|RM|#)"


def norm_addr(raw):
    """'500 S. POLK STREET SUITE 15' -> ('500', 'POLK'). Must match G82's normaliser exactly."""
    s = str(raw or "").upper()
    s = re.sub(r"[.,]", " ", s)
    s = re.sub(rf"\b{UNIT}\b.*$", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    m = re.match(r"^(\d+)\s+(.*)$", s)
    if not m:
        return None, None
    num, rest = m.group(1), m.group(2)
    rest = re.sub(rf"^{DIRS}\s+", " ", rest)
    rest = re.sub(rf"\s+{DIRS}$", " ", rest)
    rest = re.sub(rf"\s+{SUFFIX}$", " ", rest)
    rest = re.sub(r"[^A-Z0-9 ]", " ", rest)
    rest = re.sub(r"\s+", " ", rest).strip()
    return (num, rest) if rest else (num, None)


def _selftest():
    assert norm_addr("500 S. POLK STREET SUITE 15") == ("500", "POLK")
    assert norm_addr("12550 RICHLANE DR") == ("12550", "RICHLANE")
    assert norm_addr("16 EAST 9TH STREET") == ("16", "9TH")
    assert norm_addr("PO BOX 1234") == (None, None)


_selftest()

# ⛔ INDEX ONLY WHAT THE MAP CAN ACTUALLY OPEN. Measured 2026-08-19b: joining to `in_sites` gave
# 319,871 addresses, and only 12.4% of them pointed at a parcel present in the SHIPPED county
# file. Marion holds 340,765 parcels; `data/sites/18097.geojson.gz` carries 44,240, because the
# county files ship the SCREENED set rather than every house. So five addresses in six resolved to
# a key the map would then fail to find — a search that says "found" and goes nowhere, which is
# worse than "not found".
# Indexing against the county file instead makes every hit openable and shrinks the payload ~8x.
# ⚠ The consequence is deliberate and must be said on screen: a residential address returns
# nothing, because a house is not a siting candidate and this map does not draw one.
_sites_path = os.path.join(REPO, "data", "sites", "18097.geojson.gz")
with gzip.open(_sites_path, "rt", encoding="utf-8") as _f:
    _fc = json.load(_f)
DRAWN = {ft["properties"]["parcel_key"] for ft in _fc.get("features", [])
         if ft.get("properties", {}).get("parcel_key")}
print(f"parcels the map actually draws in Marion: {len(DRAWN):,}")

rows = [r for r in client.query(f"""
  SELECT x.STNUMBER, x.FULL_STNAME, x.STREET_NAME,
         REGEXP_REPLACE(x.STATEPARCELNUMBER, r'[^0-9]', '') AS pk
  FROM `{DS}.in_marion_parcel_crosswalk` x
  WHERE x.STNUMBER IS NOT NULL AND TRIM(x.STNUMBER) NOT IN ('', '0')
    AND x.STATEPARCELNUMBER IS NOT NULL""") if r["pk"] in DRAWN]
print(f"crosswalk rows whose parcel the map draws: {len(rows):,}")

idx, dropped = {}, 0
# ⛔ 15% OF ADDRESSES COVER MORE THAN ONE PARCEL, and silently keeping the first would be a hidden
# editorial choice of exactly the kind this project keeps finding. Condominiums, split lots and
# multi-parcel campuses all share a street address. The first parcel is still what the search
# opens - it has to open something - but the COUNT rides along so the panel can say "3 parcels
# share this address" instead of implying the one it picked is the whole site.
amb = {}
for r in rows:
    hit = False
    for street in (r.FULL_STNAME, r.STREET_NAME):
        num, stem = norm_addr(f"{r.STNUMBER} {street or ''}")
        if not (num and stem):
            continue
        k = f"{num}|{stem}"
        if k in idx:
            if idx[k] != r.pk:
                amb[k] = amb.get(k, 1) + 1
            hit = True
            continue
        idx[k] = r.pk
        hit = True
    if not hit:
        dropped += 1
collide = sum(amb.values()) - len(amb)

payload = {
    "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "county_fips": "18097",
    "county_name": "Marion",
    "n": len(idx),
    "note": ("Marion County's OWN published address-to-parcel crosswalk, restricted to the "
             "parcels this map actually draws. A lookup of the assessor's record, NOT a geocode - "
             "no street centreline is involved and the result is a parcel, not a point near one. "
             "Residential addresses are absent by design: a house is not a siting candidate. No "
             "other Indiana county publishes an equivalent crosswalk, which is the same gap that "
             "blocks G70, G71, G82 and G104."),
    "drawn_parcels": len(DRAWN),
    "idx": idx,
    # only the ambiguous ones, so the cost is 15% of keys rather than a count on every entry
    "multi": amb,
    "n_multi": len(amb),
}
out = os.path.join(REPO, "data", "marion_addresses.json.gz")
with gzip.open(out, "wt", encoding="utf-8", compresslevel=9) as f:
    json.dump(payload, f, separators=(",", ":"))

print(f"  addresses indexed        : {len(idx):,}")
print(f"  rows yielding no address : {dropped:,}")
print(f"  addresses with >1 parcel : {len(amb):,}  (first kept, count shipped so the UI can say so)")
print(f"  size                     : {os.path.getsize(out):,} bytes gzipped")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'data/marion_addresses.json.gz',
 'indiana_app.in_marion_parcel_crosswalk x in_sites',
 'street number + normalised street stem -> 18-digit state parcel key, for rows whose parcel we '
 'actually hold; normalisation identical to build_si_address_to_parcel.py so the two cannot '
 'disagree about which addresses exist. Loaded on first address search, never at boot. '
 'RE-SCRAPE COMMAND: python scripts/export_marion_addresses.py',
 {len(idx)}, 0.0, CURRENT_TIMESTAMP(),
 'G121b. Makes address search work for Marion County WITHOUT geocoding - it is a lookup of the '
 'county published record, so the result is a parcel and not a point near one. Marion only; '
 'no other county publishes an equivalent crosswalk.'
)""").result()
print("  _registry row written")
print("MARION ADDRESS INDEX COMPLETE")
