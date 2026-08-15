/* Indiana Siting Intelligence — one map, three presets (Land / Grid / Sentiment).
 * County aggregates carry 100% of parcels at every zoom; class-union parcels render
 * individually (exact geometry) at z>=10. Every number traces to state_summary provenance;
 * cannot-assess is shown, never zeroed; estimates never style as published truth.
 */
"use strict";

const PARCEL_ZOOM = 10;
const state = {
  summary: null, provenance: {}, counties: null, countyBbox: {},
  loaded: new Map(), loading: new Set(),
  ctx: null, receipts: null, grid: null, preset: "land",
};

async function fetchGz(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  const ds = res.body.pipeThrough(new DecompressionStream("gzip"));
  return new Response(ds).json();
}
function bboxOf(geom) {
  let w = 180, s = 90, e = -180, n = -90;
  const walk = (c) => { if (typeof c[0] === "number") { w = Math.min(w, c[0]); e = Math.max(e, c[0]); s = Math.min(s, c[1]); n = Math.max(n, c[1]); } else c.forEach(walk); };
  walk(geom.coordinates); return [w, s, e, n];
}
const fmt = (n) => n == null ? "—" : Number(n).toLocaleString("en-US");

const map = new maplibregl.Map({
  container: "map", center: [-86.28, 39.85], zoom: 6.6,
  style: { version: 8, sources: { basemap: { type: "raster",
    tiles: ["https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png"], tileSize: 256,
    attribution: "© OpenStreetMap contributors © CARTO" } },
    layers: [{ id: "basemap", type: "raster", source: "basemap" }] },
});
map.addControl(new maplibregl.NavigationControl(), "top-right");

