# TARIFF BOOK SCRAPE — the target register and the agent brief

> **Purpose.** `urdb_rates` gives us energy + demand + voltage category + kW qualifying floors, but
> **not** the customer charge, the rider stack or the seasonal split. Those three are the whole gap
> between a bracket and an itemised, CPS-grade rate model (see `BACKLOG.md` §G17). They are in the
> utilities' own tariff books, which are **public PDFs — not a gated source.**
>
> Written 2026-08-17 so the morning's agents start from a measured target list instead of a search.

---

## ⛔ RULES AN AGENT DOES NOT INHERIT — RESTATE THESE IN EVERY BRIEF

- **`energy` is READ-ONLY.** Everything we build goes to `energy-platfrom.indiana_app`. The single
  permitted write to `energy` is an APPEND to `energy.registry_sources`.
- **Every table gets a `_registry` row in the same run that writes it**, and per G16 that row must be
  enough for a stranger to RE-RUN the work: exact parameterised URL, endpoint kind, the loader
  command verbatim as `RE-SCRAPE COMMAND: …`, the publisher's own vintage (not our pull timestamp),
  and what was excluded and why.
- **Newly scraped data updates BOTH registries** in the same run — `indiana_app._registry` and an
  APPEND to `energy.registry_sources`.
- **Scrape only what the source permits.** No CAPTCHA bypass, no UA spoofing, no account creation.
  **A gated source recorded BLOCKED with its wall quoted verbatim is a SUCCESS**, not a failure.
- **Never guess a column name or a unit.** Read the schema; read the rate sheet's own units line.
- **Unpublished is NULL, never 0.** A rider the book does not state is `value_status='not_held'`
  with a NULL rate. Treating an absent rider as zero is the exact error that would make our modelled
  rate look cheaper than reality.

---

## THE TARGETS, RANKED — measured from `in_urdb_rates`, 2026-08-17

Ranked by what a data-centre or BESS developer would actually interconnect to: breadth of industrial
schedules, and how many carry **transmission** or **primary** service voltage.

| # | utility | rates held | industrial | transmission-voltage rates | primary | highest kW floor URDB shows | why it is ranked here |
|---|---|---:|---:|---:|---:|---:|---|
| **1** | **Duke Energy Indiana** | 164 | 104 | **39** | 66 | 25 kW | Largest Indiana footprint and **the most transmission-voltage schedules of any utility**. URDB's 25 kW floor is implausible for their large-load rate — **treat that as a URDB gap to close from the book**, not as fact |
| **2** | **Indiana Michigan Power (I&M / AEP)** | 137 | 63 | 18 | 32 | 1,000 kW | The **PJM/AEP footprint in northeast Indiana** — the same territory as the case-23 bus work (G40). Its book URL is already known, below |
| **3** | **Indianapolis Power & Light (AES Indiana)** | 126 | 50 | 10 | 30 | 2,000 kW | Marion County — the densest parcel and seller-intent coverage we hold |
| **4** | **NIPSCO** | 92 | 60 | 5 | 5 | **15,000 kW** | ⭐ **The only Indiana utility whose URDB rows already expose a true large-load floor** — *Industrial Power Service* at 15 MW and *High Load Factor Industrial* at 10 MW. Best single check that our class-derivation logic is right |
| **5** | **CenterPoint / Southern Indiana Gas & Electric (Vectren)** | 38 | 32 | 0 | 4 | 4,500 kW | Southwest Indiana; no transmission-voltage rate held, so the book is the only route |

**Municipals and co-ops worth a second pass, not a first one** — Richmond (10,000 kW floor, 1
transmission rate), Anderson (10,000 kW), Logansport (10,000 kW), Southeastern Indiana REMC
(5,000 kW). Small, but each already advertises a large-load floor.

---

## WHAT EACH SCRAPE MUST EXTRACT

Driven by `CPS_35MW_Rate_Model.xlsx`, which is the reference build-up. Per **tariff schedule**:

| field | why it matters | note |
|---|---|---|
| **customer / service availability charge** ($/month) | the fixed leg; trivial at 300 MW but required to close the model | ❌ absent from URDB entirely |
| **demand charge, SUMMER** ($/kW-month) | the largest single component at high load factor | ❌ URDB is flattened on season |
| **demand charge, NON-SUMMER** ($/kW-month) | ditto | ❌ |
| **which months count as summer** | CPS is Jun–Sep = 4 months | ❌ |
| **demand charge BY SERVICE VOLTAGE** | transmission vs primary vs secondary. CPS's delta was $0.50/kW-mo → **$210,000/yr on 35 MW** — the number weighed against interconnection capex | partially in URDB via `voltagecategory` |
| **transformation / step-down adder** ($/kW-month) | applies where the customer takes service below the metered voltage | ❌ |
| **energy charge** ($/kWh), and any block structure | URDB gives a min–max range only | partial |
| ⭐ **fuel base ALREADY EMBEDDED in the base rate** ($/kWh) | **the single most misread number.** The fuel adjustment is `(actual fuel cost − this embedded base) × kWh`. Omit it and the fuel clause is double-counted | ❌ |
| ⭐ **the rider stack** — FAC, RTO/PJM or MISO cost, DSM/EE, environmental compliance, regulatory-asset amortisation | **this is the gap.** `in_rate_component_gaps` bounds it: modelled energy+demand gives $0.0261–0.0606/kWh at 300 MW against a realized $0.0804 | ❌ only 3 rows held, 1 with a rate |
| **demand ratchet** (e.g. 80% of summer peak) | makes a demand charge quasi-fixed — it is why winter curtailment saves less than it appears | ❌ |
| **eligibility floor** (kW) and **minimum contract term** (years) | decides *which* schedule the developer can even take | partially in URDB |
| **effective date** | a rate sheet without its vintage is unciteable | required |

---

## OUTPUT SHAPE — the table already exists, do not invent a new one

Write to **`indiana_app.in_utility_tariff_riders`**, whose schema already fits:

```
utility · state · tariff_code · tariff_name · component_type · code · name · rate · unit ·
basis · applies_to · season · value_status · effective_date · source · source_url · notes
```

- `component_type` ∈ `base_charge` | `demand` | `energy` | `rider` | `eligibility` | `ratchet` | `fuel_base`
- `season` ∈ `summer` | `non_summer` | `all`
- `value_status` ∈ `published` | `not_held` — **a component the book does not state is `not_held`
  with a NULL rate.** Never 0.
- `applies_to` carries the service voltage where the component is voltage-specific.

⚠ **Do not overwrite `in_rate_component_gaps`.** It is the record of what was missing *before* this
scrape, and the reconciliation note inside it is how we will know the scrape actually closed the gap.

---

## KNOWN STARTING URL

`in_rate_component_gaps` already carries one, cited from `urdb_rates.schedule_doc`:

- **I&M — Indiana tariff book, IURC No. 20**
  `https://www.indianamichiganpower.com/lib/docs/ratesandtariffs/Indiana/IMINTB19_01-16-2023.pdf`

The other four publish equivalents on their own rates-and-tariffs pages, and every URDB row carries
a `source` / `source_rate_schedule` pointer — **read those first** rather than searching, per G25.

---

## THE ACCEPTANCE TEST

The scrape has succeeded when, for at least one utility, we can compute the CPS build-up end to end
and **the modelled all-in rate lands near the EIA-861 realized average for that utility and sector**.
That reconciliation — not the tidiness of the table — is the proof. If modelled still sits far below
realized, a rider is still missing, and the gap tells you roughly how large it is.
