"""G150: PUT THE RECOVERED WARN FACILITY ADDRESSES ONTO PARCELS.

`extract_warn_addresses.py` recovered 68 facility addresses across 55 firms from the filing PDFs.
This is the step that turns them into a parcel key, which is what `in_si_signal_coverage` counts
when it reports D19_warn reaching 2 parcels.

⛔ THE MATCH IS ON A NORMALISED STREET ADDRESS WITHIN THE RIGHT CITY, and both halves matter.
`energy.parcels_in` carries the DLGF property address on 98.4% of Indiana parcels (G125), so the
corpus exists. Matching on street alone would attach "1600 23rd Street" to a 23rd Street in any of
92 counties; requiring the city as well is what makes the join a claim rather than a guess.

⚠ ONLY `verdict = 'facility'` IS PLACED. The 97 refused and 97 unclassified addresses stay in the
table and reach no parcel - a town hall or an HR office pinned as a distressed industrial site
would be worse than the gap it fills.

⚠ AND A BAD ZIP DOES NOT BLOCK A MATCH. One filing writes a Kentucky zip on an Indiana city
(Thermal Structures, "Plainfield 42816"); the zip is flagged and the street+city still match,
because the zip is the part the filer got wrong.

RE-SCRAPE COMMAND: python scripts/build_warn_placement.py
⚠ IDEMPOTENT: replace_safe. Depends on in_si_warn_addresses.
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
OUT = f"{DS}.in_si_warn_placed"
D85 = "080500000047000018"
client = bigquery.Client(project="energy-platfrom")


# ================================================================================================
# ⛔ THE FIRST NORMALISER FOLDED THREE SUFFIXES AND NO DIRECTIONALS, AND IT COST MOST OF THE JOIN.
# 68 facility addresses produced 21 parcels. Diagnosing all 44 misses one by one against the
# corpus - rather than assuming they were absent - showed almost every one was a WORD-FORM
# mismatch on an address the corpus plainly holds:
#     filing "2320 Industrial Parkway"     corpus "2320 INDUSTRIAL PKWY"      PARKWAY not folded
#     filing "12301 Bluffton Road"         corpus "12301 BLUFFTON RD"         ROAD not folded
#     filing "180 Bartram Parkway"         corpus "180 BARTRAM PKWY"
#     filing "2572 East Kercher Road"      corpus "2572 KERCHER RD"           directional extra
#     filing "500 Water St"                corpus "500 W WATER ST"            directional missing
# ⚠ THE LAST TWO POINT OPPOSITE WAYS, which is why a single canonical form is not enough and the
# match is run TWICE - once with directionals, once with them removed from both sides.
# ================================================================================================
# ⭐ 2026-08-22b: THE NORMALISER IS NOW ONE MODULE, NOT N COPIES. This file and its sibling
# placement builder each carried their own SUFFIXES/DIRECTIONALS/naddr/ncity, guarded by an
# assertion in audit_si_upstream_width.py that the copies still matched. A third caller (G156's
# NFIRS and SBA placement) would have made it three. ⛔ A guard on a duplicate is not a fix for a
# duplicate - §2.15c, the defect this project has hit eight times. One definition, imported.
import os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from si_address_norm import DIRECTIONALS, SUFFIXES, naddr, ncity  # noqa: F401,E402



SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH w AS (
  SELECT company, notice_class, vacates_site, affected_workers, event_date,
         facility_street, facility_city, facility_zip, zip_outside_indiana, notice_pdf_url,
         {naddr('facility_street')} AS nstreet,
         {naddr('facility_street', drop_dir=True)} AS nstreet_nd,
         {ncity('facility_city')} AS ncity
  FROM `{DS}.in_si_warn_addresses`
  WHERE verdict = 'facility' AND facility_street IS NOT NULL AND facility_city IS NOT NULL
),
p AS (
  SELECT state_parcel_id AS parcel_key,
         {naddr('dlgf_prop_address')} AS nstreet,
         {naddr('dlgf_prop_address', drop_dir=True)} AS nstreet_nd,
         {ncity('dlgf_prop_address_city')} AS ncity
  FROM `{EN}.parcels_in`
  WHERE state_parcel_id IS NOT NULL AND state_parcel_id != '{D85}'
    AND dlgf_prop_address IS NOT NULL AND dlgf_prop_address != ''
    AND dlgf_prop_address_city IS NOT NULL
),
-- ⚠ one row per (street, city): the same address sits on several parcel records, and joining raw
-- would fan the notice out across all of them. A shared address is ambiguous, so it is COUNTED and
-- the ambiguity travels with the row instead of being resolved arbitrarily.
pd AS (
  SELECT nstreet, ncity, COUNT(DISTINCT parcel_key) AS n_parcels,
         ANY_VALUE(parcel_key) AS parcel_key
  FROM p GROUP BY 1, 2
),
pnd AS (
  SELECT nstreet_nd, ncity, COUNT(DISTINCT parcel_key) AS n_parcels,
         ANY_VALUE(parcel_key) AS parcel_key
  FROM p GROUP BY 1, 2
),
-- ⭐ PASS 1: the full normalised form, directionals intact. Highest confidence.
m1 AS (
  SELECT w.*, pd.parcel_key, pd.n_parcels, 'exact_normalised' AS match_method
  FROM w JOIN pd ON pd.nstreet = w.nstreet AND pd.ncity = w.ncity
),
-- ⭐ PASS 2: directionals dropped from BOTH sides, for the rows pass 1 could not reach.
-- ⚠ Strictly weaker: "500 W Water St" and "500 E Water St" collapse together, so a pass-2 match
-- is only accepted when the result is UNAMBIGUOUS - exactly one parcel at that address.
m2 AS (
  SELECT w.*, pnd.parcel_key, pnd.n_parcels, 'directional_dropped' AS match_method
  FROM w JOIN pnd ON pnd.nstreet_nd = w.nstreet_nd AND pnd.ncity = w.ncity
  WHERE NOT EXISTS (SELECT 1 FROM m1 WHERE m1.company = w.company
                      AND m1.facility_street = w.facility_street)
    AND pnd.n_parcels = 1
)
SELECT
  'parcels_in' AS parcel_source,
  parcel_key,
  company, notice_class, vacates_site, affected_workers, event_date,
  facility_street, facility_city, facility_zip, zip_outside_indiana, notice_pdf_url,
  n_parcels AS parcels_sharing_this_address,
  match_method,
  -- ⭐ the honest confidence: one parcel at that address is a match, several is a building we
  -- cannot resolve to a lot, and the reader is told which.
  IF(n_parcels = 1, 'exact_address', 'address_shared_by_several_parcels') AS match_grain,
  CURRENT_TIMESTAMP() AS built_at
FROM (SELECT * FROM m1 UNION ALL SELECT * FROM m2)
"""

