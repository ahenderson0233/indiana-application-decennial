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
    # 2026-08-20 (G105): the same case as water-ws-line and grid-bus-label. terr-fill IS bound and
    # covers the identical polygon, so a click anywhere on a territory already answers; binding
    # the outline and the text as well would open the same panel from three overlapping hit areas.
    "terr-line": "the service-territory OUTLINE; terr-fill carries the click for the same polygon",
    "terr-label": "the text label for terr-fill, which is itself clickable",
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

# 4. LAYER-GROUP OBJECTS bound in a loop over Object.values / Object.entries.
#
# ⚠ FIXED 2026-08-20, AND IT WAS CRYING WOLF AGAIN — the third time this audit has. This rule
#   used to name `CONTEXT_LAYERS` literally. G110 then added `ENVGATE_LAYERS` in exactly the same
#   shape, bound in exactly the same way, and the audit reported `env-flood` and `env-wet` as
#   "drawn and unclickable" for a whole session. They were bound the entire time, in
#   `for (const id of Object.values(ENVGATE_LAYERS))`. The handoff carried that false finding
#   forward as G105 work.
#
# ⛔ A HARDCODED LIST OF GROUP NAMES IS THE SAME DEFECT AS A HARDCODED WIRING COUNT: correct until
#   someone adds one, then silently wrong. Detect the SHAPE instead — any `const X = {...}` whose
#   members are iterated with Object.values/Object.entries in a body that binds a click. That
#   covers CONTEXT_LAYERS, ENVGATE_LAYERS, WIRED_LAYERS and whatever comes next, with no list.
# ⚠ BOTH SHAPES. CONTEXT_LAYERS and ENVGATE_LAYERS are declared on ONE line; WIRED_LAYERS spans
#   many. A pattern requiring the closing brace on its own line silently dropped the single-line
#   ones and re-broke ctx-ghgrp/ctx-frpp the moment it was introduced. Non-greedy to the first
#   `};` is correct here because every one of these objects is flat.
for gname, body in re.findall(r"const ([A-Z][A-Z_]*) = \{([\s\S]*?)\};", APP):
    # Is this group iterated anywhere, and does THAT loop bind a click? Check every iteration
    # site, not just the first: LAYER_MAP is iterated in syncLayers (no clicks) long before
    # anywhere else, so stopping at the first occurrence would test the wrong loop.
    hit = False
    for it in re.finditer(r"Object\.(?:values|entries)\(" + re.escape(gname) + r"\)", APP):
        # 1,200 characters is generous enough for an inner `for (const id of ids)` and the
        # three handler lines that follow it.
        if re.search(r'map\.on\(\s*"click",\s*\w+', APP[it.start():it.start() + 1200]):
            hit = True
            break
    if not hit:
        continue
    # A member is either `"L-x": "layer-id"` or `"L-x": ["layer-a", "layer-b"]`. Harvesting EVERY
    # quoted string in the body also picks up the checkbox keys, which is harmless: a key like
    # "L-water" can never collide with a drawn layer id, so it cannot mark anything wired.
    clicked |= set(re.findall(r'"([^"]+)"', body))

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
