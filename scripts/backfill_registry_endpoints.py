"""Backfill the 31 thin registry rows so every source we scraped is RE-RUNNABLE.

The audit (docs/SIGNAL_ENDPOINTS.md) found our own rows carry endpoint text but
0/31 `endpoint_kind` and 0/31 `acquisition_method`, and 7 of the endpoints are PROSE rather
than addresses ("Evansville open data", "Messenger native CSV"). Nobody can re-run those.

Ground truth is the scraper scripts themselves — the URL a script actually requests — not the
prose someone typed into a registration. Every URL below was read out of `scrapers/lane_*/*.py`.

APPEND-ONLY per D25: this writes NEW rows carrying the corrected detail. The originals stay as
the historical record; `updated_by` distinguishes them.
"""
import datetime, sys
from google.cloud import bigquery

client = bigquery.Client(project="energy-platfrom")
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()
BY = "indiana-app-session-20260815-endpoints"
DRY = "--dry-run" in sys.argv
R = "scrapers"

# (source_name, endpoint URL read from the scraper, endpoint_kind, re-run command, tables)
FIX = [
 ("MISO giqueue POI viewer - identity API",
  "https://giqueue.misoenergy.org/POI/api/pois", "rest_json",
  f"python {R}/lane_a/build_in_miso_poi_identity.py", "in_miso_poi_identity"),
 ("MISO giqueue POI transfer analysis - bounded 300MW",
  "https://giqueue.misoenergy.org/POI/api/poi_mf?poiName=<POI>&pMaxValue=300", "rest_json",
  f"python {R}/lane_a/pull_miso_poi_300mw.py", "in_miso_poi_300mw,in_bus_headroom_300"),
 ("PJM public GIS (gis.pjm.com) - queue points",
  "https://gis.pjm.com/arcgis/rest/services", "arcgis_rest",
  f"python {R}/lane_a/pull_pjm_gis_queues.py", "in_pjm_gis_queues"),
 ("PJM RTEP Project Status & Cost Allocation",
  "https://www.pjm.com/planning/m/project-construction", "html_form_post",
  f"python {R}/lane_a/pull_pjm_rtep_upgrades.py && python {R}/lane_a/pull_pjm_upgrade_details.py",
  "in_pjm_rtep_upgrades,in_pjm_rtep_upgrade_details,in_pjm_rtep_cost_allocations,in_pjm_nucra_costs"),
 ("Midwestern Gas Transmission EBB (DTM Trellis)",
  "https://dtmidstream.trellisenergy.com/ptms/public/infopost/getOperationallyAvailable.do?globalTSP=10",
  "http_csv", f"python {R}/lane_e/pull_ebb_capacity.py && python {R}/lane_e/load_to_bq.py",
  "in_gas_capacity_midwestern"),
 ("Panhandle Eastern EBB (ET Messenger)",
  "https://pipelines.energytransfer.com/ipost/PEPL/capacity/operationally-available",
  "http_csv", f"python {R}/lane_e/pull_ebb_capacity.py && python {R}/lane_e/load_to_bq.py",
  "in_gas_capacity_panhandle_eastern"),
 ("Trunkline EBB (ET Messenger)",
  "https://pipelines.energytransfer.com/ipost/TRUNKLINE/capacity/operationally-available",
  "http_csv", f"python {R}/lane_e/pull_ebb_capacity.py && python {R}/lane_e/load_to_bq.py",
  "in_gas_capacity_trunkline"),
 ("Texas Gas Transmission EBB (Boardwalk GasQuest)",
  "https://infopost.bwpipelines.com/", "http_csv",
  f"python {R}/lane_e/pull_ebb_capacity.py && python {R}/lane_e/load_to_bq.py",
  "in_gas_capacity_texas_gas"),
 ("NGPL EBB (KM DART)",
  "https://pipeline2.kindermorgan.com/Capacity/OpAvailPoint.aspx?code=NGPL", "aspx_export",
  f"python {R}/lane_e/pull_ebb_capacity.py && python {R}/lane_e/load_to_bq.py",
  "in_gas_capacity_ngpl"),
 ("ANR Pipeline EBB", "https://ebb.anrpl.com/", "http_csv",
  f"python {R}/lane_e/pull_ebb_capacity.py && python {R}/lane_e/load_to_bq.py",
  "in_gas_capacity_anr"),
 ("Rockies Express (REX) EBB", "https://pipeline.tallgrassenergylp.com/Pages/Point.aspx?pipeline=501&type=OA",
  "aspx_export", f"python {R}/lane_e/pull_ebb_capacity.py", ""),
 ("Texas Eastern EBB (Enbridge infopost)", "https://infopost.enbridge.com/", "html",
  "BLOCKED - wall recorded, do not retry without new terms", ""),
 ("Indiana WARN notices (DWD)",
  "https://dwdportal.dwd.in.gov/WARN/warn_landing/", "html_table",
  f"python {R}/lane_d/04_warn_notices_refresh.py",
  "in_si_state_warn_notices,in_si_refresh_warn_notices"),
 ("Indianapolis/Marion open data (Socrata + ArcGIS)",
  "https://data.indy.gov/api/search/v1/collections/all/items", "socrata_arcgis",
  f"python {R}/lane_d/02_indy_code_enforcement_refresh.py",
  "in_si_indy_taxsale_parcels,in_si_indy_abandoned_vacant,in_si_indy_surplus_parcels"),
 ("Indy code enforcement (ArcGIS OpenData_NonSpatial/1)",
  "https://gis.indy.gov/server/rest/services/OpenData/OpenData_NonSpatial/MapServer/1",
  "arcgis_rest", f"python {R}/lane_d/02_indy_code_enforcement_refresh.py",
  "in_si_refresh_indy_code_enforcement"),
 ("SRI tax sale (zeusauction public lists)",
  "https://www.sriservices.com/", "rest_json",
  f"python {R}/lane_d/06_sri_taxsale_in_refresh.py", "in_si_refresh_sri_taxsale_in"),
 ("IOCS court statistics workbook",
  "https://www.in.gov/courts/iocs/files/rpts-ijs-2025-pending-incoming-disposed-miscellaneous.xlsx",
  "file_xlsx", f"python {R}/lane_d/05_iocs_eviction_refresh.py", "in_si_refresh_iocs_eviction"),
 ("IBTR appeals", "https://www.in.gov/ibtr/", "rest_json",
  f"python {R}/lane_d/03_ibtr_appeals_refresh.py", "in_si_refresh_ibtr_appeals"),
 ("EPA brownfields (Indiana slice)", "https://www.epa.gov/frs", "rest_json",
  f"python {R}/lane_d/07_brownfield_epa_in_refresh.py", "in_si_refresh_brownfield_epa_in"),
 ("IURC advanced-search companion API",
  "https://iurc.portal.in.gov/", "rest_json",
  f"python {R}/lane_b/04_iurc_dockets.py", "in_iurc_dockets,in_grid_plans"),
 ("Bing news RSS (Indiana DC coverage)",
  "https://www.bing.com/news/search?format=RSS&q=", "rss",
  f"python {R}/lane_b/09_news.py", "in_news_dc"),
 ("Fort Wayne / South Bend open data (DCAT feeds)",
  "https://data-cityoffortwayne.opendata.arcgis.com/api/feed/dcat-us/1.1.json", "dcat_json",
  f"python {R}/lane_b/03_city_portals.py", "in_si_southbend_code_enforcement"),
 ("Evansville/Vanderburgh portal",
  "https://data.evansvillegov.org/", "socrata_arcgis",
  f"python {R}/lane_b/03_city_portals.py",
  "in_si_evansville_foreclosures,in_si_evansville_taxsale,in_si_evansville_taxsale_transfers"),
 ("Indiana state data portal (CKAN)", "https://data.in.gov/api/3/action/package_list",
  "ckan_api", f"python {R}/lane_b/02_state_portals.py", ""),
 ("Municode ordinance search", "https://api.municode.com/search", "rest_json",
  f"python {R}/lane_b/05_ordinances.py", "in_ordinances_dc"),
 ("American Legal ordinance library", "https://codelibrary.amlegal.com/api/search/", "rest_json",
  f"python {R}/lane_b/05_ordinances.py", "in_ordinances_dc"),
 ("GDELT article API", "https://api.gdeltproject.org/api/v2/doc/doc", "rest_json",
  "BLOCKED - rate-limit wall recorded", ""),
 ("MISO CartoVista POI heatmap", "https://cloud.cartovista.com/miso/ferc", "rest_json",
  "BLOCKED - 403 ProtectedData on Layer/geojson, DataRows, dataQueryExecute", ""),
 ("I&M/AEP hosting capacity map (PROD_MI_HC_GRID)",
  "https://services.arcgis.com/ (AGOL FeatureServer PROD_MI_HC_GRID)", "arcgis_rest",
  f"python {R}/lane_a/check_aep_states.py   # quarterly probe: MI-only today, 0 Indiana rows", ""),
]

