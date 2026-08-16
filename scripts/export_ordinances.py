"""Surface the ordinance family on Community — the county data-centre posture layer.

REGISTRY-DRIVEN BY FAMILY, deliberately. Ordinance tables are still arriving from background
acquisition agents, and a panel that names each table would go stale the moment the next one
lands — which is exactly how the nine `vw_*` location views scored as unwired for a week. This
enumerates `in_ordinances_*` from `_registry` instead, so a new table surfaces the run after it
is registered without touching this script.

WHAT THIS PANEL MUST NOT DO. The row count is not the finding. 153 candidate rows reduce to
19 sections that plausibly regulate a data centre as a land use, across 9 jurisdictions — and
Indiana's genuine codified corpus is a handful of sections in two counties. Reporting "153
ordinance rows" would overstate coverage by an order of magnitude. The panel leads with the
triage verdict and shows the candidate count behind it.

AND THE BIGGER POINT, which the codified corpus cannot express: the decision-relevant regulation
is county MORATORIA published on county websites — Boone (LEAP district, effective 2026-06-16)
and Miami (2026-05-04) — neither of which is codified anywhere. A codified-only panel renders
Boone as SILENT when it is the most restrictive posture in the state, so the page says so.
"""
import json, gzip, os, datetime
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")


def rows(sql):
    return [dict(r) for r in client.query(sql)]


def has(t):
    try:
        client.get_table(f"{DS}.{t}"); return True
    except Exception:
        return False


out = {"built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}

# the family, enumerated from the registry so new agent tables appear without a code change
out["family"] = rows(f"""
  SELECT table_name, ANY_VALUE(n_rows) n_rows, ANY_VALUE(source) source,
         ANY_VALUE(method) method, MAX(built_at) built_at
  FROM `{DS}._registry`
  WHERE STARTS_WITH(table_name, 'in_ordinances_') OR STARTS_WITH(table_name, 'in_dc_actions')
  GROUP BY table_name ORDER BY table_name""")

if has("in_ordinances_dc_v2_triage"):
    out["triage_summary"] = rows(f"""
      SELECT verdict, COUNT(*) sections, SUM(n_candidate_rows) candidate_rows
      FROM `{DS}.in_ordinances_dc_v2_triage` GROUP BY 1 ORDER BY sections DESC""")
    out["relevant"] = rows(f"""
      SELECT county, jurisdiction, code_section_id, section_title, ancestors_path, url,
             verdict, reason, search_phrases, n_candidate_rows
      FROM `{DS}.in_ordinances_dc_v2_triage`
      WHERE verdict IN ('RELEVANT','NEEDS_FULL_TEXT')
      ORDER BY verdict, county, jurisdiction""")
    out["by_county"] = rows(f"""
      SELECT county, COUNTIF(verdict='RELEVANT') relevant,
             COUNTIF(verdict='NEEDS_FULL_TEXT') needs_full_text,
             COUNTIF(verdict='NOT_RELEVANT') not_relevant
      FROM `{DS}.in_ordinances_dc_v2_triage` GROUP BY 1 ORDER BY relevant DESC, county""")

# the 7 rows that actually name a data centre, straight from the candidate table
if has("in_ordinances_dc_v2"):
    out["named"] = rows(f"""
      SELECT jurisdiction, county, section_title, snippet, url, search_phrase,
             codified_through_text
      FROM `{DS}.in_ordinances_dc_v2`
      WHERE REGEXP_CONTAINS(LOWER(IFNULL(snippet,'')), r'data cent(er|re)')
      ORDER BY county, jurisdiction""")

# coverage: which counties were actually assessed, versus never searched
for t, key in (("in_ordinances_dc_coverage_v2", "coverage"),
               ("in_ordinances_amlegal_coverage_v2", "amlegal_coverage"),
               ("in_ordinances_publisher_inventory_v2", "publishers"),
               ("in_ordinances_dc_county_sites_v2", "county_sites")):
    if has(t):
        cols = [s.name for s in client.get_table(f"{DS}.{t}").schema]
        out[key] = rows(f"SELECT {', '.join(cols[:14])} FROM `{DS}.{t}` LIMIT 400")

out["caveat"] = (
    "The row count is not the finding. Of 153 candidate rows only 7 name a data centre, and "
    "triage of the remaining 146 admits 19 sections across 9 jurisdictions. Indiana's genuine "
    "CODIFIED data-centre corpus is a handful of sections in two counties. More importantly, the "
    "decision-relevant regulation is not codified at all: county commissioner MORATORIA — Boone "
    "(LEAP district, effective 2026-06-16) and Miami (2026-05-04) — appear on county websites and "
    "in no code library. A codified-only reading renders Boone as SILENT when it is the most "
    "restrictive posture in the state.")

path = os.path.join(REPO, "data", "ordinances.json.gz")
with gzip.open(path, "wt", encoding="utf-8", compresslevel=6) as f:
    json.dump(out, f, separators=(",", ":"), default=str)

print(f"data/ordinances.json.gz — {os.path.getsize(path)/1024:.0f} KB")
print(f"  family tables surfaced: {len(out['family'])}")
for t in out["family"]:
    print(f"    {t['table_name']:44s} {t['n_rows']}")
if "triage_summary" in out:
    for v in out["triage_summary"]:
        print(f"  {v['verdict']:16s} {v['sections']:>4} sections · {v['candidate_rows']:>4} rows")
print(f"  named a data centre: {len(out.get('named', []))}")
