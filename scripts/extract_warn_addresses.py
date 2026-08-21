"""G150: THE WARN FACILITY ADDRESS IS IN THE FILING, AND EVERY FILER WRITES IT DIFFERENTLY.

Operator, 2026-08-21: *"we are displaying that we only hold two WARN notices, and I know
definitively that we hold hundreds or thousands… we really need to ensure that we are displaying
all of the data that we hold, instead of truncating or misrepresenting our actual holdings."*
Then: *"For WARN notices, the addresses are seen in the actual filings."*
Then, with the Owens Corning header: *"note that the two addresses in the header are NOT the site
location."*
Then, with the Forest River letter: *"each WARN notice is published differently… Some of the WARN
notices may NOT even contain the address of the site itself, so this should also be known."*
Then: *"you should probably manually explore a large sample of these PDFs before you write a
one-size-fits-all code for the address extraction."*

================================================================================================
⭐ SO THIRTY-FOUR FILINGS WERE READ BEFORE THIS WAS WRITTEN, AND THE OPERATOR WAS RIGHT
================================================================================================
The first version of this script was one "located at" regex plus a blocklist. Reading the corpus
killed that design. What is actually in these letters:

  ⛔ MULTI-SITE NOTICES ARE COMMON, so one address per notice is the wrong shape.
     Ascension Medical Group lists FOUR facilities as bullets - 2415A Mitchell Road, 2415C
     Mitchell Road, 2409 Mitchell Road and 1600 23rd Street, all in Bedford. Head Start lists
     three in Richmond. Taking "the" address would have silently discarded most of those sites.

  ⛔ RURAL INDIANA ADDRESSES HAVE NO STREET SUFFIX.
     "1501 County Road East 200 North in Kokomo" (BorgWarner) and "900 CR1, Elkhart" (Forest
     River) never reach a Street/Avenue/Road token the way a suffix pattern expects, and a naive
     suffix match truncates the first to "1501 County Road".

  ⛔ THE FACILITY PHRASE VARIES PER FILER, not per county - each company's counsel writes their
     own letter. Observed: "facility located at", "at its location at", "will occur is",
     "Location: 2428 Glick Street,Lafayette,Indiana,47909" (a label, and no spaces after the
     commas), and bare address blocks under bullets.

  ⛔ SOME FILINGS HAVE NO SITE AT ALL. Block, Inc. gives "Remote, Indiana 46032" - a distributed
     workforce with no premises to vacate. That is a FACT about the notice, not a parse failure,
     and it is recorded as one.

  ⛔ THE NON-FACILITY ADDRESSES ARE NUMEROUS AND PLAUSIBLE. Every letter carries the Department of
     Workforce Development. Most carry the local chief elected official - "301 Michigan Street,
     Walkerton" sits three lines above the real plant, IN THE RIGHT TOWN. Several carry outside
     counsel ("201 N. Illinois St., Ste. 1800") or an HR manager's own address ("900 CR1,
     Elkhart", Forest River). Proximity and plausibility checks pass on every one of them.

================================================================================================
THE DESIGN THAT SURVIVED THE READING
================================================================================================
Extract EVERY candidate address, CLASSIFY each by the text around it, and keep them all:

    facility      a facility phrase points at it, or it is an item in a bulleted site list
    refused       an agency / elected official / counsel / HR / registered-agent context
    unclassified  a real address with no context either way - REPORTED, never placed

⚠ One row per (notice, address), so a four-site notice yields four rows. ⛔ Nothing is placed on a
map from `unclassified`: the standing rule is refuse below a confidence threshold, and the cost of
being wrong here is a pin on a town hall.

⚠ CEILING: only 172 of the 1,220 notices carry a PDF URL in our clip. The other 1,048 are a
SEPARATE acquisition - see G151 - and are reported, never quietly absorbed.

RE-SCRAPE COMMAND: python scripts/extract_warn_addresses.py
  --limit N      stop after N PDFs (smoke test)
  --refresh      re-download PDFs already cached
⚠ IDEMPOTENT: replace_safe. PDFs cached under data/warn_pdfs/ and ARCHIVED, never deleted.
"""
import argparse
import os
import re
import sys
import time
from urllib.parse import quote

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_si_warn_addresses"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "warn_pdfs")

