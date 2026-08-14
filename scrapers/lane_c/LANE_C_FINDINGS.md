# Lane C findings — Indiana public seller-intent scrape (2026-08-14)

Scope: public distress-signal sources for Indiana commercial/industrial siting.
Rules honored: robots.txt checked per HTML host; >=1 req/s/host; UA
`DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)`; outFields=* with
pagination verified against publisher counts; observed event dates captured, `_pulled_at`
separate; all writes to `energy-platfrom.indiana_app`; every table registered in
`indiana_app._registry` in the same run; nothing gated was worked around.

Ordering: statewide completeness first (operator clarification); I&M/PJM-footprint counties
(EIA-861 utility 9324: Allen, St. Joseph, Elkhart, ...43 counties) used as tiebreaker —
South Bend/St. Joseph worked before Evansville; Fort Wayne attempted first but walled.

## Registry pre-check (do-not-reacquire honored)

`energy.registry_sources` rows for Indiana said, before any probe:
- SRI tax-sale platform (target 4) ALREADY HELD: `si_d1_sri_taxsale_listings`, 217,226 rows
  (IN 81,975 across 80/91 counties), rebuilt 2026-08-09 via the publisher's own public
  x-api-key (no account). NOT re-pulled. Re-scrape: `python -m ingest.load_sri_taxsale_bq --force`.
- Indy/Marion code enforcement (D12) held TWICE (`agis_indy_code_enforcement`,
  `si_d12_indy_marion_code_enforcement`, 910,483 rows, DUPLICATE-OF-HELD). NOT re-pulled.
- SRI/Zeus auction calendar: registered WIRED-not-populating; sheriff-sale addresses appear
  only ~30d pre-sale; PWA. Not re-probed this run.
- Marion parcels ArcGIS (services3/hrGHbYKdjpN9Dagg): BLOCKED 499 Token Required (known).
- IURC EDS portal: BLOCKED (Power Pages SPA) (known).
- IBTR determinations (D26) held: 10,071 rows.

## Tables built this run (all in `energy-platfrom.indiana_app`, all registered)

| table | rows | signal | county | observed event date |
|---|---|---|---|---|
| in_si_indy_taxsale_parcels | 62,368 | D1 tax-sale archive w/ per-sale status | Marion | STATUSDATE (epoch ms); TAXYEAR 2009->2024 |
| in_si_indy_surplus_parcels | 595 | surplus/commissioners-auction inventory | Marion | AuctionID-embedded date / SaleDate |
| in_si_indy_abandoned_vacant | 7,120 | D5 city abandoned+vacant registry | Marion | none on layer — snapshot semantics (_pulled_at) |
| in_si_state_warn_notices | 1,220 | D19 WARN 2008->2026 (full history, not just current) | statewide | Notice Date (1,016/1,220 clean M/D/YYYY) |
| in_si_southbend_demolition_orders | 80 | D21 demolition orders — FIRST D21-type holding for IN | St. Joseph | Bid_Awarded/Bid_Opening dates |
| in_si_southbend_vacant_abandoned | 47 | D5 V&A program list w/ outcomes | St. Joseph | Added_to_V_A_on_, Date_of_Outcome |
| in_si_southbend_chronic_problem | 7 | D12 chronic-problem designations | St. Joseph | Designation_Date |
| in_si_southbend_continuous_enforcement | 241 | D12 continuous-enforcement orders | St. Joseph | HEARING__OR_LETTER_DATE |
| in_si_southbend_code_enforcement | 20,414 | D12 case-level 2018-2020 — FIRST non-Marion D12 | St. Joseph | Record_Open_Date |
| in_si_evansville_foreclosures | 5,758 | D2 foreclosure, 2006-2019 annual layers | Vanderburgh | year in src_layer_name (no per-row date published) |
| in_si_evansville_taxsale | 3,202 | D1 lists Aug2020->CURRENT Aug 3, 2026 | Vanderburgh | list date in src_layer_name |
| in_si_evansville_taxsale_transfers | 941 | D1 outcomes (transfers) 2006-2011 | Vanderburgh | year in src_layer_name |
| in_si_evansville_demolition_permits | 4,190 | D21 'BUILDING WRECKING' permits (419 comm / 3,771 res) | Vanderburgh | USER_Application_Recv_d |

**13 tables, 106,183 rows, all verified table-count == registry-count == publisher-count.**
(Evansville objectIds paging note: 250-id GET chunks overflowed the server URL limit and
returned HTML; the fix that landed is POSTed queries with 100-id chunks.)

Parcel keys: South Bend tables carry 18-digit state parcel ids (71-...); Evansville carries
StatePIN (82-...); Indy tax-sale/abandoned tables carry the LOCAL 7-digit Marion parcel id
(PARCEL_I/PARCELNUMBER), not the state id — join via Marion crosswalk.

