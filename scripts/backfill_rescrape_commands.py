"""G115 - give every registry row a RE-SCRAPE COMMAND, or say honestly why it cannot have one.

    python scripts/backfill_rescrape_commands.py            # report only
    python scripts/backfill_rescrape_commands.py --apply    # append the rows

THE G16 CONTRACT, restated because this is the row that enforces it: a `_registry` entry must be
enough for A STRANGER TO RE-RUN THE WORK. Measured by `audit_registry_truth.py`, **296 of 328
registered objects carry no `RE-SCRAPE COMMAND` at all.** They predate the contract.

⛔ APPENDS, NEVER OVERWRITES - the same discipline as `reconcile_registry_counts.py`. A registry
row records what a load produced at a moment in time and rewriting it destroys that, so the
re-scrape command arrives as a NEW row and the original stays as history.

⛔ AND IT NEVER GUESSES A COMMAND. This is the whole difficulty of the row, and the reason it has
sat open: writing `python scripts/build_<name>.py` for every table would produce 296 rows that
LOOK compliant and mostly do not run. A command that does not work is worse than an absent one -
absence is visible, a wrong command is discovered by the person relying on it. So each object is
resolved to one of FIVE states, and each gets a different, honest entry:

  built_here        a script in THIS repo creates it. The command is that script, verified to
                    exist on disk. Resolved the same way audit_wiring_census.py resolves a
                    builder, INCLUDING the f-string form `OUT = f"{DS}.name"` +
                    `CREATE OR REPLACE TABLE `{OUT}`` that most build scripts here use.
  scraped_here      ⚠ INFERRED, and the row says so. The scrapers under scrapers/lane_* write
                    through the client API rather than CREATE OR REPLACE TABLE, so a builder
                    cannot be resolved the way a build script can. A loader that names the table
                    beside a write call is strong evidence, not proof.
  clip_of_energy    a clip of an `energy.*` table, made by the platform session. We do not own
                    the loader, and 174 registered objects are in this class. The honest entry
                    names the parent and says the re-run belongs to the other workstream.
  harvest           produced by a long-running QueueScope harvest. The command exists but is
                    NOT a one-liner anyone should paste - it is hours of work and there is a
                    standing rule against a second concurrent process. The entry says so and
                    points at the ladder runner.
  unresolved        ⛔ neither a builder nor a parent could be established. This is the honest
                    residue and it is REPORTED, not papered over.

⚠ WHY THE PARENT MATTERS FOR A CLIP. "Re-run this" for a clip means "re-clip from
energy.<parent>", which is a different instruction from "re-scrape the publisher" - and the
registry has to distinguish them or a future session will go looking for a scraper that was never
ours to write.
"""
import io
import os
import re
import sys as _sys

try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DS = "energy-platfrom.indiana_app"
APPLY = "--apply" in _sys.argv
client = bigquery.Client(project="energy-platfrom")

