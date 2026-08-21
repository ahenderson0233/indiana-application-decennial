"""Export the screener payload from in_screener_candidates.

THE CAP IS THE HONEST PART OF THIS FILE. There are 532,868 candidate parcels and 334 MB of parcel
geometry. A browser cannot rank half a million rows from a static host, so this ships a SUBSET --
and a subset that does not announce itself is a lie by omission, because a screener that silently
shows the top 300 looks exactly like a screener that searched everything.

So the payload carries, per county, BOTH numbers: how many we shipped and how many qualify. The UI
is required to print "showing 300 of 12,431 in Marion County". That is the same discipline as
cannot-assess rendering as itself rather than as zero.

WHAT IS SHIPPED, and why in this order:
  1. EVERY parcel carrying an owner-motivation signal (24,275). These are the scarce asset -- the
     whole point of the application -- and they are never capped away.
  2. Then the top N per county by datacentre capacity, to fill the county out.
A parcel qualifying under both is shipped once.

READS indiana_app ONLY.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
TOP_PER_COUNTY = 300
client = bigquery.Client(project="energy-platfrom")


def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    if isinstance(o, decimal.Decimal):
        return float(o)
    return str(o)


# ---- the denominator, per county: how many actually qualify ----
denom = {}
for r in client.query(f"""
  SELECT county_fips, ANY_VALUE(county_name) AS county_name,
         COUNT(*) AS qualifying,
         COUNTIF(has_signal) AS with_signal,
         COUNTIF(wd_mw IS NOT NULL) AS with_load_bus,
         ROUND(MAX(mw_dc)) AS best_mw
  FROM `{DS}.in_screener_candidates`
  WHERE county_fips IS NOT NULL
  GROUP BY county_fips"""):
    denom[r.county_fips] = {"name": r.county_name, "qualifying": r.qualifying,
                            "with_signal": r.with_signal, "with_load_bus": r.with_load_bus,
                            "best_mw": r.best_mw}

# ---- the shipped rows ----
rows = []
for r in client.query(f"""
  WITH ranked AS (
    SELECT c.*, g.mil_mi, g.mil_name, g.sua_name, g.tribal_name,
           ROUND(h.deliverable_wd_mw)  AS deliv_wd_mw,
           ROUND(h.deliverable_inj_mw) AS deliv_inj_mw,
           h.deliverable_basis         AS deliv_basis,
           h.ends_resolved             AS deliv_ends,
           h.wd_limiting_end           AS deliv_limiting_end,
           h.wd_binding_at_limit       AS deliv_wd_binding,
           h.a_bus_name                AS deliv_a_bus,
           ROUND(h.a_wd_mw)            AS deliv_a_wd,
           h.b_bus_name                AS deliv_b_bus,
           ROUND(h.b_wd_mw)            AS deliv_b_wd,
           -- G120(b)+(e), 2026-08-20. Two attribution facts the operator hit on real sites.
           a.rowlike_confidence, a.compactness, a.road_crosses,
           a.nearest_structured_key, a.nearest_structured_m, a.nearest_structured_occ_group,
           a.neighbours, a.sliver_neighbours, a.sliver_acres,
           a.same_class_neighbours, a.same_class_acres, a.assembly_acres_same_class,
           a.largest_neighbour_acres,
           -- G72: water stress at PARCEL grain. in_water_parcel held 532,868 rows and reached
           -- no surface at all.
           w.stress_label, w.depletion_label, w.groundwater_decline_label, w.basins_touched,
           ROW_NUMBER() OVER (PARTITION BY c.county_fips ORDER BY c.mw_dc DESC) AS rk
    FROM `{DS}.in_screener_candidates` c
    LEFT JOIN `{DS}.in_parcel_assembly` a USING (parcel_source, parcel_key)
    LEFT JOIN `{DS}.in_water_parcel`    w USING (parcel_source, parcel_key)
    -- G72 land-status and airspace gates. LEFT JOIN, because a parcel with no installation
    -- within 25 miles must come back NULL ("measured, nothing in range"), never 0 -- the same
    -- rule that stopped 95 false "below floor" tariff violations.
    LEFT JOIN `{DS}.in_land_gate_parcel` g USING (parcel_source, parcel_key)
    -- G116/G118: the DELIVERABLE figure. The nearest line followed to the bus at BOTH ends with
    -- the lower headroom taken, per the operator's stated method. Sits BESIDE mw_dc (the land
    -- figure), never replacing it -- a site is capped by the lower of the two, and which one
    -- binds is the point. ⚠ Do not hand-type the split here - it moved twice already (190,216 /
    -- 73,094 was quoted after the numbers had gone to 190,178 / 73,058). audit_handoff_docs.py
    -- re-measures it; this comment names the finding, not the figure.
    LEFT JOIN `{DS}.in_parcel_line_headroom` h USING (parcel_source, parcel_key)
    WHERE c.county_fips IS NOT NULL
  )
  SELECT parcel_source, parcel_key, county_fips, county_name, occ_group, site_kind,
         -- ⭐ G70: BUILDING USE. `occ_cls` is the USA Structures occupancy class and it is far
         --    finer than occ_group's five buckets: Residential / Commercial / Industrial /
         --    Agriculture / Government / Education / Assembly / Utility and Misc / Unclassified.
         --    It was in in_screener_candidates and simply never selected, so the screener showed
         --    "ci" where it could have said "Industrial".
         -- ⚠ NULL on 1,269,061 parcels - the ones with no building at all - which is a THIRD
         --    STATE, not a missing value: no structure means no occupancy class to publish.
         occ_cls,
         structure_count, parcel_acres, exact_parcel_acres, outdoor_acres, exact_outdoor_acres,
         mw_dc, mw_bess, lat, lon,

         -- ⭐ G125: WHERE AM I? Operator: "EITHER coordinates OR addresses ... so they can
         --    self-verify the results."
         -- ⛔ THE ROW'S OWN PREMISE WAS WRONG TWICE AND BOTH CORRECTIONS SHIP HERE.
         --    (1) "Address is Marion-only and must say so." It is not. That claim rests on
         --        in_si_address_parcel_bridge (51,309 Marion rows), which is the ADDRESS SEARCH
         --        crosswalk. energy.parcels_in is a different source - the DLGF's own property
         --        address - and it is populated on 3,578,398 of 3,637,663 Indiana parcels
         --        (98.4%) across all 92 counties. Measured on candidates: 527,038 of 531,325.
         --    (2) "The parcel payload ships lat/lon on every row." It does not - `lat` is
         --        populated on 2,284,133 of 3,553,194 in_sites rows, so only 40.3% of candidates
         --        carry a PUBLISHED point. Every one of them has a polygon, so a display point
         --        is derived from it and LABELLED by coord_basis.
         -- ⚠ map_lat/map_lon are for the reader's eye and the imagery deep link. They are NOT in
         --    any distance calculation - every distance on this payload was measured to a
         --    geography, and "no centroid where a footprint exists" is untouched.
         -- ⚠ Full precision is kept (G30b). The page displays 5 decimals and copies all of it.
         prop_address, prop_city, prop_zip, map_lat, map_lon, coord_basis,

         -- ⭐ G53: the CANCELLED interconnection request, which the operator asked to be
         -- "filterable by date of withdrawn application" and which the screener has never
         -- carried. A withdrawn request is consent already given and then given up: somebody
         -- studied this land, signed for it, and walked away - so the site is buildable and the
         -- owner has already shown they will deal.
         -- ⚠ wd_max_mw is the SIZE half of that row: a cancelled 5 MW solar project does not
         -- imply land for a 300 MW campus, and without it the signal flatters small sites.
         wd_requests, wd_last_date, wd_max_mw,

         -- ⭐ G130: the nearest FUTURE planned upgrade, so the screener can answer "is anything
         -- coming near this site". ⛔ in_service work is excluded upstream - it is already built.
         -- ⚠ pu_unc_mi ships WITH pu_mi and neither is meaningful alone: "2.3 mi from a planned
         -- rebuild" reads as precision, and if that project is placed only to a town centroid its
         -- own ring is 5 miles. The page must show both or it is overstating what we know.
         pu_name, pu_src, pu_status, pu_isd, pu_cost_m, pu_mi, pu_unc_mi, pu_loc_method,
         has_signal, signals, signal_types, signal_events,
         CAST(first_event AS STRING) AS first_event, CAST(last_event AS STRING) AS last_event,
         events_3y, events_5y, events_10y, keying,
         sfha_flood, wetland_on_parcel, protected_land, bonus_kinds,
         inj_bus, inj_kv, inj_mw, inj_binding, inj_mi,
         wd_bus, wd_kv, wd_mw, wd_binding, wd_conf, wd_mi, wd_iso, inj_iso, inj_conf,
         -- ⚠ INVERTED ON PURPOSE. The payload drops False to stay lean, so a boolean
         -- `in_state` would silently drop exactly the case worth reporting. Emitting the
         -- EXCEPTION as a truthy flag means the notable rows survive and the ordinary ones
         -- cost nothing. 3,993 parcels currently match a bus outside Indiana.
         IF(wd_bus_in_state = FALSE, TRUE, NULL) AS wd_bus_out_of_state,
         IF(inj_bus_in_state = FALSE, TRUE, NULL) AS inj_bus_out_of_state,
         sub_name, sub_kv, sub_mi,
         -- transmission line, 2026-08-19. A line is the one asset that can run THROUGH a
         -- parcel rather than near it: 41,986 do. line_on_parcel is a stronger fact than a
         -- small line_mi and must not be flattened into it.
         line_mi, line_on_parcel, line_kv, line_volt_class,
         -- G72 gates: who ELSE holds a say over this land. mil_mi is NULL past 25 miles.
         mil_mi, mil_name, sua_name, tribal_name,
         -- G116/G118 deliverable capacity. ⛔ `deliverable_basis` MUST ship with the figures:
         -- a NULL under 'both_ends' would be a measured absence, a NULL under 'cannot_assess'
         -- means we could not follow the line to its buses. Opposite claims, same empty cell.
         deliv_wd_mw, deliv_inj_mw, deliv_basis, deliv_ends, deliv_limiting_end,
         deliv_wd_binding, deliv_a_bus, deliv_a_wd, deliv_b_bus, deliv_b_wd,

         -- ⭐ G120(b) 2026-08-20 - THE GEOCODE TRAP, MADE VISIBLE.
         -- G120(a) proved structure_count is faithful and the corpus is six years old, which
         -- explains a NEW building reading as empty. It does NOT explain a 1990s retail store
         -- reading as empty, and this does: the address geocoded onto the ROAD, the road is its
         -- own right-of-way parcel, and that parcel genuinely has no building. The tool was
         -- answering correctly about the wrong parcel and the reader had no way to tell.
         -- ⚠ 'no' is dropped from the payload (falsy-ish strings are kept, so it is emitted as a
         -- string only when it is one of the three positive grades) - absence means "not ribbon".
         IF(rowlike_confidence = 'no', NULL, rowlike_confidence) AS rowlike,
         IF(rowlike_confidence = 'no', NULL, ROUND(compactness, 3)) AS rowlike_compactness,
         -- ⚠ this was computed in the CTE and never SELECTed, so the strongest half of the
         --   "high" grade — that a road we hold physically crosses the polygon — never reached
         --   the page and the sentence that reports it was dead code. Caught by rendering a
         --   'high' row and noticing the clause was missing from the output.
         IF(rowlike_confidence = 'no', NULL, road_crosses) AS road_crosses,
         -- the redirect: "you probably meant this parcel"
         nearest_structured_key, nearest_structured_m, nearest_structured_occ_group,

         -- ⭐ G120(e) - THE ASSEMBLY. A 40-acre campus is rarely one parcel.
         -- ⛔ Adjacency is NOT common ownership: Indiana parcel owner is NULL on all 3,553,381
         -- rows outside Marion, so this says "these adjoin", never "one person owns them".
         neighbours, sliver_neighbours, sliver_acres,
         same_class_neighbours, same_class_acres, assembly_acres_same_class,
         largest_neighbour_acres,

         -- ⭐ G72 - water stress at parcel grain (in_water_parcel, 532,868 rows, unwired until now)
         stress_label AS water_stress, depletion_label AS water_depletion,
         groundwater_decline_label AS water_gw_decline, basins_touched AS water_basins
  FROM ranked
  WHERE has_signal OR rk <= {TOP_PER_COUNTY}
  ORDER BY county_fips, mw_dc DESC"""):
    d = dict(r)
    # drop nulls so the gzipped payload stays lean; the client treats absent as "not measured"
    rows.append({k: v for k, v in d.items() if v is not None and v is not False})

shipped = {}
for x in rows:
    shipped[x["county_fips"]] = shipped.get(x["county_fips"], 0) + 1
for f, v in denom.items():
    v["shipped"] = shipped.get(f, 0)

tot_q = sum(v["qualifying"] for v in denom.values())
tot_s = len(rows)

payload = {
    "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "cap": {
        "per_county": TOP_PER_COUNTY,
        "rule": ("every parcel carrying an owner-motivation signal is shipped uncapped; "
                 f"the rest is the top {TOP_PER_COUNTY} per county by datacentre capacity"),
        "shipped": tot_s,
        "qualifying": tot_q,
        "note": ("THE UI MUST SHOW BOTH NUMBERS. A screener that silently shows a subset looks "
                 "identical to one that searched everything. Open the map console for a full county."),
    },
    # ⚠ REWRITTEN 2026-08-19. The old note said "Withdrawal ... (PJM publishes this)", which was
    # true only while the screener's load side was PJM-only. It now carries BOTH operators, and the
    # MISO half is the LICENSED vendor proxy - which G50 requires be disclosed wherever it renders.
    "direction_note": ("Injection = what a GENERATOR can push into the bus. Withdrawal = what a "
                       "LOAD can pull out, and a data centre is load. These are different "
                       "questions, not two measures of one thing - a bus can be wide open one way "
                       "and full the other."),
    "provenance_note": ("Load-side (withdrawal) figures come from two places and the row says "
                        "which: PJM from OUR OWN case-23 QueueScope harvest (wd_conf = "
                        "'own_harvest'), MISO from our LICENSED Orennia DPP-2025 proxy (wd_conf = "
                        "'vendor_licensed_proxy') because MISO publishes no public load-side "
                        "headroom at all. The licence lapses late 2027."),
    "counties": denom,
    "sites": rows,
}

out = os.path.join(REPO, "data", "screener.json.gz")
with gzip.open(out, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(payload, f, separators=(",", ":"), default=jd)

print(f"screener.json.gz written")
print(f"  shipped     : {tot_s:,} parcels across {len(denom)} counties")
print(f"  qualifying  : {tot_q:,}  ({100*tot_s/tot_q:.1f}% shipped)")
print(f"  uncapped    : {sum(1 for x in rows if x.get('has_signal')):,} signal-carrying parcels")
print(f"  with a LOAD bus  : {sum(1 for x in rows if 'wd_mw' in x):,}")
print(f"  with an INJ bus  : {sum(1 for x in rows if 'inj_mw' in x):,}")
print(f"  size        : {os.path.getsize(out):,} bytes")
print("SCREENER EXPORT COMPLETE")