# ================================================================================================
# ⛔ EVERY PATTERN AT MODULE LEVEL, WITH SELF-TESTS BUILT FROM REAL FILINGS.
# Nine recorded cases in this project of a regex corrupted by being written through a shell. These
# are typed in a file and proven against text copied out of the actual PDFs.
# ================================================================================================
SUFFIX = (r"(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|Lane|Ln|Way|Parkway|Pkwy|"
          r"Court|Ct|Place|Pl|Circle|Cir|Highway|Hwy|Pike|Trail|Trl|Terrace|Ter)")

# ⭐ THREE STREET SHAPES, because rural Indiana does not use the suburban one.
#   1. county/state road, spelled out:   1501 County Road East 200 North
#   2. county road, abbreviated:         900 CR1   /   4200 E CR 100 S
#   3. the ordinary suffixed street:     2275 Bloomingdale Drive
# ⚠ THE RURAL SHAPES MUST COME FIRST. "1501 County Road East 200 North" also matches the suffixed
# alternative, which stops at "Road" and throws away "East 200 North" - so the alternation order
# is load-bearing, not cosmetic.
STREET = (
    r"(?:"
    r"\d{1,6}\s+(?:[NSEW]\.?\s+)?(?:County\s+Road|State\s+Road|State\s+Route)\s+"
    r"(?:[NSEW]\.?\s*|East\s+|West\s+|North\s+|South\s+)?\d{1,4}\s*"
    r"(?:North|South|East|West|[NSEW])?\b"
    r"|\d{1,6}\s+(?:[NSEW]\.?\s*)?(?:CR|SR)\s?\d{1,4}\s?(?:North|South|East|West|[NSEW])?\b"
    # ⛔ EVERY WORD OF THE STREET BODY MUST START UPPERCASE OR WITH A DIGIT, and this is not
    # tidiness. The first version allowed any characters between the number and the suffix, so on
    # "plans to lay off 8 employees at its location at 989 Opportunity Parkway" it started at the
    # EMPLOYEE COUNT and swallowed the prose, returning
    #     "8 employees at its location at 989 Opportunity Parkway"
    # as a street. A lazy wildcard between two anchors will always find a way through a sentence;
    # requiring token case is what makes it stop at a real address.
    r"|\d{1,6}[A-Z]?\s+(?:[A-Z0-9][A-Za-z0-9.\-']*\s+){0,5}?" + SUFFIX + r"\b\.?"
    r")")

CITY = r"(?P<city>[A-Z][A-Za-z.\-' ]{2,28}?)"
# ⚠ 'Indiana' spelled out is as common as 'IN'; the zip is sometimes preceded by a comma
# ("Lafayette,Indiana,47909"), sometimes absent, and sometimes ZIP+4.
# ⛔ `[\s,]*` BETWEEN THE CITY AND THE STATE, NOT `\s*,?\s+`. Arconic writes
# "Location: 2428 Glick Street,Lafayette,Indiana,47909" with NO SPACE after either comma, and a
# pattern that requires whitespace there silently drops the row. Requiring a space is an
# assumption about typing, not about addresses.
TAIL = (r"[\s,]*(?:in\s+)?" + CITY + r"\b[\s,]*(?:IN|Indiana)\b\.?[\s,]*"
        r"(?P<zip>\d{5})?(?:-\d{4})?")
