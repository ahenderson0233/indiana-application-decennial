# The plan — wire first, pages second, functionality last (locked 2026-08-15)

Operator ruling: *"wiring all of the applicable datasets in BQ is a first priority… then make
pages… then work through the front-end functionality."* National/ISO/county-grain data is IN
scope at its Indiana slice — the earlier blanket waiver is superseded.

The measured surface (docs/BQ_INDIANA_CENSUS.md): **2,161 usable tables; ~65 touched.**

## Phase 1 — WIRE (current phase)

1. **Verify-and-clip sweep, class B (666 state-keyed tables).** One cheap
   `SELECT COUNT(*) WHERE state-col = IN` per table (scripted, batched via UNNEST — a few
   dollars total). Everything with Indiana rows gets clipped into `indiana_app` and
   registered. Value-read before wiring anything into a feature (a name is never a subject).
2. **Class D (79 county/geoid-keyed) + C (5 ISO-keyed) + F (304 national-grain)**: same
   treatment — FIPS-18 prefix / MISO+PJM / national-at-Indiana slices. F includes the P6
   series (LMP via held PJM pnodes + MISO pnode acquisition, FERC-714, EIA-923/930,
   ng price hubs, weather normals).
3. **SI signals, ALL fields (operator directive):** re-run every Indiana-feeding SI source
   from the registry's own endpoints/codes with `outFields=*` — script-run like Lane D
   (zero agent tokens), one staging table per source + freshness diff. Lane D's
   source_id→endpoint mapping is the worklist.
4. **All 28/29 signals:** wire the missing 12 for Indiana as candidate layers as data
   permits (D21 done; MF foreclosure code found in IOCS; A1 = listings acquisition — the
   operator confirms no company data yet, so an agent explores permitted public listing
   surfaces; D9/D18 derived once owner data lands via the county-assessor lane).
5. **Class G (45 unread) + E spot-audit**: schema reads; E is largely reached via the
   parcel/HC/zoning aggregates — audit which E members reach nothing.

## Phase 2 — PAGES (spread the tool out; map stays the console)

- **Map** (siting console — as today, decluttered once other pages absorb panels)
- **Grid & Capacity** (buses/headroom tables, queue, upgrades, gas OAC, reliability)
- **Market & Rates** (CEMS, LMP, tariffs + riders, gas prices/capacity)
- **Community & Regulatory** (county posture, receipts browser, IURC dockets, grid plans)
- **SI Feed** (signal inventory, new-this-week, acquisitions, candidates)
- **Data** (inventory, provenance, honesty ledger, census)

## Phase 3 — FUNCTIONALITY

Dossier (shipped in v0 form), upload door (own site list → same screener), composite
scoring with user weights, PMTiles all-parcel rendering (needs one WSL/Docker install),
rate-engine math port.

## Standing rules unchanged
Indiana-clipped everything · value-read before wiring · provenance + cannot-assess on
every number · estimates never style as published · scripts not agents for refreshes.
