"""Target 5c: Evansville/Vanderburgh (maps.evansvillegis.com, ArcGIS Server).
Multi-year layer stacks appended into one table per subject with src_layer columns.
Old-server-safe paging: returnIdsOnly then objectIds chunks."""
import sys
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import get, arcgis_count, load_to_bq

BASE = "https://maps.evansvillegis.com/arcgis_server/rest/services"


def pull_layer_ids(layer_url, where="1=1"):
    """Pull all rows via objectIds chunks (works on any ArcGIS Server version)."""
    meta = get(layer_url, params={"f": "json"})
    oid_field = meta.get("objectIdField") or next(
        (f["name"] for f in meta.get("fields", []) if f["type"] == "esriFieldTypeOID"), "OBJECTID")
    ids_resp = get(layer_url.rstrip("/") + "/query",
                   params={"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=180)
    ids = ids_resp.get("objectIds") or []
    rows = []
    CH = 250
    for i in range(0, len(ids), CH):
        chunk = ids[i:i + CH]
        j = get(layer_url.rstrip("/") + "/query",
                params={"objectIds": ",".join(map(str, chunk)), "outFields": "*",
                        "returnGeometry": "false", "f": "json"}, timeout=180)
        if "error" in j:
            raise RuntimeError(f"chunk error at {i}: {j['error']}")
        for f in j.get("features", []):
            rows.append(dict(f.get("attributes", {})))
    if len(rows) != len(ids):
        raise RuntimeError(f"PAGINATION ALARM {layer_url}: {len(rows)} rows vs {len(ids)} ids")
    return rows, meta


def pull_service_stack(svc_url, table, subject, notes, skip_layer_ids=()):
    """Append every vector layer of a service into one table, tagging src_layer_*."""
    smeta = get(svc_url, params={"f": "json"})
    all_rows = []
    layer_info = []
    for lyr in (smeta.get("layers") or []) + (smeta.get("tables") or []):
        lid, lname = lyr["id"], lyr.get("name", "")
        if lid in skip_layer_ids:
            continue
        lurl = f"{svc_url}/{lid}"
        try:
            n = arcgis_count(lurl)
        except Exception as e:
            layer_info.append(f"{lid}:{lname}=ERR({e})")
            continue
        rows, _m = pull_layer_ids(lurl)
        for r in rows:
            for k in list(r):
                if k.upper().startswith("SHAPE"):
                    r.pop(k, None)
            r["src_layer_id"] = lid
            r["src_layer_name"] = lname
        all_rows.extend(rows)
        layer_info.append(f"{lid}:{lname}={len(rows)}(pub {n})")
        print(f"  layer {lid} '{lname}': {len(rows)} rows (publisher {n})", flush=True)
    load_to_bq(table, all_rows, source=svc_url,
               method="arcgis_rest objectIds-chunked, all layers, outFields=* (lane_c)",
               notes=f"{subject} | layers: {'; '.join(layer_info)} | {notes}")


# 1. Foreclosures 2006-2019 (15 layers, one subject). Separate services
#    FORECLOSURES_2017 / FORECLOSURES_2018 are duplicates of layers 11/12 - skipped.
print("=== EV foreclosures ===", flush=True)
pull_service_stack(
    f"{BASE}/ASSESSOR/FORECLOSURES/MapServer",
    "in_si_evansville_foreclosures",
    "D2_foreclosure (Vanderburgh assessor annual foreclosure layers 2006-2019)",
    ("OBSERVED EVENT DATE granularity = the sale year in src_layer_name (assessor publishes "
     "one layer per year; no per-row filing date). Parcel-keyed via Current_Parcels_StatePIN/"
     "StatePIN (82-...). Full CAMA attributes incl owner, assessments, LastSaleDate. "
     "Duplicate standalone services ASSESSOR/FORECLOSURES_2017 and _2018 NOT pulled "
     "(same layers)."))

# 2. Current + recent tax-sale lists (6 layers)
print("=== EV tax sale lists ===", flush=True)
pull_service_stack(
    f"{BASE}/SITE_PROJECTS/TAX_SALE/MapServer",
    "in_si_evansville_taxsale",
    "D1_tax_sale (Vanderburgh county tax-sale property lists Aug2020-Aug2026)",
    ("OBSERVED EVENT DATE = sale-list date embedded in src_layer_name ('Tax Sale Property as "
     "of Aug 3, 2026' is the CURRENT list; earlier layers Aug 2025/July 2024/Aug 2023/Aug 2022/"
     "Aug 2020). StatePIN parcel-keyed; AMT_DUE_BEFORE_SALE, MINIMUM_BID, SALE_ID, OWNER_NAME "
     "verbatim. Complements si_d1_sri_taxsale_listings (SRI) and Marion county archive."))

# 3. Tax sale transfers 2006-2011 (outcomes)
print("=== EV tax sale transfers ===", flush=True)
pull_service_stack(
    f"{BASE}/ASSESSOR/TAX_SALES/MapServer",
    "in_si_evansville_taxsale_transfers",
    "D1_tax_sale outcome (Vanderburgh tax-sale TRANSFERS 2006-2011)",
    ("Parcels actually transferred at tax sale, one layer per year (year in src_layer_name = "
     "observed event year). StatePIN parcel-keyed, owner + assessment attributes."))

# 4. Demolition (wrecking) permits subset - D21
print("=== EV wrecking permits ===", flush=True)
url = f"{BASE}/BC/BUILDING_COMMISSION_PERMITS/MapServer/0"
where = "UPPER(USER_Project_Activity) LIKE '%WRECK%'"
pub = arcgis_count(url, where=where)
rows, meta = pull_layer_ids(url, where=where)
for r in rows:
    for k in list(r):
        if k.upper().startswith("SHAPE"):
            r.pop(k, None)
print(f"  pulled {len(rows)} wrecking permits (publisher {pub})", flush=True)
load_to_bq(
    "in_si_evansville_demolition_permits", rows,
    source=url,
    method=f"arcgis_rest objectIds-chunked WHERE {where} (lane_c)",
    notes=("D21_demolition (Vanderburgh building-commission WRECKING permits). Subject values "
           "are 'BUILDING WRECKING COMMERCIAL' / 'BUILDING WRECKING RESIDENTIAL' - the corpus "
           "has NO 'DEMOLITION' label (value-enumerated all 31 USER_Project_Activity values; "
           "DEMO=0, WRECK=4190, RAZ=0). OBSERVED EVENT DATE: USER_Application_Recv_d (epoch "
           "ms) = permit application received; USER_Actual_Start_Date/End_Date when present. "
           f"USER_Parcel_ID + address. publisher_count={pub}. Parent corpus is 153,909 permits "
           "of 31 activity types; only the wrecking subject pulled as seller-intent."))
print("DONE", flush=True)
