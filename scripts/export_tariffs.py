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
    "$/kwh":          "energy",     # x annual kWh (allocated across blocks where present)
    "$/kw/month":     "demand",     # x billing kW x months in that season
    "$/kva/month":    "demand_kva",  # x billing kVA x 12 - needs a power factor
    "$/month":        "fixed",      # x 12
    "$/kw/day":       "demand_day",  # x billing kW x 365
}
# ⛔ FUEL BASE IS NOT A CHARGE. Per CPS_35MW_Rate_Model.xlsx the base is ALREADY EMBEDDED in the
# energy charge, and what bills is the DIFFERENCE: (actual fuel cost - embedded base) x kWh. Adding
# the base as if it were its own line double-counts fuel, which is one of the reasons the first
# attempt read 13-15 c/kWh against an Indiana industrial reality of 6-9c. It is carried for display
# and for the fuel-adjustment arithmetic, never summed.
NOT_A_CHARGE = ("fuel_base",)
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

# ---- ELIGIBILITY BOUNDS, as first-class fields ----------------------------------------------
# Operator, 2026-08-18: the ceiling "should also be a consideration, especially for a data center
# customer, so it isn't applied as a C&I customer once we mock it up to the map console dossier,
# based on the requested MW value within the dashboard - this helps provide transparency."
#
# Right, and it cannot live only in the Market page's rendering logic. The dossier has to ask
# "which schedules can a load of THIS size actually take at this utility?" and get the same answer.
# So min/max are lifted out of the component rows onto the schedule itself.
#
# This is what caught NIPSCO 624: named "General Service - LARGE", it states "Company shall not
# supply demand in excess of 25,000 kW under this schedule". A 300 MW load is 12x over that
# ceiling, and we were quoting it 14.12 c/kWh as though it were an option. The NAME is not the
# eligibility - only the numbers are.
MIN_RE = re.compile(r"minimum|at least|contract demand", re.I)
MAX_RE = re.compile(r"maximum|in excess of|not exceed|no greater|up to|shall not supply", re.I)
assert MAX_RE.search("Company shall not supply demand in excess of 25,000 kW")
assert MIN_RE.search("Minimum contract demand")
assert not MAX_RE.search("Minimum contract demand")


# A LARGE-LOAD schedule is the one a data centre actually takes service under, and it must be
# findable rather than buried in an alphabetical list (operator, 2026-08-18: "I don't see any large
# load tariff pushed to the application, and this is essential for our analysis").
#
# Identified by SUBSTANCE, not by name - "General Service - Large" is NOT one (25 MW ceiling),
# while NIPSCO 631 and I&M IP-LL are. The test is a high floor or explicit large-load wording.
LARGE_LOAD_RE = re.compile(r"large load|large power|super large|high load factor|data cent",
                           re.I)
LARGE_LOAD_FLOOR_KW = 5000.0        # >=5 MW minimum contract demand marks a large-load schedule


def is_large_load(code, name, min_kw):
    if min_kw is not None and min_kw >= LARGE_LOAD_FLOOR_KW:
        return True
    return bool(LARGE_LOAD_RE.search(f"{code or ''} {name or ''}"))


def eligibility_bounds(components):
    """(min_kw, max_kw) a schedule will serve, in kW, from its own eligibility rows."""
    lo = hi = None
    for c in components:
        if c.get("type") != "eligibility" or c.get("rate") is None:
            continue
        unit = (c.get("unit") or "").strip().lower()
        if unit not in ("kw", "kva", "mw"):
            continue
        val = c["rate"] * (1000.0 if unit == "mw" else 1.0)
        # ⛔ A ZERO IS NOT A BOUND. An eligibility row carrying 0 kW was being read as a ceiling of
        # 0 MW, which excluded Duke HLF and SIGECO LP from every load - and worse, it MASKED a real
        # defect: Duke HLF's +402% error looked "fixed" only because the schedule had been quietly
        # ruled out. A bound has to be a positive quantity to mean anything.
        if not val or val <= 0:
            continue
        # ⛔ CLASSIFY ON THE NAME, NOT THE WHOLE BASIS. Duke HLF's "Minimum specified capacity"
        # row has a basis reading "not less than 25 kW; billing MAXIMUM load never ..." - one
        # clause about a floor, another mentioning a maximum. Scanning the whole string turned a
        # 25 kW FLOOR into a 25 kW CEILING, excluded the schedule from every load, and in doing so
        # HID its real +402% costing error behind a bogus exclusion.
        #
        # The name states what the row IS; the basis merely elaborates. Fall back to the basis only
        # when the name is silent, and require the basis to be unambiguous.
        nm = c.get("name") or ""
        bs = c.get("basis") or ""
        if MAX_RE.search(nm) and not MIN_RE.search(nm):
            hi = val if hi is None else min(hi, val)
        elif MIN_RE.search(nm) and not MAX_RE.search(nm):
            lo = val if lo is None else max(lo, val)
        elif MAX_RE.search(bs) and not MIN_RE.search(bs):
            hi = val if hi is None else min(hi, val)
        elif MIN_RE.search(bs) and not MAX_RE.search(bs):
            lo = val if lo is None else max(lo, val)
        # an ambiguous row states both and is left out rather than guessed at
    return lo, hi


