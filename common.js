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
/* HTML escape, shared. ⚠ NOT named `esc`: market.html declares its own `const esc` at module
   scope, and a second top-level `esc` here would be a duplicate declaration that takes that page
   down - its own comment warns of exactly this. app.js had NO html escaper at all, which is how
   an `esc(...)` added to the dossier threw "esc is not defined" at open time and made the Dossier
   button do nothing. Parse-checking did not catch it; rendering the document did. */
function escHtml(x) {
  return String(x == null ? "" : x).replace(/[<>&]/g, (m) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[m]));
}

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
  D16_catastrophic_damage: ["Building destroyed or majorly damaged", "the city's own damage assessment recorded this structure as Destroyed or Major - an owner is far more likely to sell the land than rebuild", "event"],
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


/* ============================================================================================
   TARIFF COSTING ENGINE - ONE copy, shared by the Market page and the map console's dossier.
   ============================================================================================
   ⛔ IT LIVES HERE BECAUSE TWO COPIES DRIFT. This repo has the receipts: the eligibility
   vocabulary was maintained separately in the exporter and the renderer, and when the exporter
   learned the words "ceiling" and "exceeds" the renderer did not - so a 1,000 kW schedule kept
   being quoted to a 300 MW load. The dossier needs exactly the arithmetic the Market page uses,
   and the only safe way to give it that is to have one function.

   The rules encoded below were each earned by a wrong number; the reasoning is kept inline
   because the reasoning is the part that stops it being re-broken:
     - only components that BILL enter a total; a qualifying floor is not a charge
     - block ladders are ALTERNATIVES across slices, never addends
     - TOU energy bills its own share of the year; TOU DEMAND bills full kW in every period,
       because a flat 24/7 load peaks in all of them
     - reactive and optional-service charges are excluded, counted, and disclosed
     - an inherited schedule leg is still a schedule leg, not a rider
   ============================================================================================ */
const LLF_MAX = 0.15;          // low-load-factor service is for customers under ~15% LF
const VOLT_FAMILY = {
  transmission:    "Transmission (138 kV and above)",
  subtransmission: "Sub-transmission (around 34 kV)",
  primary:         "Primary distribution (4-13 kV)",
  secondary:       "Secondary (below 4 kV)",
  any:             "Any service voltage",
};
/* Asymmetric on purpose - below a utility's blended industrial average has always meant a
   MISSING CHARGE in this codebase, while above is what a new large-load schedule does against
   decades of embedded cost. */
const BAND_LO = -20, BAND_HI = 60;

function allocate(blocks, total, scale) {
  let cost = 0, used = [];
  for (const b of blocks) {
    const lo = b.block[1] == null ? 0 : b.block[1];
    const hi = b.block[2] == null ? Infinity : b.block[2];
    const qty = Math.max(0, Math.min(total, hi) - lo);
    if (qty <= 0) continue;
    cost += qty * scale * b.rate;
    used.push({ ...b, amt: qty * scale * b.rate });
  }
  return { cost, used };
}

