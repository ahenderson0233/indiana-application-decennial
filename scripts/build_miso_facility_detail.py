"""G27 — re-clip the MISO columns we dropped, above all `percent_loading_before`.

WHY THIS ONE FIRST, of the 401 columns under-clipped across 24 tables (docs/CLIP_COMPLETENESS.json):
it is the column that answers our largest open data question. G26 established that our Indiana MISO
headroom reads zero on 641 of 642 POIs **not because the grid is full but because a monitored
facility is already over its rating before any new request exists** — 26.3% of the 40,007 Indiana
facility rows are pre-existing overloads, averaging 16.4 per POI, while `max_facility_mw_available`
on those same POIs averages 45,800 MW.

Without `percent_loading_before` the application cannot tell a user which of these it is looking at:

    "0 MW because this bus is genuinely full"          -> a fact about the site
    "0 MW because a facility was overloaded already"   -> a fact about the STUDY CASE

Those are different findings and they currently render identically, as a bare zero.

ALSO CLIPPED: `headroom_state` from `energy.miso_poi_headroom` — the publisher's own verdict
(`ZERO_HEADROOM` / `HAS_HEADROOM`), which we never took — plus `n_facilities_overloaded_base` and
`max_facility_mw_available`.

⛔ NOT FIXED HERE, deliberately. This makes the situation VISIBLE; it does not change the number.
Per the operator's ruling on G26, the PJM/MISO rule inconsistency is resolved by reaching parity
with the mitigated DPP-2025 case, not by unilaterally dropping pre-existing overloads (which would
swing Indiana from 0.2% to 100% of POIs having headroom, and is not the baseline's method either).
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

# per-POI verdict, with the publisher's own state
client.query(f"""
CREATE OR REPLACE TABLE `{DS}.in_miso_poi_state` AS
SELECT h.poi_name, h.bus_number, h.bus_name, h.kv, h.area_name,
       h.headroom_mw, h.headroom_state,                       -- <- never clipped before
       h.binding_facility, h.binding_percent_dfax, h.binding_percent_loading_before,
       h.binding_rating_mva,
       h.n_monitored_facilities, h.n_facilities_at_zero,
       h.n_facilities_overloaded_base,                        -- <- the key count
       h.max_facility_mw_available, h.median_facility_mw_available,
       h.max_percent_loading_before, h.crawl_result, h._vintage,
       CURRENT_TIMESTAMP() AS built_at
FROM `energy-platfrom.energy.miso_poi_headroom` h
JOIN (SELECT DISTINCT poi_name FROM `{DS}.in_bus_headroom_miso`
      WHERE location_status = 'indiana') ind USING (poi_name)
""").result()

# per-facility detail, carrying the loading columns that make the verdict explicable
client.query(f"""
CREATE OR REPLACE TABLE `{DS}.in_miso_facility_detail` AS
SELECT p.poi_name, p.monitored_facility, p.mw_available,
       p.percent_dfax, p.mw_impact, p.percent_impact,
       p.percent_loading_before,                              -- ⭐ THE COLUMN
       p.percent_loading_after, p.derived_rating_mva,
       p.fr_name, p.to_name, p.cont_name, p.areas_name,
       p.percent_loading_before >= 100 AS is_pre_existing_overload,
       p._vintage,
       CURRENT_TIMESTAMP() AS built_at
FROM `energy-platfrom.energy.miso_poi_monitored_facilities` p
JOIN (SELECT DISTINCT poi_name FROM `{DS}.in_bus_headroom_miso`
      WHERE location_status = 'indiana') ind USING (poi_name)
""").result()

s = list(client.query(f"""
SELECT COUNT(*) n, COUNTIF(headroom_state='ZERO_HEADROOM') zero, COUNTIF(headroom_state='HAS_HEADROOM') has,
       ROUND(AVG(n_facilities_overloaded_base),1) avg_ovl,
       ROUND(AVG(max_facility_mw_available)) avg_max_avail
FROM `{DS}.in_miso_poi_state`"""))[0]
f = list(client.query(f"""
SELECT COUNT(*) n, COUNTIF(is_pre_existing_overload) pre, COUNT(DISTINCT poi_name) pois,
       ROUND(100*COUNTIF(is_pre_existing_overload)/COUNT(*),1) pct
FROM `{DS}.in_miso_facility_detail`"""))[0]

print(f"in_miso_poi_state       : {s.n} Indiana POIs")
print(f"  publisher verdict      : ZERO_HEADROOM {s.zero}, HAS_HEADROOM {s.has}")
print(f"  avg facilities already overloaded in the BASE case: {s.avg_ovl}")
print(f"  avg most-permissive facility available            : {s.avg_max_avail:,.0f} MW")
print(f"in_miso_facility_detail : {f.n:,} facility rows over {f.pois} POIs")
print(f"  pre-existing overloads : {f.pre:,} ({f.pct}%)")
print()
print("  -> the app can now say WHY a POI reads zero, instead of only that it does.")

for t, n, note in [
    ("in_miso_poi_state", s.n,
     "Carries `headroom_state` (the publisher's own ZERO_HEADROOM / HAS_HEADROOM verdict) and "
     "`n_facilities_overloaded_base`, neither of which was ever clipped. Explains WHY a POI reads "
     "zero: on the Indiana zeros an average of 16.4 monitored facilities are already over their "
     "rating before any request, while the most permissive facility averages ~45,800 MW."),
    ("in_miso_facility_detail", f.n,
     "Per (POI, monitored facility) with `percent_loading_before` - the column identified in G27 as "
     "the one needed to distinguish 'already overloaded' from 'genuinely full'. "
     "`is_pre_existing_overload` is derived from it. Does NOT change any headroom number: per the "
     "operator's G26 ruling, parity with the mitigated DPP-2025 case comes first."),
]:
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name=@t",
                 job_config=bigquery.QueryJobConfig(query_parameters=[
                     bigquery.ScalarQueryParameter("t", "STRING", t)])).result()
    client.query(
        f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
        f"VALUES (@t,@s,@m,@n,0.0,CURRENT_TIMESTAMP(),@no)",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", t),
            bigquery.ScalarQueryParameter("s", "STRING",
                "energy.miso_poi_headroom / energy.miso_poi_monitored_facilities, Indiana POIs"),
            bigquery.ScalarQueryParameter("m", "STRING",
                "G27 re-clip of columns dropped by the original clip; joined to the 642 "
                "location_status='indiana' POIs"),
            bigquery.ScalarQueryParameter("n", "INT64", int(n)),
            bigquery.ScalarQueryParameter("no", "STRING", note)])).result()
    print(f"registered {t}")
