# Operator sign-off packet — measured 2026-08-15

Each item shows the actual value vocabulary. Reply per item: APPROVE (with the
mapping), REJECT, or DEFER. Nothing wires without your word.

## 1. D11 entity dissolution — first Indiana rows (2,129)
_Question: which statuses count as DISSOLVED for the D11 signal?_
- QUERY ERROR: 400 Unrecognized name: status; Did you mean state? at [2:28]; reason: invalidQuery, location: query, message: Unrecognized name: status; Did

## 2. D25 rail abandonment — source rows (874) vs 215 wired
_Columns first (schema); sample rows in SAMPLES docs. Question: admit all 874 as D25?_
- column_name=state
- column_name=state_count_in_docket
- column_name=state_parse_rule
- column_name=docket
- column_name=filing_no
- column_name=filed_date
- column_name=filed_for
- column_name=filing_type
- column_name=docket_title
- column_name=pdf_url
- column_name=_filing_window
- column_name=_source_url
- column_name=_pulled_at
- column_name=_derived_at

## 3. D27 UCC lapse v2 — Indiana rows (156)
_Question: wire as D27 candidates for this app?_
- column_name=signal
- column_name=state
- column_name=filing_id
- column_name=debtor_name
- column_name=raw_filing_type
- column_name=lapse_date
- column_name=filing_date
- column_name=address_line
- column_name=city
- column_name=addr_state
- column_name=zip
- column_name=keying
- column_name=quality_mult
- column_name=source_table
- column_name=_source_url
- column_name=_pulled_at

## 4. IOCS 'MF' code — mortgage foreclosure inside the eviction workbook
_Question: admit MF rows as a D2-family candidate?_
- QUERY ERROR: 400 Unrecognized name: case_type at [2:28]; reason: invalidQuery, location: query, message: Unrecognized name: case_type at [2:28]

Location

## 5. Cloudscene data centres — state vocabulary (why 'IN' matched 0)
_Question: which value means Indiana here?_
- state= | n=5283
- state=OH | n=28
- state=OR | n=23
- state=DC | n=18
- state=RI | n=10
- state=KY | n=8
- state=NY | n=8
- state=MA | n=5
- state=WV | n=3
- state=AL | n=2

## 6. airports — why only 1 'IN' row (format flag)
_Question: what does this state column actually hold?_
- state=CA | n=10
- state=FL | n=7
- state=TX | n=7
- state=NY | n=5
- state=HI | n=4
- state=OH | n=3
- state=MO | n=2
- state=NV | n=2
- state=TN | n=2
- state=NC | n=2
- state=PA | n=2
- state=DC | n=2

## 7. queue_miso vs interconnection_queue — same source?
_If id overlap is total, queue_miso is a duplicate slice - waive._
- QUERY ERROR: 400 Unrecognized name: q_id; Did you mean id? at [1:59]; reason: invalidQuery, location: query, message: Unrecognized name: q_id; Did you me

## 8. DC dedupe preview — proposed rule: same name-stem within 500 m
_Question: approve collapsing these cross-source pairs to one row each (sources listed)?_
- src=baxtel | src_1=datacentermap | name=Expedient Indianapolis  | name_1=Expedient Indianapolis | meters=5.0
- src=baxtel | src_1=osm | name=Digital Crossroad (Indiana NAP) | name_1=Digital Crossroad | meters=17.0
- src=baxtel | src_1=osm | name=Amazon: New Carlisle I DC6 | name_1=None | meters=29.0
- src=baxtel | src_1=osm | name=Amazon: New Carlisle I DC5 | name_1=None | meters=31.0
- src=baxtel | src_1=osm | name=Amazon: New Carlisle I DC7 | name_1=None | meters=35.0
- src=baxtel | src_1=osm | name=Amazon: New Carlisle I DC3 | name_1=None | meters=40.0
- src=baxtel | src_1=datacentermap | name=US Signal South Bend | name_1=Gap Union Station | meters=42.0
- src=baxtel | src_1=datacentermap | name=1547 CSR: SBIN1 | name_1=Gap Union Station | meters=42.0
- src=baxtel | src_1=osm | name=Amazon: New Carlisle I DC3 | name_1=None | meters=57.0
- src=baxtel | src_1=osm | name=Amazon: New Carlisle I DC1 | name_1=None | meters=61.0
- src=baxtel | src_1=osm | name=Amazon: New Carlisle I DC7 | name_1=None | meters=65.0
- src=baxtel | src_1=osm | name=Amazon: New Carlisle I DC4 | name_1=None | meters=75.0
- src=baxtel | src_1=osm | name=Amazon: New Carlisle I DC2 | name_1=None | meters=82.0
- src=baxtel | src_1=osm | name=Amazon: New Carlisle I DC2 | name_1=None | meters=85.0
- src=baxtel | src_1=osm | name=Amazon: New Carlisle I DC4 | name_1=None | meters=93.0
- src=baxtel | src_1=osm | name=Amazon: New Carlisle I DC6 | name_1=None | meters=120.0
- src=baxtel | src_1=osm | name=Amazon: New Carlisle II DC8 | name_1=Amazon AWS Data Center | meters=126.0
- src=baxtel | src_1=osm | name=Digital Crossroad: Hammond, IN (Phase 2) | name_1=Digital Crossroad | meters=127.0
- src=baxtel | src_1=osm | name=Amazon: New Carlisle I DC5 | name_1=None | meters=136.0
- src=baxtel | src_1=osm | name=Amazon: New Carlisle I DC6 | name_1=None | meters=145.0
