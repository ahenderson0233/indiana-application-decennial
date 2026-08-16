"""B4 — the unresolved Indianapolis colo facilities: street addresses, or the truth that
there is no building to pin.

WHAT THIS IS. Eight Cloudscene Indiana rows were flagged 'present in Cloudscene, absent from
our pinned DC layer'. Cloudscene publishes NO addresses and NO coordinates, and its Terms of
Service (explore.cloudscene.com/terms-of-service, section 4 'Fair use') forbid automated
access: "use any spider, bot, scraper or other automated means to access the Platform" and
"frame, mirror, scrape, data mine, extract or re-distribute data or other content you access
through the Platform". So Cloudscene itself was NOT scraped — it is recorded BLOCKED and the
resolution was done from the operators' own pages (live and Wayback-archived), the PeeringDB
public API, operator press releases, and the Marion County GIS crosswalks we already hold.

THE HEADLINE. ZERO of the eight are genuinely missing buildings. Five are already pinned in
`in_data_centers_located` under other names (CenturyLink was renamed Lumen in 2020; the
DataBank and Expedient pins simply carry different name forms). One (365 Data Centers) was a
suite INSIDE the 701 W Henry St carrier hotel, sold to Netrality in 2022. One (CenturyLink
Indianapolis 3) is a directory numbering ghost — the public record documents exactly TWO
distinct Lumen buildings in Indianapolis. One (AxiaTP) is an IT-services company whose own
site said its colocation was "offered in partnered facilities" — there is no AxiaTP building.

THIS IS A CURATED LOADER, NOT A SCRAPER. The evidence was gathered by hand on 2026-08-16
(every fetch robots-checked first; PeeringDB API used with honest UA and >=1.2s spacing;
sources that walled themselves — datacenters.com robots.txt 403, datacenterdynamics.com
robots disallows ClaudeBot, datacentermap.com 429 on robots.txt — were NOT fetched).
Re-running this script re-loads the curated rows; it does not re-hammer anyone's site.
Full narrative: scrapers/lane_f/COLO_ADDRESS_FINDINGS.md.

Rules honoured: writes ONLY to energy-platfrom.indiana_app (new table, nothing existing
touched); registered in `_registry` in the SAME run; one APPEND-only row into
energy.registry_sources recording the Cloudscene terms wall (the sanctioned exception);
column names BigQuery-legal, no column dropped; NO centroids — coordinates only where a
source publishes them (PeeringDB / baxtel-held) and parcel numbers only from crosswalks we
hold; a facility with no building gets NULL coordinates, not a city point.
"""
import datetime
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
TABLE = "in_dc_colo_resolved"
client = bigquery.Client(project="energy-platfrom")
PULLED = datetime.datetime.now(datetime.timezone.utc).isoformat()