# --------------------------------------------------------------------------------------------
# Resolve builders exactly the way the wiring census does, so the two instruments cannot
# disagree about who builds what.
VAR_TABLE = re.compile(r'^\s*([A-Za-z_]\w*)\s*=\s*f?["\'][^"\']*?\.([a-z_][a-z0-9_]*)["\']', re.M)
CREATE_VAR = re.compile(r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW)\s+`?\{(\w+)\}", re.I)

sources = {}
for dirpath, _, names in os.walk(REPO):
    if any(x in dirpath for x in ("__pycache__", ".git", "node_modules", "vendor", "\\data",
                                  "/data")):
        continue
    for fn in names:
        if fn.endswith(".py"):
            rel = os.path.relpath(os.path.join(dirpath, fn), REPO).replace("\\", "/")
            try:
                sources[rel] = io.open(os.path.join(dirpath, fn), encoding="utf-8",
                                       errors="ignore").read()
            except Exception:
                pass

builder = {}
for rel, src in sources.items():
    vt = {m.group(1): m.group(2) for m in VAR_TABLE.finditer(src)}
    for m in CREATE_VAR.finditer(src):
        if m.group(1) in vt:
            builder.setdefault(vt[m.group(1)], []).append(rel)
    for m in re.finditer(r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW)\s+`?[^`\s]*?"
                         r"\.(in_[a-z0-9_]+|vw_[a-z0-9_]+|_[a-z0-9_]+)`", src, re.I):
        builder.setdefault(m.group(1), []).append(rel)

# ⚠ SECOND PASS, WEAKER, AND LABELLED AS SUCH IN THE ROW IT WRITES.
# The pass above only sees `CREATE OR REPLACE TABLE`. The scrapers under scrapers/lane_* do not
# write that way - they push rows through the client API (`load_table_from_json`,
# `load_table_from_dataframe`, an explicit `table_id`/`destination`). So 82 objects carrying a
# real publisher URL as their source - api.municode.com, gis.pjm.com, the county sites - looked
# unresolved, and those are exactly the rows a RE-SCRAPE command is FOR.
#
# ⛔ THIS INFERS, so it must not pretend otherwise: a file that NAMES the table near a write call
# is very probably its loader, and "very probably" is not "verified". Rows resolved this way say
# `inferred from` in the method text, so a reader knows to check before trusting the command.
WRITEISH = re.compile(r"load_table_from|table_id|destination|insert_rows|to_gbq|WRITE_TRUNCATE",
                      re.I)
inferred = {}
for rel, src in sources.items():
    if not rel.startswith("scrapers/") or not WRITEISH.search(src):
        continue
    for m in re.finditer(r"\b(in_[a-z0-9_]{4,})\b", src):
        inferred.setdefault(m.group(1), set()).add(rel)

reg = {r.table_name: r for r in client.query(f"""
    SELECT table_name, ANY_VALUE(source) source, ANY_VALUE(method) method,
           ANY_VALUE(notes) notes, MAX(built_at) built_at
    FROM `{DS}._registry` GROUP BY table_name""")}

has_cmd = {r.table_name for r in client.query(f"""
    SELECT DISTINCT table_name FROM `{DS}._registry`
    WHERE UPPER(IFNULL(method, '') || ' ' || IFNULL(notes, '')) LIKE '%RE-SCRAPE COMMAND%'""")}

HARVEST = re.compile(r"^in_pjm_qs_|^in_pjm_queuescope|rungcheck|^in_miso_poi_ladder$"
                     r"|^in_bus_headroom_miso_ladder$")

plan = {"built_here": [], "scraped_here": [], "clip_of_energy": [], "harvest": [],
        "unresolved": []}
for name, r in sorted(reg.items()):
    if name in has_cmd:
        continue
    # ⚠ `scrapers/` COUNTS TOO, and leaving it out was an error the first run exposed:
    #    82 objects landed in "unresolved" carrying a publisher URL as their source
    #    (api.municode.com, gis.pjm.com, the county sites) because their loaders live under
    #    scrapers/lane_*, not scripts/. Those are precisely the rows a RE-SCRAPE command is FOR.
    #    scripts/ is preferred where both exist, because a build is cheaper to re-run than a scrape.
    cands = sorted(set(builder.get(name, [])))
    bs = ([b for b in cands if b.startswith("scripts/")]
          or [b for b in cands if b.startswith("scrapers/")])
    src = (r.source or "")
    if HARVEST.search(name):
        plan["harvest"].append((name, None))
    elif bs:
        plan["built_here"].append((name, bs[0]))
    elif sorted(inferred.get(name, ())):
        plan["scraped_here"].append((name, sorted(inferred[name])[0]))
    else:
        m = re.search(r"energy[.`]{1,2}([a-z_][a-z0-9_]*)", src)
        if m or "energy" in src.lower():
            plan["clip_of_energy"].append((name, m.group(1) if m else None))
        else:
            plan["unresolved"].append((name, None))

print("=" * 92)
print(f"G115 RE-SCRAPE BACKFILL - {len(reg)} registered objects, "
      f"{len(has_cmd)} already carry a command")
print("=" * 92)
for k in ("built_here", "scraped_here", "clip_of_energy", "harvest", "unresolved"):
    print(f"  {k:16s} {len(plan[k]):>4}")
todo = sum(len(v) for v in plan.values())
print(f"  {'TO WRITE':16s} {todo:>4}")

if plan["unresolved"]:
    print("\n⛔ UNRESOLVED - no builder in this repo and no energy parent named in the source.")
    print("   These get a row that SAYS SO rather than a command that would not run:")
    for n, _ in plan["unresolved"][:40]:
        print(f"      {n:44s} source={str(reg[n].source)[:52]!r}")
    if len(plan["unresolved"]) > 40:
        print(f"      … and {len(plan['unresolved']) - 40} more")

# ⛔ Verify every command actually points at a file that exists. A command naming a script that
#    is not there is precisely the "looks compliant, does not run" failure this script exists to
#    avoid, so it is checked rather than assumed.
missing = [(n, b) for n, b in plan["built_here"] + plan["scraped_here"]
           if not os.path.exists(os.path.join(REPO, b.replace("/", os.sep)))]
assert not missing, f"builder script does not exist on disk: {missing[:5]}"
print(f"\n  all {len(plan['built_here'])} builder scripts verified present on disk")

if not APPLY:
    print("\n  DRY RUN - nothing written. Re-run with --apply to append these rows.")
    _sys.exit(0)

rows = []
for name, b in plan["built_here"]:
    rows.append((name, reg[name].source, f"RE-SCRAPE COMMAND: python {b}",
                 "G115 backfill: builder resolved from the repo and verified present on disk. "
                 "Appended, not overwritten - the original load row stands as history."))
for name, b in plan["scraped_here"]:
    rows.append((name, reg[name].source, f"RE-SCRAPE COMMAND: python {b}   (inferred from - this "
                 f"loader names the table beside a BigQuery write call; verify before relying "
                 f"on it)",
                 "G115 backfill. ⚠ INFERRED, not verified: the scrapers write through the client "
                 "API rather than CREATE OR REPLACE TABLE, so the builder cannot be resolved the "
                 "way a build script can. The file named here mentions this table next to a "
                 "write call, which is strong but not proof. ⛔ Before re-running any scraper: "
                 "read robots.txt, no CAPTCHA bypass, no UA spoofing, no account creation - a "
                 "gated source recorded BLOCKED with its wall quoted verbatim is a SUCCESS."))
for name, parent in plan["clip_of_energy"]:
    p = f"energy.{parent}" if parent else "an energy.* table named in this row's source"
    rows.append((name, reg[name].source,
                 f"RE-SCRAPE COMMAND: not ours to run - re-clip from {p}. "
                 f"energy.* is READ-ONLY to this workstream and its loaders belong to the "
                 f"platform session.",
                 "G115 backfill: this object is a CLIP, so 'refresh' means re-clip from the "
                 "parent, not re-scrape a publisher. Stating the wrong one sends a future "
                 "session looking for a scraper that was never ours."))
for name, _ in plan["harvest"]:
    rows.append((name, reg[name].source,
                 "RE-SCRAPE COMMAND: powershell -ExecutionPolicy Bypass -File "
                 "scripts\\run_pjm_ladder.ps1  -- resumes, continues AND repairs the ladder, and "
                 "is safe to run while one is going because it polls for the ABSENCE of a "
                 "QueueScope process.",
                 "G115 backfill. ⛔ NEVER start a second QueueScope process, and NEVER delete "
                 "data/ - the batch markers live there and deleting them forces a duplicating "
                 "re-harvest. Owner id for case 23 is 1568, not 739; 739 loads 0 rows and exits "
                 "successfully. One direction at one MW rung is roughly 4.5 hours."))
for name, _ in plan["unresolved"]:
    rows.append((name, reg[name].source,
                 "RE-SCRAPE COMMAND: UNKNOWN - no builder exists in this repository and no "
                 "energy.* parent is named in this row. Establish the provenance before relying "
                 "on this table.",
                 "G115 backfill. ⛔ Recorded as unresolved ON PURPOSE. A plausible-looking "
                 "command that does not run is worse than an absent one: absence is visible, a "
                 "wrong command is discovered by the person relying on it."))

print(f"\n  appending {len(rows)} rows …")
# ⚠ FOUR PARALLEL ARRAYS ZIPPED BY OFFSET, not one array of STRUCTs. BigQuery rejects
#   ArrayQueryParameter with an inline "STRUCT<...>" type string outright
#   ("Invalid value for type: STRUCT<t STRING, ...> is not a valid value"), and the parallel-array
#   form needs no type gymnastics.
job = client.query(
    f"""INSERT INTO `{DS}._registry`
        (table_name, source, method, n_rows, gb_scanned, built_at, notes)
        SELECT t, s, m, NULL, 0.0, CURRENT_TIMESTAMP(), n
        FROM UNNEST(@t) AS t WITH OFFSET i
        JOIN UNNEST(@s) AS s WITH OFFSET j ON i = j
        JOIN UNNEST(@m) AS m WITH OFFSET k ON i = k
        JOIN UNNEST(@n) AS n WITH OFFSET l ON i = l""",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ArrayQueryParameter("t", "STRING", [r[0] for r in rows]),
        bigquery.ArrayQueryParameter("s", "STRING", [r[1] for r in rows]),
        bigquery.ArrayQueryParameter("m", "STRING", [r[2] for r in rows]),
        bigquery.ArrayQueryParameter("n", "STRING", [r[3] for r in rows]),
    ]))
job.result()

left = list(client.query(f"""
    SELECT COUNT(DISTINCT t.table_id) n FROM `{DS}.__TABLES__` t
    LEFT JOIN (SELECT DISTINCT table_name FROM `{DS}._registry`
               WHERE UPPER(IFNULL(method,'') || ' ' || IFNULL(notes,'')) LIKE '%RE-SCRAPE COMMAND%')
      g ON g.table_name = t.table_id
    WHERE g.table_name IS NULL AND NOT STARTS_WITH(t.table_id, '_')"""))[0].n
print(f"  objects still with NO re-scrape command: {left}")
print("RE-SCRAPE BACKFILL COMPLETE")
