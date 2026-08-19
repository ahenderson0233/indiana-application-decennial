"""G114 (non-scraping half) - recover more PJM bus locations from substations we ALREADY hold.

    python scripts/build_pjm_bus_locations_v2.py

Operator, 2026-08-19: *"We definitely lost some bus locations just below northeastern Indiana, and,
ideally, ALL bus locations should be plottable ... we should get fairly close to Orennia with our
bus placement, using them as a yardstick."*

⭐ THE OPERATOR SAW A REAL HOLE AND IT IS BIGGER THAN "SOME". Measured in `in_bus_capacity_tier0`:
PJM is located on **223 of 1,814 injection rows and 227 of 1,826 withdrawal - 12.3%** - and only
**40 / 42 of those sit inside Indiana**. MISO is the opposite: 1,731 of 1,731. North-east Indiana
is the AEP footprint, AEP is PJM, and PJM is exactly where we have almost no coordinates.

⛔ THE EXISTING MATCHER HAD ALREADY EXTRACTED EVERYTHING IT COULD, so this is not a wiring fix:
`in_pjm_bus_locations_candidate` holds 1,475 buses of which only 229 carry a point, and tier0
already uses 227 of them. **Buses gainable by joining the existing table differently: ZERO.**
1,246 rows are `location_method='none'`.

⭐ WHAT IS ACTUALLY RECOVERABLE is a better NAME MATCH. PJM's bus labels are PSS/E names - a
leading area code, a truncated station name, a voltage: `05FALL C 345 kV (243222)`. Stripping the
area code and the voltage and matching the remainder against our substation corpus finds 64
unambiguous name matches, of which **54 survive the guards and are placed** (28 exact, 26 prefix):

    05FALL C      -> FALL CREEK        05DEQUIN     -> DEQUINE
    05THORNT      -> THORNTOWN         05NEW CARLI2 -> NEW CARLISLE
    05PENDLETON1  -> PENDLETON         05SPRING     -> SPRINGVILLE

**Result, measured after the rebuild: located PJM buses 229 -> 277, and INSIDE INDIANA 42 -> 93.**
In `in_bus_capacity_tier0` that is injection 223 -> 271 and withdrawal 227 -> 275, i.e. 12.3% ->
15.1%. 10 candidates were rejected because the bus voltage sits outside the matched substation's
kV range, and 8 more were ambiguous.

⚠ THIS SCRIPT AND tier0 READ EACH OTHER, so the counts move between runs and that is expected, not
a bug: the "unlocated" worklist comes from `in_bus_capacity_tier0`, which is itself built from this
table. Run order is therefore **this script, then `build_bus_capacity_tier0_v2.py`**, and a second
pass simply finds fewer buses left to place. It converges because a match is only ever ADDED.
⛔ Never read the printed "new matches" figure as the total improvement - re-measure the located
count on the rebuilt tier0, which is what the last line of this docstring quotes.

⚠ `kv_consistent` is THREE-STATE. TRUE = checked and consistent (29). NULL = the substation
publishes no kV range to check against (25). It is never FALSE, because a real mismatch is
rejected rather than stored. An earlier version wrote `bool(kv_ok)`, which turned "could not
check" into FALSE and would have read as "checked and INCONSISTENT" on 25 rows.

⛔ AMBIGUOUS MATCHES ARE NEVER PLACED. 8 bus names match two or more distinct substations, and a
bus in the wrong place is worse than a bus with no place - it is a coordinate a developer might
drive to. They are recorded with their collision count and left unlocated.

⚠ AND THE HONEST LIMIT OF THIS METHOD, stated because it bounds what the numbers mean: our
substation corpus is an INDIANA clip (2,077 of 3,010 rows carry a point, essentially all in
Indiana). PJM's case covers the whole AEP footprint across several states. So a bus whose true
home is an Ohio or Michigan station with the same name **could** be pulled onto an Indiana
substation. Two guards, and they are the reason this is `med` confidence and not `high`:
  * the match must be UNAMBIGUOUS within the corpus, and
  * the bus voltage must be CONSISTENT with the substation's kV range.
⛔ Do not promote these to `high` without an out-of-state substation corpus to disambiguate against.

⚠ THE VENDOR IS A YARDSTICK, NEVER A SOURCE. Their positions are not copied here, and 91.9% of
theirs are estimates anyway - so "close to Orennia" would mean close to an estimate.

WRITES `indiana_app.in_pjm_bus_locations_v2` (existing candidates kept verbatim + new matches).
Reads indiana_app only.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import re
import collections
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_pjm_bus_locations_v2"
client = bigquery.Client(project="energy-platfrom")


def busword(n):
    """PSS/E bus label -> the station name inside it. '05FALL C 345 kV (243222)' -> 'FALL C'."""
    s = re.sub(r"\(\d+\)", " ", str(n or ""))
    s = re.sub(r"\b\d+(\.\d+)?\s*kv\b", " ", s, flags=re.I)
    s = re.sub(r"^\s*\d+", "", s)                  # leading area code, e.g. the "05" on AEP buses
    s = re.sub(r"[^A-Za-z ]", " ", s)
    return re.sub(r"\s+", " ", s).strip().upper()


def subword(n):
    """Substation name -> comparable stem. Drops the generic nouns, never the identity."""
    s = re.sub(r"[^A-Za-z ]", " ", str(n or "")).upper()
    s = re.sub(r"\b(SUBSTATION|SUB|STATION|TAP|PLANT|SWITCHYARD|SWITCHING|ENERGY|POWER)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _selftest():
    assert busword("05FALL C 345 kV (243222)") == "FALL C", busword("05FALL C 345 kV (243222)")
    assert busword("AB1-006 MAIN 345 kV (270176)") == "AB MAIN", busword("AB1-006 MAIN 345 kV (270176)")
    assert busword("05NEW CARLI2 138 kV (243349)") == "NEW CARLI"
    assert subword("FALL CREEK SUBSTATION") == "FALL CREEK"
    assert subword("Thorntown Sub") == "THORNTOWN"
    # ⛔ the stem must never become so short it matches everything
    assert len(busword("05A 138 kV (1)")) < 4


_selftest()

existing = [dict(r) for r in client.query(f"""
    SELECT CAST(bus_number AS STRING) AS bus_number, bus_label, bus_kv, location_method,
           match_confidence, match_basis, lat, lon, matched_substation_name, matched_source,
           kv_consistent, collision_count
    FROM `{DS}.in_pjm_bus_locations_candidate`""")]
have = {e["bus_number"] for e in existing if e["lat"] is not None}
print(f"existing candidate table: {len(existing)} rows, {len(have)} already located")

todo = [dict(r) for r in client.query(f"""
    SELECT DISTINCT CAST(bus_id AS STRING) AS bus_number, bus_name, bus_voltage_kv
    FROM `{DS}.in_bus_capacity_tier0` WHERE iso='PJM' AND latitude IS NULL""")]
subs = [dict(r) for r in client.query(f"""
    SELECT substation_name, lat, lon, max_kv, min_kv, county, county_fips
    FROM `{DS}.in_substations_dedup` WHERE lat IS NOT NULL""")]
print(f"unlocated PJM buses: {len(todo)}   substations with a point: {len(subs)}")

sidx = collections.defaultdict(list)
for s in subs:
    w = subword(s["substation_name"])
    if len(w) >= 4:
        sidx[w].append(s)

new, ambiguous, kv_reject = [], 0, 0
for b in todo:
    if b["bus_number"] in have:
        continue
    w = busword(b["bus_name"])
    if len(w) < 4:
        continue
    method, hits = None, []
    if w in sidx:
        hits, method = sidx[w], "substation_name_exact_v2"
    elif len(w) >= 5:
        hits = [s for k, v in sidx.items() if k.startswith(w) or w.startswith(k) for s in v]
        method = "substation_name_prefix_v2"
    if not hits:
        continue
    uniq = {(h["substation_name"], round(h["lat"], 4), round(h["lon"], 4)) for h in hits}
    if len(uniq) != 1:
        ambiguous += 1
        continue
    s = hits[0]
    # ⚠ kV consistency is one of only two guards standing between this and a wrong coordinate.
    kv = b["bus_voltage_kv"]
    lo, hi = s.get("min_kv"), s.get("max_kv")
    kv_ok = None
    if kv is not None and lo is not None and hi is not None:
        kv_ok = (float(lo) - 1) <= float(kv) <= (float(hi) + 1)
    if kv_ok is False:
        kv_reject += 1
        continue
    new.append({
        "bus_number": b["bus_number"], "bus_label": b["bus_name"], "bus_kv": kv,
        "location_method": method, "match_confidence": "med",
        "match_basis": f"PSS/E label stem {w!r} matched substation {s['substation_name']!r}"
                       f" in {s.get('county') or 'unknown county'}; unambiguous in corpus"
                       f"{'; kV consistent' if kv_ok is True else '; substation publishes no kV range to check'}",
        "lat": s["lat"], "lon": s["lon"],
        "matched_substation_name": s["substation_name"],
        # ⚠ THREE STATES, NOT TWO. `bool(kv_ok)` collapsed "could not check" into False, which
        # reads as "checked and INCONSISTENT" - the exact G51 defect this project keeps fixing
        # elsewhere. NULL means the substation publishes no kV range to check against; False
        # never reaches here because a real mismatch is rejected above.
        "matched_source": "in_substations_dedup", "kv_consistent": kv_ok,
        "collision_count": 1,
    })

print(f"\n  NEW unambiguous matches : {len(new)}")
print(f"  ambiguous, NOT placed   : {ambiguous}")
print(f"  rejected on kV mismatch : {kv_reject}")
by_m = collections.Counter(x["location_method"] for x in new)
for k, v in by_m.items():
    print(f"     {k}: {v}")
print("\n  samples:")
for x in new[:8]:
    print(f"    {x['bus_label'][:32]:34s} -> {x['matched_substation_name'][:26]:28s} "
          f"kv_ok={x['kv_consistent']}")

# ⛔ REPLACE, DO NOT APPEND -- THIS WAS A FAN-OUT BUG AND THE MEASUREMENT CAUGHT IT.
# `existing + new` looked right because `new` only skips buses that were already LOCATED. But a
# bus can sit in the candidate table with `location_method='none'` AND get a fresh match here, so
# those buses appeared TWICE. Downstream, tier0's LEFT JOIN duplicated them: PJM injection rows
# went 1,814 -> 1,862 while the distinct bus count stayed 1,814 -- a fan-out of exactly the shape
# the D85 guard teaches you to measure. One row per bus_number, newest match wins.
by_bus = {e["bus_number"]: e for e in existing}
for x in new:
    by_bus[x["bus_number"]] = x
rows = list(by_bus.values())
assert len(rows) == len({r["bus_number"] for r in rows}), "duplicate bus_number survived"
print(f"\n  rows after de-duplication: {len(rows)} "
      f"(existing {len(existing)} + new {len(new)} - {len(existing) + len(new) - len(rows)} replaced)")
schema = [
    bigquery.SchemaField("bus_number", "STRING"), bigquery.SchemaField("bus_label", "STRING"),
    bigquery.SchemaField("bus_kv", "FLOAT"), bigquery.SchemaField("location_method", "STRING"),
    bigquery.SchemaField("match_confidence", "STRING"),
    bigquery.SchemaField("match_basis", "STRING"), bigquery.SchemaField("lat", "FLOAT"),
    bigquery.SchemaField("lon", "FLOAT"),
    bigquery.SchemaField("matched_substation_name", "STRING"),
    bigquery.SchemaField("matched_source", "STRING"),
    bigquery.SchemaField("kv_consistent", "BOOL"),
    bigquery.SchemaField("collision_count", "INT64"),
]
client.load_table_from_json(
    rows, OUT, job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE"),
).result()

chk = list(client.query(f"""
  SELECT COUNT(*) n, COUNTIF(lat IS NOT NULL) loc,
         COUNTIF(lat IS NOT NULL AND lon BETWEEN -88.1 AND -84.7
                 AND lat BETWEEN 37.7 AND 41.8) in_indiana
  FROM `{OUT}`"""))[0]
print(f"\n{OUT}: {chk.n} rows, {chk.loc} located ({chk.in_indiana} inside the Indiana box)")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_pjm_bus_locations_v2',
 'indiana_app.in_pjm_bus_locations_candidate (kept verbatim) + in_substations_dedup name match',
 'PSS/E bus label reduced to its station stem (area code and voltage stripped) and matched to '
 'substation_name; a match is accepted ONLY if unambiguous in the corpus AND the bus voltage sits '
 'inside the substation kV range; ambiguous names and kV mismatches are left UNLOCATED. '
 'RE-SCRAPE COMMAND: python scripts/build_pjm_bus_locations_v2.py',
 {len(rows)}, 0.0, CURRENT_TIMESTAMP(),
 'G114 non-scraping half. Adds {len(new)} buses the existing matcher missed ({ambiguous} rejected '
 'as ambiguous, {kv_reject} on kV). Confidence is med, never high: our substation corpus is an '
 'INDIANA clip while PJM case 23 spans the AEP footprint, so a same-named out-of-state station '
 'cannot be disambiguated. The remaining ~1,500 need a source we do not hold.'
)""").result()
print("  _registry row written")
print("PJM BUS LOCATIONS V2 COMPLETE")