ROWS = [
    dict(
        cloudscene_slug="365-data-centers-indianapolis",
        facility_name="365 Data Centers Indianapolis",
        operator="365 Data Centers (exited 2022; suite now Netrality)",
        verdict="SAME_BUILDING_AS",
        same_building_as="Netrality 701 W Henry (Indy Telcom Center) — pinned in in_data_centers_located",
        street_address="701 West Henry Street, Suite 101",
        city="Indianapolis", state="IN", zip="46225",
        latitude=39.759534, longitude=-86.170711,
        coord_source="PeeringDB fac 2018 (coords are the 701 W Henry BUILDING's, not a separate site)",
        parcel_state_number="49-11-11-183-001.012-101",
        parcel_source="in_marion_address_crosswalk + in_marion_parcel_crosswalk (701 W HENRY ST, PARCEL_I 1104775)",
        already_pinned_as="Netrality 701 W Henry (baxtel, 39.759727,-86.170921)",
        source_url="http://web.archive.org/web/20140508052357/http://365datacenters.com/indianapolis-data-center/ | http://web.archive.org/web/20210413112512/https://365datacenters.com/colocation/indianapolis-data-center/ | https://www.globenewswire.com/en/news-release/2022/04/05/2416608/0/en/Netrality-Data-Centers-Acquires-365-Data-Centers-Indianapolis-Facility-on-the-Indy-Telcom-Campus.html",
        source_type="operator site (archived) + operator press release",
        evidence_snippet="2014 operator site: '701 West Henry Street, Suite 101, Indianapolis, IN 46225 ... service-in1@' | 2021 operator site: '701 West Henry Street Indianapolis, IN 46225 ... Our Indianapolis data center is centrally located in the only Telecom campus in downtown within walking distance of the Lucas Oil Stadium.' | press 2022-04-05: 'Netrality Data Centers announced the acquisition of 365 Data Centers' Indianapolis facility, located on the Indy Telcom campus.'",
        confidence="HIGH — the operator's own site printed this address for 8+ years; it was a SUITE inside the carrier hotel, acquired by Netrality in April 2022; 365's current site lists no Indianapolis location. A provider presence inside a pinned building, not a missing building.",
        notes="Cloudscene row is STALE (operator exited 2022). datacentermap.com's slug 365main-indianapolis now titles itself 'Netrality - Indy Telcom Suite 101'.",
    ),
    dict(
        cloudscene_slug="axia-technology-partners-indianapolis",
        facility_name="Axia Technology Partners Indianapolis",
        operator="Axia Technology Partners (AxiaTP)",
        verdict="NOT_FOUND",
        same_building_as=None,
        street_address=None, city="Indianapolis", state="IN", zip=None,
        latitude=None, longitude=None,
        coord_source="none — no facility building exists to locate; coordinates deliberately NULL (no centroid)",
        parcel_state_number=None, parcel_source=None,
        already_pinned_as=None,
        source_url="http://web.archive.org/web/20160508154509/https://www.axiatp.com/colocation/ | http://web.archive.org/web/20161202214200/https://www.axiatp.com/ | https://www.axiatp.com/",
        source_type="operator site (archived + current) + PeeringDB API (absence)",
        evidence_snippet="Own /colocation/ page, 2016: 'By partnering with data centers throughout the country, we are able to provide our clients with the multiple options for securing their data. All of the facilities we use are Tier 3 and above.' | Own homepage, 2016: 'Our colocation services are offered in partnered facilities across North America.' | PeeringDB fac search 2026-08-16: no Axia facility record anywhere; current axiatp.com advertises managed IT only, no colocation page.",
        confidence="HIGH that no AxiaTP-operated data-centre building exists — their own marketing said the colo was resold partner-facility space. WHICH partner facility housed their gear is not publicly stated. Their offices (151 N Delaware St Ste 1750, Indianapolis 46204 then; 4273 Perry Worth Rd Ste 100, Whitestown 46075 now) are offices, NOT facilities, and are deliberately not recorded as an address here.",
        notes="Cloudscene row is a service listing, not a building. Correctly absent from a building layer.",
    ),
    dict(
        cloudscene_slug="centurylink-indianapolis-1",
        facility_name="Centurylink Indianapolis 1",
        operator="Lumen Technologies (CenturyLink renamed 2020; site ex-Level 3)",
        verdict="RESOLVED",
        same_building_as=None,
        street_address="1902 S East St",
        city="Indianapolis", state="IN", zip="46225",
        latitude=39.741514, longitude=-86.150665,
        coord_source="baxtel (held in energy.data_centers_baxtel; already the pin for 'Lumen Indianapolis 1')",
        parcel_state_number="49-11-13-215-005.000-101",
        parcel_source="in_marion_address_crosswalk (1902 S EAST ST; class IND WHSE-350)",
        already_pinned_as="Lumen Indianapolis 1 (baxtel, 39.741514,-86.150665)",
        source_url="https://baxtel.com/data-center/lumen-indianapolis-1 | https://www.datacentermap.com/usa/indiana/indianapolis/level3-indianapolis1/ | https://www.datacenters.com/lumen-indianapolis-1",
        source_type="directories (baxtel page fetched; DCM/datacenters.com via search-indexed titles) — Lumen publishes no public page per PoP",
        evidence_snippet="baxtel page: '1902 South East Street', operator 'Lumen Technologies', formed from 'CenturyLink and Level(3)' | DCM slug level3-indianapolis1 titles: 'Lumen Indianapolis 1 Data Center | 1902 S. East Street' | datacenters.com: 'Lumen Indianapolis 1 data center at 1902 S. East Street offers 20,000 square feet'.",
        confidence="HIGH on the building and address — three independent directories converge, all naming this site #1, and it is already pinned. The crosscheck missed it because Cloudscene says 'CenturyLink' and the layer says 'Lumen' (2020 rename) — an instrument artifact, not a gap.",
        notes="PeeringDB lists NO Lumen facility in Indianapolis at all (netfac for AS3356/AS209/AS3549 in Indianapolis: zero rows) — Lumen under-registers; absence there is non-evidence.",
    ),
    dict(
        cloudscene_slug="centurylink-indianapolis-2",
        facility_name="Centurylink Indianapolis 2",
        operator="Lumen Technologies (site ex-TW Telecom, then Level 3, then CenturyLink)",
        verdict="RESOLVED",
        same_building_as=None,
        street_address="4625 W 86th St, Suite 500",
        city="Indianapolis", state="IN", zip="46268",
        latitude=39.91079, longitude=-86.239243,
        coord_source="baxtel (held in energy.data_centers_baxtel; already the pin for 'Lumen Indianapolis 3')",
        parcel_state_number="49-03-19-127-013.000-600",
        parcel_source="in_marion_address_crosswalk (4625 W 86TH ST)",
        already_pinned_as="Lumen Indianapolis 3 (baxtel, 39.91079,-86.239243) — SAME BUILDING, different index",
        source_url="https://www.datacentermap.com/usa/indiana/indianapolis/twtc-indianapolis/ | https://baxtel.com/data-center/lumen-indianapolis-3 | https://www.datacenters.com/lumen-indianapolis-3",
        source_type="directories (baxtel page fetched; DCM/datacenters.com via search-indexed titles)",
        evidence_snippet="DCM slug twtc-indianapolis titles: 'Lumen Indianapolis 2 Data Center | 4625 W 86th St' | baxtel lumen-indianapolis-3 page: '4625 West 86th Street' 'Suite 500', 'a former tw telecom site' (Level 3 acquired TW Telecom 2014; CenturyLink acquired Level 3 2017; Lumen 2020) | datacenters.com lumen-indianapolis-3: 4625 W 86th St.",
        confidence="HIGH on the building and address. MEDIUM on the index mapping: Cloudscene publishes no address, and the directories DISAGREE on this building's number — DCM calls 4625 W 86th 'Indianapolis 2', baxtel and datacenters.com call it 'Indianapolis 3'. The building set is certain; which Cloudscene index it carries is not.",
        notes="Already pinned (as Lumen Indianapolis 3). The 2-vs-3 index conflict is recorded, not resolved — resolving it needs Cloudscene's own page, which its terms forbid us to scrape.",
    ),
    dict(
        cloudscene_slug="centurylink-indianapolis-3",
        facility_name="Centurylink Indianapolis 3",
        operator="Lumen Technologies",
        verdict="SAME_BUILDING_AS",
        same_building_as="4625 W 86th St under baxtel/datacenters.com numbering (the centurylink-indianapolis-2 row's building); at most an on-net PoP presence inside Netrality Indy Telcom 701/733 W Henry otherwise",
        street_address=None, city="Indianapolis", state="IN", zip=None,
        latitude=None, longitude=None,
        coord_source="none — deliberately NULL: no third distinct building exists to locate, and pinning either candidate would double-count",
        parcel_state_number=None, parcel_source=None,
        already_pinned_as="collapses onto pins that already exist (Lumen Indianapolis 1/3 and/or Netrality 701/733)",
        source_url="https://baxtel.com/data-center/lumen-indianapolis-1 | https://baxtel.com/data-center/lumen-indianapolis-3 | https://www.globenewswire.com/en/news-release/2022/04/05/2416608/0/en/Netrality-Data-Centers-Acquires-365-Data-Centers-Indianapolis-Facility-on-the-Indy-Telcom-Campus.html | https://api.peeringdb.com/api/netfac?net_id=504&city=Indianapolis",
        source_type="directories + PeeringDB API + operator press",
        evidence_snippet="Public record documents exactly TWO distinct Lumen/CenturyLink buildings in Indianapolis (1902 S East St; 4625 W 86th St) — no directory lists a third address. | Netrality press 2022-04-05 lists Lumen among providers with 'direct connectivity' at the Indy Telcom campus: '...leading service providers including AT&T, Cogent Communications, Lumen, Crown Castle, Peerless Network, US Signal, Windstream, and Zayo.' | PeeringDB netfac for every Lumen ASN in Indianapolis: zero rows.",
        confidence="HIGH that there is no third CenturyLink/Lumen building in Indianapolis; this Cloudscene entry is a numbering ghost (directories renumbered the same two buildings 1/2/3 inconsistently) or reflects carrier presence inside the already-pinned Henry St carrier hotel. Correctly absent from a building layer.",
        notes="A wrong coordinate here would fabricate a site; none is recorded.",
    ),
    dict(
        cloudscene_slug="databank-ind1",
        facility_name="Databank Ind1",
        operator="DataBank (ex-LightBound; acquisition announced 2018-12-17)",
        verdict="RESOLVED",
        same_building_as=None,
        street_address="731 West Henry Street",
        city="Indianapolis", state="IN", zip="46225",
        latitude=39.759374, longitude=-86.172235,
        coord_source="PeeringDB fac 10929 (published; zipcode 46225-1114)",
        parcel_state_number="49-11-11-183-001.006-101",
        parcel_source="in_marion_address_crosswalk + in_marion_parcel_crosswalk (731 W HENRY ST, PARCEL_I 1104769)",
        already_pinned_as="Databank Indianapolis IND1 (baxtel, 39.759464,-86.171951)",
        source_url="https://www.databank.com/data-centers/indianapolis/ | https://api.peeringdb.com/api/fac/10929 | https://www.prnewswire.com/news-releases/databank-announces-acquisition-of-indianapolis-based-lightbound-300767206.html",
        source_type="operator site + PeeringDB + press",
        evidence_snippet="Operator page: 'IND1 - Downtown Indianapolis Data Center ... 731 West Henry Street, Indianapolis, IN 46225', 'purpose-built data center' and 'carrier hotel' on Henry Street, 'the crossroads of fiber and telecommunications for the State of Indiana' | PeeringDB fac 10929: address1 '731 W Henry St', 46225-1114, 39.759374,-86.172235.",
        confidence="HIGH — operator's own page and PeeringDB agree. A distinct building (own parcel) WITHIN the Indy Telcom carrier-hotel campus: its parcel 49-11-11-183-001.006-101 shares the subdivided campus parcel group with 701 (...012) and 733 (...005). ALREADY PINNED — the crosscheck's 'absent' flag contradicts the live layer; instrument artifact.",
        notes="DCM slug lightbound-731-henry-street titles 'DataBank IND1 - Downtown Indianapolis Data Center (2.1 MW)'.",
    ),
    dict(
        cloudscene_slug="databank-ind2",
        facility_name="Databank Ind2",
        operator="DataBank (ex-LightBound)",
        verdict="RESOLVED",
        same_building_as=None,
        street_address="650 West Henry Street",
        city="Indianapolis", state="IN", zip="46225",
        latitude=39.760096, longitude=-86.170486,
        coord_source="PeeringDB fac 10930 (published)",
        parcel_state_number="49-11-11-138-006.000-101",
        parcel_source="in_marion_address_crosswalk (650 W HENRY ST, PARCEL_I 1105072; class OTHER INDUSTRIAL STRUCTURES-399)",
        already_pinned_as="Databank Indianapolis IND2 (baxtel, 39.759464,-86.171265)",
        source_url="https://www.databank.com/data-centers/indianapolis/ | https://api.peeringdb.com/api/fac/10930",
        source_type="operator site + PeeringDB",
        evidence_snippet="Operator page: 'IND2 - Downtown Indianapolis Data Center ... 650 West Henry Street, Indianapolis, IN 46225' | PeeringDB fac 10930: address1 '650 West Henry Street', 46225, 39.760096,-86.170486.",
        confidence="HIGH — operator page and PeeringDB agree. Its own building and parcel on the Henry St telecom corridor (north side, across from the 701/731/733 campus group). ALREADY PINNED, though the held baxtel pin sits ~90 m from PeeringDB's published point — both site-precision; flagged for reconciliation, not corrected here.",
        notes="DCM slug lightbound-650 titles 'DataBank IND2 - Downtown Indianapolis Data Center (3.75 MW)'.",
    ),
    dict(
        cloudscene_slug="expedient-data-centers-indianapolis",
        facility_name="Expedient Data Centers Indianapolis",
        operator="Expedient",
        verdict="RESOLVED",
        same_building_as=None,
        street_address="701 Congressional Blvd.",
        city="Carmel", state="IN", zip="46032",
        latitude=39.963184, longitude=-86.145575,
        coord_source="PeeringDB fac 8458 (published; DCM coords identical; baxtel pin 39.963175,-86.145515)",
        parcel_state_number=None,
        parcel_source="none held — Hamilton County parcel, outside the Marion crosswalks we hold",
        already_pinned_as="Expedient Indianapolis (baxtel, 39.963175,-86.145515)",
        source_url="https://www.expedient.com/data-centers/indianapolis/ | https://api.peeringdb.com/api/fac/8458",
        source_type="operator site + PeeringDB",
        evidence_snippet="Operator page: '701 Congressional Blvd., Carmel, IN 46032', '53,000 sq. ft. total data center space with 26,000 sq. ft. raised floor', '4.4 MW critical IT load with 8.0 MW total generator capacity' | PeeringDB fac 8458: address1 '701 Congressional Blvd', Carmel IN 46032.",
        confidence="HIGH — operator's own page prints the address. NOTE the mailing-city trap runs the OTHER way here: Cloudscene files it under 'Indianapolis' (the market) but the building is in Carmel. ALREADY PINNED at the right spot; the crosscheck's 'absent' flag was an instrument artifact.",
        notes="Standalone suburban facility — the one entry of the eight that is nowhere near the Henry St carrier hotel.",
    ),
]

