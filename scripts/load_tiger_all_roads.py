"""G122 unlock: clip TIGER/Line ALL ROADS for Indiana, all 92 counties.

⛔ WHY THIS EXISTS. `in_parcel_assembly` can only confirm a right-of-way parcel when a road we HOLD
actually crosses it, and we held only PRIMARY (225) and SECONDARY (861) features - the interstates
and the state highways. Local streets, county roads, alleys and service drives were absent
entirely, which is why 184 of 5,757 ribbon-shaped parcels could be confirmed by geometry and the
other 5,573 could only be graded "shape_only" or "possible". A ribbon along a residential street
is invisible to a corpus that contains no residential streets.

TIGER "All Roads" is the same publisher (Census Bureau), the same vintage convention and the same
geometry model as the primary/secondary layers already loaded - it is simply the complete set,
published one file per county.

⛔ WHAT THIS IS NOT. It is not a scrape. `https://www2.census.gov/geo/tiger/` is a public
bulk-file directory in the public domain: no account, no key, no CAPTCHA, no terms gate, no
user-agent condition. Each county is a static .zip fetched once by URL. If a fetch is refused the
county is recorded as BLOCKED with the wall quoted verbatim and the load continues - a blocked
county is an observation, never a silent gap.

⚠ FULL-COLUMN CAPTURE (G124). Every attribute column the publisher ships is kept. The `[:N]`
positional cut that silently dropped operator/owner/status from four gas tables is exactly the
defect this project already paid for once; a cut by POSITION keeps whatever the publisher happened
to put first, which is not a decision anybody made.

RE-SCRAPE COMMAND: python scripts/load_tiger_all_roads.py
  --year 2024   pin a vintage (default 2024)
  --refresh     re-download even if the .zip is already on disk
⚠ IDEMPOTENT: replace_safe. The table is CREATE OR REPLACE from whatever .zip files are on disk,
so re-running cannot double-count. Downloads are cached under data/tiger_roads/ and are ARCHIVED,
never deleted.
"""
import argparse
import io
import os
import sys
import time
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import geopandas as gpd
import requests
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_roads_all"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "tiger_roads")
BASE = "https://www2.census.gov/geo/tiger/TIGER{y}/ROADS/tl_{y}_{fips}_roads.zip"

# Indiana's 92 counties are FIPS 18001..18183, odd numbers only.
COUNTIES = [f"18{n:03d}" for n in range(1, 184, 2)]
assert len(COUNTIES) == 92, f"Indiana has 92 counties, built {len(COUNTIES)}"


