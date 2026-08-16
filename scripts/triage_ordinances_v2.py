"""Triage the 146 candidate rows in `in_ordinances_dc_v2` — does the provision plausibly regulate
a DATA CENTRE AS A LAND USE?

WHY THIS IS NEEDED. Only 7 of 153 rows name a data centre. The rest matched adjacent vocabulary:
"data processing" (34), "telecommunications facility" (43), and an unquoted loose "data center"
search (66) that stems and OR-matches, so it also catches "community center", "day-care center",
"center line" and bare "data".

THE UNIT OF JUDGMENT IS THE SECTION, NOT THE ROW. A section's relevance cannot depend on which
phrase happened to match it, and triaging per row would let one section receive two contradictory
verdicts. 146 candidate rows collapse to 115 distinct sections; every row is covered by exactly
one verdict and `n_candidate_rows` reconciles the two counts.

THE TEST APPLIED, in order:
  1. Is the section in a LAND-USE instrument at all? Zoning, UDO, subdivision, land-usage title.
     A finance department, purchasing policy, personnel chapter or records ordinance is not, no
     matter how often it says "data processing" — that is procurement, not land use.
  2. Does it name a use a data centre would FALL UNDER? "data processing center", "data
     processing/call center", "Data Processing, Hosting and Related Services (NAICS 518)".
  3. A WIRELESS TELECOMMUNICATIONS FACILITY IS NOT A DATA CENTRE. It is a tower and antennae.
     43 rows matched that phrase and almost all are cell-tower siting, height and nonconformity
     rules. Admitting them would inflate the corpus with the wrong subject entirely.
  4. NEEDS_FULL_TEXT is reserved for sections that ARE a use table or a zoning definitions list —
     exactly where a data-centre use would live — but whose snippet resolved to a false positive.
     The snippet is 240 characters of a section that may run pages; absence in it is not absence
     in the section.

KNOWN FALSE-POSITIVE PATTERN, confirmed: LaPorte/Michigan City matched "Indiana Natural Heritage
Data Center", an IDNR database, not a land use. All six Michigan City candidates fail here.

Writes `in_ordinances_dc_v2_triage` and registers it in the SAME run.
`in_ordinances_dc_v2` is NOT modified.
"""
import json, datetime
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
SRC = f"{DS}.in_ordinances_dc_v2"
client = bigquery.Client(project="energy-platfrom")
BUILT = datetime.datetime.now(datetime.timezone.utc).isoformat()

# index -> (verdict, reason). Indices follow the ORDER BY county, jurisdiction, code_section_id
# used to enumerate the distinct sections; the script re-derives that order and asserts the count.
NR = "NOT_RELEVANT"
RL = "RELEVANT"
NF = "NEEDS_FULL_TEXT"

