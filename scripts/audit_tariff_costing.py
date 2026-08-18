"""EXTENSIVE per-utility costing audit: zeros, nulls, aggregations, and false claims.

Operator, 2026-08-18: "you should complete an extensive audit over each of these utilities to
discover any other issues, including any null values, aggregated calculations (e.g., adding
sub-transmission costs with transmission costs, etc.), or any false claims or inputs throughout
these 5 utilities."

WHAT THIS CHECKS, and why each one is here
------------------------------------------
Every defect found on 2026-08-18 had a signature visible in the payload BEFORE anyone read a
dollar figure. This turns each of those signatures into a standing check.

  Z1  a billing leg that comes to $0 for a service class            -> the signature of all 17
  Z2  a 0.0 on a SCHEDULE's own core leg, marked `published`        -> "unpublished is NULL, not 0"
  Z3  a component with rate NULL that still claims to bill          -> a hole asserting a number
  Z4  riders KNOWN to exist but not held for this schedule          -> $0 that means "not captured"
  Z5  a schedule whose rider stack is an OUTLIER among its siblings -> scoping missed it entirely
  A1  two components of the SAME kind summed in one class           -> alternatives added together
  F1  a schedule offering a class its own book never prices         -> a service that is not offered

⚠ ON NOT CRYING WOLF. An earlier revision flagged 15 Z2s, 13 of which were tracker factors
legitimately filed at $0.00000 for the current period - FMCA, DSMA, a TAX rider energy leg. A
published zero is a real published value and changes no bill; the rule it appeared to break
("unpublished is NULL, never 0") is about ABSENT values. This repo already has a front-end audit
that "opened with 56 findings and roughly zero real ones", and the lesson is that a checker with
false positives stops being read. So Z2 fires only on a SCHEDULE's own demand/energy/base leg,
where a zero is structural rather than a period factor; zero trackers are reported as a counted
note instead of as defects.

ON REPLICATING THE RENDERER
---------------------------
This reads the SHIPPED PAYLOAD and replicates exactly one thing from `market.html`: the predicate
deciding whether a component applies at a service class (`at()`, five lines). It deliberately does
NOT re-implement the arithmetic - it reports STRUCTURE, not dollars, so it cannot drift into being
a second opinion about the price. Cross-checked against the rendered page on 2026-08-18: same
classes, same component membership.

    python scripts/audit_tariff_costing.py            # the five IOUs
    python scripts/audit_tariff_costing.py --all      # every utility, municipals included

RE-SCRAPE COMMAND: python scripts/audit_tariff_costing.py
"""
import gzip
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAYLOAD = os.path.join(ROOT, "data", "tariffs.json.gz")

DEMAND_LEGS = ("demand", "demand_kva", "demand_day")
CORE_TYPES = ("demand", "energy", "base_charge")

# Phrases meaning "riders exist for this schedule" even when no rider row carries a rate for it.
# I&M's Sheet 44 roster is the case that found this: it states plainly that eight riders apply to
# ALL standard-service schedules, while every extracted rider factor is scoped to I.P./CS-IRP2.
ROSTER_HINTS = ("riders apply", "surcharges and rate adjustments", "applicable riders",
                "all standard-service schedules")


