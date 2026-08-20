"""G129 guard: passesGates() must stay in step with the GATE half of passes().

⛔ WHY THIS EXISTS. G129 splits every screener filter into a HARD GATE (the site is not a site) and
a PREFERENCE (the site exists, it fits this search less well). Near-miss recovery relaxes
preferences and NEVER relaxes a gate - which only holds while `passesGates()` actually contains
every gate that `passes()` enforces.

The failure mode is silent and bad in one specific direction: add a gate to `passes()`, forget
`passesGates()`, and the near-miss path stops enforcing it. A parcel in a floodway then reappears
in the results wearing a NEAR MISS badge, which is precisely the confusion G129 was filed to end.

⚠ The reverse drift matters too, though less: a control classified in FILTER_MODE but tested in
neither function is a badge promising a behaviour nothing implements.

This is a TEXT check, not an execution one - the page is JavaScript and this is Python. It reads
the three lists out of screener.html and compares them, which is enough to catch the drift that
actually happens: someone edits one function and not the other.

RE-SCRAPE COMMAND: python scripts/audit_g129_gates.py
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
PAGE = os.path.join(REPO, "screener.html")

CTRL_RE = re.compile(r"\$\(\"(s-[\w-]+)\"\)")
MODE_RE = re.compile(r"\"(s-[\w-]+)\":\s*\[\"(gate|pref)\"")

assert CTRL_RE.findall('if ($("s-noflood").checked)') == ["s-noflood"], "CTRL_RE self-test"
assert MODE_RE.findall('  "s-acres":    ["pref", "x"],') == [("s-acres", "pref")], \
    "MODE_RE self-test"


def body_of(blob, name):
    """The source text of one top-level function, by brace balance."""
    i = blob.index(f"function {name}(")
    j = blob.index("{", i)
    depth, k = 1, j + 1
    while depth and k < len(blob):
        if blob[k] == "{":
            depth += 1
        elif blob[k] == "}":
            depth -= 1
        k += 1
    return blob[j:k]


blob = io.open(PAGE, encoding="utf-8").read()
modes = dict(MODE_RE.findall(blob))
gates_declared = {k for k, v in modes.items() if v == "gate"}
prefs_declared = {k for k, v in modes.items() if v == "pref"}

passes_src = body_of(blob, "passes")
gates_src = body_of(blob, "passesGates")
prefmiss_src = body_of(blob, "preferenceMisses")

in_passes = set(CTRL_RE.findall(passes_src))
in_gates = set(CTRL_RE.findall(gates_src))
in_prefmiss = set(re.findall(r"\"(s-[\w-]+)\"", prefmiss_src))

print("=" * 92)
print("G129 - GATE / PREFERENCE CONSISTENCY")
print("=" * 92)
print(f"  declared: {len(gates_declared)} gates, {len(prefs_declared)} preferences")
print(f"  passes() references {len(in_passes)} controls, passesGates() {len(in_gates)}")

fail = []

missing = sorted((gates_declared & in_passes) - in_gates)
if missing:
    fail.append(f"{len(missing)} declared GATE(s) enforced by passes() but NOT by passesGates(): "
                f"{', '.join(missing)}")
    print("\n  ⛔ A GATE THE NEAR-MISS PATH DOES NOT ENFORCE. A site failing it can reappear")
    print("     wearing a NEAR MISS badge, which is the exact confusion G129 exists to end:")
    for m in missing:
        print(f"       {m}")

leaked = sorted(in_gates - gates_declared - {"s-milmi", "s-evwindow"})
if leaked:
    fail.append(f"{len(leaked)} control(s) enforced in passesGates() but not declared a gate: "
                f"{', '.join(leaked)}")
    print("\n  ⚠ ENFORCED AS A GATE BUT NOT DECLARED ONE - the badge and the behaviour disagree:")
    for m in leaked:
        print(f"       {m}")

unimplemented = sorted(prefs_declared - in_prefmiss - in_passes)
if unimplemented:
    fail.append(f"{len(unimplemented)} declared PREFERENCE(s) tested nowhere: "
                f"{', '.join(unimplemented)}")
    print("\n  ⚠ DECLARED A PREFERENCE BUT TESTED NOWHERE - a badge promising a behaviour that")
    print("    nothing implements:")
    for m in unimplemented:
        print(f"       {m}")

no_badge = sorted(in_passes - set(modes) - {
    "s-use", "s-dir", "s-density", "s-since", "s-sirecent", "s-keepundated", "s-si",
    "s-ci", "s-ag", "s-vac", "s-oth", "s-lineon", "s-nomil", "s-milmi", "s-nosua",
    "s-notribal", "s-binding", "s-evwindow", "s-nearmiss"})
if no_badge:
    print(f"\n  note: {len(no_badge)} control(s) in passes() carry no mode badge "
          f"({', '.join(no_badge)})")

print()
if fail:
    for f in fail:
        print(f"  FAIL  {f}")
    print(f"\n{len(fail)} G129 consistency failure(s)")
    print("=" * 92)
    sys.exit(1)
print("  passesGates() enforces every declared gate; no gate is relaxed by the near-miss path")
print("=" * 92)
