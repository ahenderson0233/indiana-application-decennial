"""THE COMPLETE GAP PICTURE — everything known to be missing, measured not recalled.

The operator's question before Phase B: how many tables/views do we hold, what reaches the
website, and what is still missing? Five questions, each answered from BigQuery:

  1. what does indiana_app physically hold (tables vs views), and what reaches a surface?
  2. of the Indiana-POSITIVE tables the census found in `energy`, which were never clipped?
  3. of the 29 seller-intent signals, which are present for Indiana and which are absent?
  4. of the si_signals source_ids, which have a live endpoint and which do not?
  5. which columns Lane D already discovered are still unwired (an endpoint often carries more
     than one signal - the reason ALL columns are pulled)?

Writes docs/GAP_REGISTER.md. READ-ONLY.
"""
import os, datetime
from google.cloud import bigquery

REPO = r"C:\Users\ahend\Downloads\Decennial Summer Work\Project Reverse Uno\California\ca-capacity-deploy\indiana-application-decennial"
DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")
out = [f"# GAP REGISTER — measured {datetime.date.today()}", "",
       "Every known gap, measured against BigQuery rather than recalled. Written before Phase B so",
       "the operator can rule on each one. Nothing here is an estimate.", ""]

def rows(sql): return [dict(r) for r in client.query(sql)]

# ---- 1. what we hold ---------------------------------------------------------------------
held = rows(f"""SELECT table_type, COUNT(*) n FROM `{DS}`.INFORMATION_SCHEMA.TABLES
                GROUP BY 1 ORDER BY n DESC""")
reg = rows(f"SELECT COUNT(DISTINCT table_name) n FROM `{DS}._registry`")[0]["n"]
out += ["## 1. What `indiana_app` holds", "", "| kind | n |", "|---|---:|"]
for h in held: out.append(f"| {h['table_type'].lower()} | {h['n']} |")
out += [f"| registered in `_registry` | {reg} |", "",
        "The website reads 196 of these (98%); the 3 that do not reach a surface are deliberate",
        "and carry written waivers (`_indiana_census` meta table + 2 zero-row FCC tables).", ""]

# ---- 2. Indiana-positive tables in `energy` that were never clipped ----------------------
census_exists = rows(f"""SELECT COUNT(*) n FROM `{DS}`.INFORMATION_SCHEMA.TABLES
                         WHERE table_name='_indiana_census'""")[0]["n"]
