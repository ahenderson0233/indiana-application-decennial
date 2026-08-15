# Paste-ready opening prompt for the Opus 5 session

---

You are continuing an EXISTING, working project: a static Indiana siting-intelligence web
app for data-centre/BESS development, repo at
`C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial`
(GitHub: ahenderson0233/indiana-application-decennial, deployed via GitHub Pages).

STEP 0 — before ANY action, read these, fully, in this order:
1. docs/HANDOFF.md   (the whole file — it contains your required-reading list, the entire
   plan, best/worst practices, the T1-T8 roadmap you will execute, section 5b listing work
   ALREADY DONE, and the DO-NOT list)
2. docs/PLAN.md
3. docs/AUDIT_WORKLIST.md  (verdicts for every BigQuery table — the audit is COMPLETE;
   never re-audit)
Then run `git log --oneline -15` in the repo and read the messages — they are the ground
truth of what exists. Then confirm to me, in one short list: what you read, which roadmap
task (T1-T8) is next per HANDOFF §5/§5b, and what you will NOT redo.

HARD RULES (violations have each cost real time; they are explained in HANDOFF §3-4):
- BigQuery project `energy-platfrom` (misspelling INTENTIONAL). Dataset `energy.*` is
  READ-ONLY except APPEND-only rows to energy.registry_sources when documenting sources.
  ALL writes go to `energy-platfrom.indiana_app`, and every table you create gets a row in
  `indiana_app._registry` in the same run.
- Never trust a table/column NAME — read 1-3 rows first (samples for every table already
  exist: grep docs/SAMPLES_INDIANA.md / SAMPLES_ALL_PART2.md — never load them whole).
- A zero or a suspiciously uniform result is a claim about YOUR instrument: suspect the
  join, then the filter, then the data. Widened predicates before accepting absence.
- Dry-run queries first; TABLESAMPLE (never SELECT * LIMIT) on big tables; batch generated
  SQL by emitted length; BigQuery reserved words include `rows` and `FULL`.
- Use Write/Edit for any content with backticks or backslashes — never inline through the
  shell. Commit with explicit paths (NEVER `git add -A`), push after each completed task.
- Indiana only, clipped at the border. Cannot-assess renders as itself, never zero.
  Estimated locations never style as published ones. Every on-screen number carries its
  source table + build date. No centroids ever. No Orennia/licensed data in repo/app/exports.
- Refreshes are SCRIPT runs (scripts/ and scrapers/ are idempotent) — do not launch agents
  for anything a script already does. Ask the operator rather than guess on any dataset
  whose use is ambiguous; batch your questions.

ENVIRONMENT (exact commands are in HANDOFF §5 Setup): python =
energy-platform\.venv\Scripts\python.exe with GOOGLE_APPLICATION_CREDENTIALS=
C:\Users\ahend\bq-key.json and PYTHONIOENCODING=utf-8; local preview via the
`indiana-app` launch config (localhost:8123).

Work the roadmap in order (T1 verify state first — data.html table count and a 2-row
upload test). After EVERY completed task: update docs/HANDOFF.md §5b so nothing is ever
recomputed, then commit and push. If an acceptance check fails, stop and report the
measured failure — do not improvise around it.

---
