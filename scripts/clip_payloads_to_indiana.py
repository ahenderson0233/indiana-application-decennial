"""G43 - clip the DRAWN map layers at the Indiana border.

    python scripts/clip_payloads_to_indiana.py --dry-run     measure, write nothing
    python scripts/clip_payloads_to_indiana.py               clip and rewrite the payloads

Operator, 2026-08-18: *"many of the layers are not properly clipped at the Indiana border, and
this is necessary for aesthetic purposes."*

Measured before this ran: 427 of 10,659 grid features, 34 overlays, 18 logistics, 14 gas, 13
facilities and 8 water features reach outside the state. It reads as sloppy, and worse it implies
coverage we have neither got nor checked -- a line drawn into Ohio suggests we know something
about Ohio.

⛔ WHY THIS CLIPS THE PAYLOAD AND NOT THE WAREHOUSE. The backlog's own warning is that clipping
geometry and then measuring to the cut end would silently overstate distance to every cross-border
asset -- G29 reintroduced from the other direction. That is avoided here by construction:

  * distances for HELD parcels are computed in BigQuery against the FULL geometry
    (`in_asset_distance_parcel`, exact ST_DISTANCE) and shipped as columns. Nothing in this script
    touches that table, so no held-parcel distance can move.
  * these payloads are the DRAWING layer only.
  * every feature this script cuts is stamped `_clipped: true`, so any future consumer can tell a
    drawn end from a real one instead of having to know.

⚠ THE ONE RESIDUAL, stated rather than buried: uploaded CSV rows fall back to a client-side
distance against the drawn geometry (`repPt`). For an uploaded site within a few miles of the
state line, the nearest cross-border asset is now measured to the cut end. That is a real (small)
bias, it is confined to uploads, and `_clipped` is on the feature so the fallback can be taught to
say so. Recorded here because a limit nobody wrote down is a limit nobody will find.

⚠ POINTS are dropped, not cut -- a point is in or out. Lines and polygons are intersected.
Anything that becomes empty is dropped and COUNTED, never silently discarded.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import argparse
import gzip
import io
import json
import os

from google.cloud import bigquery
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from shapely.validation import make_valid

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")

# Every payload the map DRAWS. county/site files are already Indiana-only by construction.
LAYERS = ["grid.geojson.gz", "overlays.geojson.gz", "logistics.geojson.gz",
          "gas.geojson.gz", "water.geojson.gz", "facilities.geojson.gz",
          "pjm.geojson.gz", "territories.geojson.gz", "context.geojson.gz",
          # G72. Built already-clipped (in_land_gates intersects the state boundary in SQL), but it
          # is listed here anyway: a payload that is clipped by CONSTRUCTION is one refactor away
          # from not being, and remembering an ordering rule is not a control.
          "gates.geojson.gz"]


def indiana():
    """The state polygon, from the publisher -- never a bounding box.

    A bbox would keep a chunk of Illinois and Kentucky and cut the Ohio River wrong; the border is
    a river for most of its southern length.
    """
    c = bigquery.Client(project="energy-platfrom")
    rows = list(c.query("""
        SELECT ST_ASGEOJSON(geom) g FROM `energy-platfrom.energy.state_boundaries`
        WHERE UPPER(stusps) = 'IN' """))
    if not rows:
        raise SystemExit("no Indiana row in energy.state_boundaries -- refusing to guess a boundary")
    geom = unary_union([make_valid(shape(json.loads(r.g))) for r in rows])
    print(f"Indiana boundary: {geom.geom_type}, area {geom.area:.3f} deg^2, "
          f"bounds {tuple(round(b, 3) for b in geom.bounds)}")
    return geom


def clip_file(name, IN, dry):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        print(f"  {name:26s} (absent)")
        return None
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        fc = json.load(fh)

    kept, cut, dropped = [], 0, 0
    for ft in fc.get("features", []):
        g = ft.get("geometry")
        if not g:
            kept.append(ft)
            continue
        try:
            geom = make_valid(shape(g))
        except Exception:
            kept.append(ft)          # unparseable: keep it rather than silently lose it
            continue
        if IN.contains(geom):
            kept.append(ft)
            continue
        if not IN.intersects(geom):
            dropped += 1             # wholly outside the state
            continue
        if geom.geom_type in ("Point", "MultiPoint"):
            dropped += 1             # a point is in or out; cutting one is meaningless
            continue
        try:
            piece = IN.intersection(geom)
        except Exception:
            kept.append(ft)
            continue
        if piece.is_empty:
            dropped += 1
            continue
        ft = dict(ft)
        ft["geometry"] = mapping(piece)
        props = dict(ft.get("properties") or {})
        props["_clipped"] = True     # drawn end != real end; say so on the feature
        ft["properties"] = props
        kept.append(ft)
        cut += 1

    before = len(fc.get("features", []))
    print(f"  {name:26s} {before:>6,} -> {len(kept):>6,}   clipped {cut:>4,}   "
          f"dropped {dropped:>4,} (wholly outside)")
    if dry:
        return (before, len(kept), cut, dropped)
    fc["features"] = kept
    fc["_clipped_to"] = "Indiana (energy.state_boundaries), drawing only"
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
        json.dump(fc, fh, separators=(",", ":"))
    os.replace(tmp, path)
    return (before, len(kept), cut, dropped)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    IN = indiana()
    print(f"\n{'DRY RUN - nothing written' if a.dry_run else 'CLIPPING'}\n")
    tot = [0, 0, 0, 0]
    for name in LAYERS:
        r = clip_file(name, IN, a.dry_run)
        if r:
            tot = [t + x for t, x in zip(tot, r)]
    print(f"\n  {'TOTAL':26s} {tot[0]:>6,} -> {tot[1]:>6,}   clipped {tot[2]:>4,}   dropped {tot[3]:>4,}")
    if not a.dry_run:
        print("\n⚠ Re-stamp assets and re-run the checkpoint: the payload freshness guard compares "
              "each file against the tables behind it.")


if __name__ == "__main__":
    main()
