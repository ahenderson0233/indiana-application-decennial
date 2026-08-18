# FEATURE INVENTORY — every surface, what it does, and where its data comes from

> Operator, 2026-08-18: *"outline EVERY single feature in this tool, what it does, and how it
> works, including what datasets it is derived from within BQ (either energy or indiana_app)."*
>
> Built by reading the code and the exporters, not from memory. Regenerate the lineage half with
> `scripts/` inspection if it drifts.

## HOW DATA REACHES A SCREEN — the shape of the whole system

```
  energy.*  (READ-ONLY, another session owns it)
      |  one-time CLIPS, never re-derived here
      v
  indiana_app.*  (300 registered objects — everything we build)
      |  scripts/export_*.py and build_*.py
      v
  data/*.json.gz  and  data/*.geojson.gz   (18 payloads, gzipped, served statically)
      |  fetchGz() in common.js
      v
  8 HTML pages + the map console
```

**Three rules that explain most of the design.** ⛔ `energy` is read-only — the only permitted
write is an APPEND to `energy.registry_sources`. ⛔ **No exporter may read `energy` directly** (the
checkpoint enforces this) — otherwise the app could not be rebuilt without the platform dataset.
⛔ Every table carries a `_registry` row written in the same run, with `source`, `method` and a
verbatim re-scrape command.

⚠ **172 of 300 registered objects record `energy.*` as their SOURCE.** They are clips that live in
`indiana_app`. Do not rebuild them.

---

# 1. MAP CONSOLE — `index.html` + `app.js`

The primary surface. A MapLibre map over 92 county parcel files, with layers, filters, scoring,
an evidence panel and the printable dossier.

### 1.1 Parcel layer and the filter stack
**What it does.** Draws candidate parcels per county and filters them live on acreage, land kind,
signal state, date window, MW capability and use case.
**How it works.** Counties load **on demand** above zoom 10 from `data/sites/{fips}.geojson.gz`
(92 files) — never all at once. `applyFilters()` re-evaluates every loaded county.
**Data.** `indiana_app.in_sites` (3.55M parcels) joined to `in_sites_county`, `in_site_gates`,
`in_si_sites_flags_v2`, `in_asset_distance_parcel`, `in_water_distance_parcel` by
`scripts/export_sites_exact.py`.

### 1.2 Layer registry and presets
**What it does.** 18 toggleable layers grouped by theme, plus four presets (Land, Grid,
Environmental, Sentiment).
**How it works.** ⭐ **One registry** — `ALL_LAYER_BOXES` — and one `syncLayers()` path. Every
preset must state every layer; `PRESET_GAPS` console-errors at boot if one does not. Unstated means
OFF, never "leave it as it was" (**G34** — that bug left wind and solar drawing after a preset
switch).
**Data.** `grid.geojson.gz` (substations, lines, bus POIs), `overlays.geojson.gz`,
`context.geojson.gz`, `water.geojson.gz`, `logistics.geojson.gz`, `pjm.geojson.gz`,
`territories.geojson.gz`, `facilities.geojson.gz`, `gas.geojson.gz`.

### 1.3 Bus / connection-point layer ⭐ REBUILT 2026-08-18
**What it does.** Every grid connection point with its **binding headroom**, sized by capacity,
amber where an owner signal exists.
**How it works.** One binding figure per bus per direction — the tightest facility with
`|shift factor| ≥ 0.05` that is **not already over its rating**. Only the **withdrawal** direction
draws by default (a data centre asks the load question). ⛔ The old worst/median/best triple is
gone: three rival numbers let a reader pick the flattering one.
**Data.** `indiana_app.in_bus_capacity_tier0` → `grid.geojson.gz` via
`scripts/export_grid_sentiment.py`. That table is built by
`scripts/build_bus_capacity_tier0_v2.py` from **PJM** `in_pjm_qs_c23sens_wd` / `_inj` (our own
QueueScope harvest, case 23) and **MISO** `in_bus_headroom_miso_vendor` (⚠ licensed Orennia
DPP-2025 proxy, `provenance_class='vendor_licensed_proxy'`, licence lapses late 2027).

