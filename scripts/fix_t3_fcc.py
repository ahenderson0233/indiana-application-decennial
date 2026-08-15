"""T3 fix: real FCC county fields (measured schema): fixed = speed-tier UNIT COUNTS by
technology (area_data_type='Total' rows only, no double count); mobile = 5G area pct."""
import json, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")
def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)

with open(os.path.join(REPO, "data", "county_context.json"), encoding="utf-8") as f:
    ctx = json.load(f)
n = 0
for r in client.query(f"""
SELECT geography_id AS fips,
  SUM(SAFE_CAST(total_units AS FLOAT64)) AS units,
  SUM(IF(LOWER(technology) LIKE '%fiber%', SAFE_CAST(total_units AS FLOAT64), 0)) AS fiber_units,
  SUM(SAFE_CAST(speed_1000_100 AS FLOAT64)) AS gig_units
FROM `{DS}.in_fcc_bdc_fixed_summary_by_geography`
WHERE geography_type='County' AND area_data_type='Total' AND biz_res='B'
GROUP BY 1"""):
    d = dict(r); fips = d.pop("fips")
    if fips in ctx["by_fips"]:
        ctx["by_fips"][fips]["fcc"] = {k: int(v or 0) for k, v in d.items()}
        n += 1
m = 0
for r in client.query(f"""
SELECT geography_id AS fips,
  ROUND(AVG(SAFE_CAST(mobilebb_5g_spd1_area_st_pct AS FLOAT64))*100,1) AS pct_5g_area
FROM `{DS}.in_fcc_bdc_mobile_summary`
WHERE geography_type='County' AND area_data_type='Total' GROUP BY 1"""):
    if r.fips in ctx["by_fips"]:
        ctx["by_fips"][r.fips].setdefault("fcc", {})["pct_5g_area"] = r.pct_5g_area
        m += 1
with open(os.path.join(REPO, "data", "county_context.json"), "w", encoding="utf-8") as f:
    json.dump(ctx, f, separators=(",", ":"), default=jd)
print(f"T3 fixed: business fixed-broadband units for {n} counties, 5G pct for {m}")
