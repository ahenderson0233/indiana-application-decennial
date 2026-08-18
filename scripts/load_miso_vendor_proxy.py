"""MISO bus headroom - LICENSED VENDOR PROXY, loaded under an explicit operator ruling.

    OPERATOR RULING 2026-08-18: "For MISO, I believe using the Orennia values as a direct proxy
    is the best option for us, and I am fine if you wire that in."

WHY THIS EXISTS, and why it is the ONLY vendor data in the estate
-----------------------------------------------------------------
MISO parity from public sources is not reachable, and the reason is measured, not assumed
(docs/BUS_PARITY_2026-08-18.md, Finding 2). Applying our own rule ladder to DPP-2021:

    raw MIN over all facilities          1 of 642 POIs above zero  (0.2%)
    excluding pre-existing overloads   642 of 642 POIs above zero  (100.0%)
    the vendor's ERIS-mitigated 2025                                 40.8%

The entire distance between 0.2% and 100% is WHICH pre-existing overloads were mitigated away.
Our case is unmitigated DPP-2021; theirs is a mitigated DPP-2025 cycle. Four independent sweeps
established that study has no public route: CartoVista rows return 403 ProtectedData under the
correct POST verb even inside the viewer's own session, giqueue is structurally DPP-2021 with no
cycle parameter anywhere in its endpoint surface, MISO's own API exposes only the queue endpoint,
and FERC ER24-2046 establishes the data is owed publicly only as interactive query responses.

So this is a MISSING INPUT, not a defective method - and it is the one input we are structurally
barred from obtaining.

RULES THIS TABLE LIVES UNDER
----------------------------
1. ISOLATED. Its own table, never blended into a column that also carries publicly-derived
   numbers. Every row is stamped provenance_class='vendor_licensed_proxy'.
2. REMOVABLE IN ONE COMMIT. When a public DPP-2025 route appears, drop this table and its
   registry rows; nothing else references it structurally.
3. NAMED ON THE FACE OF THE SURFACE. Any UI rendering these values must say the source, not
   bury it in a footnote. An estimate never styles as a published figure.
4. SUBSCRIPTION-BOUND. The licence lapses late 2027 and these values cannot remain in the tools
   after that. `licence_expires_note` carries that on every row so it cannot be forgotten.
5. NOT A YARDSTICK FILE. scripts/benchmark_vs_orennia.py still writes markdown only. This is a
   separate, deliberate, operator-authorised exception for MISO headroom ALONE.

RE-SCRAPE COMMAND: python scripts/load_miso_vendor_proxy.py --load
"""
import argparse
import csv
import datetime
import hashlib
import os
import sys

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
TABLE = f"{DS}.in_bus_headroom_miso_vendor"
# 2026-08-18 refreshed export. The MISO powerflow case is UNCHANGED between the June and August
# extracts (DPP-2025-Cycle_SUM_D_ERIS-mitigated_Final), so this is more rows of the same study, not
# a new vintage. The PJM case DID change in that same refresh - see docs/BUS_PARITY_2026-08-18.md.
SRC = (r"C:\Users\ahend\Downloads"
       r"\Greenfield Interconnection Capacity, Buses-2026-08-18T13-54-02.csv")

# RESOLVE COLUMNS BY NAME FROM THE HEADER, THEN USE POSITIONS. Both halves matter:
#
#   * NOT csv.DictReader, because the file has TWO columns both called "Bus ID". DictReader keeps
#     the LAST one silently, which is how an earlier join reported 0 overlap between their bus set
#     and ours when the true overlap is 282 of 297.
#   * NOT hardcoded positions either. The 2026-08-18 export RESHUFFLED EVERY COLUMN and the
#     hardcoded map from the June file parsed 0 MISO rows out of 17,146 - it did not error, it just
#     silently found nothing. Same partial-enumeration failure as the [:12] clip.
#
# So: take the FIRST index of each wanted name, tolerate the renames the vendor has already made,
# and ABORT if a required column is missing rather than loading a column of NULLs.
ALIASES = {
    "bus_id": ["Bus ID"],
    "bus_name": ["Bus Name"],
    "bus_kv": ["Bus Voltage (kV)"],
    "direction": ["Interconnection Type"],
    "capacity_mw": ["Bus Interconnection Capacity (MW)"],
    # renamed between the June and August exports
    "tier": ["Number of Upgrades Assumed", "Number of Upgrades Assumed (Upgrades)"],
    "constraint": ["Primary Limiting Constraint"],
    "contingency": ["Contingency Name"],
    "shift": ["Shift Factor (Number)"],
    "cutoff": ["Shift Factor Cutoff Ratio"],
    "overload": ["Existing Overload Flag"],
    "ltc": ["Local Transfer Capacity (MW)"],
    "case": ["Powerflow Case"],
    "year": ["Study Year"],
    "county": ["County"],
    "iso": ["ISO"],
    "lat": ["Latitude (Degrees)"],
    "lon": ["Longitude (Degrees)"],
    "locsrc": ["Location Source"],
    "owner": ["Owner"],
}
# 'State' was present in June and DROPPED in August. Optional, never required - and its absence is
# why the loader must not assume a fixed shape.
OPTIONAL = {"state": ["State"]}
REQUIRED = set(ALIASES)


