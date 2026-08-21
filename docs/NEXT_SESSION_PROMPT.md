# NEXT SESSION — paste everything below this line as your first message

Continue the Indiana siting-intelligence application.
Repo: `C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial`
(GitHub `ahenderson0233/indiana-application-decennial`, branch `main`)

---

## ⛔ DO THESE FOUR THINGS FIRST. Propose nothing before you have.

### 1. Is the PJM harvest alive?

```bash
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | Where-Object { $_.CommandLine -like '*pull_pjm*' } | ForEach-Object { 'PID ' + $_.ProcessId + ' :: ' + $_.CommandLine }"
```

⚠ **A count of 2 is almost always your own command self-matching.** Confirm by parentage.

**If nothing is running, resume. This one command resumes, continues AND repairs, and is safe to
run even while one is going** — it polls for the ABSENCE of a QueueScope process:

```bash
powershell -ExecutionPolicy Bypass -File scripts\run_pjm_ladder.ps1
```

⛔ **NEVER start a second QueueScope process.** ⛔ **NEVER delete `data/`** — the batch markers live
there and deleting them forces a duplicating re-harvest; **archive, never delete**. ⛔ **Owner is
1568, not 739** — 739 loads **0 rows and exits successfully**.

⛔ **DO NOT TRUST ANY RUNG LIST IN A DOCUMENT — MEASURE IT.** The ladder advanced four times during
the last session and its PID changed with it. `python scripts/audit_handoff_docs.py` prints the
live complete/short split.

### 2. Start a web server, or every page hangs

```bash
python -m http.server 8123 --directory "C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
```

⚠ A dead server looks exactly like a code bug. ⚠ **And hard-reload with a cache-busting query** — a
stale page served an old `common.js` last session and brand-new code was "missing" for three probes.

### 3. The checkpoint and the ledger audits

```bash
python scripts/checkpoint.py
python scripts/audit_backlog_state.py
python scripts/audit_backlog_truth.py
python scripts/audit_handoff_docs.py
python scripts/audit_handoff_consistency.py
```

**Expect 3 checkpoint failures and expect all three to be correct:** the **wiring census** (⭐ the
END STATE, not a gap — every unreached object carries a measured reason and the worklist is 0; the
durable check is `0 unclassified`), the **honesty audit's 1 known failure**, and **unregistered
ladder rungs** the running harvest created since the last registration pass.

⭐ **`signal display` was a fourth expected failure and it now PASSES.** All 25 SI signals either
place what they hold or carry a written reason. ⛔ Do not let it go quiet again: it exists because
`in_si_signal_coverage` held these numbers for weeks while nothing failed on them, which is why the
operator reported the problem twice and saw no change.

### 4. Read, in this order

| # | file | why |
|---|---|---|
| 1 | `docs/SESSION_START.md` | standing rules and the governing principle |
| 2 | ⭐ **`docs/HANDOFF_2026-08-21b.md`** | **THE CURRENT ONE.** §1 is the unfinished work; §3 every parcel figure that moved; §4 the instrument failures |
| 3 | ⭐ **`docs/BACKLOG.md`** | **WHERE EVERY UNFINISHED ROW STANDS** opens with G130 and the seven things left in it |
| 4 | ⭐ `docs/COMPARABLE_TOOLS.md` | what this product should look like; §3 names the ONE question each page answers |
| 5 | ⭐ `docs/RESCRAPE_LEDGER.md` | **generated** — which loaders re-run, how often, safely, and what each clip drops |
| 6 | `docs/UNWIRED_CLASSIFICATION.md` | **generated** — why each unreached object is unreached |

⚠ `HANDOFF_2026-08-20d.md` and earlier are **HISTORY**. Read them for *how*, never for *what is true
now* — §3 of the current handoff lists the figures they get wrong.

---

## ⛔ START HERE — WE READ A 13-COLUMN REDUCTION OF THE SI SOURCES (G152)