def load():
    with gzip.open(PAYLOAD, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def applies_at(c, key, family):
    """The renderer's `at()`: name no class -> applies everywhere; name some -> only those."""
    if c.get("volt"):
        return c["volt"] == key
    named = c.get("volt_named")
    if named:
        return family in named
    return True


def audit_utility(u):
    findings = []

    # does the BOOK name riders we hold no factor for?
    roster_seen = set()
    for rider in u.get("riders_index", []):
        txt = f"{rider.get('name') or ''} {rider.get('code') or ''}".lower()
        if any(h in txt for h in ROSTER_HINTS):
            roster_seen.add(rider.get("name") or rider.get("code"))

    for sc in u["schedules"]:
        code = sc["code"]
        classes = sc.get("volt_classes") or [{"key": "any", "family": "any"}]
        own_bill = [c for c in sc["components"] if c.get("bill") and c["origin"] == "schedule"]
        rider_bill = [c for c in sc["components"] if c.get("bill") and c["origin"] != "schedule"]

        # ---- Z2 / Z3 : suspicious values ----------------------------------------------------
        zero_trackers = []
        for c in sc["components"]:
            if c.get("rate") == 0 and (c.get("status") or "") == "published" and c.get("bill"):
                if c["origin"] == "schedule" and c.get("type") in CORE_TYPES:
                    findings.append(("Z2", code, c.get("volt") or "all",
                                     "STRUCTURAL 0.0 marked 'published' - %s (%s). A zero on a "
                                     "schedule's own core leg is either a real published zero or "
                                     "an absent value recorded as a number - read the sheet"
                                     % (c.get("name"), c.get("unit"))))
                else:
                    zero_trackers.append(c.get("name"))
            if c.get("rate") is None and c.get("bill"):
                findings.append(("Z3", code, c.get("volt") or "all",
                                 "claims to bill on a NULL rate - %s" % c.get("name")))
        if zero_trackers:
            findings.append(("--", code, "-",
                             "note: %d tracker factor(s) filed at $0 this period (%s) - real "
                             "published zeros, and they change no bill"
                             % (len(zero_trackers), zero_trackers[0])))

        # ---- Z4 : riders the book names but we hold no factor for ----------------------------
        if roster_seen and not rider_bill and not sc.get("riders_not_held") \
                and not sc.get("by_contract"):
            findings.append(("Z4", code, "-",
                             "NO rider factor held, yet this book states riders apply (%r). A $0 "
                             "riders column reads as 'this schedule has no riders', which the "
                             "tariff contradicts" % sorted(roster_seen)[0]))

        # ---- per service class ---------------------------------------------------------------
        for vc in classes:
            key, fam = vc.get("key"), vc.get("family", "any")
            here = [c for c in own_bill if applies_at(c, key, fam)]
            rhere = [c for c in rider_bill if applies_at(c, key, fam)]

            has_dem = any(c["bill"] in DEMAND_LEGS for c in here + rhere)
            has_en = any(c["bill"] == "energy" for c in here + rhere)

            if not has_dem and sc.get("has_demand_leg"):
                findings.append(("Z1", code, key,
                                 "DEMAND $0 - the schedule publishes a demand charge but none "
                                 "matched this class"))
            if not has_en and sc.get("has_energy_leg"):
                findings.append(("Z1", code, key,
                                 "ENERGY $0 - the schedule publishes an energy charge but none "
                                 "matched this class"))
            if not rhere and rider_bill:
                findings.append(("Z1", code, key,
                                 "RIDERS $0 - %d riders attach to this schedule but none applies "
                                 "at this class" % len({c["origin"] for c in rider_bill})))

            # ---- A1 : alternatives added together ------------------------------------------
            # A base charge plus an adder is normal. Two rows whose names differ only by a
            # voltage tier are ALTERNATIVES, and summing them is the AES/Duke defect. Conditional
            # and reactive components never enter a total, so they cannot be double-counted.
            for leg in ("energy",) + DEMAND_LEGS:
                same = [c for c in here if c["bill"] == leg and not c.get("block")
                        and not c.get("conditional") and not c.get("reactive")]
                if len(same) < 2:
                    continue
                stems = {}
                for c in same:
                    stem = (c.get("name") or "").split(" - ")[0].strip().lower()
                    stems.setdefault(stem, []).append(c)
                for stem, group in stems.items():
                    if len(group) > 1:
                        rates = ", ".join(str(c.get("rate")) for c in group)
                        findings.append(("A1", code, key,
                                         "%d '%s' %s rows summed at one class (%s) - if these are "
                                         "voltage ALTERNATIVES this is the AES/Duke defect again"
                                         % (len(group), stem, leg, rates)))

        # ---- F1 : a class the schedule offers but never prices --------------------------------
        # A negotiated schedule prices nothing by design - that is what "per contract" means.
        for vc in ([] if sc.get("by_contract") else classes):
            key, fam = vc.get("key"), vc.get("family", "any")
            if not [c for c in own_bill if applies_at(c, key, fam)]:
                findings.append(("F1", code, key,
                                 "the schedule lists this service class and prices NOTHING at it "
                                 "- a closed class, or an extraction gap"))

    # ---- Z5 : is one schedule's rider stack an OUTLIER among its siblings? ---------------------
    # Duke's HLF/LLF-TOU carried 1 billable rider against HLF's 15, because every Duke tracker
    # names "Rate HLF" / "Rate LLF" and the schedule is coded "HLF/LLF-TOU", matching neither. It
    # rendered at 7.45c - the CHEAPEST Duke row on the page - purely because its stack was absent.
    # A missing rider stack always makes a schedule look BETTER, which is exactly why it needs a
    # check of its own rather than waiting to be noticed by eye.
    counts = {}
    for sc in u["schedules"]:
        if sc.get("by_contract") or sc.get("riders_not_held"):
            continue
        counts[sc["code"]] = len({c["origin"] for c in sc["components"]
                                  if c["origin"] != "schedule" and c.get("bill")
                                  and c.get("rate")})
    if len(counts) > 1:
        top = max(counts.values())
        for code, n in sorted(counts.items()):
            if top >= 3 and n <= top / 3:
                findings.append(("Z5", code, "-",
                                 "rider stack is an OUTLIER: %d rider code(s) with a non-zero "
                                 "factor against %d on a sibling schedule here. A missing stack "
                                 "always makes a schedule look cheaper than it is" % (n, top)))
    return findings


def main():
    p = load()
    every = "--all" in sys.argv
    utils = [u for u in p["utilities"] if u["is_iou"] or every]
    real = notes = 0
    by_code = {}
    print("=" * 96)
    print("TARIFF COSTING AUDIT - %d utilities (%s)"
          % (len(utils), "all, municipals included" if every else "the five IOUs"))
    print("=" * 96)
    for u in utils:
        f = audit_utility(u)
        for kind, *_ in f:
            by_code[kind] = by_code.get(kind, 0) + 1
            if kind == "--":
                notes += 1
            else:
                real += 1
        if not f:
            print("\n  [CLEAN] %s" % u["utility"])
            continue
        hard = sum(1 for k, *_ in f if k != "--")
        print("\n  %s  -  %d finding(s), %d note(s)" % (u["utility"], hard, len(f) - hard))
        for kind, sched, cls, msg in sorted(f, key=lambda x: (x[0] == "--", x[0])):
            print("     [%s] %-12s %-30s %s" % (kind, sched, str(cls)[:30], msg))
    print("\n" + "=" * 96)
    print("%d finding(s) + %d note(s): %s"
          % (real, notes, ", ".join("%s=%d" % kv for kv in sorted(by_code.items()))))
    print("  Z1 leg at $0 | Z2 structural published 0.0 | Z3 NULL that bills")
    print("  Z4 riders exist, none held | Z5 rider stack an outlier vs siblings")
    print("  A1 same-kind rows summed | F1 class offered but never priced | -- informational")
    return 0


if __name__ == "__main__":
    sys.exit(main())
