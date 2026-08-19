# NEXT SESSION — paste everything below this line as your first message

Continue the Indiana siting-intelligence application.
Repo: `C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial`
(GitHub `ahenderson0233/indiana-application-decennial`, branch `main`)

---

## ⛔ FIRST, IN THIS ORDER. Propose nothing before you have.

### 1. Is the harvest alive?

```bash
powershell -NoProfile -Command "@(Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | Where-Object { $_.CommandLine -like '*pull_pjm*' }).Count"
```

**A 26-rung PJM ladder is running.** If that returns `0` and rungs remain, resume — this is the
only command needed and it is safe to run even if one IS going, because it polls for the ABSENCE
of a QueueScope process:

```bash
powershell -ExecutionPolicy Bypass -File scripts\run_pjm_ladder.ps1
```

State at handover: **5,000 MW INJECTION, ~53 of 74 batches.** 5,000 MW withdrawal is complete and
registered. Queued: **10/15/25/50/100/200/300/500/1000/1500/2000/3000 MW, both directions** (the
operator's list). 100 MW auto-skips — already held as `in_pjm_qs_c23sens_{wd,inj}`.

⛔ **Never a second QueueScope process.** ⛔ **Never delete `data/`** — archive. ⛔ **Owner 1568,
not 739** (739 loads 0 rows and exits *successfully*).

### ⭐ Two things that will otherwise cost you hours

**The ladder probably will not close parity, and that is measured.** 5,000 MW vs 100 MW, same case
and direction: **1,029 facilities vs 1,029, 410,947 constraint keys vs 410,947, ZERO only at
5,000 MW.** The monitored set is a property of the STUDY CASE, not the request size. It is queued
because the operator asked; do not expect it to surface the 146 missing vendor binders.

**`SHORT ... read 176 of 588` in the harvest log is NOT data loss.** I believed it was and stopped
the harvest unnecessarily. `python scripts/audit_pjm_short_reads.py` compares every bus against the
complete 100 MW reference — both tables are clean. **Run that before believing the log.**

### 2. Checkpoint

```bash
python scripts/checkpoint.py
```

**Expect exactly 3 failures:** wiring census (~286 of 300, standing), honesty audit 1 failure, and
1 unregistered table — **which IS the running harvest.** ⛔ Anything else is real, especially
`shipped payload agrees with the warehouse`, the five D85 guards, and **`no EXPORT reads energy
directly`** (that one caught a live regression yesterday).

### 3. Read, in this order

| # | file | what it is |
|---|---|---|
| 1 | `docs/SESSION_START.md` | standing rules, the governing principle |
| 2 | ⭐ **`docs/HANDOFF_2026-08-19.md`** | **THE CURRENT ONE.** Everything below in full detail |
| 3 | ⭐ **`docs/TABLE_PURPOSE_INDEX.md`** | **generated.** All 301 objects → purpose → the control that exposes it. **This is G72's worklist** |
| 4 | `docs/REFERENCE_TOOL_GAP.md` | our screening vs the operator's own two tools |
| 5 | `docs/BACKLOG.md` | the **⚠ IN FLIGHT** row first, then the G-index |
| 6 | `docs/FEATURE_INVENTORY.md` | every feature and its BigQuery table |

⚠ Everything else in `docs/` is HISTORY. Read it for *how*, never for *what is true now*.

---

## ⭐ THE FINDING THAT SHOULD SHAPE YOUR WORK

The operator was burned in a management review: **data exists that has no control, so it does not
exist to the person in the room.** `TABLE_PURPOSE_INDEX.md` measured it across all 301 objects:

| verdict | n |
|---|---:|
| **TOGGLE** — the user can operate a control that reaches it | **38** |
| **PAGE ONLY** — reaches a filterable page, no control names it | **79** |
| **READ-ONLY** — rendered, nothing you can ask a question with | **152** |
| NO SURFACE | 20 |
| INFRASTRUCTURE — correctly not a control | 12 |

The wiring census says **286 of 300 "reach a surface"**. Both are true — a surface counts a
provenance line nobody can click. **231 objects are the gap, and that is G72.**

---

## THE OPERATOR'S SIX REMAINING ITEMS — G70 to G75

Ten were ordered on 2026-08-19; four shipped (**#1** basemap, **#5** free MW entry, **#7** signal
checkboxes, **#10** map clicks). These six remain, in the order I would do them:

| # | item | the one thing to know |
|---|---|---|
| **G72** | **Wire the datasets we hold and do not show** | ⭐ **Biggest, and the worklist is already generated.** Work by OBJECTIVE using the index, not alphabetically. Both tables the operator named — `in_land_military_bases` (13) and `in_tribal_land` — are clipped and unshown. ⚠ G21 binds each one: a layer without its "so what" is volume standing in for value |
| **G70** | **More about the parcel** — address, coordinates, building use | ⭐ `nat_usa_structures` holds **3,377,472 Indiana rows**, is the largest genuinely-unwired object we hold, and carries occupancy class — the "building use" asked for. Join on `build_id`. ⛔ **Do NOT promise owner name or email:** `parcel_owner` is NULL on all 3,553,381 parcels; the only owner data is Marion's (340,765, from the county's own crosswalk) |
| **G74** | **Any Excel in, rich Excel out, persisted across pages** | `sessionStorage` is exactly the requested semantics — survives navigation, clears on refresh. Vendor SheetJS (this repo vendors, see `vendor/`). ⚠ "ANY sheet" means column mapping cannot be hardcoded: detect the header, let the user map to lat/lon or address, and **keep failing rows labelled** — §13(2) was closed on that behaviour |
| **G73** | **Rewrite the dossier around OUR data** | It currently follows a PDF the operator supplied only as an example. What we hold that the borrowed format has no room for: the **priced tariff at this parcel's own utility**, 25 owner-motivation signals with dates and keying, county posture with receipts, exact distances, the buildable-area basis. ⛔ Verify by RENDERING — a parse check once passed `esc is not defined` |
| **G71** | **Zoning from BQ** | ⚠ Two different things wear this name. The ordinance corpus answers *does this county permit a data centre*; parcel-grain zoning is metro-only (`agis_*`). Probably two surfaces, clearly labelled. Do not blend them |
| **G75** | **Polish; no stale tables** | Run the instruments first: `audit_backlog_truth.py`, `audit_wiring_census.py`, `audit_frontend.py`, `sync_layer_counts.py --check`, `audit_map_clicks.py`. Retire what is stale, *then* make what remains legible |

Also open and small: **G76** — the acceptance run's "public-data-only" criterion fails on the
Orennia **disclosures G50 requires**, so it is permanently red and a genuine leak would look
identical. Fix it to test for vendor VALUES, not the vendor's name in prose.

---

## THE BACKLOG, AS IT ACTUALLY STANDS

**46 DONE · 17 OPEN · 15 PARTIAL.** Ten items closed on 2026-08-19 and every row's state was
re-synced to what shipped, so the index can be trusted today.

**Open beyond the six above:** G53 withdrawn-queue signal (blocked on recovering an address from
late-stage filings) · G46 own placement methodology · G45 the MW ladder · G40 PJM grain parity
(owned by the parallel session) · G6 polish · G11 sentiment vocabulary diff · G15 future capacity
(618 rows, county on **0**; 227 IURC documents identified and public) · G17/G18 · G30b repo pack.

**Partial, and the interesting ones:** **G61** capacity derivation solved (ratio 0.136 → **1.010**),
binding-facility *selection* open — 146 of 298 vendor binders absent from our harvest · **G62**
placement proven at **0.03 mi median**, blocked on the substation gazetteer (MODOC, FOWLER,
STUDEBAKER, BOUNDARY, ADAMS missing) · **G55** 21 of 22 priced utilities now have an adapter; the
50 URDB-floor utilities need books that **are not published** · **G21** measured at **45** `.sowhat`
blocks, not the 4 the row claimed — what remains is the map layers · **G14** reframed: the D4 source
is **fully dated**, so it is a propagation loss, not a re-scrape · **G20** 526 taps and dead ends
are already typed, so half that row may be moot.

---

## ⛔ THE RULES, AND THE FAILURE THAT EARNED EACH

**Write boundary.** `energy` is READ-ONLY; the one permitted write is an APPEND to
`energy.registry_sources`. **Builds may read `energy`; EXPORTS MAY NOT** — an export is on the path
to the user, so the app must rebuild from `indiana_app` alone. This caught a live regression on
2026-08-19.

**Every table gets a `_registry` row in the same run**, with `source`, `method`, and a verbatim
`RE-SCRAPE COMMAND:`.

**⛔ Check the warehouse before you explore or scrape.** It has paid for itself seven times.

**Never quote a count from a document, including this one.** Run the checkpoint.

**Read the schema. Never guess a column name or type.** Four guesses cost four dead queries in one
session: `geog` (it is `geom`), `asset_class` (`substation_type`), `saleDate` (`auctionDate`), and a
signal that has no rows in the table probed — which returned "0 of 0" and read as DONE.

**⚠ Never write a regex through a shell heredoc.** Three reached disk mangled. Use the Write tool.

**Use a commit-message FILE.** Backticks in `-m` get eaten by the shell.

**⭐ `git config http.sslBackend openssl`** — the 224 MB `data/sites` push uploads fully and then
fails with a Windows schannel `SEC_E_MESSAGE_ALTERED`. OpenSSL fixes it.

**Unpublished is NULL, never 0** — but a **STATED** zero is not an absent value (G57: I&M's book
literally prints `0.000`).

**⚠ Exclude `parcels_in/080500000047000018`** from every spatial join — D85, an inverted
whole-Earth polygon, live upstream.

**⛔ No centroid where a footprint exists.** The one exception — bus distance, because buses *are*
points — is named on the page.

**After ANY front-end change:** `stamp_assets.py` → `audit_frontend.py` → **render it in a
browser** → check the deployed site. ⚠ `app.js` is boot-critical and **the map does not boot
headless** (confirmed five times). Verify by calling functions directly — that is how four defects
were caught on 2026-08-19.

**The standing checks:** `checkpoint.py` · `audit_backlog_truth.py` · `audit_map_clicks.py` ·
`audit_pjm_short_reads.py` · `sync_layer_counts.py` · `build_table_purpose_index.py` ·
`audit_frontend.py` · `tariff_fingerprint.py` · `audit_tariff_costing.py`.

---

## DO NOT RE-LITIGATE

- **MISO parity is not publicly reachable.** DPP-2025 is CEII; four sweeps proved it.
- **The 5,000 MW rung surfaced nothing new** — 0 facilities, 0 keys, measured.
- **G57 was never a defect** — the publisher prints the zero.
- **The screener already had five sections**; an earlier claim that it had none counted `<h2>` and
  missed `<summary>`.
- **G50 and G8 are closed** — probed, not assumed.

---

**Start by** telling me whether the harvest is alive and what the checkpoint printed, then what you
read, then your plan — and lead with **G72**, because the index is already its worklist.
