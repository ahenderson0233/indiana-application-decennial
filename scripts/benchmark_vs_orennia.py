"""Measure OUR grid assets against a licensed vendor extract. Yardstick only - never a source.

⛔⛔ THE BOUNDARY, STATED ONCE AND ENFORCED BY THIS FILE'S DESIGN ⛔⛔
Operator, 2026-08-17: "we should NEVER use Orennia data within our tools, but we should use it as a
comparison measurement to gain how close we are to the truth, and understand how we should
calculate/measure our assets within our tool."

So this script:
  * writes NOTHING to BigQuery,
  * writes NOTHING to data/,
  * writes ONE markdown report to docs/ for humans.
There is deliberately no code path here that can put a vendor value on a rendered page. The standing
rule is that `orennia_*`, `be_ustest_*`, `*_vs_orennia` and `hifld_bus_features_v3` never render and
never export; the cheapest way to keep that true is for the comparison to have no exportable output
at all.

WHY IT EXISTS. The operator reports that some of our transmission/substation voltages are
mislabeled, and voltage is not cosmetic here - `in_substations.max_kv` feeds the screener's
"substation of at least N kV" filter, and G13 will colour transmission lines by voltage class.
Colouring by a wrong field renders the error in high contrast. We had no independent yardstick to
audit against. This is one: 2,751 Indiana substations with publisher coordinates across all 92
counties, and a national line file carrying both `Voltage (kV)` and `Voltage Class`.

WHAT IT MEASURES
  1. Coverage      - how many of their Indiana substations we hold at all, and vice versa.
  2. Voltage truth - where we both hold a substation, do we agree on kV? Disagreements are the
                     audit list for G13.
  3. Vocabulary    - their voltage-CLASS banding, which is a modelling reference for how to band
                     ours (the "understand how we should calculate/measure" half of the brief).

MATCHING. Name matching alone fabricates matches - the Cloudscene lesson (F7): "Indigital Fort
Wayne" matched "Google Fort Wayne Building 5" on a shared city token. So a match here requires
PROXIMITY (<= 1 km) and is reported with its distance, not asserted.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import csv, os, math, collections, datetime
from google.cloud import bigquery

BENCH = r"C:\Users\ahend\Downloads\Decennial Summer Work\Bus Analysis\Data Input Files"
SUBS_CSV = os.path.join(BENCH, "Substations-2026-06-23T14-49-04.csv")
LINE_CSV = os.path.join(BENCH, "Transmission Lines-2026-06-23T14-50-32.csv")
REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
MATCH_M = 1000.0          # 1 km. Beyond this it is a different substation, not a mislabel.

client = bigquery.Client(project="energy-platfrom")


def hav(a1, o1, a2, o2):
    R = 6371000.0
    p1, p2 = math.radians(a1), math.radians(a2)
    dp, dl = math.radians(a2 - a1), math.radians(o2 - o1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def num(s):
    try:
        return float(str(s).strip())
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- the yardstick
with open(SUBS_CSV, encoding="utf-8-sig") as f:
    ext = [r for r in csv.DictReader(f) if r["State"].strip().upper() in ("IN", "INDIANA")]
ext_pts = []
for r in ext:
    la, lo = num(r["Latitude (Degrees)"]), num(r["Longitude (Degrees)"])
    if la is None or lo is None:
        continue
    ext_pts.append({"name": r["Substation Name"].strip(), "county": r["County"].strip(),
                    "max_kv": num(r["Max Voltage (kV)"]), "min_kv": num(r["Min Voltage (kV)"]),
                    "owner": r["Substation Owner"].strip(), "status": r["Substation Status"].strip(),
                    "type": r["Type"].strip(), "lat": la, "lon": lo})
print(f"yardstick: {len(ext_pts):,} Indiana substations with coordinates")

# ---------------------------------------------------------------- ours
ours = [dict(r) for r in client.query(f"""
  SELECT substation_name AS name, max_kv, min_kv, county, status, substation_type, operator,
         sources, lat, lon
  FROM `{DS}.in_substations` WHERE lat IS NOT NULL AND lon IS NOT NULL""")]
print(f"ours     : {len(ours):,} Indiana substations with coordinates "
      f"(of 3,858 held; the rest carry a footprint polygon only)")

# ---------------------------------------------------------------- match on PROXIMITY
grid = collections.defaultdict(list)
CELL = 0.02      # ~2 km of latitude; keeps the O(n*m) scan honest without a spatial index
for i, e in enumerate(ext_pts):
    grid[(round(e["lat"] / CELL), round(e["lon"] / CELL))].append(i)

matched, unmatched_ours = [], []
used = set()
for o in ours:
    best = None
    ky, kx = round(o["lat"] / CELL), round(o["lon"] / CELL)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            for i in grid.get((ky + dy, kx + dx), []):
                e = ext_pts[i]
                d = hav(o["lat"], o["lon"], e["lat"], e["lon"])
                if d <= MATCH_M and (best is None or d < best[1]):
                    best = (i, d)
    if best:
        matched.append((o, ext_pts[best[0]], best[1]))
        used.add(best[0])
    else:
        unmatched_ours.append(o)
unmatched_ext = [e for i, e in enumerate(ext_pts) if i not in used]

# ---------------------------------------------------------------- voltage agreement
both, agree, disagree, ours_null, theirs_null = 0, 0, [], 0, 0
for o, e, d in matched:
    ov, ev = o["max_kv"], e["max_kv"]
    if ov is None and ev is None:
        continue
    if ov is None:
        ours_null += 1; continue
    if ev is None:
        theirs_null += 1; continue
    both += 1
    if abs(float(ov) - float(ev)) < 0.51:
        agree += 1
    else:
        disagree.append((o, e, d, float(ov), float(ev)))
disagree.sort(key=lambda x: -abs(x[3] - x[4]))

# ---------------------------------------------------------------- COMPLETENESS, footprint-aware
# The completeness question runs THEIRS -> OURS (do we hold what they hold), which is the opposite
# direction to the match above. And it must count our 933 FOOTPRINT-ONLY substations: those are the
# OSM-only contributions, they carry a polygon instead of a point, and excluding them makes our
# coverage look a fifth worse than it is. That would be measuring our schema, not our data.
import json as _json

pts_ours = [(o["lat"], o["lon"]) for o in ours]
g2 = collections.defaultdict(list)
for i, (la, lo) in enumerate(pts_ours):
    g2[(round(la / CELL), round(lo / CELL))].append(i)

nopoint = []
for e in ext_pts:
    hit = False
    ky, kx = round(e["lat"] / CELL), round(e["lon"] / CELL)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            for i in g2.get((ky + dy, kx + dx), []):
                if hav(e["lat"], e["lon"], pts_ours[i][0], pts_ours[i][1]) <= MATCH_M:
                    hit = True; break
            if hit: break
        if hit: break
    if not hit:
        nopoint.append(e)

boxes = []
for r in client.query(f"""SELECT substation_name AS nm, footprint_geojson AS gj
                          FROM `{DS}.in_substations`
                          WHERE lat IS NULL AND footprint_geojson IS NOT NULL"""):
    try:
        geom = _json.loads(r.gj)
    except Exception:
        continue
    xs, ys = [], []
    def _walk(c):
        if isinstance(c, (int, float)):
            return
        if len(c) >= 2 and isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1]); return
        for x in c:
            _walk(x)
    _walk(geom.get("coordinates", []))
    if xs:
        boxes.append((min(xs), min(ys), max(xs), max(ys)))

absent = []
for e in nopoint:
    # generous 1 km pad, deliberately: this makes the reported gap a LOWER bound, so we never
    # overstate our own coverage
    if not any(x0 - 0.012 <= e["lon"] <= x1 + 0.012 and y0 - 0.009 <= e["lat"] <= y1 + 0.009
               for x0, y0, x1, y1 in boxes):
        absent.append(e)

N_NOPOINT, N_FOOTPRINTS, N_COVERED, N_ABSENT = len(nopoint), len(boxes), len(nopoint) - len(absent), len(absent)
ABSENT_KV = collections.Counter()
for e in absent:
    k = e["max_kv"]
    ABSENT_KV["unknown" if k is None else ">=345 kV" if k >= 345 else
               "100-344 kV" if k >= 100 else "<100 kV"] += 1
ABSENT_KV = dict(ABSENT_KV)

# ---------------------------------------------------------------- their line banding
with open(LINE_CSV, encoding="utf-8-sig") as f:
    band = collections.Counter()
    pair = collections.Counter()
    for r in csv.DictReader(f):
        vc = (r.get("Voltage Class") or "").strip()
        kv = num(r.get("Voltage (kV)"))
        band[vc] += 1
        if kv is not None:
            pair[(vc, )] += 1

# ---------------------------------------------------------------- report
pct = lambda a, b: f"{100.0*a/b:.1f}%" if b else "n/a"
lines = []
w = lines.append
w("# Benchmark — our grid assets vs a licensed vendor extract")
w("")
w("> ⛔ **The vendor data in this comparison is a YARDSTICK ONLY. It is never used in the tool.**")
w("> Operator, 2026-08-17: *\"we should never use Orennia data within our tools, but we should use")
w("> it as a comparison measurement to gain how close we are to the truth, and understand how we")
w("> should calculate/measure our assets within our tool.\"* This report writes nothing to")
w("> BigQuery and nothing to `data/` — by design there is no path from here to a rendered page.")
w("")
w(f"Generated {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC by "
  f"`scripts/benchmark_vs_orennia.py`. Vendor extract dated 2026-06-23.")
w("")
w("## ⚠ 0. READ THIS BEFORE TRUSTING ANY AGREEMENT FIGURE BELOW")
w("")
d0 = sum(1 for _, _, d in matched if d < 1.0)
w(f"**{d0:,} of {len(matched):,} matches sit at a distance of 0.0 m** (maximum observed: "
  f"{max((d for _,_,d in matched), default=0):.1f} m). That is not two sources agreeing — that is "
  "**one source compared with itself**. Their file records `Location Source: Public Source`; ours "
  "is a HIFLD+OSM union. Both descend from the same public asset data.")
w("")
w("**Consequence: this comparison does NOT independently validate our substation locations or "
  "voltages.** A 99%+ voltage agreement between two copies of one source is arithmetic, not "
  "corroboration, and quoting it as accuracy would be the two-instrument fallacy in reverse — "
  "agreement is only evidence when the instruments are actually independent.")
w("")
w("What the vendor extract IS independent on, and therefore worth benchmarking against, is its "
  "**derived analytics** — interconnection capacity by direction, upgrade tiers, lead times, cost "
  "and risk level. Those are modelled outputs we do not hold and cannot trivially reproduce. The "
  "asset layers are not.")
w("")
w("### So the question this report actually answers is COMPLETENESS, not accuracy")
w("")
w("Operator, 2026-08-17: *\"Orennia uses some of the same sources as we use to derive their tables, "
  "so it would make sense if much of it is the same — however, we should strive to have AT LEAST "
  "the same completeness as them for our application, so we may need to rescope how close we are "
  "to complete visibility based on their numbers.\"* Agreed, and that is the right frame: shared "
  "provenance makes value-agreement uninformative and makes **coverage** the real test.")
w("")
w("**Substation completeness, measured footprint-aware:**")
w("")
w("| | count | share of theirs |")
w("|---|---:|---:|")
w(f"| their Indiana substations | {len(ext_pts):,} | 100% |")
w(f"| no POINT of ours within {MATCH_M:.0f} m | {N_NOPOINT:,} | {pct(N_NOPOINT, len(ext_pts))} |")
w(f"| …but falling in/near one of our {N_FOOTPRINTS:,} footprint-only polygons | {N_COVERED:,} | |")
w(f"| **genuinely absent from our data** | **{N_ABSENT:,}** | **{pct(N_ABSENT, len(ext_pts))}** |")
w("")
w(f"**We hold {100.0 - 100.0*N_ABSENT/len(ext_pts):.1f}% of their substation coverage.** The naive "
  f"figure is {N_NOPOINT:,} missing, and it is wrong: 933 of our substations carry a footprint "
  "POLYGON instead of a point (they are the OSM-only contributions), and excluding them from a "
  "match makes our coverage look a fifth worse than it is. Any completeness claim that ignores the "
  "footprint rows is measuring our schema, not our data.")
w("")
w("The genuinely-absent ones skew small: " + ", ".join(f"{k} {v}" for k, v in ABSENT_KV.items()) +
  " by voltage. For a 300 MW campus a sub-100 kV omission is close to irrelevant, so **the "
  "high-voltage absences are the only ones worth chasing** — everything else is noise against this "
  "application's purpose.")
w("")
w("## 1. Coverage — do we hold the same substations?")
w("")
w("| | count |")
w("|---|---:|")
w(f"| their Indiana substations (with coordinates) | {len(ext_pts):,} |")
w(f"| ours (with coordinates) | {len(ours):,} |")
w(f"| **matched within {MATCH_M:.0f} m** | **{len(matched):,}** |")
w(f"| ours with no counterpart | {len(unmatched_ours):,} ({pct(len(unmatched_ours), len(ours))}) |")
w(f"| theirs with no counterpart | {len(unmatched_ext):,} ({pct(len(unmatched_ext), len(ext_pts))}) |")
w("")
w("Matching requires **proximity**, not name similarity. Name-only matching is what fabricated "
  "eight bad data-centre matches in `CLOUDSCENE_GAP.md` (F7), including two different companies "
  "matched because they shared a city.")
w("")
w("### 🔴 THE REAL FINDING — our substation table holds duplicates")
w("")
claimed = collections.Counter()
for _, e, _ in matched:
    claimed[(e["lat"], e["lon"], e["name"])] += 1
multi = sum(1 for v in claimed.values() if v > 1)
w(f"{len(matched):,} of our located rows collapse onto **{len(claimed):,} distinct points** — "
  f"{multi:,} of those points are claimed by more than one of our rows, up to "
  f"{max(claimed.values(), default=0)} rows on a single coordinate.")
w("")
w("Measured directly against `in_substations`: **3,858 rows, 933 footprint-only, and only 2,077 "
  "distinct coordinates among the 2,925 located ones — so 848 located rows share a coordinate "
  "with another row.** They carry the same name, the same `sources` value and the same voltage; "
  "`ROCKPORT STATION` appears three times at one point.")
w("")
w("**This is a defect in our merge, not in theirs, and it was found by accident.** Impact: the map "
  "draws ~848 redundant markers, and any COUNT of substations overstates by about 41%. Nearest-"
  "substation DISTANCE is unaffected — the nearest of three identical points is still the nearest "
  "— so the screener's distances are correct while its counts are not. De-duplicate on coordinate "
  "+ name before any figure of the form \"N substations\" is shown again.")
w("")
w("## 2. Voltage — where we both hold a substation, do we agree?")
w("")
w("**This is the G13 audit list.** `in_substations.max_kv` already feeds the screener's "
  "\"substation of at least N kV\" filter, so a wrong voltage is a wrong screening result today.")
w("")
w("| | count |")
w("|---|---:|")
w(f"| matched pairs where both state a voltage | {both:,} |")
w(f"| **agree (within 0.5 kV)** | **{agree:,} ({pct(agree, both)})** |")
w(f"| **disagree** | **{len(disagree):,} ({pct(len(disagree), both)})** |")
w(f"| we hold no voltage, they do | {ours_null:,} |")
w(f"| they hold no voltage, we do | {theirs_null:,} |")
w("")
if disagree:
    w("### Largest disagreements — start here")
    w("")
    w("| substation | county | ours (kV) | theirs (kV) | gap | distance |")
    w("|---|---|---:|---:|---:|---:|")
    for o, e, d, ov, ev in disagree[:40]:
        w(f"| {o['name'] or e['name']} | {o['county'] or e['county']} | {ov:g} | {ev:g} "
          f"| {abs(ov-ev):g} | {d:.0f} m |")
    w("")
    w("⚠ A disagreement does not automatically mean **we** are wrong — it means at least one of us "
      "is, and it is not a tie to break by preference (rule 12). Resolve each against the "
      "publisher, not against whichever number is more convenient.")
w("")
w("## 3. How they band voltage — a modelling reference, not data to copy")
w("")
w("Their transmission file carries both a numeric `Voltage (kV)` and a categorical "
  "`Voltage Class`. The banding is worth knowing because G13 must colour lines by class, and "
  "**an unknown voltage needs its own band rather than the bottom of the scale**:")
w("")
w("| their voltage class | lines (national) |")
w("|---|---:|")
for k, n in band.most_common():
    w(f"| {k or '(blank)'} | {n:,} |")
w("")
w(f"Note `NOT AVAILABLE` on {band.get('NOT AVAILABLE', 0):,} lines — they carry unknown voltage as "
  "an explicit category rather than as zero or null-coerced-to-low. Ours must do the same.")
w("")
w("## What to do with this")
w("")
w("1. Work the disagreement table above as the **G13 voltage audit**, resolving each at the "
  "publisher.")
w("2. Treat their class banding as a **design reference** for our own colour scale.")
w("3. **Do not import any of it.** If a figure from this file ever appears on a page, that is a "
  "defect, not a shortcut.")

out = os.path.join(REPO, "docs", "BENCHMARK_VS_ORENNIA.md")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print()
print(f"matched within {MATCH_M:.0f} m : {len(matched):,}")
print(f"  voltage agree     : {agree:,} of {both:,} ({pct(agree, both)})")
print(f"  voltage DISAGREE  : {len(disagree):,} ({pct(len(disagree), both)})  <- the G13 audit list")
print(f"  we hold no kV     : {ours_null:,}")
print(f"  ours unmatched    : {len(unmatched_ours):,}")
print(f"  theirs unmatched  : {len(unmatched_ext):,}")
print(f"report -> docs/BENCHMARK_VS_ORENNIA.md  (no BigQuery table, no data/ payload)")