**Operator, 2026-08-21:** *"we have 31 SI signals, and I guarantee that they live in more than
eight sources, so this should be checked and audited for completeness."*

⛔ **THEY WERE RIGHT AND THE PREVIOUS SESSION'S ANSWER WAS WRONG.** `audit_si_column_capture.py`
compared **8 sources**, found 0 gaps, and that was reported as *"yes, full column capture"*. It is
true of those 8 and it is not the answer to the question.

⭐ **THE GAP IS A SHAPE, NOT A COUNT. Measured:**
- `in_si_signals` draws on **19 distinct upstream `source_id`s**.
- Its parent `energy.si_signals` is **97,240,585 rows NORMALISED TO 13 COLUMNS**.
- Our clip is complete — 13 of 13 — **so the audit passed, on a reduction.**
- ⭐ The full-width upstreams are reachable: `energy.gov_surplus_frpp` (307,919),
  `energy.edgar_abs_ee_cmbs` (1,091,881), `energy.brownfield_epa_repowering` (190,976),
  `energy.acs_tract_vacancy` (85,382), five years of `energy.nfirs_*` at ~2.4M each — **39 upstream
  tables visible in `energy`**.

⛔ **THIS IS ALSO WHY WE DERIVE ONE SIGNAL PER SOURCE.** A source reduced to a date and a flag can
produce exactly one signal by construction. The operator's question — *"did you find any additional
signals beyond the ones you were searching for"* — cannot be answered until the clip is wider.

⚠ `energy` is READ-ONLY. The move is a **wider clip into `indiana_app`**, never an edit upstream.
⚠ Do it source by source with a measured "what does this add" per table. `energy.si_signals` is
97M rows; a naive full clip is not the plan.

### THEN, IN THIS ORDER — agreed with the operator, deferred from the last session

| # | row | why it is next |
|---|---|---|
| 1 | **G145** | *"date unknown"* is printed while a date IS known, and only first/last is shown. ⛔ A false statement about our own holdings outranks new capability |
| 2 | **`D22_facility_inactive`** | the last signal with no corpus count, so its loss cannot be computed |
| 3 | **G154** | the 34 unplaced WARN addresses — geocode and spatially join, do not write more regex |
| 4 | **G153** | show the user the source per signal. A real user asked for it and every field needed is already held |
| 5 | **G140's non-SI half** | 74 objects the ledger marks `unknown` idempotency |

---

---

## ⭐ THE COMPLETE SI-SIGNAL CLOSEOUT PLAN — every remaining task, in order, with the method

**Operator, 2026-08-21:** *"what are the immediate next steps (and ALL steps required to close out
ALL SI signal tasks)? You should also provide the methodologies needed to complete these tasks
effectively."*

⛔ **THE ONE RULE THAT GOVERNS ALL SIX.** `build_si_signal_v2.py` is the SPINE — it writes
`in_si_parcel_signals_v2`, `in_si_sites_flags_v2` and `in_si_signal_coverage`, and the map payload,
the screener, si.html and the county rollups all read those three. **A signal that does not enter
the spine reaches nobody.** Every task below ends with: rebuild the spine → re-export sites →
rebuild + re-export the screener → re-export si surfaces → `audit_signal_display.py` → verify in a
browser.

---

### ① G145 — "DATE UNKNOWN" IS PRINTED WHILE A DATE IS KNOWN. ⛔ DO THIS FIRST

Operator: *"it records the observation as date unknown, when one of the dates is actually known —
the correct display is seen in the dropdown, but the user shouldn't have to further explore to
actually see if our presentation is factually correct. Additionally, we should show the date of
every signal event, not just the first/last."*

⛔ **This outranks everything else here, including G152, because it is not a gap — it is a FALSE
STATEMENT about data we already hold, on the row the reader is looking at.**

**Method.**
1. **Find the decision, do not guess it.** `signalState()` in `screener.html` and its `badge()`
   helper decide "date unknown". Read both before editing anything.
