/* Shared shell for the Phase-2 pages: nav, fetch helpers, formatting, provenance. */
"use strict";
/* Tab labels are the user's first contact with the tool, so they carry NO internal codenames.
   "SI Feed" meant seller-intent and was an acronym for an acronym; "P1..P7" named slots in our
   build order. Operator, 2026-08-17: "the user won't know what P1-P7 are". See docs/BACKLOG.md G8
   for the binding translation table. */
const NAV = [["insights.html", "Insights"], ["index.html", "Map console"],
  ["screener.html", "Site screener"], ["grid.html", "Power & grid"],
  ["market.html", "Market & cost"], ["community.html", "Community & local rules"],
  ["si.html", "Owner signals"], ["data.html", "Data & sources"]];
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
/* ============================================================================================
   PLAIN LANGUAGE — ONE COPY, SHARED BY EVERY PAGE
   Operator, 2026-08-17: "the user won't know what P1-P7 are... Same with terms like OAC, where I
   didn't know the abbreviation and had to look it up - everything should be simplified and
   explained in an easily digestible way."

   This lives in common.js and NOWHERE ELSE on purpose. A second copy of a translation table in a
   second file is the defect this project has hit repeatedly: two copies of one thing WILL drift,
   and the loser is invisible. If a label is missing here, add it here.
   ============================================================================================ */

/* Owner-motivation signals. Each entry is [plain name, why a site-hunter should care, kind].
   The raw codes (D4, D12...) are our internal build order and must never reach the screen.

   KIND is load-bearing, not decoration (operator, 2026-08-17, docs/BACKLOG.md G9):
     "event" = a thing happened on a date, and it GOES STALE. A 2014 foreclosure says nothing
               about today's owner, so a recency filter is meaningful.
     "state" = a standing condition that does NOT expire. Contamination does not heal because the
               record is old; a delisted plant stays delisted. Date-gating these would silently
               delete real, current inventory.
   Measured: 35.5% of all signal attachments are UNDATED, and 90% of the single largest signal
   (unpaid property taxes) has no date. So "undated" is a THIRD state -- recency unknown -- and is
   never quietly folded into either "recent" or "old". */
const SIGNAL_PLAIN = {
  D1_tax_sale: ["Listed for tax sale", "the county has scheduled the property for auction over unpaid taxes", "event"],
  D2_foreclosure: ["Foreclosure filed", "a lender has begun taking the property back", "event"],
  D4_tax_delinquency: ["Unpaid property taxes", "taxes are overdue but no auction is scheduled yet", "event"],
  D5_unsafe_building: ["Building declared unsafe", "the building has been ruled unsafe to occupy", "event"],
  D5_vacant_board_order: ["Vacant building ordered boarded up", "the city ordered an empty BUILDING secured - this is not about empty land", "event"],
  D5_abandoned_building: ["Building recorded as abandoned", "the BUILDING is on an abandoned-property list - this is not about empty land", "state"],
  D7_brownfield: ["Brownfield / remediation site", "known or suspected contamination, which often lowers price and may carry cleanup funding - and does not expire", "state"],
  D12_code_violation: ["Repeated code violations", "a pattern of unresolved violations, not a single citation", "event"],
  D14_sba_chargeoff: ["Defaulted federal business loan", "an SBA loan against the property was written off", "event"],
  D16_structure_fire: ["Fire damage on record", "the fire service recorded a structure fire here", "event"],
  D19_warn: ["Mass-layoff notice filed", "the employer filed a state notice of a large layoff or closure", "event"],
  D20_loan_maturity: ["Mortgage maturing", "a commercial mortgage is coming due and will need refinancing", "event"],
  D21_demolition_order: ["Demolition ordered", "the building is slated to come down", "event"],
  D22_environmental_violation: ["Environmental violation", "a state or federal environmental enforcement action", "event"],
  D22_facility_inactive: ["Permitted facility went inactive", "an environmental permit here is no longer active, suggesting operations stopped", "state"],
  D24_plant_delisting: ["Plant delisted", "the site came off a register of operating plants", "state"],
  D26_assessment_appeal: ["Owner appealed their tax assessment", "the owner is disputing the property's assessed value", "event"],
  A2_gov_surplus: ["Government surplus property", "a public body has declared the property surplus to its needs", "state"],
};
const signalKind = (code) => (SIGNAL_PLAIN[String(code).trim()] || [, , "event"])[2];
/* does this parcel carry at least one signal that never goes stale? */
const hasStateSignal = (csv) => !csv ? false
  : String(csv).split(",").some((s) => signalKind(s) === "state");

/* ⛔ ONE WORD, ONE MEANING (docs/BACKLOG.md G10). "Vacant" was being used for BOTH a parcel with
   no structure AND a building standing empty - two unrelated things, no cue to the reader.
   Land with no building is UNDEVELOPED. Only a BUILDING is ever called vacant or abandoned. */
