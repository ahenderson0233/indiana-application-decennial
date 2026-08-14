/* Indiana Siting Intelligence — v0 spine console.
 * One map. County choropleth carries 100% of parcels at every zoom; class-union
 * parcels render individually (exact geometry) per county at z>=10.
 * Every number traces to state_summary.json provenance; cannot-assess is shown, never zeroed.
 */
"use strict";

const PARCEL_ZOOM = 10;
const state = {
  summary: null,
  provenance: {},
  counties: null,           // GeoJSON (with rollup props)
  countyBbox: {},           // fips -> [w,s,e,n]
  loaded: new Map(),        // fips -> feature array
  loading: new Set(),
};

async function fetchGz(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  if (typeof DecompressionStream === "undefined")
    throw new Error("This browser lacks DecompressionStream; use a current Chrome/Edge/Firefox.");
  const ds = res.body.pipeThrough(new DecompressionStream("gzip"));
  return new Response(ds).json();
}

function bboxOf(geom) {
  let w = 180, s = 90, e = -180, n = -90;
  const walk = (c) => {
    if (typeof c[0] === "number") {
      w = Math.min(w, c[0]); e = Math.max(e, c[0]);
      s = Math.min(s, c[1]); n = Math.max(n, c[1]);
    } else c.forEach(walk);
  };
  walk(geom.coordinates);
  return [w, s, e, n];
}

const fmt = (n) => n == null ? "—" : Number(n).toLocaleString("en-US");

const map = new maplibregl.Map({
  container: "map",
  center: [-86.28, 39.85],
  zoom: 6.6,
  style: {
    version: 8,
    sources: {
      basemap: {
        type: "raster",
        tiles: ["https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png"],
        tileSize: 256,
        attribution: "© OpenStreetMap contributors © CARTO",
      },
    },
    layers: [{ id: "basemap", type: "raster", source: "basemap" }],
  },
});
map.addControl(new maplibregl.NavigationControl(), "top-right");

map.on("load", async () => {
  state.summary = await (await fetch("data/state_summary.json")).json();
  for (const p of state.summary.provenance) state.provenance[p.table_name] = p;
  renderStatebar();
  renderLedger();

  state.counties = await fetchGz("data/counties.geojson.gz");
  for (const f of state.counties.features)
    state.countyBbox[f.properties.fips] = bboxOf(f.geometry);

  map.addSource("counties", { type: "geojson", data: state.counties });
  map.addLayer({
    id: "county-fill", type: "fill", source: "counties",
    paint: {
      "fill-color": ["interpolate", ["linear"], ["get", "class_union"],
        0, "#f4f7fb", 2000, "#dbe7f5", 10000, "#b7cfea", 30000, "#8fb2dc", 80000, "#5d8cc7"],
      "fill-opacity": ["interpolate", ["linear"], ["zoom"], 8.5, 0.85, 10, 0.25],
    },
  });
  map.addLayer({
    id: "county-line", type: "line", source: "counties",
    paint: { "line-color": "#7d8aa0", "line-width": 0.7 },
  });

  map.on("click", "county-fill", (e) => {
    if (map.getZoom() >= PARCEL_ZOOM) return;
    openCountyEvidence(e.features[0].properties);
  });
  map.on("moveend", maybeLoadCounties);
  maybeLoadCounties();
});

function currentFilter() {
  const useCi = document.getElementById("f-ci").checked;
  const useMw = document.getElementById("f-mw").checked;
  const useSi = document.getElementById("f-si").checked;
  const mw = Number(document.getElementById("f-mw-val").value) || 25;
  const parts = [];
  if (useCi) parts.push(["==", ["get", "occ_group"], "ci"]);
  if (useMw) parts.push([">=", ["to-number", ["get", "mw_datacenter_4_per_acre"]], mw]);
  if (useSi) parts.push(["==", ["get", "has_si_signal"], true]);
  return parts.length ? ["any", ...parts] : ["==", ["get", "occ_group"], "__none__"];
}

function jsMatches(p) {
  const useCi = document.getElementById("f-ci").checked;
  const useMw = document.getElementById("f-mw").checked;
  const useSi = document.getElementById("f-si").checked;
  const mw = Number(document.getElementById("f-mw-val").value) || 25;
  return (useCi && p.occ_group === "ci") ||
         (useMw && Number(p.mw_datacenter_4_per_acre) >= mw) ||
         (useSi && p.has_si_signal === true);
}

