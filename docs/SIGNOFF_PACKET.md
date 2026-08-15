# Operator sign-off packet v2 — measured 2026-08-15

Supersedes v1, in which items 1, 4 and 7 were BigQuery errors (columns guessed, never
read) and 5-6 answered a different question than the one asked. Every column below was
read from the schema first.

**Reply per item: APPROVE (with the mapping) / REJECT / DEFER.** Nothing wires without it.

## Summary — what the measurements recommend

| # | item | what the numbers say | recommendation |
|---|---|---|---|
| 1 | D11 dissolution | 5 status families, all 2,129 rows carry an address | admit `dissolved`+`revoked`+`forfeited`+`void` (983); `withdrawn` (1,146) is a weaker claim — your call |
| 2 | D25 rail abandonment | **most of the 874 are procedural paperwork**, not abandonment events | admit only the event filings (~127), not all 874 |
| 3 | D27 UCC lapse | all 156 are `keying=address`, quality 0.8, every row has address+zip | clean — admit as candidates |
| 4 | IOCS `MF` | question is unanswerable as posed: MF is a **column of court counts**, not rows | county-grain context only — and exclude the `STATE`/`nan` rows |
| 5 | cloudscene | `market` is the state key (260 IN rows) but the table has **no coordinates** | Data-page cross-check, not a layer |
| 6 | airports | **not a bug** — 86-row curated national set; exactly 1 is in Indiana and `state` says so | close the flag; use as context if wanted |
| 7 | queue_miso | 452 of 456 Indiana ids also in interconnection_queue — near-total duplicate | keep for `studyphase`/`poiname`/ERIS-NRIS MW only; do not render twice |
| 8 | DC dedupe | name-stem rule collapses only 3 pairs; 8 unnamed OSM rows can't be judged by it | approve the rule, then decide the unnamed-row fallback separately |