### 1.4 Site scoring
**What it does.** Composite score over six weighted parts, weights user-adjustable.
**How it works.** ⭐ A part we cannot measure is **excluded from the denominator**, never scored
zero — so a data gap never masquerades as a bad site. `scoreSite()` in `app.js`.
**Data.** the parcel payload's own columns; no separate table.

### 1.5 Evidence panel
**What it does.** Click any parcel, substation, bus, water body or queue point for a sourced panel.
**How it works.** `row(k, v, absent)` has **three** states (**G51**): a value, measured-empty, and
not-measurable. Never let silence become a claim.
**Data.** whichever payload the clicked feature came from; `prov()` prints the table, row count and
build date from `state_summary.json`.

### 1.6 ⭐ The Power Plan dossier
**What it does.** A four-page printable pack for one parcel: verdict, takeaways, next steps,
stakeholders, parcel diagram, path-to-power, interconnection checklist, evidence, scoring, and a
meeting appendix. **The only artefact a developer physically carries to a utility.**
**How it works.** `renderPowerPlan()` in `app.js`. Figure 2 draws the parcel from its **own
polygon**, to scale, with a scale bar. ⭐ The serving utility is resolved from the **parcel
footprint** (up to 64 ring vertices), not a point, and a parcel straddling two territories is
**reported as straddling** rather than assigned to one (**D-11**).
**Data.** `tariffs.json.gz` (rates), `gridsiting.json.gz` (buses), `territories.geojson.gz`,
`county_context.json`, the county parcel file. Cites `in_sites`, `in_si_sites_flags_v2`,
`in_site_gates`, `in_si_d22_echo_indiana`, `in_territories`, `in_bus_capacity_tier0`, `in_queue`,
`in_dc_actions_resolved`, `in_utility_tariff_riders`, `in_urdb_rates`.

### 1.7 Deep link and parcel highlight ⭐ NEW (G39)
**What it does.** `index.html?fips=18163&parcel=…[&open=dossier]` loads that county, fits the
parcel's polygon bounds and highlights it in amber.
**How it works.** ⚠ Counties load on demand, so the link must **drive** that machinery —
`ensureCountyLoaded()` fetches the county itself. Data and presentation fail separately: a map-layer
error no longer loses the parcel.

### 1.8 Screener layer on the map ⭐ NEW (G39)
**What it does.** The ranked shortlist, drawn geographically.
**How it works.** Lazy-loaded on first toggle (3.7 MB). ⚠ **20,040 of 51,493 sites (38.9%) carry a
lat/lon** and the control says so.
**Data.** `screener.json.gz`.

### 1.9 Measure tool, shortlist, workspaces, CSV export, upload-your-own-sites
**What they do.** Distance measuring; star parcels to a shortlist; save named workspaces
(screener + weights + layers); export the current view; score your own uploaded sites through the
same pipeline.
**Data.** browser local state; upload is scored client-side against the same payloads.

---

# 2. SITE SCREENER — `screener.html`

### 2.1 Ranked site table
**What it does.** Ranks 51,493 candidate sites on county, acreage, MW fit, grid headroom, distance
and owner signal.
**How it works.** Filters compose across class, MW, signal, date and grid; sortable columns;
first 500 rendered with the cap **stated on the page**.
**Data.** `screener.json.gz` from `indiana_app.in_screener_candidates` (532,868 rows).

### 2.2 ⭐ Per-site depth (expandable row) — NEW (G39)
**What it does.** Every row expands into four sections: getting power, sending power, the land,
owner motivation and what could stop you.
**How it works.** ⭐ Pure **rendering** — nothing new is fetched. The payload already carried the
injection side on 97.7% of sites, the owner-signal block on 47.1%, tax-credit zones on 22,819.
Every field states **what it changes**, not what it is.
**Data.** the same `screener.json.gz`.

