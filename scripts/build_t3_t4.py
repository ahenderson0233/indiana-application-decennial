"""T3 + T4 (Opus roadmap items, done ahead):
T4: si_by_signal (signal, rows, counties, latest event) -> state_summary.json
T3: FCC fixed+mobile county-grain detail -> county_context.json (value-read first, never guessed)"""
import json, gzip, os, datetime, decimal, re
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)

# ---- T4: signal inventory ----
sig = [dict(r) for r in client.query(f"""
  SELECT signal, COUNT(*) AS n, COUNT(DISTINCT county_fips) AS counties,
         CAST(MAX(observed_date) AS STRING) AS latest
  FROM `{DS}.in_si_signals` GROUP BY 1 ORDER BY n DESC""")]
p = os.path.join(REPO, "data", "state_summary.json")
summary = json.load(open(p, encoding="utf-8"))
summary["si_by_signal"] = sig
print(f"si_by_signal: {len(sig)} signals, total {sum(s['n'] for s in sig):,}")

# ---- T3: FCC county detail (value-read the schemas first) ----
print("--- fixed summary sample:")
fixed_cols = [s.name for s in client.get_table(f"{DS}.in_fcc_bdc_fixed_summary_by_geography").schema]
for r in client.query(f"""SELECT * FROM `{DS}.in_fcc_bdc_fixed_summary_by_geography`
    WHERE LENGTH(CAST(geography_id AS STRING)) = 5 LIMIT 2"""):
    print("   ", {k: str(v)[:28] for k, v in list(dict(r).items())[:12]})
print("fixed cols:", fixed_cols[:20])
mob_cols = [s.name for s in client.get_table(f"{DS}.in_fcc_bdc_mobile_summary").schema]
print("mobile cols:", mob_cols[:16])

# GRAIN (measured, not guessed): fixed = geography x technology x biz_res x area_data_type.
# County slice: geography_type='County', area_data_type='Total', biz_res='B' (business),
# technologies Fiber and Cable kept distinctly. Values are SHARES 0..1 of total_units.
ctxp = os.path.join(REPO, "data", "county_context.json")
ctx = json.load(open(ctxp, encoding="utf-8"))
for v in ctx["by_fips"].values():  # replace, never accumulate (stale keys from a prior grain-bug merge)
    v.pop("fcc", None); v.pop("fcc_mobile", None)
merged_f = merged_m = 0
for r in client.query(f"""
    SELECT CAST(geography_id AS STRING) AS fips, technology,
           SAFE_CAST(total_units AS INT64) AS units,
           SAFE_CAST(speed_100_20 AS FLOAT64) AS pct_100_20,
           SAFE_CAST(speed_1000_100 AS FLOAT64) AS pct_gig
    FROM `{DS}.in_fcc_bdc_fixed_summary_by_geography`
    WHERE geography_type='County' AND area_data_type='Total' AND biz_res='B'
      AND technology IN ('Fiber','Cable')"""):
    if r.fips in ctx["by_fips"]:
        # shape matches the app's pre-wired rendering: units / fiber_units / gig_units
        f = ctx["by_fips"][r.fips].setdefault("fcc", {})
        f["units"] = r.units
        if r.technology == "Fiber":
            f["fiber_units"] = int(round((r.pct_100_20 or 0) * (r.units or 0)))
            f["gig_units"] = int(round((r.pct_gig or 0) * (r.units or 0)))
        else:
            f["cable_100_20_units"] = int(round((r.pct_100_20 or 0) * (r.units or 0)))
        merged_f += 1
for r in client.query(f"""
    SELECT CAST(geography_id AS STRING) AS fips,
           SAFE_CAST(mobilebb_4g_area_st_pct AS FLOAT64) AS pct_4g,
           SAFE_CAST(mobilebb_5g_spd1_area_st_pct AS FLOAT64) AS pct_5g
    FROM `{DS}.in_fcc_bdc_mobile_summary`
    WHERE area_data_type='Total' AND LENGTH(CAST(geography_id AS STRING)) = 5"""):
    if r.fips in ctx["by_fips"]:
        ctx["by_fips"][r.fips]["fcc_mobile"] = {"pct_4g": r.pct_4g, "pct_5g": r.pct_5g}
        merged_m += 1
json.dump(ctx, open(ctxp, "w", encoding="utf-8"), separators=(",", ":"), default=jd)
print(f"FCC merged: fixed rows {merged_f}, mobile rows {merged_m}")

summary["built_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
json.dump(summary, open(p, "w", encoding="utf-8"), indent=1, default=jd)
print("T3+T4 DATA COMPLETE")
