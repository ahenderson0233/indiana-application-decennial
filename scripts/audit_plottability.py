"""PLOTTABILITY AUDIT — operator rule: every table should reach a feature, and everything should
be plottable to some extent.

"To some extent" is the important qualifier, so this grades rather than passes/fails:
  A. exact geometry      — a GEOGRAPHY column or geometry_geojson (draw the real shape)
  B. published point     — publisher lat/lon (draw a pin at their coordinate)
  C. address-keyable     — street + city/zip, so it CAN be located later without inventing a point
  D. county/place only   — attributable to an area, never to a site
  E. not locatable       — no geography of any kind held

Grade D is legitimate for genuinely county-grain subjects (posture, disaster counts). Grade E on
a table that describes SITES is the real defect. READ-ONLY; writes docs/PLOTTABILITY.md.
"""
import os, datetime
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

cols = {}
for r in client.query(f"""
    SELECT table_name, column_name, data_type
    FROM `{DS}`.INFORMATION_SCHEMA.COLUMNS ORDER BY table_name, ordinal_position"""):
    cols.setdefault(r.table_name, []).append((r.column_name.lower(), r.data_type))

# An EXACT-NAME match under-reports badly. Measured examples it missed: `faclong`
# (echo_cwa_facilities), `latitude_raw` (miso_poi), `lstreet1`/`lcity` (gov_surplus_nces),
# `Latitude`/`Longitude` (brownfields). Match on SUBSTRING instead, while excluding the
# false friends that merely contain the letters — 'relation', 'longname', 'population'.
GEOG = {"geography"}
LAT_RE = ("lat",)
LON_RE = ("lon", "lng", "xlong")
NOT_LAT = ("relat", "late", "plat", "latch", "violat", "instal", "circulat")
NOT_LON = ("along", "belong", "longname", "colon")
ADDR_SUB = ("address", "street", "addr", "situs", "stnumber", "full_stname")
PLACE_SUB = ("city", "county", "zip", "geoid", "fips", "township", "cz_name", "designatedarea",
             "place", "state_id", "cbsa", "tract", "geography_id")

def _has(names, subs, nots=()):
    for c in names:
        if any(s in c for s in subs) and not any(n in c for n in nots):
            return True
    return False

def grade(tbl):
    names = {c for c, _ in cols[tbl]}
    types = {t.lower() for _, t in cols[tbl]}
    has_geo = bool(GEOG & types) or any("geojson" in c or c in ("geom", "geog", "geometry") for c in names)
    has_pt = _has(names, LAT_RE, NOT_LAT) and _has(names, LON_RE, NOT_LON)
    has_addr = _has(names, ADDR_SUB)
    has_place = _has(names, PLACE_SUB)
    if has_geo: return "A exact geometry"
    if has_pt: return "B published point"
    if has_addr and has_place: return "C address-keyable"
    if has_place: return "D county/place only"
    return "E NOT LOCATABLE"

# Operator ruling 2026-08-15: market and series tables do NOT need geometry and must not be
# "fixed" by reloading. A monthly price, a statewide demand curve or a utility's annual sales
# have no location to draw — grade E is CORRECT for them, not a defect. Only tables whose rows
# describe a PLACE OR A SITE are held to the plottable standard.
SERIES = ("_sales", "_demand", "reliability", "fuel_receipts", "cems_monthly", "ferc714",
          "_prices", "price", "tariff", "urdb", "_rates", "elec_power_operational",
          "demand_response", "gas_state_capacity", "drought_by_state", "eqr_identity",
          "megadeals", "_census", "coverage", "posture", "state_irp", "puc_state_access",
          "commission_posture", "docket", "bill", "openstates", "news", "sba_foia",
          "qcew", "acs_county", "cbp_county", "workforce", "water_use", "solar_potential",
          "fcc_bdc", "ipeds", "gas_capacity_", "gas_phmsa", "eia861", "eia923", "eia860",
          "iocs", "storm_events", "disaster", "nri_counties", "usa_structures_county")
def subject(t):
    return "series/aggregate" if any(s in t for s in SERIES) else "place or site"

rows = []
for t in sorted(cols):
    if t.startswith("_"): continue
    rows.append((t, grade(t), len(cols[t]), subject(t)))

by = {}
for t, g, n, subj in rows: by.setdefault(g, []).append((t, n, subj))

out = [f"# Plottability audit — {datetime.date.today()}", "",
       "Operator rule: every table reaches a feature, and everything is plottable *to some extent*.",
       "Graded, because 'to some extent' matters — a county-grain subject is honestly grade D and",
       "should never be drawn as a pin.", "",
       "| grade | meaning | tables |", "|---|---|---:|"]
for g in ["A exact geometry", "B published point", "C address-keyable", "D county/place only", "E NOT LOCATABLE"]:
    meaning = {"A exact geometry": "GEOGRAPHY / geometry_geojson — draw the real shape",
               "B published point": "publisher lat/lon — draw their pin, never a derived one",
               "C address-keyable": "street + city/zip — locatable later, no point invented",
               "D county/place only": "attributable to an area, never to a site",
               "E NOT LOCATABLE": "no geography of any kind held"}[g]
    out.append(f"| **{g[0]}** | {meaning} | {len(by.get(g, []))} |")
out.append("")

defects = [(t, n) for t, n, subj in by.get("E NOT LOCATABLE", []) if subj == "place or site"]
series_e = [(t, n) for t, n, subj in by.get("E NOT LOCATABLE", []) if subj == "series/aggregate"]
out += ["## Grade E, split by whether it MATTERS", "",
        f"**{len(series_e)} are series/aggregate tables — grade E is CORRECT for them.** A monthly "
        "price, a statewide demand curve or a utility's annual sales have no location to draw. "
        "Operator ruling: do not reload these chasing geometry.", "",
        f"**{len(defects)} describe a place or a site and have no geography at all — these are the "
        "real defects.**", "", "| table | columns |", "|---|---:|"]
for t, n in defects: out.append(f"| `{t}` | {n} |")
out.append("")
out += ["<details><summary>Series/aggregate tables at grade E (correctly, no action)</summary>", "",
        "| table |", "|---|"]
for t, _ in series_e: out.append(f"| `{t}` |")
out += ["", "</details>", ""]

for g in ["D county/place only", "C address-keyable"]:
    lst = by.get(g, [])
    out += [f"## {g} — {len(lst)} tables", "", "| table | columns | subject |", "|---|---:|---|"]
    for t, n, subj in lst: out.append(f"| `{t}` | {n} | {subj} |")
    out.append("")

# SI tables specifically - the operator's focus
si = [(t, g) for t, g, _, _ in rows if t.startswith("in_si_")]
out += ["## Seller-intent tables specifically", "",
        f"{len(si)} SI tables. Grade spread:", "", "| grade | n |", "|---|---:|"]
sg = {}
for t, g in si: sg[g] = sg.get(g, 0) + 1
for g, n in sorted(sg.items()): out.append(f"| {g} | {n} |")
out += ["", "| table | grade |", "|---|---|"]
for t, g in sorted(si, key=lambda x: x[1]): out.append(f"| `{t}` | {g} |")
out.append("")

open(f"{REPO}\\docs\\PLOTTABILITY.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
for g in ["A exact geometry", "B published point", "C address-keyable", "D county/place only", "E NOT LOCATABLE"]:
    print(f"  {g:<22} {len(by.get(g, [])):>3}")
print(f"\nSI tables: {len(si)}; grades {sg}")
print("docs/PLOTTABILITY.md written")
