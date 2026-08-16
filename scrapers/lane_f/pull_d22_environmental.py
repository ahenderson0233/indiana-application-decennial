"""D22 environmental violations — ALL COLUMNS, Indiana.

Lane F discovery (scrapers/lane_f/MISSING_SIGNALS_FINDINGS.md) ranked D22 the easiest viable
win of the eight missing signals: EPA ECHO's REST service answered openly for Indiana (25,330
active facilities, 372 significant violators) and needs no registration.

THE ALL-COLUMNS RULE, and why it is not optional here: an endpoint usually carries more than
one signal, and we have already been burned discovering columns after the fact — Lane D's pulls
turned up eleven signal-bearing columns nobody had asked for (SRI's own lat/lon on 36% of rows,
a 100%-populated Accela case link, WARN's NAICS). So this requests EVERY column the service
offers and stores them all, rather than the handful D22 nominally needs. Deciding what matters
is a later, cheaper step than going back for a second pull.

Rules honoured: public endpoint, no registration, no key, no CAPTCHA, no paywall; >=1 req/s;
identifying User-Agent; observed EVENT dates kept distinct from `_pulled_at`; writes ONLY to
energy-platfrom.indiana_app; registered in the same run.

Usage:
    python scrapers/lane_f/pull_d22_environmental.py --probe     # column discovery only
    python scrapers/lane_f/pull_d22_environmental.py             # full pull + load
"""
import json, sys, time, urllib.parse, urllib.request, datetime
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"
ECHO = "https://echodata.epa.gov/echo/echo_rest_services.get_facilities"
# get_qid, NOT get_download. get_download refuses JSON outright — "The Output type was JSON.
# Output Type must be CSV or GEOJSOND" — and returns that as an HTML body, so a JSON parse of it
# dies with a decoder error that looks like a network fault rather than the plain refusal it is.
ECHO_ROWS = "https://echodata.epa.gov/echo/echo_rest_services.get_qid"
PROBE = "--probe" in sys.argv
client = bigquery.Client(project="energy-platfrom")

def get(url, params, pause=1.1, attempts=5):
    """One request, rate-limited, identifying itself. Returns parsed JSON.

    BOUNDED RETRY on 500/503/429 only, with exponential backoff — the same shape Lane D added to
    `arcgis_pull_all` after an ArcGIS 503 killed a 910k-row pull mid-flight. ECHO threw a bare
    HTTP 500 on the second county here; it is transient server load, not a wall, and a wall would
    look different (401/403, or a body explaining the gate). Any other status still raises at once,
    so a real refusal is never retried into looking like a success."""
    q = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(q, headers={"User-Agent": UA, "Accept": "application/json"})
    last = None
    for i in range(attempts):
        time.sleep(pause if i == 0 else min(4 * 2 ** (i - 1), 32))
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code not in (500, 502, 503, 429):
                raise                      # a genuine refusal - do not retry it away
            last = f"HTTP {e.code}"
            print(f"      transient {last}, retry {i+1}/{attempts}", flush=True)
        except (urllib.error.URLError, TimeoutError) as e:
            last = str(e)[:60]
            print(f"      network {last}, retry {i+1}/{attempts}", flush=True)
    raise RuntimeError(f"{attempts} attempts exhausted ({last}) for {q[:110]}")

# ---- step 1: open the query. ECHO returns a QID that the download endpoint then pages. ----
# A statewide request is REFUSED, and the refusal is informative rather than a shape change:
#   "Rows Returned would be 127266. Queryset Limit would be exceeded - please make search
#    parameters more selective."
# So the state is walked COUNTY BY COUNTY. That narrows the row count without narrowing the
# COLUMNS, which is the thing that must not be narrowed. Never trade columns for a smaller
# response when the row filter is the lever.
def open_query(params):
    meta = get(ECHO, {"output": "JSON", "responseset": "5", **params})
    res = meta.get("Results", {}) or {}
    err = (res.get("Error") or {}).get("ErrorMessage")
    if err: return None, 0, err
    return res.get("QueryID"), int(res.get("QueryRows") or 0), None

COUNTIES = [r.NAME for r in client.query("""
    SELECT NAME FROM `energy-platfrom.energy.county_boundaries`
    WHERE STATEFP='18' ORDER BY NAME""")]
print(f"ECHO: statewide is refused by the queryset limit; walking {len(COUNTIES)} counties\n")

qid, n, err = open_query({"p_st": "IN", "p_co": COUNTIES[0]})
if err:
    print(f"  even a single county was refused: {err}"); sys.exit(1)
print(f"  probe county {COUNTIES[0]}: QueryID {qid} · {n:,} facilities")