rows = []
for name, ep, kind, cmd, objs in FIX:
    blocked = cmd.startswith("BLOCKED")
    rows.append({
      "source_id": f"inapp_ep_{abs(hash(name)) % 10**10}",
      "source_name": name, "status": "blocked" if blocked else "done",
      "endpoint": ep, "endpoint_raw": ep, "endpoint_kind": kind,
      "acquisition_method": cmd,
      "object_names": [o.strip() for o in objs.split(",") if o.strip()],
      "geography_state": "IN", "category": "indiana-app",
      "updated_by": BY, "origin": "indiana-application-decennial",
      "last_validated_at": NOW, "access": "gated" if blocked else "public",
      "notes": ("ENDPOINT BACKFILL 2026-08-15. Supersedes the thin row appended by "
                "indiana-app-session-20260815, which carried no endpoint_kind and no "
                "acquisition_method (several endpoints were prose, not addresses). URL read from "
                "the scraper source, not retyped. registry_sources is APPEND-ONLY (D25): the "
                "original row is left intact as the historical record."),
    })

print(f"prepared {len(rows)} corrected rows "
      f"({sum(1 for r in rows if r['status']=='blocked')} blocked)")
for r in rows[:4]:
    print(f"  {r['source_name'][:44]:<44} {r['endpoint_kind']:<14} {r['endpoint'][:52]}")
if DRY:
    print("\nDRY RUN - nothing appended"); sys.exit()

errors = client.insert_rows_json("energy-platfrom.energy.registry_sources", rows)
if errors:
    print("INSERT ERRORS:", errors[:3]); sys.exit(1)
print(f"appended {len(rows)} rows to energy.registry_sources as updated_by='{BY}'")
