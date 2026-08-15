"""Lane D step 1: build the refresh target list.

Read-only against `energy-platfrom.energy` (NEVER written to):
  (a) registry_sources rows whose endpoint or name look Indiana-shaped
  (b) si_signals source_id x state='IN' rollup (what currently FEEDS Indiana)
Then cross-reference (b) against (a) by source_id/table name so we know, for each
source_id that feeds Indiana today, whether we can find its live endpoint to re-pull.

Writes only a JSON snapshot to _scratch/ (no BigQuery writes in this step).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lane_d_util as u

client = u.bq_client()

# ---------------------------------------------------------------------------
# (a) registry_sources: Indiana-shaped endpoints
# ---------------------------------------------------------------------------
q_registry = r"""
SELECT source_id, source_name, status, status_measured, endpoint, endpoint_raw, endpoint_kind,
       object_names, access, notes, domain, origin, geography_state, geography_county,
       part_gate, priority, category, acquisition_method, method, validation, validation_error,
       last_http_status, last_source_count, measured_rows, expected_count, last_validated_at
FROM `energy-platfrom.energy.registry_sources`
WHERE endpoint IS NOT NULL
  AND (REGEXP_CONTAINS(LOWER(source_name), r'indiana|indianapolis|marion|indy')
       OR REGEXP_CONTAINS(LOWER(endpoint), r'indiana|indy|\bin\b|in\.gov')
       OR REGEXP_CONTAINS(LOWER(COALESCE(geography_state,'')), r'^in$|indiana'))
"""
print("Running registry query...")
registry_rows = [dict(r) for r in client.query(q_registry).result()]
print(f"registry_sources Indiana-shaped rows: {len(registry_rows)}")

# ---------------------------------------------------------------------------
# (b) si_signals: what currently feeds Indiana
# ---------------------------------------------------------------------------
q_si = r"""
SELECT source_id, COUNT(*) n, MAX(observed_date) latest, MIN(observed_date) earliest
FROM `energy-platfrom.energy.si_signals`
WHERE state = 'IN'
GROUP BY 1
ORDER BY n DESC
"""
print("Running si_signals IN rollup...")
si_rows = [dict(r) for r in client.query(q_si).result()]
print(f"si_signals source_ids feeding IN: {len(si_rows)}")

# make JSON-safe (dates -> str)
def jsafe(d):
    out = {}
    for k, v in d.items():
        try:
            json.dumps(v)
            out[k] = v
        except TypeError:
            out[k] = str(v)
    return out

registry_rows = [jsafe(r) for r in registry_rows]
si_rows = [jsafe(r) for r in si_rows]

# ---------------------------------------------------------------------------
# Cross-reference: for each si_signals source_id feeding IN, try to find a
# registry row whose source_name or object_names or endpoint contains a
# normalized token from source_id (or vice versa).
# ---------------------------------------------------------------------------
def norm_tokens(s):
    if isinstance(s, (list, tuple)):
        s = " ".join(str(x) for x in s)
    s = str(s or "").lower()
    for ch in "_-.:/":
        s = s.replace(ch, " ")
    return set(t for t in s.split() if len(t) > 2)

reg_by_id = {r["source_id"]: r for r in registry_rows if r.get("source_id")}
reg_by_tokens = []
for r in registry_rows:
    toks = (norm_tokens(r.get("source_name", "")) | norm_tokens(r.get("endpoint", ""))
            | norm_tokens(r.get("object_names", "")) | norm_tokens(r.get("source_id", "")))
    reg_by_tokens.append((toks, r))

# Also pull the FULL registry (no Indiana filter) for an exact source_id join --
# an Indiana-feeding source_id's registry row may not itself match the Indiana-shaped
# text filter (e.g. a national source with an IN-only slice, or a registry row whose
# source_name/endpoint don't mention Indiana at all even though it feeds IN rows).
q_registry_by_id = r"""
SELECT source_id, source_name, status, status_measured, endpoint, endpoint_raw, endpoint_kind,
       object_names, access, notes, domain, origin, geography_state, geography_county,
       part_gate, priority, category, acquisition_method, method, validation, validation_error,
       last_http_status, last_source_count, measured_rows, expected_count, last_validated_at
