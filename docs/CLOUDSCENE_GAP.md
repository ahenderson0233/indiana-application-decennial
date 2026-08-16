> ## ⚠ CORRECTION 2026-08-16 — THIS TABLE'S "MATCHED" COLUMN IS NOT TRUSTWORTHY
>
> These matches were made on **operator tokens and place names alone**, with no check that the
> two rows describe the same BUILDING. Eight are demonstrably wrong and are flagged inline:
>
> * **Three different Indianapolis Lifeline buildings** — North Shadeland, South Anthony and
>   West Henry — were all matched to **Lifeline Data Centers Fort Wayne**, a different city.
>   One operator, several buildings; the token says nothing about which.
> * **Three Global Access Point facilities** across Indianapolis and South Bend collapsed onto a
>   single "Gap Union Station" via the acronym **GAP**.
> * **"Indigital Fort Wayne" was matched to "Google Fort Wayne Building 5"** — two unrelated
>   companies, joined purely because they share a city.
> * **"The Union 525"** was matched to "Gap Union Station" on the word *union*.
>
> A wrong match here is worse than no match: it reports a facility as **already held** when it is
> not, so it **understates the gap** and removes a site from anyone's follow-up list.
>
> **The authority is `in_dc_colo_resolved`**, which resolved eight Indianapolis colos from the
> operators' own published statements and found ZERO were missing buildings. `data.html` now joins
> on `cloudscene_slug` against that table and only falls back to name matching where nobody has
> looked. `in_dc_operator_aliases` records the renames a token matcher cannot see
> (CenturyLink→Lumen, LightBound→DataBank, 365→Netrality) — and is explicitly marked
> **operator-name only, never to merge facilities**, for exactly the Lifeline reason above.

# Cloudscene gap — what the 25 unmatched colo facilities actually are

Measured 260 cloudscene Indiana rows: **229 are carrier central offices** (223 Frontier alone) and are not data centres at all. The real question is the **31 colo/enterprise facilities**.

| verdict | n |
|---|---:|
| already pinned on our map | 20 |
| **held in the warehouse but never merged into the map layer** | **4** |
| not present in any source we hold | 7 |

## Recoverable now — in a source we already hold, with coordinates

The DC union was built from OSM + Baxtel + Wikidata + DCM-via-coords. **peeringdb was clipped separately as a 'connectivity layer' and never merged**, so its facilities never reached the map even though they carry coordinates.

| cloudscene name | city | found in | matched on | lat | lon |
|---|---|---|---|---:|---:|
| Indiana University Iub Data Center | Indiana Regional | `in_peeringdb_facilities (NOT merged)` | tokens university — *Indiana University Data Center* | 39.174464 | -86.500753 |
| Indiana University Iupui Data Center | Indianapolis | `in_peeringdb_facilities (NOT merged)` | tokens university — *Indiana University Data Center* | 39.174464 | -86.500753 |
| Indy Telcom Indianapolis | Indianapolis | `in_peeringdb_facilities (NOT merged)` | tokens telcom — *Netrality - Indy Telcom Center - 701 W. Henry* | 39.759534 | -86.170711 |
| Otava In1 | Indianapolis | `data_centers_baxtel (company_name)` | name-stem — *Otava* | 39.758672 | -86.167831 |

## Not found in anything we hold

| cloudscene name | city | market |
|---|---|---|
| 365 Data Centers Indianapolis | Indianapolis | indianapolis |
| Axia Technology Partners Indianapolis | Indianapolis | indianapolis |
| Indiana State Library Indiana State Data Center | Indianapolis | indianapolis |
| Intelligent Fiber Network Indianapolis 2 | Indianapolis | indianapolis |
| Intervision Indianapolis | Indianapolis | indianapolis |
| Paragon Cloud Indianapolis | Indianapolis | indianapolis |
| Wholesale Carrier Services Indianapolis | Indianapolis | indianapolis |

## Already pinned (matched our map layer)

| cloudscene name | matched on | our name |
|---|---|---|
| Colostore South Bend | place tokens bend+south | Cbts South Bend Data Center Ii |
| Dartpoints Columbus | name-stem | DartPoints: Columbus, IN |
| Data Realty South Bend | name-stem | Data Realty |
| Databank Ind1 | tokens databank+ind1 | Databank Indianapolis IND1 |
| Databank Ind2 | tokens databank+ind2 | Databank Indianapolis IND2 |
| Expedient Data Centers Indianapolis | tokens expedient | Expedient Indianapolis  |
| Global Access Point In1 | acronym GAP | ⚠ Gap Union Station — **WRONG, acronym collision** |
| Global Access Point Sb1 | acronym GAP | ⚠ Gap Union Station — **WRONG, acronym collision** |
| Global Access Point Sb2 | acronym GAP | ⚠ Gap Union Station — **WRONG, acronym collision** |
| Indiana Data Center Ft. Wayne | name-stem | Indiana Data Center |
| Indigital Fort Wayne | place tokens fort+wayne | ⚠ Google Fort Wayne Building 5 — **WRONG, different company, matched on the CITY** |
| Intelligent Fiber Network Indy Telecom Center | tokens telecom | Netrality Indy Telecom Center |
| Lifeline Data Centers North Shadeland | tokens lifeline | ⚠ Lifeline Data Centers Fort Wayne — **WRONG, different city** |
| Lifeline Data Centers South Anthony | tokens lifeline | ⚠ Lifeline Data Centers Fort Wayne — **WRONG, different city** |
| Lifeline Data Centers West Henry | tokens lifeline | ⚠ Lifeline Data Centers Fort Wayne — **WRONG, different city** |
| Sitco Solutions Evansville | tokens sitco | Sitco Data Center |
| The Union 525 Union 525 | tokens union | ⚠ Gap Union Station — **WRONG, matched on the word 'union'** |
| Us Signal Indianapolis | name-stem | US Signal Indianapolis IN01 |
| Us Signal South Bend | name-stem | US Signal South Bend |
| Wintek Lafayette | name-stem | Wintek Lafayette |