### 2.3 Links out to the map and the dossier
**What they do.** "Show this site on the map" and "Open the full Power Plan dossier".
**How it works.** ⛔ The dossier is **not** duplicated here — it needs the parcel geometry and the
console's state, and a second copy would drift. The dropdown links to it.

---

# 3. MARKET & RATES — `market.html`

### 3.1 Statewide demand, CEMS generation, delivered fuel cost
**Data.** `market.json.gz` ← `in_ferc714_demand`, `in_cems_monthly`,
`in_eia923_fuel_receipts_costs`.

### 3.2 Utility reliability (SAIDI/SAIFI)
**What it does.** Minutes off per year per utility, translated into hours.
**Data.** `market.json.gz` ← `in_eia861_reliability`.

### 3.3 Gas — design capacity, operationally-available capacity, Indiana locations
**What it does.** Whether on-site generation is feasible: pipe size, then what is actually unsold.
**How it works.** ⚠ The MW column is an **estimate we derive**, badged as such; the unit is
**inferred** (dekatherms/day) because the capture kept no units column, and the page says so.
**Data.** `gas.geojson.gz`, `gas_locations.json.gz` ← `in_gas_state_capacity`,
`in_gas_capacity_*`, `in_gas_pipelines` (clipped from `energy.gas_pipelines_hifld`).

### 3.4 Yearly cost proxy (URDB cross-check)
**What it does.** Ranks utilities on a flattened first-pass bill.
**How it works.** ⭐ **No silent cap.** It used to sort cheapest-first then `.slice(0,14)` — 432
qualifying rows across 35 utilities, 14 shown. Now one row per utility, all 35, with the 18 rates
excluded for having no demand charge **counted on the page**.
**Data.** `market.json.gz` ← `in_urdb_rates` (969 rows).

### 3.5 ⭐ THE RATE ENGINE — itemised tariffs
**What it does.** Prices every rate schedule at every service voltage, with **all applicable
riders folded in**, to an annual spend and an effective ¢/kWh, checked against what that utility's
industrial customers actually pay.
**How it works.** Per-utility **adapters** (`scripts/tariff_adapters.py`) declare each publisher's
conventions; the arithmetic is shared in `common.js` so the Market page and the dossier use **one**
engine. Block ladders are alternatives across slices; TOU splits by the tariff's own period hours;
reactive and optional-service charges are excluded, counted and disclosed; **a row missing a whole
billing leg refuses to show a rate**. Eligibility has a ceiling as well as a floor.
**Coverage.** 22 utilities costed from their own books; 50 more carry a **labelled URDB floor**
(`≥` prefix) because we hold no book.
**Data.** `tariffs.json.gz` ← `in_utility_tariff_riders` (668 components / 73 utilities),
`in_urdb_rates`, `in_eia861_sales` (the benchmark), and the enumerated map in
`scripts/utility_names.py`.

### 3.6 Demand response, EQR filers
**Data.** `context.json.gz` ← `in_eia861_demand_response`, `in_eqr_identity`.

---

# 4. GRID & CAPACITY — `grid.html`

| card | what it shows | data |
|---|---|---|
| PJM / I&M load headroom | per-bus load headroom, binding facility, pre-overloads | `in_bus_capacity_tier0` (PJM half, **ours**, case 23) |
| MISO POIs | ⭐ both directions, DPP-2025 | `in_bus_capacity_tier0` (MISO half, **licensed**) |
| Future capacity | TDSIC/IRP plans + RTO expansion | `in_grid_plans`, `in_rto_expansion` |
| RTEP upgrade drill-down | per-upgrade cost allocations | `in_rtep_bus_join`, `in_rtep_bus_summary` |
| Interconnection queue | county grain, **includes withdrawn** | `in_queue`, `in_queue_counties` |
| Generating fleet | what is on the system | `in_eia860_generators`, `in_eia860m_generators` |
| Announced retirements | capacity leaving | `in_eia860m_generators` |
| MISO study-cycle detail | where each Indiana project sits | `in_miso_dpp2025_ph1_project_costs` |