function costAt(sch, volt, kW, kWh, lf) {
  /* A component applies at this class if it names no class at all, or names THIS one. A
   * multi-class component ("transmission and primary") carries the families it named, and
   * applies only at those - letting it bill everywhere put Duke HLF at 44.31 c/kWh. */
  const famOf = (k) => (sch.volt_classes.find((x) => x.key === k) || {}).family || k;
  const at = (c) => {
    if (c.volt) return c.volt === volt;
    if (c.volt_named && c.volt_named.length) return c.volt_named.includes(famOf(volt));
    return true;
  };
  const legs = { fixed: 0, demand: 0, energy: 0 };
  const riders = { fixed: 0, demand: 0, energy: 0 };
  const lines = [];
  let reactive = 0, conditional = 0;
  const monthlyKWh = kWh / 12, hoursUse = kW ? monthlyKWh / kW : 0;

  /* An INHERITED schedule leg is still a schedule leg. A large-load framework rides on a parent
   * (I&M IP-LL on IP), and the exporter re-labels the inherited components so the reader can see
   * where they came from — "IP (underlying schedule)". Bucketing on `origin !== "schedule"` then
   * counted the parent's own demand and energy as RIDERS, which is why IP-LL showed ENERGY $0
   * across all four service classes while its Riders column carried $153.89M. The money was
   * right and every column it sat in was wrong. */
  const isScheduleLeg = (c) => c.origin === "schedule"
                        || String(c.origin).endsWith("(underlying schedule)");
  const push = (c, amt, leg) => {
    (isScheduleLeg(c) ? legs : riders)[leg] += amt;
    lines.push({ ...c, amt, leg });
  };

  // --- blocked legs first: group by (origin, kind) and allocate the ladder ---
  const blocked = sch.components.filter((c) => c.block && c.bill && at(c) && !c.conditional
                                      && !(c.low_lf_only && lf > LLF_MAX));
  const groups = {};
  for (const c of blocked) (groups[`${c.origin}|${c.block[0]}`] ||= []).push(c);
  for (const key of Object.keys(groups)) {
    const g = groups[key].slice().sort((a, b) => (a.block[1] ?? 0) - (b.block[1] ?? 0));
    const kind = g[0].block[0];
    let r;
    if (kind === "kwh_month")      r = allocate(g, monthlyKWh, 1);
    else if (kind === "hours_use") r = allocate(g, hoursUse, kW);
    else                           r = allocate(g, kW, 1);          // kW slices
    const months = kind === "kw" ? 12 : 12;                          // both bill monthly
    for (const l of r.used) push(l, l.amt * months, kind === "kw" ? "demand" : "energy");
  }

  // --- unblocked legs ---
  for (const c of sch.components) {
    if (c.block || !c.bill || !at(c)) { if (c.reactive) reactive++; continue; }
    if (c.reactive) { reactive++; continue; }
    /* An OPTIONAL service riding inside the schedule is not part of a firm 24/7 bill. NIPSCO
     * puts maintenance service ($0.62/kW/DAY, unavailable June-September, capped at 60 days a
     * year), back-up service for cogenerators, and an affiliate-transfer premium in among its
     * firm rates; billing them as mandatory added $106.22M/yr to Rate 632 and drove it to
     * +241%. Skipped and COUNTED, never silently dropped - the same treatment reactive charges
     * get, for the same reason. */
    if (c.conditional) { conditional++; continue; }
    /* A charge that forks on load factor INSIDE one schedule. Southeastern REMC's C-5 prices
     * summer demand at 15.50 $/kW for customers at or above 300 kWh/kW and 8.10 for those
     * below, both carrying season='summer' and the SAME component name - so applying both
     * charged one customer twice across the same four months. They are alternatives; at 85%
     * load factor ours is unambiguously the upper fork. */
    if (c.low_lf_only && lf > LLF_MAX) { conditional++; continue; }
    let amt = 0, leg = "demand";
    /* A time-of-use ENERGY rate bills only the kWh that falls in its own period. For a flat
     * 24/7 load that share is fixed by the clock, so it is arithmetic rather than a guess.
     * DEMAND is different and simpler: a constant load peaks in EVERY period, so each
     * time-differentiated demand charge bills the full kW - which is precisely why TOU is
     * usually a poor deal for a data centre, and worth showing rather than hiding. */
    if (c.bill === "energy")          { amt = c.rate * kWh * (c.tou_share ?? 1); leg = "energy"; }
    else if (c.bill === "demand")     { amt = c.rate * kW * (c.months ?? 12); }
    else if (c.bill === "demand_kva") { amt = c.rate * kW * (c.months ?? 12); }
    else if (c.bill === "demand_day") { amt = c.rate * kW * 365; }
    else if (c.bill === "fixed")      { amt = c.rate * 12; leg = "fixed"; }
    push(c, amt, leg);
  }
  const total = legs.fixed + legs.demand + legs.energy
              + riders.fixed + riders.demand + riders.energy;
  return { legs, riders, lines, reactive, conditional, total,
           cents: kWh ? (total / kWh) * 100 : null };
}

/* ============================================================================================
   THE DOSSIER'S TARIFF BLOCK  (audit D-1, D-3)
   ============================================================================================
   The Power Plan used to print "No component-level Indiana tariff is held yet" and "we
   deliberately do not print a $/kWh here", while `app.js` did not even load the tariff payload.
   Both statements were true when written and false by 2026-08-18: 668 components across 73
   utilities, 22 costed from their own books at every service voltage.

   ⭐ The second claim's REASONING was the part that had gone stale. It declined to print a rate
   because only "a blended county average" was available - which is exactly what the rate engine
   removed. The dossier already names the serving utility by point-in-polygon; this joins that
   name to that utility's own book.

   Lives here, not in app.js, for two reasons: the arithmetic must be the SAME engine the Market
   page uses (see the note above costAt), and app.js is boot-critical and cannot be rendered in a
   headless sandbox - so the logic sits in a file that CAN be exercised from market.html.
   ============================================================================================ */

