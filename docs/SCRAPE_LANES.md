# Indiana acquisition lanes — approved targets, rules, and status

Everything here is public data published for public use: government portals, utility
and RTO public tools, court/commission dockets, open-data platforms.

## The rules (absolute)

1. Scrape only what a source **permits** — no account creation, no terms dialogues, no
   API keys, no CAPTCHA handling, no paywall circumvention. A gated source is recorded
   **BLOCKED** with its exact wall, never worked around.
2. Pull **every layer** an endpoint serves, with `outFields=*` — material columns must
   not be silently lost.
3. Capture the **observed event date**, never the pull timestamp.
4. Write to `energy-platfrom.indiana_app` only, and register the table in
   `indiana_app._registry` **in the same run that writes it**.
5. Rate-limited (≥1s/host), identifying User-Agent, read-only requests.

## Lane A — transmission visibility (hyperscale priority, ~300 MW class)

The goal is bus/substation/line-grain interconnection visibility: available capacity
(injection AND withdrawal), limiting constraints, and upgrade-cost context.

| target | what to get | status |
|---|---|---|
| MISO DPP / interconnection study materials (public reports & posted results) | per-POI/bus capacity, constraints, network-upgrade cost allocations for Indiana-area projects | OPEN |
| MISO POI tool re-pull | our held copy has metrics but **zero bus identity** (fr/to bus = 0, lat/lon = 0.0 on all 904,486 rows; geometry endpoint previously observed 403) — re-acquire with bus ids/coords if the public payload carries them; else record BLOCKED | OPEN |
| PJM Queue Scope, AEP region | already harvested (303,671 rows held); extend owners/cases if Indiana-relevant | HELD / EXTEND |
| Indiana utility load/hosting heatmaps (AES Indiana, NIPSCO, Duke IN, CenterPoint IN, I&M) | Order-2023-era heatmaps or hosting-capacity maps, if published — for the edge-computing case | OPEN (none found in the 246-source HC estate; verify at the utilities directly) |
| IURC (Indiana Utility Regulatory Commission) | dockets: CPCNs, large-load tariffs, data-centre-related filings | OPEN |

## Lane B — community sentiment (P5; ~400 receipt-grade rows held today)

| target | what to get |
|---|---|
| County/municipal ordinances & zoning codes (American Legal, Municode, county sites) | data-centre use permissions, overlay districts, moratoria — the ordinance TEXT |
| County commission / plan-commission minutes & agendas (Legistar, CivicPlus, Granicus) | data-centre rezonings, hearings, votes — with event dates |
| Local news (state + metro outlets) | proposals, opposition, approvals |
| Moratorium / ban trackers covering Indiana | jurisdiction, action, date, source link |
| IURC dockets (shared with Lane A) | large-load and DC-related proceedings |

## Lane C — seller-intent gaps (12 of 29 signal types absent in Indiana)

Indiana-native sources first: county tax-sale platforms (SRI is Indiana-based),
sheriff/foreclosure sales, county treasurer delinquency lists, Indiana SOS business
dissolutions, WARN notices, county recorder distress doc-types (deed-in-lieu,
trustee's deed, lis pendens), building-condemnation/unsafe-structure lists.
Every candidate table is value-sampled before wiring — a name is not a subject, and one
table may hold several signals (extract all of them).

## Ordering

Lanes open **after** the map spine ships (WIP limit one). Within each lane: registry
check first (`energy.registry_sources` + `energy-platform/data/*.json`) — this project
has repeatedly re-discovered sources it already held.