CORE = ("demand", "energy", "base_charge")   # a tariff_code with any of these is a real schedule


def parse_block(basis):
    """Parse the block ladder out of the basis prose -> (kind, lo, hi); hi None = 'and above'.

    Proven against every block row in the estate: 26 of 26 parse, across all five IOUs.
      kwh_month  slices of MONTHLY kWh          "first 30,000 kWh per month"
      hours_use  slices of HOURS-USE of demand  "first 450 hours use of Billing Demand"
      kw         slices of BILLING DEMAND       "next 1,950 kW of Billing Demand"
    A block ladder is why a naive sum put NIPSCO at 57.94 c/kWh: these rates are alternatives
    applied to successive slices, and the slice boundaries are computable from load factor.
    """
    if not basis:
        return None
    b = basis.lower().replace(",", "")
    if "hours use" in b or "hour use" in b:
        kind = "hours_use"
    elif "kwh" in b:
        kind = "kwh_month"
    elif re.search(r"\bkw\b", b):
        kind = "kw"
    else:
        return None
    # "over 450 up to 500 hours use" - a BOUNDED middle block. Checked before the open-ended
    # form, or the upper bound is silently dropped and the block runs to infinity.
    m = re.search(r"over\s+([\d.]+)\s+up to\s+([\d.]+)", b)
    if m:
        return (kind, float(m.group(1)), float(m.group(2)))
    m = re.search(r"(first|next|all over|over)\s+([\d.]+)", b)
    if not m:
        m2 = re.search(r"first\s+([\d.]+)\s*kw", b)
        return ("kw", 0.0, float(m2.group(1))) if m2 else None
    word, val = m.group(1), float(m.group(2))
    if word == "first":
        return (kind, 0.0, val)
    if word in ("all over", "over"):
        return (kind, val, None)
    return (kind, None, val)          # "next N" - lower bound resolved by ordering below


def resolve_next(blocks):
    """'next N' gives a WIDTH, not a boundary. Walk the ladder in order and turn widths into
    absolute [lo, hi) bounds."""
    cursor = 0.0
    for b in blocks:
        k, lo, hi = b["block"]
        if lo is None:                 # a "next N" width
            lo, hi = cursor, cursor + hi
        b["block"] = (k, lo, hi)
        cursor = hi if hi is not None else cursor
    return blocks


def unit_key(u):
    return re.sub(r"\s+", "", (u or "").strip().lower())


# Does an applies_to name SEVERAL service classes rather than one? "transmission and primary",
# "primary voltage and higher", "primary, secondary". Such a component applies at each of them and
# is not a class of its own; treating it as one invented phantom classes on Duke HLF.
# A SLASH is a separator too, and missing it cost a real number. NIPSCO 631's demand charge
# applies to "transmission/subtransmission" - both classes - but with only "and" and "," matched,
# it fell through to volt_base(), which found "subtransmission" first and bound a $35.74/kW-month
# charge to sub-transmission ALONE. The transmission row then reported DEMAND $0 and an effective
# 5.78 c/kWh on a schedule whose headline charge IS that demand rate: $128.66M a year, missing.
MULTI_CLASS_RE = re.compile(r"\band\b|\bor higher\b|,|/")
assert MULTI_CLASS_RE.search("transmission and primary")
assert MULTI_CLASS_RE.search("primary voltage and higher")
assert MULTI_CLASS_RE.search("primary, secondary")
assert MULTI_CLASS_RE.search("transmission/subtransmission")
assert not MULTI_CLASS_RE.search("transmission (69000 v)")
assert not MULTI_CLASS_RE.search("subtransmission")
assert not MULTI_CLASS_RE.search("primary distribution")

