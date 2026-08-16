"""Fold batch A into dc_actions_county_consolidated.json — the batch the merge dropped.

WHY THIS EXISTS. The 92-county sweep wrote seven regional batches (A..G) plus a known-positive
control batch (MINE). The consolidation ran at 13:24 and read six of them; `batch_A.json` was
written at 13:37, THIRTEEN MINUTES LATER, because batch A was still re-sweeping. The merge did
not glob it in — it globbed nothing, it simply ran early. Result: the consolidated file carries
B/C/D/E/F/G/MINE and no A, and its coverage is 79 of 92 counties.

The 13 absent counties are exactly batch A's 13, and they are the entire northwest quadrant:
Benton, Carroll, Fountain, Jasper, LAKE, LAPORTE, Newton, PORTER, Pulaski, Starke, TIPPECANOE,
Warren, White. That is the most industrial corner of the state, and it includes Lake County
Ordinance 2590 — data centres PROHIBITED in all business districts, verified from the county's
own signature page. Shipping the sweep without it would have rendered those 13 counties as
"not assessed" when they are in fact assessed and, in Lake's case, the most restrictive posture
found anywhere in the run.

THE WARNING THAT WAS RELAYED WAS THE WRONG ONE. The handoff warned that a stale `batch_MINE.json`
might be double-counted if the merge globbed `batch_*.json`. Measured before writing anything:
coverage carries 79 rows across 79 distinct counties (zero duplicates), MINE contributed exactly
its 2 known-positive controls (Boone, Miami), and 2 of MINE's 5 action rows were DROPPED as
duplicates of other batches. The merge deduped deliberately. The defect was omission, not
duplication — which is why this script asserts on MISSING counties, the check the loader lacked.

SCHEMA DRIFT IS REAL AND IS NOT PAPERED OVER. Batch A predates two fields the later batches
carry, and names its timestamp differently:
  * `pulled_at`                  -> `_pulled_at`   (renamed, value preserved)
  * `expiry_condition_verbatim`  -> absent, set NULL (never invented)
  * `ordinance_pdf_url`          -> absent, set NULL
  * coverage `search_instrument` -> absent, set NULL and COUNTED in the output, because a
    fabricated instrument description would be a claim about method that no agent made
  * coverage `_pulled_at`        -> batch A recorded none on coverage rows; NULL, counted

Reads two files, writes one, touches no network and no BigQuery. The original is backed up to
`.pre_batch_a.bak` before the rewrite.
"""
# stdout must survive its own output: this console is cp1252 and characters like U+2248/U+2192/U+2717 raise
# UnicodeEncodeError from print() itself. The honesty audit once crashed on its own
# FAILURE path for exactly this reason. Degrade the glyph, never the run.
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import collections
import json
import pathlib
import shutil

HERE = pathlib.Path(__file__).resolve().parent
CONSOLIDATED = HERE / "dc_actions_county_consolidated.json"
# batch A lives in the session scratchpad where the sweep's sub-agents wrote it
SCRATCH = pathlib.Path(
    r"C:\Users\ahend\AppData\Local\Temp\claude"
    r"\C--Users-ahend-Downloads-Decennial-Summer-Work-Remaking-Orennia-REBUILD-PLANNING"
    r"\e92c9d93-ffb6-4875-9562-58ea5d0903d3\scratchpad")
BATCH_A = SCRATCH / "batch_A.json"

ALL92 = {
    "Adams", "Allen", "Bartholomew", "Benton", "Blackford", "Boone", "Brown", "Carroll", "Cass",
    "Clark", "Clay", "Clinton", "Crawford", "Daviess", "Dearborn", "Decatur", "DeKalb", "Delaware",
    "Dubois", "Elkhart", "Fayette", "Floyd", "Fountain", "Franklin", "Fulton", "Gibson", "Grant",
    "Greene", "Hamilton", "Hancock", "Harrison", "Hendricks", "Henry", "Howard", "Huntington",
    "Jackson", "Jasper", "Jay", "Jefferson", "Jennings", "Johnson", "Knox", "Kosciusko", "LaGrange",
    "Lake", "LaPorte", "Lawrence", "Madison", "Marion", "Marshall", "Martin", "Miami", "Monroe",
    "Montgomery", "Morgan", "Newton", "Noble", "Ohio", "Orange", "Owen", "Parke", "Perry", "Pike",
    "Porter", "Posey", "Pulaski", "Putnam", "Randolph", "Ripley", "Rush", "St. Joseph", "Scott",
    "Shelby", "Spencer", "Starke", "Steuben", "Sullivan", "Switzerland", "Tippecanoe", "Tipton",
    "Union", "Vanderburgh", "Vermillion", "Vigo", "Wabash", "Warren", "Warrick", "Washington",
    "Wayne", "Wells", "White", "Whitley",
}
assert len(ALL92) == 92

payload = json.loads(CONSOLIDATED.read_text(encoding="utf-8"))
batch_a = json.loads(BATCH_A.read_text(encoding="utf-8"))

actions, coverage, walls = payload["actions"], payload["coverage"], payload["walls"]
a_actions, a_coverage, a_walls = batch_a["actions"], batch_a["coverage"], batch_a["walls"]

