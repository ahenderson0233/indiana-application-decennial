"""PER-UTILITY fingerprints, so a fix for one publisher cannot silently move another.

Operator, 2026-08-18: "if the prior session didn't already make the code blocks unique and
independent for each utility, this should be top of mind, since fixing one utility caused all
other utilities to break in the last session."

The adapters (`tariff_adapters.py`) give each publisher its own declaration block, but declaring
independence is not the same as PROVING it: the arithmetic underneath is deliberately shared, and
a change there reaches everyone. That is how the last session's fixes kept trading one defect for
another - separating AES's low-load-factor class fragmented its demand leg, and making Duke's
multi-class rows class-agnostic put HLF at +402%.

So this measures it. Each utility gets a hash over everything that could change its bill:

    schedule codes, eligibility bounds, service classes, and for every component its
    billing leg, rate, months, class binding, block ladder and conditional/reactive status

Run it BEFORE a change and AFTER, and the diff names exactly which publishers moved. A change
inside one adapter block that moves a second utility is a bug in the shared layer, and this is the
instrument that says so instead of leaving it to be found on screen three sessions later.

    python scripts/tariff_fingerprint.py              # compare against the stored baseline
    python scripts/tariff_fingerprint.py --update     # accept the current state as the baseline

⛔ It fingerprints the PAYLOAD, not the source. Run `python scripts/export_tariffs.py` first, or
you are comparing against a stale build.

RE-SCRAPE COMMAND: python scripts/tariff_fingerprint.py --update
"""
import gzip
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAYLOAD = os.path.join(ROOT, "data", "tariffs.json.gz")
BASELINE = os.path.join(ROOT, "data", "tariff_fingerprints.json")

# Only the fields that can change a bill. Deliberately NOT prose: a reworded `notes` string in an
# adapter must not read as a costing change, or the instrument cries wolf and stops being used.
COMPONENT_FIELDS = ("origin", "name", "bill", "rate", "unit", "months",
                    "volt", "volt_named", "block", "conditional", "reactive",
                    "tou_period", "tou_share", "fuel_base")
SCHEDULE_FIELDS = ("code", "min_kw", "max_kw", "costable", "modifier", "large_load",
                   "blocked", "tou", "inherits_from", "has_demand_leg", "has_energy_leg",
                   "by_contract", "low_load_factor", "fuel_base_rate")


def canon(util):
    """A stable, order-independent description of everything that could change this bill."""
    out = {"utility": util["utility"],
           "benchmark_cents": util.get("benchmark_cents"),
           "schedules": []}
    for sc in sorted(util["schedules"], key=lambda s: s["code"]):
        comps = sorted(
            [[c.get(f) for f in COMPONENT_FIELDS] for c in sc["components"]],
            key=lambda row: json.dumps(row, sort_keys=True, default=str))
        out["schedules"].append({
            **{f: sc.get(f) for f in SCHEDULE_FIELDS},
            "volt_classes": [v["key"] for v in sc.get("volt_classes", [])],
            "components": comps,
        })
    return out


def fingerprints():
    with gzip.open(PAYLOAD, "rt", encoding="utf-8") as fh:
        payload = json.load(fh)
    fps = {}
    for u in payload["utilities"]:
        blob = json.dumps(canon(u), sort_keys=True, default=str)
        fps[u["utility"]] = {
            "sha": hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16],
            "schedules": len(u["schedules"]),
            "is_iou": u["is_iou"],
        }
    return fps


def main():
    if not os.path.exists(PAYLOAD):
        sys.exit("no payload - run: python scripts/export_tariffs.py")
    now = fingerprints()

    if "--update" in sys.argv:
        with open(BASELINE, "w", encoding="utf-8") as fh:
            json.dump(now, fh, indent=1, sort_keys=True)
        ious = sum(1 for v in now.values() if v["is_iou"])
        print(f"baseline written: {len(now)} utilities ({ious} IOU) -> data/tariff_fingerprints.json")
        return 0

    if not os.path.exists(BASELINE):
        print("no baseline yet. Run with --update to record one.")
        return 0

    with open(BASELINE, encoding="utf-8") as fh:
        was = json.load(fh)

    moved, added, dropped = [], [], []
    for util, v in sorted(now.items()):
        if util not in was:
            added.append(util)
        elif was[util]["sha"] != v["sha"]:
            moved.append((util, was[util], v))
    for util in sorted(was):
        if util not in now:
            dropped.append(util)

    iou_moved = [m for m in moved if m[2]["is_iou"]]
    print(f"tariff fingerprints: {len(now)} utilities checked against the baseline")
    if not (moved or added or dropped):
        print("  [PASS] every utility is byte-identical to the baseline - nothing moved")
        return 0
    for util, old, new in moved:
        tag = "IOU" if new["is_iou"] else "muni/co-op"
        note = ("" if old["schedules"] == new["schedules"]
                else f"  schedules {old['schedules']} -> {new['schedules']}")
        print(f"  [MOVED] {util}  ({tag})  {old['sha']} -> {new['sha']}{note}")
    for util in added:
        print(f"  [NEW]   {util}")
    for util in dropped:
        print(f"  [GONE]  {util}")
    print(f"\n  {len(moved)} utilities moved, {len(iou_moved)} of them IOUs.")
    print("  If you changed ONE publisher's adapter and more than one utility moved, the change")
    print("  leaked through the shared layer - that is the defect this check exists to catch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