/* territory name (in_territories) -> the tariff payload's utility, or null.
   The two vocabularies match ZERO times out of 145, so the exporter ships an enumerated map
   (scripts/utility_names.py) and stamps `territory_names` on each utility. Never fuzzy-matched:
   a wrong utility here would price the wrong company's book under this parcel's address. */
function tariffForTerritory(TF, territoryName) {
  if (!TF || !TF.utilities || !territoryName) return null;
  const want = String(territoryName).trim().toUpperCase();
  return TF.utilities.find((u) => (u.territory_names || [])
    .some((t) => String(t).trim().toUpperCase() === want)) || null;
}

/* The schedules a load of this size can actually TAKE - eligibility is a ceiling as well as a
   floor, and a schedule the customer is 300x too large for is not an option. */
function eligibleSchedules(u, kW, lf) {
  return (u.schedules || []).filter((sc) =>
    sc.costable && !sc.by_contract
    && !(sc.low_load_factor && lf > LLF_MAX)
    && !(sc.max_kw != null && kW > sc.max_kw)
    && !(sc.min_kw != null && kW < sc.min_kw));
}

/* What this parcel's utility would charge, priced through the SAME engine as the Market page.
   Returns null when we hold no book, so the caller can say so rather than invent a number. */
function tariffQuote(TF, territoryName, mw, lf) {
  const u = tariffForTerritory(TF, territoryName);
  if (!u) return null;
  const kW = mw * 1000, kWh = kW * 8760 * lf;
  const out = { utility: u.utility, urdbOnly: false, benchmark: u.benchmark_cents, rows: [] };

  const elig = eligibleSchedules(u, kW, lf);
  if (!elig.length) {
    /* No BOOK schedule fits. URDB is a floor and is labelled as one - it is flattened, carrying
       no riders, no fixed charges and no seasonal blocks, and the rider stack alone is worth
       1.5-2 c/kWh where we hold it. */
    const ur = (u.urdb || []).filter((r) => /industrial/i.test(r.sector || "") && r.e_lo != null);
    if (!ur.length) return { ...out, none: true };
    const priced = ur.map((r) => {
      const dem = r.d_max != null ? Number(r.d_max) * kW * 12 : 0;
      return { name: r.name, hasDem: r.d_max != null,
               total: dem + Number(r.e_lo) * kWh };
    }).sort((a, b) => a.total - b.total);
    return { ...out, urdbOnly: true,
             rows: priced.map((x) => ({ ...x, cents: (x.total / kWh) * 100 })) };
  }

  for (const sc of elig) {
    const classes = (sc.volt_classes || []).length ? sc.volt_classes
                                                   : [{ key: "any", family: "any", label: "any" }];
    for (const vc of classes) {
      if (/low[- ]load[- ]factor|\bllf\b/i.test(vc.label || "") && lf > LLF_MAX) continue;
      const r = costAt(sc, vc.key, kW, kWh, lf);
      /* the leg guard, unchanged: a row missing a whole billing leg never shows a rate */
      const missing = (sc.has_demand_leg !== false && (r.legs.demand + r.riders.demand) === 0)
                   || (sc.has_energy_leg !== false && (r.legs.energy + r.riders.energy) === 0);
      if (missing || r.cents == null || r.cents < 2) continue;
      out.rows.push({ code: sc.code, name: sc.name, largeLoad: !!sc.large_load,
                      voltage: vc.label || VOLT_FAMILY[vc.family] || vc.key,
                      total: r.total, cents: r.cents,
                      ridersNotHeld: !!sc.riders_not_held,
                      riders: r.riders.fixed + r.riders.demand + r.riders.energy });
    }
  }
  out.rows.sort((a, b) => a.cents - b.cents);
  return out.rows.length ? out : { ...out, none: true };
}