def fetch(fips, year, refresh):
    """Return (path, status). status is 'cached' | 'downloaded' | a verbatim BLOCKED string."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"tl_{year}_{fips}_roads.zip")
    if os.path.exists(path) and os.path.getsize(path) > 0 and not refresh:
        return path, "cached"
    url = BASE.format(y=year, fips=fips)
    try:
        r = requests.get(url, timeout=120)
    except Exception as e:                                    # network, DNS, TLS
        return None, f"BLOCKED: {type(e).__name__}: {e}"
    if r.status_code != 200:
        return None, f"BLOCKED: HTTP {r.status_code} {r.reason} for {url}"
    with open(path, "wb") as fh:
        fh.write(r.content)
    return path, "downloaded"


def read_county(path):
    """Read one county .zip into a GeoDataFrame in EPSG:4326, keeping EVERY column."""
    gdf = gpd.read_file(f"zip://{path}")
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4269")                        # TIGER ships NAD83
    return gdf.to_crs("EPSG:4326")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", default="2024")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="first N counties, for a smoke test")
    a = ap.parse_args()

    counties = COUNTIES[: a.limit] if a.limit else COUNTIES
    print(f"TIGER {a.year} ALL ROADS - {len(counties)} Indiana counties")
    print(f"  cache {CACHE}")

    frames, blocked, t0 = [], [], time.time()
    for i, fips in enumerate(counties, 1):
        path, status = fetch(fips, a.year, a.refresh)
        if path is None:
            blocked.append((fips, status))
            print(f"  [{i:>2}/{len(counties)}] {fips}  {status}")
            continue
        gdf = read_county(path)
        gdf["county_fips"] = fips[2:]                         # 3-digit, the project's convention
        gdf["stcofips"] = fips                                # 5-digit, for FEMA-style joins
        frames.append(gdf)
        if i % 10 == 0 or i == len(counties):
            print(f"  [{i:>2}/{len(counties)}] {fips}  {status:10} "
                  f"running total {sum(len(f) for f in frames):,} features")

    if not frames:
        print("⛔ nothing loaded - refusing to replace the table with an empty one")
        return 1

    all_roads = gpd.pd.concat(frames, ignore_index=True)
    print(f"\n  {len(all_roads):,} road features across {len(frames)} counties "
          f"in {time.time() - t0:.0f}s")
    print(f"  columns kept ({len(all_roads.columns)}): {', '.join(all_roads.columns)}")

    # MTFCC is the Census feature class. Report it rather than filtering - a service drive and an
    # alley are still roads for the purpose of "is this polygon a right-of-way".
    if "MTFCC" in all_roads:
        print("\n  MTFCC mix:")
        for k, v in all_roads["MTFCC"].value_counts().head(12).items():
            print(f"    {k:8} {v:>9,}")

    df = gpd.pd.DataFrame(all_roads.drop(columns="geometry"))
    df.columns = [c.lower() for c in df.columns]
    df["geom"] = all_roads.geometry.to_wkt()
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
    SELECT {', '.join(f'`{c}`' for c in cols)},
           SAFE.ST_GEOGFROMTEXT(geom, make_valid => TRUE) AS geom
    FROM `{stage}`
    WHERE geom IS NOT NULL
    """).result()
    client.delete_table(stage, not_found_ok=True)

    s = list(client.query(f"""
      SELECT COUNT(*) n, COUNTIF(geom IS NULL) nogeom,
             COUNT(DISTINCT county_fips) cf, COUNT(DISTINCT fullname) names
      FROM `{OUT}`"""))[0]
    print(f"\n  {OUT}: {s.n:,} rows, {s.cf} counties, {s.names:,} distinct road names, "
          f"{s.nogeom:,} with no geometry")

    blocked_note = ("; ".join(f"{f}: {m}" for f, m in blocked) if blocked
                    else "none - all 92 counties returned HTTP 200")
    client.query(f"""
    INSERT INTO `{DS}._registry`
      (table_name, source, method, n_rows, gb_scanned, built_at, notes)
    VALUES (
      'in_roads_all',
      'US Census Bureau TIGER/Line {a.year} ALL ROADS, one shapefile per county: '
      'https://www2.census.gov/geo/tiger/TIGER{a.year}/ROADS/tl_{a.year}_18XXX_roads.zip',
      'Public-domain bulk file directory - no account, no key, no CAPTCHA, no terms gate. '
      'All 92 Indiana county .zips fetched by URL, read with geopandas, reprojected NAD83 '
      '(EPSG:4269) to EPSG:4326, concatenated, loaded via a staging table and converted with '
      'SAFE.ST_GEOGFROMTEXT(make_valid => TRUE). EVERY publisher column is kept - no positional '
      '[:N] cut - plus county_fips (3-digit) and stcofips (5-digit). Supersedes in_roads_primary '
      '(225) + in_roads_secondary (861) for coverage; those remain for the primary/secondary '
      'distinction. Blocked counties: {blocked_note}. '
      'RE-SCRAPE COMMAND: python scripts/load_tiger_all_roads.py --year {a.year}',
      {s.n}, 0.0, CURRENT_TIMESTAMP(),
      'G122. Downloads cached under data/tiger_roads/ and ARCHIVED, never deleted. '
      'IDEMPOTENCY: replace_safe - CREATE OR REPLACE from the cached .zip set, so re-running '
      'cannot double-count. CADENCE: annual, when Census publishes the next TIGER vintage.'
    )""").result()
    print("  _registry row written")

    client.query(f"""
    INSERT INTO `energy-platfrom.energy.registry_sources`
      (source_id, source_name, domain, category, geography_state, endpoint, endpoint_kind,
       access, status, acquisition_method, what_it_provides, object_names, measured_rows,
       fmt, origin, updated_by, notes, method)
    VALUES (
      'tiger_{a.year}_roads_in', 'TIGER/Line {a.year} All Roads (Indiana)', 'www2.census.gov',
      'basemap', 'IN',
      'https://www2.census.gov/geo/tiger/TIGER{a.year}/ROADS/tl_{a.year}_18XXX_roads.zip',
      'file_download', 'public', 'LOADED', 'bulk file download, 92 county shapefiles',
      'Every road centreline in Indiana - interstates through alleys and service drives - with '
      'MTFCC feature class and full name. Confirms whether a ribbon-shaped parcel is a road '
      'right-of-way rather than a long narrow lot.',
      ['indiana_app.in_roads_all'], {s.n}, 'shapefile', 'indiana_app_session',
      'indiana_app_session',
      'G122. Blocked counties: {blocked_note}',
      'RE-SCRAPE COMMAND: python scripts/load_tiger_all_roads.py --year {a.year}'
    )""").result()
    print("  energy.registry_sources appended (the one permitted write to energy)")

    if blocked:
        print(f"\n⚠ {len(blocked)} county/counties BLOCKED and recorded verbatim:")
        for f, m in blocked:
            print(f"    {f}  {m}")
    print("\nTIGER ALL ROADS LOADED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
