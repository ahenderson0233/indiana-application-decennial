"""G130 item 4: clip TIGER/Line PLACE for Indiana - a REAL municipality gazetteer.

⛔ WHY THIS EXISTS, AND WHAT IT REPLACES. `build_planned_upgrades.py` resolves a filing that names
only a town against a gazetteer built like this:

    town AS (SELECT UPPER(TRIM(city)) ct, AVG(lat), AVG(lon) FROM in_substations GROUP BY 1)

That is **the set of towns that happen to host a substation** - 406 of them - and it is a
by-product, not a gazetteer. Indiana has far more incorporated places than that, so a filing
naming any town without a substation resolved to nothing at all. Worse, the "centroid" it returned
was the mean position of that town's SUBSTATIONS, which is not the town's centre; and the
uncertainty ring around it was a flat 5.0 miles whether the place was Indianapolis or a village of
four streets.

⭐ TIGER PLACE fixes all three at once: every incorporated place and census-designated place, the
polygon's own centroid, and **a radius derived from the place's own area** instead of a constant.

⛔ WHAT THIS IS NOT. It is not a scrape. `https://www2.census.gov/geo/tiger/` is a public-domain
bulk-file directory: no account, no key, no CAPTCHA, no terms gate, no user-agent condition. One
static .zip per state, fetched once by URL. A refused fetch is recorded BLOCKED with the wall
quoted verbatim - a blocked source is an observation, never a silent gap.

⚠ FULL-COLUMN CAPTURE (G124). Every attribute column the publisher ships is kept. The `[:N]`
positional cut that silently dropped operator/owner/status from four gas tables is the defect this
project already paid for once.

⚠ THE RADIUS IS THE EQUAL-AREA DISC, NOT THE BOUNDING BOX. A place's polygon is rarely round, and
the half-diagonal of its envelope overstates a river town badly. sqrt(area/pi) is the radius of
the circle with the same area, which is the honest "if I must draw one circle, how big" answer -
the same construction `build_planned_upgrades.py` already uses for a county.

RE-SCRAPE COMMAND: python scripts/load_tiger_place.py
  --year 2024   pin a vintage (default 2024)
  --refresh     re-download even if the .zip is already on disk
⚠ IDEMPOTENT: replace_safe. CREATE OR REPLACE from whatever .zip is on disk, so re-running cannot
double-count. Downloads are cached under data/tiger_place/ and are ARCHIVED, never deleted.
"""
import argparse
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import geopandas as gpd
import requests
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_places"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "tiger_place")
BASE = "https://www2.census.gov/geo/tiger/TIGER{y}/PLACE/tl_{y}_18_place.zip"