---

# 5. OWNER SIGNALS — `si.html`

25 cards covering which owners might sell and how strongly we believe it: per-signal coverage,
owner-grain signals that cannot reach a parcel (D11/D27/D19), IDEM enforcement, D22 environmental
compliance, D16 structure fires, vacancy tracts, SBA lending, the Evansville land bank, Marion
placement checked by two instruments, and a full source list with real freshness.
**Data.** `si_v2.json.gz`, `si_sources.json.gz`, `signoff.json.gz` ← `in_si_owner_signals`,
`in_si_d22_echo_indiana`, `in_si_d22_idem_dated`, `in_si_d5_*`, `in_si_d9_absentee_marion`,
`in_si_evansville_landbank`, `in_si_lane_d_enrichment`, `in_si_signal_coverage`,
`in_si_d11_admitted`, `in_si_d25_admitted`, `in_si_d27_admitted`, `in_acs_tract_vacancy`,
`in_sba_foia_loans`.

---

# 6. COMMUNITY & LOCAL RULES — `community.html`

Receipts browser, county posture, county data-centre actions (**the layer no code library
carries**), codified ordinances, the Indiana legislature bill tracker, federal disaster
declarations, NOAA storm events, and county court activity.
**Data.** `receipts.json.gz`, `ordinances.json.gz`, `legislature.json.gz`, `county_context.json`
← `in_dc_actions`, `in_dc_actions_resolved`, `in_ordinances_dc_v2`, `in_openstates_energy_bills_v2`
(+7 sibling tables), `in_fema_disaster_declarations`, `in_storm_events`, `in_iocs_county_context`.

⚠ **Ordering hazard, now self-healing (G64):** `export_grid_sentiment.py` rewrites
`county_context.json` and drops the IOCS block that `export_signoff_payloads.py` adds. It now
detects and repairs that itself.

---

# 7. INSIGHTS — `insights.html`

Plain-language orientation: the short version, the biggest single gap stated plainly, where the
opportunity sits, most usable land, most motivated owners, and **what this tool cannot tell you**.
**Data.** `screener.json.gz`, `gridsiting.json.gz`.

# 8. DATA & METHODS — `data.html`

Provenance, coverage, the estate census, and the waivers.
**Data.** `state_summary.json` (provenance for 300 tables), `estate_census.json.gz`.

---

# 9. THE GUARDRAILS (they are features)

| guard | what it catches | where |
|---|---|---|
| `checkpoint.py` | the whole state; exits non-zero on drift | 13 honesty checks, 5 D85 guards, payload/warehouse agreement, payload freshness, required keys |
| `audit_frontend.py` | dead element ids, payload keys read but never written, surfaces on superseded tables | 6 pages |
| `audit_tariff_costing.py` ⭐ | zero legs, structural published 0.0, NULLs that bill, riders that exist but are not held, rider-stack outliers, alternatives summed | 73 utilities |
| `tariff_fingerprint.py` ⭐ | which publishers moved after a change — proves per-utility isolation | 73 utilities |
| `audit_honesty.py` | unregistered tables, provenance completeness | `indiana_app` |
| D85 guard | one parcel is an inverted whole-Earth polygon; excluded from every spatial join | 5 tables |

---

# 10. WHAT THE TOOL DELIBERATELY DOES NOT DO

- **No LLM feature** — §13(5) needs an AI docket summary and this app has none.
- **No MISO load-side public source** — four sweeps found none; the licensed proxy fills it and
  says so.
- **No price for land, no owner name, no guarantee of power** — stated in the dossier's footer.
- **No centroid in distance maths** — acreage, asset distances and service territory all measure
  against the polygon. The one exception (bus distance, because buses *are* points) is named.
