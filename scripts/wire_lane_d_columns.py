"""Item 10 — the eleven already-pulled, never-wired Lane D columns.

Lane D pulled ALL columns from six sources and turned up signal-bearing fields nobody had asked
for. They need no scraping, no new source and no permission question: the data has been sitting
in BigQuery. Two of them are not enrichment at all — they are PLACEMENT, which is the scarcest
thing in this application:

  in_si_refresh_sri_taxsale_in.latitude/longitude   29,955 of 83,547 rows carry the publisher's
                                                    OWN coordinates. No geocoder, no estimate.
  in_si_refresh_ibtr_appeals.stateParcelNumber      a direct parcel key on 10,152 appeals, where
                                                    D26 currently arrives via an 'IN:' strip of
                                                    the corpus copy

The other nine are enrichment that changes what a reader can judge:
  saleTypeDescription   Foreclosure 62,760 · Tax Sale 15,860 · Certificate Sale 4,851 · Deed 76.
                        A tax sale and a foreclosure are different claims about an owner.
  CASE_TYPE             the full Indy violation taxonomy (already used to derive Unsafe Buildings
                        and Vacant Board Order)
  LINK                  910,483 of 910,483 Accela case URLs — a free verification drilldown on
                        every single row, so a reader can check us
  TOWNSHIP              free sub-county geography (13 values; watch the doubled 'CENTER,CENTER')
  NAICS                 on all 1,220 WARN notices — lets WARN be filtered to industries that
                        actually own real estate rather than lease it
  col_8__href           172 links to the WARN letter PDF, which names the SITE, not the HQ
  appealTypeName        Form 131 7,282 · 133 1,871 · 132 977 · 139 22
  attachmentDescriptions  document breadcrumb finer than statusName
  Program / Landfill / AML  BROWNFIELDS 1,247 · RCRA 127 · LANDFILL METHANE 54 · SUPERFUND 53

D85 GUARD on the spatial join. NO CENTROIDS: SRI's coordinates are the publisher's own point.
"""
# stdout must survive its own output: this console is cp1252 and characters like U+2248/U+2192/U+2717 raise
# UnicodeEncodeError from print() itself. The honesty audit once crashed on its own
# FAILURE path for exactly this reason. Degrade the glyph, never the run.
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import datetime
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
D85 = "080500000047000018"
client = bigquery.Client(project="energy-platfrom")
BUILT = datetime.datetime.now(datetime.timezone.utc).isoformat()


def q1(sql): return list(client.query(sql))[0]


def run(sql, label):
    job = client.query(sql); job.result()
    print(f"  {label}: {job.total_bytes_processed/1e9:.2f} GB", flush=True)


# --- 1. SRI tax sale placed by the publisher's own coordinates ---------------------------------
print("building in_si_sri_placed …", flush=True)
run(f"""
CREATE OR REPLACE TABLE `{DS}.in_si_sri_placed` AS
SELECT s.parcel_key, s.occ_group,
  -- THREE signals, not two. saleTypeDescription alone splits Foreclosure from Tax Sale, but it
  -- cannot see the difference between a sale that HAS HAPPENED and a parcel merely CERTIFIED
  -- delinquent and advertised. That difference is D1 vs D4, and it lives in a second column,
  -- saleStatusDescription, whose 'DELINQUENT' value is the pre-sale state:
  --
  --   DELINQUENT        15,860  saleType 'Tax Sale'    <- D4: certified, sale NOT yet held
  --   Sold To Plaintiff 26,860  saleType 'Foreclosure'
  --   Cancelled         25,829  saleType 'Foreclosure'
  --   Sold To 3rd Party  8,314  saleType 'Foreclosure'
  --   COUNTY             4,927  Certificate/Deed Sale
  --   Sale Active        1,757  saleType 'Foreclosure'  <- a foreclosure IN PROGRESS, so D2
  --
  -- SI_COVERAGE recorded D4 as "NOT HELD -- seasonal, schedule Jul-Oct" for a whole session and
  -- a fresh SRI acquisition was queued, while these rows sat in the warehouse. Read the value
  -- vocabulary of a status column before trusting any count taken over it.
  --
  -- Only DELINQUENT becomes D4. 'Sale Active' is an active FORECLOSURE, not a tax delinquency,
  -- and folding it in would overstate D4 by 1,757 and understate D2 by the same.
  CASE WHEN t.saleStatusDescription = 'DELINQUENT'    THEN 'D4_tax_delinquency'
       WHEN t.saleTypeDescription   = 'Foreclosure'   THEN 'D2_foreclosure'
       ELSE 'D1_tax_sale' END                              AS signal,
  t.saleTypeDescription sale_type, t.saleStatusDescription sale_status,
  t.auctionStyle auction_style, t.county, t.city,
  -- SRI publishes MM/DD/YYYY, not ISO. An ISO-only parse returned 0 dated of 31,228 — a
  -- placement with no date is close to useless when recency is the filter. Note these are
  -- largely FUTURE dates: scheduled auctions, which is a real event date, not an error.
  SAFE.PARSE_DATE('%m/%d/%Y', NULLIF(TRIM(t.auctionDate), '')) AS auction_date,
  t.ownerName1 owner_name, t.briefLegal brief_legal,
  SAFE_CAST(t.latitude AS FLOAT64) lat, SAFE_CAST(t.longitude AS FLOAT64) lon,
  TIMESTAMP('{BUILT}') AS built_at
FROM `{DS}.in_si_refresh_sri_taxsale_in` t
JOIN `{DS}.in_sites` s
  ON ST_CONTAINS(s.parcel_geog,
                 ST_GEOGPOINT(SAFE_CAST(t.longitude AS FLOAT64), SAFE_CAST(t.latitude AS FLOAT64)))
WHERE SAFE_CAST(t.latitude AS FLOAT64) IS NOT NULL
  AND SAFE_CAST(t.longitude AS FLOAT64) IS NOT NULL
  AND s.parcel_key != '{D85}'
""", "in_si_sri_placed")

