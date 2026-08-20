"""Is any top-level name declared TWICE in the scripts one page loads?

    python scripts/audit_js_duplicates.py

WHY THIS EXISTS, and it is the project's own §2.15c defect wearing front-end clothes.

`common.js` and `app.js` BOTH declared `async function fetchGz(url)`. Pages load common.js first
and app.js second, so app.js's copy silently WON -- on the map console, which is the heaviest
payload consumer in the application and the only page that fetches the 92 on-demand county files.

Nothing errored. Nothing could error: a duplicate `function` declaration in classic scripts is
legal JavaScript and the last one simply replaces the first.

The cost, measured 2026-08-19b: the G101 payload cache-bust was written into common.js, verified
present in the running page (`payloadVersions` was defined and callable), and STILL did nothing,
because the `fetchGz` the page actually called was the other one. Four lines above app.js's copy
sat a comment reading "fmt + fetchGz come from common.js (loaded first)" -- the comment described
the intent and the code contradicted it, in plain sight, for as long as both existed.

⚠ THE THREE COLLISION KINDS ARE NOT EQUALLY DANGEROUS, so they are reported separately:

  function/function  SILENT. Legal, last-wins, no diagnostic anywhere. This is the one that bites.
  var/anything       SILENT. Merges into one binding.
  const|let/anything FATAL and LOUD -- "Identifier 'x' has already been declared" takes the whole
                     page down at parse time. Dangerous, but it announces itself, so it never
                     survives to production the way a silent override does.

⚠ WHY IT IS TEXT-BASED AND WHAT THAT COSTS. There is no JS parser here (node is not installed on
this machine), so declarations are found by requiring COLUMN ZERO -- a real top-level declaration
is never indented in this codebase. That deliberately under-reports: a top-level declaration
written with leading whitespace is missed. It does not over-report, which matters more, because an
audit that cries wolf gets ignored (the rule audit_map_clicks.py had to learn twice).
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import io
import os
import re
import glob

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Column-zero declarations only -- see the header note on why this under-reports on purpose.
DECL = re.compile(
    r"^(?:async\s+)?(function|const|let|var|class)\s+([A-Za-z_$][\w$]*)",
    re.MULTILINE,
)
# <script src="foo.js?v=abc"> -- the stamp query has to come off before the file can be opened.
SCRIPT_SRC = re.compile(r'<script[^>]+src="([^"]+)"')
INLINE = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>")

SELFTEST = """
function alpha() {}
const beta = 1;
  function indented() {}