# ---- step 2: discover the column set the service actually returns ----
first = get(ECHO_ROWS, {"output": "JSON", "qid": qid, "qcolumns": "", "pageno": 1, "responseset": "5"})
rows0 = (first.get("Results", {}) or {}).get("Facilities") or []
if not rows0:
    print("  no rows on page 1; body head:", json.dumps(first)[:400]); sys.exit(1)
COLS = sorted({k for r in rows0 for k in r})
print(f"  service returns {len(COLS)} columns: {COLS[:12]}{' ...' if len(COLS) > 12 else ''}")
if PROBE:
    print("\nPROBE ONLY — nothing pulled or written.")
    print("full column list:"); [print("   ", c) for c in COLS]
    sys.exit()

# ---- step 3: walk every county, paging each to exhaustion, keeping EVERY column ----
def pull_county(county):
    q, expect, e = open_query({"p_st": "IN", "p_co": county})
    if e or not q:
        return [], 0, e or "no QueryID"
    got, page = [], 1
    while True:
        d = get(ECHO_ROWS, {"output": "JSON", "qid": q, "qcolumns": "", "pageno": page,
                            "responseset": "5"})
        batch = (d.get("Results", {}) or {}).get("Facilities") or []
        if not batch: break
        got.extend(batch); page += 1
        if len(got) >= expect or page > 500: break
    return got, expect, None

out, expected_total, failures = [], 0, []
for i, county in enumerate(COUNTIES, 1):
    # One county failing must not kill the other 91. A partial pull that REPORTS what it missed
    # is usable; a crash at county 2 of 92 is not, and neither is a silent skip.
    try:
        got, expect, e = pull_county(county)
    except Exception as ex:
        got, expect, e = [], 0, str(ex)[:120]
    expected_total += expect
    if e: failures.append((county, e))
    out.extend(got)
    print(f"  [{i:>2}/{len(COUNTIES)}] {county:<16} {len(got):>6,} / {expect:>6,}"
          + (f"  ERROR {e[:50]}" if e else ""), flush=True)
if failures:
    print(f"\n  {len(failures)} county queries failed — reported, NOT silently dropped:")
    for c, e in failures[:10]: print(f"    {c}: {e[:90]}")

# de-duplicate on the facility registry id: a facility can sit in two county queries
key = "RegistryID" if out and "RegistryID" in out[0] else (COLS[0] if COLS else None)
if key:
    seen, uniq = set(), []
    for r in out:
        k = r.get(key)
        if k and k in seen: continue
        if k: seen.add(k)
        uniq.append(r)
    print(f"\n  {len(out):,} rows pulled -> {len(uniq):,} unique on {key}")
    out = uniq
n = expected_total

pulled = datetime.datetime.now(datetime.timezone.utc).isoformat()
recs = [{**{k: (None if v in ("", "N/A") else str(v)) for k, v in r.items()},
         "_pulled_at": pulled, "_source_url": ECHO} for r in out]

# publisher count vs ours — a silent shortfall is the failure mode paging always has
print(f"\npublisher said {n:,}; we hold {len(recs):,}"
      + ("  MATCH" if len(recs) == n else "  <-- MISMATCH, investigate before trusting"))

tbl = f"{DS}.in_si_d22_echo_facilities"
job = client.load_table_from_json(recs, tbl, job_config=bigquery.LoadJobConfig(
    write_disposition="WRITE_TRUNCATE", autodetect=True))
job.result()
got = client.get_table(tbl).num_rows
print(f"loaded {got:,} rows -> {tbl}")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_si_d22_echo_facilities'").result()
client.query(f"""INSERT `{DS}._registry`
  (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES (@t,@s,@m,@n,0,CURRENT_TIMESTAMP(),@o)""",
  job_config=bigquery.QueryJobConfig(query_parameters=[
    bigquery.ScalarQueryParameter("t", "STRING", "in_si_d22_echo_facilities"),
    bigquery.ScalarQueryParameter("s", "STRING", ECHO),
    bigquery.ScalarQueryParameter("m", "STRING",
      "EPA ECHO REST, p_st=IN, ALL COLUMNS (qcolumns deliberately unset), paged to exhaustion"),
    bigquery.ScalarQueryParameter("n", "INT64", got),
    bigquery.ScalarQueryParameter("o", "STRING",
      f"D22 environmental violations. {len(COLS)} columns kept - every column the service "
      "returns, not the subset D22 nominally needs, because an endpoint usually carries more "
      "than one signal (Lane D found 11 unasked-for signal columns after the fact). Publisher "
      f"count {n:,} vs loaded {got:,}. Public endpoint, no registration or key. Event dates are "
      "the publisher's; _pulled_at is stored separately and is never presented as freshness.")])).result()
print("registered")
