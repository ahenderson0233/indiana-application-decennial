"""G161: WHAT ELSE IN `energy` CARRIES INDIANA CONTENT THAT WE DO NOT ALREADY CLIP?

⛔ THE RULE THIS IMPLEMENTS. Operator, 2026-08-17 (G25): check the warehouse before you explore or
scrape. ⚠ And the sharpened version, earned twice: **search by CONTENT, not by the name a source
ought to have.** We "held no land banks" for weeks; we held two, filed as `landbank` and `surplus`.
A table named for a utility is not a clip of that utility's home state — `hca_aep_im_mi_*` is Ohio
and Michigan. A name grep cannot see either shape.

⭐ WHAT IT DOES. Enumerates every `energy` table carrying a state-like column, counts its INDIANA
rows by that column's own value vocabulary ('IN' / 'Indiana' / '18'), and reports the ones with
Indiana content that NOTHING in `indiana_app` currently clips.

⚠ THE VALUE-VOCABULARY TRAP IS THE POINT. `si_d1_sri_taxsale_listings` spells the state 'Indiana'
where every other parent spells it 'IN', and a predicate that assumed 'IN' matched ZERO rows and
passed its own assertion. This probe accepts all three spellings and reports which one hit.

RE-SCRAPE COMMAND: python scripts/sweep_energy_indiana_si.py
⛔ READ-ONLY. Writes nothing. `energy` is READ-ONLY to this workstream.
"""
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

EN = "energy-platfrom.energy"
DS = "energy-platfrom.indiana_app"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "docs", "ENERGY_INDIANA_SWEEP.json")
client = bigquery.Client(project="energy-platfrom")

STATE_COLS = ("state", "state_abbr", "state_code", "st", "statename", "state_name",
              "property_state", "projectstate", "borrstate", "debtor_state",
              "filer_state", "situs_state", "owner_state", "mailing_state")

# ⛔ these are ours, or working tables, or already-known non-sources - excluded from the report
# rather than from the probe, so the count stays honest.
SKIP_PREFIX = ("_", "in_", "orennia_", "be_ustest_")


def state_col_map():
    """table -> the FIRST state-like column it carries, by ordinal position."""
    q = f"""
    SELECT table_name, column_name,
           ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY ordinal_position) rn
    FROM `{EN}`.INFORMATION_SCHEMA.COLUMNS
    WHERE LOWER(column_name) IN UNNEST(@c)
    """
    rows = client.query(q, job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ArrayQueryParameter("c", "STRING", list(STATE_COLS))])).result()
    return {r.table_name: r.column_name for r in rows if r.rn == 1}


def already_clipped():
    """Every energy object named as a SOURCE by something we hold in indiana_app."""
    got = set()
    q = f"SELECT source FROM `{DS}._registry` WHERE source IS NOT NULL"
    for r in client.query(q).result():
        s = (r.source or "")
        for tok in s.replace(",", " ").replace("`", " ").split():
            if "energy." in tok:
                got.add(tok.split("energy.")[-1].strip(" .;)"))
    return got


def probe(batch):
    """One UNION ALL per batch: Indiana rows by each of the three spellings."""
    parts = []
    for t, col in batch:
        parts.append(f"""
        SELECT '{t}' AS t, '{col}' AS c,
               COUNTIF(UPPER(CAST(`{col}` AS STRING)) = 'IN') AS n_in,
               COUNTIF(UPPER(CAST(`{col}` AS STRING)) = 'INDIANA') AS n_full,
               COUNTIF(CAST(`{col}` AS STRING) = '18') AS n_fips,
               COUNT(*) AS n_all
        FROM `{EN}.{t}`""")
    return list(client.query(" UNION ALL ".join(parts)).result())


def main():
    smap = state_col_map()
    clipped = already_clipped()
    print("=" * 104)
    print("G161 - EVERY `energy` TABLE WITH INDIANA CONTENT, AND WHETHER WE CLIP IT")
    print("=" * 104)
    print(f"  {len(smap):,} table(s) carry a state-like column")
    print(f"  {len(clipped):,} energy object(s) are named as a SOURCE by something in indiana_app\n")

    items = sorted(smap.items())
    hits, failed = [], []
    B = 40
    for i in range(0, len(items), B):
        batch = items[i:i + B]
        try:
            for r in probe(batch):
                n = max(r.n_in, r.n_full, r.n_fips)
                if n > 0:
                    hits.append({
                        "table": r.t, "state_col": r.c, "indiana_rows": n, "total_rows": r.n_all,
                        "vocabulary": ("IN" if r.n_in == n else "Indiana" if r.n_full == n else "18"),
                        "clipped": r.t in clipped,
                    })
        except Exception as e:
            # ⚠ one bad table must not kill the sweep - record it and carry on.
            for t, col in batch:
                failed.append(t)
            print(f"  [batch {i // B}] {str(e)[:110]}")
        print(f"  probed {min(i + B, len(items)):>4} of {len(items)}  ...  {len(hits)} with Indiana rows",
              end="\r")

    print(" " * 90, end="\r")
    hits.sort(key=lambda h: -h["indiana_rows"])
    unclipped = [h for h in hits
                 if not h["clipped"] and not h["table"].startswith(SKIP_PREFIX)]

    print(f"\n  {len(hits)} table(s) hold Indiana rows · {len(unclipped)} of them are NOT clipped\n")
    print(f"  {'table':56} {'IN rows':>12} {'of total':>13}  vocab")
    print("  " + "-" * 100)
    for h in unclipped[:80]:
        print(f"  {h['table'][:56]:56} {h['indiana_rows']:>12,} {h['total_rows']:>13,}  {h['vocabulary']}")
    if len(unclipped) > 80:
        print(f"  ... and {len(unclipped) - 80} more, all in {os.path.relpath(OUT, REPO)}")
    if failed:
        print(f"\n  ⚠ {len(failed)} table(s) could not be probed (type or permission): "
              f"{', '.join(failed[:6])}")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps({
        "probed": len(items), "with_indiana": len(hits), "unclipped": len(unclipped),
        "unprobeable": failed, "hits": hits,
    }, indent=1))
    print(f"\n  wrote {os.path.relpath(OUT, REPO)}")
    print("=" * 104)


if __name__ == "__main__":
    main()