async function gamma() {}
"""


def declarations(text):
    """-> {name: kind}. Later duplicates inside ONE file are reported by the caller."""
    return DECL.findall(text)


def _selftest():
    got = dict((n, k) for k, n in declarations(SELFTEST))
    assert got.get("alpha") == "function", got
    assert got.get("beta") == "const", got
    assert got.get("gamma") == "function", got
    assert "indented" not in got, "column-zero rule broke: indented decl was picked up"
    # the exact defect this audit was written for
    two = declarations("async function fetchGz(u) {}\nasync function fetchGz(u) {}\n")
    assert len(two) == 2, two


_selftest()

pages = sorted(glob.glob(os.path.join(REPO, "*.html")))
findings = []          # (page, name, kind_a, file_a, kind_b, file_b)
per_page_scripts = {}
page_units = {}

for page in pages:
    name = os.path.basename(page)
    src = io.open(page, encoding="utf-8").read()
    units = []  # (label, text) in LOAD ORDER, which is what decides the winner
    for s in SCRIPT_SRC.findall(src):
        f = s.split("?")[0]
        p = os.path.join(REPO, f.replace("/", os.sep))
        if not os.path.exists(p):
            continue
        if "vendor" in f:
            continue  # vendored third-party: not ours to deduplicate
        units.append((f, io.open(p, encoding="utf-8").read()))
    for i, blk in enumerate(INLINE.findall(src)):
        units.append((f"{name} inline#{i + 1}", blk))
    per_page_scripts[name] = [u[0] for u in units]
    # keep the SOURCE too, for the same-scope redeclaration check at the bottom
    page_units[name] = units

    seen = {}  # declared name -> (kind, label)
    for label, text in units:
        for kind, ident in declarations(text):
            if ident in seen:
                k0, l0 = seen[ident]
                findings.append((name, ident, k0, l0, kind, label))
            seen[ident] = (kind, label)

print("=" * 92)
print("JS TOP-LEVEL DUPLICATE DECLARATIONS")
print("=" * 92)
for p in pages:
    n = os.path.basename(p)
    print(f"  {n:18s} loads {', '.join(per_page_scripts[n]) or '(no scripts)'}")

# One collision usually shows up on several pages; report the DEFECT once, and list the pages.
by_defect = {}
for page, ident, k0, l0, k1, l1 in findings:
    by_defect.setdefault((ident, k0, l0, k1, l1), []).append(page)

silent = [d for d in by_defect if d[1] == "function" and d[3] == "function"]
varish = [d for d in by_defect if d not in silent and ("var" in (d[1], d[3]))]
fatal = [d for d in by_defect if d not in silent and d not in varish]

print()
if not by_defect:
    print("  no top-level name is declared twice in any page's script set")
else:
    for title, group, note in [
        ("SILENT OVERRIDE (function/function) - the dangerous kind, no diagnostic anywhere",
         silent, "the LATER file wins"),
        ("SILENT MERGE (var)", varish, "one binding, last assignment wins"),
        ("FATAL AT PARSE TIME (const/let) - loud, takes the page down", fatal,
         "SyntaxError: Identifier has already been declared"),
    ]:
        if not group:
            continue
        print(f"  {title}")
        for d in sorted(group):
            ident, k0, l0, k1, l1 = d
            pgs = sorted(set(by_defect[d]))
            print(f"    {ident:22s} {k0} in {l0}  ->  {k1} in {l1}   ({note})")
            print(f"    {'':22s} on: {', '.join(pgs)}")
        print()

n_real = len(silent) + len(varish) + len(fatal)
print(f"{n_real} duplicate top-level name(s) across {len(pages)} pages")

# =============================================================================================
# ⛔ SECOND CHECK, ADDED 2026-08-20 BECAUSE THE FIRST ONE MISSED A PAGE-KILLER.
#
# The check above compares TOP-LEVEL names across a page's script set. market.html was taken
# down by a collision invisible to it: a new `const usd` was added inside the same async IIFE
# that already declared one 66 lines further down. Same block, same scope, so
# `SyntaxError: Identifier 'usd' has already been declared` -- and because a syntax error aborts
# the WHOLE script, every panel on the page went blank, not just the new one.
#
# ⚠ THE SYMPTOM IS INDISTINGUISHABLE FROM A DATA PROBLEM: the page renders its HTML shell and
# every value stays on its "measuring..." placeholder, which is exactly what a missing payload
# looks like. The natural next step is to go and debug the export -- the wrong file entirely.
#
# ⛔ THE FIRST ATTEMPT AT THIS CHECK CRIED WOLF AND WAS DELETED, WHICH IS WORTH RECORDING.
# It treated "same indentation" as "same scope" and reported 249 findings, nearly all of them
# `const el` or `const s` in two different functions that happen to be indented alike. That is
# legal JavaScript and the rule this repo has learned twice already is that an audit which cries
# wolf gets ignored. Indentation is a formatting convention; scope is braces. So this tracks
# BRACES: strings, template literals, comments and regex literals are removed first, then every
# `{` pushes a unique block id. Two declarations collide only when their block PATH is identical.
# =============================================================================================


def strip_js(src):
    """Blank out strings, template literals, comments and regex literals, keeping newlines.

    Brace counting is only sound if no brace inside a string or comment is counted. Characters
    are replaced with spaces rather than deleted so line numbers survive for the report.
    ⚠ `${` inside a template literal is kept as a brace pair, because it genuinely is one and
    it nests -- dropping it would unbalance every template in app.js.
    """
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            j = src.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i)); i = j
        elif c == "/" and nxt == "*":
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join(ch if ch == "\n" else " " for ch in src[i:j])); i = j
        elif c in "\"'":
            j, q = i + 1, c
            while j < n and src[j] != q:
                j += 2 if src[j] == "\\" else 1
            j = min(j + 1, n)
            out.append("".join(ch if ch == "\n" else " " for ch in src[i:j])); i = j
        elif c == "`":
            # template literal: blank the text but KEEP the ${ } braces, which really do nest
            j, depth = i + 1, 0
            buf = [" "]
            while j < n:
                ch = src[j]
                if ch == "\\":
                    buf.append("  "); j += 2; continue
                if ch == "$" and j + 1 < n and src[j + 1] == "{":
                    buf.append(" {"); depth += 1; j += 2; continue
                if ch == "}" and depth:
                    buf.append("}"); depth -= 1; j += 1; continue
                if ch == "`" and not depth:
                    buf.append(" "); j += 1; break
                buf.append(ch if ch == "\n" else " "); j += 1
            out.append("".join(buf)); i = j
        else:
            out.append(c); i += 1
    return "".join(out)


_st = strip_js('const a = "x{y"; /* {{{ */ const b = `t${ {q:1} }u`; // }}}\nconst c = 1;')
assert _st.count("{") == _st.count("}"), f"strip_js unbalanced: {_st!r}"
assert "const c" in _st and "x{y" not in _st, _st

DECL_ANY = re.compile(r"(?:^|[;{}\)]|\bawait\b|\breturn\b|\s)(const|let)\s+([A-Za-z_$][\w$]*)\s*=")

print()
print("=" * 92)
print("SAME-SCOPE REDECLARATION - fatal at parse time, and it blanks the ENTIRE page")
print("=" * 92)
scope_hits = []
for page, units in page_units.items():
    for label, raw in units:
        src = strip_js(raw)
        stack, nblk, seen = [], 0, {}
        line = 1
        pos_line = {}
        for idx, ch in enumerate(src):
            if ch == "\n":
                line += 1
            pos_line[idx] = line
        for m in re.finditer(r"[{}]|(?:^|[;{}\)]|\s)(?:const|let)\s+[A-Za-z_$][\w$]*\s*=",
                             src, re.M):
            tok = m.group(0)
            if tok == "{":
                nblk += 1; stack.append(nblk); continue
            if tok == "}":
                if stack:
                    stack.pop()
                continue
            dm = DECL_ANY.search(tok)
            if not dm:
                continue
            name = dm.group(2)
            key = (tuple(stack), name)
            ln = pos_line.get(m.start(), 0)
            if key in seen:
                scope_hits.append((page, label, name, dm.group(1), seen[key], ln))
            else:
                seen[key] = ln
for page, where, name, kind, first, second in scope_hits:
    print(f"  ⛔ {page} [{where}]: `{kind} {name}` declared twice in ONE scope "
          f"(lines {first} and {second})")
if not scope_hits:
    print("  no const/let is declared twice inside a single scope")
print(f"\n{len(scope_hits)} same-scope redeclaration(s)")
_sys.exit(1 if (n_real or scope_hits) else 0)
