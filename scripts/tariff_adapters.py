"""PER-UTILITY tariff conventions. One declarative adapter each; shared arithmetic elsewhere.

Operator, 2026-08-18: "It may be best to just write code for the individual utilities rather than
trying to aggregate them all into one code block."

WHY THIS FILE EXISTS
--------------------
Nine costing defects were found on 2026-08-18 and **every one was a generic rule meeting a house
convention**. Worse, several fixes for one utility broke another: separating AES's low-load-factor
class fragmented its demand leg, and making multi-class components class-agnostic put Duke HLF at
+402%. A single matcher cannot satisfy five publishers who each write their tariff differently, and
19 municipals are queued behind them.

So each utility declares its own conventions here. The cost is more code; the benefit is that a
change for one utility CANNOT break another, and each adapter is independently checkable against
that publisher's book.

WHAT AN ADAPTER MAY DECLARE
---------------------------
  schedule_alias   text a rider uses for a schedule -> the schedule's code
  applies_to_norm  callable, cleans this publisher's applies_to before tokenising
  class_separators extra characters this publisher uses to join service classes
  split_classes    families this publisher genuinely subdivides (do not merge the spellings)
  merge_classes    families this publisher spells inconsistently across legs (do merge)
  parent           large-load framework -> the schedule it rides on
  large_load       schedule codes that ARE large-load, regardless of name
  not_large_load   schedule codes whose NAME says large but which are not
  notes            why, in the publisher's own terms - this is the part that survives

Everything is optional. A utility with no adapter falls back to the generic behaviour, which is
what the 19 municipals do until each is given one.
"""
import re

# ⚠ A COMMA BETWEEN TWO DIGITS IS A THOUSANDS SEPARATOR, NOT A CLASS SEPARATOR.
#
# Duke writes its two alternative transmission rates as "transmission (138,000/230,000/345,000 V)"
# and "transmission (69,000 V)". The generic multi-class test below treats a comma as a list
# separator - correctly, for "primary, secondary" - and so read the DIGIT-GROUP commas inside
# "138,000" as a class list. Both rates were marked class-agnostic-within-transmission, landed in
# the same run, and were SUMMED: 23.59 + 20.51 $/kW-month and 0.046775 + 0.044002 $/kWh, putting
# Duke HLF at 16.96 c/kWh against an 8.83 c benchmark (+92%).
#
# It is the same shape as the AES low-load-factor defect - two ALTERNATIVE rates for one service
# added together - reached by a different route. Compiled at module level and self-tested at
# import, because a pattern that silently stops matching is exactly how this went wrong before.
DIGIT_COMMA_RE = re.compile(r"(?<=\d),(?=\d)")
assert DIGIT_COMMA_RE.sub("", "transmission (138,000/230,000/345,000 v)") \
    == "transmission (138000/230000/345000 v)"
assert DIGIT_COMMA_RE.sub("", "primary, secondary") == "primary, secondary"
assert DIGIT_COMMA_RE.sub("", "shall not supply demand in excess of 25,000 kw") \
    == "shall not supply demand in excess of 25000 kw"

