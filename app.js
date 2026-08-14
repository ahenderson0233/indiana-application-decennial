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
  setPreset(state.preset); // resync any preset chosen before layers existed
  maybeLoadCounties();
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
  document.getElementById("rail-sent").style.display = p === "sentiment" ? "" : "none";
  if (!map.getLayer("county-fill")) { renderDenominator(); return; } // layers not up yet; resynced after load
  map.setPaintProperty("county-fill", "fill-color", countyPaint(p));
  map.setPaintProperty("county-fill", "fill-opacity",
    p === "land" ? ["interpolate", ["linear"], ["zoom"], 8.5, 0.85, 10, 0.25] : 0.75);
  const gridOn = p === "grid";
  for (const id of ["grid-lines", "grid-subs", "grid-bus"])
    if (map.getLayer(id)) map.setLayoutProperty(id, "visibility",
      gridOn && document.getElementById(`g-${id.split("-")[1]}`)?.checked !== false ? "visible" : "none");
  for (const fips of state.loaded.keys())
    for (const suf of ["fill", "line"])
      map.setLayoutProperty(`sites-${fips}-${suf}`, "visibility", p === "land" ? "visible" : "none");
  renderDenominator();
}
document.querySelectorAll("#presets button").forEach((b) => b.onclick = () => setPreset(b.dataset.p));
for (const id of ["g-lines", "g-subs", "g-bus"]) {
  const el = document.getElementById(id);
  if (el) el.onchange = () => setPreset("grid");
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
    <h3>Gates in BigQuery, panel wiring next</h3>
    <div class="hint">Environmental risk/benefit, water & fibre, and per-site grid distance land here from the registered clips.</div>`);
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
