"""G127: American spelling in RENDERED TEXT ONLY. Operator: *"we call it 'data center' here."*

⛔ THE ONE THING THIS MUST NOT BE IS A FIND-AND-REPLACE. `circle-color`, `fill-color`,
`line-color`, `circle-stroke-color` and `fill-outline-color` are MapLibre PAINT PROPERTIES -
measured 92 occurrences across the pages - and renaming any of them kills a layer's styling
silently, with no error and nothing in the console. CSS `color` is the same hazard, and
`in_si_warn_normalised` is a table name.

WHAT IS CHANGED
  HTML  text nodes only. Everything inside <script> and <style> is skipped whole, and so is
        every tag's attribute region - so `class="..."`, `id="..."` and any inline style are
        untouched by construction rather than by a blocklist.
  JS    string literals only, and only those that look like prose. A literal that is or contains
        a CSS/MapLibre property, a table name or a URL is skipped.

WHAT IS DELIBERATELY LEFT ALONE
  ⚠ JS IDENTIFIERS. `colourExpr`, `colours`, `recolour` and friends - 63 occurrences in app.js -
    are internal names the reader never sees. G127 asks for rendered text, the operator's
    complaint is about what a user reads, and renaming a symbol is a different change with a
    different risk. They are reported at the end so the decision is visible, not silent.
  ⚠ `grey` inside a colour value. It is a valid CSS keyword; changing it is cosmetic churn in a
    place where a typo is invisible until a layer stops painting.

RE-SCRAPE COMMAND: python scripts/fix_american_spelling.py [--check]
⚠ IDEMPOTENT: replace_safe - re-running finds nothing left to change.
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
CHECK = "--check" in sys.argv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from js_prose import rewrite_prose      # noqa: E402

# British -> American, longest first so `centres` is handled before `centre`.
PAIRS = [
    ("Centres", "Centers"), ("centres", "centers"), ("Centre", "Center"), ("centre", "center"),
    ("Metres", "Meters"), ("metres", "meters"), ("Metre", "Meter"), ("metre", "meter"),
    ("Colours", "Colors"), ("colours", "colors"), ("Coloured", "Colored"),
    ("coloured", "colored"), ("Colour", "Color"), ("colour", "color"),
    ("Behaviours", "Behaviors"), ("behaviours", "behaviors"),
    ("Behaviour", "Behavior"), ("behaviour", "behavior"),
    ("Licences", "Licenses"), ("licences", "licenses"), ("Licence", "License"),
    ("licence", "license"),
    ("Programmes", "Programs"), ("programmes", "programs"),
    ("Programme", "Program"), ("programme", "program"),
    ("Normalised", "Normalized"), ("normalised", "normalized"),
    ("Normalise", "Normalize"), ("normalise", "normalize"),
    ("Organised", "Organized"), ("organised", "organized"),
    ("Organisation", "Organization"), ("organisation", "organization"),
    ("Defence", "Defense"), ("defence", "defense"),
    ("Analysed", "Analyzed"), ("analysed", "analyzed"),
    ("Prioritised", "Prioritized"), ("prioritised", "prioritized"),
    ("Recognised", "Recognized"), ("recognised", "recognized"),
]

# ⛔ Anything matching these is left exactly as it is.
SKIP = re.compile(
    r"-colou?r\b"                      # circle-color, fill-color, line-color, text-color, ...
    r"|colou?r-"                       # color-scheme, colour-…
    r"|in_si_warn_normalised"          # a table name
    r"|https?://"                      # a URL
    r"|\.css\b|\.js\b"                 # asset paths
    , re.I)

# a JS string literal, single or double quoted, no newline inside
JSSTR_RE = re.compile(r"(['\"])((?:\\.|(?!\1)[^\\\r\n])*)\1")
# an HTML tag - everything between < and > is attribute territory and is never touched
TAG_SPLIT_RE = re.compile(r"(<[^>]*>)", re.S)
# ⛔ THE INNER GROUP MUST BE NON-CAPTURING, AND GETTING THAT WRONG CORRUPTED SEVEN PAGES.
# `re.split` returns EVERY capture group, not just the outer one. With `(<(script|style)\b...)`
# the split output interleaved the inner group's text - the bare word "script" - between the
# chunks, and the loop below appended it as if it were content. Result: `</script>scriptscript`
# rendered as visible garbage on community, data, insights, market and screener. Caught by
# reading the page in a browser, not by any audit - the markup is still well-formed, so nothing
# structural could see it.
SCRIPT_STYLE_RE = re.compile(r"(<(?:script|style)\b.*?</(?:script|style)\s*>)", re.S | re.I)
assert SCRIPT_STYLE_RE.split("a<script>x</script>b") == ["a", "<script>x</script>", "b"], \
    "re.split must yield exactly three parts - an inner capture group would add a fourth"
IDENT_RE = re.compile(r"\b[A-Za-z_$][A-Za-z0-9_$]*(?:colour|Colour)[A-Za-z0-9_$]*\b")
# a backtick template literal, and the ${...} interpolations inside it
TPL_RE = re.compile(r"`((?:\\.|[^`\\])*)`", re.S)
INTERP_RE = re.compile(r"\$\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.S)

# self-tests, at module level, typed with an editor - never through a shell heredoc
assert SKIP.search("circle-color") and SKIP.search("fill-color") and SKIP.search("line-color")
assert not SKIP.search("the data centre is here")
assert JSSTR_RE.findall('a = "data centre";')[0][1] == "data centre"
assert TAG_SPLIT_RE.split('<p class="a">centre</p>') == ['', '<p class="a">', 'centre', '</p>', '']


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def swap(text):
    """Apply the pairs to a run of prose, token by token, honouring SKIP.

    ⚠ TOKEN-WISE, NOT SUBSTRING-WISE, AND THE REASON IS A LIVE HAZARD. A plain replace also
    rewrites `fits_mw_datacentre_at_4_per_acre`, which is a COLUMN NAME in the CSV the screener
    hands the user - renaming it silently changes an export contract and breaks every saved
    spreadsheet built on it. Any token containing an underscore is an identifier, a column name
    or a table name, and is left alone. Same reasoning as the MapLibre paint properties: the
    thing that looks like a spelling mistake is sometimes a key.
    """
    if SKIP.search(text):
        return text, 0
    n = 0

    def one(m):
        nonlocal n
        tok = m.group(0)
        if "_" in tok:
            return tok                      # identifier / column name / table name
        for a, b in PAIRS:
            if a in tok:
                n += tok.count(a)
                tok = tok.replace(a, b)
        return tok

    return TOKEN_RE.sub(one, text), n


def fix_js(blob):
    """Rewrite only the RENDERED PROSE spans, via the js_prose lexer.

    ⛔ THIS WENT THROUGH TWO WRONG VERSIONS AND BOTH LOOKED FINE.
      v1 handled '...' and "..." only. This codebase builds its HTML in BACKTICK TEMPLATES, so it
         reported 65 changes while 42 occurrences of "centre" sat untouched in app.js.
      v2 added a backtick regex. A regex cannot pair a template nested inside the `${...}` of
         another template - it closes the outer one on the inner backtick - and that is the shape
         almost every rendered string here is written in. Six real occurrences survived, and the
         matching audit then reported ZERO and looked like a clean bill of health.
    js_prose.prose_spans is a real lexer with the nested case as its first self-test.
    """
    return rewrite_prose(blob, swap)


def fix_html(blob):
    """Text nodes only. <script>/<style> bodies and all tag interiors are skipped whole."""
    total = 0
    out = []
    for chunk in SCRIPT_STYLE_RE.split(blob):
        if not chunk:
            continue
        if chunk.lower().startswith("<style"):
            out.append(chunk)                      # CSS: untouched, entirely
            continue
        if chunk.lower().startswith("<script"):
            # ⛔ NOT UNTOUCHED. Skipping <script> whole left 7 occurrences in screener.html and
            # 6 in data.html, and they are the rendered ones - every page here builds its tables
            # in an inline script. The script BODY is run through the JS rules (string and
            # template literals only), while the <script ...> tag itself stays as it is.
            head = chunk[:chunk.index(">") + 1]
            tail = chunk[chunk.lower().rindex("</script"):]
            body = chunk[len(head):len(chunk) - len(tail)]
            body, k = fix_js(body)
            total += k
            out.append(head + body + tail)
            continue
        parts = TAG_SPLIT_RE.split(chunk)
        for i, part in enumerate(parts):
            if part.startswith("<") and part.endswith(">"):
                continue                           # a tag: attribute territory
            parts[i], k = swap(part)
            total += k
        out.append("".join(parts))
    return "".join(out), total


targets = [f for f in sorted(os.listdir(REPO)) if f.endswith(".html")] + ["app.js", "common.js"]
print("G127 - AMERICAN SPELLING, RENDERED TEXT ONLY")
print(f"  {'file':18} {'changes':>8}")
grand = 0
for fn in targets:
    p = os.path.join(REPO, fn)
    if not os.path.exists(p):
        continue
    blob = io.open(p, encoding="utf-8").read()
    new, n = fix_html(blob) if fn.endswith(".html") else fix_js(blob)
    grand += n
    if n and not CHECK:
        io.open(p, "w", encoding="utf-8", newline="").write(new)
    print(f"  {fn:18} {n:>8}{'  (check only, not written)' if CHECK and n else ''}")
print(f"  {'TOTAL':18} {grand:>8}")

# ---- prove the hazard survived ---------------------------------------------------------------
print("\n  MapLibre paint properties still intact (a blind replace would have killed these):")
for prop in ("circle-color", "fill-color", "line-color", "text-color",
             "circle-stroke-color", "fill-outline-color"):
    n = sum(io.open(os.path.join(REPO, f), encoding="utf-8").read().count(prop)
            for f in targets if os.path.exists(os.path.join(REPO, f)))
    print(f"    {prop:22} {n:>4}")

ids = set()
for fn in ("app.js", "common.js"):
    p = os.path.join(REPO, fn)
    if os.path.exists(p):
        ids |= set(IDENT_RE.findall(io.open(p, encoding="utf-8").read()))
if ids:
    print(f"\n  ⚠ {len(ids)} JS IDENTIFIER(S) LEFT ALONE ON PURPOSE - internal names, never rendered:")
    print(f"    {', '.join(sorted(ids))}")
    print("    Renaming a symbol is a different change with a different risk. Reported, not hidden.")
print("\nSPELLING PASS COMPLETE")