# =============================================================================================
ADAPTERS = {

    # -----------------------------------------------------------------------------------------
    "Indiana Michigan Power Co (Indiana)": {
        "notes": (
            "Writes its schedule as 'Tariff I.P.' WITH PERIODS. Tokenising that yields 'I' and 'P' "
            "and never 'IP', so all EIGHT riders - DSM, ECR, FAC, OSS/PJM, PRA, RAR, SPR, TAX, "
            "together about +8.6 $/kW-month - silently failed to attach and the bill was short by "
            "the entire rider stack while looking perfectly plausible. "
            "IP-LL is a large-load FRAMEWORK: it has an embedded capacity charge, a 12-year term "
            "and an 80% ratchet but NO energy leg of its own, because it rides on I.P. Costing it "
            "alone returned an impossible 1.77 c/kWh."),
        "applies_to_norm": lambda s: (s or "").replace(".", ""),
        # It joins classes with a SLASH as well, exactly as NIPSCO does:
        # "primary/subtransmission/transmission" on G.S.'s $210/month service charge. Unrecognised,
        # volt_base() matched "subtransmission" first, bound the charge to that class alone, and
        # in doing so INVENTED a sub-transmission service that G.S. prices no energy at.
        "class_separators": ["/"],
        "schedule_alias": {"IP": "IP", "CS-IRP2": None, "GS": "GS"},
        # ⛔ G.S. GETS NO RIDERS, AND THAT IS AN EXTRACTION GAP, NOT A FACT ABOUT THE TARIFF.
        # Every extracted I&M rider factor is scoped "Tariff I.P. and CS-IRP2" - the I.P. column -
        # while I&M's own Sheet 44 roster states that eight riders apply to ALL standard-service
        # schedules, G.S. among them. Riders are filed per schedule with different factors, so
        # borrowing I.P.'s numbers would be inventing them.
        # A $0 riders column asserts "this schedule has no riders", which the book contradicts.
        # Declared here so the page says NOT HELD and treats the total as a FLOOR.
        "riders_not_held": ["GS"],
        # G.S. prices energy only at transmission and secondary, yet carries demand charges at
        # primary and sub-transmission too. A tariff cannot serve a class it never prices energy
        # at, so those two are extraction gaps rather than services on offer.
        "classes_not_priced": {"GS": ["primary", "subtransmission"]},
        "parent": {"IP-LL": "IP"},
        "large_load": ["IP-LL"],
        "merge_classes": ["transmission", "subtransmission", "primary", "secondary"],
    },

    # -----------------------------------------------------------------------------------------
    "Indianapolis Power & Light Co": {
        "notes": (
            "Publishes a separate LOW-LOAD-FACTOR variant of transmission service, for customers "
            "under ~15% annual load factor. Reading 'low-load-factor transmission' and plain "
            "'transmission' as one family SUMMED them (0.049885 + 0.076468 $/kWh), which made "
            "transmission read 20.64 c/kWh - DEARER than secondary. A price ladder that inverts is "
            "always the tell. "
            "It also spells the same class differently per leg: 'transmission (138,000/345,000 V)' "
            "on the customer and demand charges, plain 'transmission' on energy. "
            "CSC is not a rate: 'All charges - per contract', with no rate at all. Its only "
            "numbers came from riders that happened to name it, which totalled $4.02M/yr out of "
            "nothing. PH (Process Heating) is genuinely ENERGY-ONLY - two energy blocks and a "
            "customer charge, no demand charge anywhere in the schedule - so a $0 demand column "
            "there is the tariff, not a matching failure."),
        "split_classes": ["transmission"],          # LLF transmission is a separate service
        "merge_classes": ["subtransmission", "primary", "secondary"],
        "llf_classes": ["low-load-factor transmission"],
        "large_load": ["HL"],
        "by_contract": ["CSC"],                     # negotiated, not published
    },

    # -----------------------------------------------------------------------------------------
    "Duke Energy Indiana Inc": {
        "notes": (
            "The most inconsistent of the five and the one that broke every generic rule. It "
            "subdivides transmission into TWO real rates - '(138,000/230,000/345,000 V)' and "
            "'(69,000 V)' - and primary into 'primary' and 'primary direct'; those are "
            "alternatives and must never merge. It ALSO writes multi-class strings such as "
            "'transmission and primary' and 'primary voltage and higher', which apply at each "
            "named class and are not classes themselves; treating them as class-agnostic instead "
            "let them bill everywhere and put HLF at +402%. "
            "And its 'Minimum specified capacity' row states a 25 kW FLOOR in a basis that also "
            "contains the word 'maximum' - read as a ceiling, it excluded HLF from every load and "
            "HID the +402% error behind a bogus exclusion. "
            "It writes kV lists with THOUSANDS SEPARATORS - 'transmission "
            "(138,000/230,000/345,000 V)' - and those digit-group commas were read as a class "
            "list, which merged its two ALTERNATIVE transmission rates and summed them: +92%. "
            "It splits load factor by SCHEDULE (HLF vs LLF/LLF-B) where AES splits it by class, "
            "and it keeps one CLOSED class, 'secondary (closed class)', that no new customer can "
            "take."),
        "split_classes": ["transmission", "primary"],
        "multi_class_phrases": ["transmission and primary", "primary voltage and higher",
                                "primary and primary direct",
                                # ⚠ Its CONNECTION charge spans every transmission tier at once -
                                # "transmission (69/138/230/345 kV)" - while its energy and demand
                                # charges name ONE tier each. Read as a class of its own it became
                                # a THIRD, phantom transmission class holding nothing but the
                                # $855.37/month connection charge: demand $0, energy $0, and a
                                # 0.77 c/kWh headline that led the schedule's range. It is one
                                # charge that applies at whichever transmission tier you take.
                                "transmission (69/138/230/345 kv)"],
        "bounds_from_name_only": True,   # its basis text mixes floor and ceiling wording
        "large_load": ["HLF"],
        # ⛔ ITS TOU SCHEDULE WAS GETTING NO RIDERS AT ALL, and that made it look like the best
        # deal Duke offers. Every Duke rider is filed TWICE - once for Rate HLF in $/kW-month and
        # once for Rate LLF in $/kWh - because HLF is demand-led and LLF is energy-led, so the
        # same tracker is recovered through a different billing determinant. The riders name
        # "Rate HLF" / "Rate LLF"; the schedule code is "HLF/LLF-TOU", which matches neither, so
        # its stack came to $0 and it rendered at 7.45c (-16%), the CHEAPEST Duke row on the page.
        #
        # ⚠ The obvious fix is wrong: aliasing it to BOTH would attach the $/kW-month AND the
        # $/kWh version of all ten trackers and double-recover them. HLF/LLF-TOU is one schedule
        # serving two customer types, and a customer is one or the other. At 85% load factor ours
        # is an HLF customer, so the HLF set applies and the LLF set does not. Stated on the page.
        "rider_alias": {"HLF/LLF-TOU": ["HLF"],     # a 24/7 load takes TOU as an HLF customer
                        "LLF-B": ["LLF"]},          # Tariff 10-B is the secondary LLF variant
        # grandfathered - present in the book, not available to a new load
        "closed_classes": ["secondary (closed class)"],
        # LOW load factor services: LLF/LLF-B are the counterpart to HLF, not alternatives to it
        "llf_schedules": ["LLF", "LLF-B"],
    },

    # -----------------------------------------------------------------------------------------
    "Northern Indiana Pub Serv Co": {
        "notes": (
            "Joins service classes with a SLASH: 'transmission/subtransmission'. Unrecognised, "
            "volt_base() matched 'subtransmission' first and bound Rate 631's $35.74/kW-month "
            "demand charge to sub-transmission ALONE - the transmission row then showed DEMAND $0 "
            "and 5.78 c/kWh on a schedule whose headline charge IS that demand rate. "
            "624/632/633 use INVERTED block ladders that deliberately price high-load-factor "
            "customers out, so a 24/7 load costing 15-21 c/kWh there is the tariff working, not an "
            "error - but all three also carry a 25,000 kW CEILING, so a data centre cannot take "
            "them at all. 624 is named 'General Service - LARGE' and is NOT a large-load tariff; "
            "631 is."),
        "class_separators": ["/"],
        # ⛔ NIPSCO PUBLISHES OPTIONAL SERVICES INSIDE ITS SCHEDULES, and they were being billed
        # as if firm. "Maintenance service" is capacity a customer confirms for planned outage
        # work - 0.62 $/kW/DAY in Jan/May/Dec, 0.35 in the shoulder months, NOT AVAILABLE
        # June-September and capped at 60 days per rolling 12 months. Charged as a 365-day firm
        # demand it added $106.22M/yr to Rate 632 for a service nobody elected, and drove it to
        # +241%. "Back-up service" is cogeneration stand-by, priced at Real-Time LMP plus a
        # non-fuel adder. 631's affiliate premium applies only to energy moved between commonly
        # owned adjacent premises with behind-the-meter generation.
        # None of these is part of a firm 24/7 bill. They are shown, not summed, and said to be
        # excluded - the same treatment reactive charges get, and for the same reason.
        "conditional_applies_to": ["maintenance service",
                                   "back-up service",
                                   "back-up service (cogeneration customers)",
                                   "aggregated premises with btm generation"],
        # 631's own components leave no class-bearing row once the slash-joined demand charge is
        # (correctly) made class-agnostic, so the classes fell back to junk like "all tiers" and
        # "aggregated premises with BTM generation". Its eligibility states the truth plainly:
        # transmission / sub-transmission only. Declare it rather than infer it.
        # 631, 632 and 633 all state "transmission/subtransmission" eligibility and put their
        # demand charge on that same slash-joined string. Once the slash is (correctly) read as a
        # separator, the demand row becomes class-agnostic and NO row is left carrying a class -
        # so volt_classes came out EMPTY, the renderer had no class to match against, and 633's
        # $24.72/kW-month demand charge was dropped entirely: DEMAND $0 on a demand-led schedule.
        # 631 had already been fixed this way; 632 and 633 have the identical convention.
        "explicit_classes": {"631": ["transmission", "subtransmission"],
                             "632": ["transmission", "subtransmission"],
                             "633": ["transmission", "subtransmission"]},
        "not_large_load": ["624"],
        "large_load": ["631"],
        "merge_classes": ["transmission", "subtransmission", "primary", "secondary"],
    },

    # -----------------------------------------------------------------------------------------
    # ----------------------------- MUNICIPALS AND CO-OPS (BACKLOG G55) -----------------------
    # The first four to be given adapters. The other 15 costable municipals and the 51 stubs are
    # still on the generic path - see G55. Each block below is one publisher's convention, found
    # by running scripts/audit_tariff_costing.py --all and reading that utility's own book.
    "City of Auburn, Indiana (Utility Company)": {
        "notes": (
            "Joins its two service classes with the word OR - 'primary or secondary' - on the "
            "customer and demand charges, while pricing energy at each class separately. "
            "Unrecognised, that string became a THIRD service class of its own, and it was the "
            "only one the $17.10/kVA-month demand charge applied at: the real primary and "
            "secondary rows both showed DEMAND $0. Its demand is billed in kVA, like SIGECO's."),
        "class_separators": [" or "],
        "demand_unit": "kva",
        "assumed_power_factor": 1.0,
    },

    "Southeastern Indiana R E M C": {
        "notes": (
            "Its season column says 'all' on three rows whose NAME states a three-month window - "
            "Summer Production (Jun-Aug), Winter Production (Dec-Feb) and Summer Power Supply. "
            "Billed twelve months each, they overstate the bill by four times their real "
            "exposure. UIPS-1 is a genuinely four-part demand rate - delivery, transmission, and "
            "summer/winter production are DIFFERENT determinants and do add up - so only the two "
            "production legs are seasonal, not the whole stack. "
            "C-5 forks by load factor: 15.50 $/kW summer for customers at or above 300 kWh/kW, "
            "8.10 for those below. Those are ALTERNATIVES; a 24/7 load takes the first."),
        "season_months": {"summer production billing demand": 3,
                          "winter production billing demand": 3,
                          "summer power supply demand": 3},
        # C-5 forks INSIDE the schedule on annual load factor: 15.50 $/kW summer for customers at
        # or above 300 kWh/kW, 8.10 for those below, and both carry season='summer'. They are
        # ALTERNATIVES, so applying both charged one customer twice in the same four months. A
        # 24/7 load is unambiguously the first fork; the second is excluded and said to be.
        # ⚠ Both forks share the NAME "Demand charge - June through August" and differ only by
        # rate, so the name cannot tell them apart. The BASIS can: the low fork's begins
        # "LLF fork (<300 kWh/kW)". Match on what actually distinguishes them.
        "low_lf_basis": ["llf fork"],
    },

    "City of Anderson, Indiana (Utility Company)": {
        "notes": (
            "Writes its block ladder in the component NAME - 'Energy charge - first 200 hours "
            "use', 'over 200 hours use' - and leaves the basis as the bare words 'hours-use "
            "block'. Read from the basis alone the ladder is invisible and its two rates were "
            "SUMMED, which is the NIPSCO 57.94 c/kWh defect reached from the other direction."),
    },

    "City of Logansport, Indiana (Utility Company)": {
        "notes": (
            "Same block-in-the-name convention as Anderson, but measured in kWh per kVA of "
            "billing demand: 'first 200 kWh/kVAD', 'next 100', 'over 300'. The NAME carries the "
            "bounds and the BASIS carries the kind ('hours-use block'), so neither alone is "
            "enough - both are read together."),
    },

    "City of Lebanon, Indiana (Utility Company)": {
        "notes": (
            "Block ladder in the name, on hours-use of billing maximum: 'first 300 hours use', "
            "'over 300 hours use'. Summed, they overstated PPL's energy leg."),
    },

    "Southern Indiana Gas & Elec Co": {
        "notes": (
            "Bills demand in kVA rather than kW, so a power factor is needed to convert; PF 1.0 is "
            "assumed and stated on the surface. Its HLF is transmission-only with a 4,500 kVA "
            "floor and a demand-ONLY design - no base energy charge at all - which is why a naive "
            "reader sees a low c/kWh and misreads it as cheap."),
        "demand_unit": "kva",
        "assumed_power_factor": 1.0,
        "large_load": ["LP", "HLF"],
        "merge_classes": ["transmission", "subtransmission", "primary", "secondary"],
    },
}