2. **Diagnose against the artefact.** The suspected cause: `in_si_sites_flags_v2.si_last_event_date`
   is `MAX(IF(si_admitted, last_past_event_date, NULL))`, so a parcel whose admitted signal is
   undated reads unknown even when a SECOND admitted signal on the same parcel carries a date.
   ⚠ Prove that with a query naming a specific parcel before changing a line. If the real cause is
   different, the fix above is wrong and will look like it worked.
3. **Ship every event date, not a rollup.** `in_si_parcel_signals_v2` already holds
   `first_event_date`, `last_past_event_date`, `n_events` and `n_events_dated` PER SIGNAL.
   Aggregate to an ARRAY on the flag table — `ARRAY_AGG(STRUCT(signal, first_event_date,
   last_past_event_date, n_events, n_events_dated))` — and render one line per signal.
4. ⚠ **Three-state, per signal (G51).** A signal with no date is *"the publisher does not date this
   record"*, never *"date unknown"* — the second blames us for the publisher's silence.
   `date_basis` already records which; use it rather than inventing a new test.
5. Verify on a parcel carrying two signals where exactly one is dated. That is the failing case, so
   it is the one that proves the fix.

---

### ② `D22_facility_inactive` — THE LAST SIGNAL WITH NO DENOMINATOR

**Method.** It is DERIVED from the ECHO status vocabulary rather than loaded from a table of its
own, which is why `pub_corpus` in `build_si_signal_v2.py` carries no entry for it. Add one: count
the rows in `in_si_d22_parcel_join` carrying the INACTIVE marker, exactly as
`D22_environmental_violation` already counts the violation marker beside it.
⚠ **Do not attribute the whole 34,116-row table to both signals.** That is the mistake that forced
a per-signal `GROUP BY` on `in_si_indy_code_placed`, and `reached > held` is how it announces
itself. After this, `audit_signal_display.py` reaches 0 unmeasurable signals.

---

### ③ G152 — WE READ A 13-COLUMN REDUCTION. ⭐ THE BIGGEST ROW

**Method — source by source, never a blanket clip.**
1. **Map all 19.** For each `source_id` in `in_si_signals`, find its full-width table in `energy`.
   Some are obvious (`gov_surplus_frpp`, `edgar_abs_ee_cmbs`, `acs_tract_vacancy`); the rest need a
   `__TABLES__` probe. ⛔ Standing rule G25: enumerate what we hold before proposing anything.
2. **Measure the prize per source, not the row count.** For each: how many columns beyond the 13,
   and *what could a siter do with them*. A 1.09M-row CMBS table whose extra columns are internal
   identifiers is worth less than a 932-row table carrying an operator name and a closure date.
   ⭐ Rank by decision value and write the "so what" BEFORE the clip — the governing principle is a
   veto on new work, not a polish step.
3. **Clip Indiana-only, full width, into `indiana_app`, registered in the same run** with a verbatim
   `RE-SCRAPE COMMAND:`. ⚠ `energy.si_signals` is 97,240,585 rows — filter at the clip, never after.
   ⛔ `energy` is READ-ONLY; the move is a wider clip, never an edit upstream.
4. ⭐ **Then ask the question that motivated this row: does the wider table support a SECOND
   signal?** Operator: *"this is common, and we can generally derive multiple signals from one
   source."* A closure date and an operator name is one signal; add a lease-expiry column and it is
   two. Propose each with its own D-code, admission rule and "so what".
5. **Fold into the spine as a new source block**, exactly as `w_warn` was, then run the full
   re-export chain above.
6. ⛔ Cost-flag anything above $25–50 before running it.

---

### ④ G154 — THE 34 UNPLACED WARN ADDRESSES

