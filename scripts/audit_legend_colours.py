"""G149: DOES EVERY SWATCH THE APP DRAWS ACTUALLY HAVE A COLOUR?

Operator, 2026-08-21: *"The bus legend doesn't populate bus headroom colors anymore; additionally,
we don't actually show what the color bands mean for transmission lines."*
⚠ *"anymore"* means REGRESSION, and the operator's own note on the row said it: **no audit exists
that would have caught it.** This is that audit.

================================================================================================
⛔ WHAT WENT WRONG, AND WHY NINE EXISTING AUDITS ALL PASSED THROUGH IT
================================================================================================
`renderLayerLegend()` in app.js emits swatches as `style="background:${EXPR}"`. Five of those
EXPRs named a property that does not exist, because the DATA said `colour` and the READER said
`color`:

    BUS_BANDS / TERR_TYPES / RANK_BANDS / dcTiers() / layerSwatch()   ->  declare `colour`
    renderLayerLegend()                                              ->  read `color`

Measured live before the fix:
  · all five bus bands rendered `style="background:undefined"` — the reported symptom
  · ticking service territories, the data-centre pins, or a painted ranking threw
    **`ReferenceError: color is not defined`**, which aborts the whole function, so the key froze
    on its last good render and silently stopped tracking the map

⭐ THE TWO FAILURE MODES ARE THE INTERESTING PART. `obj.color` on an object that has `colour` is a
silent `undefined`. A BARE `${color}` on an undeclared name is a hard ReferenceError. Same typo,
one shows a blank chip and the other kills the panel — which is exactly why only one half of it
was ever reported.

⚠ WHY NOTHING CAUGHT IT:
  · `audit_frontend.py`      - checks element ids and payload keys. A property name is neither.
  · `audit_js_duplicates.py` - checks redeclaration in a scope. This is a NON-declaration.
  · `audit_page_controls.py` / `audit_map_clicks.py` - check bindings, not rendered output.
  · `audit_spelling.py`      - deliberately EXCLUDES identifiers, and correctly so: MapLibre's own
    paint keys are `circle-color` / `line-color`, so banning `color` outright would be wrong.
⛔ The boundary between MapLibre's American spelling and this codebase's British one is precisely
where the bug lives. This audit polices that boundary instead of banning either side.

================================================================================================
WHAT IT CHECKS
================================================================================================
1. Every `background:${EXPR}` in the JS resolves:
     · a bare identifier  -> must be BOUND somewhere in the file (const/let/var/param/destructure)
     · a property read    -> that key must appear as a key in some object literal in the file
     · anything else (a call, escHtml(...)) -> unwrapped and re-checked
2. The transmission-line key has the SAME number of bands as the paint expression draws.
   ⛔ It did not: the hand-typed panel key listed 6 where the paint draws 7, silently omitting
   `500-734 kV` — a whole voltage class, on the map, absent from its own key.

⛔ READ-ONLY. Parses source; writes nothing, queries nothing.

RE-SCRAPE COMMAND: python scripts/audit_legend_colours.py
"""
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["app.js", "common.js", "screener.html", "si.html", "index.html"]

# `${ ... }` immediately after a CSS colour-bearing property inside a template literal
SWATCH = re.compile(r"background(?:-color)?\s*:\s*\$\{([^}]+)\}")
# strip one layer of wrapping calls: escHtml(x) -> x
UNWRAP = re.compile(r"^[A-Za-z_$][\w$]*\((.*)\)$")

# ⚠ Names bound by any of these forms count as declared. Destructuring is included because three
# of the five G149 defects were `for (const [, colour, label] of ...)` paired with `${color}`.
def bound_names(src):
    names = set()
    for pat in (r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)",
                r"\bfunction\s+([A-Za-z_$][\w$]*)",
                r"\bfunction\s*\([^)]*\)",                 # params handled below
                r"\bcatch\s*\(\s*([A-Za-z_$][\w$]*)"):
        for m in re.finditer(pat, src):
            if m.groups() and m.group(1):
                names.add(m.group(1))
    # every identifier inside a destructuring pattern or a parameter list
    for m in re.finditer(r"(?:const|let|var)\s*[\[{]([^\]}]*)[\]}]\s*=", src):
        names.update(re.findall(r"[A-Za-z_$][\w$]*", m.group(1)))
    for m in re.finditer(r"\(([^)]*)\)\s*=>", src):
        names.update(re.findall(r"[A-Za-z_$][\w$]*", m.group(1)))
    for m in re.finditer(r"\bfunction\s*[A-Za-z_$\w]*\s*\(([^)]*)\)", src):
        names.update(re.findall(r"[A-Za-z_$][\w$]*", m.group(1)))
    return names


