"""Append every source the Indiana lanes explored/scraped to energy.registry_sources
(operator-directed; APPEND-only — the registry is never truncated/merged, per D25).
Status vocabulary follows the platform: done / blocked. Walls recorded verbatim."""
import datetime
from google.cloud import bigquery

client = bigquery.Client(project="energy-platfrom")
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()
BY = "indiana-app-session-20260815"

def row(name, status, endpoint, objects, provides, notes, state="IN", category="indiana-app"):
    return {"source_id": f"inapp_{abs(hash(name)) % 10**10}", "source_name": name, "status": status,
            "endpoint": endpoint,
            "object_names": [o.strip() for o in objects.split(",") if o.strip()],
            "what_it_provides": provides,
            "notes": notes, "geography_state": state, "category": category,
            "updated_by": BY, "origin": "indiana-application-decennial",
            "last_validated_at": NOW, "access": "public" if status == "done" else "gated"}

R = [
 # Lane A / transmission
 row("MISO giqueue POI viewer - identity API", "done", "https://giqueue.misoenergy.org/POI/api/pois",
     "indiana_app.in_miso_poi_identity", "POI->bus number/name/kV/coords (9,981 with coords)",
     "closes the miso_poi_monitored_facilities identity gap 100%; DPP-2021 vintage per publisher"),
 row("MISO giqueue POI transfer analysis - bounded 300MW", "done",
     "https://giqueue.misoenergy.org/POI/api/poi_mf?poiName=<n>&pMaxValue=300",
     "indiana_app.in_miso_poi_300mw,in_bus_headroom_300",
     "per-facility allowable injection at a 300MW request (PMax verified 0..300, 3,593 distinct)",
     "INJECTION-only viewer; 641/642 IN POIs read 0 at 300MW; re-run script scrapers/lane_a/pull_miso_poi_300mw.py"),
 row("MISO CartoVista POI heatmap", "blocked", "https://cloud.cartovista.com/miso/ferc",
     "", "bus-level FCITC surface (19,223 buses declared)",
     "re-measured 2026-08-14: Layer/geojson, DataRows, dataQueryExecute all 403 empty-body (ProtectedData); metadata+MVT 200"),
 row("PJM public GIS (gis.pjm.com) - queue points", "done",
     "https://gis.pjm.com (ArcGIS REST, previously uncataloged)",
     "indiana_app.in_pjm_gis_queues", "6,923 queue points with PJM's own coordinates",
     "CTC/* and RTDMS/* layers exist but return in-body esriCarto 500 anonymously; ESM exposes no public services", state=""),
 row("PJM RTEP Project Status & Cost Allocation", "done",
     "https://www.pjm.com/planning/m/project-construction (POST family incl. UpgradeDetails, UpgradeCostAllocations, GenerateExcelNUCRAProjectsAll)",
     "indiana_app.in_pjm_rtep_upgrades,in_pjm_rtep_upgrade_details,in_pjm_rtep_cost_allocations,in_pjm_nucra_costs",
     "upgrades (15,443; 932 IN) + per-upgrade details (932/932) + cost allocations (375) + NUCRA costs (55)",
     "public POSTs, no login; crawl cache resumable in scrapers/lane_a/_cache_pjm_details", state=""),
 row("I&M/AEP hosting capacity map (PROD_MI_HC_GRID)", "done",
     "AGOL FeatureServer PROD_MI_HC_GRID", "",
     "distribution hosting capacity", "MICHIGAN-ONLY today: 0 Indiana rows measured live; publisher states MI-only; re-check quarterly"),
 row("Duke Indiana / NIPSCO / AES Indiana / CenterPoint IN hosting-capacity maps", "blocked", "",
     "", "distribution HC maps", "measured NONEXISTENT: site inspections + DOE HC atlas (July 2025) list no Indiana utilities; Duke AGOL org (76 services) has Carolinas/Ohio only"),
 # Lane E / gas EBBs
 row("Texas Gas Transmission EBB (Boardwalk GasQuest)", "done", "GasQuest anonymous API",
     "indiana_app.in_gas_capacity_texas_gas", "daily operationally-available capacity", "7 days all cycles"),
 row("Vector Pipeline EBB (gasnom.com)", "done", "gasnom.com vendor EBB HTML",
     "indiana_app.in_gas_capacity_vector", "daily OAC", "7 gas-day pages"),
 row("Midwestern Gas Transmission EBB (DTM Trellis)", "done", "Trellis public .do CSV",
     "indiana_app.in_gas_capacity_midwestern", "daily OAC", "two-block CSV parse corrected in-run"),
 row("Panhandle Eastern EBB (ET Messenger)", "done", "Messenger native CSV (gasDay param)",
     "indiana_app.in_gas_capacity_panhandle_eastern", "daily OAC WITH State+County per location",
     "county-plottable: 154 IN rows / 11 counties"),
 row("Trunkline EBB (ET Messenger)", "done", "Messenger native CSV",
     "indiana_app.in_gas_capacity_trunkline", "daily OAC WITH State+County", "49 IN rows / 3 counties"),
 row("NGPL EBB (KM DART)", "done", "DART EXCEL export replicated",
     "indiana_app.in_gas_capacity_ngpl", "daily OAC", ""),
 row("ANR / Northern Border / Crossroads EBBs (TC eConnects)", "done", "SSRS &rs:Format=CSV",
     "indiana_app.in_gas_capacity_anr,in_gas_capacity_northern_border,in_gas_capacity_crossroads",
     "daily OAC", ""),
 row("Texas Eastern EBB (Enbridge infopost)", "blocked", "https://infopost.enbridge.com",
     "", "daily OAC", "robots.txt blanket Disallow /; link.enbridge.com is a login portal; NOT scraped"),
 row("Rockies Express EBB (Tallgrass)", "blocked", "https://pipeline.tallgrassenergylp.com",
     "", "daily OAC", "Imperva/Incapsula JS bot-challenge on every path incl. NAESB-listed OA pages; NOT bypassed"),
 # Lane B / regulatory + sentiment
 row("IURC EDS docket system - anonymous companion REST", "done",
     "IURC advanced-search companion API (search, lists, per-case docs, anonymous SharePoint downloads)",
     "indiana_app.in_iurc_dockets,in_grid_plans",
     "516 DC/large-load-relevant dockets + TDSIC/IRP grid-plan docs (618 rows)",
     "REFUTES stale 'BLOCKED (SPA)' registry note - full endpoint map in scrapers/lane_b/LANE_B_FINDINGS.md"),
 row("Municode library - Indiana clients", "done", "library.municode.com public search",
     "indiana_app.in_ordinances_dc", "data-center phrase hits across 45 IN clients",
     "robots permitted the JSON search endpoints used; St. Joseph County codified DC standards found"),
 row("American Legal codelibrary", "blocked", "https://codelibrary.amlegal.com",
     "", "ordinance text search", "Cloudflare JS-challenge 403 on HTML AND /api/search/ (re-measured); held 183 IN rows are loose mentions"),
 row("Google News RSS", "blocked", "https://news.google.com/rss/search",
     "", "news search feed", "robots.txt Disallow / without /rss allow - assumption measured FALSE; not scraped"),
 row("Bing News RSS", "done", "bing.com/news RSS",
     "indiana_app.in_news_dc", "283 unique-link items via 114 county/city queries", ""),
 row("GDELT", "blocked", "gdelt API", "", "news tone", "persistent 429 even at 5.5s intervals - 0 rows"),
 row("Data Center Watch quarterlies", "blocked", "datacenterwatch /report",
     "indiana_app.in_dc_actions", "opposition actions", "quarterly detail is client-side JS from robots-disallowed /api/; headline parse only (79 rows)"),
 # Lane C / SI acquisitions
 row("Indy/Marion open data (data.indy.gov + city ArcGIS)", "done", "Socrata + ArcGIS REST",
     "indiana_app.in_si_indy_taxsale_parcels,in_si_indy_abandoned_vacant,in_si_indy_surplus_parcels",
     "tax-sale archive 62,368 / vacant 7,120 / surplus 595", ""),
 row("South Bend open data (DCAT)", "done", "South Bend DCAT catalog",
     "indiana_app.in_si_southbend_code_enforcement,in_si_southbend_demolition_orders,in_si_southbend_vacant_abandoned,in_si_southbend_continuous_enforcement,in_si_southbend_chronic_problem",
     "code enforcement 20,414 (18-digit parcel keys) + demolition orders + vacancy", ""),
 row("Evansville/Vanderburgh portal", "done", "Evansville open data",
     "indiana_app.in_si_evansville_demolition_permits,in_si_evansville_foreclosures,in_si_evansville_taxsale,in_si_evansville_taxsale_transfers",
     "wrecking permits 4,190 (D21) + foreclosures + tax sales", "full 153,909-row permit corpus flagged as follow-up"),
 row("Indiana DWD WARN page", "done", "in.gov/dwd WARN listing",
     "indiana_app.in_si_state_warn_notices,in_si_refresh_warn_notices",
     "full 2008-2026 WARN history (1,220)", "'current' page carries full history"),
 row("SRI tax-sale platform (Indiana)", "done", "sriservices/zeusauction public lists",
     "indiana_app.in_si_refresh_sri_taxsale_in", "83,547 rows refreshed all-fields", "already-held check honored; refresh only"),
 row("mycase.in.gov (court records)", "blocked", "https://public.courts.in.gov / mycase.in.gov",
     "", "statewide court/tax-warrant records", "robots.txt Disallow /API*,/APP*,/*; bulk = OJA contract channel"),
 row("Fort Wayne / Allen County GIS", "blocked", "maps.cityoffortwayne.org / acimap.us",
     "", "parcels, code enforcement", "no public REST directory: 404s + HTML catch-all; assessor behind Beacon ToS interstitial; browser network inspection is the named next step"),
 row("Indiana MPH open data (CKAN)", "done", "hub.mph.in.gov CKAN API",
     "", "state datasets catalog", "67 datasets enumerated; zero SI-relevant; data.in.gov TLS-dead"),
]
job = client.load_table_from_json(
    R, "energy-platfrom.energy.registry_sources",
    job_config=bigquery.LoadJobConfig(write_disposition="WRITE_APPEND",
        schema_update_options=[]))
job.result()
print(f"APPENDED {len(R)} source rows to energy.registry_sources (append-only)")
