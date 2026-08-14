# Indiana Siting Intelligence

A self-contained, static siting-intelligence application for **Indiana only**, covering
seller-intent origination, grid & interconnection, land & site quality, infrastructure
gates (water/fibre), environmental screening, community sentiment, and market analytics
(Parts 1–6 of the Decennial platform scope; Part 7 is out of scope here).

Built for two purposes:
1. **Live siting work** — measuring hyperscale data-centre development potential in
   Indiana (transmission-first: buses, substations, lines, interconnection headroom).
2. **A baseline** for the full nationwide application — the tiling, aggregation, and
   evidence-panel patterns proven here at 3.5M parcels are the ones the national app
   needs at 130M.

## Architecture — static, no backend

```
BigQuery (energy-platfrom.indiana_app)
   └─ one-time / per-refresh exports
        ├─ PMTiles  (geometry + ~4 styling fields per feature)
        └─ sharded JSON (full attributes, fetched on click)
              └─ committed → GitHub Pages
```

- **One map, per-part presets** — not six pages. MapLibre GL + PMTiles.
- **Side evidence panel** (not popups); every view exportable.
- GitHub Pages serves static files only; no credentials exist client-side.
- Limits respected: 100 MB/file (tiles split by zoom or shipped via Releases if needed),
  ~1 GB repo.

## Non-negotiable data rules (inherited from the platform)

- **Every on-screen number traces to a source table + refresh date.**
- **"Cannot assess" is a first-class value** — never rendered as zero, blank, or averaged away.
- **No centroids, ever.** A parcel renders as its own polygon, at exact geometry —
  no `ST_SIMPLIFY` on the individual-feature layer.
- **100% representation at every zoom**: individual features where separable, aggregates
  that include them where not. Aggregation is not truncation; nothing is ever absent.
- **User-uploaded site lists are first-class citizens** — a CSV upload enters the same
  join pipeline as the seller-intent feed. Designed in from the start.
- **Licensed/commercial reference data never enters this repository** (it is public) and
  never renders or exports. It is used only as an internal validation target, offline.
- Scraping: only what a source permits — no accounts, no terms dialogues, no CAPTCHAs,
  no paywalls. Gated sources are recorded BLOCKED with the exact wall.

## Repository layout

```
index.html, app.js, style.css   the map console (GitHub Pages serves the repo root)
vendor/                         MapLibre GL, vendored (no CDN dependency)
data/                           exported spine artifacts (gzipped GeoJSON + summary)
docs/                           architecture, measured data inventory, scrape lanes
scripts/                        reproducible BigQuery → export builders (read-only on energy.*)
scrapers/                       lane A/B/C acquisition scripts + findings
```

**Enable hosting:** GitHub → Settings → Pages → Deploy from branch → `main` / `/ (root)`.

## Data warehouse

All source data lives in BigQuery project `energy-platfrom` (spelling intentional),
dataset `energy` (read-only here). This app's Indiana slices live in dataset
`indiana_app`, each registered in `indiana_app._registry` with source, method, row
count, and build time. See [docs/DATA.md](docs/DATA.md) for the measured inventory.
