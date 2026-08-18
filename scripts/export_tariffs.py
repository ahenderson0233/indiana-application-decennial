"""Tariff payload for the Market page: SCHEDULES with their riders folded in, ready to be costed.

Operator, 2026-08-18: "All of these rates should ideally be projected out to total a yearly spend
and a per kWh cost based solely on the tariff (including the rate schedule and ALL applicable
riders). As such, the riders should NOT be in a separate tab, and you include many sections that
simply aren't rate schedules."

Both corrections are right and both were mine:

  1. A RIDER IS NOT A SCHEDULE. The first version grouped by `tariff_code` and reported "18
     schedules" for Duke. Measured, Duke has ~7 schedule entries (HLF, LLF, LLF-B, HLF/LLF-TOU)
     and ~16 riders and trackers - Rider 28, TDSIC, FAC, RTO and so on - which were being rendered
     as siblings of the schedules they modify. A rider has no customer, no eligibility and no
     standing on its own; it is an adder ON a schedule.
  2. A COMPONENT LIST IS NOT A PRICE. Showing 87 components tells a developer nothing until they
     are multiplied by a load and summed. The deliverable is an annual spend and an effective
     $/kWh, which is exactly what CPS_35MW_Rate_Model.xlsx does for one utility.

So this exporter emits SCHEDULES ONLY, each carrying the riders that apply to it, with every
component tagged by how it bills so the page can compute a real total.

    READS indiana_app ONLY (checkpoint invariant: an export must not depend on the platform dataset).

RE-SCRAPE COMMAND: python scripts/export_tariffs.py
"""
import datetime
import gzip
import json
import os
import re

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "tariffs.json.gz")
client = bigquery.Client(project="energy-platfrom")

IOU = ("Duke Energy Indiana Inc", "Northern Indiana Pub Serv Co",
       "Indiana Michigan Power Co (Indiana)", "Indianapolis Power & Light Co",
       "Southern Indiana Gas & Elec Co")

# A component either BILLS or it is a TERM. Only the first kind can enter a total, and pretending
# otherwise is how a "$/yr" figure quietly becomes fiction: "2,000 kW" is a qualifying floor, not a
# charge, and "5 years" is a contract term.
BILLING = {
    "$/kwh":          "energy",     # x annual kWh
    "$/kw/month":     "demand",     # x billing kW x 12
    "$/kva/month":    "demand_kva",  # x billing kVA x 12 - needs a power factor
    "$/month":        "fixed",      # x 12
    "$/kw/day":       "demand_day",  # x billing kW x 365
}
# Reactive charges depend on the site's power factor, which a siter has not chosen yet. Excluded
# from the total ON PURPOSE and reported, rather than silently dropped or assumed away.
REACTIVE = ("$/kvar/month",)

# A block ladder means the listed rates are ALTERNATIVES applied to successive slices of usage,
# so summing them overstates the bill - it put NIPSCO at 57.94 c/kWh against an Indiana industrial
# reality of roughly 6-9c. Self-tested at import: a pattern that silently stops matching is exactly
# how this went wrong the first time.
BLOCK_RE = re.compile(r"\b(?:first|next|all over|over)\b.*\b(?:kwh|kw|hours)\b", re.I)
assert BLOCK_RE.search("first 30,000 kWh per month")
assert BLOCK_RE.search("next 1,950 kW of Billing Demand")
assert BLOCK_RE.search("all over 1,000,000 kWh per month")
assert BLOCK_RE.search("first 450 hours use of Billing Demand")
assert not BLOCK_RE.search("service at 34,500 V or above with customer-owned transformation")
assert not BLOCK_RE.search("per kW per month, Tier 1 firm service")

CORE = ("demand", "energy", "base_charge")   # a tariff_code with any of these is a real schedule


def unit_key(u):
    return re.sub(r"\s+", "", (u or "").strip().lower())


def volt_class(text):
    """Which service voltage a component is limited to, or None for 'applies at any voltage'."""
    t = (text or "").lower()
    if "sub-transmission" in t or "subtransmission" in t:
        return "subtransmission"
    if "transmission" in t:
        return "transmission"
    if "primary" in t:
        return "primary"
    if "secondary" in t:
        return "secondary"
    return None