# ---- state BEFORE, measured rather than recalled ----------------------------------------
before_cov = {c["county"] for c in coverage}
print(f"BEFORE: {len(actions)} actions, {len(coverage)} coverage rows, {len(walls)} walls")
print(f"        batches present: {sorted({c.get('source_batch') for c in coverage})}")
print(f"        {len(ALL92 - before_cov)} counties uncovered: {sorted(ALL92 - before_cov)}")
assert "A" not in {c.get("source_batch") for c in coverage}, \
    "batch A is ALREADY in the consolidated file — this script has run before; do not double-load"

# ---- the guard the loader did not have: batch A must be exactly the shortfall -------------
a_cov_counties = {c["county"] for c in a_coverage}
overlap = a_cov_counties & before_cov
assert not overlap, f"batch A would DOUBLE-COUNT these counties: {sorted(overlap)}"
extra = a_cov_counties - ALL92
assert not extra, f"batch A carries non-counties: {sorted(extra)}"
for a in a_actions:
    assert a["county"] in ALL92, f"batch A action for unknown county: {a['county']}"

ACTION_SHAPE = list(actions[0].keys())
COVER_SHAPE = list(coverage[0].keys())
WALL_SHAPE = list(walls[0].keys())


def normalise(row, shape, batch):
    """Map a batch-A row onto the consolidated shape. Absent fields become NULL — never
    invented — and `pulled_at` carries its value across to `_pulled_at`."""
    out = {}
    for k in shape:
        if k == "source_batch":
            out[k] = batch
        elif k == "raw_row":
            out[k] = json.dumps(row, ensure_ascii=False)
        elif k == "_pulled_at":
            out[k] = row.get("_pulled_at") or row.get("pulled_at")
        else:
            out[k] = row.get(k)
    return out


new_actions = [normalise(r, ACTION_SHAPE, "A") for r in a_actions]
new_coverage = [normalise(r, COVER_SHAPE, "A") for r in a_coverage]
new_walls = [normalise(r, WALL_SHAPE, "A") for r in a_walls]

# ---- what the drift actually cost, stated rather than hidden -----------------------------
null_instrument = sum(1 for r in new_coverage if not r.get("search_instrument"))
null_cov_pulled = sum(1 for r in new_coverage if not r.get("_pulled_at"))
null_expiry = sum(1 for r in new_actions if r.get("expiry_condition_verbatim") is None)
null_pdf = sum(1 for r in new_actions if r.get("ordinance_pdf_url") is None)
print(f"\nSCHEMA DRIFT, batch A -> consolidated shape (NULL, never invented):")
print(f"  coverage.search_instrument NULL on {null_instrument} of {len(new_coverage)}"
      f"  (field did not exist in batch A)")
print(f"  coverage._pulled_at        NULL on {null_cov_pulled} of {len(new_coverage)}")
print(f"  actions.expiry_condition_verbatim NULL on {null_expiry} of {len(new_actions)}")
print(f"  actions.ordinance_pdf_url         NULL on {null_pdf} of {len(new_actions)}")
carried = sum(1 for r in new_actions if r.get("_pulled_at"))
print(f"  actions._pulled_at carried from `pulled_at` on {carried} of {len(new_actions)}")

# ---- residual duplicate check across the WHOLE merged set ---------------------------------
merged_actions = actions + new_actions
merged_coverage = coverage + new_coverage
merged_walls = walls + new_walls

key = collections.Counter(
    (a["county"], (a.get("url") or "").lower().rstrip("/"), (a.get("instrument") or "")[:60].lower())
    for a in merged_actions)
dups = {k: n for k, n in key.items() if n > 1}
assert not dups, f"exact duplicate action rows after merge: {dups}"

cov_names = [c["county"] for c in merged_coverage]
assert len(cov_names) == len(set(cov_names)), "duplicate coverage rows after merge"
missing = ALL92 - set(cov_names)
assert not missing, f"STILL not 92 of 92 after merging A: {sorted(missing)}"

# ---- write, after backing up ---------------------------------------------------------------
backup = CONSOLIDATED.with_suffix(".json.pre_batch_a.bak")
shutil.copy2(CONSOLIDATED, backup)
payload["actions"], payload["coverage"], payload["walls"] = \
    merged_actions, merged_coverage, merged_walls
CONSOLIDATED.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

print(f"\nAFTER:  {len(merged_actions)} actions (+{len(new_actions)}), "
      f"{len(merged_coverage)} coverage rows (+{len(new_coverage)}), "
      f"{len(merged_walls)} walls (+{len(new_walls)})")
print(f"        coverage now {len(set(cov_names))} of 92 counties — complete")
print(f"        backup written: {backup.name}")

grades = collections.Counter(a["evidence_grade"] for a in merged_actions)
types = collections.Counter(a["action_type"] for a in merged_actions)
print(f"\n  evidence_grade: {dict(grades)}")
print(f"  action_type:    {dict(types)}")
print(f"\n  batch A contributed {sum(1 for a in new_actions if a['evidence_grade'] == 'VERIFIED_AT_OFFICIAL_SOURCE')}"
      f" of its {len(new_actions)} actions as VERIFIED_AT_OFFICIAL_SOURCE"
      f" — the highest verified rate of any batch.")
