"""Operator aliases for the data-centre cross-check — because the gap was in the matcher.

THE DEFECT, measured in COLO_ADDRESS_FINDINGS.md. The cloudscene cross-check flagged 8
Indianapolis colo facilities as absent from our pinned layer. B4 resolved all eight and found
**ZERO were missing buildings**. Five were already pinned under a different operator name:

    CenturyLink Indy 1  -> pinned as "Lumen Indianapolis 1"      (CenturyLink renamed to Lumen, 2020)
    CenturyLink Indy 2  -> pinned as "Lumen Indianapolis 3"      (same rename)
    DataBank IND1       -> pinned, ex-LightBound                 (DataBank acquired LightBound, 2018)
    DataBank IND2       -> pinned, ex-LightBound                 (same)
    Expedient           -> pinned (the building is in Carmel; cloudscene files it under the market)

The matcher stems a name to `[a-z0-9]` and asks whether either string prefixes the other.
`centurylinkindy1` and `lumenindianapolis1` share no prefix, so it reported a gap that did not
exist. **The instrument was wrong, not the layer** — and a false "5 missing data centres" on a
competitive-landscape page is exactly the kind of number a reader would act on.

CLOUDSCENE_GAP.md carries the same defect in the other direction: it matched "Lifeline West Henry"
to "Lifeline Fort Wayne", which are different buildings in different cities.

So: a curated alias table, each row carrying WHY the names differ and the evidence for it. This is
a rename/acquisition ledger, not a scrape — cloudscene's terms forbid automated access and it was
recorded BLOCKED, so the evidence comes from the operators' own sites and press releases, which is
how B4 resolved all eight in the first place.

Writes only to energy-platfrom.indiana_app.
"""
import datetime

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")
BUILT = datetime.datetime.now(datetime.timezone.utc).isoformat()

# alias_from, alias_to, kind, effective_year, evidence
ALIASES = [
    ("CenturyLink", "Lumen", "rename", 2020,
     "CenturyLink rebranded to Lumen Technologies in 2020; baxtel and datacentermap both title "
     "1902 S East St as Lumen Indianapolis 1, ex-'CenturyLink and Level(3)'."),
    ("Level 3", "Lumen", "acquisition_then_rename", 2017,
     "Level 3 acquired by CenturyLink 2017, which became Lumen 2020. datacentermap still carries "
     "the slug level3-indianapolis1 for the Lumen-titled facility."),
    ("Level(3)", "Lumen", "acquisition_then_rename", 2017, "Punctuated form of the same operator."),
    ("TW Telecom", "Lumen", "acquisition_then_rename", 2014,
     "tw telecom acquired by Level 3 in 2014 -> CenturyLink 2017 -> Lumen 2020. datacentermap's "
     "twtc-indianapolis slug titles itself Lumen Indianapolis 2 at 4625 W 86th St."),
    ("LightBound", "DataBank", "acquisition", 2018,
     "DataBank announced the acquisition of Indianapolis-based LightBound on 2018-12-17 "
     "(prnewswire). DCM slugs lightbound-731-henry-street and lightbound-650 are DataBank IND1/IND2."),
    ("365 Data Centers", "Netrality", "acquisition", 2022,
     "Netrality acquired 365 Data Centers' Indianapolis facility on the Indy Telcom campus, "
     "2022-04-05 (globenewswire). 365's own site no longer lists Indianapolis among its markets; "
     "the datacentermap slug 365main-indianapolis now titles itself 'Netrality - Indy Telcom "
     "Suite 101'."),
    ("365main", "Netrality", "acquisition", 2022, "Slug form of the same operator."),
    ("Lifeline Data Centers", "Netrality", "acquisition", 2021,
     "Netrality acquired the Indy Telcom campus (incl. Lifeline) in July 2021. NOTE: Lifeline "
     "operated MULTIPLE buildings - 733 W Henry in Indianapolis and a Fort Wayne site - so this "
     "alias must NOT be used to match on operator alone. CLOUDSCENE_GAP.md wrongly matched "
     "'Lifeline West Henry' to 'Lifeline Fort Wayne': same operator, different cities, different "
     "buildings."),
]

rows = [{"alias_from": a, "alias_to": b, "alias_kind": k, "effective_year": str(y),
         "evidence": e, "built_at": BUILT} for a, b, k, y, e in ALIASES]

COLS = ["alias_from", "alias_to", "alias_kind", "effective_year", "evidence", "built_at"]
client.load_table_from_json(
    rows, f"{DS}.in_dc_operator_aliases",
    job_config=bigquery.LoadJobConfig(
        schema=[bigquery.SchemaField(c, "STRING") for c in COLS],
        write_disposition="WRITE_TRUNCATE")).result()
n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_dc_operator_aliases`"))[0].n
print(f"loaded {n} operator aliases -> in_dc_operator_aliases")

# --- prove the alias table actually closes the gap it was built for ---------------------------
print("\ndoes it resolve the 8 that B4 investigated?")
for r in client.query(f"""
  SELECT facility_name, operator, verdict, already_pinned_as
  FROM `{DS}.in_dc_colo_resolved` ORDER BY verdict, facility_name"""):
    matched = next((a for a in ALIASES
                    if a[0].lower().replace(" ", "") in
                    (str(r.facility_name) + " " + str(r.operator)).lower().replace(" ", "")), None)
    tag = f"alias {matched[0]} -> {matched[1]}" if matched else "no alias needed"
    print(f"  {str(r.facility_name)[:38]:38s} {str(r.verdict):18s} {tag}")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_dc_operator_aliases'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
    f"VALUES (@t,@s,@m,@n,0.0,CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "in_dc_operator_aliases"),
        bigquery.ScalarQueryParameter("s", "STRING",
            "operator press releases and their own sites (databank.com, 365datacenters.com via "
            "Wayback, globenewswire, prnewswire) - the same evidence B4 used"),
        bigquery.ScalarQueryParameter("m", "STRING",
            "Curated rename/acquisition ledger, not a scrape. cloudscene's terms forbid automated "
            "access and it is recorded BLOCKED, so operator identity was established from the "
            "operators' own published statements."),
        bigquery.ScalarQueryParameter("n", "INT64", int(n)),
        bigquery.ScalarQueryParameter("no", "STRING",
            "Fixes the cross-check matcher, NOT the data-centre layer. B4 proved ZERO of 8 flagged "
            "facilities were missing buildings; 5 were pinned under a predecessor operator name and "
            "the stem-prefix matcher could not see it. "
            "USE ON OPERATOR NAME ONLY, NEVER TO MERGE FACILITIES: Lifeline ran several buildings, "
            "and CLOUDSCENE_GAP.md already matched 'Lifeline West Henry' to 'Lifeline Fort Wayne' - "
            "same operator, different cities, different buildings.")])).result()
print("\nregistered in_dc_operator_aliases")
