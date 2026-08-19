"""G15 - LOCATE THE FUTURE-CAPACITY PROJECTS, and G62's ceiling measured from a second direction.

Operator: G15 has read "6 utilities held, but location/cost/in-service extracted at 0%. Re-extract,
then locate in two tiers: exact join for existing assets, uncertainty rings for vaguely-described
new ones." Operator, 2026-08-19: *"we should expand upon what we have for future capacity, leaning
into kV, in service, cost ... the utilities often provide location estimates or regions where a
project will take place"* (G87, merged here).

================================================================================================
⭐ THE ROW SAYS "RE-EXTRACT". IT DOES NOT NEED RE-EXTRACTING. IT NEEDS MAPPING.
================================================================================================
Measured before writing a line of this file. `in_grid_plans` holds 618 rows with county on 0 and
cost on 0 - and the row reads as though the text was never captured and 227 IURC PDFs must be
parsed to get it back. That is not what happened. THE TEXT IS ALREADY IN THE TABLE:

    project_name = '1 | TS000091 | Burns Ditch 13810-37 | Breaker | 138kV | 22.4 | 87% | 19.40 | '

The whole pipe-delimited source row was written into `project_name`, and the columns beside it -
`location_text`, `substation_names`, `county` - were left NULL. So this is a PROPAGATION LOSS
INSIDE OUR OWN PIPELINE, exactly the shape G14 turned out to have, and no scrape is required.
323 of 391 text rows carry the 8-pipe shape; 321 match `<seq> | <ID> | <asset> | <type> | <kV>`.

================================================================================================
WHAT THIS SCRIPT CAN AND CANNOT RECOVER - measured, not hoped
================================================================================================
CAN:  the project id, the ASSET NAME, the asset type, and the voltage - all four are discrete
      fields in the row we already hold.
CAN:  a COUNTY, wherever the asset's station name resolves against `in_substations`.
CANNOT: a COST. Fields 6-8 are `22.4 | 87% | 19.40`. One of them is plausibly $M and another is
      plausibly a benefit ratio, and the workpaper's own column headers did not survive into this
      table. ⛔ Guessing which is which would put a dollar figure on a page from a coin flip, so
      `cost_usd_m` STAYS NULL and this file says why. Recovering it means going back to the
      workpaper header row, which IS the re-extraction G15 describes - for cost only, not for
      location.

================================================================================================
⭐ G62'S CEILING, REPRODUCED FROM A COMPLETELY DIFFERENT DIRECTION
================================================================================================
G62 concluded, from PJM bus placement, that "the ceiling is the gazetteer, not the matcher". This
script hits the same wall from IURC project text. The stations it cannot resolve are not obscure:

    CHICAGO AVE · SOUTH VALPARAISO · MICHIGAN CITY · MILLER · ROCK RUN · STILLWELL ·
    EAST WINAMAC · BURNS DITCH · TRAIL CREEK · MARKTOWN · KOSCIUSKO

Every one is a real northwest-Indiana NIPSCO station. ⛔ AND THE GAZETTEER CANNOT BE EXTENDED FROM
WHAT WE HOLD: `in_substations` (3,858) is already the complete Indiana cut of
`energy.mat_grid_substations`, and neither parent source carries them either - checked directly,
`osm_power_substations` has 2,873 Indiana rows and `nat_substations_hifld` 2,077, and NEITHER
contains a single one of the twelve names by exact match. So this is one shared blocker behind two
backlog items, and it is an ACQUISITION, not a matcher bug.

What the matcher CAN still win is suffix handling - HIFLD carries "SCHAHFER STATION" where the
workpaper says "SCHAHFER" - so the match ladder below tries exact, then suffix-stripped, then
prefix, and RECORDS WHICH ONE FIRED so a weak match is visible as one.

RULES: reads indiana_app only (this is a build, but it needs nothing from `energy`). Registry row
written in the same run. D85 is not reachable here - no parcel join. ASCII console output.

RE-RUN: python scripts/build_grid_plans_located.py
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import re, collections
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

# Words that end a station name and begin an asset description. Ordered longest-first so that
# SUBSTATION is consumed before SUB and BUS TIE before BUS.
ASSET_WORDS = (r"SUBSTATION|SWITCHGEAR|TRANSFORMER|BUS\s*TIE|RECLOSER|CAPACITOR|REGULATOR|"
               r"BREAKER|CIRCUIT|RELAY|XFMR|SWGR|LINE|BKR|XFR|CAP|REG|SUB|BUS|TIE")
# Suffixes the gazetteer adds and the workpapers omit (measured: HIFLD holds "SCHAHFER STATION").
GAZ_SUFFIX = re.compile(r"\s+(STATION|SUBSTATION|SUB|TAP|SWITCHYARD|PLANT)$")

ROW_RE = re.compile(r"^\s*\S+\s*\|\s*([A-Z]{2}\d{6})\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|")


def station_of(asset_name):
    """The substation a piece of equipment sits in, from the equipment's own name."""
    s = (asset_name or "").replace("‐", "-").strip()
    s = re.split(r"\s*#", s)[0]                              # '... #2 XFR' -> '...'
    s = re.sub(rf"(?i)\b(?:{ASSET_WORDS})\b.*$", "", s)      # stop at the asset word
    s = re.sub(r"(?i)\b\d+\s*/?\s*\d*\s*k?v\b.*$", "", s)    # stop at 138kV or 345/138kV
    s = re.sub(r"\s*\d[\d\-]*\s*$", "", s)                   # trailing circuit numbers
    return re.sub(r"[\s,\-]+$", "", s).strip().upper()


