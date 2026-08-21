"""Catch what audit_handoff_docs.py structurally cannot: documents contradicting each other.

⛔ WHY A SECOND DOCUMENT AUDIT. `audit_handoff_docs.py` re-measures every FIGURE and checks it
appears somewhere in the set. That is necessary and it is not sufficient: on 2026-08-20c a prompt
passed that audit while its header said "16 OPEN" and its body, two lines down, said "OPEN reads
15". Both numbers appeared; neither contradicted the warehouse; the document contradicted ITSELF.
Three such contradictions shipped in one file.

This audit asks a different question: **do the ledger, the handoff and the prompt tell the same
story about the same G-row?** It is deliberately narrow - status words and row lists, not prose -
because a wide document audit that cries wolf gets ignored, and this project has retired one of
those already.

WHAT IT CHECKS
  1. Every G-row named as CLOSED/DONE in the handoff or the prompt is actually DONE in the ledger.
  2. Every G-row the ledger calls PARTIAL or OPEN is never described as done in either document.
  3. A "N rows closed" claim matches the length of the list it is next to.
  4. The current handoff is the newest one, and no OTHER handoff claims to be current.
  5. The prompt names a first task, and that task is not a row the ledger has closed.

RE-SCRAPE COMMAND: python scripts/audit_handoff_consistency.py
"""
import glob
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(REPO, "docs", "BACKLOG.md")

HANDOFFS = sorted(glob.glob(os.path.join(REPO, "docs", "HANDOFF_*.md")))
CURRENT = HANDOFFS[-1] if HANDOFFS else None
PROMPT = os.path.join(REPO, "docs", "NEXT_SESSION_PROMPT.md")

ROW_RE = re.compile(r"^\|\s*\*\*(G\d+)\*\*\s*\|")
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
         "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
         "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
         "nineteen": 19, "twenty": 20}
CLOSED_RE = re.compile(r"\b(" + "|".join(WORDS) + r")\s+rows?\s+closed", re.I)
GLIST_RE = re.compile(r"G\d+")

assert CLOSED_RE.search("Eight rows closed (G1, G2)"), "CLOSED_RE self-test"
assert ROW_RE.match("| **G130** | x | y | z |"), "ROW_RE self-test"

fail, note = [], []


def status_of(cells):
    """The ledger's status for one row.

    ⛔ KEY ON THE EMOJI MARKER, NOT THE WORD, and this audit got it wrong on its first run: it
    matched status WORDS and reported 85 DONE / 1 PARTIAL / 13 OPEN against the authoritative
    audit_backlog_state.py's 100 / 17 / 8, leaving 29 rows unclassified. A status cell is prose
    with a marker in front of it - the word "DONE" can appear anywhere in that prose, and a 🟡 row
    whose text mentions being done is still PARTIAL. This mirrors classify() in
    audit_backlog_state.py deliberately: two parsers of one column must agree or neither is
    trustworthy.
    """
    s = cells[2] if len(cells) > 2 else ""
    if "~~" in s or "SUPERSEDED" in s.upper():
        return "SUPERSEDED"
    for marker, kind in (("✅", "DONE"), ("🟢", "DONE"), ("📌", "STANDING"),
                         ("🟡", "PARTIAL"), ("🔴", "OPEN")):
        if marker in s:
            return kind
    u = s.upper()
    if "DONE" in u or "FIXED" in u or "COMPLETE" in u:
        return "DONE"
    return "?"


# ⛔ PARSE THE LEDGER EXACTLY THE WAY audit_backlog_state.py DOES, and this took two corrections.
#   (a) The status cell is `([^|]*)` - it STOPS at the next pipe. Splitting on " | " instead swept
#       up text from further along the row, and one row's prose containing the word SUPERSEDED
#       then mis-classified it.
#   (b) A G-number can appear TWICE - a superseded row and the live row that replaced it (G11 and
#       G18 both do). The live one is the first entry that does not classify as SUPERSEDED; a
#       plain dict keyed on the number silently keeps whichever came last.
# Between them these two produced 99 DONE / 3 SUPERSEDED against the trusted 100 / 2. Two parsers
# of one column disagreeing by one row is exactly the defect this audit exists to catch, so it
# had to be caught here first.
CELL_RE = re.compile(r"\|\s*\*\*(G\d+)\*\*\s*\|([^|]*)\|([^|]*)\|")
_entries = {}
for ln in io.open(BACKLOG, encoding="utf-8"):
    m = CELL_RE.match(ln)
    if m:
        _entries.setdefault(m.group(1), []).append(m.group(3).strip())
ledger = {}
for g, states in _entries.items():
    live = [s for s in states if status_of([None, None, s]) != "SUPERSEDED"]
    ledger[g] = status_of([None, None, (live or states)[0]])

