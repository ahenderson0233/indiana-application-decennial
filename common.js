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
 /* The corpus carries six more codes than the flag set does. They were unlabelled, so the SI Feed's
     signal inventory printed RAW CODENAMES at the reader (G8: an internal codename is never a name).
     Five of them are real observations that cannot reach a parcel -- they are recorded against a
     debtor, a court case, a rail corridor or a county -- and the sixth is not a signal at all. */
  D6_bankruptcy: ["Bankruptcy filing", "the owner or occupying business filed for bankruptcy - recorded against a debtor, not against a parcel", "event"],
  D17_commercial_eviction: ["Commercial eviction case", "an eviction action in the county courts - held at county grain, so it is context rather than parcel evidence", "event"],
  D25_rail_abandonment: ["Rail line abandonment", "a carrier filed to abandon a rail line - a line is not a parcel, so this flags a corridor rather than a site", "event"],
  D8_exit_intent: ["Stated intent to exit", "a filing or public statement that the operator plans to leave the site", "event"],
  D3_seized_auction: ["Seized-property auction", "the property was seized and scheduled for public auction", "event"],
  D5_vacancy: ["Undeveloped land - NOT a signal", "a parcel with no building on it. The operator ruled that the absence of a structure is not evidence an owner wants to sell, so this is never admitted as a signal - it is kept only as sizing context", "state"],
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

/* ============================================================================================
   CHARTS (G18). Operator, 2026-08-17: "if we are intending to use charts like the ones attached,
   they should be labeled and explained fully."

   The previous version drew a bare polyline and nothing else — no axes, no scale, no units, no
   date range. A reader could see that something oscillated and could not tell whether the range
   was 2 GWh or 20 GWh, or what period was covered.

   ⛔ AND IT CONTRADICTED ITS OWN CAPTION. It silently plotted `series.slice(-120)` while the
   caption beside it read "228 months" — so the chart showed 120 of them. That is a correctness
   bug, not a styling one: the picture and the label described different datasets.

   Three things it now always does:
     1. Y axis with real values and the unit, and it is ZERO-BASED by default. Scaling to
        min..max exaggerates variation; a demand series that never drops below 6 GWh looks like it
        collapses to nothing if the axis starts at 6.
     2. X axis showing the ACTUAL first and last period plotted, and the full series unless the
        caller asks otherwise — and if anything IS dropped it is stated on the chart.
     3. A partial-final-period guard. CEMS ends 2026-04 at 54,227 MWh against a typical few
        million — an incomplete month, which drew a cliff that looks like the grid switched off.
        A trailing point below 20% of the previous median is greyed and labelled "partial", never
        silently plotted as a collapse.                                                          */
