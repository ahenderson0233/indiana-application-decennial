"""G72 - LAND-STATUS AND AIRSPACE GATES: the four objects that answer "who else already owns a say
over this land", clipped, flagged onto parcels, and shipped as their own payload.

Operator, 2026-08-19: *"we should add datasets from BQ like military bases, tribal land, and
similar datasets that give us more contextual information about the land and environment (I know
that we don't currently use all of our BQ tables that we could - this is NOT limited to only the
environment section)."*

All four were already clipped into `indiana_app` and NONE of them reached a control. They were
named only inside a provenance dictionary in `app.js`, tagged "PAGE-NEXT" - which is why
`TABLE_PURPOSE_INDEX.md` files them READ-ONLY: a reader can see the name on the Data page and
cannot ask the map a single question with it.

================================================================================================
!! THE THING THAT WOULD HAVE SHIPPED WRONG, and it is the whole reason this file measures first
================================================================================================
`in_tribal_land` holds **14 rows and NOT ONE OF THEM IS IN INDIANA.** Measured before wiring:
Laguna Pueblo (New Mexico), L'Anse (Michigan), Kootenai (Idaho), Lake Traverse (South Dakota),
Lac Courte Oreilles, La Jolla, La Posta... every one false against `ST_INTERSECTS` with the
Indiana boundary. Its registry row explains it: `method = 'census-keyed clip (geoid:geoid)'`.
It was clipped by a KEY JOIN, not spatially, and the key it joined on selected an alphabetical
run around "K"/"L" out of the 858-row national parent.

Shipping a "Tribal land" checkbox on top of that table would have drawn New Mexico on an Indiana
map, or - worse, because it is silent - drawn nothing at all and read to the user as "no tribal
land here", which is a NEGATIVE FINDING WE NEVER MEASURED. That is the same defect shape as
treating an unpublished rate as zero (95 false "below floor" violations) and as printing "none"
where we never looked (G51).

The truth, measured against `energy.tribal_land` (858 rows) spatially:
    Indiana holds EXACTLY ONE tribal feature - **Pokagon Off-Reservation Trust Land**,
    178.1 acres inside the state line (the holding spans into Michigan; total aland 2,740 acres).
So this build RE-CLIPS the table properly and the layer is honest at one polygon.

================================================================================================
WHAT EACH GATE ACTUALLY CHANGES FOR A DEVELOPER  (G21 binds: no surface without this line)
================================================================================================
* MILITARY INSTALLATION (13, all verified inside Indiana). A large load or a tall structure near
  an installation draws a DoD Siting Clearinghouse review, and the review is on the DoD's clock,
  not the county's. This is the one gate on the list that can add a year without ever saying no.
* SPECIAL-USE AIRSPACE (19, all verified inside Indiana - MOAs and restricted areas around
  Jefferson Proving Ground and Atterbury). Governs what may be built TALL and what radar must
  keep seeing. Matters for cooling towers, stacks and met masts, not for the slab.
* TRIBAL TRUST LAND (1, re-clipped here). A DIFFERENT SOVEREIGN - not county zoning, not state
  permitting. A siter who treats it as ordinary land is negotiating with the wrong government.
* TALL OBSTRUCTIONS >=200 ft AGL (4,591 of 15,638 Indiana rows). 200 ft is the FAA Part 77 notice
  threshold, so this is the set that already had to tell the FAA it exists. What a siter reads off
  it: a cluster of >=200 ft structures is a place where tall things have ALREADY been permitted,
  which is a cheap prior on how an air-space review will go for a cooling tower or a stack.
  ! Do NOT read it as a transmission trace. Transmission-line towers are 4,067 of the 15,638-row
  corpus but only 44 survive the 200 ft cut - almost every T-L tower is shorter than the notice
  threshold. Use `in_transmission_union` for where the lines run; this layer is about HEIGHT.

================================================================================================
RULES OBEYED HERE
================================================================================================
* Reads `energy` only for the two re-clips and the state boundary. This is a BUILD script, which
  is the only kind permitted to (exports may not - the checkpoint enforces it).
* `state_boundaries` has **`geom`**, not `geog`. Guessed wrong once on 2026-08-19; read the schema.
* D85 (`parcels_in/080500000047000018`, the inverted whole-Earth polygon) is excluded BY KEY from
  the parcel join, or every parcel on Earth would flag against every gate.
* Every table written gets a `_registry` row in the same run carrying a verbatim RE-SCRAPE COMMAND.
* Unpublished is NULL, never 0. A parcel with no gate within 25 miles gets NULL, not 999.
* ASCII only in console output - cp1252 cannot encode the arrows and three scripts have died on
  their own print().

RE-RUN: python scripts/build_land_gates.py
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = (r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California"
        r"\ca-capacity-deploy\indiana-application-decennial")
DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
D85 = "080500000047000018"
MILES = 1609.344
NEAR_CAP_M = 40234          # 25 miles - the same cap nearestBus() and in_asset_distance_parcel use
AGL_NOTICE_FT = 200         # FAA Part 77 notice threshold

client = bigquery.Client(project="energy-platfrom")
IN_GEOM = f"(SELECT ANY_VALUE(geom) FROM `{EN}.state_boundaries` WHERE UPPER(stusps)='IN')"


def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    if isinstance(o, decimal.Decimal):
        return float(o)
    return str(o)


def rc(x):
    if isinstance(x, float):
        return round(x, 6)
    if isinstance(x, list):
        return [rc(v) for v in x]
    return x


def q(sql):
    return list(client.query(sql).result())


def one(sql):
    return q(sql)[0]


def reg(name, source, method, n, notes):
    """G16: a registry row must be enough for a STRANGER to re-run the work."""
    notes = notes.replace("'", "")
    client.query(f"""INSERT `{DS}._registry`
        (table_name, source, method, n_rows, gb_scanned, built_at, notes)
        VALUES ('{name}', '{source}', '{method}', {n}, 0.1, CURRENT_TIMESTAMP(),
                '{notes} | RE-SCRAPE COMMAND: python scripts/build_land_gates.py')""").result()


print("=" * 94)
print("G72 LAND-STATUS AND AIRSPACE GATES")
print("=" * 94)

# ---------------------------------------------------------------------------------------------
# 1. RE-CLIP in_tribal_land SPATIALLY. See the header - the existing table is 14 rows of
#    out-of-state land produced by a key join. Measured, not assumed, on every run.
# ---------------------------------------------------------------------------------------------
# ⛔ THIS BLOCK WAS NOT IDEMPOTENT AND THE SCRIPT COULD ONLY EVER RUN ONCE - fixed 2026-08-20d.
#    It measured `in_tribal_land.geom` and then CREATE OR REPLACE'd that same table with the
#    geometry column renamed to `geog`. First run: fine. Every run after: "Unrecognized name:
#    geom", and the whole land-gates build died at step 1. Caught when G122 forced a rebuild of
#    everything downstream of in_screener_candidates. This is trap 4 - an in-place repair that
#    reads its own output - and it meant the RE-SCRAPE COMMAND in this table's registry row was
#    not runnable, which is exactly what G124 exists to find.
_cols = {f.name for f in client.get_table(f"{DS}.in_tribal_land").schema}
_gcol = "geom" if "geom" in _cols else "geog"
before = one(f"""SELECT COUNT(*) n,
    COUNTIF(ST_INTERSECTS({_gcol}, {IN_GEOM})) hit FROM `{DS}.in_tribal_land`""")
print(f"\n[1] in_tribal_land BEFORE: {before.n} rows, {before.hit} of them actually inside "
      f"Indiana (geometry column '{_gcol}'"
      f"{'; the spatial repair has already been applied' if _gcol == 'geog' else ''})")

client.query(f"""CREATE OR REPLACE TABLE `{DS}.in_tribal_land` AS
SELECT namelsad, name, geoid, classfp, lsad, funcstat, aiannhce, aiannhns, comptyp,
       aland, awater,
       ROUND(ST_AREA(ST_INTERSECTION(geom, {IN_GEOM})) / 4046.8564224, 1) AS acres_in_indiana,
       ROUND(ST_AREA(geom) / 4046.8564224, 1) AS acres_total,
       ST_INTERSECTION(geom, {IN_GEOM}) AS geog
