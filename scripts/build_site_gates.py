"""Per-parcel environmental gate columns for the rendered class union (1.2M parcels),
then re-export data/sites/*.geojson.gz with the gate props merged.

Gates (P4 risk + benefit, P4b): sfha_flood BOOL, wetland_on_parcel BOOL, protected_land BOOL,
bonus_kinds STRING. NULL = cannot assess (no gate data intersecting the county's coverage);
FALSE = measured-and-clear. County-grain fibre/water stay in county context.
"""
import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

sql = f"""
CREATE OR REPLACE TABLE `{DS}.in_site_gates` AS
WITH cls AS (
  SELECT parcel_source, parcel_key, parcel_geog
  FROM `{DS}.in_sites`
  WHERE parcel_geog IS NOT NULL
    AND (occ_group='ci' OR mw_datacenter_4_per_acre>=25 OR has_si_signal)
),
fl AS (
  SELECT c.parcel_source, c.parcel_key, LOGICAL_OR(f.SFHA_TF='T') AS sfha
  FROM cls c JOIN `{DS}.in_flood` f ON ST_INTERSECTS(c.parcel_geog, f.geog)
  GROUP BY 1,2),
we AS (
  SELECT c.parcel_source, c.parcel_key, TRUE AS wet
  FROM cls c JOIN `{DS}.in_wetlands` w ON ST_INTERSECTS(c.parcel_geog, w.geog)
  GROUP BY 1,2),
pa AS (
  SELECT c.parcel_source, c.parcel_key, TRUE AS prot
  FROM cls c JOIN `{DS}.in_padus` p ON ST_INTERSECTS(c.parcel_geog, p.geog)
  GROUP BY 1,2),
bo AS (
  SELECT c.parcel_source, c.parcel_key, STRING_AGG(DISTINCT b.kind, ',') AS bonus_kinds
  FROM cls c JOIN `{DS}.in_bonus_geo` b ON b.geog IS NOT NULL AND ST_INTERSECTS(c.parcel_geog, b.geog)
  GROUP BY 1,2)
SELECT c.parcel_source, c.parcel_key,
       IFNULL(fl.sfha, FALSE) AS sfha_flood,
       IFNULL(we.wet, FALSE) AS wetland_on_parcel,
       IFNULL(pa.prot, FALSE) AS protected_land,
       bo.bonus_kinds
FROM cls c
LEFT JOIN fl USING (parcel_source, parcel_key)
LEFT JOIN we USING (parcel_source, parcel_key)
LEFT JOIN pa USING (parcel_source, parcel_key)
LEFT JOIN bo USING (parcel_source, parcel_key)
"""
dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
print(f"gates dry-run: {dry.total_bytes_processed/1e9:.1f} GB", flush=True)
client.query(sql).result()
stats = list(client.query(f"""
  SELECT COUNT(*) AS n, COUNTIF(sfha_flood) AS sfha, COUNTIF(wetland_on_parcel) AS wet,
         COUNTIF(protected_land) AS prot, COUNTIF(bonus_kinds IS NOT NULL) AS bonus
  FROM `{DS}.in_site_gates`"""))[0]
print(f"gates: {dict(stats)}", flush=True)
client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES ('in_site_gates','in_sites x in_flood/in_wetlands/in_padus/in_bonus_geo',
          'per-parcel ST_INTERSECTS gates, class union', {stats.n}, {dry.total_bytes_processed/1e9:.3f},
          CURRENT_TIMESTAMP(), 'FALSE = measured clear; joined only for class-union parcels')""").result()

# re-export site files with gates merged
def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)
def rc(x):
    if isinstance(x, float): return round(x, 7)
    if isinstance(x, list): return [rc(v) for v in x]
    return x

q = f"""
SELECT sc.county_fips, s.* EXCEPT(parcel_geog), g.sfha_flood, g.wetland_on_parcel,
       g.protected_land, g.bonus_kinds, ST_ASGEOJSON(s.parcel_geog) AS gj
FROM `{DS}.in_sites` s
JOIN `{DS}.in_sites_county` sc USING (parcel_source, parcel_key)
LEFT JOIN `{DS}.in_site_gates` g USING (parcel_source, parcel_key)
WHERE s.occ_group='ci' OR s.mw_datacenter_4_per_acre>=25 OR s.has_si_signal
ORDER BY sc.county_fips"""
it = client.query(q).result(page_size=20000)
cur, buf, files, total = None, [], 0, 0
def flush(fips, buf):
    with gzip.open(os.path.join(REPO, "data", "sites", f"{fips}.geojson.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
        json.dump({"type": "FeatureCollection", "features": buf}, f, separators=(",", ":"), default=jd)
    print(f"  {fips}: {len(buf):,}", flush=True)
for r in it:
    d = dict(r); fips = d.pop("county_fips"); gj = d.pop("gj")
    if gj is None: continue
    if fips != cur and cur is not None:
        flush(cur, buf); files += 1; buf = []
    cur = fips
    buf.append({"type": "Feature", "properties": d, "geometry": rc(json.loads(gj))})
    total += 1
if buf: flush(cur, buf); files += 1
print(f"RE-EXPORT COMPLETE: {files} counties, {total:,} features", flush=True)
