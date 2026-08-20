"""A small JS lexer that yields the RENDERED PROSE spans of a script, and nothing else.

⛔ WHY THIS EXISTS RATHER THAN ANOTHER REGEX. Both `fix_american_spelling.py` and
`audit_spelling.py` were built on a backtick regex, and both had the SAME blind spot in the SAME
place: a template literal nested inside the `${...}` of another template. A regex cannot pair
those - it closes the outer template on the inner backtick and reads the rest of the file as
code. This codebase builds nearly all of its rendered HTML in exactly that shape:

    `<div class="sowhat">${x.jobs ? `<b>The data-centre industry employs ...</b>` : ""}</div>`

So the fixer silently skipped those spans, and the audit then reported ZERO findings and looked
like a clean bill of health. A guard that cannot see the one construct the code is written in is
worse than no guard: it converts an unchecked convention into a checked-looking one.

WHAT COUNTS AS PROSE
  - the body of a '...' or "..." string
  - the literal parts of a `...` template, at any nesting depth
  - NOT the inside of a ${...} expression (that renders a VALUE, not the identifier's spelling)
  - NOT // or /* */ comments
  - NOT regex literals, which are code and can contain anything

Each span is returned as (start, end) into the ORIGINAL text, so a caller can rewrite in place
without re-finding anything.

RE-SCRAPE COMMAND: python scripts/js_prose.py   (runs its own self-test)
"""
import re

_ID_CHAR = re.compile(r"[A-Za-z0-9_$)\]]")


def prose_spans(js):
    """Yield (start, end) spans of literal prose in `js`. Nesting-aware."""
    spans = []
    i, n = 0, len(js)
    # stack of open contexts: "tpl" for a template literal, "expr" for a ${...} inside one
    stack = []
    prev_significant = ""

    while i < n:
        c = js[i]

        # ---- comments -------------------------------------------------------------------
        if c == "/" and i + 1 < n and not stack[-1:] == ["tpl"]:
            if js[i + 1] == "/":
                j = js.find("\n", i)
                i = n if j < 0 else j
                continue
            if js[i + 1] == "*":
                j = js.find("*/", i + 2)
                i = n if j < 0 else j + 2
                continue
            # a regex literal starts where an operand cannot: after an operator or a keyword
            if not _ID_CHAR.match(prev_significant or " "):
                j, esc, cls = i + 1, False, False
                while j < n:
                    d = js[j]
                    if esc:
                        esc = False
                    elif d == "\\":
                        esc = True
                    elif d == "[":
                        cls = True
                    elif d == "]":
                        cls = False
                    elif d == "/" and not cls:
                        break
                    elif d == "\n":
                        j = i          # not a regex after all
                        break
                    j += 1
                if j > i:
                    i = j + 1
                    prev_significant = "/"
                    continue

        # ---- plain strings --------------------------------------------------------------
        if c in "'\"":
            q, j, esc = c, i + 1, False
            while j < n:
                d = js[j]
                if esc:
                    esc = False
                elif d == "\\":
                    esc = True
                elif d == q:
                    break
                elif d == "\n":
                    break
                j += 1
            spans.append((i + 1, j))
            i = j + 1
            prev_significant = "'"
            continue

        # ---- template literals ----------------------------------------------------------
        if c == "`":
            if stack[-1:] == ["tpl"]:
                stack.pop()                       # closing this template
                i += 1
                prev_significant = "`"
                continue
            stack.append("tpl")
            i += 1
            start = i
            # walk the literal part until ${ or the closing backtick
            while i < n:
                if js[i] == "\\":
                    i += 2
                    continue
                if js[i] == "`":
                    break
                if js[i] == "$" and i + 1 < n and js[i + 1] == "{":
                    break
                i += 1
            spans.append((start, i))
            continue

        if stack[-1:] == ["tpl"] and c == "$" and i + 1 < n and js[i + 1] == "{":
            stack.append("expr")
            i += 2
            continue

        if stack[-1:] == ["expr"] and c == "}":
            stack.pop()                            # back inside the template literal
            i += 1
            start = i
            while i < n:
                if js[i] == "\\":
                    i += 2
                    continue
                if js[i] == "`":
                    break
                if js[i] == "$" and i + 1 < n and js[i + 1] == "{":
                    break
                i += 1
            spans.append((start, i))
            continue

        if stack[-1:] == ["expr"] and c == "{":
            stack.append("expr")                   # an object literal inside the expression
            i += 1
            continue

        if not c.isspace():
            prev_significant = c
        i += 1

    return [(a, b) for a, b in spans if b > a]


def prose_text(js):
    """All the prose, joined - for searching."""
    return "\n".join(js[a:b] for a, b in prose_spans(js))


def rewrite_prose(js, fn):
    """Apply `fn(text) -> (text, n)` to every prose span. Returns (new_js, total_n)."""
    spans = prose_spans(js)
    out, last, total = [], 0, 0
    for a, b in spans:
        out.append(js[last:a])
        new, k = fn(js[a:b])
        total += k
        out.append(new)
        last = b
    out.append(js[last:])
    return "".join(out), total


# --------------------------------------------------------------------------------------------
# SELF-TESTS. The nested case is the whole reason this module exists, so it is first.
# --------------------------------------------------------------------------------------------
_T = prose_text
assert "a data centre" in _T("x = `<div>${a ? `<b>a data centre</b>` : ''}</div>`;"), \
    "NESTED TEMPLATE - the case both regex versions missed"
assert "a data centre" in _T("x = `a data centre needs power`;")
assert "a data centre" in _T('x = "a data centre";')
assert "centre" not in _T("// a data centre here"), "line comment"
assert "centre" not in _T("/* a data centre here */"), "block comment"
assert "colour" not in _T('{ colour: "#16a34a" }'), "object key is code"
assert "metres" not in _T("const metres = 5;"), "variable name is code"
assert "metres" not in _T("x = `about ${metres} m`;"), "interpolated identifier is code"
assert "circle-color" in _T('p["circle-color"] = "#fff";'), "a quoted property IS a literal"
assert _T("x = `a${b}c`;").replace("\n", "") == "ac", "literal parts either side of an interpolation"

if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("js_prose self-tests pass, including the nested-template case")