def literal_keys(src):
    """Every key used in an object literal, e.g. `{ colour: "#fff" }` -> {"colour"}."""
    return set(re.findall(r"[{,]\s*([A-Za-z_$][\w$]*)\s*:", src))


def sibling(name):
    """The British/American twin of a colour-ish name, if there is one."""
    if "colour" in name:
        return name.replace("colour", "color")
    if "color" in name:
        return name.replace("color", "colour")
    return None


print("=" * 96)
print("G149 - EVERY SWATCH THE APP DRAWS MUST HAVE A COLOUR")
print("=" * 96)

fails = []
checked = 0
for fn in FILES:
    path = os.path.join(REPO, fn)
    if not os.path.exists(path):
        continue
    src = io.open(path, encoding="utf-8").read()
    names, keys = bound_names(src), literal_keys(src)
    for m in SWATCH.finditer(src):
        expr = m.group(1).strip()
        checked += 1
        u = UNWRAP.match(expr)
        if u:
            expr = u.group(1).strip()
        line = src[:m.start()].count("\n") + 1
        if re.fullmatch(r"[A-Za-z_$][\w$]*", expr):
            if expr not in names:
                sib = sibling(expr)
                extra = (f" — but `{sib}` IS bound here; the declaration and the reader "
                         f"disagree on the spelling" if sib and sib in names else "")
                fails.append(f"{fn}:{line}  `${{{expr}}}` is NOT DECLARED anywhere in this file"
                             f"{extra}. At runtime this is a ReferenceError and it aborts the "
                             f"whole render.")
        elif re.fullmatch(r"[A-Za-z_$][\w$]*\.[A-Za-z_$][\w$]*", expr):
            obj, key = expr.split(".")
            if key not in keys:
                sib = sibling(key)
                extra = (f" — but `{sib}` is a key on an object literal in this file; the "
                         f"declaration and the reader disagree on the spelling"
                         if sib and sib in keys else "")
                fails.append(f"{fn}:{line}  `${{{expr}}}` reads a key `{key}` that no object "
                             f"literal here declares{extra}. At runtime this renders "
                             f"`background:undefined` — a blank chip, silently.")

print(f"  {checked} swatch interpolation(s) checked across {len(FILES)} file(s)")

# ------------------------------------------------------------------ the line-band count check
app = io.open(os.path.join(REPO, "app.js"), encoding="utf-8").read()
m = re.search(r"const LINE_KV_BANDS\s*=\s*\[(.*?)\n\];", app, re.S)
if not m:
    fails.append("app.js: LINE_KV_BANDS is gone. The transmission-line palette must have ONE "
                 "definition that the paint, the panel key and the corner Key all read.")
else:
    n_bands = len(re.findall(r"^\s*\[", m.group(1), re.M))
    # ⚠ ANCHOR ON THE LAYER, NOT ON A CHARACTER WINDOW. The first version of this probe read the
    # 400 characters after the first `line-color` in the file and asked whether LINE_KV_BANDS was
    # among them — which found a DIFFERENT layer's paint and reported a failure that did not
    # exist. "A hardcoded verdict is not a probe" applies to a hardcoded WINDOW just as much.
    blk = re.search(r'id:\s*"grid-lines"(.*?)(?=map\.addLayer|\Z)', app, re.S)
    paint_uses = bool(blk) and "LINE_KV_BANDS" in blk.group(1)
    corner = 'box === "L-lines"' in app
    print(f"  LINE_KV_BANDS declares {n_bands} band(s)")
    if n_bands < 7:
        fails.append(f"app.js: LINE_KV_BANDS has {n_bands} bands; the audited voltage classes are "
                     f"7 (735+, 500-734, 300-499, 200-299, 100-199, under 100, unknown). The "
                     f"hand-typed key that this replaced was missing 500-734 entirely.")
    if not paint_uses:
        fails.append("app.js: the grid-lines paint does not build from LINE_KV_BANDS — the "
                     "palette is typed twice again, which is how 500-734 went missing.")
    if not corner:
        fails.append("app.js: the corner Key does not spell out the line bands (no "
                     "`box === \"L-lines\"` branch). Voltage is the first thing a siter reads off "
                     "a line; 'banded' is not a key.")

print("\n" + "=" * 96)
if fails:
    print(f"{len(fails)} LEGEND COLOUR FAILURE(S):")
    for f in fails:
        print(f"  ⛔ {f}")
    print("=" * 96)
    sys.exit(1)
print("0 legend colour failure(s) — every swatch resolves, and the line bands have one definition")
print("=" * 96)
