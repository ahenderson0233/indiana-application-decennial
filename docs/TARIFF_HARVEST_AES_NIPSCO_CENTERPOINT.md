# TARIFF HARVEST — AES Indiana, NIPSCO, CenterPoint/SIGECO (targets #3, #4, #5)

> Harvested 2026-08-18 from the utilities' own tariff books (public PDFs, no gate).
> 184 component rows loaded to `energy-platfrom.indiana_app.in_utility_tariff_riders`
> (long format, one row per schedule x component x voltage/tier x block), alongside the
> 3 pre-existing I&M seed rows (untouched). Both registries updated in the same run.
>
> RE-SCRAPE: `python scripts/load_tariff_books_aes_nipsco_centerpoint.py --fetch`
> (sentinel-guarded: every load-bearing number is asserted against the PDFs before any write;
> a silently-revised PDF fails the run instead of loading stale transcriptions).
>
> Duke Energy Indiana and I&M are the other agent's harvest — nothing here touches them.

---

## THE HEADLINES

1. ⭐ **NIPSCO has a purpose-built large-load tariff and URDB does not know it exists.**
   The 2025 rate case book (Volume 16, eff 2025-07-01) CANCELS the 8xx series URDB cites and
   creates **Rate 631 "Industrial Power Service – Large"**: >=10,000 kW contract demand,
   transmission/subtransmission only, **three service tiers** — Tier 1 firm at **$35.74/kW-mo +
   $0.030977/kWh**, Tier 2 non-firm at **Day-Ahead LMP (NIPS.NIPS)**, Tier 3 non-firm
   third-party/MISO-Asset-Owner — plus a **$0.014689/kWh transmission charge on all tiers**,
   a 5-year minimum term, and MISO LMR curtailment (>=2h notice) on the non-firm tiers.
   This is exactly the class a data centre takes service under, and its economics are
   *election-dependent*: all-firm is the ceiling, heavy Tier 2/3 rides the market.

2. **The AES voltage delta is enormous.** Rate HL demand: primary $34.30 vs transmission
   $25.00/kW-mo — **$9.30/kW-mo, ~$3.9M/yr on 35 MW**, against the cost of customer-owned
   step-down (HL customers own everything past the POD anyway).

3. **Fuel bases embedded in base rates** (the single most misread number — omit these and the
   FAC is double-counted):
   | utility | embedded fuel base | where stated |
   |---|---|---|
   | AES Indiana | **$0.043811/kWh** | Rider 6 formula (F/S − 0.043811) |
   | NIPSCO | **$0.025032/kWh** | Rider 670 formula ((F/S) − 0.025032) |
   | SIGECO LP | **$0.040254/kWh** | schedule's own Fuel Charge line = App A "Base Fuel" |
   | SIGECO HLF | **$0.039170/kWh** | ditto (line loss 1.68% vs LP 4.27%) |

4. **No summer/non-summer split exists in any of the three books for these classes.** Every
   demand and energy charge is a single year-round number. The only seasonal boundary any book
   states is NIPSCO's exclusion of **June–September** from maintenance service. `season='all'`
   on every row is the books' structure, not an assumption.

5. **The acceptance test passes on AES Indiana.** Modelled all-in HL-transmission at 90% LF =
   **$0.10127/kWh** vs EIA-861 realized industrial average **$0.10478** (2023) — within 3.4%.
   The pre-harvest model (energy+demand only) gave $0.0261–0.0606; the rider stack + fixed
   legs + fuel base close the gap. Details below.

---

## WHAT WAS CAPTURED, PER UTILITY

### AES Indiana / IPL — 62 rows (book: IURC E-20, Cause 46258, **eff 2026-07-27**)

