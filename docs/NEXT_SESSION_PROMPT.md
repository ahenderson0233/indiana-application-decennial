# NEXT SESSION — paste everything below this line as your first message

Continue the Indiana siting-intelligence application.
Repo: `C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial`
(GitHub `ahenderson0233/indiana-application-decennial`, branch `main`)

---

## ⛔ DO THESE THREE THINGS FIRST, IN THIS ORDER. Propose nothing before you have.

### 1. Is the PJM harvest alive?

```bash
powershell -NoProfile -Command "@(Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | Where-Object { $_.CommandLine -like '*pull_pjm*' }).Count"
```

⚠ **A count of 2 is almost always your own command self-matching** — the filter string
`*pull_pjm*` appears in your own process's command line. Confirm by parentage before believing it:

```bash
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | Where-Object { $_.CommandLine -like '*pull_pjm*' } | ForEach-Object { 'PID ' + $_.ProcessId + ' :: ' + $_.CommandLine }"
```

**If it returns 0, resume it. This one command resumes, continues AND repairs, and it is safe to
run even while one is already going** — it polls for the ABSENCE of a QueueScope process rather
than waiting on a handle, which is the exact failure that once spawned a duplicate harvester:

```bash
powershell -ExecutionPolicy Bypass -File scripts\run_pjm_ladder.ps1
```

⛔ **NEVER start a second QueueScope process.** ⛔ **NEVER delete `data/`** — the checkpoint
markers live there and deleting them forces a duplicating re-harvest; **archive, never delete**.
⛔ **Owner is 1568, not 739** — 739 is AEP in the *default* case and loads **0 rows while exiting
successfully**.

### 2. Checkpoint

```bash
python scripts/checkpoint.py
```

**Expect 1–3 failures and expect them to be correct** (it was **1** at 08:18 on 2026-08-19 — the wiring census alone, at 287 of 304)**:**

| failing check | why |
|---|---|
| `wiring census: N of ~301` | new tables not yet on a surface. Standing — and **G72 is the item that closes it** |
| `honesty audit: 1 failure` + `1 unregistered` | **the unregistered table IS whichever ladder rung is mid-flight.** It registers on completion |

⛔ **Anything else failing is real.** `shipped payload agrees with the warehouse`, the five `D85`
guards, `no shipped payload is older than the table it reads` and `no payload has lost a key`
must all PASS — each exists because it already broke once.

⚠ If the wiring census reports `ConnectionResetError`, that is a network blip (a closed laptop),
not a defect. Re-run it.

### 3. Read, in this order

| # | file | why |
|---|---|---|
| 1 | `docs/SESSION_START.md` | standing rules and the governing principle |
| 2 | ⭐ **`docs/HANDOFF_2026-08-19.md`** | **the current one.** The ladder, the traps, everything below in full |
| 3 | ⭐ **`docs/TABLE_PURPOSE_INDEX.md`** | **generated.** 301 objects → purpose → the control that exposes it. **The worklist for G72** |
| 4 | `docs/BACKLOG.md` | the **⚠ IN FLIGHT** row first, then the G-index (G1–G76) |
| 5 | ⭐ **`docs/REFERENCE_TOOL_GAP.md`** | our screening vs the operator's own two tools |
| 6 | `docs/FEATURE_INVENTORY.md` | every feature, how it works, its BigQuery table |
| 7 | `docs/BUS_PARITY_2026-08-18.md` | the vendor comparison; §3f is the placement methodology |
| 8 | `scripts/tariff_adapters.py` | each publisher's conventions — before ANY tariff work |

⚠ `HANDOFF.md`, `GAMEPLAN.md`, `PATH_TO_COMPLETE.md`, `NATIONAL_HANDOVER.md` and every
`HANDOFF_2026-08-1[78]*.md` are **HISTORY** — read them for *how*, never for *what is true now*.

**Then run this before you believe any backlog row:**

```bash
python scripts/audit_backlog_truth.py
```

It probes each open item instead of trusting its wording. It has already caught five stale rows.

---