V = {
 1: (NR, "Muncie finance department; creates an internal data processing division - procurement/administration, not land use"),
 2: (NR, "wastewater definitions; matched 'operational data' about effluent sampling"),
 3: (NR, "zoning officer procedure; matched 'the following data' in a permit application list"),
 4: (RL, "Jasper UDO use list names 'data processing / call center' under Professional Services"),
 5: (NR, "county information systems department; internal IT purchasing, not a land use"),
 6: (NR, "digital accessibility policy for public employees; matched 'data tables'"),
 7: (NR, "county purchasing policy; special purchase of data processing contracts"),
 8: (NR, "UDO definitions, but the matched entry defines a WIRELESS telecommunications facility - towers and antennae, not a data centre"),
 9: (NR, "wireless facility setback requirement - cell tower siting"),
 10: (NR, "wireless facility zoning-district rule - cell tower siting"),
 11: (NR, "wireless facility construction and maintenance - cell tower"),
 12: (RL, "Hamilton County UDO PERMITTED USE TABLE lists 'DATA PROCESSING CENTER' as a use"),
 13: (NR, "subdivision plat requirement; matched 'center lines of all streets'"),
 14: (NR, "as-built documentation; matched 'center lines of all streets'"),
 15: (RL, "Franklin zoning definitions define 'Data processing center' and 'Communications service exchange' as land uses"),
 16: (RL, "Franklin land-use table lists 'Data processing/call center' across districts"),
 17: (NR, "Agricultural district; only match is telecommunications facility/tower"),
 18: (NR, "Rural residential district; cross-reference to tower height standards"),
 19: (NR, "Suburban neighbourhood residential; tower height cross-reference"),
 20: (NR, "Suburban residential RS-1; tower height cross-reference"),
 21: (NR, "Suburban residential RS-2; tower height cross-reference"),
 22: (NR, "Suburban residential RS-3; tower height cross-reference"),
 23: (NR, "Traditional neighbourhood residential; tower height cross-reference"),
 24: (NR, "Traditional residential RT-1; tower height cross-reference"),
 25: (NR, "Traditional residential RT-2; tower height cross-reference"),
 26: (NR, "Traditional residential RT-3; tower height cross-reference"),
 27: (NR, "Multifamily residential; tower height cross-reference"),
 28: (NR, "Manufactured home park district; tower height cross-reference"),
 29: (RL, "Franklin MXD downtown-centre district use table lists 'Data processing/call center'"),
 30: (NR, "MXN neighbourhood-centre district; only a tower height cross-reference matched"),
 31: (RL, "Franklin MXC community-centre district use table lists 'Data processing/call center'"),
 32: (RL, "Franklin MXR regional-centre district use table lists 'Data processing/call center'"),
 33: (NR, "Institutional district; only telecommunications facility/tower matched"),
 34: (RL, "Franklin IBD industrial business-development district lists 'Data processing/call center'"),
 35: (RL, "Franklin IL light-industrial district lists 'Data processing/call center'"),
 36: (RL, "Franklin IG general-industrial district lists 'Data processing/call center'"),
 37: (NR, "general height standards; cross-reference to telecommunications facility standards"),
 38: (NR, "telecommunication facility standards - cell tower interference rules"),
 39: (NR, "sexually-oriented business separation distances; 'Technology Park' appears only as a measuring reference"),
 40: (RL, "Warsaw table of permitted uses lists 'Data processing services'"),
 41: (NR, "flood damage prevention districts; matched 'flood data'"),
 42: (NR, "airport district uses; matched 'recording data from the county recorder'"),
 43: (NR, "zoning definitions 'C'; matched co-location of a WIRELESS telecommunications facility"),
 44: (NR, "Michigan City finance department; a division of data processing - administration, not land use"),
 45: (NR, "commission membership; matched 'career tech center'"),
 46: (NR, "veterans commission; matched 'community centers, civic centers, convention centers'"),
 47: (NR, "sustainability commission; matched 'data gathering and analysis'"),
 48: (NR, "public-records copying fee; matched 'data processing printouts'"),
 49: (RL, "Griffith I-1 Light Industrial permitted uses lists '(16) Data processing, hardware and software'"),
 50: (NR, "alarm system permits; matched 'communications center'"),
 51: (NR, "improvement location permits; matched 'center-lines' of streets"),
 52: (NR, "special regulations for WIRELESS telecommunication facilities - towers"),
 53: (NR, "public purchasing definitions; data processing per IC 4-23-16-5 - procurement"),
 54: (NR, "special purchasing methods for data processing contracts - procurement"),
 55: (NR, "refuse collection; matched 'accurate data and records'"),
 56: (RL, "Whiting UDO land-use definitions define 'Data Processing, Hosting and Related Services (NAICS 518)' - the NAICS code for data centres and hosting"),
 57: (RL, "Whiting authorised-uses table lists NAICS 518 Data Processing, Hosting and Related Services"),
 58: (RL, "Whiting Downtown Business district permits 'Data Processing, Hosting and Related Services'"),
 59: (RL, "Whiting Boulevard Business district permits 'Data Processing, Hosting and Related Services'"),
 60: (NR, "utility identity-theft programme; matched outsourced 'web hosting' and 'call center operations' - a data-security policy, not a land use"),
 61: (NR, "floodplain status standards; matched flood 'data'"),
 62: (RL, "Indianapolis-Marion zoning definitions list 'data processing and analysis center' among uses"),
 63: (NR, "flood-control secondary district; matched 'maps and data'"),
 64: (NR, "gravel/sand/borrow district; matched 'every 30 feet on center' planting"),
 65: (NF, "Special Use Districts list in the Indianapolis primary-districts chapter; snippet resolved to 'diversion center' but a special-use list is where a data-centre use would appear"),
 66: (NR, "protections for the homeless; matched 'accurate data'"),
 67: (NR, "IT board definitions; internal information technology governance"),
 68: (NR, "IT board membership qualification referencing a 'large data processing installation' - a person's experience, not a land use"),
 69: (NR, "IT board approval of data processing service contracts - procurement"),
 70: (NR, "official city websites; matched 'web hosting' purchasing approval"),
 71: (NR, "personnel definitions; matched 'director of central data processing'"),
 72: (NR, "criminal investigation fund; matched purchase of automated data processing equipment"),
 73: (NF, "Bloomington zoning districts establish a 'Showers Technology Park Overlay'; a technology-park overlay is a plausible host district and the snippet only names it"),
 74: (NR, "defined words; matched 'day care center'"),
 75: (NR, "public-safety advisory commission; matched 'gather data'"),
 76: (NR, "primary plat approval; matched 'indicating the data by notations'"),
 77: (NR, "zoning definitions, but the matched entries are a WIRELESS telecommunications facility and 'Community Center'"),
 78: (NF, "Kendallville LAND USE MATRIX with a 'Technology Park' row; a use matrix is exactly where a data-centre use would be listed and the snippet shows one line"),
 79: (NR, "primary plat contents; matched 'indicating the data'"),
 80: (NR, "wireless telecommunication facility standards - towers"),
 81: (NR, "nonconforming telecommunication facilities - towers"),
 82: (NF, "Portage zoning DEFINED WORDS section; matched a wireless-facility definition and a truncated business-school entry, but a zoning definitions section is where a data-centre use would be defined"),
 83: (NR, "county list of grant funds; matched 'Expo Center Fund'"),
 84: (NR, "fixed-asset capitalisation policy; matched 'data processing equipment'"),
 85: (NR, "stormwater permit procedure; matched 'plans and accompanying data'"),
 86: (NR, "final site plan approval thresholds; matched 'C-3 city center commercial district'"),
 87: (NR, "application form requirements; matched 'center-lines' of streets"),
 88: (RL, "North Liberty accessory uses permits 'Internet-based services, such as ... data processing' in the TC, C and GI districts"),
 89: (NR, "regulations for WIRELESS telecommunication facilities - towers"),
 90: (NR, "enforcement penalties for wireless facility signs and lights"),
 91: (NF, "North Liberty zoning DEFINITIONS section; snippet resolved to 'community center' but this is where a data-centre use would be defined"),
 92: (NR, "residential lawn parking; matched 'statistical data'"),
 93: (NR, "precious metals dealers; matched 'computer data system'"),
 94: (NR, "biting animals; matched 'Animal Resource Center'"),
 95: (NR, "vacant building maintenance; matched 'center of the vertical boards' in a board-up spec"),
 96: (NR, "section RESERVED - repeals a data processing board and agency; an administrative body, and repealed"),
 97: (NR, "public safety communications definitions; matched 'consolidated dispatch center'"),
 98: (NR, "septic system design; matched 'other technical information or data'"),
 99: (NR, "application form requirements; matched 'center-lines' of streets"),
 100: (NF, "St. Joseph County planning and zoning DEFINITIONS; snippet resolved to the wireless-facility entry, but this is the county's definitions section"),
 101: (NR, "penalty provision; assesses property used for a wireless telecommunications facility"),
 102: (NR, "accessory uses; wireless facility compound screening"),
 103: (NF, "LAND USE STANDARDS of the Indiana Enterprise Center Overlay - the LEAP-adjacent overlay. Snippet resolved to 'child care center', but this is the operative land-use section of the state's most significant data-centre overlay"),
 104: (RL, "IEC Overlay DEFINITIONS define a use 'concerned with building, maintaining, or processing data and providing other data processing services'"),
 105: (NR, "mobile home park PUD rules; matched 'recycling drop-off center'"),
 106: (NR, "prohibited signs; matched 'electronic message center sign'"),
 107: (NR, "siting hierarchy for WIRELESS telecommunication facilities - towers"),
 108: (NR, "solar energy system standards; matched 'center of any public road' setback"),
 109: (NR, "stormwater appeals; matched 'data extrapolated from HYDRAIN'"),
 110: (NR, "subdivision construction plans; matched 'center lines of all roads'"),
 111: (NR, "fire prevention right of entry; matched 'police department dispatch center'"),
 112: (NR, "special exceptions; the matched use is a telecommunications facility - tower"),
 113: (NF, "Wabash TABLE OF PERMITTED USES; snippet shows only the Telecommunications Facility row, but a permitted-use table is where a data-centre use would be listed"),
 114: (NR, "zoning definitions; defines a telecommunications facility as transmitting equipment and structures - a tower, not a data centre"),
 115: (NR, "sign regulations; matched 'Shopping center'"),
}