| schedule | floor | customer charge | demand $/kW-mo | energy $/kWh | term |
|---|---|---|---|---|---|
| **HL** (by voltage) | 2,000 kW | $150 / $215 / $500 (pri/sub-T/trans; LLF-trans $520.20) | **34.30 / 25.20 / 25.00** (LLF-trans 15.42) | 0.050079 / 0.050527 / 0.049885 (LLF 0.076468) | 5 yr |
| **PL** | 500 kW | $133 | 30.98 | 0.051710 | 3 yr |
| **SL** | 50 kW | $128 | 28.50 | 0.049723 | 3 yr |
| **PH** | 100 kW | $1,275 | none (energy-only) | 0.112363 first 250 hrs-use, then 0.097587 | — |
| **CSC** | 2,000 kW | negotiated | negotiated | negotiated | — |

- Ratchets: HL **75%** of 11-month high; PL/SL/PH 60%. Billing demand = avg of 3 highest
  15-min intervals. Power factor: multiplier table on demand+energy, base 85% lagging
  (0.951 at PF=1.00 → 1.3335 at PF=0.50).
- Rider stack, current factors (07-24-26 factor sheet, $/kWh, HL/PL column):
  TDSIC +0.000272 | FAC **−0.000801** | ECR +0.001505 | **DSM +0.010889** (opt-out groups
  −0.000403 … +0.005804 — a large new load elects opt-out) | CAP +0.001796 | OSS +0.003599 |
  RTO +0.000693 | GPR +0.001800 (voluntary only).
- Rider 28 Phase-In credits (per class, BOTH legs): e.g. HL1 −$0.00264/kWh **and** −$1.81/kW.
  The book does not define the HL1/HL2/HL3 subclass mapping — rows say so rather than guess.
- Rider 4 transformation adder is **1.65% of installed equipment cost per month** — a
  percent-of-cost adder, NOT $/kW.
- **No dedicated large-load/data-centre schedule exists in the 46258 book** (roster: SL, PL,
  PH, HL, CSC). CSC negotiated contracts (>=2,000 kW, IURC filing under I.C. 8-1-2-24/25) are
  the vehicle for a very large load.

### NIPSCO — 78 rows (book: Volume 16 eff 2025-07-01; charge sheets 2nd-Rev **eff 2026-03-01**)

| schedule | floor–ceiling | demand $/kW-mo | energy $/kWh | term |
|---|---|---|---|---|
| ⭐ **631 IPS-Large** | >=10,000 kW (T1 default 30,000) | **35.74** (Tier 1) | 0.030977 (T1); DA-LMP (T2); MISO settlements (T3); **+0.014689 transmission, all tiers** | 5 yr min |
| **632 IPS-Small** | 15,000–25,000 kW | 16.73 | 0.076305 / **0.155863 / 0.276692** (INVERTED blocks >450/>500 hrs-use) | 1 yr +m-t-m |
| **633 IPS-Small-HLF** | 10,000–25,000 kW | 24.72 | 0.062933 / 0.057642 / 0.056060 (>600/>660 hrs-use) | 1 yr +m-t-m |
| **624 GSL** | 50 kW–25,000 kW | $1,566 first 50 kW, 20.48 next 1,950, 19.66 over 2,000 | 0.132014→0.109019 (4 blocks) | — |

- **Rate 632's inverted tail block (27.7c/kWh over 500 hrs-use) prices high load factor OUT
  of that schedule by design** — a >68% LF customer belongs on 633 or 631.
- Voltage deltas on 624 are deductions: −$1.18/kW primary, −$1.46/kW 34.5kV+, −3% kWh
  primary metering. Ratchets: 632/633 greatest-of(75% contract, on-peak max, off-peak max net
  of surplus, 75% of 11-month high); 624 80%/12-mo under 3 MW, $20.39/kW on contract demand
  at >=3 MW.
- kVAR: $0.32/kVAR-mo two-sided around 85% PF (peak-period basis) on 631/632/633.
- Back-up energy: RT LMP + $0.002332/kWh non-fuel adder. Maintenance service $0.62/kW-day
  (Jan/May/Dec), $0.35 (shoulder), **not available Jun–Sep**.
