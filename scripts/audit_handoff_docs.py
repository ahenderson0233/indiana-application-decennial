"""Are the handoff, the prompt and the backlog TRUE of the application as it stands?

    python scripts/audit_handoff_docs.py

⭐ WHY THIS EXISTS. This project's own rule is "never quote a count from a document, including this
one" - and the documents are full of counts, because a handoff without numbers is useless. The
resolution is not fewer numbers, it is a script that re-measures them.

It caught two real problems the first time it ran on 2026-08-20:
  * the handoff quoted 190,216 / 73,094 for grid-binds vs land-binds while the live figures were
    190,178 / 73,058 - they had moved when in_screener_candidates was rebuilt after the G84
    demotion, hours after the sentence was written;
  * and it caught them only after ITS OWN CHECK was fixed. The first version asserted that the
    string "190,216" APPEARED in the document, which it did. ⛔ A PRESENCE TEST PASSES ON A STALE
    NUMBER BY CONSTRUCTION - it can only catch a deleted figure, never a wrong one. Compare values.

⚠ It has cried wolf twice, both times on correct prose: once on "the count is 23,795, NOT 24,277",
which is the clearest way to cite a superseded figure. An audit that cries wolf gets ignored, so
the superseded-value cues are deliberately generous.

Run it after editing any of the three documents, and before handing off.
"""

import io, os, re, sys, subprocess
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from google.cloud import bigquery

REPO = (r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California"
        r"\ca-capacity-deploy\indiana-application-decennial")
DS = "energy-platfrom.indiana_app"
c = bigquery.Client(project="energy-platfrom")
DOCS = ["docs/HANDOFF_2026-08-20.md", "docs/NEXT_SESSION_PROMPT.md", "docs/BACKLOG.md"]
text = {d: io.open(os.path.join(REPO, d), encoding="utf-8").read() for d in DOCS}
allt = "\n".join(text.values())

fails, checks = [], 0


def check(label, ok, detail):
    global checks
    checks += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {detail}")
    if not ok:
        fails.append(label)


def one(sql):
    return list(c.query(sql))[0]


print("=" * 92)
print("A. FIGURES QUOTED IN THE DOCUMENTS, RE-MEASURED")
print("=" * 92)

r = one(f"SELECT COUNTIF(has_si_signal) n FROM `{DS}.in_si_sites_flags_v2`")
check("flagged parcels", r.n == 23795 and "23,795" in allt, f"live {r.n:,}, docs say 23,795")

r = one(f"""SELECT COUNTIF(deliverable_wd_mw IS NOT NULL AND deliverable_wd_mw < c.mw_dc) grid,
                   COUNTIF(deliverable_wd_mw IS NOT NULL AND deliverable_wd_mw >= c.mw_dc) land
            FROM `{DS}.in_parcel_line_headroom` h
            JOIN `{DS}.in_screener_candidates` c USING (parcel_source, parcel_key)""")
# ⛔ COMPARE THE VALUE, DO NOT TEST FOR THE STRING. The first version asserted that "190,216"
# APPEARED in the docs -- which it did, while the live figure was 190,178. A presence test passes
# on a stale number by construction; it can only ever catch a DELETED figure, never a wrong one.
check("grid-binds / land-binds", f"{r.grid:,}" in allt and f"{r.land:,}" in allt,
      f"live grid {r.grid:,} land {r.land:,} -- docs must contain both")

r = one(f"""SELECT COUNT(*) n, COUNTIF(ends_resolved=2) both_ FROM `{DS}.in_line_bus_endpoints`""")
check("lines resolved both ends", r.both_ == 1018 and "1,018" in allt,
      f"live {r.both_:,} of {r.n:,}, docs say 1,018")

rungs = {t.table_id: t for t in c.query(f"""
    SELECT table_id FROM `{DS}.__TABLES__`
    WHERE REGEXP_CONTAINS(table_id, r'^in_pjm_qs_c23_(inj|wd)_[0-9]+$')""")}
b = {}
for t in rungs:
    b[t] = one(f"SELECT COUNT(DISTINCT bus_number) n FROM `{DS}.{t}`").n
check("inj_25 short by 29", b.get("in_pjm_qs_c23_inj_25") == 1797,
      f"live {b.get('in_pjm_qs_c23_inj_25'):,} buses; docs say 1,797 of 1,826")
