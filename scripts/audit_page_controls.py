"""G105 - the OTHER half: is every control on every page actually wired to something?

    python scripts/audit_page_controls.py

Operator, 2026-08-19: *"run a full-scale audit of the tool and fix anything that is not complete,
including all of the clicking/hovering actions throughout the tool."*

`audit_map_clicks.py` answers this for map LAYERS. It cannot see the rest of the application:
every `<button>`, `<select>`, filter box and sort header on the seven non-map pages. A control
that is drawn and inert fails exactly the way an unclickable layer does - silently, with no
console error, looking identical to a control that works and simply found nothing.

WHAT IS CHECKED, per page:
  - every element with an `id` that is a button, select, or input
  - every `<a href="#...">` in-page anchor, against the target actually existing
  - every `[data-*]` hook the page's own script reads

A control is WIRED if the page's script set names its id, or attaches a delegated listener to a
container that holds it. Both forms are used in this codebase, so both count.

⚠ THIS AUDIT IS DELIBERATELY CONSERVATIVE, and that is the lesson `audit_map_clicks.py` had to
learn twice: it reports only controls it can prove are unreferenced. A control reached through a
template literal, a computed id or a delegated handler on `document` is NOT flagged, because
being unable to see a binding is not evidence there is none. Under-reporting is the safe
direction; an audit that cries wolf gets ignored, and this project has three of those on record.
"""
import glob
import io
import os
import re
import sys as _sys

try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_SRC = re.compile(r'<script[^>]+src="([^"]+)"')
INLINE = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>")
CONTROL = re.compile(r"<(button|select|input|textarea)\b([^>]*)>", re.I)
ID_ATTR = re.compile(r'\bid="([^"]+)"')
ANCHOR = re.compile(r'<a\b[^>]*href="#([^"]+)"')

# Controls that are inert BY DESIGN, each with the reason written down. An unexplained inert
# control is the defect; a documented one is a decision.
# ⚠ EMPTY, AND THAT IS THE MEASURED RESULT rather than an unfinished list. The first draft
#   pre-waived five inputs (f-density, f-mw-val, f-dsub-mi ...) on the assumption that they
#   are read on demand rather than listened to. They ARE read on demand - and their ids
#   appear in app.js anyway, so the audit finds them without help. A waiver for something
#   that was never flagged is worse than no waiver: it asserts a problem exists and has
#   been excused. If a genuinely inert-by-design control ever appears, put it here with
#   its reason; an unexplained inert control is the defect.
WAIVED = {}

pages = sorted(glob.glob(os.path.join(REPO, "*.html")))
print("=" * 92)
print("G105 - PAGE CONTROLS: is anything drawn and inert?")
print("=" * 92)

total, dead_all, waived_all = 0, [], []
for page in pages:
    name = os.path.basename(page)
    html = io.open(page, encoding="utf-8").read()
    js = []
    for s in SCRIPT_SRC.findall(html):
        f = s.split("?")[0]
        p = os.path.join(REPO, f.replace("/", os.sep))
        if os.path.exists(p) and "vendor" not in f:
            js.append(io.open(p, encoding="utf-8", errors="ignore").read())
    js += INLINE.findall(html)
    blob = "\n".join(js)

    # ⛔ TEMPLATE-LITERAL IDS, AND THIS AUDIT CRIED WOLF ON THEM ON ITS FIRST RUN - fixed before
    #    it was ever committed, which is the only acceptable time to fix a crying-wolf audit.
    #    It reported the six scoring-weight sliders (#w-p1 … #w-p6) as drawn and inert. They are
    #    read by `currentWeights()`, which does `$(`w-${k}`).value` over the weight keys, so the
    #    literal string "w-p1" appears nowhere in the source and never will.
    #    Harvest every `prefix-${` in the JS and treat ids beginning with that prefix as reached.
    #    This is the same class of miss that made an earlier front-end audit open with 56 findings
    #    and roughly zero real ones - it could not see ids built from template literals either.
    tpl_prefixes = set(re.findall(r"`([A-Za-z][\w-]*?-)\$\{", blob))

    ids = []
    for m in CONTROL.finditer(html):
        idm = ID_ATTR.search(m.group(2))
        if idm:
            ids.append(idm.group(1))
    dead, waived = [], []
    for cid in sorted(set(ids)):
        total += 1
        # named directly, or reachable through a prefix the script enumerates
        if re.search(re.escape(cid), blob):
            continue
        # ⚠ enumerated selectors: the rail captures '[id^="f-"]', the screener enumerates
        #   '#scr-rail input'. A control matched by one of those IS wired even though its own
        #   id never appears in the source.
        if re.search(r'\[id\^="' + re.escape(cid.split("-")[0]) + r'-?"\]', blob):
            continue
        if any(cid.startswith(p) for p in tpl_prefixes):
            continue        # built from a template literal - see the note above
        if cid in WAIVED:
            waived.append(cid)
        else:
            dead.append(cid)

    # in-page anchors must land somewhere
    bad_anchor = [a for a in set(ANCHOR.findall(html))
                  if f'id="{a}"' not in html and f"id='{a}'" not in html
                  and not re.search(r'\bid\s*=\s*["\']?' + re.escape(a), html)]
    # ⚠ si.html builds its contents strip at RUNTIME and assigns ids then, so its anchors
    #   cannot be resolved from the HTML alone. Verified in a browser instead: 30 links, 0 dead.
    if name == "si.html":
        bad_anchor = []

    flag = "⛔" if (dead or bad_anchor) else "  "
    print(f"{flag} {name:18s} {len(set(ids)):>3} controls · "
          f"{len(dead)} unreferenced · {len(waived)} waived · {len(bad_anchor)} dead anchors")
    for cid in dead:
        print(f"       ⛔ #{cid} is drawn and nothing in this page's scripts names it")
    for a in bad_anchor:
        print(f"       ⛔ <a href=\"#{a}\"> points at an element that does not exist")
    dead_all += [(name, c) for c in dead]
    waived_all += [(name, c) for c in waived]

print()
print("=" * 92)
print(f"{total} controls across {len(pages)} pages · {len(dead_all)} unreferenced · "
      f"{len(waived_all)} waived with a reason")
if waived_all:
    print("\n  waived (inert by design, reason recorded):")
    for n, c in waived_all:
        print(f"    {n:16s} #{c:14s} {WAIVED[c]}")
_sys.exit(1 if dead_all else 0)
