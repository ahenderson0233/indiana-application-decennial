# Indiana 92-county data-centre ACTION sweep — the layer no code library carries

**Swept 2026-08-16 by 8 agents. Merged, gated and loaded 2026-08-16.**
Tables: `energy-platfrom.indiana_app.in_dc_actions_county_v2` (107 actions) and
`in_dc_actions_coverage_v2` (92 counties, one row each). Loader
`scrapers/lane_f/pull_dc_actions_county.py`. Surfaced on Community by
`scripts/export_ordinances.py`.

---

## 1. Why this exists

`ORDINANCE_FINDINGS.md` §2 established that a codified-ordinance corpus **cannot answer the
county-posture question in Indiana.** After sweeping 19 vocabularies across every searchable
Indiana Municode code, the codified corpus that genuinely names a data centre as a land use is
**three sections in two counties**. Meanwhile Boone County — the LEAP district, the largest
data-centre story in the state — adopted a one-year moratorium in June 2026 that appears in no
code library at all, because it is not yet codified and Boone is not a Municode client.

**A product that reads only codified codes renders Boone as SILENT, i.e. permissive, when it is
among the most restrictive postures in Indiana.** That inversion is what this sweep exists to
prevent.

## 2. What it found

| | |
|---|---:|
| counties swept | **92 of 92** |
| counties where an action was found | 53 |
| counties where nothing surfaced | 39 |
| action rows | **107** |
| …**verified at the government's own source** | **23**, across **15 counties** |
| …reported only, a worklist | 84 |
| walls recorded verbatim | 38 hosts |

### Action types

| type | verified | lead only | total |
|---|---:|---:|---:|
| proposed | 5 | 24 | 29 |
| **moratorium** | **7** | 17 | 24 |
| approval-permissive | 1 | 21 | 22 |
| **adopted-uncodified-ordinance** | **5** | 3 | 8 |
| petition-pending | 3 | 4 | 7 |
| denied | 0 | 7 | 7 |
| withdrawn | 1 | 5 | 6 |
| expired-moratorium | 1 | 1 | 2 |
| **ban-prohibition** | 0 | 2 | 2 |

### The 13 verified restrictive postures — the decision-relevant set

| county | type | instrument | effective |
|---|---|---|---|
| **Boone** | moratorium | Ordinance 2026-08, one-year, unincorporated county | 2026-06-16 → 2027-06-15 |
| **Lake** | adopted-uncodified-ordinance | **Ordinance 2590** — data centres **PROHIBITED in all business districts**; Special Exception in M-1/M-2 | 2025-08-12 |
| **LaPorte** | adopted-uncodified-ordinance | LaPorte County Data Center Ordinance | no date stated |
| **Martin** | adopted-uncodified-ordinance | Ordinance 2026-22, special-permitting requirement | no date stated |
| **Martin** | moratorium | Ordinance 2026-23, temporary | no date stated |
| **Miami** | moratorium | recorded instrument, all DC applications/permits | 2026-05-04 |
| **Rush** | moratorium | 90-day, special session | 2026-02-13 |
| **Rush** | moratorium | 6-month, all DC applications | 2026-03-09 |
| **Shelby** | moratorium | resolution, new DC applications | no date stated |
| **Starke** | moratorium | Ordinance 2025-37, temporary | 2025-12-15 |
| **Tippecanoe** | adopted-uncodified-ordinance | UZO Amendment #123 "Large Data Centers" | no date stated |
| **Tippecanoe** | adopted-uncodified-ordinance | Town of Dayton Ordinance 2025-19, adopting the UZO standards | no date stated |
| **White** | expired-moratorium | Ordinance 2025-10-20-02, six-month term | 2025-10-20 → 2026-04-20 |

**Not one of these is in any codified code library.**

## 3. The instrument: how it was run, and what that costs

Eight agents, one per region plus a re-sweep, each doing ≥2 web-search queries per county and
then verifying at the county's **own** `.gov`/`.us` site where reachable. `robots.txt` was read
per host **before** any fetch; a challenged or 403 robots.txt is recorded BLOCKED and the host is
never crawled. Two known-positive controls (Boone, Miami) were planted: **the loader refuses to
run if either is missing or unverified**, because their absence would mean the instrument is
broken rather than that the counties are silent.