check("wd_50 short", b.get("in_pjm_qs_c23_wd_50") == 1625,
      f"live {b.get('in_pjm_qs_c23_wd_50'):,} buses; docs say 1,625 of 1,826")
complete = sorted(t.replace("in_pjm_qs_c23_", "") for t, n in b.items() if n >= 1826)
check("complete rungs", set(complete) == {"inj_10", "inj_15", "inj_5000", "wd_10", "wd_15",
                                          "wd_25", "wd_5000"}, f"live complete = {complete}")

unreg = [r.table_id for r in c.query(f"""
  SELECT t.table_id FROM `{DS}.__TABLES__` t
  LEFT JOIN (SELECT DISTINCT table_name FROM `{DS}._registry`) g ON g.table_name=t.table_id
  WHERE g.table_name IS NULL AND NOT STARTS_WITH(t.table_id,'_')""")]
check("2 unregistered tables", len(unreg) == 2, f"live {unreg}")

r = one(f"""SELECT COUNT(*) n FROM `{DS}.in_severe_weather_county`""")
check("severe weather counties", r.n == 92, f"live {r.n}")

r = one(f"""SELECT COUNT(DISTINCT parcel_id) p FROM `{DS}.in_si_address_parcel`""")
check("D11/D27 parcels reached", r.p == 131 and "131" in allt, f"live {r.p}, docs say 131")

print()
print("=" * 92)
print("B. BACKLOG STATE VS WHAT THE DOCUMENTS CLAIM")
print("=" * 92)
# ⚠ encoding="utf-8" and errors="replace": the audit prints ⛔/⭐ and the default cp1252 decode
# throws, which killed this section entirely on the first run.
out = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "audit_backlog_state.py")],
                     capture_output=True, text=True, cwd=REPO,
                     encoding="utf-8", errors="replace").stdout or ""
counts = dict(re.findall(r"^\s+(DONE|PARTIAL|OPEN|STANDING|SUPERSEDED)\s+(\d+)", out, re.M))
counts = {k: int(v) for k, v in counts.items()}
print(f"  live: {counts}")
for k, claimed in (("DONE", 80), ("PARTIAL", 21), ("OPEN", 15)):
    check(f"handoff claims {claimed} {k}", counts.get(k) == claimed
          and f"{claimed} {'DONE' if k=='DONE' else k}" in allt.replace("**", ""),
          f"live {counts.get(k)}, docs say {claimed}")
check("0 active duplicates", "ACTIVE DUPLICATES (two live rows for one number): 0" in out,
      "structural check")

print()
print("=" * 92)
print("C. EVERY FILE THE DOCUMENTS REFERENCE")
print("=" * 92)
refs = set()
for d, t in text.items():
    refs |= set(re.findall(r"`((?:scripts|docs|data)/[\w./-]+\.(?:py|md|js|json|gz))`", t))
missing = sorted(r for r in refs if not os.path.exists(os.path.join(REPO, r)))
check("no dangling file reference", not missing, f"{len(refs)} referenced, missing: {missing}")

print()
print("=" * 92)
print("D. STALE-FIGURE SWEEP — numbers that MOVED this session")
print("=" * 92)
for doc in ("docs/HANDOFF_2026-08-20.md", "docs/NEXT_SESSION_PROMPT.md"):
    t = text[doc]
    # 24,277 is legitimate ONLY where it is described as the OLD value
    bad = [ln.strip()[:100] for ln in t.split("\n")
           if "24,277" in ln and not re.search(r"24,277\s*(?:→|->|\u2192)|was|before|old|moved|\bnot\b", ln, re.I)]
    check(f"{os.path.basename(doc)}: no bare 24,277", not bad, bad or "only as a superseded value")
    bad2 = [ln.strip()[:100] for ln in t.split("\n")
            if re.search(r"\b291 of 309\b|\b235 of 316\b", ln)
            and not re.search(r"→|->|\u2192|was|from", ln)]
    check(f"{os.path.basename(doc)}: no bare old census", not bad2, bad2 or "clean")

print()
print("=" * 92)
print(f"{checks} checks, {len(fails)} FAILED")
if fails:
    for f in fails:
        print(f"  ⛔ {f}")
sys.exit(1 if fails else 0)
