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

print("\n=== 7. every committed LOADER actually landed its table ===")
# THE FAILURE THIS CATCHES, in full, because it cost 13 counties and was invisible for a day:
# `scrapers/lane_f/pull_dc_actions_county.py` was committed at 13:42 on 2026-08-16. The table it
# writes, `in_dc_actions_county_v2`, did not exist. The session reported "everything committed and
# pushed" and it was TRUE of the repo — but this project's .gitignore excludes `scrapers/**/*.json`
# by design, so the sweep's 388 KB of acquired data could never enter a commit, and `git add` on
# explicitly-named paths never warns about a file you did not name. A clean tree was read as
# "the work is safe" when it only ever meant "everything git tracks".
#
# So: a committed loader whose table does not exist is an UNFINISHED ACQUISITION. For a scraper,
# "committed" and "safe" are different properties, and only the warehouse proves the second one.
registered = {r.table_name for r in client.query(
    f"SELECT DISTINCT table_name FROM `{DS}._registry`")}

WRITES = ("load_table_from_json", "WRITE_TRUNCATE", "CREATE OR REPLACE TABLE",
          "load_table_from_dataframe")
# a table name as it appears in a string literal: in_foo, vw_foo, or the _meta convention
NAME = re.compile(r"""['"`]([a-z_][a-z0-9_]{3,})['"`]""")
PREFIX = ("in_", "vw_", "_ind")

unlanded, writers = [], 0
for p in sorted(glob.glob(os.path.join(REPO, "scrapers", "**", "*.py"), recursive=True) +
                glob.glob(os.path.join(REPO, "scripts", "*.py"))):
    src = open(p, encoding="utf-8", errors="ignore").read()
    if not any(w in src for w in WRITES):
        continue                      # a probe or a reader, not a loader — nothing to land
    named = {m for m in NAME.findall(src) if m.startswith(PREFIX)}
    # `_load("in_x", ...)` style helpers put the name in a variable; catch the f-string form too
    named |= {m for m in re.findall(r"\{DS\}\.([a-z_][a-z0-9_]{3,})", src)
              if m.startswith(PREFIX)}
    # A trailing underscore means this is an f-string PREFIX FRAGMENT (`f"in_si_{slug}"`), not a
    # table. Lane C and Lane D's util modules build names that way, and counting them as claims
    # made this check fail on two loaders that had in fact landed everything they wrote.
    named = {m for m in named if not m.endswith("_")}
    if not named:
        continue                      # writes to a name we cannot resolve statically; not a claim
    writers += 1
    if not (named & registered):
        unlanded.append((os.path.relpath(p, REPO).replace("\\", "/"), sorted(named)[:4]))

check("every committed loader has a table in _registry", not unlanded,
      f"{writers} loaders scanned · {len(unlanded)} name only tables that DO NOT EXIST"
      + ("".join(f"\n         !! {f} -> {n}" for f, n in unlanded) if unlanded else
         " — no unfinished acquisition is sitting in the repo pretending to be done"))

out = {
    "audited_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "checks_run": checks, "failures": len(findings), "findings": findings,
}
path = os.path.join(REPO, "docs", "HONESTY_AUDIT.json")
json.dump(out, open(path, "w", encoding="utf-8"), indent=1)

print(f"\n{'='*72}")
print(f"E1 HONESTY AUDIT: {checks} checks, {len(findings)} FAILURES")
for f in findings:
    # ASCII deliberately. This line used a Unicode cross and the Windows console is cp1252, so
    # the audit CRASHED on the one path that matters -- reporting its own failures. An audit that
    # only survives when it passes is not an audit.
    print(f"  FAIL: {f['check']}: {f['detail']}")
if not findings:
    print("  every check passed — but a passing audit is only as good as its checks,")
    print("  and these are aimed at the four errors this project has actually made.")
print(f"written: docs/HONESTY_AUDIT.json")
