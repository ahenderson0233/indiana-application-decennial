"""WIRE-NEXT batch 5 (zeros-class genuine finds): widened predicates OR'd across each
table's state-ish columns (TRIM + spelling variants). Subject-check pending notes carried."""
import re
from collections import defaultdict
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
E = "`energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")

TARGETS = ["si_d11_entity_dissolution", "gov_surplus_nces", "si_d25_stb_abandonment_state",
           "nfirs_fireincident_2022", "si_d27_ucc_lapse_v2", "txexp_miso_mtep_appendix_a_status"]
STATE_COL = re.compile(r"state|(?:^|_)st(?:$|_)|stusps")
cols = defaultdict(list)
for r in client.query("SELECT table_id, column_name FROM `energy-platfrom.energy.column_census`"):
    if r.table_id in TARGETS and STATE_COL.search(r.column_name.lower()):
        cols[r.table_id].append(r.column_name)
WIDE = "'IN','INDIANA','18','IND','IND.','INDIANA ','IN ','18.0'"
for t in TARGETS:
    cc = cols.get(t, [])[:3]
    if not cc:
        print(f"SKIP {t}: no state-ish column"); continue
    pred = " OR ".join(f"UPPER(TRIM(CAST(`{c}` AS STRING))) IN ({WIDE})" for c in cc)
    dest = "in_" + t
    sql = f"CREATE OR REPLACE TABLE `{DS}.{dest}` AS SELECT * FROM {E}.{t}` WHERE {pred}"
    dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
    client.query(sql).result()
    n = list(client.query(f"SELECT COUNT(*) AS n FROM `{DS}.{dest}`"))[0].n
    client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
      VALUES ('{dest}','energy.{t}','widened-predicate clip ({", ".join(cc)})', {n},
              {dry.total_bytes_processed/1e9:.3f}, CURRENT_TIMESTAMP(),
              'zeros-class genuine find; SUBJECT-CHECK PENDING before any feature claims signal semantics')""").result()
    print(f"{dest}: {n:,}")
print("WIRE-NEXT BATCH 5 COMPLETE")