## 1. D11 entity dissolution — 2,129 Indiana rows
_The subject column is `raw_status` (publisher's words) normalised into `status_family`. v1 asked for `status`, which does not exist. QUESTION: which families count as DISSOLVED?_

**status_family → raw_status vocabulary**
- status_family=withdrawn · n=1146 · distinct_raw=4 · example_raw_values=INACTIVE   / Surrendered | INACTIVE   / Withdrawn - Can Reinstate | IN
- status_family=dissolved · n=493 · distinct_raw=10 · example_raw_values=Administratively Dissolved | Cancelled | Dissolved | INACTIVE   / Auto
- status_family=revoked · n=470 · distinct_raw=7 · example_raw_values=INACTIVE   / Automatically Revoked - Annual Report - Can Reinstate | I
- status_family=forfeited · n=19 · distinct_raw=1 · example_raw_values=Forfeited
- status_family=void · n=1 · distinct_raw=1 · example_raw_values=INACTIVE   / Void - Ab Initio

**plottability + date range**
- earliest=2004-12-21 · latest=2026-03-11 · cities=343 · with_address=2129

**The split that matters is `withdrawn` (1,146) vs the rest (983).** Read the raw values: the
withdrawn family is *"Surrendered"* and *"Withdrawn - Can Reinstate"* — an out-of-state entity
giving up its authority to do business in Indiana, or a lapse that can be undone. The other four
families are terminal or near-terminal: *Administratively Dissolved, Cancelled, Dissolved,
Automatically Revoked, Forfeited, Void - Ab Initio*. If D11 is meant to signal "this business is
ending, its property may come free", `withdrawn` is the weaker half of the evidence and admitting
it more than doubles the signal count. Every row is address-keyed, so all 2,129 are plottable
either way — this is a subject question, not a coverage one.

## 2. D25 rail abandonment — 874 source rows vs 215 wired
_`state_count_in_docket` is the crux: a docket naming many states should not count wholly to Indiana. QUESTION: admit all 874, or only single-state / Indiana-primary dockets?_

**how many states each docket names**
- state_count_in_docket=1 · n=737 · dockets=86
- state_count_in_docket=2 · n=137 · dockets=13

**how the state was parsed out (the instrument)**
- state_parse_rule=location_clause · n=874

**filing_type vocabulary**
- filing_type=Reply · n=185
- filing_type=Request For Extension Of Time · n=150
- filing_type=Notice Of Exemption · n=53
- filing_type=Trail Use Request · n=53
- filing_type=Consummation Notice · n=50
- filing_type=Motion/Petition/Request · n=31
- filing_type=Modify/Supplement Prior Filing Or The Record · n=30
- filing_type=Certificate Of Service · n=26
- filing_type=Petition For Exemption · n=24
- filing_type=Protest/Opposition Statement · n=22

**READ THE FILING TYPES — this is why only 215 were wired.** The multi-state worry turns out to
be minor (737 rows name one state, 137 name two; no docket names more). The real problem is that
most of the 874 are *procedural paperwork about* an abandonment, not the abandonment: Reply 185,
Request For Extension Of Time 150, Certificate Of Service 26, Modify/Supplement 30,
Protest/Opposition 22. The rows that are actual abandonment events are
**Notice Of Exemption 53 + Consummation Notice 50 + Petition For Exemption 24 = 127**.
Admitting all 874 would count a law firm's extension request as a rail-line abandonment signal.

## 3. D27 UCC lapse v2 — 156 Indiana rows
_QUESTION: wire as D27 candidates? `keying`/`quality_mult` say how confidently each row reaches an address._

**filing type vocabulary**
- raw_filing_type=UCC financing statement · n=146
- raw_filing_type=ORIG FIN STMT · n=10

**keying quality → how many are actually placeable**
- keying=address · quality_mult=0.8 · n=156 · with_address=156 · with_zip=156

## 4. IOCS 'MF' — the question as posed cannot be answered, and here is why
_v1 asked to 'admit MF rows'. There are no MF rows. `in_si_refresh_iocs_eviction` is a court-statistics WORKBOOK: one row per court, and every case-type code (MR, CF, EV, MF, …) is a COLUMN holding a count. So MF is a per-court aggregate, not a per-address event — it cannot become a parcel-level SI signal at any confidence. QUESTION: admit it as COUNTY-GRAIN context on the Community page instead, or drop it?_

**what MF actually contains**
- courts=6519 · courts_with_mf=1109 · total_mf_filings=83446 · total_ev_evictions=442076 · counties=94

**top counties by MF (county grain is the only honest grain here)**
- County_Name=STATE · mortgage_foreclosures=21300 · evictions=120917
- County_Name=nan · mortgage_foreclosures=10235 · evictions=31069
- County_Name=MARION · mortgage_foreclosures=5089 · evictions=53016
- County_Name=LAKE · mortgage_foreclosures=4092 · evictions=12911
- County_Name=ALLEN · mortgage_foreclosures=1203 · evictions=10038
- County_Name=HANCOCK · mortgage_foreclosures=1102 · evictions=1307
- County_Name=JOHNSON · mortgage_foreclosures=853 · evictions=4370
- County_Name=ST. JOSEPH · mortgage_foreclosures=837 · evictions=5700
- County_Name=ELKHART · mortgage_foreclosures=744 · evictions=4142
- County_Name=MADISON · mortgage_foreclosures=741 · evictions=2242

**TWO POISON ROWS — whoever wires this must exclude them.** The county list reads 94 names for a
92-county state. `County_Name='STATE'` (21,300 MF / 120,917 EV) is a **statewide total row**, and
`'nan'` (10,235 / 31,069) is an unlabelled residue. Summing the column as-is double-counts the
entire state and then adds an orphan bucket — a county chart built on it would be wrong by
roughly 38% before anyone noticed. Real county grain is the remaining 92.

## 5. Cloudscene — `state` is empty for 98% of rows, so it is the wrong key
_5,283 of 5,388 rows have a blank state; the populated handful are other states. Indiana has to be found through `city`/`market`. QUESTION: approve city/market matching (list below), or leave cloudscene out — we already hold 244 Indiana DCs with coordinates?_

**country split (is this even a US-centric table?)**
- country=US · n=5388 · blank_state=5283

**candidate Indiana rows via city/market**
- market=indiana-regional · city=Indiana Regional · n=225
- market=indianapolis · city=Indianapolis · n=23
- market=south-bend · city=South Bend · n=6
- market=fort-wayne · city=Fort Wayne · n=4
- market=evansville · city=Evansville · n=2

**RESOLVED by a follow-up value-read — `market` IS cloudscene's state key.** `indiana-regional`
looked like the name-is-not-a-subject trap (Indiana County, *Pennsylvania* is a real place), so
it was checked rather than assumed. It is a state bucket: the same `<state>-regional` pattern
exists across the table (illinois-regional 322, texas-regional 300, california-regional 295,
michigan-regional 221, ohio-regional 159 — 152 markets, 2,959 rows in `-regional` buckets).
The member rows are Indiana towns — Frontier Akron/Albion/Anderson/Angola, Wintek Lafayette,
Indiana University IUB, Frontier Terre Haute, Dartpoints Columbus. **Indiana total = 260 rows**
(225 indiana-regional + 23 indianapolis + 6 south-bend + 4 fort-wayne + 2 evansville).

**But note what cloudscene does NOT have: coordinates.** Its whole schema is
`cloudscene_slug, name, city, state, market, url`. These 260 can never be a map layer — at best
a name-list cross-check against the 244 DCs we already hold *with* coordinates. RECOMMENDATION:
admit as a Data-page completeness check (how many cloudscene names we already have pinned),
not as a layer. Your call.

## 6. airports — 86 rows nationally, and it carries GEOMETRY
_The table is a curated 86-row set, not a full airport list, and it has a `geom` GEOGRAPHY column — so `state` never needed to be trusted. Spatial clip is the answer. QUESTION: approve clipping by geometry (results below) and using it as an obstruction/airspace context layer?_

**the instrument**
- total_rows=86 · with_geometry=86 · state_says_IN=1

**rows whose GEOMETRY falls in Indiana (clipped to the state polygon)**
- name=Indianapolis Intl · servcity=INDIANAPOLIS · state=IN · type_code=AD · operstatus=OPERATIONAL · latitude=39-43-02.3000N · longitude=086-17-40.7000W

**…and what the `state` column claims for those same Indiana rows (the format flag)**
- state=IN · n=1

**THE FLAG IS RESOLVED — there was never a format bug.** The batch-4 audit flagged "airports
reads 1 IN row — format-suspect (Indiana has dozens of airports)". It does have dozens; this
table does not carry them. It is an 86-row curated national set (CA 10, FL 7, TX 7, NY 5 — the
same order of magnitude everywhere), and the single Indiana member, Indianapolis Intl, is
geometrically in Indiana *and* labelled `IN`. The instrument was right and the suspicion was
wrong. Close the flag.

## 7. queue_miso vs interconnection_queue — is one a duplicate slice of the other?
_v1 asked queue_miso for `q_id`; its key is `projectnumber` (interconnection_queue uses `q_id`). Compared properly below. QUESTION: if the Indiana project numbers overlap substantially, waive queue_miso as a duplicate — or keep it for the columns the other lacks (studyphase, poiname, dp1/dp2 ERIS+NRIS MW)?_

**row and id counts**
- src=queue_miso (all states) · n=3794 · ids=3794
- src=queue_miso (state=IN) · n=456 · ids=456
- src=interconnection_queue (state=IN) · n=948 · ids=948
- src=interconnection_queue (IN, MISO region) · n=583 · ids=583

**identity overlap on the Indiana slice (the actual duplicate test)**
- miso_in_ids=456 · icq_in_ids=948 · shared_ids=452

**what queue_miso adds that interconnection_queue has no column for**
- studyphase=Phase 2 · n=173
- studyphase=GIA · n=169
- studyphase=Study Not Started · n=73
- studyphase=Phase 1 · n=27
- studyphase= · n=14

**452 of 456 — it is a duplicate slice, but not a worthless one.** Every Indiana project number
in queue_miso but 4 already exists in interconnection_queue, so rendering both would double-count
the queue on any map or total. What queue_miso adds is columns the other table has no field for:
`studyphase` (Phase 1 / Phase 2 / GIA — where each project sits in the study cycle),
`poiname` (the point of interconnection, which joins to our bus work), and the DPP ERIS/NRIS MW
split. RECOMMENDATION: waive as a *layer*, keep as a *join* onto the existing queue rows.

## 8. DC dedupe — the proposed rule, actually applied
_v1's preview listed every cross-source pair within 500 m REGARDLESS of name, so it showed what proximity alone would collapse, not what the rule would. Applied here: normalise the name (lowercase, alphanumeric only) and require one to be a prefix of the other. QUESTION: approve this rule? Note the NULL-name problem in the third block._

**WOULD COLLAPSE (name-stem matches) — check these are genuinely one facility**
- src=baxtel · src_b=datacentermap · name=Expedient Indianapolis  · name_b=Expedient Indianapolis · meters=5.0
- src=baxtel · src_b=osm · name=Digital Crossroad (Indiana NAP) · name_b=Digital Crossroad · meters=17.0
- src=baxtel · src_b=osm · name=Digital Crossroad: Hammond, IN (Phase 2) · name_b=Digital Crossroad · meters=127.0

**WOULD STAY SEPARATE despite being within 500 m — check none of these are one facility**
- src=baxtel · src_b=datacentermap · name=US Signal South Bend · name_b=Gap Union Station · meters=42.0
- src=baxtel · src_b=datacentermap · name=1547 CSR: SBIN1 · name_b=Gap Union Station · meters=42.0
- src=baxtel · src_b=osm · name=Amazon: New Carlisle II DC8 · name_b=Amazon AWS Data Center · meters=126.0
- src=baxtel · src_b=osm · name=Amazon: New Carlisle II DC7 · name_b=Amazon AWS Data Center · meters=162.0
- src=baxtel · src_b=osm · name=CoreWeave: Hammond, IN · name_b=Digital Crossroad · meters=187.0
- src=baxtel · src_b=osm · name=Amazon: New Carlisle II DC9 · name_b=Amazon AWS Data Center · meters=291.0
- src=baxtel · src_b=osm · name=Amazon: New Carlisle II DC4 · name_b=Amazon AWS Data Center · meters=335.0
- src=baxtel · src_b=osm · name=Amazon: New Carlisle II DC2 · name_b=Amazon AWS Data Center · meters=407.0
- src=baxtel · src_b=datacentermap · name=QLevr: Charlestown, Indiana · name_b=1800 Cristiani Parkway · meters=437.0

**THE GAP: pairs where one source has NO NAME — a name-stem rule cannot judge these, so they stay as duplicate pins unless you approve a distance-only fallback**
- src=baxtel · src_b=osm · a_name=Amazon: New Carlisle I DC4 · b_name=None · pairs=4 · nearest_m=75.0
- src=baxtel · src_b=osm · a_name=Amazon: New Carlisle I DC2 · b_name=None · pairs=4 · nearest_m=82.0
- src=baxtel · src_b=osm · a_name=Amazon: New Carlisle I DC3 · b_name=None · pairs=4 · nearest_m=40.0
- src=baxtel · src_b=osm · a_name=Amazon: New Carlisle I DC1 · b_name=None · pairs=4 · nearest_m=61.0
- src=baxtel · src_b=osm · a_name=Amazon: New Carlisle I DC5 · b_name=None · pairs=4 · nearest_m=31.0
- src=baxtel · src_b=osm · a_name=Amazon: New Carlisle I DC7 · b_name=None · pairs=3 · nearest_m=35.0
- src=baxtel · src_b=osm · a_name=Amazon: New Carlisle I DC6 · b_name=None · pairs=3 · nearest_m=29.0

**source composition of the 244**
- src=baxtel · n=136 · unnamed=0
- src=datacentermap · n=95 · unnamed=0
- src=osm · n=13 · unnamed=8

**What the rule actually does, and the one judgment it cannot make.** Applied honestly, the
name-stem rule is conservative: it collapses **3 pairs** (Expedient Indianapolis at 5 m; Digital
Crossroad twice, at 17 m and 127 m). It correctly *refuses* to collapse "Amazon: New Carlisle II
DC8" into OSM's generic "Amazon AWS Data Center" — those are separate buildings on one campus,
and a distance-only rule would have eaten the whole New Carlisle campus into a single pin.
The gap is OSM's **8 unnamed rows**, which generate 20+ pairs inside 500 m of named Baxtel
buildings. A name rule cannot judge a row with no name. Three options, your pick:
(a) leave them as separate pins and say so on the layer; (b) drop unnamed OSM rows that sit
within 150 m of a named row from another source; (c) keep them but mark them `unnamed_duplicate_
candidate` so they render differently. Option (a) is the honest default and needs no approval.