rows = [dict(r) for r in client.query(f"""
SELECT jurisdiction, county, code_section_id,
       ANY_VALUE(section_title) section_title,
       ANY_VALUE(ancestors_path) ancestors_path,
       ANY_VALUE(url) url,
       STRING_AGG(DISTINCT search_phrase ORDER BY search_phrase) search_phrases,
       COUNT(*) n_candidate_rows
FROM `{SRC}`
WHERE NOT REGEXP_CONTAINS(LOWER(IFNULL(snippet,'')), r'data cent(er|re)')
GROUP BY 1,2,3
ORDER BY county, jurisdiction, code_section_id""")]

assert len(rows) == len(V), f"section count moved: {len(rows)} sections vs {len(V)} verdicts"
total = sum(r["n_candidate_rows"] for r in rows)
assert total == 146, f"candidate rows moved: {total}, expected 146"

out = []
for i, r in enumerate(rows, 1):
    verdict, reason = V[i]
    out.append({**r, "verdict": verdict, "reason": reason,
                "triaged_at": BUILT, "triage_method": "manual read of section_title + "
                "ancestors_path + snippet against a land-use test; unit of judgment is the "
                "distinct section, not the row"})

schema = [bigquery.SchemaField(k, "INT64" if k == "n_candidate_rows" else "STRING")
          for k in out[0]]