const FILL_COLOR = ["case",
  ["==", ["get", "has_si_signal"], true], "#d97706",
  ["==", ["get", "occ_group"], "ci"], "#2563eb",
  "#059669"];

function addCountyLayers(fips, fc) {
  const src = `sites-${fips}`;
  if (map.getSource(src)) return;
  map.addSource(src, { type: "geojson", data: fc });
  map.addLayer({
    id: `${src}-fill`, type: "fill", source: src, minzoom: PARCEL_ZOOM,
    filter: currentFilter(),
    paint: { "fill-color": FILL_COLOR, "fill-opacity": 0.45 },
  });
  map.addLayer({
    id: `${src}-line`, type: "line", source: src, minzoom: PARCEL_ZOOM,
    filter: currentFilter(),
    paint: { "line-color": "#333", "line-width": 0.6 },
  });
  map.on("click", `${src}-fill`, (e) => openParcelEvidence(e.features[0].properties));
  map.on("mouseenter", `${src}-fill`, () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", `${src}-fill`, () => (map.getCanvas().style.cursor = ""));
}

function countiesInView() {
  const b = map.getBounds();
  return Object.entries(state.countyBbox)
    .filter(([, [w, s, e, n]]) => b.getWest() < e && b.getEast() > w && b.getSouth() < n && b.getNorth() > s)
    .map(([fips]) => fips);
}

async function maybeLoadCounties() {
  if (!state.counties) return;
  if (map.getZoom() < PARCEL_ZOOM) { renderDenominator(); return; }
  for (const fips of countiesInView()) {
    if (state.loaded.has(fips) || state.loading.has(fips)) continue;
    state.loading.add(fips);
    fetchGz(`data/sites/${fips}.geojson.gz`)
      .then((fc) => { state.loaded.set(fips, fc.features); addCountyLayers(fips, fc); renderDenominator(); })
      .catch((err) => console.error(err))
      .finally(() => state.loading.delete(fips));
  }
  renderDenominator();
}

function applyFilters() {
  const f = currentFilter();
  for (const fips of state.loaded.keys()) {
    map.setFilter(`sites-${fips}-fill`, f);
    map.setFilter(`sites-${fips}-line`, f);
  }
  renderDenominator();
}
for (const id of ["f-ci", "f-mw", "f-si", "f-mw-val"])
  document.getElementById(id).addEventListener("change", applyFilters);

function renderStatebar() {
  const t = state.summary.totals;
  document.getElementById("statebar").textContent =
    `${fmt(t.all_parcels)} Indiana parcels held · ${fmt(t.class_union)} in rendered classes ` +
    `(C&I ${fmt(t.ci)} · ≥25 MW ${fmt(t.ge25)} · SI ${fmt(t.si)}) · built ${state.summary.built_at_utc}`;
}

function renderLedger() {
  const c = state.summary.cannot_assess;
  document.getElementById("ledger").innerHTML =
    `<b>Cannot-assess (listed, not hidden):</b><br>` +
    `${fmt(c.si_observations_unmappable)} SI observations with no mappable location<br>` +
    `${fmt(c.parcels_without_geometry)} parcel(s) without geometry<br>` +
    `${fmt(c.parcels_geometry_but_no_county)} parcel(s) unassignable to a county<br>` +
    `Parcels outside the rendered classes are fully counted in county shading and totals.`;
}

function renderDenominator() {
  const el = document.getElementById("denominator");
  const btn = document.getElementById("export-csv");
  if (map.getZoom() < PARCEL_ZOOM) {
    el.textContent = `County view — shading counts ALL ${fmt(state.summary?.totals.all_parcels)} parcels. Zoom to z≥${PARCEL_ZOOM} to load individual parcels.`;
    btn.disabled = true;
    return;
  }
  const inView = countiesInView();
  let classTotal = 0, match = 0, loaded = 0;
  for (const f of state.counties.features)
    if (inView.includes(f.properties.fips)) classTotal += f.properties.class_union;
  for (const fips of inView) {
    const feats = state.loaded.get(fips);
    if (!feats) continue;
    loaded++;
    for (const ft of feats) if (jsMatches(ft.properties)) match++;
  }
  el.innerHTML = `<b>${fmt(match)}</b> sites match filters, of <b>${fmt(classTotal)}</b> class sites ` +
    `in ${inView.length} county(ies) in view (${loaded} loaded${state.loading.size ? ", loading…" : ""}).<br>` +
    `<span class="hint">County shading behind counts all parcels — nothing is dropped.</span>`;
  btn.disabled = match === 0;
}

/* ---------- evidence panel ---------- */
const panel = document.getElementById("evidence");
document.getElementById("ev-close").onclick = () => panel.classList.add("hidden");

function prov(table) {
  const p = state.provenance[table];
  return p ? `source: energy-platfrom.indiana_app.${table} · rows ${fmt(p.n_rows)} · built ${p.built_at.slice(0, 16)}Z`
           : `source: ${table}`;
}

function row(k, v, cannot) {
  const val = (v === null || v === undefined || v === "") ?
    `<span class="cannot">cannot assess</span>` :
    (typeof v === "number" ? fmt(v) : String(v));
  return `<tr><td>${k}</td><td${cannot ? ' class="cannot"' : ""}>${val}</td></tr>`;
}

function openParcelEvidence(p) {
  document.getElementById("ev-title").textContent = `Parcel ${p.parcel_key}`;
  const acres = (x) => x == null ? null : Number(x).toFixed(2);
  document.getElementById("evidence-body").innerHTML = `
    <h3>Land & site (Part 3)</h3>
    <table>
      ${row("parcel key", p.parcel_key)}${row("source table", p.parcel_source)}
      ${row("occupancy group", p.occ_group)}${row("occupancy class", p.occ_cls)}
      ${row("parcel acres", acres(p.parcel_acres))}${row("outdoor acres", acres(p.outdoor_acres))}
      ${row("structures on parcel", p.structure_count)}${row("structure sqft", p.structure_sqft)}
      ${row("fits MW @ 4/acre (DC default)", p.mw_datacenter_4_per_acre == null ? null : Math.floor(p.mw_datacenter_4_per_acre))}
      ${row("fits MW @ 10/acre (BESS default)", p.mw_bess_10_per_acre == null ? null : Math.floor(p.mw_bess_10_per_acre))}
      ${row("location tier", p.geom_kind || "parcel_polygon")}
    </table>
    <div class="prov">${prov("in_sites")} · both MW figures are adjustable defaults, not answers</div>
    <h3>Seller intent (Part 1)</h3>
    <table>
      ${row("carries SI signal", p.has_si_signal === true ? "yes" : (p.has_si_signal === false ? "no" : null))}
      ${row("signal types", p.si_signal_types)}${row("signal events", p.si_signal_events)}
      ${row("signals", p.si_signals)}${row("last event date", p.si_last_event_date)}
    </table>
    <div class="prov">${prov("in_si_signals")}</div>
    <h3>Coming to this panel</h3>
    <div class="hint">Grid gates (substations, queue, PJM/I&M bus results), water & fibre gates,
    environmental risk/benefit matrix — the clips are already in BigQuery (see docs/DATA.md);
    wiring them into this panel is the next milestone.</div>`;
  panel.classList.remove("hidden");
}

function openCountyEvidence(p) {
  document.getElementById("ev-title").textContent = `${p.county_name} County`;
  document.getElementById("evidence-body").innerHTML = `
    <h3>County rollup — 100% of parcels counted</h3>
    <table>
      ${row("parcels", p.parcels)}${row("with a building", p.with_building)}
      ${row("strict C&I", p.ci)}${row("fits ≥25 MW @ 4/acre", p.ge25mw)}
      ${row("carries SI signal", p.si_sites)}${row("rendered-class union", p.class_union)}
      ${row("MW potential @ 4/acre (sum)", p.mw_potential_at_4)}
    </table>
    <div class="prov">${prov("in_county_rollup")}</div>
    <div class="hint" style="margin-top:8px">Zoom to z≥${PARCEL_ZOOM} over this county to load its parcels individually (exact geometry).</div>`;
  panel.classList.remove("hidden");
}

/* ---------- CSV export of the filtered, in-view sites ---------- */
document.getElementById("export-csv").onclick = () => {
  const inView = countiesInView();
  const rows = [];
  for (const fips of inView) {
    const feats = state.loaded.get(fips);
    if (!feats) continue;
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
