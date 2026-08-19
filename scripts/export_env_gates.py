"""G110 - ship the flood and wetland GEOMETRY, so a gate you can filter on is a gate you can SEE.

    python scripts/export_env_gates.py

Operator, 2026-08-19: *"The flood zones, wetlands, and the protected land should also show the map
layer when checked, not just used as a filtering tool."*

⭐ THE OPERATOR IS RIGHT AND IT WAS WORSE THAN "NOT SHOWN": `LAYER_MAP` held **no flood layer and
no wetland layer at all**. A reader could exclude every parcel touching a floodplain and had no way
to see the floodplain. Protected land was the near-miss - `L-padus` draws, but from a different
control than the `f-noprot` filter, so ticking the filter revealed nothing.

⚠ THE OLD REFUSAL WAS HONEST AND IS NOW OUT OF DATE. `index.html` carried a hint saying the source
layers are "804 MB and 1.3 GB - far too large to send to a browser". Both figures are correct
(`in_flood` 803.8 MB / 66,140 rows; `in_wetlands` 1,319.6 MB / 453,995 rows). What was never tested
is whether the DECISION-RELEVANT SUBSET is too large. It is not, by two orders of magnitude:

    flood, SFHA only, ST_SIMPLIFY 60 m   25,421 polygons   346.3 MB raw -> 10.4 MB
    wetlands >= 20 acres, same tolerance  9,769 polygons                ->  9.0 MB

⛔ TWO DELIBERATE CUTS, AND BOTH ARE DISCLOSED ON THE CONTROL ITSELF, because a silent subset is
the G58 defect - the `.slice(0, 14)` that showed 14 of 432 qualifying rows and looked complete.

  1. FLOOD IS SFHA ONLY. `SFHA_TF='T'` keeps 25,421 of 66,140. The 40,708 dropped are `FLD_ZONE='X'`
     - land the FEMA study examined and found OUTSIDE the 1% floodplain. Drawing "not a hazard" as
     a hazard-layer polygon would invert the meaning of the layer.
  2. WETLANDS ARE >= 20 ACRES. 9,769 of 453,995, which is 2.2%. ⚠ THIS IS THE ONE THAT NEEDS
     SAYING OUT LOUD: a 0.4-acre wetland still triggers Clean Water Act §404 permitting, so the cut
     is a RENDERING limit, not a statement that small wetlands do not matter. The per-parcel
     `wetland_on_parcel` FILTER is unaffected and still measured against all 453,995.

⭐ SIMPLIFICATION IS A LIE UNLESS IT IS BOUNDED. 60 m means a drawn boundary can sit ~60 m from the
true one - fine for "is my site near a floodplain", useless for "does this corner of my parcel sit
inside it". The parcel-level flag answers the second question and the popup says so.

Fetched on FIRST TOGGLE, never at boot - the same rule as the context layers.
⛔ READS indiana_app ONLY (an export may not read `energy`).
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import json
import gzip
import os
import datetime
from google.cloud import bigquery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DS = "energy-platfrom.indiana_app"
TOL_M = 60           # simplification tolerance, metres -- stated on the control
WET_MIN_ACRES = 20   # the disclosed cut
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
WITH flood AS (
  SELECT 'flood' AS layer,
         FLD_ZONE AS zone,
         ZONE_SUBTY AS zone_subtype,
         SFHA_TF AS sfha,
         STATIC_BFE AS bfe,
         src_county AS county,
         CAST(NULL AS STRING) AS wetland_type,
         CAST(NULL AS FLOAT64) AS acres,
         ST_SIMPLIFY(geog, {TOL_M}) AS g
  FROM `{DS}.in_flood`
  WHERE SFHA_TF = 'T'
),
wet AS (
  SELECT 'wetland' AS layer,
         CAST(NULL AS STRING) AS zone,
         CAST(NULL AS STRING) AS zone_subtype,
         CAST(NULL AS STRING) AS sfha,
         CAST(NULL AS STRING) AS bfe,
         CAST(NULL AS STRING) AS county,
         WETLAND_TYPE AS wetland_type,
         ROUND(SAFE_CAST(ACRES AS FLOAT64), 1) AS acres,
         ST_SIMPLIFY(geog, {TOL_M}) AS g
  FROM `{DS}.in_wetlands`
  WHERE SAFE_CAST(ACRES AS FLOAT64) >= {WET_MIN_ACRES}
)
SELECT layer, zone, zone_subtype, sfha, bfe, county, wetland_type, acres,
       ST_ASGEOJSON(g) AS gj
FROM (SELECT * FROM flood UNION ALL SELECT * FROM wet)
WHERE g IS NOT NULL AND NOT ST_ISEMPTY(g)
"""