function chartLine(series, key, opts = {}) {
  const o = Object.assign({ unit: "", color: "#b45309", xKey: "month", zeroBased: true,
                            reading: "", height: 150 }, opts);
  const all = (series || []).filter((r) => r && r[key] != null);
  if (all.length < 2) return `<div class="hint cannot">not enough data to draw</div>`;

  // partial final period: real, and it drew a cliff that read as a collapse
  const vals = all.map((r) => Number(r[key]));
  const mid = [...vals].sort((a, b) => a - b)[Math.floor(vals.length / 2)];
  const partial = vals[vals.length - 1] < mid * 0.2;
  const s = partial ? all.slice(0, -1) : all;
  const v = s.map((r) => Number(r[key]));

  const W = 640, H = o.height, L = 62, R = 10, T = 12, B = 26;
  const hi = Math.max(...v), lo = o.zeroBased ? 0 : Math.min(...v);
  const span = (hi - lo) || 1;
  const x = (i) => L + (i / (s.length - 1)) * (W - L - R);
  const y = (n) => T + (1 - (n - lo) / span) * (H - T - B);

  const si = (n) => Math.abs(n) >= 1e9 ? (n / 1e9).toFixed(1) + "B"
    : Math.abs(n) >= 1e6 ? (n / 1e6).toFixed(1) + "M"
    : Math.abs(n) >= 1e3 ? (n / 1e3).toFixed(0) + "k" : String(Math.round(n));

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => lo + f * span);
  const grid = ticks.map((t) => `<line x1="${L}" y1="${y(t).toFixed(1)}" x2="${W - R}"
      y2="${y(t).toFixed(1)}" stroke="#e8ebf0" stroke-width="1"/>
    <text x="${L - 6}" y="${(y(t) + 3).toFixed(1)}" font-size="9.5" fill="#7a8494"
      text-anchor="end">${si(t)}</text>`).join("");

  const path = v.map((n, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(n).toFixed(1)}`).join("");
  const per = (r) => String(r && r[o.xKey] || "").slice(0, 7);

  return `<figure class="chart">
    <svg viewBox="0 0 ${W} ${H}" role="img" style="width:100%">
      ${grid}
      <path d="${path}" fill="none" stroke="${o.color}" stroke-width="1.4"/>
      <line x1="${L}" y1="${T}" x2="${L}" y2="${H - B}" stroke="#cbd5e1"/>
      <line x1="${L}" y1="${H - B}" x2="${W - R}" y2="${H - B}" stroke="#cbd5e1"/>
      <text x="${L}" y="${H - 8}" font-size="9.5" fill="#7a8494">${per(s[0])}</text>
      <text x="${W - R}" y="${H - 8}" font-size="9.5" fill="#7a8494"
        text-anchor="end">${per(s[s.length - 1])}</text>
      <text x="${L - 6}" y="${T - 3}" font-size="9.5" fill="#556" text-anchor="end"
        font-weight="600">${o.unit}</text>
    </svg>
    <figcaption class="hint">
      ${o.reading ? `<b>${o.reading}</b><br>` : ""}
      Showing <b>all ${fmt(s.length)}</b> periods, ${per(s[0])} to ${per(s[s.length - 1])}.
      Vertical axis ${o.zeroBased ? "starts at zero" : "is not zero-based, so variation looks larger than it is"}${o.unit ? `, in ${o.unit}` : ""}.
      ${partial ? `<br><b>The final period (${per(all[all.length - 1])}) is excluded</b> — it reports
        ${si(vals[vals.length - 1])} against a typical ${si(mid)}, i.e. an incomplete period, and
        plotting it drew a cliff that looked like a collapse.` : ""}
    </figcaption>
  </figure>`;
}

/* kept so older call sites do not break; new code should call chartLine() */
function svgLine(series, key, color = "#0f172a") {
  return chartLine(series, key, { color });
}
/* ---------------------------------------------------------------------------------------------
 * G28 — A DERIVED MW IS NOT A SITE CAPACITY. Say so, everywhere it appears.
 *
 * acres x MW/acre is arithmetic, not engineering. Measured across the 532,868 screener candidates
 * the median is a sane 94 MW and p99 is 710 MW — but the tail is not sane: 2,204 parcels compute
 * above 1,000 MW, 368 above 2,000 MW, and the maximum is 25,428 MW. A 6,374-acre farm multiplied by
 * 4 MW/acre is arithmetically correct and absurd as a presentation: nobody has built a 25 GW campus.
 *
 * ⛔ The fix is NOT to cap the number silently — that hides real land from a reader who may be
 * assembling a multi-phase campus. The fix is to BAND it against what has actually been built and
 * to state the two things the arithmetic ignores:
 *   1. gross parcel area, before setbacks, easements, rights-of-way, internal water, steep slope
 *      and existing structures — real buildable area is always smaller (G28);
 *   2. land is only one gate. Power, water and community posture bind long before acreage does.
 *
 * Returns {band, note} — band is a short label, note is the honest sentence. Both are safe to
 * render raw. G21 reuses this anywhere a derived MW is shown.
 * ------------------------------------------------------------------------------------------- */
function mwReality(mw, density) {
  const m = Number(mw) || 0;
  const d = density ? ` at ${density} MW/acre` : "";
  if (m >= 2000) return { band: "land-area artefact", note:
    `<b>Treat ${Math.round(m).toLocaleString()} MW as an upper bound on LAND, not a site capacity.</b> ` +
    `It is gross acreage${d}, before setbacks, easements, internal water and existing structures — ` +
    `and it exceeds every data-centre campus ever built. Large parcels like this are phased over ` +
    `years, and power will bind long before land does.` };
  if (m >= 1000) return { band: "very large, phase it", note:
    `At ${Math.round(m).toLocaleString()} MW this is at the very top of what exists anywhere — the ` +
    `largest operating campuses are roughly 1,000–2,000 MW. Read it as multi-phase land, not a ` +
    `single build, and note it is gross acreage${d} before setbacks and easements.` };
  if (m >= 25) return { band: "hyperscale-capable", note:
    `Gross acreage${d}, before setbacks, easements, internal water and existing structures, so real ` +
    `buildable capacity is lower. Land is rarely the binding constraint at this size — power is.` };
  return { band: "below the data-centre floor", note:
    `Below the 25 MW datacentre floor${d}, though it may still suit a BESS. Gross acreage, before ` +
    `setbacks and easements.` };
}

document.addEventListener("DOMContentLoaded", () => renderNav());
