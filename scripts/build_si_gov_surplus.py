"""G97 - federal surplus property as a SELLER-INTENT SIGNAL, and the label defect it exposed.

    python scripts/build_si_gov_surplus.py

Operator: *"Use federal surplus property as a SI signal - this will move where it is currently
being displayed throughout the application."*

⛔ THE FIRST FINDING IS A CORRECTNESS DEFECT ON A SHIPPED SURFACE, NOT A WIRING JOB.
The map console draws `in_gov_surplus_frpp` under a checkbox labelled **"Federal surplus
property"** with 1,594 Indiana points. Measured, `asset_status` says:

    Current Mission Need          1,540      <- NOT surplus. 96.6% of the layer.
    Disposed                         26      <- already sold; a comparable, not a lead
    Future Mission Need              11      <- NOT surplus
    Report of Excess Submitted        9      <- surplus. THIS is the signal.
    Determination to Dispose          8      <- surplus. THIS is the signal.

So the layer's NAME asserts something true of 17 of its 1,594 points. A reader turning on
"Federal surplus property" and seeing a dense scatter across Indiana would reasonably conclude
the federal government is disposing of hundreds of sites. It is not. That is the same shape as
the CLOUDSCENE_GAP mistake - a name match standing in for a data match.

⭐ WHY THE REAL SIGNAL IS WORTH HAVING EVEN THOUGH IT IS TINY. Every other signal in D1-D27
infers willingness to sell from DISTRESS - unpaid taxes, a foreclosure, a condemnation order.
A Report of Excess is an owner *publicly stating in a federal filing* that it does not want the
property. There is no inference at all. 17 leads with no inference beats 17,000 with one.

⚠ AND A SECOND STATE WORTH KEEPING SEPARATE: `utilization` flags 2 Underutilized and 2
Unutilized independently of asset_status, one of them for **26 consecutive years**. An asset
nobody has used since 1999 that is still booked as Current Mission Need is a lead of a different
kind - not declared, but visible.

⛔ WHAT THIS DOES NOT DO. It does not promise acres: `acres` is populated on 78 of 1,594 rows
(4.9%) and is NULL on every single declared-excess row. A surface must not print an acreage it
does not have, and must not print 0.

⚠ DUPLICATE POINTS ARE REAL AND NOT AN ERROR. Six Edinburgh rows share one coordinate because
FRPP reports PER ASSET - a building, a structure and a storage yard on one installation are
three rows. `assets_at_point` counts them so a popup can say "6 federal assets here" instead of
drawing six identical dots and implying six sites.

WRITES `indiana_app.in_si_gov_surplus_v2` and `indiana_app.in_si_gov_surplus_parcel`.
Reads indiana_app only.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_si_gov_surplus_v2"
OUTP = f"{DS}.in_si_gov_surplus_parcel"
D85 = "080500000047000018"          # the inverted whole-Earth parcel
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{OUT}` AS
WITH r AS (
  SELECT
    real_property_unique_identifier AS asset_id,
    COALESCE(using_agency, reporting_agency)   AS agency,
    reporting_bureau                            AS bureau,
    installation_name, real_property_type, real_property_use,
    asset_status, utilization,
    city_name, county_name, street_address, zip_code,
    SAFE_CAST(latitude  AS FLOAT64) AS lat,
    SAFE_CAST(longitude AS FLOAT64) AS lon,
    SAFE_CAST(acres AS FLOAT64)     AS acres,
    SAFE_CAST(consecutive_years_underutilized AS INT64) AS years_underutilized,
    SAFE.PARSE_DATE('%m/%d/%Y', excess_date)                    AS excess_date,
    SAFE.PARSE_DATE('%m/%d/%Y', determination_to_dispose_date)  AS dispose_date,
    SAFE.PARSE_DATE('%m/%d/%Y', disposition_date)               AS disposition_date,
    disposition_method
  FROM `{DS}.in_gov_surplus_frpp`
),
classed AS (
  SELECT *,
    CASE
      WHEN asset_status IN ('Report of Excess Submitted', 'Determination to Dispose')
        THEN 'declared_excess'
      WHEN asset_status = 'Disposed' THEN 'disposed'
      WHEN utilization = 'Unutilized'   THEN 'unutilized_not_declared'
      WHEN utilization = 'Underutilized' THEN 'underutilized_not_declared'
      ELSE 'in_use'
    END AS surplus_class
  FROM r
)
SELECT c.*,
  -- FRPP reports PER ASSET, so an installation with a building, a shed and a yard is 3 rows at
  -- one coordinate. Count them rather than drawing three dots that look like three sites.
  -- ⚠ PARTITION BY a FLOAT64 is rejected by BigQuery outright; the key must be a string.
  COUNT(*) OVER (PARTITION BY FORMAT('%.5f|%.5f', lat, lon)) AS assets_at_point,
  surplus_class IN ('declared_excess', 'unutilized_not_declared',
                    'underutilized_not_declared') AS is_si_signal,
  CURRENT_TIMESTAMP() AS built_at
FROM classed c
"""

print("building in_si_gov_surplus_v2 ...")
job = client.query(SQL)
job.result()
gb = round((job.total_bytes_processed or 0) / 1e9, 3)

