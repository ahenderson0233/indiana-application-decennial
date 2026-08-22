"""G161(b): THE OTHER 71% — INDIANA CONTENT IN TABLES THAT CARRY NO STATE COLUMN.

⛔ WHY THIS EXISTS. `sweep_energy_indiana_si.py` probed every `energy` table with a state-like
column: **697 of 2,412**. Operator, 2026-08-22: *"not all of these datasets include county, state,
or address, so you may need to widen or narrow your scope based on this, especially if we haven't
scraped all column values for that table/view yet."* That is the G25 content rule applied one level
deeper than the first sweep applied it — **1,715 tables were invisible to it.**

⭐ WHAT THIS DOES. For every state-less table it picks the cheapest Indiana-identifying column it
actually carries and probes with that column's OWN vocabulary:

  county FIPS  -> a 5-character code beginning '18'   (18001 Adams ... 18183 Whitley)
  county name  -> the 92 Indiana county names, exact
  ZIP          -> 46000-47999, Indiana's whole range
  lat + lon    -> the Indiana bounding box, 37.77/41.76 N by -88.10/-84.78 W
  address text -> ', IN ' with a delimiter, or the word INDIANA

⚠ THE TRAP THIS PROBE IS BUILT TO AVOID, MEASURED 2026-08-22. `parcels_nm_l00.taxdistrictstate`
holds values like `'12 In'`, `'12 IN LR'` and `'12 In T'`. A `LIKE '%IN%'` predicate matches
hundreds of NEW MEXICO rows. **Every state test here is an EXACT match or a delimited one**, never
a bare substring.

⛔ AND THE THIRD CATEGORY, WHICH IS THE OPERATOR'S REAL POINT. A table with NO Indiana-identifying
column at all is **not** a table without Indiana content — it is a table we cannot ASK. Those are
counted and reported separately as `unaskable`, because recording them as "no Indiana" would be the
absence-of-evidence defect this project has already paid for.

RE-SCRAPE COMMAND: python scripts/sweep_energy_indiana_wide.py
⛔ READ-ONLY. Writes nothing to BigQuery.
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

EN = "energy-platfrom.energy"
DS = "energy-platfrom.indiana_app"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "docs", "ENERGY_INDIANA_SWEEP_WIDE.json")
client = bigquery.Client(project="energy-platfrom")

STATE_COLS = ("state", "state_abbr", "state_code", "st", "statename", "state_name",
              "property_state", "projectstate", "borrstate", "debtor_state",
              "filer_state", "situs_state", "owner_state", "mailing_state")

FIPS_COLS = ("countyfips", "county_fips", "fips", "geoid", "county_geoid", "cntyfips", "stcofips")
CTY_COLS = ("county", "county_name", "countyname", "cty", "county_nm", "situscounty")
ZIP_COLS = ("zip", "zipcode", "zip_code", "postal", "postalcode", "postal_code",
            "situszipcode", "site_zip", "mail_zip", "zip5")
LAT_COLS = ("latitude", "lat", "y", "ylat", "lat_dd")
LON_COLS = ("longitude", "lon", "lng", "x", "xlon", "lon_dd")
ADDR_COLS = ("address", "full_address", "site_address", "situsaddressall", "addressfull",
             "address_line_1", "street_address", "location_address", "property_address",
             "mailaddressall", "addr", "address1")

# Indiana bounding box, generous by ~0.02 deg so a border parcel is not missed.
LAT_LO, LAT_HI, LON_LO, LON_HI = 37.75, 41.79, -88.12, -84.76


def indiana_counties():
    # ⚠ in_sites carries no county NAME column - guessed once, corrected by reading the schema.
    # in_county_rollup.county_name is the 92-county set, verified 92 distinct.
    q = f"SELECT DISTINCT UPPER(county_name) c FROM `{DS}.in_county_rollup` WHERE county_name IS NOT NULL"
    out = sorted({r.c for r in client.query(q).result() if r.c})
    if len(out) < 80:
        raise SystemExit(f"in_county_rollup returned {len(out)} county names, expected 92")
    return out


def columns_by_table():
    q = f"""
    SELECT table_name, LOWER(column_name) col, data_type
    FROM `{EN}`.INFORMATION_SCHEMA.COLUMNS
    """
    out = {}
    for r in client.query(q).result():
        out.setdefault(r.table_name, {})[r.col] = r.data_type
    return out


def already_clipped():
    got = set()
    for r in client.query(f"SELECT source FROM `{DS}._registry` WHERE source IS NOT NULL").result():
        for tok in (r.source or "").replace(",", " ").replace("`", " ").split():
            if "energy." in tok:
                got.add(tok.split("energy.")[-1].strip(" .;)"))
    return got


def pick(cols):
    """The cheapest Indiana-identifying probe this table can actually support."""
    txt = ("STRING",)
    for c in FIPS_COLS:
        if c in cols:
            return ("fips", c, None)
    for c in CTY_COLS:
        if c in cols and cols[c] in txt:
            return ("county", c, None)
    for c in ZIP_COLS:
        if c in cols:
            return ("zip", c, None)
    la = next((c for c in LAT_COLS if c in cols), None)
    lo = next((c for c in LON_COLS if c in cols), None)
    if la and lo and cols[la] in ("FLOAT64", "NUMERIC", "INT64", "BIGNUMERIC"):
        return ("bbox", la, lo)
    for c in ADDR_COLS:
        if c in cols and cols[c] in txt:
            return ("addr", c, None)
    return (None, None, None)


def expr(kind, a, b, counties_param):
    if kind == "fips":
        return (f"COUNTIF(LENGTH(TRIM(CAST(`{a}` AS STRING))) IN (5, 11) "
                f"AND STARTS_WITH(TRIM(CAST(`{a}` AS STRING)), '18'))")
    if kind == "county":
        return f"COUNTIF(UPPER(TRIM(`{a}`)) IN UNNEST({counties_param}))"
    if kind == "zip":
        return (f"COUNTIF(SAFE_CAST(SUBSTR(REGEXP_REPLACE(CAST(`{a}` AS STRING), r'[^0-9]', ''), 1, 5) "
                f"AS INT64) BETWEEN 46000 AND 47999)")
    if kind == "bbox":
        return (f"COUNTIF(SAFE_CAST(`{a}` AS FLOAT64) BETWEEN {LAT_LO} AND {LAT_HI} "
                f"AND SAFE_CAST(`{b}` AS FLOAT64) BETWEEN {LON_LO} AND {LON_HI})")
    if kind == "addr":
        return (f"COUNTIF(REGEXP_CONTAINS(UPPER(`{a}`), r'(,\\s*IN\\b)|(\\bINDIANA\\b)'))")
    return "0"


def main():
    counties = indiana_counties()
    allcols = columns_by_table()
    clipped = already_clipped()
    stateful = {t for t, c in allcols.items() if any(s in c for s in STATE_COLS)}
    targets = {t: c for t, c in allcols.items() if t not in stateful}

    print("=" * 104)
    print("G161(b) - INDIANA CONTENT IN THE TABLES WITH NO STATE COLUMN")
    print("=" * 104)
    print(f"  {len(allcols):,} energy tables · {len(stateful):,} carry a state column "
          f"(swept already) · {len(targets):,} did not")
    print(f"  probing against {len(counties)} Indiana county names\n")

    plan, unaskable = [], []
    for t, cols in sorted(targets.items()):
        kind, a, b = pick(cols)
        (plan if kind else unaskable).append((t, kind, a, b) if kind else t)

    from collections import Counter
    print("  probe chosen:", dict(Counter(k for _, k, _, _ in plan)))
    print(f"  ⛔ {len(unaskable):,} table(s) carry NO Indiana-identifying column - "
          f"these are UNASKABLE, not empty\n")

    hits, failed = [], []
    B = 25
    for i in range(0, len(plan), B):
        batch = plan[i:i + B]
        sel = " UNION ALL ".join(
            f"SELECT '{t}' t, '{k}' k, COUNT(*) n_all, {expr(k, a, b, '@cty')} n_in "
            f"FROM `{EN}.{t}`" for t, k, a, b in batch)
        try:
            for r in client.query(sel, job_config=bigquery.QueryJobConfig(
                    query_parameters=[bigquery.ArrayQueryParameter("cty", "STRING", counties)])).result():
                if r.n_in and r.n_in > 0:
                    hits.append({"table": r.t, "probe": r.k, "indiana_rows": r.n_in,
                                 "total_rows": r.n_all, "clipped": r.t in clipped})
        except Exception as e:
            failed.extend(t for t, _, _, _ in batch)
            print(f"  [batch {i // B}] {str(e)[:100]}")
        print(f"  probed {min(i + B, len(plan)):>5} of {len(plan)}  ...  {len(hits)} hits", end="\r")

    print(" " * 90, end="\r")
    hits.sort(key=lambda h: -h["indiana_rows"])
    new = [h for h in hits if not h["clipped"] and not h["table"].startswith(("_", "in_", "orennia_"))]
    print(f"\n  {len(hits)} table(s) hold Indiana rows · {len(new)} NOT already clipped\n")
    print(f"  {'table':56} {'IN rows':>12} {'of total':>13}  probe")
    print("  " + "-" * 100)
    for h in new[:70]:
        print(f"  {h['table'][:56]:56} {h['indiana_rows']:>12,} {h['total_rows']:>13,}  {h['probe']}")
    if len(new) > 70:
        print(f"  ... and {len(new) - 70} more, in {os.path.relpath(OUT, REPO)}")
    if failed:
        print(f"\n  ⚠ {len(failed)} unprobeable (type/permission): {', '.join(failed[:5])}")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps({
        "energy_tables": len(allcols), "with_state_col": len(stateful),
        "probed_here": len(plan), "unaskable": sorted(unaskable),
        "with_indiana": len(hits), "unclipped": len(new), "unprobeable": failed, "hits": hits,
    }, indent=1))
    print(f"\n  wrote {os.path.relpath(OUT, REPO)}")
    print("=" * 104)


if __name__ == "__main__":
    main()
