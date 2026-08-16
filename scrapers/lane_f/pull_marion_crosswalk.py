"""Marion County parcel crosswalk + the SPATIAL abandoned/vacant layer — ALL COLUMNS.

THE PROBLEM THIS SOLVES. Every Marion-County signal we hold is keyed to a 7-DIGIT LOCAL parcel
id (`5019155`), while `in_sites` is keyed to the 18-digit STATE parcel number. A naive join reads
zero, and the previous session concluded no crosswalk existed because
`in_si_indy_taxsale_parcels.PARCELNUMBER` turned out to be the same 7-digit local id, not a state
key. That conclusion was right about that table and wrong about the world:

  gis.indy.gov/server/rest/services/sde_Parcel/sde_Parcel/MapServer/5  'Parcel State Pin'
      347,049 parcels carrying PARCEL_I (local) AND STATEPARCELNUMBER (49-06-25-178-053.000-101)

That is the crosswalk. It unlocks 7,120 abandoned buildings and the Marion tax-sale set, which
have been reachable only by address at a 1.8% rate (125 of 7,120).

AND A SECOND ROUTE, because the first pull used the wrong service:

  gis.indy.gov/.../MapIndy/MapIndyProperty/MapServer/11  'Abandoned and Vacant'
      the SAME 7,120 rows, but esriGeometryPolygon — geometry, not just attributes

We pulled the attribute copy from `OpenData_NonSpatial`, which is exactly what its name says. With
geometry, a parcel join needs no key at all: the polygon is the location. Both routes are taken,
so each can CHECK the other — if the crosswalk and the geometry disagree about which parcel an
abandoned building sits on, that disagreement is a finding, not something to silently prefer away.

ALL COLUMNS: `outFields=*` on every request. The state-pin layer also carries PROPERTY_CLASS,
PROPERTY_SUB_CLASS_DESCRIPTION and owner-state fields nobody asked for — the Lane D lesson is
that the columns you did not ask for are the ones you come back for.

Rules honoured: public ArcGIS REST, no key, no account, no CAPTCHA, no paywall; identifying
User-Agent; SHORTFALL DETECTION against the server's own returnCountOnly; `_pulled_at` kept
distinct from any publisher date; writes ONLY to energy-platfrom.indiana_app; registered in the
SAME run that writes.
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
import json, time, datetime, urllib.parse, urllib.request, sys
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
ROOT = "https://gis.indy.gov/server/rest/services"
UA = {"User-Agent": "decennial-indiana-siting/1.0 (research; contact via repo)"}
PAGE = 2000
client = bigquery.Client(project="energy-platfrom")
PULLED = datetime.datetime.now(datetime.timezone.utc).isoformat()

ONLY = sys.argv[1] if len(sys.argv) > 1 else None   # re-run one layer without re-pulling 347k rows

LAYERS = [
    {"key": "crosswalk", "path": "sde_Parcel/sde_Parcel/MapServer/5",
     "table": "in_marion_parcel_crosswalk", "geom": False,
     "what": "Marion parcel local-id <-> state parcel number crosswalk"},
    {"key": "abandoned", "path": "MapIndy/MapIndyProperty/MapServer/11",
     "table": "in_si_indy_abandoned_vacant_spatial", "geom": True,
     "what": "Indy abandoned & vacant, WITH polygon geometry"},
    # THE ADDRESS CROSSWALK. 465,050 Marion addresses, each carrying FULL_ADDRESS *and*
    # STATEPARCELNUMBER — so an Indianapolis street address reaches a parcel DIRECTLY, with no
    # geocoding step and no invented normalisation. This is what the 910k-row Indy code corpus
    # needs: 54,995 Unsafe Buildings + Vacant Board Order rows across ~24,789 addresses currently
    # reach 711 parcels through the generic address bridge.
    {"key": "addresses", "path": "sde_Addressing/sde_Addressing/MapServer/0",
     "table": "in_marion_address_crosswalk", "geom": False,
     "what": "Marion address -> state parcel number crosswalk (Indy's own address authority)"},
]


def get(url, tries=5):
    """Bounded retry on transient transport failures only — never on a refusal."""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code in (500, 502, 503, 504, 429):
                last = f"HTTP {e.code}"
                time.sleep(2 * (i + 1))
                continue
            raise
        except Exception as e:                      # socket timeouts, resets
            last = str(e)[:90]
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"gave up after {tries} attempts: {last}")


for L in LAYERS:
    if ONLY and L["key"] != ONLY:
        continue
    base = f"{ROOT}/{L['path']}"
    expected = get(f"{base}/query?where=1%3D1&returnCountOnly=true&f=json").get("count")
    print(f"\n=== {L['table']} — publisher reports {expected:,} rows ===", flush=True)

    rows, offset = [], 0
    while True:
        # f=geojson, NOT f=json, for geometry layers. `f=json` returns Esri geometry
        # (`{"rings": [...]}`), which ST_GEOGFROMGEOJSON cannot read — it parsed 0 of 7,120 on
        # the first attempt. GeoJSON is what BigQuery actually consumes.
        q = {"where": "1=1", "outFields": "*", "returnGeometry": "true" if L["geom"] else "false",
             "resultOffset": offset, "resultRecordCount": PAGE,
             "f": "geojson" if L["geom"] else "json"}
        if L["geom"]:
            q["outSR"] = "4326"
        d = get(f"{base}/query?{urllib.parse.urlencode(q)}")
        feats = d.get("features", [])
        if not feats:
            break
        for ft in feats:
            src_attrs = ft.get("properties") if L["geom"] else ft.get("attributes")
            rec = {k: (None if v == "" else v) for k, v in (src_attrs or {}).items()}
            if L["geom"]:
                rec["geometry_json"] = json.dumps(ft.get("geometry")) if ft.get("geometry") else None
            rec["_pulled_at"] = PULLED
            rec["_source_url"] = base
            rows.append(rec)
        offset += len(feats)
        print(f"  {offset:,} / {expected:,}", flush=True)
        if len(feats) < PAGE and not d.get("exceededTransferLimit"):
            break
        time.sleep(0.3)

    # SHORTFALL DETECTION — a silently short page is the defect that let Adams pass at 825 of 928
    if expected and len(rows) < expected:
        print(f"  *** SHORTFALL: got {len(rows):,} of {expected:,} "
              f"({100*len(rows)/expected:.1f}%) — NOT LOADED. Re-run before trusting it. ***")
        sys.exit(1)
    print(f"  complete: {len(rows):,} rows", flush=True)

    # ArcGIS ships SQL-Server shape fields named `SHAPE.STArea()` — illegal in BigQuery, and it
    # kills the load AFTER a clean 347,049-row pull. Sanitise the NAME only; drop no column, and
    # keep the original spelling on the registry row so the rename is recoverable, not silent.
    def safe(k):
        s = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in k)
        return ("_" + s) if (not s or s[0].isdigit()) else s

    renames = {}
    norm = []
    for r in rows:
        out = {}
        for k, v in r.items():
            sk = safe(k)
            if sk != k:
                renames[k] = sk
            out[sk] = None if v is None else str(v)
        norm.append(out)
    if renames:
        print("  renamed for BigQuery: " +
              ", ".join(f"{a} -> {b}" for a, b in list(renames.items())[:6]), flush=True)

    # every value as STRING: these are publisher attributes, and a type guess here would be a
    # second instrument. Casting happens downstream, where the intent is explicit.
    keys = sorted({k for r in norm for k in r})
    schema = [bigquery.SchemaField(k, "STRING") for k in keys]
    job = client.load_table_from_json(
        [{k: r.get(k) for k in keys} for r in norm], f"{DS}.{L['table']}",
        job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE"))
    job.result()
    n = list(client.query(f"SELECT COUNT(*) n FROM `{DS}.{L['table']}`"))[0].n
    print(f"  loaded {n:,} rows, {len(keys)} columns -> {L['table']}", flush=True)

    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='{L['table']}'").result()
    client.query(
        f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, built_at) "
        f"VALUES (@t,@s,@m,@n,CURRENT_TIMESTAMP())",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", L["table"]),
            bigquery.ScalarQueryParameter("s", "STRING", base),
            bigquery.ScalarQueryParameter(
                "m", "STRING",
                f"{L['what']}. ArcGIS REST paged query, outFields=* (ALL columns), "
                f"{'geometry in EPSG:4326' if L['geom'] else 'attributes only'}, "
                f"shortfall-checked against returnCountOnly={expected}. Public endpoint, no key."
                + (f" Columns renamed for BigQuery legality (no column dropped): "
                   + "; ".join(f"{a}->{b}" for a, b in renames.items()) if renames else "")),
            bigquery.ScalarQueryParameter("n", "INT64", int(n))])).result()
    print(f"  registered {L['table']}", flush=True)

print("\nDONE")
