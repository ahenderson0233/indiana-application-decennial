"""G167: COLUMN BY COLUMN — DOES ANY FIELD WE HOLD AND DO NOT READ CARRY A SIGNAL?

⛔ THE QUESTION NOTHING WAS ASKING. Operator, 2026-08-22b: *"Are all of our tables 100% populated
with ALL columns, enabling us to gather event dates, add contextual evidence … and the potential of
those tables to have other SI signals displayed within them?"*

⭐ HALF OF THAT IS ALREADY ANSWERED AND MUST NOT BE RE-DONE. `audit_si_upstream_width.py` proves
all 18 clips are FULL WIDTH against their `energy` parent; `audit_si_column_capture.py` proves the
8 direct-scrape sources match their PUBLISHER. **We hold the columns.** The unanswered half is what
is IN them — G152 widened 18 clips and the per-column question was never put to any of them.

⚠ WHY A COLUMN COUNT CANNOT ANSWER IT. `in_si_up_indy_code` gained 5 columns over the sibling the
builder actually reads, and every one was `_source_url` / `county_name` / `geoid` /
`publisher_state` / `si_signal` — provenance and housekeeping. A wider clip is not a richer one,
and only reading the columns tells you which you have.

⭐ WHAT THIS REPORTS, per column of every full-width clip:
    · **null rate** — a 100%-null column is held and empty, which is the `parcel_owner` shape:
      declared by the schema, useless in fact, and worth knowing so nobody re-checks it hopefully.
    · **distinct count** — 1 distinct value is a constant, not data.
    · **DATE?** — parses as a date, ISO or `MM/DD/YYYY` or epoch-millis. ⚠ An event date is the
      single most valuable thing a clip can add, because G145 made dates renderable.
    · **STATUS?** — a low-cardinality string vocabulary. *A status column is where a hidden signal
      lives* — `saleStatusDescription` hid D4 inside D1 for a whole session.
    · **MONEY?** — a numeric column whose name says amount/value/price. D14's
      `grosschargeoffamount` is why that clip was worth wiring at all.

⛔ IT RANKS, IT DOES NOT DECIDE. Every candidate still needs a D-code, an admission rule and a
written "so what" before it ships, and a source that cannot earn one is a refusal to record. This
audit exists so that judgement is made against measurements instead of against column names.

RE-SCRAPE COMMAND: python scripts/audit_si_column_value.py
⛔ READ-ONLY. Writes one JSON report.
"""
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.cloud import bigquery

from si_upstream_sources import REPAIRS, SOURCES, YEAR_GAPS

DS = "energy-platfrom.indiana_app"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "docs", "SI_COLUMN_VALUE.json")
SCRIPTS = os.path.join(REPO, "scripts")
client = bigquery.Client(project="energy-platfrom")

# provenance/housekeeping — held for good reason, never a signal. Named so the report can say
# "nothing here" honestly instead of padding the candidate list.
HOUSEKEEPING = {"_source_url", "source_url", "_pulled_at", "pulled_at", "_derived_at",
                "_snapshot_date", "snapshot_date", "objectid", "globalid", "_agis_key",
                "publisher_state", "state", "state_code", "geoid", "county_name", "si_signal",
                "_sheet", "_page_url", "_page_year", "_page_label", "row_scope", "is_test_record",
                "state_source", "shape_starea", "shape_stlength", "geometry_geojson"}
MONEY = ("amount", "amt", "value", "price", "bid", "cost", "usd", "balance", "loss", "receipts",
         "paid", "assessed", "approval", "chargeoff")

# ⛔ GEOGRAPHY CANNOT BE CAST TO STRING and the first run died on in_si_up_vacancy_derived with
# "Invalid cast from GEOGRAPHY to STRING". Skipped by TYPE, not by name — a geography column is
# never a date, a status or a money field, so nothing is lost by not profiling it.
UNPROFILABLE = {"GEOGRAPHY", "STRUCT", "ARRAY", "JSON", "BYTES", "INTERVAL"}

# ⚠ TABLES ALREADY REFUSED, WITH THE REASON. Their columns are real but they can never become a
# parcel signal, so listing 78 money columns from a trustee financial return crowds out the two
# findings that matter. They are still PROFILED (the report keeps them); they are excluded from the
# CANDIDATE ranking, which is a worklist and has to be actionable.
REFUSED = {
    "in_ustp_ch7_tfr": "office-month financial totals; no debtor, no address (G163)",
    "in_si_up_bankruptcy": "0 of 90 dockets are businesses - named private individuals (G163)",
    "in_si_up_iocs_court": "no commercial/residential split; refused_residential (G165)",
    "in_si_up_vacancy_derived": "footprint absence is not seller intent - operator ruling (G163)",
    "in_si_up_warn_multistate": "every address column NULL on all 1,220 Indiana rows (G152)",
}


def clips():
    out = [t for _, _, _, t, _ in SOURCES]
    out += [t for t, _, _, _ in REPAIRS]
    out += [t for t, _, _, _ in YEAR_GAPS]
    return sorted(set(out))