rows = list(client.query(f"""
  SELECT utility, tariff_code, tariff_name, component_type, code, name,
         rate, unit, basis, applies_to, season, value_status
  FROM `{DS}.in_utility_tariff_riders`
  ORDER BY utility, tariff_code, component_type, name"""))
print(f"components read: {len(rows):,}")

# ---- split each utility's rows into schedules and riders ------------------------------------
by_util = {}
for r in rows:
    by_util.setdefault(r.utility, []).append(r)

utilities = []
n_sched = n_rider = 0
for util, rs in by_util.items():
    codes = {}
    for r in rs:
        codes.setdefault(r.tariff_code or "(unspecified)", []).append(r)

    sched_codes = {c: v for c, v in codes.items()
                   if any(x.component_type in CORE for x in v)}
    rider_codes = {c: v for c, v in codes.items() if c not in sched_codes}

    def comp(r, origin, origin_name):
        uk = unit_key(r.unit)
        return {
            "origin": origin,                 # "schedule" or the rider's code
            "origin_name": origin_name,
            "type": r.component_type,
            "name": r.name or r.code,
            "rate": r.rate,
            "unit": r.unit,
            "bill": BILLING.get(uk) if r.rate is not None else None,
            "reactive": uk in REACTIVE,
            "volt": volt_class(r.applies_to) or volt_class(r.name),
            "applies_to": r.applies_to,
            "basis": r.basis,
            "season": r.season,
            "status": r.value_status,
            # A BLOCK is an alternative, not an addend. The books encode the ladder in prose -
            # "first 30,000 kWh per month", "next 70,000 kWh", "all over 1,000,000 kWh",
            # "first 450 hours use of Billing Demand" - and summing those rates instead of
            # applying them as a ladder put NIPSCO at 57.94 c/kWh against an Indiana industrial
            # reality of roughly 6-9c. Flag it; a schedule containing blocks is NOT costable
            # until the ladder is parsed and applied.
            # Detects a DECLINING/INVERTED BLOCK LADDER in the basis prose: "first 30,000 kWh
            # per month", "next 70,000 kWh", "all over 1,000,000 kWh", "first 450 hours use of
            # Billing Demand". Those rates are ALTERNATIVES, not addends.
            #
            # ⚠ The first version of this line went through a shell heredoc and its \b word
            # boundaries reached disk as literal BACKSPACE bytes (0x08). It then matched nothing,
            # silently, while `grep` rendered the line as clean text because the terminal ate the
            # control characters - so the code looked right and detected zero blocks. Compiled at
            # module level now, and asserted at import, so it cannot fail quietly again.
            "block": bool(BLOCK_RE.search(r.basis or "")),
        }

    scheds = []
    for code, v in sched_codes.items():
        name = next((x.tariff_name for x in v if x.tariff_name), None)
        components = [comp(r, "schedule", name) for r in v]

        # ---- attach the riders that apply to THIS schedule ----------------------------------
        # ⛔ Two bugs lived here and both produced a plausible-looking total that was far too high.
        #
        #  1. SUBSTRING MATCHING. `code.lower() in applies_to` made schedule "HL" match the rider
        #     rows for HL1, HL2 AND HL3 - which are mutually exclusive VOLTAGE TIERS of one rider -
        #     so a single rider was counted three times.
        #  2. A CLASS LIST IS NOT A BLANKET. applies_to reads "HL (all voltages), PL". Scanning for
        #     the phrase "all voltages" treated that as applying to EVERY schedule, so an HL rider
        #     also landed on SL and PH, which have their own separate rows.
        #
        # Together they put AES's rider stack at $28.89/kW-month and the modelled bill at 13.77
        # c/kWh, against an Indiana industrial reality of roughly 6-9c. The arithmetic was right;
        # the matching was wrong.
        #
        # So: tokenise applies_to into CLASS TOKENS and require a real match. Tier rows are
        # collapsed to one value rather than summed, and the collapse is reported.
        attached, tiered = [], {}
        for rcode, rv in rider_codes.items():
            rname = next((x.tariff_name for x in rv if x.tariff_name), rcode)
            for r in rv:
                a = (r.applies_to or "")
                toks = set(re.findall(r"[A-Za-z]{1,4}\d{0,2}|\d{3}", a.upper()))
                c_up = code.upper()
                exact = c_up in toks
                # "HL1" is a tier OF "HL" - same class, one of several alternatives
                tier = any(t != c_up and t.startswith(c_up) and t[len(c_up):].isdigit()
                           for t in toks)
                # a genuine blanket says "all classes"/"all rate schedules" with NO class list
                blanket = (re.search(r"all (classes|rate schedules|listed schedules|tiers)", a, re.I)
                           is not None and not re.search(r"\b(HL|PL|SL|PH|LLF|HLF)\b", a))
                if not (exact or tier or blanket):
                    continue
                cc = comp(r, rcode, rname)
                if tier and not exact:
                    tiered.setdefault((rcode, unit_key(r.unit)), []).append(cc)
                else:
                    attached.append(cc)
        # collapse each tiered group to its median: the tiers are alternatives, a customer sits on
        # exactly one, and which one is not derivable from the book alone.
        for (rcode, _uk), group in tiered.items():
            group.sort(key=lambda c: c["rate"])
            mid = group[len(group) // 2]
            mid = dict(mid, tiered_of=len(group))
            attached.append(mid)
        components += attached
        billable = [c for c in components if c["bill"]]
        scheds.append({
            "code": code, "name": name,
            "components": components,
            "n_components": len(components),
            "n_billable": len(billable),
            "n_riders_attached": len({c["origin"] for c in attached}),
            "volt_classes": sorted({c["volt"] for c in components if c["volt"]}),
            # a schedule with no energy AND no demand charge cannot be costed; say so rather than
            # emitting a confidently wrong total
            # costable = has a billable leg AND no block ladder. Refusing to total a
            # block-rated schedule is the whole point: a wrong dollar figure on a page shown to
            # management is worse than an honest absence.
            "blocked": any(c["block"] for c in billable),
            "costable": (any(c["bill"] == "energy" for c in billable)
                         or any(c["bill"] in ("demand", "demand_kva") for c in billable))
                        and not any(c["block"] for c in billable),
        })
    scheds.sort(key=lambda s: (not s["costable"], -s["n_billable"], s["code"]))

    riders_only = [{"code": c, "name": next((x.tariff_name for x in v if x.tariff_name), c),
                    "n": len(v)} for c, v in rider_codes.items()]
    n_sched += len(scheds)
    n_rider += len(riders_only)
    utilities.append({
        "utility": util, "is_iou": util in IOU,
        "n_schedules": len(scheds), "n_riders": len(riders_only),
        "schedules": scheds, "riders_index": sorted(riders_only, key=lambda x: x["code"]),
    })

utilities.sort(key=lambda u: (not u["is_iou"], -u["n_schedules"], u["utility"]))

payload = {
    "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "summary": {
        "utilities": len(utilities), "iou": sum(1 for u in utilities if u["is_iou"]),
        "schedules": n_sched, "riders": n_rider, "components": len(rows),
        "costable": sum(1 for u in utilities for s in u["schedules"] if s["costable"]),
    },
    "utilities": utilities,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with gzip.open(OUT, "wt", encoding="utf-8") as fh:
    json.dump(payload, fh, separators=(",", ":"))
s = payload["summary"]
print(f"tariffs.json.gz : {s['utilities']} utilities ({s['iou']} IOU) · "
      f"{s['schedules']} SCHEDULES ({s['costable']} costable) · {s['riders']} riders attached to them · "
      f"{s['components']} components · {os.path.getsize(OUT):,} bytes")
for u in utilities[:5]:
    print(f"    {u['utility'][:38]:38s} schedules={u['n_schedules']:>2}  riders={u['n_riders']:>2}")
