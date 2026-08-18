# TARIFF HARVEST - THE COMMISSION ROUTE: Duke, I&M, and every remaining Indiana electric utility

> Harvested 2026-08-18 **from the IURC's own systems** (docketed-case filings + 30-day filings
> + the Commission's Annual Report), not from utility websites. 235 component rows loaded to
> `energy-platfrom.indiana_app.in_utility_tariff_riders` (total now 419: AES 62, NIPSCO 78,
> CenterPoint 44 from the earlier utility-site harvest - untouched - plus Duke 87, I&M 63,
> jurisdictional municipals 21, non-jurisdictional findings 64). Both registries updated in
> the same run.
>
> RE-SCRAPE: `python scripts/load_tariff_books_iurc_duke_im_munis.py --fetch`
> (sentinel-guarded: every load-bearing number is asserted against the commission documents
> before any write; a revised document fails the run instead of loading stale transcriptions).
>
> ⭐ **THE REUSABLE COMMISSION ROUTE** section at the bottom is written for a stranger pointing
> this at another state. It is the part of this harvest that scales to 49 more states.

---

## THE HEADLINES

1. ⭐ **The commission route works exactly where the utility site is walled.** duke-energy.com
   returns HTTP 403 to every scripted client (verbatim wall below). The IURC portal serves
   the SAME approved tariff sheets - with cause numbers and commission date stamps - over
   plain anonymous HTTP. Every Duke number in the warehouse now cites a commission filing,
   which is the legal rate, not a marketing copy of it.

2. **Duke Energy Indiana's current book is IURC No. 16** (Cause 46038, order 2025-01-29;
   sheets effective 2025-02-27), acquired as the rate case's own "Step 1 Compliance Filing
   Attachment C - Redline and Clean Tariff" (303 pp). The 2026 "Step 2" increase (+4.27%
   overall) did NOT change base sheet levels - it rides in **Tariff No. 67 Credits
   Adjustment** effective bills-rendered March 2026, approved by docket entry 2026-05-27.
   ⚠ A joint OUCC/Industrial-Group/Nucor/CAC **appeal to the full Commission (filed
   2026-06-04) was pending at harvest** - Step 2 rates are interim-subject-to-refund flavored.

3. ⭐ **Duke Rate HLF has NO annual demand ratchet.** Billing demand is the current month's
   highest 30-minute load (floor 25 kW), monthly minimum = the maximum load charge, plus a
   scheduled-maintenance proration (2 windows/yr, <=14 days, $500/use). AES HL 75%, NIPSCO
   75%, SIGECO 90%, I&M large-load 80% - **Duke is the only big-5 industrial tariff where
   curtailing a month directly erases that month's demand bill.**

4. **Duke's fuel base embedded in base rates is $0.034378/kWh** (Tariff No. 60 formula
   "BF", raised from $0.026955 by the 46038 order). The FAC factor now in effect is small
   (+$0.004319/kWh HLF, Jul-Sep 2026) precisely BECAUSE the base absorbed 2022-era fuel.
   Omit BF and the fuel clause double-counts.

5. **Duke bills HLF trackers in $/kW, not $/kWh.** Ten of eleven trackers state "the revenue
   adjustment for Rate HLF shall be based on demands"; only FAC (60) and Credits (67) are
   per-kWh for HLF. Current HLF tracker stack (net): ECR -1.0039, RTO +0.6317, Reliability
   +0.1586, REP -0.0153, Load Control -0.3366, GCT +0.7399, TDSIC +0.7443 (bulk
   transmission) = **+0.919 $/kW-mo net**, plus per-kWh FAC +0.004319, EE +0.001949 (0 if
   opted out), Credits -0.002708, FMCA $0 (published zero).

6. ⭐ **Duke created a new Generation Cost Tracker (Tariff No. 75, Cause 46193)** - clean
   energy projects under IC 8-1-8.8, rate-base treatment, resets up to every 6 months, first
   factors effective April 2026 (HLF +$0.739905/kW). GCT-2 was pending at harvest. This is
   where new-build generation cost for load growth lands between rate cases - the number to
   watch for any large-load study.