# ---- LARGE-LOAD FRAMEWORKS ------------------------------------------------------------------
# Operator, 2026-08-18: "the large load tariff/s ... are incomplete and don't actually carry out a
# yearly projection or any applicable riders ... these are the rates that most concern us."
#
# Right, and flagging them "modifier - not costed" was the wrong call. I&M's IP-LL is not a
# standalone rate: it has an embedded capacity charge, a longer term and a heavier ratchet, but NO
# energy leg, because it rides ON Tariff I.P. So cost it as its PARENT plus its own components -
# that is what a large customer would actually pay - rather than refusing to cost the one schedule
# a data centre is most likely to take.
LARGE_LOAD_PARENT = {
    ("Indiana Michigan Power Co (Indiana)", "IP-LL"): "IP",
}


def parent_of(util, code):
    """The schedule a large-load framework rides on, if it rides on one."""
    if (util, code) in LARGE_LOAD_PARENT:
        return LARGE_LOAD_PARENT[(util, code)]
    # generic: a "-LL"/"large load" code with no energy leg rides on its stem
    m = re.match(r"^(.*?)[-_ ]?(LL|LARGE)$", (code or "").upper())
    return m.group(1) if m else None


VOLT_ORDER = ["transmission", "subtransmission", "primary", "secondary", "any"]


def volt_base(text):
    """Coarse voltage family, used only for ORDERING and for a display label."""
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


def service_class(applies_to, name):
    """The SERVICE CLASS a component belongs to - not merely its voltage family.

    ⛔ Bucketing into four voltage families was wrong, and it produced a number that was visibly
    backwards: AES HL read 20.64 c/kWh at TRANSMISSION against 10.61 at sub-transmission, because
    "transmission" and "low-load-factor transmission" were treated as the same bucket and their
    rates SUMMED (0.049885 + 0.076468). The same defect hides in Duke HLF, which publishes
    "primary" AND "primary direct", and "transmission (138/230/345 kV)" AND "transmission (69 kV)".

    Those are ALTERNATIVES - a customer takes exactly one - so each distinct `applies_to` is its
    own class. That is the publisher's own distinction, and honouring it costs nothing; inventing
    a coarser grouping is what cost us three wrong numbers.
    """
    a = (applies_to or "").strip()
    if not a:
        b = volt_base(name)
        return (b or "any"), (b or "any")
    key = re.sub(r"\s+", " ", a.lower())
    return key, (volt_base(a) or volt_base(name) or "any")


# Time-of-use periods are NOT alternatives and NOT addends: each rate applies to the kWh that
# falls in its own period, so costing them needs a LOAD SHAPE - what fraction of consumption lands
# on peak, mid-peak and off-peak. We do not hold one. Summing them gives 0.209 $/kWh on Duke's TOU
# schedule, which is nonsense, so a TOU schedule is flagged and not costed.
TOU_RE = re.compile(r"\b(peak|off-peak|mid-peak|on-peak|super off-peak|shoulder)\b", re.I)

# ⭐ A DATA CENTRE IS A FLAT 24/7 LOAD, so a time-of-use schedule IS costable - operator,
# 2026-08-18: "We do have a load shape - data centers work 24/7". With constant load the split
# across periods is not a guess, it is just the HOURS in each period, and the tariff states them:
#   super off-peak  "12-4 am hours"                       -> 4 h/day
#   on-peak         "5-9 pm all year; +6-8 am winter"     -> 4 h/day, +2 h/day in winter
#   off-peak        "all other hours"                     -> the remainder
# Winter is taken as the 5 non-summer months Duke bills that way; the extra morning window adds
# 2 h/day across roughly 151 days.
ONPEAK_H = 4 * 365 + 2 * 151          # 1,762 h/yr
SUPEROFF_H = 4 * 365                  # 1,460 h/yr
OFFPEAK_H = 8760 - ONPEAK_H - SUPEROFF_H
TOU_SHARE = {
    "super_off": SUPEROFF_H / 8760.0,
    "on":        ONPEAK_H / 8760.0,
    "off":       OFFPEAK_H / 8760.0,
}
assert abs(sum(TOU_SHARE.values()) - 1.0) < 1e-9, "TOU period shares must cover the year exactly"


def tou_period(name, basis):
    """Which TOU period a component bills in - or None if it is not time-differentiated."""
    t = f"{name or ''} {basis or ''}".lower()
    if "super off-peak" in t or "12-4 am" in t:
        return "super_off"
    if "mid-peak" in t:
        return "mid"          # a DEMAND period, not an energy slice
    if "off-peak" in t:
        return "off"
    if "on-peak" in t or "peak" in t:
        return "on"
    return None


