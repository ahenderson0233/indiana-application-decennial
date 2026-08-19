"""G89 - when does a data-centre moratorium actually LAPSE?

    python scripts/build_dc_action_expiry.py

Operator, 2026-08-19: *"We should probably dive deeper into the expiration dates of DC
bans/moratoriums, and if none exists, we should be able to estimate/derive an expiration date
based on the data we currently hold (e.g., one year moratorium is 365 days from the effective
date)."*

⭐ WHY IT MATTERS: a county with a moratorium expiring in four months is a DIFFERENT site from one
with an open-ended ban, and the map paints both the same red today. The lapse date is the single
most decision-relevant fact about a temporary restriction and we were not publishing it.

⛔ THE HONEST YIELD IS SMALL, AND THAT IS THE FINDING. Twelve moratorium-or-ban actions (the
filter takes bans too, because an outright prohibition is the same question with no end date):

    published end date      2   Merrillville (2026-06-01 to 2027-05-31), Whitley (to 2027-07-06)
    DERIVABLE               1   Starke - adopted 2025-12-15 with "not to exceed one (1) year",
                                so it lapses 2026-12-15
    OPEN-ENDED, stays NULL  1   Huntington - "until the HCPC has time to develop new regulations"
    duration but NO ANCHOR  1   Floyd/New Albany - "up to one year", no effective date recorded
    nothing stated          7   Cass, Dearborn, Franklin, Fulton, Marshall (x2 - a ban and an
                                already-expired moratorium), Porter/Valparaiso

    => 3 of 12 carry a date at all, and only 3 of the 12 are currently dated-and-live.

So this adds ONE date. ⛔ That is the correct answer, not a shortfall to engineer around. The
alternative - anchoring Floyd's "one year" to the date the city ANNOUNCED the ban, or treating
Fulton's silence as a default 12 months - would manufacture a lapse date a developer might plan
around. **Inventing a date here is worse than admitting there is none.**

⚠ A DERIVED DATE MUST NEVER STYLE AS A PUBLISHED ONE. `expiry_basis` carries which it is on every
row, and the surface is required to badge it.

⚠ AN OPEN-ENDED MORATORIUM IS NOT A MISSING DATE. "Until the plan commission finishes new
regulations" is a fully specified condition that simply has no calendar date. It gets its own
basis value and quotes the condition, so it never reads as "we failed to find one".

WRITES `indiana_app.in_dc_action_expiry`. Reads indiana_app only.
⛔ Does NOT modify `in_dc_actions_resolved` - those columns are VERIFIED fields and a re-check may
confirm or advance a row, never silently overwrite one.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import re
import datetime
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_dc_action_expiry"
client = bigquery.Client(project="energy-platfrom")

# ---- duration vocabulary, declarative -----------------------------------------------------
# ⚠ Written and self-tested here rather than as a BigQuery regex: these patterns have to cope
# with "one (1) year", "1-year", "a 1 year ban" and "twelve (12) months" in the same corpus.
DURATIONS = [
    (re.compile(r"\b(?:two|2)\s*(?:\(\s*2\s*\))?[-\s]*year", re.I), 730, "2 years"),
    (re.compile(r"\b(?:eighteen|18)\s*(?:\(\s*18\s*\))?[-\s]*month", re.I), 548, "18 months"),
    (re.compile(r"\b(?:twelve|12)\s*(?:\(\s*12\s*\))?[-\s]*month", re.I), 365, "12 months"),
    (re.compile(r"\b(?:one|1|a)\s*(?:\(\s*1\s*\))?[-\s]*year", re.I), 365, "1 year"),
    (re.compile(r"\b(?:nine|9)\s*(?:\(\s*9\s*\))?[-\s]*month", re.I), 274, "9 months"),
    (re.compile(r"\b(?:six|6)\s*(?:\(\s*6\s*\))?[-\s]*month", re.I), 180, "6 months"),
    (re.compile(r"\b(?:ninety|90)\s*(?:\(\s*90\s*\))?[-\s]*day", re.I), 90, "90 days"),
]
# ⚠ ORDER MATTERS against the duration list: a text can say BOTH "one year" and "until the
# commission acts" (Floyd says almost exactly that). Open-ended wins, because a renewable or
# condition-terminated period has no reliable calendar end.
OPEN_ENDED = re.compile(
    r"until\s+(?:the|such\s+time|further|new\s+regulations)|"
    r"until\s+\w+\s+(?:has|have)\s+time|"
    r"pending\s+(?:the\s+)?(?:adoption|completion|development)",
    re.I)


def _selftest():
    def dur(t):
        for rx, days, label in DURATIONS:
            if rx.search(t):
                return days, label
        return None, None
    assert dur("not to exceed one (1) year")[0] == 365
    assert dur("a 1 year ban on the construction")[0] == 365
    assert dur("approved a One-Year Moratorium")[0] == 365
    assert dur("for six (6) months")[0] == 180
    assert dur("no duration at all here")[0] is None
    assert OPEN_ENDED.search("until the HCPC has time to develop new regulations")
    assert not OPEN_ENDED.search("shall continue for a time period not to exceed one (1) year")
    # 2 years must not be swallowed by the 1-year pattern
    assert dur("a two (2) year moratorium")[1] == "2 years"


_selftest()

rows = list(client.query(f"""
  SELECT county, jurisdiction, confirmed_action_type, verified_effective_from,
         verified_effective_to, expiry_condition_verbatim, verbatim_snippet, date_note,
         posture_renderable, official_url
  FROM `{DS}.in_dc_actions_resolved`
  WHERE LOWER(IFNULL(confirmed_action_type,'')) LIKE '%morator%'
     OR LOWER(IFNULL(confirmed_action_type,'')) LIKE '%ban%'
  ORDER BY county"""))
print(f"{len(rows)} moratorium/ban actions\n")

TODAY = datetime.date.today()


def as_date(v):
    """⚠ `verified_effective_from` / `_to` are STRING columns, not DATE. Assuming otherwise threw
    'str object has no attribute isoformat'. Anything that is not a clean ISO date returns None
    rather than a guess -- a partial date here would propagate into a derived lapse date."""
    if v is None:
        return None
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    s = str(v).strip()
    if not s:
        return None
    try:
        return datetime.date.fromisoformat(s[:10])
    except ValueError:
        return None


out = []
for r in rows:
    eff_from = as_date(r.verified_effective_from)
    eff_to = as_date(r.verified_effective_to)
    text = " ".join(x for x in (r.expiry_condition_verbatim, r.verbatim_snippet) if x)
    days = label = None
    for rx, d, lab in DURATIONS:
        if rx.search(text):
            days, label = d, lab
            break
    open_ended = bool(OPEN_ENDED.search(text))

    end, basis, note = eff_to, None, None
    if eff_to is not None:
        basis = "published"
        note = "The instrument states this end date. Not derived."
    elif open_ended:
        basis = "open_ended"
        note = ("No calendar end. The instrument ties the lapse to a CONDITION, quoted in "
                "expiry_condition_verbatim. This is a specified condition, not a missing date.")
    elif days and eff_from is not None:
        end = eff_from + datetime.timedelta(days=days)
        basis = "derived"
        note = (f"DERIVED, not published: effective {eff_from} plus the "
                f"{label} stated in the instrument. Treat as indicative - a body that adopted a "
                f"moratorium can extend it, and several here already have.")
    elif days:
        basis = "duration_without_anchor"
        note = (f"The instrument states a {label} duration but we hold no verified effective "
                f"date to count from, so no end date can be computed. Anchoring it to the "
                f"announcement date would invent precision we do not have.")
    else:
        basis = "not_stated"
        note = "Neither an end date nor a duration appears in the record we verified."

    expired = None
    if end is not None:
        expired = end < TODAY
    elif (r.confirmed_action_type or "").startswith("expired"):
        expired = True

    out.append({
        "county": r.county, "jurisdiction": r.jurisdiction,
        "action_type": r.confirmed_action_type,
        "effective_from": eff_from.isoformat() if eff_from else None,
        "expiry_date": end.isoformat() if end else None,
        "expiry_basis": basis,
        "expiry_duration_label": label,
        "expiry_condition_verbatim": r.expiry_condition_verbatim,
        "expiry_note": note,
        "is_expired": expired,
        "days_remaining": (end - TODAY).days if (end and not expired) else None,
        "posture_renderable": r.posture_renderable,
        "official_url": r.official_url,
    })

for o in out:
    rem = f"{o['days_remaining']}d left" if o["days_remaining"] is not None else ""
    print(f"  {o['county']:12s} {str(o['action_type']):20s} from={str(o['effective_from']):11s} "
          f"end={str(o['expiry_date']):11s} [{o['expiry_basis']}] {rem}")

from collections import Counter
print("\nexpiry_basis:", dict(Counter(o["expiry_basis"] for o in out)))
print("dated end (published or derived):",
      sum(1 for o in out if o["expiry_date"]), "of", len(out))

schema = [
    bigquery.SchemaField("county", "STRING"), bigquery.SchemaField("jurisdiction", "STRING"),
    bigquery.SchemaField("action_type", "STRING"), bigquery.SchemaField("effective_from", "DATE"),
    bigquery.SchemaField("expiry_date", "DATE"), bigquery.SchemaField("expiry_basis", "STRING"),
    bigquery.SchemaField("expiry_duration_label", "STRING"),
    bigquery.SchemaField("expiry_condition_verbatim", "STRING"),
    bigquery.SchemaField("expiry_note", "STRING"), bigquery.SchemaField("is_expired", "BOOL"),
    bigquery.SchemaField("days_remaining", "INT64"),
    bigquery.SchemaField("posture_renderable", "BOOL"),
    bigquery.SchemaField("official_url", "STRING"),
]
client.load_table_from_json(
    out, OUT,
    job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE"),
).result()
print(f"\n{OUT}: {len(out)} rows written")

n_derived = sum(1 for o in out if o["expiry_basis"] == "derived")
n_pub = sum(1 for o in out if o["expiry_basis"] == "published")
client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_dc_action_expiry',
 'indiana_app.in_dc_actions_resolved (verified county/municipal data-centre actions)',
 'duration extracted declaratively from expiry_condition_verbatim + verbatim_snippet with a '
 'self-tested pattern list (2y/18m/12m/1y/9m/6m/90d); expiry_date = verified_effective_from + '
 'duration ONLY where both exist; open-ended conditions detected separately and left NULL with '
 'the condition quoted; no default duration is ever assumed. '
 'RE-SCRAPE COMMAND: python scripts/build_dc_action_expiry.py',
 {len(out)}, 0.0, CURRENT_TIMESTAMP(),
 'G89. {n_pub} published end dates + {n_derived} derived = {n_pub + n_derived} dated of {len(out)}. '
 'expiry_basis distinguishes published / derived / open_ended / duration_without_anchor / '
 'not_stated - a derived date MUST be badged and never styled as published. An open-ended '
 'moratorium is a stated condition, not a missing value.'
)""").result()
print("  _registry row written")
print("DC ACTION EXPIRY COMPLETE")