def kv_of(text):
    m = re.search(r"(\d{1,3})\s*k?v", (text or ""), re.I)
    return float(m.group(1)) if m else None


print("=" * 94)
print("G15  LOCATE THE FUTURE-CAPACITY PROJECTS")
print("=" * 94)

src = [dict(r) for r in client.query(f"""
  SELECT utility, document_name, document_url, filed_date, project_name, project_type,
         voltage_kv, in_service_year, raw_row, source, extraction_status
  FROM `{DS}.in_grid_plans`""")]
print(f"\nin_grid_plans: {len(src)} rows")

gaz = collections.defaultdict(list)
for r in client.query(f"""SELECT substation_name, county, county_fips, max_kv, lat, lon
                          FROM `{DS}.in_substations` WHERE substation_name IS NOT NULL"""):
    gaz[r["substation_name"].upper().strip()].append(dict(r))
gaz_stripped = collections.defaultdict(list)
for k, v in gaz.items():
    gaz_stripped[GAZ_SUFFIX.sub("", k).strip()].extend(v)
print(f"gazetteer: {len(gaz)} distinct station names over "
      f"{sum(len(v) for v in gaz.values())} substations")


def match(station):
    """Exact, then suffix-stripped, then prefix. Returns (hit, how) - `how` is never dropped."""
    if not station:
        return None, "no station name in the source text"
    if station in gaz:
        return gaz[station][0], "exact"
    bare = GAZ_SUFFIX.sub("", station).strip()
    if bare in gaz_stripped:
        return gaz_stripped[bare][0], "suffix-insensitive"
    cands = [k for k in gaz if k.startswith(station + " ") or station.startswith(k + " ")]
    # ⚠ ONE candidate only. Two stations sharing a prefix are two different places, and picking
    # the first would be the CLOUDSCENE_GAP mistake -- eight fabricated matches from a name join.
    if len(cands) == 1:
        return gaz[cands[0]][0], "prefix (unambiguous)"
    if len(cands) > 1:
        return None, f"ambiguous: {len(cands)} stations share this name"
    return None, "not in the gazetteer"


out, how_counts = [], collections.Counter()
for r in src:
    text = (r["project_name"] or r["raw_row"] or "")
    m = ROW_RE.match(text.replace("‐", "-"))
    proj_id = asset = atype = None
    kv = r["voltage_kv"]
    if m:
        proj_id, asset, atype = m.group(1), m.group(2), m.group(3)
        kv = kv or kv_of(m.group(4))
    st = station_of(asset) if asset else None
    hit, how = match(st) if asset else (None, "row is not the parsable workpaper shape")
    how_counts[how] += 1
    out.append({
        "utility": r["utility"], "document_name": r["document_name"],
        "document_url": r["document_url"], "filed_date": r["filed_date"],
        "project_id": proj_id,
        # ⚠ the ASSET NAME, not the whole pipe row -- that mis-mapping is the defect being fixed
        "asset_name": asset, "asset_type": atype, "station_name": st,
        "voltage_kv": kv, "in_service_year": r["in_service_year"],
        "cost_usd_m": None,                       # see the header: NOT guessed from an unlabelled column
        "county": hit["county"] if hit else None,
        "county_fips": hit["county_fips"] if hit else None,
        "lat": hit["lat"] if hit else None, "lon": hit["lon"] if hit else None,
        "matched_substation": hit["substation_name"] if hit else None,
        "location_method": how,
        "location_status": "located" if hit else "not located",
        "source": r["source"], "raw_row": text[:900],
    })