print("\n  the classification, which is the whole point of this build:")
for r in client.query(f"""SELECT surplus_class, COUNT(*) n,
                                 COUNT(DISTINCT FORMAT('%.5f|%.5f', lat, lon)) points,
                                 COUNTIF(acres IS NOT NULL) with_acres
                          FROM `{OUT}` GROUP BY 1 ORDER BY n DESC"""):
    print(f"    {r.surplus_class:28s} {r.n:>5} rows  {r.points:>4} distinct points  "
          f"{r.with_acres:>3} with acreage")

sig = list(client.query(f"SELECT COUNTIF(is_si_signal) n, COUNT(*) tot FROM `{OUT}`"))[0]
print(f"\n  => {sig.n} of {sig.tot} rows are a genuine seller-intent signal "
      f"({100.0 * sig.n / sig.tot:.1f}%). The layer is labelled as if all {sig.tot} were.")

# ---- place the signal on parcels. D85 excluded; fan-out measured, not assumed. ----
SQLP = f"""
CREATE OR REPLACE TABLE `{OUTP}` AS
WITH sig AS (
  SELECT * FROM `{OUT}` WHERE is_si_signal AND lat IS NOT NULL AND lon IS NOT NULL
)
SELECT s.asset_id, s.agency, s.surplus_class, s.real_property_use, s.city_name,
       s.county_name AS frpp_county, s.excess_date, s.dispose_date, s.years_underutilized,
       s.assets_at_point, s.lat, s.lon,
       -- ⚠ in_sites carries no county_fips; the county comes from FRPP's own column above.
       p.parcel_source, p.parcel_key, p.occ_group, p.parcel_acres, p.structure_count,
       CURRENT_TIMESTAMP() AS built_at
FROM sig s
LEFT JOIN `{DS}.in_sites` p
  ON p.parcel_key != '{D85}'                                   -- ⚠ D85: whole-Earth polygon
 AND ST_CONTAINS(p.parcel_geog, ST_GEOGPOINT(s.lon, s.lat))
"""
print("\nplacing the signal on parcels ...")
job2 = client.query(SQLP)
job2.result()
gb2 = round((job2.total_bytes_processed or 0) / 1e9, 3)

pl = list(client.query(f"""
  SELECT COUNT(*) rows_, COUNT(DISTINCT asset_id) assets,
         COUNTIF(parcel_key IS NOT NULL) placed,
         COUNT(DISTINCT parcel_key) parcels
  FROM `{OUTP}`"""))[0]
src = list(client.query(f"SELECT COUNTIF(is_si_signal) n FROM `{OUT}`"))[0].n
fan = pl.rows_ / max(src, 1)
print(f"  {pl.rows_} rows from {src} signal assets  (fan-out {fan:.2f})")
print(f"  placed on a parcel: {pl.placed} rows, {pl.parcels} distinct parcels")
# ⚠ trap 7: a LEFT JOIN against a polygon table fans out if D85 slips in. ~1.0 is the proof.
assert fan < 1.6, f"FAN-OUT {fan:.2f} - a whole-Earth polygon is probably in the join"

print("\n  the leads, one line each:")
for r in client.query(f"""SELECT surplus_class, agency, city_name, frpp_county, real_property_use,
                                 excess_date, years_underutilized, parcel_key, parcel_acres
                          FROM `{OUTP}`
                          ORDER BY surplus_class, city_name LIMIT 30"""):
    where = f"{r.city_name or '?'}, {r.frpp_county or '?'}"
    pk = r.parcel_key or "no parcel at this point"
    ac = f"{r.parcel_acres:.1f} ac" if r.parcel_acres else "acreage not held"
    yr = f" [{r.years_underutilized}y unused]" if r.years_underutilized else ""
    print(f"    {r.surplus_class:28s} {where:26s} {str(r.real_property_use)[:22]:22s}"
          f"{yr:16s} {pk[:22]:22s} {ac}")

for tbl, n, g, note in [
    (OUT.split(".")[-1], sig.tot, gb,
     'G97. Classifies every Indiana FRPP row by whether the federal government has actually '
     'DECLARED it surplus. 1,540 of 1,594 are Current Mission Need, so the map checkbox reading '
     '"Federal surplus property" was true of 17 points, not 1,594. acres is held on 78 rows '
     '(4.9%) and on ZERO declared-excess rows, so no acreage may be printed for a lead. '
     'assets_at_point exists because FRPP reports per ASSET, not per site.'),
    (OUTP.split(".")[-1], pl.rows_, gb2,
     'G97. Places the declared/unutilized subset on parcels by ST_CONTAINS. D85 excluded and '
     'fan-out measured at build time (assert < 1.6). A LEFT JOIN so an asset with no parcel '
     'under it stays visible as an unplaced lead rather than disappearing.')]:
    client.query(f"""
    INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
    VALUES (
     '{tbl}',
     'indiana_app.in_gov_surplus_frpp (GSA Federal Real Property Profile) + indiana_app.in_sites',
     'asset_status and utilization read as the publisher writes them: declared_excess = Report '
     'of Excess Submitted or Determination to Dispose; unutilized/underutilized_not_declared '
     'come from the utilization column independently. Dates are m/d/Y strings parsed with '
     'SAFE.PARSE_DATE. '
     'RE-SCRAPE COMMAND: python scripts/build_si_gov_surplus.py',
     {n}, {g}, CURRENT_TIMESTAMP(), '{note}'
    )""").result()
print("\n  2 _registry rows written")
print("GOV SURPLUS SIGNAL COMPLETE")
