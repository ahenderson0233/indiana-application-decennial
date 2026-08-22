"""G152: DO WE HOLD EVERY COLUMN OF EVERY UPSTREAM SI SOURCE, INDIANA-WIDE?

Operator, 2026-08-21: *"we have 31 SI signals, and I guarantee that they live in more than eight
sources"*, and then: *"Even if a source scrapes everything but one column, we still want to
rescrape it for everything because that one field may contain something materially important."*

⛔ THE ANSWER BEFORE THIS AUDIT EXISTED WAS "YES, 8 SOURCES, 0 GAPS", AND IT WAS WRONG.
`audit_si_column_capture.py` compares OUR CLIP against THE PUBLISHER for the eight sources we
scrape directly, and it passes. That is true and it is not the question. The generic corpus
`in_si_signals` draws on 19 upstream `source_id`s, and its parent `energy.si_signals` is
**97,240,585 rows normalised to 13 columns**. Our clip of the reduction is complete — 13 of 13 —
so the column audit passed ON A REDUCTION.

⭐ THIS AUDIT ASKS THE OTHER QUESTION: for each of the 19, how wide is the real parent, how much of
it do we hold, and how many Indiana rows are we leaving upstream?

⚠ AND IT CHECKS THE THING THAT COLUMN COUNTING CANNOT SEE. Two clips were already FULL WIDTH and
still wrong, because they were keyed on the wrong column:
  · in_sba_foia_loans on `cdc_state`, the LENDER's office — 5,135 rows against 39,889.
  · in_ustp_ch7_tfr on `ch7_state_tax_paid`, a DOLLAR column — 33 rows, none of them Indiana.
So this audit compares HELD against the parent's Indiana count, not just the schemas.

RE-SCRAPE COMMAND: python scripts/audit_si_upstream_width.py
⛔ READ-ONLY. Writes nothing.
"""
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.cloud import bigquery

from si_upstream_sources import REPAIRS, SOURCES, YEAR_GAPS

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
client = bigquery.Client(project="energy-platfrom")

fails = []


def cols_of(ds, t):
    try:
        return [f.name for f in client.get_table(f"{ds}.{t}").schema]
    except Exception:
        return None


print("=" * 104)
print("G152 - THE 19 UPSTREAM SI SOURCES, AT FULL WIDTH")
print("=" * 104)
print("⛔ energy.si_signals is 97,240,585 rows NORMALISED TO 13 COLUMNS. Everything below is what "
      "those\n   13 columns discard, and whether we now hold it.\n")
print(f"{'target':32} {'parent':34} {'cols':>9} {'rows':>10}  verdict")
print("-" * 104)

plan = ([(t, p, pr, "new") for _, p, pr, t, _ in SOURCES]
        + [(t, p, pr, "repair") for t, p, pr, _ in REPAIRS]
        + [(t, p, pr, "yeargap") for t, p, pr, _ in YEAR_GAPS])

held_total = 0
for target, parent, pred, kind in plan:
    pc, oc = cols_of(EN, parent), cols_of(DS, target)
    if pc is None:
        fails.append(f"{parent}: parent table is gone from energy")
        print(f"{target:32} {parent:34} {'—':>9} {'—':>10}  ⛔ PARENT MISSING")
        continue
    if oc is None:
        fails.append(f"{target}: not built - run scripts/build_si_upstream_wide.py")
        print(f"{target:32} {parent:34} {'—':>9} {'—':>10}  ⛔ NOT BUILT")
        continue
    avail = list(client.query(
        f"SELECT COUNT(*) n FROM `{EN}.{parent}` WHERE {pred}").result())[0]["n"]
    ours = client.get_table(f"{DS}.{target}").num_rows
    held_total += ours
    missing = [c for c in pc if c not in oc]
    if missing:
        fails.append(f"{target}: narrower than {parent} - missing {missing[:6]}")
        v = f"⛔ NARROW, missing {len(missing)}"
    elif ours != avail:
        # ⛔ the sba/ustp shape: full width, wrong rows.
        fails.append(f"{target}: holds {ours:,} of {avail:,} Indiana rows in {parent}")
        v = f"⛔ SHORT by {avail - ours:,}"
    else:
        v = "full width, all Indiana rows"
    print(f"{target:32} {parent:34} {len(oc):>4}/{len(pc):<4} {ours:>10,}  {v}")

# ================================================================================================
# ⛔ IS THE PARENT ITSELF COMPLETE? THE QUESTION THIS AUDIT COULD NOT SEE UNTIL 2026-08-22.
# Everything above compares OUR CLIP against its `energy` PARENT. Both can be perfectly consistent
# while the PARENT is a partial load of its own publisher — and then we hold 100% of 68%.
# Operator, 2026-08-22: *"have they all been rescraped for fresh data, and do we actually hold ALL
# columns for each table?"* This is the half of that question nothing was answering.
# ⭐ `energy.registry_sources` records the platform session's own load status per object, so the
# answer is already written down; nobody was reading it.
# ⚠ REPORTS, DOES NOT FAIL. `energy` is READ-ONLY and its loaders belong to the platform session,
# so a PARTIAL parent is not something this workstream can fix — but it IS something we must know,
# because a signal built on it rests on a fraction of the source.
# ================================================================================================
print("\n" + "=" * 104)
print("IS EACH PARENT ITSELF FULLY LOADED? (read from energy.registry_sources)")
print("=" * 104)
parents = sorted({p for _, p, _, _ in plan})
stat = list(client.query(f"""
WITH latest AS (
  SELECT o AS parent, status,
         ROW_NUMBER() OVER (PARTITION BY o ORDER BY last_validated_at DESC) rn
  FROM `{EN}.registry_sources`, UNNEST(object_names) o
  WHERE o IN UNNEST(@p))
SELECT parent, status FROM latest WHERE rn = 1 ORDER BY parent""",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ArrayQueryParameter("p", "STRING", parents)])).result())
partial = [(r.parent, (r.status or "")[:110]) for r in stat
           if (r.status or "").upper().startswith("PARTIAL")]
