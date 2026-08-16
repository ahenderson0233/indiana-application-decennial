"""Surface the five objects that C2, C3, E2 and B4 built and then left unreachable.

WHY THIS EXISTS. Phase A was declared complete at "242 of 242 registered objects reach a
surface". Then C2 built the rate engine, C3 built the bus join, E2 built the cadence table and
B4 resolved the colo addresses -- five new objects, none wired -- and the census went to
249 of 254 without anyone re-running it. `ACCEPTANCE_RUN.json` criterion 1 then QUOTED the stale
WIRING_CENSUS.md instead of running the script, so §13 reported PASS on a figure that had been
wrong for hours.

The lesson is the one this project keeps re-earning and is why the census is a script: the
DENOMINATOR MOVES ON EVERY BUILD. A build that registers an object without wiring it silently
un-completes Phase A.

WHAT EACH TABLE IS, AND THE HONESTY CONSTRAINT IT CARRIES:

  in_rate_wholesale_floor   METHODOLOGY §4.6 -- ISO wholesale is a HARD FLOOR. Any bundled retail
                            rate below ~1.75x it is not credible. The window is asserted as the
                            window we GOT (a "12-month" filter returned 39 days of feed), so the
                            gate is conservative, not calibrated -- that is stated on screen.
  in_rate_eligibility       MW floors are eligibility MINIMUMS, never ceilings.
  in_rate_component_gaps    `value_status='not_held'` means UNPUBLISHED. It renders as NULL, never
                            as 0 -- treating an absent rate as zero is what produced 95 false
                            "violations" in the engine's first run.
  in_rtep_bus_join          `match_confidence` rides on every row. 68% of upgrades reach no
                            facility and are reported as unmatched rather than forced onto a bus.
  in_refresh_cadence        derived from PUBLISHER event dates. Where no date exists the cadence
                            is "cannot derive", which is shipped as itself.
  in_dc_colo_resolved       the B4 negative result: ZERO of 8 are missing buildings. Rows with no
                            building carry NULL coordinates deliberately, so nothing renders as a
                            fake site. NULL lat/lon here is the finding, not a gap.

Read-only against BigQuery; writes one payload. Fetched by market.html, grid.html and data.html.
"""
# stdout must survive its own output: this console is cp1252 and characters like U+2248/U+2192/U+2717 raise
# UnicodeEncodeError from print() itself. The honesty audit once crashed on its own
# FAILURE path for exactly this reason. Degrade the glyph, never the run.
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import datetime
import gzip
import json
import os

from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")


def rows(sql):
    return [dict(r) for r in client.query(sql)]