located = sum(1 for o in out if o["location_status"] == "located")
with_kv = sum(1 for o in out if o["voltage_kv"] is not None)
with_asset = sum(1 for o in out if o["asset_name"])
print(f"\nparsed an asset name on {with_asset} of {len(out)}")
print(f"voltage now on {with_kv} of {len(out)}  (was 326)")
print(f"LOCATED to a county: {located} of {len(out)}  ({100*located/len(out):.0f}%)")
print("\nhow each row resolved:")
for k, n in how_counts.most_common():
    print(f"   {n:>4}  {k}")

miss = collections.Counter(o["station_name"] for o in out
                           if o["station_name"] and o["location_status"] != "located")
print("\nSTATIONS THE GAZETTEER DOES NOT HOLD (the G62 ceiling), by row count:")
for s, n in miss.most_common(14):
    print(f"   {n:>3}  {s}")

schema = [
    bigquery.SchemaField("utility", "STRING"), bigquery.SchemaField("document_name", "STRING"),
    bigquery.SchemaField("document_url", "STRING"), bigquery.SchemaField("filed_date", "STRING"),
    bigquery.SchemaField("project_id", "STRING"), bigquery.SchemaField("asset_name", "STRING"),
    bigquery.SchemaField("asset_type", "STRING"), bigquery.SchemaField("station_name", "STRING"),
    bigquery.SchemaField("voltage_kv", "FLOAT"), bigquery.SchemaField("in_service_year", "INTEGER"),
    bigquery.SchemaField("cost_usd_m", "FLOAT"), bigquery.SchemaField("county", "STRING"),
    bigquery.SchemaField("county_fips", "STRING"), bigquery.SchemaField("lat", "FLOAT"),
    bigquery.SchemaField("lon", "FLOAT"), bigquery.SchemaField("matched_substation", "STRING"),
    bigquery.SchemaField("location_method", "STRING"), bigquery.SchemaField("location_status", "STRING"),
    bigquery.SchemaField("source", "STRING"), bigquery.SchemaField("raw_row", "STRING"),
]
for o in out:
    fd = o["filed_date"]
    o["filed_date"] = None if fd is None else str(fd)
    y = o["in_service_year"]
    o["in_service_year"] = int(y) if y is not None else None

tbl = f"{DS}.in_grid_plans_located"
client.load_table_from_json(
    out, tbl,
    job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE")).result()
print(f"\nwrote {tbl}: {len(out)} rows")

note = (f"G15. Splits the pipe-delimited workpaper row that was written whole into project_name "
        f"into its real fields, then locates each asset by matching its station to in_substations "
        f"(exact, then suffix-insensitive, then UNAMBIGUOUS prefix; location_method records which). "
        f"Located {located} of {len(out)}. cost_usd_m is deliberately NULL - the workpaper columns "
        f"6-8 are unlabelled in this table and guessing which is dollars would print a coin flip. "
        f"CEILING IS THE GAZETTEER, not the matcher: in_substations is already the complete Indiana "
        f"cut of energy.mat_grid_substations, and neither osm_power_substations (2,873 IN) nor "
        f"nat_substations_hifld (2,077 IN) holds the missing NIPSCO stations. Same blocker as G62.")
client.query(f"""INSERT `{DS}._registry`
  (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES ('in_grid_plans_located', 'indiana_app.in_grid_plans x in_substations',
          'pipe-row split + station->gazetteer match ladder', {len(out)}, 0.1, CURRENT_TIMESTAMP(),
          '{note.replace("'", "")} | RE-SCRAPE COMMAND: python scripts/build_grid_plans_located.py')
""").result()
print("registered.")
