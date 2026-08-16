"""STAGE 3 -- county-website ordinances. THE FINDING THAT INVALIDATES A CODIFIED-ONLY CORPUS.

WHY THIS EXISTS. Stages 1 and 2 search CODIFIED codes. Boone County -- the LEAP district, the
single largest data-centre story in Indiana -- adopted a ONE-YEAR MORATORIUM on new data centre
development on 2026-06-15. It appears in NEITHER publisher corpus:

  * Boone County is not a Municode client at all, and
  * Boone County IS an American Legal client (slug `boonecountyin`) whose code is behind the
    Cloudflare wall recorded in stage 2, and
  * even with full access, a June-2026 commissioners' ordinance is not yet CODIFIED -- amlegal
    reports Boone's code currency as an earlier supplement.

So the most decision-relevant posture in the state -- a moratorium, i.e. "you cannot build here
right now" -- is structurally invisible to a codified-code search. Six counties are in this
category. A siting product that reads only codified codes would show Boone County as SILENT,
which inverts the truth.

EVIDENCE GRADING IS THE POINT OF THIS TABLE. `evidence_grade` is either
  VERIFIED_AT_OFFICIAL_SOURCE -- fetched from the county's own .gov site, publisher's own words
  REPORTED_NEEDS_VERIFICATION -- found via news/aggregator, NOT yet confirmed at the .gov source
Nothing is promoted between grades without a fetch. The second grade is a WORKLIST, not a fact,
and must never be rendered as a posture.

robots.txt was read for every .gov host fetched; boonecounty.in.gov and miamicountyin.gov both
publish `User-agent: * / Disallow:` (allow-all). Dates are the PUBLISHER'S OWN adoption dates;
`_pulled_at` is separate.
"""
import datetime, json
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")
PULLED = datetime.datetime.now(datetime.timezone.utc).isoformat()

ROWS = [
    dict(
        jurisdiction="Boone County", county="Boone", state="IN",
        provider="county_website", publisher_host="boonecounty.in.gov",
        posture_source_words="moratorium",
        instrument="one-year moratorium on new data center development",
        applies_to="unincorporated Boone County",
        observed_date="2026-06-15",
        observed_date_note="adoption date stated by the county: Board of Commissioners "
                           "unanimously approved 2026-06-15",
        effective_from="2026-06-16", effective_to="2027-06-15",
        verbatim_snippet="temporarily pauses the filing, processing, review, and acceptance of "
                         "applications related to new data center facilities in unincorporated "
                         "areas of the county",
        verbatim_purpose="the action will provide time to evaluate the potential impacts of data "
                         "center development and determine whether updates to the county's "
                         "planning and zoning regulations are needed",
        url="https://boonecounty.in.gov/2026/06/15/19190/",
        evidence_grade="VERIFIED_AT_OFFICIAL_SOURCE",
        why_publishers_miss_it="not a Municode client; amlegal client `boonecountyin` is behind "
                               "the Cloudflare wall AND a 2026 ordinance is not yet codified",
        ordinance_number=None),
    dict(
        jurisdiction="Miami County", county="Miami", state="IN",
        provider="county_website", publisher_host="miamicountyin.gov",
        posture_source_words="temporary moratorium",
        instrument="temporary moratorium on acceptance/processing/approval of data centre "
                   "applications and permits; a permanent regulating ordinance was still PROPOSED",
        applies_to="Miami County (improvement location permits)",
        observed_date="2026-05-04",
        observed_date_note="county states the Board of Commissioners adopted the moratorium "
                           "2026-05-04; plan commission favourable recommendation 2026-05-13; "
                           "proposed ordinance set for board consideration 2026-07-20",
        effective_from="2026-05-04", effective_to=None,
        verbatim_snippet="temporary moratorium on the acceptance, processing, and approval of all "
                         "applications and permits, including the issuance of improvement location "
                         "permits, including construction or operation of data centers",
        verbatim_purpose="establishing regulations for the review, processing, and approval of "
                         "applications and permits related to data center developments",
        url="https://www.miamicountyin.gov/910/Proposed-Data-Center-Ordinance-Moratoriu",
        evidence_grade="VERIFIED_AT_OFFICIAL_SOURCE",
        why_publishers_miss_it="not a Municode client; not codified at the time of pull",
        ordinance_number=None),
    # ---- LEADS. Reported by news/aggregators, NOT confirmed at the county's own site by this
    # run. Recorded so the gap is actionable; MUST NOT be rendered as posture.
    dict(jurisdiction="Marshall County", county="Marshall", state="IN",
         provider="county_website_lead", publisher_host=None,
         posture_source_words="prohibition / ban",
         instrument="reported: replaced a temporary moratorium with a PROHIBITION in the county "
                    "zoning ordinance",
         applies_to=None, observed_date="2026-04-20",
         observed_date_note="reported adoption date; NOT verified at the county source",
         effective_from=None, effective_to=None, verbatim_snippet=None, verbatim_purpose=None,
         url="https://www.datacenterbans.com/state/indiana",
         evidence_grade="REPORTED_NEEDS_VERIFICATION",
         why_publishers_miss_it="amlegal client `marshallcountyin` is behind the Cloudflare wall",
         ordinance_number=None),
    dict(jurisdiction="Madison County", county="Madison", state="IN",
         provider="county_website_lead", publisher_host=None,
         posture_source_words="moratorium",
         instrument="reported: six-month moratorium, adopted unanimously, effective immediately",
         applies_to=None, observed_date="2026-06",
         observed_date_note="reported month only; NOT verified at the county source",
         effective_from=None, effective_to=None, verbatim_snippet=None, verbatim_purpose=None,
         url="https://www.lpm.org/news/2026-06-17/indiana-community-passes-short-term-data-center-moratorium",
         evidence_grade="REPORTED_NEEDS_VERIFICATION",
         why_publishers_miss_it="no Municode or amlegal county client found",
         ordinance_number=None),
    dict(jurisdiction="Fulton County", county="Fulton", state="IN",
         provider="county_website_lead", publisher_host=None,
         posture_source_words="moratorium",
         instrument="reported: one-year moratorium adopted 2-1 while the county studies siting rules",
         applies_to=None, observed_date="2026-03-02",
         observed_date_note="reported adoption date; NOT verified at the county source",
         effective_from=None, effective_to=None, verbatim_snippet=None, verbatim_purpose=None,
         url="https://www.datacenterbans.com/state/indiana",
         evidence_grade="REPORTED_NEEDS_VERIFICATION",
         why_publishers_miss_it="no Municode or amlegal county client found",
         ordinance_number=None),
    dict(jurisdiction="Starke County", county="Starke", state="IN",
         provider="county_website_lead", publisher_host="starke.in.gov",
         posture_source_words="draft ordinance",
         instrument="DRAFT data centre ordinance posted 2025-11-12; status at pull time unknown",
         applies_to=None, observed_date="2025-11-12",
         observed_date_note="date in the county's own draft filename; adoption NOT confirmed",
         effective_from=None, effective_to=None, verbatim_snippet=None, verbatim_purpose=None,
         url="https://starke.in.gov/wp-content/uploads/2025/11/Draft-Ordinance-Data-Center-11.12.25.pdf",
         evidence_grade="REPORTED_NEEDS_VERIFICATION",
         why_publishers_miss_it="Knox (Municode, Starke County seat) code search returned 2 hits "
                                "but the COUNTY ordinance is on the county's own site as a PDF",
         ordinance_number=None),
]