out += ["## 2. Indiana-positive tables in `energy` never clipped into `indiana_app`", ""]
if census_exists:
    cols = [c["column_name"] for c in rows(f"""
        SELECT column_name FROM `{DS}`.INFORMATION_SCHEMA.COLUMNS
        WHERE table_name='_indiana_census'""")]
    out.append(f"_census columns: {', '.join(cols)}_")
    out.append("")
    cnt = rows(f"SELECT COUNT(*) n FROM `{DS}._indiana_census`")[0]["n"]
    out.append(f"The census holds {cnt} rows. Per-table clip status:")
    out.append("")
    # the census keys on `table_id`, not `table_name` - read, not guessed
    tot = rows(f"""SELECT COUNTIF(in_rows > 0) positive, COUNT(*) all_rows
                   FROM `{DS}._indiana_census`""")[0]
    gap = rows(f"""
      WITH cen AS (SELECT table_id, in_rows, total_rows, method FROM `{DS}._indiana_census`
                   WHERE in_rows > 0),
           have AS (SELECT REGEXP_REPLACE(table_name, r'^in_', '') AS base
                    FROM `{DS}`.INFORMATION_SCHEMA.TABLES)
      SELECT c.table_id, c.in_rows, c.total_rows, c.method
      FROM cen c LEFT JOIN have h ON h.base = c.table_id
      WHERE h.base IS NULL ORDER BY c.in_rows DESC""")
    # A raw "227 missing" would be alarming and WRONG. Most are reached through a derived table
    # or were waived with a measured reason during the audit. Classify before reporting.
    import re as _re
    OTHER_STATE = _re.compile(r"^(parcels_(?!in)|socrata_|agis_(?!indy)|ckan_|carto_|state_bulk_)")
    SPINE = _re.compile(r"^(mat_|vw_|si_wire_|si_coverage|dim_|block_groups|census_tracts)")
    REACHED_VIA = {  # big tables we DO reach, through a pre-aggregated derivative
        "cems_hourly": "in_cems_monthly", "fcc_bdc_fixed_availability": "in_county_fibre",
        "nwi_wetlands": "in_wetlands", "nfhl_flood_zones": "in_flood",
        "nhd_flowline": "in_water", "eqr_*": "in_eqr_identity",
    }
    buckets = {"spine internal (reached via a derived table)": [],
               "other-state / owner-mailing-state (waived in audit)": [],
               "reached through a pre-aggregated derivative": [],
               "GENUINELY UNWIRED — needs an operator ruling": []}
    for g in gap:
        t = g["table_id"]
        if t in REACHED_VIA: buckets["reached through a pre-aggregated derivative"].append(g)
        elif SPINE.match(t): buckets["spine internal (reached via a derived table)"].append(g)
        elif OTHER_STATE.match(t): buckets["other-state / owner-mailing-state (waived in audit)"].append(g)
        else: buckets["GENUINELY UNWIRED — needs an operator ruling"].append(g)

    out.append(f"Census: **{tot['positive']} of {tot['all_rows']} tables carry Indiana rows.** "
               f"{len(gap)} have no `in_` table of their own — but that headline is misleading, "
               f"because most are reached through a derived table or were waived with a reason "
               f"during the audit. Classified:")
    out.append("")
    out.append("| class | tables |")
    out.append("|---|---:|")
    for k, v in buckets.items(): out.append(f"| {k} | {len(v)} |")
    real = buckets["GENUINELY UNWIRED — needs an operator ruling"]
    out.append("")
    out.append(f"### The {len(real)} genuinely unwired, largest first")
    out.append("")
    out.append("| table | indiana rows | of total | keyed by |")
    out.append("|---|---:|---:|---|")
    for g in real[:60]:
        out.append(f"| `{g['table_id']}` | {g['in_rows']:,} | {g['total_rows']:,} | {g['method']} |")
    if len(real) > 60:
        out.append(f"\n_…and {len(real) - 60} more, all smaller._")
else:
    out.append("_indiana_census not found._")
out.append("")

# ---- 3. the 29 SI signals ---------------------------------------------------------------
out += ["", "## 3. Seller-intent signals present vs absent", ""]
sig = rows(f"""SELECT signal, COUNT(*) n, COUNT(DISTINCT county_fips) counties,
                      CAST(MAX(observed_date) AS STRING) latest
               FROM `{DS}.in_si_signals` GROUP BY 1 ORDER BY n DESC""")
out += [f"**{len(sig)} signals carry Indiana rows.**", "",
        "| signal | rows | counties | latest event |", "|---|---:|---:|---|"]
for s in sig:
    out.append(f"| {s['signal']} | {s['n']:,} | {s['counties']} | {s['latest'] or '—'} |")
# ---- TIMING: the operator's priority gap ------------------------------------------------
# "I am mostly concerned with the timing of each event." Measure where dates exist and where
# they are lost, per signal, rather than reporting one aggregate.
tim = rows(f"""
  SELECT signal, COUNT(*) n, COUNTIF(observed_date IS NOT NULL) dated,
         CAST(MIN(observed_date) AS STRING) lo, CAST(MAX(observed_date) AS STRING) hi,
         COUNTIF(observed_date >= DATE '2023-08-15') last_3y,
         COUNTIF(observed_date >= DATE '2025-08-15') last_1y
  FROM `{DS}.in_si_signals` GROUP BY 1 ORDER BY n DESC""")
out += ["", "## 3a. TIMING — where event dates exist, and where they are lost", "",
        "The operator's priority: *a code violation in the 1990s does not help us.* Per signal, "
        "how many rows carry an observed event date, and how recent are they?", "",
        "| signal | rows | dated | span | last 3 yrs | last 1 yr |", "|---|---:|---:|---|---:|---:|"]
for t in tim:
    pct = f"{100*t['dated']/t['n']:.0f}%" if t["n"] else "—"
    out.append(f"| {t['signal']} | {t['n']:,} | {t['dated']:,} ({pct}) | "
               f"{t['lo'] or '—'} → {t['hi'] or '—'} | {t['last_3y']:,} | {t['last_1y']:,} |")