client.load_table_from_json(
    out, f"{DS}.in_ordinances_dc_v2_triage",
    job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE")).result()

n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_ordinances_dc_v2_triage`"))[0].n
print(f"in_ordinances_dc_v2_triage: {n} sections covering {total} candidate rows\n")

for x in client.query(f"""SELECT verdict, COUNT(*) sections, SUM(n_candidate_rows) rows_
    FROM `{DS}.in_ordinances_dc_v2_triage` GROUP BY 1 ORDER BY sections DESC"""):
    print(f"  {x.verdict:16s} {x.sections:>4} sections · {x.rows_:>4} candidate rows")

print("\nRELEVANT and NEEDS_FULL_TEXT, by county:")
for x in client.query(f"""SELECT county, jurisdiction,
      COUNTIF(verdict='RELEVANT') rel, COUNTIF(verdict='NEEDS_FULL_TEXT') nft
    FROM `{DS}.in_ordinances_dc_v2_triage` GROUP BY 1,2
    HAVING rel > 0 OR nft > 0 ORDER BY rel DESC, nft DESC"""):
    print(f"  {x.county:14s} {x.jurisdiction:28s} RELEVANT={x.rel:<3} NEEDS_FULL_TEXT={x.nft}")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_ordinances_dc_v2_triage'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at) "
    f"VALUES (@t,@s,@m,@n,CURRENT_TIMESTAMP())",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "in_ordinances_dc_v2_triage"),
        bigquery.ScalarQueryParameter("s", "STRING", f"{SRC} (not modified)"),
        bigquery.ScalarQueryParameter(
            "m", "STRING",
            "Manual triage of the 146 candidate rows that do NOT contain 'data cent(er|re)'. "
            "Unit of judgment is the distinct SECTION (115), so one section cannot receive two "
            "contradictory verdicts; n_candidate_rows reconciles 115 sections to 146 rows. "
            "Test: (1) is it a land-use instrument at all - finance/purchasing/personnel/records "
            "chapters are not; (2) does it name a use a data centre falls under; (3) a WIRELESS "
            "telecommunications facility is a tower, NOT a data centre; (4) NEEDS_FULL_TEXT only "
            "for use tables and zoning definitions sections whose 240-char snippet resolved to a "
            "false positive - absence in the snippet is not absence in the section."),
        bigquery.ScalarQueryParameter("n", "INT64", int(n))])).result()
print("\nregistered in_ordinances_dc_v2_triage")
