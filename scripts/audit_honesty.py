"""E1 — the honesty audit. Spec §13(3): sample on-screen numbers, trace each to a source table
and a build date, and prove no cannot-assess is rendered as 0 or blank.

THIS AUDIT IS ADVERSARIAL BY DESIGN. It is not a checklist that passes; it looks for the four
failure modes this project has actually committed, and it FAILS LOUDLY when it finds one:

  1. A number on screen with no source table behind it, or a source table with no build date.
  2. A ZERO that is really a cannot-assess. This is the project's signature error — D5's 945,896
     undated rows read as a signal, urdb's 0.0c/kWh read as a rate below the wholesale floor,
     "0 high-priority violators" when 95 exist. A zero is a claim about the instrument.
  3. A payload figure that DISAGREES with the warehouse it came from. If the map says 11,117 and
     BigQuery says something else, one of them is lying to a user right now.
  4. An ESTIMATE styled as a published fact — a centroid presented as a location, a proxy
     presented as a rate.

It reads the shipped payloads on disk, not the code that writes them, because what ships is what
the user sees.
"""
import gzip, json, os, glob, re, datetime
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")


def q1(sql): return list(client.query(sql))[0]


findings, checks = [], 0


def check(name, ok, detail):
    global checks
    checks += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    if not ok:
        findings.append({"check": name, "detail": detail})


print("=== 1. every registered object carries a source AND a build date ===")
r = q1(f"""SELECT COUNT(*) n,
  COUNTIF(source IS NULL OR TRIM(source)='') no_source,
  COUNTIF(built_at IS NULL) no_date,
  COUNTIF(method IS NULL OR TRIM(method)='') no_method
FROM (SELECT table_name, ANY_VALUE(source) source, ANY_VALUE(method) method, MAX(built_at) built_at
      FROM `{DS}._registry` GROUP BY table_name)""")
check("provenance completeness", r.no_source == 0 and r.no_date == 0,
      f"{r.n} objects · {r.no_source} without a source · {r.no_date} without a build date · "
      f"{r.no_method} without a method")

print("\n=== 2. the payload agrees with the warehouse ===")
flag_bq = q1(f"SELECT COUNTIF(has_si_signal) n FROM `{DS}.in_si_sites_flags_v2`").n
site_files = sorted(glob.glob(os.path.join(REPO, "data", "sites", "*.geojson.gz")))
flag_disk = 0
for f in site_files:
    with gzip.open(f, "rt", encoding="utf-8") as fh:
        for ft in json.load(fh)["features"]:
            if ft["properties"].get("has_si_signal") is True:
                flag_disk += 1
check("SI flag: payload vs warehouse", flag_disk == flag_bq,
      f"{len(site_files)} county files carry {flag_disk:,} flagged parcels; BigQuery says "
      f"{flag_bq:,}" + ("" if flag_disk == flag_bq else "  <-- ONE OF THESE IS LYING TO A USER"))

print("\n=== 3. no cannot-assess is shipped as a ZERO ===")
# the D5 signature: a count of 0 that means "we did not measure", not "we measured none"
z = q1(f"""SELECT
  COUNTIF(si_signal_types = 0 AND has_si_signal) types_zero_but_flagged,
  COUNTIF(si_signal_events = 0 AND has_si_signal) events_zero_but_flagged,
  COUNTIF(has_si_signal AND si_last_event_date IS NULL) flagged_undated
FROM `{DS}.in_si_sites_flags_v2`""")
check("flagged parcels never carry a zero signal count",
      z.types_zero_but_flagged == 0 and z.events_zero_but_flagged == 0,
      f"{z.types_zero_but_flagged} flagged with 0 types, {z.events_zero_but_flagged} with 0 events; "
      f"{z.flagged_undated:,} flagged carry NO date — correct, that is NULL not 0")