/* The Figure 3 cell and its "what it means" column, as [held, meaning]. */
function tariffCells(q, mw, lf) {
  const money = (n) => Math.abs(n) >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : `$${fmt(Math.round(n))}`;
  if (!q) {
    return [`<span class="cannot">utility not resolved, so no tariff can be looked up</span>`,
            `Figure 1 could not name the serving utility, so there is no book to price. Resolve
             the utility first - the rate follows from it.`];
  }
  if (q.none) {
    return [`${q.utility}<div class="hint"><span class="cannot">no rate we hold applies at
             ${fmt(mw)} MW</span></div>`,
            `We hold no schedule this load is eligible for at this utility. That is usually a
             CEILING - small municipal schedules cap out well below a data centre - and it means
             the rate would be individually negotiated.`];
  }
  if (q.urdbOnly) {
    const b = q.rows[0];
    return [`${q.utility}<div class="hint">no tariff book held &mdash; URDB floor</div>
             <b>&ge;${b.cents.toFixed(2)}&cent;/kWh</b> &middot; &ge;${money(b.total)}/yr
             <div class="hint">${String(b.name || "").slice(0, 40)}${b.hasDem ? "" : " · no demand charge captured"}</div>`,
            `<b>A floor, not a bill.</b> URDB is flattened &mdash; no riders, no fixed charges, no
             seasonal blocks. Where we hold both, the rider stack alone adds roughly
             <b>1.5&ndash;2&cent;/kWh</b>. Use it to decide whether this utility is worth a call.`];
  }
  const best = q.rows[0], worst = q.rows[q.rows.length - 1];
  const spread = worst.total - best.total;
  const ll = q.rows.find((r) => r.largeLoad);
  /* ⛔ THE SPREAD IS NOT ALWAYS A VOLTAGE SPREAD, and calling it one was wrong. Where a utility
     publishes no service-class split - most municipals and co-ops - every row keys to "any", and
     the gap between cheapest and dearest is a gap between SCHEDULES. Printing "6.61c at any
     against 8.16c at any ... service voltage is a site decision" attributed a schedule choice to
     a voltage choice and told the reader to go and check a thing that does not vary here. */
  const named = (r) => r.voltage && !/^any$/i.test(r.voltage);
  const byVoltage = best.code === worst.code && named(best) && named(worst);
  const at = (r) => named(r) ? ` at ${r.voltage}` : "";
  return [
    `${q.utility}<div class="hint">${q.rows.length} priced option(s) at ${fmt(mw)} MW,
       ${(lf * 100).toFixed(0)}% load factor</div>
     <b>${best.ridersNotHeld ? "&ge;" : ""}${best.cents.toFixed(2)}&cent;/kWh</b> &middot;
     ${best.ridersNotHeld ? "&ge;" : ""}${money(best.total)}/yr
     <div class="hint">cheapest: <b>${best.code}</b>${best.largeLoad ? " (large load)" : ""}${at(best)}</div>
     ${ll && ll.code !== best.code ? `<div class="hint">large-load schedule <b>${ll.code}</b>:
       ${ll.cents.toFixed(2)}&cent;</div>` : ""}
     ${q.benchmark != null ? `<div class="hint">industrial customers here actually pay
       ${q.benchmark}&cent; (EIA-861)</div>` : ""}`,
    `${q.rows.length === 1
       ? `<b>One priced option.</b> ${best.cents.toFixed(2)}&cent;/kWh on <b>${best.code}</b>${at(best)}.`
       : byVoltage
       ? `<b>Service voltage is a site decision worth ${money(spread)} a year here</b> &mdash;
          ${best.cents.toFixed(2)}&cent; at ${best.voltage} against ${worst.cents.toFixed(2)}&cent;
          at ${worst.voltage}. Which one you can take is set by what is in the ground near the
          site, not by which is cheapest.`
       : `<b>Which schedule you qualify for is worth ${money(spread)} a year here</b> &mdash;
          ${best.cents.toFixed(2)}&cent; on <b>${best.code}</b>${at(best)} against
          ${worst.cents.toFixed(2)}&cent; on <b>${worst.code}</b>${at(worst)}.
          ${named(best) || named(worst) ? "" : "This utility publishes no service-voltage split, so the choice is the schedule, not the bus. "}Eligibility
          is set by contract demand and load factor, so confirm which one you actually qualify for.`}
     Every figure includes the schedule's own charges <b>and every rider that
     attaches to it</b>${best.ridersNotHeld
       ? ", except this schedule's riders, which the book says exist but we do not hold - so treat it as a floor"
       : ""}.`];
}

