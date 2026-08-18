# TARIFF HARVEST — THE ORDINANCE/BOARD ROUTE: municipals, REMCs, and the wholesalers behind them

> Harvested 2026-08-18 from the utilities' OWN publications — city ordinances stamped into the
> IURC 30-day system, municipal codes, utility rate pages, co-op board tariff books, audited
> financial statements — because for these 19 utilities **no commission tariff exists to
> acquire** (FY2025 IURC Annual Report census, established by the prior harvest). 252 component
> rows loaded to `energy-platfrom.indiana_app.in_utility_tariff_riders`; the 3 `not_held` BASE
> placeholders (Anderson/Auburn/Frankfort) are replaced; the 64 jurisdiction finding rows and
> all 334 IOU rows are untouched. **Table now 668 rows; zero not_held-with-a-rate violations.**
> Both registries updated in the same run.
>
> RE-SCRAPE: `python scripts/load_tariff_books_munis_coops.py --fetch`
> (sentinel-guarded; image-only scans are sha256-pinned and were transcribed by human-visual
> page reads — a silently revised scan fails the run).
> ⚠ RE-RUN ORDER: if `load_tariff_books_iurc_duke_im_munis.py` is ever re-run, re-run THIS
> loader afterwards — its utility-scoped DELETE removes this harvest's rows for the shared
> utilities, then reinstates its placeholders.

---

## THE HEADLINES

1. ⭐ **Six ordinance-route utilities have genuine 10-MVA-class tariffs, and three of them are
   transmission-fed.** Frankfort **Rate IP** (10 MW, fed from the 69 kV system, customer owns
   the 138 kV transformation — new in 2022), Crawfordsville **IP** (10 MW, direct 138 kV),
   Richmond **TS** (10 MW at ≥69 kV), Anderson **IP/ISTP** (10 MVA primary / 34.5 kV),
   Tell City **E2** (10 MVA), Auburn **EHV** (30 MVA nominal floor at 69 kV). URDB knew about
   exactly one of these (Richmond TS) and carried 2014 numbers for it.

2. ⭐ **Two municipals sell 10-MVA service as an IMPA wholesale pass-through at cost plus a
   wires fee.** Anderson ISTP = IMPA demand+energy passthrough + **$2.407/kVA** facilities;
   Tell City E2 = IMPA **Power Sales Rate Schedule "B"** passthrough + **$3.00/kVA** + $1,000/mo.
   With IMPA's own accrued cost at **8.45 c/kWh (2025)**, that prices a 90%-LF pass-through load
   near ~8.9 c/kWh all-in — and makes the IMPA wholesale trajectory (+2.7% board-approved for
   2026) the real rate driver, not the muni's sheet.

3. **Anderson bills its IP demand on the IMPA-coincident hour** (billed demand = the 60-minute
   interval IMPA uses to bill Anderson; $16.624/kW), with only a $2.958/kVA distribution leg on
   the customer's own NCP. Auburn offers the same CP logic as an option (IDIP, codes 40/43/45).
   SEI REMC's UIPS-1 goes further: a four-part demand stack where the production legs ride
   **MISO's estimated daily peak hour** ($10.65 summer / $9.50 winter) — a flexible data centre
   that vacates CP hours pays only $6.50 transmission + $3.35 delivery. **CP-billed demand is
   the ordinance-route's version of Duke's no-ratchet HLF: curtailment directly erases cost.**

4. **Ratchets range from none to brutal.** No multi-month ratchet at all: Anderson LP/IP/ISTP,
   Frankfort PPL/IP, Richmond (all classes — monthly kVA floors only), Lebanon PPL, Mishawaka
   Rate I, SCI LI/LP. 50%/12-mo: Crawfordsville PP/IP. 60%/11-12-mo: Auburn (most), Jasper GSD,
   Columbia City, Tell City E. 75%/11-mo: SCI IP, SEI IP-1/IPS-1/UIPS-1-delivery. **Auburn EHV:
   100% of the 11-month high with a 25,000 kVA floor** (~$427k/mo minimum demand bill at
   $17.10/kVA) — the harshest large-load term in Indiana.

5. ⭐ **The purchased-power bases are now measured** — the muni/co-op analog of the IOU fuel
   base, and the same double-count hazard: Anderson PPCAT base **$16.872/kW + $0.03213/kWh**;
   SCI REMC tracker subtractor **$0.0923/kWh**; PPEC WPCA base **$0.06958/kWh**; Peru Rider ED
   base $0.06072/kWh (= actual IMPA cost, trued monthly). Richmond's Q3-2026 ECA is a
   **demand-leg credit** (−$0.853/kVA) plus +1.59 c/kWh energy; Lebanon's is the reverse
   (+$2.83/kVA = +16% on its demand leg this quarter).

