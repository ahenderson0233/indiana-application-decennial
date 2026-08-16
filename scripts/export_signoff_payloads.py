"""Export the seven sign-off tables into the app's payloads.

  data/signoff.json.gz          NEW - D11/D25/D27 admitted rows, cloudscene cross-check,
                                queue_miso extras, and the admitted-vs-source denominators
  data/county_context.json      IOCS county context merged onto each county (replace, never
                                accumulate - the T3 grain bug was caused by accumulating)
  data/facilities.geojson.gz    the DC layer re-pointed at in_data_centers_deduped, carrying
                                unnamed_cannot_dedupe so possible duplicates stay visible

Read-only against BigQuery. Idempotent. Run after scripts/build_signoff_wiring.py.
"""
# stdout must survive its own output: this console is cp1252 and characters like U+2248/U+2192/U+2717 raise
# UnicodeEncodeError from print() itself. The honesty audit once crashed on its own
# FAILURE path for exactly this reason. Degrade the glyph, never the run.
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import json, gzip, os, datetime, decimal
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

def jd(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, decimal.Decimal): return float(o)
    return str(o)
def rows(sql): return [dict(r) for r in client.query(sql)]

out = {}

# ---- D11 / D25 / D27 admitted, with the denominators that make admission legible ----
out["d11"] = rows(f"""SELECT entity_name, raw_status, status_family,
    CAST(observed_date AS STRING) observed_date, address_line, city, zip
  FROM `{DS}.in_si_d11_admitted` ORDER BY observed_date DESC LIMIT 1200""")
out["d25"] = rows(f"""SELECT docket, docket_title, filing_type,
    CAST(filed_date_parsed AS STRING) filed_date, filed_for, state_count_in_docket, pdf_url
  FROM `{DS}.in_si_d25_admitted` ORDER BY filed_date_parsed DESC""")
out["d27"] = rows(f"""SELECT debtor_name, raw_filing_type, CAST(lapse_date AS STRING) lapse_date,
    CAST(filing_date AS STRING) filing_date, address_line, city, zip, keying, quality_mult
  FROM `{DS}.in_si_d27_admitted` ORDER BY lapse_date DESC""")
out["cloudscene"] = rows(f"""SELECT name, city, market FROM `{DS}.in_cloudscene_crosscheck`
  ORDER BY market, name""")
out["queue_miso"] = rows(f"""SELECT project_key, county, poiname, studyphase, studygroup,
    facilitytype, fueltype, dp1erismw, dp1nrismw, summernetmw, applicationstatus
  FROM `{DS}.in_queue_miso_extras` ORDER BY county, project_key""")

# The admitted/source denominators. A count with no denominator is a claim you cannot check.
out["admission"] = rows(f"""
  SELECT 'D11 entity dissolution' AS signal, 983 AS admitted, 2129 AS source_rows,
         'terminal statuses only; 1,146 withdrawn excluded' AS rule
  UNION ALL SELECT 'D25 rail abandonment', 127, 874,
         'abandonment events only; 747 procedural filings excluded'
  UNION ALL SELECT 'D27 UCC lapse', 156, 156, 'all rows admitted; every one address-keyed'
  UNION ALL SELECT 'IOCS mortgage foreclosure', 92, 94,
         'county grain only; STATE total row and nan residue excluded'
  UNION ALL SELECT 'cloudscene', 260, 5388,
         'Indiana rows via market; cross-check only, table holds no coordinates'
  UNION ALL SELECT 'queue_miso', 456, 3794,
         'Indiana slice kept as a JOIN; 452 of 456 already in interconnection_queue'
  UNION ALL SELECT 'data centres deduped', 242, 244,
         'name-stem within 500 m; 8 unnamed OSM rows kept and flagged'""")

