"""MISO DPP-2025 POI Analysis / transfer study via CartoVista cloud -- route prober + loader.

WHAT THIS IS
------------
The commercial benchmark derives its Indiana bus numbers from MISO's DPP-2025-Cycle case. We
hold MISO's DPP-2021 (from the legacy giqueue viewer). The DPP-2025 case is published only
through the CartoVista FERC Order 2023 POI heatmap at cloud.cartovista.com/miso. This script
maps EVERY public route on that deployment, records a table x route x HTTP-status matrix, loads
the tables that are actually reachable into `energy-platfrom.indiana_app`, and quotes the wall
verbatim for the tables that are not.

THE MEASURED VERDICT (2026-08-17) -- see docs/MISO_DPP2025_ROUTE.md for the full matrix
---------------------------------------------------------------------------------------
Discovery + metadata routes are ALL public (HTTP 200):
    ferc.cartovista.com/api/settings/miso/ferc                         200
    cloud.../miso/api/v2/maps/{poiAnalysisMapId}/details               200   (map 1: POI analysis)
    cloud.../miso/api/v2/maps/{currentQueueMapId}/details              200   (map 2: current queue)
    cloud.../miso/api/v2/DataTable/{guid}/DataColumns   (all 6 tables) 200
    cloud.../miso/api/v2/GridLayer/{gridLayerId}/details               200
    cloud.../miso/api/v2/GridLayer/{gridLayerId}/GridSources           200
    cloud.../miso/WebportalServices/Thumbnail.aspx?gridLayerId=...     200   (COLORIZED png only)

The ROW-LEVEL data splits per table (POST DataTable/{guid}/DataRows):
    MISO_POIs_2025-11-11      19,223 rows   403 Forbidden / ProtectedData
    MISO_TSA_2025-11-11      691,523 rows   403 Forbidden / ProtectedData   <- the headroom driver
    MISO_GIQueue-2025-11-11    3,253 rows   403 Forbidden / ProtectedData
    MISO Counties [Prod]       1,003 rows   200 OPEN  (county identity reference; NOT headroom)
    MISO FootPrint [Prod]          1 row    200 OPEN  (MISO outline; NOT headroom)
    DPP2022 - Injection mask       0 rows   200 OPEN, serves []  (empty)

The three headline tables are 403 "ProtectedData" and that is CONFIRMED THREE WAYS, so it is a
real wall and not a missing-parameter or missing-session artifact:
    1. raw unauthenticated POST                        -> 403  (prior session + this one)
    2. this script's probe                             -> 403
    3. fetch() from the LIVE VIEWER's own JS context,  -> 403
       carrying the anonymous session cookies + the
       correct same-origin referer (tested 2026-08-17)
The viewer renders those tables only through DataServices/dataQueryExecute, whose response body
is AES-ENCRYPTED with a cloud-CartoVista key (NOT the giqueue key; body is base64 that does NOT
carry the OpenSSL "Salted__" header). Decrypting it is a separate reverse-engineering task and is
NOT attempted here. See the doc for the exact lead.

THE GRID RASTER (operator asked specifically): the POI map carries ONE gridLayer,
`3ed5bf8e-b0a3-4276-aaff-8ba79c47c181`, publicAccess:true, units MW, one GridSource named
**"Peak - 2022"** (min -77268, max 3700 MW). Its metadata is public and its colorized Thumbnail
png renders, but EVERY raw-value route 404s (`/geotiff`, `/GeoTiff`, `/tiff`, `/download`,
`/data`, `/GridSource/{id}`, tile paths, WebportalServices/{Download,Export,GridData}.aspx). The
config XML's GridSource `<Src>` is empty and renderingMode="color", i.e. the client only ever
receives colorized tiles, never the numeric grid. So the raw MW surface is NOT retrievable, and
the layer's own name is "Peak - 2022" -- vintage is NOT confirmed DPP-2025. We already hold the
raw DPP-2021 MW surface in energy.miso_poi_capacity_surface_geotiff, so nothing is loaded here.

VINTAGE LABELS DISAGREE ON THIS DEPLOYMENT -- recorded so nobody trusts one blindly:
    settings studyTitle .................. "DPP2025"  (+ publisher disclaimer: DPP-2025-Cycle)
    map.title ............................ "DPP 2023 - POI Analysis Map [Production]"
    map.vanityUrl ........................ "59878/DPP-2023-POI-Analysis-Map-Production"
    gridLayer.name ....................... "DPP2022 - Capacity heatmap"
    gridSource.name ...................... "Peak - 2022"
The authoritative vintage for the POI/TSA study is the publisher's disclosure "currently using
the models and inputs from the DPP-2025-Cycle." The grid raster's own label is 2022 and must not
be relabelled DPP-2025.

BOUNDARIES: read-only GET + query-POST (DataRows is a QUERY, nothing is mutated), identifying
User-Agent, >=1.15s per host, no accounts, no keys, no UA spoofing. A 403 recorded with its wall
quoted verbatim is a SUCCESS.

USAGE
-----
    python scripts/pull_miso_dpp2025.py --matrix              # probe every route, print the matrix, NO writes
    python scripts/pull_miso_dpp2025.py --load --smoke        # load OPEN tables (rowCount<=25) + registry
    python scripts/pull_miso_dpp2025.py --load                # load OPEN tables in full (~1,004 rows) + registry
    python scripts/pull_miso_dpp2025.py --load --dry-run      # parse + show, do not touch BigQuery
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import argparse
import json
import time
import urllib.error
import urllib.request

PROJECT = "energy-platfrom"
DATASET = "indiana_app"            # <- our sink; energy.* is READ-ONLY for this workstream
DS = f"{PROJECT}.{DATASET}"
ORG = "miso"
CLOUD = f"https://cloud.cartovista.com/{ORG}/api/v2"
SETTINGS_URL = f"https://ferc.cartovista.com/api/settings/{ORG}/ferc"

UA = ("DecennialGroup-DataAudit/1.0 (read-only public FERC Order 2023 POI heatmap; "
      "contact ahenderson@decennialgroup.com)")
MIN_INTERVAL = 1.15
TIMEOUT = 60
MAX_BYTES = 64 * 1024 * 1024

# The two maps this study exposes (from settings/miso/ferc, study 83dffd45-...):
POI_ANALYSIS_MAP = "59878415-54b3-4502-9429-bfd90c7ce3c5"
CURRENT_QUEUE_MAP = "6bf71952-3862-421b-a156-ed3d0a3ca98b"

# The six data tables (uniqueIdentifier -> systemIdentifier), declared row counts from details.
# Kept explicit so a re-run re-verifies each by name rather than trusting discovery order.
TABLES = [
    # (label, systemIdentifier, declared_rows, out_table_or_None)
    ("MISO_POIs_2025-11-11",       "da6949ad-2cf3-436f-bbe2-397c47c33da0", 19223, None),
    ("MISO_TSA_2025-11-11",        "d48a4a1b-f6d2-4c50-8ff8-7ed4fecb61aa", 691523, None),
    ("MISO_GIQueue-2025-11-11",    "8b40a6a0-a273-4410-b0c5-e9adacc8873f", 3253, None),
    ("MISO_Counties",              "98af4e3b-1772-4cf7-b15f-c5899120dbb8", 1003, "in_miso_dpp2025_counties"),
    ("MISO_FootPrint",             "421ee8c5-939e-4266-8bb2-f2b84fd8ed17", 1,    "in_miso_dpp2025_footprint"),
    ("DPP2022_-_Injection_area_mask2", "ffcefe7e-eba0-45b3-ba95-b5d8edcf77bf", 0, None),
]
GRIDLAYER_ID = "3ed5bf8e-b0a3-4276-aaff-8ba79c47c181"

_last = {}


def _throttle(url):
    h = url.split("/")[2]
    dt = time.time() - _last.get(h, 0.0)
    if dt < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - dt)
    _last[h] = time.time()


def http(url, body=None, method=None):
    """Throttled, bounded request. Returns (status:int|str, text:str). Never raises for HTTP errors."""
    _throttle(url)
    headers = {"User-Agent": UA, "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method or ("POST" if body is not None else "GET"),
                                 headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            buf = bytearray()
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                buf += chunk
                if len(buf) > MAX_BYTES:
                    break
            return r.status, bytes(buf).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read(4096).decode("utf-8", "replace")
        except Exception:
            return e.code, ""
    except Exception as e:
        return "ERR", f"{type(e).__name__}: {e}"


def data_columns(guid):
    st, txt = http(f"{CLOUD}/DataTable/{guid}/DataColumns")
    cols = []
    if st == 200:
        try:
            for c in json.loads(txt):
                cols.append({"id": c.get("identifier") or c.get("name"), "name": c.get("name"),
                             "type": c.get("dataType") or c.get("type")})
        except Exception:
            pass
    return st, cols


def data_rows(guid, start, count):
    """POST DataRows. Returns (status, list_of_record_dicts_or_None, raw_head)."""
    st, txt = http(f"{CLOUD}/DataTable/{guid}/DataRows", body={"startRow": start, "rowCount": count})
    if st != 200:
        return st, None, txt[:240]
    try:
        return st, json.loads(txt), txt[:120]
    except Exception:
        return st, None, txt[:240]


def _rec_to_dict(rec):
    """One DataRows record -> {column_identifier: value}. The server returns identifier arrays."""
    cols = rec.get("dataColumnsIdentifiers") or []
    vals = rec.get("values") or []
    d = dict(zip(cols, vals))
    d["_row_identifier"] = rec.get("identifier")
    return d


# --------------------------------------------------------------------------- discovery / matrix
def cmd_matrix(a):
    print("=== MISO DPP-2025 CartoVista route matrix ===")
    st, txt = http(SETTINGS_URL)
    print(f"[settings] {SETTINGS_URL} -> {st}")
    for label, mid in (("POI analysis map", POI_ANALYSIS_MAP), ("current queue map", CURRENT_QUEUE_MAP)):
        st, txt = http(f"{CLOUD}/maps/{mid}/details")
        ntab = ngrid = None
        if st == 200:
            try:
                d = json.loads(txt)
                ntab = len(d.get("dataTables") or [])
                ngrid = len(d.get("gridLayers") or [])
            except Exception:
                pass
        print(f"[map] {label:18s} {mid} -> {st}  dataTables={ntab} gridLayers={ngrid}")

    print("\n%-30s %-12s %-14s %-8s %s" % ("table", "DataColumns", "declared_rows", "DataRows", "verdict"))
    print("-" * 96)
    matrix = []
    for label, guid, declared, out in TABLES:
        sc, cols = data_columns(guid)
        sr, rows, head = data_rows(guid, 0, 5)
        if sr == 200 and rows is not None:
            verdict = f"OPEN (served {len(rows)})"
        elif sr == 403:
            verdict = "BLOCKED 403 ProtectedData"
        else:
            verdict = f"status {sr}"
        matrix.append({"table": label, "guid": guid, "declared_rows": declared,
                       "datacolumns_status": sc, "n_columns": len(cols),
                       "datarows_status": sr, "datarows_head": head, "verdict": verdict})
        print("%-30s %-12s %-14s %-8s %s" % (label[:30], sc, declared, sr, verdict))
        if sr == 403:
            print(f"    WALL: {head}")

    # grid layer
    sg, _ = http(f"{CLOUD}/GridLayer/{GRIDLAYER_ID}/details")
    sgs, _ = http(f"{CLOUD}/GridLayer/{GRIDLAYER_ID}/GridSources")
    sth, _ = http(f"https://cloud.cartovista.com/{ORG}/WebportalServices/Thumbnail.aspx?gridLayerId={GRIDLAYER_ID}")
    print(f"\n[grid] GridLayer/{GRIDLAYER_ID[:8]}../details={sg} /GridSources={sgs} Thumbnail.aspx={sth} "
          f"(colorized png only; raw-value routes 404 -- see module docstring)")
    return matrix


# --------------------------------------------------------------------------- load open tables
def fetch_all_open(guid, declared, cap):
    """Fetch reachable rows from an OPEN table. Detects the DataRows 1,000-row cap (startRow
    ignored -> repeated first page) and stops when a page adds no new identifier."""
    out, seen, start = [], set(), 0
    page = min(1000, declared) or 1
    while start < max(declared, 1):
        want = min(page, cap - len(out)) if cap else page
        if want <= 0:
            break
        st, rows, head = data_rows(guid, start, want)
        if st != 200 or not rows:
            break
        new = 0
        for rec in rows:
            rid = rec.get("identifier")
            if rid in seen:
                continue
            seen.add(rid)
            new += 1
            out.append(_rec_to_dict(rec))
        if new == 0 or (cap and len(out) >= cap):
            break
        start += len(rows)
    return out


def registry(client, table, n_rows, source, method, notes):
    """A _registry row in the SAME run that writes the table (checkpoint requires it)."""
    from google.cloud import bigquery
    client.query(f"DELETE FROM `{DS}._registry` WHERE table_name=@t",
                 job_config=bigquery.QueryJobConfig(query_parameters=[
                     bigquery.ScalarQueryParameter("t", "STRING", table)])).result()
    client.query(
        f"""INSERT `{DS}._registry`
            (table_name, source, method, n_rows, gb_scanned, built_at, notes)
            VALUES (@t,@s,@m,@n,0.0,CURRENT_TIMESTAMP(),@notes)""",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", table),
            bigquery.ScalarQueryParameter("s", "STRING", source),
            bigquery.ScalarQueryParameter("m", "STRING", method),
            bigquery.ScalarQueryParameter("n", "INT64", int(n_rows)),
            bigquery.ScalarQueryParameter("notes", "STRING", notes)])).result()
    print(f"   _registry row written for {table}: n_rows={n_rows:,}")


def cmd_load(a):
    cap = 25 if a.smoke else 0
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    to_load = [(lbl, guid, declared, out) for (lbl, guid, declared, out) in TABLES if out]
    client = None
    if not a.dry_run:
        from google.cloud import bigquery
        client = bigquery.Client(project=PROJECT)

    for label, guid, declared, out_table in to_load:
        sc, cols = data_columns(guid)
        colmap = {c["id"]: c["name"] for c in cols}
        recs = fetch_all_open(guid, declared, cap)
        print(f"\n[{label}] declared={declared} fetched={len(recs)} "
              f"({'SMOKE cap ' + str(cap) if cap else 'full'}); columns={[c['id'] for c in cols]}")
        if not recs:
            print(f"   no rows fetched -- skipping {out_table}")
            continue
        rows = []
        for r in recs:
            row = {k: v for k, v in r.items() if not k.startswith("_")}
            row["_row_identifier"] = r.get("_row_identifier")
            row["_source_datatable_guid"] = guid
            row["_source_datarows_url"] = f"{CLOUD}/DataTable/{guid}/DataRows"
            row["_cartovista_map"] = POI_ANALYSIS_MAP
            row["_study_vintage_disclosed"] = "DPP-2025-Cycle (publisher settings disclaimer)"
            row["_column_name_map"] = json.dumps(colmap, ensure_ascii=False)
            row["_pulled_at"] = stamp
            rows.append(row)
        if a.dry_run:
            print("   DRY RUN sample:", json.dumps(rows[0], default=str)[:400])
            continue
        from google.cloud import bigquery
        dest = f"{DS}.{out_table}"
        client.load_table_from_json(rows, dest, job_config=bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE", autodetect=True)).result()
        got = list(client.query(f"SELECT COUNT(*) n FROM `{dest}`").result())[0].n
        print(f"   loaded {got:,} rows -> {dest}")
        if got != len(rows):
            raise RuntimeError(f"ROW CONSERVATION FAILED {len(rows)} in -> {got} out")
        served_note = ("SERVED-COMPLETE" if got >= declared
                       else f"PARTIAL {got} of {declared} (DataRows caps at 1,000, startRow ignored)")
        registry(
            client, out_table, got,
            source=f"cloud.cartovista.com/{ORG}/api/v2/DataTable/{guid}/DataRows (FERC Order 2023 MISO POI Analysis Map, study DPP2025)",
            method=(f"POST DataRows body {{startRow,rowCount}}; OPEN (HTTP 200) where the headline POI/TSA/GIQueue "
                    f"tables are 403 ProtectedData. RE-SCRAPE COMMAND: python scripts/pull_miso_dpp2025.py --load"),
            notes=(f"{served_note}. {label}: reference/boundary layer of MISO's DPP-2025 POI Analysis Map, "
                   f"NOT bus headroom. Columns (identifier->name): {json.dumps(colmap, ensure_ascii=False)}. "
                   f"OBSERVED VINTAGE: study disclosed as DPP-2025-Cycle; note the deployment's internal labels "
                   f"disagree (map.title 'DPP 2023', gridLayer 'DPP2022'). The bus-headroom tables on the SAME map "
                   f"(MISO_POIs 19,223; MISO_TSA 691,523; MISO_GIQueue 3,253) are 403 Forbidden/ProtectedData on "
                   f"DataRows -- confirmed unauthenticated AND from the live viewer's own session. "
                   f"See docs/MISO_DPP2025_ROUTE.md."))
    return 0


def main():
    p = argparse.ArgumentParser(description="MISO DPP-2025 CartoVista route prober + open-table loader.")
    p.add_argument("--matrix", action="store_true", help="probe every route, print the matrix, no writes")
    p.add_argument("--load", action="store_true", help="load the OPEN tables into indiana_app + registry rows")
    p.add_argument("--smoke", action="store_true", help="with --load, cap each table at 25 rows")
    p.add_argument("--dry-run", action="store_true", help="with --load, parse + show, do not touch BigQuery")
    a = p.parse_args()
    if a.matrix:
        cmd_matrix(a)
        return 0
    if a.load:
        return cmd_load(a)
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