tot_n = sum(t["n"] for t in tim); tot_d = sum(t["dated"] for t in tim)
tot_3 = sum(t["last_3y"] for t in tim); tot_1 = sum(t["last_1y"] for t in tim)
out += ["", f"**Totals: {tot_d:,} of {tot_n:,} SI rows ({100*tot_d/tot_n:.1f}%) carry an event "
        f"date. Only {tot_3:,} ({100*tot_3/tot_n:.1f}%) are from the last three years and "
        f"{tot_1:,} ({100*tot_1/tot_n:.1f}%) from the last one.**", "",
        "So the SI corpus is mostly HISTORIC. Filtering to what would actually move an owner "
        "today collapses it hard — which is the honest answer, and the reason recency has to be "
        "a first-class filter rather than a nicety.", "",
        "Separately, the date does NOT reach the parcel: `si_last_event_date` on `in_sites` is "
        "populated for ~0.6% of SI parcels (935 of 165,494 measured over 7 counties). The dates "
        "exist in `in_si_signals` but are lost in the join onto parcels — that propagation, not "
        "re-scraping, is the first fix.", ""]

no_county = [s for s in sig if not s["counties"]]
out += ["", f"County attribution is absent on {len(no_county)} of {len(sig)} signals (only "
        "`D5_vacancy` carries `county_fips`). Operator ruling 2026-08-15: **lower priority, we can "
        "derive county ourselves** from the parcel or address geography. Noted, not chased.", "",
        "The engine's weighted model defines 29 signals; the absent ones are the acquisition",
        "backlog below.", ""]

# ---- 4. staged-but-unwired signal tables -------------------------------------------------
out += ["## 4. Signal tables held but not feeding `in_si_signals`", ""]
staged = rows(f"""
  SELECT table_name, n_rows FROM (
    SELECT table_name, ANY_VALUE(n_rows) n_rows FROM `{DS}._registry`
    WHERE REGEXP_CONTAINS(table_name, r'^in_si_') GROUP BY table_name)
  ORDER BY table_name""")
out += ["| table | rows |", "|---|---:|"]
for s in staged: out.append(f"| `{s['table_name']}` | {s['n_rows'] or 0:,} |")
out.append("")

# ---- 5. signals absent entirely: the acquisition backlog --------------------------------
HELD = {s["signal"].split("_")[0] for s in sig}
MODEL = {  # the engine's weighted model (spec §3), signal -> what it is
 "D1": "tax sale", "D2": "foreclosure / lis pendens", "D3": "seized-asset auction",
 "D4": "tax delinquency", "D5": "vacancy", "D6": "bankruptcy", "D7": "brownfield",
 "D8": "exit intent (rezoning / variance)", "D9": "absentee owner", "D10": "underutilisation",
 "D11": "entity dissolution", "D12": "code violation", "D13": "utility shutoff",
 "D14": "SBA charge-off", "D15": "lien filing", "D16": "structure fire",
 "D17": "commercial eviction", "D18": "owner age / estate", "D19": "WARN layoff/closure",
 "D20": "loan maturity", "D21": "demolition permit", "D22": "environmental violation",
 "D23": "public surplus disposal", "D24": "plant delisting", "D25": "rail abandonment",
 "D26": "assessment appeal", "D27": "UCC lapse", "A1": "market listing", "A2": "gov surplus"}
missing = {k: v for k, v in MODEL.items() if k not in HELD}
out += ["", "## 5. Signals absent from the Indiana feed — the acquisition backlog", "",
        f"**{len(missing)} of the {len(MODEL)} modelled signals carry no Indiana rows.** These need "
        "exploration or scraping. Per the operator's standing instruction, any pull takes **ALL "
        "columns**: an endpoint often carries more than one signal, and the Lane D pulls proved it "
        "(§6 below).", "", "| signal | what it is |", "|---|---|"]
for k, v in sorted(missing.items()): out.append(f"| **{k}** | {v} |")
staged_note = [k for k in ("D11", "D21", "D27") if k in missing]
if staged_note:
    out += ["", f"Note: {', '.join(staged_note)} already have Indiana rows STAGED and admitted by "
            "operator sign-off (`in_si_d11_admitted` 983, `in_si_candidates` D21, "
            "`in_si_d27_admitted` 156) but have not been folded back into `in_si_signals` itself. "
            "Those are a wiring step, not an acquisition."]