# The 19 municipals and co-ops have NO adapter yet, and that is the open half of the tariff work
# (BACKLOG G55). They are 19 separate publishers; expect 19 sets of conventions, and expect the
# generic fallback to be wrong for most of them until each is looked at.
NO_ADAPTER_YET = "municipals and co-ops - see BACKLOG G55"


def adapter(utility):
    return ADAPTERS.get(utility, {})


def norm_applies_to(utility, text):
    """Apply this publisher's cleanup before any tokenising or class matching."""
    fn = adapter(utility).get("applies_to_norm")
    return fn(text) if fn else (text or "")


def separators(utility):
    """Characters this publisher uses to join several classes in one applies_to."""
    return adapter(utility).get("class_separators", [])


def forced_parent(utility, code):
    return adapter(utility).get("parent", {}).get(code)


def large_load_override(utility, code):
    """True / False to force, None to fall back to the generic test."""
    a = adapter(utility)
    if code in a.get("not_large_load", []):
        return False
    if code in a.get("large_load", []):
        return True
    return None


def family_policy(utility, family):
    """'split' | 'merge' | None - whether this publisher subdivides this voltage family."""
    a = adapter(utility)
    if family in a.get("split_classes", []):
        return "split"
    if family in a.get("merge_classes", []):
        return "merge"
    return None