## Value-sample saves (rule 10 / §"a name is not a subject")

- AGOL org `allenco` (Tax_delinquent_parcels 726, Vacant_parcels 1,018, Landbank_parcels 44)
  is Allen County **OHIO** (rows: "CITY OF LIMA OHIO", zips 45801, ohlex.asc.ohio-state.edu
  companion service). REJECTED before load. The tempting first-D4 claim was false.
- Evansville permits: demolition subject is labeled `BUILDING WRECKING *`; the corpus has NO
  'DEMOLITION' value (all 31 USER_Project_Activity values enumerated; DEMO=0, WRECK=4,190).
- Indy "Abandoned and Vacant" exists as 3 byte-identical layers (OpenData_Infrastructure/2,
  MapIndyProperty/11, /16) — pulled once, registry note forbids wiring the copies.
- Evansville FORECLOSURES_2017/_2018 standalone services duplicate combined-service layers
  11/12 — skipped.
- data.indy.gov hub "Tax Sale Reports 2010-2017" and "Surplus Sale Reports" items are PDF
  document collections; the live layers pulled above supersede them.

## BLOCKED (exact walls; recorded, not worked around)

1. **Statewide tax warrants (D13-analog)** — no open dataset exists. hub.mph.in.gov CKAN
   enumerated: 67 datasets, zero seller-intent subjects. data.in.gov: dead (SSL
   TLSV1_UNRECOGNIZED_NAME; API connection reset). mycase.in.gov (Odyssey, the statewide
   court/tax-warrant search): robots.txt `Disallow: /API*`, `/APP*`, `/*` for `User-agent: *`
   — hard robots wall. public.courts.in.gov robots disallows /MYCASE/*. Bulk trial-court data
   requires an Office of Judicial Administration data agreement (contract channel).
2. **Fort Wayne / Allen County IN open GIS** — no public REST directory found:
   maps.cityoffortwayne.org 404s /arcgis|/server|/gis; acimap.us catch-alls every path
   (incl. /arcgis/rest/services, config.json) to the same HTML shell; no city/county AGOL
   open-data org surfaces in AGOL search; gis.allencounty.us NXDOMAIN. County assessor data
   sits behind Beacon (schneidercorp) ToS interstitial = terms dialogue, out of bounds.
3. **DWD WARN portal app** (dwdportal.dwd.in.gov/WARN/warn_landing/) — PowerApps portal SPA
   (gov.content.powerapps.us bundles); not scrapeable without executing the app. Moot: the
   static in.gov table carries the full 2008-2026 history and was pulled.
4. **Indiana SOS / INBiz entity dissolutions (D11)** — standing decisions honored: bulk
   purchase REJECTED; per-entity search gated (account). Not probed.
5. **Indianapolis demolition permits as a dataset** — none on gis.indy.gov or the hub;
   permits live in Accela Citizen Access (interactive search, session-gated). NOTE: Indy
   demolition ORDERS are already inside the HELD 910,483-row D12 corpus (case/violation
   types) — extract there, no new acquisition needed.

## 3 highest-value sources found but NOT finished

1. **Indy TaxSaleViewer "BuildingBlocks" siblings + Parcel Bill Code table**
   (gis.indy.gov OpenData_NonSpatial/12 `Parcel Bill Code`, TaxSaleViewer service stack):
   the local-parcel->state-parcel crosswalk needed to join the two Marion tables above to
   `in_sites`; one more ArcGIS pull each.
2. **Evansville full building-permit corpus** (BC/BUILDING_COMMISSION_PERMITS/0,
   153,909 rows, 31 activity types): NEW COMMERCIAL BUILDING / COMMERCIAL REPAIR rows are a
   forward-activity (A-side) signal and the wrecking subset's parent; a full pull is ~80
   objectIds-chunked requests, straightforward, just large.
3. **Fort Wayne/Allen County IN via browser network inspection**: acimap.us is a JS iMap
   whose backing ArcGIS server is only visible from the app's network traffic; one
   browser-devtools session would likely expose a public REST endpoint (city had
   vacant/blight programs, so D5/D12/D21 subjects plausibly exist).
   (Runner-up: Mayor's Action Center service-case tables on OpenData_NonSpatial/2-4 —
   nuisance-complaint signal, weaker subject, sampled not pulled.)

## Platform corrections for the registry

- hub.mph.in.gov is **CKAN**, not Socrata (brief said Socrata). Socrata discovery API 404s
  for all in.gov domains.
- South Bend's open-data DCAT feed mislabels one dataset ("Awarded Bids" points at
  OpenData/VacantAbandoned/MapServer/2).