### Two gates the loader enforces before it will write

1. **The denominator gate.** `ALL92` is compared against `energy.county_boundaries` STATEFP='18'
   and must match exactly. A 93rd "county" is precisely how a FEMA roll-up broke elsewhere in
   this project (`fipsCountyCode='000'` is 'Statewide', not a county).
2. **The completeness gate — added after it was needed.** Coverage must be 92 of 92 or the load
   is refused. See §5.

### What the negative findings are actually worth

`SEARCHED_NONE_FOUND` at the web-search layer is **weaker** than a full-text codified search, and
weaker still than reading the county's minutes. Measured honestly across the 39:

- **only 21 of 39 had the county's official site fetched at all**; 9 never identified a county
  website;
- **4 counties — Henry, Johnson, Union, Wayne — were recorded on a single query**, below the ≥2
  the method itself requires. They are the weakest rows in the table.

**None of these may be scored as permissive.** Absence of evidence at the search layer is not
evidence of absence of regulation.

## 4. The 84 leads, and why they are shipped separately

`REPORTED_NEEDS_VERIFICATION` means a news outlet or aggregator carries it and no government
source was reached. These are a **worklist, never a posture.** They are separated at export time
(`export_ordinances.py` splits on `evidence_grade` in SQL, not in the page) and rendered in a
distinct table headed *"A WORKLIST, NOT A POSTURE"*.

Two of the three reported **bans** — Cass and Marshall — are in this set. A prohibition is the
strongest siting signal available, so those are the highest-value verifications outstanding.

## 5. ⚠ THE DEFECT THIS RUN CAUGHT — and it was the opposite of the one predicted

The session handoff warned that a stale `batch_MINE.json` might be **double-counted** if the
merge globbed `batch_*.json`. Measured before anything was written:

- coverage carried **79 rows across 79 distinct counties — zero duplicates**;
- `batch_MINE` contributed exactly its **2 known-positive controls** (Boone, Miami);
- **2 of MINE's 5 action rows were dropped** as duplicates of other batches.

The merge deduped deliberately. **The real defect was omission.** The consolidation ran at
**13:24**; `batch_A.json` was written at **13:37** because NW was still re-sweeping. The file
therefore carried B/C/D/E/F/G/MINE and no A — **79 of 92 counties** — and the 13 absent counties
were the entire northwest quadrant: Benton, Carroll, Fountain, Jasper, **Lake**, **LaPorte**,
Newton, **Porter**, Pulaski, Starke, **Tippecanoe**, Warren, White.

Shipping that would have rendered the state's most industrial corner as *not assessed*, and
**Lake County Ordinance 2590 would have sat unread in a JSON file.**

The loader printed the shortfall and would have loaded anyway. It now **refuses**:

```python
assert not missing, (
    f"REFUSING TO LOAD: coverage is {len(cov_counties)} of 92 counties; ...
     do NOT load a partial sweep, because not-assessed renders as not-regulated.")
```

**Transferable rule: a completeness shortfall must be an ASSERT, not a print.** A console line
in a long agent run is not a control. The same run had a correct duplicate gate and no
completeness gate, and it was the missing one that fired.

## 6. ⚠ THE SECOND RECOVERY — NW was swept twice and only one pass was collected

Eight sweep agents ran; **seven wrote batch files, one did not.** The first NW agent
(14.8 MB transcript, finished 13:02) returned its results **in its final message**, which the
parent was supposed to collect and never did. It was recovered from the transcript by
`scrapers/lane_f/salvage_agent_results.py` and preserved as
`scrapers/lane_f/nw_sweep_first_pass_salvaged.json`.

**The re-sweep is not a superset of it.** Measured:

| | actions | verified |
|---|---:|---:|
| NW first pass (never collected) | 17 | **11** |
| NW re-sweep (`batch_A`, loaded) | 20 | 9 |

Per county, neither dominates: the first pass verified more in **Jasper, Lake and Starke**; the
re-sweep verified more in **Tippecanoe** and found **Fountain** at all (the first recorded
Fountain BLOCKED). The loaded table is therefore the *later* sweep, not the *best* one.