def bounds_name_only(utility):
    return bool(adapter(utility).get("bounds_from_name_only"))


def is_multi_class(utility, text):
    """Does this applies_to name several classes, by this publisher's conventions?"""
    # digit-group commas first, or "138,000" reads as a class list - see DIGIT_COMMA_RE
    t = DIGIT_COMMA_RE.sub("", (text or "").lower())
    for phrase in adapter(utility).get("multi_class_phrases", []):
        if phrase in t:
            return True
    for sep in separators(utility):
        if sep in t:
            return True
    return bool(re.search(r"\band\b|\bor higher\b|,", t))


assert not is_multi_class("Duke Energy Indiana Inc",
                          "transmission (138,000/230,000/345,000 V)")
assert not is_multi_class("Duke Energy Indiana Inc", "transmission (69,000 V)")
assert is_multi_class("Duke Energy Indiana Inc", "primary and primary direct (2,400-34,500 V)")
assert is_multi_class("Northern Indiana Pub Serv Co", "transmission/subtransmission")


def is_low_lf_component(utility, basis):
    """Is this the LOW-load-factor fork of a charge that forks inside one schedule?

    Southeastern Indiana REMC's C-5 is the case: 15.50 $/kW summer at or above 300 kWh/kW, 8.10
    below, both carrying season='summer' and the SAME component name. They are alternatives, so
    applying both charged one customer twice across the same four months. Matched on the basis,
    which is the only field that distinguishes them.
    """
    b = (basis or "").strip().lower()
    if not b:
        return False
    return any(p in b for p in adapter(utility).get("low_lf_basis", []))


