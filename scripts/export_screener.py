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
    SELECT *, ROW_NUMBER() OVER (PARTITION BY county_fips ORDER BY mw_dc DESC) AS rk
    FROM `{DS}.in_screener_candidates`
    WHERE county_fips IS NOT NULL
  )
  SELECT parcel_source, parcel_key, county_fips, county_name, occ_group, site_kind,
         structure_count, parcel_acres, exact_parcel_acres, outdoor_acres, exact_outdoor_acres,
         mw_dc, mw_bess, lat, lon,
         has_signal, signals, signal_types, signal_events,
         CAST(first_event AS STRING) AS first_event, CAST(last_event AS STRING) AS last_event,
         events_3y, events_5y, events_10y, keying,
         sfha_flood, wetland_on_parcel, protected_land, bonus_kinds,
         inj_bus, inj_kv, inj_mw, inj_mw_worst, inj_mw_best, inj_binding, inj_mi,
         wd_bus, wd_kv, wd_mw, wd_binding, wd_conf, wd_mi,
         sub_name, sub_kv, sub_mi
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
    "direction_note": ("Injection = what a GENERATOR can push into the bus (MISO publishes this). "
                       "Withdrawal = what a LOAD can pull out (PJM publishes this). A data centre "
                       "is load. These are different questions, not two measures of one thing."),
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