r = q1(f"""SELECT COUNT(*) n, COUNT(DISTINCT parcel_key) parcels,
  COUNTIF(occ_group != 'residential') nonres_rows,
  COUNT(DISTINCT IF(occ_group != 'residential', parcel_key, NULL)) nonres_parcels,
  COUNTIF(auction_date IS NOT NULL) dated
FROM `{DS}.in_si_sri_placed`""")
src = q1(f"""SELECT COUNTIF(SAFE_CAST(latitude AS FLOAT64) IS NOT NULL) n
             FROM `{DS}.in_si_refresh_sri_taxsale_in`""")
print(f"  {r.n:,} rows on {r.parcels:,} parcels from {src.n:,} located SRI rows "
      f"({100*r.n/max(src.n,1):.1f}%) · non-residential parcels {r.nonres_parcels:,} · "
      f"dated {r.dated:,}")
print(f"  fan-out {r.n/max(src.n,1):.3f} rows per located sale "
      f"(≈2.0 would mean D85 is still in the join)")

# --- 2. IBTR appeals placed by their OWN state parcel number ------------------------------------
print("\nbuilding in_si_ibtr_placed …", flush=True)
run(f"""
CREATE OR REPLACE TABLE `{DS}.in_si_ibtr_placed` AS
SELECT s.parcel_key, s.occ_group, 'D26_assessment_appeal' AS signal,
  a.appealTypeName appeal_type, a.statusName status_name,
  a.attachmentDescriptions attachment_descriptions,
  a.townshipName township, a.countyName county, a.petitionerName petitioner,
  COALESCE(SAFE.PARSE_DATE('%Y-%m-%d', SUBSTR(a.dateReceived, 1, 10)),
           SAFE.PARSE_DATE('%m/%d/%Y', NULLIF(TRIM(a.dateReceived), ''))) AS date_received,
  a.assessmentYear assessment_year,
  TIMESTAMP('{BUILT}') AS built_at
FROM `{DS}.in_si_refresh_ibtr_appeals` a
JOIN `{DS}.in_sites` s
  ON s.parcel_key = REGEXP_REPLACE(a.stateParcelNumber, r'[^0-9]', '')
WHERE a.stateParcelNumber IS NOT NULL
  AND LENGTH(REGEXP_REPLACE(a.stateParcelNumber, r'[^0-9]','')) = 18
  AND s.parcel_key != '{D85}'
""", "in_si_ibtr_placed")

i = q1(f"""SELECT COUNT(*) n, COUNT(DISTINCT parcel_key) parcels,
  COUNT(DISTINCT IF(occ_group != 'residential', parcel_key, NULL)) nonres_parcels,
  COUNTIF(date_received IS NOT NULL) dated FROM `{DS}.in_si_ibtr_placed`""")
