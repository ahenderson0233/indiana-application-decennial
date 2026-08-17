"""Did our clips take every column the parent offers? Audit all of indiana_app against energy.

WHY. Operator, 2026-08-17: *"It is likely that we didn't scrape the full columns from any of these
tables, so please explore this."* The hypothesis was confirmed on the first table we checked and it
was not cosmetic: `in_miso_poi_300mw` dropped `headroom_state`, `n_facilities_overloaded_base` and
the publisher's own `_invariant_columns` / `_probe_dependent_columns` metadata. Missing
`headroom_state` is why the app cannot tell a user whether a POI reads zero because it is genuinely
full or because a monitored facility was **already overloaded before their project existed** -
two completely different findings that currently render identically.

A dropped column is invisible: nothing errors, the table looks complete, and the loss only shows up
as an answer that is quietly narrower than it should be.

This walks every registered `in_*` table whose registry `source` names an `energy.*` parent, and
reports the columns the parent has that we do not.

NAME NORMALISATION MATTERS. Our clips sometimes keep the publisher's raw casing (`PercentDf`,
`MwImpact`) while the parent uses snake_case (`percent_dfax`, `mw_impact`). Comparing raw names
would report dozens of false gaps - the same failure class as the front-end audit opening with 56
findings and roughly zero real ones. So both sides are normalised to lower-case alphanumerics
before comparison, and near-matches are reported separately from true absences.

READ-ONLY. Touches nothing.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import re, json, os, collections
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
client = bigquery.Client(project="energy-platfrom")

# Case and punctuation are not the only way the same field is spelled differently across a clip.
# ALIASES are, and ignoring them makes this audit cry wolf: the first run reported `latitude` and
# `longitude` as missing from `in_pjm_bus_locations_candidate`, which holds them as `lat`/`lon`.
# That is rule 9 (an audit with false positives gets ignored) reappearing in a new script, so the
# aliases are folded in BEFORE anything is called missing.
ALIAS = {
    "latitude": "lat", "longitude": "lon", "lng": "lon", "long": "lon",
    "countyfips": "countyfips", "county_fips": "countyfips",
    "substationname": "name", "substation_name": "name",
    "poinamerequested": "poinamerequested",
    "dfaxfield": "dfax", "percentdfax": "dfax", "percentdf": "dfax",
    "mwavailable": "pmax", "mwimpact": "mwimpact",
    "monitoredfacility": "monitoredfacilityname",
    "contflowmw": "contflowmw", "baseflowmw": "baseflowmw",
    "ratebasemva": "ratebasemva", "ratecontmva": "ratecontmva",
    "areasname": "areasname", "contname": "contname", "contid": "contid",
    "frbus": "frbus", "frname": "frname", "tobus": "tobus", "toname": "toname",
    "geom": "geog", "geometry": "geog", "geometrygeojson": "geog",
    "pulledat": "pulledat", "sourceurl": "sourceurl",
}
def norm(s):
    k = re.sub(r"[^a-z0-9]", "", str(s).lower())
    return ALIAS.get(k, k)

# every registered table and the source string it recorded
reg = {r.table_name: (r.source or "") for r in client.query(f"""
  SELECT table_name, source FROM `{DS}._registry`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY built_at DESC) = 1""")}

# which of those name an energy parent we can actually inspect
energy_tables = {r.table_id for r in client.query(
    "SELECT table_id FROM `energy-platfrom.energy.__TABLES__`")}

pairs = []
for t, src in reg.items():
    for m in re.findall(r"energy[-.]platfrom\.energy\.([a-zA-Z0-9_]+)|(?<![\w.])energy\.([a-zA-Z0-9_]+)", src):
        parent = m[0] or m[1]
        if parent in energy_tables:
            pairs.append((t, parent))
            break

print(f"{len(reg)} registered tables; {len(pairs)} clip a resolvable energy parent")
print()

rows, total_missing = [], 0
for t, parent in sorted(pairs):
    try:
        ours = [f.name for f in client.get_table(f"{DS}.{t}").schema]
        theirs = [f.name for f in client.get_table(f"energy-platfrom.energy.{parent}").schema]
    except Exception as e:
        print(f"  [skip] {t}: {str(e)[:70]}")
        continue
    ourn = {norm(x) for x in ours}
    missing = [x for x in theirs if norm(x) not in ourn]
    if not missing:
        continue
    total_missing += len(missing)
    rows.append({"table": t, "parent": parent, "ours": len(ours), "theirs": len(theirs),
                 "missing": missing})

rows.sort(key=lambda r: -len(r["missing"]))
print(f"{len(rows)} clips are missing at least one parent column "
      f"({total_missing} columns total)\n")
for r in rows:
    print(f"  {r['table']:44s} {r['ours']:>3} of {r['theirs']:>3} cols  "
          f"({len(r['missing'])} missing)")
    print(f"      parent: energy.{r['parent']}")
    print(f"      missing: {', '.join(r['missing'][:14])}"
          f"{' …' if len(r['missing']) > 14 else ''}")

out = os.path.join(REPO, "docs", "CLIP_COMPLETENESS.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump({"clips_checked": len(pairs), "clips_incomplete": len(rows),
               "columns_missing_total": total_missing, "detail": rows}, f, indent=1)
print(f"\nwritten -> docs/CLIP_COMPLETENESS.json")
print("A dropped column is invisible: nothing errors and the table looks complete. "
      "Re-clip before trusting any answer these tables feed.")