const LAND_PLAIN = {
  ci: "commercial / industrial",
  ag: "farmland",
  undeveloped: "undeveloped land",   // no structure on the parcel. NOT "vacant".
  built: "has buildings",
};
const landPlain = (occ_group, structure_count) =>
  LAND_PLAIN[occ_group] || ((structure_count || 0) > 0 ? LAND_PLAIN.built : LAND_PLAIN.undeveloped);
/* "D4_tax_delinquency,D2_foreclosure" -> "Unpaid property taxes · Foreclosure filed" */
function signalsPlain(csv) {
  if (!csv) return "";
  return String(csv).split(",").map((s) => {
    const k = s.trim(), e = SIGNAL_PLAIN[k];
    return e ? `<span title="${e[1]}">${e[0]}</span>`
             : k.replace(/^[A-Z]\d+_/, "").replace(/_/g, " ");
  }).join(" · ");
}

/* Abbreviations we cannot avoid showing (they are the publisher's own names). Every one of these
   gets expanded on first use, with a plain gloss. Rendered by abbr(). */
const GLOSSARY = {
  MISO: ["Midcontinent Independent System Operator", "the grid operator for most of Indiana"],
  PJM: ["PJM Interconnection", "the grid operator for eastern Indiana and the mid-Atlantic"],
  RTO: ["Regional Transmission Organization", "the company that runs the high-voltage grid across several states"],
  ISO: ["Independent System Operator", "same idea as an RTO"],
  OAC: ["Operationally Available Capacity", "how much gas a pipeline can still take on a given day"],
  SFHA: ["Special Flood Hazard Area", "FEMA's 1-in-100-year flood zone"],
  HIFLD: ["Homeland Infrastructure Foundation-Level Data", "a federal dataset of infrastructure locations"],
  OSM: ["OpenStreetMap", "a public, community-maintained map"],
  POI: ["Point of Interconnection", "the specific place a project would connect to the grid"],
  IDEM: ["Indiana Department of Environmental Management", "the state environmental agency"],
  IURC: ["Indiana Utility Regulatory Commission", "the state body that approves utility rates"],
  FERC: ["Federal Energy Regulatory Commission", "the federal energy regulator"],
  EIA: ["U.S. Energy Information Administration", "the federal energy statistics agency"],
  IRP: ["Integrated Resource Plan", "a utility's published long-term plan for building generation"],
  MTEP: ["MISO Transmission Expansion Plan", "MISO's approved list of grid upgrades to be built"],
  RTEP: ["Regional Transmission Expansion Plan", "PJM's equivalent of MTEP"],
  URDB: ["Utility Rate Database", "a public collection of published electricity tariffs"],
  SAIDI: ["System Average Interruption Duration Index", "average minutes a customer is without power per year"],
  SAIFI: ["System Average Interruption Frequency Index", "average number of outages a customer sees per year"],
  BESS: ["Battery Energy Storage System", "a grid-connected battery installation"],
  kV: ["kilovolt", "a measure of line voltage; higher generally means more capacity"],
  MW: ["megawatt", "a measure of electrical power; a large data centre campus is 300-1,000 MW"],
};
/* <span class="abbr">MISO</span> style inline expansion */
function abbr(k) {
  const e = GLOSSARY[k];
  return e ? `<abbr title="${e[0]} — ${e[1]}">${k}</abbr>` : k;
}
/* Expand every known abbreviation inside a block of already-rendered HTML text. */
function glossify(root) {
  const el = typeof root === "string" ? document.getElementById(root) : root;
  if (!el) return;
  const keys = Object.keys(GLOSSARY).filter((k) => /^[A-Z]{2,6}$/.test(k));
  const re = new RegExp(`\\b(${keys.join("|")})\\b`, "g");
  const walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  const hits = [];
  while (walk.nextNode()) {
    const n = walk.currentNode;
    if (n.parentElement.closest("abbr,script,style,input,select,textarea")) continue;
    if (re.test(n.nodeValue)) hits.push(n);
    re.lastIndex = 0;
  }
  for (const n of hits) {
    const span = document.createElement("span");
    span.innerHTML = n.nodeValue.replace(re, (m) => abbr(m));
    n.parentNode.replaceChild(span, n);
  }
}

function svgLine(series, key, color = "#0f172a") {
  const s = series.slice(-120), mx = Math.max(...s.map((r) => r[key] || 0));
  const pts = s.map((r, i) => `${(i / (s.length - 1) * 300).toFixed(1)},${(80 - (r[key] || 0) / mx * 75).toFixed(1)}`).join(" ");
  return `<svg viewBox="0 0 300 84" style="width:100%;max-width:640px;background:#f8fafc;border:1px solid #e3e6ec;border-radius:6px"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.2"/></svg>`;
}
document.addEventListener("DOMContentLoaded", () => renderNav());
