"""Ship the full tariff schedule / rider breakdown to the Market page.

Operator, 2026-08-18: "the market updates (including tariffs and a complete table breakdown ... for
all of the tariff schedules/riders)".

WHY A DEDICATED PAYLOAD. The Market page already carries a URDB-derived cost proxy, and that proxy
is FLATTENED - no riders, no fixed charges, no seasonal split. It is a ranking tool and it
understates. `in_utility_tariff_riders` is the itemised thing: 419 components across 73 schedules,
read from the utilities' own books and the IURC's stamped copies.

    READS indiana_app ONLY. An export is on the path to what the user sees, so it must not depend
    on the platform dataset (checkpoint invariant).

RE-SCRAPE COMMAND: python scripts/export_tariffs.py
"""
import datetime
import gzip
import json
import os

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "tariffs.json.gz")
client = bigquery.Client(project="energy-platfrom")

# The five investor-owned utilities first: they serve the overwhelming majority of Indiana load and
# are the only ones a large new customer realistically interconnects to. Municipals and co-ops
# follow, and most are `not_held` placeholders recording WHERE their rates live rather than a rate.
IOU = ("Duke Energy Indiana Inc", "Northern Indiana Pub Serv Co",
       "Indiana Michigan Power Co (Indiana)", "Indianapolis Power & Light Co",
       "Southern Indiana Gas & Elec Co")

# component_type -> (display order, plain-English group). The order is the order a bill is built up
# in, not alphabetical: what you pay to be connected, then for capacity, then for energy, then the
# fuel pass-through, then the riders stacked on top - and the conditions that decide if you qualify.
GROUPS = {
    "base_charge": (1, "Fixed charge"),
    "demand":      (2, "Demand (capacity)"),
    "energy":      (3, "Energy"),
    "fuel_base":   (4, "Fuel base embedded in rates"),
    "rider":       (5, "Riders"),
    "ratchet":     (6, "Ratchet"),
    "eligibility": (7, "Eligibility & terms"),
}

rows = list(client.query(f"""
  SELECT utility, tariff_code, tariff_name, component_type, code, name,
         rate, unit, basis, applies_to, season, value_status
  FROM `{DS}.in_utility_tariff_riders`
  ORDER BY utility, tariff_code, component_type, name"""))
print(f"components read: {len(rows):,}")

by_util = {}
for r in rows:
    u = by_util.setdefault(r.utility, {"utility": r.utility, "is_iou": r.utility in IOU,
                                       "schedules": {}})
    key = r.tariff_code or "(unspecified)"
    sch = u["schedules"].setdefault(key, {"code": key, "name": r.tariff_name, "components": []})
    if r.tariff_name and not sch["name"]:
        sch["name"] = r.tariff_name
    order, group = GROUPS.get(r.component_type, (9, r.component_type or "other"))
    sch["components"].append({
        "group": group, "order": order, "type": r.component_type,
        "code": r.code, "name": r.name,
        # NULL rate is preserved as null. It means the book does not publish this component -
        # never zero. Treating an unstated rider as 0 is what would make a modelled bill look
        # cheaper than reality, and the loaders were built to keep that distinction.
        "rate": r.rate, "unit": r.unit, "basis": r.basis,
        "applies_to": r.applies_to, "season": r.season,
        "status": r.value_status,
    })

utilities = []
for u in by_util.values():
    scheds = sorted(u["schedules"].values(), key=lambda s: (-len(s["components"]), s["code"]))
    for s in scheds:
        s["components"].sort(key=lambda c: (c["order"], c["name"] or ""))
        s["n_priced"] = sum(1 for c in s["components"] if c["rate"] is not None)
    utilities.append({"utility": u["utility"], "is_iou": u["is_iou"],
                      "n_schedules": len(scheds), "n_components": sum(len(s["components"]) for s in scheds),
                      "schedules": scheds})
utilities.sort(key=lambda x: (not x["is_iou"], -x["n_components"], x["utility"]))

payload = {
    "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "summary": {
        "utilities": len(utilities),
        "iou": sum(1 for u in utilities if u["is_iou"]),
        "schedules": sum(u["n_schedules"] for u in utilities),
        "components": len(rows),
        "priced": sum(1 for r in rows if r.rate is not None),
        "not_held": sum(1 for r in rows if r.value_status == "not_held"),
    },
    "utilities": utilities,
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with gzip.open(OUT, "wt", encoding="utf-8") as fh:
    json.dump(payload, fh, separators=(",", ":"))
s = payload["summary"]
print(f"tariffs.json.gz : {s['utilities']} utilities ({s['iou']} IOU) · {s['schedules']} schedules · "
      f"{s['components']} components ({s['priced']} priced, {s['not_held']} not held) · "
      f"{os.path.getsize(OUT):,} bytes")
