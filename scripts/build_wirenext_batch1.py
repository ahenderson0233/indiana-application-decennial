"""WIRE-NEXT batch 1: clip the audit queue into indiana_app using each table's MEASURED
key column from _indiana_census (never a guessed predicate). Registers everything.
Also attaches ferc714_state_demand to the Market payload (Indiana demand series)."""
import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
E = "`energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")

TARGETS = ["ferc714_state_demand", "nhd_waterbody", "spc_severe_events", "faa_obstacles",
           "echo_cwa_facilities", "utility_tariff_riders", "dc_eei_tariffs",
           "econ_gjf_megadeals", "state_irp_catalog", "gov_auction_gsa", "ustp_ch7_tfr",
           "queue_miso", "nfirs_basicincident_2024", "nfirs_incidentaddress_2024",
           "nfirs_basicincident_2023", "nfirs_incidentaddress_2023",
           "nfirs_basicincident_2022", "nfirs_incidentaddress_2022"]
keys = {r.table_id: (r.method, r.key_column) for r in client.query(
    f"""SELECT table_id, method, key_column FROM `{DS}._indiana_census`
        WHERE in_rows > 0 AND table_id IN UNNEST({TARGETS!r})""")}

def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)

for t in TARGETS:
    if t not in keys:
        print(f"SKIP {t}: not Indiana-positive in census"); continue
    method, col = keys[t]
    pred = (f"UPPER(CAST(`{col}` AS STRING)) IN ('IN','INDIANA','18')" if method == "state"
            else f"STARTS_WITH(CAST(`{col}` AS STRING), '18')")
    dest = "in_" + t
    sql = f"CREATE OR REPLACE TABLE `{DS}.{dest}` AS SELECT * FROM {E}.{t}` WHERE {pred}"
    dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
    client.query(sql).result()
    n = list(client.query(f"SELECT COUNT(*) AS n FROM `{DS}.{dest}`"))[0].n
    client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
      VALUES ('{dest}','energy.{t}','census-keyed clip ({method}:{col})', {n},
              {dry.total_bytes_processed/1e9:.3f}, CURRENT_TIMESTAMP(),
              'WIRE-NEXT batch 1 - subject read pending per audit protocol')""").result()
    print(f"{dest}: {n:,} rows")

# attach the Indiana demand series to the Market payload (schema-read, not guessed)
cols = [s.name for s in client.get_table("energy-platfrom.energy.ferc714_state_demand").schema]
print("ferc714_state_demand cols:", cols[:14])
datec = next((c for c in cols if "date" in c.lower() or "hour" in c.lower() or "time" in c.lower()), None)
mwc = next((c for c in cols if "mw" in c.lower() or "demand" in c.lower() or "load" in c.lower()), None)
if datec and mwc:
    series = [dict(r) for r in client.query(f"""
      SELECT DATE_TRUNC(DATE({datec}), MONTH) AS month,
             ROUND(SUM(SAFE_CAST({mwc} AS FLOAT64)),0) AS demand_mwh
      FROM `{DS}.in_ferc714_state_demand` GROUP BY 1 ORDER BY 1""")]
    p = os.path.join(REPO, "data", "market.json.gz")
    with gzip.open(p, "rt", encoding="utf-8") as f: market = json.load(f)
    market["state_demand"] = series
    with gzip.open(p, "wt", encoding="utf-8", compresslevel=6) as f:
        json.dump(market, f, separators=(",", ":"), default=jd)
    print(f"market.json state_demand: {len(series)} months")
else:
    print(f"ferc714 attach deferred: date/mw columns not identifiable mechanically ({cols[:10]})")

# provenance refresh
p = os.path.join(REPO, "data", "state_summary.json")
summary = json.load(open(p, encoding="utf-8"))
summary["provenance"] = [dict(r) for r in client.query(
    f"""SELECT table_name, source, n_rows, CAST(built_at AS STRING) AS built_at FROM `{DS}._registry`
        QUALIFY ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY built_at DESC)=1 ORDER BY table_name""")]
summary["built_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
json.dump(summary, open(p, "w", encoding="utf-8"), indent=1, default=jd)
print("provenance:", len(summary["provenance"]))
print("WIRE-NEXT BATCH 1 COMPLETE")