FROM `{EN}.tribal_land`
WHERE ST_INTERSECTS(geom, {IN_GEOM})""").result()
tr = one(f"""SELECT COUNT(*) n, STRING_AGG(namelsad, '; ') names,
    ROUND(SUM(acres_in_indiana), 1) ac FROM `{DS}.in_tribal_land`""")
print(f"    AFTER  (spatial clip): {tr.n} rows -- {tr.names} -- {tr.ac} acres inside Indiana")
reg("in_tribal_land", "energy.tribal_land",
    "SPATIAL clip ST_INTERSECTION to Indiana (REPLACES a census-keyed geoid join)", tr.n,
    f"REPAIRED 2026-08-19: the previous build used method=census-keyed clip (geoid:geoid) and "
    f"returned 14 rows of which ZERO intersect Indiana (Laguna Pueblo NM, LAnse MI, Kootenai ID, "
    f"Lake Traverse SD ...). Indiana holds exactly {tr.n}: {tr.names}, {tr.ac} acres in-state. "
    f"Tribal trust land is a SEPARATE SOVEREIGN - not county zoning, not state permitting")

# ---------------------------------------------------------------------------------------------
# 2. ONE NORMALISED GATE TABLE. Three sources, three different geometry columns - read, not
#    guessed: military carries `_g` (GEOGRAPHY), tribal now carries `geog`, and SUA carries ONLY
#    `geometry_geojson` (STRING) with no GEOGRAPHY column at all.
# ---------------------------------------------------------------------------------------------
client.query(f"""CREATE OR REPLACE TABLE `{DS}.in_land_gates` AS
SELECT 'military' AS kind,
       sitename AS name,
       CONCAT(COALESCE(sitereportingcomponent, 'unknown component'),
              ' / status ', COALESCE(siteoperationalstatus, 'unstated')) AS detail,
       CASE WHEN LOWER(COALESCE(isjointbase, '')) IN ('yes', 'true', 'y')
            THEN 'joint base' ELSE NULL END AS note,
       _g AS geog