**And they contradict each other on a fact.** Jasper County rezone petition **Cause #PC-22-25**
(NIPSCO, ~5 parcels Ag→I-2, Kankakee Township) is recorded `denied` by the first pass and
`petition-pending` by the re-sweep — **both graded VERIFIED_AT_OFFICIAL_SOURCE.** That is not
reconcilable by inspection and was **not** resolved by picking the more plausible one. It is
referred to official-source verification.

**Transferable rule: an agent's deliverable must be a FILE IT WRITES ITSELF.** Every brief in the
verification pass now says so explicitly. A parent collecting replies is a single point of
failure, and here it failed twice over — once by running early, once by never reading a reply at
all.

## 7. Why the parent never got its confirmations

Every regional agent tried to reply and every reply failed identically:

> "No agent named 'general-purpose' is reachable… use the agent ID from a background agent's
> spawn result."

The parent identified itself by agent **type**, not by ID. Counts were relayed by hand. One agent
(WC) went further and correctly refused to take the requesting session's legitimacy on trust,
noting it could not corroborate a live sibling session — the right instinct, and in this case the
request was genuine.

## 8. The walls — 38 hosts, quoted verbatim, none worked around

Two shapes dominate, and both bear on the operator's outstanding robots-vs-terms ruling:

**`ClaudeBot` disallowed by name while the site serves the public freely.** `dcmap.us`,
`pdclarion.com`, `datacenterdynamics.com`, `purdueexponent.org`, `newsbug.info`, `wndu.com`,
`wsbt.com`, `kokomotribune.com`, `wane.com`, `14news.com` — typically alongside
`Claude-Web` and `anthropic-ai`.

**County governments 403-ing their own `robots.txt`.** `co.hendricks.in.us`,
`dearborncounty.org`, `pikecounty.in.gov`, `sullivancounty.in.gov`, `fountaincounty.net`,
`evansvillegov.org`, `bedfordtimes-press.com`. The permission file itself could not be read, so
no crawl of those hosts could be justified and none was attempted.

Also recorded: one paywall (`morgancountycorrespondent.com`), one HTTP 400 on robots.txt
(`us-east-1-indy.graphassets.com` — which is why the official Indianapolis Proposal No. 238, 2026
PDF was **not** fetched, conservatively), and one network failure explicitly distinguished from a
policy wall (`wthr.com`, timeout then ECONNRESET).

**Four walls from the uncollected NW first pass were missing from the consolidated set** and are
recovered in `nw_sweep_first_pass_salvaged.json`: `datacenterdynamics.com`, `purdueexponent.org`,
`newsbug.info`, `wndu.com`.

## 9. What is outstanding

1. **Verify the 84 leads** — in flight, four agents, official sources only. Marshall's and Cass's
   reported **bans** first.
2. **Resolve Jasper PC-22-25** (§6) at the Plan Commission's own minutes.
3. **Re-sweep the 4 single-query counties** — Henry, Johnson, Union, Wayne.
4. **Fetch the official site for the 18 negative counties where it was never reached.**
5. **Reconcile the salvaged NW first pass** against the verification results, rather than against
   the re-sweep.
6. Fold verified expiry dates into P5 county posture so a moratorium's **end date** is on the
   dossier — a 90-day moratorium and a permanent ban are not the same siting fact.

## 10. Provenance

Publisher's own dates throughout (`observed_date`, `effective_from`, `effective_to`,
`expiry_condition_verbatim` for condition-based expiries such as *"until the Zoning Ordinance is
amended"*); `_pulled_at` is a separate column and is never mixed with them. `raw_row` carries each
agent's original JSON row unmodified, and `source_batch` names the sweep that produced it.

Both tables registered in `_registry` in the same run that wrote them; one append-only row to
`energy.registry_sources` (`updated_by='indiana-app-ordinances-agent'`). **`energy-platfrom.energy`
was otherwise read-only.** `in_ordinances_dc*` and `in_dc_actions` (the 79-row DataCenterWatch
tracker) were not modified — three separate instruments, never merged.