assert is_low_lf_component("Southeastern Indiana R E M C",
                           "LLF fork (<300 kWh/kW); non-summer $7.10")
assert not is_low_lf_component("Southeastern Indiana R E M C",
                               "class: >=75 kVA transformer capacity")
assert not is_low_lf_component("Duke Energy Indiana Inc", "LLF fork (<300 kWh/kW)")


def season_months(utility, name, season):
    """How many months a year this rate is in force.

    The `season` column is authoritative when it commits to one - "summer" or "non_summer". When
    it says "all" it is a DEFAULT rather than a statement, and a publisher may declare the real
    window for a named component. Southeastern Indiana REMC is the case that found this: three
    rows whose names state a three-month window carry season='all' and were billed twelve.

    ⛔ Nothing is inferred from a name unless that utility's own adapter says to. Reading seasons
    out of names generally would repeat the mistake that gave NIPSCO's "Transmission charge" a
    transmission service class.
    """
    sn = (season or "").strip().lower()
    if sn.startswith("summer"):
        return 4
    if sn.startswith("non"):
        return 8
    declared = adapter(utility).get("season_months", {})
    if declared:
        key = (name or "").strip().lower()
        for phrase, months in declared.items():
            if phrase in key:
                return months
    return 12


assert season_months("Southeastern Indiana R E M C", "Summer Production billing demand",
                     "all") == 3
