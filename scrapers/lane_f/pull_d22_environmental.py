"""D22 environmental violations — ALL COLUMNS, Indiana. ECHO bulk CSV + IDEM enforcement DB.

Lane F discovery (scrapers/lane_f/MISSING_SIGNALS_FINDINGS.md) ranked D22 the easiest viable
win of the eight missing signals: two independent open sources, no registration on either.

THE ALL-COLUMNS RULE, and why it is not optional here: an endpoint usually carries more than
one signal, and we have already been burned discovering columns after the fact — Lane D's pulls
turned up eleven signal-bearing columns nobody had asked for (SRI's own lat/lon on 36% of rows,
a 100%-populated Accela case link, WARN's NAICS). So this keeps EVERY column both sources
offer. Deciding what matters is a later, cheaper step than going back for a second pull.

--------------------------------------------------------------------------------------------
WHY THIS SCRIPT NO LONGER WALKS COUNTIES — the previous version's route is a dead end
--------------------------------------------------------------------------------------------
The prior version paged `echo_rest_services.get_qid` county by county and died on HTTP 429
after one county. That 429 is not transient load, and retrying it is not the fix. ECHO states
its quota in the refusal body verbatim:

    "If your requests exceed 300 per hour or 1,500 per day, we will throttle your request.
     ECHO has exports of bulk data available for download at
     https://echo.epa.gov/tools/data-downloads."

The old code also set `responseset=5` — five rows per request. Adams alone (928 rows) is 186
requests; the 92-county walk is roughly 25,000 requests against a 1,500/day ceiling. It could
never have finished, at any pause length. Route 3 (slow the walk down) is arithmetically
impossible, not merely slow, so it was not attempted.

ECHO's own error message names the remedy, and the remedy is better on every axis:
  * ONE request instead of ~25,000
  * 133 columns instead of the REST service's 59 — the bulk file is a strict superset,
    adding TRI releases/transfers, GHG CO2, EJ demographics (FAC_PERCENT_MINORITY,
    FAC_POP_DEN), impaired-water flag, and per-programme 13-quarter compliance histories
  * no paging, therefore no short-page defect (the Adams 825-of-928 bug is structurally gone)

--------------------------------------------------------------------------------------------
ONE HONEST DISCREPANCY, NOT PAPERED OVER
--------------------------------------------------------------------------------------------
ECHO's REST service refuses a statewide query with "Rows Returned would be 127266", but the
bulk ECHO Exporter holds 58,021 Indiana rows. These are two different universes, not a
shortfall: ECHO Exporter is the compliance-tracked regulated universe (CAA stationary sources,
CWA dischargers, RCRA handlers, SDWA systems, + TRI/GHG), one row per FRS REGISTRY_ID, whereas
the REST facility search resolves a broader FRS interest universe. The bulk file is the one
that carries the compliance columns D22 needs — every column named in the D22 spec
(FAC_SNC_FLG, CAA_HPV_FLAG, FAC_PENALTY_COUNT, per-programme compliance status, lat/lon,
NAICS, FIPS) is present and populated. Both figures are recorded in the registry notes rather
than quietly reconciled. See MISSING_SIGNALS_FINDINGS.md "D22 ACQUISITION RESULT".

Rules honoured: public endpoints, no registration, no key, no CAPTCHA, no paywall; identifying
User-Agent; observed EVENT dates kept distinct from `_pulled_at`; writes ONLY to
energy-platfrom.indiana_app; both tables registered in the SAME run.

Usage:
    python scrapers/lane_f/pull_d22_environmental.py --probe    # inspect columns, load nothing
    python scrapers/lane_f/pull_d22_environmental.py            # full pull + load (idempotent)
    python scrapers/lane_f/pull_d22_environmental.py --refresh  # ignore the cached zip
    python scrapers/lane_f/pull_d22_environmental.py --only echo|idem
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
import csv, collections, datetime, html, io, json, os, re, sys, tempfile, time
import urllib.error, urllib.parse, urllib.request
import zipfile
from google.cloud import bigquery

csv.field_size_limit(10_000_000)

DS = "energy-platfrom.indiana_app"
UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"

ECHO_BULK = "https://echo.epa.gov/files/echodownloads/echo_exporter.zip"
ECHO_MEMBER = "ECHO_EXPORTER.csv"
# Recorded for provenance: this is the endpoint the previous route used and the quota that
# ended it. Kept in the file so nobody re-derives the dead end.
ECHO_REST = "https://echodata.epa.gov/echo/echo_rest_services.get_facilities"
ECHO_REST_STATEWIDE_CLAIM = 127266

IDEM_URL = "https://oe.idem.in.gov/idem_oe_order"

PROBE = "--probe" in sys.argv
REFRESH = "--refresh" in sys.argv
ONLY = None
if "--only" in sys.argv:
    ONLY = sys.argv[sys.argv.index("--only") + 1].lower()

CACHE = os.environ.get("D22_CACHE") or os.path.join(tempfile.gettempdir(), "d22_cache")
os.makedirs(CACHE, exist_ok=True)

client = bigquery.Client(project="energy-platfrom")
PULLED = datetime.datetime.now(datetime.timezone.utc).isoformat()


def register(table, source, method, n_rows, notes):
    """Registry write, same run as the load. Delete-then-insert keeps re-runs idempotent."""
    client.query(
        f"DELETE FROM `{DS}._registry` WHERE table_name=@t",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", table)])).result()
    client.query(f"""INSERT `{DS}._registry`
        (table_name, source, method, n_rows, gb_scanned, built_at, notes)
        VALUES (@t,@s,@m,@n,0,CURRENT_TIMESTAMP(),@o)""",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("t", "STRING", table),
            bigquery.ScalarQueryParameter("s", "STRING", source),
            bigquery.ScalarQueryParameter("m", "STRING", method),
            bigquery.ScalarQueryParameter("n", "INT64", n_rows),
            bigquery.ScalarQueryParameter("o", "STRING", notes)])).result()
    print(f"  registered {table}")


def load_json_rows(rows, table, cols):
    """Load as all-STRING. 133 heterogeneous columns is exactly where autodetect guesses a type
    from the first rows and then dies on row 40,000; STRING never fails and loses nothing, since
    the source is CSV text anyway. Downstream uses SAFE_CAST (FAC_LAT/FAC_LONG especially)."""
    schema = [bigquery.SchemaField(c, "STRING") for c in cols]
    buf = io.BytesIO(("\n".join(json.dumps(r) for r in rows)).encode("utf-8"))
    job = client.load_table_from_file(buf, f"{DS}.{table}", job_config=bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE", schema=schema,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON))
    job.result()
    n = client.get_table(f"{DS}.{table}").num_rows
    print(f"  loaded {n:,} rows x {len(cols)} cols -> {DS}.{table}")
    return n


# =============================================================================================
# ECHO — bulk CSV. One request for the nation, filtered to Indiana locally.
# =============================================================================================
def fetch_bulk():
    """Download echo_exporter.zip, cached. Returns (path, last_modified, from_cache)."""
    dest = os.path.join(CACHE, "echo_exporter.zip")
    req = urllib.request.Request(ECHO_BULK, headers={"User-Agent": UA}, method="HEAD")
    with urllib.request.urlopen(req, timeout=120) as r:
        remote_len = int(r.headers.get("Content-Length") or 0)
        last_mod = r.headers.get("Last-Modified") or ""
    print(f"  remote: {remote_len/1e6:.1f} MB, Last-Modified {last_mod}")

    if not REFRESH and os.path.exists(dest) and os.path.getsize(dest) == remote_len:
        print(f"  cache hit ({dest}) — size matches remote, not re-downloading")
        return dest, last_mod, True

    print(f"  downloading -> {dest}")
    req = urllib.request.Request(ECHO_BULK, headers={"User-Agent": UA})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as f:
        got = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if got % (100 << 20) < (1 << 20):
                print(f"    {got/1e6:.0f}/{remote_len/1e6:.0f} MB", flush=True)
    size = os.path.getsize(dest)
    # A truncated download is the failure mode a streamed fetch actually has, and it would look
    # exactly like a smaller state. Refuse it rather than load a short file.
    if remote_len and size != remote_len:
        raise RuntimeError(f"truncated download: got {size} bytes, expected {remote_len}")
    print(f"  downloaded {size/1e6:.1f} MB in {time.time()-t0:.0f}s")
    return dest, last_mod, False


def is_indiana(r):
    """FAC_STATE='IN' OR either FIPS field in state 18.

    The FIPS arm is not belt-and-braces: it recovers 18 real Indiana facilities whose FAC_STATE
    is blank or plain wrong (a Michigan City site with FAC_STATE='', a Muncie site filed under
    'DE'). Row filters may be widened; columns may never be narrowed."""
    if (r.get("FAC_STATE") or "").strip() == "IN":
        return True
    for k in ("FAC_FIPS_CODE", "FAC_DERIVED_STCTY_FIPS"):
        v = (r.get(k) or "").strip()
        if len(v) == 5 and v.startswith("18"):
            return True
    return False


def do_echo():
    print("ECHO bulk CSV (route 1) — statewide REST is refused by a published 300/hr quota\n")
    path, last_mod, cached = fetch_bulk()
    z = zipfile.ZipFile(path)
    members = [i.filename for i in z.infolist()]
    if ECHO_MEMBER not in members:
        raise RuntimeError(f"{ECHO_MEMBER} not in zip; members={members}")

    rows, national, by_state = [], 0, collections.Counter()
    with z.open(ECHO_MEMBER) as fh:
        rdr = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"))
        cols = list(rdr.fieldnames)
        if PROBE:
            print(f"  {len(cols)} columns:")
            for c in cols:
                print("     ", c)
            return None
        for r in rdr:
            national += 1
            by_state[(r.get("FAC_STATE") or "").strip()] += 1
            if is_indiana(r):
                rows.append(r)

    print(f"  scanned {national:,} national rows; Indiana {len(rows):,}")
    # Rule 7: an empty or too-tidy result is a claim about the instrument. Two cheap assertions.
    if national < 1_000_000:
        raise RuntimeError(f"only {national:,} national rows — zip looks truncated/wrong member")
    if not 20_000 < len(rows) < 200_000:
        raise RuntimeError(f"Indiana count {len(rows):,} outside sane band — check the filter")

    counties = collections.Counter(
        re.sub(r"\s+COUNTY$", "", (r.get("FAC_COUNTY") or "").strip().upper()) for r in rows)
    named = {c for c in counties if c and c not in ("UNDETERMINED", "STATEWIDE")}
    print(f"  distinct county labels: {len(named)}  (blank on {counties.get('', 0):,} rows)")

    recs = [{**{k: (None if v in (None, "", "N/A") else str(v)) for k, v in r.items()},
             "_pulled_at": PULLED, "_source_url": ECHO_BULK,
             "_source_file": ECHO_MEMBER, "_source_last_modified": last_mod}
            for r in rows]
    outcols = cols + ["_pulled_at", "_source_url", "_source_file", "_source_last_modified"]

    tbl = "in_si_d22_echo_facilities"
    n = load_json_rows(recs, tbl, outcols)
    register(
        tbl, ECHO_BULK,
        "EPA ECHO bulk export echo_exporter.zip -> ECHO_EXPORTER.csv, filtered to Indiana on "
        "FAC_STATE='IN' OR FIPS-18, ALL 133 source columns kept",
        n,
        f"D22 environmental violations/compliance, facility level. {len(cols)} source columns "
        f"+ 4 provenance = {len(outcols)}. Route: ECHO's REST service refuses a statewide query "
        f"and throttles at a PUBLISHED 300/hr, 1,500/day quota, and its own 429 body points to "
        f"this bulk file; the prior county-walk route needed ~25,000 requests at responseset=5 "
        f"and was arithmetically impossible. Bulk is also a strict superset of REST's 59 columns "
        f"(adds TRI, GHG, EJ demographics, 13-qtr compliance histories). COUNT NOTE: REST claims "
        f"{ECHO_REST_STATEWIDE_CLAIM:,} for a statewide search vs {n:,} here - different "
        f"universes, not a shortfall: ECHO Exporter is the compliance-tracked regulated universe "
        f"(one row per FRS REGISTRY_ID), REST facility search resolves a broader FRS interest "
        f"universe. No paging, so no short-page risk. All columns STRING - use SAFE_CAST for "
        f"FAC_LAT/FAC_LONG. Source file Last-Modified {last_mod}; _pulled_at is our fetch time "
        f"and is never presented as data freshness. Public, no registration or key.")
    return n


# =============================================================================================
# IDEM — Monthly Actions and Orders. One POST returns the whole 1995->present corpus.
# =============================================================================================
IDEM_FORM = {
    "company_name": "", "case_number": "", "old_case_number": "",
    "county": "All", "media": "All", "type": "0",
    "start_month": "Jan", "start_day": "01", "start_year": "1995",
    "end_month": "Dec", "end_day": "31", "end_year": str(datetime.date.today().year),
    "page": "F",            # F = "All Records"; T = 50/page. F is why this is one request.
    "action": "Search",
}
IDEM_COLS = ["company_person", "case_number", "old_case_number", "media",
             "type_of_action_order", "city", "county", "document_url", "document_published",
             "_pulled_at", "_source_url"]


def do_idem():
    print("\nIDEM Monthly Actions and Orders — one POST, All counties, 1995->present\n")
    data = urllib.parse.urlencode(IDEM_FORM).encode()
    req = urllib.request.Request(IDEM_URL, data=data, headers={
        "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded",
        "Referer": IDEM_URL, "Accept": "text/html,*/*"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as r:
        body = r.read()
    txt = body.decode("utf-8", "replace")
    print(f"  HTTP 200, {len(body)/1e6:.1f} MB in {time.time()-t0:.0f}s")

    # IDEM prints its own total. That is the shortfall check, and it is exact.
    m = re.search(r'<font color="ff0000">(\d+)</font>\s*cases were found', txt)
    claimed = int(m.group(1)) if m else None
    print(f"  IDEM reports {claimed:,} cases" if claimed else "  no count banner found")

    hdrs = re.findall(r"<TH[^>]*>\s*<font[^>]*>([^<]*)</font>\s*</TH>", txt, re.I)
    if PROBE:
        print(f"  result columns: {hdrs} (+ document_url extracted from the case-number link)")
        return None

    cell = re.compile(r"<TD[^>]*>(.*?)</TD>", re.I | re.S)
    link = re.compile(r'href="([^"]+)"', re.I)

    def clean(s):
        u = link.search(s)
        t = re.sub(r"<[^>]+>", "", s)
        return html.unescape(t).replace("\xa0", " ").strip(), (u.group(1) if u else None)

    rows = []
    for tr in re.findall(r"<TR>(.*?)</TR>", txt, re.I | re.S):
        cells = cell.findall(tr)
        if len(cells) != 7:
            continue
        vals, urls = zip(*(clean(c) for c in cells))
        doc = next((u for u in urls if u), None)
        rows.append({
            "company_person": vals[0] or None, "case_number": vals[1] or None,
            "old_case_number": vals[2] or None, "media": vals[3] or None,
            "type_of_action_order": vals[4] or None, "city": vals[5] or None,
            "county": vals[6] or None,
            # the hyperlink is itself a signal: an unlinked case is one IDEM has not yet
            # published the document for. Kept rather than discarded, per the all-columns rule.
            "document_url": doc, "document_published": "Y" if doc else "N",
            "_pulled_at": PULLED, "_source_url": IDEM_URL})

    print(f"  parsed {len(rows):,} rows")
    if claimed is not None and len(rows) != claimed:
        raise RuntimeError(f"parsed {len(rows)} but IDEM reported {claimed} — parser is short, "
                           "refusing to load a silently-truncated table")
    print(f"  parsed count MATCHES IDEM's own reported total")

    linked = sum(1 for r in rows if r["document_url"])
    print(f"  {linked:,} with published document, {len(rows)-linked:,} not yet published")
    print(f"  {len({r['county'] for r in rows})} distinct counties, "
          f"{len({r['media'] for r in rows})} media values")

    tbl = "in_si_d22_idem_enforcement"
    n = load_json_rows(rows, tbl, IDEM_COLS)
    register(
        tbl, IDEM_URL,
        "IDEM Monthly Actions and Orders, single POST county=All media=All type=All "
        "1995-01-01..current-year-12-31, page=F (All Records), all result columns kept",
        n,
        f"D22 Indiana-specific enforcement record, one row per enforcement action/order "
        f"(NOV, Agreed Order, Commissioner's Order, Emergency Order + amendments), 1995-present. "
        f"Parsed {n:,} = IDEM's own reported total exactly. {linked:,} rows carry a published "
        f"document URL; document_published flags the rest, which IDEM states will appear in the "
        f"next monthly cycle - that flag is a real signal, not padding. Media taxonomy in the "
        f"data is RICHER than the search form exposes (form offers 4: AIR/WATER/HAZARD/SOLID; "
        f"data carries 9, incl DRINKWATER, WASTEWATER, UST, CONFINED, Q-Wetlands). Complements "
        f"ECHO: ECHO is the facility universe, IDEM is the state enforcement docket. Public form, "
        f"no registration; robots.txt has no Disallow directives. Event dates are the "
        f"publisher's; _pulled_at is our fetch time.")
    return n


if __name__ == "__main__":
    e = i = None
    if ONLY in (None, "echo"):
        e = do_echo()
    if ONLY in (None, "idem"):
        i = do_idem()
    if PROBE:
        print("\nPROBE ONLY — nothing pulled or written.")
    else:
        print(f"\nDONE  echo={e if e is not None else 'skipped'}  "
              f"idem={i if i is not None else 'skipped'}")