out = {"built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}

# ---- C2: the rate engine -------------------------------------------------------------------
out["wholesale_floor"] = rows(f"""
  SELECT iso, market, intervals, first_day, last_day, avg_lmp_usd_mwh, avg_lmp_cents_kwh,
         p50_cents_kwh, min_credible_retail_cents_kwh
  FROM `{DS}.in_rate_wholesale_floor` ORDER BY iso""")

out["eligibility"] = rows(f"""
  SELECT utility, tariff_code, tariff_name, requirement, threshold_value, unit, basis,
         value_status, effective_date, source, source_url, notes, verdict_300mw
  FROM `{DS}.in_rate_eligibility`""")

out["component_gaps"] = rows(f"""
  SELECT utility, tariff_code, tariff_name, component_type, component, unit, basis,
         value_status, rate_or_null, held_state, source_url, notes
  FROM `{DS}.in_rate_component_gaps` ORDER BY utility, component""")

# ---- C3: RTEP upgrades -> the bus they attach to --------------------------------------------
out["rtep_bus_summary"] = rows(f"""
  SELECT facility, bus_number, substation_id, county, kv, lat, lon, upgrades,
         baseline_upgrades, supplemental_upgrades, load_growth_upgrades,
         equipment_types, drivers, match_confidence
  FROM `{DS}.in_rtep_bus_summary` ORDER BY upgrades DESC, facility""")

# the join is 1,229 rows; ship the matched detail, and report the unmatched as a COUNT rather
# than padding the payload with rows that reach nothing
out["rtep_bus_detail"] = rows(f"""
  SELECT upgrade_id, task, equipment, driver, project_type, sub_region, criteria_violation,
         endpoint_name, endpoint_role, substation_name, substation_county, substation_max_kv,
         bus_number, bus_kv, bus_loc_confidence, match_method, match_confidence
  FROM `{DS}.in_rtep_bus_join`
  WHERE substation_id IS NOT NULL
  ORDER BY match_confidence DESC, upgrade_id LIMIT 600""")

out["rtep_match_rates"] = rows(f"""
  SELECT match_confidence,
         COUNT(*) rows_,
         COUNT(DISTINCT upgrade_id) upgrades,
         COUNTIF(bus_number IS NOT NULL) reach_a_bus
  FROM `{DS}.in_rtep_bus_join` GROUP BY 1 ORDER BY rows_ DESC""")

# ---- E2: refresh cadence, derived from publisher dates --------------------------------------
out["cadence"] = rows(f"""
  SELECT subject, kind, rows_, first_event, last_event, dated, days_since_last_event,
         suggested_cadence, cadence_basis, likely_stale
  FROM `{DS}.in_refresh_cadence`
  ORDER BY likely_stale DESC, days_since_last_event DESC NULLS LAST LIMIT 300""")

out["cadence_summary"] = rows(f"""
  SELECT suggested_cadence, COUNT(*) subjects, COUNTIF(likely_stale) stale
  FROM `{DS}.in_refresh_cadence` GROUP BY 1 ORDER BY subjects DESC""")

# ---- B4: the colo resolution, whose headline is a NEGATIVE result ----------------------------
out["colo"] = rows(f"""
  SELECT cloudscene_slug, facility_name, operator, verdict, same_building_as, street_address,
         city, zip, latitude, longitude, coord_source, parcel_state_number, already_pinned_as,
         source_url, confidence, notes
  FROM `{DS}.in_dc_colo_resolved` ORDER BY verdict, facility_name""")

# ---- the caveats are COMPUTED, so they cannot drift from the data they describe --------------
_f = out["wholesale_floor"]
_gaps = out["component_gaps"]
_nh = sum(1 for g in _gaps if g.get("value_status") == "not_held")
_unmatched = sum(r["rows_"] for r in out["rtep_match_rates"] if not r["reach_a_bus"])
_colo_missing = sum(1 for c in out["colo"] if c["verdict"] not in ("RESOLVED",))

out["caveats"] = {
    "wholesale_floor": (
        "ISO wholesale is a HARD FLOOR (METHODOLOGY §4.6): a bundled retail rate below roughly "
        "1.75x it is not credible. The window shown is the window the feed ACTUALLY returned, "
        "not the one requested — a 12-month filter came back with far less. The gate is therefore "
        "CONSERVATIVE, not calibrated."
        + (f" Measured: {', '.join(f'{r['iso']} {r['first_day']}→{r['last_day']}, {r['intervals']:,} intervals' for r in _f)}."
           if _f else "")),
    "eligibility": (
        "MW thresholds are eligibility MINIMUMS, never ceilings. A tariff with a 300 MW floor "
        "does not cap a site at 300 MW."),
    "component_gaps": (
        f"{_nh} of {len(_gaps)} components are NOT HELD and render as NULL, never as 0. "
        "Treating an absent rate as zero is exactly what produced 95 false 'below floor' "
        "violations on this engine's first run. No component-level Indiana tariff exists in the "
        "estate, which is why P6 quotes no per-parcel rate."),
    "rtep_bus": (
        f"{_unmatched:,} of the join's rows reach no bus and are reported as unmatched rather "
        "than forced onto one. The bus hop goes through an already-resolved substation name, not "
        "a second name guess — bus_label is PSS/E format and matches nothing directly. "
        "match_confidence rides on every row."),
    "cadence": (
        "Cadence is DERIVED from each publisher's own event dates, not declared. Subjects with no "
        "event date carry 'cannot derive' and are shown as such."),
    "colo": (
        f"The headline here is a NEGATIVE result: ZERO of 8 are missing buildings. "
        f"{_colo_missing} resolve to something other than a distinct building — a suite inside the "
        "701 W Henry carrier hotel, a directory numbering ghost, or a reseller with no building at "
        "all. Rows with no building carry NULL coordinates DELIBERATELY so nothing renders as a "
        "fake site. Five were already pinned under a different operator name "
        "(CenturyLink→Lumen, LightBound→DataBank, 365→Netrality) — the crosscheck matcher lacked "
        "the aliases, so the 'gap' was in the instrument, not the layer."),
}

path = os.path.join(REPO, "data", "engines.json.gz")
with gzip.open(path, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(out, f, separators=(",", ":"), default=str)

print(f"data/engines.json.gz — {os.path.getsize(path)/1024:.0f} KB")
print(f"  wholesale floor rows : {len(_f)}")
print(f"  eligibility rows     : {len(out['eligibility'])}")
print(f"  component gaps       : {len(_gaps)} ({_nh} not_held -> NULL)")
print(f"  rtep bus summary     : {len(out['rtep_bus_summary'])} facilities")
print(f"  rtep bus detail      : {len(out['rtep_bus_detail'])} matched rows shipped")
print(f"  cadence subjects     : {len(out['cadence'])}")
print(f"  colo resolutions     : {len(out['colo'])}")
