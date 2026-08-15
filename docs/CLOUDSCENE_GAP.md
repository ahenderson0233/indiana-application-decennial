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
| Global Access Point In1 | acronym GAP | Gap Union Station |
| Global Access Point Sb1 | acronym GAP | Gap Union Station |
| Global Access Point Sb2 | acronym GAP | Gap Union Station |
| Indiana Data Center Ft. Wayne | name-stem | Indiana Data Center |
| Indigital Fort Wayne | place tokens fort+wayne | Google Fort Wayne Building 5 |
| Intelligent Fiber Network Indy Telecom Center | tokens telecom | Netrality Indy Telecom Center |
| Lifeline Data Centers North Shadeland | tokens lifeline | Lifeline Data Centers Fort Wayne |
| Lifeline Data Centers South Anthony | tokens lifeline | Lifeline Data Centers Fort Wayne |
| Lifeline Data Centers West Henry | tokens lifeline | Lifeline Data Centers Fort Wayne |
| Sitco Solutions Evansville | tokens sitco | Sitco Data Center |
| The Union 525 Union 525 | tokens union | Gap Union Station |
| Us Signal Indianapolis | name-stem | US Signal Indianapolis IN01 |
| Us Signal South Bend | name-stem | US Signal South Bend |
| Wintek Lafayette | name-stem | Wintek Lafayette |
