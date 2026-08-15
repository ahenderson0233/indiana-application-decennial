/* Shared shell for the Phase-2 pages: nav, fetch helpers, formatting, provenance. */
"use strict";
const NAV = [["index.html", "Map console"], ["grid.html", "Grid & Capacity"],
  ["market.html", "Market & Rates"], ["community.html", "Community & Regulatory"],
  ["si.html", "SI Feed"], ["data.html", "Data"]];
function renderNav(active) {
  const here = location.pathname.split("/").pop() || "index.html";
  const el = document.getElementById("nav");
  if (!el) return;
  el.innerHTML = NAV.map(([href, label], i) =>
    `<a href="${href}" class="${href === here ? "active" : ""}"><span class="num">0${i + 1}</span>${label}</a>`).join("");
}
async function fetchGz(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return new Response(res.body.pipeThrough(new DecompressionStream("gzip"))).json();
}
async function fetchJson(url) { return (await fetch(url + "?v=" + Date.now())).json(); }
const fmt = (n) => n == null ? "—" : Number(n).toLocaleString("en-US");
let PROV = {};
async function loadProv() {
  const s = await fetchJson("data/state_summary.json");
  for (const p of s.provenance) PROV[p.table_name] = p;
  return s;
}
function prov(t) {
  const p = PROV[t];
  return p ? `source: indiana_app.${t} · rows ${fmt(p.n_rows)} · built ${String(p.built_at).slice(0, 16)}Z` : `source: ${t}`;
}
function svgLine(series, key, color = "#0f172a") {
  const s = series.slice(-120), mx = Math.max(...s.map((r) => r[key] || 0));
  const pts = s.map((r, i) => `${(i / (s.length - 1) * 300).toFixed(1)},${(80 - (r[key] || 0) / mx * 75).toFixed(1)}`).join(" ");
  return `<svg viewBox="0 0 300 84" style="width:100%;max-width:640px;background:#f8fafc;border:1px solid #e3e6ec;border-radius:6px"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.2"/></svg>`;
}
document.addEventListener("DOMContentLoaded", () => renderNav());
