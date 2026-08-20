"""G128(b): put the ANSWER before the WORKPAPER on si, market, grid and community.

Operator, 2026-08-20c: *"it looks like an intern made this."* `docs/COMPARABLE_TOOLS.md` measured
what was underneath that judgement: six of eight pages are ANTHOLOGIES ordered by how the data was
BUILT rather than by the question a reader arrives with. `si.html` opens with *"Why this many and
not more? - the whole funnel, with every loss named"*, which is a build diary, and the section a
reader actually wants - *which owners might sell you land* - is FIFTH.

The real-estate record pattern is the fix: every CoStar property page runs identity -> location ->
size -> tenancy -> financials -> comparables, in that order, every time, so a user learns the
shape once and then navigates by muscle memory. Ours changes shape per page and starts with the
working.

================================================================================================
⛔ WHY THIS IS A PERMUTATION AND NOTHING ELSE
================================================================================================
The previous attempt to move blocks on these pages broke SIX pages with 18 fatal findings, because
a `.sowhat` div carries the `id` its own script writes into. So this tool:

  · moves only the TOP-LEVEL children of the page container. Several cards are NESTED inside a
    two-column `.gridcards` wrapper - si's "By year"/"Severity x class" pair, the ACS/SBA pair,
    community's disaster/drought pairs - and lifting one out would orphan the other.
  · takes each block's PRECEDING gap with it. The comment above si's funnel card documents that
    card; detached, it would end up annotating whatever landed in its place.
  · ⭐ ASSERTS BYTE CONSERVATION. The multiset of block texts before and after must be identical -
    the output is a permutation of the input or the write is refused. Not one character of markup
    is edited here, so an `id`, a handler or a payload key cannot be lost by construction.
  · requires the new order to be a PERMUTATION of every reorderable index, so a block cannot be
    silently dropped by being left out of the list.

⚠ WHAT THIS TOOL DOES NOT DO. It does not decide the order - the orders live in ORDERS below, one
per page, each with the reason written next to it. That is the judgement half of G128(b) and it
should be read and argued with, not buried in code.

RE-SCRAPE COMMAND: python scripts/reorder_page_sections.py [--check]
⚠ IDEMPOTENT: replace_safe. The orders are expressed as the DESIRED final sequence keyed by a
stable title fragment, not by index, so re-running an already-ordered page is a no-op.
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

TAG_RE = re.compile(r"<(/?)([a-zA-Z][\w-]*)([^>]*)>", re.S)
VOID = {"br", "hr", "img", "input", "meta", "link", "source", "col", "area", "base", "wbr"}
STRIP = re.compile(r"<[^>]+>")
H_RE = re.compile(r"<h[1-4]\b[^>]*>(.*?)</h[1-4]\s*>", re.S | re.I)

assert TAG_RE.match("<div class=\"card\">").group(2) == "div", "TAG_RE self-test"
assert not TAG_RE.match("<!-- a comment -->"), "a comment must not parse as a tag"


# ==============================================================================================
# THE ORDERS. Each entry is a title fragment, matched against the block's first heading.
# Anything not named keeps its relative position AFTER the named ones, in its original order -
# so a block added later cannot vanish, it just lands in the tail.
# ==============================================================================================
ORDERS = {
    # ONE QUESTION: which owners might sell, and how strongly do we believe it?
    # ⭐ The ANSWER card was FIFTH and was even tagged data-group="How many, and why" - filed with
    #    the workpaper. Signals first, then what we cannot place, then the funnel that explains
    #    the count, then provenance, then context.
    "si.html": [
        "Which owners might sell you land",          # THE ANSWER
        "Absentee owners",                           # and how to reach them
        "State environmental enforcement",
        "Federal environmental compliance",
        "Structure fires severe enough",
        # NOT LISTED: "Cancelled grid projects" and "Two ways a parcel answer can be
        #   right". Both live inside the <details> accordion - already behind a fold, and
        #   not top-level blocks. Naming them would be an order this tool cannot honour,
        #   and it reported them as unmatched rather than guessing.
        "Signals about an OWNER, not a parcel",      # the limits of the answer
        "Can the parcel host anything",
        "Why this many",                             # THE WORKPAPER starts here
        "Every severity filter we apply",
        "Does an environmental violation really mean",
        "Per-signal coverage",
        "Signal inventory",                          # provenance
        "Highest-vacancy census tracts",             # context, not signal
    ],
    # ONE QUESTION: what will power cost here, and who sells it?
    # ⭐ "What would power cost here?" - the rate quote, the thing the page exists for - was
    #    THIRTEENTH, behind statewide demand, fuel costs and generation mix.
    # ⚠ The rate-engine caveat card follows the quote immediately: it is DISCLOSURE about the
    #    number above it, not an appendix, and separating them would leave the quote unqualified.
    "market.html": [
        "What would power cost here",                # THE ANSWER
        "The rate engine",                           # its disclosure - must stay adjacent
        "What each utility's industrial customers actually paid",
        "Yearly cost proxy",
        "C&amp;I tariffs",
        "What the last five data centers in Indiana actually got",
        "The incentives actually granted at this scale",
        "How reliable is each utility",              # who sells it, and how well
        "FERC EQR filers",
        "Where Indiana's power comes from",          # CONTEXT from here down
        "Indiana statewide demand",
        "Delivered fuel cost at Indiana plants",
        "how much is actually free",
        "Gas OAC",
    ],
    # ONE QUESTION: can a site get power here, and what would interconnection cost?
    # ⭐ Headroom and cost were already near the front; the DRILL-DOWNS were interleaved with them.
    #    A per-upgrade allocation table is a workpaper - useful, and not the first thing.
    "grid.html": [
        "LOAD headroom per bus",                             # THE ANSWER: headroom per bus
        "Buses ",
        "What an interconnection upgrade actually costs",
        "Which branches actually bind",              # what would stop you
        "Where the planned work actually is",        # what might help you
        "Future capacity",
        "Interconnection queue",                     # who is ahead of you
        "Indiana generating fleet",                  # context
        "RTEP upgrade drill-down",                   # WORKPAPER from here down
        "MISO study-cycle detail",
        "RTEP upgrades",
    ],
    # ONE QUESTION: will this county let me build?
    # ⭐ The RECEIPTS BROWSER opened the page. It is the evidence drawer - provenance - and it now
    #    sits last, behind the answer it supports.
    # ⚠ #leg-detail is the legislature card's detail panel and is pinned immediately after it.
    "community.html": [
        "County posture",                            # THE ANSWER: go / think hard / no-go
        "County data-center actions",
        "Local data-center ordinances",
        "Indiana legislature",
        "__ID__leg-detail",                          # its detail panel - must stay adjacent
        "Permitted water dischargers",               # site-level context
        "Drought, week by week",
        "Federal disaster declarations",
        "Court activity by county",
        "Receipts browser",                          # PROVENANCE, last
    ],
}


def main_span(blob):
    m = re.search(r"<main\b[^>]*>", blob, re.I)
    if m:
        depth = 1
        for t in TAG_RE.finditer(blob, m.end()):
            if t.group(2).lower() != "main":
                continue
            depth += -1 if t.group(1) else 1
            if depth == 0:
                return m.end(), t.start()
        return m.end(), len(blob)
    b = re.search(r"<body\b[^>]*>", blob, re.I)
    e = re.search(r"</body\s*>", blob, re.I)
    return (b.end() if b else 0), (e.start() if e else len(blob))


def top_blocks(blob, a, b):
    out, i = [], a
    while i < b:
        t = TAG_RE.search(blob, i)
        if not t or t.start() >= b:
            break
        if t.group(1):
            i = t.end()
            continue
        tag, attrs = t.group(2).lower(), (t.group(3) or "")
        if tag in VOID or attrs.rstrip().endswith("/"):
            out.append((t.start(), t.end(), tag, attrs))
            i = t.end()
            continue
        depth, j = 1, b
        for n in TAG_RE.finditer(blob, t.end()):
            if n.start() >= b:
                break
            if n.group(2).lower() != tag or (n.group(3) or "").rstrip().endswith("/"):
                continue
            depth += -1 if n.group(1) else 1
            if depth == 0:
                j = n.end()
                break
        out.append((t.start(), j, tag, attrs))
        i = j
    return out


def container(blob):
    a, b = main_span(blob)
    for s, e, tag, attrs in top_blocks(blob, a, b):
        cls = (re.search(r'class="([^"]*)"', attrs) or [None, ""])[1]
        if cls and re.search(r"\bpage\b|\bwrap\b", cls):
            return blob.index(">", s) + 1, e
    return a, b


def label(blob, s, e, attrs):
    """A block's identity: its first heading, or __ID__<id> when it has no heading."""
    seg = blob[s:e]
    h = H_RE.search(seg)
    if h:
        txt = re.sub(r"\s+", " ", STRIP.sub("", h.group(1))).strip()
        if txt:
            return txt
        # ⚠ AN EMPTY HEADING IS NOT A LABEL. community's #leg-detail carries
        # <h2 id="leg-detail-title"></h2> and is filled at runtime, so matching on heading text
        # returned "" and the panel was about to be stranded in the tail, away from the
        # legislature card whose rows open it.
    i = re.search(r'\bid="([\w-]+)"', attrs)
    return f"__ID__{i.group(1)}" if i else ""