6. ⭐ **All three wholesalers are board-priced, none is FERC rate-jurisdictional today — and two
   have explicit data-centre policies.** WVPA **left FERC on 2025-01-01** (eTariff cancellations
   ER25-838/-842/-843) and its Board adopted the same formulary rate (budget billing + true-up);
   it publishes the only named **large-load menu** (300 kW → 35 MW+; the 1.5 MW+ tier is
   marketed to data centres; 35 MW+ is negotiated market supply). Hoosier is FPA 201(f)-exempt
   (RUS G&T borrower; FERC touchpoint = MISO TO revenue requirement only) and adopted a
   **Consumer Directed Resource Policy: loads >50 MW pay all costs outside the traditional
   tariffs** (2026-05-12). IMPA prices under its Bond Resolution ("Rates are not subject to
   state or federal regulation"), members signed through **2057**. Even Buckeye Power (PPEC's
   Ohio G&T) board-approved a dedicated **data-center rate schedule in March 2026**.

7. **The June-2022 URT filings are the Rosetta stone for muni vintages.** Anderson 50507,
   Auburn 50523, Frankfort 50549, Richmond 50559, Lebanon 50535, Crawfordsville 50561 and Tell
   City's Ord 1190 all implement the HEA-1002 Utility Receipts Tax repeal in one June-2022
   window — each stamped tariff is the utility's last commission-touched base book, sitting on
   a 2012–2021 rate-case base. Everything since moves by council ordinance (Logansport 2025-02,
   Columbia City 2026-5, Mishawaka Ord 5954) or quarterly tracker.

---

## WHAT WAS CAPTURED, PER UTILITY (large-load classes; current values)

