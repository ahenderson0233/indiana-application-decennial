"""Per-bus PJM WITHDRAWAL headroom (the DC-direction single number):
MIN(available_mw) over facilities the new load meaningfully stresses (|dfax|>=5%),
EXCLUDING pre-existing overloads (pre_loading>=100% — measured: every zero row is one;
they are disclosed per bus, not counted as the bus's headroom). 2027 RTEP Summer Peak."""
import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

client.query(f"""
CREATE OR REPLACE TABLE `{DS}.in_pjm_bus_withdrawal` AS
SELECT bus_number, ANY_VALUE(bus_label) AS bus_label, ANY_VALUE(bus_kv) AS bus_kv,
       MIN(IF(ABS(SAFE_CAST(dfax AS FLOAT64)) >= 0.05
              AND SAFE_CAST(pre_loading_pct AS FLOAT64) < 100,
              SAFE_CAST(available_mw AS FLOAT64), NULL)) AS withdrawal_mw,
       COUNTIF(SAFE_CAST(pre_loading_pct AS FLOAT64) >= 100) AS existing_overloads,
       COUNT(*) AS facilities,
       ARRAY_AGG(IF(ABS(SAFE_CAST(dfax AS FLOAT64)) >= 0.05
                    AND SAFE_CAST(pre_loading_pct AS FLOAT64) < 100, transmission_facility, NULL)
                 IGNORE NULLS ORDER BY SAFE_CAST(available_mw AS FLOAT64) ASC LIMIT 1)[OFFSET(0)] AS binding_facility,
       ANY_VALUE(case_label) AS case_label
FROM `{DS}.in_pjm_queuescope_aep`
WHERE operating_mode = 'WITHDRAWAL'
GROUP BY bus_number""").result()
st = list(client.query(f"""SELECT COUNT(*) buses, COUNTIF(withdrawal_mw > 0) positive,
    APPROX_QUANTILES(withdrawal_mw, 4) q FROM `{DS}.in_pjm_bus_withdrawal`"""))[0]
print("pjm withdrawal (gated):", dict(st))
client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES ('in_pjm_bus_withdrawal','in_pjm_queuescope_aep',
          'MIN(available_mw) per bus, WITHDRAWAL, dfax>=5pct, pre-existing overloads excluded+counted',
          {st.buses}, 0.02, CURRENT_TIMESTAMP(),
          '2027 RTEP Summer Peak; the DC-direction single number; measured: every zero row was a pre-existing overload')""").result()

wd = {int(r.bus_number): dict(r) for r in client.query(f"SELECT * FROM `{DS}.in_pjm_bus_withdrawal`")}
def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)
p = os.path.join(REPO, "data", "pjm.geojson.gz")
with gzip.open(p, "rt", encoding="utf-8") as f: fc = json.load(f)
n, cand = 0, 0
for ft in fc["features"]:
    pr = ft["properties"]
    if pr.get("layer") == "bus_candidate":
        cand += 1
        try:
            w = wd.get(int(float(pr.get("bus_number"))))
        except (TypeError, ValueError):
            w = None
        if w:
            pr["withdrawal_mw"] = float(w["withdrawal_mw"]) if w["withdrawal_mw"] is not None else None
            pr["wd_binding"] = w["binding_facility"]; pr["wd_existing_overloads"] = w["existing_overloads"]
            pr["wd_case"] = w["case_label"]; n += 1
with gzip.open(p, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(fc, f, separators=(",", ":"), default=jd)
print(f"pjm.geojson.gz: withdrawal attached to {n} of {cand} located buses")
print("PJM WITHDRAWAL WIRING COMPLETE")
