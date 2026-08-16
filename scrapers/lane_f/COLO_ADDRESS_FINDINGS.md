# B4 — the unresolved Indianapolis colo facilities: resolved, or shown to be no building at all

*Run 2026-08-16. Table: `energy-platfrom.indiana_app.in_dc_colo_resolved` (8 rows, registered in
`_registry` the same run). Loader: `scrapers/lane_f/resolve_colo_addresses.py` — a curated,
evidence-carrying loader, not a re-scraper.*

## The headline, plainly

**ZERO of the eight are genuinely missing buildings.**

| how they resolve | n | which |
|---|---:|---|
| already pinned in `in_data_centers_located`, flagged "absent" by a NAME artifact | **5** | CenturyLink Indy 1 & 2 (layer says **Lumen** — 2020 rename), DataBank IND1, DataBank IND2, Expedient |
| provider presence inside the pinned 701 W Henry carrier hotel — suite, not building | **1** | 365 Data Centers (Suite 101; sold to Netrality 2022; listing stale) |
| directory numbering ghost — no third building exists | **1** | CenturyLink Indianapolis 3 |
| no building anywhere — reseller of partner facilities | **1** | AxiaTP |

The B4 hypothesis is **confirmed in substance**: the Henry Street telecom campus explains four of
the eight entries (365 inside 701; DataBank's two buildings at 731 and 650 are their own parcels
*within/beside* the campus; CenturyLink #3 at most an on-net presence there) — and the remaining
"missing" facilities were never missing, only renamed or never buildings.

**Not one new pin is warranted.** Every resolved address is already represented in the layer; the
two SAME_BUILDING_AS/NOT_FOUND rows carry deliberately NULL coordinates so nothing renders as a
fake site.

## Per-facility verdicts

### 1. 365 Data Centers Indianapolis — `SAME_BUILDING_AS` Netrality 701 W Henry
**701 West Henry Street, Suite 101, Indianapolis, IN 46225** · parcel `49-11-11-183-001.012-101` ·
coords 39.759534, −86.170711 (the *building's*, per PeeringDB fac 2018)
- Operator's own site, 2014 ([archived](http://web.archive.org/web/20140508052357/http://365datacenters.com/indianapolis-data-center/)): *"701 West Henry Street, Suite 101, Indianapolis, IN 46225"*, service email `service-in1@`.
- Operator's own site, 2021 ([archived](http://web.archive.org/web/20210413112512/https://365datacenters.com/colocation/indianapolis-data-center/)): *"701 West Henry Street Indianapolis, IN 46225 … centrally located in the only Telecom campus in downtown within walking distance of the Lucas Oil Stadium."*
- [Press, 2022-04-05](https://www.globenewswire.com/en/news-release/2022/04/05/2416608/0/en/Netrality-Data-Centers-Acquires-365-Data-Centers-Indianapolis-Facility-on-the-Indy-Telcom-Campus.html): *"Netrality Data Centers announced the acquisition of 365 Data Centers' Indianapolis facility, located on the Indy Telcom campus."* The campus itself: *"a 205,000 sq ft., 11-building campus"* (Netrality since July 2021).
- Today: 365's site advertises 16 markets — **Indianapolis is not among them**; datacentermap's old `365main-indianapolis` slug now titles itself "Netrality - Indy Telcom Suite 101".
- **Confidence: HIGH.** A suite inside the carrier hotel, correctly absent from a building layer; the Cloudscene row is stale.

### 2. Axia Technology Partners Indianapolis — `NOT_FOUND` (there is no building)
No address recorded, coordinates NULL — deliberately.
- Their own [/colocation/ page, 2016](http://web.archive.org/web/20160508154509/https://www.axiatp.com/colocation/): *"By partnering with data centers throughout the country, we are able to provide our clients with the multiple options for securing their data. All of the facilities we use are Tier 3 and above."*
- Their own [homepage, 2016](http://web.archive.org/web/20161202214200/https://www.axiatp.com/): *"Our colocation services are offered in partnered facilities across North America."*
- PeeringDB (2026-08-16): no Axia facility record anywhere. Current [axiatp.com](https://www.axiatp.com/): managed IT services only, no colocation page.
- Their offices — 151 N Delaware St Ste 1750, Indianapolis (then); 4273 Perry Worth Rd Ste 100, Whitestown (now) — are **offices**, and were *not* recorded as facility addresses (that is the mailing-address trap this item warned about).
- **Confidence: HIGH** that no AxiaTP building exists. *Which* partner facility hosted their gear is not publicly stated.

### 3. CenturyLink Indianapolis 1 — `RESOLVED` (already pinned as **Lumen** Indianapolis 1)
**1902 S East St, Indianapolis, IN 46225** · parcel `49-11-13-215-005.000-101` (IND WHSE-350) ·
coords 39.741514, −86.150665 (baxtel, already the pin)
- Three directories converge and all call this site **#1**: [baxtel](https://baxtel.com/data-center/lumen-indianapolis-1) (*"1902 South East Street"*, Lumen, ex-"CenturyLink and Level(3)"), datacentermap (slug `level3-indianapolis1`, title *"Lumen Indianapolis 1 Data Center | 1902 S. East Street"*), datacenters.com (*"…at 1902 S. East Street offers 20,000 square feet"*).
- **Confidence: HIGH** on building and address. The crosscheck missed it because Cloudscene says *CenturyLink* and the layer says *Lumen* — instrument artifact, not a gap.

### 4. CenturyLink Indianapolis 2 — `RESOLVED` (already pinned as **Lumen Indianapolis 3**)
**4625 W 86th St, Suite 500, Indianapolis, IN 46268** · parcel `49-03-19-127-013.000-600` ·
coords 39.91079, −86.239243 (baxtel, already the pin)
- Ex-TW Telecom site (Level 3 acquired TWTC 2014 → CenturyLink 2017 → Lumen 2020). [datacentermap](https://www.datacentermap.com/usa/indiana/indianapolis/twtc-indianapolis/) titles it *"Lumen Indianapolis 2 Data Center | 4625 W 86th St"*; [baxtel](https://baxtel.com/data-center/lumen-indianapolis-3) and datacenters.com call the **same building** *"Lumen Indianapolis 3"* (*"4625 West 86th Street", "Suite 500", "a former tw telecom site"*).
- **Confidence: HIGH on the building, MEDIUM on the index.** Cloudscene publishes no address and the directories disagree on this building's number; resolving 2-vs-3 would require Cloudscene's own page, which its terms forbid us to scrape. The building set is certain either way.

### 5. CenturyLink Indianapolis 3 — `SAME_BUILDING_AS` (a numbering ghost; no third building)
No address, coordinates NULL — pinning either candidate would double-count.
- The public record documents **exactly two** distinct CenturyLink/Lumen buildings in Indianapolis (1902 S East St; 4625 W 86th St). No directory lists a third address; under baxtel/datacenters.com numbering, "Indianapolis 3" *is* 4625 W 86th St.
- The only other documented Lumen presence in the city is on-net at the Indy Telcom campus — Netrality's 2022 press lists *"…leading service providers including AT&T, Cogent Communications, **Lumen**, Crown Castle, Peerless Network, US Signal, Windstream, and Zayo."*
- PeeringDB shows **zero** Lumen netfac rows in Indianapolis for AS3356/AS209/AS3549 ([query](https://api.peeringdb.com/api/netfac?net_id=504&city=Indianapolis)) — Lumen under-registers there, so that absence is non-evidence either way.
- **Confidence: HIGH that no third building exists.** Correctly absent from a building layer.

### 6. DataBank IND1 — `RESOLVED` (already pinned)
**731 West Henry Street, Indianapolis, IN 46225** · parcel `49-11-11-183-001.006-101` ·
coords 39.759374, −86.172235 (PeeringDB fac 10929, published; ZIP+4 46225-1114)
- [Operator's own page](https://www.databank.com/data-centers/indianapolis/): *"IND1 - Downtown Indianapolis Data Center … 731 West Henry Street, Indianapolis, IN 46225"* — described as *"purpose-built data center"* and *"carrier hotel"* on Henry Street, *"the crossroads of fiber and telecommunications for the State of Indiana."*
- Ex-LightBound ([DataBank press, 2018-12-17](https://www.prnewswire.com/news-releases/databank-announces-acquisition-of-indianapolis-based-lightbound-300767206.html)); DCM slug `lightbound-731-henry-street`.
- Its parcel shares the subdivided campus group `49-11-11-183-001.*` with 701 (…012) and 733 (…005) — a distinct building **within** the Indy Telcom carrier-hotel campus, with its own pin.
- **Confidence: HIGH.** Already pinned as "Databank Indianapolis IND1" — the crosscheck's "absent" flag contradicts the live layer.

### 7. DataBank IND2 — `RESOLVED` (already pinned)
**650 West Henry Street, Indianapolis, IN 46225** · parcel `49-11-11-138-006.000-101` ·
coords 39.760096, −86.170486 (PeeringDB fac 10930, published)
- [Operator's own page](https://www.databank.com/data-centers/indianapolis/): *"IND2 - Downtown Indianapolis Data Center … 650 West Henry Street, Indianapolis, IN 46225."* Ex-LightBound 650 (DCM slug `lightbound-650`).
- Own building and parcel on the north side of Henry St, across from the 701/731/733 group.
- **Confidence: HIGH.** Already pinned as "Databank Indianapolis IND2". Note: the held baxtel pin (39.759464, −86.171265) sits ~90 m from PeeringDB's published point — both site-precision; flagged for reconciliation, not silently corrected.

### 8. Expedient Data Centers Indianapolis — `RESOLVED` (already pinned; building is in Carmel)
**701 Congressional Blvd., Carmel, IN 46032** · no parcel held (Hamilton Co., outside our Marion
crosswalks) · coords 39.963184, −86.145575 (PeeringDB fac 8458; DCM identical; baxtel pin ≈ same)
- [Operator's own page](https://www.expedient.com/data-centers/indianapolis/): *"701 Congressional Blvd., Carmel, IN 46032"* — *"53,000 sq. ft. total"*, *"4.4 MW critical IT load."*
- The mailing-city trap runs the **other way** here: Cloudscene files it under "Indianapolis" (the market); the building is in Carmel. Already pinned at the right spot.
- **Confidence: HIGH.**

## The access ledger (checked before every fetch)

| source | robots.txt | terms | action |
|---|---|---|---|
| **cloudscene.com** | `User-agent: * / Allow: /` | **FORBIDS**: §4 Fair use — *"you are not allowed to: a. use any spider, bot, scraper or other automated means to access the Platform; b. frame, mirror, scrape, data mine, extract or re-distribute data or other content you access through the Platform"* ([source](https://explore.cloudscene.com/terms-of-service/), accessed 2026-08-16) | **BLOCKED — not scraped.** Recorded in `energy.registry_sources` (append-only row, status BLOCKED / access BLOCKED_TERMS). Worked from operators instead. |
| datacenters.com | robots.txt request itself returned **403** | — | **BLOCKED — not fetched.** Only search-engine-visible page titles cited. |
| datacenterdynamics.com | `User-agent: ClaudeBot / Disallow: /` | — | **Respected — not fetched**, despite generic `Allow: /`. |
| datacentermap.com | robots.txt request returned **429** | — | **Backed off — not fetched.** Only search-visible titles + DCM data already held in the warehouse used. |
| peeringdb.com / api | only auth paths disallowed | public API | Fetched: 15 API calls, honest UA `decennial-indiana-siting/1.0`, ≥1.2 s spacing. Raw JSON archived in session evidence. |
| databank.com | no restrictions (ClaudeBot explicitly allowed) | — | Fetched 2 pages. |
| expedient.com | sitemap-only robots.txt | — | Fetched 2 pages. |
| 365datacenters.com | allow-all, `Crawl-delay: 10` | — | Fetched 1 page (respecting delay); history via Wayback. |
| axiatp.com | `Disallow: /*?`, `Crawl-delay: 3` | — | Fetched 1 plain-path page; history via Wayback. |
| baxtel.com | public content pages explicitly crawlable (`/api`,`/search`,`/admin`,`/users` disallowed) | — | Fetched 3 pages. |
| netrality.com, globenewswire, telecomramblings, techpoint.org, archive.org | permissive | — | Fetched 1–2 pages each. |

No CAPTCHA encountered, none bypassed; no accounts, no logins, no paywalls, no UA spoofing.

## Instrument findings (a clean result is a claim about the instrument first)

1. **Five of the eight "absent" facilities are in `in_data_centers_located` right now** (Lumen
   Indianapolis 1 & 3, Databank Indianapolis IND1/IND2, Expedient Indianapolis). Whatever produced
   the B4 list flagged presence-in-layer facilities as absent — the CenturyLink→Lumen rename
   explains two; the DataBank/Expedient flags contradict both the live layer and
   `docs/CLOUDSCENE_GAP.md` (which shows them token-matched). The crosscheck matcher, not the
   layer, is where the defect lives.
2. **`docs/GAMEPLAN.md` B4 says "the 7 unresolved facilities"; the operator-approved commission
   named 8.** The commissioned list is what this run resolved; the arithmetic difference is part
   of the same instrument question.
3. **I did not resolve all eight to distinct buildings — and that is the correct outcome.** Eight
   Cloudscene rows collapse onto six real buildings (1902 S East; 4625 W 86th; 731, 650, 701 W
   Henry; 701 Congressional Blvd) plus one non-building. Mailing/HQ traps were live: AxiaTP's
   downtown office suite and 365's Norwalk CT headquarters were both candidates a naive geocode
   would have pinned; neither was recorded.
4. **No centroids.** Rows with no building carry NULL coordinates. All recorded coordinates are
   source-published (PeeringDB / baxtel-held); all Marion parcels come from crosswalks we already
   hold (`in_marion_address_crosswalk` → `in_marion_parcel_crosswalk`).

## Follow-ups worth filing (not done here)

- Reconcile the ~90 m IND2 pin offset (baxtel vs PeeringDB) when the layer is next rebuilt.
- The crosscheck matcher needs an operator-alias table (CenturyLink→Lumen, LightBound→DataBank,
  365→Netrality) — three of this run's eight were pure rename artifacts.
- `docs/CLOUDSCENE_GAP.md`'s "Lifeline West Henry → Lifeline Fort Wayne" match is wrong (733 W
  Henry is the Netrality/ex-Lifeline Indianapolis building, pinned separately) — same matcher
  defect, different row.
