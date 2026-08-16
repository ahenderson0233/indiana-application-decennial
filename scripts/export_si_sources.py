"""A3 — the SI source-visibility panel.

18 city/state SI sources feed `in_si_signals` upstream, but no screen showed them, so their
freshness work lived only in a findings file. This exports one row per source: what it holds,
the PUBLISHER'S observed date range (never our pull stamp presented as freshness), when we
pulled it, and which signal family it feeds.

The event-date column differs per table and was read from each schema, not guessed. Three
tables hold NO publisher date at all — those say so rather than borrowing `_pulled_at` and
calling it freshness, which would report our diligence as the data's currency.

Also settles a duplicate: in_si_refresh_warn_notices and in_si_state_warn_notices hold the same
1,220 notices with identical company/city/worker/date values. Measured, then waived.
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
import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

# (table, publisher event-date column or None, signal family, what one row IS)
SOURCES = [
 ("in_si_refresh_sri_taxsale_in", "auctionDate", "D1 tax sale", "a parcel listed in an SRI tax sale"),
 ("in_si_indy_taxsale_parcels", "STATUSDATE", "D1 tax sale", "a Marion County tax-sale parcel"),
 ("in_si_evansville_taxsale", None, "D1 tax sale", "a Vanderburgh tax-sale record"),
 ("in_si_evansville_taxsale_transfers", "transfer_date", "D1 tax sale", "a post-sale transfer"),
 ("in_si_refresh_indy_code_enforcement", "OPEN_DATE", "D12 code enforcement", "an Indianapolis code case"),
 ("in_si_southbend_code_enforcement", "Record_Open_Date", "D12 code enforcement", "a South Bend code case"),
 ("in_si_southbend_continuous_enforcement", "HEARING__OR_LETTER_DATE", "D12 code enforcement", "a continuous-enforcement action"),
 ("in_si_southbend_chronic_problem", "Designation_Date", "D12 code enforcement", "a chronic-problem property designation"),
 ("in_si_southbend_demolition_orders", "Bid_Opening_Date", "D21 demolition", "a demolition bid"),
 ("in_si_southbend_vacant_abandoned", "Original_Outcome_Date_before_Re", "D5 vacancy", "a vacant/abandoned determination"),
 ("in_si_indy_abandoned_vacant", None, "D5 vacancy", "an Indianapolis abandoned/vacant address"),
 ("in_si_evansville_foreclosures", "Current_Parcels_LastSaleDate", "D2 foreclosure", "a foreclosure-linked parcel"),
 ("in_si_refresh_ibtr_appeals", "dateReceived", "D26 assessment appeal", "a tax-board appeal"),
 ("in_si_state_warn_notices", "Notice_Date", "D15 WARN", "a WARN layoff/closure notice"),
 ("in_si_refresh_warn_notices", "Notice_Date", "D15 WARN", "a WARN notice (duplicate copy)"),
 ("in_si_indy_surplus_parcels", "SaleDate", "D23 public surplus", "a city-surplus parcel"),
 ("in_si_refresh_brownfield_epa_in", None, "brownfield", "an EPA brownfield site"),
 ("in_si_refresh_iocs_eviction", None, "county context", "a COURT, with case-type counts as columns"),
]

# Publisher dates arrive in four shapes here, and the fourth is the one that matters: SEVEN of
# these columns hold EPOCH MILLISECONDS as strings ('1656424281000' = 2022-06-28), the Esri/ArcGIS
# convention, because the sources are ArcGIS feature services. A first pass tried only string
# formats and reported those seven as "unparseable" — which would have shipped a freshness panel
# that silently knew nothing about the majority of our SI rows. Value-read the column, then parse.
def date_expr(col):
    c = f"CAST(`{col}` AS STRING)"
    epoch = (f"IF(REGEXP_CONTAINS({c}, r'^[0-9]{{12,13}}$'), "
             f"DATE(TIMESTAMP_MILLIS(SAFE_CAST({c} AS INT64))), NULL)")
    return (f"COALESCE({epoch}, SAFE.PARSE_DATE('%m/%d/%Y', {c}), "
            f"SAFE.PARSE_DATE('%Y-%m-%d', SUBSTR({c},1,10)), "
            f"SAFE.PARSE_DATE('%m/%d/%y', {c}), SAFE.PARSE_DATE('%d-%b-%Y', {c}))")

out = []
for tbl, datecol, family, unit in SOURCES:
    row = {"table": tbl, "family": family, "unit": unit, "date_column": datecol}
    n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.{tbl}`"))[0].n
    row["rows"] = n
    if datecol:
        try:
            r = list(client.query(f"""
              SELECT CAST(MIN({date_expr(datecol)}) AS STRING) lo,
                     CAST(MAX({date_expr(datecol)}) AS STRING) hi,
                     COUNTIF({date_expr(datecol)} IS NOT NULL) parsed
              FROM `{DS}.{tbl}`"""))[0]
            row.update({"first_event": r.lo, "last_event": r.hi, "dated_rows": r.parsed})
            row["date_status"] = ("ok" if r.parsed and r.parsed > n * 0.5
                                  else "partial" if r.parsed else "unparseable")
        except Exception as ex:
            row["date_status"] = "error"; row["note"] = str(ex)[:90]
    else:
        row["date_status"] = "no publisher date held"
    try:
        p = list(client.query(f"SELECT CAST(MAX(_pulled_at) AS STRING) p FROM `{DS}.{tbl}`"))[0].p
        row["pulled_at"] = (p or "")[:10]
    except Exception:
        row["pulled_at"] = None
    out.append(row)
    print(f"  {tbl:<44} {n:>8,}  {row['date_status']:<22} "
          f"{row.get('first_event','')} → {row.get('last_event','')}")

# The WARN duplicate, measured rather than asserted
warn = list(client.query(f"""
  SELECT (SELECT COUNT(*) FROM `{DS}.in_si_refresh_warn_notices`) a,
         (SELECT COUNT(*) FROM `{DS}.in_si_state_warn_notices`) b,
         (SELECT COUNT(*) FROM (
            SELECT CONCAT(IFNULL(Company,''),'|',IFNULL(City,''),'|',IFNULL(Notice_Date,'')) k
            FROM `{DS}.in_si_refresh_warn_notices`
            INTERSECT DISTINCT
            SELECT CONCAT(IFNULL(Company,''),'|',IFNULL(City,''),'|',IFNULL(Notice_Date,''))
            FROM `{DS}.in_si_state_warn_notices`)) shared"""))[0]
# A4: NFIRS structure fires, filtered to the building/structure incident range and to Indiana
# The SI funnel, per the operator's doctrine: a signal only counts when it would plausibly move
# an owner to sell. Raw incidents -> structure fires -> NON-RESIDENTIAL -> material loss.
nf = [dict(r) for r in client.query(f"""
  SELECT yr, COUNT(*) fires,
         COUNTIF(property_class='non-residential') non_res,
         COUNTIF(severity != 'no loss reported') with_loss,
         COUNTIF(property_class='non-residential' AND severity IN
                 ('moderate >=$10k','major >=$100k','catastrophic >=$500k')) si_grade,
         COUNTIF(address_quality='number + street') keyable
  FROM `{DS}.in_nfirs_structure_fires` GROUP BY 1 ORDER BY 1""")]
nf_sev = [dict(r) for r in client.query(f"""
  SELECT property_class, severity, COUNT(*) n FROM `{DS}.in_nfirs_structure_fires`
  GROUP BY 1,2 ORDER BY 1, n DESC""")]
# the SI-grade incidents themselves - non-residential, material loss, address-keyable
nf_top = [dict(r) for r in client.query(f"""
  SELECT CAST(incident_date AS STRING) d, street_address, city, property_use_code,
         severity, property_loss_usd, contents_loss_usd
  FROM `{DS}.in_nfirs_structure_fires`
  WHERE property_class='non-residential'
    AND severity IN ('moderate >=$10k','major >=$100k','catastrophic >=$500k')
  ORDER BY IFNULL(property_loss_usd,0) + IFNULL(contents_loss_usd,0) DESC LIMIT 40""")]

payload = {"sources": out, "warn_dup": {"refresh_rows": warn.a, "state_rows": warn.b,
                                        "shared_keys": warn.shared},
           "nfirs": {"by_year": nf, "severity": nf_sev, "si_grade": nf_top,
                     "raw_incidents": list(client.query(f"""
                        SELECT (SELECT COUNT(*) FROM `{DS}.in_nfirs_basicincident_2020` WHERE STATE='IN')
                             + (SELECT COUNT(*) FROM `{DS}.in_nfirs_basicincident_2021` WHERE STATE='IN') n"""))[0].n}}
p = os.path.join(REPO, "data", "si_sources.json.gz")
with gzip.open(p, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(payload, f, separators=(",", ":"), default=str)
print(f"\nsi_sources.json.gz {os.path.getsize(p)/1024:.0f} KB · {len(out)} sources")
print(f"WARN duplicate check: refresh {warn.a} · state {warn.b} · shared company|city|date keys {warn.shared}")