with gzip.open(os.path.join(REPO, "data", "signoff.json.gz"), "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(out, f, separators=(",", ":"), default=jd)
print("signoff.json.gz: " + " · ".join(f"{k} {len(v)}" for k, v in out.items()))

# ---- IOCS onto county context (REPLACE, never accumulate) --------------------------------
p = os.path.join(REPO, "data", "county_context.json")
ctx = json.load(open(p, encoding="utf-8"))
for v in ctx["by_fips"].values():
    v.pop("iocs", None)
merged = 0
for r in rows(f"""SELECT county_fips, mortgage_foreclosures, evictions, small_claims, court_rows
                  FROM `{DS}.in_iocs_county_context`"""):
    fips = str(r["county_fips"])
    if fips in ctx["by_fips"]:
        ctx["by_fips"][fips]["iocs"] = {"mf": r["mortgage_foreclosures"], "ev": r["evictions"],
                                        "sc": r["small_claims"], "courts": r["court_rows"]}
        merged += 1
json.dump(ctx, open(p, "w", encoding="utf-8"), separators=(",", ":"), default=jd)
print(f"county_context.json: IOCS merged onto {merged}/92 counties")

# ---- facilities layer: DC points from the DEDUPED table ----------------------------------
fp = os.path.join(REPO, "data", "facilities.geojson.gz")
fc = json.loads(gzip.decompress(open(fp, "rb").read()).decode())
kept = [f for f in fc["features"] if f["properties"].get("layer") != "dc"]
before = len(fc["features"]) - len(kept)
# Source the DC layer from in_data_centers_located, which carries the PUBLISHER'S precision
# label. 92 of 242 are census-gazetteer CITY centroids, not facility locations - the map has
# to say so rather than draw them like the 150 real ones.
dc = 0
for r in rows(f"""SELECT src, name, operator, lat, lon, unnamed_cannot_dedupe, dedupe_note,
                         location_precision, precision_method, pins_at_this_point
                  FROM `{DS}.in_data_centers_located` WHERE lat IS NOT NULL AND lon IS NOT NULL"""):
    kept.append({"type": "Feature",
                 "properties": {"layer": "dc", "src": r["src"], "name": r["name"],
                                "operator": r["operator"],
                                "unnamed_cannot_dedupe": r["unnamed_cannot_dedupe"],
                                "dedupe_note": r["dedupe_note"],
                                "location_precision": r["location_precision"],
                                "precision_method": r["precision_method"],
                                "pins_at_this_point": r["pins_at_this_point"]},
                 "geometry": {"type": "Point", "coordinates": [round(r["lon"], 7), round(r["lat"], 7)]}})
    dc += 1
with gzip.open(fp, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump({"type": "FeatureCollection", "features": kept}, f, separators=(",", ":"), default=jd)
print(f"facilities.geojson.gz: DC points {before} -> {dc} (deduped), {len(kept):,} features total")

# ---- provenance refresh so the Data page lists the new tables ----------------------------
# DEDUPE ON READ. Several early scripts INSERTed a registry row on every re-run without
# clearing the previous one, so _registry holds 216 rows for 195 tables (in_grid_plans and
# in_si_candidates appear 4x each). The Data page was therefore claiming 216 registered
# tables while holding 195 - a management-facing number overstated by 11%. Rather than delete
# ledger history, which is a genuine audit trail of when each table was rebuilt, keep only the
# most recent row PER TABLE for display. Newer scripts (this one, build_signoff_wiring.py)
# delete their own prior row before inserting, so the duplication does not grow.
sp = os.path.join(REPO, "data", "state_summary.json")
s = json.load(open(sp, encoding="utf-8"))
s["provenance"] = rows(f"""
  SELECT * EXCEPT(rn) FROM (
    SELECT table_name, source, method, n_rows, CAST(built_at AS STRING) built_at, notes,
           ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY built_at DESC) rn
    FROM `{DS}._registry`)
  WHERE rn = 1 ORDER BY table_name""")
s["registry_rows_total"] = list(client.query(f"SELECT COUNT(*) n FROM `{DS}._registry`"))[0].n
s["registry_note"] = ("provenance lists the LATEST build row per table; _registry itself keeps "
                      "every build as an audit trail, so its raw row count is higher")
s["built_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
json.dump(s, open(sp, "w", encoding="utf-8"), indent=1, default=jd)
print(f"state_summary.json: provenance now lists {len(s['provenance'])} tables")
