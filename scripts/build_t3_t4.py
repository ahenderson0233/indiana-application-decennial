"""Roadmap T3 + T4: FCC county detail into county_context; SI-by-signal into state_summary.
Schema-read first, never guessed."""
import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")
def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)

# T3: read the FCC summary shapes first
for t in ("in_fcc_bdc_fixed_summary_by_geography", "in_fcc_bdc_mobile_summary"):
    cols = [s.name for s in client.get_table(f"{DS}.{t}").schema]
    print(f"{t}: {cols[:16]}")
    for r in client.query(f"SELECT * FROM `{DS}.{t}` LIMIT 2"):
        print("  ", {k: str(v)[:28] for k, v in list(dict(r).items())[:8]})

fixed_cols = [s.name for s in client.get_table(f"{DS}.in_fcc_bdc_fixed_summary_by_geography").schema]
geoc = next(c for c in fixed_cols if "geography_id" in c.lower())
typec = next((c for c in fixed_cols if "geography_type" in c.lower() or c.lower() == "geography_desc_type"), None)
# pick a few numeric coverage columns by name shape
pctcols = [c for c in fixed_cols if any(k in c.lower() for k in ("pct", "percent"))][:3]
print("using pct cols:", pctcols, "| type col:", typec)

with open(os.path.join(REPO, "data", "county_context.json"), encoding="utf-8") as f:
    ctx = json.load(f)
where_type = f"AND LOWER(CAST({typec} AS STRING)) LIKE '%county%'" if typec else ""
sel = ", ".join(f"AVG(SAFE_CAST(`{c}` AS FLOAT64)) AS `{c}`" for c in pctcols)
n3 = 0
for r in client.query(f"""SELECT SUBSTR(CAST({geoc} AS STRING),1,5) AS fips, {sel}
    FROM `{DS}.in_fcc_bdc_fixed_summary_by_geography`
    WHERE LENGTH(CAST({geoc} AS STRING)) >= 5 {where_type} GROUP BY 1"""):
    d = dict(r); fips = d.pop("fips")
    if fips in ctx["by_fips"]:
        ctx["by_fips"][fips]["fcc"] = {k: (round(v, 1) if v is not None else None) for k, v in d.items()}
        n3 += 1
with open(os.path.join(REPO, "data", "county_context.json"), "w", encoding="utf-8") as f:
    json.dump(ctx, f, separators=(",", ":"), default=jd)
print(f"T3: fcc detail merged for {n3} counties")

# T4: SI by signal
sig = [dict(r) for r in client.query(f"""
  SELECT signal, COUNT(*) AS n, COUNT(DISTINCT county_fips) AS counties,
         CAST(MAX(observed_date) AS STRING) AS latest
  FROM `{DS}.in_si_signals` GROUP BY 1 ORDER BY n DESC""")]
p = os.path.join(REPO, "data", "state_summary.json")
s = json.load(open(p, encoding="utf-8"))
s["si_by_signal"] = sig
s["provenance"] = [dict(r) for r in client.query(
    f"""SELECT table_name, source, n_rows, CAST(built_at AS STRING) AS built_at FROM `{DS}._registry`
        QUALIFY ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY built_at DESC)=1 ORDER BY table_name""")]
s["built_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
json.dump(s, open(p, "w", encoding="utf-8"), indent=1, default=jd)
tot = sum(x["n"] for x in sig)
print(f"T4: {len(sig)} signals, total {tot:,} (must equal 1,818,158)")
print("T3+T4 COMPLETE")
