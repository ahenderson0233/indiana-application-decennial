"""P3-P6 wiring: parcel owner/zoning attrs (measured join), seismic, EIA-861 utilities, URDB tariffs.
  BQ: in_parcel_attrs, in_seismic, in_eia861_territory, in_urdb_rates (registered)
  data/attrs/{fips}.json.gz  parcel_key -> [owner, owner_class, zoning, land_use, year_built, assessed_value]
  data/county_context.json   + seismic design category + utilities-serving count
  data/market.json.gz        + Indiana tariff table (URDB)
"""
import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
E = "`energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")

def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)
def reg(name, source, method, n, gb, notes=""):
    client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
      VALUES ('{name}','{source}','{method}', {n}, {gb:.3f}, CURRENT_TIMESTAMP(), '{notes}')""").result()

# 1) MEASURE the attrs join before believing it (apn_key vs the spine parcel_key)
jr = list(client.query(f"""
SELECT COUNT(*) AS class_parcels,
       COUNTIF(a.apn_key IS NOT NULL) AS with_attrs,
       COUNTIF(a.parcel_owner IS NOT NULL) AS with_owner
FROM (SELECT parcel_source, parcel_key FROM `{DS}.in_sites`
      WHERE occ_group='ci' OR mw_datacenter_4_per_acre>=25 OR has_si_signal) s
LEFT JOIN (SELECT * FROM {E}.mat_parcel_attrs` WHERE state='IN') a
  ON a.parcel_source = s.parcel_source AND a.apn_key = s.parcel_key"""))[0]
rate = jr.with_attrs / jr.class_parcels * 100
print(f"attrs join: {jr.with_attrs:,}/{jr.class_parcels:,} = {rate:.1f}% (owner on {jr.with_owner:,})")

sql = f"""
CREATE OR REPLACE TABLE `{DS}.in_parcel_attrs` AS
SELECT s.parcel_source, s.parcel_key, sc.county_fips,
       a.parcel_owner, a.owner_class, a.zoning, a.land_use, a.year_built, a.assessed_value
FROM (SELECT parcel_source, parcel_key FROM `{DS}.in_sites`
      WHERE occ_group='ci' OR mw_datacenter_4_per_acre>=25 OR has_si_signal) s
JOIN `{DS}.in_sites_county` sc USING (parcel_source, parcel_key)
JOIN (SELECT * FROM {E}.mat_parcel_attrs` WHERE state='IN') a
  ON a.parcel_source = s.parcel_source AND a.apn_key = s.parcel_key"""
dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
client.query(sql).result()
n = list(client.query(f"SELECT COUNT(*) AS n FROM `{DS}.in_parcel_attrs`"))[0].n
reg("in_parcel_attrs", "energy.mat_parcel_attrs x in_sites", "apn_key join, measured", n,
    dry.total_bytes_processed/1e9, f"join rate {rate:.1f}pct of class parcels - shown in panel")
print(f"in_parcel_attrs: {n:,}")

os.makedirs(os.path.join(REPO, "data", "attrs"), exist_ok=True)
it = client.query(f"""SELECT county_fips, parcel_key, parcel_owner, owner_class, zoning,
    land_use, year_built, assessed_value FROM `{DS}.in_parcel_attrs`
    ORDER BY county_fips""").result(page_size=20000)
cur, buf, files = None, {}, 0
def flush(fips, buf):
    with gzip.open(os.path.join(REPO, "data", "attrs", f"{fips}.json.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
        json.dump(buf, f, separators=(",", ":"), default=jd)
for r in it:
    if r.county_fips != cur and cur is not None:
        flush(cur, buf); files += 1; buf = {}
    cur = r.county_fips
    buf[r.parcel_key] = [r.parcel_owner, r.owner_class, r.zoning, r.land_use, r.year_built, r.assessed_value]
if buf: flush(cur, buf); files += 1
print(f"attrs files: {files} counties")

# 2) seismic (county grain)
client.query(f"""CREATE OR REPLACE TABLE `{DS}.in_seismic` AS
  SELECT * FROM {E}.seismic_design` WHERE STARTS_WITH(geoid,'18')""").result()
n = list(client.query(f"SELECT COUNT(*) AS n FROM `{DS}.in_seismic`"))[0].n
reg("in_seismic", "energy.seismic_design", "geoid prefix 18", n, 0.01)
print(f"in_seismic: {n}")

# 3) EIA-861 utilities per county
client.query(f"""CREATE OR REPLACE TABLE `{DS}.in_eia861_territory` AS
  SELECT * FROM {E}.eia861_service_territory` WHERE state='IN'""").result()
n = list(client.query(f"SELECT COUNT(*) AS n FROM `{DS}.in_eia861_territory`"))[0].n
reg("in_eia861_territory", "energy.eia861_service_territory", "state=IN", n, 0.02)
print(f"in_eia861_territory: {n:,}")

# 4) URDB Indiana tariffs
client.query(f"""CREATE OR REPLACE TABLE `{DS}.in_urdb_rates` AS
  SELECT * FROM {E}.urdb_rates`
  WHERE REGEXP_CONTAINS(LOWER(utility), r'indiana|nipsco|vectren|hoosier|indianapolis|duke energy ind')""").result()
n = list(client.query(f"SELECT COUNT(*) AS n FROM `{DS}.in_urdb_rates`"))[0].n
reg("in_urdb_rates", "energy.urdb_rates", "Indiana-named utilities (regex, disclosed)", n, 0.01,
    "floor - a utility not name-matching Indiana is missed; territory join is the upgrade")
print(f"in_urdb_rates: {n}")

# 5) merge into county_context + market
with open(os.path.join(REPO, "data", "county_context.json"), encoding="utf-8") as f:
    ctx = json.load(f)
for r in client.query(f"""SELECT geoid, ANY_VALUE(sdc) AS sdc, ANY_VALUE(site_class) AS site_class
    FROM `{DS}.in_seismic` GROUP BY 1"""):
    if r.geoid in ctx["by_fips"]: ctx["by_fips"][r.geoid]["seismic"] = {"sdc": r.sdc, "site_class": r.site_class}
for r in client.query(f"""SELECT county_id_fips, COUNT(DISTINCT utility_id_eia) AS utilities,
    MAX(CAST(report_date AS STRING)) AS asof FROM `{DS}.in_eia861_territory` GROUP BY 1"""):
    if r.county_id_fips in ctx["by_fips"]:
        ctx["by_fips"][r.county_id_fips]["eia861"] = {"utilities": r.utilities, "asof": r.asof}
with open(os.path.join(REPO, "data", "county_context.json"), "w", encoding="utf-8") as f:
    json.dump(ctx, f, separators=(",", ":"), default=jd)

with gzip.open(os.path.join(REPO, "data", "market.json.gz"), "rt", encoding="utf-8") as f:
    market = json.load(f)
market["tariffs"] = [dict(r) for r in client.query(f"""
  SELECT utility, name, sector, rate_type, has_demand_charge,
         energy_rate_min_usd_kwh, energy_rate_max_usd_kwh, demand_rate_max_usd_kw,
         CAST(startdate AS STRING) AS startdate
  FROM `{DS}.in_urdb_rates`
  WHERE LOWER(sector) IN ('commercial','industrial')
  ORDER BY utility, name""")]
market["attrs_join_rate_pct"] = round(rate, 1)
with gzip.open(os.path.join(REPO, "data", "market.json.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(market, f, separators=(",", ":"), default=jd)
print(f"tariffs in market.json: {len(market['tariffs'])}")
print("P36 WIRING COMPLETE")
