"""G154: PLACE THE RECOVERED WARN ADDRESSES BY GEOCODING, NOT BY MATCHING STRINGS.

88 facility addresses were recovered from the WARN filing PDFs and 51 reached a parcel. The other
37 match no parcel on street+city even after suffix and directional normalisation on both sides.

================================================================================================
⛔ THE CAUSE IS NOT SPELLING, WHICH IS WHY MORE REGEX WOULD NOT HAVE HELPED
================================================================================================
The DLGF address is the ASSESSOR'S address for a LOT. A medical campus or a distribution park does
not have one per building. Ascension files `2415A Mitchell Road`, `2415C Mitchell Road` and
`2512 Q Street` in Bedford — suite addresses on one campus that the assessor carries under a single
base parcel address, or under none at all. Same shape for `9590 Allpoints Parkway`.

⭐ SO STOP COMPARING TEXT AND START COMPARING GEOMETRY. Geocode the recovered address to a
coordinate, then ask which parcel polygon CONTAINS that coordinate. That is how a suite address on
a campus resolves to the lot it stands on, and it is the method `in_si_gov_surplus_v2` already uses
for the federal points.

================================================================================================
THE GEOCODER, AND THE PERMISSION CHECK
================================================================================================
US Census Geocoder, `geocoding.geo.census.gov` — a public federal endpoint, no key, no account.
⚠ CHECKED BEFORE THE FIRST CALL, per the standing rule, and the answer is recorded either way:
  · `https://geocoding.geo.census.gov/robots.txt` -> HTTP 404. No robots policy is published, so
    there is no directive to honour or to violate.
  · `https://geocoding.geo.census.gov/geocoder/` -> HTTP 200, the public documentation page.
  · No CAPTCHA, no user-agent condition, no account. Nothing is bypassed here.
This script re-runs that check on every run and REFUSES to geocode if the answer changes.

⛔ AND THE MATCH IS GRADED, BECAUSE A COORDINATE IS NOT A PLACEMENT.
A rooftop or street-interpolated point that falls inside a parcel polygon is a match. A point that
lands nowhere, or whose matched house number differs from the one in the filing, is REFUSED and
carried as a refusal. A pin someone plans around must be earned — the same reason
`build_warn_placement.py` refuses a pass-2 match that is ambiguous.

⚠ EXPECT THIS TO RECOVER MOST OF THE 37, NOT ALL. The residue is reported with its reason.

RE-SCRAPE COMMAND: python scripts/geocode_warn_addresses.py
⚠ IDEMPOTENT: replace_safe. Depends on in_si_warn_addresses and in_si_warn_placed.
⛔ THEN RE-RUN scripts/build_si_signal_v2.py and the exporters.
"""
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import requests
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_si_warn_geocoded"
D85 = "080500000047000018"
BENCH = "Public_AR_Current"
URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
client = bigquery.Client(project="energy-platfrom")


def permission_check():
    """⛔ Re-run every time. A wall is an OBSERVATION, not a property of a host - four robots-403
    walls in this project's history did not reproduce on re-test, and the inverse is just as
    possible: a host that was open can close."""
    print("PERMISSION CHECK (recorded either way, per the standing rule)")
    try:
        r = requests.get("https://geocoding.geo.census.gov/robots.txt", timeout=45)
        if r.status_code == 200 and "Disallow: /" in r.text:
            print(f"  ⛔ BLOCKED. robots.txt now says, verbatim:\n{r.text[:400]}")
            return False
        print(f"  robots.txt -> HTTP {r.status_code} "
              f"({'no policy published' if r.status_code == 404 else 'no blanket Disallow'})")
    except Exception as e:
        print(f"  ⚠ robots.txt unreachable ({type(e).__name__}) - treating as unknown, not as "
              f"permission. Refusing.")
        return False
    print("  no CAPTCHA, no account, no user-agent condition. Proceeding.")
    return True


def geocode(one_line):
    try:
        r = requests.get(URL, params={"address": one_line, "benchmark": BENCH, "format": "json"},
                         timeout=60)
    except Exception as e:
        return None, f"BLOCKED: {type(e).__name__}"
    if r.status_code != 200:
        return None, f"BLOCKED: HTTP {r.status_code} {r.reason}"
    try:
        m = r.json()["result"]["addressMatches"]
    except Exception:
        return None, "response is not the documented shape"
    if not m:
        return None, "the geocoder found no match for this address"
    best = m[0]
    c = best.get("coordinates") or {}
    if c.get("x") is None or c.get("y") is None:
        return None, "matched but returned no coordinate"
    return {"lon": float(c["x"]), "lat": float(c["y"]),
            "matched": best.get("matchedAddress", ""),
            "n_matches": len(m)}, None


