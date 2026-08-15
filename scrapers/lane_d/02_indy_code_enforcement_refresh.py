"""Lane D refresh: Indianapolis/Marion County code enforcement (D12 signal).

Feeds si_signals source_id = si_d12_indy_marion_code_enforcement (747,211 IN rows held,
observed 2010-03-29 .. 2024-02-27 per BigQuery). Registry-mapped endpoint (ArcGIS, live,
ungated, BUILT+LOADED before):
  https://gis.indy.gov/server/rest/services/OpenData/OpenData_NonSpatial/MapServer/1

Full re-pull, outFields=*, paged to exhaustion, all fields (not just the originally-wired
subset) -> energy-platfrom.indiana_app.in_si_refresh_indy_code_enforcement.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lane_d_util as u

LAYER = "https://gis.indy.gov/server/rest/services/OpenData/OpenData_NonSpatial/MapServer/1"
TABLE = "in_si_refresh_indy_code_enforcement"

u.ensure_dataset_and_registry()

print(f"Pulling layer meta for {LAYER} ...")
meta = u.arcgis_layer_meta(LAYER)
print("layer name:", meta.get("name"), "| maxRecordCount:", meta.get("maxRecordCount"))
fields = [f["name"] for f in meta.get("fields", [])]
print(f"{len(fields)} fields: {fields}")

rows, publisher_count = u.arcgis_pull_all(LAYER, want_geometry=False)
print(f"Pulled {len(rows)} rows; publisher returnCountOnly={publisher_count}")

if not rows:
    raise SystemExit("ABORT: zero rows pulled, refusing to load/register")

n = u.load_to_bq(
    TABLE, rows,
    source="gis.indy.gov OpenData_NonSpatial/MapServer/1 (Indianapolis/Marion County code enforcement)",
    method="arcgis outFields=* resultOffset paging to exhaustion",
    notes=(f"Lane D freshness refresh of si_d12_indy_marion_code_enforcement "
           f"(747,211 IN rows held in si_signals, observed 2010-03-29..2024-02-27). "
           f"Publisher returnCountOnly={publisher_count}; pulled {len(rows)}. "
           f"All {len(fields)} layer fields captured, not just the originally-wired subset. "
           f"Registry note: a separate agis_indy_code_enforcement/si_d12 acquisition already "
           f"holds 910,483 rows (DUPLICATE-OF-HELD per Lane C) - this refresh re-measures the "
           f"LIVE publisher state independently for the freshness diff."),
)
print(f"DONE: {n} rows loaded to in_si_refresh_indy_code_enforcement")
