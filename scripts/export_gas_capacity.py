"""G92 - put GAS HEADROOM into the pipeline popup, which showed operator and type and nothing else.

    python scripts/export_gas_capacity.py

Operator, 2026-08-19: *"We need more data in the map popups (e.g., the natural gas pipelines should
show headroom, where the data is available, and this can be applied elsewhere as well, in many
places)."*

⭐ WE HOLD IT AND IT IS GOOD. Energy Transfer's iPost boards give, per named location, the DESIGN
capacity, the OPERATING capacity, the scheduled quantity and - the one that matters - the
OPERATIONALLY AVAILABLE capacity, i.e. how much is free that gas day. In Indiana, for the current
gas day: **28 locations, 2.53 million Dth/day free**.

    Elkhart - Consumers Energy   453,287 free of 715,000 design   (~2,906 MW)
    Indiana Gas, Madison Co.     374,305 free of 544,000 design   (~2,399 MW)
    Citizens Energy, Marion Co.  338,206 free of 400,000 design   (~2,168 MW)

⛔ FOUR MEASUREMENT TRAPS, EVERY ONE OF WHICH BIT DURING THIS BUILD:

 1. **`state` IS SPACE-PADDED** - the literal value is `'IN      '`, so `WHERE state='IN'` returns
    ZERO rows and looks like "we hold nothing for Indiana". Exactly the padding that made the PJM
    binding-facility comparison read 0 of 282 when the true answer was 100. Always TRIM.
 2. **THE CAPACITY IS IN `oac`, NOT `operationally_available_capacity`.** The table carries BOTH
    columns; the long-form one is NULL on all 203 Indiana rows. Two copies of one thing, and the
    populated one is the abbreviation.
 3. **`operator` IS THE SHIPPER, NOT THE PIPELINE.** It reads 'Ardagh Glass Inc.' - the customer at
    that delivery point. The pipeline is in `pipeline`. Joining the map's pipeline features on
    `operator` would match nothing and quietly report no capacity anywhere.
 4. **`requested_gas_day` MIXES a date with the literal string `'current'`.** Only the `'current'`
    rows are the live snapshot; the dated rows are history and summing all of them multiplies the
    state's free capacity by the number of days captured.

⚠ COVERAGE IS 2 PIPELINES OF 12 ON THE MAP - 34 of 213 drawn segments. The other 179 get an
explicit "no capacity feed captured for this pipeline", never a blank. A pipeline with no number
beside it must not read as a pipeline with no capacity.

⚠ THE MW FIGURE IS OURS, NOT THEIRS, and is badged wherever it renders. Unit is INFERRED: the
capture kept no units column, but the magnitudes match dekatherms/day and 1 Dth = 1 MMBtu, so at a
6.5 MMBtu/MWh combined-cycle heat rate, MW = Dth/day / 24 / 6.5 = Dth/day / 156. That is the same
divisor `market.html` already discloses, deliberately, so the two surfaces cannot disagree.

⛔ NO GEOMETRY. These rows carry a location NAME and a county, never a coordinate, so they are
attached to the pipeline the reader clicked - they are NOT plotted as points. Inventing a point for
"INDIANA GAS, MADISON" would be a centroid, which this project bans outright.

READS indiana_app ONLY.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import json
import gzip
import os
import re
import datetime
from google.cloud import bigquery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DS = "energy-platfrom.indiana_app"
DTH_PER_MW_DAY = 156        # 24 h x 6.5 MMBtu/MWh -- same divisor as market.html
SOURCES = ["in_gas_capacity_panhandle_eastern", "in_gas_capacity_trunkline"]
client = bigquery.Client(project="energy-platfrom")


def pipe_key(name):
    """Normalise a pipeline name so the map's 'Panhandle Eastern Pipe Line Co.' meets the feed's
    'Panhandle Eastern Pipe Line Company, LP'. ⚠ Corporate suffixes only -- nothing that could
    merge two DIFFERENT pipelines."""
    s = (name or "").lower()
    s = re.sub(r"[.,]", " ", s)
    s = re.sub(r"\b(company|companies|co|corporation|corp|llc|lp|l p|inc|the)\b", " ", s)
    s = re.sub(r"\bpipe line\b", "pipeline", s)
    return re.sub(r"\s+", " ", s).strip()


def _selftest():
    assert pipe_key("Panhandle Eastern Pipe Line Co.") == pipe_key(
        "Panhandle Eastern Pipe Line Company, LP"), pipe_key("Panhandle Eastern Pipe Line Co.")
    assert pipe_key("Trunkline Gas Co.") == pipe_key("Trunkline Gas Company, LLC")
    # ⛔ must NOT collapse two different pipelines
    assert pipe_key("Texas Gas Transmission Co.") != pipe_key("Texas Eastern Transmission Co.")


_selftest()

by_pipe = {}
for tbl in SOURCES:
    q = f"""
      SELECT TRIM(pipeline) AS pipeline, TRIM(loc_name) AS loc_name, TRIM(county) AS county,
             TRIM(loc_purp_desc) AS purpose, TRIM(loc_zn) AS zone,
             SAFE_CAST(TRIM(oac) AS INT64) AS free_dth,
             SAFE_CAST(TRIM(dc)  AS INT64) AS design_dth,
             SAFE_CAST(TRIM(opc) AS INT64) AS operating_dth,
             SAFE_CAST(TRIM(tsq) AS INT64) AS scheduled_dth,
             TRIM(operator) AS shipper, MAX(TRIM(pulled_at)) OVER () AS pulled_at
      FROM `{DS}.{tbl}`
      WHERE TRIM(UPPER(state)) = 'IN'
        AND TRIM(requested_gas_day) = 'current'   -- the live snapshot only; dated rows are history
      ORDER BY free_dth DESC"""
    n = 0
    for r in client.query(q):
        k = pipe_key(r.pipeline)
        e = by_pipe.setdefault(k, {"pipeline_name": r.pipeline, "locations": [],
                                   "pulled_at": r.pulled_at, "source_table": tbl})
        e["locations"].append({
            "name": r.loc_name, "county": r.county, "purpose": r.purpose, "zone": r.zone,
            "free_dth": r.free_dth, "design_dth": r.design_dth,
            "operating_dth": r.operating_dth, "scheduled_dth": r.scheduled_dth,
            "shipper": r.shipper,
        })
        n += 1
    print(f"  {tbl:38s} {n:3d} Indiana locations on the current gas day")

for k, e in by_pipe.items():
    free = [x["free_dth"] for x in e["locations"] if x["free_dth"] is not None]
    e["n_locations"] = len(e["locations"])
    e["total_free_dth"] = sum(free) if free else None
    e["max_free_dth"] = max(free) if free else None
    # ⚠ OURS, not the publisher's. Badged wherever it renders.
    e["total_free_mw_est"] = round(sum(free) / DTH_PER_MW_DAY) if free else None
    e["max_free_mw_est"] = round(max(free) / DTH_PER_MW_DAY) if free else None
    e["locations"].sort(key=lambda x: -(x["free_dth"] or 0))

payload = {
    "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "dth_per_mw_day": DTH_PER_MW_DAY,
    "by_pipeline": by_pipe,
    "coverage_note": ("Operationally-available capacity is captured for TWO pipelines only "
                      "(Panhandle Eastern and Trunkline, both Energy Transfer iPost boards). "
                      "Every other pipeline on the map has NO capacity feed captured — that is an "
                      "absence of measurement, not a measurement of zero."),
    "unit_note": ("The boards post no units column. Magnitudes match dekatherms/day and 1 Dth = "
                  "1 MMBtu, so the unit is INFERRED. MW is OUR estimate at a 6.5 MMBtu/MWh "
                  "combined-cycle heat rate: MW = Dth/day / 156."),
    "geometry_note": ("These locations carry a NAME and a county, never a coordinate, so they are "
                      "shown against the pipeline you clicked and are not plotted as points."),
}

out = os.path.join(REPO, "data", "gas_capacity.json.gz")
with gzip.open(out, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(payload, f, separators=(",", ":"))

tot = sum(e["total_free_dth"] or 0 for e in by_pipe.values())
print(f"\n  pipelines with a feed : {len(by_pipe)}")
print(f"  Indiana locations     : {sum(e['n_locations'] for e in by_pipe.values())}")
print(f"  total free            : {tot:,} Dth/day  (~{round(tot / DTH_PER_MW_DAY):,} MW estimated)")
print(f"  size                  : {os.path.getsize(out):,} bytes")
for k, e in by_pipe.items():
    print(f"    {e['pipeline_name'][:44]:46s} {e['n_locations']:3d} locs  "
          f"{e['total_free_dth']:>10,} Dth/d  ~{e['total_free_mw_est']:>6,} MW")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'data/gas_capacity.json.gz',
 'indiana_app.in_gas_capacity_panhandle_eastern + in_gas_capacity_trunkline (Energy Transfer iPost)',
 'TRIM(state)=IN and TRIM(requested_gas_day)=current only; capacity read from `oac` (the '
 'long-form operationally_available_capacity column is NULL on every Indiana row); keyed by '
 '`pipeline`, NOT `operator` (operator is the shipper at the delivery point); MW is a derived '
 'estimate at Dth/day/156 and is badged. '
 'RE-SCRAPE COMMAND: python scripts/export_gas_capacity.py',
 {sum(e['n_locations'] for e in by_pipe.values())}, 0.0, CURRENT_TIMESTAMP(),
 'G92. The gas pipeline popup previously showed operator and type only. Coverage is 2 of the 12 '
 'pipelines drawn (34 of 213 segments); the other 179 render an explicit no-feed-captured line '
 'rather than a blank, because a missing number must not read as zero capacity.'
)""").result()
print("  _registry row written")
print("GAS CAPACITY EXPORT COMPLETE")