def read_by_a_builder():
    """Column names that appear anywhere in a build script — a crude but useful 'already used'."""
    blob = []
    for fn in os.listdir(SCRIPTS):
        if fn.startswith("build_") and fn.endswith(".py"):
            blob.append(io.open(os.path.join(SCRIPTS, fn), encoding="utf-8",
                                errors="replace").read())
    return "\n".join(blob)


def main():
    used = read_by_a_builder()
    print("=" * 104)
    print("G167 - EVERY COLUMN OF EVERY FULL-WIDTH SI CLIP, AND WHETHER IT CARRIES ANYTHING")
    print("=" * 104)

    report, candidates = {}, []
    for tbl in clips():
        try:
            t = client.get_table(f"{DS}.{tbl}")
        except Exception:
            continue
        cols = [f for f in t.schema
                if f.name.lower() not in HOUSEKEEPING and f.field_type not in UNPROFILABLE]
        if not cols or t.num_rows == 0:
            continue
        # one query per table: null rate + distinct + date-parse per column
        sel = []
        for f in cols:
            n = f.name
            sel.append(f"COUNTIF(`{n}` IS NULL) AS `n__{n}`")
            sel.append(f"COUNT(DISTINCT CAST(`{n}` AS STRING)) AS `d__{n}`")
            sel.append(
                f"COUNTIF(SAFE.PARSE_DATE('%Y-%m-%d', CAST(`{n}` AS STRING)) IS NOT NULL "
                f"OR SAFE.PARSE_DATE('%m/%d/%Y', CAST(`{n}` AS STRING)) IS NOT NULL "
                f"OR SAFE.PARSE_DATE('%m-%d-%Y', CAST(`{n}` AS STRING)) IS NOT NULL "
                f"OR (SAFE_CAST(`{n}` AS FLOAT64) BETWEEN 3.15e11 AND 2.2e12)) AS `t__{n}`")
        try:
            r = list(client.query(
                f"SELECT COUNT(*) AS _n, {', '.join(sel)} FROM `{DS}.{tbl}`").result())[0]
        except Exception as e:
            print(f"  ⚠ {tbl}: {str(e)[:80]}")
            continue

        rows = r["_n"]
        entries = []
        for f in cols:
            n = f.name
            nulls, dist, dates = r[f"n__{n}"], r[f"d__{n}"], r[f"t__{n}"]
            filled = rows - nulls
            e = {
                "column": n, "type": f.field_type,
                "null_pct": round(100 * nulls / rows, 1) if rows else 100.0,
                "distinct": dist,
                "is_date": bool(rows and dates / rows > 0.5),
                "is_status": bool(f.field_type == "STRING" and 1 < dist <= 40 and filled > rows * 0.5),
                "is_money": bool(any(m in n.lower() for m in MONEY)),
                "read_by_a_builder": n in used,
            }
            entries.append(e)
            # ⭐ a CANDIDATE is: populated, not already read, and carrying a date, a status or money
            if (e["null_pct"] < 50 and not e["read_by_a_builder"]
                    and (e["is_date"] or e["is_status"] or e["is_money"])
                    and e["distinct"] > 1 and tbl not in REFUSED):
                candidates.append({"table": tbl, **e})
        report[tbl] = {"rows": rows, "columns": entries}
        allnull = sum(1 for e in entries if e["null_pct"] >= 99.9)
        print(f"  {tbl:32} {rows:>9,} rows · {len(entries):>3} cols · "
              f"{allnull:>2} are ~100% NULL")

    print("\n" + "=" * 104)
    print(f"CANDIDATE COLUMNS — populated, not read by any builder, carrying a DATE / STATUS / MONEY")
    print("=" * 104)
    candidates.sort(key=lambda c: (not c["is_date"], not c["is_money"], c["null_pct"]))
    print(f"  {'table':30} {'column':26} {'null%':>6} {'distinct':>9}  what")
    print("  " + "-" * 96)
    for c in candidates[:40]:
        what = ",".join(k for k, v in
                        (("DATE", c["is_date"]), ("STATUS", c["is_status"]), ("MONEY", c["is_money"]))
                        if v)
        print(f"  {c['table'][:30]:30} {c['column'][:26]:26} {c['null_pct']:>6} "
              f"{c['distinct']:>9,}  {what}")
    print(f"\n  {len(candidates)} candidate column(s) across {len(report)} clip(s)")
    # ⛔ SAY WHAT WAS EXCLUDED AND WHY. A worklist that silently omits tables reads as "nothing
    # here", which is the absence-of-evidence defect this project has paid for repeatedly.
    print(f"\n  ⚠ {len(REFUSED)} clip(s) are PROFILED in the JSON but excluded from this ranking,")
    print("    because the table is already refused and its columns cannot become a parcel signal:")
    for k, why in sorted(REFUSED.items()):
        print(f"     {k:28} {why}")
    print("  ⛔ A CANDIDATE IS NOT A SIGNAL. Each needs a D-code, an admission rule and a written")
    print("     \"so what\" — and a source that cannot earn one is a refusal to record, not a gap.")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"clips": report, "candidates": candidates}, indent=1))
    print(f"\n  wrote {os.path.relpath(OUT, REPO)}")
    print("=" * 104)


if __name__ == "__main__":
    main()
