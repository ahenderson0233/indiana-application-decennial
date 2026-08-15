"""Re-clip in_sites now that vw_parcel_sites carries the EXACT building/outdoor space
calculation (mat_parcel_outdoor_exact: parcel - measured footprint intersection).
Measures exact-vs-approximate delta before anything renders."""
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

sql = f"""CREATE OR REPLACE TABLE `{DS}.in_sites` AS
SELECT * FROM `energy-platfrom.energy.vw_parcel_sites` WHERE state='IN'"""
dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
client.query(sql).result()
st = list(client.query(f"""
SELECT COUNT(*) n, COUNTIF(exact_outdoor_acres IS NOT NULL) with_exact,
       COUNTIF(mw_datacenter_4_per_acre_exact >= 25) ge25_exact,
       COUNTIF(mw_datacenter_4_per_acre >= 25) ge25_approx,
       ROUND(AVG(ABS(IFNULL(exact_outdoor_acres,0) - IFNULL(outdoor_acres,0))),2) avg_delta_acres
FROM `{DS}.in_sites`"""))[0]
print("re-clip:", dict(st))
client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES ('in_sites','energy.vw_parcel_sites (now incl. mat_parcel_outdoor_exact)',
          'RE-CLIP with exact building/outdoor columns', {st.n},
          {dry.total_bytes_processed/1e9:.3f}, CURRENT_TIMESTAMP(),
          'exact coverage {st.with_exact} of {st.n}; ge25MW exact {st.ge25_exact} vs approx {st.ge25_approx}')""").result()
print("registered")