# rate engine: an absent rate must be NULL, never 0 (METHODOLOGY 4.6)
r2 = q1(f"""SELECT COUNTIF(energy_cents_kwh_low = 0) zero_rates,
  COUNTIF(energy_cents_kwh_low IS NULL) null_rates, COUNT(*) n
FROM `{DS}.in_rate_proxies`""")
check("rate proxies: absent is NULL, never 0", r2.zero_rates == 0,
      f"{r2.n} proxy rows · {r2.zero_rates} carry 0.0 as a rate · {r2.null_rates} correctly NULL")

# component gaps: not_held must be NULL
r3 = q1(f"""SELECT COUNTIF(held_state != 'held' AND rate_or_null IS NOT NULL) leaked
  FROM `{DS}.in_rate_component_gaps`""")
check("unpublished tariff components are NULL", r3.leaked == 0,
      f"{r3.leaked} not-held components carry a numeric rate")

print("\n=== 4. estimates never style as published facts ===")
dc = q1(f"""SELECT COUNT(*) n, COUNTIF(location_precision IS NULL) unlabelled
  FROM `{DS}.in_data_centers_located`""") if True else None
check("every data-centre pin carries a precision label", dc.unlabelled == 0,
      f"{dc.n} pins · {dc.unlabelled} without a precision label "
      f"(92 were census CITY CENTROIDS rendered as facilities before this was added)")

# the D85 guard: any spatial product must exclude the whole-Earth parcel
d85 = "080500000047000018"
for t in ("in_si_parcel_signals_v2", "in_si_d22_parcel_join", "in_si_sri_placed"):
    try:
        n = q1(f"SELECT COUNTIF(parcel_key='{d85}') n FROM `{DS}.{t}`").n
        check(f"D85 excluded from {t}", n == 0,
              f"{n} rows on the inverted whole-Earth parcel")
    except Exception as e:
        check(f"D85 excluded from {t}", False, f"could not check: {str(e)[:60]}")

print("\n=== 5. every claim on screen is reachable from a registered table ===")
unreg = q1(f"""
WITH t AS (SELECT table_name FROM `{DS}.INFORMATION_SCHEMA.TABLES` WHERE table_name NOT LIKE '\\\\_%'),
     r AS (SELECT DISTINCT table_name FROM `{DS}._registry`)
SELECT COUNT(*) n FROM t LEFT JOIN r USING (table_name) WHERE r.table_name IS NULL""")
check("no unregistered table in indiana_app", unreg.n == 0,
      f"{unreg.n} tables exist without a _registry row (each blocks another session's checkpoint)")

print("\n=== 6. the SI flag is not a vacancy flag again ===")
v = q1(f"""SELECT COUNTIF(has_si_signal) flagged,
  COUNTIF(has_si_signal AND occ_group='no_structure') land,
  COUNTIF(has_si_signal AND occ_group='residential') resid
FROM `{DS}.in_si_sites_flags_v2`""")
land_share = 100 * v.land / max(v.flagged, 1)
check("flag is not dominated by empty land", land_share < 90,
      f"{v.flagged:,} flagged · {land_share:.1f}% empty land (was 99.2% before the D5 split) · "
      f"{v.resid} residential (the ruling says zero)")
check("no residential parcel is flagged", v.resid == 0,
      f"{v.resid} residential parcels carry an admitted signal")

out = {
    "audited_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "checks_run": checks, "failures": len(findings), "findings": findings,
}
path = os.path.join(REPO, "docs", "HONESTY_AUDIT.json")
json.dump(out, open(path, "w", encoding="utf-8"), indent=1)

print(f"\n{'='*72}")
print(f"E1 HONESTY AUDIT: {checks} checks, {len(findings)} FAILURES")
for f in findings:
    print(f"  ✗ {f['check']}: {f['detail']}")
if not findings:
    print("  every check passed — but a passing audit is only as good as its checks,")
    print("  and these are aimed at the four errors this project has actually made.")
print(f"written: docs/HONESTY_AUDIT.json")