FROM `{DS}.in_land_military_bases`
WHERE _g IS NOT NULL AND ST_INTERSECTS(_g, {IN_GEOM})
UNION ALL
SELECT 'tribal', namelsad,
       CONCAT(FORMAT('%.0f', acres_in_indiana), ' acres inside Indiana',
              CASE WHEN acres_total > acres_in_indiana + 1
                   THEN FORMAT(' of %.0f total (crosses the state line)', acres_total)
                   ELSE '' END),
       'federal trust land - a separate sovereign', geog
FROM `{DS}.in_tribal_land` WHERE geog IS NOT NULL
UNION ALL
SELECT 'sua', name,
       CONCAT(COALESCE(type_code, '?'), ' airspace, ',
              COALESCE(lower_val, '?'), '-', COALESCE(upper_val, '?'), ' ',
              COALESCE(upper_uom, 'FT')),
       NULLIF(TRIM(COALESCE(comm_name, cont_agent, '')), ''),
       SAFE.ST_GEOGFROMGEOJSON(geometry_geojson, make_valid => TRUE)
FROM `{DS}.in_land_faa_sua`
WHERE SAFE.ST_GEOGFROMGEOJSON(geometry_geojson, make_valid => TRUE) IS NOT NULL""").result()
g = one(f"""SELECT COUNT(*) n, COUNTIF(kind='military') m, COUNTIF(kind='tribal') t,
    COUNTIF(kind='sua') s FROM `{DS}.in_land_gates`""")
print(f"\n[2] in_land_gates: {g.n} polygons -- {g.m} military, {g.t} tribal, {g.s} special-use airspace")
reg("in_land_gates", "indiana_app.in_land_military_bases + in_tribal_land + in_land_faa_sua",
    "UNION ALL of three gate sources normalised to (kind, name, detail, note, geog)", g.n,
    f"G72. One layer per kind on the map console. {g.m} military installations (DoD Siting "
    f"Clearinghouse review runs on the DoDs clock, not the countys), {g.t} tribal trust "
    f"(different sovereign), {g.s} special-use airspace (governs what may be built TALL)")

# ---------------------------------------------------------------------------------------------
# 3. TALL OBSTRUCTIONS. `agl`/`amsl` are zero-padded STRINGS and `type`/`city` carry trailing
#    spaces - both read from the schema, both handled. 200 ft AGL is the FAA Part 77 threshold,
#    so this is exactly the set that already had to notify the FAA that it exists.
# ---------------------------------------------------------------------------------------------
client.query(f"""CREATE OR REPLACE TABLE `{DS}.in_faa_obstacles_tall` AS
SELECT TRIM(type) AS obstacle_type,
       SAFE_CAST(agl AS INT64) AS agl_ft,
       SAFE_CAST(amsl AS INT64) AS amsl_ft,
       SAFE_CAST(quantity AS INT64) AS quantity,
       TRIM(COALESCE(city, '')) AS city,
       CASE lighting WHEN 'U' THEN 'unknown' WHEN 'N' THEN 'none' WHEN 'R' THEN 'red'
                     WHEN 'D' THEN 'medium-intensity white (day)' WHEN 'H' THEN 'high-intensity white'
                     WHEN 'M' THEN 'medium-intensity white' WHEN 'S' THEN 'synchronised red'
                     WHEN 'F' THEN 'flood' WHEN 'C' THEN 'dual red / white' ELSE lighting END AS lighting,
       CASE verified_status WHEN 'O' THEN 'verified' WHEN 'U' THEN 'unverified' ELSE verified_status END AS verified,
       SAFE_CAST(latdec AS FLOAT64) AS lat,
       SAFE_CAST(londec AS FLOAT64) AS lon,
       ST_GEOGPOINT(SAFE_CAST(londec AS FLOAT64), SAFE_CAST(latdec AS FLOAT64)) AS geog
