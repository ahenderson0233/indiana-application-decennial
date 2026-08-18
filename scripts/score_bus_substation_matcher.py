"""Bus-name -> substation matcher, scored against a labelled truth set.

⭐ WHY THIS EXISTS. The Orennia subscription lapses late 2027 and their data cannot remain in the
tools. Their bus coordinates are 70% `Estimated` - derived by matching the bus NAME to a substation,
which is the same technique available to us - so there is no privileged coordinate feed to lose.
What we lose is the ANSWER KEY. So build the matcher now, while we can still score it.

YARDSTICK USE ONLY. Vendor coordinates SCORE the matcher. The coordinates the matcher OUTPUTS come
from our own substation tables (`energy.mat_grid_substations`, HIFLD/OSM). Nothing of theirs is
stored or shipped - which is exactly the permitted use under the standing ruling.

RE-SCRAPE COMMAND: python scripts/score_bus_substation_matcher.py
"""
import math
import re
import statistics as st
from collections import defaultdict

from google.cloud import bigquery

c = bigquery.Client(project="energy-platfrom")
AEP_STATES = ("IN", "OH", "WV", "VA", "KY", "MI", "IL", "PA", "TN", "WI", "MD", "NC")


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def skeleton(s):
    """PJM abbreviations drop vowels: GRNGST <- GRANGE ST. Keep the first letter."""
    n = norm(s)
    return n[0] + re.sub(r"[AEIOU]", "", n[1:]) if n else n


# kV values that appear as a TRAILING part of a bus name (07VIC161 = VIC at 161 kV). Longest
# first so 161 is stripped before 16 would be. Only these - a bare trailing "2" is part of a name.
KV_SUFFIX = ("1000", "765", "500", "345", "230", "161", "138", "115", "100", "69", "46", "34", "13")
# suffixes that describe the FACILITY, not the place: tap points and station markers
NAME_SUFFIX = ("STATN", "STATION", "SUBSTA", "SUB", "TAP", "TP", "STA", "SS")


def busname(label):
    """'05AMOS 765 kV (242508)' -> 'AMOS';  '07VIC161' -> 'VIC';  'O7RATTS161' -> 'RATTS'.

    Learned by READING the two conventions rather than assuming one:
      PJM   '05AMOS 765 kV (242508)'  - name, then voltage, then bus number, space separated
      MISO  '07VIC161', '07SUL_TP'    - area prefix, name, voltage or facility suffix, NO spaces
    Three traps live in the MISO form and each one silently kills an exact match:
      1. the trailing digits ARE the kV and are not part of the name;
      2. _TP / TP / STATN are facility markers, not place names;
      3. 'O7RATTS161' begins with the LETTER O, not a zero - a typo in the publisher's own data,
         so the prefix strip has to accept both.
    """
    s = (label or "").upper()
    m = re.match(r"^\s*(.*?)\s+[0-9.]+\s*KV", s)      # PJM form: cut at the voltage
    s = m.group(1) if m else s
    s = re.sub(r"^[0O]\d", "", s.strip())              # area prefix, tolerating O-for-zero
    s = norm(s)
    for suf in NAME_SUFFIX:                            # facility markers before voltage:
        if s.endswith(suf) and len(s) > len(suf) + 2:  # LYLESTATN -> LYLES
            s = s[: -len(suf)]
            break
    for kv in KV_SUFFIX:                               # trailing voltage: VIC161 -> VIC
        if s.endswith(kv) and len(s) > len(kv) + 1:
            s = s[: -len(kv)]
            break
    for suf in NAME_SUFFIX:                            # and again, for VIC161TP ordering
        if s.endswith(suf) and len(s) > len(suf) + 2:
            s = s[: -len(suf)]
            break
    return s


def hav(a, b, c2, d):
    R, p = 3958.8, math.radians
    return 2 * R * math.asin(math.sqrt(
        math.sin(p(c2 - a) / 2) ** 2
        + math.cos(p(a)) * math.cos(p(c2)) * math.sin(p(d - b) / 2) ** 2))


# ---- truth set: the vendor's placed buses, from the licensed MISO proxy already in BigQuery ----
truth = {}
for r in c.query("""SELECT bus_number, bus_name, bus_kv, lat, lon
                    FROM `energy-platfrom.indiana_app.in_bus_headroom_miso_vendor`
                    WHERE lat IS NOT NULL AND bus_number IS NOT NULL
                    GROUP BY 1, 2, 3, 4, 5"""):
    truth[int(r.bus_number)] = (r.bus_name, r.bus_kv, r.lat, r.lon)
print(f"truth set (vendor-placed buses with coordinates): {len(truth):,}")

# ---- our substations, national over the AEP/MISO footprint ----
subs = []
for r in c.query(f"""SELECT substation_name nm, lat, lon, max_kv, min_kv
                     FROM `energy-platfrom.energy.mat_grid_substations`
                     WHERE substation_name IS NOT NULL AND lat IS NOT NULL
                       AND state IN {AEP_STATES}"""):
    subs.append((r.nm, r.lat, r.lon, r.max_kv, r.min_kv))
print(f"candidate substations: {len(subs):,}")

by_exact, by_skel, by_pref = defaultdict(list), defaultdict(list), defaultdict(list)
for nm, la, lo, mx, mn in subs:
    rec = (nm, la, lo, mx, mn)
    n = norm(nm)
    by_exact[n].append(rec)
    by_skel[skeleton(nm)].append(rec)
    if len(n) >= 5:
        by_pref[n[:5]].append(rec)


def kv_ok(rec, kv):
    """Voltage gate. A 138 kV bus cannot sit at a substation topping out at 34 kV.
    NULL voltage on either side is NOT a mismatch - unknown is not disagreement."""
    if kv is None:
        return True
    mx, mn = rec[3], rec[4]
    if mx is None and mn is None:
        return True
    hi = mx if mx is not None else mn
    lo = mn if mn is not None else mx
    return (lo or 0) * 0.5 <= kv <= (hi or 0) * 2.0


def candidates(name, kv, strategy, gate):
    idx = {"exact": by_exact, "skeleton": by_skel, "prefix5": by_pref}[strategy]
    key = {"exact": name, "skeleton": skeleton(name), "prefix5": name[:5]}[strategy]
    out = idx.get(key, [])
    if gate:
        out = [r for r in out if kv_ok(r, kv)]
    return out


print()
for gate in (False, True):
    print(f"{'=' * 78}\nVOLTAGE GATE: {'ON' if gate else 'OFF'}\n{'=' * 78}")
    for strat in ("exact", "skeleton", "prefix5"):
        hits, dists, amb = 0, [], 0
        for bn, (name, kv, tl, to) in truth.items():
            cands = candidates(busname(name), kv, strat, gate)
            if not cands:
                continue
            hits += 1
            amb += len(cands) > 1
            dists.append(min(hav(r[1], r[2], tl, to) for r in cands))
        if not dists:
            print(f"  {strat:9s} matched 0")
            continue
        g1 = sum(1 for d in dists if d <= 1)
        g5 = sum(1 for d in dists if d <= 5)
        print(f"  {strat:9s} matched {hits:>5}/{len(truth)} ({100 * hits / len(truth):4.1f}%)"
              f"  ambiguous={amb:>4}  median={st.median(dists):6.2f}mi"
              f"  <=1mi={100 * g1 / len(dists):3.0f}%  <=5mi={100 * g5 / len(dists):3.0f}%")