def house_no(s):
    """The leading house number, or '' - used to grade the match."""
    tok = str(s or "").strip().split(" ")
    return tok[0] if tok and tok[0].isdigit() else ""


print("=" * 96)
print("G154 - GEOCODE THE WARN ADDRESSES THAT NO STRING MATCH COULD PLACE")
print("=" * 96)
if not permission_check():
    raise SystemExit("\n⛔ Refusing to geocode. Recorded as BLOCKED, which is a valid outcome.")

todo = list(client.query(f"""
  SELECT a.company, a.facility_street, a.facility_city, a.facility_zip, a.notice_pdf_url
  FROM `{DS}.in_si_warn_addresses` a
  LEFT JOIN `{DS}.in_si_warn_placed` p
    ON p.company = a.company AND p.facility_street = a.facility_street
  WHERE a.verdict = 'facility' AND p.parcel_key IS NULL
    AND a.facility_street IS NOT NULL AND a.facility_city IS NOT NULL
""").result())
print(f"\n{len(todo)} recovered facility address(es) that no string match could place\n")

rows, blocked = [], 0
for i, t in enumerate(todo, 1):
    one = f"{t.facility_street}, {t.facility_city}, IN"
    if t.facility_zip:
        one += f" {t.facility_zip}"
    g, why = geocode(one)
    if g is None:
        blocked += 1
        print(f"  [{i:>2}] {t.facility_street[:46]:46} REFUSED: {why}")
        rows.append({"company": t.company, "facility_street": t.facility_street,
                     "facility_city": t.facility_city, "notice_pdf_url": t.notice_pdf_url,
                     "lat": None, "lon": None, "matched_address": None,
                     "geocode_grade": "no_match", "refuse_reason": why})
    else:
        # ⛔ GRADE IT. A geocoder returns its best guess, not a promise. If the house number it
        # matched is not the one in the filing, it has snapped to a different building on the
        # street and placing it would be a pin someone plans around.
        want, got = house_no(t.facility_street), house_no(g["matched"])
        grade = "rooftop_or_interpolated" if (want and want == got) else "street_only"
        rows.append({"company": t.company, "facility_street": t.facility_street,
                     "facility_city": t.facility_city, "notice_pdf_url": t.notice_pdf_url,
                     "lat": g["lat"], "lon": g["lon"], "matched_address": g["matched"],
                     "geocode_grade": grade,
                     "refuse_reason": None if grade == "rooftop_or_interpolated"
                     else f"house number {want or '?'} != matched {got or '?'}"})
        print(f"  [{i:>2}] {t.facility_street[:46]:46} {grade:24} {g['matched'][:44]}")
    time.sleep(0.4)          # ⚠ courteous rate, unasked for but not optional

if not rows:
    raise SystemExit("nothing to geocode")

schema = [bigquery.SchemaField(n, ty) for n, ty in [
    ("company", "STRING"), ("facility_street", "STRING"), ("facility_city", "STRING"),
    ("notice_pdf_url", "STRING"), ("lat", "FLOAT64"), ("lon", "FLOAT64"),
    ("matched_address", "STRING"), ("geocode_grade", "STRING"), ("refuse_reason", "STRING")]]
