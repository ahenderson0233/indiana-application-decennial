"""G130 export: data/planned.geojson.gz — planned upgrades, their corridors and their rings.

Operator, 2026-08-20f: *"these upgrades or new developments should NOT display the same as the
current grid assets."*

THREE FEATURE KINDS, so the map can draw planned work as planned work:

  kind="ring"      a polygon showing where the asset COULD be. Radius comes from `uncertainty_mi`,
                   which is keyed on HOW WELL WE KNOW THE LOCATION and never on project status.
                   Drawn first so it sits under everything.
  kind="corridor"  a LineString between two resolved endpoints - a line rebuild between two named
                   substations, where drawing a dot at the midpoint would put the work miles from
                   where it actually is.
                   ⚠ THE COUNT IS PRINTED, NEVER TYPED HERE. An earlier version of this docstring
                   named a figure ("81") that the build's own summary then contradicted with 133,
                   because the build counted `end_a_lat IS NOT NULL` while a line needs BOTH ends.
                   A number hand-typed into a comment is a number that will disagree with the code
                   beside it.
  kind="point"     the representative point.

⭐ 2026-08-21 - THE PAYLOAD NOW CARRIES WHAT G130 ITEMS 1-3 ADDED: `mw` (the MW a MISO DPP-2025
interconnection would enable), `cost_zone` / `cost_zones` (which PJM zone bears the cost, on the
26 upgrades PJM publishes an allocation for), and `refused` (why a placement was withheld). ⛔ A
refused row is NOT in this file at all - it has no coordinate - but the reason is on the table so
the coverage figure reconciles.

⛔ THE RINGS ARE GENERATED HERE, NOT IN THE BROWSER. A MapLibre `circle` radius is in PIXELS, so a
5-mile uncertainty would shrink as the reader zooms in - the ring would tell a different story at
every zoom level, and it would be smallest exactly when the reader is looking hardest. A geodesic
polygon is the same ground distance at every zoom.

⚠ READS indiana_app ONLY. Builds may read energy; exports may not.

RE-SCRAPE COMMAND: python scripts/export_planned_upgrades.py
⚠ IDEMPOTENT: replace_safe - it writes one file from one query.
"""
import gzip
import json
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DS = "energy-platfrom.indiana_app"
OUT = os.path.join(REPO, "data", "planned.geojson.gz")
RING_VERTICES = 48          # smooth enough at any zoom, cheap enough to ship

client = bigquery.Client(project="energy-platfrom")


def ring(lat, lon, miles, n=RING_VERTICES):
    """A geodesic-ish circle as a GeoJSON ring. Good to a few metres at Indiana latitudes."""
    d = miles / 3958.7613                                  # angular distance, earth radii
    la, lo = math.radians(lat), math.radians(lon)
    out = []
    for i in range(n + 1):
        b = 2 * math.pi * i / n
        la2 = math.asin(math.sin(la) * math.cos(d) + math.cos(la) * math.sin(d) * math.cos(b))
        lo2 = lo + math.atan2(math.sin(b) * math.sin(d) * math.cos(la),
                              math.cos(d) - math.sin(la) * math.sin(la2))
        out.append([round(math.degrees(lo2), 5), round(math.degrees(la2), 5)])
    return out


rows = list(client.query(f"""
  SELECT source, project_id, title, description, driver, project_type, location_text, owner,
         status_raw, status_class, in_service_date, actual_in_service_date,
         ROUND(cost_usd_m, 2) AS cost_usd_m,
         ROUND(mw_enabled) AS mw_enabled,
         alloc_top_zone, alloc_top_pct, alloc_n_zones, alloc_top5,
         county_name, anchor_name,
         loc_method, loc_basis, ROUND(uncertainty_mi, 1) AS uncertainty_mi,
         ROUND(lat, 6) AS lat, ROUND(lon, 6) AS lon,
         ROUND(end_a_lat, 6) AS a_lat, ROUND(end_a_lon, 6) AS a_lon,
         ROUND(end_b_lat, 6) AS b_lat, ROUND(end_b_lon, 6) AS b_lon
  FROM `{DS}.in_planned_upgrades`
  WHERE lat IS NOT NULL AND lon IS NOT NULL
  ORDER BY source, project_id"""))
print(f"{len(rows):,} placed planned items")