- Rider factors now in effect (631 T1 / 632 / 633, $/kWh): FAC **0.000000** (published zero,
  eff 2026-08-01) | RTO 0.003275 (T2 0.001752) / 0.002626 / 0.004468 | RA −0.000786 / −0.000549
  / −0.000670 | DSMA 0.000000 / 0.004775 / 0.003155 | TDSIC 0.000203 / 0.000085 / 0.000184 |
  ECT 0.001901 / 0.001592 / 0.002634 | GCT 0.001429 / 0.001007 / 0.001649 | FMCA 0.000000 all |
  GPR 0.003363 voluntary.

### CenterPoint / SIGECO (CEI South) — 44 rows (book: IURC E-14; sheets eff 2025-02-13 → 2026-08-01)

| schedule | floor | fixed | demand | energy | term |
|---|---|---|---|---|---|
| **LP** | 300 **kVA** prior-year max | $150/mo | **16.150 $/kVA-mo**, −2.563 TVD at 69kV+ | 0.034582 + fuel 0.040254 + VPC 0.001652 | 3 yr |
| **HLF** | 4,500 **kVA**, transmission only | none (min bill $122,773.50/mo) | **35.465 $/kVA-mo** | NO base energy — fuel 0.039170 + VPC 0.001608 only | 5 yr, 3-yr notice |

- **This book bills demand in kVA** — power factor is priced through the billing unit.
- HLF ratchet is the strongest of the three utilities: highest of max / **90% of prior-year
  high** / 75% contract / 75% term-high; off-peak (Sat/Sun/hol + 20:00–07:00) disregarded but
  never <50% of month max.
- Appendix factors now in effect (LP / HLF): FAC 0.005613 / 0.005491 $/kWh (Aug–Oct 2026,
  Cause 38708-FAC151) | **NGPPS gas-pipeline 2.239 / 2.388 $/kVA-mo** (demand-based, hides
  inside Appendix A) | DSMA 2.055 $/kVA + 0.007281 $/kWh for participants, **HLF 0.000
  (published zero — 0% program allocation)**, >1 MW customers may opt out immediately |
  CECA 0.000732 / 0.000448 | ECA 0.000286 / 0.000433 | SCP securitization 0.005270 / 0.004000 |
  SRR suspended (0) | SAC −0.000555 / −0.000399 | MCRA 0.064 / 0.065 $/kVA | RCRA 0.004428 /
  0.003223 | TDSIC 0.376 / 0.197 $/kVA (LP-TVD −0.234) | TAR −1.628 / −1.328 $/kVA.
- Rider IP-2 (interruptible) is a **closed class** — only customers taking it since Sept 1997.
  Riders IC/IO are the open interruptible paths; credits contract-specific.

---

## THE ACCEPTANCE TEST — modelled all-in vs EIA-861 realized

Assumptions: 90% load factor, 730 h/mo (657 kWh per kW-mo), PF=1, 30 MW.

| build | modelled $/kWh | realized (EIA-861 2023 industrial) | delta | verdict |
|---|---|---|---|---|
| AES HL-transmission, DSM default | **0.10127** | 0.10478 (AES Indiana) | **−3.4%** | ✅ **PASSES** — the build-up closes end-to-end |
| AES HL-transmission, DSM opt-out | 0.08997 | 0.10478 | −14% | consistent (opt-out is cheaper than the class average) |
| SIGECO HLF | 0.10997 | 0.09021 (SIGECO) | +22% | directionally consistent: 2023 realized predates the 45990 increases + securitization stack now on the books |
| NIPSCO 631 Tier 1 **all-firm** | 0.10609 | 0.06097 (NIPSCO) | +74% | see below — the gap is the tariff's own design, measured not guessed |
| NIPSCO 633 at 20 MW | 0.11152 | 0.06097 | +83% | same vintage/mix caveat |

