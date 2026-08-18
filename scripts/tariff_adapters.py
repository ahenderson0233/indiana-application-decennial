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
        "schedule_alias": {"IP": "IP", "CS-IRP2": None, "GS": "GS"},
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
            "on the customer and demand charges, plain 'transmission' on energy."),
        "split_classes": ["transmission"],          # LLF transmission is a separate service
        "merge_classes": ["subtransmission", "primary", "secondary"],
        "llf_classes": ["low-load-factor transmission"],
        "large_load": ["HL"],
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
            "HID the +402% error behind a bogus exclusion."),
        "split_classes": ["transmission", "primary"],
        "multi_class_phrases": ["transmission and primary", "primary voltage and higher",
                                "primary and primary direct"],
        "bounds_from_name_only": True,   # its basis text mixes floor and ceiling wording
        "large_load": ["HLF"],
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
        # 631's own components leave no class-bearing row once the slash-joined demand charge is
        # (correctly) made class-agnostic, so the classes fell back to junk like "all tiers" and
        # "aggregated premises with BTM generation". Its eligibility states the truth plainly:
        # transmission / sub-transmission only. Declare it rather than infer it.
        "explicit_classes": {"631": ["transmission", "subtransmission"]},
        "not_large_load": ["624"],
        "large_load": ["631"],
        "merge_classes": ["transmission", "subtransmission", "primary", "secondary"],
    },

    # -----------------------------------------------------------------------------------------
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
    t = (text or "").lower()
    for phrase in adapter(utility).get("multi_class_phrases", []):
        if phrase in t:
            return True
    for sep in separators(utility):
        if sep in t:
            return True
    return bool(re.search(r"\band\b|\bor higher\b|,", t))


def explicit_classes(utility, code):
    """Service classes this publisher states outright, when its components do not carry them."""
    return adapter(utility).get("explicit_classes", {}).get(code)


def describe(utility):
    """The convention note, for the page and for whoever reads this next."""
    return adapter(utility).get("notes")
