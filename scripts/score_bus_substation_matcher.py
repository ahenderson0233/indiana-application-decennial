"""Bus-name -> substation matcher, scored against the vendor's 282 placed buses.

YARDSTICK ONLY. Vendor coordinates are used to SCORE our matcher; the coordinates our
matcher outputs come from in_substations_dedup (HIFLD/OSM). Nothing of theirs is stored.
"""
import csv, math, re, statistics as st
from collections import defaultdict
from google.cloud import bigquery

c = bigquery.Client(project="energy-platfrom")
CSV = (r"C:\Users\ahend\Downloads\Decennial Summer Work\Bus Analysis\Data Input Files"
       r"\Greenfield Interconnection Capacity, Buses-2026-06-23T16-58-00.csv")

# ---- truth set: vendor bus -> (lat, lon) ----------------------------------------------
rd = csv.reader(open(CSV, encoding="utf-8-sig", newline="")); next(rd)
I_ID, I_ISO, I_LAT, I_LON, I_CTY = 0, 44, 45, 47, 43
truth = {}
for r in rd:
    if r[I_ISO] != "PJM":
        continue
    try:
        truth[r[I_ID].split("_", 1)[-1]] = (float(r[I_LAT]), float(r[I_LON]), r[I_CTY])
    except ValueError:
        pass
print(f"vendor PJM buses with coordinates: {len(truth)}")

# ---- our buses -------------------------------------------------------------------------
buses = {}
for r in c.query("""SELECT DISTINCT bus_number, bus_label
                    FROM `energy-platfrom.indiana_app.in_pjm_qs_tc2phii_wd`"""):
    buses[str(r.bus_number).strip()] = r.bus_label
print(f"our AEP buses: {len(buses)}")

# ---- our substations (name -> coords). Indiana only, which is the clip we want ----------
subs = []
for r in c.query("""SELECT substation_name, lat, lon, county, max_kv
                    FROM `energy-platfrom.indiana_app.in_substations_dedup`
                    WHERE substation_name IS NOT NULL AND lat IS NOT NULL"""):
    subs.append((r.substation_name, r.lat, r.lon, r.county, r.max_kv))
print(f"Indiana substations with coordinates: {len(subs)}")


def busname(label):
    """'05AMOS 765 kV (242508)' -> 'AMOS'  (strip 2-digit area prefix and the kV tail)"""
    m = re.match(r"^\s*(.*?)\s+[0-9.]+\s*kV", label or "")
    n = (m.group(1) if m else (label or "")).upper()
    n = re.sub(r"^\d{2}", "", n)              # area prefix: 05, 06, 17...
    return re.sub(r"[^A-Z0-9]", "", n)


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def skeleton(s):
    """consonant skeleton - PJM abbreviations drop vowels: GRNGST <- GRANGE ST"""
    s = norm(s)
    return s[0] + re.sub(r"[AEIOU]", "", s[1:]) if s else s


sub_exact, sub_skel = defaultdict(list), defaultdict(list)
for name, la, lo, cty, kv in subs:
    sub_exact[norm(name)].append((name, la, lo))
    sub_skel[skeleton(name)].append((name, la, lo))


def hav(a, b, c2, d):
    R = 3958.8
    p = math.radians
    return 2 * R * math.asin(math.sqrt(
        math.sin(p(c2 - a) / 2) ** 2 + math.cos(p(a)) * math.cos(p(c2)) * math.sin(p(d - b) / 2) ** 2))


STRATS = {}
STRATS["exact"] = lambda n: sub_exact.get(n, [])
STRATS["skeleton"] = lambda n: sub_skel.get(skeleton(n), [])


def prefix_match(n):
    if len(n) < 5:
        return []
    out = [(nm, la, lo) for nm, la, lo in
           ((s[0], s[1], s[2]) for s in subs) if norm(nm).startswith(n[:5])]
    return out


STRATS["prefix5"] = prefix_match

# ---- score each strategy on the buses we can check --------------------------------------
checkable = [b for b in buses if b in truth]
print(f"buses we can SCORE (ours AND vendor-placed): {len(checkable)}\n")

for sname, fn in STRATS.items():
    hits, dists, ambig = 0, [], 0
    for b in checkable:
        cands = fn(busname(buses[b]))
        if not cands:
            continue
        hits += 1
        if len(cands) > 1:
            ambig += 1
        tl, to, _ = truth[b]
        dists.append(min(hav(la, lo, tl, to) for _, la, lo in cands))
    if not dists:
        print(f"  {sname:10s} matched 0")
        continue
    good = sum(1 for d in dists if d <= 1.0)
    ok5 = sum(1 for d in dists if d <= 5.0)
    print(f"  {sname:10s} matched {hits:>4}/{len(checkable)}  ambiguous={ambig:>3}  "
          f"median={st.median(dists):7.2f} mi  within1mi={good:>3} ({100*good/len(dists):.0f}%)  "
          f"within5mi={ok5:>3} ({100*ok5/len(dists):.0f}%)")

# ---- coverage over ALL our buses, not just the scoreable ones ---------------------------
print("\ncoverage over all 1,826 buses:")
for sname, fn in STRATS.items():
    n = sum(1 for b in buses if fn(busname(buses[b])))
    print(f"  {sname:10s} places {n:>5} ({100*n/len(buses):.1f}%)")
