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
  data/gridsiting.json.gz   buses (MISO injection + PJM withdrawal), MTEP planned projects,
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
for r in client.query(f"""
  WITH lad AS (
    SELECT poi_name,
           ARRAY_AGG(STRUCT(request_mw, ROUND(headroom_mw, 1) AS mw, request_fits)
                     ORDER BY request_mw) AS ladder
    FROM `{DS}.in_bus_headroom_miso_ladder`
    GROUP BY poi_name
  )
  SELECT m.poi_name, m.bus_number, m.bus_name, m.kv, m.area_name,
         m.worst_mw, m.best_mw, m.median_mw,
         m.facilities_at_zero, m.monitored_facilities, m.worst_binding_facility, m.vintage,
         m.lat, m.lon,
         IFNULL(lad.ladder, []) AS ladder
  FROM `{DS}.in_bus_headroom_miso` m
  LEFT JOIN lad ON lad.poi_name = m.poi_name
  WHERE m.location_status = 'indiana' AND m.lat IS NOT NULL AND m.lon IS NOT NULL"""):
    d = dict(r)
    ladder = [dict(x) for x in (d.get("ladder") or [])]
    # headline = the actual at the smallest rung we hold. The client re-reads `ladder` for the
    # size the user actually selects; this is only the default.
    head = next((x for x in ladder if x["request_mw"] == 100), ladder[0] if ladder else None)
    buses.append({
        "src": "MISO",
        "direction": "injection",          # <- generator-side. NOT a load-serving number.
        "name": d["bus_name"] or d["poi_name"],
        "poi": d["poi_name"],
        "bus": d["bus_number"],
        "kv": d["kv"],
        "area": d["area_name"],
        "mw": r1(head["mw"]) if head else None,      # ACTUAL (min over constraints), not a median
        "mw_basis": "actual at the stated request size (minimum over binding constraints)",
        "ladder": ladder,                            # every rung, so the UI can follow the user
        "ctx_worst": r1(d["worst_mw"]),              # context only - never the headline
        "ctx_best": r1(d["best_mw"]),
        "ctx_median": r1(d["median_mw"]),
        "at_zero": d["facilities_at_zero"],
        "monitored": d["monitored_facilities"],
        "binding": d["worst_binding_facility"],
        "vintage": d["vintage"],
        "conf": "publisher",               # publisher-supplied coordinates
        "lat": r6(d["lat"]), "lon": r6(d["lon"]),
    })
    n_miso += 1

# ---------------------------------------------------------------- PJM: WITHDRAWAL
# This is the direction a data centre actually needs. match_confidence is carried through and
# NOT flattened: a bus placed by prefix match is a weaker claim than one matched exactly, and the
# screener must be able to show that rather than average it away.
n_pjm = 0
for r in client.query(f"""
  SELECT bus_number, bus_label, bus_kv, withdrawal_mw, existing_overloads, facilities,
         binding_facility, case_label, lat, lon, location_method, match_confidence
  FROM `{DS}.vw_pjm_bus_withdrawal_located`
  WHERE lat IS NOT NULL AND lon IS NOT NULL"""):
    d = dict(r)
    kv = None
    try:
        kv = int(float(d["bus_kv"]))
    except (TypeError, ValueError):
        kv = None                          # bus_kv is STRING; unparseable stays NULL, never 0
    buses.append({
        "src": "PJM",
        "direction": "withdrawal",         # <- load-side. This is what a DC needs.
        "name": d["bus_label"],
        "poi": d["bus_label"],
        "bus": d["bus_number"],
        "kv": kv,
        "area": d["case_label"],
        "mw": r1(d["withdrawal_mw"]),
        "mw_worst": None, "mw_best": None, "mw_raw": r1(d["withdrawal_mw"]),
        "at_zero": d["existing_overloads"],
        "monitored": d["facilities"],
        "binding": d["binding_facility"],
        "vintage": d["case_label"],
        "conf": d["match_confidence"] or "unknown",
        "loc_method": d["location_method"],
        "lat": r6(d["lat"]), "lon": r6(d["lon"]),
    })
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
        "costs": "indiana_app.in_lbnl_interconnection_costs",
        "utilities": "indiana_app.in_territories",
    },
}

out = os.path.join(REPO, "data", "gridsiting.json.gz")
with gzip.open(out, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(payload, f, separators=(",", ":"), default=jd)

print(f"gridsiting.json.gz written")
print(f"  buses          : {len(buses):,}  ({n_miso:,} MISO injection + {n_pjm:,} PJM withdrawal)")
print(f"  mtep (Indiana) : {len(mtep):,} planned projects")
print(f"  costs          : {len(costs):,} studied interconnections")
print(f"  utilities      : {len(util):,} service territories")
print(f"  GAPS -> MISO no-coords {gap.miso_no_coords:,} | MISO out-of-state {gap.miso_outside:,} "
      f"| PJM unlocated {gap.pjm_unlocated:,}")
print(f"  size           : {os.path.getsize(out):,} bytes")
print("GRID SITING EXPORT COMPLETE")
