"""Export the grid-siting payload: bus headroom, planned transmission, interconnection cost.

WHY THIS EXISTS. The app screens grid access as "within X miles of a substation >= Y kV". That is a
PROXIMITY test, and proximity is not capacity. A parcel 0.4 mi from a 345 kV substation with zero
available headroom is a worse site than one 3 mi from a bus with 800 MW, and the current screener
ranks them the other way round. The warehouse already holds the capacity answer and nothing
surfaced it: 642 located MISO buses, 229 located PJM buses, 328 MTEP planned projects and 116 real
LBNL interconnection cost studies were all registered and unreachable from any page.

*** THE ONE THING THIS FILE EXISTS TO KEEP STRAIGHT: DIRECTION. ***

    MISO publishes INJECTION headroom  -- how much a GENERATOR can push INTO the bus.
    PJM  publishes WITHDRAWAL capacity -- how much a LOAD can pull OUT of the bus.

A data centre is LOAD. It needs WITHDRAWAL. Injection headroom is not a weaker version of the same
number, it is a different question, and a 5,000 MW injection figure says nothing about whether a
300 MW load can be served. Merging them into one "headroom_mw" column would produce a screener that
ranks confidently and wrongly across two thirds of the state -- and it would look completely normal,
because both are large positive MW figures from real ISO models.

So `direction` rides on EVERY bus row, no row is emitted without it, and the client is expected to
filter on it rather than average across it. The count of each is printed on every run.

COVERAGE IS NOT SYMMETRIC, AND THE PAYLOAD SAYS SO:
  * MISO 642 of 11,820 rows are Indiana-located. 2,212 more are joinable but carry NO coordinates
    and 8,966 are outside Indiana. Emitting only the 642 is correct; recording the 2,212 as a
    known gap is also correct, because "no bus near this parcel" and "we could not place the bus"
    are different findings and only one of them is about the site.
  * PJM 229 of 1,475 rows are located at all; the other 1,246 have location_method='none'.
    Those 1,246 are counted in the gap ledger, never dropped silently.

Outputs (gzipped; the client decompresses natively via DecompressionStream):
  data/gridsiting.json.gz   buses (MISO + PJM, BOTH directions each), MTEP planned projects,
                            LBNL interconnection costs, utility stakeholder table, gap ledger

READS indiana_app ONLY. An export is on the path to what the user sees, so the app stays
rebuildable without the platform dataset (see build_si_plottability_clip.py).
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
client = bigquery.Client(project="energy-platfrom")


def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    if isinstance(o, decimal.Decimal):
        return float(o)
    return str(o)


def r6(x):
    return None if x is None else round(float(x), 6)


def r1(x):
    return None if x is None else round(float(x), 1)


def rows(sql):
    """Every row of a query as plain dicts. ⚠ Added for G130 rather than writing a second query
    idiom inline - this file already builds `mtep` and `buses` with hand-rolled loops, and a third
    shape would be the two-copies drift this project keeps paying for."""
    return [dict(x) for x in client.query(sql)]


buses = []

# ---------------------------------------------------------------- MISO: INJECTION
# location_status='indiana' is the publisher's own placement, not a centroid we derived.
#
# ⛔ THE HEADLINE IS THE ACTUAL, WHICH IS A **MINIMUM** OVER CONSTRAINTS. NOT A MEDIAN.
# This file previously published `median_mw` as the headline and that was badly wrong.
# Headroom is set by the FIRST constraint to bind, so it is a min; a median across the monitored
# facility x contingency set mixes the binding constraint in with dozens of unconstrained ones and
# answers a question nobody asked. Measured 2026-08-17: `median_mw` averages ~1,193 MW across the
# 642 Indiana POIs, while the actual at a 300 MW request is **0 MW on 641 of 642** — because
# `facilities_at_zero` averages 15.8 of 59.8 monitored facilities, i.e. the binding constraints are
# already at their limit in the base case. Publishing the median would have told a user a bus had
# ~1,193 MW available when it has none.
#
# Operator, 2026-08-17: "we use worst, median, and best case scenarios, and we should really only
# be presenting the 'actuals' as Orennia does." Correct, and the worst/median/best columns were
# never a methodology choice - they were a workaround for a degenerate probe run at
# pmax_request=99999, which returned worst_mw=0 on ~88% of POIs.
#
# So: the headline comes from the LADDER (the actual at each stated request size), and
# worst/best ride along as context only, clearly named as such.
n_miso = 0
# ---------------------------------------------------------------------------------------------
# ⭐ ONE SOURCE FOR BOTH ISOs AND BOTH DIRECTIONS: in_bus_capacity_tier0.
#
# This export used to read `in_bus_headroom_miso` (DPP-2021, INJECTION only) and
# `vw_pjm_bus_withdrawal_located` (the superseded 2027 RTEP case) DIRECTLY, bypassing tier0
# entirely. Two consequences reached the dossier, which is the document a developer carries to a
# utility:
#   * across the two thirds of Indiana inside MISO, the only number available was the GENERATOR
#     direction. A data centre asking "how much load can I connect here" got the wrong question
#     answered, or silence.
#   * PJM was screened against a study we had already replaced.
#
# Now: MISO from the operator-authorised Orennia DPP-2025 proxy (both directions, every bus
# located), PJM from our own case-23 harvest (both directions, 1,826 buses). One vintage per ISO,
# stated on every row, so nothing on a map mixes two studies.
#
# ⚠ The PJM figure is headroom at a 100 MW PROBE, not a bus maximum - we hold no other scenario
# yet. `probe_mw` rides on the row and the surfaces say so.
n_miso = n_pjm = 0
for r in client.query(f"""
  SELECT iso, interconnection_type, bus_id, bus_name, bus_voltage_kv, bus_area,
         bus_interconnection_capacity_mw AS mw, primary_limiting_constraint,
         existing_overload_flag, n_facilities_overloaded_base, n_monitored_facilities,
         constraint_headroom_mw, powerflow_case, latitude, longitude, provenance_class, probe_mw
  FROM `{DS}.in_bus_capacity_tier0`
  WHERE latitude IS NOT NULL AND longitude IS NOT NULL"""):
    d = dict(r)
    direction = (d["interconnection_type"] or "").lower()      # "withdrawal" | "injection"
    buses.append({
        "src": d["iso"],
        "direction": direction,
        "name": d["bus_name"] or d["bus_id"],
        "poi": d["bus_name"] or d["bus_id"],
        "bus": d["bus_id"],
        "kv": int(d["bus_voltage_kv"]) if d["bus_voltage_kv"] else None,
        "area": d["bus_area"],
        "mw": r1(d["mw"]),
        "mw_basis": ("headroom at a 100 MW probe - the tightest facility with |shift factor| >= 5% "
                     "that is not already over its rating. NOT a bus maximum: we hold no other "
                     "scenario yet" if d["iso"] == "PJM" else
                     "vendor-published interconnection capacity, minimum over binding constraints, "
                     "excluding facilities already over their rating"),
        "binding": d["primary_limiting_constraint"],
        "monitored": d["n_monitored_facilities"],
        "at_zero": d["n_facilities_overloaded_base"],
        "overloaded_base": d["n_facilities_overloaded_base"],
        "best_facility_mw": r1(d["constraint_headroom_mw"]),
        "vintage": d["powerflow_case"],
        # a reader must be able to see which rows are licensed vendor data and which we derived
        "provenance": d["provenance_class"],
        "probe_mw": d["probe_mw"],
        "conf": "publisher" if d["provenance_class"] != "own_harvest" else "estimated",
        "lat": r6(d["latitude"]), "lon": r6(d["longitude"]),
    })
    if d["iso"] == "MISO":
        n_miso += 1
    else:
        n_pjm += 1

# ---------------------------------------------------------------- MTEP planned transmission
# The Illinois dashboard's "planned grid investments" idea: where capacity is going to appear,
# which no existing-asset layer shows. MTEP Appendix A carries NO coordinates -- it names
# from_sub/to_sub instead -- so these are emitted as a TABLE keyed by substation name, not as
# map points. Inventing a point for them would be a centroid by another name.
mtep = []
for r in client.query(f"""
  SELECT target_mtep_cycle, mtep_project_id, project, project_type, name, facility_description,
         facility_owner_s, planning_status, current_cost, expected_isd, facility_type,
         from_sub, to_sub, max_kv, estimated_miles_new, estimated_miles_upgrade,
         state_1, state_2, prov_source_url
  FROM `{DS}.in_txexp_miso_mtep_appendix_a_status`
  WHERE UPPER(IFNULL(state_1,'')) IN ('IN','INDIANA') OR UPPER(IFNULL(state_2,'')) IN ('IN','INDIANA')
  ORDER BY expected_isd"""):
    mtep.append(dict(r))

# ---------------------------------------------------------------- LBNL interconnection costs
# Real studied $/kW from completed interconnection studies. Every column in this table is STRING
# (it is a spreadsheet lift), so numeric coercion happens HERE and unparseable stays NULL rather
# than becoming 0 -- an unpublished cost is not a free interconnection.
def num(s):
    try:
        v = float(str(s).replace(",", "").replace("$", "").strip())
        return round(v, 2)
    except (TypeError, ValueError):
        return None


costs = []
for r in client.query(f"""
  SELECT project, state, county, transmission_owner, balancing_authority, fuel, resource_type,
         nameplate_mw, request_status, study_type, study_year,
         _2022_poi_cost_kw, _2022_network_cost_kw, _2022_total_cost_kw,
         _2024_poi_cost_kw, _2024_network_cost_kw, _2024_total_cost_kw,
         transmission_voltage, poi_transmission_line
  FROM `{DS}.in_lbnl_interconnection_costs`"""):
    d = dict(r)
    costs.append({
        "project": d["project"], "state": d["state"], "county": d["county"],
        "owner": d["transmission_owner"], "ba": d["balancing_authority"],
        "fuel": d["fuel"] or d["resource_type"],
        "mw": num(d["nameplate_mw"]), "status": d["request_status"],
        "study": d["study_type"], "year": d["study_year"],
        "poi_kw": num(d["_2024_poi_cost_kw"]) if num(d["_2024_poi_cost_kw"]) is not None else num(d["_2022_poi_cost_kw"]),
        "net_kw": num(d["_2024_network_cost_kw"]) if num(d["_2024_network_cost_kw"]) is not None else num(d["_2022_network_cost_kw"]),
        "tot_kw": num(d["_2024_total_cost_kw"]) if num(d["_2024_total_cost_kw"]) is not None else num(d["_2022_total_cost_kw"]),
        "kv": d["transmission_voltage"], "line": d["poi_transmission_line"],
    })

# ---------------------------------------------------------------- utility stakeholder table
# Feeds "Figure 1: Electric Stakeholder Roles and Responsibilities" on the dossier: who serves the
# site, who generates, who owns the wires, and who balances. control_area is the balancing
# authority and is the field that tells a reader whether they are in MISO or PJM at all.
util = []
for r in client.query(f"""
  SELECT territory_id, utility, utility_type, holding_company, regulated, control_area,
         customers, summer_peak_mw, retail_mwh, data_year
  FROM `{DS}.in_territories`
  ORDER BY IFNULL(customers,0) DESC"""):
    util.append(dict(r))

# ---------------------------------------------------------------- the gap ledger
# Cannot-assess renders as itself. These are the rows we hold but cannot place, counted so that
# "no bus near this parcel" can never be confused with "we could not locate the bus".
gap = list(client.query(f"""
  SELECT
    (SELECT COUNT(*) FROM `{DS}.in_bus_headroom_miso` WHERE location_status='joinable_no_coords') AS miso_no_coords,
    (SELECT COUNT(*) FROM `{DS}.in_bus_headroom_miso` WHERE location_status='outside_indiana')    AS miso_outside,
    (SELECT COUNT(*) FROM `{DS}.vw_pjm_bus_withdrawal_located` WHERE lat IS NULL)                 AS pjm_unlocated,
    (SELECT COUNT(*) FROM `{DS}.in_txexp_miso_mtep_appendix_a_status`)                            AS mtep_all