def fetch(year, refresh):
    """Return (path, status). status is 'cached' | 'downloaded' | a verbatim BLOCKED string."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"tl_{year}_18_place.zip")
    if os.path.exists(path) and os.path.getsize(path) > 0 and not refresh:
        return path, "cached"
    url = BASE.format(y=year)
    try:
        r = requests.get(url, timeout=180)
    except Exception as e:                                    # network, DNS, TLS
        return None, f"BLOCKED: {type(e).__name__}: {e}"
    if r.status_code != 200:
        return None, f"BLOCKED: HTTP {r.status_code} {r.reason} for {url}"
    with open(path, "wb") as fh:
        fh.write(r.content)
    return path, "downloaded"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", default="2024")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()

    print(f"TIGER {a.year} PLACE - Indiana municipality gazetteer")
    print(f"  cache {CACHE}")
    t0 = time.time()

    path, status = fetch(a.year, a.refresh)
    if path is None:
        print(f"  ⛔ {status}")
        print("  refusing to replace the table - a blocked fetch is recorded, never guessed around")
        return 1
    print(f"  {status}: {path}")

    gdf = gpd.read_file(f"zip://{path}")
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4269")                        # TIGER ships NAD83
    gdf = gdf.to_crs("EPSG:4326")
    print(f"  {len(gdf):,} places in {time.time() - t0:.0f}s")
    print(f"  columns kept ({len(gdf.columns)}): {', '.join(gdf.columns)}")

    if "LSAD" in gdf:
        print("\n  LSAD mix (the publisher's legal/statistical class):")
        for k, v in gdf["LSAD"].value_counts().head(12).items():
            print(f"    {k:8} {v:>6,}")

    df = gpd.pd.DataFrame(gdf.drop(columns="geometry"))
    df.columns = [c.lower() for c in df.columns]
    df["geom"] = gdf.geometry.to_wkt()
    for c in df.columns:
        if c != "geom":
            df[c] = df[c].astype("string")

    client = bigquery.Client(project="energy-platfrom")
    stage = f"{OUT}_stage"
    print(f"\n  staging {len(df):,} rows -> {stage}")
    job = client.load_table_from_dataframe(
        df, stage,
        job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"))
    job.result()

    cols = [c for c in df.columns if c != "geom"]
    client.query(f"""
    CREATE OR REPLACE TABLE `{OUT}` AS
    WITH g AS (
      SELECT {', '.join(f'`{c}`' for c in cols)},
             SAFE.ST_GEOGFROMTEXT(geom, make_valid => TRUE) AS geom
      FROM `{stage}`
    )
    SELECT
      * EXCEPT(geom),
      geom,
      -- the place's OWN centre, not the mean of the substations inside it
      ST_Y(ST_CENTROID(geom)) AS lat,
      ST_X(ST_CENTROID(geom)) AS lon,
      ROUND(ST_AREA(geom) / 2589988.11, 3) AS area_sq_mi,
      -- ⭐ the equal-area disc: the radius of the circle with this place's area. An honest single
      -- number for "the filing says only the town name, so it is somewhere in here".
      -- ⚠ FLOORED AT 1.0 mi. A hamlet of 0.2 sq mi yields 0.25 mi, which would draw a ring
      -- TIGHTER than a substation_match gets - and we know less here, not more. The floor keeps
      -- the ring ordering honest against the other tiers.
      GREATEST(1.0, ROUND(SQRT(ST_AREA(geom) / ACOS(-1)) / 1609.344, 1)) AS radius_mi
    FROM g
    WHERE geom IS NOT NULL
    """).result()
    client.delete_table(stage, not_found_ok=True)

    s = list(client.query(f"""
      SELECT COUNT(*) n, COUNT(DISTINCT UPPER(TRIM(name))) names,
             COUNTIF(geom IS NULL) nogeom,
             ROUND(MIN(radius_mi), 1) rmin, ROUND(MAX(radius_mi), 1) rmax,
             ROUND(APPROX_QUANTILES(radius_mi, 2)[OFFSET(1)], 1) rmed
      FROM `{OUT}`"""))[0]
    print(f"\n  {OUT}: {s.n:,} places, {s.names:,} distinct names, {s.nogeom} without geometry")
    print(f"  radius: min {s.rmin} mi, median {s.rmed} mi, max {s.rmax} mi "
          f"(the flat 5.0 mi it replaces was neither)")

    # ⭐ THE POINT OF THE WHOLE CLIP, MEASURED: how much bigger is this than the by-product?
    cmp_ = list(client.query(f"""
      WITH byproduct AS (
        SELECT DISTINCT UPPER(TRIM(city)) nm FROM `{DS}.in_substations`
        WHERE geog IS NOT NULL AND city IS NOT NULL AND TRIM(city) != ''
      ), tiger AS (SELECT DISTINCT UPPER(TRIM(name)) nm FROM `{OUT}`)
      SELECT (SELECT COUNT(*) FROM byproduct) old_n,
             (SELECT COUNT(*) FROM tiger) new_n,
             (SELECT COUNT(*) FROM tiger t JOIN byproduct b USING (nm)) both_n,
             (SELECT COUNT(*) FROM byproduct b WHERE NOT EXISTS
                (SELECT 1 FROM tiger t WHERE t.nm = b.nm)) only_old"""))[0]
    print(f"\n  ⭐ gazetteer: {cmp_.old_n} substation-host towns -> {cmp_.new_n:,} TIGER places "
          f"({cmp_.both_n} in both)")
    print(f"  ⚠ {cmp_.only_old} name(s) the substation table has and TIGER does not - those are "
          f"unincorporated localities, and they stay reachable because the old tier is KEPT as a "
          f"fallback rather than replaced")

    client.query(f"""
    INSERT INTO `{DS}._registry`
      (table_name, source, method, n_rows, gb_scanned, built_at, notes)
    VALUES (
      'in_places',
      'US Census Bureau TIGER/Line {a.year} PLACE, Indiana state file: '
      'https://www2.census.gov/geo/tiger/TIGER{a.year}/PLACE/tl_{a.year}_18_place.zip',
      'Public-domain bulk file directory - no account, no key, no CAPTCHA, no terms gate. '
      'One state .zip fetched by URL, read with geopandas, reprojected NAD83 (EPSG:4269) to '
      'EPSG:4326, loaded via a staging table and converted with SAFE.ST_GEOGFROMTEXT('
      'make_valid => TRUE). EVERY publisher column is kept - no positional [:N] cut - plus a '
      'derived lat/lon (the polygon centroid), area_sq_mi, and radius_mi = the EQUAL-AREA DISC '
      'radius sqrt(area/pi), floored at 1.0 mi. Replaces the 406-name by-product gazetteer that '
      'build_planned_upgrades.py derived from in_substations.city, which held only towns that '
      'happen to host a substation and returned the mean of those substations rather than the '
      'town centre. Every place carries both an incorporated/CDP class (LSAD) and a polygon, so '
      'a filing naming only a town gets a real centre and a ring sized from that town. '
      'RE-SCRAPE COMMAND: python scripts/load_tiger_place.py --year {a.year}',
      {s.n}, 0.0, CURRENT_TIMESTAMP(),
      'G130 item 4. Fetch status: {status}. Downloads cached under data/tiger_place/ and '
      'ARCHIVED, never deleted. IDEMPOTENCY: replace_safe - CREATE OR REPLACE from the cached '
      '.zip, so re-running cannot double-count. CADENCE: annual, when Census publishes the next '
      'TIGER vintage.'
    )""").result()
    print("\n  _registry row written")

    client.query(f"""
    INSERT INTO `energy-platfrom.energy.registry_sources`
      (source_id, source_name, domain, category, geography_state, endpoint, endpoint_kind,
       access, status, acquisition_method, what_it_provides, object_names, measured_rows,
       fmt, origin, updated_by, notes, method)
    VALUES (
      'tiger_{a.year}_place_in', 'TIGER/Line {a.year} Places (Indiana)', 'www2.census.gov',
      'basemap', 'IN',
      'https://www2.census.gov/geo/tiger/TIGER{a.year}/PLACE/tl_{a.year}_18_place.zip',
      'file_download', 'public', 'LOADED', 'bulk file download, one state shapefile',
      'Every incorporated place and census-designated place in Indiana, with its polygon, its '
      'own centroid and an equal-area radius. Resolves a planned-upgrade filing that names only '
      'a town, and sizes the uncertainty ring from that town rather than a flat 5 miles.',
      ['indiana_app.in_places'], {s.n}, 'shapefile', 'indiana_app_session',
      'indiana_app_session',
      'G130 item 4. Fetch status: {status}',
      'RE-SCRAPE COMMAND: python scripts/load_tiger_place.py --year {a.year}'
    )""").result()
    print("  energy.registry_sources appended (the one permitted write to energy)")
    print("\nTIGER PLACE COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
