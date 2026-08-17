# Water geometry — Indiana surface water that can actually be drawn and measured to

All figures below are from live `COUNT(*)` queries run 2026-08-17 after the by-key backfill
completed. Nothing here is estimated.

## Why these tables exist

`energy.nhd_flowline` (39,542,980 rows) and `energy.nhd_waterbody` (10,431,981 rows) carry a
`SHAPE:GEOGRAPHY` column that is **NULL on every row nationally**. They are attribute-only: no river
or lake in the estate could be drawn or measured to. `energy` is read-only, so the fix was a fresh
acquisition into `indiana_app` from the same publisher.

| table | rows | distinct `permanent_identifier` | null `geog` | distinct `huc8` |
|---|---:|---:|---:|---:|
| `indiana_app.in_nhd_flowline_geom` | 163,976 | 163,976 | 0 | 73 |
| `indiana_app.in_nhd_waterbody_geom` | 7,430 | 7,430 | 0 | 64 |

Zero duplicates in either table (checked on `permanent_identifier` with braces and case normalised —
`{ABC}` and `abc` are the same feature and a raw `DISTINCT` would not catch that pair).

**Source.** USGS The National Map, ArcGIS REST, public/anonymous — no key, no terms dialogue, no
CAPTCHA: `hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer` layer **6** (Flowline - Large
Scale) and layer **12** (Waterbody - Large Scale).

## The cut, stated rather than hidden

- **Flowlines:** `ftype = 460` (StreamRiver) **with a non-null `gnis_name`** — named watercourses
  only. Indiana holds 972,487 ftype-460 flowlines; 152,165 are named. The unnamed ones are headwater
  trickles, and NHD's own act of naming is the publisher's judgement of "real watercourse".
- **Waterbodies:** `ftype 436` Reservoir (all sizes), `390` LakePond ≥ 0.1 km², `466` SwampMarsh
  ≥ 0.1 km². The 10 ha floor is a **judgement, not a fact**: smaller lakes are excluded as too small
  to cool anything.

### `water_role` — a swamp is never a water source

`ftype` is decoded, never screened raw:

| ftype | label | `water_role` | rows | Indiana |
|---|---|---|---:|---:|
| 460 | StreamRiver | `source` | 163,976 | 152,165 |
| 436 | Reservoir | `source` | 4,963 | 3,659 |
| 390 | LakePond | `source` | 1,767 | 1,595 |
| 466 | SwampMarsh | **`constraint`** | 700 | 661 |

466 is wetland — a thing that stops you building, not a thing you can cool with. It is carried
rather than dropped so the constraint stays visible, but the downstream distance table filters on
`water_role = 'source'`, and mislabelling it would tell a developer there is water to draw where
there is in fact a wetland to permit around. The commonly quoted "2,301 Indiana lakes over 10 ha" is
all three ftypes summed and silently includes the 661 marshes.

## Completeness

Measured at key level against the estate's own authority — every `permanent_identifier` that
`energy.nhd_*` says is Indiana and in the stated cut must now have geometry:

| table | Indiana cut complete | was, before this pass |
|---|---|---|
| `in_nhd_flowline_geom` | **152,165 / 152,165 = 100.00%** | 148,317 / 152,165 = 97.47% |
| `in_nhd_waterbody_geom` | **5,915 / 5,915 = 100.00%** | 4,900 / 5,915 = 82.84% |

The earlier figures were the bounding-box sweep alone. The by-key pass requested the 3,848 flowline
and 1,015 waterbody keys the built tables still lacked, in batches of 40, bisecting the batch
whenever the service answered HTTP 500 to an over-long `IN (...)` clause.

**The publisher returned geometry for every single key requested — 3,848 of 3,848 and 1,015 of
1,015. There is no HUC8, and no key, that USGS returned nothing for.**

Validity is four measurements, not one function call, because **BigQuery has no `ST_ISVALID`** (that
is PostGIS) — a GEOGRAPHY is valid by construction and anything unparseable comes back NULL. On all
rows of both tables: 0 NULL `geog`, 0 `ST_ISEMPTY`, 0 zero-length/zero-area, and max extent well
under the 1e12 inverted-polygon guard (largest is Lake Michigan at 5.89e10 m², legitimately a member
— Indiana owns its southern shore).

## ⚠ HUC8 coverage, and why "N of 76" is the wrong denominator

`in_huc8_boundaries` holds 76 subbasin polygons and is widely read as "Indiana's subbasins". **It is
not.** Two independent tests agree exactly on the real figure:

- 39 of the 76 intersect the union of Indiana county polygons the estate holds (87 of 92);
- 39 of the 76 list `IN` in the publisher's own `states` field.