map.on("load", async () => {
  state.summary = await (await fetch("data/state_summary.json")).json();
  for (const p of state.summary.provenance) state.provenance[p.table_name] = p;
  state.ctx = await (await fetch("data/county_context.json")).json();
  renderStatebar(); renderLedger();

  state.counties = await fetchGz("data/counties.geojson.gz");
  for (const f of state.counties.features) {
    state.countyBbox[f.properties.fips] = bboxOf(f.geometry);
    const c = state.ctx.by_fips[f.properties.fips];
    if (c) {
      f.properties.opposition_intensity = c.posture?.opposition_intensity ?? null;
      f.properties.posture = c.posture?.posture ?? null;
      f.properties.queue_active_mw = c.queue?.active_mw ?? null;
    }
  }
  map.addSource("counties", { type: "geojson", data: state.counties });
  map.addLayer({ id: "county-fill", type: "fill", source: "counties",
    paint: { "fill-color": countyPaint("land"),
             "fill-opacity": ["interpolate", ["linear"], ["zoom"], 8.5, 0.85, 10, 0.25] } });
  map.addLayer({ id: "county-line", type: "line", source: "counties",
    paint: { "line-color": "#7d8aa0", "line-width": 0.7 } });
  map.on("click", "county-fill", (e) => {
    if (state.preset === "land" && map.getZoom() >= PARCEL_ZOOM) return;
    openCountyEvidence(e.features[0].properties);
  });
  map.on("moveend", maybeLoadCounties);

  // grid preset data (small; load once, filter by layer prop)
  state.grid = await fetchGz("data/grid.geojson.gz");
  map.addSource("grid", { type: "geojson", data: state.grid });
  map.addLayer({ id: "grid-lines", type: "line", source: "grid",
    filter: ["==", ["get", "layer"], "line"], layout: { visibility: "none" },
    paint: { "line-color": ["step", ["to-number", ["get", "voltage"], 0], "#9aa5b5", 100, "#4a7bd0", 300, "#7c3aed"],
             "line-width": ["step", ["to-number", ["get", "voltage"], 0], 1, 100, 1.6, 300, 2.4] } });
  map.addLayer({ id: "grid-subs", type: "circle", source: "grid",
    filter: ["==", ["get", "layer"], "substation"], layout: { visibility: "none" },
    paint: { "circle-radius": ["interpolate", ["linear"], ["to-number", ["get", "max_kv"], 0], 0, 2.2, 138, 4, 345, 6.5],
             "circle-color": "#334155", "circle-opacity": 0.75 } });
  map.addLayer({ id: "grid-bus", type: "circle", source: "grid",
    filter: ["==", ["get", "layer"], "bus_poi"], layout: { visibility: "none" },
    paint: { "circle-radius": ["interpolate", ["linear"], ["to-number", ["get", "median_mw"], 0], 0, 3.5, 2000, 8, 8000, 12],
             "circle-color": "#d97706", "circle-stroke-color": "#7c2d12", "circle-stroke-width": 1, "circle-opacity": 0.85 } });
  for (const id of ["grid-bus", "grid-subs", "grid-lines"]) {
    map.on("click", id, (e) => openGridEvidence(e.features[0].properties));
    map.on("mouseenter", id, () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", id, () => (map.getCanvas().style.cursor = ""));
  }
  // environmental overlays (P4) + PJM layers (published queue points vs ESTIMATE buses)
  state.overlays = await fetchGz("data/overlays.geojson.gz");
  map.addSource("overlays", { type: "geojson", data: state.overlays });
  map.addLayer({ id: "env-padus", type: "fill", source: "overlays",
    filter: ["==", ["get", "layer"], "padus"], layout: { visibility: "none" },
    paint: { "fill-color": "#15803d", "fill-opacity": 0.35, "fill-outline-color": "#14532d" } });
  map.addLayer({ id: "env-bonus", type: "fill", source: "overlays",
    filter: ["==", ["get", "layer"], "bonus"], layout: { visibility: "none" },
    paint: { "fill-color": "#7c3aed", "fill-opacity": 0.22, "fill-outline-color": "#5b21b6" } });
  state.gas = await fetchGz("data/gas.geojson.gz");
  map.addSource("gas", { type: "geojson", data: state.gas });
  map.addLayer({ id: "gas-lines", type: "line", source: "gas",
    filter: ["==", ["get", "layer"], "gas"], layout: { visibility: "none" },
    paint: { "line-color": "#b45309", "line-width": 1.6, "line-dasharray": [3, 2] } });
  map.addLayer({ id: "gas-pts", type: "circle", source: "gas",
    filter: ["in", ["get", "layer"], ["literal", ["compressor", "storage"]]],
    layout: { visibility: "none" },
    paint: { "circle-radius": 5, "circle-color": ["case", ["==", ["get", "layer"], "compressor"], "#b45309", "#78350f"],
             "circle-stroke-color": "#fff", "circle-stroke-width": 1 } });
  for (const id of ["gas-lines", "gas-pts"]) {
    map.on("click", id, (e) => openMiscEvidence(e.features[0].properties));
    map.on("mouseenter", id, () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", id, () => (map.getCanvas().style.cursor = ""));
  }
  state.pjm = await fetchGz("data/pjm.geojson.gz");
  map.addSource("pjm", { type: "geojson", data: state.pjm });
  map.addLayer({ id: "pjm-queue", type: "circle", source: "pjm",
    filter: ["==", ["get", "layer"], "queue_point"], layout: { visibility: "none" },
    paint: { "circle-radius": 3, "circle-color": "#64748b", "circle-opacity": 0.7 } });
  map.addLayer({ id: "pjm-bus-est", type: "circle", source: "pjm",
    filter: ["==", ["get", "layer"], "bus_candidate"], layout: { visibility: "none" },
    paint: { "circle-radius": 6, "circle-color": "#ffffff", "circle-opacity": 0.5,
             "circle-stroke-color": "#dc2626", "circle-stroke-width": 2 } });
  for (const id of ["env-padus", "env-bonus", "pjm-queue", "pjm-bus-est"]) {
    map.on("click", id, (e) => openMiscEvidence(e.features[0].properties));
    map.on("mouseenter", id, () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", id, () => (map.getCanvas().style.cursor = ""));
  }
  setPreset(state.preset); // resync any preset chosen before layers existed
  maybeLoadCounties();
  document.body.dataset.ready = "1";
});

function countyPaint(preset) {
  if (preset === "sentiment")
    return ["case", ["==", ["get", "opposition_intensity"], null], "#f2f2f0",
      ["interpolate", ["linear"], ["to-number", ["get", "opposition_intensity"], 0],
       0, "#eef6ee", 1, "#fde68a", 3, "#f59e0b", 6, "#b91c1c"]];
  return ["interpolate", ["linear"], ["get", "class_union"],
    0, "#f4f7fb", 2000, "#dbe7f5", 10000, "#b7cfea", 30000, "#8fb2dc", 80000, "#5d8cc7"];
}

/* ---------- presets ---------- */
function setPreset(p) {
  state.preset = p;
  document.querySelectorAll("#presets button").forEach((b) => b.classList.toggle("active", b.dataset.p === p));
  document.getElementById("rail-land").style.display = p === "land" ? "" : "none";
  document.getElementById("rail-grid").style.display = p === "grid" ? "" : "none";
  document.getElementById("rail-env").style.display = p === "env" ? "" : "none";
  document.getElementById("rail-sent").style.display = p === "sentiment" ? "" : "none";
  if (!map.getLayer("county-fill")) { renderDenominator(); return; } // layers not up yet; resynced after load
  map.setPaintProperty("county-fill", "fill-color", countyPaint(p));
  map.setPaintProperty("county-fill", "fill-opacity",
    p === "land" ? ["interpolate", ["linear"], ["zoom"], 8.5, 0.85, 10, 0.25] : (p === "env" ? 0.15 : 0.75));
  const gridOn = p === "grid";
  for (const id of ["grid-lines", "grid-subs", "grid-bus"])
    if (map.getLayer(id)) map.setLayoutProperty(id, "visibility",
      gridOn && document.getElementById(`g-${id.split("-")[1]}`)?.checked !== false ? "visible" : "none");
  for (const id of ["pjm-queue", "pjm-bus-est"])
    if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", gridOn ? "visible" : "none");
  for (const id of ["gas-lines", "gas-pts"])
    if (map.getLayer(id)) map.setLayoutProperty(id, "visibility",
      gridOn && document.getElementById("g-gas").checked ? "visible" : "none");
  if (map.getLayer("env-padus")) {
    map.setLayoutProperty("env-padus", "visibility",
      p === "env" && document.getElementById("e-padus").checked ? "visible" : "none");
    map.setLayoutProperty("env-bonus", "visibility",
      p === "env" && document.getElementById("e-bonus").checked ? "visible" : "none");
  }
  for (const fips of state.loaded.keys())
    for (const suf of ["fill", "line"])
      map.setLayoutProperty(`sites-${fips}-${suf}`, "visibility", p === "land" ? "visible" : "none");
  renderDenominator();
}
document.querySelectorAll("#presets button").forEach((b) => b.onclick = () => setPreset(b.dataset.p));
for (const id of ["g-lines", "g-subs", "g-bus", "g-gas"]) {
  const el = document.getElementById(id);
  if (el) el.onchange = () => setPreset("grid");
}
for (const id of ["e-padus", "e-bonus"]) {
  const el = document.getElementById(id);
  if (el) el.onchange = () => setPreset("env");
}

/* ---------- land parcels (unchanged mechanics) ---------- */
function currentFilter() {
  const p = [], mw = Number(document.getElementById("f-mw-val").value) || 25;
  if (document.getElementById("f-ci").checked) p.push(["==", ["get", "occ_group"], "ci"]);
  if (document.getElementById("f-mw").checked) p.push([">=", ["to-number", ["get", "mw_datacenter_4_per_acre"]], mw]);
  if (document.getElementById("f-si").checked) p.push(["==", ["get", "has_si_signal"], true]);
  return p.length ? ["any", ...p] : ["==", ["get", "occ_group"], "__none__"];
}
function jsMatches(p) {
  const mw = Number(document.getElementById("f-mw-val").value) || 25;
  return (document.getElementById("f-ci").checked && p.occ_group === "ci") ||
         (document.getElementById("f-mw").checked && Number(p.mw_datacenter_4_per_acre) >= mw) ||
         (document.getElementById("f-si").checked && p.has_si_signal === true);
}
const FILL_COLOR = ["case", ["==", ["get", "has_si_signal"], true], "#d97706",
  ["==", ["get", "occ_group"], "ci"], "#2563eb", "#059669"];
function addCountyLayers(fips, fc) {
  const src = `sites-${fips}`;
  if (map.getSource(src)) return;
  map.addSource(src, { type: "geojson", data: fc });
  map.addLayer({ id: `${src}-fill`, type: "fill", source: src, minzoom: PARCEL_ZOOM,
    filter: currentFilter(), layout: { visibility: state.preset === "land" ? "visible" : "none" },
    paint: { "fill-color": FILL_COLOR, "fill-opacity": 0.45 } });
  map.addLayer({ id: `${src}-line`, type: "line", source: src, minzoom: PARCEL_ZOOM,
    filter: currentFilter(), layout: { visibility: state.preset === "land" ? "visible" : "none" },
    paint: { "line-color": "#333", "line-width": 0.6 } });
  map.on("click", `${src}-fill`, (e) => openParcelEvidence(e.features[0].properties));
}
function countiesInView() {
  const b = map.getBounds();
  return Object.entries(state.countyBbox)
    .filter(([, [w, s, e, n]]) => b.getWest() < e && b.getEast() > w && b.getSouth() < n && b.getNorth() > s)
    .map(([f]) => f);
}
async function maybeLoadCounties() {
  if (!state.counties) return;
  if (state.preset !== "land" || map.getZoom() < PARCEL_ZOOM) { renderDenominator(); return; }
  for (const fips of countiesInView()) {
    if (state.loaded.has(fips) || state.loading.has(fips)) continue;
    state.loading.add(fips);
    fetchGz(`data/sites/${fips}.geojson.gz`)
      .then((fc) => { state.loaded.set(fips, fc.features); addCountyLayers(fips, fc); renderDenominator(); })
      .catch((e) => console.error(e)).finally(() => state.loading.delete(fips));
  }
  renderDenominator();
}
function applyFilters() {
  const f = currentFilter();
  for (const fips of state.loaded.keys()) {
    map.setFilter(`sites-${fips}-fill`, f); map.setFilter(`sites-${fips}-line`, f);
  }
  renderDenominator();
}
for (const id of ["f-ci", "f-mw", "f-si", "f-mw-val"])
  document.getElementById(id).addEventListener("change", applyFilters);

/* ---------- header, ledger, denominators ---------- */
function renderStatebar() {
  const t = state.summary.totals;
  document.getElementById("statebar").textContent =
    `${fmt(t.all_parcels)} Indiana parcels held · ${fmt(t.class_union)} in rendered classes ` +
    `(C&I ${fmt(t.ci)} · ≥25 MW ${fmt(t.ge25)} · SI ${fmt(t.si)}) · built ${state.summary.built_at_utc}`;
}
function renderLedger() {
  const c = state.summary.cannot_assess;
  const subsTotal = state.provenance["in_substations"]?.n_rows;
  document.getElementById("ledger").innerHTML =
    `<b>Cannot-assess (listed, not hidden):</b><br>` +
    `${fmt(c.si_observations_unmappable)} SI observations with no mappable location<br>` +
    `${fmt(c.parcels_without_geometry)} parcel(s) without geometry · ${fmt(c.parcels_geometry_but_no_county)} without a county<br>` +
    `Substations without published coordinates stay off the map but in the counts (held: ${fmt(subsTotal)}).<br>` +
    `MISO bus values are study results (DPP-2021 vintage) — worst/best shown separately, never fused. PJM/I&I buses have no public coordinates yet; a located candidate set is being built and will render as ESTIMATES, styled apart.`;
}
function renderDenominator() {
  const el = document.getElementById("denominator"), btn = document.getElementById("export-csv");
  if (state.preset === "grid") {
    const g = state.grid ? state.grid.features : [];
    const n = (l) => g.filter((f) => f.properties.layer === l).length;
    el.innerHTML = `<b>${fmt(n("substation"))}</b> substations · <b>${fmt(n("line"))}</b> line segments · ` +
      `<b>${fmt(n("bus_poi"))}</b> MISO bus POIs with publisher coordinates (of ${fmt(state.provenance["in_bus_headroom_miso"]?.n_rows)} MISO-wide).`;
    btn.disabled = true; return;
  }
  if (state.preset === "sentiment") {
    el.innerHTML = `County shading = opposition intensity (grey = no receipts held — cannot assess, not calm). Click a county for its receipts.`;
    btn.disabled = true; return;
  }
  if (state.preset === "env") {
    const o = state.overlays ? state.overlays.features : [];
    el.innerHTML = `<b>${fmt(o.filter((f) => f.properties.layer === "padus").length)}</b> protected areas · ` +
      `<b>${fmt(o.filter((f) => f.properties.layer === "bonus").length)}</b> bonus-credit geographies rendered. ` +
      `Wetlands / flood / fibre are county-grain (click a county) until the tile pipeline ships.`;
    btn.disabled = true; return;
  }
  if (map.getZoom() < PARCEL_ZOOM) {
    el.textContent = `County view — shading counts ALL ${fmt(state.summary?.totals.all_parcels)} parcels. Zoom to z≥${PARCEL_ZOOM} to load individual parcels.`;
    btn.disabled = true; return;
  }
  const inView = countiesInView();
  let classTotal = 0, match = 0, loaded = 0;
  for (const f of state.counties.features)
    if (inView.includes(f.properties.fips)) classTotal += f.properties.class_union;
  for (const fips of inView) {
    const feats = state.loaded.get(fips); if (!feats) continue;
    loaded++; for (const ft of feats) if (jsMatches(ft.properties)) match++;
  }
  el.innerHTML = `<b>${fmt(match)}</b> sites match filters, of <b>${fmt(classTotal)}</b> class sites in ${inView.length} county(ies) (${loaded} loaded${state.loading.size ? ", loading…" : ""}).<br><span class="hint">County shading behind counts all parcels — nothing is dropped.</span>`;
  btn.disabled = match === 0;
}

/* ---------- evidence panels ---------- */
const panel = document.getElementById("evidence");
document.getElementById("ev-close").onclick = () => panel.classList.add("hidden");
function prov(t) {
  const p = state.provenance[t];
  return p ? `source: indiana_app.${t} · rows ${fmt(p.n_rows)} · built ${String(p.built_at).slice(0, 16)}Z` : `source: ${t}`;
}
function row(k, v) {
  const val = (v === null || v === undefined || v === "") ? `<span class="cannot">cannot assess</span>`
    : (typeof v === "number" ? fmt(v) : String(v));
  return `<tr><td>${k}</td><td>${val}</td></tr>`;
}
function show(title, html) {
  document.getElementById("ev-title").textContent = title;
  document.getElementById("evidence-body").innerHTML = html;
  panel.classList.remove("hidden");
}
function openParcelEvidence(p) {
  const a = (x) => x == null ? null : Number(x).toFixed(2);
  show(`Parcel ${p.parcel_key}`, `
    <h3>Land & site (Part 3)</h3><table>
      ${row("parcel key", p.parcel_key)}${row("source table", p.parcel_source)}
      ${row("occupancy group", p.occ_group)}${row("occupancy class", p.occ_cls)}
      ${row("parcel acres", a(p.parcel_acres))}${row("outdoor acres", a(p.outdoor_acres))}
      ${row("structures", p.structure_count)}${row("structure sqft", p.structure_sqft)}
      ${row("fits MW @ 4/acre (DC default)", p.mw_datacenter_4_per_acre == null ? null : Math.floor(p.mw_datacenter_4_per_acre))}
      ${row("fits MW @ 10/acre (BESS default)", p.mw_bess_10_per_acre == null ? null : Math.floor(p.mw_bess_10_per_acre))}
      ${row("location tier", p.geom_kind || "parcel_polygon")}</table>
    <div class="prov">${prov("in_sites")} · MW figures are adjustable defaults, not answers</div>
    <h3>Seller intent (Part 1)</h3><table>
      ${row("carries SI signal", p.has_si_signal === true ? "yes" : (p.has_si_signal === false ? "no" : null))}
      ${row("signal types", p.si_signal_types)}${row("signal events", p.si_signal_events)}
      ${row("signals", p.si_signals)}${row("last event date", p.si_last_event_date)}</table>
    <div class="prov">${prov("in_si_signals")}</div>
    <h3>Environmental gates (Part 4)</h3><table>
      ${row("SFHA flood zone on parcel", p.sfha_flood === undefined ? null : (p.sfha_flood ? "YES — flag" : "no (measured clear)"))}
      ${row("wetland on parcel", p.wetland_on_parcel === undefined ? null : (p.wetland_on_parcel ? "YES — flag" : "no (measured clear)"))}
      ${row("protected land overlap", p.protected_land === undefined ? null : (p.protected_land ? "YES — flag" : "no (measured clear)"))}
      ${row("bonus-credit eligibility", p.bonus_kinds === undefined ? null : (p.bonus_kinds || "none intersecting"))}</table>
    <div class="prov">${prov("in_site_gates")} · water distance + fibre-at-parcel are county-grain pending the tile pipeline</div>`);
}
function openGridEvidence(p) {
  if (p.layer === "bus_poi") {
    show(`MISO POI: ${p.poi_name}`, `
      <h3>Bus identity</h3><table>
      ${row("bus number", p.bus_number)}${row("bus name", p.bus_name)}${row("kV", p.kv)}${row("area", p.area_name)}</table>
      <h3>Transfer capability (study results — not an offer)</h3><table>
      ${row("worst across facilities (MW)", p.worst_mw)}${row("median (MW)", p.median_mw)}${row("best (MW)", p.best_mw)}
      ${row("monitored facilities", p.monitored_facilities)}${row("facilities at zero", p.facilities_at_zero)}
      ${row("worst binding facility", p.worst_binding_facility)}${row("study vintage", p.vintage)}</table>
      <div class="prov">${prov("in_bus_headroom_miso")} · probe ran at an effectively infinite request, so WORST reads 0 almost everywhere — read the three numbers together</div>`);
  } else if (p.layer === "substation") {
    show(`Substation: ${p.substation_name || "(unnamed)"}`, `
      <table>${row("kV range", `${p.min_kv ?? "—"}–${p.max_kv ?? "—"}`)}${row("county", p.county)}
      ${row("status", p.status)}${row("type", p.substation_type)}${row("lines", p.line_count)}${row("operator", p.operator)}</table>
      <div class="prov">${prov("in_substations")} (HIFLD + OSM, deduped)</div>`);
  } else {
    show(`Transmission line`, `
      <table>${row("owner", p.owner)}${row("voltage (kV)", p.voltage)}${row("class", p.volt_class)}
      ${row("status", p.status)}${row("from", p.sub_1)}${row("to", p.sub_2)}</table>
      <div class="prov">${prov("in_transmission_lines")} (HIFLD)</div>`);
  }
}
function openMiscEvidence(p) {
  if (p.layer === "bus_candidate") {
    show(`PJM bus ${p.bus_number} — ESTIMATED location`, `
      <div class="est-badge">ESTIMATE — ${p.location_method}, confidence ${p.match_confidence}</div>
      <table>${row("bus label", p.bus_label)}${row("kV", p.bus_kv)}
      ${row("matched substation", p.matched_substation_name)}${row("kV consistent", p.kv_consistent)}
      ${row("competing matches", p.collision_count)}</table>
      <div class="prov">${prov("in_pjm_bus_locations_candidate")} · an estimate never styles as a published coordinate — hollow red ring means derived</div>`);
  } else if (p.layer === "queue_point") {
    const rows_ = Object.entries(p).filter(([k]) => k !== "layer").slice(0, 10)
      .map(([k, v]) => row(k, v)).join("");
    show(`PJM queue point`, `<table>${rows_}</table>
      <div class="prov">${prov("in_pjm_gis_queues")} · PJM's own published coordinates (gis.pjm.com)</div>`);
  } else if (p.layer === "gas") {
    show(`Gas pipeline`, `
      <table>${row("operator", p.operator)}${row("type", p.typepipe)}</table>
      <div class="prov">${prov("in_gas_pipelines")} (HIFLD) · state-border design capacity is in the Market panel; daily operational availability is an open acquisition lane</div>`);
  } else if (p.layer === "compressor" || p.layer === "storage") {
    const rows_ = Object.entries(p).filter(([k]) => k !== "layer").slice(0, 9)
      .map(([k, v]) => row(k, v)).join("");
    show(`Gas ${p.layer}`, `<table>${rows_}</table>
      <div class="prov">${prov(p.layer === "compressor" ? "in_gas_compressor_stations" : "in_gas_storage")}</div>`);
  } else if (p.layer === "padus") {
    show(`Protected: ${p.name || "(unnamed)"}`, `
      <table>${row("designation", p.designation)}${row("owner type", p.owner_type)}
      ${row("manager", p.manager)}${row("acres", p.acres)}</table>
      <div class="prov">${prov("in_padus")}</div>`);
  } else {
    show(`Bonus geography: ${p.kind}`, `
      <table>${row("kind", p.kind)}${row("key", p.key)}${row("attributes", p.attrs_json)}</table>
      <div class="prov">${prov("in_bonus_geo")} · the BENEFIT half of P4 — improves economics</div>`);
  }
}

async function loadPipeline() {
  if (!state.pipeline) state.pipeline = await fetchGz("data/pipeline.json.gz");
  return state.pipeline;
}
document.getElementById("btn-pipeline").onclick = async () => {
  if (!state.summary) return; // still loading
  const pl = await loadPipeline();
  const plans = pl.grid_plans.filter((r) => r.row_type === "project").slice(0, 60);
  const rto = pl.rto_expansion.slice(0, 60);
  show("Future capacity — where upgrades are coming", `
    <h3>State-jurisdictional grid plans (TDSIC/IRP) — ${fmt(pl.grid_plans.filter((r) => r.row_type === "project").length)} projects</h3>
    <table>${plans.map((r) => row(`${r.utility || ""} ${r.in_service_year || ""}`,
      `${r.project_name || r.location_text || ""} ${r.voltage_kv ? r.voltage_kv + " kV" : ""} ${r.cost_usd_m ? "$" + r.cost_usd_m + "M" : ""}`)).join("")}</table>
    <div class="prov">${prov("in_grid_plans")} · locations are named endpoints/counties (joinable), never geocoded</div>
    <h3>RTO expansion (MISO MTEP + PJM RTEP) — ${fmt(pl.rto_expansion.length)} Indiana-naming projects</h3>
    <table>${rto.map((r) => row(`${r.rto || r.source || ""} ${r.in_service_year || r.isd || ""}`,
      `${r.project_name || r.upgrade_name || r.description || ""}`)).join("")}</table>
    <div class="prov">${prov("in_rto_expansion")} · first 60 of each shown; full lists in BigQuery + CSV on request</div>
    <h3>PJM queue network-upgrade costs</h3>
    <table>${pl.nucra_costs.slice(0, 20).map((r) => row(r.project_id || r.queue_id || "project",
      JSON.stringify(r).slice(0, 120))).join("")}</table>
    <div class="prov">${prov("in_pjm_nucra_costs")}</div>`);
};

document.getElementById("btn-market").onclick = async () => {
  if (!state.summary) return;
  if (!state.market) state.market = await fetchGz("data/market.json.gz");
  const m = state.market;
  const recent = m.monthly.slice(-120);
  const max = Math.max(...recent.map((r) => r.gross_load_mwh || 0));
  const pts = recent.map((r, i) => `${(i / (recent.length - 1) * 300).toFixed(1)},${(80 - (r.gross_load_mwh || 0) / max * 75).toFixed(1)}`).join(" ");
  const gas = (m.gas_state_capacity || []).filter((r) => r.year >= 2015)
    .sort((a, b) => b.capacity_mmcfd - a.capacity_mmcfd).slice(0, 25);
  show("Market (P6) — generation & gas capacity", `
    <h3>CEMS gross generation, Indiana plants (last 10 years, monthly)</h3>
    <svg viewBox="0 0 300 84" style="width:100%;background:#f8fafc;border:1px solid #e3e6ec;border-radius:6px">
      <polyline points="${pts}" fill="none" stroke="#0f172a" stroke-width="1.2"/></svg>
    <div class="prov">${prov("in_cems_monthly")} · ${m.monthly.length} months held (${m.monthly[0]?.month} → ${m.monthly[m.monthly.length - 1]?.month})</div>
    <h3>Top plants by generation</h3>
    <table>${m.top_plants.slice(0, 10).map((r) => row(`plant ${r.plant_id_epa}`,
      `${fmt(r.gross_load_mwh)} MWh · ${fmt(r.co2_tons)} t CO2 · thru ${r.last_month}`)).join("")}</table>
    <h3>Gas pipeline capacity at Indiana borders (EIA, design)</h3>
    <table>${gas.map((r) => row(`${r.pipeline || ""} ${r.year}`,
      `${r.state_from}→${r.state_to} (${r.county_from || "?"}→${r.county_to || "?"}): ${fmt(r.capacity_mmcfd)} MMcf/d`)).join("")}</table>
    <div class="prov">${prov("in_gas_state_capacity")} · DESIGN capacity — daily operational availability (EBB) is an open acquisition lane</div>`);
};

const FEATURE_HOME = {
  in_sites: "Land preset — parcels + filters + evidence", in_si_signals: "Land evidence (SI section)",
  in_sites_county: "county assignment (spine)", in_county_rollup: "county layer + county evidence",
  in_substations: "Grid preset", in_transmission_lines: "Grid preset", in_bus_headroom_miso: "Grid preset (MISO POIs)",
  in_miso_poi_identity: "feeds in_bus_headroom_miso", in_pjm_bus_locations_candidate: "Grid preset (estimate ring)",
  in_pjm_gis_queues: "Grid preset (queue points)", in_queue: "Future-capacity panel + county evidence",
  in_queue_counties: "county evidence (queue)", in_grid_plans: "Future-capacity panel",
  in_rto_expansion: "Future-capacity panel", in_pjm_nucra_costs: "Future-capacity panel",
  in_pjm_rtep_upgrades: "Future-capacity panel (source of RTO rows)",
  in_pjm_rtep_upgrade_details: "DEFERRED: per-upgrade drill-down panel",
  in_pjm_rtep_cost_allocations: "DEFERRED: per-upgrade drill-down panel",
  in_pjm_queuescope_aep: "DEFERRED: needs bus locations (candidate set is the path)",
  in_padus: "Environmental preset", in_bonus_geo: "Environmental preset",
  in_wetlands: "county evidence (gate stats); polygons DEFERRED to tile pipeline",
  in_flood: "county evidence (gate stats); polygons DEFERRED to tile pipeline",
  in_water: "DEFERRED: tile pipeline (2.4M flowlines)",
  in_fcc_bdc: "county evidence via in_county_fibre",
  in_county_fibre: "county evidence", in_county_flood: "county evidence", in_county_wetlands: "county evidence",
  in_iurc_dockets: "Sentiment receipts", in_news_dc: "Sentiment receipts", in_dc_actions: "Sentiment receipts",
  in_ordinances_dc: "Sentiment receipts", in_cems_monthly: "Market panel (P6)",
  in_gas_pipelines: "Grid preset (gas layer)", in_gas_compressor_stations: "Grid preset (gas layer)",
  in_gas_storage: "Grid preset (gas layer)", in_gas_state_capacity: "Market panel (gas capacity)",
  in_gas_processing_plants: "measured zero in Indiana — evidence of absence, registered",
  in_gas_lng_terminals: "measured zero in Indiana — evidence of absence, registered",
  in_site_gates: "parcel evidence panel (environmental gates)",
};
document.getElementById("btn-inventory").onclick = () => {
  if (!state.summary) return; // still loading
  const rows_ = state.summary.provenance.map((p) => {
    let home = FEATURE_HOME[p.table_name];
    if (!home) home = p.table_name.startsWith("in_si_") ?
      "STAGED: new SI acquisitions awaiting subject wiring" : "STAGED: refresh/staging table";
    const cls = home.startsWith("DEFERRED") || home.startsWith("STAGED") ? ' class="cannot"' : "";
    return `<tr><td>${p.table_name}<br><span class="hint">${fmt(p.n_rows)} rows · ${String(p.built_at).slice(0, 10)}</span></td><td${cls}>${home}</td></tr>`;
  }).join("");
  show("Data inventory — every table has a feature home or a stated waiver", `
    <div class="hint">The Indiana-scoped version of the platform rule: every dataset ships in a feature or carries a waiver. DEFERRED/STAGED rows are the honest waivers.</div>
    <table>${rows_}</table>`);
};

async function openCountyEvidence(p) {
  const c = state.ctx.by_fips[p.fips] || {};
  let html = `
    <h3>County rollup — 100% of parcels counted</h3><table>
      ${row("parcels", p.parcels)}${row("with a building", p.with_building)}${row("strict C&I", p.ci)}
      ${row("fits ≥25 MW @ 4/acre", p.ge25mw)}${row("carries SI signal", p.si_sites)}
      ${row("MW potential @ 4/acre (sum)", p.mw_potential_at_4)}</table>
    <div class="prov">${prov("in_county_rollup")}</div>
    <h3>Interconnection queue</h3><table>
      ${row("projects", c.queue?.projects)}${row("active projects", c.queue?.active_projects)}
      ${row("active MW", c.queue?.active_mw)}${row("withdrawn (a signal, kept)", c.queue?.withdrawn_projects)}</table>
    <div class="prov">${prov("in_queue_counties")}</div>
    <h3>Environmental & infrastructure gates (county grain)</h3><table>
      ${row("wetland features / acres", c.wetlands ? `${fmt(c.wetlands.wetland_features)} / ${fmt(c.wetlands.wetland_acres)} ac` : null)}
      ${row("flood features (SFHA)", c.flood ? `${fmt(c.flood.flood_features)} (${fmt(c.flood.sfha_features)} SFHA)` : null)}
      ${row("fibre-served locations (FCC)", c.fibre ? `${fmt(c.fibre.fiber_locations)} of ${fmt(c.fibre.locations)}` : null)}
      ${row("fibre providers", c.fibre?.fiber_providers)}
      ${row("gig-capable locations", c.fibre?.gig_locations)}</table>
    <div class="prov">${prov("in_county_wetlands")} · ${prov("in_county_fibre")} · per-parcel gate columns are the tile-pipeline milestone</div>
    <h3>Community posture</h3><table>
      ${row("posture", c.posture?.posture)}${row("opposition intensity", c.posture?.opposition_intensity)}
      ${row("local restriction", c.posture?.has_local_restriction)}${row("moratoriums", c.posture?.local_moratoriums)}
      ${row("news tone (avg)", c.posture?.news_avg_tone)}</table>
    <div class="prov">source: energy.vw_county_dc_posture · one counter in this view is under verification and not shown</div>`;
  if (!state.receipts) { try { state.receipts = await fetchGz("data/receipts.json.gz"); } catch (e) { state.receipts = []; } }
  const name = (p.county_name || "").toUpperCase().replace(/ COUNTY$/, "");
  const rows = state.receipts.filter((r) => (r.county || "").toUpperCase().replace(/ COUNTY$/, "") === name).slice(0, 40);
  html += `<h3>Receipts (${rows.length} county-tagged · statewide dockets under Sentiment preset)</h3>`;
  html += rows.length ? `<table>` + rows.map((r) =>
    `<tr><td>${r.kind}<br><span class="hint">${r.observed_date ?? "no date"}</span></td>
     <td>${r.url ? `<a href="${r.url}" target="_blank" rel="noopener">${r.title}</a>` : r.title}<br><span class="hint">${r.detail ?? ""}</span></td></tr>`).join("") + `</table>`
    : `<div class="hint">No county-tagged receipts held — cannot assess, not "quiet".</div>`;
  show(`${p.county_name} County`, html);
}

/* ---------- CSV export (land preset) ---------- */
document.getElementById("export-csv").onclick = () => {
  const rows = [];
  for (const fips of countiesInView()) {
    const feats = state.loaded.get(fips); if (!feats) continue;
    for (const ft of feats) if (jsMatches(ft.properties)) rows.push(ft.properties);
  }
  if (!rows.length) return;
  const cols = Object.keys(rows[0]);
  const esc = (v) => v == null ? "" : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v);
  const csv = [cols.join(","), ...rows.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = `indiana_sites_filtered_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
};