print(f"querying flood (SFHA only) + wetlands (>= {WET_MIN_ACRES} acres), simplified {TOL_M} m ...")
job = client.query(SQL)
rows = list(job.result())
gb = round((job.total_bytes_processed or 0) / 1e9, 3)
print(f"  {len(rows):,} polygons, {gb} GB scanned")

feats, n_flood, n_wet = [], 0, 0
for r in rows:
    props = {"layer": r.layer}
    if r.layer == "flood":
        n_flood += 1
        props.update({k: v for k, v in
                      (("zone", r.zone), ("zone_subtype", r.zone_subtype),
                       ("bfe", r.bfe), ("county", r.county)) if v not in (None, "")})
    else:
        n_wet += 1
        props.update({k: v for k, v in
                      (("wetland_type", r.wetland_type), ("acres", r.acres)) if v is not None})
    feats.append({"type": "Feature", "properties": props, "geometry": json.loads(r.gj)})

payload = {
    "type": "FeatureCollection",
    "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    # ⭐ The disclosure travels WITH the data, so a surface cannot render this and forget to say
    # what was left out. The control reads these strings; it does not restate them.
    "coverage": {
        "flood": {
            "drawn": n_flood, "source_rows": 66140,
            "rule": "Special Flood Hazard Area only (SFHA_TF='T')",
            "excluded": "40,708 Zone X polygons - land the FEMA study examined and found OUTSIDE "
                        "the 1% annual-chance floodplain. Absence of a polygon here is NOT "
                        "evidence the site is unstudied.",
        },
        "wetland": {
            "drawn": n_wet, "source_rows": 453995,
            "rule": f"NWI polygons of {WET_MIN_ACRES} acres or more",
            "excluded": f"444,226 wetlands under {WET_MIN_ACRES} acres, 97.8% of the corpus. "
                        "A rendering limit, NOT a judgement: a 0.4-acre wetland still triggers "
                        "Clean Water Act section 404 permitting. The per-parcel wetland filter is "
                        "measured against all 453,995 and is unaffected by this cut.",
        },
        "simplify_m": TOL_M,
        "precision_note": f"Boundaries are simplified to {TOL_M} m, so a drawn edge can sit about "
                          f"{TOL_M} m from the surveyed one. Use this layer to see WHERE the "
                          f"constraint is; use the per-parcel flag to decide whether a specific "
                          f"site is affected.",
    },
    "features": feats,
}

out = os.path.join(REPO, "data", "envgates.geojson.gz")
with gzip.open(out, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(payload, f, separators=(",", ":"))

print(f"  flood polygons  : {n_flood:,} of 66,140 source rows (SFHA only)")
print(f"  wetland polygons: {n_wet:,} of 453,995 source rows (>= {WET_MIN_ACRES} acres)")
print(f"  size            : {os.path.getsize(out):,} bytes gzipped")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'data/envgates.geojson.gz',
 'indiana_app.in_flood (FEMA NFHL) + indiana_app.in_wetlands (USFWS NWI)',
 'flood filtered to SFHA_TF=T; wetlands filtered to ACRES >= {WET_MIN_ACRES}; both '
 'ST_SIMPLIFY(geog, {TOL_M}) then ST_ASGEOJSON; fetched on first toggle, not at boot. '
 'RE-SCRAPE COMMAND: python scripts/export_env_gates.py',
 {len(feats)}, {gb}, CURRENT_TIMESTAMP(),
 'G110. Makes a filterable gate VISIBLE - previously LAYER_MAP had no flood or wetland layer at '
 'all. Two cuts, both disclosed in the payloads own coverage block and printed on the control: '
 'Zone X excluded (not a hazard), wetlands under {WET_MIN_ACRES} acres excluded (rendering limit '
 'only - the per-parcel filter still uses all 453,995).'
)""").result()
print("  _registry row written")
print("ENV GATE LAYER EXPORT COMPLETE")