## ⭐ THE FINDING THAT SHOULD DRIVE YOUR SESSION

The wiring census says **282 of 300 objects "reach a surface"** — but a surface counts a
provenance line nobody can click. Ask the stricter question, *can a USER OPERATE A CONTROL that
reaches it*, and the answer is:

| verdict | n |
|---|---:|
| **TOGGLE** — a control the user can operate | **38** |
| **PAGE ONLY** — reaches a filterable page, nothing names it | 79 |
| **READ-ONLY** — rendered, nothing to ask a question with | 152 |
| NO SURFACE | 20 |
| INFRASTRUCTURE — correctly not a control | 12 |

**38 of 301.** That gap is what a management review exposed on 2026-08-19, and **G72 closes it.**
`TABLE_PURPOSE_INDEX.md` names every object, its objective, and whether a control reaches it.

---

## WHAT THE LADDER HAS PROVEN — do not re-run this experiment

| comparison | new constraint keys | new facilities |
|---|---:|---:|
| withdrawal 5,000 vs 100 MW | **0** of 410,947 | **0** of 1,029 |
| injection 5,000 vs 10 MW | **443** | **0** of 1,300 |

⭐ A bigger injection request **is** a strict superset of constraint keys — but **not one new
FACILITY appears in either direction.** The monitored set is a property of the STUDY CASE, not the
request size. ⛔ **So the ladder cannot close the 146-missing-binder gap**; that gap is facilities,
and PJM parity needs a different attack.

⚠ Both tables carry ~102,000 duplicate rows (655,790 rows over 553,719 keys). Structural, not a
defect — **always dedupe on (bus, facility, contingency) before comparing anything.**

---

## ⛔ FIVE TRAPS THAT COST REAL TIME. Read these or repeat them.

1. **A `SHORT` line in the harvest log is NOT data loss.** The loader prints
   `SHORT 05JEFRSO 765 kV (243208): read 188 of 594` and loads the rows anyway. That looks exactly
   like the ECHO silent-short-page defect. It is not: every table checked clean against a
   known-good reference. Use `python scripts/audit_pjm_short_reads.py`, **never the log**.
   Stopping a healthy harvest over one of these is what created a 25-bus gap that then had to be
   repaired.
2. **Killing the ladder supervisor kills its python child a few seconds later**, even though an
   immediate check says the child survived. The supervisor holds its plan **in memory**, so
   editing `run_pjm_ladder.ps1` cannot reach a running one. To reorder the queue without losing
   work, wait for the current rung to finish.
3. **`nulls` and `rows` are BigQuery reserved words.** A probe using `COUNTIF(...) nulls` fails,
   and if your `except` swallows it every table reports as MISSING. Surface the exception.
4. **Never guess a column name.** Four cost a query each on 2026-08-19 alone: `geog` (it is
   `geom`), `asset_class` (`substation_type`), `saleDate` (`auctionDate`), and `nulls`.
5. **Backticks in `git commit -m` get eaten by the shell.** Use `-F <file>`. Standing rule.

⚠ **`data/sites/` is ~224 MB of already-gzipped files and `git push` FAILS on it**
(`SEC_E_MESSAGE_ALTERED`). If a push dies after a sites re-export, that is why — not your commit.

**The pattern behind all of them: a clean or alarming number is a claim about your INSTRUMENT
first.** Check the join, then the filter, then the data.

---

## WHAT IS OPEN — the operator's own list first

| # | item |
|---|---|
| **G70** | more about the parcel — address, coordinates, owner name, building use (USA Structures) |
| **G71** | zoning from BigQuery, if we hold it |
| **G72** | ⭐ **wire the 231 objects that reach no control.** The biggest item; the index is the worklist |
| **G73** | rewrite the dossier around OUR data, not the PDF the operator supplied as an example |
| **G74** | ⭐ any Excel in, rich Excel out, persisted across pages (resets on refresh) |
| **G75** | polish: no stale tables, professional finish |
| **G76** | the acceptance "public-data-only" check fails on the disclosures the rules REQUIRE |

