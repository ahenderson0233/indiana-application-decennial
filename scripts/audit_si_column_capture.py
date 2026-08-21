"""G140: DO WE HOLD EVERY COLUMN THE PUBLISHER OFFERS, FOR EVERY SI SIGNAL SOURCE?

Operator, 2026-08-21: *"have we 100% guaranteed that we have ALL columns for ALL SI signals, and no
rescrapes are necessary for obtaining new columns? If not, that is the first action item."*

⛔ THE HONEST ANSWER BEFORE THIS SCRIPT EXISTED WAS NO, AND WARN IS THE PROOF OF WHAT IT COSTS.
`in_si_warn_normalised` captured 17 columns including `notice_pdf_urls` and NOT the facility
address - because the address is not a column in the listing, it is prose inside the linked filing.
That single gap held D19_warn at 2 placed parcels against 1,220 notices held, for months, while
every count in the application looked healthy. A missing column is not a cosmetic loss; it is a
signal that cannot reach a parcel.

⭐ WHY THIS CAN BE ANSWERED DEFINITIVELY FOR MOST OF THEM. Seven of the SI publisher tables come
from ArcGIS REST services, and an ArcGIS layer PUBLISHES ITS OWN FIELD LIST at `?f=json`. So this
is not an estimate: we ask the publisher what it offers and compare it against what we hold. For
the rest the parent is an `energy.*` table and the comparison is a schema diff.

WHAT A FINDING MEANS HERE
  · a field the publisher offers and we do not hold  -> a RE-SCRAPE would gain it
  · a field we hold and the publisher no longer has  -> the source changed under us
  · nothing missing                                  -> full capture, and no re-scrape needed
                                                        FOR COLUMNS (new EVENTS are a separate
                                                        question - that is the rehearsal)

⚠ NOT EVERY MISSING FIELD IS WORTH HAVING. ArcGIS layers carry Shape__Area, OBJECTID and editor
-tracking fields that mean nothing to a siter. Those are listed as `noise` and excluded from the
verdict, so the finding count stays readable - the rule this project already learned is that a wide
audit that cries wolf gets ignored.

⛔ THIS IS READ-ONLY. It fetches layer METADATA, never rows, and writes nothing anywhere.

RE-SCRAPE COMMAND: python scripts/audit_si_column_capture.py
"""
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import requests
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
c = bigquery.Client(project="energy-platfrom")

# ⚠ ArcGIS housekeeping fields. Present on nearly every layer, useful to nobody siting a data
# centre, and listing them as gaps would bury the real findings.
NOISE = re.compile(
    r"^(objectid|fid|shape|shape_|shape__|globalid|se_anno_cad_data|"
    r"created_user|created_date|last_edited_user|last_edited_date|editdate|creationdate|"
    r"creator|editor|st_area|st_length)", re.I)

# every table that feeds an SI signal, with where it came from
SOURCES = [
    ("in_si_indy_abandoned_vacant", "arcgis",
     "https://gis.indy.gov/server/rest/services/OpenData/OpenData_Infrastructure/MapServer/2"),
    ("in_si_southbend_vacant_abandoned", "arcgis",
     "https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services/"
     "AllVacantandAbandonedProperties/FeatureServer/3"),
    ("in_si_southbend_code_enforcement", "arcgis",
     "https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services/"
     "Code_Enforcement_Cases/FeatureServer/0"),
    ("in_si_southbend_continuous_enforcement", "arcgis",
     "https://services1.arcgis.com/0n2NelSAfR7gTkr1/arcgis/rest/services/"
     "Continuous_Enforcement/FeatureServer/4"),
    ("in_si_evansville_taxsale", "arcgis",
     "https://maps.evansvillegis.com/arcgis_server/rest/services/SITE_PROJECTS/TAX_SALE/"
     "MapServer"),
    ("in_si_evansville_foreclosures", "arcgis",
     "https://maps.evansvillegis.com/arcgis_server/rest/services/ASSESSOR/FORECLOSURES/"
     "MapServer"),
    ("in_si_evansville_demolition_permits", "arcgis",
     "https://maps.evansvillegis.com/arcgis_server/rest/services/BC/"
     "BUILDING_COMMISSION_PERMITS/MapServer/0"),
    # the generic corpus, against its energy parent
    ("in_si_signals", "energy", "si_signals"),
]


def our_cols(table):
    try:
        return {f.name.lower() for f in c.get_table(f"{DS}.{table}").schema}
    except Exception:
        return None


def _get(url):
    try:
        r = requests.get(url.rstrip("/") + "?f=json", timeout=60)
    except Exception as e:
        return None, f"BLOCKED: {type(e).__name__}: {e}"
    if r.status_code != 200:
        return None, f"BLOCKED: HTTP {r.status_code} {r.reason}"
    try:
        j = r.json()
    except Exception:
        return None, "BLOCKED: response is not JSON"
    if "error" in j:
        return None, f"BLOCKED: layer error {str(j['error'])[:80]}"
    return j, None