# ⛔ NO re.I ON THIS ONE, AND THAT IS THE WHOLE POINT OF THE TOKEN-CASE RULE ABOVE.
# With re.I set, `[A-Z0-9]` matches lowercase too - so the "every street word starts uppercase"
# guard silently did nothing, and "Plant 63 located at 2275 Bloomingdale Drive" came back as the
# street "63 located at 2275 Bloomingdale Drive". A case-sensitive pattern is the guard; the flag
# was quietly cancelling it.
# ⚠ The cue patterns below KEEP re.I - prose case varies, address case does not.
ADDR = re.compile(r"(?P<street>" + STREET + r")" + TAIL)

# ================================================================================================
# A FACILITY PHRASE IN THE TEXT JUST BEFORE THE ADDRESS.
# ⭐ THE SECOND HALF OF THIS LIST CAME FROM READING THE 97 ADDRESSES THE FIRST VERSION SET ASIDE AS
# `unclassified`, at the operator's instruction that ~172 filings should yield more than 68
# facilities. They were not ambiguous - they were labelled in ways the first cue list did not know:
#     "Name and Address of Site Where the Plant Closing Will Occur:"   (AAR Aircraft Services)
#     "The address of this Plant is"                                    (Aurorium)
#     "permanently laying off workers at the following Affected Facilities:"  (Franciscan, 4 sites)
#     "Discontinuance of ... Management and Operation of Facility at"   (FedEx Supply Chain)
# ⚠ The Franciscan and Head Start filings are LISTS - one cue, then several "Name, address" pairs -
# which is why LIST_CONTEXT below carries the cue forward across the following addresses instead of
# requiring one per line.
# ================================================================================================
FACILITY_CUE = re.compile(
    r"facility\s+located\s+at|located\s+at|location\s+at|location\s*:|"
    r"operations?\s+at|premises\s+at|site\s+(?:is\s+)?at|will\s+occur\s+(?:is|at)|"
    r"employment\s+site|affected\s+(?:site|facility|location)|"
    r"closing[^.]{0,40}\bat\b|lay\s*off[^.]{0,40}\bat\b|"
    r"plant\s+\d+\s+located|"
    r"address\s+of\s+(?:the\s+)?(?:site|plant|facility)|"
    r"site\s+where\s+the\s+(?:plant\s+)?closing|"
    r"name\s+and\s+address|"
    r"operation\s+of\s+(?:the\s+)?facility\s+at|"
    r"following\s+affected\s+facilit|affected\s+facilities\s*:|"
    r"following\s+(?:location|site|facilit)", re.I)

# ⭐ A LIST CUE STAYS IN FORCE FOR THE ADDRESSES THAT FOLLOW IT.
# "…at the following Affected Facilities: Franciscan Health Michigan City, 3500 Franciscan Way,
#  Michigan City, IN 46360 Franciscan Health Lafayette Central, 1501 Hartford St., …"
# Only the FIRST address has the cue within 130 characters; the rest are separated by the next
# facility's NAME. Requiring a cue per address would have kept one hospital of four.
LIST_CUE = re.compile(
    r"following\s+affected\s+facilit|affected\s+facilities\s*:|"
    r"following\s+(?:locations?|sites?|facilities)\s*:|"
    r"at\s+the\s+following", re.I)

# ⛔ contexts that make an address NOT the plant
REFUSE_CUE = re.compile(
    r"workforce\s+development|indiana\s+government\s+center|10\s+(?:n\.?|north)\s+senate|"
    r"rapid\s+response|department\s+of\s+labor|"
    # ⚠ ADDED AFTER READING THE UNCLASSIFIED BUCKET: two filings put '10 North Senate Ave'
    # under 'Indiana State Dislocated Worker Unit' rather than under the department name, so
    # the state's own address came through as an unclassified candidate.
    r"dislocated\s+worker\s+unit|state\s+dislocated|warn-notice@|via\s+e-?mail|"
    r"chief\s+elected\s+official|town\s+council|city\s+council|county\s+council|"
    r"board\s+of\s+(?:commissioners|works)|\bmayor\b|town\s+hall|city\s+hall|"
    r"registered\s+agent|corporation\s+trust|\battn\b|attention\s*:|"
    r"human\s+resources|\bhr\b\s+manager|please\s+contact|questions\s+regarding|"
    r"counsel|attorney|\besq\b|law\s+(?:firm|office)|\bllp\b|copy\s+to|\bcc\s*:|sincerely",
    re.I)

