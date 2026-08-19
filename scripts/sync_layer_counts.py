"""Re-state every layer checkbox's count FROM THE SHIPPED PAYLOAD.

    python scripts/sync_layer_counts.py --check     fail if any label disagrees
    python scripts/sync_layer_counts.py             rewrite the labels

G65 put a feature count in each map-layer label so a reader can see how much is behind a toggle.
G43 then clipped those payloads at the Indiana border and moved most of them -- PJM candidate
buses went 229 -> 42, because 82% of our AEP harvest is in Ohio, West Virginia, Virginia,
Kentucky and Michigan.

A hand-typed count is correct exactly once. This reads the count out of the payload the browser
actually downloads, so the label cannot drift from what is drawn. Run it after any export or clip,
and in --check mode it is a standing guard.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import argparse
import collections
import gzip
import io
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# checkbox id -> (payload, the `layer` value(s) it draws). One entry per control in LAYER_MAP that
# carries a count in its label; controls whose count is meaningless (parcels, screener) are absent.
COUNTED = {
    "L-log-rail":   ("logistics.geojson.gz", ["rail"]),
    "L-log-road1":  ("logistics.geojson.gz", ["road1"]),
    "L-log-road2":  ("logistics.geojson.gz", ["road2"]),
    "L-pjm-queue":  ("pjm.geojson.gz", ["queue_point"]),
    "L-pjm-bus":    ("pjm.geojson.gz", ["bus_candidate"]),
    "L-gas-pipe":   ("gas.geojson.gz", ["gas"]),
    "L-gas-comp":   ("gas.geojson.gz", ["compressor"]),
    "L-gas-stor":   ("gas.geojson.gz", ["storage"]),
    # G72 land-status and airspace gates
    "L-mil":        ("gates.geojson.gz", ["military"]),
    "L-tribal":     ("gates.geojson.gz", ["tribal"]),
    "L-sua":        ("gates.geojson.gz", ["sua"]),
    "L-obst":       ("gates.geojson.gz", ["obstacle"]),
    "L-fac-plant":  ("facilities.geojson.gz", ["plant", "plant_hifld"]),
    "L-fac-solar":  ("facilities.geojson.gz", ["solar"]),
    "L-fac-wind":   ("facilities.geojson.gz", ["wind"]),
}
BONUS = {"L-bonus-lit": "low_income_tract", "L-bonus-qct": "qct", "L-bonus-coal": "coal_closure",
         "L-bonus-oz": "opportunity_zone", "L-bonus-ec": "energy_community",
         "L-bonus-hab": "critical_habitat"}

cache = {}


def counts(payload):
    if payload not in cache:
        p = os.path.join(REPO, "data", payload)
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            fc = json.load(fh)
        cache[payload] = fc["features"]
    return cache[payload]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    want = {}
    for box, (payload, kinds) in COUNTED.items():
        c = collections.Counter((f["properties"] or {}).get("layer") for f in counts(payload))
        want[box] = sum(c[k] for k in kinds)
    bk = collections.Counter((f["properties"] or {}).get("kind")
                             for f in counts("overlays.geojson.gz")
                             if (f["properties"] or {}).get("layer") == "bonus")
    for box, kind in BONUS.items():
        want[box] = bk[kind]

    p = os.path.join(REPO, "index.html")
    s = io.open(p, encoding="utf-8").read()
    drift, fixed = [], 0
    for box, n in sorted(want.items()):
        # the count is the FIRST number inside the label's hint span
        m = re.search(r'(id="' + re.escape(box) + r'"[\s\S]{0,220}?<span class="hint">\()([\d,]+)', s)
        if not m:
            drift.append(f"{box}: no count in its label (expected {n:,})")
            continue
        shown = int(m.group(2).replace(",", ""))
        if shown == n:
            continue
        drift.append(f"{box}: label says {shown:,}, payload holds {n:,}")
        if not a.check:
            s = s[:m.start(2)] + f"{n:,}" + s[m.end(2):]
            fixed += 1

    if a.check:
        for d in drift:
            print("  DRIFT " + d)
        print(f"\n{len(drift)} label(s) disagree with the payload"
              if drift else "\nevery layer label matches its payload")
        _sys.exit(1 if drift else 0)

    io.open(p, "w", encoding="utf-8", newline="").write(s)
    for d in drift:
        print("  " + d)
    print(f"\n{fixed} label(s) rewritten from the shipped payloads")


if __name__ == "__main__":
    main()
