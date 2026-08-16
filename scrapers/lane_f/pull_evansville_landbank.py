"""Evansville Land Bank Corp (IC 36-7-38) — the one genuinely new abandoned-property source the
Lane F discovery run found VIABLE, and which was then never loaded. This closes that miss.

WHAT IT IS, AND WHAT IT IS NOT. A land bank inventory is **availability**, not distress: these are
properties a public body is actively trying to sell, which makes the owner motivated by
definition. That is a different claim from "this building is abandoned", and the discovery run
was explicit that the city describes the "vast majority" as vacant LOTS, with no structure flag
in the schema. So it is admitted as `A2_gov_surplus` (availability), never as
`D5_abandoned_building`, and whether a structure exists is read from our own parcel layer via
`occ_group` rather than assumed.

Keyed by `StatePIN` (82-… Vanderburgh), which is the same key that already places Evansville tax
sales and foreclosures at 99.7%.

FRAGILITY RECORDED: the service name carries a snapshot date (`Landbank_Available_July2025`) and
will rotate. This script therefore DISCOVERS the layer from the FeatureServer directory rather
than hard-coding the id, and says so loudly if it cannot find it — a 404 here means the snapshot
rolled, not that the source died.
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
import json, datetime, urllib.request, urllib.parse, re, sys
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
ORG = "https://services1.arcgis.com/iZyBOluseC8ffQc2/arcgis/rest/services"
UA = {"User-Agent": "decennial-indiana-siting/1.0 (research; contact via repo)"}
client = bigquery.Client(project="energy-platfrom")
PULLED = datetime.datetime.now(datetime.timezone.utc).isoformat()


def get(u, t=60):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


# --- discover the layer, because the snapshot name rotates -------------------------------------
svcs = [s["name"] for s in get(f"{ORG}?f=json").get("services", [])]
cand = [s for s in svcs if re.search(r"(?i)landbank|land_bank", s)]
print(f"land-bank services visible: {cand or 'NONE'}")
if not cand:
    sys.exit("ABORT: no land-bank service on this org. The July2025 snapshot has rotated — "
             "re-discover the service name before assuming the source is gone.")

# THE PUBLISHER KEEPS NINE SNAPSHOTS, not one. Taking whichever sorts first grabs a 2023 copy
# and silently discards March 2026. They are nine point-in-time inventories of ONE subject, so
# the union-and-dedupe ruling applies: load them ALL, stamp each with the date in its own service
# name, and let the history stand. A parcel present in 2021 and absent by 2026 was SOLD — a
# completed disposal is a real event, and it only exists if the older snapshots are kept.
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def snapshot_date(name):
    y = re.search(r"(20\d{2})", name)
    mo = re.search(r"(?i)(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", name)
    if not y:
        return None
    return f"{y.group(1)}-{MONTHS[mo.group(1).lower()]:02d}-01" if mo else f"{y.group(1)}-01-01"


rows, used = [], []
for name in cand:
    fs = get(f"{ORG}/{name}/FeatureServer?f=json")
    for L in fs.get("layers", []) + fs.get("tables", []):
        base = f"{ORG}/{name}/FeatureServer/{L['id']}"
        try:
            expected = get(f"{base}/query?where=1%3D1&returnCountOnly=true&f=json").get("count")
        except Exception:
            continue
        if not expected:
            continue
        snap = snapshot_date(name)
        got = 0
        offset = 0
        while True:
            q = {"where": "1=1", "outFields": "*", "returnGeometry": "false",
                 "resultOffset": offset, "resultRecordCount": 1000, "f": "json"}
            d = get(f"{base}/query?{urllib.parse.urlencode(q)}")
            feats = d.get("features", [])
            if not feats:
                break
            for ft in feats:
                rec = {k: (None if v == "" else v) for k, v in (ft.get("attributes") or {}).items()}
                rec["_layer_name"] = L.get("name")
                rec["_service_name"] = name
                rec["_snapshot_date"] = snap
                rec["_pulled_at"] = PULLED
                rec["_source_url"] = base
                rows.append(rec)
            got += len(feats)
            offset += len(feats)
            if len(feats) < 1000 and not d.get("exceededTransferLimit"):
                break
        print(f"  {name:38s} snapshot={snap} {got:,} of {expected:,} rows")
        if got < expected:
            sys.exit(f"SHORTFALL on {name}: {got} of {expected} — nothing loaded.")
        used.append((name, snap, got))

if not rows:
    sys.exit("ABORT: land-bank services found but no rows returned.")
print(f"pulled {len(rows):,} rows across {len(used)} snapshots "
      f"({min(u[1] for u in used if u[1])} .. {max(u[1] for u in used if u[1])})")


def safe(k):
    s = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in k)
    return ("_" + s) if (not s or s[0].isdigit()) else s


# Nine snapshots spell their columns differently across five years ("State PIN", "State_PIN",
# "StatePIN"), and sanitising collapses some pairs onto one name — BigQuery then rejects the load
# with "Field already exists". Resolve collisions by suffixing rather than by dropping either
# column: which spelling a snapshot used is itself provenance, and the ALL-COLUMNS rule holds.
# NOTE: BigQuery column names are case-INSENSITIVE for uniqueness, so `State_PIN` and `state_pin`
# collide even though Python sees two distinct strings. The collision key must be lowercased or
# the load fails with "Field already exists" on names that look different.
name_map, taken = {}, {}
for orig in sorted({k for r in rows for k in r}):
    base_name = safe(orig)
    if base_name.lower() in taken and taken[base_name.lower()] != orig:
        i = 2
        while f"{base_name}_{i}".lower() in taken:
            i += 1
        base_name = f"{base_name}_{i}"
    taken[base_name.lower()] = orig
    name_map[orig] = base_name
collided = [(o, n) for o, n in name_map.items() if n != safe(o)]
if collided:
    print("  collision-resolved column names (both kept): " +
          ", ".join(f"{o} -> {n}" for o, n in collided[:6]))

norm = [{name_map[k]: (None if v is None else str(v)) for k, v in r.items()} for r in rows]
keys = sorted({k for r in norm for k in r})
client.load_table_from_json(
    [{k: r.get(k) for k in keys} for r in norm], f"{DS}.in_si_evansville_landbank",
    job_config=bigquery.LoadJobConfig(
        schema=[bigquery.SchemaField(k, "STRING") for k in keys],
        write_disposition="WRITE_TRUNCATE")).result()
n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.in_si_evansville_landbank`"))[0].n
print(f"loaded {n:,} rows, {len(keys)} columns")

# does the StatePIN reach a parcel, and is there a structure on it?
# THE KEY IS SPELLED THREE WAYS ACROSS NINE YEARS OF SNAPSHOTS — StatePIN (2021-2025),
# State_PIN (2021-2024, partial) and STATE_PIN (2026 only). Reading only one of them reported
# "0 distinct StatePIN" for the NEWEST snapshot and therefore "0 disposed", which would have been
# a confident wrong claim about the inventory rather than about the column. COALESCE all of them.
pin_cols = [k for k in keys if "pin" in k.lower()]
pin_col = f"COALESCE({', '.join(pin_cols)})" if pin_cols else None
print(f"\n  parcel-key columns coalesced: {pin_cols}")
if pin_col:
    print("\n  per snapshot:")
    for x in client.query(f"""SELECT _snapshot_date d, COUNT(*) n,
        COUNT(DISTINCT {pin_col}) pins FROM `{DS}.in_si_evansville_landbank`
        GROUP BY 1 ORDER BY 1"""):
        print(f"    {x.d}  {x.n:>5,} rows · {x.pins:>5,} distinct StatePIN")
    r = list(client.query(f"""
      WITH lb AS (SELECT DISTINCT REGEXP_REPLACE({pin_col}, r'[^0-9]','') k
                  FROM `{DS}.in_si_evansville_landbank` WHERE {pin_col} IS NOT NULL)
      SELECT COUNT(*) pins, COUNTIF(s.parcel_key IS NOT NULL) placed,
             COUNTIF(s.occ_group='no_structure') vacant_lots,
             COUNTIF(s.occ_group IS NOT NULL AND s.occ_group NOT IN ('no_structure','residential')) nonres_structure,
             COUNTIF(s.occ_group='residential') residential
      FROM lb LEFT JOIN `{DS}.in_sites` s ON s.parcel_key = lb.k"""))[0]
    print(f"\n  DISTINCT StatePIN across all snapshots -> parcel: {r.placed:,} of {r.pins:,} placed")
    print(f"    vacant lots {r.vacant_lots:,} · NON-RESIDENTIAL STRUCTURE {r.nonres_structure:,} "
          f"· residential {r.residential:,}")
    print("    (the city said 'vast majority vacant lots' — measured here rather than assumed)")
    # a parcel in an old snapshot but not the newest has left the inventory: it was DISPOSED OF
    r2 = list(client.query(f"""
      WITH mx AS (SELECT MAX(_snapshot_date) d FROM `{DS}.in_si_evansville_landbank`),
      cur AS (SELECT DISTINCT {pin_col} p FROM `{DS}.in_si_evansville_landbank`, mx
              WHERE _snapshot_date = mx.d),
      allp AS (SELECT DISTINCT {pin_col} p FROM `{DS}.in_si_evansville_landbank`)
      SELECT (SELECT COUNT(*) FROM allp) ever, (SELECT COUNT(*) FROM cur) still_held,
             (SELECT COUNT(*) FROM allp WHERE p NOT IN (SELECT p FROM cur)) disposed"""))[0]
    print(f"    ever in the inventory {r2.ever:,} · still held at the latest snapshot "
          f"{r2.still_held:,} · LEFT the inventory (disposed) {r2.disposed:,}")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_si_evansville_landbank'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at) "
    f"VALUES (@t,@s,@m,@n,CURRENT_TIMESTAMP())",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "in_si_evansville_landbank"),
        bigquery.ScalarQueryParameter("s", "STRING", f"{ORG}/{used[0]}/FeatureServer/{used[1]}"),
        bigquery.ScalarQueryParameter(
            "m", "STRING",
            "Evansville Land Bank Corp inventory, ALL columns, layer DISCOVERED from the "
            "FeatureServer directory because the snapshot name rotates (Landbank_Available_"
            "July2025). AVAILABILITY semantics, not distress — admitted as A2_gov_surplus, never "
            "as D5_abandoned_building. Keyed by StatePIN; structure presence read from in_sites."),
        bigquery.ScalarQueryParameter("n", "INT64", int(n))])).result()
print("registered in_si_evansville_landbank")