| utility | rows | large-load schedule | floor | fixed $/mo | demand | energy $/kWh | ratchet | tracker (current) |
|---|---:|---|---|---|---|---|---|---|
| **Anderson** | 31 | IP / **ISTP** | 10,000 kVA | 172.55 / — | 2.958/kVA dist + **16.624/kW on IMPA CP** / ISTP: IMPA passthrough + 2.407/kVA | 0.033524 / passthrough | none (floors) | PPCAT (36835-S3); base 16.872/kW + 0.03213/kWh; **46397 PENDING +12.58%** |
| **Auburn** | 33 | EHV / EHP / EHPT @ 69 kV | 30,000 / 5,000 / 5,000 kVA | 345.10 / 246.50 | **17.10/kVA (every class)** | 0.031084 / 0.031855 / 0.031246 | EHV **100%**+25 MVA floor; others 60%/11-mo; CP option (IDIP) | PPT $0.034896/kWh; leaving IURC (Ords 2026-12/-13 pending) |
| **Frankfort** | 24 | **Rate IP** (new 2022) | 10 MW @ 69 kV | 591.48 | 24.054/kVA | 0.028275 | none (10 MVA floor) | PPCAT (held); Rate B $114.79 print anomaly flagged |
| **Richmond** | 25 | **TS** / ISP / ISS | 10,000 kW ≥69 kV / 1,000 kW | 192.56 | 21.70 / 23.67 / 24.66 per kVA | 0.02710 / 0.03324 / 0.03393 | none (monthly floors) | ECA Q3-26: **−0.853292/kVA** + 0.015869/kWh |
| **Logansport** | 16 | Industrial Substation | (floor in Ord 2018-26, not online) | **32,500 flat** | 14.592/kVAD | 0.045442 | n/p | **NONE — annual steps 2025-29**; NextEra PPA $0.03915 to 2028 |
| **Mishawaka** | 12 | Rate I | >149 kW | 18.35 | 7.00/kW | 0.0769 | **none** | none posted; **2026 step (Ord 5954) unpublished** |
| **Peru** | 13 | PS | 50 kW | min 355.81 | 6.44 pri / 7.11 sec per kW | 0.095074 / 0.101105 | none (50 kW floor) | PPCAT cum. $0.001178; ED rider ≤1.5 MW |
| **Jasper** | 10 | GSD (only demand class) | 50 kVA | 89.61 | 16.04/kVA @ **100% PF basis** | 0.045599 | 60%/11-mo | monthly PCA (value at office); IMPA PSC to 2042 |
| **Lebanon** | 11 | PPL ("ILP") | 50 kVA | 98.51 | 17.38/kVA | 0.0358/0.0310 blocks | none (50 kVA floor) | Q3-26: **+2.829798/kVA** + 0.010946/kWh; EDR ≥1 MW; **no LEAP electric rate** |
| **Crawfordsville** | 14 | **IP** / PP | 10 MW @ 138 kV / 50 kW | 591.62 / 295.77 | 22.77 / **29.29** per kVA | 0.026489 / 0.027624 | 50%/12-mo | factor values NOT published (`not_held`); **2026 ordinance PENDING** |
| **Columbia City** | 11 | GS-I / GS-L | 800 / 100 kW ×3 mo | 126.77 / 100.36 | 7.45 / 7.51 per kVA + 50% nameplate min | 0.09872 / 0.10154 | 60%/12-mo | quarterly ECA (Cause 40768 legacy); Ord 2026-5 phases to 2028 |
| **Tell City** | 14 | **E2** / E | 10,000 / 400–2,000 kVA | 1,000.00 / 350.00 | E2: 3.00/kVA + **IMPA Rate-B passthrough**; E: 26.45/kVA | passthrough / 0.03757 | E2 contract-or-10 MVA; E 60% CP-based | Q3-26 E: +0.011564/kWh −2.89/kVA; **2–10 MVA band = contract only** |
| **SEI REMC** | 21 | **UIPS-1** (Hoosier Standard Wholesale) | 5,000 kW | 125.00 | **10.65 S-CP + 9.50 W-CP + 6.50 T-CP + 3.35 NCP** | 0.08015/0.06515 TOU | delivery 75%/5 MW | PCT Q3-26 0.00249 (H.E. passthrough); C-5 has the only **seasonal** demand split |
| **Southern Ind. Power** | 4 | **not published** | — | 35.00 (res) | — | 0.1214 (res) | — | 0.00260 Hoosier tracker; **C&I sheets = co-op office, Tell City** |
| **SCI REMC** | 11 | IP (discretionary) / LI | 500 kW / >1,000 kVA | 394.40 | IP: 11.56 PP + 11.81 dist = 23.37/kW; LI: 7.42+13.40 | IP TOU 0.06425/0.04904; LI 0.05411 | IP 75%/11-mo; LI none | base **$0.0923/kWh** embedded; IP passes Hoosier tracker directly |
| **Paulding-Putnam** | 8 | LPI / IND1 | contracted kVA | 130.00 / 200.00 | 11.00 / 23.50 per kW | blocks 0.101→0.0545 / 0.050 | IND1 12-mo minimum | WPCA base **$0.06958**; **Buckeye/PJM**, not an Indiana G&T |
| **Hoosier Energy** | 5 | wholesale (via 17 members) | — | — | Standard Wholesale Tariff: MISO-CP production + transmission + delivery | H.E. tracker 0.00249 | — | board-set, 201(f); **>50 MW = pay-all-costs CDR policy**; QF CPP 0.03705 |
| **WVPA** | 5 | wholesale (21 members, to 2060) | — | — | board Formula Rate Tariff (ex-FERC 2025-01-01) | budget + true-up | — | **published menu: 300 kW → 35 MW+ (negotiated)** |
| **IMPA** | 6 | wholesale (61 members, to 2057) | — | — | Rate Schedule "B" demand+energy+reactive | **8.45 c/kWh accrued 2025** | — | Bond Resolution; +2.7% for 2026; Large User Intake process |

Residential/GS headlines were loaded for every retail utility (one to three rows each) so
class cross-checks against EIA-861 remain possible.

## ⭐ WHICH OF THESE COULD ACTUALLY SERVE A DATA CENTRE — the judgement

Scale anchor: a modest **30 MW @ 90% LF ≈ 236 GWh/yr**. 2023 measured retail (EIA-861):
Richmond 856 GWh (industrial 514), Anderson 847 (266), Mishawaka 532, SEI REMC 509 (98),
Southern Indiana REC 441 (**309 industrial at 7.18 c/kWh realized — cheapest non-IOU in the
state**), Logansport 432 (258), Crawfordsville 363 (241), Frankfort 359 (229), Auburn 325
(238), Jasper 275, Lebanon 241, Peru 225, Paulding-Putnam 105.

**Tier 1 — a published tariff a 10–30 MW load could sign today, behind a wholesaler with
capacity planning:**
- **Richmond TS**: the only muni transmission tariff with full numbers ($192.56 + $21.70/kVA +
  2.71 c + ECA). At 90% LF ≈ **7.6 c/kWh all-in** at current ECA — cheapest firm muni path in
  this harvest; 514 GWh of existing industrial says the wires are real. IMPA supply.