print("G150 - PLACING THE RECOVERED WARN ADDRESSES ON PARCELS")
job = client.query(SQL)
job.result()
print(f"  built, {round((job.total_bytes_processed or 0) / 1e9, 2)} GB scanned")

s = list(client.query(f"""
  SELECT COUNT(*) n, COUNT(DISTINCT parcel_key) parcels, COUNT(DISTINCT company) firms,
         COUNTIF(match_grain = 'exact_address') exact, COUNTIF(vacates_site) vac
  FROM `{OUT}`"""))[0]
tot = list(client.query(f"""
  SELECT COUNTIF(verdict = 'facility') fac FROM `{DS}.in_si_warn_addresses`"""))[0].fac
print(f"  ⭐ {s.parcels} PARCELS reached, from {s.n} matches across {s.firms} firms")
print(f"  ⭐ {s.exact} matched an address held by exactly one parcel")
print(f"  ⭐ {s.vac} of the matches are notices that VACATE the site")
print(f"  ⚠ {tot - s.n} of the {tot} facility addresses found no parcel at that street and city")

before = list(client.query(f"""
  SELECT parcels_reached FROM `{DS}.in_si_signal_coverage` WHERE signal = 'D19_warn'"""))
if before:
    print(f"\n  ⛔ BEFORE THIS: in_si_signal_coverage reported D19_warn reaching "
          f"{before[0].parcels_reached} parcels — against 1,220 notices held.")
    print(f"  ⭐ AFTER: {s.parcels} parcels, and the ceiling is the 172 notices that carry a PDF "
          f"URL, not the 1,220 we hold. The other 1,048 are G151.")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_si_warn_placed',
 'indiana_app.in_si_warn_addresses (facility addresses parsed from the filing PDFs) x '
 'energy.parcels_in (DLGF property address, populated on 98.4% of Indiana parcels)',
 'Places a WARN facility on a parcel by matching a NORMALISED street address WITHIN THE SAME '
 'CITY - street alone would attach a 23rd Street to any of 92 counties. Suffix words are folded '
 'on both sides (STREET/ST., AVENUE/AVE., DRIVE/DR.) because the filer and the assessor write '
 'them differently. ⛔ ONLY verdict=facility rows are placed; the refused (agency, elected '
 'official, counsel, HR) and unclassified addresses reach no parcel. An address held by more than '
 'one parcel is marked address_shared_by_several_parcels rather than resolved arbitrarily. A zip '
 'outside Indiana does not block the match - it is a typo in the filing and is flagged. '
 'RE-SCRAPE COMMAND: python scripts/build_warn_placement.py',
 {s.n}, 0.0, CURRENT_TIMESTAMP(),
 'G150, operator 2026-08-21. in_si_signal_coverage reported D19_warn reaching 2 parcels against '
 '1,220 notices held, because in_si_warn_normalised carries no address column at all. '
 'IDEMPOTENCY: replace_safe. CADENCE: monthly, with the extractor.'
)""").result()
print("\n  _registry row written")
print("WARN PLACEMENT COMPLETE")