def resolve(header):
    idx = {}
    for key, names in {**ALIASES, **OPTIONAL}.items():
        for nm in names:
            if nm in header:
                idx[key] = header.index(nm)  # FIRST occurrence - handles the duplicate Bus ID
                break
    missing = REQUIRED - set(idx)
    if missing:
        sys.exit(f"FAILED: export is missing required column(s): {sorted(missing)}\n"
                 f"        The vendor has changed the schema again - update ALIASES.")
    return idx

SCHEMA = [
    bigquery.SchemaField("bus_id", "STRING"),
    bigquery.SchemaField("bus_number", "INT64"),
    bigquery.SchemaField("bus_name", "STRING"),
    bigquery.SchemaField("bus_kv", "FLOAT64"),
    bigquery.SchemaField("operating_mode", "STRING"),
    bigquery.SchemaField("upgrade_tier", "INT64"),
    bigquery.SchemaField("capacity_mw", "FLOAT64"),
    bigquery.SchemaField("primary_limiting_constraint", "STRING"),
    bigquery.SchemaField("contingency_name", "STRING"),
    bigquery.SchemaField("shift_factor", "FLOAT64"),
    bigquery.SchemaField("shift_factor_cutoff", "FLOAT64"),
    bigquery.SchemaField("existing_overload_flag", "BOOL"),
    bigquery.SchemaField("local_transfer_capacity_mw", "FLOAT64"),
    bigquery.SchemaField("powerflow_case", "STRING"),
    bigquery.SchemaField("study_year", "STRING"),
    bigquery.SchemaField("county", "STRING"),
    bigquery.SchemaField("state", "STRING"),
    bigquery.SchemaField("lat", "FLOAT64"),
    bigquery.SchemaField("lon", "FLOAT64"),
    bigquery.SchemaField("location_source", "STRING"),
    bigquery.SchemaField("owner", "STRING"),
    bigquery.SchemaField("provenance_class", "STRING"),
    bigquery.SchemaField("licence_expires_note", "STRING"),
    bigquery.SchemaField("_source_file", "STRING"),
    bigquery.SchemaField("_source_sha256", "STRING"),
    bigquery.SchemaField("_loaded_at", "TIMESTAMP"),
]

LICENCE_NOTE = ("LICENSED VENDOR VALUE - not publicly derived. Subscription lapses late 2027; "
                "these values must be removed from the tools at that point. Replace with our own "
                "derivation when a public DPP-2025 route exists.")