def reorder(page, wanted):
    path = os.path.join(REPO, page)
    blob = io.open(path, encoding="utf-8").read()
    a, b = container(blob)
    blocks = top_blocks(blob, a, b)

    # each block's EXTENT includes the gap before it, so its comment travels with it
    extents, prev = [], a
    for s, e, tag, attrs in blocks:
        extents.append((prev, e, tag, attrs, s))
        prev = e
    tail = blob[prev:b]

    # ⭐ THE FIXED HEADER RUN: every block before the first TITLED section. That is the h1, the
    # standfirst, and - the case that nearly went wrong - a summary band of big-stat cards with no
    # heading at all. si.html opens with four bigstat cards (parcels flagged, of those dated,
    # observations held, candidate parcels). Labelling by heading text made them "" and they were
    # headed for the TAIL, which would have buried the page's own headline figures under thirteen
    # sections - a reordering tool making the page worse in exactly the way it exists to fix.
    def titled(k):
        s_, xe_ = extents[k][4], extents[k][1]
        h = H_RE.search(blob[s_:xe_])
        return bool(h and re.sub(r"\s+", " ", STRIP.sub("", h.group(1))).strip())

    # ⚠ The page's own <h1> IS titled, so a bare "stop at the first titled block" rule stopped at
    # index 0 and fixed NOTHING - every page then offered to move its own title into the tail.
    # The run ends at the first titled SECTION: a container element carrying a heading.
    fixed = []
    for k in range(len(extents)):
        tag = extents[k][2]
        cls = (re.search(r'class="([^"]*)"', extents[k][3]) or [None, ""])[1] or ""
        if tag in ("h1", "h2", "h3", "p") or re.search(r"\bsub\b", cls) or not titled(k):
            fixed.append(k)
            continue
        break
    movable = [k for k in range(len(extents)) if k not in fixed]

    labels = {k: label(blob, extents[k][4], extents[k][1], extents[k][3]) for k in movable}

    def match(frag):
        for k in movable:
            if frag.lower() in labels[k].lower():
                return k
        return None

    order, used, missing = [], set(), []
    for frag in wanted:
        k = match(frag)
        if k is None or k in used:
            if k is None:
                missing.append(frag)
            continue
        order.append(k)
        used.add(k)
    rest = [k for k in movable if k not in used]
    new_order = fixed + order + rest

    # ⭐ BYTE CONSERVATION. A permutation or nothing.
    before = sorted(blob[xs:xe] for xs, xe, _, _, _ in extents)
    after = sorted(blob[extents[k][0]:extents[k][1]] for k in new_order)
    assert before == after, f"{page}: NOT A PERMUTATION - refusing to write"
    assert len(new_order) == len(extents), f"{page}: block count changed"

    out = blob[:a] + "".join(blob[extents[k][0]:extents[k][1]] for k in new_order) + tail + blob[b:]
    # a second conservation check on the whole file: same length, same tag census
    assert len(out) == len(blob), f"{page}: file length changed ({len(blob)} -> {len(out)})"
    for t in ("<div", "</div>", "<table", "</table>", "<script", "</script>", 'class="card"'):
        assert out.count(t) == blob.count(t), f"{page}: {t} count changed"

    moved = sum(1 for i, k in enumerate(new_order) if k != i)
    return path, blob, out, labels, order, rest, missing, moved