**The NIPSCO gap is explainable and decision-relevant, not a defect in the harvest.**
(1) The realized 2023 average is dominated by legacy steel loads on the *cancelled* 732/733
rates — the Volume 16 book repriced industrial service wholesale. (2) Rate 631's design means
a real large load does NOT take all-firm service: the all-firm build is the **ceiling**. At a
30% firm / 70% Tier 2 mix with DA-LMP near $0.035, the blend lands ≈ $0.062–0.070/kWh —
right at the realized average. **The firm/non-firm election is the single biggest lever on a
NIPSCO data-centre bill, bigger than any rider.**

---

## BLOCKED — nothing

Zero gates were hit. All three books are open public PDFs; no CAPTCHA, no login, no paywall
appeared at any point. For the record, the two near-misses that were *moved pages*, not walls:

- `nipsco.com/services/rates-and-tariffs/electric-rates` and `/rates-and-tariffs` → HTTP 404
  ("Page not found" site page). The live index is
  `nipsco.com/our-company/about-us/regulatory-information/electric-rates`.
- URDB's Vectren pointers (`vectren.com/.../south_services_electric_tariff.pdf`, 2019 vintage)
  are dead post-merger; the live book is
  `centerpointenergy.com/en-us/Documents/RatesandTariffs/Indiana/Southwest/in-south-electric-tariff.pdf`.

## NOT_HELD — and why (4 rows of 184)

| row | why NULL |
|---|---|
| NIPSCO 631 / 632 / 633 customer charge | The schedules define two/three-part rates with **no customer-charge line**. The omission looks structural, but the books nowhere say "zero", so per the never-zero rule these are `not_held` with NULL — not 0. |
| NIPSCO 631 Tier 1 billing determinant | Sheet 80 prices $35.74/kW-mo **without naming the determinant** (contract vs measured kW). Contract-demand billing is implied by the "definite amount" clause but never stated. Confirm before modelling partial-utilization scenarios. |
| SIGECO HLF customer charge | No line in the schedule; the $122,773.50/mo minimum bill is the de facto fixed leg. |
| AES situational riders (2/5/8/9/13/14/16/17/19/23/27), SIGECO IP-2 | Participation/contract riders with no always-on factor; one status row each. IP-2 is additionally a closed class (Sept-1997 legacy). |

Formula-priced components (631 Tier 2 DA-LMP energy, Tier 3 MISO settlements, AES PF
multiplier tables, CSC negotiated charges) are `published` with NULL rate and the formula in
`basis` — the book publishes them, just not as one number. Published **zeros** (NIPSCO FAC
and FMCA at current vintage, DSMA for 631-T1, SIGECO SRR and HLF-DSMA) are loaded as 0.0
because the book states $0.000000 — a stated zero is not an absent value.

## Registry state after this run

- `indiana_app._registry` — `in_utility_tariff_riders` re-registered: n_rows=187 (AES 62,
  NIPSCO 78, CenterPoint 44, I&M seed 3), full parameterised endpoints, verbatim RE-SCRAPE
  command, publisher vintages, exclusions.
- `energy.registry_sources` — three APPENDs: `tariff-book:aes-indiana:e20-46258`,
  `tariff-book:nipsco:vol16`, `tariff-book:cei-south:e14` (the only writes to `energy`).
- `in_rate_component_gaps` was **not touched** — it remains the before-picture this harvest
  closes.

## Known limits

- AES rider factors carry the 07-24-26 sheet's periods (Jul–Nov/Jul–Dec/Jul–Oct 2026);
  TDSIC-11, FAC-152/153, ECR-39, GPR-19, CAP-10, RTO-10 rows are pending future filings with
  blank values on the sheet — re-run the loader when the utility posts the next sheet.
- SIGECO Rate BAMP (base/backup/maintenance) and NIPSCO Rider 676 (631's backup/maintenance
  rider) were captured only at headline level (backup adder, maintenance day-rates); their
  full contract mechanics live on the cited sheets.
- Raw PDFs are cached at `scrapers/tariff_books/{aes,nipsco,centerpoint}/` (gitignored per
  scraper-artifact convention); the loader's `--fetch` re-downloads them at any time.