assert season_months("Southeastern Indiana R E M C", "Delivery billing demand", "all") == 12
assert season_months("Duke Energy Indiana Inc", "Summer Production billing demand", "all") == 12
assert season_months("Duke Energy Indiana Inc", "anything", "summer") == 4


def rider_alias(utility, code):
    """Extra names a rider may use for THIS schedule.

    A rider names the rate it belongs to in the publisher's words, which is not always the
    schedule's code. Duke files every tracker against "Rate HLF" and "Rate LLF" while its
    time-of-use schedule is coded "HLF/LLF-TOU" and matched neither, so it carried no riders and
    read as Duke's cheapest option.

    ⚠ This maps to ONE scope, never a union. Duke's HLF and LLF factors are the same tracker on
    different billing determinants ($/kW-month against $/kWh), so attaching both double-recovers.
    """
    return adapter(utility).get("rider_alias", {}).get(code, [])


def riders_not_held(utility, code):
    """True when the book says riders apply to this schedule but we hold no factor for it.

    Different from "this schedule has no riders", and the page must not render the two the same
    way. I&M's Sheet 44 roster names eight riders applying to all standard-service schedules while
    every extracted factor is scoped to I.P./CS-IRP2 - so G.S.'s stack is unknown, not zero.
    """
    return code in adapter(utility).get("riders_not_held", [])


def classes_not_priced(utility, code):
    """Service classes this schedule lists but never prices - an extraction gap, not an option."""
    return adapter(utility).get("classes_not_priced", {}).get(code, [])


def closed_classes(utility):
    """Service classes this publisher has CLOSED to new customers.

    A grandfathered class is not an option a siter can choose, and pricing one implies it is.
    Declared per publisher because the wording is the publisher's: Duke is the only one in the
    estate that marks a class this way, writing "secondary (closed class)".
    """
    return adapter(utility).get("closed_classes", [])


def is_by_contract(utility, code):
    """A 'schedule' whose rate is negotiated rather than published.

    AES's CSC (Customer Specific Contracts) states "All charges - per contract" and carries no
    rate at all. It is a PROCESS, not a price; totalling it produced a $4.02M/yr figure built
    from nothing but the riders that happened to name it.
    """
    return code in adapter(utility).get("by_contract", [])


def is_conditional(utility, applies_to):
    """Is this an OPTIONAL service the customer has not elected, rather than part of a firm bill?

    Declared per publisher because it is the publisher who decides what rides inside a schedule.
    NIPSCO puts maintenance service, back-up service and an affiliate premium in with the firm
    rates; treating those as mandatory added $106.22M/yr to Rate 632 alone.
    """
    a = (applies_to or "").strip().lower()
    if not a:
        return False
    return any(a == p or a.startswith(p)
               for p in adapter(utility).get("conditional_applies_to", []))


assert is_conditional("Northern Indiana Pub Serv Co", "maintenance service")
assert is_conditional("Northern Indiana Pub Serv Co", "back-up service (cogeneration customers)")
assert not is_conditional("Northern Indiana Pub Serv Co", "transmission/subtransmission")
assert not is_conditional("Duke Energy Indiana Inc", "maintenance service")   # not declared there


def is_low_load_factor(utility, code):
    """A whole SCHEDULE that only serves low-load-factor customers.

    Publishers split load factor two different ways and the difference matters. AES makes it a
    SERVICE CLASS inside one schedule ("low-load-factor transmission"), which the renderer
    already drops above 15% LF. Duke makes it a SCHEDULE - LLF and LLF-B against HLF - and those
    were being priced at 85% load factor, a service the customer cannot take.
    """
    return code in adapter(utility).get("llf_schedules", [])


def explicit_classes(utility, code):
    """Service classes this publisher states outright, when its components do not carry them."""
    return adapter(utility).get("explicit_classes", {}).get(code)


def describe(utility):
    """The convention note, for the page and for whoever reads this next."""
    return adapter(utility).get("notes")
