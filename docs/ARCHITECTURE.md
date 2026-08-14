# Architecture

## The constraint that shapes everything

GitHub Pages serves static files and cannot query BigQuery. For one state this is a
feature: Indiana's entire estate exports to tiles + JSON that host statically, which
eliminates the row-cap/transport problem outright — a tile carries geometry plus ~4
styling fields (~40 bytes/feature) instead of 25-field JSON rows.

## Transport split: geometry vs attributes

| question | transport | payload |
|---|---|---|
| where is everything? | PMTiles (pre-built, cached, HTTP range reads) | geometry + ~4 styling fields |
| what does THIS one say? | sharded static JSON, fetched on click | all attributes, one site |

The attribute store is sharded by county / tile key so a click fetches a few KB.
This same contract is what a server-backed national app would serve from an API —
the front end doesn't care, which is what makes this repo the national baseline.

### v0 transport (shipped 2026-08-14) — and the flagged upgrade

This machine has no tippecanoe/WSL/Docker/GDAL, so v0 ships **without** binary tiles:

- `data/counties.geojson.gz` — 92 counties with full rollup stats; the choropleth carries
  **100% of the 3,553,194 parcels at every zoom**.
- `data/sites/{fips}.geojson.gz` — per-county **class-union** parcels
  (`occ_group='ci' OR mw@4>=25 OR has_si_signal` = 1,200,924 parcels), exact geometry,
  full attributes, lazy-loaded per viewport at z≥10 and decompressed natively in the
  browser (`DecompressionStream`).
- Parcels outside the class union are **fully counted** in the county layer and the
  on-screen denominators — aggregation, not truncation. Rendering ALL 3.55M parcels
  individually is the PMTiles upgrade, which needs one install on the build machine
  (either `wsl --install` then `sudo apt install …/tippecanoe`, or Docker Desktop) —
  flagged, not silently skipped.

## Zoom-grain ladder — 100% representation, never truncation

| zoom | grain | source |
|---|---|---|
| z0–z5 | state | pre-aggregated |
| z6–z8 | county (92) | county rollup tables |
| z9–z11 | H3 hex bins | pre-aggregated |
| z12+ | individual feature, EXACT geometry | PMTiles |

Rules: a feature may become a pixel in an aggregate; it may never become absent.
The on-screen denominator is always a real COUNT over the active filter
("1,847 of 412,904"), never the length of the returned array. Location-quality tiers
(`parcel_polygon > structure_point > source_point > rooftop_geocode > place_centroid >
none`) style distinctly and never render as equals. No centroids are ever derived from
shapes. No simplification on the individual-feature layer.

## Size limits and the split strategy

- 100 MB per file → tiles split by zoom band (z0–z11 / z12+) and, if a band still
  exceeds 100 MB, by region; GitHub Releases carries anything stubbornly larger.
- ~1 GB repo target; the parcel layer is the only job at risk and is dry-run + cost/size
  flagged before each build.

## The upload door (designed in from day one)

A user-dropped CSV/XLSX parses client-side (no upload — the site is static, data never
leaves the browser), geocodes/joins against the same published lookup surfaces the
seller-intent feed uses, and flows through identical filters, panels, and exports.
Failures are kept and labelled, never dropped. Upload parity is an acceptance test.

## Refresh model

Each export artifact records its source tables and build time; the app surfaces that as
the freshness label on every layer and every number. Rebuilds are one script run per
layer (`scripts/`), idempotent, and safe to re-run.