tot = q1(f"SELECT COUNT(*) n FROM `{DS}.in_si_refresh_ibtr_appeals`").n
print(f"  {i.n:,} of {tot:,} appeals placed on {i.parcels:,} parcels "
      f"· non-residential {i.nonres_parcels:,} · dated {i.dated:,}")
print(f"  (the corpus route via an 'IN:' strip reaches 2,985 parcels — this is the same signal "
      f"through the publisher's own key)")

# --- 3. the enrichment columns, as one readable table ------------------------------------------
print("\nbuilding in_si_lane_d_enrichment …", flush=True)
run(f"""
CREATE OR REPLACE TABLE `{DS}.in_si_lane_d_enrichment` AS
SELECT 'sri_taxsale' src, 'saleTypeDescription' col, saleTypeDescription val, COUNT(*) n,
       COUNTIF(SAFE_CAST(latitude AS FLOAT64) IS NOT NULL) n_located
FROM `{DS}.in_si_refresh_sri_taxsale_in` GROUP BY 1,2,3
UNION ALL
SELECT 'indy_code', 'CASE_TYPE', CASE_TYPE, COUNT(*), 0
FROM `{DS}.in_si_refresh_indy_code_enforcement` GROUP BY 1,2,3
UNION ALL
SELECT 'indy_code', 'TOWNSHIP', TOWNSHIP, COUNT(*),
       COUNTIF(LINK IS NOT NULL AND LINK != '')
FROM `{DS}.in_si_refresh_indy_code_enforcement` GROUP BY 1,2,3
UNION ALL
SELECT 'warn', 'NAICS', NAICS, COUNT(*),
       COUNTIF(col_8__href IS NOT NULL AND col_8__href != '')
FROM `{DS}.in_si_refresh_warn_notices` GROUP BY 1,2,3
UNION ALL
SELECT 'ibtr', 'appealTypeName', appealTypeName, COUNT(*), 0
FROM `{DS}.in_si_refresh_ibtr_appeals` GROUP BY 1,2,3
UNION ALL
SELECT 'brownfield', 'Program', Program, COUNT(*),
       COUNTIF(Landfill IS NOT NULL AND Landfill NOT IN ('','0','None'))
FROM `{DS}.in_si_refresh_brownfield_epa_in` GROUP BY 1,2,3
""", "in_si_lane_d_enrichment")
e = q1(f"""SELECT COUNT(*) n, COUNT(DISTINCT CONCAT(src,'.',col)) cols
           FROM `{DS}.in_si_lane_d_enrichment`""")
print(f"  {e.n:,} vocabulary rows across {e.cols} columns")

# --- 4. register --------------------------------------------------------------------------------
for name, n, srcs, method in [
 ("in_si_sri_placed", int(r.n), f"{DS}.in_si_refresh_sri_taxsale_in + in_sites",
  "SRI tax-sale and foreclosure rows placed by the PUBLISHER'S OWN latitude/longitude "
  "(29,955 of 83,547 carry them) via ST_CONTAINS — no geocoder, no estimate, no centroid. "
  "saleTypeDescription splits Foreclosure into D2 and Tax/Certificate/Deed Sale into D1, "
  "because a tax sale and a foreclosure are different claims about an owner. D85 excluded."),
 ("in_si_ibtr_placed", int(i.n), f"{DS}.in_si_refresh_ibtr_appeals + in_sites",
  "IBTR assessment appeals placed by their own stateParcelNumber rather than through the "
  "corpus copy's 'IN:'-prefixed key. Carries appealTypeName (Form 131/133/132/139) and "
  "attachmentDescriptions, neither of which had ever been surfaced. D85 excluded."),
 ("in_si_lane_d_enrichment", int(e.n), "six in_si_refresh_* tables",
  "measured value vocabularies for the Lane D columns that were pulled and never wired: "
  "saleTypeDescription, CASE_TYPE, TOWNSHIP+LINK, NAICS+PDF link, appealTypeName, "
  "Program+Landfill. No scraping — this was already in BigQuery."),
]:
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{name}'").result()
    client.query(
        f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at) "
        f"VALUES (@t,@s,@m,@n,CURRENT_TIMESTAMP())",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", name),
            bigquery.ScalarQueryParameter("s", "STRING", srcs),
            bigquery.ScalarQueryParameter("m", "STRING", method),
            bigquery.ScalarQueryParameter("n", "INT64", n)])).result()
    print(f"registered {name} ({n:,})")
print("\nDONE")