FROM `{DS}.in_faa_obstacles`
WHERE TRIM(state) = 'IN'
  AND SAFE_CAST(agl AS INT64) >= {AGL_NOTICE_FT}
  AND SAFE_CAST(latdec AS FLOAT64) IS NOT NULL
  AND SAFE_CAST(londec AS FLOAT64) IS NOT NULL""").result()
ob = one(f"""SELECT COUNT(*) n, MAX(agl_ft) tallest,
    COUNTIF(obstacle_type LIKE 'T-L%') tl FROM `{DS}.in_faa_obstacles_tall`""")
print(f"[3] in_faa_obstacles_tall: {ob.n} at >={AGL_NOTICE_FT} ft AGL, tallest {ob.tallest} ft, "
      f"{ob.tl} of them transmission-line towers")
reg("in_faa_obstacles_tall", "indiana_app.in_faa_obstacles",
    f"state=IN AND agl>={AGL_NOTICE_FT} ft; agl/amsl cast from zero-padded STRING; type/city TRIMmed; "
    f"lighting and verified_status decoded from their single-letter vocabularies", ob.n,
    f"G72. {AGL_NOTICE_FT} ft AGL is the FAA Part 77 NOTICE threshold, so every row here already "
    f"had to tell the FAA it exists. Reads two ways for a siter: clutter to clear for a tall "
    f"structure, and - since {ob.tl} are transmission-line towers - a visible trace of where "
    f"heavy transmission actually runs. Tallest in Indiana is {ob.tallest} ft AGL")

# ---------------------------------------------------------------------------------------------
# 4. PARCEL FLAGS, so the SCREENER can filter on all of this and not just the map.
#    Measured against the parcel FOOTPRINT (`in_sites.parcel_geog`), never a centroid.
#    D85 excluded by key. NULL past 25 miles - absent is not zero.
# ---------------------------------------------------------------------------------------------
client.query(f"""CREATE OR REPLACE TABLE `{DS}.in_land_gate_parcel` AS
WITH cand AS (
  SELECT c.parcel_source, c.parcel_key, s.parcel_geog
  FROM `{DS}.in_screener_candidates` c
  JOIN `{DS}.in_sites` s USING (parcel_source, parcel_key)
  WHERE s.parcel_geog IS NOT NULL AND c.parcel_key != '{D85}'
),
mil AS (SELECT * FROM `{DS}.in_land_gates` WHERE kind = 'military'),
near_mil AS (
  SELECT c.parcel_source, c.parcel_key,
         ARRAY_AGG(STRUCT(m.name AS nm, ST_DISTANCE(c.parcel_geog, m.geog) AS d)
                   ORDER BY ST_DISTANCE(c.parcel_geog, m.geog) LIMIT 1)[OFFSET(0)] AS best
  FROM cand c JOIN mil m ON ST_DWITHIN(c.parcel_geog, m.geog, {NEAR_CAP_M})
  GROUP BY 1, 2
),
on_sua AS (
  SELECT c.parcel_source, c.parcel_key,
         STRING_AGG(DISTINCT g.name, '; ' ORDER BY g.name) AS sua_name
  FROM cand c JOIN `{DS}.in_land_gates` g
    ON g.kind = 'sua' AND ST_INTERSECTS(c.parcel_geog, g.geog)
  GROUP BY 1, 2
),
on_tribal AS (
  SELECT c.parcel_source, c.parcel_key,
         STRING_AGG(DISTINCT g.name, '; ' ORDER BY g.name) AS tribal_name
  FROM cand c JOIN `{DS}.in_land_gates` g
    ON g.kind = 'tribal' AND ST_INTERSECTS(c.parcel_geog, g.geog)
  GROUP BY 1, 2
)
SELECT c.parcel_source, c.parcel_key,
       ROUND(nm.best.d / {MILES}, 3) AS mil_mi,
       nm.best.nm AS mil_name,
       su.sua_name,
       tb.tribal_name
