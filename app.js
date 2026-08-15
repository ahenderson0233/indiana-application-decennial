/* Indiana Siting Intelligence — composable Screener + Layers console.
 * Everything renders together; the screener composes across parts (class, MW, SI, grid
 * distance, environmental gates, county sentiment). Every number carries provenance;
 * cannot-assess renders as itself; estimates never style as published coordinates. */
"use strict";

const PARCEL_ZOOM = 10;
const MI = 1609.344;
const state = {
  summary: null, provenance: {}, counties: null, countyBbox: {}, ctx: null,
  loaded: new Map(), loading: new Set(), receipts: null,
  grid: null, gas: null, pjm: null, terr: null, overlays: null, cand: null,
  subBins: null, lineBins: null, poiList: null,
  shortlist: JSON.parse(localStorage.getItem("in_shortlist") || "[]"),
  measure: { on: false, pts: [] }, market: null, pipeline: null,
};

/* ---------- helpers ---------- */
async function fetchGz(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return new Response(res.body.pipeThrough(new DecompressionStream("gzip"))).json();
}
/* fmt + fetchGz come from common.js (loaded first) */
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
map.addControl(new maplibregl.NavigationControl(), "top-right");
map.addControl(new maplibregl.ScaleControl({ unit: "imperial" }), "bottom-left");