# ⭐ a filing that says the workforce is remote has no site, and that is an ANSWER
REMOTE = re.compile(r"\bremote\s*,\s*indiana\b|\bfully\s+remote\b|\bwork\s+from\s+home\b|"
                    r"\bremote(?:ly)?\b[^.\n]{0,40}(?:workforce|employees|workers)", re.I)

# ---- self-tests, every string copied out of a real filing --------------------------------------
_OWENS = ("of a permanent plant closure at Owens Corning's (the \"Company\") facility located at "
          "105 Industrial Park Drive, Walkerton, IN 46574 (the \"Facility\").")
_HDR = ("Indiana Department of Workforce Development Indiana Government Center South "
        "10 North Senate Avenue Indianapolis, IN 46204 "
        "Walkerton, Indiana Chief Elected Official Walkerton Town Council "
        "301 Michigan Street Walkerton, IN 46574")
_FOREST = ("closing its entire operations at Plant 63 located at 2275 Bloomingdale Drive, "
           "Bristol, Indiana 46507 (\"Facility\"). please contact Jorge Lizarazo, Corporate "
           "Human Resources Manager: Address: 900 CR1, Elkhart, IN 46514")
_BORG = ("Morgan Street facility located at 1501 County Road East 200 North in Kokomo, Indiana "
         "beginning on October 22,")
_ARCONIC = "Location: 2428 Glick Street,Lafayette,Indiana,47909"
_BWI = ("BWI Group plans to lay off 8 employees at its location at 989 Opportunity Parkway, "
        "Greenfield, Indiana 46140.")

assert ADDR.search(_OWENS).group("street") == "105 Industrial Park Drive"
_b = ADDR.search(_BORG)
assert _b and _b.group("street").startswith("1501 County Road East 200"), \
    f"the rural county-road shape must not truncate at 'Road': {_b and _b.group('street')!r}"
assert _b.group("city").lower() == "kokomo", f"BorgWarner city: {_b.group('city')!r}"
assert ADDR.search(_ARCONIC).group("city") == "Lafayette", "no-space commas must still parse"
assert ADDR.search(_BWI).group("street") == "989 Opportunity Parkway"
assert FACILITY_CUE.search("Location:"), "the bare 'Location:' label is a facility cue"
assert FACILITY_CUE.search("at its location at"), "BWI's phrasing is a facility cue"
assert REFUSE_CUE.search("Corporate Human Resources Manager"), "an HR contact is not the plant"
assert REFUSE_CUE.search("Walkerton Town Council"), "the elected official is not the plant"
assert REMOTE.search("Remote, Indiana 46032"), "a remote workforce has no site"


def pdf_text(path):
    try:
        from pdfminer.high_level import extract_text
        return extract_text(path) or ""
    except Exception:
        pass
    try:
        import PyPDF2
        with open(path, "rb") as fh:
            return "\n".join((p.extract_text() or "") for p in PyPDF2.PdfReader(fh).pages)
    except Exception:
        return None


