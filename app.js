/* Indiana Siting Intelligence — composable Screener + Layers console.
 * Everything renders together; the screener composes across parts (class, MW, SI, grid
 * distance, environmental gates, county sentiment). Every number carries provenance;
 * cannot-assess renders as itself; estimates never style as published coordinates. */
"use strict";

const PARCEL_ZOOM = 10;
const MI = 1609.344;
const state = {
  summary: null, counties: null, countyBbox: {}, ctx: null,
  loaded: new Map(), loading: new Set(), receipts: null,
  grid: null, gas: null, pjm: null, terr: null, overlays: null, cand: null,
  subBins: null, lineBins: null, poiList: null,
  shortlist: JSON.parse(localStorage.getItem("in_shortlist") || "[]"),
  // G93: `market` and `pipeline` went with the modals that fetched them. market.json.gz and
  // pipeline.json.gz are still built and still read by market.html and grid.html, which is where
  // that content belongs; the map no longer holds a second copy in memory.
  measure: { on: false, pts: [] },
};

/* ---------- helpers ---------- */
/* fmt + fetchGz come from common.js (loaded first).
   ⛔ DO NOT RE-DECLARE `fetchGz` HERE. It was declared in this file too, four lines above this
   very comment, for long enough that the comment and the code contradicted each other in plain
   sight. app.js loads AFTER common.js, so the copy here silently WON on every page that includes
   it -- which is the map console, the heaviest payload consumer in the application and the only
   page that fetches the 92 on-demand county files.
   The cost was measured on 2026-08-19b: the G101 cache-bust was added to common.js, verified as
   present (`payloadVersions` was defined), and still did nothing here, because `fetchGz` in the
   page was the other one. Two copies of one thing WILL drift, and the loser is invisible. */
function bboxOf(geom) {
  let w = 180, s = 90, e = -180, n = -90;
  const walk = (c) => { if (typeof c[0] === "number") { w = Math.min(w, c[0]); e = Math.max(e, c[0]); s = Math.min(s, c[1]); n = Math.max(n, c[1]); } else c.forEach(walk); };
  walk(geom.coordinates); return [w, s, e, n];
}
function havM(a, b, c, d) {
  const p = Math.PI / 180;
  const x = Math.sin((c - a) * p / 2) ** 2 + Math.cos(a * p) * Math.cos(c * p) * Math.sin((d - b) * p / 2) ** 2;
  return 12742000 * Math.asin(Math.sqrt(x));
}
function repPt(geom) { // any coordinate ON the feature (a vertex — not a derived centroid)
  let c = geom.coordinates;
  while (typeof c[0] !== "number") c = c[0];
  return c;
}
const binKey = (lon, lat) => `${Math.floor(lon * 10)}:${Math.floor(lat * 10)}`;
function binPush(bins, lon, lat, obj) {
  const k = binKey(lon, lat);
  (bins[k] = bins[k] || []).push(obj);
}
function binNear(bins, lon, lat, ring = 2) { // ~0.1° cells; ring 2 ≈ up to ~15 mi
  const out = [], bx = Math.floor(lon * 10), by = Math.floor(lat * 10);
  for (let i = -ring; i <= ring; i++) for (let j = -ring; j <= ring; j++) {
    const c = bins[`${bx + i}:${by + j}`]; if (c) out.push(...c);
  }
  return out;
}

/* ---------- map ---------- */
const map = new maplibregl.Map({
  container: "map", center: [-86.28, 39.85], zoom: 6.6,
  style: { version: 8, glyphs: "https://fonts.openmaptiles.org/{fontstack}/{range}.pbf",
    sources: { basemap: { type: "raster",
      tiles: ["https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png"], tileSize: 256,
      attribution: "© OpenStreetMap contributors © CARTO" } },
    layers: [{ id: "basemap", type: "raster", source: "basemap" }] },
});

/* ==============================================================================================
   G134 - WHY YOU COULD NOT CLICK A SUBSTATION WHILE PARCELS WERE ON.

   Operator, 2026-08-21: *"We currently lack the ability to click on buses, substations,
   transmission line, and other clickable features when parcels are in view … the user would like
   to understand the grid assets … proximate to the prospected site location and is unable to
   do so right now."*

   ⛔ IT WAS NOT A MISSING HANDLER, WHICH IS WHY `audit_map_clicks.py` PASSED THROUGHOUT. Every
   layer HAS a click handler; the audit checks exactly that and could never see this. Measured in
   the browser on a substation sitting inside a candidate parcel, `show()` was called three times
   in this order:
       1. "Substation: UNKNOWN123164"
       2. "Transmission line"
       3. "Parcel 011003100005000005"     <- LAST, so it is the one left on screen
   MapLibre delegates a layer-scoped click to EVERY layer with a feature under the cursor, in the
   order the listeners were registered. The parcel handler is registered inside addCountyLayers(),
   which runs when a county's parcels load - always AFTER the asset layers were bound at boot. So
   the biggest, least specific target silently won every contested click.

   ⭐ THE RULE: a small target beats a big one. A parcel polygon yields when something more
   specific is under the same four pixels. Points, lines and labels are specific; county and
   territory boundaries are context and are not; area fills lose unless they are a genuinely
   small footprint.

   ⛔ AND THE LIST OF CLICKABLE LAYERS IS COLLECTED, NEVER TYPED. A hardcoded list is the defect
   this project files under "remove a control and its registry entry in one change" - it would go
   stale the first time a layer was added. Wrapping map.on() means a layer becomes eligible by the
   act of being given a handler, so the rule cannot drift from reality.
   ⚠ The wrapper must be installed BEFORE any handler is registered, which is why it sits here,
   immediately after the map is constructed, rather than beside the parcel code it protects.
   ============================================================================================== */
const PARCEL_LAYER_RE = /^sites-\d+-(fill|line)$/;
/* context, not assets: these describe the region a parcel is IN, so they must never outrank it */
const CLICK_CONTEXT = new Set(["basemap", "county-fill", "county-line", "terr-fill", "terr-line"]);
/* fills small enough to BE the asset - a substation footprint is the substation */
const CLICK_SMALL_FILL = new Set(["grid-subs-fp"]);
/* lower rank wins. A dot is more specific than a line; a line than an area; an area than the
   parcel it sits on; the parcel than the county around it. */
const CLICK_RANK_BY_TYPE = { circle: 0, symbol: 0, line: 1, fill: 2 };
const CLICK_LAYERS = new Set();

function clickRank(id) {
  if (CLICK_SMALL_FILL.has(id)) return 0;
  if (PARCEL_LAYER_RE.test(id)) return 3;
  if (CLICK_CONTEXT.has(id)) return 4;
  const l = map.getLayer(id);
  const r = l && CLICK_RANK_BY_TYPE[l.type];
  return r === undefined ? 2 : r;
}

/* ⚠ RANK IS RESOLVED AT CLICK TIME, NOT AT REGISTRATION TIME. Most handlers are bound before
   their layer exists (load-on-first-toggle), so map.getLayer() would be undefined here. */
function clickWins(id, pt) {
  const mine = clickRank(id);
  if (mine === 0) return true;                    /* nothing outranks a point */
  const pad = 4;                                  /* forgiving for a 3 px dot on a touchpad */
  const feats = map.queryRenderedFeatures(
    [[pt.x - pad, pt.y - pad], [pt.x + pad, pt.y + pad]]);
  return !feats.some((f) => f.layer.id !== id
                         && CLICK_LAYERS.has(f.layer.id)      /* would actually open something */
                         && clickRank(f.layer.id) < mine);
}

/* ⛔ EVERY LAYER-SCOPED CLICK HANDLER IS WRAPPED, RATHER THAN THIRTEEN HANDLERS BEING EDITED.
   The first attempt guarded only the parcel handler. It stopped the parcel stealing the click and
   then the TRANSMISSION LINE won instead - measured, clicking a substation dot opened
   "Transmission line" - because the line's handler is simply bound after the substation's. Every
   contested pair has this shape, so guarding one of them just moves the bug. One rule, applied
   where the delegation happens, fixes all of them and cannot be forgotten for the next layer.
   ⚠ Ties are left alone: two point layers exactly overlapping both fire, and the later-bound one
   is what stays on screen. That is rare and harmless; ranking within a tier would be inventing a
   preference nobody has stated. */
(() => {
  const _on = map.on.bind(map);
  map.on = function (type, layerOrFn, fn) {
    if (type === "click" && typeof layerOrFn === "string" && typeof fn === "function") {
      CLICK_LAYERS.add(layerOrFn);
      return _on(type, layerOrFn, function (e) {
        if (!clickWins(layerOrFn, e.point)) return;
        return fn.apply(this, arguments);
      });
    }
    return _on.apply(map, arguments);
  };
})();
/* #1 BASEMAP TOGGLE, 2026-08-19. Operator: the Illinois tool has one and this did not.
   ⛔ SWAPS THE RASTER SOURCE'S TILES, NEVER THE STYLE. map.setStyle() rebuilds the style object
   and would destroy all 42 layers, every per-county parcel source and every click binding we have
   added -- the map would go blank and nothing would error. setTiles() changes only the URLs the
   basemap raster reads, leaving everything drawn on top of it untouched.
   Satellite is the one that earns its place: a siter looking at 600 acres wants to know whether it
   is row crop, woodland or already cleared, and a road map cannot answer that. */
const BASEMAPS = {
  light:     { t: ["https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png"],
               a: "© OpenStreetMap contributors © CARTO" },
  voyager:   { t: ["https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png"],
               a: "© OpenStreetMap contributors © CARTO" },
  dark:      { t: ["https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png"],
               a: "© OpenStreetMap contributors © CARTO" },
  satellite: { t: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
               a: "Imagery © Esri, Maxar, Earthstar Geographics" },
};
function setBasemap(key) {
  const b = BASEMAPS[key] || BASEMAPS.light;
  const src = map.getSource("basemap");
  if (src && src.setTiles) src.setTiles(b.t);
  // the attribution is a legal requirement, not decoration -- it has to follow the tiles
  const el = document.querySelector(".maplibregl-ctrl-attrib-inner");
  if (el) el.innerHTML = b.a;
  // satellite is dark: the parcel outline and the legend need to stay readable on it
  document.body.classList.toggle("basemap-dark", key === "satellite" || key === "dark");
}
map.addControl(new maplibregl.NavigationControl(), "top-right");
map.addControl(new maplibregl.ScaleControl({ unit: "imperial" }), "bottom-left");

if (document.getElementById("basemap"))
  document.getElementById("basemap").addEventListener("change", (e) => setBasemap(e.target.value));
map.on("load", async () => {
  state.summary = await (await fetch("data/state_summary.json?v=" + Date.now())).json();
  /* Fills common.js's PROV, which is the ONE provenance store. This page used to keep a second
     one (`state.provenance`) read by a second `prov()` declared in this file -- identical output,
     different backing store, and app.js loads last so its copy silently won. Both are gone. */
  for (const p of state.summary.provenance) PROV[p.table_name] = p;
  state.ctx = await (await fetch("data/county_context.json?v=" + Date.now())).json();
  renderStatebar(); renderLedger(); renderShortlistCount();

  state.counties = await fetchGz("data/counties.geojson.gz");
  for (const f of state.counties.features) {
    state.countyBbox[f.properties.fips] = bboxOf(f.geometry);
    const c = state.ctx.by_fips[f.properties.fips];
    if (c) {
      f.properties.opposition_intensity = c.posture?.opposition_intensity ?? null;
      f.properties.has_restriction = c.posture?.has_local_restriction ?? null;
      f.properties.queue_active_mw = c.queue?.active_mw ?? null;
      /* G88, operator 2026-08-19: *"instead of having queued MW, we should put the number of DC
         developments that are either completed/in progress (maybe one field for each)"*.
         ⛔ TWO FIELDS, NEVER SUMMED. `dc_listed` is a DIRECTORY listing (baxtel / datacentermap /
         OSM / PeeringDB) and `dc_pipeline` is a VERIFIED act of a county body. They come from
         different sources, mean different things, and a project can appear in both. */
      f.properties.dc_listed = c.dc_posture?.listed ?? null;
      f.properties.dc_pipeline = c.dc_posture
        ? (c.dc_posture.approved || 0) + (c.dc_posture.proposed || 0) : null;
      // G11: the VERIFIED action, which the map previously could not see at all. Measured
      // 2026-08-17: 33 counties carry one and the map called 13 of them "quiet" — Cass has a BAN,
      // Floyd/Huntington/Whitley have moratoriums, all with has_local_restriction = false. And 10
      // counties have APPROVED a data centre, which is the strongest positive signal there is and
      // had no representation on the map whatsoever.
      f.properties.action_tone = c.action_summary?.tone ?? null;
      f.properties.action_headline = c.action_summary?.headline ?? null;
      f.properties.action_approved = c.action_summary?.approved ? 1 : 0;
    }
  }
  map.addSource("counties", { type: "geojson", data: state.counties });
  map.addLayer({ id: "county-fill", type: "fill", source: "counties",
    paint: { "fill-color": countyPaint("class_union"),
             "fill-opacity": ["interpolate", ["linear"], ["zoom"], 8.5, 0.8, 10, 0.18] } });
  map.addLayer({ id: "county-line", type: "line", source: "counties",
    paint: { "line-color": "#8b95a7", "line-width": 0.8 } });
  map.on("click", "county-fill", (e) => {
    if (state.measure.on) return;
    if (map.getZoom() >= PARCEL_ZOOM) return;
    openCountyEvidence(e.features[0].properties);
  });

  // grid (substations / lines / MISO bus POIs) — build distance bins as we load
  state.grid = await fetchGz("data/grid.geojson.gz");
  state.subBins = {}; state.lineBins = {}; state.poiList = [];
  for (const f of state.grid.features) {
    const p = f.properties;
    if (p.layer === "substation") {
      // 933 substations are footprint POLYGONS with no published point. Bin every vertex: the
      // nearest vertex approximates the nearest point on the boundary, which is both truer than
      // a centroid and permitted — deriving a centroid to stand in for a site is not.
      const meta = { name: p.substation_name, kv: Number(p.max_kv) || 0 };
      const walkS = (c) => { if (typeof c[0] === "number") binPush(state.subBins, c[0], c[1], { lon: c[0], lat: c[1], ...meta }); else c.forEach(walkS); };
      walkS(f.geometry.coordinates);
    } else if (p.layer === "line") {
      // kv is the NORMALISED kilovolt column; `voltage` is the publisher's raw string and is in
      // VOLTS for OSM rows, so binning on it would read a 138 kV OSM line as 138,000.
      const kv = Number(p.kv) || Number(p.voltage) || 0;
      const walk = (c) => { if (typeof c[0] === "number") binPush(state.lineBins, c[0], c[1], { lon: c[0], lat: c[1], kv }); else c.forEach(walk); };
      walk(f.geometry.coordinates);
    } else if (p.layer === "bus_poi") {
      const [lon, lat] = f.geometry.coordinates;
      /* ONE figure per bus per direction now. The old median/best pair let a parcel be
         described by whichever of three numbers flattered it; tier0 carries the binding value. */
      state.poiList.push({ lon, lat, name: p.poi_name, mw: p.headroom_mw,
                           direction: p.direction, iso: p.iso });
    }
  }
  map.addSource("grid", { type: "geojson", data: state.grid });
  /* G111, operator 2026-08-19: *"The buses should show both withdrawal and injection amounts,
     since a developer may be concerned with co-locating their site prospect with generation."*
     The payload holds ONE FEATURE PER BUS PER DIRECTION (3,542 features, 1,772 withdrawal +
     1,770 injection) and the map draws only the withdrawal half -- deliberately, because two
     stacked dots per station is unreadable. So the reader could never see the injection number
     at all. Pair them here, by bus, and let ONE popup answer both questions.
     ⚠ The pairing key is `${iso}|${bus_number}` and NOT bus_number alone: the two ISOs number
     their buses independently and a collision would silently merge two different buses. */
  state.busPairs = new Map();
  for (const f of (state.grid.features || [])) {
    const p = f.properties;
    if (!p || p.layer !== "bus_poi") continue;
    const k = `${p.iso}|${p.bus_number}`;
    const e = state.busPairs.get(k) || {};
    e[p.direction] = p;
    state.busPairs.set(k, e);
  }
  map.addLayer({ id: "grid-lines", type: "line", source: "grid",
    filter: ["==", ["get", "layer"], "line"],
    /* G13: coloured by the AUDITED voltage class, not by a raw number.
       The previous paint did `to-number(voltage, 0)` on `voltage_raw`, which turns HIFLD's
       "-999999" not-available marker into a real negative number — 335 lines were being drawn as
       though they were the lowest-voltage in the state, for the wrong reason.
       ⛔ `unknown` gets its OWN colour (dashed grey), never the bottom of the ramp: a line whose
       voltage we do not know is not a small line. */
    paint: { "line-color": ["match", ["get", "volt_class"],
               "735 and above", "#4c1d95",
               "500-734",       "#6d28d9",
               "300-499",       "#7c3aed",
               "200-299",       "#2563eb",
               "100-199",       "#4a7bd0",
               "under 100",     "#93b4e3",
               /* unknown */    "#b6bdc9"],
             "line-width": ["match", ["get", "volt_class"],
               "735 and above", 3.0, "500-734", 2.8, "300-499", 2.6,
               "200-299", 2.1, "100-199", 1.7, "under 100", 1.1,
               /* unknown */ 1.1] } });
  /* ⛔ `line-dasharray` is NOT a data-driven paint property in MapLibre — a ["case"] expression on
     it throws inside addLayer, and because that happens during boot it killed everything after it,
     including the parcel layers. The map simply lost its parcels with no visible error.
     The dashed treatment for unknown-voltage lines therefore needs its OWN layer, filtered. */
  map.addLayer({ id: "grid-lines-unknown", type: "line", source: "grid",
    filter: ["all", ["==", ["get", "layer"], "line"], ["==", ["get", "volt_class"], "unknown"]],
    paint: { "line-color": "#b6bdc9", "line-width": 1.1, "line-dasharray": [2, 2] } });
  // A circle layer silently ignores polygon features, so the 933 footprint-only substations
  // need their own fill layer — otherwise they are in the payload and still invisible.
  map.addLayer({ id: "grid-subs", type: "circle", source: "grid",
    filter: ["all", ["==", ["get", "layer"], "substation"], ["==", ["get", "geom_kind"], "point"]],
    paint: { "circle-radius": ["interpolate", ["linear"], ["to-number", ["get", "max_kv"], 0], 0, 2.2, 138, 4.2, 345, 7],
             "circle-color": "#334155", "circle-opacity": 0.8 } });
  map.addLayer({ id: "grid-subs-fp", type: "fill", source: "grid",
    filter: ["all", ["==", ["get", "layer"], "substation"], ["==", ["get", "geom_kind"], "footprint"]],
    paint: { "fill-color": "#334155", "fill-opacity": 0.45, "fill-outline-color": "#0f172a" } });
  /* ---------- G77: BUSES ARE COLOURED BY HEADROOM ---------------------------------------------
     Operator, 2026-08-19: *"Buses should show headroom by coloring."*

     They were sized by headroom and coloured one flat amber, which asks the reader to compare
     CIRCLE AREAS - the worst channel there is for a quantity, and hopeless at the bottom of the
     range where almost all of these sit.

     ⭐ BANDED, NOT A CONTINUOUS RAMP, AND THE BANDS ARE MEASURED. Withdrawal headroom across
     1,772 buses: 652 AT ZERO, median 17 MW, p75 61, p90 200, p95 364, p99 1,257, max 5,000. A
     linear ramp over that would paint 90% of the map one colour. The breaks are set at the
     DECISIONS instead - the app's own 25 MW datacentre floor and the 300 MW target the dossier
     uses - so a colour answers "can this host my project", not "what percentile is this".

     ⛔ ZERO GETS ITS OWN COLOUR, DELIBERATELY NOT THE DARK END OF A RAMP. A zero here is a
     statement about the STUDY CASE, not the bus: 99.7% of zero-headroom rows are already at or
     over 100% loaded before any request arrives (G40). "Nothing available because the network is
     already full" and "a small amount available" are different findings, and a gradient would
     render them as neighbours. */
  map.addLayer({ id: "grid-bus", type: "circle", source: "grid",
    /* ⚠ there were TWO `filter` keys here - the first was silently overwritten by the second.
       Harmless in JS and confusing to read, so the dead one is gone. Only the load direction
       draws by default: a data centre asks the withdrawal question, and drawing both stacked
       two dots on every station. */
    filter: ["all", ["==", ["get", "layer"], "bus_poi"],
                    ["==", ["get", "direction"], "Withdrawal"]],
    paint: { "circle-radius": ["interpolate", ["linear"], ["to-number", ["get", "headroom_mw"], 0], 0, 4, 2000, 9, 8000, 13],
             "circle-color": ["step", ["to-number", ["get", "headroom_mw"], 0],
                              BUS_BANDS[0].colour,          // 0 - already at or over its limit
                              1,    BUS_BANDS[1].colour,    // under the 25 MW datacentre floor
                              25,   BUS_BANDS[2].colour,
                              100,  BUS_BANDS[3].colour,
                              300,  BUS_BANDS[4].colour],
             "circle-stroke-color": "#44403c", "circle-stroke-width": 1.1, "circle-opacity": 0.92 } });
  map.addLayer({ id: "grid-bus-label", type: "symbol", source: "grid", minzoom: 8,
    filter: ["all", ["==", ["get", "layer"], "bus_poi"],
                    ["==", ["get", "direction"], "Withdrawal"]],
    layout: { "text-field": ["concat", ["to-string", ["round", ["to-number", ["get", "headroom_mw"], 0]]], " MW"],
              "text-size": 10, "text-offset": [0, 1.4], "text-font": ["Noto Sans Regular"] },
    paint: { "text-color": "#7c2d12", "text-halo-color": "#fff", "text-halo-width": 1 } });

  state.pjm = await fetchGz("data/pjm.geojson.gz");
  map.addSource("pjm", { type: "geojson", data: state.pjm });
  map.addLayer({ id: "pjm-queue", type: "circle", source: "pjm",
    filter: ["==", ["get", "layer"], "queue_point"], layout: { visibility: "none" },
    paint: { "circle-radius": 3, "circle-color": "#64748b", "circle-opacity": 0.75 } });
  map.addLayer({ id: "pjm-bus-est", type: "circle", source: "pjm",
    filter: ["==", ["get", "layer"], "bus_candidate"], layout: { visibility: "none" },
    paint: { "circle-radius": 6, "circle-color": "#fff", "circle-opacity": 0.5,
             "circle-stroke-color": "#dc2626", "circle-stroke-width": 2 } });

  state.gas = await fetchGz("data/gas.geojson.gz");
  map.addSource("gas", { type: "geojson", data: state.gas });
  map.addLayer({ id: "gas-lines", type: "line", source: "gas",
    filter: ["==", ["get", "layer"], "gas"], layout: { visibility: "none" },
    paint: { "line-color": "#b45309", "line-width": 1.6, "line-dasharray": [3, 2] } });
  // G65: a compressor station and a storage field answer different questions -- one is whether the
  // pipe can push more gas to you, the other is whether there is buffered supply nearby -- so they
  // no longer share a checkbox.
  map.addLayer({ id: "gas-compressor", type: "circle", source: "gas",
    filter: ["==", ["get", "layer"], "compressor"], layout: { visibility: "none" },
    paint: { "circle-radius": 5, "circle-color": "#b45309",
             "circle-stroke-color": "#fff", "circle-stroke-width": 1 } });
  map.addLayer({ id: "gas-storage", type: "circle", source: "gas",
    filter: ["==", ["get", "layer"], "storage"], layout: { visibility: "none" },
    paint: { "circle-radius": 5, "circle-color": "#78350f",
             "circle-stroke-color": "#fff", "circle-stroke-width": 1 } });

  state.terr = await fetchGz("data/territories.geojson.gz");
  map.addSource("terr", { type: "geojson", data: state.terr });
  /* ---------- G94: TERRITORIES SHOW WHO IS WHERE ----------------------------------------------
     Operator, 2026-08-19: *"I want to see the service territory boundaries be bolded and be able
     to decipher exactly which territory is where (they are not currently named or color coded
     differently anywhere)."*

     ⛔ AND THERE IS A REASON THEY WERE NOT COLOUR CODED: THE MATCH NEVER FIRED. The previous paint
     tested `utility_type == "investor_owned"` and `== "cooperative"`, lower-case with an
     underscore. The payload's actual values are `INVESTOR OWNED` (17), `COOPERATIVE` (40),
     `MUNICIPAL` (14) and `NOT AVAILABLE` (74) - upper-case, spaced. So EVERY ONE of the 145
     territories fell through to the default grey, and the layer looked deliberately coloured while
     being uniform. A guessed value vocabulary, exactly like a guessed column name.

     Three layers now, because one cannot answer "which territory is where": a fill coloured by
     TYPE, a bolded boundary, and the utility's NAME.
     ⚠ Coloured by TYPE and not by utility: 145 categorical colours is noise, and the type is what
     changes who you negotiate with and whether the IURC is involved at all.
     ⚠ NOT AVAILABLE is its own colour and its own legend row - it is 74 of 145, so rendering it as
     if it were an ordinary category would hide that half the layer has no type. */
  map.addLayer({ id: "terr-fill", type: "fill", source: "terr", layout: { visibility: "none" },
    paint: { "fill-color": TERR_FILL, "fill-opacity": 0.30 } }, "county-line");
  map.addLayer({ id: "terr-line", type: "line", source: "terr", layout: { visibility: "none" },
    paint: { "line-color": TERR_FILL, "line-width": 2.0, "line-opacity": 0.95 } }, "county-line");
  map.addLayer({ id: "terr-label", type: "symbol", source: "terr", minzoom: 7,
    layout: { visibility: "none", "text-field": ["get", "utility"], "text-size": 11,
              "text-font": ["Noto Sans Regular"], "text-allow-overlap": false,
              "text-max-width": 9 },
    paint: { "text-color": "#1f2937", "text-halo-color": "#fff", "text-halo-width": 1.6 } });

  /* ---- G12: water. Watersheds and water-stress basins.
     Rivers and lakes are deliberately ABSENT: the national hydrography tables carry attributes
     with NO geometry on any of their 50M rows, so watercourses can be counted per watershed but
     cannot be drawn. Inventing a blue line from something else would be worse than omitting it. */
  state.water = await fetchGz("data/water.geojson.gz");
  map.addSource("water", { type: "geojson", data: state.water });
  // stress first so watershed outlines sit on top of it
  map.addLayer({ id: "water-stress-fill", type: "fill", source: "water",
    filter: ["==", ["get", "layer"], "stress_basin"], layout: { visibility: "none" },
    paint: { "fill-color": ["interpolate", ["linear"], ["to-number", ["get", "stress_score"], 0],
               0, "#e0f2fe", 1, "#7dd3fc", 2, "#fbbf24", 3, "#f97316", 4, "#b91c1c"],
             "fill-opacity": 0.4, "fill-outline-color": "#0369a1" } }, "county-line");
  map.addLayer({ id: "water-ws-fill", type: "fill", source: "water",
    filter: ["==", ["get", "layer"], "watershed"], layout: { visibility: "none" },
    paint: { "fill-color": "#0ea5e9", "fill-opacity": 0.10 } }, "county-line");
  map.addLayer({ id: "water-ws-line", type: "line", source: "water",
    filter: ["==", ["get", "layer"], "watershed"], layout: { visibility: "none" },
    paint: { "line-color": "#0369a1", "line-width": 1.1, "line-dasharray": [3, 2] } }, "county-line");
  for (const lid of ["water-ws-fill", "water-stress-fill"]) {
    map.on("click", lid, (e) => { if (!state.measure.on) openWaterEvidence(e.features[0].properties); });
    map.on("mousemove", lid, (e) => showTip(e, e.features[0].properties.layer === "watershed"
      ? `${e.features[0].properties.name} watershed`
      : `water stress: ${e.features[0].properties.stress_label || "unrated"}`));
    map.on("mouseleave", lid, hideTip);
  }

  state.overlays = await fetchGz("data/overlays.geojson.gz");
  map.addSource("overlays", { type: "geojson", data: state.overlays });
  map.addLayer({ id: "env-padus", type: "fill", source: "overlays",
    filter: ["==", ["get", "layer"], "padus"], layout: { visibility: "none" },
    paint: { "fill-color": "#15803d", "fill-opacity": 0.32, "fill-outline-color": "#14532d" } });
  /* G65: "Tax-credit areas" was ONE checkbox over SIX different federal geographies, and they do
     not point the same way. An energy community is a 10% adder you are chasing; critical habitat
     is a constraint that can stop the project. Collapsing a benefit and a blocker into one tick is
     the volume-over-value failure the governing principle names. One control each, coloured apart:
     benefits violet, the habitat constraint red. */
  for (const [kind, id, colour] of [
    ["low_income_tract",  "env-bonus-lit",  "#7c3aed"],
    ["qct",               "env-bonus-qct",  "#8b5cf6"],
    ["coal_closure",      "env-bonus-coal", "#6d28d9"],
    ["opportunity_zone",  "env-bonus-oz",   "#a78bfa"],
    ["energy_community",  "env-bonus-ec",   "#4c1d95"],
    ["critical_habitat",  "env-bonus-hab",  "#b91c1c"],
  ]) {
    map.addLayer({ id, type: "fill", source: "overlays",
      filter: ["all", ["==", ["get", "layer"], "bonus"], ["==", ["get", "kind"], kind]],
      layout: { visibility: "none" },
      paint: { "fill-color": colour, "fill-opacity": 0.2, "fill-outline-color": colour } });
  }
  map.addLayer({ id: "env-nonatt", type: "fill", source: "overlays",
    filter: ["==", ["get", "layer"], "nonattainment"], layout: { visibility: "none" },
    paint: { "fill-color": "#9f1239", "fill-opacity": 0.18, "fill-outline-color": "#881337" } });

  /* ---------- G72: LAND-STATUS AND AIRSPACE GATES -------------------------------------------
     Operator, 2026-08-19: "we should add datasets from BQ like military bases, tribal land, and
     similar datasets that give us more contextual information about the land and environment."

     All four objects were already clipped in BigQuery and NONE reached a control -- app.js named
     them only inside the provenance dictionary, tagged "PAGE-NEXT". They answer one question the
     console could not ask before: WHO ELSE ALREADY HOLDS A SAY OVER THIS LAND.

     ⚠ `in_tribal_land` held 14 rows and NOT ONE was in Indiana -- it had been clipped by a
     geoid key join rather than spatially, so it carried Laguna Pueblo (NM), L'Anse (MI),
     Kootenai (ID) and eleven more. Re-clipped in scripts/build_land_gates.py; Indiana holds
     exactly ONE tribal feature, Pokagon Off-Reservation Trust Land. Drawing the old table would
     have rendered New Mexico on an Indiana map, or drawn nothing and read as "no tribal land
     here" -- a negative finding we never measured, which is the G51 defect exactly.

     Small enough to fetch at boot: 33 polygons + 4,591 points = 150 KB. */
  state.gates = await fetchGz("data/gates.geojson.gz");
  map.addSource("gates", { type: "geojson", data: state.gates });
  for (const [layer, id, colour, op] of [
    ["military", "gate-mil",    "#b45309", 0.30],
    ["tribal",   "gate-tribal", "#0f766e", 0.34],
    ["sua",      "gate-sua",    "#4338ca", 0.14],
  ]) {
    map.addLayer({ id, type: "fill", source: "gates",
      filter: ["==", ["get", "layer"], layer], layout: { visibility: "none" },
      paint: { "fill-color": colour, "fill-opacity": op, "fill-outline-color": colour } });
  }
  // Height is the whole point of this layer, so it is the thing the radius encodes. 200 ft is the
  // FAA Part 77 NOTICE threshold -- every point here already had to tell the FAA it exists.
  map.addLayer({ id: "gate-obst", type: "circle", source: "gates",
    filter: ["==", ["get", "layer"], "obstacle"], layout: { visibility: "none" },
    paint: { "circle-radius": ["interpolate", ["linear"], ["coalesce", ["get", "agl_ft"], 200],
                               200, 2.5, 500, 5, 1200, 9],
             // ⭐ G72/G80, 2026-08-20: 1,816 of these 4,590 records are WIND TURBINES, and a
             //    turbine is a siting SIGNAL rather than an obstruction. It is standing proof
             //    that this exact ground already cleared landowner consent, an interconnection
             //    and a local permit. Drawn green so it separates from the towers and stacks,
             //    which are the gate half of the layer.
             "circle-color": ["case", ["==", ["get", "obstacle_type"], "WINDMILL"],
                              "#16a34a", "#78716c"],
             "circle-opacity": 0.75,
             "circle-stroke-color": "#292524", "circle-stroke-width": 0.5 } });

  state.fac = await fetchGz("data/facilities.geojson.gz");
  map.addSource("fac", { type: "geojson", data: state.fac });
  /* G112: count the two precision tiers FROM THE PAYLOAD, for the legend. ⛔ Do not hand-type
     these. The comment below and the popup both said "92 of 242" while the shipped payload holds
     249 pins (157 site + 92 city) -- the 242 came from a table row count and drifted. A legend is
     the last place a stale denominator should live. */
  state.dcTiers = { site: 0, city: 0 };
  for (const f of (state.fac.features || [])) {
    if (f.properties && f.properties.layer === "dc")
      state.dcTiers[f.properties.location_precision === "city" ? "city" : "site"]++;
  }
  // 92 of the 242 data-centre pins are census-gazetteer CITY centroids (datacentermap
  // publishes precision='city'), not facility locations — 32 of them land on one point near
  // New Carlisle, Microsoft Mishawaka among them, ~15 km from where it is drawn. A city
  // centroid must never be drawn like a surveyed coordinate, so the two tiers render apart:
  // solid = the publisher gave a site coordinate; hollow amber = city precision, position
  // approximate. Size carries how many facilities share the point.
  map.addLayer({ id: "fac-dc", type: "circle", source: "fac",
    filter: ["all", ["==", ["get", "layer"], "dc"], ["!=", ["get", "location_precision"], "city"]],
    layout: { visibility: "none" },
    paint: { "circle-radius": 6.5, "circle-color": "#0ea5e9", "circle-stroke-color": "#0c4a6e",
             "circle-stroke-width": 1.6, "circle-opacity": 0.9 } });
  map.addLayer({ id: "fac-dc-city", type: "circle", source: "fac",
    filter: ["all", ["==", ["get", "layer"], "dc"], ["==", ["get", "location_precision"], "city"]],
    layout: { visibility: "none" },
    /* G112, operator 2026-08-19: *"Why do some data centers show as different colors and have
       different sizes? Regardless, they should all be the same size."*
       ⛔ THE SIZE RAMP IS GONE. It interpolated the radius 7->15 on `pins_at_this_point`, which
       asked the reader to compare circle AREAS to recover a count -- the exact channel G77 just
       removed from the bus layer for being the worst way to encode a quantity. The count is
       already stated in words in the popup, where it can be read instead of estimated.
       ⭐ THE COLOUR STAYS, because it is not decoration: hollow amber means the coordinate is a
       CITY CENTROID, not the facility. 92 of 242 records are like this and 32 of them share one
       point near New Carlisle -- Microsoft Mishawaka among them, ~15 km from where it draws.
       Painting an approximate position like a surveyed one is the failure the estimate-badging
       rule exists to prevent. The legend now names both tiers so it need not be clicked to learn. */
    paint: { "circle-radius": 6.5,
             "circle-color": "#f59e0b", "circle-opacity": 0.12,
             "circle-stroke-color": "#b45309", "circle-stroke-width": 1.6 } });
  /* G65: solar, wind and thermal plant were one checkbox called "Power plants - solar - wind".
     They are three different siting facts: an operating thermal plant is an interconnection and a
     possible retirement, a wind farm is a competitor for the same queue slots, and solar is
     neither. Split, keeping the colours the combined layer already used so nothing moves on screen. */
  map.addLayer({ id: "fac-plant", type: "circle", source: "fac",
    filter: ["in", ["get", "layer"], ["literal", ["plant", "plant_hifld"]]],
    layout: { visibility: "none" },
    paint: { "circle-radius": 4.5, "circle-color": "#6b7280", "circle-opacity": 0.75 } });
  map.addLayer({ id: "fac-solar", type: "circle", source: "fac",
    filter: ["==", ["get", "layer"], "solar"], layout: { visibility: "none" },
    paint: { "circle-radius": 4.5, "circle-color": "#eab308", "circle-opacity": 0.75 } });
  map.addLayer({ id: "fac-wind", type: "circle", source: "fac",
    filter: ["==", ["get", "layer"], "wind"], layout: { visibility: "none" },
    paint: { "circle-radius": 2.5, "circle-color": "#38bdf8", "circle-opacity": 0.75 } });
  for (const id of ["fac-dc", "fac-dc-city", "fac-plant", "fac-solar", "fac-wind"]) {
    map.on("click", id, (e) => {
      if (state.measure.on) return;
      const p = e.features[0].properties;
      const rows_ = Object.entries(p).filter(([k]) => k !== "layer").slice(0, 10).map(([k, v]) => row(k, v)).join("");
      show(p.layer === "dc" ? `Existing data center: ${p.name || ""}` : `Facility (${p.layer})`,
        `<table>${rows_}</table>${p.layer === "dc" && p.location_precision === "city"
           ? `<div class="cannot">THIS IS NOT THE FACILITY'S LOCATION. datacentermap publishes
              <code>precision=city</code> for this record, and the coordinate is a census-gazetteer
              CITY CENTROID${p.precision_method ? ` (method: ${p.precision_method})` : ""} — the town it
              sits in, not the site. ${Number(p.pins_at_this_point) > 1
                ? `<b>${p.pins_at_this_point} facilities share this exact point</b>, so they are drawn on
                   top of one another. ` : ""}It is shown hollow, it is excluded from distance
              calculations, and it must not be used to site anything. 92 of our 242 data-center
              records are like this.</div>` : ""}
         ${p.layer === "dc" && String(p.unnamed_cannot_dedupe) === "true"
           ? `<div class="cannot">This point has no name in its source (OpenStreetMap), so the
              name-stem dedupe rule cannot judge whether it duplicates a named building nearby.
              It is shown rather than merged or dropped — 8 of the 242 are like this.</div>` : ""}
         <div class="prov">${p.layer === "dc"
           ? prov("in_data_centers_located") + " · 5-source union (peeringdb merged 2026-08-15), deduped by operator rule "
             + "(same name-stem within 500 m → one row; 244 → 242). Separate buildings on one campus are "
             + "deliberately NOT merged — a distance-only rule would collapse the whole New Carlisle campus into one pin."
           : prov("in_eia_plants")}</div>`);
    });
    map.on("mousemove", id, (e) => showTip(e, tipText(e.features[0].properties)));
    map.on("mouseleave", id, hideTip);
  }
  state.log = await fetchGz("data/logistics.geojson.gz");
  map.addSource("log", { type: "geojson", data: state.log });
  // line-dasharray is data-CONSTANT in MapLibre — a ["case", …] here makes addLayer reject the
  // whole layer (silently: the toggle then does nothing). Split rail/road into two layers.
  // G65: primary and secondary roads were both "log-lines". An interstate is an access fact; a
  // county road is not the same claim, so they get their own controls and their own weights.
  map.addLayer({ id: "log-road1", type: "line", source: "log", layout: { visibility: "none" },
    filter: ["==", ["get", "layer"], "road1"],
    paint: { "line-color": "#78716c", "line-width": 1.6 } });
  map.addLayer({ id: "log-road2", type: "line", source: "log", layout: { visibility: "none" },
    filter: ["==", ["get", "layer"], "road2"],
    paint: { "line-color": "#a8a29e", "line-width": 1 } });
  map.addLayer({ id: "log-lines-rail", type: "line", source: "log", layout: { visibility: "none" },
    filter: ["==", ["get", "layer"], "rail"],
    paint: { "line-color": "#57534e", "line-width": 1.4, "line-dasharray": [4, 2] } });
  for (const id of ["log-road1", "log-road2", "log-lines-rail"]) {
    map.on("mousemove", id, (e) => showTip(e, `${e.features[0].properties.layer}: ${e.features[0].properties.name || e.features[0].properties.fullname || ""}`));
    map.on("mouseleave", id, hideTip);
  }
  state.cand = await fetchGz("data/candidates.geojson.gz");
  map.addSource("cand", { type: "geojson", data: state.cand });
  map.addLayer({ id: "cand-line", type: "line", source: "cand", layout: { visibility: "none" },
    paint: { "line-color": "#7c3aed", "line-width": 2, "line-dasharray": [2, 1.5] } });

  // clicks + hover for every non-parcel layer
  const clickable = { "grid-bus": gridEv, "grid-subs": gridEv, "grid-subs-fp": gridEv, "grid-lines": gridEv,
    "pjm-queue": miscEv, "pjm-bus-est": miscEv, "gas-lines": miscEv,
    // #10, 2026-08-19: these four were DRAWN and unclickable. grid-lines-unknown carries the 270
    // lines whose voltage the publisher does not state -- its own class since G13, and the reader
    // could see it and never ask what it was. The three logistics layers had a hover tooltip and
    // no click at all, which is the same shape as the logistics layer being invisible for weeks.
    "grid-lines-unknown": gridEv,
    "log-lines-rail": miscEv, "log-road1": miscEv, "log-road2": miscEv,
    "gas-compressor": miscEv, "gas-storage": miscEv,
    "env-padus": miscEv, "env-nonatt": miscEv, "cand-line": candEv,
    // G65: the six tax-credit geographies each need their own evidence popup, or splitting the
    // layer would have silently removed the click that explained it.
    "env-bonus-lit": miscEv, "env-bonus-qct": miscEv, "env-bonus-coal": miscEv,
    "env-bonus-oz": miscEv, "env-bonus-ec": miscEv, "env-bonus-hab": miscEv,
    // G72: every gate layer gets its click in the SAME statement that draws it. Adding a layer
    // without its handler is how three logistics layers spent weeks visible and unexplainable.
    "gate-mil": miscEv, "gate-tribal": miscEv, "gate-sua": miscEv, "gate-obst": miscEv };
  for (const [id, fn] of Object.entries(clickable)) {
    map.on("click", id, (e) => { if (!state.measure.on) fn(e.features[0].properties); });
    map.on("mouseenter", id, () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", id, () => { map.getCanvas().style.cursor = ""; hideTip(); });
    map.on("mousemove", id, (e) => showTip(e, tipText(e.features[0].properties)));
  }
  map.on("click", "terr-fill", (e) => {
    if (!state.measure.on && document.getElementById("L-terr").checked)
      miscEv({ ...e.features[0].properties, layer: "territory" });
  });
  map.on("click", (e) => { if (state.measure.on) measureClick(e); });
  map.on("moveend", maybeLoadCounties);

  syncLayers(); maybeLoadCounties();
  /* G39: a ?fips=&parcel= link resolves AFTER the county machinery exists, because it has to
     drive it - fetch that county's parcels itself rather than waiting for the viewport to
     wander over them. Failures are reported to the reader, not swallowed. */
  handleDeepLink().catch((e) => console.error("deep link failed", e));
  /* G74: the user's own sites come back when they return from another page. It runs LAST and in
     its own try, because a restore is a convenience -- a bad stored row must never be able to
     stop the console booting. */
  try { restoreUploadedSites(); } catch (e) { console.error("restoring uploaded sites failed", e); }
  document.body.dataset.ready = "1";
});

/* ---------- county paint / metric ---------- */
function countyPaint(metric) {
  if (metric === "none") return "rgba(0,0,0,0)";
  if (metric === "opposition_intensity")
    return ["case", ["==", ["get", "opposition_intensity"], null], "#f2f2f0",
      ["interpolate", ["linear"], ["to-number", ["get", "opposition_intensity"], 0],
       0, "#eef6ee", 1, "#fde68a", 3, "#f59e0b", 6, "#b91c1c"]];
  /* G88: the two data-centre metrics that replaced "active queue MW" as a county shading.
     ⛔ Queue MW was standing in for DEVELOPMENT ACTIVITY and overstated it by construction -- G35
     measured that 49 of 87 counties have had >=50% of everything ever queued WITHDRAWN. The queue
     figure is still held and still rendered, but in the parcel evidence panel, where it is framed
     as what it actually is: competition for study slots. It is not a proxy for demand. */
  if (metric === "dc_listed")
    return ["case", ["==", ["get", "dc_listed"], null], "#f2f2f0",
      ["interpolate", ["linear"], ["to-number", ["get", "dc_listed"], 0],
       0, "#f7f4fb", 1, "#e0d3f0", 5, "#b79ada", 20, "#8b5cf6", 70, "#5b21b6"]];
  if (metric === "dc_pipeline")
    return ["case", ["==", ["get", "dc_pipeline"], null], "#f2f2f0",
      ["interpolate", ["linear"], ["to-number", ["get", "dc_pipeline"], 0],
       0, "#f4faf6", 1, "#cbead8", 3, "#6ec9a0", 6, "#15803d"]];
  // G11: shade by what the county has ACTUALLY DONE about data centres, verified at an official
  // source. Deliberately a 4-colour categorical rather than a gradient - "has a ban" and "has
  // approved one" are not two ends of one scale, they are different facts. Counties with no
  // recorded action are neutral grey and must NOT read as permissive: absence of a recorded rule
  // is not evidence there is no rule.
  if (metric === "action_tone")
    return ["match", ["get", "action_tone"],
      "blocking", "#b91c1c",   // a ban or a live moratorium
      "watch",    "#f59e0b",   // proposed, denied, uncodified - timing or precedent risk
      "open",     "#15803d",   // has approved a data centre; precedent exists
      "neutral",  "#cbd5e1",
      "#f2f2f0"];              // nothing recorded - NOT the same as nothing there
  const field = metric === "ge25mw" ? "ge25mw" : "class_union";
  return ["interpolate", ["linear"], ["get", field],
    0, "#f4f7fb", 2000, "#dbe7f5", 10000, "#b7cfea", 30000, "#8fb2dc", 80000, "#5d8cc7"];
}
/* A shaded map with no legend is a colouring-in exercise (the governing principle: everything on
   screen must say what it means for a decision). Each metric states its own scale AND its caveat. */
/* G21 -- a legend is a colour key; it is not a "so what". Each metric below now states what a
   developer should DO with the shading, in their decision unit, and says plainly whether it can
   disqualify a site or is context only. The operator's test case was "what does opposition
   intensity 4 mean for a decision?" -- the honest answer is that it is an unbounded relative count
   that changes your SCHEDULE, never the site's buildability, and that is now what it says. */
const METRIC_LEGEND = {
  action_tone: `<span class="swatch" style="background:#b91c1c"></span> ban or live moratorium ·
    <span class="swatch" style="background:#f59e0b"></span> proposed / denied / uncodified ·
    <span class="swatch" style="background:#15803d"></span> has approved one ·
    <span class="swatch" style="background:#f2f2f0;border:1px solid #cbd5e1"></span> nothing recorded.
    <b>Verified at an official source.</b> Grey means we found nothing — <b>not that nothing
    exists</b>; Indiana's rules are mostly county moratoria no code library carries.
    <br><b>A restriction outranks a development.</b> 10 counties have approved a data center and
    <b>6 of them are still amber or red</b> — Lake County has an approval <i>and</i> a moratorium.
    An existing project does not erase a ban, so the color shows the restriction. The approval is
    still worth knowing: a county that has said yes before may be readier to say yes again, which
    is why it is kept as its own fact rather than averaged away.
    <br>This is the one shading that can <b>stop a project outright</b>, and it is
    measured in council calendar — months, not design weeks. Treat red as a schedule you cannot
    engineer around, amber as <i>ask before you option the land</i>, and grey as <b>unknown, so
    call the county</b> — never as permission.`,
  opposition_intensity: `Low <span class="swatch" style="background:#eef6ee"></span>
    <span class="swatch" style="background:#fde68a"></span>
    <span class="swatch" style="background:#f59e0b"></span>
    <span class="swatch" style="background:#b91c1c"></span> high.
    ⚠ Partly tracks <b>news volume</b>, so large metros read higher for reasons that are not
    posture. Compare counties of similar size only.
    <br><b>There is no unit here.</b> It is a relative count of recorded objection activity, not a
    score out of ten and not a probability of refusal — so a 4 in Marion and a 4 in a rural county
    are not the same quantity and must not be compared.
    <br>It changes your <b>schedule and outreach budget</b>, not whether the site is
    buildable. A high reading says start community engagement before you file, and plan for a longer
    hearing process. <b>Context only — it never disqualifies a parcel</b>; for something that can,
    switch to <i>what the county has DONE</i>.`,
  dc_listed: `<b>Data centers a directory already lists in this county.</b> The closest thing we
    hold to "completed" — but it is a listing, not a certificate of occupancy.
    <br>It cuts both ways and both matter. A county with operating data centers has
    <b>demonstrated it will permit one</b>, and usually has the transmission and fibre to match.
    It is also <b>competition</b> for the same substation capacity and the same local goodwill.
    <br>⚠ <b>92 of our 249 pins are city centroids</b>, not facility locations, and 32 of those sit
    on a single point. Open a county to see how many of ITS pins are city-precision before reading
    a high number as a dense cluster.`,
  dc_pipeline: `<b>Data centers approved or proposed but not yet listed as operating</b> —
    approvals and pending petitions from county and municipal bodies, each verified at the
    authority's own published record.
    <br>This is the forward-looking half, and it is the better predictor of
    posture: an approval is a county saying yes <i>recently</i>, under its current board.
    ⚠ It is not a construction count — the permission exists, the building may not.
    ⛔ <b>Never add this to the operating count.</b> They come from different sources and one
    project can appear in both.`,
  class_union: `How many parcels passed the screen. A dense county is not a better county — it is a
    bigger one.
    <br>Use this to choose <b>where to look</b>, never to rank. A county with 4,000
    passing parcels and no headroom is worse than one with 40 beside a 345 kV line. Pick a search
    area here, then rank actual sites in the <b>screener</b>, which measures grid distance exactly.
    Context, not a ranking.`,
  ge25mw: `Parcels large enough for 25 MW at your density assumption.
    <br>This is an <b>upper bound on the land</b>, not a capacity you can build. It
    counts gross acreage at the density you set above — it says nothing about whether the grid can
    <i>deliver</i> 25 MW there, and nothing about how much of the parcel is actually buildable once
    setbacks, wetlands and floodplain come out. Pair it with the grid layers before shortlisting.`,
  none: `No shading.`,
};
function setCountyMetric(metric) {
  // legend FIRST, and the map call guarded. setPaintProperty throws if the map never initialised
  // (no WebGL, or a layer not yet added), and an exception there used to take the legend down with
  // it — so the one part that still works without a map silently did not.
  // ⚠ document.getElementById directly, NOT the $ helper: this runs at module scope during
  // evaluation, and `const $` is declared a few lines BELOW. Calling $ here threw
  // "Cannot access '$' before initialization" — a temporal-dead-zone error that aborted the whole
  // of app.js. Same defect class the front-end audit was built to catch: a top-level throw kills
  // every feature after it, with nothing on screen to say so.
  const el = document.getElementById("metric-legend");
  if (el) el.innerHTML = METRIC_LEGEND[metric] || "";
  try {
    if (map && map.getLayer && map.getLayer("county-fill"))
      map.setPaintProperty("county-fill", "fill-color", countyPaint(metric));
  } catch (e) { /* map not ready; the legend above is still correct */ }
}
document.getElementById("county-metric").addEventListener("change", (e) => setCountyMetric(e.target.value));
setCountyMetric("class_union");

/* G13: filter transmission lines by voltage class, with a legend that names what each colour is
   AND admits what "unknown" means. 335 lines had HIFLD's -999999 not-available marker loaded as a
   real number; 65 of those had a recoverable band and were rescued rather than binned. */
const LINE_KV_LEGEND = `
  <span class="swatch" style="background:#4c1d95"></span>735+ ·
  <span class="swatch" style="background:#7c3aed"></span>300&ndash;499 ·
  <span class="swatch" style="background:#2563eb"></span>200&ndash;299 ·
  <span class="swatch" style="background:#4a7bd0"></span>100&ndash;199 ·
  <span class="swatch" style="background:#93b4e3"></span>under 100 ·
  <span class="swatch" style="background:#b6bdc9"></span>unknown (dashed).
  <b>Unknown is its own color, not the bottom of the scale</b> — a line whose voltage we do not
  know is not a small line. 270 lines are genuinely unrated.`;
function setLineKv(v) {
  // document.getElementById, NOT the $ helper — this is called at module scope, above `const $`.
  // Same temporal-dead-zone trap that setCountyMetric hit an hour earlier; I repeated it verbatim.
  // The lesson that stuck: any function invoked during evaluation must not touch a later const.
  const el = document.getElementById("line-kv-legend");
  if (el) el.innerHTML = LINE_KV_LEGEND;
  try {
    if (map && map.getLayer && map.getLayer("grid-lines")) {
      map.setFilter("grid-lines", v === "all"
        ? ["==", ["get", "layer"], "line"]
        : ["all", ["==", ["get", "layer"], "line"], ["==", ["get", "volt_class"], v]]);
      // the dashed unknown layer follows the same filter, or it would keep drawing unknown lines
      // while the user has asked to see only 345 kV
      if (map.getLayer("grid-lines-unknown"))
        map.setLayoutProperty("grid-lines-unknown", "visibility",
          (v === "all" || v === "unknown") ? "visible" : "none");
    }
  } catch (e) { /* map not ready; the legend above is still correct */ }
}
const lkv = document.getElementById("L-line-kv");
if (lkv) { lkv.addEventListener("change", (e) => setLineKv(e.target.value)); setLineKv("all"); }

/* ---------- screener ---------- */
const $ = (id) => document.getElementById(id);
const V = (id) => Number($(id).value) || 0;
function recencyCutoff() {
  if (!$("f-recent").checked) return null;
  return new Date(Date.now() - V("f-recent-days") * 864e5).toISOString().slice(0, 10);
}
function classOk(p) {
  return ($("f-ci").checked && p.occ_group === "ci") ||
         ($("f-ag").checked && p.occ_group === "agriculture") ||
         ($("f-vac").checked && p.occ_group === "no_structure") ||
         ($("f-other").checked && p.occ_group === "other_nonres");
}
/* The acreage every surface screens, tooltips and reports on. ONE function so the screener,
   the tooltip and the evidence panel can never disagree about the same parcel.

   THE BUILDABLE AREA DEPENDS ON WHAT YOU ARE BUILDING (operator ruling, 2026-08-15):
   a hyperscale DC builds over or removes an existing structure, so its buildable area is the
   WHOLE PARCEL. A BESS sites around what is already there, so it gets OUTDOOR SPACE
   (parcel − measured footprints). Scoring every use case on outdoor space structurally
   under-rated C&I parcels — they carry the buildings — which is exactly backwards for a DC.
   For undeveloped land the two are the same number, so the ruling only moves parcels with structures.

   Either basis can disagree with itself. Measured across the class union: 126 of 1,200,924
   parcels report an exact area under half the recorded acreage, and for 85 of them
   footprints_intersecting is ZERO. With nothing intersecting, outdoor area IS the parcel by
   arithmetic, so a smaller exact figure is the exact pipeline's geometry disagreeing with the
   recorded acreage — not a measurement of buildings. Preferring it blindly dropped 23 parcels
   of 75+ acres (300 MW at 4 MW/acre) out of the screener with no footprint to blame. So when
   the two disagree that way, trust the recorded parcel area — and say so, rather than swallow it. */
function useCase() { const el = $("f-usecase"); return el ? el.value : "dc"; }
function acreageOf(p, uc) {
  const mode = uc || useCase();
  const parcel = Number(p.parcel_acres) || 0;
  const exactParcel = p.exact_parcel_acres == null ? null : Number(p.exact_parcel_acres);
  if (mode === "dc") {
    // whole parcel: the structure is not an obstacle, it is demolition scope.
    //
    // B3 RULE (operator, 2026-08-16): where recorded and exact acreage disagree beyond the
    // threshold, TAKE THE SMALLER and label it disputed. Never silently take the larger — the
    // larger is the number that makes a site look viable, so preferring it is the one error that
    // costs a site visit. 136 parcels read exact > 200% of recorded and 136 read exact < 50%;
    // 50 of those are >=25 acres and non-residential, i.e. large enough to change a decision.
    // The extremes are geometry defects, not assessor error: 471404900001500004 is recorded at
    // 308.5 ac against 5.3 ac of exact geometry.
    if (exactParcel != null && parcel > 0 &&
        (exactParcel < parcel * 0.5 || exactParcel > parcel * 2.0)) {
      const smaller = Math.min(parcel, exactParcel);
      return { acres: smaller,
               basis: `${smaller === exactParcel ? "exact geometry" : "recorded parcel area"} — ` +
                      `the smaller of two disagreeing measures (recorded ${parcel.toFixed(1)} ac ` +
                      `vs exact ${exactParcel.toFixed(1)} ac)`,
               disputed: true, mode };
    }
    if (exactParcel != null) return { acres: exactParcel, basis: "whole parcel, exact geometry", disputed: false, mode };
    return { acres: parcel, basis: "whole parcel, recorded acreage", disputed: false, mode };
  }
  const exact = p.exact_outdoor_acres == null ? null : Number(p.exact_outdoor_acres);
  const legacy = p.outdoor_acres == null ? null : Number(p.outdoor_acres);
  if (exact != null && p.footprints_intersecting === 0 && parcel > 0 && exact < parcel * 0.99)
    return { acres: parcel, basis: "parcel area (no footprints intersect)", disputed: true, mode };
  if (exact != null) return { acres: exact, basis: "outdoor space, exact (parcel − measured footprints)", disputed: false, mode };
  if (legacy != null) return { acres: legacy, basis: "outdoor space, approximate", disputed: false, mode };
  return { acres: parcel, basis: "parcel area", disputed: false, mode };
}
function jsMatches(p) {
  if (!classOk(p)) return false;
  if ($("f-mw").checked) {
    if (acreageOf(p).acres * V("f-density") < V("f-mw-val")) return false;
  }
  if ($("f-si").checked) {
    if (p.has_si_signal !== true) return false;
    const cut = recencyCutoff();
    // A MISSING date is not an old date. Measured over 7 counties: 165,494 parcels carry an SI
    // signal and only 935 (0.6%) carry an event date, so the old `(date || "") < cut` test
    // silently dropped 99.4% of them as if they were stale. That penalised sites for OUR
    // coverage gap — the exact thing the spec's availability-normalisation rule forbids.
    // Undated parcels now pass and are COUNTED, so the user sees what recency could not judge.
    if (cut && p.si_last_event_date && p.si_last_event_date < cut) return false;
    /* ⛔ UNDATED IS NOT OLD, and a bare `last_event >= cut` would delete it silently — NULL >= DATE
       evaluates to NULL, not TRUE. That is "unpublished is NULL, never 0" wearing a new costume, and
       it lands hardest on our biggest signal: 90% of tax-delinquency records carry no date at all.
       So undated records are KEPT BY DEFAULT and the user chooses (G9 ruling, 2026-08-17). */
    if (cut && !p.si_last_event_date) {
      if (!$("f-keepundated").checked) return false;
      state.undatedSI++;
    }
  }
  if ($("f-noflood").checked && p.sfha_flood === true) return false;
  if ($("f-nowet").checked && p.wetland_on_parcel === true) return false;
  if ($("f-noprot").checked && p.protected_land === true) return false;
  if ($("f-bonus").checked && !p.bonus_kinds) return false;
  if ($("f-dsub").checked && !(p._dsub_mi != null && p._dsub_mi <= V("f-dsub-mi") && p._dsub_kv >= V("f-dsub-kv"))) return false;
  if ($("f-dline").checked && !(p._dline_mi != null && p._dline_mi <= V("f-dline-mi"))) return false;
  return true;
}
/* ---------- G11: ONE ANSWER ABOUT A COUNTY, NOT TWO ------------------------------------------
   MEASURED 2026-08-19, and the earlier fix only reached one of four surfaces.

   `county_context.json` carries TWO descriptions of the same county side by side. The legacy
   `posture` block is a 4-value summary (quiet / active_discussion / contested / restricted) built
   upstream; the `action_summary` block is derived from the 9-value VERIFIED action vocabulary in
   `in_dc_actions_resolved`. When they disagree, the verified one is right:

     Cass        posture "quiet",  local_bans 0, has_local_restriction FALSE  -> holds a BAN
     Floyd       posture "quiet",  has_local_restriction FALSE                -> holds a MORATORIUM
     Huntington  posture "quiet",  has_local_restriction FALSE                -> holds a MORATORIUM
     Whitley     posture "quiet",  has_local_restriction FALSE                -> holds a MORATORIUM
     Clark       posture "quiet"                                              -> has APPROVED one
     Jasper      posture "quiet"                                              -> has APPROVED one

   ⛔ `local_bans` is **0 on all 92 counties** while the warehouse holds two ban-prohibition
   actions, so any test written against it can never fire. The county SHADING was moved onto
   `action_summary` earlier; the SCORE, this FILTER and the DOSSIER were not, so three surfaces
   still read the stale field and one of them calls a banned county the most permissive word we
   have. Same estate, two surfaces, different answers - the defect this project keeps re-finding.

   This helper is the single resolver. Everything that asks "what is this county's posture"
   goes through it, so the four surfaces cannot drift again. */
const POSTURE_RANK = { blocking: 3, watch: 2, neutral: 1, open: 0 };
function countyPosture(fips) {
  const c = state.ctx.by_fips[fips] || {};
  const po = c.posture || {};
  const sum = c.action_summary || null;
  // A verified BLOCKING action outranks anything the 4-value summary says. An expired moratorium
  // is deliberately NOT blocking - it is "watch" - because a lapsed pause that reads as live is a
  // false negative, and it sends a developer away from a county that has actually re-opened.
  const blocking = !!sum && sum.tone === "blocking";
  /* ⚠ THE TWO VOCABULARIES CAN EACH SEE A RESTRICTION THE OTHER MISSES, so the answer is the
     WORSE of them, not whichever one happens to be present. Cass shows the verified side alone
     (a ban, while the legacy block says "quiet"); MARION shows the legacy side alone (a live
     moratorium, while its verified headline is the milder "proposed"). Reading only one would
     let a restricted county through in one direction or the other. */
  const legacyRestricted = po.has_local_restriction === true
    || !!po.local_moratoriums || !!po.local_bans;
  return {
    tone: sum ? sum.tone : (legacyRestricted ? "blocking" : null),
    headline: sum ? sum.headline : (po.posture || null),
    why: sum ? sum.why : null,
    approved: !!(sum && sum.approved),
    nActions: sum ? sum.n : 0,
    blocking,                       // a VERIFIED blocking action - drives the wording
    legacyRestricted,               // the legacy flag alone - still evidence
    restricted: blocking || legacyRestricted,   // what every DECISION must use
    // kept for display only; never for a decision - see the measurement above
    legacy: po.posture || null,
    opposition: po.opposition_intensity,
    verified: !!sum,
  };
}
function countyOk(fips) {
  const c = state.ctx.by_fips[fips] || {};
  if ($("f-sent").checked) {
    const oi = c.posture?.opposition_intensity;
    if (oi == null || Number(oi) > V("f-sent-max")) return false;
  }
  // G11: was `c.posture?.has_local_restriction === true`, which is FALSE on Cass, Floyd,
  // Huntington and Whitley - so "exclude counties with a local restriction" kept four counties
  // that hold a ban or a moratorium. It now asks the verified vocabulary.
  if ($("f-norestrict").checked && countyPosture(fips).restricted) return false;
  return true;
}
/* G5: the rail collapses, so the filters in force must be visible somewhere that never does.
   Without this, a user who set a filter in a closed section sees an empty map and cannot tell a
   real "nothing matches" from a forgotten toggle. Reads the controls live, so it can never drift
   out of step with what is actually applied. */
function renderActiveFilters() {
  const el = $("m-active"); if (!el) return;
  const on = (id) => { const e = $(id); return e && e.checked; };
  const c = [];
  const uc = $("f-usecase");
  if (uc) c.push(uc.value === "bess" ? "battery storage" : "data center");
  if (on("f-mw")) c.push(`fits ${fmt(V("f-mw-val"))}+ MW @ ${V("f-density")} MW/acre`);
  const cls = [["f-ci", "commercial/industrial"], ["f-ag", "farmland"], ["f-vac", "undeveloped"]]
    .filter(([id]) => !on(id)).map(([, l]) => l);
  if (cls.length) c.push(`excluding ${cls.join(", ")}`);
  if (on("f-other")) c.push("incl. other non-residential");
  if (on("f-dsub")) c.push(`≤${V("f-dsub-mi")} mi of a ${V("f-dsub-kv")}+ kV substation`);
  if (on("f-dline")) c.push(`≤${V("f-dline-mi")} mi of a line`);
  if (on("f-si")) c.push("owner-motivation signal");
  if (on("f-recent")) c.push(`activity in ${V("f-recent-days")} days`);
  // an EXCLUSION must appear in the bar too - a collapsed section must never hide what it removed
  if (on("f-recent") && !$("f-keepundated").checked) c.push("undated records excluded");
  if (on("f-cand")) c.push("incl. candidate signals");
  if (on("f-noflood")) c.push("no flood zone");
  if (on("f-nowet")) c.push("no wetland");
  if (on("f-noprot")) c.push("no protected land");
  if (on("f-bonus")) c.push("tax-credit areas only");
  if (on("f-sent")) c.push(`opposition ≤ ${V("f-sent-max")}`);
  if (on("f-norestrict")) c.push("no local restriction");
  el.innerHTML = `<div class="chipbar"><b>Filters in effect</b>${
    c.map((x) => `<span class="chip">${x}</span>`).join("")}</div>`;
}

function applyFilters() {
  for (const [fips, feats] of state.loaded) {
    const ok = countyOk(fips);
    const keys = new Set();
    if (ok) for (const ft of feats) if (jsMatches(ft.properties)) keys.add(ft.properties.parcel_key);
    map.setFilter(`sites-${fips}-fill`, ["in", ["get", "parcel_key"], ["literal", [...keys]]]);
    map.setFilter(`sites-${fips}-line`, ["in", ["get", "parcel_key"], ["literal", [...keys]]]);
  }
  renderActiveFilters();
  renderDenominator();
  /* G96: a ranking painted under the PREVIOUS filters must not survive them, or the reader is
     looking at last question's answer over this question's parcels. clearRankedPaint() restores
     through applyParcelHighlight(), so the two never fight over fill-color. */
  if (state.rankPainted) clearRankedPaint(); else applyParcelHighlight();
}
for (const id of ["f-ci", "f-ag", "f-vac", "f-other", "f-mw", "f-mw-val", "f-density", "f-si",
  "f-recent", "f-recent-days", "f-keepundated", "f-noflood", "f-nowet", "f-noprot", "f-bonus",
  "f-dsub", "f-dsub-mi", "f-dsub-kv", "f-dline", "f-dline-mi", "f-sent", "f-sent-max", "f-norestrict",
  "f-usecase", "f-cand"])
  $(id).addEventListener("change", applyFilters);
renderActiveFilters();   // paint it once at boot, before any county has loaded
// Switching use case moves the density to that use case's default — but only if the user has
// not typed their own number, because silently overwriting a deliberate value is worse than
// leaving a stale default. Both defaults stay adjustable either way.
$("f-usecase").addEventListener("change", () => {
  const d = $("f-density"), cur = Number(d.value);
  if (cur === 4 || cur === 10) d.value = useCase() === "bess" ? 10 : 4;
  applyFilters();
});
$("f-cand").addEventListener("change", syncLayers);

/* ---------- layers panel ---------- */
/* G65 — ONE CONTROL PER FEATURE CLASS. Operator, 2026-08-19, after a management review:
   "every map feature should be togglable by nature."
   Measured before the change: 19 checkboxes covered 33 drawable classes, because five boxes were
   BUNDLES -- power plants with wind and solar, rail with two road classes, pipelines with
   compressors and storage, queue points with candidate buses, and six federal tax-credit
   geographies behind the single word "Tax-credit areas".
   This registry stays the single source of truth for layer state (G34): syncLayers() iterates it,
   so a layer added here without a box, or a box added without a layer, is the one thing that can
   still break "off means hidden". Add both, together, always. */
/* G77: ONE definition of the bus bands, read by the map paint AND by the legend, so a colour on
   the map can never mean something different in the key. Breaks are decisions, not percentiles. */
/* G94: one definition of the territory colours, shared by the fill, the outline and the legend.
   ⚠ The values are the payload's OWN vocabulary, read from it - upper case, spaced. */
const TERR_TYPES = [
  ["INVESTOR OWNED", "#2563eb", "Investor-owned - regulated by the IURC"],
  ["COOPERATIVE",    "#d97706", "Rural electric co-operative (REMC)"],
  ["MUNICIPAL",      "#059669", "Municipal utility"],
  ["NOT AVAILABLE",  "#94a3b8", "type not published by the source (74 of 145)"],
];
/* G112. The two data-centre pin tiers, named for the legend. ⚠ Colours must MATCH the fac-dc /
   fac-dc-city paint below; they are literals here because those layers are created inside the
   facilities loader, long after this runs. If a paint colour changes, change it here too.
   ⛔ The COUNTS are read from state.dcTiers, measured off the payload at load time -- never typed.
   The hardcoded "242" that used to sit here was already wrong: the payload ships 249. */
function dcTiers() {
  const t = state.dcTiers, n = t ? t.site + t.city : 0;
  const of = (x) => (t ? ` (${fmt(x)} of ${fmt(n)})` : "");
  return [
    ["#0ea5e9", `solid — the publisher gave a site coordinate${of(t && t.site)}`],
    ["#f59e0b", `hollow — CITY CENTROID only, not the facility${of(t && t.city)}`],
  ];
}
const TERR_FILL = ["match", ["get", "utility_type"],
                   ...TERR_TYPES.flatMap(([v, c]) => [v, c]), "#cbd5e1"];
const BUS_BANDS = [
  { colour: "#b91c1c", label: "0 MW - already at or over its limit" },
  { colour: "#f59e0b", label: "under 25 MW - below the datacenter floor" },
  { colour: "#84cc16", label: "25-99 MW" },
  { colour: "#16a34a", label: "100-299 MW" },
  { colour: "#065f46", label: "300 MW and above - hyperscale-capable" },
];
const LAYER_MAP = { "L-subs": ["grid-subs", "grid-subs-fp"], "L-lines": ["grid-lines", "grid-lines-unknown"],
  "L-bus": ["grid-bus", "grid-bus-label"],
  "L-pjm-queue": ["pjm-queue"], "L-pjm-bus": ["pjm-bus-est"],
  "L-gas-pipe": ["gas-lines"], "L-gas-comp": ["gas-compressor"], "L-gas-stor": ["gas-storage"],
  "L-terr": ["terr-fill", "terr-line", "terr-label"], "L-padus": ["env-padus"], "L-nonatt": ["env-nonatt"],
  "L-bonus-lit": ["env-bonus-lit"], "L-bonus-qct": ["env-bonus-qct"],
  "L-bonus-coal": ["env-bonus-coal"], "L-bonus-oz": ["env-bonus-oz"],
  "L-bonus-ec": ["env-bonus-ec"], "L-bonus-hab": ["env-bonus-hab"],
  "L-watershed": ["water-ws-fill", "water-ws-line"], "L-waterstress": ["water-stress-fill"],
  "L-dc": ["fac-dc", "fac-dc-city"],
  "L-fac-plant": ["fac-plant"], "L-fac-solar": ["fac-solar"], "L-fac-wind": ["fac-wind"],
  "L-log-rail": ["log-lines-rail"], "L-log-road1": ["log-road1"], "L-log-road2": ["log-road2"],
  // G72 land-status and airspace gates. One control per KIND, never one "land constraints" tick:
  // a military installation, a sovereign boundary and an altitude ceiling are three different
  // conversations with three different bodies, and collapsing them is the same volume-over-value
  // failure that put an energy-community adder and a critical-habitat blocker on one checkbox.
  "L-mil": ["gate-mil"], "L-tribal": ["gate-tribal"], "L-sua": ["gate-sua"],
  "L-obst": ["gate-obst"] };
/* ---------- context layers: 1 MB of geometry, so fetched on FIRST USE, not at boot ----------
   Six layers share one payload. The first toggle loads it and builds all six; later toggles
   just flip visibility. A layer that has not loaded yet reports so rather than silently
   doing nothing — the failure mode the logistics layer had for weeks. */
// Schools and weather stations were removed by operator ruling 2026-08-15 — schools were staged
// for a separate Illinois experiment, and a GHCN station location is not something a siter acts
// on. Both are recorded as waivers on the Data page rather than silently dropped.
// ⛔ `L-frpp` / `ctx-frpp` REMOVED 2026-08-20 (G97), NOT just relabelled. It drew all 1,594
//    federal points under a checkbox reading "Federal surplus property" while 1,540 of them are
//    Current Mission Need. `wired-fedprop` replaces it and states each point's actual status,
//    and `wired-surplus` carries the 20 that are genuinely a signal.
//    ⚠ Leaving the key here while deleting the checkbox from index.html is what took the whole
//    app down for one cycle: the loop below did `$(box).addEventListener` on a null. Two changes
//    that were each fine and were fatal together — trap 3, again.
const CONTEXT_LAYERS = { "L-ghgrp": "ctx-ghgrp" };

/* ---------- G110: THE ENVIRONMENTAL GATES YOU CAN FILTER ON, YOU CAN NOW SEE ------------------
   Operator, 2026-08-19: *"The flood zones, wetlands, and the protected land should also show the
   map layer when checked, not just used as a filtering tool."*

   ⛔ IT WAS WORSE THAN "NOT SHOWN". `LAYER_MAP` had NO flood layer and NO wetland layer at all, so
   a reader could exclude every parcel touching a floodplain and had no way to look at one. The
   page even carried a hint explaining why: the sources are 804 MB and 1.3 GB. That was true and
   it was the wrong test -- nobody had measured the DECISION-RELEVANT SUBSET, which is 4.7 MB
   gzipped for both layers together.

   4.7 MB is real weight, so it is fetched on FIRST TOGGLE like the context layers, never at boot.
   ⚠ Both layers are SUBSETS and both cuts are printed on the control from the payload's own
   `coverage` block -- never restated here, or the disclosure and the data would drift. */
const ENVGATE_LAYERS = { "L-flood": "env-flood", "L-wet": "env-wet" };

/* ---------- G39: THE SCREENER, ON THE MAP ----------------------------------------------------
   Operator, 2026-08-18: *"we essentially need to wire the Site Screener to the map, since we
   would like to visibly see those sites geographically around the map layers."*

   The screener ranked sites in a table with no geographic expression, so a reader could not see
   whether the top sites CLUSTER, or how they sit against transmission, water and county posture -
   which is most of what makes a shortlist believable.

   ⚠ MEASURED FIRST, AND THE COVERAGE IS PARTIAL: of 51,493 screener sites, **20,040 (38.9%)
   carry a lat/lon**. The rest are real sites we simply hold no point for. The layer says so on
   the control rather than quietly drawing a subset, because "the screener's sites" and "the
   screener's sites we can plot" are different claims and only one of them is true here.

   3.7 MB of payload, so it is fetched on FIRST TOGGLE, never at boot - the same rule the context
   layers follow. Sized by what the parcel can host, because on a map the useful question is
   "where are the BIG ones", not "where are there any". */
state.scrLoaded = false; state.scrLoading = null;
async function ensureScreenerLayer() {
  if (state.scrLoaded) return true;
  if (state.scrLoading) return state.scrLoading;
  state.scrLoading = (async () => {
    /* ⚠ NOT `d`. audit_frontend binds the fetchGz variable name and then scans every `<var>.key`
       in the file to check it against the payload's real keys - so a one-letter name in a
       2,500-line file collides with every other `d.something` and reports keys this code never
       read. The audit was right to complain: a one-letter name for a payload is bad here. */
    const scr = await fetchGz("data/screener.json.gz");
    const sites = (scr.sites || []).filter((x) => x.lat != null && x.lon != null);
    state.scrTotal = (scr.sites || []).length;
    state.scrPlotted = sites.length;
    map.addSource("scr", { type: "geojson", data: { type: "FeatureCollection",
      features: sites.map((x) => ({ type: "Feature",
        geometry: { type: "Point", coordinates: [Number(x.lon), Number(x.lat)] },
        properties: { parcel_key: x.parcel_key, fips: x.county_fips, county: x.county_name,
                      mw_dc: Number(x.mw_dc) || 0, acres: Number(x.parcel_acres) || 0,
                      sig: x.has_signal ? 1 : 0, wd_mw: x.wd_mw == null ? -1 : Number(x.wd_mw) } })) } });
    map.addLayer({ id: "scr-pts", type: "circle", source: "scr", layout: { visibility: "none" },
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["get", "mw_dc"], 0, 3, 100, 5, 500, 8, 2000, 12],
        /* Amber where the owner shows a public reason to sell, slate where not. That is the one
           distinction a siter acts on differently - a cold approach versus a warm one. */
        "circle-color": ["case", ["==", ["get", "sig"], 1], "#d97706", "#475569"],
        "circle-opacity": 0.75,
        "circle-stroke-width": 1, "circle-stroke-color": "#ffffff" } });
    map.on("click", "scr-pts", (e) => {
      if (state.measure.on) return;
      const q = e.features[0].properties;
      openScreenerSite(String(q.fips), String(q.parcel_key), q);
    });
    state.scrLoaded = true;
    return true;
  })();
  return state.scrLoading;
}

/* A screener point is a POINTER to a parcel, not a copy of it. Clicking one loads that county and
   opens the real parcel panel, so there is exactly one place a parcel is described. */
async function openScreenerSite(fips, key, fallback) {
  const ok = await ensureCountyLoaded(fips);
  const feats = ok ? (state.loaded.get(fips) || []) : [];
  const ft = feats.find((f) => f.properties && f.properties.parcel_key === key);
  if (ft) { highlightParcel(ft); return openParcelEvidence(ft.properties, fips); }
  show("Screener site", `<div class="sowhat">This site is in the screener's list, but its parcel
    record did not load for county ${escHtml(fips)}, so the full evidence panel cannot be shown.
    What the screener holds:</div>
    <table class="ev">
      ${row("County", fallback && fallback.county)}
      ${row("Parcel", key)}
      ${row("Fits (MW, data center)", fallback && fallback.mw_dc)}
      ${row("Acres", fallback && fallback.acres)}
      ${row("Owner shows a reason to sell", fallback && fallback.sig ? "yes" : "no",
            "measured — no signal on this parcel")}
    </table>`, `${fips}|${key}`);
}
/* G34 -- ONE REGISTRY, ONE SYNC PATH. Two registries for one concept let "off means hidden" be
   enforced for some layers and not others. It is the same defect class as the [:12] clip in
   build_census_wires.py: a PARTIAL ENUMERATION that silently leaves the remainder in a stale
   state -- except here the remainder was visible map geometry. `grid` set "L-fac": 1 and no other
   preset mentioned L-fac at all, so wind and solar kept drawing after switching to Environmental,
   which is exactly what the operator reported. Every preset now states every layer, unstated boxes
   default to OFF rather than persisting, and a gap is reported loudly at boot. */
/* ---------- G72/G80/G97/G98: the objects that reached NO surface, as layers -------------------
   Six new controls, one payload, loaded on FIRST TOGGLE like the context and env-gate layers.

   ⭐ EACH ONE HAS TO EARN ITS PLACE (the governing principle is a veto, not a polish step):
     water        a 100 MW evaporative campus wants 1-2 MGD of make-up water. Only bodies you
                  could actually permit an intake against are drawn - named, or over 12 acres.
     fedprop      ⛔ REPLACES the old "Federal surplus property" control, which drew 1,594 points
                  of which 1,540 are Current Mission Need. See the note on `L-fedprop`.
     surplus      the 20 that ARE declared surplus or unutilised - an owner publicly stating it
                  does not want the land, with no inference at all.
     withdrawn    a landowner who signed an interconnection agreement, then had the project
                  cancelled: consent already given, grid position already studied.
     campus       colleges (workforce) and USDA-inspected food plants (heavy industrial sites
                  with big power and water service already in the ground).                    */
/* ⛔ NO OBSTACLE LAYER HERE, AND THAT IS DELIBERATE. The first draft of this block added one —
   and `L-obst` / `gate-obst` already draws the same 4,590 FAA records from gates.geojson.gz,
   with a click handler. Two copies of one layer is §2.15c: they WILL drift and the loser is
   invisible. The one thing the new draft had that the old layer lacked — that 1,816 of these
   are WINDMILLS, and an existing turbine is proof that this exact ground already cleared
   landowner consent, an interconnection and a local permit — was added to `gate-obst` instead. */
const WIRED_LAYERS = {
  "L-water": ["wired-waterbody", "wired-flowline"],
  "L-fedprop": ["wired-fedprop"],
  "L-surplus": ["wired-surplus"],
  "L-withdrawn": ["wired-withdrawn"],
  "L-campus": ["wired-college", "wired-foodplant"],
};
const ALL_LAYER_BOXES = [...Object.keys(LAYER_MAP), ...Object.keys(CONTEXT_LAYERS),
                         ...Object.keys(ENVGATE_LAYERS), ...Object.keys(WIRED_LAYERS),
                         "L-planned",
                         "L-parcels", "L-screener"];
state.ctxLoaded = false; state.ctxLoading = null;
async function ensureContextLayers() {
  if (state.ctxLoaded) return true;
  if (state.ctxLoading) return state.ctxLoading;
  state.ctxLoading = (async () => {
    const fc = await fetchGz("data/context.geojson.gz");
    map.addSource("ctx", { type: "geojson", data: fc });
    map.addLayer({ id: "ctx-ghgrp", type: "circle", source: "ctx",
      filter: ["==", ["get", "layer"], "ghgrp"], layout: { visibility: "none" },
      paint: { "circle-radius": 5, "circle-color": "#dc2626", "circle-opacity": 0.7,
               "circle-stroke-color": "#7f1d1d", "circle-stroke-width": 1 } });
    for (const id of Object.values(CONTEXT_LAYERS)) {
      map.on("mousemove", id, (e) => showTip(e, ctxTip(e.features[0].properties)));
      map.on("mouseleave", id, hideTip);
      map.on("click", id, (e) => { if (!state.measure.on) ctxEvidence(e.features[0].properties); });
    }
    state.ctxLoaded = true;
    return true;
  })();
  return state.ctxLoading;
}
function ctxTip(p) {
  if (p.layer === "ghgrp") return `GHGRP emitter: ${p.name || "?"}` +
    (p.co2e_latest ? ` · ${fmt(Math.round(p.co2e_latest))} t CO2e (${p.co2e_year})` : "");
  return p.layer;
}

/* ---------- G72/G80/G97/G98 layers, loaded on first toggle ------------------------------------ */
state.wiredLoaded = false; state.wiredLoading = null;
const SURPLUS_PLAIN = {
  declared_excess: "DECLARED SURPLUS — a Report of Excess or a Determination to Dispose is on file",
  unutilized_not_declared: "unutilised — nobody has used it, but no disposal is filed",
  underutilized_not_declared: "underutilised — partly used, no disposal filed",
  disposed: "already disposed of — a comparable, not a lead",
  in_use: "in use — Current or Future Mission Need. NOT surplus.",
};
async function ensureWiredLayers() {
  if (state.wiredLoaded) return true;
  if (state.wiredLoading) return state.wiredLoading;
  state.wiredLoading = (async () => {
    const [fc1, fc2] = await Promise.all([
      fetchGz("data/wired.geojson.gz"), fetchGz("data/wired2.geojson.gz")]);
    map.addSource("wired", { type: "geojson", data: fc1 });
    map.addSource("wired2", { type: "geojson", data: fc2 });
    const hid = { visibility: "none" };
    map.addLayer({ id: "wired-waterbody", type: "fill", source: "wired",
      filter: ["==", ["get", "layer"], "waterbody"], layout: hid,
      paint: { "fill-color": "#2563eb", "fill-opacity": 0.28,
               "fill-outline-color": "#1e40af" } });
    map.addLayer({ id: "wired-flowline", type: "line", source: "wired",
      filter: ["==", ["get", "layer"], "flowline"], layout: hid,
      paint: { "line-color": "#3b82f6", "line-width": 1.1, "line-opacity": 0.75 } });
    map.addLayer({ id: "wired-fedprop", type: "circle", source: "wired",
      filter: ["==", ["get", "layer"], "fedprop"], layout: hid,
      paint: { "circle-radius": 4,
               "circle-color": ["case", ["==", ["get", "is_si_signal"], true], "#d97706", "#0d9488"],
               "circle-opacity": 0.75 } });
    map.addLayer({ id: "wired-surplus", type: "circle", source: "wired",
      filter: ["all", ["==", ["get", "layer"], "fedprop"],
               ["==", ["get", "is_si_signal"], true]], layout: hid,
      paint: { "circle-radius": 9, "circle-color": "#d97706", "circle-opacity": 0.85,
               "circle-stroke-color": "#7c2d12", "circle-stroke-width": 2 } });
    map.addLayer({ id: "wired-withdrawn", type: "circle", source: "wired",
      filter: ["==", ["get", "layer"], "withdrawn"], layout: hid,
      paint: { "circle-radius": ["interpolate", ["linear"], ["coalesce", ["get", "mw"], 0],
                                 0, 4, 100, 7, 500, 12, 1000, 16],
               "circle-color": "#9333ea", "circle-opacity": 0.6,
               "circle-stroke-color": "#581c87", "circle-stroke-width": 1 } });
    map.addLayer({ id: "wired-college", type: "circle", source: "wired2",
      filter: ["==", ["get", "layer"], "college"], layout: hid,
      paint: { "circle-radius": 4, "circle-color": "#0891b2", "circle-opacity": 0.8 } });
    map.addLayer({ id: "wired-foodplant", type: "circle", source: "wired2",
      filter: ["==", ["get", "layer"], "foodplant"], layout: hid,
      paint: { "circle-radius": 4, "circle-color": "#b45309", "circle-opacity": 0.8 } });
    // ⛔ `wired-gridplan` WAS HERE AND IS RETIRED - G130, 2026-08-20f. It drew the located
    // utility grid plans as SOLID FILLED CIRCLES, the same primitive this console uses for real
    // substations, so planned work read as built work. It also showed nothing from PJM RTEP or
    // MISO MTEP. The `L-planned` group supersedes it: FOUR sources - PJM RTEP, MISO MTEP, the
    // MISO DPP-2025 interconnection study and the IURC grid plans - violet / hollow / dashed,
    // with an uncertainty ring per item.
    // ⚠ NO COUNT IS TYPED HERE ANY MORE. This comment said "700 placed items" and G130's second
    // pass moved it to 971; a figure in a comment is a figure nothing re-measures. The live
    // number is on the grid page, generated.
    // ⚠ The checkbox, the WIRED_LAYERS entry and this addLayer were removed in ONE change.
    // Removing the control while a layer registry still named it is exactly how the L-frpp
    // edit threw during boot and rendered the whole page blank.
    // ⛔ EVERY layer gets BOTH a hover and a click. G105's precedent is layers that were drawn
    //    and unclickable for weeks; adding six more without handlers would repeat it exactly.
    for (const ids of Object.values(WIRED_LAYERS)) for (const id of ids) {
      map.on("mousemove", id, (e) => showTip(e, wiredTip(e.features[0].properties)));
      map.on("mouseleave", id, hideTip);
      map.on("click", id, (e) => { if (!state.measure.on) wiredEvidence(e.features[0].properties); });
    }
    state.wiredLoaded = true;
    return true;
  })();
  return state.wiredLoading;
}
function wiredTip(p) {
  switch (p.layer) {
    case "waterbody": return `${p.name || p.kind || "waterbody"} — ${fmt(p.acres)} acres`;
    case "flowline": return `${p.name} — ${p.km} km reach`;
    case "fedprop": return `${p.agency || "federal property"} — ` +
      (SURPLUS_PLAIN[p.surplus_class] || p.surplus_class);
    case "withdrawn": return `${p.iso} ${p.project_id} — ${fmt(p.mw)} MW ${p.resource_type || ""}` +
      ` withdrawn ${p.wd_date || "?"}`;
    case "gridplan": return `${p.utility}: ${p.asset_name || p.station_name || "planned work"}` +
      (p.voltage_kv ? ` — ${p.voltage_kv} kV` : "") +
      (p.in_service_year ? `, in service ${p.in_service_year}` : "");
    case "college": return `${p.name} (${p.city || "?"})`;
    case "foodplant": return `${p.name} — USDA-inspected plant`;
    default: return p.layer;
  }
}
/* one entry per layer: [table, what it is, ⭐ what it changes about a decision] */
const WIRED_PROV = {
  waterbody: ["in_nhd_waterbody_geom", "NHD waterbodies, named or over 12 acres.",
    "A 100 MW evaporative-cooled campus consumes roughly 1–2 million gallons a day of make-up " +
    "water. The question is not whether water is nearby but whether a body is big enough to " +
    "permit an intake against — farm ponds are deliberately not drawn, because showing them " +
    "would answer the question wrongly in the reassuring direction."],
  flowline: ["in_nhd_flowline_geom", "Named NHD reaches of at least 1 km.",
    "163,976 flowlines are held; an unnamed 500 m ditch is not an intake, so only the 7,202 " +
    "named reaches over a kilometer are drawn."],
  fedprop: ["in_si_gov_surplus_v2", "Every federally-held property in Indiana, with what it IS.",
    "⛔ THIS CONTROL USED TO SAY “Federal surplus property” AND DRAW ALL 1,594 POINTS. Measured: " +
    "1,540 of them are Current Mission Need — the label was true of 17. Each point now states " +
    "its own asset status, and the 20 that are genuinely declared surplus or unutilised have " +
    "their own control beside this one."],
  withdrawn: ["in_si_queue_withdrawn", "Cancelled interconnection requests, placed.",
    "A landowner who signed an interconnection agreement already consented to host energy " +
    "infrastructure and now has a studied grid position with no project on it — willingness " +
    "revealed by preference rather than inferred from distress. ⚠ The point is the " +
    "INTERCONNECTION point, not the generator parcel; those can be a mile apart down a gen-tie."],
  gridplan: ["in_grid_plans_located",
    "Planned utility work from IURC TDSIC and IRP filings, placed on the station it names.",
    "⭐ THIS IS CAPACITY THAT DOES NOT EXIST YET, and it is the only layer here that is about the " +
    "FUTURE. A substation being rebuilt to a higher voltage in 2027 changes what a site beside it " +
    "can ask for in 2028. ⚠ Most of the 618 planned items name no station the gazetteer holds; " +
    "those name only a utility and are placed to that utility's service TERRITORY on the grid " +
    "page rather than invented into a point here. ⛔ Cost is deliberately NULL on every row: the " +
    "workpaper's numeric columns arrive unlabelled, and guessing which one is dollars would print " +
    "a coin flip."],
  college: ["in_candidate_sites_colleges", "Degree-granting institutions.",
    "Operations staffing. A campus within commuting distance is where technicians come from, " +
    "and it is also a large institutional landowner."],
  foodplant: ["in_fsis_establishments", "USDA-inspected meat and poultry plants.",
    "Heavy industrial sites with large electrical service, large water service and a discharge " +
    "permit already in the ground — the cheapest kind of brownfield to convert, and a pool that " +
    "closes often enough to be worth watching."],
};
function wiredEvidence(p) {
  const [tbl, what, sowhat] = WIRED_PROV[p.layer] || ["", "", ""];
  const skip = new Set(["layer"]);
  let extra = "";
  if (p.layer === "fedprop") {
    extra = `<div class="sowhat"><b>${SURPLUS_PLAIN[p.surplus_class] || p.surplus_class}</b>` +
      (p.assets_at_point > 1
        ? ` · FRPP reports per ASSET, and ${p.assets_at_point} federal assets share this exact
            coordinate — one installation, not ${p.assets_at_point} sites.` : "") +
      (p.years_underutilized ? ` · unused for <b>${p.years_underutilized} years</b>.` : "") +
      `</div>`;
  }
  if (p.layer === "withdrawn") {
    extra = `<div class="sowhat">` +
      (p.parcel_key
        ? `A parcel sits under this point — <b>${p.parcel_key}</b>${p.parcel_acres
            ? `, ${fmt(Math.round(p.parcel_acres))} acres` : ""}. ⚠ That is a LEAD, not the site:
           the queue point is where the project would have interconnected, which can be a mile
           from the generator.`
        : `No parcel sits under this point, so this is vicinity-grade only.`) +
      (p.years_since_withdrawal != null
        ? ` Withdrawn <b>${p.years_since_withdrawal} year${p.years_since_withdrawal === 1 ? "" : "s"}
            ago</b> — recency governs, because a 2006 cancellation says little about today's owner.`
        : "") + `</div>`;
  }
  const rows_ = Object.entries(p).filter(([k]) => !skip.has(k))
    .map(([k, v]) => row(landPlainLabel(k), v)).join("");
  show(wiredTip(p), `${extra}<table>${rows_}</table>
    <div class="sowhat">${sowhat}</div>
    <div class="prov">${prov(tbl)} · ${what}</div>`);
}
/* the payload keys are database columns; a reader should not have to decode them */
const WIRED_LABELS = {
  agl_ft: "height above ground (ft)", amsl_ft: "height above sea level (ft)",
  assets_at_point: "federal assets at this coordinate", surplus_class: "status",
  is_si_signal: "counts as an owner-motivation signal", years_underutilized: "years unused",
  ptype: "property type", use: "current use", excess_date: "reported excess on",
  mw: "capacity requested (MW)", wd_date: "withdrawn on", poi_name: "interconnection point",
  years_since_withdrawal: "years since withdrawal", placement_grain: "how precisely it is placed",
  location_method: "how it was placed", parcel_key: "parcel under the point",
  parcel_acres: "that parcel's acreage", resource_type: "what it would have been",
  counterparty: "transmission owner", km: "reach length (km)", acres: "surface acres",
  sqkm: "surface area (km²)", kind: "type", verified: "FAA verification",
};
const landPlainLabel = (k) => WIRED_LABELS[k] || k.replace(/_/g, " ");
const CTX_PROV = {
  // NOTE: adjacent string literals do NOT concatenate in JavaScript (that is Python). Writing
  // them that way here threw `SyntaxError: Unexpected string` and took the ENTIRE app down —
  // the map never initialised. Use explicit + or one string.
  ghgrp: ["vw_ghgrp_emissions_located",
    "EPA greenhouse-gas reporters: 263 Indiana facilities — neighbours already holding air " +
    "permits. Reported CO2e now rides on the pin: the emissions sat in in_ghgrp_emissions with " +
    "no geography and were joined on facility_id (9,310/9,310). 211 of the 263 pins carry a " +
    "latest-year figure; the rest report no emissions in the most recent year held and show " +
    "nothing rather than a zero. in_ghgrp_emitter_facilities is a subset (all 246 of its ids " +
    "are among these) and supplies the reporting year."],
};
function ctxEvidence(p) {
  const [tbl, note] = CTX_PROV[p.layer] || ["", ""];
  const rows_ = Object.entries(p).filter(([k]) => k !== "layer")
    .map(([k, v]) => row(k, v)).join("");
  show(ctxTip(p), `<table>${rows_}</table>
    <div class="prov">${prov(tbl)}<br>${note}</div>`);
}
$("L-screener").addEventListener("change", async (e) => {
  if (e.target.checked) {
    $("L-screener-note").textContent = "loading the screener's sites…";
    try { await ensureScreenerLayer(); } catch (err) {
      $("L-screener-note").textContent = "could not load the screener payload";
      e.target.checked = false; return;
    }
    /* Say what is on screen and what is NOT. 38.9% coverage silently drawn would read as "these
       are the screener's sites" when it is a subset of them. */
    $("L-screener-note").innerHTML = `${fmt(state.scrPlotted)} of ${fmt(state.scrTotal)} screener
      sites carry a location and are drawn (${(100 * state.scrPlotted / state.scrTotal).toFixed(0)}%).
      <b>Amber = the owner shows a public reason to sell.</b> Size is what the parcel could host.`;
  }
  syncLayers();
});

/* ---------- G110: the flood / wetland geometry, loaded on first use ---------------------------
   ⚠ FILL-ONLY WOULD BE UNREADABLE. A translucent fill over a translucent fill (these two overlap
   constantly - river floodplains ARE wetlands) reads as one muddy colour, so each carries a line
   as well and the fills stay light. */
state.envLoaded = false; state.envLoading = null; state.envCoverage = null;
async function ensureEnvGateLayers() {
  if (state.envLoaded) return true;
  if (state.envLoading) return state.envLoading;
  state.envLoading = (async () => {
    /* ⚠ NOT named `fc`. `ensureContextLayers()` above uses `const fc` for a DIFFERENT payload,
       and audit_frontend.py resolves `<var>.<key>` reads against whichever payload that variable
       name was last bound to -- so a second `fc` made it report `.coverage` as a missing key on
       context.geojson.gz. The audit is right to be simple here; the fix is a distinct name. */
    const envFc = await fetchGz("data/envgates.geojson.gz");
    state.envCoverage = envFc.coverage || null;
    map.addSource("envgates", { type: "geojson", data: envFc });
    /* ⛔ Drawn UNDER the parcel layers, never over them. These are context for a site, and a
       hazard polygon painted on top of the parcel you are evaluating hides the subject. */
    const before = map.getLayer("county-line") ? "county-line" : undefined;
    map.addLayer({ id: "env-flood", type: "fill", source: "envgates",
      filter: ["==", ["get", "layer"], "flood"], layout: { visibility: "none" },
      paint: { "fill-color": "#38bdf8", "fill-opacity": 0.28,
               "fill-outline-color": "#0369a1" } }, before);
    map.addLayer({ id: "env-wet", type: "fill", source: "envgates",
      filter: ["==", ["get", "layer"], "wetland"], layout: { visibility: "none" },
      paint: { "fill-color": "#14b8a6", "fill-opacity": 0.3,
               "fill-outline-color": "#0f766e" } }, before);
    for (const id of Object.values(ENVGATE_LAYERS)) {
      map.on("mousemove", id, (e) => showTip(e, envGateTip(e.features[0].properties)));
      map.on("mouseleave", id, hideTip);
      map.on("click", id, (e) => { if (!state.measure.on) envGateEvidence(e.features[0].properties); });
    }
    state.envLoaded = true;
    return true;
  })();
  return state.envLoading;
}
/* FEMA's zone codes are the vocabulary of the source, not of the reader. A is the 1% floodplain
   with no studied elevation; AE is the same with a Base Flood Elevation published; AO is sheet
   flow; V/VE is coastal wave action (Indiana has 83 VE polygons, all on Lake Michigan). */
const FLD_ZONE_PLAIN = {
  A: "1% annual-chance floodplain (no base flood elevation published)",
  AE: "1% annual-chance floodplain, base flood elevation published",
  AH: "1% annual-chance shallow flooding, 1-3 ft ponding",
  AO: "1% annual-chance shallow flooding, sheet flow",
  VE: "coastal high-hazard area - wave action, base flood elevation published",
  V: "coastal high-hazard area - wave action",
};
function envGateTip(p) {
  if (p.layer === "flood")
    return `Flood: ${FLD_ZONE_PLAIN[p.zone] || `zone ${p.zone || "?"}`}`;
  return `Wetland${p.acres != null ? ` · ${fmt(p.acres)} acres` : ""}` +
         (p.wetland_type ? ` · ${p.wetland_type}` : "");
}
function envGateEvidence(p) {
  const cov = state.envCoverage || {};
  const c = p.layer === "flood" ? (cov.flood || {}) : (cov.wetland || {});
  const rows_ = p.layer === "flood"
    ? row("Zone", FLD_ZONE_PLAIN[p.zone] || p.zone) +
      row("FEMA zone code", p.zone) +
      /* ⚠ -9999 IS FEMA'S NULL SENTINEL, and it arrives as the STRING "-9999.0". A literal
         `!== "-9999"` test sailed straight past the decimal form and printed a base flood
         elevation of minus 9,999 feet -- the same shape as the `00/00/0000` date sentinel.
         Compare numerically, and treat anything at or below -9000 as not published. */
      row("Base flood elevation",
          (p.bfe != null && Number(p.bfe) > -9000) ? `${p.bfe} ft` : null,
          "not published for this polygon") +
      row("County", p.county)
    : row("Size", p.acres != null ? `${fmt(p.acres)} acres` : null, "not stated") +
      row("NWI class", p.wetland_type);
  const what = p.layer === "flood"
    ? "A mapped Special Flood Hazard Area. Building here triggers floodplain permitting, " +
      "elevation or floodproofing requirements, and federal flood insurance obligations on a " +
      "federally-backed loan. It is a cost and a schedule item, not usually an absolute stop."
    : "A National Wetlands Inventory polygon. Disturbing it needs a Clean Water Act section 404 " +
      "permit from the Army Corps, which is the single slowest federal approval most sites meet.";
  show(envGateTip(p), `<table>${rows_}</table>
    <div class="sowhat">${what}</div>
    <div class="hint">⚠ <b>Boundaries are simplified to about ${escHtml(String(cov.simplify_m || 60))} m</b>
      for drawing, so an edge here can sit that far from the surveyed line. To decide whether a
      SPECIFIC parcel is affected, use the per-parcel flag in the site's evidence panel, which is
      measured against the full-resolution source.</div>
    <div class="prov">${prov(p.layer === "flood" ? "in_flood" : "in_wetlands")}<br>
      Drawn: ${fmt(c.drawn)} of ${fmt(c.source_rows)} — ${escHtml(c.rule || "")}</div>`);
}
for (const [box, layerId] of Object.entries(ENVGATE_LAYERS)) {
  if (!$(box)) continue;
  $(box).addEventListener("change", async (e) => {
    const note = $(`${box}-note`);
    if (e.target.checked) {
      if (note) note.textContent = "loading…";
      try { await ensureEnvGateLayers(); } catch (err) {
        if (note) note.textContent = "could not load the layer";
        e.target.checked = false; syncLayers(); return;
      }
      /* The cut is printed from the payload, so the control cannot claim coverage the data does
         not have. This is the G58 rule: a subset that does not announce itself is a lie. */
      const c = (state.envCoverage || {})[box === "L-flood" ? "flood" : "wetland"] || {};
      if (note) note.innerHTML = `Drawing <b>${fmt(c.drawn)}</b> of ${fmt(c.source_rows)}. ` +
        `${escHtml(c.rule || "")}. <span class="hint">${escHtml(c.excluded || "")}</span>`;
    } else if (note) note.textContent = "";
    syncLayers();
  });
}

for (const [box, layerId] of Object.entries(CONTEXT_LAYERS)) {
  // ⛔ GUARD, ADDED AFTER THIS EXACT LINE TOOK THE WHOLE APP DOWN. A layer registry entry whose
  //    checkbox has been removed from the HTML returns null here, and an unguarded
  //    .addEventListener throws during boot — before the map is built, so the page renders
  //    nothing at all and the cause is nowhere near the symptom. Every other registry loop in
  //    this file already guards; this one did not.
  if (!$(box)) { console.warn(`CONTEXT_LAYERS names ${box}, which is not on this page`); continue; }
  $(box).addEventListener("change", async (e) => {
    if (e.target.checked) {
      $(box).parentElement.style.opacity = "0.55";
      await ensureContextLayers();
      $(box).parentElement.style.opacity = "";
    }
    if (map.getLayer(layerId))
      map.setLayoutProperty(layerId, "visibility", $(box).checked ? "visible" : "none");
  });
}

/* ---------- G52: THE KEY FOR WHAT IS CURRENTLY DRAWN --------------------------------------------
   Operator, 2026-08-18: *"place a legend or key in the corner of the map for what the map is
   currently displaying."* Urgent since G65, which took the map from 19 controls to 30 - thirty
   toggles with no key is worse than nineteen.

   ⛔ It is DERIVED, never written down twice. The label comes from the checkbox's own <label>, and
   the colour is read back off the map with getPaintProperty(). A hand-maintained legend is a second
   copy of the palette and WILL drift - the same shape as G34's two layer registries and the
   duplicated eligibility vocabulary. Nothing here needs touching when a layer is added: put the box
   in ALL_LAYER_BOXES and it appears.

   A layer whose colour is a MapLibre expression (transmission lines, coloured by kV band; the
   data-centre pins, tiered by location precision) has no single swatch, and says so rather than
   showing one of its colours and implying the rest. */
const PAINT_KEYS = ["circle-color", "line-color", "fill-color"];
function layerSwatch(layerIds) {
  for (const id of layerIds) {
    if (!map.getLayer(id)) continue;
    for (const k of PAINT_KEYS) {
      let v;
      try { v = map.getPaintProperty(id, k); } catch (e) { continue; }
      if (typeof v === "string") return { colour: v, banded: false };
      if (Array.isArray(v)) return { colour: null, banded: true };
    }
  }
  return null;                                   // not on the map yet (lazy layer) - say so
}
function renderLayerLegend() {
  const body = $("legend-body"), count = $("legend-count");
  if (!body) return;
  const rows = [];
  for (const box of ALL_LAYER_BOXES) {
    const el = $(box);
    if (!el || !el.checked) continue;
    const lbl = el.closest("label");
    // the control's own words, minus the parenthetical count - the legend is a key, not a repeat
    let name = lbl ? lbl.textContent.replace(/\s+/g, " ").trim() : box;
    name = name.replace(/\s*\((?:[\d,]+|[\d,]+\s*[^)]*)\)\s*$/, "").trim();
    const ids = LAYER_MAP[box] || (CONTEXT_LAYERS[box] ? [CONTEXT_LAYERS[box]]
              : ENVGATE_LAYERS[box] ? [ENVGATE_LAYERS[box]]
              : box === "L-screener" ? ["scr-pts"] : []);
    const sw = ids.length ? layerSwatch(ids) : null;
    const chip = sw === null
      ? `<i class="lg-sw lg-pending" title="not loaded yet"></i>`
      : sw.banded
        ? `<i class="lg-sw lg-banded" title="several colors - banded by value"></i>`
        : `<i class="lg-sw" style="background:${escHtml(sw.color)}"></i>`;
    rows.push(`<div class="lg-row">${chip}<span>${escHtml(name)}</span>` +
              (sw && sw.banded && box !== "L-bus" ? ` <span class="hint">banded</span>` : "") +
              (sw === null ? ` <span class="hint">loading</span>` : "") + `</div>`);
    /* G77: "banded" is not a key. Where the bands carry the whole meaning of the layer - and on
       the bus layer they ARE the answer to "can this host my project" - spell them out. Read from
       the same BUS_BANDS the paint uses, so the key cannot drift from the map. */
    if (box === "L-terr")
      for (const [, colour, label] of TERR_TYPES)
        rows.push(`<div class="lg-row" style="margin-left:14px">` +
                  `<i class="lg-sw" style="background:${color}"></i>` +
                  `<span class="hint">${escHtml(label)}</span></div>`);
    if (box === "L-bus")
      for (const b of BUS_BANDS)
        rows.push(`<div class="lg-row" style="margin-left:14px">` +
                  `<i class="lg-sw" style="background:${b.color}"></i>` +
                  `<span class="hint">${escHtml(b.label)}</span></div>`);
    /* G112: the data-centre pins are TWO colours and the reader had to click one to find out why.
       The distinction is a claim about how much the coordinate can be trusted, which is exactly
       the sort of thing a key is for. Sizes are now equal, so colour is the only channel left. */
    if (box === "L-dc")
      for (const [colour, label] of dcTiers())
        rows.push(`<div class="lg-row" style="margin-left:14px">` +
                  `<i class="lg-sw" style="background:${color}"></i>` +
                  `<span class="hint">${escHtml(label)}</span></div>`);
  }
  /* G96: while a ranking is painted, the parcel colour means something completely different from
     its usual "has an owner signal" — so the key has to say so, or the reader carries the wrong
     interpretation across. */
  if (state.rankPainted) {
    rows.push(`<div class="lg-row lg-metric"><i class="lg-sw lg-banded"></i>` +
              `<span>parcel color = <b>your ranking score</b>, not owner signal</span></div>`);
    for (const [, colour, label] of RANK_BANDS)
      rows.push(`<div class="lg-row" style="margin-left:14px">` +
                `<i class="lg-sw" style="background:${color}"></i>` +
                `<span class="hint">${escHtml(label)}</span></div>`);
  }
  const metric = $("county-metric") ? $("county-metric").value : "none";
  if (metric && metric !== "none")
    rows.push(`<div class="lg-row lg-metric"><i class="lg-sw lg-banded"></i>` +
              `<span>county shading: ${escHtml($("county-metric").selectedOptions[0].text)}</span></div>`);
  body.innerHTML = rows.length ? rows.join("")
    : `<div class="hint">Nothing is switched on. Open a section on the left and tick a layer.</div>`;
  if (count) count.textContent = rows.length ? `(${rows.length} on)` : "(nothing on)";
  // collapse itself when there is nothing to key, so an empty box never sits over the map
  const box = $("layer-legend");
  if (box && !rows.length) box.open = false;
}

function syncLayers() {
  if (!map.getLayer("county-fill")) return;
  for (const [box, ids] of Object.entries(LAYER_MAP))
    for (const id of ids) if (map.getLayer(id))
      map.setLayoutProperty(id, "visibility", $(box).checked ? "visible" : "none");
  // G34: context layers go through the SAME path. They load lazily, so a layer that is not on the
  // map yet is skipped -- it will be created with visibility "none" and synced on its next toggle.
  if (state.scrLoaded && map.getLayer("scr-pts"))
    map.setLayoutProperty("scr-pts", "visibility", $("L-screener").checked ? "visible" : "none");
  for (const [box, id] of Object.entries(CONTEXT_LAYERS))
    if (map.getLayer(id) && $(box))
      map.setLayoutProperty(id, "visibility", $(box).checked ? "visible" : "none");
  // G110: the env-gate layers are lazy in exactly the same way and go through the same path
  for (const [box, id] of Object.entries(ENVGATE_LAYERS))
    if (map.getLayer(id) && $(box))
      map.setLayoutProperty(id, "visibility", $(box).checked ? "visible" : "none");
  // G72/G80: same lazy path again. ONE visibility mechanism for every layer on the console —
  // a second one would be the two-copies-drift defect, and the legend reads from this call.
  for (const [box, ids] of Object.entries(WIRED_LAYERS))
    for (const id of ids) if (map.getLayer(id) && $(box))
      map.setLayoutProperty(id, "visibility", $(box).checked ? "visible" : "none");
  // G130: planned investments use the SAME one visibility mechanism. Their status boxes and the
  // ring toggle are a FILTER on top of it, not a second way of hiding things - two mechanisms for
  // one behaviour is the drift defect this comment block already warns about.
  for (const [box, ids] of Object.entries(PLANNED_LAYERS))
    for (const id of ids) if (map.getLayer(id) && $(box))
      map.setLayoutProperty(id, "visibility", $(box).checked ? "visible" : "none");
  const showP = $("L-parcels").checked;
  for (const fips of state.loaded.keys())
    for (const suf of ["fill", "line"])
      map.setLayoutProperty(`sites-${fips}-${suf}`, "visibility", showP ? "visible" : "none");
  if (map.getLayer("cand-line"))
    map.setLayoutProperty("cand-line", "visibility", $("f-cand").checked ? "visible" : "none");
  renderLayerLegend();     // G52: one call site, so the key cannot disagree with what is drawn
}
for (const id of [...Object.keys(LAYER_MAP), "L-parcels"]) $(id).addEventListener("change", syncLayers);
// the context and screener boxes are wired elsewhere, but the KEY must still update for them
for (const id of [...Object.keys(CONTEXT_LAYERS), ...Object.keys(ENVGATE_LAYERS), "L-screener"])
  if ($(id)) $(id).addEventListener("change", () => setTimeout(renderLayerLegend, 0));

/* ==============================================================================================
   G130 - PLANNED GRID INVESTMENTS. Where future capacity may appear.

   Operator, 2026-08-20f: *"I would like to place these upgrades or new developments on the map for
   where future capacity may exist… these upgrades or new developments should NOT display the same
   as the current grid assets."*

   ⛔ SO THEY DO NOT. Existing steel on this console is a SOLID FILLED circle or a SOLID line.
   Planned work is VIOLET, HOLLOW and DASHED, and it sits under an uncertainty ring:
       ring      a translucent violet polygon showing where the asset COULD be
       corridor  a DASHED line, for upgrades that are a rebuild between two named substations -
                 drawing those as a dot at the midpoint would put the work miles from where it is
       point     a hollow violet marker, never a filled one

   ⭐ THE RING IS SIZED BY HOW WELL WE KNOW THE LOCATION, NEVER BY PROJECT STATUS. That is the
   design decision taken from the operator's Illinois tool, and it is the right one: a project can
   be fully approved and still be named only by its town.
       verified_asset_match   NO RING - a known position must not be drawn as a guessed one
       substation_match       NO RING
       corridor midpoint      half the span, and the span is capped at 75 mi because past that
                              the "corridor" is a comma-separated LIST of places, not a line
       corridor one end       3 mi
       town centroid          that town's own TIGER radius + 4 mi, which contains 86.7% of
                              measured substation-to-town cases against 83.0% for the flat 5 mi
                              it replaced
       county centroid        the county's own equal-area radius

   ⚠ NOT EVERY PLANNED ITEM CARRIES A POSITION, and the ones that do not are held and REPORTED,
   never drawn - an upgrade in the wrong place is worse than one with no place, because it is a
   coordinate someone might plan around. ⛔ The counts are NOT typed here: they were, they went
   stale inside one session, and the grid page generates them instead.
   ⛔ `in_service` work is ALREADY BUILT and is off by default: it is not future capacity.
   ============================================================================================== */
const PLANNED_LAYERS = { "L-planned": ["planned-ring", "planned-corridor", "planned-point"] };
const PLANNED_VIOLET = "#7c3aed";

function plannedStatusFilter() {
  const on = ["proposed", "approved", "filed_plan", "in_service", "cancelled"]
    .filter((s) => { const b = $("P-" + s); return b && b.checked; });
  /* ⚠ literal-false rather than an empty "in" list: MapLibre treats ["in", x, ["literal", []]]
     as matching nothing, which is what we want, but being explicit keeps the intent readable. */
  return on.length ? ["in", ["get", "status"], ["literal", on]] : false;
}

function syncPlannedFilters() {
  if (!map.getLayer("planned-point")) return;
  const st = plannedStatusFilter();
  const withKind = (kind) => st === false ? false : ["all", ["==", ["get", "kind"], kind], st];
  map.setFilter("planned-point", withKind("point"));
  map.setFilter("planned-corridor", withKind("corridor"));
  const ringsOn = $("P-rings") ? $("P-rings").checked : true;
  map.setFilter("planned-ring", ringsOn ? withKind("ring") : false);
}

state.plannedLoaded = false; state.plannedLoading = null;
async function ensurePlannedLayers() {
  if (state.plannedLoaded) return true;
  if (state.plannedLoading) return state.plannedLoading;
  state.plannedLoading = (async () => {
    const fc = await fetchGz("data/planned.geojson.gz");
    map.addSource("planned", { type: "geojson", data: fc });
    const hid = { visibility: "none" };

    /* the ring goes in FIRST so it sits under the point it belongs to */
    map.addLayer({ id: "planned-ring", type: "fill", source: "planned",
      filter: ["==", ["get", "kind"], "ring"], layout: hid,
      paint: { "fill-color": PLANNED_VIOLET, "fill-opacity": 0.07,
               "fill-outline-color": PLANNED_VIOLET } });
    map.addLayer({ id: "planned-corridor", type: "line", source: "planned",
      filter: ["==", ["get", "kind"], "corridor"], layout: hid,
      paint: { "line-color": PLANNED_VIOLET, "line-width": 2.2, "line-opacity": 0.85,
               /* ⛔ DASHED. Every existing transmission line on this console is solid; a solid
                  violet line would read as a line that is already there. */
               "line-dasharray": [2, 1.6] } });
    map.addLayer({ id: "planned-point", type: "circle", source: "planned",
      filter: ["==", ["get", "kind"], "point"], layout: hid,
      paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 6, 3.5, 12, 7],
               /* ⛔ HOLLOW. The fill is almost transparent and the ring is the weight, so a
                  planned asset never reads as a built one at a glance. */
               "circle-color": "#ffffff", "circle-opacity": 0.55,
               "circle-stroke-color": PLANNED_VIOLET, "circle-stroke-width": 2.2 } });

    /* ⚠ ITERATE THE REGISTRY, not one hardcoded key. audit_map_clicks.py recognises a group
       bound via Object.values(...) - that shape was added after CONTEXT_LAYERS and ENVGATE_LAYERS
       were both reported as "drawn and unclickable" for a session while being bound the whole
       time. Indexing PLANNED_LAYERS["L-planned"] binds correctly but is invisible to the audit,
       and a true finding the instrument cannot see is worth no more than a false one. */
    for (const ids of Object.values(PLANNED_LAYERS)) for (const id of ids) {
      map.on("mousemove", id, (e) => showTip(e, plannedTip(e.features[0].properties)));
      map.on("mouseleave", id, hideTip);
      map.on("click", id, (e) => { if (!state.measure.on) plannedEvidence(e.features[0].properties); });
    }
    syncPlannedFilters();
    state.plannedLoaded = true;
    return true;
  })();
  return state.plannedLoading;
}

const PLANNED_STATUS_PLAIN = {
  proposed: "PROPOSED — filed, not yet approved",
  approved: "APPROVED / in execution",
  in_service: "ALREADY IN SERVICE — not future capacity",
  filed_plan: "in a utility's filed capital plan",
  cancelled: "CANCELLED or withdrawn",
  unclassified: "status not published in a form we can classify",
};

function plannedTip(p) {
  const bits = [`<b>${p.title || p.pid}</b>`, p.src];
  if (p.status) bits.push(PLANNED_STATUS_PLAIN[p.status] || p.status);
  if (p.cost_m) bits.push(`$${fmt(Math.round(p.cost_m))}M`);
  if (p.isd) bits.push(`in service ${String(p.isd).slice(0, 10)}`);
  if (p.unc_mi) bits.push(`±${p.unc_mi} mi`);
  return bits.join(" · ");
}

function plannedEvidence(p) {
  show(`Planned: ${p.title || p.pid}`, `
    <h3>Where future capacity may appear</h3><table>
      ${row("source", p.src)}
      ${row("project", p.pid)}
      ${row("status", p.status ? (PLANNED_STATUS_PLAIN[p.status] || p.status) : null,
            "the filing publishes no status we can classify")}
      ${row("status as filed", p.status_raw)}
      ${row("expected in service", p.isd ? String(p.isd).slice(0, 10) : null,
            "no in-service date published")}
      ${/* ⚠ THREE-STATE, PROPERLY. The default "not measured here" would be a lie on a 2028
            project: there is no ACTUAL in-service date because the work has not happened, and
            saying we did not measure it implies a gap in us rather than a fact about the
            project. The row only appears once the work is in service. */
        p.status === "in_service"
          ? row("actually in service on", p.aisd ? String(p.aisd).slice(0, 10) : null,
                "recorded in service, but the date is not published")
          : ""}
      ${row("cost", p.cost_m != null ? `$${fmt(Math.round(p.cost_m))}M` : null,
            "no cost published for this project")}
      ${/* ⭐ G130 item 2. MW exists only on the MISO DPP-2025 interconnection rows, so the row
            appears only there rather than reporting "not measured" on 2,651 projects for which
            the question is not even asked. */
        p.mw != null
          ? row("capacity it would enable", `${fmt(p.mw)} MW`) +
            (p.cost_m ? row("cost per MW",
              `$${fmt(Math.round(1000 * p.cost_m / p.mw))}k per MW`) : "")
          : ""}
      ${/* ⭐ G130 item 1. PJM publishes a zone-by-zone allocation for 26 upgrades; on every other
            project this is genuinely unpublished, not unmeasured. */
        p.cost_zone
          ? row("who bears the cost", `${escHtml(p.cost_zone)} ${p.cost_zone_pct}%` +
                (p.cost_n_zones > 1 ? ` of ${p.cost_n_zones} zones` : "")) +
            (p.cost_zones ? row("largest shares", escHtml(p.cost_zones)) : "")
          : ""}
      ${row("owner / utility", p.owner, "this feed publishes no owner")}
      ${row("what the work is", p.descr, "this feed publishes no description")}
      ${row("driver", p.driver, "this feed publishes no driver")}
      ${row("county", p.county, "no county resolved for this project")}
    </table>
    <h3>How well we know WHERE it is</h3><table>
      ${row("location as filed", p.loc_text)}
      ${row("anchor", p.anchor)}
      ${row("method", p.loc_method)}
      ${row("uncertainty", p.unc_mi != null ? `±${p.unc_mi} miles` : null)}
    </table>
    <div class="sowhat">⚠ <b>${escHtml(p.loc_basis || "location basis not recorded")}.</b>
      The ring on the map is that distance, and it is sized by how well the LOCATION is known —
      not by how far along the project is. ⛔ This is planned or filed work, not an existing
      asset, and it is not reflected in any published hosting-capacity figure.</div>
    <div class="prov">${prov("in_planned_upgrades")}</div>`);
}

/* G72/G80: load-on-first-toggle for the six new controls. ⚠ If the fetch fails the box is
   UNTICKED again — a ticked box over an absent layer is the failure mode the logistics layers
   had for weeks, where the reader believed they were looking at data that was never drawn. */
for (const box of Object.keys(WIRED_LAYERS)) {
  const el = $(box);
  if (!el) continue;
  el.addEventListener("change", async (e) => {
    if (e.target.checked) {
      try { await ensureWiredLayers(); } catch (err) {
        reportBootFailure(err); e.target.checked = false; return;
      }
    }
    syncLayers();
  });
}

/* G130: the planned-investment box loads on first tick, exactly like the wired boxes, and
   UNTICKS itself if the fetch fails - a ticked box over an absent layer is the failure this
   console already had once. The status boxes and the ring toggle only re-filter, so they never
   need to load anything. */
{
  const el = $("L-planned");
  if (el) el.addEventListener("change", async (e) => {
    if (e.target.checked) {
      try { await ensurePlannedLayers(); } catch (err) {
        reportBootFailure(err); e.target.checked = false; return;
      }
    }
    syncLayers();
    syncPlannedFilters();
  });
  for (const id of ["P-proposed", "P-approved", "P-filed_plan", "P-in_service",
                    "P-cancelled", "P-rings"]) {
    const b = $(id);
    if (b) b.addEventListener("change", syncPlannedFilters);
  }
}

/* ---------- G110b: TICKING A GATE FILTER REVEALS THE GATE --------------------------------------
   Operator: the layers "should also show the map layer when checked, not just used as a filtering
   tool" -- and, separately, "maybe it should be an option to filter down sites".

   Those are two verbs that were sharing one control, so they are now two controls that COOPERATE:
   excluding sites on a gate switches that gate's layer on, so the reader can see what they just
   removed. ⚠ It is deliberately ONE-WAY and non-sticky: turning the filter off does NOT turn the
   layer off, because by then the reader may be using the layer for its own sake, and yanking it
   away would be the tool overriding a choice the reader made. */
const GATE_FILTER_TO_LAYER = { "f-noflood": "L-flood", "f-nowet": "L-wet", "f-noprot": "L-padus" };
for (const [filterBox, layerBox] of Object.entries(GATE_FILTER_TO_LAYER)) {
  const f = $(filterBox), l = $(layerBox);
  if (!f || !l) continue;
  f.addEventListener("change", () => {
    if (!f.checked || l.checked) return;
    l.checked = true;
    // dispatch, do not call directly: the lazy loaders hang off the change event, and L-padus
    // and L-flood reach the map by different routes
    l.dispatchEvent(new Event("change"));
  });
}
if ($("county-metric")) $("county-metric").addEventListener("change", renderLayerLegend);

/* ---------- G66: THE FOUR PART-PRESETS ARE GONE ----------------------------------------------
 * Operator, 2026-08-19: "remove the JUMP TO A VIEW section, since we want the user to toggle
 * these things on and off." The presets set a county metric and a full layer state in one click;
 * with G65 splitting 19 boxes into 26, a preset would be deciding 26 answers on the reader's
 * behalf, which is the opposite of the ask.
 *
 * ⛔ WHAT MUST NOT GO WITH THEM. `ALL_LAYER_BOXES` and `syncLayers()` STAY. The registry is what
 * enforces "off means hidden" -- G34 was exactly this bug: `grid` set "L-fac": 1, no other preset
 * mentioned it, and wind and solar stayed drawn after a preset switch because nothing set them
 * back to 0. Deleting the registry along with the presets would reintroduce it with 26 boxes
 * instead of 17. What is retired is PRESETS, the preset applier, and PRESET_GAPS (which existed
 * only to check that every preset stated every layer -- with no presets there is nothing to check).
 *
 * The county-shading selector `#county-metric` survives on its own; it was never a preset, the
 * presets merely set it.
 *
 * Historical note, kept because the shape recurs: the removed applier iterated the REGISTRY rather
 * than the preset, precisely so an unstated box turned OFF instead of persisting. That principle
 * now lives in syncLayers() alone.
 * -------------------------------------------------------------------------------------------- */

/* ---------- parcels ---------- */
const FILL_COLOR = ["case", ["==", ["get", "has_si_signal"], true], "#d97706",
  ["==", ["get", "occ_group"], "ci"], "#2563eb",
  ["==", ["get", "occ_group"], "agriculture"], "#059669", "#64748b"];
/* G29 — PREFER THE EXACT DISTANCE WE SHIPPED; approximate only when we have none.
 *
 * The loop below measures from repPt() — the parcel's FIRST VERTEX — to one binned vertex per line.
 * Both ends are wrong, it always OVERSTATES, and it can never return 0 even when the conductor
 * physically crosses the parcel. Measured: on the 41,986 parcels a line actually crosses, this
 * method returns a median 0.088 mi and up to 0.772 mi where the true answer is 0.0.
 *
 * `in_asset_distance_parcel` computes the real thing — ST_DISTANCE(parcel_geog, line_geog) — and
 * export_sites_exact.py ships it as x_line_mi / x_sub_mi. Those cover the 532,868 screener
 * candidates. Anything else (an uploaded CSV row with no parcel polygon, a parcel outside the
 * candidate set) has no exact value and still needs the approximation, so the fallback stays.
 *
 * `_dist_exact` rides on every parcel so the evidence panel can say WHICH measurement it is
 * showing. A number whose method is invisible is the defect that produced this fix. */
function enrichDistances(feats) {
  for (const ft of feats) {
    const p = ft.properties;
    const [lon, lat] = repPt(ft.geometry);

    // ---- transmission line ----
    if (p.x_line_mi != null) {
      p._dline_mi = p.x_line_mi;          // exact: 0.0 when the line crosses the parcel
      p._dline_kv = p.x_line_kv ?? null;  // null = voltage not published; never render as 0 kV
      p._dline_on = !!p.x_line_on;
      p._dist_exact = true;
    } else {
      let bl = null;
      for (const v of binNear(state.lineBins, lon, lat)) {
        const d = havM(lat, lon, v.lat, v.lon);
        if (!bl || d < bl.d) bl = { d, v };
      }
      if (bl) { p._dline_mi = +(bl.d / MI).toFixed(2); p._dline_kv = bl.v.kv; }
      p._dist_exact = false;
    }

    // ---- substation ----
    if (p.x_sub_mi != null) {
      p._dsub_mi = p.x_sub_mi;
      p._dsub_kv = p.x_sub_kv ?? null;
      p._dsub_name = p.x_sub_name || null;
    } else {
      let best = null;
      for (const s of binNear(state.subBins, lon, lat)) {
        const d = havM(lat, lon, s.lat, s.lon);
        if (!best || d < best.d) best = { d, s };
      }
      if (best) { p._dsub_mi = +(best.d / MI).toFixed(2); p._dsub_kv = best.s.kv; p._dsub_name = best.s.name; }
    }

    // ---- bus ----
    // G29 CLOSED 2026-08-19. The exact value now ships, so prefer it and keep the client-side
    // measurement only as the fallback for rows that never had one (uploaded CSVs).
    if (p.x_bus_wd_mi != null || p.x_bus_inj_mi != null) {
      // withdrawal is the default: a data centre asks the LOAD question (G63). Both are carried
      // so the panel can show them apart -- never fused into one "bus headroom".
      const wd = p.x_bus_wd_mi != null;
      p._dpoi_mi   = wd ? p.x_bus_wd_mi   : p.x_bus_inj_mi;
      p._dpoi_name = wd ? p.x_bus_wd_name : p.x_bus_inj_name;
      p._dpoi_mw   = wd ? p.x_bus_wd_mw   : p.x_bus_inj_mw;
      p._dpoi_kv   = wd ? p.x_bus_wd_kv   : p.x_bus_inj_kv;
      p._dpoi_dir  = wd ? "getting power" : "sending power";
      p._dpoi_exact = true;
      continue;
    }
    p._dpoi_exact = false;
    // ---- fallback: client-side, first-vertex. Overstates, and can never return 0. ----
    // ⚠ GUARDED. enrichDistances runs inside the county fetch's .then(), so if poiList had not
    // loaded yet this loop threw "state.poiList is not iterable" and took the WHOLE function with
    // it — every parcel in that county silently lost EVERY distance, substation and line included,
    // with the rejection swallowed by the promise chain. Found by calling this directly in a browser.
    let bp = null;
    for (const q of (Array.isArray(state.poiList) ? state.poiList : [])) {
      const d = havM(lat, lon, q.lat, q.lon);
      if (!bp || d < bp.d) bp = { d, q };
    }
    if (bp) { p._dpoi_mi = +(bp.d / MI).toFixed(1); p._dpoi_name = bp.q.name; p._dpoi_mw = bp.q.mw; }
  }
}
function addCountyLayers(fips, fc) {
  const src = `sites-${fips}`;
  if (map.getSource(src)) return;
  map.addSource(src, { type: "geojson", data: fc });
  map.addLayer({ id: `${src}-fill`, type: "fill", source: src, minzoom: PARCEL_ZOOM,
    layout: { visibility: $("L-parcels").checked ? "visible" : "none" },
    paint: { "fill-color": parcelFillPaint(), "fill-opacity": 0.45 } }, "grid-lines");
  map.addLayer({ id: `${src}-line`, type: "line", source: src, minzoom: PARCEL_ZOOM,
    layout: { visibility: $("L-parcels").checked ? "visible" : "none" },
    paint: { "line-color": "#333", "line-width": 0.6 } }, "grid-lines");
  map.on("click", `${src}-fill`, (e) => {
    if (state.measure.on) return;
    /* ⭐ G134 is handled centrally by the map.on wrapper at the top of this file - the parcel
       yields automatically to anything more specific under the same four pixels. Nothing is
       needed here, and adding a second guard would be the two-copies defect. */
    /* highlight whichever parcel the panel is about, however it was reached */
    const key = e.features[0].properties.parcel_key;
    const full = (state.loaded.get(fips) || []).find((f) => f.properties
      && f.properties.parcel_key === key);
    if (full) highlightParcel(full);
    openParcelEvidence(e.features[0].properties, fips);
  });
  map.on("mousemove", `${src}-fill`, (e) => showTip(e, tipText(e.features[0].properties)));
  map.on("mouseleave", `${src}-fill`, hideTip);
}
/* ---------- G95: SHOW ME WHICH PARCELS CARRY THE CONSTRAINT ----------------------------------
   Operator, 2026-08-19: *"the layers still say 'exclude' XXX layer, which doesn't help us if we
   want to see the layer itself."*

   Right, and the honest answer is not a layer. `in_flood` is 803.8 MB and `in_wetlands` 1,319.6 MB
   -- neither can be sent to a browser, and shipping a simplified version would be a different
   claim wearing the same name. What we DO hold, on every parcel, is a flag measured against those
   sources. So the map highlights the affected PARCELS, which answers the siting question ("is this
   site affected?") rather than the cartographic one ("where is the floodplain?"). The control says
   which of the two it is doing.

   ⚠ `undefined` is NOT `false` here. A parcel outside in_site_gates was never measured, so it is
   drawn in the ordinary colour and is not claimed to be clear. */
function parcelFillPaint() {
  const k = $("f-hilite") ? $("f-hilite").value : "";
  if (!k) return FILL_COLOR;
  return ["case", ["==", ["get", k], true], "#dc2626", FILL_COLOR];
}
function applyParcelHighlight() {
  const paint = parcelFillPaint();
  for (const fips of state.loaded.keys())
    if (map.getLayer(`sites-${fips}-fill`))
      map.setPaintProperty(`sites-${fips}-fill`, "fill-color", paint);
  const el = $("f-hilite-note");
  if (el) {
    const k = $("f-hilite").value;
    if (!k) { el.textContent = ""; return; }
    let hit = 0, measured = 0;
    for (const feats of state.loaded.values())
      for (const f of feats) {
        const v = f.properties[k];
        if (v === undefined) continue;
        measured++; if (v === true) hit++;
      }
    el.innerHTML = measured
      ? `<b>${fmt(hit)}</b> of ${fmt(measured)} loaded parcels carry it, drawn in red. `
        + `Parcels we never measured stay the ordinary color rather than being called clear.`
      : `Zoom in until parcels load to see the highlight.`;
  }
}
if ($("f-hilite")) $("f-hilite").addEventListener("change", applyParcelHighlight);

function countiesInView() {
  const b = map.getBounds();
  return Object.entries(state.countyBbox)
    .filter(([, [w, s, e, n]]) => b.getWest() < e && b.getEast() > w && b.getSouth() < n && b.getNorth() > s)
    .map(([f]) => f);
}
/* ---------- G39: DEEP LINK FROM THE SCREENER ------------------------------------------------
   Operator, 2026-08-17: *"when we click on a screener observation (or a map link), we get directed
   to where the site is on the map console."*

   ⚠ The console loads parcels PER COUNTY ON DEMAND, and only for counties in view above zoom 10 -
   so a deep link cannot just fly somewhere and hope. It has to fetch that county's file itself,
   wait for it, then select the parcel. This is the trap the backlog flagged. */
async function ensureCountyLoaded(fips) {
  if (state.loaded.has(fips)) return true;
  if (state.loading.has(fips)) {
    for (let i = 0; i < 100 && state.loading.has(fips); i++)
      await new Promise((r) => setTimeout(r, 100));
    return state.loaded.has(fips);
  }
  state.loading.add(fips);
  try {
    const fc = await fetchGz(`data/sites/${fips}.geojson.gz`);
    /* ⛔ DATA FIRST, PRESENTATION SECOND, AND THEY FAIL SEPARATELY. The first version did
       enrichDistances -> set -> addCountyLayers inside one try, so a throw in EITHER map step
       lost the parcels and the deep link reported "that link did not resolve" - blaming the link
       for a rendering failure. The parcels are what the deep link and the dossier need; the map
       layer is decoration. Register the data, then attempt each map step on its own. */
    state.loaded.set(fips, fc.features);
    try { enrichDistances(fc.features); }
    catch (e) { console.warn("deep link: distance enrichment skipped for " + fips, e); }
    try { addCountyLayers(fips, fc); applyFilters(); }
    catch (e) { console.warn("deep link: county layers not added for " + fips, e); }
    return true;
  } catch (e) {
    console.error("deep link: county " + fips + " failed to load", e);
    return false;
  } finally { state.loading.delete(fips); }
}

/* ---------- G121: THE MAP SEARCH BAR ----------------------------------------------------------
   Operator, 2026-08-19: *"add in a search bar in the upper left hand corner of the map where an
   address, coordinates, or parcel ID (or similar for locating a site) can be inputted by the user
   and they immediately get zoomed into the site and the popup displays."*

   ⛔ ADDRESS CANNOT BE DONE AS ASKED, AND THE BOX SAYS SO INSTEAD OF FAILING QUIETLY. There is no
   geocoder in this application, deliberately: an address resolves to a street CENTRELINE and a
   centreline is not a parcel. The only address-to-parcel corpus we hold is Marion County's
   crosswalk, 347,049 rows, far too large to ship to a browser. Typing something address-shaped
   returns an explanation and the two routes that do work, rather than "no results".

   ⭐ WHAT IS SEARCHABLE IS WIDER THAN AN ADDRESS, because it is everything we hold WITH a
   coordinate: a parcel id, a coordinate pair, a county, a substation, a transmission bus, a data
   centre, a utility territory.

   ⭐ A BARE PARCEL ID RESOLVES ITS OWN COUNTY. The first two digits of an Indiana state parcel
   number are the county's alphabetical index, so fips = 18001 + (n-1)*2. Measured against the
   candidate corpus: the rule holds on 532,235 of 532,691 keys (99.9%). The 456 exceptions start
   '00' and fall back to searching whatever counties are already loaded.

   ⚠ AN ESTIMATED POSITION IS BADGED IN THE RESULT LIST, not only after you fly there. 91.9% of
   PJM bus positions are estimates and 92 of 249 data-centre pins are city centroids; a search
   that flies to an estimate without saying so converts a caveat into a coordinate. */
const MS_ADDRESSY = /\d+\s+[A-Za-z].*\b(st|street|rd|road|ave|avenue|dr|drive|ln|lane|blvd|boulevard|ct|court|hwy|highway|pike|way|pkwy)\b/i;

/* ---------- G105: THE DEEP-LINK PIN, and why it needed its own function ------------------------
   The amber pin was created in TWO places — the search bar and the deep-link handler — with the
   same eleven lines copied, `properties: {}` in both, and NO CLICK BINDING in either. So the one
   marker on the map that says "this is the thing you asked for" was the only marker you could not
   ask about: click it and nothing happened, and once the panel was closed there was no way back
   to it without searching again.

   Two copies of one thing is §2.15c, so this is now one function. The properties travel WITH the
   feature, which is what makes the click possible at all — a pin with empty properties has
   nothing to re-show. */
function dropPin(lat, lon, props) {
  const gj = { type: "Feature", geometry: { type: "Point", coordinates: [lon, lat] },
               properties: { lat, lon, ...props } };
  if (map.getSource("deeplink-pt")) { map.getSource("deeplink-pt").setData(gj); return; }
  map.addSource("deeplink-pt", { type: "geojson", data: gj });
  map.addLayer({ id: "deeplink-pt", type: "circle", source: "deeplink-pt",
    paint: { "circle-radius": 11, "circle-color": "#f59e0b", "circle-opacity": 0.35,
             "circle-stroke-color": "#b45309", "circle-stroke-width": 2.5 } });
  map.on("mousemove", "deeplink-pt", (e) =>
    showTip(e, `${e.features[0].properties.label || "your search result"} — click to re-open`));
  map.on("mouseleave", "deeplink-pt", hideTip);
  map.on("click", "deeplink-pt", (e) => {
    if (state.measure.on) return;
    const p = e.features[0].properties;
    show(p.label ? `Located: ${escHtml(String(p.label))}` : "Located", `
      <table>${row("coordinate", `${Number(p.lat).toFixed(5)}, ${Number(p.lon).toFixed(5)}`)}
        ${row("what it is", p.src || null)}</table>
      ${p.estimate ? `<div class="cannot">⚠ <b>This position is an ESTIMATE.</b>
        ${escHtml(String(p.estimate))} Treat it as "about here", not as a survey.</div>` : ""}
      <div class="hint">This is the pin dropped by your search or by the link you followed. Every
        layer under it is still clickable — the pin marks the spot, it does not own it.</div>`);
  });
}

function msFlyTo(lat, lon, label, src, estimate) {
  map.flyTo({ center: [lon, lat], zoom: 15 });
  dropPin(lat, lon, { label, src, estimate: estimate || "" });
  show(`Found: ${escHtml(label)}`, `
    <table>${row("Coordinate", `${lat.toFixed(5)}, ${lon.toFixed(5)}`)}
      ${row("What it is", src)}</table>
    ${estimate ? `<div class="cannot">⚠ <b>This position is an ESTIMATE.</b> ${escHtml(estimate)}
      Treat it as "about here", not as a survey.</div>` : ""}
    <div class="hint">Searched from the box at the top left. Everything drawn on the map is still
      clickable — this only moved you to the place.</div>`);
}

/** Build the searchable index from payloads already in memory. Nothing new is fetched. */
function msIndex() {
  const out = [];
  /* ⚠ DEDUPED ON (kind, name, position). `bus_poi` carries ONE FEATURE PER DIRECTION (G111), so
     every bus would otherwise appear twice in the results — searching "DEQUIN" returned the
     substation and then the same bus listed two times, which reads as two different buses. */
  const seen = new Set();
  const push = (kind, name, lat, lon, est) => {
    if (!name || !Number.isFinite(lat) || !Number.isFinite(lon)) return;
    const k = `${kind}|${String(name).toLowerCase()}|${lat.toFixed(5)}|${lon.toFixed(5)}`;
    if (seen.has(k)) return;
    seen.add(k);
    out.push({ kind, name: String(name), lat, lon, est });
  };
  for (const f of ((state.counties && state.counties.features) || [])) {
    const b = state.countyBbox[f.properties.fips];
    if (b) push("county", f.properties.county_name, (b[1] + b[3]) / 2, (b[0] + b[2]) / 2, null);
  }
  for (const f of ((state.grid && state.grid.features) || [])) {
    const p = f.properties, c = (f.geometry || {}).coordinates;
    if (!c) continue;
    if (p.layer === "substation") push("substation", p.substation_name, c[1], c[0], null);
    else if (p.layer === "bus_poi")
      push("bus", p.bus_name || p.poi_name, c[1], c[0],
           "Bus positions are derived by matching the bus label to a substation gazetteer.");
  }
  for (const f of ((state.fac && state.fac.features) || [])) {
    const p = f.properties, c = (f.geometry || {}).coordinates;
    if (!c || p.layer !== "dc") continue;
    push("data center", p.name, c[1], c[0], p.location_precision === "city"
      ? "The publisher gives CITY precision for this record — this is a town centroid, not the facility."
      : null);
  }
  for (const f of ((state.terr && state.terr.features) || [])) {
    const p = f.properties, g = f.geometry;
    // ⚠ `bboxOf` walks geom.coordinates and throws on a feature that has none. A payload can
    // legitimately carry a properties-only feature, and a search box must not take the map down
    // because one row lacks geometry.
    if (!g || !g.coordinates || !p || !p.utility) continue;
    let bb;
    try { bb = bboxOf(g); } catch (e) { continue; }
    push("utility territory", p.utility, (bb[1] + bb[3]) / 2, (bb[0] + bb[2]) / 2,
         "Territory center, not an office or an asset.");
  }
  return out;
}

/* G121b: one route from a parcel key to an opened parcel, shared by the parcel-ID search and the
   Marion address search. ⛔ Written once: the ?parcel= deep link, the id search and the address
   search all have to fit the parcel's own OUTLINE and open the same panel, and three copies of
   that would drift — which is the defect this codebase hits most often. */
async function msOpenParcel(pk, typedAs, nMulti, say) {
  const cc = parseInt(String(pk).slice(0, 2), 10);
  const fips = cc >= 1 && cc <= 92 ? String(18001 + (cc - 1) * 2) : null;
  if (fips) await ensureCountyLoaded(fips);
  for (const [f, feats] of state.loaded) {
    const ft = feats.find((x) => x.properties && x.properties.parcel_key === pk);
    if (!ft) continue;
    const pts = [];
    (function walk(c) { if (typeof c[0] === "number") { pts.push(c); return; }
                        for (const x of c) walk(x); })(ft.geometry.coordinates);
    if (pts.length) {
      const xs = pts.map((v) => v[0]), ys = pts.map((v) => v[1]);
      const pad = Math.max(40, Math.min(110, Math.round(
        Math.min(map.getContainer().clientWidth, map.getContainer().clientHeight) * 0.12)));
      map.fitBounds([[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]],
                    { padding: pad, maxZoom: 17.5, duration: 900 });
    }
    highlightParcel(ft);
    openParcelEvidence(ft.properties, f);
    /* ⚠ 16,087 Marion addresses cover MORE THAN ONE parcel — condominiums, split lots, campuses.
       We open the first, because something has to open, but the reader is told rather than left
       to assume the parcel they are looking at is the whole site. */
    if (nMulti > 1) {
      const p = document.querySelector("#ev-body") || document.body;
      const n = document.createElement("div");
      n.className = "cannot";
      n.innerHTML = `\u26a0 <b>${fmt(nMulti)} parcels share the address ` +
        `${escHtml(String(typedAs || ""))}.</b> This is one of them — the county register lists ` +
        `the rest under the same street address, so check the neighbours before assuming this ` +
        `parcel is the whole site.`;
      p.insertBefore(n, p.firstChild);
    }
    return true;
  }
  if (say) {
    say(`<div class="ms-note">\u26d4 <b>Parcel <code>${escHtml(String(pk))}</code> was not
      found</b>${fips ? ` in county ${escHtml(fips)}, which its first two digits point to.` : "."}
      That is a measured absence, not a rejection of the id — the parcel may sit outside the
      screened set this map draws.</div>`);
  }
  return false;
}

/* Must match `norm_addr()` in export_marion_addresses.py and build_si_address_to_parcel.py.
   Three normalisers over one corpus would disagree about which addresses exist. */
const MS_DIRS = /^(N|S|E|W|NE|NW|SE|SW|NORTH|SOUTH|EAST|WEST)\s+/;
const MS_DIRS_END = /\s+(N|S|E|W|NE|NW|SE|SW|NORTH|SOUTH|EAST|WEST)$/;
const MS_SUFFIX = /\s+(STREET|ST|AVENUE|AVE|ROAD|RD|DRIVE|DR|LANE|LN|BOULEVARD|BLVD|COURT|CT|PLACE|PL|CIRCLE|CIR|PARKWAY|PKWY|TERRACE|TER|WAY|TRAIL|TRL|HIGHWAY|HWY|PIKE|SQUARE|SQ)$/;
const MS_UNIT = /\b(SUITE|STE|UNIT|APT|APARTMENT|FLOOR|FL|BLDG|BUILDING|ROOM|RM|#).*$/;
function msNormAddr(raw) {
  let s2 = String(raw || "").toUpperCase().replace(/[.,]/g, " ").replace(MS_UNIT, " ")
    .replace(/\s+/g, " ").trim();
  const m = s2.match(/^(\d+)\s+(.*)$/);
  if (!m) return [null, null];
  let rest = m[2].replace(MS_DIRS, " ").replace(MS_DIRS_END, " ").replace(MS_SUFFIX, " ")
    .replace(/[^A-Z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
  return rest ? [m[1], rest] : [m[1], null];
}

state.addrIdx = null; state.addrLoading = null;
async function msAddressIndex() {
  if (state.addrIdx) return state.addrIdx;
  if (state.addrLoading) return state.addrLoading;
  state.addrLoading = fetchGz("data/marion_addresses.json.gz")
    .then((d) => { state.addrIdx = d; return d; })
    .catch(() => { state.addrIdx = { idx: null, n: 0, _failed: true }; return state.addrIdx; });
  return state.addrLoading;
}

async function msRun(q) {
  const out = $("ms-out");
  const say = (html) => { out.innerHTML = html; out.classList.remove("hidden"); };
  q = (q || "").trim();
  if (!q) { out.classList.add("hidden"); return; }

  // 1. a coordinate pair -- "39.77, -86.15" or "39.77 -86.15"
  const m = q.match(/^\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)\s*$/);
  if (m) {
    let a = parseFloat(m[1]), b = parseFloat(m[2]);
    // ⚠ accept either order: a lon/lat paste is at least as common as lat/lon, and Indiana's
    // longitude is unambiguously negative, so the pair can be sorted out rather than refused.
    if (Math.abs(a) > 90 && Math.abs(b) <= 90) { const t = a; a = b; b = t; }
    const qual = coordQuality(m[1], m[2]);
    /* ⛔ TESTED AGAINST THE COUNTY POLYGONS, NOT A BOUNDING BOX. The first version used a
       rectangle (lat 37.5-42, lon -88.5..-84.5) and a rectangle around Indiana contains a large
       piece of Illinois: pasting Chicago's 41.88, -87.63 sailed through the guard and the map
       flew to it. `countyOf()` already does the exact point-in-polygon test and is what
       `ingestRecords()` uses, so the two paths now agree on what "in Indiana" means. */
    const cty = (state.counties && state.countyBbox) ? countyOf(b, a) : null;
    if (!cty) {
      say(`<div class="ms-note">⚠ <b>${a.toFixed(4)}, ${b.toFixed(4)} is not inside any Indiana
        county.</b> This tool holds Indiana only, so there is nothing there to describe. Check the
        order of the pair if you meant somewhere in the state.</div>`);
      return;
    }
    out.classList.add("hidden");
    msFlyTo(a, b, `${a.toFixed(5)}, ${b.toFixed(5)}`,
      `a coordinate you typed — ${cty.county_name}`,
      qual.trust === "site" ? null : qual.why);
    return;
  }

  // 2. a parcel id -- resolve its own county from the first two digits
  if (/^\d{12,20}$/.test(q)) {
    say(`<div class="ms-note">Locating parcel <code>${escHtml(q)}</code>…</div>`);
    out.classList.add("hidden");
    await msOpenParcel(q, null, 0, say);
    return;
  }
  /* 3. AN ADDRESS. ⭐ G121b: this WORKS for Marion County, and it is not a geocode — it is a
     lookup of the county's own published address-to-parcel crosswalk, so the answer is a PARCEL
     rather than a point near one. Everywhere else it is declined with the reason, because no
     other Indiana county publishes an equivalent and a street centreline is not a parcel. */
  if (MS_ADDRESSY.test(q)) {
    const [num, stem] = msNormAddr(q);
    if (!num || !stem) {
      say(`<div class="ms-note">That does not parse as a street address. Try
        <code>1200 N Meridian St</code>, a coordinate pair, or a parcel ID.</div>`);
      return;
    }
    say(`<div class="ms-note">Looking up <b>${escHtml(q)}</b> in Marion County's address
      register…</div>`);
    const ai = await msAddressIndex();
    const pk = ai.idx ? ai.idx[`${num}|${stem}`] : null;
    if (!pk) {
      say(`<div class="ms-note">⛔ <b>Not found among the addresses we can open.</b>
        Two separate reasons, and it is worth knowing which one you have hit.
        <br><b>1. Only Marion County publishes an address register we can use</b>, and we search
        it directly — <b>${fmt(ai.n || 0)} addresses</b>. The other 91 counties publish no
        equivalent, and this application has <b>no geocoder</b> on purpose: an address would
        resolve to a street <i>centerline</i>, and a centerline is not a parcel — siting from one
        puts your site in the road.
        <br><b>2. Even in Marion, only SITING CANDIDATES are indexed.</b> The map draws
        ${fmt(ai.drawn_parcels || 0)} of Marion's 340,765 parcels — the screened, non-residential
        set. A house has no entry here because a house is not a site.
        <br><b>What works everywhere:</b> the <b>coordinates</b> (e.g.
        <code>39.7684, -86.1581</code>) or the <b>parcel ID</b>.</div>`);
      return;
    }
    const nMulti = (ai.multi && ai.multi[`${num}|${stem}`]) || 0;
    out.classList.add("hidden");
    await msOpenParcel(pk, q, nMulti);
    return;
  }

  // 4. a named thing we hold with a coordinate
  const needle = q.toLowerCase();
  const idx = msIndex();
  const hits = idx.filter((x) => x.name.toLowerCase().includes(needle))
    .sort((a, b) => a.name.length - b.name.length).slice(0, 12);
  if (!hits.length) {
    say(`<div class="ms-note">Nothing matching <b>${escHtml(q)}</b> among the counties,
      substations, buses, data centers and territories currently loaded.
      ${state.grid ? "" : "<b>The grid layers are still loading</b> — try again in a moment."}</div>`);
    return;
  }
  say(hits.map((h, i) => `<div class="ms-row" data-i="${i}">
      <div><b>${escHtml(h.name)}</b>${h.est ? ` <span class="ms-est">estimated position</span>` : ""}</div>
      <div class="ms-kind">${escHtml(h.kind)}</div></div>`).join(""));
  for (const el of out.querySelectorAll(".ms-row")) {
    el.onclick = () => {
      const h = hits[Number(el.dataset.i)];
      out.classList.add("hidden");
      msFlyTo(h.lat, h.lon, h.name, h.kind, h.est);
    };
  }
}

if ($("ms-q")) {
  let msT = null;
  $("ms-q").addEventListener("input", (e) => {
    clearTimeout(msT);
    const v = e.target.value;
    // debounce: msIndex() walks several payloads, and rebuilding it per keystroke is wasteful
    msT = setTimeout(() => msRun(v), 180);
  });
  /* Keyboard navigation. A search box you have to reach for the mouse to use is half a search
     box — and the result list is the only place the ESTIMATED-position badge appears before you
     commit, so arrowing through it has to be possible. */
  $("ms-q").addEventListener("keydown", (e) => {
    const out = $("ms-out");
    const rows = [...out.querySelectorAll(".ms-row")];
    const cur = rows.findIndex((r) => r.classList.contains("on"));
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      if (!rows.length) return;
      e.preventDefault();
      const next = e.key === "ArrowDown"
        ? Math.min(rows.length - 1, cur + 1)
        : Math.max(0, (cur < 0 ? 0 : cur - 1));
      rows.forEach((r) => r.classList.remove("on"));
      rows[next].classList.add("on");
      rows[next].scrollIntoView({ block: "nearest" });
      return;
    }
    if (e.key === "Enter") {
      clearTimeout(msT);
      // Enter takes the highlighted row if there is one, otherwise the first, otherwise re-runs
      const pick = cur >= 0 ? rows[cur] : rows[0];
      if (pick) { e.preventDefault(); pick.click(); return; }
      msRun(e.target.value);
      return;
    }
    if (e.key === "Escape") { out.classList.add("hidden"); e.target.blur(); }
  });
  document.addEventListener("click", (e) => {
    if (!e.target.closest("#mapsearch")) $("ms-out").classList.add("hidden");
  });
}

/* ?fips=18163&parcel=8206...&open=dossier
   `open=dossier` goes straight to the Power Plan; anything else opens the evidence panel. */
async function handleDeepLink() {
  const q = new URLSearchParams(location.search);
  /* ---- G86/G4: fly to a COORDINATE ------------------------------------------------------------
     Operator, 2026-08-19: *"everything should be clickable to bring the user to the location that
     the table uses (e.g. buses in grid and capacity should have a link to the map for where they
     are located)."* G39 built the parcel deep link and drove the county machinery from it; this is
     the same door for anything that is a point rather than a parcel.
         index.html?lat=40.6&lon=-86.1&z=13&label=05BROCKG
     ⚠ A label is a CLAIM about a place, so the marker says where the coordinate came from rather
     than implying we surveyed it. Most PJM bus positions are estimates (91.9% of the vendor's are),
     and a link that flies to an estimate without saying so turns a caveat into a coordinate. */
  const qlat = parseFloat(q.get("lat")), qlon = parseFloat(q.get("lon"));
  if (Number.isFinite(qlat) && Number.isFinite(qlon)) {
    const z = Math.min(17, Math.max(4, parseFloat(q.get("z")) || 13));
    map.flyTo({ center: [qlon, qlat], zoom: z });
    const label = (q.get("label") || "").trim();
    const src = (q.get("src") || "").trim();
    // one pin implementation, shared with the search bar — see dropPin
    dropPin(qlat, qlon, { label, src });
    show(label ? `Located: ${escHtml(label)}` : "Located",
      `<table>${row("coordinate", `${qlat.toFixed(5)}, ${qlon.toFixed(5)}`)}
        ${row("what it is", label || null)}${row("source", src || null)}</table>
       <div class="sowhat">You arrived here from a table. ⚠ <b>A bus coordinate is often an
         ESTIMATE</b> — no operator publishes a public coordinate feed for PJM buses, and the
         position is derived by matching the bus label to a substation gazetteer. Treat it as
         "about here", not as a survey.</div>`);
  }
  const fips = (q.get("fips") || "").trim(), key = (q.get("parcel") || "").trim();
  if (!fips || !key) return;
  show("Opening site…", `<div class="hint">Loading county ${escHtml(fips)} and locating parcel
    ${escHtml(key)}…</div>`);
  const ok = await ensureCountyLoaded(fips);
  const ft = (state.loaded.get(fips) || []).find((f) => f.properties
    && f.properties.parcel_key === key);
  if (!ok || !ft) {
    show("Site not found", `<div class="sowhat"><b>That link did not resolve.</b> Parcel
      <code>${escHtml(key)}</code> is not in county <code>${escHtml(fips)}</code>'s file. The link
      may be from an older build, or the parcel may have dropped out of the render set.</div>`);
    return;
  }
  /* Fly to the parcel's own geometry, not a point.
     ⚠ Operator, 2026-08-18: *"the whole show this site on the map doesn't zoom in enough to
     actually see the site"*. Two causes, both fixed here. `padding: 220` on a 1920px viewport
     leaves under 1,500px for the parcel, and `maxZoom: 15` caps the view at roughly 3 km across -
     so a 5-acre parcel arrived as a speck in the middle of a county. Padding is now a small
     fraction of the shorter viewport edge, and the cap is 17.5, which puts a small parcel across
     most of the screen while still keeping the county's parcels loaded. */
  const pts = [];
  (function walk(c) { if (typeof c[0] === "number") { pts.push(c); return; }
                      for (const x of c) walk(x); })(ft.geometry.coordinates);
  if (pts.length) {
    const xs = pts.map((v) => v[0]), ys = pts.map((v) => v[1]);
    const pad = Math.max(40, Math.min(110, Math.round(
      Math.min(map.getContainer().clientWidth, map.getContainer().clientHeight) * 0.12)));
    map.fitBounds([[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]],
                  { padding: pad, maxZoom: 17.5, duration: 900 });
  }
  /* ⭐ And SAY WHICH ONE. Operator: *"the site parcel should probably be highlighted slightly so
     we can actually decipher what parcel is identified in the screener."* Right - a parcel panel
     that opens without marking the parcel leaves the reader guessing which of the dozens on
     screen it describes. Drawn as its own source above the county fill so it reads regardless of
     which layers are on. */
  highlightParcel(ft);
  if (q.get("open") === "dossier") await openDossier(ft.properties, fips);
  else openParcelEvidence(ft.properties, fips);
}

/* The one parcel this session is about, outlined so it is findable among its neighbours. One
   source reused, so selecting another parcel moves the highlight rather than stacking them. */
function highlightParcel(ft) {
  if (!ft || !ft.geometry) return;
  const fc = { type: "FeatureCollection", features: [{ type: "Feature", geometry: ft.geometry,
                                                       properties: {} }] };
  if (map.getSource("sel-parcel")) { map.getSource("sel-parcel").setData(fc); return; }
  map.addSource("sel-parcel", { type: "geojson", data: fc });
  map.addLayer({ id: "sel-parcel-fill", type: "fill", source: "sel-parcel",
    paint: { "fill-color": "#f59e0b", "fill-opacity": 0.28 } });
  map.addLayer({ id: "sel-parcel-line", type: "line", source: "sel-parcel",
    paint: { "line-color": "#b45309", "line-width": 2.5 } });
}

async function maybeLoadCounties() {
  if (!state.counties) return;
  if (map.getZoom() < PARCEL_ZOOM) { renderDenominator(); return; }
  for (const fips of countiesInView()) {
    if (state.loaded.has(fips) || state.loading.has(fips)) continue;
    state.loading.add(fips);
    fetchGz(`data/sites/${fips}.geojson.gz`)
      .then((fc) => { enrichDistances(fc.features); state.loaded.set(fips, fc.features); addCountyLayers(fips, fc); applyFilters(); })
      .catch((e) => console.error(e)).finally(() => state.loading.delete(fips));
  }
  renderDenominator();
}

/* ---------- tooltip ---------- */
const tip = document.getElementById("tooltip");
function tipText(p) {
  // same acreageOf() as the screener and the evidence panel — a tooltip that disagreed with
  // the panel it opens would be two instruments claiming one parcel
  // "land supports up to", never "fits": acres x MW/acre is an upper bound on GROSS land, and the
  // tooltip is the one surface a user reads without any surrounding caveat (G28).
  if (p.parcel_key) return `${p.occ_group || ""} · ${Number(p.parcel_acres || 0).toFixed(1)} ac · land supports up to ${Math.floor(acreageOf(p).acres * V("f-density"))} MW${p.has_si_signal ? " · SI" : ""}${p._dsub_mi != null ? ` · sub ${p._dsub_mi} mi` : ""}`;
  if (p.layer === "bus_poi")
    return `${p.bus_name || p.poi_name} · ${p.iso} ${String(p.direction || "").toLowerCase()} · `
         + `${fmt(p.headroom_mw)} MW`;
  if (p.layer === "substation") return `${p.substation_name || "substation"} · ${p.min_kv ?? "?"}–${p.max_kv ?? "?"} kV`;
  if (p.layer === "line") return `${p.voltage || "?"} kV line · ${p.owner || ""}`;
  if (p.layer === "queue_point") return "PJM queue point (published coords)";
  if (p.layer === "bus_candidate") return `PJM bus ${p.bus_number} · load headroom ${p.withdrawal_mw != null ? Math.round(p.withdrawal_mw) + " MW" : "—"} · ESTIMATE loc (${p.match_confidence})`;
  if (p.candidate_signal) return `CANDIDATE ${p.candidate_signal} · ${p.occ_group || ""}`;
  if (p.layer === "gas") return `gas pipeline · ${p.operator || ""}`;
  if (p.layer === "dc") return `EXISTING DC: ${p.name || ""} (${p.src})`;
  if (["plant", "plant_hifld", "solar", "wind"].includes(p.layer)) return `${p.layer}: ${p.name || p.plant_name || ""}`;
  // G72 gates
  if (p.layer === "military") return `MILITARY: ${p.name} — DoD review territory`;
  if (p.layer === "tribal") return `TRIBAL TRUST: ${p.name} — a separate sovereign`;
  if (p.layer === "sua") return `SPECIAL-USE AIRSPACE: ${p.name} · ${p.detail || ""}`;
  if (p.layer === "obstacle") return `${p.obstacle_type || "obstruction"} · ${p.agl_ft} ft AGL${p.city ? " · " + p.city : ""}`;
  return p.name || p.kind || p.utility || "";
}
function showTip(e, text) {
  if (!text || state.measure.on) return hideTip();
  tip.textContent = text;
  tip.style.left = e.point.x + 12 + "px"; tip.style.top = e.point.y + 12 + "px";
  tip.classList.remove("hidden");
}
function hideTip() { tip.classList.add("hidden"); }

/* ---------- measure tool ---------- */
$("btn-measure").onclick = () => {
  state.measure.on = !state.measure.on; state.measure.pts = [];
  $("btn-measure").classList.toggle("active", state.measure.on);
  if (!state.measure.on && map.getSource("measure")) {
    map.getSource("measure").setData({ type: "FeatureCollection", features: [] });
    renderDenominator();
  }
  map.getCanvas().style.cursor = state.measure.on ? "crosshair" : "";
};
function measureClick(e) {
  state.measure.pts.push([e.lngLat.lng, e.lngLat.lat]);
  const pts = state.measure.pts;
  const fc = { type: "FeatureCollection", features: [
    { type: "Feature", geometry: { type: "LineString", coordinates: pts }, properties: {} },
    ...pts.map((c) => ({ type: "Feature", geometry: { type: "Point", coordinates: c }, properties: {} }))] };
  if (!map.getSource("measure")) {
    map.addSource("measure", { type: "geojson", data: fc });
    map.addLayer({ id: "measure-line", type: "line", source: "measure",
      paint: { "line-color": "#0f172a", "line-width": 2, "line-dasharray": [2, 1] } });
    map.addLayer({ id: "measure-pts", type: "circle", source: "measure",
      paint: { "circle-radius": 3.5, "circle-color": "#0f172a" } });
  } else map.getSource("measure").setData(fc);
  let m = 0;
  for (let i = 1; i < pts.length; i++) m += havM(pts[i - 1][1], pts[i - 1][0], pts[i][1], pts[i][0]);
  $("denominator").innerHTML = `📏 <b>${(m / MI).toFixed(2)} mi</b> (${pts.length} points — click to extend, toggle 📏 to finish)`;
}

/* ---------- header / ledger / denominator ---------- */
function renderStatebar() {
  const t = state.summary.totals;
  $("statebar").textContent =
    `${fmt(t.all_parcels)} parcels · ${fmt(t.class_union)} in rendered classes · built ${state.summary.built_at_utc.slice(0, 16)}Z`;
}
function renderLedger() {
  const c = state.summary.cannot_assess;
  $("ledger").innerHTML =
    `<b>Honesty ledger:</b> ${fmt(c.si_observations_unmappable)} SI observations unmappable · ` +
    `${fmt(c.parcels_without_geometry)} parcel w/o geometry · ${fmt(c.parcels_geometry_but_no_county)} w/o county · ` +
    `substations without published coords stay off-map but in counts · MISO headroom is the licensed Orennia DPP-2025 study, BOTH directions, one binding figure per bus — the old worst/median/best triple is gone, it invited a reader to pick the flattering one · ` +
    `PJM bus locations marked ESTIMATE render as hollow red rings · grid distances are to the nearest mapped feature (a floor, not a guarantee) · ` +
    `headroom DIRECTION matters, and we now hold BOTH for BOTH operators: PJM from our own case-23 harvest, MISO from the licensed Orennia DPP-2025 proxy — MISO publishes no load-side figure at all, so that half is licensed rather than ours. Its 300MW numbers answer the generator question and a MISO load-direction source is an open acquisition lane.`;
}
function renderDenominator() {
  if (state.measure.on) return;
  // G74: the Excel and CSV buttons enable and disable together -- two exports of one view that
  // could disagree about whether there is anything to export would be a nasty little bug.
  const el = $("denominator");
  const btn = { set disabled(v) { $("export-csv").disabled = $("export-xlsx").disabled = v; },
                get disabled() { return $("export-csv").disabled; } };
  if (map.getZoom() < PARCEL_ZOOM) {
    el.innerHTML = `County view — shading counts <b>all ${fmt(state.summary?.totals.all_parcels)}</b> parcels. Zoom to z≥${PARCEL_ZOOM} for parcels; layers stay on at every zoom.`;
    btn.disabled = true; return;
  }
  const inView = countiesInView();
  let classTotal = 0, match = 0, loaded = 0;
  for (const f of state.counties.features)
    if (inView.includes(f.properties.fips)) classTotal += f.properties.class_union;
  state.undatedSI = 0;   // counted by jsMatches during THIS pass, so reset immediately before it
  for (const fips of inView) {
    const feats = state.loaded.get(fips); if (!feats) continue;
    loaded++;
    if (countyOk(fips)) for (const ft of feats) if (jsMatches(ft.properties)) match++;
  }
  const undated = state.undatedSI
    ? `<br><span class="cannot">${fmt(state.undatedSI)} of these carry an SI signal with no event date — recency cannot be assessed for them, so they are kept rather than dropped.</span>` : "";
  el.innerHTML = `<b>${fmt(match)}</b> sites pass the screener, of <b>${fmt(classTotal)}</b> class sites in view (${loaded}/${inView.length} counties loaded${state.loading.size ? "…" : ""}).${undated}<br><span class="hint">County shading counts every parcel — nothing is dropped by the screen.</span>`;
  btn.disabled = match === 0;
}

/* ================= COMPOSITE SCORING (spec §11) =================================
   Contract: 0-100 sub-scores each with a STATED BASIS -> part scores -> composite;
   ASSESSABLE-ONLY AVERAGING AT EVERY LEVEL; defaults the user can override; every score
   opens its evidence.

   Two rules from ANALYSIS_METHODOLOGY shaped this:
   · "No hard-coded floors/ceilings/radii/weights - config-driven." Everything tunable lives
     in SCORE_CFG below and the weights are sliders, not constants buried in a formula.
   · §2.21 "a ranked list dominated by one unusual subgroup means ranking selects for the
     error." So P3 SATURATES: a parcel twice the size you asked for scores 100, and a parcel
     fifty times the size also scores 100. Scoring size linearly would rank the biggest
     polygon in Indiana first every time - which is how an inverted full-globe parcel wins a
     siting search (see the platform's D85).

   cannot-assess returns null and is DROPPED FROM THE DENOMINATOR. It never becomes a zero,
   because zero means "measured and bad" and null means "we could not look". */
const SCORE_CFG = {
  weights: { p1: 2, p2: 5, p3: 4, p4: 3, p5: 3, p6: 1 },   // defaults; user overrides via sliders
  p2: { subMiFull: 0.5, subMiZero: 6, kvGood: 138, lineMiFull: 0.5, lineMiZero: 4 },
  p3: { saturateAtMultiple: 2 },        // hits 100 at 2x the MW you asked for
  p4: { flood: -35, wetland: -20, protected: -45, bonusEach: 12, bonusCap: 24 },
  // P5 scores the publisher's OWN posture category, not a scale I invented. The first version
  // of this scored opposition_intensity linearly to a guessed ceiling of 8 and every Marion
  // County parcel came out 0 — because the measured distribution is nothing like 0-8: across
  // the 92 counties it runs min 0, median 0, p75 2, p90 4, and then Marion alone at 25. One
  // county is 3x the next (Marshall, 8). A linear scale either flattens 90% of the state or
  // zeroes its largest metro. The categorical posture is the publisher's judgment and is
  // robust to that outlier; intensity is reported as context with its rank.
  p5: { posture: { quiet: 100, active_discussion: 70, contested: 45, restricted: 20 }, unknown: 60 },
  // P6 saturates at the MEASURED p90 of the 87 counties holding a queue figure (median 259 MW,
  // p75 700, p90 1493, max 7977) rather than a round number.
  p6: { queueMwSaturate: 1493 },
};
const clamp100 = (x) => Math.max(0, Math.min(100, x));
const lerpDown = (v, full, zero) => v == null ? null : clamp100(100 * (zero - v) / (zero - full));

/* Each sub-score returns {score, basis} or null for cannot-assess. */
function scoreP1(p) {
  const n = Number(p.si_signal_events) || 0, types = Number(p.si_signal_types) || 0;
  if (p.has_si_signal !== true)
    return { score: 0, basis: "no seller-intent signal fired on this parcel (measured, not missing)" };
  const breadth = clamp100(35 + 25 * Math.min(types, 2) + 5 * Math.min(n, 3));
  // Recency now scores, which it could not before. Under the v1 flag only 0.6% of flagged parcels
  // carried an event date, so a recency term would have measured our coverage instead of the
  // signal; under v2 it is 92%. A parcel with NO date still gets no recency term rather than a
  // penalty — a missing date is not an old date.
  const r3 = Number(p.si_events_3y) || 0, r5 = Number(p.si_events_5y) || 0;
  const bonus = r3 > 0 ? 15 : (r5 > 0 ? 8 : 0);
  const why = r3 > 0 ? `${r3} inside 3 years` : (r5 > 0 ? `${r5} inside 5 years` : null);
  return { score: clamp100(breadth + bonus),
    basis: `${n} signal event${n === 1 ? "" : "s"} across ${types} signal type${types === 1 ? "" : "s"}` +
      (why ? ` · ${why}` : "") +
      (p.si_last_event_date ? ` · latest ${p.si_last_event_date}`
                            : " · no event date held, so recency is not scored (not penalised)") };
}
function scoreP2(p) {
  if (p._dsub_mi == null && p._dline_mi == null) return null;   // distances not computed for this parcel
  const parts = [], why = [];
  if (p._dsub_mi != null) {
    let s = lerpDown(p._dsub_mi, SCORE_CFG.p2.subMiFull, SCORE_CFG.p2.subMiZero);
    if (p._dsub_kv != null && p._dsub_kv < SCORE_CFG.p2.kvGood) s *= 0.75;   // low-voltage is worth less
    parts.push(s);
    why.push(`${p._dsub_mi} mi to ${p._dsub_name || "a substation"}${p._dsub_kv ? ` (${p._dsub_kv} kV)` : ""}`);
  }
  if (p._dline_mi != null) {
    parts.push(lerpDown(p._dline_mi, SCORE_CFG.p2.lineMiFull, SCORE_CFG.p2.lineMiZero));
    why.push(`${p._dline_mi} mi to a transmission line`);
  }
  return { score: parts.reduce((a, b) => a + b, 0) / parts.length, basis: why.join(" · ") };
}
function scoreP3(p) {
  const a = acreageOf(p), target = V("f-mw-val") || 25, density = V("f-density") || 4;
  const fits = a.acres * density;
  const s = clamp100(100 * fits / (target * SCORE_CFG.p3.saturateAtMultiple));
  return { score: s, basis: `${a.acres.toFixed(1)} ac — ${a.basis} (${a.mode === "dc" ? "hyperscale DC: builds over structures" : "BESS: sites around structures"}) ` +
    `— fits ~${Math.floor(fits)} MW at ${density} MW/acre; you asked for ${target} MW, and this saturates at ${target * SCORE_CFG.p3.saturateAtMultiple} MW` +
    (a.disputed ? " — sources disagree on this parcel's size, see the panel" : "") };
}
function scoreP4(p) {
  const c = SCORE_CFG.p4; let s = 100; const why = [];
  if (p.sfha_flood === true) { s += c.flood; why.push("in an SFHA flood zone"); }
  if (p.wetland_on_parcel === true) { s += c.wetland; why.push("wetland on parcel"); }
  if (p.protected_land === true) { s += c.protected; why.push("overlaps protected land"); }
  const bonus = p.bonus_kinds ? String(p.bonus_kinds).split(",").filter(Boolean) : [];
  if (bonus.length) { s += Math.min(bonus.length * c.bonusEach, c.bonusCap); why.push(`bonus-credit: ${bonus.join(", ")}`); }
  if (!why.length) why.push("measured clear on flood, wetland and protected land; no bonus geography");
  return { score: clamp100(s), basis: why.join(" · ") };
}
function scoreP5(p, fips) {
  const po = (state.ctx.by_fips[fips] || {}).posture;
  if (!po) return null;
  const cfg = SCORE_CFG.p5;
  const cp = countyPosture(fips);
  const key = String(po.posture || "").toLowerCase();
  let s = key in cfg.posture ? cfg.posture[key] : cfg.unknown;
  const why = [];
  /* G11: THE VERIFIED ACTION LEADS, and the 4-value summary is only the fallback.
     Scored off `po.posture` alone, Cass read "quiet" - the most permissive band we have - while
     holding a ban, and Clark and Jasper read "quiet" while having APPROVED a data centre, which
     is the most actionable positive signal a siter can get. Both directions were wrong. */
  /* ⚠ TAKE THE WORSE OF THE TWO, THEN ALLOW A LIFT ONLY IF NEITHER OBJECTS.
     The first version of this clamp read "if a verified action exists, ignore the legacy flag",
     and that inverted the very bug it was fixing: MARION carries has_local_restriction = true and
     a live moratorium, but its verified headline is the milder "proposed" with approved = true,
     so it jumped from 20 to a PERFECT 100 - a county with a live moratorium scored as wide open.
     A restriction from either vocabulary is evidence; only the absence of both permits the lift. */
  if (cp.verified) why.push(`verified county action: ${cp.headline}`);
  else why.push(`county posture: ${po.posture || "unrecorded"} (no verified action on record)`);

  if (cp.blocking) {
    s = Math.min(s, cfg.posture.restricted);
    why.push(cp.why || "a verified blocking action is on the books");
  } else if (cp.legacyRestricted) {
    s = Math.min(s, cfg.posture.restricted);
    why.push("a local restriction is on the books, and no verified action supersedes it");
  } else if (cp.approved) {
    s = Math.max(s, cfg.posture.quiet);
    why.push("this county has APPROVED a data center - precedent exists");
  } else if (cp.verified && cp.why) {
    why.push(cp.why);
  }
  const oi = Number(po.opposition_intensity);
  if (Number.isFinite(oi)) why.push(`opposition intensity ${oi} (statewide median 0, p90 4, max 25)`);
  // ⛔ NOT `po.local_moratoriums` / `po.local_bans`: local_bans is 0 on all 92 counties while the
  // warehouse holds two bans, so a test on it can never fire. Count the verified actions instead.
  if (cp.nActions) why.push(`${cp.nActions} verified action(s) on record`);
  return { score: clamp100(s),
    basis: why.join(" · ") + " — COUNTY grain, not parcel; intensity partly tracks news volume, so large metros read higher" };
}
function scoreP6(p, fips) {
  const c = state.ctx.by_fips[fips] || {}, parts = [], why = [];
  if (c.fcc && c.fcc.units) {
    const share = 100 * (c.fcc.fiber_units || 0) / c.fcc.units;
    parts.push(clamp100(share));
    why.push(`${share.toFixed(0)}% of county business units have fibre ≥100/20 (statewide median 60%)`);
  }
  if (c.queue && c.queue.active_mw != null) {
    parts.push(clamp100(100 * c.queue.active_mw / SCORE_CFG.p6.queueMwSaturate));
    // Direction RULED by the operator 2026-08-15: active queue MW counts as SUPPLY, i.e.
    // favourable — generation arriving near the site. (The competing reading, that those
    // projects contend for the same interconnection capacity, was considered and rejected.)
    why.push(`${fmt(c.queue.active_mw)} MW active in the county queue, counted as supply`);
  }
  if (!parts.length) return null;
  return { score: parts.reduce((a, b) => a + b, 0) / parts.length,
           basis: why.join(" · ") + " — COUNTY grain, not parcel" };
}
/* ---------- G96: EVERY ranked match on the map, not just the shortlist ------------------------
   Operator, 2026-08-19: *"beyond the short list of “best” sites, it should also highlight
   all of the applicable sites to the filters/layers applied to the map"*.

   ⭐ This is a paint change over state we already hold — `sc-rank` has always computed a composite
   for every matching parcel in view and then thrown all but twelve away. The scores are banded,
   not ramped, for the same reason the bus layer is (G77): a continuous ramp asks the reader to
   compare shades, and the useful question is "which tier is this in".
   ⚠ It paints the parcels that were RANKED, which is not the same set as the parcels that pass
   the filters — a parcel whose every scoring part is unmeasurable gets no composite and is
   deliberately left unpainted rather than scored zero. */
const RANK_BANDS = [
  [80, "#15803d", "80–100 — strongest on the parts we could measure"],
  [60, "#65a30d", "60–79"],
  [40, "#eab308", "40–59"],
  [0,  "#f97316", "under 40"],
];
function paintRanked(rows) {
  const byBand = new Map(RANK_BANDS.map(([t]) => [t, []]));
  for (const r of rows) {
    const band = RANK_BANDS.find(([t]) => r.composite >= t);
    if (band) byBand.get(band[0]).push(r.p.parcel_key);
  }
  /* The parcels are already drawn by their own county layers, so this recolours THEM rather than
     adding a second geometry source — drawing the same polygon twice is how a map ends up with
     two disagreeing outlines. */
  const colourExpr = ["case"];
  for (const [t, colour] of RANK_BANDS) {
    const keys = byBand.get(t);
    if (!keys.length) continue;
    colourExpr.push(["in", ["get", "parcel_key"], ["literal", keys]], colour);
  }
  colourExpr.push("#cbd5e1");
  let painted = 0;
  for (const fips of state.loaded.keys()) {
    const id = `sites-${fips}-fill`;
    if (!map.getLayer(id)) continue;
    try {
      map.setPaintProperty(id, "fill-color", colourExpr.length > 2 ? colourExpr : "#cbd5e1");
      map.setPaintProperty(id, "fill-opacity", 0.55);
      painted++;
    } catch (e) { /* a county mid-load has no layer yet; it will paint on its next rank */ }
  }
  /* ⛔ ONLY CLAIM IT IF IT HAPPENED. This was `state.rankPainted = true` unconditionally, so when
     no parcel layer existed the legend still announced "parcel color = your ranking score" over
     a map with no coloured parcel on it — a key describing a paint job that was never applied. */
  state.rankPainted = painted > 0;
  renderLayerLegend();
  return painted;
}
/* ⛔ The recolour has to be UNDOABLE, or the map keeps a stale ranking after the filters move and
   the reader reads last question's answer against this question's parcels.
   ⚠ Restores through `applyParcelHighlight()`, the function that already owns parcel fill — NOT
   through a remembered constant. A second copy of the default colour here would drift from
   `FILL_COLOR` and from the `f-hilite` highlight, and the loser would be invisible. */
function clearRankedPaint() {
  if (!state.rankPainted) return;
  state.rankPainted = false;
  for (const fips of state.loaded.keys()) {
    const id = `sites-${fips}-fill`;
    if (map.getLayer(id)) {
      try { map.setPaintProperty(id, "fill-opacity", 0.45); } catch (e) { /* mid-load */ }
    }
  }
  applyParcelHighlight();
}

function currentWeights() {
  const w = {};
  for (const k of Object.keys(SCORE_CFG.weights)) w[k] = Number($(`w-${k}`).value);
  return w;
}
/* The composite. Parts that cannot be assessed leave the denominator entirely. */
function scoreSite(p, fips, w) {
  const parts = { p1: scoreP1(p), p2: scoreP2(p), p3: scoreP3(p),
                  p4: scoreP4(p), p5: scoreP5(p, fips), p6: scoreP6(p, fips) };
  let num = 0, den = 0;
  for (const k of Object.keys(parts)) if (parts[k] && w[k] > 0) { num += parts[k].score * w[k]; den += w[k]; }
  const missing = Object.keys(parts).filter((k) => !parts[k] && w[k] > 0);
  return { composite: den ? num / den : null, parts, missing, weightUsed: den };
}
const PART_NAME = { p1: "Seller intent", p2: "Grid access", p3: "Land & size",
                    p4: "Environmental", p5: "Community", p6: "Market & infra" };

$("sc-on").addEventListener("change", (e) => {
  $("sc-weights").classList.toggle("hidden", !e.target.checked);
});
/* G68: the weights were range sliders capped at 5, with a read-only `wv-*` span mirroring each
   one. A user could neither type a weight nor set one above 5 -- and a cap on a weight is a silent
   filter on the ranking, the same shape as G58's .slice(0,14). They are now number inputs with no
   max, so the input IS the readout and the mirror spans are gone. `scoreSite()` still reads
   `w-${k}`, unchanged. */
$("sc-reset").onclick = () => {
  for (const [k, v] of Object.entries(SCORE_CFG.weights)) $(`w-${k}`).value = v;
};
$("sc-rank").onclick = () => {
  const w = currentWeights();
  if (!Object.values(w).some((x) => x > 0)) { $("sc-out").innerHTML = `<span class="cannot">Every weight is zero — nothing to rank on.</span>`; return; }
  const rows = [];
  const cannot = { p1: 0, p2: 0, p3: 0, p4: 0, p5: 0, p6: 0 };
  for (const fips of countiesInView()) {
    const feats = state.loaded.get(fips); if (!feats || !countyOk(fips)) continue;
    for (const ft of feats) {
      const p = ft.properties; if (!jsMatches(p)) continue;
      const r = scoreSite(p, fips, w);
      for (const k of r.missing) cannot[k]++;
      if (r.composite != null) rows.push({ p, fips, ...r });
    }
  }
  if (!rows.length) { $("sc-out").innerHTML = `<span class="cannot">No screened sites in view to rank.</span>`; return; }
  rows.sort((a, b) => b.composite - a.composite);
  state.ranked = rows;
  /* G96, operator 2026-08-19: *"beyond the short list of 'best' sites, it should also highlight
     all of the applicable sites to the filters/layers applied to the map"*.
     ⛔ `rows.slice(0, 12)` was a silent cap of exactly the G58 shape — it printed "N sites ranked"
     and then showed twelve, so a reader could not tell whether the 13th was close behind the 12th
     or nowhere near it. The list is now scrollable and shows up to 250, the count is stated, and
     EVERY ranked site is painted on the map rather than only the shortlist. */
  const LIST_CAP = 250;
  const top = rows.slice(0, LIST_CAP);
  paintRanked(rows);
  const cannotLine = Object.entries(cannot).filter(([, n]) => n > 0)
    .map(([k, n]) => `${PART_NAME[k]} ${fmt(n)}`).join(" · ");
  $("sc-out").innerHTML =
    `<b>${fmt(rows.length)}</b> screened sites ranked, and <b>every one of them is now painted on
     the map</b> — the list below is only the readable end of it.
     ${rows.length > LIST_CAP
        ? `<div class="hint">Listing the top ${fmt(LIST_CAP)} of ${fmt(rows.length)}; the rest are
           on the map and in the CSV. <b>Scroll the list.</b></div>` : ""}
     Click a row for its score breakdown.
     <div class="scroll" style="max-height:320px">
     <table>${top.map((r, i) => `<tr><td class="rank">${i + 1}</td>
       <td><a data-i="${i}">${r.p.parcel_key}</a><div class="hint">${(state.ctx.by_fips[r.fips]?.posture?.county_name) || r.fips} · ${r.p.occ_group}</div></td>
       <td class="sc">${Math.round(r.composite)}</td></tr>`).join("")}</table></div>
     ${cannotLine ? `<div class="cannot" style="margin-top:5px">Left out of the denominator where unmeasurable — ${cannotLine}. These sites are ranked on the parts we could assess, not marked down for the parts we could not.</div>` : ""}
     <div class="prov">weights ${Object.entries(w).map(([k, v]) => `${k.toUpperCase()}:${v}`).join(" ")} · composite = weighted mean of assessable parts only</div>`;
  for (const a of $("sc-out").querySelectorAll("a[data-i]"))
    a.onclick = () => { const r = top[Number(a.dataset.i)]; openScoreEvidence(r); };
};
function openScoreEvidence(r) {
  const w = currentWeights();
  const rows_ = Object.keys(PART_NAME).map((k) => {
    const s = r.parts[k];
    if (!s) return `<tr><td>${PART_NAME[k]} <span class="hint">w${w[k]}</span></td>
      <td colspan="2" class="cannot">not measured here — left out of the denominator</td></tr>`;
    return `<tr><td>${PART_NAME[k]} <span class="hint">w${w[k]}</span></td><td class="sc">${Math.round(s.score)}</td>
      <td><div class="scorebar"><i style="width:${Math.round(s.score)}%"></i></div>
      <span class="hint">${s.basis}</span></td></tr>`;
  }).join("");
  show(`Score ${Math.round(r.composite)} — parcel ${r.p.parcel_key}`,
    `<h3>How this score was built</h3><table>${rows_}</table>
     <div class="prov">Composite = weighted mean over the ${Object.values(r.parts).filter(Boolean).length}
       assessable parts (total weight ${r.weightUsed}); parts we could not measure were dropped from the
       denominator, never scored zero. Weights are yours — change them and re-rank.
       ${prov("in_sites")}</div>
     <div class="rowbtns" style="margin-top:6px"><button id="sc-open-parcel">Open the full parcel evidence</button></div>`,
    `${r.p.parcel_source}|${r.p.parcel_key}`);   // same shortlist key the parcel panel uses
  $("sc-open-parcel").onclick = () => openParcelEvidence(r.p, r.fips);
}

/* ---------- evidence panels ---------- */
const panel = $("evidence");
$("ev-close").onclick = () => panel.classList.add("hidden");
$("ev-print").onclick = () => window.print(); // print stylesheet isolates the panel for printing
// The dossier button only appears on a PARCEL panel — a dossier for a substation or a queue point
// would be a document about nothing. state.dossierFor carries the parcel the panel is showing.
$("ev-dossier").onclick = () => {
  if (state.dossierFor) openDossier(state.dossierFor.p, state.dossierFor.fips);
};
/* `prov()` lives in common.js. ⛔ Do not re-declare it here -- see the fetchGz note at the top of
   this file; `scripts/audit_js_duplicates.py` fails the build on a second declaration. */
/* G21 + G27 -- the severity BAND is what changes a decision, not the yes/no flag. "You are in a
   nonattainment area" is a fact; "you are in a SERIOUS ozone nonattainment area" is a permitting
   cost and a schedule. Ranked so the bad end is obvious without parsing EPA's vocabulary. The band
   is EPA's own published finding (citation + URL carried per row since the G27 re-clip); the
   consequence text is the statutory regime that band triggers, never our estimate. */
const NAA_RANK = { "Extreme": 6, "Severe-17": 5, "Severe-15": 5, "Serious": 4, "Moderate": 3,
  "Subpart 2/Moderate": 3, "Marginal": 2, "Subpart 2/Marginal": 2, "Transitional": 1,
  "Not Classified": 1, "Former Subpart 1": 1, "Incomplete Data": 0 };
function naaSoWhat(p) {
  const cls = p.classification;
  const rank = Object.prototype.hasOwnProperty.call(NAA_RANK, cls) ? NAA_RANK[cls] : null;
  let sev;
  if (!cls) {
    sev = p.current_status === "Maintenance"
      ? `<b>No classification applies &mdash; this area is in maintenance.</b> EPA redesignated it to
         attainment and it runs on a maintenance plan, so new combustion is reviewed under PSD rather
         than the stricter nonattainment route. This is the <i>lighter</i> of the two regimes.`
      : `<b>No classification published.</b> Cannot assess the band from EPA's own record &mdash;
         confirm with IDEM before sizing any combustion here.`;
  } else if (rank === null) {
    sev = `<b>${cls}</b> is a classification this app has no band for. Read EPA's finding before
           relying on it either way.`;
  } else if (rank >= 4) {
    sev = `<b>${cls} sits at the strict end.</b> The band sets both the size at which a new source
           counts as <i>major</i> and the ratio of emission offsets it must buy &mdash; the worse the
           band, the smaller the plant that is captured and the more offsets it owes. A generator
           fleet that is routine in an attainment county can here trigger LAER plus purchased
           offsets: real dollars, and months added to the schedule.`;
  } else if (rank >= 2) {
    sev = `<b>${cls} is a middle band.</b> Nonattainment New Source Review still reaches a major new
           source &mdash; LAER and offsets &mdash; but at a higher major-source threshold and a lower
           offset ratio than a Serious or Severe area.`;
  } else {
    sev = `<b>${cls}</b> is a legacy or unresolved designation, usually attached to a revoked standard
           or an area EPA could not classify. Treat it as a prompt to ask IDEM, not a live constraint.`;
  }
  const src = p.classification_url
    ? `<br><a href="${p.classification_url}" target="_blank" rel="noopener">EPA's published finding</a>`
    : "";
  return `<div class="sowhat">${sev}<br><b>Solar or battery-only? Largely moot.</b> The burden lands
    on combustion &mdash; it bites a gas-fired or diesel-backed data center, not a BESS.${src}</div>`;
}
/* THREE states, not two (operator, 2026-08-18: "say something that is more truthful to the user").
 *
 *   a value            -> show it
 *   measured, empty    -> caller passes `absent`, e.g. "none within 25 miles". This is a FINDING,
 *                         and a useful one: we looked and there is nothing there.
 *   not measurable     -> "not measured here" (the G8 wording), because we have no source, no
 *                         coverage, or the join did not resolve.
 *
 * ⛔ The two must never collapse into one phrase. Printing "none" for something we never measured
 * invents a negative finding the reader cannot detect - the same defect as treating an unpublished
 * rate as zero, which once produced 95 false "below floor" violations. Printing "cannot assess"
 * where we DID look and found nothing understates what we know, which is the complaint that
 * prompted this. The default stays the honest one, so a caller that says nothing is never taken to
 * be asserting emptiness. */
function row(k, v, absent) {
  /* G51 sweep, 2026-08-19. Pass `absent` ONLY when the source covers every parcel, so a null
     genuinely means "measured, nothing here". in_asset_distance_parcel and in_water_distance_parcel
     both cover all 532,868 candidates at fan-out 1.000, which is what makes the grid and water rows
     safe. Anything per-county or per-source keeps the default -- inventing "none" where we never
     looked is the defect this three-state helper exists to prevent. */
  const val = (v === null || v === undefined || v === "")
    ? `<span class="cannot">${absent || "not measured here"}</span>`
    : (typeof v === "number" ? fmt(v) : String(v));
  return `<tr><td>${k}</td><td>${val}</td></tr>`;
}
function show(title, html, starKey) {
  // every panel hides the dossier button; openParcelEvidence and openDossier re-show it, so a
  // substation or queue-point panel can never offer a dossier for a parcel it is not about
  if (!/^(Parcel|Dossier|Power Plan)/.test(title)) {
    $("ev-dossier").classList.add("hidden");
    state.dossierFor = null;
  }
  $("ev-title").textContent = title;
  $("evidence-body").innerHTML = html;
  const star = $("ev-star");
  if (starKey) {
    star.classList.remove("hidden");
    star.classList.toggle("starred", state.shortlist.some((s) => s.key === starKey));
    star.onclick = () => toggleShortlist(starKey, title);
  } else star.classList.add("hidden");
  panel.classList.remove("hidden");
}
/* Water evidence. Every row states what it means for a project, per the governing principle: a
   watershed name and a score are trivia until the reader knows what to do about them. */
function openWaterEvidence(p) {
  if (p.layer === "stress_basin") {
    const sc = Number(p.stress_score);
    const verdict = sc >= 3 ? "<b class='cannot'>Contested.</b> Expect scrutiny on any large new withdrawal, and budget time for it."
      : sc >= 2 ? "<b>Moderately stressed.</b> Withdrawal is workable but will be looked at."
      : "<b>Not stress-constrained.</b> Water is unlikely to be the thing that stops you here.";
    return show(`Water stress — basin ${p.basin_id}`, `
      <div class="hint" style="margin-bottom:8px">${verdict}</div>
      <table>
        ${row("Baseline water stress", p.stress_label, "WRI Aqueduct does not rate this basin")}
        ${row("Water depletion", p.depletion_label, "WRI Aqueduct does not rate this basin")}
        ${row("Groundwater decline", p.groundwater_decline_label, "WRI Aqueduct does not rate this basin")}
      </table>
      <div class="prov"><b>What this is:</b> the share of available surface water already
        allocated, from the WRI Aqueduct dataset, published per hydrological basin. It measures
        <i>competition for water</i>, not whether water is physically present.
        <b>Basins are not counties</b> — we keep them at their published grain rather than
        averaging them onto a county, which would invent a precision the source does not have.</div>`);
  }
  const rivers = Number(p.named_rivers) || 0, res = Number(p.reservoirs) || 0;
  const lakes = Number(p.lakes_over_10ha) || 0;
  const verdict = (res + lakes) > 0
    ? `<b>Surface water is present in this watershed</b> — ${res} reservoir(s) and ${lakes} lake(s)
       over 10 hectares, plus ${fmt(rivers)} named rivers.`
    : rivers > 0
      ? `<b>Rivers but no substantial standing water.</b> ${fmt(rivers)} named rivers and no
         reservoir or lake above 10 hectares, so a surface-water supply here means a river intake.`
      : `<b class="cannot">No substantial surface water recorded in this watershed.</b>`;
  show(`Watershed — ${p.name}`, `
    <div class="hint" style="margin-bottom:8px">${verdict}</div>
    <table>
      ${row("Watershed code (HUC8)", p.huc8)}
      ${row("States it spans", p.states)}
      ${row("Area", p.area_sqkm ? `${fmt(p.area_sqkm)} km²` : null)}
      ${row("Named rivers", rivers)}
      ${row("Reservoirs", res)}
      ${row("Lakes over 10 hectares", lakes)}
      ${/* G51: the NHD clip is COMPLETE for Indiana (163,976 flowlines, 7,430 waterbodies at
             100% state-cut completeness), so an empty here is a measured finding, not a gap. */
        row("Largest waterbody", p.largest_waterbody_sqkm ? `${fmt(p.largest_waterbody_sqkm)} km²` : null,
            "no waterbody recorded in this watershed (measured)")}
    </table>
    <div class="prov"><b>Why a watershed and not a county:</b> water is allocated, contested and
      permitted by watershed. Two parcels a mile apart in different subbasins can face different
      objections and different bodies. Note this watershed may cross a state line — several of
      Indiana's drain into Ohio, Michigan or Illinois, which is a jurisdictional fact worth knowing
      early.<br><b>The rivers and lakes above are counted, not drawn.</b> The national hydrography
      data we hold carries attributes with no geometry, so we can tell you how many there are and
      not where they run.</div>`);
}

/* ---------- G3: THE POWER PLAN ----------
   A four-page, print-to-PDF site document modelled on the Power Plan format the operator supplied
   (three worked examples: LA-Cajun, NJ-Jetstream, WI-Maple). The evidence panel answers "what do we
   know about this parcel"; this answers the question a developer actually takes to a utility:
   "what is the path to power here, who do I have to talk to, and what do I have to find out next".

   Page 1  status, load ramp, key takeaways, next steps, Figure 1 stakeholders, Figure 2 diagram
   Page 2  Figure 3 Path-to-Power Outlook - generation, transmission, tariffs, local rules
   Page 3  Figure 4 what stands between this parcel and power (DERIVED - G73 replaced the
           borrowed PDF's eight hardcoded "Not started" milestones, dossier audit D-8),
           Figure 5 who else holds a say over the land (G72 gates), Figure 6 evidence held
   Page 4  site detail and the stakeholder-meeting appendix

   Built from the SAME functions the screener and the panel use - acreageOf(), scoreSite(), prov()
   - so the document can never disagree with the map that produced it.

   Rules it must not break:
     · every figure names its source table and build date
     · cannot-assess prints as itself and is LEFT OUT of the score denominator, never zeroed
     · MW figures are adjustable assumptions at the user's own density, and say so
     · a headroom figure ALWAYS carries its direction and its study vintage. Our MISO case is
       the licensed DPP-2025 case, and a 0 there means every monitored facility at that bus is
       already over its rating - which must never read as "this bus is full" */

/* which service territory contains the parcel - Figure 1 needs the utility, and the utility is a
   polygon question, not a county question */
/* ⛔ WE HOLD THE FOOTPRINT, SO DO NOT ASK A POINT. Operator, 2026-08-18: *"we should already
   have the service territory footprints within this application, so that should be used if you
   are using parcels to tariff rates. As such, we really shouldn't ever be using centroids ... We
   only use it when we absolutely must, and this should not be one of those times."*

   `p.lat`/`p.lon` is a representative interior point - measured 2-332 m from the true centroid and
   always inside the parcel - but it is still ONE point standing in for a polygon. Resolving the
   serving utility from it means a parcel straddling a territory boundary is silently assigned to
   whichever territory happens to contain that point. That was survivable when the dossier only
   NAMED the utility. It is not survivable now that the same name selects a tariff book: a wrong
   territory attaches a dollar figure to the wrong company under this parcel's address.

   So test the parcel's own ring vertices. If they all land in one territory, that is the answer
   and it is now a polygon answer. If they do not, the parcel STRADDLES a boundary - which is a
   real finding about the site, not a defect - and the dossier says so instead of picking one.
   Returns { T, all, straddles, basis }. (dossier audit D-11) */
function territoryForParcel(fips, key, lat, lon) {
  const feats = state.loaded.get(fips) || [];
  const ft = feats.find((f) => f.properties && f.properties.parcel_key === key);
  const pts = [];
  if (ft && ft.geometry) {
    (function walk(c) {
      if (typeof c[0] === "number") { pts.push(c); return; }
      for (const x of c) walk(x);
    })(ft.geometry.coordinates);
  }
  if (!pts.length) {
    /* geometry not loaded (the county has not been opened). Fall back to the interior point and
       SAY that is what happened, rather than presenting it as a footprint answer. */
    const T = territoryAt(lat, lon);
    return { T, all: T ? [T] : [], straddles: false, basis: "interior point (parcel outline not loaded)" };
  }
  /* Sample the whole ring but cap the work - a parcel can carry thousands of vertices and this
     runs inside a click handler. Every vertex is a real boundary point of the parcel, so an even
     stride across them is a fair test of whether the parcel crosses a territory line. */
  const stride = Math.max(1, Math.floor(pts.length / 64));
  const seen = new Map();
  for (let i = 0; i < pts.length; i += stride) {
    const T = territoryAt(pts[i][1], pts[i][0]);
    if (T && T.utility) seen.set(T.utility, T);
  }
  const all = [...seen.values()];
  if (!all.length) {
    const T = territoryAt(lat, lon);
    return { T, all: T ? [T] : [], straddles: false, basis: "interior point (no vertex resolved)" };
  }
  return { T: all[0], all, straddles: all.length > 1,
           basis: `parcel footprint, ${Math.ceil(pts.length / stride)} boundary points tested` };
}


/* Bounding boxes, computed once and cached. territoryForParcel tests up to 64 ring vertices, and
   each test used to walk all 145 territories' full rings - 435 ms on a 70-acre parcel, inside a
   click handler. A bbox reject is four comparisons and changes NO answer: a point outside a
   polygon's bounding box cannot be inside the polygon. */
function terrBoxes() {
  if (state._terrBox) return state._terrBox;
  const boxes = [];
  for (const f of (state.terr ? state.terr.features : [])) {
    const g = f.geometry; if (!g) continue;
    const polys = g.type === "Polygon" ? [g.coordinates]
                : g.type === "MultiPolygon" ? g.coordinates : [];
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const poly of polys) for (const q of (poly[0] || [])) {
      if (q[0] < x0) x0 = q[0];
      if (q[0] > x1) x1 = q[0];
      if (q[1] < y0) y0 = q[1];
      if (q[1] > y1) y1 = q[1];
    }
    boxes.push({ f, polys, x0, y0, x1, y1 });
  }
  state._terrBox = boxes;
  return boxes;
}

function territoryAt(lat, lon) {
  if (!state.terr || lat == null || lon == null) return null;
  const inRing = (ring) => {
    let hit = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i], [xj, yj] = ring[j];
      if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) hit = !hit;
    }
    return hit;
  };
  for (const b of terrBoxes()) {
    if (lon < b.x0 || lon > b.x1 || lat < b.y0 || lat > b.y1) continue;   // bbox reject
    const f = b.f, polys = b.polys;
    /* ⛔ RINGS AFTER THE FIRST ARE HOLES, and only poly[0] was tested. A parcel inside a
       territory's donut hole - a municipal utility enclosed by an IOU, the common Indiana case -
       resolved to the ENCLOSING utility. That decides all four rows of the dossier's Figure 1,
       the regulated/market wording and next step 1, so it names the wrong company to call.
       Naming the wrong utility is worse than naming none. (dossier audit D-7) */
    for (const poly of polys) {
      if (!poly.length || !inRing(poly[0])) continue;
      let inHole = false;
      for (let h = 1; h < poly.length; h++) if (inRing(poly[h])) { inHole = true; break; }
      if (!inHole) return f.properties;
    }
  }
  return null;
}

/* nearest bus IN A NAMED DIRECTION, and IN THE SITE'S OWN GRID.
   Two constraints, both learned the hard way on the first render:

   1. Never "nearest bus" without the direction — a withdrawal number and an injection number
      answer different questions, and measured on 200 AEP buses they agree on exactly ZERO.
   2. ⛔ Never a bus from a DIFFERENT balancing authority. The first Power Plan drawn for a Marion
      County site (MISO / AES Indiana) quoted a **PJM** withdrawal bus 40.6 miles away as its
      load-side answer, while Figure 1 correctly said no MISO load-side figure exists. The document
      contradicted itself on the same page. A PJM bus cannot serve a MISO-territory site: you do
      not get to interconnect to a neighbouring RTO because its data happens to be published.
   3. And a cap, because a "nearest" 40 miles away is not a fact about the site. */
const BUS_MAX_MI = 25;
function nearestBus(lat, lon, direction, ba) {
  if (!state.gridsiting || lat == null) return null;
  let best = null;
  for (const b of state.gridsiting.buses) {
    if (b.direction !== direction || b.lat == null) continue;
    if (ba && b.src && b.src !== ba) continue;        // same grid operator only
    const d = havM(lat, lon, b.lat, b.lon);
    if (!best || d < best.d) best = { d, b };
  }
  if (!best) return null;
  const mi = +(best.d / MI).toFixed(1);
  return mi > BUS_MAX_MI ? null : { ...best.b, mi };
}

/* Grid-model facility names are raw solver identifiers - "243275 05DELAWR1 138 245803 05DELAWR2
   138 Z1" is a from-bus, a to-bus, voltages and a circuit id run together. Printing that in a
   document a developer takes to a utility is noise. Keep the readable station names. */
function bindingPlain(s) {
  if (!s) return null;
  const names = String(s).match(/[A-Z][A-Z0-9_.\-]{3,}/g) || [];
  const clean = [...new Set(names.map((n) => n.replace(/^\d+/, "")).filter((n) => n.length > 2))];
  return clean.length ? clean.slice(0, 2).join(" – ") : String(s).slice(0, 40);
}

/* ---------- G72/G73: who else holds a say over THIS point -------------------------------------
   The gate payload is 33 polygons and 4,591 points, already in memory from boot, so this is a
   direct test rather than a lookup against a precomputed table. The screener gets the same three
   facts from `in_land_gate_parcel` in BigQuery; this is the client-side twin for a single parcel.

   ⚠ The military distance is measured to the nearest POLYGON VERTEX, which is an upper bound on
   the true distance to the boundary and can read slightly long for a large installation. It is
   used to decide whether to RAISE the question, never to answer it, so erring long is the safe
   direction -- and the dossier says the review is triggered by the DoD, not by our number. */
function gatesForPoint(lat, lon) {
  const out = { mil: null, milMi: null, sua: [], tribal: null, tall1mi: 0, measurable: false };
  /* ⛔ `Number(null)` IS 0, AND 0 IS FINITE. The first version guarded with isFinite() alone, so a
     parcel carrying lat = null measured from (0, 0) -- the Gulf of Guinea -- and reported the
     nearest military installation as "5966.75 mi, Fort Wayne IAP-2". Not every parcel in the
     county payload carries a coordinate, so this was reachable, and it produced a garbage number
     that looks exactly like a measurement.
     ⚠ `measurable` is the third state: without it every coordinate-less parcel would render
     "none within reach (measured)", which invents a negative finding we never made -- the same
     defect as printing "none" where we never looked (G51). */
  const la = (lat === null || lat === undefined || lat === "") ? NaN : Number(lat);
  const lo = (lon === null || lon === undefined || lon === "") ? NaN : Number(lon);
  if (!state.gates || !Number.isFinite(la) || !Number.isFinite(lo)) return out;
  // Indiana's bounding box. A coordinate outside it is a bad row, not a distant site.
  if (la < 37.5 || la > 42.1 || lo < -88.6 || lo > -84.4) return out;
  out.measurable = true;
  lat = la; lon = lo;
  for (const f of state.gates.features) {
    const g = f.properties.layer;
    if (g === "obstacle") {
      const [ox, oy] = f.geometry.coordinates;
      if (havM(lat, lon, oy, ox) <= 1609.344) out.tall1mi++;
      continue;
    }
    const inside = f.geometry && f.geometry.type !== "Point" && pointInPoly(lon, lat, f.geometry);
    if (g === "sua" && inside) out.sua.push(f.properties.name);
    else if (g === "tribal" && inside) out.tribal = f.properties.name;
    else if (g === "military") {
      if (inside) { out.mil = f.properties.name; out.milMi = 0; continue; }
      const walk = (c) => {
        if (typeof c[0] === "number") {
          const d = havM(lat, lon, c[1], c[0]) / 1609.344;
          if (out.milMi === null || d < out.milMi) { out.milMi = d; out.mil = f.properties.name; }
        } else c.forEach(walk);
      };
      if (out.milMi !== 0) walk(f.geometry.coordinates);
    }
  }
  if (out.milMi != null) out.milMi = Math.round(out.milMi * 100) / 100;
  return out;
}

/* Figure 2 - the parcel drawn from its own geometry. No basemap, no centroid: the outline is the
   publisher's polygon, scaled to fit. A dossier that showed a pin instead of the parcel would be
   showing a place, not a property. */
function parcelDiagram(fips, key) {
  const feats = state.loaded.get(fips) || [];
  const ft = feats.find((f) => f.properties.parcel_key === key);
  if (!ft || !ft.geometry) return `<div class="hint cannot">Parcel outline not loaded — open the
    county on the map first and the diagram will draw.</div>`;
  const pts = [];
  (function walk(c) {
    if (typeof c[0] === "number") { pts.push(c); return; }
    for (const x of c) walk(x);
  })(ft.geometry.coordinates);
  if (!pts.length) return "";
  const xs = pts.map((q) => q[0]), ys = pts.map((q) => q[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const W = 300, H = 190, pad = 12;
  const sx = (x1 - x0) || 1e-6, sy = (y1 - y0) || 1e-6;
  const k = Math.min((W - 2 * pad) / sx, (H - 2 * pad) / sy);
  const px = (q) => [pad + (q[0] - x0) * k, H - pad - (q[1] - y0) * k];
  const rings = ft.geometry.type === "Polygon" ? [ft.geometry.coordinates]
    : ft.geometry.type === "MultiPolygon" ? ft.geometry.coordinates : [];
  const paths = rings.map((poly) => poly.map((ring) =>
    `<path d="${ring.map((q, i) => `${i ? "L" : "M"}${px(q).map((n) => n.toFixed(1)).join(",")}`).join(" ")}Z"
      fill="#d97706" fill-opacity=".18" stroke="#b45309" stroke-width="1.3"/>`).join("")).join("");
  // a scale bar makes the drawing readable as a SIZE rather than a shape
  const midLat = (y0 + y1) / 2;
  const mPerDeg = 111320 * Math.cos(midLat * Math.PI / 180);
  const barM = 200, barPx = (barM / mPerDeg) * k;
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:340px;background:#fbfcfd;
      border:1px solid #e3e6ec;border-radius:6px">${paths}
    ${barPx > 8 && barPx < W - 30 ? `<line x1="${pad}" y1="${H - 5}" x2="${pad + barPx}" y2="${H - 5}"
      stroke="#334155" stroke-width="1.5"/><text x="${pad}" y="${H - 8}" font-size="8"
      fill="#334155">200 m</text>` : ""}</svg>`;
}

async function openDossier(p, fips) {
  if (!state.gridsiting) {
    try { state.gridsiting = await fetchGz("data/gridsiting.json.gz"); }
    catch { state.gridsiting = { buses: [], mtep: [], utilities: [] }; }
  }
  /* ⛔ THE DOSSIER USED TO CARRY NO TARIFF DATA AT ALL, and said so in print - while the payload
     existed and the Market page priced every utility in it. Loaded lazily, on the same
     fetch-or-empty pattern as gridsiting, so a missing file degrades to "not held" instead of
     taking the map console down. (dossier audit D-1) */
  if (!state.tariffs) {
    try { state.tariffs = await fetchGz("data/tariffs.json.gz"); }
    catch { state.tariffs = { utilities: [] }; }
  }
  return renderPowerPlan(p, fips);
}

function renderPowerPlan(p, fips) {
  const a = (x) => x == null ? null : Number(x).toFixed(2);
  // county context is NESTED — {posture, queue, iocs, fcc}, not flat. Reading it flat produced
  // ten spurious "cannot assess" rows on the first build, which is a dossier lying about our
  // coverage rather than about the county. Read the shape, do not assume it.
  const c = state.ctx.by_fips[fips] || {};
  const po = c.posture || {}, q = c.queue || {}, ioc = c.iocs || {};
  const w = currentWeights();
  const r = scoreSite(p, fips, w);
  const uc = useCase();
  const density = V("f-density");
  const acr = acreageOf(p, uc);
  const mw = Math.floor(acr.acres * density);
  const assessable = Object.values(r.parts).filter(Boolean).length;
  const missing = Object.keys(PART_NAME).filter((k) => !r.parts[k]);

  // the verdict line: capability first, because a motivated seller on a 0.1-acre lot is not a site
  const fitsDC = (Number(p.mw_datacenter_4_per_acre) || 0) >= 25;
  const fitsBESS = (Number(p.parcel_acres) || 0) >= 0.5;
  const verdict = !fitsBESS
    ? `<b class="cannot">Too small for either use case</b> — ${acr.acres.toFixed(2)} ac cannot host a ~5 MW BESS`
    : fitsDC ? `<b>Viable for a hyperscale search</b> — land supports up to ${fmt(mw)} MW at ${density} MW/acre
                <span class="hint">(${mwReality(mw, density).band})</span>`
             : `<b>BESS-scale only</b> — land supports ~${mw} MW at ${density} MW/acre; below the 25 MW datacenter floor`;

  const partRows = Object.keys(PART_NAME).map((k) => {
    const s = r.parts[k];
    if (!s) return `<tr><td>${PART_NAME[k]}</td><td class="cannot">not measured here</td>
      <td class="hint">left out of the denominator, not scored zero</td></tr>`;
    return `<tr><td>${PART_NAME[k]} <span class="hint">w${w[k]}</span></td>
      <td class="sc">${Math.round(s.score)}</td><td class="hint">${s.basis}</td></tr>`;
  }).join("");

  /* ⭐ G133: THE DECLARED-INTENT FAMILY, ON THE MAP AS WELL AS THE SCREENER.
     Operator, 2026-08-21: *"all of the changes you made have to flow throughout the application,
     not just in one section."* This block existed only in the screener until then, so a reader on
     the map console could not see that a parcel's owner had FORMALLY DECLARED it surplus.
     ⛔ It renders SEPARATELY from the distress signals above and is labelled DECLARED, because the
     two are different claims: every D-code infers willingness from trouble, these state it. */
  const intentDetail = p.has_intent_signal === true ? `
      ${row("⭐ DECLARED intent", intentPlain(p.intent_signals),
             "an intent signal is recorded but its type is not named")}
      ${row("who", p.intent_who)}
      ${row("when", p.intent_last_date,
             "the source records no date for this declaration")}
      ${row("capacity given up here", p.intent_mw_given_up != null
             ? `${fmt(Math.round(p.intent_mw_given_up))} MW` : null,
             "not an interconnection withdrawal, so no capacity figure applies")}` : "";

  const siDetail = (p.has_si_signal === true ? `
      ${row("Owner-motivation signals", signalsPlain(p.si_signals),
             "signal recorded but its type is not named")}
      ${row("first / last event", [p.si_first_event_date, p.si_last_event_date].filter(Boolean).join(" → ") || null,
             "undated — the source publishes no date for this record")}
      ${row("events in 3 / 5 / 10 yrs", p.si_events_3y != null ? `${p.si_events_3y} / ${p.si_events_5y} / ${p.si_events_10y}` : null)}
      ${row("how it reached this parcel", p.si_keying)}
      ${row("where the date came from", p.si_date_basis)}`
    : `<tr><td>seller-intent signal</td><td>none admitted on this parcel</td>
       <td class="hint">measured, not missing</td></tr>`) + intentDetail;

  /* ⛔ THIS LIST CITED TWO TABLES THE DOSSIER NEVER READS (in_substations,
     in_transmission_union) AND OMITTED FOUR IT DOES - the bus capacities behind the headline
     withdrawal figure, the queue, the county posture and the tariffs. G16's test is "could a
     stranger re-run this from what the document states", and it could not. Now it names what
     actually produced the numbers above. (dossier audit D-4) */
  const tables = ["in_sites", "in_si_sites_flags_v2", "in_site_gates", "in_si_d22_echo_indiana",
                  "in_territories", "in_bus_capacity_tier0", "in_queue", "in_dc_actions_resolved",
                  "in_utility_tariff_riders", "in_urdb_rates",
                  // G72/G73: Figure 5 reads these, so the document must name them. The last
                  // version of this list cited two tables the dossier never read and omitted
                  // four it did -- G16's test is whether a stranger could re-run it from here.
                  "in_land_gates", "in_faa_obstacles_tall"];

  /* ---- the Power Plan's own inputs ---- */
  const lat = Number(p.lat), lon = Number(p.lon);
  /* footprint, not a point - see territoryForParcel */
  const terr = territoryForParcel(fips, p.parcel_key, lat, lon);
  const T = terr.T || {};
  const ba = (T.control_area || "").toUpperCase();
  // both constrained to the site's OWN balancing authority - see nearestBus()
  const wdBus = nearestBus(lat, lon, "withdrawal", ba);   // load side - what a data centre needs
  const injBus = nearestBus(lat, lon, "injection", ba);   // generator side
  const target = uc === "dc" ? Math.min(mw, 300) : Math.min(mw, 5);
  const G = state.gridsiting || { mtep: [], utilities: [] };
  /* ⛔ THIS WAS A 6-CHARACTER SUBSTRING MATCH on a station name, which both over-matches (any
     station sharing six leading characters) and under-matches (any naming variation inside them),
     and silently degraded to matching "~~" when there was no bus. There is no shared key between
     MTEP's `from_sub` and our bus names, so rather than dress a string guess up as a join, the
     row below reports the statewide count only and the near-station clause is withheld.
     Re-enable it when a real key exists. (dossier audit D-9) */
  const mtepNear = [];

  /* The parcel's own utility, priced through the SAME engine the Market page uses (common.js).
     85% is the load factor a 24/7 data centre runs at and is stated wherever the figure appears;
     the dossier has no load-factor control of its own. */
  const TARIFF_LF = 0.85;
  const quote = tariffQuote(state.tariffs, T.utility, target, TARIFF_LF);
  const [tariffHeld, tariffMeans] = tariffCells(quote, target, TARIFF_LF);

  const dateStr = new Date().toISOString().slice(0, 10);
  const regulated = String(T.regulated || "").toUpperCase().startsWith("Y") || T.utility_type === "INVESTOR OWNED";

  /* ---- G73: FIGURE 4 IS NOW DERIVED ----------------------------------------------------------
     Operator, 2026-08-19: *"The dossier should be geared more to the data that we hold, rather
     than the document I provided earlier - that was just an idea of what I have seen in the past.
     Make it revolve around our application."*

     What was here was eight hardcoded milestone rows, every one printed "Not started", copied
     from the sample PDF's interconnection checklist. Dossier audit D-8 named the problem exactly:
     ⛔ **it would not change if a study DID exist**, so it was literal markup wearing the costume
     of a measurement. A reader cannot tell a checklist nobody ran from a checklist that came back
     empty, and the second is a finding while the first is decoration.

     Replaced with the question the document actually exists to answer - what stands between THIS
     parcel and power - built from what we measured at this point. Ordered by what can STOP a
     project above what merely costs time, because that is the order a developer triages in. */
  const gt = gatesForPoint(lat, lon);
  const gateRow = (q, state_, action, cls) =>
    `<tr><td>${q}</td><td${cls ? ` class="${cls}"` : ""}>${state_}</td>
     <td class="hint">${action}</td></tr>`;
  const gateRows = [
    p.protected_land === true
      ? gateRow("Protected land", "OVERLAPS", "Usually ends the conversation. Confirm the designation and the manager before spending anything else.", "cannot")
      : gateRow("Protected land", p.protected_land === undefined ? "not measured" : "clear",
                "Measured against PAD-US. Nothing to do.", p.protected_land === undefined ? "cannot" : ""),
    p.sfha_flood === true
      ? gateRow("Flood hazard", "IN AN SFHA", "A mapped 1-in-100 hazard. Raises insurance and can rule out a build. Get a surveyed elevation certificate before design.", "cannot")
      : gateRow("Flood hazard", p.sfha_flood === undefined ? "not measured" : "clear",
                "FEMA Special Flood Hazard Area.", p.sfha_flood === undefined ? "cannot" : ""),
    p.wetland_on_parcel === true
      ? gateRow("Wetland on the parcel", "YES", "Federal permitting and a longer clock. Delineate early — the boundary decides how much of the parcel you actually keep.", "cannot")
      : gateRow("Wetland on the parcel", p.wetland_on_parcel === undefined ? "not measured" : "clear", "National Wetlands Inventory."),
    gt.tribal
      ? gateRow("Land status", `TRIBAL TRUST — ${gt.tribal}`, "A different sovereign. County zoning is not the path; the tribal government is the counterparty.", "cannot")
      : (gt.milMi != null && gt.milMi <= 3)
        ? gateRow("Land status", `${gt.milMi} mi from ${gt.mil}`, "Close enough that a DoD Siting Clearinghouse review is likely. It adds months rather than refusing. Raise it in the first utility conversation, not at permitting.")
        : !gt.measurable
          ? gateRow("Land status", "not measured", "This parcel carries no coordinate, so the federal and tribal gates could not be tested against it.", "cannot")
          : gateRow("Land status", "no federal or tribal interest within 3 mi", "Measured against military installations and tribal trust land."),
    (() => {
      const mwAvail = wdBus && wdBus.mw != null ? Math.round(wdBus.mw) : null;
      if (!wdBus) return gateRow("Getting power", "no bus measured within 25 mi", "We looked and found none in this balancing authority. That is a finding about the site, not a gap.", "cannot");
      if (mwAvail === 0) return gateRow("Getting power", `0 MW at ${wdBus.name}`,
        "Zero here is a statement about the STUDY CASE, not the bus — the network is already at or over its limit before any new request. Upgrades, a different bus, or a different site.", "cannot");
      return gateRow("Getting power", `${fmt(mwAvail)} MW at ${wdBus.name}, ${a(wdBus.mi)} mi`,
        `Against your ${fmt(target)} MW target. ${mwAvail >= target ? "Covers it on today's binding constraint." : "Short of it — expect upgrades, phasing, or a second point of delivery."}`);
    })(),
    /* G11: this row asked `po.has_local_restriction`, which is FALSE on Cass, Floyd, Huntington
       and Whitley — so the dossier told a reader "nothing on record" for a county holding a BAN.
       It now asks the verified vocabulary through the one resolver. */
    (() => {
      const cp = countyPosture(fips);
      if (cp.blocking) return gateRow("Local rules", `${String(cp.headline).toUpperCase()} ON RECORD`,
        `${cp.why} The Community page carries the receipt and the official URL.`, "cannot");
      // legacy-only: a restriction is recorded but no VERIFIED action explains it. Say exactly
      // that rather than borrowing the milder verified headline, which is how Marion would have
      // read "proposed" while holding a live moratorium.
      if (cp.legacyRestricted) return gateRow("Local rules", "RESTRICTION ON RECORD",
        "A local restriction is recorded for this county and no verified action supersedes it. Read the instrument before spending anything - the Community page carries what we hold.", "cannot");
      if (cp.approved) return gateRow("Local rules", `${cp.headline} — has approved before`,
        "This county has already approved a data center, which is the strongest positive precedent a siter can cite. Find that approval and read its conditions.");
      if (cp.verified) return gateRow("Local rules", cp.headline,
        `${cp.why} Not a block, but it is movement — track it.`);
      return gateRow("Local rules",
        po.opposition_intensity != null ? `no verified action; opposition intensity ${po.opposition_intensity}` : "nothing on record",
        "Nothing recorded is not the same as welcoming. It means no action has reached us.");
    })(),
    quote && quote.cents != null
      ? gateRow("What power costs", `${quote.cents.toFixed(2)}¢/kWh at ${T.utility}`,
                `Priced from that utility's own book at ${Math.round(TARIFF_LF * 100)}% load factor, riders included. Confirm which schedule you qualify for — eligibility has a ceiling as well as a floor.`)
      : gateRow("What power costs", T.utility ? "no priced book held" : "no utility resolved",
                T.utility ? "We hold no tariff book for this utility, so any figure would be a floor rather than a price." : "No territory polygon covers this parcel.", "cannot"),
  ].join("");

  /* Figure 1 - who has to say yes. Four roles, because those are the four conversations. */
  const fig1 = `
    <table class="pp">
      <tr><th>#</th><th>Role</th><th>Who</th><th>What it means for you</th></tr>
      <tr><td>1</td><td><b>Electric service utility</b></td>
        <td>${T.utility || '<span class="cannot">no territory polygon covers this parcel</span>'}
          ${terr.straddles ? `<div class="hint"><b>⚠ This parcel STRADDLES ${terr.all.length}
            service territories</b> — ${terr.all.map((x) => escHtml(x.utility)).join(", ")}. Which one
            serves you is decided at the meter, not by us, and the rate below is priced for the
            first. Confirm with both before relying on either.</div>` : ""}</td>
        <td class="hint">The company that would actually serve the site. They run the load study and
          set your rate schedule.</td></tr>
      <tr><td>2</td><td><b>Generation provider</b></td>
        <td>${T.utility ? (regulated
            ? `${T.utility} <span class="hint">(regulated market)</span>`
            : `${T.utility} or the wholesale market`) : '<span class="cannot">not resolved</span>'}</td>
        <td class="hint">${regulated
          ? "A regulated market, so power is bought through the utility. Securing generation bilaterally may still be possible via a special contract."
          : "Generation can be procured from the utility or on the wholesale market."}</td></tr>
      <tr><td>3</td><td><b>Transmission owner</b></td>
        <td>${T.holding_company || T.utility || '<span class="cannot">not resolved</span>'}</td>
        <td class="hint">Owns the high-voltage wires you would connect to, and builds any upgrades
          your project triggers.</td></tr>
      <tr><td>4</td><td><b>Balancing authority</b></td>
        <td>${ba || '<span class="cannot">not resolved</span>'}</td>
        <td class="hint">${ba === "MISO"
          ? "MISO runs the grid here. ⚠ MISO publishes only the sending-power direction publicly; the load-side figure below comes from our licensed Orennia subscription, which is the only source that carries it."
          : ba === "PJM" ? "PJM runs the grid here, and publishes load-side (withdrawal) capacity — the direction a data center needs."
          : "Sets the interconnection process and study queue."}</td></tr>
    </table>`;

  /* Key takeaways - generated, not written. Each one is a fact with a consequence. */
  const takeaways = [
    fitsDC ? `The land supports <b>up to ${fmt(mw)} MW</b> at your ${density} MW/acre assumption
      (${acr.acres.toFixed(0)} acres, ${acr.basis}). ${mwReality(mw, density).note}`
      : `<b>Size is the binding constraint.</b> ${acr.acres.toFixed(2)} acres supports about ${fmt(mw)} MW
         — below the 25 MW datacenter floor.`,
    /* Undeveloped land is NOT an owner-motivation signal — emptiness says nothing about whether
       the owner will sell (G10, and the D5 split parked 945,896 footprint-absence rows as
       NOT_A_SIGNAL). But it IS a genuine build advantage, and the app kept these parcels for
       exactly that reason. Say why, rather than leaving the reader to infer it. */
    (p.site_kind === "no_structure" || (Number(p.structure_count) || 0) === 0)
      ? `<b>Nothing built on this parcel.</b> That is not a distress signal — an empty parcel says
         nothing about whether its owner will sell — but it is a real <b>build</b> advantage: no
         demolition, no tenants to relieve, no structure to work around, and the whole area is
         available for a battery pad. Undeveloped land is the cleanest BESS inventory we hold.`
      : null,
    wdBus ? `Nearest <b>load-side</b> bus is <b>${wdBus.name}</b> (${fmt(wdBus.kv)} kV)
        at ${wdBus.mi} mi, with <b>${fmt(wdBus.mw)} MW</b> of published withdrawal capacity.`
      : `<b>No load-side capacity figure could be matched to this site.</b> ${ba === "PJM"
         ? "We hold PJM's current case for 1,826 buses but can place only 227 of them, and none is within 25 miles"
         : "MISO publishes none publicly and our licensed substitute has no bus within 25 miles"}
         — a gap in OUR coverage, not a finding about the site.`,
    injBus && injBus.mw > 0
      ? `Nearest generation-side point <b>${injBus.name}</b> shows ${fmt(injBus.mw)} MW of injection
         headroom — relevant only if you intend to co-locate generation.`
      : injBus && injBus.overloaded_base > 0
        // G27: we can now say WHY the zero, instead of only that it is zero.
        ? `Generation-side headroom reads <b>zero at ${injBus.name}</b>, and we can say why:
           <b>${injBus.overloaded_base} monitored facilities there are already over their rating
           before any new request exists</b>, while the most permissive facility at the same point
           shows ${fmt(injBus.best_facility_mw)} MW. So the zero describes <b>a constraint that
           predates your project</b>, not a bus with nothing left. ⚠ Our study case is
           <b>DPP-2021</b>, four cycles old and <i>unmitigated</i>; the current published case has
           those mitigations applied.`
        : `Generation-side headroom nearby reads <b>zero</b>. ⚠ Our MISO study case is
           <b>DPP-2021</b>, four cycles old: it models a grid saturated by projects queued in 2021,
           most since withdrawn, and omits transmission built since. Treat a zero here as
           <i>“our model is stale”</i>, not <i>“this bus is full”</i>.`,
    p.has_si_signal === true
      ? `The owner shows a public reason to sell: <b>${signalsPlain(p.si_signals) || "signal on record"}</b>${
          p.si_last_event_date ? ` (latest ${p.si_last_event_date})` : " — date not recorded"}.`
      : `<b>No owner-motivation signal.</b> This is a cold approach — the land is capable, but
         nothing suggests the owner is looking to transact.`,
    /* G11: this takeaway printed the stale 4-value posture, so it said "County posture is quiet"
       for CASS, which holds a ban. It now reads the same resolver as the score and the filter. */
    (() => {
      const cp = countyPosture(fips);
      if (cp.blocking) return `<b class="cannot">This county has a verified ${cp.headline}
        on record.</b> ${cp.why}`;
      if (cp.legacyRestricted) return `<b class="cannot">A local restriction is recorded for this
        county</b> and no verified action supersedes it — read the instrument before committing.`;
      if (cp.approved) return `<b>This county has already APPROVED a data center.</b> That is the
        strongest positive precedent available to you; find the approval and read its conditions.`;
      if (cp.verified) return `County has ${cp.nActions} verified action(s) on record, led by
        <b>${cp.headline}</b>. ${cp.why || ""}`;
      return po.posture ? `County posture is <b>${po.posture}</b>, with no verified action on
        record — which is not the same as welcoming.` : null;
    })(),
  ].filter(Boolean);

  /* Next steps - the actual calls to make, in order */
  const steps = [
    T.utility ? `Engage <b>${T.utility}</b> to confirm service territory and open a load study for
      a ~${fmt(target)} MW request at this address.`
      : `Confirm which utility serves this parcel — our territory polygons did not resolve it.`,
    ba === "MISO"
      ? `Ask ${T.utility || "the utility"} directly for load-serving capability at the nearest
         station. <b>MISO publishes no public withdrawal headroom</b>, so the utility's own study is
         the only route to that number.`
      : `Ask for a QueueScope-equivalent withdrawal study at the nearest bus and confirm the
         published figure against the utility's own model.`,
    /* ⛔ THIS USED TO PRINT A HARDCODED $210,000/yr FROM A WORKED 35 MW EXAMPLE AT ONE UTILITY,
       unconditionally, for every parcel in Indiana. The advice was right and the number was
       somebody else's. It is now this utility's own spread at this parcel's load. (audit D-3) */
    (quote && !quote.none && !quote.urdbOnly && quote.rows.length > 1)
      /* ⚠ ONE NUMBER, ONE FORMAT. This line and the Figure 3 tariff cell describe the same spread,
         and rounding it to whole millions here while the cell showed one decimal printed "$2M" and
         "$2.3M" in the same document. Two figures for one fact is how a reader stops trusting
         both. It also has to name the right CAUSE: where the cheapest and dearest rows are
         different SCHEDULES, telling the reader to go and check their service voltage sends them
         after the wrong thing. */
      ? (() => {
          const lo = quote.rows[0], hi = quote.rows[quote.rows.length - 1];
          const d = hi.total - lo.total;
          const amt = Math.abs(d) >= 1e6 ? `$${(d / 1e6).toFixed(1)}M` : `$${fmt(Math.round(d))}`;
          const sameSched = lo.code === hi.code;
          return `Establish the rate schedule that applies at ~${fmt(target)} MW${sameSched
            ? " and at your expected service voltage" : ""}. At <b>${quote.utility}</b> the options
            you qualify for span <b>${lo.cents.toFixed(2)}–${hi.cents.toFixed(2)}¢/kWh</b> at
            ${(TARIFF_LF * 100).toFixed(0)}% load factor — <b>${amt} a year</b> — ${sameSched
            ? `and the difference is the <b>service voltage</b>, so confirm which one you can
               physically reach before assuming the cheapest.`
            : `and the difference is <b>which schedule you qualify for</b> (${lo.code} against
               ${hi.code}), which turns on contract demand and load factor — confirm your
               eligibility with them, not just the voltage.`}`;
        })()
      : `Establish the rate schedule that applies at ~${fmt(target)} MW and at your expected service
         voltage. <b>Service voltage materially changes the bill</b>, and we hold no priced
         schedule for this utility, so ask them for the applicable schedule and its riders.`,
    po.has_local_restriction
      ? `⚠ Local restrictions are recorded in this county — confirm current zoning status and any
         moratorium expiry before spending on diligence.`
      : `Confirm local zoning and whether any moratorium is pending. Indiana's data-center rules are
         largely county-level and often uncodified, so absence from our data is not proof of absence.`,
    acr.disputed ? `Resolve the acreage dispute with the county assessor before relying on capacity.` : null,
  ].filter(Boolean);

  show(`Power Plan — parcel ${p.parcel_key}`, `
    <div class="dossier powerplan">

    <!-- ============================ PAGE 1 ============================ -->
    <div class="pp-hd">
      <div><b>The Power Plan</b> — ${po.county_name || fips} County, Indiana</div>
      <div class="hint">Parcel ${p.parcel_key} · prepared ${dateStr}</div>
    </div>

    <!-- ⭐ G125: the dossier opens by saying WHERE the site is. A document a reader is expected to
         act on has to be checkable against imagery before anything else in it means much, and
         until now the dossier printed a parcel key and no location at all. -->
    <h3>Where this site is</h3>
    <table class="pp">${locationRows(p)}</table>

    <table class="pp">
      <tr><th style="width:31%">Interconnection status</th>
          <td>No utility study on record for this site. This is a <b>prospecting</b> document: it
            describes the path to power, not a project in progress.</td></tr>
      <tr><th>Expected load ramp</th>
          <td>Phase 1 <b>${fmt(target)} MW</b> · Phase 2 TBD · Phase 3 TBD
            <div class="hint">Phase 1 is your ${density} MW/acre assumption capped at a typical
              first phase. Edit the density on the left to change it.</div></td></tr>
      <tr><th>Verdict</th><td>${verdict}</td></tr>
    </table>

    <h3>Key takeaways and concerns</h3>
    <!-- .filter(Boolean): takeaways may now contain nulls (an entry that only applies to some
         parcels, e.g. the undeveloped-land note). Without it a null renders as "<li>null</li>". -->
    <ul class="pp-list">${takeaways.filter(Boolean).map((t) => `<li>${t}</li>`).join("")}</ul>

    <h3>Next steps for this property</h3>
    <ol class="pp-list">${steps.map((t) => `<li>${t}</li>`).join("")}</ol>

    <h3>Figure 1 · Electric stakeholder roles and responsibilities</h3>
    ${fig1}
    <div class="prov">${prov("in_territories")} · resolved by ${escHtml(terr.basis)} against the
      published territory boundary — <b>not by county, and not from a centroid</b>. Ring
      vertices are tested individually so a parcel crossing a territory line is reported as
      crossing it rather than silently assigned to one side.</div>

    <h3>Figure 2 · Parcel diagram</h3>
    ${parcelDiagram(fips, p.parcel_key)}
    <div class="prov">The parcel's own recorded boundary, drawn to scale. <b>Acreage, the
      distances to transmission, substations and water, and the service territory above are all
      measured against this polygon</b>, never a centroid. ⚠ The one exception is stated rather
      than hidden: the <b>nearest bus</b> in Figure 3 is measured from the
      parcel's interior point, because the bus locations we hold are themselves points.</div>

    <!-- ============================ PAGE 2 ============================ -->
    <div class="pp-break"></div>
    <h3>Figure 3 · Path-to-power outlook</h3>
    <table class="pp">
      <tr><th style="width:19%">Parameter</th><th style="width:46%">What we hold</th><th>What it means</th></tr>

      <tr><td><b>Getting power<br>(withdrawal)</b></td>
        <td>${wdBus
          ? `<b>${wdBus.name}</b> · ${fmt(wdBus.kv)} kV · ${wdBus.mi} mi<br>
             <b>${fmt(wdBus.mw)} MW</b> published withdrawal capacity
             ${wdBus.binding ? `<div class="hint">first constraint to bind: ${bindingPlain(wdBus.binding)}</div>` : ""}
             <div class="hint">vintage: ${wdBus.vintage || "per publisher"}</div>
             ${wdBus.provenance === "vendor_licensed_proxy" ? `<div class="hint"><b>⚠ Licensed
               vendor figure.</b> MISO publishes no load-side headroom at all, so this comes from
               our Orennia subscription rather than from a public source. It is the best number
               that exists for this direction, and it is not ours — the license lapses late 2027,
               after which this row goes back to reading "not published".</div>`
               : wdBus.probe_mw ? `<div class="hint">⚠ Headroom at a <b>${fmt(wdBus.probe_mw)} MW
               probe</b>, not this bus's maximum — we hold no other scenario yet, so a larger
               request could bind on a different facility.</div>` : ""}`
          : `<span class="cannot">Not published for this location.</span>`}</td>
        <td class="hint">${wdBus
          ? `This is the direction a data center needs. It is a published screening figure, not a
             service guarantee — only the utility's own study is binding.`
          : `<b>A gap in OUR coverage, not a property of the site.</b> ${ba === "PJM"
             ? `We hold PJM's current case for 1,826 buses, but only 227 of them carry a location
                we trust, so no bus could be matched within 25 miles of here. The figure exists;
                placing it is the open work.`
             : `MISO publishes no load-side headroom publicly, and our licensed substitute covers
                1,731 buses — none within 25 miles of this parcel.`} Ask the utility directly.`}</td></tr>

      <tr><td><b>Sending power<br>(injection)</b></td>
        <td>${injBus
          ? `<b>${injBus.name}</b> · ${fmt(injBus.kv)} kV · ${injBus.mi} mi<br>
             <b>${fmt(injBus.mw)} MW</b> injection headroom
             <div class="hint">study case: ${escHtml(injBus.vintage || "per publisher")}</div>`
          : `<span class="cannot">No bus within 25 miles.</span>`}</td>
        <td class="hint">Only relevant if you intend to co-locate generation or export.
          <b>It is not a substitute for the withdrawal figure</b> — re-measured on the current
          PJM case across <b>1,826 buses</b>, the two directions agree on <b>none</b> of the 407
          where either is non-zero, and every non-zero one is on the generation side.</td></tr>

      <tr><td><b>Generation capacity</b></td>
        <td>${q.active_mw != null
          ? `${fmt(q.active_mw)} MW active in the county interconnection queue across
             ${fmt(q.active_projects ?? 0)} project(s)${q.withdrawn_projects
             ? `<div class="hint">${fmt(q.withdrawn_projects)} projects have withdrawn</div>` : ""}`
          : `<span class="cannot">no queue activity recorded in this county</span>`}</td>
        <td class="hint">Queue volume counts as future <b>supply</b> nearby, not as competing
          demand. High withdrawal counts are normal and indicate queue churn, not failure.</td></tr>

      <tr><td><b>Planned transmission</b></td>
        <td>${(G.mtep || []).length
          ? `${fmt((G.mtep || []).length)} MISO expansion projects recorded statewide
             <div class="hint">not filtered to this site — MTEP names stations in its own
               vocabulary and we hold no key that joins it to our buses</div>`
          : `<span class="cannot">none recorded</span>`}</td>
        <td class="hint">Where capacity is <i>going</i> to appear. A site next to a planned upgrade
          may be viable on a later timeline even if it is constrained today.</td></tr>

      <tr><td><b>Tariffs and rates</b></td>
        <td>${tariffHeld}</td>
        <td class="hint">${tariffMeans}</td></tr>

      <tr><td><b>Local rules</b></td>
        ${/* G11: this cell printed the stale 4-value posture AND `local_bans ?? 0`, which is 0 on
             all 92 counties -- so for CASS it read "quiet ... 0 ban(s) recorded" beside a verified
             ban. It was the FIFTH surface still on the legacy vocabulary, found by grepping for
             the label rather than trusting that the earlier four were all of them. */
          (() => {
            const cp = countyPosture(fips);
            const detail = cp.nActions
              ? `<div class="hint">${cp.nActions} verified action(s) on record${cp.why ? ` &mdash; ${cp.why}` : ""}</div>`
              : `<div class="hint">no verified county action on record</div>`;
            if (cp.blocking) return `<td><span class="cannot"><b>${String(cp.headline).toUpperCase()}</b></span>${detail}</td>`;
            if (cp.legacyRestricted) return `<td><span class="cannot"><b>restriction recorded</b></span>${detail}</td>`;
            if (cp.approved) return `<td><b>has approved a data center</b>${detail}</td>`;
            return `<td>${cp.headline || '<span class="cannot">not assessed</span>'}${detail}</td>`;
          })()}
        <td class="hint">Indiana's decision-relevant data-center regulation is mostly county
          moratoria published on county websites, which no code library contains.
          <b>Absence here is not evidence of absence.</b></td></tr>
    </table>

    <!-- ============================ PAGE 3 ============================ -->
    <div class="pp-break"></div>
    <h3>Figure 4 · What stands between this parcel and power</h3>
    <table class="pp">
      <tr><th style="width:27%">Question</th><th style="width:20%">What we measured here</th>
          <th>What you do about it</th></tr>
      ${gateRows}
    </table>
    <div class="prov">Every row above is <b>derived from this parcel</b>, and a row we could not
      measure says so rather than showing a zero. ⚠ Ordered by what moves first: the things that
      can stop a project sit above the things that only cost time.</div>

    <h3>Figure 5 · Who else already holds a say over this land</h3>
    <table class="pp">
      <tr><th style="width:27%">Interest</th><th style="width:20%">Here</th><th>Why it matters</th></tr>
      ${row("Military installation", gt.milMi == null ? null
             : (gt.milMi === 0 ? `ON ${gt.mil}` : `${gt.milMi} mi — ${gt.mil}`),
             gt.measurable ? "none within reach (measured)" : "this parcel carries no coordinate, so this was not measured")}
      <tr><td colspan="2"></td><td class="hint">A large load or a tall structure near an active
        installation can draw a <b>DoD Siting Clearinghouse</b> review. It runs on the
        Department's clock, not the county's — it rarely refuses, it adds months. Ask early.</td></tr>
      ${row("Special-use airspace", gt.sua.length ? gt.sua.join("; ") : null,
             gt.measurable ? "none overhead (measured)" : "this parcel carries no coordinate, so this was not measured")}
      <tr><td colspan="2"></td><td class="hint">Governs what may be built <b>tall</b> — cooling
        towers, stacks, met masts and construction cranes. The data hall is rarely the problem;
        the plant on top of it can be.</td></tr>
      ${row("Tribal trust land", gt.tribal, gt.measurable ? "no (measured)" : "this parcel carries no coordinate, so this was not measured")}
      <tr><td colspan="2"></td><td class="hint">A <b>different sovereign</b>: the counterparty is
        the tribal government, not the county.</td></tr>
      ${row("Tall obstructions within 1 mile", gt.tall1mi ? `${gt.tall1mi} at or above 200 ft` : null,
             gt.measurable ? "none within a mile (measured)" : "this parcel carries no coordinate, so this was not measured")}
      <tr><td colspan="2"></td><td class="hint">Everything counted here already cleared an FAA
        review at 200 ft or more, so a cluster is cheap evidence that a tall structure of your own
        will clear one too.</td></tr>
    </table>
    <div class="prov">${prov("in_land_gates")} · ${prov("in_faa_obstacles_tall")} —
      measured against this parcel's own point. ⚠ The military distance is to the nearest boundary
      vertex, so it reads slightly long for a large installation; it is used to decide whether to
      raise the question, never to answer it.</div>

    <h3>Figure 6 · Evidence held for this site</h3>
    <table class="pp">
      <tr><th style="width:31%">Question</th><th>What we can show</th></tr>
      ${row("Land &amp; size", `${acr.acres.toFixed(2)} ac — ${acr.basis}`)}
      ${row("Fits a 25 MW datacenter", fitsDC ? "yes" : "no")}
      ${row("Fits a 5 MW battery", fitsBESS ? "yes" : "no")}
      ${acr.disputed ? `<tr><td>Acreage dispute</td><td class="cannot">recorded and measured
        acreage disagree — the SMALLER is used, never the larger</td></tr>` : ""}
      ${row("Flood zone", p.sfha_flood === undefined ? null : (p.sfha_flood ? "YES — mapped flood hazard" : "clear (measured)"))}
      ${row("Wetland on parcel", p.wetland_on_parcel === undefined ? null : (p.wetland_on_parcel ? "YES" : "clear (measured)"))}
      ${row("Protected land overlap", p.protected_land === undefined ? null : (p.protected_land ? "YES" : "clear (measured)"))}
      ${row("Federal tax-credit zone", p.bonus_kinds,
             p.bonus_kinds === undefined ? undefined : "none — this parcel is in no bonus zone")}
      ${siDetail}
    </table>
    <div class="prov">Sources used in this document:<br>${tables.map((t) => prov(t)).join("<br>")}</div>

    <!-- ============================ PAGE 4 ============================ -->
    <div class="pp-break"></div>
    <h3>Scoring detail</h3>
    <div class="hint" style="margin-bottom:6px">Composite <b>${Math.round(r.composite)}</b> over
      ${assessable} of 6 assessable parts (total weight ${r.weightUsed}).${missing.length
      ? ` Not assessable here: ${missing.map((k) => PART_NAME[k]).join(", ")} — excluded from the
        denominator rather than scored zero, so a data gap never masquerades as a bad site.` : ""}
      <b>The weights are yours</b> and change the ranking; these are defaults, not an answer.</div>
    <table class="pp">${partRows}</table>

    <h3>Appendix · Stakeholder meeting record</h3>
    <table class="pp">
      <tr><th style="width:22%">Meeting</th><td class="fillin">&nbsp;</td></tr>
      <tr><th>Date</th><td class="fillin">&nbsp;</td></tr>
      <tr><th>Utility attendees</th><td class="fillin">&nbsp;</td></tr>
      <tr><th>Our attendees</th><td class="fillin">&nbsp;</td></tr>
      <tr><th>Capacity discussed</th><td class="fillin">&nbsp;</td></tr>
      <tr><th>Action items</th><td class="fillin" style="height:54px">&nbsp;</td></tr>
    </table>
    <div class="prov" style="margin-top:10px"><b>What this document is not.</b> It is a screening
      pack built from public data. It does not price the land, name the owner, or guarantee power.
      Every capacity figure is a published screening number superseded by the utility's own study,
      and every figure above names the table and build date it came from.</div>
    </div>`,
    `${p.parcel_source}|${p.parcel_key}`);
  state.dossierFor = { p, fips };
  $("ev-dossier").classList.remove("hidden");
}

/* ============================================================================================
   G125 - WHERE AM I? Operator, 2026-08-20c: *"we need to ensure that EITHER coordinates OR
   addresses are visible somewhere in the popups/dossier, which is crucial for the user to
   identify exactly where we are, so they can self-verify the results."*

   ⛔ TWO THINGS THE ROW ASSUMED WERE WRONG, AND BOTH ARE HANDLED HERE.
     1. "Address is Marion-only and must say so." It is NOT. That rests on
        in_si_address_parcel_bridge (51,309 Marion rows), which is the address SEARCH crosswalk.
        energy.parcels_in carries the DLGF's own property address on 3,578,398 of 3,637,663
        Indiana parcels - 98.4%, all 92 counties. Measured on candidates: 527,038 of 531,325.
     2. "The payload already carries the coordinate on every row." It does not - `lat` is
        published on 2,284,133 of 3,553,194 in_sites rows, so 59.7% of parcels had none. Every
        one HAS a polygon, so a display point is derived from it and LABELLED as derived.

   ⚠ NEVER PRINT 0,0. `Number(null)` is 0 and 0 is finite, and that once put a military base in
   the Gulf of Guinea. A parcel with no point says so.
   ⭐ Full precision is kept in the copy field (G30b, all 13 places); 5 decimals are displayed,
   which is about a metre - the right resolution for finding a site in imagery.
   ⛔ These coordinates are for the reader and the imagery link. Nothing measures with them.
   ============================================================================================ */
function locationRows(p) {
  const lat = p.x_map_lat != null ? Number(p.x_map_lat)
            : (p.map_lat != null ? Number(p.map_lat)
            : (p.lat != null ? Number(p.lat) : null));
  const lon = p.x_map_lon != null ? Number(p.x_map_lon)
            : (p.map_lon != null ? Number(p.map_lon)
            : (p.lon != null ? Number(p.lon) : null));
  const basis = p.x_coord_basis || p.coord_basis
    || (p.lat != null ? "published" : null);
  const addr = p.x_addr || p.prop_address || null;
  const city = p.x_city || p.prop_city || null;
  const zip = p.x_zip || p.prop_zip || null;

  const hasPt = lat != null && lon != null && Number.isFinite(lat) && Number.isFinite(lon)
                && !(lat === 0 && lon === 0);
  const pair = hasPt ? `${lat.toFixed(5)}, ${lon.toFixed(5)}` : null;
  const full = hasPt ? `${lat}, ${lon}` : "";
  const full1 = String(full).replace(/'/g, "&#39;");

  const line = [addr, [city, zip].filter(Boolean).join(" ")].filter(Boolean).join(", ");
  return `
    ${row("address", line || null, "no address published for this parcel")}
    ${row("coordinates", hasPt
        ? `<span class="mono">${pair}</span>` +
          ` <button class="mini" onclick="navigator.clipboard&&navigator.clipboard.writeText('${full1}')"
             title="copy all 13 decimal places">copy</button>` +
          ` <a href="https://www.google.com/maps/search/?api=1&query=${lat},${lon}"
             target="_blank" rel="noopener">imagery</a>`
        : null, "no coordinate held for this parcel")}
    ${basis === "parcel_interior_point"
        ? `<tr><td>coordinate basis</td><td><span class="cannot">derived from the parcel
             outline</span> — the assessor publishes no point for this parcel</td></tr>`
        : (basis ? row("coordinate basis", "published by the assessor") : "")}
    ${row("parcel id", p.parcel_key)}`;
}

function openParcelEvidence(p, fips) {
  state.dossierFor = { p, fips };
  $("ev-dossier").classList.remove("hidden");
  const a = (x) => x == null ? null : Number(x).toFixed(2);
  const c = state.ctx.by_fips[fips] || {};
  const density = V("f-density");
  const acr = acreageOf(p);
  show(`Parcel ${p.parcel_key}`, `
    <h3>Where</h3><table>${locationRows(p)}</table>
    <h3>Land & size (P3)</h3><table>
      ${row("class", p.occ_group)}${row("parcel acres", a(p.parcel_acres))}
      ${row("outdoor acres (EXACT: parcel − measured building intersection)", a(p.exact_outdoor_acres))}
      ${row("outdoor acres (approximate)", a(p.outdoor_acres))}
      ${row("building acres (exact)", a(p.exact_bldg_acres))}
      ${row("footprints intersecting this parcel", p.footprints_intersecting)}
      ${row("how outdoor space was measured", p.outdoor_acres_method)}
      ${row("screened on", `${acr.acres.toFixed(2)} ac — ${acr.basis}`)}
      ${row(`fits @ ${density} MW/acre (your setting)`, Math.floor(acr.acres * density) + " MW")}
      ${row("the other use case would use", (() => {
          const alt = acreageOf(p, acr.mode === "dc" ? "bess" : "dc");
          return `${alt.acres.toFixed(2)} ac → ${Math.floor(alt.acres * density)} MW (${acr.mode === "dc" ? "BESS, outdoor only" : "hyperscale DC, whole parcel"})`;
        })())}
      ${row("structures", p.structure_count)}${row("structure sqft", p.structure_sqft)}</table>
    <div class="hint">Use case <b>${acr.mode === "dc" ? "hyperscale DC" : "BESS"}</b>: a DC builds over
      or removes an existing structure, so it is sized on the whole parcel; a BESS sites around what is
      there, so it is sized on outdoor space. Switch it in the screener.</div>
    ${acr.disputed ? `<div class="cannot">Sources disagree on this parcel's size: the exact-geometry
      figure falls well below the recorded parcel area (${Number(p.parcel_acres).toFixed(2)} ac)${p.footprints_intersecting === 0
        ? ", and no building footprint intersects it — with nothing to subtract, the two should match" : ""}.
      Screened on the recorded acreage; the exact figures are shown above unchanged so you can judge them.
      126 of 1,200,924 class-union parcels show this — see docs/HANDOFF.md.</div>` : ""}
    <div class="prov">${prov("in_sites")} · exact figures from mat_parcel_outdoor_exact (footprint∩parcel measured, shared buildings not double-counted) · density is your adjustable assumption, not an answer</div>
    <h3>Power &amp; grid — how hard is it to get power here?</h3><table>
      ${row("nearest substation", p._dsub_name
          ? `${p._dsub_name}${p._dsub_kv ? ` (${p._dsub_kv} kV)` : " (voltage not published)"} · ${p._dsub_mi === 0 ? "on this parcel" : `${p._dsub_mi} mi`}`
          : "none within the search radius (measured)")}
      ${row("nearest transmission line", p._dline_mi != null
          ? `${p._dline_kv ? `${p._dline_kv} kV` : "voltage not published"} · ${p._dline_on ? "<b>runs across this parcel</b>" : `${p._dline_mi} mi`}`
          : "none within the search radius (measured)")}
      ${row("nearest bus",
          p._dpoi_name
            ? `${p._dpoi_name}${p._dpoi_kv ? ` (${p._dpoi_kv} kV)` : ""} · ` +
              `${p._dpoi_mi === 0 ? "on this parcel" : `${p._dpoi_mi} mi`} · ` +
              `${fmt(p._dpoi_mw)} MW ${p._dpoi_dir === "sending power" ? "injection" : "load"} headroom` +
              (p._dpoi_exact ? "" : ` <span class="cannot">(approximate &mdash; measured from a point)</span>`)
            : null,
          "no bus within 25 miles (measured)")}</table>
    ${p._dline_mi != null ? `<div class="sowhat">${
      p._dline_on
        ? "A transmission line already crosses this parcel, so there is <b>no greenfield line to build</b> — but expect an easement and conductor-clearance constraint that shapes where you can put steel."
        : (p._dline_mi <= 1
            ? `A line is ${p._dline_mi} mi away — close enough that a spur is usually a cost item rather than a route-and-permit project.`
            : `The nearest line is ${p._dline_mi} mi away, so budget for a build and its own right-of-way.`)
      } ${
      p._dline_kv == null
        ? "⚠ This line's voltage is not published, so its capacity is unknown — it is <b>not</b> a low-voltage line, we simply cannot tell."
        : (p._dline_kv >= 345
            ? `At ${p._dline_kv} kV this is backbone transmission, the class that can carry a hyperscale campus.`
            : (p._dline_kv >= 100
                ? `At ${p._dline_kv} kV this is sub-transmission — workable, but confirm it can take your load.`
                : `At ${p._dline_kv} kV this is a distribution-class lateral and <b>will not serve a 300 MW load</b> without a major upgrade, whatever its distance says.`))
      }</div>` : ""}
    <div class="prov">${prov("in_substations")} · ${p._dist_exact
        ? "distances measured edge-to-edge against the real line and parcel geometry, so 0.0 mi means the asset physically crosses the parcel"
        : "⚠ approximate — measured from a representative point on the parcel, so a true 0.0 is reported as a small non-zero distance"} · distances are floors against mapped features, not service guarantees</div>
    ${(() => {
      /* QUEUE PRESSURE. Both RTOs are already held — in_queue carries 583 MISO and 361 PJM Indiana
         rows with MW and status, and county_context ships the rollup. The county map already SHADES
         by active queue MW; what was missing is the parcel-level read, which is where a developer
         actually asks the question.
         ⚠ TWO OPPOSED READINGS, and only stating both is honest: queued GENERATION nearby is future
         supply, which helps a large load — but it is simultaneously competition for the same
         interconnection study slots and the same network upgrades. And a high WITHDRAWAL rate is a
         third signal entirely: it says projects that tried here gave up. */
      const q = (state.ctx?.by_fips?.[fips] || {}).queue;
      if (!q || !q.projects) return "";
      const wd = q.withdrawn_projects || 0, tot = q.projects || 0;
      const attrition = tot ? Math.round(100 * wd / tot) : 0;
      return `
    <h3>Queue pressure — who is ahead of you here?</h3><table>
      ${row("active projects in this county", `${fmt(q.active_projects || 0)} of ${fmt(tot)} ever queued`)}
      ${row("active queued capacity", `${fmt(q.active_mw || 0)} MW`)}
      ${row("withdrawn", `${fmt(wd)} projects (${attrition}% of all attempts)`)}
    </table>
    <div class="sowhat">${
      (q.active_mw || 0) > 0
        ? `<b>${fmt(q.active_mw)} MW across ${fmt(q.active_projects)} live projects</b> is already in the interconnection queue in this county. That cuts both ways: queued generation is future <i>supply</i> near your load, but it is also competition for the same study slots and the same network upgrades, and those projects hold their place ahead of you.`
        : `No live queue activity in this county — you would not be competing for study slots locally, but there is also no nearby generation being built out.`
      }${attrition >= 50 && tot >= 4
        ? ` ⚠ <b>${attrition}% of everything ever queued here was withdrawn.</b> That is a signal about how hard interconnection has proved locally, not about your site.`
        : ""}</div>
    <div class="prov">${prov("in_queue")} · county grain, both RTOs · active/withdrawn are the publisher's own status</div>` ;
    })()}
    ${p.x_wat_mi != null ? `
    <h3>Water — can this site be cooled?</h3><table>
      ${row("nearest water source",
          p.x_wat_mi == null ? null
            : `${p.x_wat_name || "unnamed"} (${p.x_wat_kind || "surface water"}) · ${p.x_wat_on ? "<b>on this parcel</b>" : `${p.x_wat_mi} mi`}`,
          "no surface-water source within 10 miles (measured)")}
    </table>
    <div class="sowhat">${
      p.x_wat_on
        ? "A surface-water source sits on this parcel, so a cooling intake is a site-design question rather than a pipeline project — subject to a withdrawal permit."
        : (p.x_wat_mi <= 1
            ? `Water is ${p.x_wat_mi} mi away — close enough that an intake and pipe are a normal cost line.`
            : `The nearest source is ${p.x_wat_mi} mi away; past about a mile, piping water becomes its own project with its own easements.`)
      }${p.x_wat_greatlake ? " ⚠ The nearest source is <b>Lake Michigan</b>, which is governed by the Great Lakes Compact — a materially harder withdrawal regime than an inland river, whatever the short distance suggests." : ""}
      Power generation is already Indiana's largest water user — 3,822 of 7,177 Mgal/d withdrawn statewide — and <b>99.5% of that is drawn from surface water</b>, the same kind of source measured above. A new thermal load is competing for the resource this parcel would draw on, not an untouched one.</div>
    <div class="prov">${prov("in_water_distance_parcel")} · nearest NHD water <b>source</b> (reservoir, lake or named river) by exact geometry; swamp and marsh are excluded because a wetland is something to permit around, not draw from</div>` : ""}
    <h3>Seller intent (P1)</h3><table>
      ${row("carries SI signal", p.has_si_signal === true ? "yes" : (p.has_si_signal === false ? "no" : null))}
      ${row("signal types / events", p.si_signal_types != null ? `${p.si_signal_types} / ${p.si_signal_events}` : null)}
      ${row("signals", p.si_signals)}
      ${row("first event", p.si_first_event_date)}${row("last event", p.si_last_event_date)}
      ${row("events in last 3 / 5 / 10 yrs", p.si_events_3y != null
          ? `${p.si_events_3y} / ${p.si_events_5y} / ${p.si_events_10y}` : null)}
      ${row("how it reached this parcel", p.si_keying)}
      ${row("where the date came from", p.si_date_basis)}
      ${row("held but not counted here", (Number(p.si_excl_resid) || 0) + (Number(p.si_excl_lowsev) || 0) > 0
          ? [p.si_excl_resid ? `${p.si_excl_resid} residential-class` : null,
             p.si_excl_lowsev ? `${p.si_excl_lowsev} below the severity bar` : null]
            .filter(Boolean).join(" · ") : null)}</table>
    <div class="prov">${prov("in_si_sites_flags_v2")} · admitted at the NON-RESIDENTIAL level only
      — a ~300 MW datacenter and a ~5 MW BESS both need land a house does not have — and only where
      severity would plausibly move an owner to sell, so a weed citation and a residential teardown
      do not qualify. Undeveloped land still renders for BESS siting; footprint absence simply stopped
      counting as intent. Where a date basis reads "layer name", the publisher wrote the event date
      into the dataset title rather than a column, so it is month- or year-precision.</div>
    <h3>Environmental gates (P4)</h3><table>
      ${row("SFHA flood", p.sfha_flood === undefined ? null : (p.sfha_flood ? "YES — flag" : "clear (measured)"))}
      ${row("wetland on parcel", p.wetland_on_parcel === undefined ? null : (p.wetland_on_parcel ? "YES — flag" : "clear (measured)"))}
      ${row("protected land", p.protected_land === undefined ? null : (p.protected_land ? "YES — flag" : "clear (measured)"))}
      ${row("bonus credits", p.bonus_kinds === undefined ? null : (p.bonus_kinds || "none intersecting"))}</table>
    <div class="prov">${prov("in_site_gates")}</div>
    ${/* G72/G92: the gates reach the PARCEL POPUP too, not only the dossier and the screener.
         G51 applies cleanly here because in_land_gates is a COMPLETE Indiana clip - 33 polygons
         covering every square meter we care about - so "none" is a measured finding rather than
         an absence of measurement, and each row says which it is. */
      (() => {
        const g = gatesForPoint(Number(p.lat), Number(p.lon));
        return `<h3>Who else holds a say over this land</h3><table>
          ${row("nearest military installation", g.milMi == null ? null
                 : (g.milMi === 0 ? `ON ${g.mil}` : `${g.milMi} mi &mdash; ${g.mil}`),
                 g.measurable ? "none within reach (measured)" : "this parcel carries no coordinate, so this was not measured")}
          ${row("special-use airspace", g.sua.length ? g.sua.join("; ") : null,
                 g.measurable ? "none overhead (measured)" : "this parcel carries no coordinate, so this was not measured")}
          ${row("tribal trust land", g.tribal, g.measurable ? "no (measured)" : "this parcel carries no coordinate, so this was not measured")}
          ${row("tall obstructions within 1 mi", g.tall1mi || null,
                 g.measurable ? "none at or above 200 ft (measured)" : "this parcel carries no coordinate, so this was not measured")}
        </table>
        <div class="prov">${prov("in_land_gates")} &middot; ${prov("in_faa_obstacles_tall")} &middot;
          a DoD review runs on the Department's clock, not the county's; airspace governs what may
          be built TALL; tribal trust land is a different sovereign.</div>`;
      })()}
    <h3>County context (P3b/P4/P5/P6)</h3><table>
      ${row("wetlands (county)", c.wetlands ? `${fmt(c.wetlands.wetland_features)} features / ${fmt(c.wetlands.wetland_acres)} ac` : null)}
      ${row("fibre-served locations", c.fibre ? `${fmt(c.fibre.fiber_locations)} of ${fmt(c.fibre.locations)} (${c.fibre.fiber_providers} providers)` : null)}
      ${row("seismic design category", c.seismic?.sdc)}
      ${row("business broadband units (FCC)", c.fcc ? `${fmt(c.fcc.units)} (fiber ${fmt(c.fcc.fiber_units)} · gig ${fmt(c.fcc.gig_units)})` : null)}
      ${row("5G area coverage %", c.fcc?.pct_5g_area)}
      ${row("utilities serving county", c.eia861?.utilities)}
      ${row("county opposition intensity", c.posture?.opposition_intensity)}
      ${row("active queue MW (county)", c.queue?.active_mw)}</table>
    <div class="prov">source: county aggregates (see Inventory) · per-parcel water/fibre are the tile-pipeline milestone</div>`,
    `${p.parcel_source}|${p.parcel_key}`);
}
/* ---------- G111: ONE BUS, BOTH DIRECTIONS -----------------------------------------------------
   Operator, 2026-08-19: *"The buses should show both withdrawal and injection amounts, since a
   developer may be concerned with co-locating their site prospect with generation."*

   ⭐ The reason matters as much as the ask. A data center that brings its own generation asks TWO
   questions of one bus -- how much load can I pull OUT, and how much can I push IN -- and they are
   genuinely different numbers, not two views of one. A bus can be wide open one way and full the
   other. Answering them on separate surfaces made the co-location case impossible to evaluate.

   ⛔ WHAT THIS REPLACED, because it was worse than incomplete:
     * every bus was titled "MISO POI", including the 41 PJM ones;
     * a whole section headed "Injection headroom at a 300 MW request" read `headroom300_mw` and
       `binding_300`, and BOTH ARE ABSENT FROM ALL 3,542 FEATURES -- the section rendered empty on
       every bus in the state, the same defect shape as the dossier's hardcoded "Not started" rows;
     * it cited `in_bus_headroom_miso`, a table G63 superseded, as its provenance.

   ⚠ THE MISSING DIRECTION IS A THREE-STATE, NOT A ZERO (G51). PJM holds 1,814 injection buses and
   1,826 withdrawal -- a real 12-bus asymmetry, not rounding -- so a bus present one way and absent
   the other says so in words. */
function busTitle(p) {
  return `${p.iso || "?"} bus: ${p.bus_name || p.poi_name || p.bus_number}`;
}
function busSourceLine(d) {
  if (!d) return "";
  return d.provenance === "vendor_licensed_proxy"
    ? "licensed Orennia DPP-2025 proxy — MISO publishes no public load-side figure at all, " +
      "and this license lapses late 2027"
    : `our own PJM QueueScope harvest${d.probe_mw ? ` at a ${fmt(d.probe_mw)} MW probe` : ""}`;
}
function busDirectionBlock(d, label, whatItMeans) {
  if (!d) {
    return `<h3>${label}</h3>
      <div class="cannot">Not published for this bus in this study case. ⚠ This is a MEASURED
      ABSENCE, not zero capacity — PJM's case carries 1,814 injection buses and 1,826 withdrawal,
      so a bus really can appear in one direction and not the other.</div>`;
  }
  return `<h3>${label}</h3>
    <div class="sowhat">${whatItMeans}</div>
    <table>
    ${row("Available", d.headroom_mw != null ? `${fmt(Math.round(d.headroom_mw))} MW` : null,
          "no capacity published at this bus")}
    ${row("First constraint to bind", d.worst_binding_facility)}
    ${row("Monitored facilities", d.monitored_facilities)}
    ${row("Already over their rating", d.facilities_at_zero, "not counted for this bus")}
    ${row("Already overloaded before any request", d.existing_overload_flag === true ? "yes" : null,
          "no")}
    ${row("Study case", d.vintage)}
    ${row("Source", busSourceLine(d))}</table>`;
}
function busBothDirections(p) {
  const pair = (state.busPairs && state.busPairs.get(`${p.iso}|${p.bus_number}`)) || {};
  // fall back to the clicked feature, so the panel still works if the index is missing
  const wd = pair.Withdrawal || (p.direction === "Withdrawal" ? p : null);
  const inj = pair.Injection || (p.direction === "Injection" ? p : null);
  return `
    <h3>Bus identity</h3><table>
    ${row("Bus number", p.bus_number)}${row("Bus name", p.bus_name)}
    ${row("kV", p.kv)}${row("Area", p.area_name)}${row("Grid operator", p.iso)}</table>
    ${busDirectionBlock(wd, "Withdrawal — what a LOAD can pull out",
      "This is the data-center question. It is what the site itself can draw.")}
    ${busDirectionBlock(inj, "Injection — what a GENERATOR can push in",
      "This is the co-location question. If you intend to build your own generation on or beside " +
      "the site, this is the number that decides whether it can reach the grid here.")}
    <div class="prov">${prov("in_bus_capacity_tier0")} · one table, both ISOs, both directions.
      ⚠ The two directions are independent: a bus wide open for load can be closed for
      generation, and the reverse. Do not read one as a proxy for the other.</div>`;
}

function gridEv(p) {
  if (p.layer === "bus_poi") {
    show(busTitle(p), busBothDirections(p));
  } else if (p.layer === "substation") {
    const S = { "HIFLD+OSM": "both HIFLD and OpenStreetMap describe this substation, matched to each other at 0.5 m on average (2,354 of 3,858)",
                "OSM": "OpenStreetMap ONLY — HIFLD does not carry this substation. 933 of 3,858 are visible only because OSM was merged in.",
                "HIFLD": "HIFLD only — OpenStreetMap has no matching footprint (571 of 3,858)" };
    /* G51 sweep, 2026-08-20. A third state is added ONLY where a coverage argument exists, which
       is this row's own rule — inventing "none" where we never looked is the unpublished-rate-
       as-zero defect. Here the argument is that `in_substations` is the COMPLETE Indiana cut of
       its parent (3,858 = 3,858, checked), so a blank field is the publisher declining to state
       it, not us failing to look. `kV range` deliberately keeps no third state: an unknown
       voltage is genuinely unknown and 1,769 rows carry none. */
    const geomWhy = { point_and_footprint: "published point, and a footprint we can draw",
                      point_only: "a published point; no footprint published",
                      footprint_only_point_derived:
                        "footprint only — the marker is a centroid WE derived, not a survey point",
                      no_location: "no usable Indiana location" }[p.geom_kind];
    show(`Substation: ${p.substation_name || "(unnamed)"}`, `
      <table>${row("kV range", `${p.min_kv ?? "—"}–${p.max_kv ?? "—"}`)}
      ${row("county", p.county, "neither publisher records a county for this station")}
      ${row("status", p.status, "no status published")}
      ${row("type", p.substation_type, "untyped by both publishers")}
      ${row("lines", p.line_count, "line count not published")}
      ${row("operator", p.operator, "no operator named by either publisher")}
      ${row("sources merged", p.sources)}
      ${row("how it is positioned", geomWhy)}</table>
      <div class="prov">${prov("in_substations")}<br>${S[p.sources] || "source not recorded"}
      ${p.geom_kind === "footprint_only_point_derived"
        ? `<br>⚠ <b>This station had no coordinate until 2026-08-20.</b> OpenStreetMap maps
           substations as POLYGONS and only node records carry a latitude, so 933 of these were
           read as unlocated while their footprint sat in the same table. Distance measurements
           use the footprint, not this marker.` : ""}</div>`);
  } else {
    show("Transmission line", `
      <table>${row("source", p.src === "osm" ? "OpenStreetMap" : "HIFLD")}
      ${row("owner", p.owner, "no owner published for this circuit")}
      ${/* ⛔ NO third state on voltage, on purpose. 335 lines carried HIFLD's -999999 sentinel and
            1,114 OSM lines carry none at all — "unknown" here is genuinely unknown, and printing
            "none" would put a 765 kV backbone and an unlabelled lateral in the same bucket. */
        row("voltage", p.kv != null ? `${p.kv} kV` : p.voltage)}
      ${row("class", p.volt_class, "voltage unknown, so no class can be assigned")}
      ${row("status", p.status, "no status published")}
      ${row("from", p.sub_1, "endpoint not named by the publisher")}
      ${row("to", p.sub_2, "endpoint not named by the publisher")}
      ${row("name (OSM)", p.osm_name, "unnamed in OpenStreetMap")}
      ${row("length", p.km != null ? `${p.km} km` : null)}</table>
      <div class="prov">${prov("in_transmission_union")} — ONE merged layer, 27,866 km.
      ${p.src === "osm"
        ? `<b>This line exists only in OpenStreetMap.</b> ${p.merge_note}. 1,114 lines / 2,706 km
           are visible only because OSM was merged in — 11% more transmission than HIFLD alone,
           on the layer the screener measures distance against.`
        : "HIFLD linework. OSM lines running within 100 m of a HIFLD line are treated as the same circuit and suppressed, so nothing is drawn twice."}</div>`);
  }
}
/* ---------- G92: GAS HEADROOM IN THE PIPELINE POPUP -------------------------------------------
   Operator, 2026-08-19: *"the natural gas pipelines should show headroom, where the data is
   available"*. The qualifier is doing real work: we hold a feed for TWO of the twelve pipelines
   drawn, so the other ten must say so rather than render an empty table. A pipeline with no
   number beside it must never read as a pipeline with no capacity. */
state.gasCap = null; state.gasCapLoading = null;
async function ensureGasCapacity() {
  if (state.gasCap) return state.gasCap;
  if (state.gasCapLoading) return state.gasCapLoading;
  state.gasCapLoading = fetchGz("data/gas_capacity.json.gz")
    .then((d) => { state.gasCap = d; return d; })
    .catch(() => { state.gasCap = { by_pipeline: {}, _failed: true }; return state.gasCap; });
  return state.gasCapLoading;
}
/* ⚠ MUST MATCH `pipe_key()` in scripts/export_gas_capacity.py. The map says 'Panhandle Eastern
   Pipe Line Co.' and the feed says 'Panhandle Eastern Pipe Line Company, LP'. Corporate suffixes
   only -- nothing that could merge two genuinely different pipelines (Texas Gas Transmission and
   Texas Eastern Transmission must stay apart). */
function gasPipeKey(name) {
  return String(name || "").toLowerCase()
    .replace(/[.,]/g, " ")
    .replace(/\b(company|companies|co|corporation|corp|llc|lp|l p|inc|the)\b/g, " ")
    .replace(/\bpipe line\b/g, "pipeline")
    .replace(/\s+/g, " ").trim();
}
function gasPipelineHtml(p) {
  const head = `<table>${row("Operator", p.operator)}${row("Type", p.typepipe)}</table>`;
  if (!state.gasCap) {
    return head + `<div class="hint">loading daily capacity…</div>`;
  }
  const e = state.gasCap.by_pipeline[gasPipeKey(p.operator)];
  if (!e) {
    /* ⛔ TWO DIFFERENT ABSENCES, and telling them apart is the useful part. We hold NINE capacity
       boards; only Panhandle Eastern and Trunkline publish a STATE column, so only those two can
       have their Indiana rows isolated. The other seven post the operator's whole system with no
       geography at all — ANR's locations are in Ohio, Texas Gas's in Louisiana. Saying "no feed"
       about those would be wrong, and wiring them would attach Louisiana gas to Indiana. */
    const boards = (state.gasCap.boards_without_geography) || {};
    const key = gasPipeKey(p.operator);
    const heldName = Object.keys(boards).find((k) => key.includes(k) || k.includes(key));
    if (heldName) {
      return head + `
        <div class="cannot">⚠ <b>We hold this pipeline's capacity board, and cannot place its rows
        in Indiana.</b> ${escHtml(boards[heldName])} posts operationally-available capacity for its
        <b>whole system</b> with no state or county field, so there is no way to tell which of its
        locations are the Indiana ones without guessing — and guessing would attach another
        state's gas to this line.
        <br><b>This is a geography gap, not an absence of data, and certainly not zero capacity.</b>
        Closing it needs a location-to-state reference for this operator's own point names.</div>
        <div class="prov">${prov("in_gas_pipelines")} · interstate border design capacity for every
        pipeline is on the <a href="market.html">Market</a> page.</div>`;
    }
    return head + `
      <div class="cannot">⚠ <b>No daily-capacity board is captured for this pipeline.</b> We hold
      boards for nine operators; only <b>Panhandle Eastern</b> and <b>Trunkline</b> identify their
      Indiana locations, and this pipeline is not among the nine. An absence of measurement,
      <b>not</b> a measurement of zero.</div>
      <div class="prov">${prov("in_gas_pipelines")} · interstate border design capacity for every
      pipeline is on the <a href="market.html">Market</a> page.</div>`;
  }
  const top = (e.locations || []).slice(0, 8).map((l) => `<tr>
      <td>${escHtml(l.name || "")}<br><span class="hint">${escHtml(l.county || "")} ·
        ${escHtml(l.purpose || "")}</span></td>
      <td><b>${fmt(l.free_dth)}</b> Dth/d free<br>
        <span class="hint">of ${fmt(l.design_dth)} design · ~${fmt(Math.round((l.free_dth || 0) / 156))} MW</span></td>
    </tr>`).join("");
  return head + `
    <h3>Gas free on this pipeline today, in Indiana</h3><table>
      ${row("Locations posting", e.n_locations)}
      ${row("Total free", `${fmt(e.total_free_dth)} Dth/day`)}
      ${row("Largest single point", `${fmt(e.max_free_dth)} Dth/day`)}
      ${row("Supports roughly", `${fmt(e.total_free_mw_est)} MW`)}
    </table>
    <div class="est-badge">MW is OUR ESTIMATE — the boards post no units column. Magnitudes match
      dekatherms/day and 1 Dth = 1 MMBtu, so at a 6.5 MMBtu/MWh combined-cycle heat rate,
      MW = Dth/day ÷ 156.</div>
    <div class="sowhat">This is <b>what is free today</b>, not design capacity — the number a
      developer actually needs when on-site generation or a dual-fuel backup is the plan. A single
      point with 450,000 Dth/day free can support a hyperscale campus on its own; a point posting a
      few thousand is a boiler connection. ⚠ Availability is a <b>daily</b> posting and moves.</div>
    <h3>Where the room is</h3><table>${top}</table>
    <div class="prov">${prov(e.source_table)} · gas day “current”, pulled
      ${escHtml(String(e.pulled_at || "").slice(0, 10))}.
      ⛔ These locations carry a NAME and a county, never a coordinate, so they are listed against
      the pipeline rather than plotted — inventing a point for them would be a centroid.</div>`;
}

function miscEv(p) {
  if (p.layer === "bus_candidate") {
    show(`PJM bus ${p.bus_number} — ESTIMATED location`, `
      <div class="est-badge">ESTIMATE — ${p.location_method}, confidence ${p.match_confidence}</div>
      <h3>Load headroom (withdrawal — the DC direction)</h3><table>
      ${row("available before first NEW constraint", p.withdrawal_mw != null ? `${fmt(Math.round(p.withdrawal_mw))} MW` : null)}
      ${row("binding facility", p.wd_binding)}
      ${row("pre-existing overloads (disclosed, not counted)", p.wd_existing_overloads)}
      ${row("study case", p.wd_case)}</table>
      <div class="prov">${prov("in_pjm_bus_withdrawal")} · facilities with |dfax|≥5%; a 300MW-class load needs upgrades everywhere in this case — see Future capacity for which and what cost</div>
      <h3>Bus identity</h3><table>${row("bus label", p.bus_label)}${row("kV", p.bus_kv)}
      ${row("matched substation", p.matched_substation_name)}${row("kV consistent", p.kv_consistent)}
      ${row("competing matches", p.collision_count)}</table>
      <div class="prov">${prov("in_pjm_bus_locations_candidate")}</div>`);
  } else if (p.layer === "queue_point") {
    const rows_ = Object.entries(p).filter(([k]) => k !== "layer").slice(0, 10).map(([k, v]) => row(k, v)).join("");
    show("PJM queue point", `<table>${rows_}</table><div class="prov">${prov("in_pjm_gis_queues")} · PJM's own coordinates</div>`);
  } else if (p.layer === "gas") {
    /* G92: this popup showed operator and type -- two fields -- and its own provenance line
       admitted "daily availability is an open lane". It is not an open lane any more: Energy
       Transfer's iPost boards give free capacity per named location and we hold 29 in Indiana.
       Loaded on first gas click (2 KB), then re-rendered. */
    show("Gas pipeline", gasPipelineHtml(p));
    if (!state.gasCap) ensureGasCapacity().then(() => show("Gas pipeline", gasPipelineHtml(p)));
  } else if (p.layer === "compressor" || p.layer === "storage") {
    const rows_ = Object.entries(p).filter(([k]) => k !== "layer").slice(0, 9).map(([k, v]) => row(k, v)).join("");
    show(`Gas ${p.layer}`, `<table>${rows_}</table>
      <div class="prov">${prov(p.layer === "compressor" ? "in_gas_compressor_stations" : "in_gas_storage")}</div>`);
  } else if (p.layer === "territory") {
    show(`Territory: ${p.utility}`, `
      <table>${row("type", p.utility_type)}${row("holding co", p.holding_company)}${row("regulated", p.regulated)}
      ${row("control area", p.control_area)}${row("customers", p.customers)}${row("summer peak MW", p.summer_peak_mw)}</table>
      <div class="prov">${prov("in_territories")} · "utility" = wires owner; clipped at the state line</div>`);
  } else if (p.layer === "padus") {
    show(`Protected: ${p.name || "(unnamed)"}`, `
      <table>${row("designation", p.designation)}${row("owner type", p.owner_type)}${row("manager", p.manager)}${row("acres", p.acres)}</table>
      <div class="prov">${prov("in_padus")}</div>`);
  } else if (p.layer === "nonattainment") {
    show(`Nonattainment: ${p.area_name || ""}`, `
      <table>${row("pollutant", p.pollutant_name)}${row("classification", p.classification)}
      ${row("current status", p.current_status)}${row("designation effective", p.designation_effective_date)}
      ${row("classification effective", p.classification_effective_date)}</table>
      ${naaSoWhat(p)}
      <div class="prov">${prov("in_nonattainment")} · air-permitting gate for on-site generation</div>`);
  /* G72. Each gate says WHO you would be negotiating with and WHAT it costs you in time --
     not what the polygon is. A reader who cannot act on it does not need it on the map. */
  } else if (p.layer === "military") {
    show(`Military installation: ${p.name}`, `
      <table>${row("component", p.detail)}${row("note", p.note)}</table>
      <div class="sowhat"><b>What this changes:</b> a large load or a tall structure near an
        active installation can draw a <b>DoD Siting Clearinghouse</b> review — an energy-project
        review that runs on the Department's clock, not the county's. It rarely says no outright;
        it adds months, and it is the one gate here that can move a schedule without ever
        producing a refusal. Find out early, not at permitting.</div>
      <div class="prov">${prov("in_land_gates")} · 13 installations, all verified inside Indiana</div>`);
  } else if (p.layer === "tribal") {
    show(`Tribal trust land: ${p.name}`, `
      <table>${row("extent", p.detail)}${row("status", p.note)}</table>
      <div class="sowhat"><b>What this changes:</b> this is a <b>different sovereign</b>. County
        zoning and the state permitting path do not apply the way they do one field over —
        the counterparty is the tribal government. Indiana holds exactly one such holding.</div>
      <div class="prov">${prov("in_land_gates")} · re-clipped 2026-08-19: the previous table held
        14 rows and none of them were in Indiana</div>`);
  } else if (p.layer === "sua") {
    show(`Special-use airspace: ${p.name}`, `
      <table>${row("airspace", p.detail)}${row("controlling agency", p.note)}</table>
      <div class="sowhat"><b>What this changes:</b> this governs what may be built <b>tall</b> and
        what radar must keep seeing — cooling towers, stacks, met masts and construction cranes,
        not the slab. A data hall almost never conflicts; the plant on top of it can.</div>
      <div class="prov">${prov("in_land_gates")} · 19 MOAs and restricted areas</div>`);
  } else if (p.layer === "obstacle") {
    show(`${p.obstacle_type || "Obstruction"} — ${fmt(p.agl_ft)} ft AGL`, `
      <table>${row("height above ground", p.agl_ft != null ? `${fmt(p.agl_ft)} ft` : null)}
      ${row("height above sea level", p.amsl_ft != null ? `${fmt(p.amsl_ft)} ft` : null)}
      ${row("nearest place", p.city, "not stated by the FAA")}
      ${row("lighting", p.lighting)}${row("FAA verification", p.verified)}</table>
      <div class="sowhat"><b>What this changes:</b> everything drawn here is at or above the
        <b>200 ft FAA notice threshold</b>, so it has already been through an airspace review at
        this location. A cluster of them is a cheap prior that a tall structure of your own will
        clear. ⚠ It is <b>not</b> a transmission trace — only 44 of these are line towers, because
        almost every tower is shorter than 200 ft. Use the transmission layer for that.</div>
      <div class="prov">${prov("in_faa_obstacles_tall")} · 4,591 of 15,638 Indiana obstructions</div>`);
  } else {
    show(`Bonus geography: ${p.kind}`, `
      <table>${row("kind", p.kind)}${row("key", p.key)}${row("attributes", p.attrs_json)}</table>
      <div class="prov">${prov("in_bonus_geo")} · the BENEFIT half of P4 (energy community / LIC / OZ / habitat / coal-closure)</div>`);
  }
}
function candEv(p) {
  show(`CANDIDATE ${p.candidate_signal}: ${p.parcel_key}`, `
    <div class="est-badge">CANDIDATE — staged for this app; ${p.match_method}</div>
    <table>${row("class", p.occ_group)}${row("activity (publisher's words)", p.activity)}
    ${row("observed date", p.observed_date)}${row("owner (permit)", p.owner)}${row("source", p.candidate_source)}</table>
    <div class="prov">${prov("in_si_candidates")} · 99.5% of permit parcels placed (exact + parent-family, methods labeled)</div>`);
}
/* ---------- G88: what this county has ACTUALLY built and permitted, and who serves it ----------
   Operator, 2026-08-19: *"For county posture, instead of having queued MW, we should put the
   number of DC developments that are either completed/in progress (maybe one field for each), and
   the utility should be able to be determined."*

   ⛔ TWO NUMBERS, NEVER ONE, AND NEVER ADDED. `listed` is what a commercial directory says exists
   today; `approved` is a county body's own verified decision. Different sources, different
   meanings, and a single project can be in both.
   ⚠ The city-precision caveat travels WITH the count, because a county whose pins are gazetteer
   centroids has a different evidence base from one with surveyed coordinates and the number alone
   cannot show that. */
function dcPostureBlock(c) {
  const d = c.dc_posture;
  if (!d) return "";
  const cityNote = d.listed > 0 && d.listed_city_precision > 0
    ? ` <span class="hint">⚠ ${fmt(d.listed_city_precision)} of these are city-centroid
        positions, not facility locations</span>`
    : "";
  /* ⚠ The territory polygons OVERLAP -- 145 of them cover 2.03x the state -- so "the utility" is
     a tiebreak, not a fact. Where more than one utility blankets the county, say so. */
  const util = d.primary_utility
    ? `${escHtml(d.primary_utility)}${d.n_utilities_covering_half > 1
        ? ` <span class="hint">⚠ ${d.n_utilities_covering_half} utilities' service areas each
            cover most of this county; this is the largest by customers, not an exclusive
            franchise</span>` : ""}`
    : null;
  return `
    <h3>Data centers in this county</h3><table>
      ${row("Operating (directory-listed)", d.listed ? `${fmt(d.listed)}${cityNote}` : null,
            "none listed by any of our four directories")}
      ${row("Approved by a local body", d.approved || null, "none recorded")}
      ${row("Proposed / pending", d.proposed || null, "none recorded")}
      ${row("Denied", d.denied || null, "none recorded")}
      ${row("Withdrawn by the applicant", d.withdrawn || null, "none recorded")}
      ${row("Operators present", d.operators && d.operators.length
            ? escHtml(d.operators.slice(0, 6).join(", ")) : null, "not named by the source")}
      ${row("Serving utility", util, "no territory resolved for this county")}
      ${row("Utilities whose area touches this county", d.n_utilities)}
    </table>
    <div class="sowhat">${d.listed || d.approved
      ? "<b>This county has said yes before.</b> An operating or approved data center is the " +
        "strongest evidence that a board will permit one — and simultaneously competition for " +
        "the same substation capacity."
      : (d.denied
        ? "<b>This county has refused one.</b> That is a posture signal a queue figure cannot give you."
        : "No data center is recorded here either way. That is <b>not</b> evidence of a welcome — " +
          "it means no precedent exists in either direction.")}</div>
    <div class="prov">${prov("in_dc_county_posture")} · operating counts are a spatial join of
      directory listings; approvals are verified at the authority's own record.
      ⛔ Do not add the two — different sources, and one project can appear in both.</div>`;
}
/* ---------- G89: when does the restriction LAPSE? --------------------------------------------
   ⛔ A DERIVED DATE MUST NEVER STYLE AS A PUBLISHED ONE, and an open-ended moratorium is a stated
   CONDITION rather than a missing value. Both are badged from `expiry_basis`. */
const EXPIRY_BADGE = {
  published: ["published", "The instrument itself states this end date."],
  derived: ["DERIVED", "Computed from the effective date plus the duration written into the " +
                       "instrument. Indicative only — a body that adopted a moratorium can extend it."],
  open_ended: ["open-ended", "No calendar end: the instrument ties the lapse to a condition."],
  duration_without_anchor: ["no start date", "A duration is stated but we hold no verified " +
                            "effective date to count from, so no end can be computed."],
  not_stated: ["not stated", "Neither an end date nor a duration appears in the verified record."],
};
function actionExpiryBlock(c) {
  const xs = c.action_expiry;
  if (!xs || !xs.length) return "";
  const items = xs.map((x) => {
    const [badge, why] = EXPIRY_BADGE[x.expiry_basis] || ["", ""];
    const when = x.expiry_date
      ? `<b>${escHtml(x.expiry_date)}</b>${x.days_remaining != null
          ? ` — ${fmt(x.days_remaining)} days away` : ""}${x.is_expired ? " — <b>ALREADY LAPSED</b>" : ""}`
      : "no end date";
    return `<tr><td>${escHtml(x.jurisdiction || "")}<br>
        <span class="hint">${escHtml(x.action_type || "")}${x.effective_from
          ? ` · effective ${escHtml(x.effective_from)}` : ""}</span></td>
      <td>${when} <span class="est-badge">${escHtml(badge)}</span><br>
        <span class="hint">${escHtml(why)}</span>
        ${x.condition ? `<br><span class="hint">Condition, verbatim: “${escHtml(x.condition)}”</span>` : ""}
      </td></tr>`;
  }).join("");
  return `
    <h3>When does the restriction lapse?</h3>
    <table>${items}</table>
    <div class="sowhat">A moratorium with a date is a <b>schedule</b> problem; an open-ended one is
      a <b>siting</b> problem. Which of the two you are looking at changes whether this county
      belongs on a shortlist at all.</div>
    <div class="prov">${prov("in_dc_action_expiry")} · ⚠ only 3 of 12 restrictions we hold carry
      any end date at all. We do not assume a default duration — inventing a lapse date a
      developer might plan around is worse than admitting there is none.</div>`;
}

/* ---------- G72/G80: severe-weather history, one of the 83 objects that reached no surface -----
   `in_spc_severe_events` held 24,716 located events, 1950-2024, and nothing rendered one.

   ⭐ It earns a place because it is a STRUCTURAL DESIGN AND INSURANCE input, and because it is the
   rare county fact that does not move: a board can lift a moratorium, it cannot move the storm
   track.
   ⛔ COUNTY GRAIN ON PURPOSE. A tornado is a TRACK and the source carries only its start point, so
   a per-parcel figure would be invented precision.
   ⚠ Both an all-time and a since-2000 count are shown, because reporting practice changed
   enormously over 74 years — hail and wind counts partly measure OBSERVATION, not weather, and a
   single all-time number would quietly present one as the other. */
function severeWeatherBlock(c) {
  const w = c.severe_weather;
  if (!w) return "";
  const ef = w.tornado_max_ef;
  return `
    <h3>Severe weather on record${w.first_year ? `, ${w.first_year}–${w.last_year}` : ""}</h3>
    <table>
      ${row("Tornadoes", w.tornado ? `${fmt(w.tornado)} <span class="hint">(${fmt(w.tornado_since_2000)} since 2000)</span>` : null, "none recorded")}
      ${row("Strongest on record", ef != null ? `<b>EF${ef}</b>` : null,
            w.tornado ? "none of them rated" : "no tornado recorded")}
      ${row("EF3 or stronger", w.tornado_ef3_plus || null, "none")}
      ${row("Large hail", w.hail ? `${fmt(w.hail)} <span class="hint">(${fmt(w.hail_since_2000)} since 2000)</span>` : null, "none recorded")}
      ${row("Damaging wind", w.wind ? `${fmt(w.wind)} <span class="hint">(${fmt(w.wind_since_2000)} since 2000)</span>` : null, "none recorded")}
    </table>
    <div class="sowhat">${w.tornado_ef3_plus
      ? `<b>${w.tornado_ef3_plus} tornado${w.tornado_ef3_plus === 1 ? " has" : "es have"} reached
         EF3 or stronger here.</b> That is a hardening and insurance question at design time, not a
         reason to avoid the county — but it belongs in the capital estimate rather than being
         discovered by the underwriter.`
      : `No EF3-or-stronger tornado is on record in this county. Weaker events still occur;
         the absence of a severe one is a lower design load, not immunity.`}</div>
    <div class="prov">${prov("in_severe_weather_county")} · NOAA Storm Prediction Center, placed on
      the event's START point. ⚠ Counts partly track REPORTING: spotter networks and population
      grew over the window, so compare the since-2000 figures between counties rather than the
      all-time ones. An unrated tornado is counted but carries no EF.</div>`;
}

/* ---------- G72/G80: eight county-grain objects that reached no surface ------------------------
   ⚠ THE VINTAGES DIFFER BY UP TO NINE YEARS and each figure carries its own, rather than one
     footnote covering all of them. USGS publishes water use every five years (2015 is current;
     2020 is the next release), ACS is 2023, BLS 2024.
   ⛔ A HELD-BUT-EMPTY COLUMN RENDERS AS ITSELF (G51). BLS suppresses the construction breakout on
     all 92 counties, so the row says the publisher does not break it out. Printing 0 would invite
     a reader to conclude the county has no builders. */
function countyExtrasBlock(c) {
  const x = c.extras;
  if (!x) return "";
  const mgd = (v) => v == null ? null : `${v.toFixed(2)} <span class="hint">Mgal/day</span>`;
  // ⭐ THE WATER SENTENCE IS THE ONE THAT CHANGES A DECISION, so it is computed, not asserted.
  const ps = x.public_supply_mgd;
  const waterSoWhat = ps == null
    ? `No county water-use figure is held, so the size of the ask cannot be put in context here.`
    : ps === 0
      ? `<b>This county has no public-supply withdrawal at all in the USGS survey.</b> That is a
         stated zero, not a gap: there is no municipal system of any size to negotiate with, so a
         cooling-water supply here means a well field or a pipeline, priced and permitted from
         scratch.`
      : `<b>A 100 MW evaporative-cooled campus wants roughly 1–2 Mgal/day of make-up water.</b>
         This county's ENTIRE public supply withdraws ${ps.toFixed(2)} Mgal/day, so such a campus
         would be asking for about <b>${Math.round(100 * 1.5 / ps)}%</b> of everything the public
         system currently takes. ${x.public_supply_surface_mgd > x.public_supply_groundwater_mgd
           ? `It is a SURFACE-water county, so the conversation is an intake permit and a
              low-flow limit.`
           : `It is a GROUNDWATER county, so the conversation is aquifer drawdown and a
              significant-water-withdrawal registration, not a river intake.`}
         Air-cooling avoids nearly all of it and costs efficiency instead — that trade is the
         decision this number informs.`;
  const risk = x.nri_risk_rating;
  return `
    <h3>Water supply <span class="hint">(USGS, ${x.water_use_year || "?"})</span></h3><table>
      ${row("public supply, all withdrawals", mgd(ps), "not surveyed")}
      ${row("… from groundwater", mgd(x.public_supply_groundwater_mgd), "none")}
      ${row("… from surface water", mgd(x.public_supply_surface_mgd), "none")}
      ${row("industrial self-supplied", mgd(x.industrial_selfsupplied_mgd), "none reported")}
      ${row("thermoelectric (existing power)", mgd(x.thermoelectric_mgd), "none — no thermal plant draws here")}
      ${row("every use in the county", mgd(x.all_uses_mgd), "not surveyed")}</table>
    <div class="sowhat">${waterSoWhat}</div>
    <div class="prov">${prov("in_county_context_extras")} · USGS county water use.
      ⚠ 2015 is the most recent survey published; USGS releases every five years.</div>

    <h3>Workforce &amp; economy</h3><table>
      ${row("people employed", x.employment)}
      ${row("establishments", x.estabs)}
      ${row("average weekly wage", x.avg_weekly_wage ? `$${fmt(x.avg_weekly_wage)}` : null)}
      ${row("civilian labour force", x.civilian_labor_force)}
      ${row("median household income", x.median_hh_income ? `$${fmt(x.median_hh_income)}` : null)}
      ${row("construction employment", null,
            x.construction_breakout_held === false
              ? "BLS does not publish the construction split at county grain" : "not measured here")}
      ${row("CS &amp; engineering degrees awarded", x.campus_cs_eng_awards,
            x.campus_institutions ? "campus present, none awarded" : "no institution in this county")}</table>
    <div class="sowhat">A 300 MW build needs on the order of a thousand trades at peak, then a
      few dozen permanent staff. <b>The wage sets the build cost and the labour force sets whether
      the trades are local or imported</b> — imported crews carry per-diem, travel and a schedule
      that moves with someone else's project. ⛔ The construction-specific figure is
      <b>held-but-empty on all 92 counties</b> and is shown as such rather than as a zero.</div>

    <h3>Hazard &amp; resilience <span class="hint">(FEMA National Risk Index)</span></h3><table>
      ${row("composite risk", risk)}
      ${row("expected annual loss", x.nri_expected_annual_loss_musd != null
            ? `$${x.nri_expected_annual_loss_musd}M <span class="hint">across the whole county</span>` : null)}
      ${row("community resilience", x.nri_resilience_rating)}
      ${row("buildings on record", x.bldg_count)}
      ${row("solar resource", x.ghi_kwh_m2_day
            ? `${x.ghi_kwh_m2_day} <span class="hint">kWh/m²/day</span>` : null)}</table>
    <div class="sowhat">FEMA's index is an <b>insurance and hardening</b> input, and it pairs with
      the storm history above: that panel counts what has happened, this one prices what is
      expected annually. <b>Community resilience is the half people skip</b> — it measures how
      fast the county recovers, which is what decides whether a two-day outage is two days.
      Indiana's solar resource barely varies (4.0–4.3 kWh/m²/day statewide), so on-site solar is
      a land-cost question here, never a location question.</div>

    <h3>Is the industry already here?</h3><table>
      ${row("data-center establishments", x.dc_industry_establishments, "none in this county")}
      ${row("people employed in them", x.dc_industry_employment, "none in this county")}
      ${row("utilities employment", x.utilities_employment, "none reported")}
      ${row("telecoms employment", x.telecom_employment, "none reported")}</table>
    <div class="sowhat">${x.dc_industry_employment
      ? `<b>The data-center industry already employs ${fmt(x.dc_industry_employment)} people in
         ${x.dc_industry_establishments} establishments here.</b> That usually means the
         substation capacity, the fibre and — most valuable of all — the permit precedent already
         exist, and somebody at the county has done this before.`
      : `<b>No data-center industry employment is recorded in this county.</b> Only 15 of
         Indiana's 92 counties have any, so this is the normal case rather than a warning — but
         it does mean you would be the first, and first movers write the ordinance rather than
         inheriting one.`}</div>`;
}

async function openCountyEvidence(p) {
  const c = state.ctx.by_fips[p.fips] || {};
  let html = `
    <h3>County rollup — 100% of parcels counted</h3><table>
      ${row("parcels", p.parcels)}${row("with a building", p.with_building)}${row("strict C&I", p.ci)}
      ${row("fits ≥25 MW @ 4/acre", p.ge25mw)}${row("carries SI signal", p.si_sites)}
      ${row("MW potential (sum)", p.mw_potential_at_4)}</table>
    <div class="prov">${prov("in_county_rollup")}</div>
    <!-- G51 sweep, 2026-08-20. The coverage argument here is that the queue and the EIA-861
         territory table are COMPLETE 92-county sets: every Indiana county has a row, so an empty
         cell means "we looked at this county and there are none", which is a finding. That is
         exactly the case the third state exists for, and exactly what these rows used to hide
         behind a bare dash. -->
    <h3>Grid & queue</h3><table>
      ${row("queue projects", c.queue?.projects, "no interconnection request on record here")}
      ${row("active MW", c.queue?.active_mw, "nothing active in the queue")}
      ${row("withdrawn (a signal, kept)", c.queue?.withdrawn_projects,
            "nothing has been withdrawn here")}
      ${row("utilities serving", c.eia861?.utilities, "no utility reports service territory here")}</table>
    <h3>Gates</h3><table>
      ${row("wetlands", c.wetlands ? `${fmt(c.wetlands.wetland_features)} / ${fmt(c.wetlands.wetland_acres)} ac` : null)}
      ${row("flood features (SFHA)", c.flood ? `${fmt(c.flood.flood_features)} (${fmt(c.flood.sfha_features)})` : null)}
      ${row("fibre-served / total locations", c.fibre ? `${fmt(c.fibre.fiber_locations)} / ${fmt(c.fibre.locations)}` : null)}
      ${row("business units: fiber ≥100/20 · gig (FCC)", c.fcc ? `${fmt(c.fcc.fiber_units)} · ${fmt(c.fcc.gig_units)} of ${fmt(c.fcc.units)}` : null)}
      ${row("mobile coverage 5G · 4G (area %)", c.fcc_mobile ? `${Math.round((c.fcc_mobile.pct_5g || 0) * 100)}% · ${Math.round((c.fcc_mobile.pct_4g || 0) * 100)}%` : null)}
      ${/* ⚠ NO third state. The seismic table covers 88 of 92 counties, not all of them, so a
            blank cell here may mean "not surveyed" rather than "no category" — and there is no
            way for the reader to tell which. The default "not measured here" is the safe
            direction and is what a caller saying nothing already gets. */
        row("seismic design category", c.seismic?.sdc)}</table>
    <div class="prov">${prov("in_seismic")} · ASCE 7 site class and design category, 88 of 92
      counties. ${prov("in_county_fibre")} · ${prov("in_county_flood")} ·
      ${prov("in_county_wetlands")}</div>
    <h3>Community posture</h3><table>
      ${row("posture", c.posture?.posture)}${row("opposition intensity", c.posture?.opposition_intensity)}
      ${row("local restriction", c.posture?.has_local_restriction)}${row("moratoriums", c.posture?.local_moratoriums)}</table>
    ${dcPostureBlock(c)}
    ${actionExpiryBlock(c)}
    ${severeWeatherBlock(c)}
    ${countyExtrasBlock(c)}`;
  if (!state.receipts) { try { state.receipts = await fetchGz("data/receipts.json.gz"); } catch { state.receipts = []; } }
  const name = (p.county_name || "").toUpperCase().replace(/ COUNTY$/, "");
  const rows_ = state.receipts.filter((r) => (r.county || "").toUpperCase().replace(/ COUNTY$/, "") === name).slice(0, 40);
  html += `<h3>Receipts (${rows_.length} county-tagged)</h3>` +
    (rows_.length ? `<table>` + rows_.map((r) =>
      `<tr><td>${r.kind}<br><span class="hint">${r.observed_date ?? "no date"}</span></td>
       <td>${r.url ? `<a href="${r.url}" target="_blank" rel="noopener">${r.title}</a>` : r.title}<br><span class="hint">${r.detail ?? ""}</span></td></tr>`).join("") + `</table>`
      : `<div class="hint">No county-tagged receipts held — cannot assess, not "quiet".</div>`);
  show(`${p.county_name} County`, html);
}

/* ---------- shortlist ---------- */
function renderShortlistCount() { $("sl-count").textContent = state.shortlist.length; }

/* ---------- C4: saved workspaces (spec §13 "user-saved custom workspaces") ----------
   Persists the whole analytical position — every screener setting, the scoring weights, which
   layers are on, and the map view — under a name, in localStorage.

   CONTROLS ARE ENUMERATED, NOT LISTED. A hardcoded list of ids is the same defect as a hardcoded
   wiring count: it is correct until someone adds a control, and then it silently saves an
   incomplete workspace. Anything matching f-* / sc-* / L-* is captured, so a new filter is
   included the day it ships without touching this code.

   Stored per-browser and said so on screen — a workspace that silently fails to follow the user
   to another machine would be worse than no workspace at all. */
const WS_KEY = "in_workspaces";
const wsControls = () => [...document.querySelectorAll('[id^="f-"],[id^="sc-"],[id^="L-"]')]
  .filter((el) => el.tagName === "INPUT" || el.tagName === "SELECT");
const wsAll = () => { try { return JSON.parse(localStorage.getItem(WS_KEY) || "{}"); } catch { return {}; } };

function wsCapture() {
  const controls = {};
  for (const el of wsControls()) {
    controls[el.id] = el.type === "checkbox" || el.type === "radio"
      ? { checked: el.checked } : { value: el.value };
  }
  const ctr = map.getCenter();
  return { controls, view: { lng: +ctr.lng.toFixed(5), lat: +ctr.lat.toFixed(5), zoom: +map.getZoom().toFixed(2) },
           saved_at: new Date().toISOString(), n_controls: Object.keys(controls).length };
}

function wsApply(ws) {
  let applied = 0, missing = [];
  for (const [id, v] of Object.entries(ws.controls || {})) {
    const el = document.getElementById(id);
    if (!el) { missing.push(id); continue; }        // a control that no longer exists is REPORTED
    if ("checked" in v) el.checked = v.checked; else el.value = v.value;
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.dispatchEvent(new Event("input", { bubbles: true }));
    applied++;
  }
  if (ws.view) map.jumpTo({ center: [ws.view.lng, ws.view.lat], zoom: ws.view.zoom });
  try { syncLayers(); applyFilters(); } catch (e) { console.warn("workspace applied, redraw failed", e); }
  return { applied, missing };
}

function wsRefreshList() {
  const all = wsAll(), sel = $("ws-list");
  sel.innerHTML = `<option value="">— saved workspaces —</option>` +
    Object.keys(all).sort().map((n) =>
      `<option value="${n.replace(/"/g, "&quot;")}">${n} (${String(all[n].saved_at || "").slice(0, 10)})</option>`).join("");
}

if ($("ws-save")) {
  $("ws-save").addEventListener("click", () => {
    const name = ($("ws-name").value || "").trim();
    if (!name) { $("ws-status").innerHTML = `<span class="cannot">Name it first.</span>`; return; }
    const all = wsAll(); const existed = !!all[name];
    all[name] = wsCapture();
    localStorage.setItem(WS_KEY, JSON.stringify(all));
    wsRefreshList();
    $("ws-status").innerHTML = `${existed ? "Overwrote" : "Saved"} <b>${name}</b> — ` +
      `${all[name].n_controls} controls + map view. Stored in this browser only.`;
  });
  $("ws-load").addEventListener("click", () => {
    const name = $("ws-list").value, all = wsAll();
    if (!name || !all[name]) { $("ws-status").innerHTML = `<span class="cannot">Pick a workspace first.</span>`; return; }
    const { applied, missing } = wsApply(all[name]);
    $("ws-status").innerHTML = `Loaded <b>${name}</b> — ${applied} controls restored` +
      (missing.length ? `. <span class="cannot">${missing.length} no longer exist and were skipped: ${missing.slice(0, 4).join(", ")}</span>` : ".");
  });
  $("ws-del").addEventListener("click", () => {
    const name = $("ws-list").value, all = wsAll();
    if (!name || !all[name]) { $("ws-status").innerHTML = `<span class="cannot">Pick a workspace first.</span>`; return; }
    delete all[name]; localStorage.setItem(WS_KEY, JSON.stringify(all));
    wsRefreshList(); $("ws-status").textContent = `Deleted ${name}.`;
  });
  wsRefreshList();
}
function toggleShortlist(key, title) {
  const i = state.shortlist.findIndex((s) => s.key === key);
  if (i >= 0) state.shortlist.splice(i, 1);
  else state.shortlist.push({ key, title, added: new Date().toISOString().slice(0, 10) });
  localStorage.setItem("in_shortlist", JSON.stringify(state.shortlist));
  renderShortlistCount();
  $("ev-star").classList.toggle("starred", state.shortlist.some((s) => s.key === key));
}
/* ---------- G93: THE ONE CONTROL THAT REPLACED THE FIVE -----------------------------------------
   Operator: the five top-right tabs should be *"replaced by something useful, insightful, or
   actionable"*. ⛔ Not five new buttons. The test applied was: what can this MAP not answer at a
   glance that is not already answered somewhere else on the page?

   Ruled out: a live count of passing parcels (the rail's `#denominator` already does it), and
   anything that is a page (that was the defect).

   What survives the test is the POWER picture for what is currently on screen. A siter pans to an
   area and the honest question is "is there any capacity here at all, and what is stopping it" -
   which needs the buses IN THE VIEWPORT, not statewide totals, and no other surface is viewport-
   aware. ⚠ It reports both directions (G111) and says how many buses it could not place, because
   only 12.3% of PJM buses carry a coordinate (G114) and a silent viewport count would read as
   "there are three buses here" when there may be thirty. */
$("btn-powerview").onclick = () => {
  if (!state.grid) { show("Power in view", `<div class="hint">The grid layer is still loading.</div>`); return; }
  const b = map.getBounds();
  const seen = new Map();   // iso|bus -> {wd, inj, name, kv, iso}
  for (const f of state.grid.features) {
    const p = f.properties;
    if (p.layer !== "bus_poi") continue;
    const [lon, lat] = f.geometry.coordinates;
    if (lon < b.getWest() || lon > b.getEast() || lat < b.getSouth() || lat > b.getNorth()) continue;
    const k = `${p.iso}|${p.bus_number}`;
    const e = seen.get(k) || { name: p.bus_name, kv: p.kv, iso: p.iso };
    if (p.direction === "Withdrawal") e.wd = p.headroom_mw;
    else e.inj = p.headroom_mw;
    e.binding = e.binding || p.worst_binding_facility;
    seen.set(k, e);
  }
  const buses = [...seen.values()];
  if (!buses.length) {
    show("Power in view", `<div class="cannot">No located bus falls inside the current view.
      ⚠ That is <b>not</b> the same as no capacity here. Only 12.3% of PJM buses carry a
      coordinate at all (223 of 1,814), and the gap is concentrated in the AEP footprint across
      north-eastern Indiana — so an empty view in that part of the state usually means we cannot
      PLACE the buses, not that none exist. MISO is fully located, 1,731 of 1,731.</div>`);
    return;
  }
  const wd = buses.map((x) => x.wd).filter((v) => v != null).sort((a, b2) => a - b2);
  const inj = buses.map((x) => x.inj).filter((v) => v != null).sort((a, b2) => a - b2);
  const med = (a) => a.length ? a[Math.floor(a.length / 2)] : null;
  const atLeast = (a, n) => a.filter((v) => v >= n).length;
  // which constraint binds most often here -- the actionable half, and the reason this is not
  // just a headroom histogram
  const tally = {};
  for (const x of buses) if (x.binding) tally[x.binding] = (tally[x.binding] || 0) + 1;
  const top = Object.entries(tally).sort((a, b2) => b2[1] - a[1]).slice(0, 3);
  const isos = [...new Set(buses.map((x) => x.iso))].join(" + ");
  show("Power in view", `
    <div class="hint">Everything below is measured over the <b>${fmt(buses.length)} located
      buses inside the current map view</b> (${escHtml(isos)}). Pan or zoom and reopen to
      re-measure.</div>
    <h3>Withdrawal — what a LOAD can pull out</h3><table>
      ${row("Buses with a load figure", wd.length || null, "none in view")}
      ${row("Median headroom", wd.length ? `${fmt(Math.round(med(wd)))} MW` : null)}
      ${row("Best in view", wd.length ? `${fmt(Math.round(wd[wd.length - 1]))} MW` : null)}
      ${row("At or above 300 MW", wd.length ? `${atLeast(wd, 300)} of ${wd.length}` : null)}
      ${row("At zero", wd.length ? `${wd.filter((v) => v <= 0).length} of ${wd.length}` : null)}
    </table>
    <h3>Injection — what a GENERATOR can push in</h3><table>
      ${row("Buses with an injection figure", inj.length || null, "none in view")}
      ${row("Median headroom", inj.length ? `${fmt(Math.round(med(inj)))} MW` : null)}
      ${row("Best in view", inj.length ? `${fmt(Math.round(inj[inj.length - 1]))} MW` : null)}
    </table>
    <h3>What binds first here</h3>
    ${top.length ? `<table>${top.map(([f, n]) =>
        row(escHtml(f), `binds first on ${n} of ${buses.length} buses`)).join("")}</table>
      <div class="sowhat">A constraint that binds across many buses in one area is a
        <b>regional</b> limit, not a site problem — moving a few miles will not escape it, and it
        is the thing to ask the utility about first.</div>`
      : `<div class="hint">No binding facility recorded on the buses in view.</div>`}
    <div class="prov">${prov("in_bus_capacity_tier0")} · viewport measurement, both directions.
      ⚠ Counts located buses only.</div>`);
};

$("btn-shortlist").onclick = () => {
  const rows_ = state.shortlist.map((s) => `<tr><td>${s.title}</td><td>${s.added}
    <button class="unstar" data-k="${s.key}">remove</button></td></tr>`).join("");
  show(`Shortlist (${state.shortlist.length})`, state.shortlist.length
    ? `<table>${rows_}</table><div class="hint">Stored in this browser. Star parcels from their evidence panel; export via the CSV button with your screen applied.</div>`
    : `<div class="hint">Empty — open any parcel's evidence panel and press ★.</div>`);
  document.querySelectorAll(".unstar").forEach((b) => b.onclick = () => { toggleShortlist(b.dataset.k, ""); $("btn-shortlist").click(); });
};

/* ---------- top panels ----------
   G93 removed the Inventory / Acquisitions / Market / Future-capacity modals, and `FEATURE_HOME`
   went with them: it was a hand-maintained table mapping each table name to the surface that
   shows it, read by the Inventory modal alone. It had already drifted (it still named
   `in_bus_headroom_miso`, superseded by G63). The generated `docs/TABLE_PURPOSE_INDEX.md` and
   `audit_wiring_census.py` answer the same question from the warehouse instead of from memory. */

/* ---------- upload door: user's own sites through the same pipeline ---------- */
/* =============================================================================================
   G79 - THE DOSSIER MUST COVER MANUALLY INPUTTED SITES
   Operator, 2026-08-19: *"The dossier should contain manually inputted sites, not just the sites
   we currently have in view."*

   ⭐ THE ROW'S PREMISE WAS TOO PESSIMISTIC, AND CHECKING IT IS MOST OF THE ANSWER.
   G79 assumed this needed a "degraded-mode design", because `renderPowerPlan()` reads the
   parcel's own POLYGON - Figure 2 draws it to scale and the serving utility resolves from up to
   64 ring vertices - and an uploaded row is a point.

   But our parcel corpus is EVERY Indiana parcel (3,553,194 of them). A point inside Indiana is
   therefore almost always INSIDE one, and once it is resolved there is nothing degraded about
   it: the uploaded site gets the identical dossier a held parcel gets, from the same function,
   because it IS a held parcel - the reader simply arrived at it by coordinate instead of by
   clicking. The honest design is RESOLVE FIRST, degrade only when resolution fails.

   ⛔ AND SAY WHICH ONE HAPPENED. A dossier that silently swaps the user's point for a parcel is
   claiming a correspondence it has not shown. The panel states that the parcel was found under
   the coordinate, and offers the raw upload beside it.

   ⚠ Degraded mode is still needed and is still honest, for three cases: a point outside Indiana,
   a row with no coordinate at all, and a point that lands where we hold no parcel (a road
   right-of-way gap, water, or an unmapped parcel). Each says WHICH figures survive on a bare
   point and what the missing ones would have needed - never a blank, never a zero (G51).
   ============================================================================================= */
/* ⚠ countyOf() already returns the word "County" in county_name ("Marion County"), so appending
   it produced "Marion County County". Normalised once here rather than at each call site. */
const ctyLabel = (c) => !c ? "" : /county$/i.test(String(c.county_name).trim())
  ? String(c.county_name).trim() : `${String(c.county_name).trim()} County`;

async function uploadedEvidence(p) {
  const lat = Number(p._lat ?? p.lat), lon = Number(p._lon ?? p.lon);
  const raw = Object.entries(p).filter(([k]) => k !== "layer" && !k.startsWith("_"))
    .slice(0, 14).map(([k, v]) => row(k, v)).join("");
  const rawBlock = `<h3>The row you uploaded</h3><table>${raw}</table>`;

  if (p._status !== "placed" || !isFinite(lat) || !isFinite(lon)) {
    show(`Your site (row ${p._row})`, `
      <div class="cannot"><b>No dossier can be built for this row.</b>
        ${p._status === "outside Indiana"
          ? "The coordinate is outside Indiana, and every layer in this application is clipped at the state border. It is kept in your list and in the export rather than dropped."
          : "The row carries no usable coordinate, so it cannot be placed against any layer. It is kept in your list and in the export rather than dropped — a row we cannot place is not a row we discard."}
      </div>${rawBlock}`);
    return;
  }

  const cty = countyOf(lon, lat);
  show(`Your site (row ${p._row})`, `<div class="hint">looking for a parcel under this
    coordinate…</div>${rawBlock}`);
  let ft = null;
  if (cty) {
    try {
      await ensureCountyLoaded(cty.fips);
      // ⚠ state.loaded holds an ARRAY OF FEATURES, not a FeatureCollection. Every other reader in
      //   this file uses `(state.loaded.get(fips) || [])` directly; treating it as `{features:…}`
      //   threw on `.find` of undefined.
      ft = (state.loaded.get(cty.fips) || []).find((f) => pointInPoly(lon, lat, f.geometry));
    } catch (err) { /* fall through to degraded mode; the reason is stated below */ }
  }

  if (ft) {
    state.uploadResolved = { row: p._row, lat, lon };
    await openDossier(ft.properties, cty.fips);
    // ⭐ prepend the correspondence rather than hiding it: this dossier is about a PARCEL we
    //    found under the reader's point, and they are entitled to see that step.
    $("evidence-body").insertAdjacentHTML("afterbegin", `
      <div class="sowhat"><b>This is the full dossier — nothing is degraded.</b>
        Your uploaded row ${p._row} at <code>${lat.toFixed(5)}, ${lon.toFixed(5)}</code> falls
        inside a parcel we hold (<code>${escHtml(String(ft.properties.parcel_key ||
          ft.properties.key || ""))}</code> in ${escHtml(ctyLabel(cty))}), so every
        figure below is measured from that parcel's own boundary — the same way it would be for a
        site you clicked. ⚠ <b>Check the parcel is the one you meant.</b> A coordinate that landed
        on a road selects the road right-of-way, which is a true answer about the wrong land.</div>`);
    return;
  }

  // ---- degraded mode: a real point, no parcel under it ----
  /* ⚠ THREE VOCABULARIES CHECKED AGAINST THE DATA, NOT GUESSED — all three were wrong first try:
       nearestBus filters on a LOWER-CASE direction ('withdrawal' / 'injection'). Capitalised
         strings match nothing and return null, which would have rendered as an honest-looking
         "no bus within 25 miles" on every uploaded site in the state.
       territoryAt returns the raw feature properties, where the name is `utility`, not `name`.
       gatesForPoint returns {mil, milMi, sua[], tribal, tall1mi} and has NO summary field. */
  const g = gatesForPoint(lat, lon);
  const terr = territoryAt(lat, lon);
  const wd = nearestBus(lat, lon, "withdrawal");
  const inj = nearestBus(lat, lon, "injection");
  const gateBits = [];
  if (g) {
    if (g.mil) gateBits.push(`${g.mil}${g.milMi ? ` at ${g.milMi} mi` : " — the point is inside it"}`);
    if (g.tribal) gateBits.push(`tribal trust land: ${g.tribal}`);
    if (g.sua && g.sua.length) gateBits.push(`special-use airspace: ${g.sua.join(", ")}`);
    if (g.tall1mi) gateBits.push(`${g.tall1mi} tall obstruction${g.tall1mi === 1 ? "" : "s"} within a mile`);
  }
  show(`Your site (row ${p._row})`, `
    <div class="cannot"><b>Partial dossier — we hold no parcel under this coordinate.</b>
      It is inside ${cty ? escHtml(ctyLabel(cty)) : "Indiana"}, so everything keyed
      to LOCATION still works. Everything keyed to the parcel BOUNDARY cannot be computed, and is
      listed as such below rather than left blank.</div>
    <h3>What still holds at this point</h3><table>
      ${row("county", cty && cty.county_name)}
      ${row("serving utility", terr && terr.utility, "no service territory covers this point")}
      ${row("nearest load bus", wd && `${wd.name} — ${fmt(Math.round(wd.mw))} MW at ${wd.mi.toFixed(1)} mi`,
            "no withdrawal bus within 25 miles")}
      ${row("nearest generation bus", inj && `${inj.name} — ${fmt(Math.round(inj.mw))} MW at ${inj.mi.toFixed(1)} mi`,
            "no injection bus within 25 miles")}
      ${row("substation", p._sub_name && `${p._sub_name} at ${p._sub_mi} mi`,
            "no substation within 25 miles")}
      ${row("transmission line", p._dline_mi != null ? `${p._dline_mi} mi` : null,
            "no line within 25 miles")}
      ${row("who else holds a say over this land", gateBits.length ? gateBits.join(" · ") : null,
            "no installation, sovereign boundary, airspace ceiling or tall obstruction in range")}
    </table>
    <h3>What a parcel would have added, and why it cannot</h3><table>
      ${row("acreage and buildable area", null, "needs a boundary — a point has no area")}
      ${row("megawatts the ground could host", null, "derived from acreage, so it follows the above")}
      ${row("the parcel diagram", null, "drawn from the boundary polygon")}
      ${row("deliverable capacity", null,
            "measured from the parcel to the nearest line and then to the bus at each end")}
      ${row("owner-motivation signals", null, "attached to a parcel key, which this point has none of")}
    </table>
    ${rawBlock}
    <div class="prov">your upload · enriched client-side against the same layers as the feed.
      Nothing leaves the browser. ⚠ A point with no parcel under it usually means water, a road
      right-of-way gap, or a parcel the county has not published — not that the land is
      unowned.</div>`);
}

function pointInPoly(lon, lat, geom) {
  const test = (ring) => {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i], [xj, yj] = ring[j];
      if ((yi > lat) !== (yj > lat) && lon < (xj - xi) * (lat - yi) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  };
  const polys = geom.type === "Polygon" ? [geom.coordinates] : geom.coordinates;
  return polys.some((p) => test(p[0]) && !p.slice(1).some(test));
}
function countyOf(lon, lat) {
  for (const f of state.counties.features) {
    const [w, s, e, n] = state.countyBbox[f.properties.fips];
    if (lon < w || lon > e || lat < s || lat > n) continue;
    if (pointInPoly(lon, lat, f.geometry)) return f.properties;
  }
  return null;
}
function parseCsv(text) {
  let cur = [""], inQ = false, out = [];
  for (const ch of text) {
    if (inQ) { if (ch === '"') inQ = false; else cur[cur.length - 1] += ch; }
    else if (ch === '"') inQ = true;
    else if (ch === ",") cur.push("");
    else if (ch === "\n" || ch === "\r") { if (cur.length > 1 || cur[0]) out.push(cur); cur = [""]; }
    else cur[cur.length - 1] += ch;
  }
  if (cur.length > 1 || cur[0]) out.push(cur);
  if (!out.length) return [];
  const hdr = out[0].map((h) => h.trim().toLowerCase());
  return out.slice(1).map((r) => Object.fromEntries(hdr.map((h, i) => [h, r[i]])));
}
state.uploaded = [];
state.uploadSheet = null;          // { sheets, chosen, headerRow, mapping, filename }

/* ---------- G74: ANY sheet in --------------------------------------------------------------
   Operator, 2026-08-19: *"It is crucial that we have full functionality for the user to load in
   sites within the application. ANY Excel sheet should be able to be inputted."*

   The old door took a CSV whose header was row 1 and whose coordinate columns were literally
   called lat/lon, and told everyone else "No lat/lon columns found". That is a hardcoded schema
   wearing an error message. Three things change here:
     * .xlsx as well as .csv/.tsv, read by vendor/xlsx-lite.js -- no CDN, nothing uploaded.
     * The HEADER ROW IS FOUND, not assumed. Real exports carry a title and a date stamp above it.
     * The MAPPING IS PROPOSED AND THEN ASKED. We guess, we show the guess in a dropdown per role,
       and the user overrides it. A guess presented as a fact is worse than a question -- and a
       silent wrong guess on the longitude column puts every one of their sites in the wrong
       county with no visible failure. */
function renderUploadMapper() {
  const u = state.uploadSheet;
  if (!u) { $("upload-map").innerHTML = ""; return; }
  const rows = u.sheets[u.chosen].rows;
  const header = (rows[u.headerRow] || []).map((c, i) =>
    (String(c ?? "").trim() || `column ${XLSXLite.colName(i)}`));
  const sheetPick = u.sheets.length > 1
    ? `<label class="blk" style="margin-bottom:4px">Sheet
         <select id="up-sheet">${u.sheets.map((s, i) =>
           `<option value="${i}"${i === u.chosen ? " selected" : ""}>${escHtml(s.name)} (${s.rows.length} rows)</option>`).join("")}</select></label>` : "";
  const opts = (sel) => `<option value="">— not in my sheet —</option>` + header.map((h, i) =>
    `<option value="${i}"${String(sel) === String(i) ? " selected" : ""}>${escHtml(h)}</option>`).join("");
  $("upload-map").innerHTML = `
    <div style="border:1px solid #cbd5e1;border-radius:6px;padding:7px;background:#f8fafc">
      <b>Which column is which?</b>
      ${sheetPick}
      <label class="blk" style="margin-bottom:4px">Header row
        <select id="up-hdr">${rows.slice(0, Math.min(rows.length, 20)).map((r, i) =>
          `<option value="${i}"${i === u.headerRow ? " selected" : ""}>row ${i + 1}: ${
            escHtml((r || []).filter((c) => c != null && String(c).trim() !== "").slice(0, 4).join(" | ")).slice(0, 48)}</option>`).join("")}</select></label>
      ${COLUMN_ROLES.map(([role, label]) =>
        `<label class="blk" style="margin-bottom:3px">${label}${role === "lat" || role === "lon" ? " <b>*</b>" : ""}
           <select class="up-role" data-role="${role}">${opts(u.mapping[role])}</select></label>`).join("")}
      <div class="hint" style="margin-top:4px"><b>*</b> Latitude and longitude are required to place
        a site. We do <b>not</b> geocode an address to a street centerline — that is a project rule,
        because a centerline is not a parcel. Rows without coordinates are still kept and exported.</div>
      <button id="up-apply" style="margin-top:5px">Load these ${Math.max(0, rows.length - u.headerRow - 1)} rows</button>
    </div>`;
  const resync = () => {
    if ($("up-sheet")) u.chosen = Number($("up-sheet").value);
    u.headerRow = Number($("up-hdr").value);
    u.mapping = guessColumns((u.sheets[u.chosen].rows[u.headerRow] || []));
    renderUploadMapper();
  };
  if ($("up-sheet")) $("up-sheet").onchange = () => { u.headerRow = findHeaderRow(u.sheets[Number($("up-sheet").value)].rows); resync(); };
  $("up-hdr").onchange = resync;
  for (const el of document.querySelectorAll(".up-role"))
    el.onchange = () => { u.mapping[el.dataset.role] = el.value; };
  $("up-apply").onclick = () => {
    const { records } = mapSheetRows(u.sheets[u.chosen].rows, u.headerRow, u.mapping);
    if (!records.length) { $("upload-status").innerHTML = `<span class="cannot">That header row leaves no data rows below it.</span>`; return; }
    ingestRecords(records, "_lat", "_lon", { filename: u.filename, sheet: u.sheets[u.chosen].name,
      sheetCount: u.sheets.length, mapping: u.mapping, headerRow: u.headerRow });
  };
}

$("upload").addEventListener("change", async (e) => {
  const file = e.target.files[0]; if (!file) return;
  $("upload-status").textContent = "reading…";
  let wb;
  try { wb = await XLSXLite.readAny(file); }
  catch (err) {
    $("upload-status").innerHTML = `<span class="cannot">Could not read that file: ${escHtml(err.message)}</span>`;
    return;
  }
  // the sheet with the most rows is the right default far more often than sheet 1 -- workbooks
  // routinely open on a cover sheet or a notes tab
  const chosen = wb.sheets.reduce((b, s, i, a) => (s.rows.length > a[b].rows.length ? i : b), 0);
  state.uploadSheet = { sheets: wb.sheets, chosen, filename: file.name,
    headerRow: findHeaderRow(wb.sheets[chosen].rows), mapping: {} };
  state.uploadSheet.mapping = guessColumns(wb.sheets[chosen].rows[state.uploadSheet.headerRow] || []);
  const g = state.uploadSheet.mapping;
  renderUploadMapper();
  $("upload-status").innerHTML = g.lat !== undefined && g.lon !== undefined
    ? `Found coordinates automatically. Check the mapping and load.`
    : `<span class="cannot">No coordinate columns recognized — pick them above.</span>`;
});

function ingestRecords(recs, latK, lonK, meta) {
  let placed = 0, unplaced = 0, outside = 0;
  const feats = [];
  state.uploaded = recs.map((r, i) => {
    const lat = parseFloat(r[latK]), lon = parseFloat(r[lonK]);
    const row_ = { ...r, _row: r._row ?? i + 1 };
    if (!isFinite(lat) || !isFinite(lon)) { row_._status = "cannot-place (no coords)"; unplaced++; return row_; }
    const cty = countyOf(lon, lat);
    if (!cty) { row_._status = "outside Indiana"; outside++; return row_; }
    const c = state.ctx.by_fips[cty.fips] || {};
    // PARITY (spec §13(2)): an uploaded site must be scored EXACTLY as a held parcel is, so it
    // goes through the SAME function held parcels do rather than a parallel copy of the maths.
    // The copy that used to live here computed the same substation distance but wrote it to
    // `_sub_mi`, while the scorer reads `_dsub_mi` — so scoreP2 hit its
    // `if (p._dsub_mi == null && p._dline_mi == null) return null` guard and EVERY UPLOADED ROW
    // WENT UNSCORED. It also never computed transmission-line distance at all. Two code paths
    // for one calculation will always drift; one function cannot.
    const ft = { type: "Feature", properties: row_,
                 geometry: { type: "Point", coordinates: [lon, lat] } };
    enrichDistances([ft]);          // mutates row_ in place: _dsub_*, _dline_*, _dpoi_*
    Object.assign(row_, {
      _status: "placed", _county: cty.county_name,
      // legacy aliases kept so the enriched-CSV export keeps its old headers
      _sub_mi: row_._dsub_mi ?? null, _sub_name: row_._dsub_name ?? null,
      _sub_kv: row_._dsub_kv ?? null,
      _poi_mi: row_._dpoi_mi ?? null, _poi_headroom_mw: row_._dpoi_mw ?? null,
      _county_opposition: c.posture?.opposition_intensity ?? null,
      _county_restriction: c.posture?.has_local_restriction ?? null,
      _county_seismic: c.seismic?.sdc ?? null,
      _county_fiber_locs: c.fibre?.fiber_locations ?? null,
      _county_queue_mw: c.queue?.active_mw ?? null,
    });
    // and now it can actually be scored, by the same scorer the map uses
    const sc = (typeof scoreP2 === "function") ? scoreP2(row_) : null;
    if (sc) { row_._p2_score = sc.score ?? sc; row_._p2_why = (sc.why || []).join("; "); }
    placed++;
    feats.push({ type: "Feature", properties: { ...row_, layer: "uploaded" },
      geometry: { type: "Point", coordinates: [lon, lat] } });
    return row_;
  });
  const fc = { type: "FeatureCollection", features: feats };
  if (map.getSource("uploaded")) map.getSource("uploaded").setData(fc);
  else {
    map.addSource("uploaded", { type: "geojson", data: fc });
    map.addLayer({ id: "uploaded-pts", type: "circle", source: "uploaded",
      paint: { "circle-radius": 7, "circle-color": "#16a34a", "circle-stroke-color": "#fff",
               "circle-stroke-width": 2 } });
    map.on("click", "uploaded-pts", (e2) => uploadedEvidence(e2.features[0].properties));
    map.on("mousemove", "uploaded-pts", (e2) => showTip(e2, `your site · ${e2.features[0].properties._county || ""} · sub ${e2.features[0].properties._sub_mi ?? "?"} mi`));
    map.on("mouseleave", "uploaded-pts", hideTip);
  }
  // G74: persist across PAGES. The store drops itself on a refresh, which is the semantics the
  // operator asked for and is NOT what sessionStorage does on its own -- see SiteStore.
  const saved = SiteStore.save(state.uploaded, { ...(meta || {}), placed, unplaced, outside });
  $("upload-map").innerHTML = "";
  $("upload-status").innerHTML =
    `<b>${placed}</b> placed · ${outside} outside Indiana · <b>${unplaced}</b> cannot-place `
    + `(kept, listed in export) — green markers.`
    + (meta && meta.filename ? `<br><span class="hint">${escHtml(meta.filename)}`
        + (meta.sheetCount > 1 ? ` · sheet “${escHtml(meta.sheet)}”` : "")
        + ` · header row ${(meta.headerRow ?? 0) + 1}</span>` : "")
    + (saved.ok
        ? `<br><span class="hint">Kept while you move between pages; cleared when you refresh.</span>`
        : `<br><span class="cannot">${escHtml(saved.error)}</span>`);
  $("upload-export").disabled = $("upload-export-csv").disabled = $("upload-clear").disabled = false;
  return { placed, unplaced, outside };
}

/* G74: restore on a page change. The store is empty after a refresh by design, so this quietly
   does nothing then -- which is the requirement, not a failure. */
function restoreUploadedSites() {
  if (!SiteStore.has()) return;
  const m = SiteStore.meta() || {};
  ingestRecords(SiteStore.rows(), "_lat", "_lon", m);
}

/* ---------- G74: rich Excel out -------------------------------------------------------------
   "The Excel outputs should also be nearly all-encompassing." So the workbook carries EVERY
   column present on any row (union, never rows[0]'s keys -- a first row lacking the enriched
   distance fields would otherwise drop them for everyone), plus a README sheet that says what
   the file is, when it was built, what was filtered and what the columns mean. A spreadsheet
   that leaves the tool without its provenance becomes an anonymous number in someone's deck. */
function sheetFromRows(rows, title) {
  const cols = [...new Set(rows.flatMap((r) => Object.keys(r)))];
  // put the readable identity columns first; leave everything else in discovered order
  const lead = ["_row", "_status", "_name", "_county", "county_name", "parcel_key", "_lat", "_lon", "lat", "lon"];
  cols.sort((a, b) => {
    const ia = lead.indexOf(a), ib = lead.indexOf(b);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
  });
  return { name: title, rows: [cols.map((c) => c.replace(/^_/, "")), ...rows.map((r) => cols.map((c) => {
    const v = r[c];
    return v === null || v === undefined ? null : (typeof v === "object" ? JSON.stringify(v) : v);
  }))] };
}
function readmeSheet(what, lines) {
  return { name: "README", rows: [
    ["Indiana Siting Intelligence — " + what], [],
    ["Exported", new Date().toISOString().replace("T", " ").slice(0, 19) + " UTC"],
    ...lines.map((l) => (Array.isArray(l) ? l : [l])), [],
    ["Blank means NOT MEASURED, never zero."],
    ["A cell reading 'cannot-place' is a row we kept deliberately rather than dropping."],
    ["Distances are in miles, measured to the parcel footprint, not to a centroid."],
    ["Nothing in this workbook was uploaded anywhere — it was built in your browser."],
  ] };
}
$("upload-export").onclick = () => {
  if (!state.uploaded.length) return;
  const m = SiteStore.meta() || {};
  XLSXLite.download(XLSXLite.write([
    readmeSheet("your uploaded sites, enriched", [
      ["Source file", m.filename || "(unknown)"],
      ["Sheet", m.sheet || "(only sheet)"],
      ["Rows", state.uploaded.length],
      ["Placed", m.placed ?? ""], ["Outside Indiana", m.outside ?? ""], ["Cannot place", m.unplaced ?? ""],
      [],
      ["Every column you supplied is preserved. Columns we added are prefixed in the source data"],
      ["with an underscore and appear here without it: county, sub_mi, poi_mi, p2_score and so on."],
    ]),
    sheetFromRows(state.uploaded, "Your sites"),
  ]), "your_sites_enriched.xlsx");
};
$("upload-export-csv").onclick = () => {
  if (!state.uploaded.length) return;
  const cols = [...new Set(state.uploaded.flatMap((r) => Object.keys(r)))];
  const esc = (v) => v == null ? "" : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v);
  const csv = [cols.join(","), ...state.uploaded.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n");
  XLSXLite.download(new Blob([csv], { type: "text/csv" }), "your_sites_enriched.csv");
};
$("upload-clear").onclick = () => {
  state.uploaded = []; state.uploadSheet = null; SiteStore.clear();
  if (map.getSource("uploaded")) map.getSource("uploaded").setData({ type: "FeatureCollection", features: [] });
  $("upload-status").textContent = ""; $("upload-map").innerHTML = "";
  $("upload-export").disabled = $("upload-export-csv").disabled = $("upload-clear").disabled = true;
};

/* ---------- CSV and Excel export ------------------------------------------------------------
   G74: "nearly all-encompassing". The workbook carries the parcels you can see under the filters
   you set, a README that states BOTH numbers (shown and matching) and the filters in force, and
   your uploaded sites as their own sheet if any are loaded -- so the file is self-describing
   once it is out of the tool. */
function exportRows() {
  const rows = [];
  for (const fips of countiesInView()) {
    const feats = state.loaded.get(fips); if (!feats || !countyOk(fips)) continue;
    for (const ft of feats) if (jsMatches(ft.properties)) rows.push(ft.properties);
  }
  return rows;
}
function activeFilterLines() {
  const out = [];
  const push = (k, v) => out.push([k, v]);
  push("Project type", $("f-usecase").selectedOptions[0].text);
  if ($("f-mw").checked) push("Fits at least", `${V("f-mw-val")} MW at ${V("f-density")} MW/acre`);
  for (const [id, label] of [["f-ci", "commercial / industrial"], ["f-ag", "farmland"],
    ["f-vac", "undeveloped"], ["f-other", "other non-residential"]])
    if ($(id) && $(id).checked) push("Land class kept", label);
  if ($("f-dsub").checked) push("Within of a substation", `${V("f-dsub-mi")} mi, min ${V("f-dsub-kv")} kV`);
  if ($("f-dline").checked) push("Within of a transmission line", `${V("f-dline-mi")} mi`);
  for (const [id, label] of [["f-noflood", "flood zones excluded"], ["f-nowet", "wetland excluded"],
    ["f-noprot", "protected-land overlap excluded"], ["f-bonus", "tax-credit areas only"]])
    if ($(id) && $(id).checked) push("Environmental", label);
  push("Counties in view", countiesInView().length);
  return out;
}
$("export-xlsx").onclick = () => {
  const rows = exportRows();
  if (!rows.length) return;
  const sheets = [readmeSheet("screened parcels", [
    ["Rows in this workbook", rows.length],
    ["What they are", "the parcels inside the current map view that pass every filter below"],
    ["⚠ This is the VIEW, not the state", "pan out or clear filters to widen it"],
    [], ["FILTERS IN FORCE"], ...activeFilterLines(),
  ]), sheetFromRows(rows, "Screened parcels")];
  if (state.uploaded.length) sheets.push(sheetFromRows(state.uploaded, "Your sites"));
  XLSXLite.download(XLSXLite.write(sheets),
    `indiana_screened_sites_${new Date().toISOString().slice(0, 10)}.xlsx`);
};
$("export-csv").onclick = () => {
  const rows = exportRows();
  if (!rows.length) return;
  // union, not rows[0]'s keys: the screener attaches _dsub_*/_dpoi_* per parcel, so a first
  // row that happens to lack them would silently drop those columns from everyone's export
  const cols = [...new Set(rows.flatMap((r) => Object.keys(r)))];
  const esc = (v) => v == null ? "" : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v);
  const csv = [cols.join(","), ...rows.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = `indiana_screened_sites_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
};