def arcgis_fields(url):
    """Every field the SERVICE publishes, across ALL of its layers. Returns (fields, note).

    ⛔ THE FIRST VERSION PROBED ONE LAYER AND REPORTED FULL CAPTURE ON A FALSE COMPARISON.
    Evansville FORECLOSURES is not a layer, it is a service of TWELVE layers - one per year, from
    "Foreclosures - 2006" to "Foreclosures_2017" - carrying between 15 and 207 fields each. Asking
    layer 0 for its 79 fields and comparing that against our 456 columns produced "ours 456,
    publisher 79, FULL CAPTURE", which is arithmetically reassuring and means nothing: the loader
    unions every year, so the honest denominator is the union of every layer's fields.
    ⚠ The same shape applies to TAX_SALE. A service root is not a layer, and treating it as one is
    the "wrong grain" defect wearing a URL.
    """
    j, note = _get(url)
    if j is None:
        return None, note
    if j.get("fields"):
        return {x["name"].lower() for x in j["fields"]}, None
    layers = j.get("layers")
    if not layers:
        return None, "no `fields` and no `layers` in the metadata"
    allf, seen, failed = set(), 0, []
    for lyr in layers:
        k, e = _get(f"{url.rstrip('/')}/{lyr['id']}")
        if k is None or not k.get("fields"):
            failed.append(str(lyr["id"]))
            continue
        allf |= {x["name"].lower() for x in k["fields"]}
        seen += 1
    if not seen:
        return None, f"service root with {len(layers)} layers, none readable"
    note = (f"union of {seen} layer(s)"
            + (f"; {len(failed)} unreadable: {','.join(failed[:4])}" if failed else ""))
    return allf, note


print("=" * 100)
print("G140 - FULL-COLUMN CAPTURE FOR EVERY SI SIGNAL SOURCE")
print("=" * 100)
print("⛔ READ-ONLY: fetches layer metadata, never rows, writes nothing.\n")

findings, blocked, checked = [], [], 0
for table, kind, ref in SOURCES:
    ours = our_cols(table)
    if ours is None:
        print(f"⚠ {table}: not in the warehouse - skipped")
        continue
    if kind == "arcgis":
        theirs, note = arcgis_fields(ref)
    else:
        try:
            theirs = {f.name.lower() for f in c.get_table(f"{EN}.{ref}").schema}
            note = None
        except Exception as e:
            theirs, note = None, f"parent energy.{ref} unreadable: {str(e)[:70]}"
    if theirs is None:
        blocked.append((table, note))
        print(f"⛔ {table:40} {note}")
        continue
    checked += 1
    # ⚠ A UNIONED LOADER DISAMBIGUATES DUPLICATE NAMES WITH A _N SUFFIX. Evansville foreclosures
    # unions twelve yearly layers that share field names, so ours carries `acreage`, `acreage_1`,
    # `acreage_12`. Comparing raw would report `acreage` as held and `acreage_1` as an extra we
    # invented; comparing on the STEM is what makes the two sides the same vocabulary.
    stems = {re.sub(r"_\d+$", "", x) for x in ours}
    missing = sorted(x for x in theirs - ours - stems if not NOISE.match(x))
    noise_missing = sorted(x for x in theirs - ours if NOISE.match(x))
    extra = sorted(x for x in ours - theirs if re.sub(r"_\d+$", "", x) not in theirs)
    status = "FULL CAPTURE" if not missing else f"{len(missing)} FIELD(S) NOT HELD"
    if note:
        status += f"  [{note}]"
    print(f"{'✔' if not missing else '⛔'} {table:40} ours {len(ours):>3} · publisher "
          f"{len(theirs):>3} · {status}")
    if missing:
        findings.append((table, missing))
        for m in missing[:14]:
            print(f"      not held: {m}")
        if len(missing) > 14:
            print(f"      … and {len(missing) - 14} more")
    if noise_missing:
        print(f"      ({len(noise_missing)} housekeeping field(s) ignored: "
              f"{', '.join(noise_missing[:5])}…)")
    if extra:
        print(f"      ⚠ {len(extra)} column(s) we hold that the publisher does not list "
              f"(derived by our loader, or the source changed): {', '.join(extra[:6])}")

print()
print("=" * 100)
print(f"{checked} source(s) compared · {len(findings)} with a real gap · {len(blocked)} blocked")
print("=" * 100)
if findings:
    print("\n⛔ A RE-SCRAPE WOULD GAIN THESE. Each line is a column the publisher offers today and")
    print("   we do not hold, so it cannot reach any surface no matter what the front end does.")
    for t, m in findings:
        print(f"   {t}: {len(m)} field(s) — {', '.join(m[:8])}{'…' if len(m) > 8 else ''}")
for t, why in blocked:
    print(f"\n⚠ {t}: {why}")

# ⛔ THE ANSWER TO THE OPERATOR'S QUESTION, STATED PLAINLY RATHER THAN IMPLIED BY A TABLE.
print("\n" + "=" * 100)
if findings or blocked:
    print("ANSWER: NO - full column capture is NOT guaranteed across the SI signals.")
    print("        The gaps above are recoverable by re-running the named loaders.")
else:
    print("ANSWER: YES - every comparable SI source is at full column capture.")
print("⚠ THIS IS ABOUT COLUMNS ONLY. Whether the publisher has new EVENTS since our last pull is a")
print("  different question and is what the re-scrape rehearsal answers.")
print("=" * 100)
sys.exit(1 if findings else 0)
