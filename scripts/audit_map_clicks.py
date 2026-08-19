"""Which drawn map layers have NO click handler?

    python scripts/audit_map_clicks.py

Operator, 2026-08-19: *"analyze the clicking mechanism throughout the map console and determine a
fix to see the popups for all of the applicable layers, rather than just having the county popup
generate."*

A layer with no click is invisible to the reader in the way that matters: they can see the thing
and cannot ask what it is. It fails SILENTLY -- MapLibre does not complain about a layer nobody
bound -- so it is exactly the class of defect that survives a code read. The logistics layer was
drawn and inert for weeks for this reason.

⚠ THE AUDIT ITSELF HAD TO BE FIXED TWICE, which is the part worth keeping. A first version used
one multiline regex for looped bindings and reported `fac-*` and `water-*` as unbound when both
are bound -- the loop variable is not always `id`, and one loop body is longer than the window it
allowed. Rule 9 here is that an audit which cries wolf gets ignored, so detection is now
LINE-BASED: find each loop over a literal id list, then look ahead a bounded number of lines for a
click bound to that loop's own variable.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import io
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = io.open(os.path.join(REPO, "app.js"), encoding="utf-8").read()
LINES = APP.split("\n")

# Layers that legitimately have no click, each with the reason stated. A waiver has to be written
# down; an unexplained omission is the defect.
WAIVED = {
    "county-line": "a hairline border, not a subject -- county-fill carries the click",
    "grid-bus-label": "the text label for grid-bus, which is itself clickable",
    "water-ws-line": "the watershed OUTLINE; water-ws-fill carries the click for the same feature",
    "measure-line": "the measure tool's own overlay -- clicking it would fight the tool",
    "measure-pts": "ditto",
    "sel-parcel-fill": "the highlight drawn ON a selected parcel; the parcel layer owns the click",
    "sel-parcel-line": "ditto",
}

added = set(re.findall(r'addLayer\(\{\s*id:\s*"([^"]+)"', APP))
# layers built inside a loop over [kind, id, colour] triples (the G65 tax-credit split)
added |= set(re.findall(r'\[\s*"[a-z_]+",\s*"(env-bonus-[a-z]+)"', APP))

# 1. direct bindings
clicked = set(re.findall(r'map\.on\(\s*"click",\s*"([^"]+)"', APP))

# 2. looped bindings, line-based (see the header note)
for i, ln in enumerate(LINES):
    m = re.search(r"for \(const (\w+) of \[([^\]]+)\]\)", ln)
    if not m:
        continue
    var, lst = m.group(1), m.group(2)
    window = "\n".join(LINES[i:i + 40])
    if re.search(r'map\.on\(\s*"click",\s*' + re.escape(var) + r"\b", window):
        clicked |= set(re.findall(r'"([^"]+)"', lst))

# 3. the `clickable` object map, iterated as [id, fn]
for m in re.finditer(r"const clickable = \{([\s\S]*?)\};", APP):
    clicked |= set(re.findall(r'"([a-z][a-z0-9-]+)"\s*:', m.group(1)))

# 4. CONTEXT_LAYERS values, bound in their own loop over Object.entries
for m in re.finditer(r"const CONTEXT_LAYERS = \{([\s\S]*?)\};", APP):
    clicked |= set(re.findall(r':\s*"([^"]+)"', m.group(1)))

tmpl = re.findall(r'map\.on\(\s*"click",\s*`([^`]+)`', APP)

print(f"{len(added)} layers drawn, {len(clicked)} carry a click binding")
if tmpl:
    print(f"  (+ template-literal bindings, not name-matchable: {tmpl})")

real = []
print("\nLAYERS WITHOUT A DIRECT CLICK")
for a in sorted(added - clicked):
    why = WAIVED.get(a)
    if why:
        print(f"  waived   {a:20s} {why}")
    else:
        print(f"  NONE     {a}")
        real.append(a)

print(f"\n{len(real)} layer(s) the reader can see and cannot ask about: {real or 'none'}")
_sys.exit(1 if real else 0)