def classify(txt):
    """Every candidate address in one filing, each with a verdict and the reason for it.

    ⚠ Returns a LIST. A four-site notice yields four facility rows; a notice carrying only a
    header yields refusals and no facility; a remote-workforce notice yields none and says why.
    """
    if not txt:
        return [], "unreadable"
    flat = re.sub(r"\s+", " ", txt)
    out, seen = [], set()
    for m in ADDR.finditer(flat):
        street = m.group("street").strip(" ,.")
        city = (m.group("city") or "").strip(" ,.")
        key = (street.upper(), city.upper())
        if key in seen:
            continue
        seen.add(key)
        before = flat[max(0, m.start() - 130):m.start()]
        # ⭐ a list cue anywhere in the 600 characters before this address keeps applying: the
        # Franciscan filing names four hospitals under one "Affected Facilities:" heading.
        in_list = bool(LIST_CUE.search(flat[max(0, m.start() - 600):m.start()]))
        # ⛔ THE REFUSAL LOOKS BACKWARD ONLY, and the first version looked forward too and broke
        # the operator's own example. In the Forest River letter the plant address is followed,
        # 40 characters later, by "please contact Jorge Lizarazo, Corporate Human Resources
        # Manager" - so a window that reached forward found an HR cue and REFUSED THE PLANT.
        # ⚠ In a letter the disqualifying label always PRECEDES its address: "Attn:", "Town
        # Council", "Human Resources Manager: Address:". Looking forward can only pick up the
        # next paragraph, which belongs to a different address.
        if REFUSE_CUE.search(before):
            verdict, why = "refused", "an agency, elected official, counsel or HR contact address"
        elif FACILITY_CUE.search(before):
            verdict, why = "facility", "the filing points at this address as the affected site"
        elif in_list:
            verdict, why = "facility", "an entry in a list of affected facilities"
        elif re.search(r"[•●▪\-]\s*$", before[-4:]):
            # ⚠ A BULLETED LIST OF SITES carries no cue per line - the cue sits one line above the
            # whole list. This is the only concession to layout in here, and it is what recovers
            # the four Ascension facilities that a per-line cue test would have thrown away.
            verdict, why = "facility", "an item in a bulleted list of affected sites"
        else:
            verdict, why = "unclassified", "a real address with no context either way"
        # ⚠ A ZIP OUTSIDE INDIANA IS A FACT ABOUT THE FILING, NOT A REASON TO DROP THE ROW.
        # Found by reading the 68 accepted addresses: Thermal Structures gives
        # "2800 Airwest Blvd, Plainfield 42816" and 42816 is a KENTUCKY zip - Plainfield, Indiana
        # is 46168. The street and city are plausible and the zip is a typo in the letter. Indiana
        # is 46001-47997. Flagged so a downstream geocode can distrust the zip rather than
        # inheriting it silently, and so the filing's own error stays visible.
        zp = m.group("zip")
        bad_zip = bool(zp) and not (46001 <= int(zp) <= 47997)
        out.append({"street": street, "city": city, "zip": zp, "zip_outside_indiana": bad_zip,
                    "verdict": verdict, "basis": why})
    note = None
    if not any(o["verdict"] == "facility" for o in out) and REMOTE.search(flat):
        note = "remote_workforce"
    return out, note


_c = [o for o in classify(_OWENS + " " + _HDR)[0] if o["verdict"] == "facility"]
assert _c and all(o["street"] != "301 Michigan Street" for o in _c), \
    "the plant must be accepted and the Town Council must not"
_f = [o for o in classify(_FOREST)[0] if o["verdict"] == "facility"]
assert len(_f) == 1 and _f[0]["street"] == "2275 Bloomingdale Drive", \
    f"Forest River: only the plant, not the HR address. got {_f}"
