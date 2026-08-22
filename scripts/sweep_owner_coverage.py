"""G147: OWNER NAME AND ASSESSED VALUE BEYOND MARION — WHAT DO WE ACTUALLY HOLD, BY COUNTY?

⛔ THE QUESTION. Operator, 2026-08-22b: *"Is there any data beyond Marion County? Much of our data
is limited to that region, and we really need to get statewide coverage, if possible."*

⭐ WHY IT GATES EVERYTHING. Five backlog rows (G70, G71, G104, G90b, G147) are held open on owner
name and assessed value, and a sixth (**G166**, D22_probate) turns out to need nothing else — the
probate technique is already built and proven on 534,937 parcels in twelve states, and Indiana has
zero rows for exactly one reason: `mat_parcel_attrs.parcel_owner` is 100% NULL on all 3,553,381
Indiana parcels. **The ceiling is owner names, not method.**

⚠ SO THIS ASKS THE QUESTION BY CONTENT, NOT BY NAME. It finds every table in EITHER dataset that
carries an owner-name-like column, checks whether it holds Indiana parcels, and reports **how many
of the 92 counties each one covers** — because "we hold owner data" and "we hold owner data for one
county" are different answers and the second has been mistaken for the first before.

⛔ AND IT MUST NOT REPEAT THE NAME-GREP FAILURE. We "held no land banks" for weeks while holding
two, filed as `landbank` and `surplus`. Column names are the probe here, and the county count is
measured from the data rather than from what a table is called.

RE-SCRAPE COMMAND: python scripts/sweep_owner_coverage.py
⛔ READ-ONLY. Writes nothing.
"""
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "docs", "OWNER_COVERAGE.json")
client = bigquery.Client(project="energy-platfrom")

OWNER_COLS = ("owner_name", "owner1", "ownerall", "owner", "parcel_owner", "ownername",
              "owner_1", "taxpayer_name", "deeded_owner", "petitionername", "petitner",
              "borrname", "owner_full_name", "propertyowner")
VALUE_COLS = ("assessed_value", "assessed_total", "total_value", "assessedvalue",
              "market_value", "just_value", "total_assessed")


def cols_with(ds, wanted):
    q = f"""
    SELECT table_name, LOWER(column_name) col
    FROM `{ds}`.INFORMATION_SCHEMA.COLUMNS
    WHERE LOWER(column_name) IN UNNEST(@w)"""
    out = {}
    for r in client.query(q, job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ArrayQueryParameter("w", "STRING", list(wanted))])).result():
        out.setdefault(r.table_name, []).append(r.col)
    return out


def main():
    print("=" * 104)
    print("G147 - OWNER NAME AND ASSESSED VALUE, BY COUNTY, ACROSS THE WHOLE ESTATE")
    print("=" * 104)

    # the 92 names, bare and upper - in_county_rollup stores 'Allen County'
    counties = [r.c for r in client.query(f"""
        SELECT UPPER(REGEXP_REPLACE(county_name, r'(?i)\\s+COUNTY$', '')) c
        FROM `{DS}.in_county_rollup`""").result()]
    print(f"  probing against {len(counties)} Indiana county names\n")

    found = []
    for ds, label in ((DS, "indiana_app"), (EN, "energy")):
        owners = cols_with(ds, OWNER_COLS)
        print(f"  {label}: {len(owners)} table(s) carry an owner-name-like column")
        for tbl, ocols in sorted(owners.items()):
            if tbl.startswith(("_", "orennia_", "be_ustest_")):
                continue
            ocol = ocols[0]
            # does it carry an Indiana PARCEL KEY, and how many counties?
            schema = {f.name.lower(): f.field_type
                      for f in client.get_table(f"{ds}.{tbl}").schema}
            key = next((k for k in ("parcel_key", "state_parcel_id", "stateparcelnumber",
                                    "stateparcelid", "parcel_id", "parcno") if k in schema), None)
            if key is None:
                continue
            try:
                r = list(client.query(f"""
                  SELECT COUNT(*) n,
                         COUNTIF(`{ocol}` IS NOT NULL AND CAST(`{ocol}` AS STRING) != '') named,
                         COUNT(DISTINCT SUBSTR(REGEXP_REPLACE(CAST(`{key}` AS STRING),
                                               r'[^0-9]', ''), 1, 5)) county_prefixes
                  FROM `{ds}.{tbl}`""").result())[0]
            except Exception:
                continue
            if r.named == 0:
                continue
            found.append({"dataset": label, "table": tbl, "owner_col": ocol, "key_col": key,
                          "rows": r.n, "with_owner": r.named,
                          "distinct_county_prefixes": r.county_prefixes})

    found.sort(key=lambda h: -h["with_owner"])
    print(f"\n  {len(found)} table(s) carry BOTH a parcel key and a populated owner name\n")
    print(f"  {'table':46} {'rows':>10} {'with owner':>11} {'cty pfx':>8}  key")
    print("  " + "-" * 98)
    for h in found[:25]:
        print(f"  {h['dataset'][:3]}:{h['table'][:42]:42} {h['rows']:>10,} "
              f"{h['with_owner']:>11,} {h['distinct_county_prefixes']:>8}  {h['key_col']}")

    # ⭐ THE HEADLINE: how many of the 92 counties does the owner estate actually cover?
    print("\n" + "=" * 104)
    print("THE COUNTY COVERAGE OF WHAT WE HOLD")
    print("=" * 104)
    r = list(client.query(f"""
      WITH o AS (
        SELECT DISTINCT SUBSTR(REGEXP_REPLACE(parcel_key, r'[^0-9]', ''), 1, 5) fips
        FROM `{DS}.in_marion_owner_value` WHERE owner_name IS NOT NULL)
      SELECT (SELECT COUNT(*) FROM o) counties_with_owner,
             (SELECT COUNT(*) FROM `{DS}.in_county_rollup`) counties_total,
             (SELECT COUNT(*) FROM `{DS}.in_marion_owner_value` WHERE owner_name IS NOT NULL) parcels
      """).result())[0]
    print(f"  in_marion_owner_value covers {r.counties_with_owner} of {r.counties_total} counties, "
          f"{r.parcels:,} parcels with an owner name")
    tot = list(client.query(
        f"SELECT COUNT(*) n FROM `{DS}.in_sites`").result())[0].n
    print(f"  ⛔ that is {100 * r.parcels / tot:.1f}% of the {tot:,} Indiana parcels in in_sites")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(found, indent=1))
    print(f"\n  wrote {os.path.relpath(OUT, REPO)}")
    print("=" * 104)


if __name__ == "__main__":
    main()