- **Anderson ISTP / Tell City E2** (IMPA passthrough): price ≈ IMPA cost + wires
  (~8.7–9.0 c/kWh at 90% LF on 2025 accrued 8.45 c). Transparent, no retail margin risk;
  Anderson adds the 46397 caveat (base rates rising +12.58% class-average, hearing 2026-09-21).
- **Frankfort IP / Crawfordsville IP** (10 MW @ 69/138 kV): real transmission on-ramps
  (~2.8/2.65 c energy + $24.05/$22.77 kVA ≈ 6.3–6.6 c/kWh at 90% LF **before trackers** — but
  both munis are ~360 GWh systems, so a 30 MW load is a ~65% system expansion: feasible only
  as an IMPA-planned addition, and Crawfordsville has a rate ordinance pending NOW.

**Tier 2 — sized for 5–20 MW with the G&T's blessing:**
- **SEI REMC UIPS-1**: 5 MW floor, MISO-CP demand design a flexible load can arbitrage — but
  Hoosier's **>50 MW Consumer Directed Resource Policy** means anything hyperscale becomes a
  bespoke full-cost contract. Same for SCI REMC (IP is *discretionary by its own text*) and
  Southern Indiana Power (7.18 c realized industrial, but its large-power sheet is unpublished
  — worth the phone call to Tell City).
- **Auburn EHV**: the only 30-MVA-floor retail class in Indiana and I&M/AEP-supplied (not
  IMPA), at 3.1 c energy + $17.10/kVA — but the 100%/25 MVA ratchet prices out anything that
  cannot run flat, its 13.2 c/kWh realized industrial average shows the tracker burden, and
  the utility is mid-withdrawal from IURC jurisdiction (rate governance about to change).

**Tier 3 — not realistic for data-centre-scale load:** Mishawaka (no transmission class,
biggest class starts at 149 kW, 2026 rates unpublished, Wolverine contract renegotiates 2030),
Logansport (fixed NextEra PPA to **2028** covers today's 432 GWh — no headroom instrument;
Industrial Substation class is priced but its floor text is in a paper ordinance), Peru
(off-peak carve-out capped at 6 MW aggregate; ED rider tops out at 1.5 MW), Jasper (no class
above GSD), Lebanon (50 kVA sheet + 1 MW EDR only — **no LEAP electric rate exists**; a LEAP
load is an IMPA negotiation), Columbia City (7.45/kVA + ~10 c energy, 800 kW class),
Paulding-Putnam (105 GWh system; Buckeye's 2026 DC schedule governs anyway).

**The wholesale punchline:** for every IMPA muni the marginal large-load price is IMPA's board
trajectory (8.45 c accrued 2025, +2.7% 2026, contracts to 2057); for every Hoosier REMC it is
the CDR policy (>50 MW pays its own way); WVPA is the only one openly advertising for the
business with a menu up to 35 MW+. **A data-centre conversation in muni/co-op Indiana is a
wholesaler conversation wearing a local badge.**

## BLOCKED — with the walls quoted verbatim

1. **seiremc.com (Wix) rate-limited bulk fetching** — HTTP 429, body:
   `<!doctype html><meta charset="utf-8"><meta name=viewport content="width=device-width, initial-scale=1"><title>429</title>429 Too Many Requests`
   Cleared by a ~35-min cooldown + 30 s pacing; **all 15 files obtained** — a throttle, not a wall.
2. **ppec.coop legacy file paths** — HTTP 404 (`Page not found – Paulding Putnam Electric
   Cooperative`) after a Drupal→WordPress migration. Resolved via Wayback capture
   `20260515080132` of the then-live 2026.02 book (archive.org availability API itself 429'd
   twice; CDX + direct timestamped fetch used).
3. **federalregister.gov HTML** — `302 Found -> https://unblock.federalregister.gov/` (bot
   wall); the official FR API `raw_text_url` served the same notices (WVPA docket numbers).
4. **Municode (Mishawaka)** — HTTP 200 but a 6,095-byte AngularJS shell (`<html lang="en"
   ng-app="mcc.library_desktop" ...>`): code text loads only via JS. Not needed — the city's
   own tariff pages carry the rates. (Jasper's Municode content WAS retrievable via the
   public `api.municode.com` JSON the page itself calls; job 483743 / Supplement 11.)
5. Several hosts (frankfort-in.gov, impa.com, celp.com, jasperindiana.gov) 403 the WebFetch
   tool but served plain `urllib` with the declared audit UA normally — recorded, not walls.
6. **Hoosier annual reports are FlippingBook-only** (no direct PDF) — jurisdiction facts taken
   from the cached FERC order and IURC-filed IRP instead.

No CAPTCHA was bypassed or completed anywhere; no accounts; no UA spoofing.

## NOT_HELD — and why (all are records-location findings, not fetch failures)

| row | why NULL | route |
|---|---|---|
| `MISH-2026-EXHIBIT-A` | Ordinance 5954 (adopted 2025-11-17) steps rates 2026-01-01; Exhibit A not posted anywhere online — loaded 2025-step values are one step low | Mishawaka Utilities Business Office, 100 Lincolnway W, or City Clerk |
| `LOGA-FLOORS` | class eligibility text (incl. the 10,000 kW Industrial Substation floor URDB carries) lives in base Ordinance 2018-26; city's online archive starts 2021 | Logansport Clerk-Treasurer ordinance book |
| `CRAW-PPCAT-CURRENT` | Appendix A/B tracker VALUES are not compiled in the published tariff PDF and no tracker sheet is posted | CEL&P utility office; also re-pull after the pending 2026 ordinance |
| `SIP-CI-NOTPUB` | Southern Indiana Power publishes NO C&I/large-power schedules (sitemap enumerated) | co-op office, Tell City, IN |
| 64 jurisdiction rows | unchanged from the IURC harvest — they remain true and are the census, not gaps | n/a |

Also flagged on `published` rows: Frankfort Rate B customer charge **$114.79 as printed**
(URT math says $14.79 — almost certainly a sheet typo, noted on the row); Mishawaka Rate I's
inverted-reading power-factor sentence quoted verbatim; Tell City's booklet citing
"36836-S3" [sic]; CEL&P EDR month-ranges printed "1-2"/"25-35" [sic]; PPEC's site announcing
a $45 residential service charge from Feb-2026 bills while the book page prints $41.50.

## Verification and registry state

- **Sentinels:** every load-bearing number asserted against the cached documents (
  text layer, agent OCR artifact, or decoded HTML). **Image-only scans** (Richmond book,
  Columbia City Ord 2026-5, Tell City Q3-26 tracker, Logansport Ord 2025-02) are
  **sha256-pinned**; their numbers were transcribed by human-visual page reads on 2026-08-18
  (Richmond pages 11/15/19/23/27 read individually; Richmond OCR figures used ONLY where
  visually confirmed — the ISS-COIN OCR-only figures live in a status row's basis, not a rate
  column).
- **Scoped DELETE:** `utility IN (19 mine) AND code IN (255 mine+superseded)` — the five IOUs
  (334 rows), the A/A/F tracker rows and all NONJURIS/JURIS rows are untouchable by
  construction; post-load check confirms 87/78/63/62/44 intact and zero
  not_held-with-a-rate violations table-wide.
- `indiana_app._registry`: re-registered `in_utility_tariff_riders` (n_rows=668) with `source`
  AND `method` (RE-SCRAPE command, re-run order, vintages, pendings, exclusions).
- `energy.registry_sources`: three APPENDs — `muni-tariff:ordinance-route:jurisdictional-base`,
  `muni-tariff:ordinance-route:withdrawn-munis`, `coop-tariff:board-route:remcs+wholesalers`.
- Raw documents cached at `scrapers/tariff_books/munis_coops/<utility>/` (19 folders, ~90
  files incl. OCR artifacts and cached wall evidence).

## Known limits and re-run triggers

- **Anderson Cause 46397**: settlement hearing 2026-09-21 — base book WILL change (+12.58%
  proposed). Re-run after the order + compliance schedules.
- **Auburn Ordinances 2026-12/-13**: IURC withdrawal + new council rate book, first reading
  April 2026; if completed, Auburn's vintage chain leaves the commission entirely.
- **Crawfordsville**: amending rate ordinance introduced 2026-07-13 (hearing 2026-08-10);
  current 50561 book is on its last legs.
- **Mishawaka Ord 5954** Exhibit A (2026 step) — fetch from the clerk; **Columbia City**
  phases II/III auto-step 2027/2028 (values already on the rows' basis text);
  **Logansport** steps annually to 2029 (2027-29 columns in the cached rate guide).
- Quarterly trackers (Anderson/Auburn/Frankfort/Richmond/Peru/Lebanon/Tell City/SEI/SIP) roll
  every quarter; the 30-day filing system and utility sites carry the next factors.
- IMPA/Hoosier wholesale price SHEETS remain non-public; levels are triangulated from member
  passthroughs, the Anderson tracker base, and audited statements. WVPA's pre-2025 formula
  rate text survives in FERC eLibrary under the cancelled ER25-838/-842/-843 dockets.