assert classify("Our workforce is Remote, Indiana 46032")[1] == "remote_workforce"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()

    client = bigquery.Client(project="energy-platfrom")
    # ⭐ THE PAGE IS THE SOURCE OF TRUTH FOR FILING LINKS, NOT THE NORMALISED TABLE.
    # `in_si_warn_page` is a direct re-scrape of the DWD listing (refresh_warn_page.py) and carries
    # every link the publisher offers; `in_si_warn_normalised` carries the classification work
    # (vacates_site, notice_class) that the extractor orders by. Joining them uses each for what it
    # is authoritative about, instead of trusting one loader's copy of the other's data.
    # ⚠ THE JOIN IS ON NORMALISED TEXT. Comparing the page's raw company name against the database
    # copy produced eight false mismatches on entities alone (`&amp;`, the curly apostrophe), so
    # both sides are folded here the same way refresh_warn_page.py folds them.
    rows = list(client.query(f"""
      WITH pg AS (
        SELECT REGEXP_REPLACE(LOWER(TRIM(company)), r'\\s+', ' ') co,
               REGEXP_REPLACE(LOWER(TRIM(IFNULL(city, ''))), r'\\s+', ' ') ci,
               ANY_VALUE(notice_pdf_url) notice_pdf_urls
        FROM `{DS}.in_si_warn_page`
        WHERE notice_pdf_url IS NOT NULL GROUP BY 1, 2),
      nm AS (
        SELECT REGEXP_REPLACE(LOWER(TRIM(company)), r'\\s+', ' ') co,
               REGEXP_REPLACE(LOWER(TRIM(IFNULL(city, ''))), r'\\s+', ' ') ci,
               ANY_VALUE(company) company, ANY_VALUE(city) city,
               MAX(event_date) event_date, ANY_VALUE(notice_class) notice_class,
               LOGICAL_OR(IFNULL(vacates_site, FALSE)) vacates_site,
               MAX(affected_workers) affected_workers
        FROM `{DS}.in_si_warn_normalised` GROUP BY 1, 2)
      SELECT IFNULL(nm.company, pg.co) company, nm.city, nm.event_date, nm.notice_class,
             IFNULL(nm.vacates_site, FALSE) vacates_site, nm.affected_workers,
             pg.notice_pdf_urls
      FROM pg LEFT JOIN nm ON nm.co = pg.co AND nm.ci = pg.ci
      ORDER BY vacates_site DESC, event_date DESC"""))
    if a.limit:
        rows = rows[: a.limit]
    print("G150 - WARN FACILITY ADDRESSES, CLASSIFIED")
    print(f"  {len(rows)} notices carry a PDF URL")
    os.makedirs(CACHE, exist_ok=True)

    out, blocked, multi = [], [], 0
    st = {"facility": 0, "refused": 0, "unclassified": 0,
          "remote": 0, "no_address": 0, "unreadable": 0}
    for i, r in enumerate(rows, 1):
        url = quote(str(r.notice_pdf_urls).split(",")[0].strip(), safe=":/?&=%#")
        name = re.sub(r"[^A-Za-z0-9]+", "_", url.split("/")[-1])[:80] + ".pdf"
        path = os.path.join(CACHE, name)
        if not os.path.exists(path) or a.refresh:
            try:
                resp = requests.get(url, timeout=60)
            except Exception as e:
                blocked.append((r.company, f"BLOCKED: {type(e).__name__}: {e}"))
                continue
            if resp.status_code != 200:
                blocked.append((r.company,
                                f"BLOCKED: HTTP {resp.status_code} {resp.reason} for {url}"))
                continue
            with open(path, "wb") as fh:
                fh.write(resp.content)
            time.sleep(0.4)
        txt = pdf_text(path)
        if txt is None:
            st["unreadable"] += 1
            continue
        addrs, note = classify(txt)
        fac = [x for x in addrs if x["verdict"] == "facility"]
        if len(fac) > 1:
            multi += 1
        if note == "remote_workforce":
            st["remote"] += 1
        if not addrs:
            st["no_address"] += 1
        for x in addrs:
            st[x["verdict"]] += 1
            out.append({
                "company": r.company, "notice_city": r.city,
                "event_date": str(r.event_date) if r.event_date else None,
                "notice_class": r.notice_class, "vacates_site": r.vacates_site,
                "affected_workers": r.affected_workers,
                "facility_street": x["street"], "facility_city": x["city"],
                "facility_zip": x["zip"], "zip_outside_indiana": x["zip_outside_indiana"],
                "verdict": x["verdict"], "address_basis": x["basis"],
                "sites_in_notice": len(fac), "notice_note": note, "notice_pdf_url": url,
            })
        if i % 40 == 0 or i == len(rows):
            print(f"  [{i:>3}/{len(rows)}] facility={st['facility']} refused={st['refused']} "
                  f"unclassified={st['unclassified']} blocked={len(blocked)}")

    print(f"\n  ⭐ {st['facility']} FACILITY addresses accepted")
    print(f"  ⭐ {multi} notices name MORE THAN ONE site — one address per notice would have "
          f"dropped the rest")
    print(f"  ⛔ {st['refused']} refused (agency, elected official, counsel, HR)")
    print(f"  ⚠ {st['unclassified']} unclassified — held and reported, NEVER placed")
    print(f"  ⚠ {st['remote']} notices describe a REMOTE workforce with no site at all")
    print(f"  ⚠ {st['no_address']} filings carried no parseable address")
    print(f"  ⚠ {st['unreadable']} PDFs unreadable as text")
    print(f"  ⛔ {len(blocked)} BLOCKED")
    for co, why in blocked[:5]:
        print(f"       {str(co)[:26]:26} {why[:88]}")

    if not out:
        print("\n  ⛔ nothing recovered - refusing to replace the table with an empty one")
        return 1

    import pandas as pd
    client.load_table_from_dataframe(
        pd.DataFrame(out), OUT,
        job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")).result()

    s = list(client.query(f"""
      SELECT COUNT(*) n, COUNTIF(verdict='facility') fac,
             COUNT(DISTINCT IF(verdict='facility', company, NULL)) firms,
             COUNTIF(verdict='facility' AND vacates_site) vac
      FROM `{OUT}`"""))[0]
    print(f"\n  {OUT}: {s.n} rows, {s.fac} facility addresses across {s.firms} firms, "
          f"{s.vac} that vacate the site")

    client.query(f"""
    INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
    VALUES (
      'in_si_warn_addresses',
      'Indiana DWD WARN notice PDFs, static public files whose URLs are already recorded in '
      'indiana_app.in_si_warn_normalised.notice_pdf_urls (https://www.in.gov/dA/...pdf)',
      'One row per (notice, address). EVERY candidate address in each filing is extracted and '
      'CLASSIFIED by the text around it: facility (a facility phrase points at it, or it is an '
      'item in a bulleted site list), refused (agency / chief elected official / outside counsel / '
      'HR contact / registered agent), or unclassified (a real address with no context either way '
      '- reported, NEVER placed). Notices describing a remote workforce are flagged as having no '
      'site rather than counted as a parse failure. Three street shapes because rural Indiana has '
      'no suffix: suffixed streets, spelled county/state roads (1501 County Road East 200 North) '
      'and abbreviated ones (900 CR1); city may be followed by IN or Indiana, with or without a '
      'comma before the zip. ⭐ DESIGNED AFTER READING 34 FILINGS at the operator instruction - '
      'multi-site notices are common (Ascension lists four facilities), so one address per notice '
      'was the wrong shape. '
      'RE-SCRAPE COMMAND: python scripts/extract_warn_addresses.py',
      {s.n}, 0.0, CURRENT_TIMESTAMP(),
      'G150, operator 2026-08-21. in_si_warn_normalised holds 1,220 notices and NO address column, '
      'which is why in_si_signal_coverage shows D19_warn reaching 2 parcels - never placeable '
      'rather than filtered down. ⚠ CEILING: only 172 of the 1,220 carry a PDF URL in our clip; '
      'the other 1,048 are G151, a separate acquisition. '
      'IDEMPOTENCY: replace_safe. CADENCE: monthly.'
    )""").result()
    print("  _registry row written")
    print("WARN ADDRESS EXTRACTION COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