/* =============================================================================================
   G74 - SiteStore: the user's own sites, held across PAGES but cleared on a REFRESH.
   =============================================================================================
   Operator, 2026-08-19: *"ANY Excel sheet should be able to be inputted and saved to the
   application (locally, always resetting when the page is refreshed, but should stay when
   changing between the application's pages)."*

   Read that requirement carefully, because the obvious implementation gets it WRONG.
   `sessionStorage` survives a refresh - it is cleared only when the tab closes. So sessionStorage
   ALONE gives "stays across pages" and fails "resets on refresh".

   The distinction the operator asked for is available, and exactly:
       performance.getEntriesByType("navigation")[0].type
   returns "reload" when the user pressed refresh and "navigate" when they followed a link. So the
   store lives in sessionStorage and is DROPPED on boot if this page load was a reload. That is
   the stated behaviour rather than the nearest convenient one.

   Nothing leaves the browser. The site is static and has no server to send a file to; the store
   is per-tab and dies with it.
   ============================================================================================= */
const SITE_STORE_KEY = "in_user_sites_v1";
const SiteStore = (() => {
  let dropped = false;
  try {
    const nav = performance.getEntriesByType("navigation")[0];
    // `back_forward` is a restore, not a refresh, so it KEEPS the sites - the user is navigating.
    if (nav && nav.type === "reload") { sessionStorage.removeItem(SITE_STORE_KEY); dropped = true; }
  } catch { /* private mode or no Navigation Timing: fall through, the store just stays empty */ }

  const read = () => {
    try { return JSON.parse(sessionStorage.getItem(SITE_STORE_KEY) || "null"); } catch { return null; }
  };
  return {
    /** Rows as loaded, each already carrying _row and _status. Never null. */
    rows: () => (read() || {}).rows || [],
    /** {filename, sheet, sheetCount, loadedAt, mapping, n, placed, unplaced} or null. */
    meta: () => { const s = read(); return s ? s.meta : null; },
    has: () => ((read() || {}).rows || []).length > 0,
    save(rows, meta) {
      const blob = JSON.stringify({ rows, meta: { ...meta, n: rows.length, loadedAt: new Date().toISOString() } });
      try {
        sessionStorage.setItem(SITE_STORE_KEY, blob);
        return { ok: true };
      } catch (e) {
        // sessionStorage is ~5 MB. A big sheet must FAIL LOUDLY here rather than half-save and
        // reappear truncated on the next page, which would look like data loss with no cause.
        return { ok: false, error: `too large to keep across pages (${(blob.length / 1048576).toFixed(1)} MB; the browser allows about 5). It is loaded on THIS page only.` };
      }
    },
    clear() { sessionStorage.removeItem(SITE_STORE_KEY); },
    /** true if this page load discarded a store because the user pressed refresh. */
    wasDroppedByReload: () => dropped,
  };
})();

/* ---------- G74: header detection and column mapping -----------------------------------------
   "ANY Excel sheet" means the column names CANNOT be hardcoded. Two things go wrong in real
   files and both are handled here:
     1. The header is not row 1. Exports routinely carry a title, a blank line and a date stamp
        above it. findHeaderRow() picks the first row that looks like a header - mostly non-empty,
        mostly text, and no duplicate names.
     2. The names are the user's, not ours. guessColumns() proposes a mapping and the UI lets the
        user override every one of them, because a guess presented as a fact is worse than a
        question. */
function findHeaderRow(rows) {
  const limit = Math.min(rows.length, 20);
  let best = 0, bestScore = -1;
  for (let i = 0; i < limit; i++) {
    const r = (rows[i] || []).map((c) => (c === null || c === undefined ? "" : String(c).trim()));
    const filled = r.filter((c) => c !== "");
    if (filled.length < 2) continue;
    const text = filled.filter((c) => !Number.isFinite(Number(c))).length;
    const uniq = new Set(filled.map((c) => c.toLowerCase())).size;
    // reward: wide, textual, no repeats. penalise being far down the sheet.
    const score = filled.length + text * 2 + (uniq === filled.length ? 3 : -3) - i * 0.5;
    if (score > bestScore) { bestScore = score; best = i; }
  }
  return best;
}