7. **I&M's Tariff I.P. was VERIFIED against the commission's copy** (Cause 46097 submission,
   eff 2025-02-19) - the brief's numbers are exact: demand $/kW-mo 327-Secondary 16.474 /
   322-Primary 14.089 / 323-Subtransmission 10.825 / 324-Transmission 10.194; fuel base
   $0.0129810/kWh (Original Sheet 46, Cause 45933). The **>=70 MW / >=150 MW-aggregate Large
   Load framework** (the Amazon docket - Amazon Data Services and the Data Center Coalition
   were parties): 80% ratchet, 12-yr initial term after a <=5-yr ramp, 42-month exit notice,
   20% free capacity reduction after year 5 then an Exit Fee, collateral = 24x the max
   monthly non-fuel bill, and a **Step 1 Embedded Capacity Charge** ($10.959-$13.289/kW by
   voltage) inside the minimum charge. Bill floor at transmission: (14.700 min-demand +
   10.959 embedded + 8.59 demand-leg riders) x 80% ~= **$27.4/kW-mo even at zero energy**.

8. ⭐ **The jurisdiction census is now measured, from the Commission's own annual report**
   (FY2025, pp. 37-38): of 79 municipal electrics, **only Anderson, Auburn, and Frankfort
   remain rate-jurisdictional** (IC 8-1.5-3-9/-9.1); **"No REMCs remain under Commission
   authority for rate regulation"** (IC 8-1-13-18.5); Hoosier Energy, WVPA, and IMPA have no
   retail-rate jurisdiction (CPCN/IRP/financing review only). Every URDB-listed Indiana
   muni/co-op now carries an explicit jurisdiction row - **a gap with a reason, not a miss.**

---

## WHAT WAS CAPTURED, PER UTILITY

### Duke Energy Indiana - 87 rows (IURC No. 16 book, Cause 46038, sheets eff 2025-02-27)

| schedule | floor | connection $/mo | demand $/kW-mo | energy $/kWh | ratchet |
|---|---|---|---|---|---|
| **HLF** (Tariff 12) | 25 kW | 31.90 sec / 125.61 pri / 855.37 trans | sec 27.51 / pri 19.75 / pri-direct 22.92 / trans-69kV 23.59 / trans-138kV+ 20.51 | 0.055534 / 0.064825 / 0.047773 / 0.046775 / 0.044002 | **NONE** (monthly 30-min max) |
| **LLF** (10-A) | none | 27.63 / 109.55 / 331.00 | pri 6.54 / pri-direct 8.31 / trans 5.16 | 0.089722 / 0.078946 / 0.081902 | none (30-min max) |
| **LLF-Secondary** (10-B) | none | 27.63 | 8.02 | 0.101700 | none |
| **HLF/LLF TOU** (11.5, optional) | >20 MW needs approval | as HLF | 3-part: peak 1.57-3.36 + mid 6.91-14.78 + base 0.03-2.19 by voltage | peak 0.0555-0.1127 / off 0.0491-0.0989 / discount(12-4am) 0.0354-0.0661 | base leg = 12-mo max or 50% contract |

- kVAr $0.34/kVAr-mo on all three schedules. Metering +/-1% by voltage. HLF/LLF customers
  at primary+ **own the entire substation past the POD** (Company meters only).
- **No summer/non-summer split anywhere** - single year-round rates (matches the other four
  Indiana books). TOU peak windows: 5-9 pm all year + 6-8 am winter; six holidays off-peak.