feats, n_ring, n_cor = [], 0, 0
for r in rows:
    p = {
        "layer": "planned",
        "src": r.source, "pid": r.project_id, "title": r.title,
        "descr": r.description,
        "driver": r.driver, "ptype": r.project_type, "loc_text": r.location_text,
        "owner": r.owner, "status_raw": r.status_raw, "status": r.status_class,
        "isd": r.in_service_date, "aisd": r.actual_in_service_date,
        "cost_m": r.cost_usd_m, "county": r.county_name, "anchor": r.anchor_name,
        "loc_method": r.loc_method, "loc_basis": r.loc_basis, "unc_mi": r.uncertainty_mi,
        # ⭐ G130 items 1-2. `mw` only exists on the MISO DPP-2025 rows and `cost_zone` only on
        # the 26 PJM upgrades that publish an allocation - both stay absent elsewhere rather than
        # rendering as a zero, because unpublished is NULL and never 0.
        "mw": r.mw_enabled,
        "cost_zone": r.alloc_top_zone, "cost_zone_pct": r.alloc_top_pct,
        "cost_n_zones": r.alloc_n_zones, "cost_zones": r.alloc_top5,
    }
    p = {k: v for k, v in p.items() if v is not None}

    if r.uncertainty_mi and r.uncertainty_mi > 0:
        feats.append({"type": "Feature",
                      "properties": {**p, "kind": "ring"},
                      "geometry": {"type": "Polygon",
                                   "coordinates": [ring(r.lat, r.lon, r.uncertainty_mi)]}})
        n_ring += 1
    if r.a_lat is not None and r.b_lat is not None:
        feats.append({"type": "Feature",
                      "properties": {**p, "kind": "corridor"},
                      "geometry": {"type": "LineString",
                                   "coordinates": [[r.a_lon, r.a_lat], [r.b_lon, r.b_lat]]}})
        n_cor += 1
    feats.append({"type": "Feature",
                  "properties": {**p, "kind": "point"},
                  "geometry": {"type": "Point", "coordinates": [r.lon, r.lat]}})

fc = {"type": "FeatureCollection", "features": feats}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with gzip.open(OUT, "wt", encoding="utf-8") as fh:
    json.dump(fc, fh, separators=(",", ":"))
print(f"  data/planned.geojson.gz — {len(feats):,} features "
      f"({len(rows):,} points, {n_cor:,} corridors, {n_ring:,} rings), "
      f"{os.path.getsize(OUT) // 1024} KB")

# what the reader will be able to filter on, and the honest denominator
tot = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_planned_upgrades`"))[0].n
print(f"\n  ⚠ CAP DISCLOSURE for the page: {len(rows):,} of {tot:,} planned items carry a "
      f"position. The other {tot - len(rows):,} are held and reported, never drawn.")
for r in client.query(f"""
  SELECT status_class, COUNT(*) n, COUNTIF(lat IS NOT NULL) placed
  FROM `{DS}.in_planned_upgrades` GROUP BY 1 ORDER BY 2 DESC"""):
    print(f"    {r.status_class:14} {r.placed:>5,} placed of {r.n:>5,}")

# ⭐ THE SECOND DENOMINATOR, and it is the one a siter actually wants. Operator ruling
# 2026-08-21: already-built work is carried and defaults OFF, so a coverage figure that mixes it
# in understates how well we can place the things that have not happened yet.
f = list(client.query(f"""
  SELECT COUNTIF(status_class IN ('proposed','approved','filed_plan')) fut,
         COUNTIF(lat IS NOT NULL AND status_class IN ('proposed','approved','filed_plan')) fp,
         COUNTIF(status_class = 'in_service') built,
         COUNTIF(lat IS NOT NULL AND status_class = 'in_service') builtp
  FROM `{DS}.in_planned_upgrades`"""))[0]
print(f"\n  ⭐ STILL TO COME: {f.fp:,} of {f.fut:,} placed ({100 * f.fp / f.fut:.1f}%) — "
      f"the figure the grid page must lead with")
print(f"  ⚠ ALREADY BUILT: {f.builtp:,} of {f.built:,} placed — carried, and OFF by default")

# ⛔ THE BORDER, RE-ASSERTED ON THE PAYLOAD ITSELF. The build asserts it on the table; this
# asserts it on the file that actually ships, because those are two different artefacts and G43
# exists because a payload once disagreed with its table.
out_of_box = [ft for ft in feats if ft["geometry"]["type"] == "Point"
              and not (37.7 <= ft["geometry"]["coordinates"][1] <= 41.8
                       and -88.2 <= ft["geometry"]["coordinates"][0] <= -84.7)]
assert not out_of_box, f"{len(out_of_box)} exported point(s) outside the Indiana box"
print(f"  ⭐ 0 of {len(rows):,} exported points fall outside the Indiana box")
print("PLANNED UPGRADES EXPORT COMPLETE")