client.load_table_from_json(
    rows, f"{DS}.in_si_warn_geocode_raw",
    job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE")).result()

# ⛔ D85 EXCLUDED. It is an inverted whole-Earth polygon; without this guard EVERY point lands on
# it and the fan-out assertion below is what proves the guard worked.
SNAP_M = 150

job = client.query(f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH pt AS (
  SELECT *, IF(lat IS NULL, NULL, ST_GEOGPOINT(lon, lat)) AS g
  FROM `{DS}.in_si_warn_geocode_raw`
  WHERE geocode_grade = 'rooftop_or_interpolated'
),
-- ⭐ CONTAINMENT FIRST. If a parcel polygon contains the point, that is the answer and nothing
-- else is considered.
inside AS (
  SELECT p.company, p.facility_street, s.parcel_source, s.parcel_key, 0.0 AS snap_m
  FROM pt p JOIN `{DS}.in_sites` s
    ON s.parcel_key != '{D85}' AND ST_INTERSECTS(s.parcel_geog, p.g)
),
-- ⛔ THE ROAD TRAP, AND IT IS WHY 22 OF 34 FOUND NO PARCEL ON THE FIRST RUN.
-- The Census `onelineaddress` service returns a STREET-INTERPOLATED point - a position along the
-- road centreline, not the roof. The centreline sits inside the ROAD's own right-of-way parcel,
-- and G122 deliberately excluded roadway parcels from the candidate set. So the honest first
-- answer was "no parcel contains this point", and it was true and useless.
-- ⚠ This is the SAME defect G120(b) already documented from the other direction: "the address
--   geocoded onto the ROAD, the road is its own right-of-way parcel, and that parcel genuinely
--   has no building."
-- ⭐ So a point that lands in no parcel is snapped to the NEAREST parcel within {SNAP_M} m.
--
-- ⛔ BUT PROXIMITY ALONE IS NOT ENOUGH, AND THE OPERATOR WAS RIGHT TO PUSH ON IT.
-- Operator, 2026-08-21: *"would you not be able to geocode the address to the parcel itself?"*
-- ⚠ CHECKED, PER G25, BEFORE ANSWERING - and we DO hold a rooftop corpus, but it does not help
--   these rows:
--     · energy.mat_si_rooftop_geocode - 5,880 Indiana rows, EVERY one at precision_tier
--       'INVALID_state_centroid' on the identical point (40.1084, -86.2258) with
--       usable_for_distance = FALSE. It is a placeholder that honestly labels itself as one.
--     · energy.mat_si_address_location - 51,821 GENUINE Indiana rooftop geocodes
--       (precision_tier 'rooftop_geocode', location_method 'building_footprint_geocode',
--       46,530 distinct points). Real, and it covers exactly **1 of our 88** WARN addresses.
--   There is no free federal ROOFTOP geocoder; the Census service interpolates along a street by
--   design. So the answer is not a better geocoder - it is CORROBORATION.
--
-- ⭐ THE SNAP IS THEREFORE REQUIRED TO AGREE WITH THE PARCEL'S OWN ADDRESS. The nearest parcel is
--   accepted only if the DLGF property address on that parcel names the SAME STREET as the
--   filing. That rules out snapping across the road or onto the lot behind, which pure proximity
--   cannot. A parcel that is both within {SNAP_M} m of the geocoded point AND carries an address
--   on the same street is a corroborated match by two independent routes.
-- ⛔ A snap the street does NOT corroborate is refused, not down-weighted. A pin someone plans
--   around has to be earned.
pstreet AS (
  SELECT s.parcel_source, s.parcel_key, s.parcel_geog,
         -- the street NAME only: drop the leading house number, keep the rest
         TRIM(REGEXP_REPLACE(REGEXP_REPLACE(UPPER(IFNULL(l.prop_address, '')),
              r'^[0-9]+[A-Z]?\\s+', ''), r'[^A-Z0-9 ]', ' ')) AS street_words
  FROM `{DS}.in_sites` s
  JOIN `{DS}.in_parcel_location` l USING (parcel_source, parcel_key)
  WHERE s.parcel_key != '{D85}' AND l.prop_address IS NOT NULL AND l.prop_address != ''
),
near AS (
  SELECT company, facility_street, parcel_source, parcel_key, snap_m, street_ok FROM (
    SELECT p.company, p.facility_street, s.parcel_source, s.parcel_key,
           ROUND(ST_DISTANCE(s.parcel_geog, p.g), 1) AS snap_m,
           -- ⚠ token containment, not equality: the filing writes "Industrial Park Drive" and the
           -- assessor "INDUSTRIAL PARK DR", so compare on the distinctive word.
           REGEXP_CONTAINS(
             IFNULL(s.street_words, ''),
             CONCAT(r'\\b',
               REGEXP_REPLACE(
                 TRIM(REGEXP_REPLACE(REGEXP_REPLACE(UPPER(p.facility_street),
                      r'^[0-9]+[A-Z]?\\s+', ''), r'[^A-Z0-9 ]', ' ')),
                 r' .*$', ''),
               r'\\b')) AS street_ok,
           ROW_NUMBER() OVER (PARTITION BY p.company, p.facility_street
                              ORDER BY ST_DISTANCE(s.parcel_geog, p.g)) AS rn
    FROM pt p JOIN pstreet s
      ON ST_DWITHIN(s.parcel_geog, p.g, {SNAP_M})
    WHERE NOT EXISTS (SELECT 1 FROM inside i
                      WHERE i.company = p.company AND i.facility_street = p.facility_street)
  ) WHERE rn = 1
),
hit AS (
  SELECT company, facility_street, parcel_source, parcel_key, snap_m, TRUE AS street_ok
  FROM inside
  UNION ALL
  SELECT company, facility_street, parcel_source, parcel_key, snap_m, street_ok FROM near
)
SELECT g.*,
       IF(h.street_ok, h.parcel_source, NULL) AS parcel_source,
       IF(h.street_ok, h.parcel_key, NULL)    AS parcel_key,
       h.snap_m,
       CASE WHEN g.geocode_grade = 'street_only'
              THEN 'refused: the geocoder snapped to a different house number on the same street'
            WHEN h.parcel_key IS NULL AND g.lat IS NULL
              THEN 'refused: the geocoder found no match'
            WHEN h.parcel_key IS NULL
              THEN 'geocoded, but no parcel within {SNAP_M} m'
            WHEN NOT h.street_ok
              THEN 'refused: the nearest parcel is on a different street, so proximity is not '
                   || 'corroborated'
            WHEN h.snap_m = 0.0 THEN 'placed - the parcel contains the point'
            ELSE 'placed - nearest parcel, corroborated by its own street address'
       END AS placement
FROM `{DS}.in_si_warn_geocode_raw` g
LEFT JOIN hit h ON h.company = g.company AND h.facility_street = g.facility_street
""")
job.result()

f = list(client.query(f"""
  SELECT COUNT(*) n, COUNT(DISTINCT CONCAT(company,'|',facility_street)) d,
         COUNTIF(STARTS_WITH(placement, 'placed')) placed,
         COUNT(DISTINCT IF(STARTS_WITH(placement, 'placed'), parcel_key, NULL)) parcels
  FROM `{OUT}`"""))[0]
fanout = f.n / f.d if f.d else 0
print(f"\n  fan-out {f.n} rows / {f.d} distinct addresses = {fanout:.4f}")
if fanout > 1.05:
    raise SystemExit(f"⛔ fan-out {fanout:.4f} - a point is landing in more than one parcel. "
                     f"Check the D85 guard before trusting any of this.")
print(f"  ⭐ {f.placed} address(es) PLACED on {f.parcels} parcel(s) by geocode + spatial join")
print(f"  ⚠ {f.n - f.placed} refused, each with its reason recorded")
for r in client.query(f"SELECT placement, COUNT(*) n FROM `{OUT}` GROUP BY 1 ORDER BY n DESC"):
    print(f"      {r.n:>3}  {r.placement}")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name IN "
             f"('in_si_warn_geocoded','in_si_warn_geocode_raw')").result()
# ⛔ THE INTERMEDIATE GETS A ROW TOO. The first version registered only the output, which left
# in_si_warn_geocode_raw unregistered - and "every table is registered" is a checkpoint invariant
# that blocks the platform session's own check. An unregistered table is an UNAUDITED table.
client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at)
VALUES ('in_si_warn_geocode_raw', 'US Census Geocoder (geocoding.geo.census.gov)',
 'G154 intermediate: the raw geocoder response per WARN facility address - lat/lon, the address '
 'the geocoder actually matched, and a grade. Kept separate from in_si_warn_geocoded so the '
 'geocode and the spatial join can be re-examined independently; the join is cheap to redo, the '
 'geocode is 34 network calls. RE-SCRAPE COMMAND: python scripts/geocode_warn_addresses.py '
 'IDEMPOTENT: replace_safe.',
 (SELECT COUNT(*) FROM `{DS}.in_si_warn_geocode_raw`), CURRENT_TIMESTAMP())""").result()
client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at)
VALUES ('in_si_warn_geocoded',
 'US Census Geocoder (geocoding.geo.census.gov) + indiana_app.in_sites',
 'G154. The WARN facility addresses that string matching could not place, geocoded against the '
 'Public_AR_Current benchmark and joined by ST_INTERSECTS to in_sites.parcel_geog with D85 '
 'excluded and fan-out asserted <= 1.05. GRADED: a match whose house number differs from the '
 'filing is REFUSED as street_only, never placed. Permission re-checked on every run - robots.txt '
 'returns HTTP 404 (no policy published), no key, no account, no CAPTCHA. '
 'RE-SCRAPE COMMAND: python scripts/geocode_warn_addresses.py IDEMPOTENT: replace_safe. '
 'THEN RE-RUN scripts/build_si_signal_v2.py and the exporters.',
 (SELECT COUNT(*) FROM `{OUT}`), CURRENT_TIMESTAMP())""").result()
print("\n  registered in_si_warn_geocoded")
print("\nDONE")
