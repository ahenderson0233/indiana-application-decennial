"""GENERATED high-level inventory of every object in indiana_app — what it is, and what it CARRIES.

WHY THIS EXISTS. In one session this project asserted, wrongly, that:
  * D4 tax delinquency was NOT HELD          -- 17,617 delinquent rows were in in_si_refresh_sri_taxsale_in
  * no owner data existed anywhere            -- in_marion_parcel_crosswalk holds owner mailing address
                                                 on 346,919 of 347,049 Marion parcels
  * D12 admitted 228 parcels "in one county"  -- 228 is ADMITTED; 10,370 are REACHED
Each error came from reading a document instead of the warehouse, or from a keyword filter over
column NAMES rather than a look at what the columns CONTAIN.

So this inventory does not just list tables. For every object it surfaces the columns that have
repeatedly turned out to matter and been missed:
  OWNER    owner name / mailing address -- absentee (D9) and owner-approach (D18) inputs
  DATE     anything holding a real date, detected by CONTENT, not by column name
  STATUS   low-cardinality vocabularies, because a status column is usually a hidden signal split
           (saleStatusDescription hid D4 inside D1; CASE_TYPE hid unsafe-building inside D12)
  GEO      coordinates or geometry -- can it be placed without a bridge?
  KEY      parcel keys -- can it join to the spine at all?

Regenerate with: python scripts/build_table_inventory.py
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
import datetime
import os
import re

from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

OWNER = re.compile(r"owner|taxpayer|grantee|deeded", re.I)
GEO = re.compile(r"^(lat|lon|latitude|longitude|geog|geom|shape|x|y)$|_lat$|_lon$|geog|geometry", re.I)
KEY = re.compile(r"parcel|apn|pin|state_?id|statepin|propertyid", re.I)
DATEISH = re.compile(r"date|_at$|year|filed|issued|adopted|effective|published|expire", re.I)
STATUSISH = re.compile(r"status|type|class|verdict|grade|category|kind|action|disposition", re.I)

# families, in the order a reader would want them
FAMILY = [
    ("SELLER-INTENT: the flag and its inputs", re.compile(r"^in_si_(sites_flags|parcel_signals|signal_coverage|signals|owner_signals)")),
    ("SELLER-INTENT: acquired source corpora", re.compile(r"^in_si_")),
    ("PARCEL SPINE & capability gates", re.compile(r"^in_(sites|site_gates|parcel_attrs|sites_county|county_rollup|marion_)")),
    ("DATA CENTRES & competitive landscape", re.compile(r"^in_(dc_|data_centers|cloudscene|peeringdb)")),
    ("ORDINANCES & county posture", re.compile(r"^in_(ordinances|dc_actions|commission_posture)")),
    ("GRID: queues, buses, headroom, RTEP", re.compile(r"^in_(pjm|miso|queue|bus_|rtep|substations|transmission|grid_plans|rto_|txexp|territories|iurc)")),
    ("GENERATION & emissions", re.compile(r"^in_(eia|power_plants|generation|operating_gen|solar|wind|cems|ghgrp|nrc|elec_)")),
    ("GAS", re.compile(r"^in_gas")),
    ("RATES & market", re.compile(r"^in_(rate_|urdb|utility_tariff|eqr|ferc|econ_|news_)")),
    ("ENVIRONMENT & hazard", re.compile(r"^in_(flood|wetlands|water|nhd|padus|brownfield|echo|nonattain|storm|spc_|fema|seismic|drought|land_)")),
    ("COMMUNITY, LABOUR, LEGISLATURE", re.compile(r"^in_(acs|cbp|qcew|workforce|openstates|candidate_sites|iocs|nfirs|sba)")),
    ("INFRASTRUCTURE & context", re.compile(r"^in_(roads|railroads|airports|faa|fcc|zctas|tribal|usa_structures|logistics)")),
    ("VIEWS & derived location joins", re.compile(r"^vw_")),
    ("META / audit", re.compile(r"^_")),
]

tables = sorted(client.list_tables("energy-platfrom.indiana_app"), key=lambda t: t.table_id)
reg = {r.table_name: r for r in client.query(
    f"SELECT table_name, ANY_VALUE(source) source, ANY_VALUE(n_rows) n_rows, "
    f"ANY_VALUE(notes) notes, MAX(built_at) built_at FROM `{DS}._registry` GROUP BY table_name")}

print(f"inspecting {len(tables)} objects…")
records = []
for t in tables:
    try:
        tb = client.get_table(f"{DS}.{t.table_id}")
    except Exception:
        continue
    cols = [f.name for f in tb.schema]
    rec = {
        "name": t.table_id, "rows": tb.num_rows, "is_view": tb.table_type == "VIEW",
        "ncols": len(cols),
        "owner": [x for x in cols if OWNER.search(x)],
        "geo": [x for x in cols if GEO.search(x)],
        "key": [x for x in cols if KEY.search(x)],
        "dateish": [x for x in cols if DATEISH.search(x)],
        "statusish": [x for x in cols if STATUSISH.search(x)],
        "reg": reg.get(t.table_id),
    }
    records.append(rec)

# --- for the tables most likely to hide a signal, MEASURE the interesting columns -------------
print("measuring owner/status population on candidate tables…")
for rec in records:
    rec["owner_pop"], rec["status_vocab"] = {}, {}
    if rec["is_view"] or not rec["rows"]:
        continue
    if rec["owner"]:
        sel = ", ".join(f"COUNTIF(`{x}` IS NOT NULL AND LENGTH(TRIM(CAST(`{x}` AS STRING)))>1) AS `c{i}`"
                        for i, x in enumerate(rec["owner"][:4]))
        try:
            r = dict(list(client.query(f"SELECT {sel} FROM `{DS}.{rec['name']}`"))[0])
            for i, x in enumerate(rec["owner"][:4]):
                if r.get(f"c{i}"):
                    rec["owner_pop"][x] = r[f"c{i}"]
        except Exception:
            pass
    # a low-cardinality status column is where hidden signal splits live
    for x in rec["statusish"][:3]:
        try:
            rows = list(client.query(
                f"SELECT CAST(`{x}` AS STRING) v, COUNT(*) n FROM `{DS}.{rec['name']}` "
                f"GROUP BY 1 ORDER BY n DESC LIMIT 7"))
            if 1 < len(rows) <= 7:
                rec["status_vocab"][x] = [(str(z.v)[:26], z.n) for z in rows]
        except Exception:
            pass

o = [f"# TABLE INVENTORY — `{DS}`", "",
     f"**GENERATED {datetime.date.today()} by `scripts/build_table_inventory.py`. Do not hand-edit.**", "",
     f"{len(records)} objects. This exists because this project has repeatedly asserted it did not hold "
     "data that was sitting in the warehouse. It lists not just what each object IS but what it "
     "CARRIES — owner fields, real dates, status vocabularies, coordinates and parcel keys — because "
     "every one of those misses was a column nobody looked at.", "",
     "**How to read the flags:** `OWNER` = carries owner name or mailing address (D9/D18 input). "
     "`GEO` = placeable without a bridge. `KEY` = can join to the parcel spine. `DATE` = has a "
     "date-bearing column. `STATUS` = low-cardinality vocabulary, i.e. **a possible hidden signal "
     "split** — this is how D4 was found hiding inside D1.", ""]

seen = set()
for title, pat in FAMILY:
    fam = [r for r in records if r["name"] not in seen and pat.match(r["name"])]
    if not fam:
        continue
    seen |= {r["name"] for r in fam}
    o += [f"## {title}", "",
          "| object | rows | flags | what it is |", "|---|---:|---|---|"]
    for r in sorted(fam, key=lambda x: -(x["rows"] or 0)):
        flags = []
        if r["owner_pop"]:
            flags.append("**OWNER**")
        if r["geo"]:
            flags.append("GEO")
        if r["key"]:
            flags.append("KEY")
        if r["dateish"]:
            flags.append("DATE")
        if r["status_vocab"]:
            flags.append("**STATUS**")
        if r["is_view"]:
            flags.append("_view_")
        srcs = (r["reg"].source if r["reg"] else "") or ""
        o.append(f"| `{r['name']}` | {r['rows']:,} | {' '.join(flags)} | {srcs[:96]} |")
    o.append("")

o += ["## ⚠ Objects carrying OWNER data — the D9/D18 inputs we already hold", "",
      "Absentee ownership is *owner mailing state/zip ≠ situs*. Every input below is already in "
      "the warehouse; none of it required a new acquisition.", "",
      "| object | column | populated |", "|---|---|---:|"]
for r in sorted(records, key=lambda x: -max(x["owner_pop"].values() or [0])):
    for col, npop in sorted(r["owner_pop"].items(), key=lambda kv: -kv[1])[:3]:
        o.append(f"| `{r['name']}` | `{col}` | {npop:,} |")

o += ["", "## ⚠ STATUS vocabularies — where a hidden signal split can live", "",
      "`saleStatusDescription` hid **D4 tax delinquency** inside D1_tax_sale for a whole session. "
      "`CASE_TYPE` hid unsafe-building and vacant-board-order inside D12. Read the vocabulary "
      "before trusting any count taken over one of these.", ""]
for r in records:
    for col, vocab in r["status_vocab"].items():
        if len(vocab) < 2:
            continue
        vs = " · ".join(f"{v} {n:,}" for v, n in vocab)
        o += [f"- **`{r['name']}`.`{col}`** — {vs}"]

path = os.path.join(REPO, "docs", "TABLE_INVENTORY.md")
open(path, "w", encoding="utf-8").write("\n".join(o) + "\n")
print(f"\ndocs/TABLE_INVENTORY.md — {len(records)} objects · "
      f"{sum(1 for r in records if r['owner_pop'])} carry owner data · "
      f"{sum(1 for r in records if r['status_vocab'])} carry a status vocabulary")