⭐ **Also named by BOTH of the operator's own reference tools and missing from ours:
RADIUS-FROM-A-POINT SEARCH** — click the map or type a coordinate, set a radius in miles, screen
inside it. We hold everything it needs. See `REFERENCE_TOOL_GAP.md`.

**Open, not operator-new:** **G53** withdrawn queue as a seller signal (blocked — the address
lives in late-stage filings, test feasibility first) · **G15** future capacity (618 rows, county on
**0**; 227 IURC documents identified, public, unparsed) · **G55** 50 utilities on a URDB floor —
⛔ **their books are not published anywhere**, this is procurement, not engineering · **G20** six
real substation gaps · **G14** propagate dates we already hold · **G21** the map-layer half.

---

## THE STANDING RULES, each earned by getting it wrong

**Write boundary.** `energy-platfrom.energy` is **READ-ONLY**. Everything goes to
`energy-platfrom.indiana_app`. The one permitted write is an APPEND to `energy.registry_sources`.
**Restate this in every agent brief — agents do not inherit it.**
⚠ **Build scripts may read `energy`; EXPORTS MAY NOT.** An export is on the path to what the user
sees, so the app must be rebuildable from `indiana_app` alone. The checkpoint enforces it and
caught a violation within one run on 2026-08-19.

**Every table gets a `_registry` row in the same run**, carrying `source` AND `method` with a
verbatim `RE-SCRAPE COMMAND:` sufficient for a stranger to re-run it.

**⛔ Check the warehouse before you explore or scrape.** Enumerate `energy.__TABLES__` and
`indiana_app._registry` first. It has paid for itself seven times.

**Never quote a count from a document, including this one.** Run the checkpoint.

**Read the schema. Never guess a column name or type.** `bus_number` is a **STRING**.

**⚠ Never write a regex through a shell heredoc** — three patterns have reached disk mangled. Use
the Write tool and self-test at import.

**Unpublished is NULL, never 0.** ⚠ But a **stated** zero is not an absent value: I&M prints
`0.000 $/kW` on Tariff G.S. and that is correct (G57).

**⚠ EXCLUDE `parcels_in/080500000047000018` from EVERY spatial join** — D85, an inverted
whole-Earth polygon, live upstream. Prove the guard by measuring fan-out (~1.0, not ~2.0).

**⛔ No centroid where a footprint exists.** **Never `git add -A`** — stage explicit paths.

**After ANY front-end change:** `python scripts/stamp_assets.py` → `python scripts/audit_frontend.py`
→ verify in a browser → check `https://ahenderson0233.github.io/indiana-application-decennial/`.
⚠ **`app.js` is boot-critical and the map does NOT boot headless** (confirmed five times). Verify
by calling functions directly — `renderLayerLegend()`, `openDossier()` with a real parcel from
`data/sites/{fips}.geojson.gz`. A parse check once passed `esc is not defined`.

**Two standing self-heals exist and both fired on 2026-08-19** — `export_grid_sentiment.py`
re-runs the IOCS enricher and re-runs the border clip after it rewrites payloads. Do not remove
them; remembering an ordering rule is not a control.

---

## ⛔ DO NOT RE-LITIGATE

- **MISO parity is not publicly reachable.** DPP-2025 is CEII; four sweeps proved it. Do not
  re-probe CartoVista or giqueue, and do not buy a trial.
- **The G26 headroom method is settled** — pre-existing overloads are flagged and reported, not
  dropped. It is implemented.
- **The ladder will not surface new FACILITIES.** Measured in both directions.
- **A `SHORT` log line is not data loss.**
- **G57 was never a defect** — the publisher prints the zero.
- **Vendor data is a yardstick, never a source.** The single authorised exception is
  `in_bus_headroom_miso_vendor` (MISO only), stamped `provenance_class='vendor_licensed_proxy'`,
  disclosed in prose on every surface that uses it, licence lapsing late 2027.

---

**Start by** telling me whether the harvest is alive and what the checkpoint printed, then what you
read, then your plan — and lead with G72 unless I say otherwise.