def fnum(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def read_rows():
    if not os.path.exists(SRC):
        sys.exit(f"FAILED: source not found: {SRC}")
    sha = hashlib.sha256(open(SRC, "rb").read()).hexdigest()
    rd = csv.reader(open(SRC, encoding="utf-8-sig", newline=""))
    ix = resolve(next(rd))
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def g(row, key):
        i = ix.get(key)
        return row[i] if i is not None and i < len(row) else ""

    out = []
    for r in rd:
        if g(r, "iso") != "MISO":
            continue
        bid = g(r, "bus_id")
        tier = g(r, "tier")
        out.append({
            "bus_id": bid,
            "bus_number": int(bid.split("_", 1)[-1]) if bid.split("_", 1)[-1].isdigit() else None,
            "bus_name": g(r, "bus_name") or None,
            "bus_kv": fnum(g(r, "bus_kv")),
            "operating_mode": g(r, "direction") or None,
            "upgrade_tier": int(tier) if tier.isdigit() else None,
            "capacity_mw": fnum(g(r, "capacity_mw")),
            "primary_limiting_constraint": g(r, "constraint") or None,
            "contingency_name": g(r, "contingency") or None,
            "shift_factor": fnum(g(r, "shift")),
            "shift_factor_cutoff": fnum(g(r, "cutoff")),
            # never coerce a blank to False - an unstated flag is unknown
            "existing_overload_flag": (None if not g(r, "overload").strip()
                                       else g(r, "overload").strip().lower() == "true"),
            "local_transfer_capacity_mw": fnum(g(r, "ltc")),
            "powerflow_case": g(r, "case") or None,
            "study_year": g(r, "year") or None,
            "county": g(r, "county") or None,
            "state": g(r, "state") or None,
            "lat": fnum(g(r, "lat")),
            "lon": fnum(g(r, "lon")),
            "location_source": g(r, "locsrc") or None,
            "owner": g(r, "owner") or None,
            "provenance_class": "vendor_licensed_proxy",
            "licence_expires_note": LICENCE_NOTE,
            "_source_file": os.path.basename(SRC),
            "_source_sha256": sha,
            "_loaded_at": now,
        })
    return out, sha


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--load", action="store_true")
    a = ap.parse_args()

    rows, sha = read_rows()
    print(f"MISO rows parsed: {len(rows):,}")
    buses = {r["bus_id"] for r in rows}
    tiers = sorted({r["upgrade_tier"] for r in rows if r["upgrade_tier"] is not None})
    dirs = sorted({r["operating_mode"] for r in rows if r["operating_mode"]})
    t0 = [r for r in rows if r["upgrade_tier"] == 0 and r["capacity_mw"] is not None]
    pos = sum(1 for r in t0 if r["capacity_mw"] > 0)
    print(f"  buses={len(buses):,}  tiers={tiers}  directions={dirs}")
    print(f"  tier-0 rows={len(t0):,}  above zero={pos:,} ({100 * pos / max(len(t0), 1):.1f}%)")
    print(f"  source sha256={sha[:16]}...")
    if not a.load:
        print("\n(dry run - pass --load to write)")
        return

    client = bigquery.Client(project="energy-platfrom")
    job = client.load_table_from_json(
        rows, TABLE,
        job_config=bigquery.LoadJobConfig(schema=SCHEMA, write_disposition="WRITE_TRUNCATE"))
    job.result()
    n = client.get_table(TABLE).num_rows
    print(f"loaded {TABLE}: {n:,} rows")

    notes = (
        "MISO bus interconnection capacity - LICENSED VENDOR PROXY (Orennia extract), loaded under "
        "operator ruling 2026-08-18 because MISO parity has no public route. "
        "PROVENANCE: every row provenance_class='vendor_licensed_proxy'. NOT publicly derived. "
        "SUBSCRIPTION-BOUND: licence lapses late 2027; remove then. "
        "WHY: our DPP-2021 rule ladder brackets their value 0.2%-100% against their 40.8%; the gap "
        "is which pre-existing overloads their ERIS-mitigated DPP-2025 case removed, and four "
        "sweeps proved that study has no public route (CartoVista 403 ProtectedData, giqueue "
        "structurally DPP-2021, MISO API queue-endpoint only, FERC ER24-2046 interactive-only). "
        f"SOURCE FILE: {os.path.basename(SRC)} sha256={sha}. "
        "PUBLISHER VINTAGE: powerflow case DPP-2025-Cycle_SUM_D_ERIS-mitigated_Final. "
        "EXCLUDED: PJM and SERC rows (we derive PJM ourselves from QueueScope case 23). "
        "RE-SCRAPE COMMAND: python scripts/load_miso_vendor_proxy.py --load")

    # source AND method are required: the honesty audit's provenance-completeness check counts
    # any object missing either one, and an incomplete row failed it the first time this ran.
    source = ("Orennia 'Greenfield Interconnection Capacity, Buses' extract 2026-06-23 "
              "(licensed vendor CSV), MISO rows only")
    method = ("Direct load of the vendor's per-bus tier-0..4 capacity, ISO='MISO' slice, read "
              "POSITIONALLY because the file has two columns named 'Bus ID'. LICENSED PROXY under "
              "operator ruling 2026-08-18: MISO parity has no public route (DPP-2025 is CEII). "
              "Not publicly derived; must be removed when the subscription lapses late 2027.")
    client.query(f"""
        INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at, notes)
        VALUES ('in_bus_headroom_miso_vendor', @source, @method, {n}, CURRENT_TIMESTAMP(), @notes)""",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("source", "STRING", source),
            bigquery.ScalarQueryParameter("method", "STRING", method),
            bigquery.ScalarQueryParameter("notes", "STRING", notes)])).result()
    print("registered in indiana_app._registry")

    # column names READ from the live schema, not guessed: it is what_it_provides, not provides,
    # and there is no rescrape_command column - the command lives in notes.
    client.query("""
        INSERT INTO `energy-platfrom.energy.registry_sources`
          (source_name, source_id, endpoint, endpoint_kind, access, status, what_it_provides,
           object_names, measured_rows, category, geography_state, acquisition_method, notes)
        VALUES ('orennia-miso-bus-capacity-proxy', 'orennia_miso_bus_capacity_proxy', @src,
                'vendor_csv', 'licensed', 'LOADED_AS_PROXY',
                'MISO bus interconnection capacity, tiers 0-4, both directions, DPP-2025 ERIS-mitigated',
                @objs, @n,
                'grid', 'IN', 'licensed_vendor_extract', @notes)""",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("src", "STRING", SRC),
            bigquery.ArrayQueryParameter(
                "objs", "STRING", ["energy-platfrom.indiana_app.in_bus_headroom_miso_vendor"]),
            bigquery.ScalarQueryParameter("n", "INT64", n),
            bigquery.ScalarQueryParameter("notes", "STRING", notes)])).result()
    print("appended to energy.registry_sources")


if __name__ == "__main__":
    main()