print("G128(b) - ANSWER BEFORE WORKPAPER")
total_moved = 0
for page, wanted in ORDERS.items():
    path, blob, out, labels, order, rest, missing, moved = reorder(page, wanted)
    total_moved += moved
    print(f"\n{'=' * 96}\n{page}: {moved} block(s) change position\n{'=' * 96}")
    for pos, k in enumerate(order, 1):
        print(f"  {pos:>2}. {labels[k][:82]}")
    for k in rest:
        print(f"   · (unnamed, kept in the tail) {labels[k][:66]}")
    if missing:
        print(f"  ⚠ {len(missing)} title fragment(s) matched NOTHING - the page changed under the "
              f"order and they were skipped rather than guessed at:")
        for f in missing:
            print(f"      {f}")
    if not CHECK and out != blob:
        io.open(path, "w", encoding="utf-8", newline="").write(out)

print(f"\n{total_moved} block(s) repositioned across {len(ORDERS)} pages"
      f"{'  (--check: nothing written)' if CHECK else ''}")
print("\n⚠ NEXT, and none of these is optional:")
print("   python scripts/stamp_assets.py && python scripts/audit_frontend.py")
print("   python scripts/audit_page_controls.py && python scripts/audit_js_duplicates.py")
print("   then open every page - a permutation cannot break a reference, but it CAN")
print("   reveal that something depended on order")