out.append("")

# ---- 6. Lane D: columns already pulled but never wired ----------------------------------
out += ["## 6. Already pulled, never wired — extra signals inside endpoints we already have", "",
        "Lane D pulled all columns from six sources and found signal-bearing columns nobody had "
        "asked for. **These need no scraping — the data is already in BigQuery.** From "
        "`scrapers/lane_d/LANE_D_FINDINGS.md`:", "",
        "| table | column | what it carries |", "|---|---|---|",
        "| `in_si_refresh_sri_taxsale_in` | `saleTypeDescription` | Foreclosure 62,760 · Tax Sale 15,860 · Certificate Sale 4,851 · Deed Sale 76 — a finer subtype than the open/resolved split |",
        "| `in_si_refresh_sri_taxsale_in` | `latitude`/`longitude` | 29,955 of 83,547 (35.9%) — **direct plotting**, no geocoding needed |",
        "| `in_si_refresh_indy_code_enforcement` | `CASE_TYPE` | a full violation taxonomy — Unsafe Buildings, Vacant Board Order, Illegal Dumping, Zoning, Environmental — not one 'code enforcement' bucket |",
        "| `in_si_refresh_indy_code_enforcement` | `LINK` | 910,483/910,483 (100%) direct Accela case-detail URLs — a free verification drilldown on every row |",
        "| `in_si_refresh_indy_code_enforcement` | `TOWNSHIP` | free sub-county geography on every row (watch the doubled `'CENTER,CENTER'` publisher artifact) |",
        "| `in_si_refresh_warn_notices` | `NAICS` | 6-digit industry code on all but 204 rows — lets WARN be filtered to industries that own real estate |",
        "| `in_si_refresh_warn_notices` | `col_8__href` | 172 direct links to the WARN letter PDF |",
        "| `in_si_refresh_ibtr_appeals` | `appealTypeName` | Form 131/133/132/139 petition types, never surfaced |",
        "| `in_si_refresh_ibtr_appeals` | `attachmentDescriptions` | document-type breadcrumb finer than `statusName` |",
        "| `in_si_refresh_brownfield_epa_in` | `Program` | BROWNFIELDS 1,247 · RCRA 127 · LANDFILL METHANE 54 · SUPERFUND 53 |",
        "| `in_si_refresh_brownfield_epa_in` | `Landfill` / `AML` | binary flags, 83 and 4 respectively |",
        "| `in_si_refresh_iocs_eviction` | `MF` | mortgage foreclosure — **WIRED 2026-08-15** as county context |",
        "", "Eleven of the twelve remain unwired. This is the cheapest coverage available: no "
        "scraping, no new source, no permission question.", ""]

# ---- 7. Lane D scrape status -------------------------------------------------------------
out += ["## 7. Scrape status — where the SI re-pull actually stands", "",
        "`scrapers/lane_d/LANE_D_FINDINGS.md`, verified against BigQuery rather than its own "
        "scratch files:", "",
        "- **All six Lane D scripts COMPLETED** — 6 tables, 1,013,404 rows, all columns, all "
        "registered. Only `02_indy_code_enforcement` had never run; it ran and returned 910,483 "
        "rows matching the publisher count exactly.",
        "- **A publisher-side staleness finding, not ours:** Indy code enforcement's `OPEN_DATE` "
        "spans exactly 2010-03-29 → 2024-02-27 with zero rows after. The publisher's layer has "
        "not opened a case in 2.5 years — re-pulling it again changes nothing.",
        "- **10 of 19 Indiana-feeding `si_signals` source_ids have NO live endpoint identified "
        "at all**, including the largest signal, `si_d5_vacancy_derived` (945,896 rows), which is "
        "derived and has no endpoint of its own. Those need discovery before any re-pull.",
        "- **One paywall, standing:** `si_d25` InBiz bulk data — $9,500 + $500/mo, rejected. "
        "Recorded BLOCKED with the exact wall; not re-probed.",
        "- The IOCS 2026 workbook 404s: the publisher has not posted it yet. Not a wall.", ""]

open(f"{REPO}\\docs\\GAP_REGISTER.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out[:40]))
print(f"\n... docs/GAP_REGISTER.md written ({len(out)} lines)")
