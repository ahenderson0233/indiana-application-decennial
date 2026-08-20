"""G125: the parcel's own ADDRESS and a display COORDINATE, as a build - not inside an export.

⛔ THIS EXISTS BECAUSE I BROKE A STANDING RULE AND THE CHECKPOINT CAUGHT IT.
"Builds may read `energy`; EXPORTS MAY NOT." I put the `energy.parcels_in` address join directly
into `export_sites_exact.py`, and the checkpoint failed with:

    no EXPORT reads energy directly: ['scripts/export_sites_exact.py']

The rule is not bureaucratic. An export is on the path to what the user sees, so if an export
depends on `energy` then the application cannot be rebuilt without the platform session's dataset
- and `energy` is READ-ONLY to this workstream and owned by somebody else. The clip has to be a
table we own, in `indiana_app`, with its own registry row and its own re-scrape command.

WHAT IT HOLDS. One row per Indiana parcel, keyed the way the rest of this workstream keys parcels:
  prop_address / prop_city / prop_zip   the DLGF's own property address
  map_lat / map_lon                     a DISPLAY point, published where we have one
  coord_basis                           'published' or 'parcel_interior_point'
  dlgf_class_code                       the property class, which G122 uses to exonerate ribbons

⭐ THE ADDRESS IS STATEWIDE, AND THREE DOCUMENTS SAID OTHERWISE. G125, the handoff and the backlog
all record "address is Marion-only and must say so", on the strength of
`in_si_address_parcel_bridge` (51,309 Marion rows). That table is the address SEARCH crosswalk -
it resolves a typed address to a parcel. This is the reverse lookup and it comes from a different
source: measured, `dlgf_prop_address` is populated on 3,578,398 of 3,637,663 Indiana parcels
(98.4%) across all 92 counties.

⚠ THE COORDINATE IS DISPLAY-ONLY AND MUST STAY THAT WAY. `lat` is published on 2,284,133 of
3,553,194 in_sites rows, so 59.7% of parcels had no point at all and the screener printed "no
coordinate held". Every one of them HAS a polygon, so a point is derived from it and LABELLED.
⛔ Nothing may measure with map_lat/map_lon. "No centroid where a footprint exists" governs
distance, and every distance in this estate is computed against a geography.
⚠ Never emit 0,0: Number(null) is 0 and 0 is finite, which once measured a military base from the
Gulf of Guinea.

⚠ 38,840 `state_parcel_id` values repeat in the parent, so the source is de-duplicated before the
join and fan-out is asserted at exactly 1.0.

RE-SCRAPE COMMAND: python scripts/build_parcel_location.py
⚠ IDEMPOTENT: replace_safe. CADENCE: with the parcel refresh.
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_parcel_location"
D85 = "080500000047000018"

client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH loc AS (
  SELECT state_parcel_id AS parcel_key,
         ANY_VALUE(NULLIF(COALESCE(NULLIF(dlgf_prop_address, ''),
                                   NULLIF(prop_add, '')), ''))            AS prop_address,
         ANY_VALUE(NULLIF(COALESCE(NULLIF(dlgf_prop_address_city, ''),
                                   NULLIF(prop_city, '')), ''))           AS prop_city,
         ANY_VALUE(NULLIF(COALESCE(NULLIF(dlgf_prop_address_zip, ''),
                                   NULLIF(prop_zip, '')), ''))            AS prop_zip,
         ANY_VALUE(NULLIF(dlgf_prop_class_code, ''))                      AS dlgf_class_code
  FROM `energy-platfrom.energy.parcels_in`
  WHERE state_parcel_id IS NOT NULL AND state_parcel_id != '{D85}'
  GROUP BY 1
)
SELECT s.parcel_source, s.parcel_key,
       loc.prop_address, loc.prop_city, loc.prop_zip, loc.dlgf_class_code,
       -- ⛔ DISPLAY ONLY. Never joined on, never measured with.
       COALESCE(s.lat, ST_Y(ST_CENTROID(s.parcel_geog))) AS map_lat,
       COALESCE(s.lon, ST_X(ST_CENTROID(s.parcel_geog))) AS map_lon,
       IF(s.lat IS NOT NULL, 'published', 'parcel_interior_point') AS coord_basis,
       CURRENT_TIMESTAMP() AS built_at
FROM `{DS}.in_sites` s
LEFT JOIN loc ON loc.parcel_key = s.parcel_key
WHERE s.parcel_key != '{D85}' AND s.parcel_geog IS NOT NULL
"""

print("G125 - PARCEL LOCATION (address + display coordinate)")
job = client.query(SQL)
job.result()
gb = round((job.total_bytes_processed or 0) / 1e9, 2)
print(f"  built, {gb} GB scanned")

f = list(client.query(f"""
  SELECT COUNT(*) n, COUNT(DISTINCT CONCAT(parcel_source,'/',parcel_key)) d,
         COUNTIF(prop_address IS NOT NULL) adr,
         COUNTIF(map_lat IS NOT NULL) pt,
         COUNTIF(coord_basis = 'published') pub,
         COUNTIF(coord_basis = 'parcel_interior_point') der,
         COUNTIF(prop_address IS NULL AND map_lat IS NULL) neither
  FROM `{OUT}`"""))[0]
ratio = f.n / f.d if f.d else 0
print(f"  fan-out {f.n:,} / {f.d:,} = {ratio:.4f}")
assert abs(ratio - 1.0) < 1e-9, f"FAN-OUT {ratio} - the address join duplicated parcels"
print(f"  {f.n:,} parcels")
print(f"    with an address        {f.adr:,}  ({100 * f.adr / f.n:.1f}%)")
print(f"    with a display point   {f.pt:,}  ({100 * f.pt / f.n:.1f}%)")
print(f"      published            {f.pub:,}")
print(f"      derived from polygon {f.der:,}")
print(f"    with NEITHER           {f.neither:,}")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_parcel_location',
 'indiana_app.in_sites x energy.parcels_in (dlgf_prop_address, dlgf_prop_address_city, '
 'dlgf_prop_address_zip, prop_add, dlgf_prop_class_code)',
 'One row per Indiana parcel carrying the DLGF property address and a DISPLAY coordinate. '
 'Exists as a BUILD rather than inside export_sites_exact.py because an export may not read '
 'energy.* - the checkpoint enforces that, and it caught this. Joined on state_parcel_id (NOT '
 'parcel_id, which is the county dashed form and matches ~1%); the source is de-duplicated '
 'because 38,840 state_parcel_id values repeat, and fan-out is asserted at exactly 1.0. '
 'map_lat/map_lon are the published point where one exists and an ST_CENTROID of the parcel '
 'polygon where it does not, with coord_basis recording which. '
 'RE-SCRAPE COMMAND: python scripts/build_parcel_location.py',
 {f.n}, {gb}, CURRENT_TIMESTAMP(),
 'G125. ⭐ THE ADDRESS IS STATEWIDE, correcting three documents that recorded it as Marion-only: '
 '{f.adr} of {f.n} parcels carry one across all 92 counties. The Marion-only belief came from '
 'in_si_address_parcel_bridge, which is the address SEARCH crosswalk and a different corpus. '
 '⛔ map_lat/map_lon are DISPLAY ONLY - no distance in this estate is measured from them. '
 'IDEMPOTENCY: replace_safe. CADENCE: with the parcel refresh.'
)""").result()
print("  _registry row written")
print("PARCEL LOCATION COMPLETE")