**Method.** ⛔ **Stop matching strings.** The cause is not spelling: the DLGF address is the
assessor's address for a LOT, and a medical campus or distribution park has none per building —
Ascension's `2415A Mitchell Road` and `2512 Q Street` are suites on one parcel.
1. **Geocode the recovered address to a coordinate.** The US Census Geocoder
   (`geocoding.geo.census.gov`) is public, free, needs no key and supports batch — the same class
   of public bulk endpoint as the TIGER loaders already in this repo. ⚠ Check its terms before the
   first call and record the answer either way; BLOCKED-with-the-wall-quoted is a success.
2. **`ST_INTERSECTS` the point against `in_sites.parcel_geog`**, excluding D85, exactly as
   `in_si_gov_surplus_v2` already does. Assert fan-out ≈ 1.0.
3. ⚠ **Grade the match and refuse the weak ones.** A rooftop geocode inside a polygon is a match; a
   ZIP-centroid geocode is not, and placing it would be a pin someone plans around. The geocoder
   returns its own match quality — carry it, never average it away.
4. Expect this to recover most of the 34, not all. Report the residue with its reason.

---

### ⑤ G153 — SHOW THE USER WHERE EACH SIGNAL CAME FROM

Operator, relaying a real user: *"provide documentation of the SI signals… a link to the source or
document within the filings so that the user can double-check the validity themselves."*

**Method.** ⭐ **Nothing needs acquiring — every field is already held and none of it reaches a
surface.**
1. `in_si_parcel_signals_v2` carries `source_ids`, `keying_methods`, `bridge_methods` and
   `date_basis`, per parcel per signal.
2. `in_si_warn_addresses` carries the actual `notice_pdf_url`; `in_si_warn_page` carries the
   publisher's link for every notice.
3. `_registry` carries a stable endpoint URL for every source table.
4. Build ONE resolver: `source_id` → human label + clickable URL. Render it as a per-signal
   provenance line in the dossier and in the screener detail row. ⛔ One resolver in `common.js`,
   not a copy per page — the private `INTENT_PLAIN` map this session had to delete is the warning.
5. ⚠ Where the source is a bulk file rather than a per-record page, link the DATASET and say so. A
   link that promises a filing and delivers a homepage is worse than no link.
6. ⭐ This is the accounting-tool pattern `docs/COMPARABLE_TOOLS.md` §2 already names as our
   strongest suit, applied where a reader most needs it.

---

### ⑥ G144 — MINIMUM NUMBER OF SI SIGNALS, IN THE SCREENER

**Method.** A number input, badged **GATE** (G129), counting `si_signal_types` — **signal TYPES,
not events**. ⚠ Four code violations on one parcel is ONE signal; counting events would let a
single chronically-cited address masquerade as four independent reasons to sell. `si_signal_types`
is already on the flag table and already in the screener payload, so this is a control and a
predicate, not a build.

---

### ⑦ THEN, AND ONLY THEN, CLOSE G150

G150 is *"the SI signals under-represent what we hold"*. It is closeable when every signal has a
denominator (②), nothing is silently truncated (`audit_signal_display.py` green), the widened clip
has been assessed (③), and a reader can verify a signal themselves (⑤).
⛔ **Do not close it before that.** Four rows in this project have been closed while still carrying
live work — G130 was the fourth — which is why `audit_backlog_truth.py` probes the artefact rather
than the ledger.

### STILL OUTSIDE THE SI SET, AND UNCHANGED