"""))[0]

payload = {
    "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "direction_note": (
        "MISO publishes INJECTION headroom (generator-side). PJM publishes WITHDRAWAL capacity "
        "(load-side). A data centre is load and needs withdrawal. These are different questions, "
        "not two measurements of one quantity - do not average or compare them across sources."
    ),
    "buses": buses,
    # ⭐ G130, operator 2026-08-20f: "what is our current coverage of system upgrades?" - the
    # answer belongs on the page, generated, so it cannot go stale in a chat reply or a document.
    "planned_by_source": rows(f"""
      SELECT source, COUNT(*) AS projects,
             COUNTIF(lat IS NOT NULL) AS placed,
             COUNTIF(status_class IN ('proposed','approved','filed_plan')) AS still_to_come,
             -- ⭐ THE SECOND DENOMINATOR (operator ruling 2026-08-21). Coverage over EVERYTHING
             -- mixes in 1,248 already-built projects and understates how well we can place the
             -- work that has not happened yet, which is the only work a siter is choosing between.
             COUNTIF(lat IS NOT NULL AND status_class IN ('proposed','approved','filed_plan'))
               AS placed_still_to_come,
             ROUND(SUM(cost_usd_m)) AS cost_usd_m
      FROM `{DS}.in_planned_upgrades` GROUP BY 1 ORDER BY 2 DESC"""),
    "planned_by_method": rows(f"""
      SELECT loc_method, ANY_VALUE(loc_basis) AS basis, COUNT(*) AS projects,
             ROUND(AVG(uncertainty_mi), 1) AS ring_mi
      FROM `{DS}.in_planned_upgrades` GROUP BY 1 ORDER BY 3 DESC"""),
    # ⭐ G130 item 1-2: what the planned work will COST, and who bears it.
    # ⛔ The MISO figure is INDIANA ONLY. The published DPP-2025 table spans 14 states and totals
    # $29,522M / 56,043 MW; three of this project's own documents quoted that as the Indiana
    # answer. Indiana is 21 projects. Operator ruling 2026-08-21: Indiana only, and the
    # MISO-wide total is not carried anywhere on any surface.
    "planned_cost": rows(f"""
      SELECT 'MISO DPP-2025 interconnection (Indiana)' AS what,
             COUNT(*) AS projects, ROUND(SUM(cost_usd_m)) AS cost_usd_m,
             ROUND(SUM(mw_enabled)) AS mw,
             ROUND(1000 * SUM(cost_usd_m) / NULLIF(SUM(mw_enabled), 0)) AS k_per_mw
      FROM `{DS}.in_planned_upgrades` WHERE source = 'MISO DPP-2025'"""),
    # ⚠ 26 UPGRADES, NOT 375 ROWS. in_pjm_rtep_cost_allocations holds 375 rows because it is a
    # per-ZONE breakdown - 21 to 24 zones per upgrade. Reporting the row count as coverage would
    # overstate it fourteenfold.
    "planned_alloc": rows(f"""
      SELECT COUNTIF(alloc_n_zones IS NOT NULL) AS upgrades_with_allocation,
             COUNTIF(source = 'PJM RTEP') AS pjm_upgrades,
             SUM(alloc_n_zones) AS zone_shares
      FROM `{DS}.in_planned_upgrades`"""),
    # ⛔ REFUSALS ARE PUBLISHED, NOT HIDDEN. A guard that silently drops a row is
    # indistinguishable to a reader from data we never held.
    "planned_refused": rows(f"""
      SELECT placement_refused AS reason, COUNT(*) AS projects
      FROM `{DS}.in_planned_upgrades`
      WHERE placement_refused IS NOT NULL GROUP BY 1 ORDER BY 2 DESC"""),
    "mtep": mtep,
    "costs": costs,
    "utilities": util,
    "gaps": {
        "miso_buses_joinable_but_no_coordinates": gap.miso_no_coords,
        "miso_buses_outside_indiana": gap.miso_outside,
        "pjm_buses_never_located": gap.pjm_unlocated,
        "mtep_projects_all_states": gap.mtep_all,
        "note": "listed, never rendered as zero and never dropped",
    },
    "provenance": {
        "buses_miso": "indiana_app.in_bus_headroom_miso (location_status='indiana')",
        "buses_pjm": "indiana_app.vw_pjm_bus_withdrawal_located",
        "mtep": "indiana_app.in_txexp_miso_mtep_appendix_a_status (state_1/state_2 = IN)",
        "planned": "indiana_app.in_planned_upgrades (PJM RTEP + MISO MTEP + IURC grid plans, "
                   "placed by a tiered method with an uncertainty radius)",
        "costs": "indiana_app.in_lbnl_interconnection_costs",
        "utilities": "indiana_app.in_territories",
    },
}

out = os.path.join(REPO, "data", "gridsiting.json.gz")
with gzip.open(out, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(payload, f, separators=(",", ":"), default=jd)

print(f"gridsiting.json.gz written")
print(f"  buses          : {len(buses):,}  ({n_miso:,} MISO + {n_pjm:,} PJM, both directions each)")
print(f"  mtep (Indiana) : {len(mtep):,} planned projects")
print(f"  costs          : {len(costs):,} studied interconnections")
print(f"  utilities      : {len(util):,} service territories")
print(f"  GAPS -> MISO no-coords {gap.miso_no_coords:,} | MISO out-of-state {gap.miso_outside:,} "
      f"| PJM unlocated {gap.pjm_unlocated:,}")
print(f"  size           : {os.path.getsize(out):,} bytes")
print("GRID SITING EXPORT COMPLETE")