const COLUMN_ROLES = [
  // ⚠ point_y / point_x are Esri's own coordinate column names and appear on almost every
  // shapefile-derived export. They must be EXACT aliases: their only distinguishing token is a
  // single letter, and single letters are barred from token matching (see guessColumns).
  ["lat",     "Latitude",   ["lat", "latitude", "y", "ycoord", "y_coord", "lat_dd", "latdec",
                             "northing", "point_y", "centroid_y", "center_y", "intptlat"]],
  ["lon",     "Longitude",  ["lon", "lng", "long", "longitude", "x", "xcoord", "x_coord", "lon_dd",
                             "londec", "easting", "point_x", "centroid_x", "center_x", "intptlon"]],
  ["name",    "Site name",  ["name", "site", "site_name", "sitename", "project", "project_name", "label", "id", "site_id"]],
  ["address", "Address",    ["address", "addr", "street", "site_address", "full_address", "location"]],
  ["county",  "County",     ["county", "county_name", "cty"]],
  ["acres",   "Acres",      ["acres", "acreage", "area_acres", "size_acres", "parcel_acres", "gis_acres"]],
  ["mw",      "MW wanted",  ["mw", "size_mw", "capacity_mw", "load_mw", "demand_mw", "mw_required"]],
];

/* THREE PASSES, STRICTEST FIRST, and the ordering is the point. A single pass lets a loose match
   on an early role steal a column that a later role would have matched exactly.

   Measured against a realistic export whose header reads "Site Latitude (WGS84)": a one-pass
   prefix/suffix matcher finds NOTHING for lat or lon, because `site_latitude_wgs84` neither
   equals `latitude` nor starts or ends with it. Pass 2 splits the header into TOKENS and matches
   any token, which is what real headers need.

   ⚠ Token matching is restricted to aliases of 3+ characters. `x` and `y` are legitimate
   coordinate names on their own, but as tokens they appear inside things like "max_mw" and would
   place every site in the wrong hemisphere without ever looking wrong on screen. */
function guessColumns(header) {
  const norm = header.map((h) => String(h ?? "").trim().toLowerCase()
    .replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, ""));
  const toks = norm.map((h) => h.split("_").filter(Boolean));
  const out = {};
  const taken = new Set();
  const claim = (role, i) => { if (i >= 0 && !taken.has(i)) { out[role] = i; taken.add(i); return true; } return false; };
  const free = (k) => !taken.has(k) && out[k] === undefined;

  for (const [role, , aliases] of COLUMN_ROLES)                                       // 1. exact
    claim(role, norm.findIndex((h, k) => !taken.has(k) && aliases.includes(h)));
  for (const [role, , aliases] of COLUMN_ROLES) {                                     // 2. token
    if (out[role] !== undefined) continue;
    const long = aliases.filter((a) => a.length >= 3);
    claim(role, toks.findIndex((t, k) => !taken.has(k) && t.some((x) => long.includes(x))));
  }
  for (const [role, , aliases] of COLUMN_ROLES) {                                     // 3. affix
    if (out[role] !== undefined) continue;
    const long = aliases.filter((a) => a.length >= 3);
    claim(role, norm.findIndex((h, k) => !taken.has(k) && h
      && long.some((a) => h.startsWith(a) || h.endsWith(a))));
  }
  // A longitude found without a latitude (or the reverse) is almost always a mis-hit rather than
  // a sheet that really carries one axis. Dropping the lone one puts the question to the user.
  if ((out.lat === undefined) !== (out.lon === undefined)) {
    delete out.lat; delete out.lon;
  }
  return out;
}

/** Rows-of-arrays + a mapping -> rows-of-objects, keeping EVERY original column as well.
    Nothing is dropped: a row we cannot place is kept and labelled, because ss13(2) upload parity
    was closed on exactly that behaviour. */
function mapSheetRows(rows, headerRow, mapping) {
  const header = (rows[headerRow] || []).map((c, i) => {
    const s = String(c ?? "").trim();
    return s || `column_${XLSXLite.colName(i)}`;
  });
  const out = [];
  for (let i = headerRow + 1; i < rows.length; i++) {
    const r = rows[i] || [];
    if (!r.some((c) => c !== null && c !== undefined && String(c).trim() !== "")) continue;
    const rec = { _row: i + 1 };
    header.forEach((h, k) => { rec[h] = r[k] ?? null; });
    for (const [role] of COLUMN_ROLES)
      if (mapping[role] !== undefined && mapping[role] !== "") rec["_" + role] = r[Number(mapping[role])] ?? null;
    out.push(rec);
  }
  return { header, records: out };
}
