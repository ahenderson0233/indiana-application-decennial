"""Lane D refresh: EPA RE-Powering Mapper brownfield/contaminated-land sites,
INDIANA SLICE ONLY (brownfield_epa_repowering signal).

Feeds si_signals source_id = brownfield_epa_repowering (1,378 IN rows held, no
observed_date -- a STATE-class signal per METHODS' DECAY classification, not an EVENT).
Registry-mapped endpoint (public ArcGIS FeatureServer, no auth, exact source_id match,
'done' status, national -- 190,976 total features across all states/territories):
  https://services.arcgis.com/cJ9YHowT8TU7DUyn/arcgis/rest/services/RE_Powering_Mapper_Sites_2022/FeatureServer/0

MULTI-STATE SOURCE WITH AN INDIANA SLICE (task step 5): the layer publishes a real
`State` field (esriFieldTypeString, confirmed via layer metadata /? f=json -- not a
guessed column), so the Indiana slice is pulled via the ENDPOINT's own WHERE filter
(State='IN'), never by guessing which column might hold a state code.

outFields=*, paged to exhaustion, verified against returnCountOnly ->
energy-platfrom.indiana_app.in_si_refresh_brownfield_epa_in.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lane_d_util as u

LAYER = "https://services.arcgis.com/cJ9YHowT8TU7DUyn/arcgis/rest/services/RE_Powering_Mapper_Sites_2022/FeatureServer/0"
TABLE = "in_si_refresh_brownfield_epa_in"
WHERE = "State='IN'"

u.ensure_dataset_and_registry()

national_count = u.arcgis_count(LAYER)
in_count = u.arcgis_count(LAYER, where=WHERE)
print(f"National total (returnCountOnly): {national_count}; Indiana slice (State='IN'): {in_count}")

if not in_count:
    raise SystemExit(f"ABORT: WHERE {WHERE} matched 0 rows -- state value format assumption "
                      f"is wrong (not a live-data problem); do not fabricate a different filter.")

rows, publisher_count = u.arcgis_pull_all(LAYER, where=WHERE, want_geometry=False)
print(f"Pulled {len(rows)} IN rows; publisher returnCountOnly={publisher_count}")

if not rows:
    raise SystemExit("ABORT: zero rows pulled, refusing to load/register")

n = u.load_to_bq(
    TABLE, rows,
    source="EPA RE-Powering Mapper Sites 2022 ArcGIS FeatureServer, State='IN' slice of a national layer",
    method="arcgis outFields=* WHERE State='IN' resultOffset paging to exhaustion",
    notes=(f"Lane D freshness refresh of brownfield_epa_repowering (1,378 IN rows held in "
           f"si_signals; STATE-class signal, no observed_date expected). National layer holds "
           f"{national_count} features; Indiana slice (State='IN', a real published field, not "
           f"a guessed column) = {in_count} per publisher returnCountOnly, {len(rows)} pulled. "
           f"Other states deliberately NOT pulled -- out of scope for this Indiana lane. "
           f"Programme/status-shaped columns (Program, Landfill, AML, REPwrPrfle) are candidate "
           f"columns for the new-signal-candidates review."),
)
print(f"DONE: {n} rows loaded to {TABLE}")
