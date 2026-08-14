"""Target 5a: South Bend / St. Joseph County (I&M priority) seller-intent layers.
All from the city's public AGOL org (0n2NelSAfR7gTkr1) found via data-southbend DCAT."""
import sys
sys.path.insert(0, r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial\scrapers\lane_c")
from lane_c_util import arcgis_pull_all, load_to_bq

AGOL = "https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services"

PULLS = [
    dict(
        table="in_si_southbend_demolition_orders",
        url=f"{AGOL}/Active_Demolition_Orders/FeatureServer/0",
        subject="D21_demolition (FIRST D21-type source held for Indiana)",
        notes=("South Bend 'Demolition Orders (Historic / Non-Authoritative)' from "
               "data-southbend DCAT. Parcel-keyed: 'State' column IS the 18-digit state parcel "
               "id (71-...), 'County' is the county tax id - publisher swapped the labels, "
               "value-verified. OBSERVED EVENT DATES: Bid_Awarded_Date / Bid_Opening_Date "
               "(epoch ms when present). Sourced from the city's SharePoint code_enforcement/"
               "demolitions list. Snapshot, not live Accela."),
    ),
    dict(
        table="in_si_southbend_vacant_abandoned",
        url=f"{AGOL}/AllVacantandAbandonedProperties/FeatureServer/3",
        subject="D5_vacancy (city V&A program list w/ outcomes)",
        notes=("South Bend 'All Vacant and Abandoned Properties (Historic / Non-Authoritative)'. "
               "State_ID_LU = 18-digit state parcel id. OBSERVED EVENT DATE: Added_to_V_A_on_ "
               "(program entry) and State_ID_LU_Date_of_Outcome (outcome). Condition codes + "
               "repair cost estimates included."),
    ),
    dict(
        table="in_si_southbend_chronic_problem",
        url=f"{AGOL}/Chronic_Problem_Properties_List/FeatureServer/0",
        subject="D12_code_violation (chronic problem property designations)",
        notes=("South Bend Chronic Problem Properties List (municipal designation under city "
               "ordinance). OBSERVED EVENT DATE: Designation_Date (epoch ms). Address-keyed. "
               "Tiny list but the designation is a strong distress marker."),
    ),
    dict(
        table="in_si_southbend_continuous_enforcement",
        url=f"{AGOL}/Continuous_Enforcement/FeatureServer/4",
        subject="D12_code_violation (continuous-enforcement orders)",
        notes=("South Bend Continuous Enforcement orders. PARCELID (county) + STATE_ID "
               "(18-digit state parcel id). OBSERVED EVENT DATE: HEARING__OR_LETTER_DATE; "
               "EXPIRATION_DATE bounds the order. Status Active/... kept verbatim."),
    ),
    dict(
        table="in_si_southbend_code_enforcement",
        url=f"{AGOL}/Code_Enforcement_Cases/FeatureServer/0",
        subject="D12_code_violation (case-level, St. Joseph County - NEW county for D12)",
        notes=("South Bend Code Enforcement Cases 2018-2020 (Historic). State_ID__ = 18-digit "
               "state parcel id -> parcel-keyed. OBSERVED EVENT DATE: Record_Open_Date "
               "(epoch ms); Record_Status_Date = status-change date. Record_Type spans "
               "Litter/Grass and Weeds/housing etc - consumer must read Record_Type "
               "(a name is not a subject). Extends D12 beyond Marion County."),
    ),
]

for p in PULLS:
    print("=" * 80, flush=True)
    print("PULLING", p["table"], flush=True)
    rows, publisher_count = arcgis_pull_all(p["url"], want_geometry=False)
    print(f"  pulled {len(rows)} rows (publisher count {publisher_count})", flush=True)
    load_to_bq(
        p["table"], rows,
        source=p["url"],
        method="arcgis_rest_paged outFields=* (lane_c)",
        notes=f"{p['subject']} | publisher_count={publisher_count} | {p['notes']}",
    )
print("DONE", flush=True)
