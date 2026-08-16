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
# stdout must survive its own output: this console is cp1252 and characters like U+2248/U+2192/U+2717 raise
# UnicodeEncodeError from print() itself. The honesty audit once crashed on its own
# FAILURE path for exactly this reason. Degrade the glyph, never the run.
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
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

# ---- THE UNCODIFIED LAYER: county-website actions, all 92 counties ------------------------
# This is the layer the codified corpus structurally cannot see, and it is the one that decides
# siting. It is kept SEPARATE from the codified tables and split by evidence_grade at export
# time rather than in the page, so a lead cannot reach a posture surface by accident.
if has("in_dc_actions_county_v2"):
    out["county_actions"] = rows(f"""
      SELECT county, jurisdiction, action_type, instrument, posture_source_words,
             observed_date, date_note, effective_from, effective_to,
             expiry_condition_verbatim, verbatim_snippet, url, ordinance_pdf_url,
             doc_type, evidence_grade, why_codified_misses_it
      FROM `{DS}.in_dc_actions_county_v2`
      ORDER BY
        CASE evidence_grade WHEN 'VERIFIED_AT_OFFICIAL_SOURCE' THEN 0 ELSE 1 END,
        CASE action_type WHEN 'ban-prohibition' THEN 0 WHEN 'moratorium' THEN 1
             WHEN 'adopted-uncodified-ordinance' THEN 2 WHEN 'expired-moratorium' THEN 3
             WHEN 'petition-pending' THEN 4 WHEN 'proposed' THEN 5 WHEN 'denied' THEN 6
             WHEN 'withdrawn' THEN 7 ELSE 8 END,
        county""")
    out["county_action_summary"] = rows(f"""
      SELECT action_type,
             COUNTIF(evidence_grade='VERIFIED_AT_OFFICIAL_SOURCE') verified,
             COUNTIF(evidence_grade='REPORTED_NEEDS_VERIFICATION') lead_only,
             COUNT(*) total
      FROM `{DS}.in_dc_actions_county_v2` GROUP BY 1 ORDER BY total DESC""")

if has("in_dc_actions_coverage_v2"):
    # THE RE-SWEEP OVERRIDES THE FIRST PASS where it ran. 18 counties had been recorded
    # SEARCHED_NONE_FOUND without their official site ever being fetched — a search-engine look
    # scored as a county-level negative. Three of them turned out to have real actions, so those
    # three were rendering as "nothing found" on this page while a ~1 GW PUD (Henry), a
    # recommended moratorium (Tipton) and a ~$65B campus under construction (Sullivan) sat behind
    # the false negative. A weaker instrument must never overwrite a stronger one, so the join
    # takes the re-sweep row wherever it exists.
    resweep_join = ("LEFT JOIN `%s.in_dc_actions_resweep_coverage` r USING (county)" % DS
                    if has("in_dc_actions_resweep_coverage") else "")
    out["county_action_coverage"] = rows(f"""
      SELECT c.county,
             IFNULL(r.status, c.status) status,
             IFNULL(r.county_site_host, c.county_site_host) county_site_host,
             IFNULL(r.queries_run, c.queries_run) queries_run,
             IFNULL(r.official_site_fetched, c.official_site_fetched) official_site_fetched,
             IFNULL(r.search_instrument, c.search_instrument) search_instrument,
             IFNULL(r.notes, c.notes) notes,
             r.county IS NOT NULL AS re_swept
      FROM `{DS}.in_dc_actions_coverage_v2` c
      {resweep_join}
      ORDER BY status, county""") if resweep_join else rows(f"""
      SELECT county, status, county_site_host, queries_run, official_site_fetched,
             search_instrument, notes, FALSE AS re_swept
      FROM `{DS}.in_dc_actions_coverage_v2` ORDER BY status, county""")

# the three actions the first pass missed entirely
if has("in_dc_actions_resweep"):
    out["resweep_actions"] = rows(f"""
      SELECT county, jurisdiction, action_type, instrument, observed_date, effective_from,
             effective_to, verbatim_snippet, url, evidence_grade, date_note
      FROM `{DS}.in_dc_actions_resweep` ORDER BY evidence_grade, county""")