FROM `energy-platfrom.energy.registry_sources`
WHERE source_id IN UNNEST(@ids)
"""
from google.cloud import bigquery as _bq
si_source_ids = [s["source_id"] for s in si_rows]
job_config = _bq.QueryJobConfig(query_parameters=[_bq.ArrayQueryParameter("ids", "STRING", si_source_ids)])
exact_rows = [jsafe(dict(r)) for r in client.query(q_registry_by_id, job_config=job_config).result()]
reg_by_id_exact = {r["source_id"]: r for r in exact_rows}
print(f"Exact source_id join against FULL registry (no Indiana text filter): {len(exact_rows)} matched")

mapping = []
for s in si_rows:
    sid = s["source_id"]
    exact = reg_by_id_exact.get(sid) or reg_by_id.get(sid)
    if exact:
        mapping.append({
            "source_id": sid,
            "n_rows_held": s["n"],
            "latest_observed": s["latest"],
            "earliest_observed": s["earliest"],
            "matched_registry_source_name": exact.get("source_name"),
            "matched_registry_endpoint": exact.get("endpoint") or exact.get("endpoint_raw"),
            "matched_registry_status": exact.get("status"),
            "matched_registry_endpoint_kind": exact.get("endpoint_kind"),
            "matched_registry_access": exact.get("access"),
            "match_method": "exact_source_id",
            "match_token_overlap": 999,
        })
        continue
    sid_toks = norm_tokens(sid)
    best = None
    best_overlap = 0
    for toks, r in reg_by_tokens:
        overlap = len(sid_toks & toks)
        if overlap > best_overlap:
            best_overlap = overlap
            best = r
    mapping.append({
        "source_id": sid,
        "n_rows_held": s["n"],
        "latest_observed": s["latest"],
        "earliest_observed": s["earliest"],
        "matched_registry_source_name": best.get("source_name") if best else None,
        "matched_registry_endpoint": (best.get("endpoint") or best.get("endpoint_raw")) if best else None,
        "matched_registry_status": best.get("status") if best else None,
        "matched_registry_endpoint_kind": best.get("endpoint_kind") if best else None,
        "matched_registry_access": best.get("access") if best else None,
        "match_method": "fuzzy_token" if best else "none",
        "match_token_overlap": best_overlap,
    })

unmapped = [m for m in mapping if m["match_token_overlap"] == 0 or m["matched_registry_endpoint"] is None]
mapped = [m for m in mapping if m not in unmapped]

out = {
    "registry_indiana_shaped_rows": registry_rows,
    "si_signals_in_rollup": si_rows,
    "mapping": mapping,
    "mapped_count": len(mapped),
    "unmapped_count": len(unmapped),
}

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_scratch", "01_target_list.json")
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2, ensure_ascii=False)

print(f"\nWrote {out_path}")
print(f"\n=== si_signals source_ids feeding IN ({len(si_rows)}) ===")
for s in si_rows:
    print(f"  {s['source_id']:<45} n={s['n']:>10}  earliest={s['earliest']}  latest={s['latest']}")

print(f"\n=== Cross-reference: mapped {len(mapped)} / unmapped {len(unmapped)} ===")
for m in mapping:
    flag = "OK" if m["match_token_overlap"] > 0 and m["matched_registry_endpoint"] else "UNMAPPED"
    print(f"  [{flag}] {m['source_id']:<45} -> {m['matched_registry_source_name']} (overlap={m['match_token_overlap']})")

print(f"\n=== registry_sources Indiana-shaped endpoint rows ({len(registry_rows)}) ===")
for r in registry_rows:
    print(f"  {r['source_name'][:60]:<60} status={r.get('status')}  endpoint={str(r.get('endpoint'))[:100]}")