print("=" * 92)
print("HANDOFF / PROMPT / BACKLOG CONSISTENCY")
print("=" * 92)
print(f"  ledger: {len(ledger)} G-rows  "
      f"({sum(1 for v in ledger.values() if v == 'DONE')} DONE, "
      f"{sum(1 for v in ledger.values() if v == 'PARTIAL')} PARTIAL, "
      f"{sum(1 for v in ledger.values() if v == 'OPEN')} OPEN)")
print(f"  current handoff: {os.path.basename(CURRENT) if CURRENT else 'NONE'}")

# ---- 1 + 2. rows the documents call closed must be closed in the ledger ------------------------
for path in [p for p in (CURRENT, PROMPT) if p]:
    txt = io.open(path, encoding="utf-8").read()
    name = os.path.basename(path)
    for m in CLOSED_RE.finditer(txt):
        # ⚠ STOP AT THE END OF THE LIST. The first version read 260 characters past the claim and
        # swept up the G-numbers in the NEXT clause - "…and two advanced with their question
        # answered (G126, G130)" - then reported that "Eight rows closed" named ten rows. The
        # claim owns the parenthesis or dash-clause that follows it, and nothing after.
        tail = txt[m.end():m.end() + 300]
        stop = min([i for i in (tail.find(" and "), tail.find("."), tail.find("\n\n"))
                    if i > 0] or [len(tail)])
        listed = GLIST_RE.findall(tail[:stop])
        claimed = WORDS[m.group(1).lower()]
        if listed and len(listed) != claimed:
            fail.append(f"{name}: says '{m.group(0)}' but names {len(listed)} rows "
                        f"({', '.join(listed)})")
        for g in listed:
            st = ledger.get(g)
            if st and st != "DONE":
                fail.append(f"{name}: lists {g} among rows CLOSED, but the ledger says {st}")
            elif st is None:
                fail.append(f"{name}: lists {g} as closed, but no such row exists in the ledger")

# ---- 3. no document may describe a non-DONE row as finished ------------------------------------
DONE_PHRASE = re.compile(
    r"(G\d+)[^.\n|]{0,80}?\b(is (?:now )?(?:complete|closed|done|finished)|"
    r"has (?:been )?(?:completed|closed|finished))", re.I)
for path in [p for p in (CURRENT, PROMPT) if p]:
    txt = io.open(path, encoding="utf-8").read()
    name = os.path.basename(path)
    for m in DONE_PHRASE.finditer(txt):
        g, st = m.group(1), ledger.get(m.group(1))
        if st and st not in ("DONE", "SUPERSEDED"):
            fail.append(f"{name}: describes {g} as finished (\"{m.group(0)[:60]}…\") "
                        f"but the ledger says {st}")

# ---- 4. exactly one document may claim to be the current handoff -------------------------------
claim = []
for p in HANDOFFS + [os.path.join(REPO, "docs", "SESSION_START.md")]:
    if not os.path.exists(p):
        continue
    t = io.open(p, encoding="utf-8").read()
    for m in re.finditer(r"THE CURRENT ONE", t):
        seg = t[max(0, m.start() - 160):m.start()]
        named = re.findall(r"HANDOFF_[\d\-a-z]+\.md", seg)
        claim.append((os.path.basename(p), named[-1] if named else "(itself)"))
current_base = os.path.basename(CURRENT) if CURRENT else ""
for where, target in claim:
    if target not in ("(itself)", current_base) and where != current_base:
        fail.append(f"{where}: points at {target} as THE CURRENT ONE, but the newest handoff "
                    f"is {current_base}")
    if where != current_base and target == "(itself)" and where.startswith("HANDOFF_"):
        fail.append(f"{where}: a superseded handoff still calls itself THE CURRENT ONE")
note.append(f"{len(claim)} 'THE CURRENT ONE' marker(s): "
            f"{', '.join(f'{w}->{t}' for w, t in claim) or 'none'}")

# ---- 5. the prompt's first task must not already be closed -------------------------------------
if os.path.exists(PROMPT):
    t = io.open(PROMPT, encoding="utf-8").read()
    m = re.search(r"START HERE[^\n]*\n", t)
    if not m:
        fail.append("NEXT_SESSION_PROMPT.md: no 'START HERE' section - the next session has no "
                    "stated first task")
    else:
        head = t[m.start():m.start() + 400]
        gs = GLIST_RE.findall(head)
        for g in gs[:1]:
            st = ledger.get(g)
            if st == "DONE":
                fail.append(f"NEXT_SESSION_PROMPT.md: START HERE leads with {g}, which the ledger "
                            f"has already CLOSED")
            else:
                note.append(f"prompt leads with {g} (ledger: {st}) - correct")

print()
for n in note:
    print(f"  note  {n}")
print()
if fail:
    for f in fail:
        print(f"  FAIL  {f}")
else:
    print("  the ledger, the handoff and the prompt tell the same story")
print()
print(f"{len(fail)} consistency failure(s)")
print("=" * 92)
sys.exit(1 if fail else 0)
