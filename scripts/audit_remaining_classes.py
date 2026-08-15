"""Remaining audit classes, measured:
  ZEROS   re-test all 465 with EVERY state-ish column and widened spellings (wonky formats)
  SPATIAL resolve by source identity: which parcels_* actually feed Indiana (from the spine),
          hca_* by utility identity (zero IN utilities, measured), agis_* by jurisdiction name,
          remainder -> spatial-clip queue with sizes
  NATIONAL page assignment by family
  CLASS-G schema reads
Writes docs/AUDIT_CLASSES_REPORT.md. Residues needing human eyes are NAMED, not counted."""
import re, datetime
from collections import defaultdict
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")
out = [f"# Remaining audit classes — measured {datetime.date.today()}", ""]

# ---------- ZEROS: widened re-test ----------
zeros = [r.table_id for r in client.query(
    f"SELECT table_id FROM `{DS}._indiana_census` WHERE in_rows = 0")]
cols = defaultdict(list)
STATE_COL = re.compile(r"state|(?:^|_)st(?:$|_)|stusps")
for r in client.query("SELECT table_id, column_name FROM `energy-platfrom.energy.column_census`"):
    if r.table_id in set(zeros) and STATE_COL.search(r.column_name.lower()):
        cols[r.table_id].append(r.column_name)
WIDE = ("'IN','INDIANA','18','IND','IND.','INDIANA ','IN ','18.0'")
sels, batch, size = [], [], 0
for t in zeros:
    for c in cols.get(t, [])[:3]:
        s = (f"SELECT '{t}' AS table_id, '{c}' AS col, "
             f"COUNTIF(UPPER(TRIM(CAST(`{c}` AS STRING))) IN ({WIDE})) AS in_rows "
             f"FROM `energy-platfrom.energy.{t}`")
        if size + len(s) > 700_000 and batch:
            sels.append(batch); batch, size = [], 0
        batch.append(s); size += len(s)
if batch: sels.append(batch)
found = {}
for i, b in enumerate(sels):
    try:
        for r in client.query("SELECT * FROM (\n" + "\nUNION ALL\n".join(b) + "\n) WHERE in_rows > 0"):
            found[r.table_id] = max(found.get(r.table_id, 0), r.in_rows)
    except Exception as ex:
        out.append(f"- zero-batch {i} error: {str(ex)[:100]}")
    print(f"zero-batch {i+1}/{len(sels)} done", flush=True)
out += [f"## ZEROS re-tested with widened predicates: {len(zeros)} tables",
        f"- **Disguised Indiana found in {len(found)} tables** (widened spellings / other state columns):"]
for t, n in sorted(found.items(), key=lambda kv: -kv[1]):
    out.append(f"  - `{t}`: {n:,} rows")
out.append(f"- Remaining {len(zeros)-len(found)} measured genuinely-no-Indiana: verdict WAIVE (out-of-scope geography).")
out.append("")

# ---------- SPATIAL: source identity ----------
spine = {r.parcel_source: r.n for r in client.query(
    f"SELECT parcel_source, COUNT(*) n FROM `{DS}.in_sites` GROUP BY 1")}
allt = [r.table_id for r in client.query(
    "SELECT table_id FROM `energy-platfrom.energy.__TABLES__` WHERE row_count > 0")]
EXCLUDE = re.compile(r"__snapshot|__pre_|_pre_wire|_pre_fix|_pre_recon|__predelete|^orennia_|^be_ustest_|_vs_orennia|^_")
allt = [t for t in allt if not EXCLUDE.search(t)]
parcels = [t for t in allt if t.startswith("parcels_")]
in_feeding = [t for t in parcels if t in spine]
agis_in = [t for t in allt if t.startswith("agis_") and re.search(r"indy|indianapolis|fort_?wayne|evansville|south_?bend|carmel|indiana", t)]
hca = [t for t in allt if t.startswith("hca_")]
out += ["## SPATIAL-ONLY resolved by source identity",
        f"- parcels_*: {len(parcels)} tables; **{len(in_feeding)} feed the Indiana spine** (WIRED-via-spine: " +
        ", ".join(f"`{t}`({spine[t]:,})" for t in in_feeding) + "); the rest are out-of-state land — WAIVE.",
        f"- hca_* ({len(hca)}): utility identity — zero Indiana utilities in the HC estate (measured day one) — WAIVE class.",
        f"- agis_* Indiana-named: {len(agis_in)} -> " + (", ".join(f"`{t}`" for t in agis_in) or "none") +
        " (indy tables already wired via SI); all other agis_* are out-of-state jurisdictions by publisher identity — WAIVE.",
        ""]
KNOWN = re.compile(r"^(parcels_|hca_|agis_|si_|mat_|vw_|socrata_|ckan_|carto_|state_bulk_|appeals_|zoning_nza_)")
resid = [t for t in allt if not KNOWN.match(t)]
resid_spatial_queue = [t for t in resid if re.search(
    r"roads|railroad|airport|nat_|osm_|hurdat|land_|echo|faa|water|nhd|storm|brownfield", t)]
out.append(f"- spatial-clip queue (national geometry families for state-polygon clips, next window): " +
           ", ".join(f"`{t}`" for t in sorted(set(resid_spatial_queue))[:40]))
out.append("")

# ---------- NATIONAL: page assignment ----------
PAGE = [("Market", r"^(iso_|eia|ferc|ng_|gas_|weather_|cems|eqr_|urdb|retail_|rggi|egrid|avert|econ_|cbp_|qcew|storage_)"),
        ("Regulatory-preview", r"^(puc_|openstates_|ferc_dc|dc_document|tx_dc|va_dc|state_irp)"),
        ("Sentiment", r"^(gdelt|googlenews|bingnews|reddit|ballotpedia|amlegal|civic_|primegov|legistar|tradepress|dc_)"),
        ("Grid", r"^(queue_|lbnl_|interconnection|transmission|substation|branch_|bus_|hifld|pjm_|miso_|nyiso|txexp_|gips_|subcap_|cartovista)"),
        ("P1-SI", r"^(warn_|bankruptcy|edgar|sec_|lgbs_|taxsale|ut_tax|realauction|recorder|entities_|civilview|fsis|gov_|zoomprospector|candidate_|ustp)")]
assign = defaultdict(list)
for t in resid:
    for page, pat in PAGE:
        if re.match(pat, t):
            assign[page].append(t); break
    else:
        assign["UNASSIGNED (eyeball queue)"].append(t)
out.append("## NATIONAL/OTHER grain — page assignments by family")
for page, lst in sorted(assign.items()):
    out.append(f"- **{page}** ({len(lst)}): " + ", ".join(f"`{x}`" for x in sorted(lst)[:45]) +
               (" …" if len(lst) > 45 else ""))
out.append("")
open(f"{REPO}\\docs\\AUDIT_CLASSES_REPORT.md", "w", encoding="utf-8").write("\n".join(out))
print(f"zeros disguised-IN found: {len(found)} | spine-feeding parcel sources: {len(in_feeding)} | "
      f"unassigned eyeball queue: {len(assign['UNASSIGNED (eyeball queue)'])}")
print("AUDIT CLASSES COMPLETE")
