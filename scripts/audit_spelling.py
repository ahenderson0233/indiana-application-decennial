"""G127 guard: no British spelling in RENDERED text. Runs in the checkpoint so it cannot come back.

⛔ WHY AN AUDIT AND NOT JUST A FIX. `fix_american_spelling.py` rewrites 43 occurrences today and
will rewrite 0 tomorrow - and then someone writes "data centre" in a new panel and nothing
notices. The operator's complaint was that this had accumulated to 71 occurrences against 2
correct ones, which is what an unguarded convention looks like after three sessions.

⭐ AND IT CHECKS WHAT A READER SEES, NOT WHAT THE FILE CONTAINS. That distinction is the whole
design:
  - a COMMENT is not rendered. There are 25 of them in app.js alone, and failing the checkpoint
    over a comment would train everyone to ignore this audit.
  - `circle-color`, `fill-color`, `line-color` are MapLibre PAINT PROPERTIES. 92 of them.
  - `fits_mw_datacentre_at_4_per_acre` is a COLUMN NAME in the CSV the screener hands the user;
    renaming it changes an export contract.
  - `in_si_warn_normalised` is a table name.
⚠ It also catches what the fixer CANNOT reach: a template literal nested inside the `${...}` of
another template defeats the fixer's matcher, and three rendered occurrences survived the first
pass that way. The audit sees them because it reads text, not syntax.

RE-SCRAPE COMMAND: python scripts/audit_spelling.py
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

BRITISH = ["centre", "centres", "metre", "metres", "colour", "colours", "coloured",
           "behaviour", "behaviours", "licence", "licences", "programme", "programmes",
           "normalised", "normalise", "organised", "organisation", "defence", "analysed",
           "prioritised", "recognised"]
WORD_RE = re.compile(r"\b(" + "|".join(BRITISH) + r")\b", re.I)

# strip what is not rendered
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
LINE_COMMENT_RE = re.compile(r"(?<![:'\"`\\])//[^\r\n]*")
SCRIPT_RE = re.compile(r"<script\b[^>]*>(.*?)</script\s*>", re.S | re.I)
STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style\s*>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>", re.S)
IDENT_TOKEN_RE = re.compile(r"[A-Za-z0-9]*_[A-Za-z0-9_]*")
PROP_RE = re.compile(r"[a-z]+-colou?r|colou?r-[a-z]+", re.I)

assert WORD_RE.search("a data centre here"), "WORD_RE self-test"
assert not WORD_RE.search("circle-color"), "a paint property must not match a British word"
assert LINE_COMMENT_RE.search("// a data centre"), "LINE_COMMENT_RE self-test"
assert not LINE_COMMENT_RE.search('"https://x"'), "a URL is not a line comment"


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from js_prose import prose_text as js_literal_prose      # noqa: E402

# ⛔ THIS USED TO BE A PAIR OF REGEXES AND IT WENT WRONG IN BOTH DIRECTIONS BEFORE IT WENT RIGHT.
#    Scanning the whole file cried wolf - 35 findings, 31 of them JavaScript identifiers such as
#    `{ colour: "#16a34a" }` and `const metres = ...`, neither of which is ever rendered.
#    Narrowing it to a backtick regex then reported ZERO, because a template nested inside the
#    `${...}` of another template cannot be paired by a regex - and that is the shape almost every
#    rendered string in app.js is written in. Proven on an injected regression: 10 of 11 cases
#    passed and the one failure was exactly the nested case.
#    js_prose.py is a real lexer and carries that case as its first self-test.


def rendered_text(path):
    """Return only what a reader could see: no comments, no CSS, no tags, no identifiers."""
    blob = io.open(path, encoding="utf-8").read()
    if path.endswith(".html"):
        blob = HTML_COMMENT_RE.sub(" ", blob)
        blob = STYLE_RE.sub(" ", blob)
        # keep script BODIES - they build the tables - but strip their comments
        def keep_body(m):
            body = m.group(1)
            body = BLOCK_COMMENT_RE.sub(" ", body)
            body = LINE_COMMENT_RE.sub(" ", body)
            return " " + body + " "
        blob = SCRIPT_RE.sub(keep_body, blob)
        blob = TAG_RE.sub(" ", blob)
    else:
        blob = BLOCK_COMMENT_RE.sub(" ", blob)
        blob = LINE_COMMENT_RE.sub(" ", blob)
        blob = js_literal_prose(blob)
    blob = PROP_RE.sub(" ", blob)
    blob = IDENT_TOKEN_RE.sub(" ", blob)      # snake_case: column names, table names
    return blob


targets = [f for f in sorted(os.listdir(REPO)) if f.endswith(".html")] + ["app.js", "common.js"]
print("=" * 92)
print("G127 - BRITISH SPELLING IN RENDERED TEXT")
print("=" * 92)

findings = []
for fn in targets:
    p = os.path.join(REPO, fn)
    if not os.path.exists(p):
        continue
    text = rendered_text(p)
    for m in WORD_RE.finditer(text):
        ctx = re.sub(r"\s+", " ", text[max(0, m.start() - 46):m.end() + 46]).strip()
        findings.append((fn, m.group(1), ctx))

if findings:
    for fn, w, ctx in findings[:40]:
        print(f"  {fn:16} {w:12} …{ctx}…")
    if len(findings) > 40:
        print(f"  … and {len(findings) - 40} more")
else:
    print("  no British spelling in any rendered string")

print(f"\n  scanned {len(targets)} files")
print(f"  {len(findings)} finding(s) in RENDERED text")
print("  ⚠ comments, MapLibre paint properties, CSS and snake_case identifiers are excluded by")
print("    construction - see the header for why each one is not a defect.")
print("=" * 92)
sys.exit(1 if findings else 0)