The other **37 never touch Indiana** — Michigan, Wisconsin, Ohio and Kentucky basins, 22 of them
more than 100 km away and the furthest 462 km (Manistique River, Michigan Upper Peninsula; also
Door-Kewaunee WI, Escanaba MI, Carp-Pine MI, Licking KY, Blanchard OH).

| | of all 76 rows | **of the 39 that actually touch Indiana** |
|---|---|---|
| `in_nhd_flowline_geom` | 62 | **39 of 39** |
| `in_nhd_waterbody_geom` | 54 | **39 of 39** |

**Both tables cover every Indiana subbasin.** Reporting "62 of 76" would understate the flowline
table as ~82% complete when its Indiana coverage is total, and would send the next session off to
acquire tens of thousands of Michigan and Wisconsin streams that have no bearing on Indiana siting.

The boundaries table is also wrong in the other direction: 11 HUC8 codes that appear on real Indiana
NHD features (e.g. `05140103`, `05140204`, `05110001`) have no polygon in it at all.

## ⚠ `src_state` is not a reliable state test — root cause of the above

After the by-key pass completed the cut, 932 flowlines and 90 waterbodies have geometry **outside** a
generous Indiana box (-89..-84, 37..42.5). Every one of them is a row that `energy.nhd_flowline` /
`nhd_waterbody` itself tags `src_state = 'IN'`:

- **785 flowlines** sit just into western Ohio, in `05080001` Upper Great Miami and `04100007`
  Auglaize — both genuinely Indiana/Ohio shared subbasins, so these are defensible.
- **147 flowlines** are in Michigan and Wisconsin, as far north as 46.1°N in the Upper Peninsula —
  roughly 480 km from Indiana and in no sense Indiana water.

This is the same defect that contaminated `in_huc8_boundaries`: a subbasin list derived from
`SELECT DISTINCT SUBSTR(reachcode,1,8) ... WHERE src_state='IN'` (the origin of the frequently
quoted "Indiana has 77 HUC8 subbasins") inherits `src_state`'s error, and the polygons for those
bogus HUC8s were then fetched.

**These rows are kept, not deleted** — they are real NHD features that the estate's own authority
claims, and deleting them would hide the defect rather than record it. Consequences:

- **Nearest-water distance is unaffected.** Nothing 480 km away is ever the nearest anything to an
  Indiana parcel.
- **Any count of rows here as "Indiana rivers" will overcount.** Use a geometric filter, or
  `in_nhd_indiana_slice` understood for what it actually means: "`energy.nhd_*` tags this
  `src_state='IN'`" — which is true of all 932.

The build now asserts the invariant that survived contact with the data — no geometry outside the
Indiana neighbourhood that the Indiana slice did *not* claim (measured: 0) — rather than the old
hard `off_map == 0`, which held only while the table was a bbox sweep that could not physically
contain such a feature.

## Membership, and why it is not decided by the bounding box

A watershed does not respect a state line. The tiled bbox is a *fetch mechanism*; Indiana membership
is decided by an explicit `permanent_identifier` key match against the `src_state='IN'` slice, with
braces and case normalised on both sides. Border features are **retained** and flagged
`in_nhd_indiana_slice = FALSE` rather than dropped — a parcel in Posey County cares about the Wabash
whichever bank it is on. 11,811 flowlines and 1,515 waterbodies are such adjacent-state features.

`huc8` is `SUBSTR(reachcode,1,8)` kept as **STRING**. Every Indiana HUC8 begins `04` or `05`, and an
INT64 round-trip destroys the leading zero — measured, not theoretical: autodetect once typed
`reachcode` as INTEGER and turned `04040001000928` into `4040001000928`. 0 rows in either table have
a `huc8` of the wrong length.

## Re-scrape

```bash
# full rebuild
python scripts/pull_nhd_geometry.py && python scripts/build_nhd_geometry.py

# close a gap in an existing table WITHOUT rebuilding it (never CREATE OR REPLACE — that would
# discard verified rows). Resumable: an interrupted run keeps what it already wrote to disk.
python scripts/pull_nhd_geometry.py --append-missing && python scripts/build_nhd_geometry.py --append
```

The by-key pass costs roughly one second per key against a public federal service we do not own, so
a few thousand keys runs for an hour. That is deliberate politeness, not slowness to be optimised
away.

## Registered in

- `indiana_app._registry` — `in_nhd_flowline_geom` (163,976), `in_nhd_waterbody_geom` (7,430)
- `energy.registry_sources` — appended, the one permitted write to the read-only `energy` dataset.
  It is append-only, so the superseded rows recording 160,128 and 6,415 could not be corrected in
  place and remain. **Read the highest `measured_rows` for an endpoint as current**; the newer rows
  carry a note naming the row they supersede.