# ---- OFFICIAL-SOURCE VERIFICATION of the leads ------------------------------------------------
# `posture_renderable` is the gate, and it is computed in the warehouse rather than in the page.
# Two of these rows are MISATTRIBUTED OUT-OF-STATE leads that were live in the app as Indiana
# postures: Brown County's action belongs to Brown County WISCONSIN, Clay County's to Clay County
# FLORIDA. They are shipped as an explicit CORRECTION rather than silently dropped, because a row
# that quietly disappears teaches nobody why it was wrong.
if has("in_dc_actions_resolved"):
    out["verified_postures"] = rows(f"""
      SELECT county, jurisdiction, confirmed_action_type, verified_instrument,
             verified_observed_date, verified_effective_from, verified_effective_to,
             expiry_condition_verbatim, verbatim_snippet, official_url, date_note,
             verification_note, match_method
      FROM `{DS}.in_dc_actions_resolved`
      WHERE posture_renderable
      ORDER BY
        CASE confirmed_action_type WHEN 'ban-prohibition' THEN 0 WHEN 'moratorium' THEN 1
             WHEN 'adopted-uncodified-ordinance' THEN 2 WHEN 'expired-moratorium' THEN 3
             ELSE 4 END, county""")

    out["unresolved_leads"] = rows(f"""
      SELECT county, jurisdiction, lead_action_type, lead_instrument, verdict,
             final_evidence_grade, verification_note, official_url
      FROM `{DS}.in_dc_actions_resolved`
      WHERE NOT posture_renderable AND verdict != 'CONTRADICTED'
      ORDER BY county""")

    out["corrections"] = rows(f"""
      SELECT county, jurisdiction, lead_action_type, lead_instrument,
             date_note, verification_note, official_url
      FROM `{DS}.in_dc_actions_resolved`
      WHERE verdict = 'CONTRADICTED' ORDER BY county""")

    out["verification_summary"] = rows(f"""
      SELECT final_evidence_grade, COUNT(*) n, COUNTIF(posture_renderable) renderable
      FROM `{DS}.in_dc_actions_resolved` GROUP BY 1 ORDER BY n DESC""")

if has("in_dc_actions_verify_walls"):
    out["verify_walls"] = rows(f"""
      SELECT host, wall_verbatim FROM `{DS}.in_dc_actions_verify_walls` ORDER BY host""")

# coverage: which counties were actually assessed, versus never searched
for t, key in (("in_ordinances_dc_coverage_v2", "coverage"),
               ("in_ordinances_amlegal_coverage_v2", "amlegal_coverage"),
               ("in_ordinances_publisher_inventory_v2", "publishers"),
               ("in_ordinances_dc_county_sites_v2", "county_sites")):
    if has(t):
        cols = [s.name for s in client.get_table(f"{DS}.{t}").schema]
        out[key] = rows(f"SELECT {', '.join(cols[:14])} FROM `{DS}.{t}` LIMIT 400")

# The caveat is COMPUTED, not typed. An earlier version hard-coded "Boone and Miami" and was
# already wrong the moment the 92-county sweep landed 13 more verified counties.
_ca = out.get("county_actions", [])
_verified = [a for a in _ca if a["evidence_grade"] == "VERIFIED_AT_OFFICIAL_SOURCE"]
_restrictive = [a for a in _verified if a["action_type"] in
                ("moratorium", "ban-prohibition", "adopted-uncodified-ordinance")]
_cov = out.get("county_action_coverage", [])
out["caveat"] = (
    "The row count is not the finding. Of 153 candidate rows only 7 name a data centre, and "
    "triage of the remaining 146 admits 19 sections across 9 jurisdictions — Indiana's genuine "
    "CODIFIED data-centre corpus is a handful of sections in two counties. "
    f"The decision-relevant regulation is not codified at all. A sweep of all {len(_cov) or 92} "
    f"county websites found {len(_ca)} land-use actions, of which {len(_verified)} are verified at "
    f"the government's own source and {len(_restrictive)} of those are restrictive (moratorium, "
    "ban, or adopted-but-uncodified ordinance). None of it appears in any code library. A "
    "codified-only reading renders Boone — the LEAP district, under a one-year moratorium — as "
    "SILENT, and misses Lake County Ordinance 2590, which prohibits data centres in every "
    "business zoning district. "
    f"The remaining {len(_ca) - len(_verified)} rows are REPORTED_NEEDS_VERIFICATION: a worklist "
    "carried by news or aggregators only. They are shown separately and must never be read as "
    "posture.")

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
if "county_actions" in out:
    print(f"  county-website actions: {len(out['county_actions'])} "
          f"({len(_verified)} VERIFIED, {len(_ca) - len(_verified)} leads) "
          f"across {len(_cov)} counties assessed")
    for s in out["county_action_summary"]:
        print(f"    {s['action_type']:30s} verified={s['verified']:>3} lead={s['lead_only']:>3}")
if "verified_postures" in out:
    vp, ul, cx = out["verified_postures"], out["unresolved_leads"], out["corrections"]
    print(f"  official-source verification: {len(vp)} postures now RENDERABLE · "
          f"{len(ul)} still unresolved · {len(cx)} CORRECTIONS")
    for c in cx:
        print(f"    CORRECTION {c['county']}: {str(c['date_note'])[:82]}")
    print(f"  total verified county postures = {len(_verified)} (sweep) + {len(vp)} (verified) "
          f"= {len(_verified) + len(vp)}")