for r in ROWS:
    r["_pulled_at"] = PULLED
    r["_source_kind"] = "county government website"

keys = sorted({k for r in ROWS for k in r})
client.load_table_from_json(
    [{k: (None if r.get(k) is None else str(r.get(k))) for k in keys} for r in ROWS],
    f"{DS}.in_ordinances_dc_county_sites_v2",
    job_config=bigquery.LoadJobConfig(
        schema=[bigquery.SchemaField(k, "STRING") for k in keys],
        write_disposition="WRITE_TRUNCATE")).result()
n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_ordinances_dc_county_sites_v2`"))[0].n
v = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_ordinances_dc_county_sites_v2` "
                      f"WHERE evidence_grade='VERIFIED_AT_OFFICIAL_SOURCE'"))[0].n
print(f"loaded {n} rows ({v} verified at official source, {n-v} leads) "
      f"-> in_ordinances_dc_county_sites_v2")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_ordinances_dc_county_sites_v2'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at, notes) "
    f"VALUES (@t,@s,@m,@n,CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "in_ordinances_dc_county_sites_v2"),
        bigquery.ScalarQueryParameter("s", "STRING", "Indiana county government websites"),
        bigquery.ScalarQueryParameter("m", "STRING",
            "Data-centre moratoria/bans adopted by county commissioners and published on county "
            ".gov sites -- NOT present in any codified-code corpus. Boone and Miami fetched from "
            "the county's own site (robots allow-all) and carry the publisher's verbatim wording "
            "and its own adoption date; the rest are leads."),
        bigquery.ScalarQueryParameter("n", "INT64", int(n)),
        bigquery.ScalarQueryParameter("no", "STRING",
            "READ evidence_grade BEFORE USING ANY ROW. Only VERIFIED_AT_OFFICIAL_SOURCE rows are "
            "facts; REPORTED_NEEDS_VERIFICATION rows are a worklist and must never be rendered "
            "as a posture. This table is the counter-example to a codified-only corpus: a "
            "moratorium is the strongest siting signal there is and none of these appear in "
            "in_ordinances_dc_v2.")])).result()

client.query(
    "INSERT INTO `energy-platfrom.energy.registry_sources` "
    "(source_name, status, endpoint, endpoint_kind, acquisition_method, object_names, "
    " updated_by, geography_state, last_validated_at) "
    "VALUES (@n,@s,@e,@k,@m,@o,'indiana-app-ordinances-agent','IN',CURRENT_TIMESTAMP())",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("n", "STRING",
            "Indiana county-website data-centre moratoria and bans (not codified)"),
        bigquery.ScalarQueryParameter("s", "STRING", "PARTIAL"),
        bigquery.ScalarQueryParameter("e", "STRING", "https://boonecounty.in.gov/ ; https://www.miamicountyin.gov/"),
        bigquery.ScalarQueryParameter("k", "STRING", "html"),
        bigquery.ScalarQueryParameter("m", "STRING",
            "targeted fetch of county .gov pages after robots.txt check (allow-all); verbatim "
            "wording + the county's own adoption date; evidence-graded, leads kept separate"),
        bigquery.ArrayQueryParameter("o", "STRING", ["in_ordinances_dc_county_sites_v2"])])).result()
print("registered + appended to registry_sources")