map.on("load", async () => {
  state.summary = await (await fetch("data/state_summary.json?v=" + Date.now())).json();
  for (const p of state.summary.provenance) state.provenance[p.table_name] = p;
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
      const [lon, lat] = f.geometry.coordinates;
      binPush(state.subBins, lon, lat, { lon, lat, name: p.substation_name, kv: Number(p.max_kv) || 0 });
    } else if (p.layer === "line") {
      const walk = (c) => { if (typeof c[0] === "number") binPush(state.lineBins, c[0], c[1], { lon: c[0], lat: c[1], kv: Number(p.voltage) || 0 }); else c.forEach(walk); };
      walk(f.geometry.coordinates);
    } else if (p.layer === "bus_poi") {
      const [lon, lat] = f.geometry.coordinates;
      state.poiList.push({ lon, lat, name: p.poi_name, median: p.median_mw, best: p.best_mw });
    }
  }
  map.addSource("grid", { type: "geojson", data: state.grid });
  map.addLayer({ id: "grid-lines", type: "line", source: "grid",
    filter: ["==", ["get", "layer"], "line"],
    paint: { "line-color": ["step", ["to-number", ["get", "voltage"], 0], "#9aa5b5", 100, "#4a7bd0", 300, "#7c3aed"],
             "line-width": ["step", ["to-number", ["get", "voltage"], 0], 1, 100, 1.7, 300, 2.6] } });
  map.addLayer({ id: "grid-subs", type: "circle", source: "grid",
    filter: ["==", ["get", "layer"], "substation"],
    paint: { "circle-radius": ["interpolate", ["linear"], ["to-number", ["get", "max_kv"], 0], 0, 2.2, 138, 4.2, 345, 7],
             "circle-color": "#334155", "circle-opacity": 0.8 } });
  map.addLayer({ id: "grid-bus", type: "circle", source: "grid",
    filter: ["==", ["get", "layer"], "bus_poi"],
    paint: { "circle-radius": ["interpolate", ["linear"], ["to-number", ["get", "median_mw"], 0], 0, 4, 2000, 9, 8000, 13],
             "circle-color": "#d97706", "circle-stroke-color": "#7c2d12", "circle-stroke-width": 1.2, "circle-opacity": 0.9 } });
  map.addLayer({ id: "grid-bus-label", type: "symbol", source: "grid", minzoom: 8,
    filter: ["==", ["get", "layer"], "bus_poi"],
    layout: { "text-field": ["concat", ["to-string", ["round", ["to-number", ["get", "median_mw"], 0]]], " MW"],
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
  map.addLayer({ id: "gas-pts", type: "circle", source: "gas",
    filter: ["in", ["get", "layer"], ["literal", ["compressor", "storage"]]], layout: { visibility: "none" },
    paint: { "circle-radius": 5, "circle-color": ["case", ["==", ["get", "layer"], "compressor"], "#b45309", "#78350f"],
             "circle-stroke-color": "#fff", "circle-stroke-width": 1 } });

  state.terr = await fetchGz("data/territories.geojson.gz");
  map.addSource("terr", { type: "geojson", data: state.terr });
  map.addLayer({ id: "terr-fill", type: "fill", source: "terr", layout: { visibility: "none" },
    paint: { "fill-color": ["case", ["==", ["get", "utility_type"], "investor_owned"], "#93c5fd",
             ["==", ["get", "utility_type"], "cooperative"], "#fcd34d", "#d1d5db"],
             "fill-opacity": 0.28, "fill-outline-color": "#475569" } }, "county-line");

  state.overlays = await fetchGz("data/overlays.geojson.gz");
  map.addSource("overlays", { type: "geojson", data: state.overlays });
  map.addLayer({ id: "env-padus", type: "fill", source: "overlays",
    filter: ["==", ["get", "layer"], "padus"], layout: { visibility: "none" },
    paint: { "fill-color": "#15803d", "fill-opacity": 0.32, "fill-outline-color": "#14532d" } });
  map.addLayer({ id: "env-bonus", type: "fill", source: "overlays",
    filter: ["==", ["get", "layer"], "bonus"], layout: { visibility: "none" },
    paint: { "fill-color": "#7c3aed", "fill-opacity": 0.2, "fill-outline-color": "#5b21b6" } });
  map.addLayer({ id: "env-nonatt", type: "fill", source: "overlays",
    filter: ["==", ["get", "layer"], "nonattainment"], layout: { visibility: "none" },
    paint: { "fill-color": "#9f1239", "fill-opacity": 0.18, "fill-outline-color": "#881337" } });

  state.fac = await fetchGz("data/facilities.geojson.gz");
  map.addSource("fac", { type: "geojson", data: state.fac });
  map.addLayer({ id: "fac-dc", type: "circle", source: "fac",
    filter: ["==", ["get", "layer"], "dc"], layout: { visibility: "none" },
    paint: { "circle-radius": 6.5, "circle-color": "#0ea5e9", "circle-stroke-color": "#0c4a6e",
             "circle-stroke-width": 1.6, "circle-opacity": 0.9 } });
  map.addLayer({ id: "fac-gen", type: "circle", source: "fac",
    filter: ["in", ["get", "layer"], ["literal", ["plant", "plant_hifld", "solar", "wind"]]],
    layout: { visibility: "none" },
    paint: { "circle-radius": ["case", ["==", ["get", "layer"], "wind"], 2.5, 4.5],
             "circle-color": ["case", ["==", ["get", "layer"], "solar"], "#eab308",
               ["==", ["get", "layer"], "wind"], "#38bdf8", "#6b7280"],
             "circle-opacity": 0.75 } });
  for (const id of ["fac-dc", "fac-gen"]) {
    map.on("click", id, (e) => {
      if (state.measure.on) return;
      const p = e.features[0].properties;
      const rows_ = Object.entries(p).filter(([k]) => k !== "layer").slice(0, 10).map(([k, v]) => row(k, v)).join("");
      show(p.layer === "dc" ? `Existing data centre: ${p.name || ""}` : `Facility (${p.layer})`,
        `<table>${rows_}</table><div class="prov">${p.layer === "dc" ? prov("in_data_centers_all") + " · 4-source union; cross-source dedupe pending operator rule" : prov("in_eia_plants")}</div>`);
    });
    map.on("mousemove", id, (e) => showTip(e, tipText(e.features[0].properties)));
    map.on("mouseleave", id, hideTip);
  }
  state.log = await fetchGz("data/logistics.geojson.gz");
  map.addSource("log", { type: "geojson", data: state.log });
  // line-dasharray is data-CONSTANT in MapLibre — a ["case", …] here makes addLayer reject the
  // whole layer (silently: the toggle then does nothing). Split rail/road into two layers.
  map.addLayer({ id: "log-lines", type: "line", source: "log", layout: { visibility: "none" },
    filter: ["!=", ["get", "layer"], "rail"],
    paint: { "line-color": "#a8a29e", "line-width": 1 } });
  map.addLayer({ id: "log-lines-rail", type: "line", source: "log", layout: { visibility: "none" },
    filter: ["==", ["get", "layer"], "rail"],
    paint: { "line-color": "#57534e", "line-width": 1.4, "line-dasharray": [4, 2] } });
  for (const id of ["log-lines", "log-lines-rail"]) {
    map.on("mousemove", id, (e) => showTip(e, `${e.features[0].properties.layer}: ${e.features[0].properties.name || e.features[0].properties.fullname || ""}`));
    map.on("mouseleave", id, hideTip);
  }
  state.cand = await fetchGz("data/candidates.geojson.gz");
  map.addSource("cand", { type: "geojson", data: state.cand });
  map.addLayer({ id: "cand-line", type: "line", source: "cand", layout: { visibility: "none" },
    paint: { "line-color": "#7c3aed", "line-width": 2, "line-dasharray": [2, 1.5] } });

  // clicks + hover for every non-parcel layer
  const clickable = { "grid-bus": gridEv, "grid-subs": gridEv, "grid-lines": gridEv,
    "pjm-queue": miscEv, "pjm-bus-est": miscEv, "gas-lines": miscEv, "gas-pts": miscEv,
    "env-padus": miscEv, "env-bonus": miscEv, "env-nonatt": miscEv, "cand-line": candEv };
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
  document.body.dataset.ready = "1";
});

/* ---------- county paint / metric ---------- */
function countyPaint(metric) {
  if (metric === "none") return "rgba(0,0,0,0)";
  if (metric === "opposition_intensity")
    return ["case", ["==", ["get", "opposition_intensity"], null], "#f2f2f0",
      ["interpolate", ["linear"], ["to-number", ["get", "opposition_intensity"], 0],
       0, "#eef6ee", 1, "#fde68a", 3, "#f59e0b", 6, "#b91c1c"]];
  if (metric === "queue_active_mw")
    return ["case", ["==", ["get", "queue_active_mw"], null], "#f2f2f0",
      ["interpolate", ["linear"], ["to-number", ["get", "queue_active_mw"], 0],
       0, "#f4f7fb", 200, "#c7d9f0", 1000, "#7fa8d9", 3000, "#3b6bb5"]];
  const field = metric === "ge25mw" ? "ge25mw" : "class_union";
  return ["interpolate", ["linear"], ["get", field],
    0, "#f4f7fb", 2000, "#dbe7f5", 10000, "#b7cfea", 30000, "#8fb2dc", 80000, "#5d8cc7"];
}
document.getElementById("county-metric").addEventListener("change", (e) => {
  map.setPaintProperty("county-fill", "fill-color", countyPaint(e.target.value));
});

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

   Exact outdoor space (parcel minus the measured footprint intersection) wins when present —
   it fixes the shared-building overcount. But it carries one contradiction, measured across
   the class union: 126 of 1,200,924 parcels report an exact parcel area under half the
   recorded acreage, and for 85 of them footprints_intersecting is ZERO. With nothing
   intersecting, outdoor area IS the parcel by arithmetic, so an exact figure below it is the
   exact pipeline's geometry disagreeing with the recorded acreage — not a measurement of
   buildings. Preferring it blindly dropped 23 parcels of 75+ acres (300 MW at 4 MW/acre) out
   of the screener with no footprint to blame. So: when nothing intersects, trust the parcel.
   The disagreement is not swallowed — acreageOf() reports it and the panel prints it. */
function acreageOf(p) {
  const parcel = Number(p.parcel_acres) || 0;
  const exact = p.exact_outdoor_acres == null ? null : Number(p.exact_outdoor_acres);
  const legacy = p.outdoor_acres == null ? null : Number(p.outdoor_acres);
  if (exact != null && p.footprints_intersecting === 0 && parcel > 0 && exact < parcel * 0.99)
    return { acres: parcel, basis: "parcel area (no footprints intersect)", disputed: true };
  if (exact != null) return { acres: exact, basis: "exact (parcel − measured footprints)", disputed: false };
  if (legacy != null) return { acres: legacy, basis: "approximate", disputed: false };
  return { acres: parcel, basis: "parcel area", disputed: false };
}
function jsMatches(p) {
  if (!classOk(p)) return false;
  if ($("f-mw").checked) {
    if (acreageOf(p).acres * V("f-density") < V("f-mw-val")) return false;
  }
  if ($("f-si").checked) {
    if (p.has_si_signal !== true) return false;
    const cut = recencyCutoff();
    if (cut && (p.si_last_event_date || "") < cut) return false;
  }
  if ($("f-noflood").checked && p.sfha_flood === true) return false;
  if ($("f-nowet").checked && p.wetland_on_parcel === true) return false;
  if ($("f-noprot").checked && p.protected_land === true) return false;
  if ($("f-bonus").checked && !p.bonus_kinds) return false;
  if ($("f-dsub").checked && !(p._dsub_mi != null && p._dsub_mi <= V("f-dsub-mi") && p._dsub_kv >= V("f-dsub-kv"))) return false;
  if ($("f-dline").checked && !(p._dline_mi != null && p._dline_mi <= V("f-dline-mi"))) return false;
  return true;
}
function countyOk(fips) {
  const c = state.ctx.by_fips[fips] || {};
  if ($("f-sent").checked) {
    const oi = c.posture?.opposition_intensity;
    if (oi == null || Number(oi) > V("f-sent-max")) return false;
  }
  if ($("f-norestrict").checked && c.posture?.has_local_restriction === true) return false;
  return true;
}
function applyFilters() {
  for (const [fips, feats] of state.loaded) {
    const ok = countyOk(fips);
    const keys = new Set();
    if (ok) for (const ft of feats) if (jsMatches(ft.properties)) keys.add(ft.properties.parcel_key);
    map.setFilter(`sites-${fips}-fill`, ["in", ["get", "parcel_key"], ["literal", [...keys]]]);
    map.setFilter(`sites-${fips}-line`, ["in", ["get", "parcel_key"], ["literal", [...keys]]]);
  }
  renderDenominator();
}
for (const id of ["f-ci", "f-ag", "f-vac", "f-other", "f-mw", "f-mw-val", "f-density", "f-si",
  "f-recent", "f-recent-days", "f-noflood", "f-nowet", "f-noprot", "f-bonus",
  "f-dsub", "f-dsub-mi", "f-dsub-kv", "f-dline", "f-dline-mi", "f-sent", "f-sent-max", "f-norestrict"])
  $(id).addEventListener("change", applyFilters);
$("f-cand").addEventListener("change", syncLayers);

/* ---------- layers panel ---------- */
const LAYER_MAP = { "L-subs": ["grid-subs"], "L-lines": ["grid-lines"],
  "L-bus": ["grid-bus", "grid-bus-label"], "L-pjm": ["pjm-queue", "pjm-bus-est"],
  "L-gas": ["gas-lines", "gas-pts"], "L-terr": ["terr-fill"],
  "L-padus": ["env-padus"], "L-bonusgeo": ["env-bonus"], "L-nonatt": ["env-nonatt"],
  "L-dc": ["fac-dc"], "L-fac": ["fac-gen"], "L-log": ["log-lines", "log-lines-rail"] };
function syncLayers() {
  if (!map.getLayer("county-fill")) return;
  for (const [box, ids] of Object.entries(LAYER_MAP))
    for (const id of ids) if (map.getLayer(id))
      map.setLayoutProperty(id, "visibility", $(box).checked ? "visible" : "none");
  const showP = $("L-parcels").checked;
  for (const fips of state.loaded.keys())
    for (const suf of ["fill", "line"])
      map.setLayoutProperty(`sites-${fips}-${suf}`, "visibility", showP ? "visible" : "none");
  if (map.getLayer("cand-line"))
    map.setLayoutProperty("cand-line", "visibility", $("f-cand").checked ? "visible" : "none");
}
for (const id of [...Object.keys(LAYER_MAP), "L-parcels"]) $(id).addEventListener("change", syncLayers);

/* ---------- the four part-presets (the dashboard's original pages) ----------
 * Each sets the county shading + the layer defaults for that analysis; every layer
 * stays user-toggleable afterwards — a preset frames the page, it never locks it. */
const PRESETS = {
  land: { metric: "class_union",
    layers: { "L-parcels": 1, "L-subs": 0, "L-lines": 0, "L-bus": 0, "L-pjm": 0, "L-gas": 0,
              "L-terr": 0, "L-padus": 0, "L-bonusgeo": 0, "L-nonatt": 0 } },
  grid: { metric: "queue_active_mw",
    layers: { "L-parcels": 1, "L-subs": 1, "L-lines": 1, "L-bus": 1, "L-pjm": 1, "L-gas": 1,
              "L-terr": 1, "L-padus": 0, "L-bonusgeo": 0, "L-nonatt": 0, "L-dc": 1, "L-fac": 1 } },
  env: { metric: "class_union",
    layers: { "L-parcels": 1, "L-subs": 0, "L-lines": 0, "L-bus": 0, "L-pjm": 0, "L-gas": 0,
              "L-terr": 0, "L-padus": 1, "L-bonusgeo": 1, "L-nonatt": 1 } },
  sentiment: { metric: "opposition_intensity",
    layers: { "L-parcels": 0, "L-subs": 0, "L-lines": 0, "L-bus": 0, "L-pjm": 0, "L-gas": 0,
              "L-terr": 0, "L-padus": 0, "L-bonusgeo": 0, "L-nonatt": 0 } },
};
document.querySelectorAll("#presets button").forEach((b) => b.onclick = () => {
  const pr = PRESETS[b.dataset.p]; if (!pr) return;
  document.querySelectorAll("#presets button").forEach((x) => x.classList.toggle("active", x === b));
  for (const [id, v] of Object.entries(pr.layers)) {
    const el = $(id); if (el) el.checked = !!v;
  }
  $("county-metric").value = pr.metric;
  if (map.getLayer("county-fill"))
    map.setPaintProperty("county-fill", "fill-color", countyPaint(pr.metric));
  syncLayers(); applyFilters();
});

/* ---------- parcels ---------- */
const FILL_COLOR = ["case", ["==", ["get", "has_si_signal"], true], "#d97706",
  ["==", ["get", "occ_group"], "ci"], "#2563eb",
  ["==", ["get", "occ_group"], "agriculture"], "#059669", "#64748b"];
function enrichDistances(feats) {
  for (const ft of feats) {
    const [lon, lat] = repPt(ft.geometry);
    let best = null;
    for (const s of binNear(state.subBins, lon, lat)) {
      const d = havM(lat, lon, s.lat, s.lon);
      if (!best || d < best.d) best = { d, s };
    }
    if (best) { ft.properties._dsub_mi = +(best.d / MI).toFixed(2); ft.properties._dsub_kv = best.s.kv; ft.properties._dsub_name = best.s.name; }
    let bl = null;
    for (const v of binNear(state.lineBins, lon, lat)) {
      const d = havM(lat, lon, v.lat, v.lon);
      if (!bl || d < bl.d) bl = { d, v };
    }
    if (bl) { ft.properties._dline_mi = +(bl.d / MI).toFixed(2); ft.properties._dline_kv = bl.v.kv; }
    let bp = null;
    for (const q of state.poiList) {
      const d = havM(lat, lon, q.lat, q.lon);
      if (!bp || d < bp.d) bp = { d, q };
    }
    if (bp) { ft.properties._dpoi_mi = +(bp.d / MI).toFixed(1); ft.properties._dpoi_name = bp.q.name; ft.properties._dpoi_median = bp.q.median; }
  }
}
function addCountyLayers(fips, fc) {
  const src = `sites-${fips}`;
  if (map.getSource(src)) return;
  map.addSource(src, { type: "geojson", data: fc });
  map.addLayer({ id: `${src}-fill`, type: "fill", source: src, minzoom: PARCEL_ZOOM,
    layout: { visibility: $("L-parcels").checked ? "visible" : "none" },
    paint: { "fill-color": FILL_COLOR, "fill-opacity": 0.45 } }, "grid-lines");
  map.addLayer({ id: `${src}-line`, type: "line", source: src, minzoom: PARCEL_ZOOM,
    layout: { visibility: $("L-parcels").checked ? "visible" : "none" },
    paint: { "line-color": "#333", "line-width": 0.6 } }, "grid-lines");
  map.on("click", `${src}-fill`, (e) => { if (!state.measure.on) openParcelEvidence(e.features[0].properties, fips); });
  map.on("mousemove", `${src}-fill`, (e) => showTip(e, tipText(e.features[0].properties)));
  map.on("mouseleave", `${src}-fill`, hideTip);
}
function countiesInView() {
  const b = map.getBounds();
  return Object.entries(state.countyBbox)
    .filter(([, [w, s, e, n]]) => b.getWest() < e && b.getEast() > w && b.getSouth() < n && b.getNorth() > s)
    .map(([f]) => f);
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
  if (p.parcel_key) return `${p.occ_group || ""} · ${Number(p.parcel_acres || 0).toFixed(1)} ac · fits ${Math.floor(acreageOf(p).acres * V("f-density"))} MW${p.has_si_signal ? " · SI" : ""}${p._dsub_mi != null ? ` · sub ${p._dsub_mi} mi` : ""}`;
  if (p.layer === "bus_poi") return `${p.poi_name} · median ${fmt(p.median_mw)} MW / best ${fmt(p.best_mw)} MW`;
  if (p.layer === "substation") return `${p.substation_name || "substation"} · ${p.min_kv ?? "?"}–${p.max_kv ?? "?"} kV`;
  if (p.layer === "line") return `${p.voltage || "?"} kV line · ${p.owner || ""}`;
  if (p.layer === "queue_point") return "PJM queue point (published coords)";
  if (p.layer === "bus_candidate") return `PJM bus ${p.bus_number} · load headroom ${p.withdrawal_mw != null ? Math.round(p.withdrawal_mw) + " MW" : "—"} · ESTIMATE loc (${p.match_confidence})`;
  if (p.candidate_signal) return `CANDIDATE ${p.candidate_signal} · ${p.occ_group || ""}`;
  if (p.layer === "gas") return `gas pipeline · ${p.operator || ""}`;
  if (p.layer === "dc") return `EXISTING DC: ${p.name || ""} (${p.src})`;
  if (["plant", "plant_hifld", "solar", "wind"].includes(p.layer)) return `${p.layer}: ${p.name || p.plant_name || ""}`;
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
    `substations without published coords stay off-map but in counts · MISO values are DPP-2021 study results (worst/median/best shown together) · ` +
    `PJM bus locations marked ESTIMATE render as hollow red rings · grid distances are to the nearest mapped feature (a floor, not a guarantee) · ` +
    `headroom DIRECTION matters: PJM buses carry LOAD (withdrawal) headroom — the DC question; MISO's public viewer is INJECTION-only, so its 300MW numbers answer the generator question and a MISO load-direction source is an open acquisition lane.`;
}
function renderDenominator() {
  if (state.measure.on) return;
  const el = $("denominator"), btn = $("export-csv");
  if (map.getZoom() < PARCEL_ZOOM) {
    el.innerHTML = `County view — shading counts <b>all ${fmt(state.summary?.totals.all_parcels)}</b> parcels. Zoom to z≥${PARCEL_ZOOM} for parcels; layers stay on at every zoom.`;
    btn.disabled = true; return;
  }
  const inView = countiesInView();
  let classTotal = 0, match = 0, loaded = 0;
  for (const f of state.counties.features)
    if (inView.includes(f.properties.fips)) classTotal += f.properties.class_union;
  for (const fips of inView) {
    const feats = state.loaded.get(fips); if (!feats) continue;
    loaded++;
    if (countyOk(fips)) for (const ft of feats) if (jsMatches(ft.properties)) match++;
  }
  el.innerHTML = `<b>${fmt(match)}</b> sites pass the screener, of <b>${fmt(classTotal)}</b> class sites in view (${loaded}/${inView.length} counties loaded${state.loading.size ? "…" : ""}).<br><span class="hint">County shading counts every parcel — nothing is dropped by the screen.</span>`;
  btn.disabled = match === 0;
}

/* ---------- evidence panels ---------- */
const panel = $("evidence");
$("ev-close").onclick = () => panel.classList.add("hidden");
$("ev-print").onclick = () => window.print(); // print stylesheet isolates the evidence panel as a dossier
function prov(t) {
  const p = state.provenance[t];
  return p ? `source: indiana_app.${t} · rows ${fmt(p.n_rows)} · built ${String(p.built_at).slice(0, 16)}Z` : `source: ${t}`;
}
function row(k, v) {
  const val = (v === null || v === undefined || v === "") ? `<span class="cannot">cannot assess</span>`
    : (typeof v === "number" ? fmt(v) : String(v));
  return `<tr><td>${k}</td><td>${val}</td></tr>`;
}
function show(title, html, starKey) {
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
function openParcelEvidence(p, fips) {
  const a = (x) => x == null ? null : Number(x).toFixed(2);
  const c = state.ctx.by_fips[fips] || {};
  const density = V("f-density");
  const acr = acreageOf(p);
  show(`Parcel ${p.parcel_key}`, `
    <h3>Land & size (P3)</h3><table>
      ${row("class", p.occ_group)}${row("parcel acres", a(p.parcel_acres))}
      ${row("outdoor acres (EXACT: parcel − measured building intersection)", a(p.exact_outdoor_acres))}
      ${row("outdoor acres (approximate)", a(p.outdoor_acres))}
      ${row("building acres (exact)", a(p.exact_bldg_acres))}
      ${row("footprints intersecting this parcel", p.footprints_intersecting)}
      ${row("how outdoor space was measured", p.outdoor_acres_method)}
      ${row("screened on", `${acr.acres.toFixed(2)} ac — ${acr.basis}`)}
      ${row(`fits @ ${density} MW/acre (your setting)`, Math.floor(acr.acres * density) + " MW")}
      ${row("structures", p.structure_count)}${row("structure sqft", p.structure_sqft)}</table>
    ${acr.disputed ? `<div class="cannot">Sources disagree on this parcel's size: no building footprint
      intersects it, yet the exact-geometry figure (${Number(p.exact_outdoor_acres).toFixed(2)} ac) falls below
      the recorded parcel area (${Number(p.parcel_acres).toFixed(2)} ac). With nothing to subtract, the two should
      match. Screened on the recorded acreage; the exact figure is shown above unchanged so you can judge it.
      126 of 1,200,924 class-union parcels show this — see docs/HANDOFF.md.</div>` : ""}
    <div class="prov">${prov("in_sites")} · exact figures from mat_parcel_outdoor_exact (footprint∩parcel measured, shared buildings not double-counted) · density is your adjustable assumption, not an answer</div>
    <h3>Grid access (P2) — computed to nearest mapped feature</h3><table>
      ${row("nearest substation", p._dsub_name ? `${p._dsub_name} (${p._dsub_kv} kV) · ${p._dsub_mi} mi` : null)}
      ${row("nearest transmission line", p._dline_mi != null ? `${p._dline_kv} kV · ${p._dline_mi} mi (to nearest vertex)` : null)}
      ${row("nearest MISO POI", p._dpoi_name ? `${p._dpoi_name} · ${p._dpoi_mi} mi · median ${fmt(p._dpoi_median)} MW` : null)}</table>
    <div class="prov">${prov("in_substations")} · distances are floors against mapped features, not service guarantees</div>
    <h3>Seller intent (P1)</h3><table>
      ${row("carries SI signal", p.has_si_signal === true ? "yes" : (p.has_si_signal === false ? "no" : null))}
      ${row("signal types / events", p.si_signal_types != null ? `${p.si_signal_types} / ${p.si_signal_events}` : null)}
      ${row("signals", p.si_signals)}${row("last event", p.si_last_event_date)}</table>
    <div class="prov">${prov("in_si_signals")}</div>
    <h3>Environmental gates (P4)</h3><table>
      ${row("SFHA flood", p.sfha_flood === undefined ? null : (p.sfha_flood ? "YES — flag" : "clear (measured)"))}
      ${row("wetland on parcel", p.wetland_on_parcel === undefined ? null : (p.wetland_on_parcel ? "YES — flag" : "clear (measured)"))}
      ${row("protected land", p.protected_land === undefined ? null : (p.protected_land ? "YES — flag" : "clear (measured)"))}
      ${row("bonus credits", p.bonus_kinds === undefined ? null : (p.bonus_kinds || "none intersecting"))}</table>
    <div class="prov">${prov("in_site_gates")}</div>
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
function gridEv(p) {
  if (p.layer === "bus_poi") {
    show(`MISO POI: ${p.poi_name}`, `
      <h3>Bus identity</h3><table>
      ${row("bus number", p.bus_number)}${row("bus name", p.bus_name)}${row("kV", p.kv)}${row("area", p.area_name)}</table>
      <h3>Injection headroom at a 300 MW request (bounded re-harvest)</h3><table>
      ${row("available for a 300MW-class INJECTION", p.headroom300_mw != null ? `${fmt(Math.round(p.headroom300_mw))} MW` : null)}
      ${row("binding facility @300MW", p.binding_300)}</table>
      <div class="prov">${prov("in_bus_headroom_300")} · ⚠ this MISO viewer is INJECTION-only (generators); it cannot answer the data-centre LOAD question — PJM buses carry the withdrawal number; a MISO load-direction source is an open lane</div>
      <h3>Transfer capability at infinite request (study detail)</h3><table>
      ${row("worst across facilities (MW)", p.worst_mw)}${row("median (MW)", p.median_mw)}${row("best (MW)", p.best_mw)}
      ${row("monitored facilities", p.monitored_facilities)}${row("at zero", p.facilities_at_zero)}
      ${row("worst binding facility", p.worst_binding_facility)}${row("vintage", p.vintage)}</table>
      <div class="prov">${prov("in_bus_headroom_miso")} · probe ran at an effectively infinite request — read the three numbers together</div>`);
  } else if (p.layer === "substation") {
    show(`Substation: ${p.substation_name || "(unnamed)"}`, `
      <table>${row("kV range", `${p.min_kv ?? "—"}–${p.max_kv ?? "—"}`)}${row("county", p.county)}
      ${row("status", p.status)}${row("type", p.substation_type)}${row("lines", p.line_count)}${row("operator", p.operator)}</table>
      <div class="prov">${prov("in_substations")} (HIFLD + OSM, deduped)</div>`);
  } else {
    show("Transmission line", `
      <table>${row("owner", p.owner)}${row("voltage (kV)", p.voltage)}${row("class", p.volt_class)}
      ${row("status", p.status)}${row("from", p.sub_1)}${row("to", p.sub_2)}</table>
      <div class="prov">${prov("in_transmission_lines")} (HIFLD)</div>`);
  }
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
    show("Gas pipeline", `<table>${row("operator", p.operator)}${row("type", p.typepipe)}</table>
      <div class="prov">${prov("in_gas_pipelines")} · border design capacity in Market; daily availability is an open lane</div>`);
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
      ${row("current status", p.current_status)}${row("designation effective", p.designation_effective_date)}</table>
      <div class="prov">${prov("in_nonattainment")} · air-permitting gate for on-site generation</div>`);
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
async function openCountyEvidence(p) {
  const c = state.ctx.by_fips[p.fips] || {};
  let html = `
    <h3>County rollup — 100% of parcels counted</h3><table>
      ${row("parcels", p.parcels)}${row("with a building", p.with_building)}${row("strict C&I", p.ci)}
      ${row("fits ≥25 MW @ 4/acre", p.ge25mw)}${row("carries SI signal", p.si_sites)}
      ${row("MW potential (sum)", p.mw_potential_at_4)}</table>
    <div class="prov">${prov("in_county_rollup")}</div>
    <h3>Grid & queue</h3><table>
      ${row("queue projects", c.queue?.projects)}${row("active MW", c.queue?.active_mw)}
      ${row("withdrawn (a signal, kept)", c.queue?.withdrawn_projects)}${row("utilities serving", c.eia861?.utilities)}</table>
    <h3>Gates</h3><table>
      ${row("wetlands", c.wetlands ? `${fmt(c.wetlands.wetland_features)} / ${fmt(c.wetlands.wetland_acres)} ac` : null)}
      ${row("flood features (SFHA)", c.flood ? `${fmt(c.flood.flood_features)} (${fmt(c.flood.sfha_features)})` : null)}
      ${row("fibre-served / total locations", c.fibre ? `${fmt(c.fibre.fiber_locations)} / ${fmt(c.fibre.locations)}` : null)}
      ${row("business units: fiber ≥100/20 · gig (FCC)", c.fcc ? `${fmt(c.fcc.fiber_units)} · ${fmt(c.fcc.gig_units)} of ${fmt(c.fcc.units)}` : null)}
      ${row("mobile coverage 5G · 4G (area %)", c.fcc_mobile ? `${Math.round((c.fcc_mobile.pct_5g || 0) * 100)}% · ${Math.round((c.fcc_mobile.pct_4g || 0) * 100)}%` : null)}
      ${row("seismic design category", c.seismic?.sdc)}</table>
    <h3>Community posture</h3><table>
      ${row("posture", c.posture?.posture)}${row("opposition intensity", c.posture?.opposition_intensity)}
      ${row("local restriction", c.posture?.has_local_restriction)}${row("moratoriums", c.posture?.local_moratoriums)}</table>`;
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
function toggleShortlist(key, title) {
  const i = state.shortlist.findIndex((s) => s.key === key);
  if (i >= 0) state.shortlist.splice(i, 1);
  else state.shortlist.push({ key, title, added: new Date().toISOString().slice(0, 10) });
  localStorage.setItem("in_shortlist", JSON.stringify(state.shortlist));
  renderShortlistCount();
  $("ev-star").classList.toggle("starred", state.shortlist.some((s) => s.key === key));
}
$("btn-shortlist").onclick = () => {
  const rows_ = state.shortlist.map((s) => `<tr><td>${s.title}</td><td>${s.added}
    <button class="unstar" data-k="${s.key}">remove</button></td></tr>`).join("");
  show(`Shortlist (${state.shortlist.length})`, state.shortlist.length
    ? `<table>${rows_}</table><div class="hint">Stored in this browser. Star parcels from their evidence panel; export via the CSV button with your screen applied.</div>`
    : `<div class="hint">Empty — open any parcel's evidence panel and press ★.</div>`);
  document.querySelectorAll(".unstar").forEach((b) => b.onclick = () => { toggleShortlist(b.dataset.k, ""); $("btn-shortlist").click(); });
};

/* ---------- top panels ---------- */
$("btn-market").onclick = async () => {
  if (!state.summary) return;
  if (!state.market) state.market = await fetchGz("data/market.json.gz");
  const m = state.market;
  const recent = m.monthly.slice(-120);
  const max = Math.max(...recent.map((r) => r.gross_load_mwh || 0));
  const pts = recent.map((r, i) => `${(i / (recent.length - 1) * 300).toFixed(1)},${(80 - (r.gross_load_mwh || 0) / max * 75).toFixed(1)}`).join(" ");
  const gas = (m.gas_state_capacity || []).filter((r) => r.year >= 2015).sort((a, b) => b.capacity_mmcfd - a.capacity_mmcfd).slice(0, 25);
  show("Market (P6)", `
    <h3>CEMS gross generation, Indiana plants (10y monthly)</h3>
    <svg viewBox="0 0 300 84" style="width:100%;background:#f8fafc;border:1px solid #e3e6ec;border-radius:6px">
      <polyline points="${pts}" fill="none" stroke="#0f172a" stroke-width="1.2"/></svg>
    <div class="prov">${prov("in_cems_monthly")} · ${m.monthly.length} months held</div>
    <h3>Top plants</h3>
    <table>${m.top_plants.slice(0, 10).map((r) => row(`plant ${r.plant_id_epa}`, `${fmt(r.gross_load_mwh)} MWh · thru ${r.last_month}`)).join("")}</table>
    <h3>Gas capacity at Indiana borders (EIA, design)</h3>
    <table>${gas.map((r) => row(`${r.pipeline || ""} ${r.year}`, `${r.state_from}→${r.state_to}: ${fmt(r.capacity_mmcfd)} MMcf/d`)).join("")}</table>
    <div class="prov">${prov("in_gas_state_capacity")} · daily operational availability (EBB) is an open lane</div>
    ${m.state_demand ? `<h3>Indiana statewide demand (FERC-714, monthly MWh)</h3>
    <svg viewBox="0 0 300 84" style="width:100%;background:#f8fafc;border:1px solid #e3e6ec;border-radius:6px">
      <polyline points="${(() => { const s = m.state_demand.slice(-120); const mx = Math.max(...s.map((r) => r.demand_mwh || 0)); return s.map((r, i) => `${(i / (s.length - 1) * 300).toFixed(1)},${(80 - (r.demand_mwh || 0) / mx * 75).toFixed(1)}`).join(" "); })()}" fill="none" stroke="#b45309" stroke-width="1.2"/></svg>
    <div class="prov">${prov("in_ferc714_state_demand")} · ${m.state_demand.length} months held</div>` : ""}
    <h3>Utility reliability (EIA-861 SAIDI/SAIFI)</h3>
    <table>${(m.reliability || []).filter((r) => r.saidi_minutes_per_year != null).slice(0, 15).map((r) =>
      row(`${String(r.utility_name).slice(0, 34)} ${r.data_year}`,
      `SAIDI ${fmt(Math.round(r.saidi_minutes_per_year))} min/yr · SAIFI ${r.saifi_times_per_year ?? "—"} · ${fmt(r.number_of_customers)} customers`)).join("")}</table>
    <div class="prov">${prov("in_eia861_reliability")} · outage risk per utility — a screening metric</div>
    <h3>Indiana C&I tariffs (URDB) — ${fmt((m.tariffs || []).length)}</h3>
    <table>${(m.tariffs || []).slice(0, 30).map((r) => row(String(r.utility).slice(0, 38),
      `${r.name || ""} · ${r.sector || ""}${r.has_demand_charge ? " · demand-charged" : ""}${r.energy_rate_max_usd_kwh ? " · ≤$" + r.energy_rate_max_usd_kwh + "/kWh" : ""}`)).join("")}</table>
    <div class="prov">${prov("in_urdb_rates")} · name-matched floor; full tariff math is the rate-engine milestone</div>`);
};
$("btn-pipeline").onclick = async () => {
  if (!state.summary) return;
  if (!state.pipeline) state.pipeline = await fetchGz("data/pipeline.json.gz");
  const pl = state.pipeline;
  const plans = pl.grid_plans.filter((r) => r.row_type === "project").slice(0, 60);
  show("Future capacity — where upgrades are coming", `
    <h3>State grid plans (TDSIC/IRP) — ${fmt(pl.grid_plans.filter((r) => r.row_type === "project").length)} projects</h3>
    <table>${plans.map((r) => row(`${r.utility || ""} ${r.in_service_year || ""}`,
      `${r.project_name || r.location_text || ""} ${r.voltage_kv ? r.voltage_kv + " kV" : ""} ${r.cost_usd_m ? "$" + r.cost_usd_m + "M" : ""}`)).join("")}</table>
    <div class="prov">${prov("in_grid_plans")} · named endpoints/counties, never geocoded</div>
    <h3>RTO expansion (MTEP + RTEP) — ${fmt(pl.rto_expansion.length)} Indiana-naming</h3>
    <table>${pl.rto_expansion.slice(0, 60).map((r) => row(`${r.rto || r.source || ""} ${r.in_service_year || r.isd || ""}`,
      `${r.project_name || r.upgrade_name || r.description || ""}`)).join("")}</table>
    <div class="prov">${prov("in_rto_expansion")}</div>
    <h3>Queue projects by county — ${fmt(pl.queue_projects.length)}</h3>
    <table>${pl.queue_projects.slice(0, 40).map((r) => row(`${r.county || "?"} · ${r.status || ""}`,
      `${r.project_name || r.entity || ""} ${r.capacity_mw ? fmt(r.capacity_mw) + " MW" : ""} ${r.resource_type || ""}`)).join("")}</table>
    <div class="prov">${prov("in_queue")} · withdrawn rows kept deliberately (a siting signal)</div>`);
};
document.getElementById("btn-acq").onclick = () => {
  if (!state.summary) return;
  const ACQ_COUNTY = { indy: "Marion", evansville: "Vanderburgh", southbend: "St. Joseph", state: "statewide", refresh: "statewide refresh" };
  const rows_ = state.summary.provenance
    .filter((p) => p.table_name.startsWith("in_si_") && !["in_si_signals", "in_si_candidates"].includes(p.table_name))
    .map((p) => {
      const key = Object.keys(ACQ_COUNTY).find((k) => p.table_name.includes(k)) || "";
      return `<tr><td>${p.table_name.replace(/^in_si_(refresh_)?/, "").replace(/_/g, " ")}<br><span class="hint">${ACQ_COUNTY[key] || ""} · ${String(p.built_at).slice(0, 10)}</span></td><td>${fmt(p.n_rows)} rows</td></tr>`;
    }).join("");
  show("Staged SI acquisitions", `
    <div class="hint">New Indiana sources awaiting the human subject test (auto-wiring on a name is a documented defect class). Approved ones graduate to candidate layers like D21.</div>
    <table>${rows_}</table><div class="prov">source: indiana_app._registry</div>`);
};
const FEATURE_HOME = {
  in_sites: "Parcels + screener + evidence", in_si_signals: "parcel evidence (SI)",
  in_sites_county: "county spine", in_county_rollup: "county layer + evidence",
  in_substations: "Substations layer + distance screen", in_transmission_lines: "Lines layer + distance screen",
  in_bus_headroom_miso: "MISO bus layer (labeled MW)", in_miso_poi_identity: "feeds bus layer",
  in_pjm_bus_locations_candidate: "PJM estimate rings", in_pjm_gis_queues: "PJM queue points",
  in_queue: "Future-capacity panel + county evidence", in_queue_counties: "county evidence",
  in_grid_plans: "Future-capacity panel", in_rto_expansion: "Future-capacity panel",
  in_pjm_nucra_costs: "Future-capacity panel", in_pjm_rtep_upgrades: "Future-capacity source",
  in_pjm_rtep_upgrade_details: "DEFERRED: upgrade drill-down", in_pjm_rtep_cost_allocations: "DEFERRED: upgrade drill-down",
  in_pjm_queuescope_aep: "DEFERRED: needs bus locations", in_padus: "Protected-land layer",
  in_bonus_geo: "Bonus layer + parcel gate", in_wetlands: "county gates + parcel gate",
  in_flood: "county gates + parcel gate", in_water: "DEFERRED: tile pipeline",
  in_fcc_bdc: "county gates via in_county_fibre", in_county_fibre: "county evidence",
  in_county_flood: "county evidence", in_county_wetlands: "county evidence",
  in_iurc_dockets: "county receipts", in_news_dc: "county receipts", in_dc_actions: "county receipts",
  in_ordinances_dc: "county receipts", in_cems_monthly: "Market panel",
  in_gas_pipelines: "Gas layer", in_gas_compressor_stations: "Gas layer", in_gas_storage: "Gas layer",
  in_gas_state_capacity: "Market panel", in_gas_processing_plants: "measured zero in Indiana — registered evidence",
  in_gas_lng_terminals: "measured zero in Indiana — registered evidence",
  in_site_gates: "parcel gates + screener", in_miso_poi: "SUPERSEDED by in_bus_headroom_miso",
  in_territories: "Territories layer", in_seismic: "county evidence",
  in_eia861_territory: "county evidence", in_urdb_rates: "Market panel",
  in_parcel_attrs: "BLOCKED-UPSTREAM: IN slice 100% NULL — question filed",
  in_county_water: "DEFERRED: tile pipeline", in_si_candidates: "Candidate overlay (dashed purple)",
  in_nonattainment: "Nonattainment layer + evidence", in_eia861_reliability: "Market panel (reliability)",
  in_ferc714_state_demand: "Market panel (state demand chart)",
  in_nhd_waterbody: "WIRE-NEXT: water gate complement (county agg + tiles)",
  in_spc_severe_events: "WIRE-NEXT: P4 severe-weather county stats",
  in_faa_obstacles: "WIRE-NEXT: P4 obstacle-proximity gate",
  in_echo_cwa_facilities: "WIRE-NEXT: water-permit facilities layer",
  in_utility_tariff_riders: "Market panel (riders — next)", in_dc_eei_tariffs: "Market panel (EEI benchmark — next)",
  in_econ_gjf_megadeals: "county evidence (megadeals — next)", in_state_irp_catalog: "Future-capacity panel (IRP refs)",
  in_gov_auction_gsa: "Acquisitions (A2 extension)", in_ustp_ch7_tfr: "Acquisitions (D6 extension)",
  in_queue_miso: "FLAG: diff vs interconnection_queue before wiring",
  in_nfirs_basicincident_2024: "Acquisitions (D16 vintage, subject-read pending)",
  in_nfirs_incidentaddress_2024: "joins in_nfirs_basicincident_2024",
  in_nfirs_basicincident_2023: "Acquisitions (D16 vintage)", in_nfirs_incidentaddress_2023: "joins 2023",
  in_nfirs_basicincident_2022: "Acquisitions (D16 vintage)", in_nfirs_incidentaddress_2022: "joins 2022",
  in_miso_poi_300mw: "Grid — bounded 300MW harvest (facility grain)",
  in_bus_headroom_300: "MISO bus panel (injection @300MW headline)",
  in_pjm_bus_withdrawal: "PJM bus panel + tooltip (LOAD headroom headline)",
  in_data_centers_datacentermap: "PAGE-NEXT: existing-DC layer (157)", in_power_plants: "PAGE-NEXT: plants layer",
  in_solar_pv_facilities: "PAGE-NEXT: solar layer", in_lbnl_interconnection_costs: "Future-capacity (cost benchmarks)",
  in_fema_nri_counties: "county evidence (risk index)", in_qcew_county_labor: "county evidence (workforce)",
  in_acs_county: "county evidence", in_water_use: "county evidence (water use)",
  in_solar_potential: "county evidence", in_usa_structures_county: "county evidence",
  in_cbp_county_industry: "county evidence (industry mix)", in_workforce_ipeds_directory: "county evidence",
  in_eia861_sales: "Market (retail sales)", in_eia861_sales_ult_cust: "Market (retail sales)",
  in_fsis_establishments: "context layer (large occupiers)", in_fsis_establishments_inactive: "Acquisitions (closure signal)",
  in_candidate_sites_colleges: "upload-door demo set", in_data_centers_peeringdb: "PAGE-NEXT: connectivity layer",
  in_peeringdb_facilities: "PAGE-NEXT: connectivity layer", in_land_faa_sua: "PAGE-NEXT: airspace gate",
  in_tribal_land: "PAGE-NEXT: land-status gate", in_sec_cik_registrant_state: "Acquisitions (D23 support)",
  in_commission_posture: "Sentiment context", in_dc_docket_tracker: "Sentiment context",
  in_balancing_authority_areas: "Grid context", in_groundwater_sites: "water gate context",
  in_puc_state_access_ledger: "Regulatory-preview context",
  in_data_centers_all: "⭐ Existing-DC layer + Grid page", in_data_centers: "feeds in_data_centers_all",
  in_fcc_bdc_fixed_summary_by_geography: "county fibre detail (page-next)",
  in_fcc_bdc_mobile_summary: "county mobile coverage (page-next)",
  in_fcc_bdc_provider_summary: "provider detail (page-next)",
  in_elec_power_operational: "Market page (operations series — next)",
  in_operating_generators: "Facilities layer source (860M live)",
  in_ghgrp_emissions: "emitter detail (joins facilities)", in_workforce_ipeds_cs_eng: "county workforce depth",
  in_railroads: "logistics layer (page-next)", in_roads_primary: "logistics layer (page-next)",
  in_roads_secondary: "logistics layer (page-next)", in_zctas: "geography spine",
  in_land_military_bases: "P4 gate layer (page-next)", in_water_aqueduct: "water-stress context",
  in_drought_by_state: "water context (Market)", in_nrc_reactors: "measured zero in Indiana — registered",
  in_data_centers_baxtel: "feeds in_data_centers_all", in_data_centers_cloudscene: "FLAG: state vocabulary unread",
  in_si_d11_entity_dissolution: "Acquisitions (D11 first IN rows — subject-check pending)",
  in_gov_surplus_nces: "Acquisitions (A2 school surplus)", in_si_d25_stb_abandonment_state: "Acquisitions (D25 dent)",
  in_si_d27_ucc_lapse_v2: "Acquisitions (D27 dent)", in_txexp_miso_mtep_appendix_a_status: "Future-capacity source",
  in_nfirs_fireincident_2022: "Acquisitions (D16 vintage)",
  in_gas_capacity_texas_gas: "Gas OAC (Market page next)", in_gas_capacity_vector: "Gas OAC",
  in_gas_capacity_midwestern: "Gas OAC", in_gas_capacity_panhandle_eastern: "Gas OAC (county-plottable)",
  in_gas_capacity_trunkline: "Gas OAC (county-plottable)", in_gas_capacity_ngpl: "Gas OAC",
  in_gas_capacity_anr: "Gas OAC", in_gas_capacity_northern_border: "Gas OAC",
  in_gas_capacity_crossroads: "Gas OAC",
};
$("btn-inventory").onclick = () => {
  if (!state.summary) return;
  const rows_ = state.summary.provenance.map((p) => {
    let home = FEATURE_HOME[p.table_name];
    if (!home) home = p.table_name.startsWith("in_si_refresh_") ? "Acquisitions panel (freshness refresh)"
      : (p.table_name.startsWith("in_si_") ? "Acquisitions panel (awaiting subject test)" : "STAGED");
    const cls = /DEFERRED|STAGED|BLOCKED|awaiting/.test(home) ? ' class="cannot"' : "";
    return `<tr><td>${p.table_name}<br><span class="hint">${fmt(p.n_rows)} rows · ${String(p.built_at).slice(0, 10)}</span></td><td${cls}>${home}</td></tr>`;
  }).join("");
  show("Data inventory — every table has a home or a stated waiver", `<table>${rows_}</table>`);
};

/* ---------- upload door: user's own sites through the same pipeline ---------- */
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
$("upload").addEventListener("change", async (e) => {
  const file = e.target.files[0]; if (!file) return;
  const recs = parseCsv(await file.text());
  const latK = Object.keys(recs[0] || {}).find((k) => ["lat", "latitude", "y"].includes(k));
  const lonK = Object.keys(recs[0] || {}).find((k) => ["lon", "lng", "longitude", "x"].includes(k));
  if (!latK || !lonK) {
    $("upload-status").innerHTML = `<span class="cannot">No lat/lon columns found (headers: ${Object.keys(recs[0] || {}).slice(0, 8).join(", ")}). Address-only lists need coordinates — centreline geocoding is refused by project rule.</span>`;
    return;
  }
  let placed = 0, unplaced = 0, outside = 0;
  const feats = [];
  state.uploaded = recs.map((r, i) => {
    const lat = parseFloat(r[latK]), lon = parseFloat(r[lonK]);
    const row_ = { ...r, _row: i + 1 };
    if (!isFinite(lat) || !isFinite(lon)) { row_._status = "cannot-place (no coords)"; unplaced++; return row_; }
    const cty = countyOf(lon, lat);
    if (!cty) { row_._status = "outside Indiana"; outside++; return row_; }
    const c = state.ctx.by_fips[cty.fips] || {};
    let best = null;
    for (const s of binNear(state.subBins, lon, lat)) {
      const d = havM(lat, lon, s.lat, s.lon); if (!best || d < best.d) best = { d, s };
    }
    let bp = null;
    for (const q of state.poiList) {
      const d = havM(lat, lon, q.lat, q.lon); if (!bp || d < bp.d) bp = { d, q };
    }
    Object.assign(row_, {
      _status: "placed", _county: cty.county_name,
      _sub_mi: best ? +(best.d / MI).toFixed(2) : null, _sub_name: best?.s.name, _sub_kv: best?.s.kv,
      _poi_mi: bp ? +(bp.d / MI).toFixed(1) : null, _poi_median_mw: bp?.q.median,
      _county_opposition: c.posture?.opposition_intensity ?? null,
      _county_restriction: c.posture?.has_local_restriction ?? null,
      _county_seismic: c.seismic?.sdc ?? null,
      _county_fiber_locs: c.fibre?.fiber_locations ?? null,
      _county_queue_mw: c.queue?.active_mw ?? null,
    });
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
    map.on("click", "uploaded-pts", (e2) => {
      const p = e2.features[0].properties;
      const rows_ = Object.entries(p).filter(([k]) => k !== "layer").slice(0, 16)
        .map(([k, v]) => row(k.replace(/^_/, ""), v)).join("");
      show(`Your site (row ${p._row})`, `<table>${rows_}</table>
        <div class="prov">your upload · enriched client-side against the same layers as the feed — upload parity is a scope commitment; nothing leaves the browser</div>`);
    });
    map.on("mousemove", "uploaded-pts", (e2) => showTip(e2, `your site · ${e2.features[0].properties._county || ""} · sub ${e2.features[0].properties._sub_mi ?? "?"} mi`));
    map.on("mouseleave", "uploaded-pts", hideTip);
  }
  $("upload-status").innerHTML = `<b>${placed}</b> placed · ${outside} outside Indiana · <b>${unplaced}</b> cannot-place (kept, listed in export) — green markers.`;
  $("upload-export").disabled = $("upload-clear").disabled = false;
});
$("upload-export").onclick = () => {
  if (!state.uploaded.length) return;
  const cols = [...new Set(state.uploaded.flatMap((r) => Object.keys(r)))];
  const esc = (v) => v == null ? "" : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v);
  const csv = [cols.join(","), ...state.uploaded.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = "your_sites_enriched.csv"; a.click();
};
$("upload-clear").onclick = () => {
  state.uploaded = [];
  if (map.getSource("uploaded")) map.getSource("uploaded").setData({ type: "FeatureCollection", features: [] });
  $("upload-status").textContent = ""; $("upload-export").disabled = $("upload-clear").disabled = true;
};

/* ---------- CSV export ---------- */
$("export-csv").onclick = () => {
  const rows = [];
  for (const fips of countiesInView()) {
    const feats = state.loaded.get(fips); if (!feats || !countyOk(fips)) continue;
    for (const ft of feats) if (jsMatches(ft.properties)) rows.push(ft.properties);
  }
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