assert TOU_RE.search("Mid-peak demand charge - primary")
assert TOU_RE.search("Discount (super off-peak) energy charge")
assert not TOU_RE.search("Energy charge - transmission")

# ---- the ACCEPTANCE BENCHMARK -------------------------------------------------------------
# What this utility's INDUSTRIAL customers actually paid, all-in, per EIA-861. A modelled tariff
# bill that lands far from this is wrong, and saying so on the page is the difference between a
# calculation and a claim. CPS_35MW_Rate_Model.xlsx uses the same anchor for the same reason.
#
# ⚠ EIA publishes under its own utility names, which are NOT our names. Mapped EXPLICITLY rather
# than fuzzy-matched: a wrong benchmark silently validates a wrong bill, which is worse than none.
EIA_NAME = {
    "Duke Energy Indiana Inc":            "Duke Energy Indiana, LLC",
    "Northern Indiana Pub Serv Co":       "Northern Indiana Pub Serv Co",
    "Indiana Michigan Power Co (Indiana)": "Indiana Michigan Power Co",
    "Indianapolis Power & Light Co":      "AES Indiana",
    "Southern Indiana Gas & Elec Co":     "Southern Indiana Gas & Elec Co",
}
bench = {}
for r in client.query(f"""
  SELECT utility_name,
         MAX(data_year) AS yr,
         ROUND(100 * SAFE_DIVIDE(SUM(SAFE_CAST(thousand_dollars_2 AS FLOAT64)),
                                 SUM(SAFE_CAST(megawatthours_2 AS FLOAT64))), 2) AS ind_cents
  FROM `{DS}.in_eia861_sales`
  WHERE state = 'IN' AND SAFE_CAST(megawatthours_2 AS FLOAT64) > 100000
  GROUP BY utility_name"""):
    bench[r.utility_name] = {"cents": r.ind_cents, "year": r.yr}
