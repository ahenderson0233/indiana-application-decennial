"""Target 1 pulls: Indianapolis/Marion County seller-intent layers -> indiana_app.
Each table registered in the same run. Code enforcement (MapServer/1) deliberately
NOT pulled: already held twice in warehouse (si_d12_indy_marion_code_enforcement,
agis_indy_code_enforcement; registry says DUPLICATE-OF-HELD)."""
import sys
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import arcgis_pull_all, load_to_bq

PULLS = [
    dict(
        table="in_si_indy_taxsale_parcels",
        url="https://gis.indy.gov/server/rest/services/TaxSaleViewer/TaxSaleParcels_BuildingBlocks/MapServer/0",
        subject="D1_tax_sale (Marion County archive w/ per-sale status)",
        notes=("Marion County tax-sale parcel records, TaxSaleViewer app layer. TAXYEAR spans "
               "2009->2024; STATUSNAME (Satisfied/Deed Issued/...); STATUSDATE epoch-ms is the "
               "observed status event date; SALEID+RECORDTYPE identify the sale. PARCELNUMBER is "
               "the LOCAL Marion parcel id (7-digit), not the 18-digit state id. Distinct "
               "provenance from si_d1_sri_taxsale_listings (SRI actives): this is the county's "
               "own archive with outcomes. Geometry not stored (parcel-keyed)."),
    ),
    dict(
        table="in_si_indy_surplus_parcels",
        url="https://gis.indy.gov/server/rest/services/SurplusProperties/SurplusPropertiesFeatures2/MapServer/7",
        subject="surplus_auction (county-owned parcels offered at commissioners auction)",
        notes=("SurplusProperties.dbo.SurplusParcels table. AuctionID embeds the auction date "
               "(e.g. '08162018 Commissioners'); SaleDate/SaleStatus/MinimumBid/VacantImpr "
               "present on subset. Observed event date = auction date in AuctionID or SaleDate. "
               "Government-owned surplus inventory, A1-adjacent (actively marketed by county)."),
    ),
    dict(
        table="in_si_indy_abandoned_vacant",
        url="https://gis.indy.gov/server/rest/services/OpenData/OpenData_Infrastructure/MapServer/2",
        subject="D5_vacancy (city abandoned+vacant property registry)",
        notes=("Indy 'Abandoned and Vacant Houses' registry, parcel-keyed, STATUS in "
               "{Abandoned, Vacant}. NO event-date field exists on the layer - registry "
               "membership as of _pulled_at only (snapshot semantics). Identical copies exist at "
               "MapIndy/MapIndyProperty/MapServer/11 and /16 (same 7,120 count, same rows) - "
               "pulled ONCE from the OpenData copy; do not also wire the MapIndy copies."),
    ),
]

for p in PULLS:
    print("=" * 80)
    print("PULLING", p["table"], "<-", p["url"])
    rows, publisher_count = arcgis_pull_all(p["url"], want_geometry=False)
    print(f"  pulled {len(rows)} rows (publisher count {publisher_count})")
    # drop ArcGIS shape-derived noise columns
    for r in rows:
        for k in list(r):
            if k.upper().startswith("SHAPE"):
                r.pop(k, None)
    load_to_bq(
        p["table"], rows,
        source=p["url"],
        method="arcgis_rest_paged outFields=* (lane_c)",
        notes=f"{p['subject']} | publisher_count={publisher_count} | {p['notes']}",
    )
print("DONE")