# ---- load ---------------------------------------------------------------------------------
for r in ROWS:
    r["_pulled_at"] = PULLED

COLS = ["cloudscene_slug", "facility_name", "operator", "verdict", "same_building_as",
        "street_address", "city", "state", "zip", "latitude", "longitude", "coord_source",
        "parcel_state_number", "parcel_source", "already_pinned_as", "source_url",
        "source_type", "evidence_snippet", "confidence", "notes", "_pulled_at"]
schema = [bigquery.SchemaField(c, "FLOAT64" if c in ("latitude", "longitude") else
                               ("TIMESTAMP" if c == "_pulled_at" else "STRING"))
          for c in COLS]
job = client.load_table_from_json(
    [{c: r.get(c) for c in COLS} for r in ROWS], f"{DS}.{TABLE}",
    job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE"))
job.result()
n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.{TABLE}`"))[0].n
print(f"loaded {n} rows -> {TABLE}", flush=True)

# ---- register in the SAME run --------------------------------------------------------------
client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{TABLE}'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
    "VALUES (@t,@s,@m,@n,@g,CURRENT_TIMESTAMP(),@o)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", TABLE),
        bigquery.ScalarQueryParameter("s", "STRING",
            "operator sites (live + Wayback) + PeeringDB public API + operator press releases "
            "+ baxtel pages + Marion GIS crosswalks already held; Cloudscene NOT scraped (ToS forbids)"),
        bigquery.ScalarQueryParameter("m", "STRING",
            "B4 manual multi-source address resolution, verbatim evidence per row; robots.txt "
            "checked before every fetch; honest UA; >=1.2s spacing; walled sources recorded and "
            "skipped (datacenters.com robots 403, datacenterdynamics ClaudeBot-disallowed, "
            "datacentermap 429). NO centroids: coordinates only from PeeringDB/baxtel-published "
            "points; NULL where no building exists. See scrapers/lane_f/COLO_ADDRESS_FINDINGS.md"),
        bigquery.ScalarQueryParameter("n", "INT64", int(n)),
        bigquery.ScalarQueryParameter("g", "FLOAT64", 0.35),
        bigquery.ScalarQueryParameter("o", "STRING",
            "verdicts: 4 RESOLVED (all four already pinned under other names - CenturyLink->Lumen "
            "rename x2, DataBank x2 name-form), 1 RESOLVED-in-Carmel (Expedient, already pinned), "
            "2 SAME_BUILDING_AS (365 DC = suite in Netrality 701 W Henry; CenturyLink Indy 3 = "
            "numbering ghost), 1 NOT_FOUND (AxiaTP resells partner facilities - no building). "
            "ZERO genuinely missing buildings; gb_scanned covers session exploration queries."),
    ])).result()
print("registered in _registry", flush=True)

# ---- record the Cloudscene wall (sanctioned APPEND-only row) --------------------------------
client.query(
    "INSERT INTO `energy-platfrom.energy.registry_sources` "
    "(source_name, domain, origin, endpoint, endpoint_kind, category, geography_state, access, "
    " status, status_measured, last_validated_at, acquisition_method, what_it_provides, method, "
    " notes, updated_by, object_names) "
    "VALUES (@sn,@d,@or2,@e,@ek,@c,@gs,@a,@st,@ts,CAST(@ts AS TIMESTAMP),"
    "@am,@w,@m,@no,@u,@obj)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("sn", "STRING", "cloudscene.com data-centre directory (B4 colo resolution)"),
        bigquery.ScalarQueryParameter("d", "STRING", "cloudscene.com"),
        bigquery.ScalarQueryParameter("or2", "STRING", "https://cloudscene.com"),
        bigquery.ScalarQueryParameter("e", "STRING", "https://explore.cloudscene.com/terms-of-service/"),
        bigquery.ScalarQueryParameter("ek", "STRING", "html"),
        bigquery.ScalarQueryParameter("c", "STRING", "data_centers"),
        bigquery.ScalarQueryParameter("gs", "STRING", "IN"),
        bigquery.ScalarQueryParameter("a", "STRING", "BLOCKED_TERMS"),
        bigquery.ScalarQueryParameter("st", "STRING", "BLOCKED"),
        bigquery.ScalarQueryParameter("ts", "STRING", PULLED),
        bigquery.ScalarQueryParameter("am", "STRING",
            "none — robots.txt permits (User-agent: * / Allow: /) but the Terms of Service forbid "
            "automated access; facilities resolved from operators/PeeringDB/press instead"),
        bigquery.ScalarQueryParameter("w", "STRING",
            "colo facility names/slugs/market only — publishes NO addresses and NO coordinates"),
        bigquery.ScalarQueryParameter("m", "STRING", "terms check 2026-08-16, section 4 'Fair use'"),
        bigquery.ScalarQueryParameter("no", "STRING",
            "Verbatim wall: 'you are not allowed to: a. use any spider, bot, scraper or other "
            "automated means to access the Platform; b. frame, mirror, scrape, data mine, extract "
            "or re-distribute data or other content you access through the Platform' "
            "(explore.cloudscene.com/terms-of-service, accessed 2026-08-16)"),
        bigquery.ScalarQueryParameter("u", "STRING", "lane_f_b4_colo_resolution"),
        bigquery.ArrayQueryParameter("obj", "STRING", ["in_dc_colo_resolved"]),
    ])).result()
print("cloudscene wall appended to energy.registry_sources", flush=True)
print("done")