print(f"benchmark utilities: {len(bench)}")

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
            "bill": (None if r.component_type in NOT_A_CHARGE
                     else BILLING.get(uk) if r.rate is not None else None),
            "fuel_base": r.component_type == "fuel_base",
            # months this rate is in force. The books state a season on the row where one applies;
            # absent a season the rate runs all 12 months.
            "months": (4 if (r.season or "").strip().lower().startswith("summer")
                       else 8 if (r.season or "").strip().lower().startswith("non")
                       else 12),
            "reactive": uk in REACTIVE,
            "volt": service_class(r.applies_to, r.name)[0],
            "volt_family": service_class(r.applies_to, r.name)[1],
            "volt_label": (r.applies_to or service_class(r.applies_to, r.name)[1]),
            "tou": bool(TOU_RE.search(r.name or "")),
            "tou_period": tou_period(r.name, r.basis),
            "tou_share": TOU_SHARE.get(tou_period(r.name, r.basis) or "", None),
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
            "block": parse_block(r.basis) if BLOCK_RE.search(r.basis or "") else None,
        }

    scheds = []
    for code, v in sched_codes.items():
        name = next((x.tariff_name for x in v if x.tariff_name), None)
        components = [comp(r, "schedule", name) for r in v]

        # ---- decide, PER FAMILY, whether the publisher is drawing a real sub-class ----------
        # Two failure modes pull in opposite directions and both produced wrong bills:
        #
        #   * Too COARSE. Bucketing everything into four voltage families summed AES HL's
        #     "transmission" and "low-load-factor transmission" rates, and Duke HLF's
        #     "transmission (138/230/345 kV)" and "transmission (69 kV)" - giving transmission a
        #     HIGHER price than secondary, which is backwards.
        #   * Too FINE. Keying on the raw applies_to string fragmented AES, whose energy row says
        #     "transmission" while its demand row says "transmission (138,000/345,000 V)". Same
        #     service, two spellings - and the demand leg fell out of the run, reading 4.99 c/kWh.
        #
        # So sub-class ONLY where a single leg really carries two rates in one family. That is the
        # publisher telling us these are alternatives; one spelling across two legs is not.
        # A schedule often spells the SAME class differently on different legs. AES HL says
        # "transmission (138,000/345,000 V)" on its customer and demand charges but plain
        # "transmission" on its energy charge - four keys where there are two services, so the
        # transmission class ended up holding energy with no demand and read 4.99 c/kWh, while its
        # twin held demand with no energy and vanished.
        #
        # Stripping the parenthetical fixes AES. It would BREAK Duke, whose "transmission
        # (138/230/345 kV)" and "transmission (69 kV)" are genuinely different rates that must not
        # merge. So normalise only where it does not collide: if two distinct raw keys in the same
        # (family, leg) collapse to one normalised key, that family keeps its raw keys.
        def _norm_key(k):
            return re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", "", k or "")).strip(" ,;") or k

        fam_leg, collide = {}, set()
        for c in components:
            if c["origin"] != "schedule" or not c.get("bill") or c.get("block"):
                continue
            fam = c.get("volt_family")
            if not fam or fam == "any":
                continue
            fam_leg.setdefault((fam, c["bill"]), set()).add(c["volt"])
        for (fam, _leg), keys in fam_leg.items():
            if len({_norm_key(k) for k in keys}) < len(keys):
                collide.add(fam)          # normalising would merge two real rates - do not
        split_fams = {fam for (fam, _leg), keys in fam_leg.items() if len(keys) > 1}

        # A component whose applies_to names SEVERAL classes - "transmission and primary",
        # "primary and primary direct", "primary voltage and higher" - applies at each of them. It
        # is not a class of its own, and treating it as one invented phantom service classes on
        # Duke HLF. Mark it class-agnostic so it lands in every run for this schedule.
        # Compiled at module level and self-tested at import. TWICE a regex
        # authored through a shell heredoc reached disk with literal BACKSPACE
        # bytes where \b was intended, matching nothing while grep showed it clean.
        MULTI = MULTI_CLASS_RE
        for c in components:
            fam = c.get("volt_family")
            if fam and fam != "any" and MULTI.search(c.get("volt") or ""):
                # "transmission and primary" applies at BOTH of those - and at nothing else.
                # Making it class-agnostic instead let it bill at secondary too, which put Duke
                # HLF at 44.31 c/kWh (+402%). Record the families it actually names.
                txt = (c.get("volt") or "").lower()
                named = [f for f in ("transmission", "subtransmission", "primary", "secondary")
                         if f in txt or (f == "subtransmission" and "sub-transmission" in txt)]
                if "or higher" in txt or "and higher" in txt:
                    # "primary voltage and higher" = primary and everything above it
                    floor = VOLT_ORDER.index(named[0]) if named else len(VOLT_ORDER)
                    named = [f for f in ("transmission", "subtransmission", "primary", "secondary")
                             if VOLT_ORDER.index(f) <= floor]
                c["volt"] = None
                c["volt_named"] = named or None
                continue
            if not fam or fam == "any":
                c["volt"] = None            # applies at every class (most riders land here)
            elif fam not in split_fams:
                c["volt"] = fam             # one service; merge the spellings
                c["volt_label"] = fam.replace("subtransmission", "sub-transmission").capitalize()
            elif fam not in collide:
                c["volt"] = _norm_key(c["volt"])     # same service, different spellings per leg
                c["volt_label"] = _norm_key(c["volt_label"])
            # else: the publisher really is distinguishing - keep the raw key

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
                # ⛔ STRIP THE PERIODS FIRST. I&M writes its schedule as "Tariff I.P. and
                # CS-IRP2"; tokenising that as-is yields "I" and "P" separately and NEVER "IP", so
                # every one of I&M's eight riders - DSM, ECR, FAC, OSS/PJM, PRA, RAR, SPR, TAX,
                # worth roughly +8.6 $/kW-month between them - silently failed to attach to
                # schedule IP. The bill was short by the entire rider stack and looked fine.
                toks = set(re.findall(r"[A-Za-z]{1,4}\d{0,2}|\d{3}",
                                      a.upper().replace(".", "")))
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
            # ONLY the schedule's own components define the service classes. A rider's
            # applies_to ("participating customers, all classes") is not a service voltage, and
            # treating it as one invented phantom rows priced at 0.18 c/kWh.
            "volt_classes": [
                {"key": k,
                 "label": next(c["volt_label"] for c in components if c["volt"] == k),
                 "family": next(c["volt_family"] for c in components if c["volt"] == k)}
                for k in sorted(
                    {c["volt"] for c in components
                     if c["volt"] and c["volt"] != "any" and c["origin"] == "schedule"},
                    key=lambda k: (
                        VOLT_ORDER.index(next((c["volt_family"] for c in components
                                               if c["volt"] == k), "any"))
                        if next((c["volt_family"] for c in components if c["volt"] == k), "any")
                        in VOLT_ORDER else 99, k))],
            # a schedule with no energy AND no demand charge cannot be costed; say so rather than
            # emitting a confidently wrong total
            # costable = has a billable leg AND no block ladder. Refusing to total a
            # block-rated schedule is the whole point: a wrong dollar figure on a page shown to
            # management is worse than an honest absence.
            "blocked": any(c["block"] for c in billable),
            # a block ladder is costable once its bounds are absolute
            "fuel_base_rate": next((c["rate"] for c in components if c.get("fuel_base")), None),
            "min_kw": eligibility_bounds(components)[0],
            "max_kw": eligibility_bounds(components)[1],
            "large_load": is_large_load(code, name, eligibility_bounds(components)[0]),
            # BLOCKS NO LONGER DISQUALIFY. The ladder parses (26/26) and its slice boundaries
            # are computable from load factor, so a blocked schedule can be costed correctly.
            # What still cannot be costed is a schedule with no energy leg of its own - I&M's
            # IP-LL large-load framework is a MODIFIER on IP, and costing it alone returned an
            # impossible 1.77 c/kWh.
            "modifier": not any(c["bill"] == "energy" for c in billable),
            "tou": any(c.get("tou") for c in billable),
            # TOU IS costable for a flat 24/7 load: the period shares are arithmetic, not a guess.
            "costable": any(c["bill"] == "energy" for c in billable),
        })
    # A large-load framework inherits its parent's billing legs so it can be costed. Its OWN
    # components (embedded capacity charge, ratchet, term) are kept and marked, so the reader can
    # see what the framework adds on top of the underlying schedule.
    by_code = {sc["code"]: sc for sc in scheds}
    for sc in scheds:
        if not sc.get("modifier"):
            continue
        pc = parent_of(util, sc["code"])
        parent = by_code.get(pc)
        if not parent:
            continue
        # Inherit the parent's SCHEDULE legs AND its attached RIDERS. Taking only the schedule
        # legs left I&M IP-LL with energy $0 and zero riders, yet it still printed 7.06 c/kWh -
        # a confident number built from a demand charge and nothing else. A large-load framework
        # rides on the whole of its parent, riders included; that is what the customer pays.
        inherited = [dict(c, origin=(f"{pc} (underlying schedule)" if c["origin"] == "schedule"
                                     else f"{c['origin']} (via {pc})"))
                     for c in parent["components"] if c.get("bill")]
        sc["components"] = sc["components"] + inherited
        sc["inherits_from"] = pc
        sc["modifier"] = False
        billable2 = [c for c in sc["components"] if c.get("bill")]
        sc["n_components"] = len(sc["components"])
        sc["n_billable"] = len(billable2)
        sc["n_riders_attached"] = len({c["origin"] for c in sc["components"]
                                       if c["origin"] != "schedule"
                                       and not str(c["origin"]).endswith("(underlying schedule)")})
        sc["costable"] = any(c["bill"] == "energy" for c in billable2)
        sc["volt_classes"] = parent["volt_classes"]
        sc["fuel_base_rate"] = sc.get("fuel_base_rate") or parent.get("fuel_base_rate")
        if sc.get("min_kw") is None:
            sc["min_kw"] = parent.get("min_kw")
        if sc.get("max_kw") is None:
            sc["max_kw"] = parent.get("max_kw")

    scheds.sort(key=lambda s: (not s.get("large_load"), not s["costable"],
                               -s["n_billable"], s["code"]))

    riders_only = [{"code": c, "name": next((x.tariff_name for x in v if x.tariff_name), c),
                    "n": len(v)} for c, v in rider_codes.items()]
    n_sched += len(scheds)
    n_rider += len(riders_only)
    b = bench.get(EIA_NAME.get(util, util))
    utilities.append({
        "utility": util, "is_iou": util in IOU,
        # so the dossier can answer "what can a load of this size actually take here?" directly
        "eligibility": [{"code": sc["code"], "name": sc["name"],
                         "min_kw": sc.get("min_kw"), "max_kw": sc.get("max_kw"),
                         "costable": sc.get("costable"), "tou": sc.get("tou"),
                         "large_load": sc.get("large_load"),
                         "inherits_from": sc.get("inherits_from")}
                        for sc in scheds],
        # None where EIA publishes no industrial sales for this utility - most municipals and
        # co-ops. An absent benchmark means the calculation cannot be judged, and the page says so
        # rather than implying it passed.
        "benchmark_cents": (b or {}).get("cents"),
        "benchmark_year": (b or {}).get("year"),
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