FROM cand c
LEFT JOIN near_mil   nm USING (parcel_source, parcel_key)
LEFT JOIN on_sua     su USING (parcel_source, parcel_key)
LEFT JOIN on_tribal  tb USING (parcel_source, parcel_key)""").result()
p = one(f"""SELECT COUNT(*) n, COUNTIF(mil_mi IS NOT NULL) m, COUNTIF(mil_mi <= 3) m3,
    COUNTIF(sua_name IS NOT NULL) s, COUNTIF(tribal_name IS NOT NULL) t
    FROM `{DS}.in_land_gate_parcel`""")
fan = one(f"""SELECT ROUND(COUNT(*) / COUNT(DISTINCT CONCAT(parcel_source, '/', parcel_key)), 4) f
    FROM `{DS}.in_land_gate_parcel`""")
print(f"[4] in_land_gate_parcel: {p.n:,} parcels -- {p.m:,} within 25 mi of an installation "
      f"({p.m3:,} within 3 mi), {p.s:,} under special-use airspace, {p.t:,} on tribal trust land")
print(f"    D85 fan-out check: {fan.f} (must be ~1.0, never ~2.0)")
if fan.f > 1.001:
    raise SystemExit(f"FAN-OUT {fan.f} -- the D85 guard did not hold. Do not ship this.")
reg("in_land_gate_parcel", "indiana_app.in_screener_candidates x in_sites x in_land_gates",
    f"parcel FOOTPRINT (parcel_geog) vs gate polygons; nearest military within {NEAR_CAP_M} m "
    f"(25 mi) else NULL; SUA and tribal are ST_INTERSECTS; D85 excluded by key; fan-out {fan.f}",
    p.n,
    f"G72 screener half. {p.m3} parcels sit within 3 miles of a military installation, which is "
    f"the band where a DoD Siting Clearinghouse review is likely. NULL means measured and nothing "
    f"within 25 miles - it does not mean zero")

# ---------------------------------------------------------------------------------------------
# 5. THE PAYLOAD. Its own small file rather than another 8.7 MB onto overlays.geojson.gz, and
#    fetched at boot because 33 polygons and 4.6k points are cheap.
#    G43: clipped at the border already by construction; the payload clipper also carries it.
# ---------------------------------------------------------------------------------------------
feats = []
for r in q(f"""SELECT kind, name, detail, note, ST_ASGEOJSON(geog) gj
               FROM `{DS}.in_land_gates` WHERE geog IS NOT NULL"""):
    d = dict(r)
    gj = d.pop("gj")
    d["layer"] = d.pop("kind")
    feats.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
n_poly = len(feats)
for r in q(f"""SELECT obstacle_type, agl_ft, amsl_ft, city, lighting, verified, lat, lon
               FROM `{DS}.in_faa_obstacles_tall` ORDER BY agl_ft DESC"""):
    d = dict(r)
    lat, lon = d.pop("lat"), d.pop("lon")
    d["layer"] = "obstacle"
    feats.append({"type": "Feature", "properties": d,
                  "geometry": {"type": "Point", "coordinates": [rc(lon), rc(lat)]}})
out = os.path.join(REPO, "data", "gates.geojson.gz")
with gzip.open(out, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump({"type": "FeatureCollection", "features": feats}, f,
              separators=(",", ":"), default=jd)
size = os.path.getsize(out) / 1024
print(f"\n[5] data/gates.geojson.gz: {len(feats):,} features "
      f"({n_poly} polygons + {len(feats) - n_poly:,} points), {size:.0f} KB")
print("\nDONE. Now: python scripts/stamp_assets.py && python scripts/audit_frontend.py")