seen = {r.parent for r in stat}
print(f"  {len(stat)} of {len(parents)} parent(s) carry a load status in energy.registry_sources")
for miss in sorted(set(parents) - seen):
    print(f"  ⚠ {miss}: no status recorded upstream - completeness unknown")
if partial:
    print(f"  ⛔ {len(partial)} PARENT(S) ARE A PARTIAL LOAD OF THEIR OWN PUBLISHER:")
    for name, s in partial:
        print(f"     {name}: {s}")
    print("  ⚠ Our clip of these is complete; the PARENT is not. Any signal derived from them")
    print("     rests on a fraction of the source. Re-clip when the platform session finishes.")
else:
    print("  ⭐ every parent with a recorded status is fully loaded")

# ================================================================================================
# ⭐ THE ADDRESS NORMALISER — ONE DEFINITION, 2026-08-22b.
#
# ⛔ WHAT THIS CHECK USED TO BE, AND WHY IT CHANGED. build_warn_placement.py and
# build_si_cmbs_signals.py each carried their own copy of SUFFIXES/DIRECTIONALS, and this block
# asserted the two copies were character-identical. That is **a guard on a duplicate, not a fix for
# one** — §2.15c, the defect this project has hit eight times. When G156 needed a THIRD caller
# (NFIRS and SBA placement) the guard would have had to police three copies.
#
# ⭐ The lists now live once, in `scripts/si_address_norm.py`, and every placement builder imports
# them. So the invariant worth asserting is no longer "do the copies match" — it is **"is there
# still exactly one definition, and does every placement builder import it rather than re-declare
# it".** A re-declaration anywhere is the drift starting again.
# ================================================================================================
print("\n" + "=" * 104)
print("THE ADDRESS NORMALISER - one definition, imported by every placement builder")
print("=" * 104)

CANON = "scripts/si_address_norm.py"
PLACERS = ["scripts/build_warn_placement.py", "scripts/build_si_cmbs_signals.py",
           "scripts/build_si_addr_placement.py"]


def _text(path):
    p = os.path.join(REPO, path)
    return io.open(p, encoding="utf-8").read() if os.path.exists(p) else None


canon = _text(CANON)
if canon is None:
    fails.append(f"{CANON}: the one normaliser is GONE - every placement builder is now broken")
    print(f"  ⛔ {CANON} does not exist")
else:
    for name in ("SUFFIXES", "DIRECTIONALS"):
        if not re.search(name + r"\s*=\s*\[", canon):
            fails.append(f"{CANON}: {name} is not defined in the canonical module")
            print(f"  ⛔ {name}: missing from {CANON}")
        else:
            print(f"  [PASS] {name}: defined once, in {CANON}")

# ⚠ the real check: nobody re-declares it. A second definition is the drift restarting.
redeclared = []
for path in PLACERS:
    t = _text(path)
    if t is None:
        continue                      # a builder that does not exist yet is not a failure
    if re.search(r"^SUFFIXES\s*=\s*\[", t, re.M) or re.search(r"^def naddr\(", t, re.M):
        redeclared.append(path)
    elif "si_address_norm" not in t:
        fails.append(f"{path}: places addresses but does not import the one normaliser")
        print(f"  ⛔ {os.path.basename(path)}: neither imports nor defines the normaliser")
    else:
        print(f"  [PASS] {os.path.basename(path)}: imports it")
if redeclared:
    fails.append("normaliser RE-DECLARED in: " + ", ".join(redeclared)
                 + " - two copies will drift and the loser is invisible")
    for p in redeclared:
        print(f"  ⛔ {os.path.basename(p)}: re-declares SUFFIXES/naddr instead of importing")

# ================================================================================================
print("\n" + "=" * 104)
print("WHAT THE WIDER CLIP BOUGHT - signals that could not exist under a 13-column reduction")
print("=" * 104)
for r in client.query(f"""
  SELECT signal, corpus_rows, parcels_reached, parcels_admitted
  FROM `{DS}.in_si_signal_coverage`
  WHERE signal IN ('D28_cmbs_loan_distress','D29_anchor_tenant_exit')
  ORDER BY signal"""):
    print(f"  {r.signal:26} held {r.corpus_rows:>6,}  reached {r.parcels_reached:>4,}  "
          f"admitted {r.parcels_admitted:>4,}")
for r in client.query(f"""
  SELECT signal, COUNT(DISTINCT parcel_key) parcels, COUNT(*) events
  FROM `{DS}.in_si_intent_signals` WHERE signal = 'I3_land_bank' GROUP BY 1"""):
    print(f"  {r.signal:26} {r.parcels:,} parcels, {r.events:,} events "
          f"(G133's third leg - two registers we already held)")

print("\n" + "=" * 104)
print(f"{len(plan)} upstream clip(s) audited · {held_total:,} Indiana rows held at full width")
if fails:
    print(f"\n{len(fails)} FAILURE(S):")
    for f in fails:
        print(f"  ⛔ {f}")
    print("\n⚠ Fix with: python scripts/build_si_upstream_wide.py")
    sys.exit(1)
print("\n⭐ Every upstream source is clipped Indiana-wide at FULL WIDTH. No column is left behind.")
print("=" * 104)