**G102** state surplus · **G103** water utilities · **land banks** (G133's third leg) — all three
are ACQUISITIONS we hold nothing for, confirmed by warehouse check, not assumed. ⭐ Send to an Opus
(non-Fable) agent and brief it with the write boundary, no-CAPTCHA / no-UA-spoof and
BLOCKED-is-a-success, because **agents do not inherit them**.

---

## THE BACKLOG — 102 DONE · 16 PARTIAL · 28 OPEN

⚠ **OPEN JUMPED 8 → 29 AND THAT IS NOT A REGRESSION.** The operator opened **21 new rows** on
2026-08-21 in four batches — G131–G151. Nothing reopened; the surface of the work grew.

**Eight rows closed last session** — G53, G122, G123, G124, G125, G127, G128, G129 — every one
re-verified against the artefact on 2026-08-21. Two advanced with their question answered: G126 (the
bus gazetteer ceiling). ⭐ **G130 then CLOSED on 2026-08-21** — planned upgrades shipped and verified.
⭐ **G132, G133, G134 and G138 also closed on 2026-08-21**, and G150 advanced (WARN placement 2 → 51).

### AFTER G130, in priority order

**① THE DLGF GATEWAY PURCHASE — the highest-value action left, and it is yours, not code's.**
It unblocks **G70** (parcel owner), **G71** (zoning), **G104** (assessed value) and **G90(b)** at
once. All are 100% NULL for Indiana in both our clip and the national parent, which holds 40.8M
assessed values for 43 other states. **Not a clip defect; re-clipping will not help.** ⭐ G70 has
shrunk twice — its building-use half and its address half both shipped — so only OWNER remains.

**② THE DEFERRED SCRAPES.** G102 (state surplus, likely IDOA) · G103 (water utilities, EPA SDWIS) ·
G114's remaining ~1,464 PJM bus coordinates · G15's cost re-extraction from the workpaper header
row. ⭐ **Send to an Opus (non-Fable) agent** and brief it with the write boundary, no-CAPTCHA /
no-UA-spoof and BLOCKED-is-a-success, because **agents do not inherit them**.

**③ TWO DECISIONS THAT ARE YOURS, NOT CODE'S.**
- ⚠ **G129 option (b)** — a per-filter GATE/PREFERENCE toggle instead of the fixed published
  classification. More honest and more work. Option (a) is live: 18 gates, 14 preferences, badged,
  259 near misses recovered.
- ⚠ **How aggressive should the G122 exclusion be?** 3,159 road and 1,861 rail corridors are gone.
  A further **28,187 parcels are ribbon-shaped with NO road along them** — creeks, pipeline
  easements, genuinely long narrow industrial land — and they are REPORTED, not excluded.
  ⛔ Widening the shape threshold until they disappear is how a heuristic eats its own corpus.

**④ EVERYTHING ELSE PARTIAL is honest about its remainder** — G6, G15, G21, G26, G27, G40, G45,
G46, G51, G55, G62, G90, G106, G113, G114, plus G126 and G130 above. **Seventeen rows**, and
that is the whole PARTIAL set. The backlog table says what each still needs.

⚠ **One row to look at even though the ledger calls it DONE:** `audit_backlog_truth.py` probes
**G29** and reports that transmission, substation and water distances ship exact `ST_DISTANCE`
while the **BUS distance is still computed client-side on the map console**. The ledger says
DONE, the artefact says half. Decide which is right before relying on a bus distance from the map.

---

## ⛔ SIX THINGS THAT WILL MISLEAD YOU

**① Every parcel figure moved.** Candidates **531,325** (not 532,693), flagged **23,766** (not
23,795), GRID binds **189,807**, LAND binds **72,725**, substations-on-a-parcel **1,820**. ⚠ Median
substation distance **rose** 2.08 → **2.15 mi** because the parcels removed were corridors that hug
infrastructure — a number moving the unhelpful way after a correction usually means it was real.

**② THE ADDRESS IS STATEWIDE.** Three documents said Marion-only. `energy.parcels_in` carries the
DLGF property address on **98.4% of Indiana parcels across all 92 counties**.

**③ "Ribbon parcels with a road" is 25, not 184** — and that is the fix working. The other 159 were
excluded as rights-of-way.

**④ The wiring census FAILING is correct** and is not work.

**⑤ `IS` / `M4 - Project in Service` is ALREADY BUILT** — 9,163 of 15,443 PJM RTEP rows — and is
**not** future capacity. It is off by default on the map.

**⑥ The screener carries TWO capacity figures.** `mw_dc` is LAND; `deliv_wd_mw` is GRID. Never
collapse them.

---

## ⛔ TRAPS — read §4 and §5 of the handoff in full

1. ⛔ **NEVER WRITE A REGEX THROUGH A SHELL HEREDOC. NINE occurrences, several last session.** `\n`
   became a literal newline; `\b` became literal backspace bytes inside a live JS regex; and one
   heredoc edit silently applied HALF of a two-part change. ⭐ Edit tool, module level, self-test.
2. ⛔ **BUILDS MAY READ `energy`; EXPORTS MAY NOT.** The checkpoint enforces it.
3. ⛔ **A HARDCODED VERDICT IS NOT A PROBE.** `audit_backlog_truth.py` called G53 OPEN for two
   sessions after it shipped, because that branch printed a verdict it had already decided.
4. ⛔ **AN AUDIT REGISTERED BUT NOT DISPATCHED RUNS AND REPORTS NOTHING.**
5. ⛔ **A PINNED LITERAL TURNS A MEASUREMENT INTO A CONSTANT** — an audit asserted `== 184` and
   failed when the thing it measures was correctly fixed.
6. ⛔ **A LOOKALIKE IS SOMETIMES A KEY** — `fits_mw_datacentre_at_4_per_acre` is a CSV column name;
   `circle-color` and 91 siblings are MapLibre paint properties.
7. ⛔ **REMOVE A CONTROL AND ITS REGISTRY ENTRY IN ONE CHANGE.**
8. ⚠ **A value vocabulary lies** — FRPP `state_code` is `'18'`; WARN `notice_class` is UPPER-CASE;
   `nearestBus` wants lower-case; roads use `geom`; and **PJM dates are `M/D/YYYY` while MISO's are
   ISO, in one column**.
9. ⚠ **Cumulative categories are not buckets** (Drought D0 means "D0 or worse").
10. ⚠ **A statistic true of 98% of the corpus tells a siter nothing.**

**A clean, alarming or UNCHANGED number is a claim about your INSTRUMENT first.**

---

## THE STANDING RULES

`energy-platfrom.energy` is **READ-ONLY**; everything goes to `energy-platfrom.indiana_app`. The one
permitted write is an APPEND to `energy.registry_sources`. **Restate this in every agent brief —
agents do not inherit it.** ⚠ **Builds may read `energy`; EXPORTS MAY NOT.**

**Every table gets a `_registry` row in the same run** with `source`, `method` and a verbatim
`RE-SCRAPE COMMAND:`. ⭐ `docs/RESCRAPE_LEDGER.md` also records, per object, whether re-running is
**safe** (replace_safe / append_only / unknown), how often the PUBLISHER changes, and which parent
columns the clip drops.

**⛔ Check the warehouse before you explore or scrape. Read the schema. Never guess a column name OR
A VALUE VOCABULARY.**
**Unpublished is NULL, never 0** — but a **stated** zero is a fact.
**⚠ EXCLUDE `parcels_in/080500000047000018`** from every spatial join (D85); prove it by fan-out.
**⛔ No centroid where a footprint exists.** ⚠ The G125 display coordinate is the one exception and
is quarantined: `map_lat`/`map_lon` are for the reader's eye and feed no distance.
**Never `git add -A`.** **Use a commit-message FILE.**

**After ANY front-end change:** `python scripts/stamp_assets.py` → `audit_frontend.py` →
`audit_js_duplicates.py` → `audit_page_controls.py` → `audit_spelling.py` → **hard-reload and verify
in a browser**. ⭐ The map boots headless via `scripts/boot_map_harness.js`.

---

**Start by** telling me whether the harvest is alive, what the checkpoint printed, and what the
ledger audits printed — then what you read, then your plan.
⭐ **Lead with G130** — finishing the grid upgrades — unless I say otherwise.