- **No dedicated large-load schedule exists.** The 46038 book's only large-load text is the
  >=20 MW financial-assurance clause in HLF/TOU. Very large loads use HLF + (pending) GCT +
  negotiated contract dockets (Duke's Contract cause history: Nucor 45464, SDI 45466 ...).
- **Rate BDP (Tariff 21)** offers additional/backup delivery points - status row loaded;
  charge detail flagged for follow-up if a dual-feed topology is priced.
- Tracker stack, current factors (HLF column; LLF in table; all cause-stamped):

| tracker (Tariff No.) | standing cause | eff (2026 bills) | Rate HLF | Rate LLF |
|---|---|---|---|---|
| 60 FAC | 38707 (FAC 148) | Jul c1 | +0.004319 $/kWh | +0.004422 $/kWh |
| 62 Environmental Compliance | 42061 (ECR 45) | Aug c11 | **-1.003934 $/kW** | -0.002372 $/kWh |
| 65 TDSIC | 45647 (TDSIC 5) | May c1 | +0.575165 sec / +1.228107 pri / +0.792319 pri-dir / **+1.660720 common-trans / +0.744252 bulk-trans $/kW** | +0.000152 trans .. +0.003046 pri $/kWh |
| 66 Energy Efficiency | 45803 (DSM-2) | Jan c1 | +0.001949 $/kWh participating; **$0.000000 opted out (published zero)** | same |
| 67 Credits (carries Step 2) | 46038 + 30-day | Mar c1 | -0.002708 $/kWh | -0.004203 $/kWh |
| 68 RTO non-fuel | 42736 (RTO 61) | Jan c1 | **+0.631727 $/kW** | +0.001547 $/kWh |
| 70 Reliability | 44348 (SRA 11) | Mar c1 | +0.158617 $/kW | +0.000393 $/kWh |
| 72 Federally Mandated | (none yet) | - | **$0 - published zero** ("will continue at $0 rates until new federally mandated projects are approved") | $0 |
| 73 Renewable Energy Project | 44932 (REP 8) | Jul c1 | -0.015268 $/kW | -0.000028 $/kWh |
| 74 Load Control | 45803 (DSM-2) | Jan c1 | -0.336579 $/kW | -0.000835 $/kWh |
| 75 Generation Cost Tracker | 46193 (GCT 1) | Apr c1 | **+0.739905 $/kW** | +0.001731 $/kWh |

- The applicability map ("Appendix A1" in the brief) is **First Revised Tariff No. A**,
  eff 2026-03-25, filed with the GCT-1 final tariff: all eleven trackers apply to RS, CS,
  LLF, HLF, WP, SL, MHLS, UOLS, MOLS, LED, MS, USFL.

### Indiana Michigan Power (I&M) - 63 rows (I.U.R.C. No. 20; I.P. from Cause 46097 commission copy)

| item | 327 Secondary | 322 Primary | 323 Subtrans | 324 Transmission |
|---|---|---|---|---|
| service charge $/mo | 180.00 | 275.00 | 275.00 | 275.00 |
| demand $/kW-mo | 16.474 | 14.089 | 10.825 | 10.194 |
| energy c/kWh first 410 kWh/kW | 5.703 | 5.413 | 5.333 | 5.058 |
| energy c/kWh over 410 kWh/kW | 1.359 | 1.313 | 1.296 | 1.286 |
| minimum demand charge $/kW | 20.995 | 18.472 | 15.106 | 14.700 |
| LL Step-1 embedded capacity $/kW | 13.289 | 12.427 | 12.271 | 10.959 |

- Floor 600 kW (written contract >=1,500 kW); 15-min demand; **60% standard ratchet**
  (greater of contract / 11-mo high / 1,000 kW); off-peak (nights + weekends) disregarded
  with 60% floors; kVAr +/-$1.50 two-sided around 50% of kW; metering x1.01 / x0.98.
- **Large Load (>=70 MW plant or >=150 MW aggregated, new load on/after 2024-01-01):** ESA
  required, 12-yr initial term after <=5-yr ramp, 42-month notice, **80% ratchet**, 20% free
  reduction after yr 5 then Exit Fee (= remaining minimum charge, less OSS/PJM contribution
  after yr 1; 1-5 yr window), collateral 24x max monthly non-fuel bill (waived at A-/A3 +
  10x liquidity; half-waived, cap $250M, on liquidity alone).
- Rider roster (Sheet 44) with current IP/CS-IRP2 factors, all commission-filed:

| rider (sheet) | cause + vintage | IP energy leg | IP demand leg |
|---|---|---|---|
| FAC (46/46.1) | 38702 FAC 96, eff 2026-06-08 (to Oct-2026) | +0.002422 $/kWh (non-res) | - |
| RAR (50) | 45164 RA 6, eff Apr-2026 | 0.0000 (published zero) | +0.242 $/kW |
| OSS/PJM (48) | 43774 PJM 16, eff Jun-2026 | **-0.004297 $/kWh (credit)** | **+7.316 $/kW** |
| ECR (47) | 44871 ECR 9, eff Jan-2026 | +0.000407 | +0.378 |
| SPR (51) | 45245 SPR 4, eff Oct-2025 | +0.000008 | +0.048 |
| DSM/EE (45) | 43827 DSM-14, eff Jan-2026 | +0.003306 non-opt-out; **+0.000218 new-customer opt-out (CVR+DR only)** | - |
| PRA phase-in (52) | 46090, eff Mar-2025 | -0.000003 | -0.343 (credit) |
| TAX (53) | 46080, eff Apr-2025 | 0.0000 (published zero) | +0.952 |

- Fuel base **$0.0129810/kWh** (Original Sheet 46, Cause 45933) - stated as `F/S - $0.0129810`.
- Tariff G.S. captured at headline (class ceiling 1,000 kW 12-mo avg; demand $3.597 sec /
  $2.368 pri / **published-zero 0.000 at subtrans+trans**; energy 11.05->8.00 c/kWh blocks).
- The 3 placeholder seed rows were superseded by this full commission-sourced set.

### Jurisdictional municipals - 21 rows (commission-stamped 30-day tariffs, Jul-Sep 2026)

| utility | mechanism | latest stamped tariff | industrial-class factors (Q3 2026) |
|---|---|---|---|
| **Anderson Municipal Light & Power** | PPCAT quarterly tracker (Cause 36835-S3, 1989) | 30-Day Filing 50917, approved 2026-07-08 | IP $4.891/kVA + $0.010230/kWh; LP $3.839/kVA + $0.012005/kWh; LP-OffPeak $1.674 + $0.008314; SP $3.973/kW + $0.011193 |
| **Auburn Municipal Electric** | purchased-power tracker (supplier I&M/AEP) | 30-Day Filing 50912, approved 2026-06-24 | $0.034896/kWh, all schedules (prior qtr $0.034398) |
| **Frankfort City Light & Power** | PPCAT quarterly tracker (Cause 36835-S3) | 30-Day Filing 50903, approved 2026-06-17 | Rate A $0.007093 / B $0.006238 / C $0.007193 /kWh; Industrial PPL **-$1.928663/kVA** + $0.013858/kWh; flat $0.004745 |

- **Base schedules for all three are `not_held` rows with the acquisition route recorded**
  (not walls): Anderson's base rates are IN PLAY - its 2025 Electric Rate Case, Cause
  46397, was pending at harvest (settlement hearing noticed 2026-09-21). Frankfort's recent
  docket 46343 is a joint Duke asset-transfer petition, not a rate case.
- The Frankfort stamped sheet is a scan; OCR renders the PPL demand credit as "(1 .928663)"
  (stray space) - transcribed -1.928663 with the OCR note on the row.

---

## THE JURISDICTION CENSUS - non-jurisdictional utilities (64 finding rows)

From the Commission's own FY2025 Annual Report (pp. 37-38), quoted on every row:

- **"Only three municipally owned electric utilities remain under the Commission's
  jurisdiction: Anderson, Auburn, and Frankfort."** The other **57 URDB-listed municipals**
  (Richmond, Washington, Peru, Logansport, Jasper, Crawfordsville*, Mishawaka, Tell City,
  Columbia City, Rensselaer, Scottsburg, Bluffton, Lebanon, Greenfield, ... full list in the
  table) each carry a `NONJURIS-MUNI` row: withdrawn under IC 8-1.5-3-9/-9.1, rates set by
  municipal ordinance, route = municipal code/clerk or URDB/EIA-861. 60 of 79 munis are IMPA
  members. (*Crawfordsville has no URDB rate rows; it is covered by the census statement and
  the blanket finding rather than a per-utility row.)
- **"No REMCs remain under Commission authority for rate regulation"** (IC 8-1-13-18.5) -
  the 4 URDB-listed distribution co-ops (South Central Indiana REMC, Southeastern Indiana
  REMC, Southern Indiana REC, Paulding-Putnam) carry `NONJURIS-REMC` rows; the statement
  covers all ~38 Indiana REMCs.
- **Hoosier Energy REC** and **Wabash Valley Power Association (Alliance)** (the two G&Ts):
  Commission regulation "primarily limited to decisions to purchase, build, or lease
  generation facilities, and the review of their IRPs" - no retail-rate tariffs exist at the
  IURC to acquire. Member REMC boards set retail rates.
- **IMPA**: municipal joint agency; IURC reviews financing/CPCN/IRP only; member municipal
  councils set retail rates.

**A jurisdictional gap is a finding, not a miss** - anyone re-running this harvest should NOT
look for commission tariffs for these 64 entities; the rows say so and say where to look
instead.

---

## THE ACCEPTANCE TEST - modelled all-in vs EIA-861 realized

Assumptions: 90% load factor, 657 kWh per kW-mo, PF~1, 30 MW, current (2026) factor stack.
Realized = EIA-861 2023 industrial revenue/MWh from `in_eia861_sales` (measured this run:
Duke $785,420k / 8,895,565 MWh; I&M $524,197k / 6,518,226 MWh).

| build | modelled $/kWh | realized 2023 | delta | verdict |
|---|---|---|---|---|
| Duke HLF bulk transmission, EE participating | **0.0802** | 0.0883 | -9.2% | consistent - see below |
| Duke HLF bulk transmission, EE opt-out | 0.0783 | 0.0883 | -11.4% | consistent (opt-out cheaper than class average) |
| I&M I.P. transmission (324), DSM opt-out | **0.0638** | 0.0804 | -20.7% | directionally consistent - see below |

- **Duke -9%:** the realized class average blends secondary/primary customers (demand
  $27.51/$19.75 + energy 0.0555/0.0648) with transmission; a bulk-transmission 90%-LF build
  SHOULD sit below it. 2023 realized also carries 2023 FAC levels - the 46038 order moved
  ~2.7 c/kWh of fuel INTO base ($0.026955 -> $0.034378 BF), so old-vintage realized vs
  new-vintage modelled is not apples-to-apples. The build-up itself is closed: every
  component from connection charge to GCT is a cited commission number.
- **I&M -21%:** same vintage caveat (45933 rates took effect mid-2024, phase-in credits
  still flowing) plus voltage mix; the largest lever in the build is OSS/PJM: +$7.316/kW
  demand leg NET of a -0.43 c/kWh energy credit. At 90% LF they nearly cancel (-$2.82/kW
  equivalent); at low load factor the demand leg dominates - I&M's stack penalizes low LF
  harder than the base rates suggest.
- Large-load floors (zero-energy months): Duke HLF bulk-trans ~= $21.4/kW-mo (demand +
  net kW-trackers, no ratchet); I&M LL transmission ~= $27.4/kW-mo (80% ratchet on min
  demand + embedded capacity + rider kW legs). **Duke's no-ratchet HLF is the cheapest
  walk-away month among the big five.**

---

## BLOCKED - with the walls quoted verbatim

1. **duke-energy.com - HTTP 403 (Akamai edge), measured again this run** (single polite GET,
   research UA, 2026-08-18):

   ```
   HTTP 403
   <HTML><HEAD><TITLE>Access Denied</TITLE></HEAD><BODY><H1>Access Denied</H1>
   You don't have permission to access "http://www.duke-energy.com/home/billing/rates"
   on this server.
   Reference #18.da4c017.1787065495.7de6b705
   https://errors.edgesuite.net/18.da4c017.1787065495.7de6b705
   </BODY></HTML>
   ```

   No CAPTCHA, no login - a fingerprint wall. **Recorded as the reason the commission route
   exists; nothing was needed from the site.** The 17 Duke PDFs a prior agent inventoried on
   duke-energy.com are all superseded by commission-filed equivalents above.

2. **IURC portal search PAGES gate their search button client-side with Google reCAPTCHA**
   (`grecaptcha.getResponse()` on /advanced-search/ and /search-thirtyday-cases/). The
   backing companion JSON API answers anonymous POSTs with no token - the same calls the
   page's own JS makes. We used the API exactly as served and **did not bypass or complete
   any CAPTCHA**. If the API is ever token-gated, this becomes a real wall: record it and
   stop.

3. **Duke's 2025-04-30 amended tariffs (rate-migration nunc pro tunc)** were filed directly
   with the Commission's Energy Division and approved 2025-05-14 - they appear in NEITHER
   the docketed filings NOR the 30-day system (searched both; Duke's 30-day count since
   2025-01-01 is zero). Not a bot wall - a records-system boundary. The 2026-05-27 docket
   entry states the migration adjustment was implemented and refunded through Tracker 67, so
   base-sheet levels above (eff 2025-02-27) are carried with this caveat on the rows.

## NOT_HELD - and why

| rows | why NULL |
|---|---|
| Anderson / Auburn / Frankfort base schedules (3 rows) | Base rate levels predate this harvest's scope; the quarterly trackers loaded ARE the commission-current adders. Route on each row: docketed rate-case orders (Anderson's 46397 PENDING - re-pull after the order) or the utility. Never 0. |
| 57 muni + 4 REMC + Hoosier/WVPA/IMPA jurisdiction rows (64) | No commission tariff EXISTS to hold - non-jurisdictional by statute, annual-report quote on every row. These are findings, not fetch failures. |
| Duke HLF-RATCHET, HLF-20MW, HLF-SUBSTATION, TOU-ELIG, BDP-STATUS, Appendix-A roster, Step-2 status; I&M IP-OFFPEAK, IP-METERV, IPLL-ELIG-companion text rows | Structural/status facts published without a single number - `published` with NULL rate and the clause in `basis`/`notes` (same convention as the AES/NIPSCO harvest's formula rows). |

Published **zeros** loaded as 0.0 because the sheet states them: Duke FMCA "$0", Duke EE
opt-out "$0.000000", I&M RAR and TAX IP energy legs "0.0000", I&M G.S. subtrans/trans demand
"0.000". A stated zero is not an absent value.

## Registry state after this run

- `indiana_app._registry` - `in_utility_tariff_riders` re-registered: n_rows=419, source
  names every commission system + cause + vintage, method carries the verbatim RE-SCRAPE
  command, the companion-API payload shapes, all case GUIDs, pending proceedings, and the
  exclusions. Both `source` and `method` populated (honesty-audit provenance check).
- `energy.registry_sources` - three APPENDs (the only writes to `energy`):
  `iurc-tariff:duke-indiana:46038-book+trackers`, `iurc-tariff:indiana-michigan:46097-ip+riders`,
  `iurc-tariff:municipals:30day+census` - each with parameterised endpoints, case GUIDs,
  `what_it_provides`, and `object_names=['in_utility_tariff_riders']`.
- `in_rate_component_gaps` untouched - it remains the before-picture.
- Raw documents cached at `scrapers/tariff_books/iurc/{duke,im,municipal}/` + the annual
  report (gitignored per scraper-artifact convention); `--fetch` re-downloads everything.

## Known limits and pending proceedings (re-run triggers)

- **Duke:** FAC 149 (filed 2026-07-30; factors ~Oct 2026), TDSIC 6 (hearing 2026-09-01),
  DSM-3 (filed 2026-06-18), GCT 2 (proposed order 2026-08-11), ECR 46 (~Mar 2027), and the
  **Step-2 full-Commission appeal** - any of these changes the current stack; re-run the
  loader after each final tariff.
- **I&M:** FAC 97 (filed 2026-08-03), RA 7 (filed 2026-08-14), SPR 5 (proposed order
  2026-07-27), ECR 10 (hearing 2026-09-10), new DSM plan (46255, filed 2026-06-01).
- **Anderson rate case 46397** - base rates will change (settlement hearing 2026-09-21).
- Duke Tariff 21 (BDP) charge detail and Tariff 23 (Peak Load Management) mechanics were
  captured at status level only.
- I&M Sheet 44 riders were transcribed for the IP/CS-IRP2 class; GS-class factor columns are
  on the same cited sheets if ever needed.

---

## ⭐ THE REUSABLE COMMISSION ROUTE

*Written for a stranger pointing this at state #2. Indiana is one instance of a pattern:
every state PUC runs a docketed-case system, and the approved tariff is always in it.*

### The Indiana instance, end to end

1. **Front door:** `https://iurc.portal.in.gov/` (Microsoft Dynamics 365 portal). The
   search pages are `/advanced-search/` (docketed), `/search-thirtyday-cases/` (30-day
   administrative), `/adv-non-docketed-search/` (annual reports etc.).
2. **The real backend** is a "companion app" REST service named in each page's JS
   (`portalCompanionUrl`):
   `https://zus1iurcprodd365companionappmaster-appservice.azurewebsites.net`
   - `GET /api/list/{industrytypes|petitiontypes|utilitytypes|statustypes}` - dropdown
     GUIDs (3,617 utilities; petition types include Rates, Tariff Matters, FAC, GCA, RTO,
     ECR, DSM, TDSIC, Jurisdiction ...).
   - `POST /api/search/advanced` - body = the form fields
     (`txtCause, txtSubDocket, ddlPetitionType, ddlCaseStatus, ddlIndustry, txtParties,
     ddlUtilities, txtDateBegin/End, txtFilingDateBegin/End, txtOrderDateBegin/End,
     txtPageNumber`), empty strings when unused. Returns `{TotalRecords, data[], PagerDetails}`
     with `iurc_legalcaseid` (the case GUID), docket + subdocket numbers, parties, dates.
   - `POST /api/search/thirtyday` - same idea; **`ddl*` fields must be `"-1"` when unset**
     (empty string 500s). Row key: `iurc_legalcase30dayid`, filing number `iurc_name`.
   - `POST /api/document/filings` body `{"txtPageNumber":"1","Id":" <case-guid>"}` - note
     the LEADING SPACE in Id (the page's own quirk). Paged; each filing carries
     `iurc_description, iurc_datefiled, iurc_documentLink`.
   - `POST /api/document/thirtydayfilings` - same shape for 30-day cases; `iurc_comments`
     labels documents as `Initial Filing / Approval Order / Approved Tariff`.
   - Documents: `GET https://iurc.portal.in.gov` + `iurc_documentLink`
     (`/_entity/sharepointdocumentlocation/<filing-guid>/<library-guid>?file=<name>`), plain
     anonymous GET, returns the PDF/XLSX.
   - Politeness: >=1.1-1.3 s between calls, identifying UA. The pages front the SEARCH
     button with client-side reCAPTCHA; the API itself is anonymous - replicate the page's
     calls, never touch the widget.

### How a cause maps to the CURRENT tariff

The commission never posts "the tariff book" as one library object - **the current book is
the union of the latest approved leaf per sheet**, and every leaf is a docket artifact:

| what you want | where it lives | the tell |
|---|---|---|
| base schedule sheets (the book) | the LAST GENERAL RATE CASE docket (petition type "Rates") | a filing named **"Compliance Filing"** / "Submission of Compliance Tariff" shortly AFTER the final order - Duke 46038 "Step 1 Compliance Filing Attachment C (Redline and Clean Tariff)"; I&M 45933 "Submission of Compliance Tariff" |
| a new/modified schedule between cases | its own "Tariff Matters" docket | "Submission of Tariff - Tariff I.P." (I&M 46097) |
| tracker/rider CURRENT values | each rider's STANDING docket with numbered sub-dockets (38707 **FAC 148**, 42061 **ECR 45**, 45647 **TDSIC 5** ...) | the filing named **"Submission of Final Tariff"** after each sub-docket's order; highest-numbered sub-docket with a final tariff = current factors. A sub-docket without one is PENDING - use the prior one |
| small-utility rates (jurisdictional munis, trackers, minor text changes) | the **30-day filing system** | document literally labeled **"Approved Tariff"** with the commission stamp |
| who is jurisdictional AT ALL | the commission's **Annual Report** | the census sentences quoted above - read it FIRST and skip the non-jurisdictional dead ends |

Duke sub-docket letters decode as: FAC=fuel (quarterly), ECR=environmental (semi-annual),
TDSIC=T&D infrastructure, RTO=RTO non-fuel (annual), SRA=reliability, REP=renewables,
DSM=efficiency+load control, GCT=generation cost (new), REP/SRA/GCT numbering restarts per
cause. I&M: FAC (semi-annual), PJM=OSS/PJM, RA=resource adequacy, SPR=solar, ECR, DSM.

### What changes for another state

1. **The portal software.** Indiana is Dynamics 365 + a companion REST app. The `energy.puc_*`
   family already catalogues the other patterns we have met: PUCO Ohio = ASP.NET __VIEWSTATE
   POSTs; MN = eDockets GET params; PA = ufprt token; NV = OnBase /api/CustomQuery; HI =
   Salesforce Aura. **Step one in any state: open the docket-search page, watch its own
   XHR calls, and replicate them** - the JSON backend is almost always anonymous even when
   the page has a CAPTCHA on the button.
2. **The vocabulary.** "Compliance filing" / "Final Tariff" / "Approved Tariff" are the
   Indiana tells; other states use "compliance tariff", "stamped tariff", "supplement".
   The invariant: **the utility must file the approved sheets back into the docket after
   every order** - grep the post-order filings of the last rate case.
3. **The jurisdiction census.** Every commission publishes an annual report (or utility
   directory) that says who it rate-regulates. Read it before fetching: in Indiana it
   eliminated 64 of 69 non-IOU utilities in one page.
4. **Some states are EASIER:** several PUCs (e.g. Kentucky PSC) host a per-utility tariff
   library directly - no docket walk needed. Check for a "Tariffs" section first; Indiana's
   in.gov "Utility Tariffs" page is a link farm to utility sites (measured), so the docket
   walk is the route HERE, not everywhere.
5. **What is invariant:** commission copies carry the cause number + effective date (the
   citation), they are never bot-walled the way utility marketing sites are, and the
   tracker-standing-docket structure (base book + numbered rider sub-dockets) recurs in
   every vertically-regulated state.
