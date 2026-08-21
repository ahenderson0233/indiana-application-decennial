"""G130 export: data/planned.geojson.gz — planned upgrades, their corridors and their rings.

Operator, 2026-08-20f: *"these upgrades or new developments should NOT display the same as the
current grid assets."*

THREE FEATURE KINDS, so the map can draw planned work as planned work:

  kind="ring"      a polygon showing where the asset COULD be. Radius comes from `uncertainty_mi`,
                   which is keyed on HOW WELL WE KNOW THE LOCATION and never on project status.
                   Drawn first so it sits under everything.
  kind="corridor"  a LineString between two resolved endpoints. 81 upgrades are a line rebuild
                   between two named substations, and drawing those as a dot at the midpoint
                   would put the work up to 13 miles from where it actually is.
                   ⚠ 81, not 133 - the build's summary briefly claimed 133 because it counted
                   `end_a_lat IS NOT NULL` while a line needs BOTH ends. The export could only
                   draw 81, and a build contradicting its own export is the two-instruments
                   defect in miniature.
  kind="point"     the representative point.

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
         ROUND(cost_usd_m, 2) AS cost_usd_m, county_name, anchor_name,
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
print("PLANNED UPGRADES EXPORT COMPLETE")
