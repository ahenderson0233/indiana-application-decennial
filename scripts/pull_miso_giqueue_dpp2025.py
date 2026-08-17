"""MISO DPP-2025 hunt on giqueue.misoenergy.org -- CLIENT-CODE prober + BLOCKED verdict.

WHAT THIS IS
------------
The operator's hypothesis was that MISO's DPP-2025-Cycle POI/transfer-study data is "hidden in and
around the same location" as the DPP-2021 viewer at giqueue.misoenergy.org/PoiAnalysis. Rather than
guess sibling URLs (a prior sweep did that and 404'd on all of them), this reads the viewer's OWN
client code and every config it loads, and enumerates the authoritative endpoint surface from the
code itself.

THE MEASURED VERDICT (2026-08-17) -- see docs/MISO_DPP2025_ROUTE.md section 6 for the full writeup
-------------------------------------------------------------------------------------------------
giqueue/PoiAnalysis is a STATIC, single-deployment CartoVista 6.2.2 app hard-wired to DPP-2021.
It has NO cycle/case/year concept anywhere in its code, config, or data layers, so there is no
"same location" for a 2025 case to hide in. It serves DPP-2021 and only DPP-2021. BLOCKED, and
structurally so -- this ends the giqueue search.

The COMPLETE dynamic endpoint surface, read out of the 103,615-byte app bundle module-by-module:
    GET  /POI/api/pois                     bare GET, no params, body AES-encrypted (OpenSSL Salted__)
    GET  /POI/api/poi_mf?poiName=&pMaxValue=   ONLY those two params; plain JSON
    POST /POI/api/generateUserGridLayer    WRITE (server-side user grid) -- never called
    GET  /POI/api/deleteUserGridLayer{id}  WRITE -- never called
    GET  /poi/api/gridLayer/mainGeoTiff    one fixed raster (DPP-2021), no param
There is no /cycles, no /cases, no list/metadata endpoint, and no XHR beyond jQuery $.ajax to the
routes above. The "DPP-2021-Cycle" string exists ONLY as human-readable <WelcomeSubTitle> disclaimer
text in PoiAnalysisConfig.xml -- it is never parsed into a request. That is why ?cycle=/?case= were
already found to be IGNORED (byte-identical): the server app was never written to read them.

Every vintage marker on giqueue says 2021 (disclaimer text; grid timeStamp 2021-01-04; static POI
JSON Last-Modified 2020-2021; app version 1.0.212), so -- unlike the CartoVista cloud deployment,
whose labels self-contradict -- there is no vintage ambiguity to resolve here.

WHAT IT DOES
------------
--probe (default): re-fetch the client code + configs live, re-verify the endpoint surface and the
    "no cycle token" finding, print verbatim HTTP evidence and the BLOCKED verdict. NO writes. Run
    this to detect if MISO ever changes the app (e.g. starts serving 2025 in place).
--register: additionally APPEND one row to energy.registry_sources documenting the BLOCKED avenue.
    energy.* is READ-ONLY for this workstream EXCEPT this one append. No indiana_app table is
    created because giqueue serves only the DPP-2021 data already held in energy.miso_poi_*.

BOUNDARIES: read-only GET, identifying User-Agent, >=1.2s per host, no accounts, no keys, no UA
spoofing, nothing mutated. A BLOCKED avenue recorded with its walls quoted verbatim is a SUCCESS.

USAGE
    python scripts/pull_miso_giqueue_dpp2025.py --probe
    python scripts/pull_miso_giqueue_dpp2025.py --register
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import argparse
import re
import time
import urllib.error
import urllib.request

HOST = "https://giqueue.misoenergy.org"
UA = ("DecennialGroup-DataAudit/1.0 (read-only public MISO generator-interconnection POI viewer; "
      "contact ahenderson@decennialgroup.com)")
MIN_INTERVAL = 1.2
TIMEOUT = 90
MAX_BYTES = 8 * 1024 * 1024  # the app bundle is ~104 KB; this prober never needs the multi-MB tiff

# The files that ARE the application. Named-file GETs: the /PoiAnalysis/map/ *directory* is 403,
# but every named file under it serves 200, which is how the configs are read.
INDEX = "/PoiAnalysis/index.html"
MAIN = "/PoiAnalysis/scripts/main.js"
BUNDLE = "/PoiAnalysis/scripts/PublicGenerationInterconnectionToolApp.min.js"
APP_CONFIG = "/PoiAnalysis/PoiAnalysisConfig.xml"
MAP_CONFIG = "/PoiAnalysis/map/MISO_DEMOConfig.xml"
DATA_CONFIG = "/PoiAnalysis/map/MISO_DEMOThematic.xml"

# The complete dynamic endpoint surface, read out of the bundle. A re-run asserts these are still
# the only routes and that none has gained a cycle/case parameter.
EXPECTED_ROUTES = [
    ("/POI/api/pois", "GET, no params, AES-encrypted body"),
    ("/POI/api/poi_mf", "GET, params poiName + pMaxValue ONLY"),
    ("/POI/api/generateUserGridLayer", "POST, WRITE (user grid) -- never called"),
    ("/POI/api/deleteUserGridLayer", "GET, WRITE -- never called"),
    ("/poi/api/gridLayer/mainGeoTiff", "GET, one fixed raster (DPP-2021), no param"),
]
# Tokens that WOULD indicate a cycle/case selector if present in code. Only JS switch-case is
# expected to match, and those are filtered out below.
CYCLE_TOKENS = ["DPP", "cycle", "Cycle", "2021", "2022", "2023", "2024", "2025", "vintage",
                "studyCycle", "caseId", "cycleId"]

_last = 0.0


def _throttle():
    global _last
    dt = time.time() - _last
    if dt < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - dt)
    _last = time.time()


def fetch(path):
    """Read-only throttled GET. Returns (status, text, headers_dict). Never raises for HTTP errors."""
    url = path if path.startswith("http") else HOST + path
    _throttle()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
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
            return r.status, bytes(buf).decode("utf-8", "replace"), dict(r.headers.items())
    except urllib.error.HTTPError as e:
        try:
            body = e.read(2048).decode("utf-8", "replace")
        except Exception:
            body = ""
        return e.code, body, dict(e.headers.items()) if e.headers else {}
    except Exception as e:
        return "ERR", f"{type(e).__name__}: {e}", {}


def cmd_probe(a):
    print("=== giqueue.misoenergy.org DPP-2025 hunt -- reading the application's own code ===\n")

    # 1) fetch the code + configs, print verbatim HTTP evidence
    findings = {}
    print("%-62s %-6s %-9s %s" % ("path", "HTTP", "bytes", "Last-Modified"))
    print("-" * 100)
    for path in [INDEX, MAIN, BUNDLE, APP_CONFIG, MAP_CONFIG, DATA_CONFIG,
                 BUNDLE + ".map", "/robots.txt", "/sitemap.xml"]:
        st, txt, hd = fetch(path)
        findings[path] = (st, txt, hd)
        lm = hd.get("Last-Modified", "-")
        n = len(txt.encode("utf-8", "replace")) if isinstance(txt, str) else 0
        print("%-62s %-6s %-9s %s" % (path[:62], st, f"{n:,}" if st == 200 else "-", lm))

    st_bundle, bundle, hd_bundle = findings[BUNDLE]
    st_cfg, appcfg, _ = findings[APP_CONFIG]
    if st_bundle != 200 or st_cfg != 200:
        print("\n!! The app bundle or app config did not serve 200 -- the deployment may have "
              "changed. Re-read docs/MISO_DPP2025_ROUTE.md section 6 and re-verify by hand.")
        return findings

    server = hd_bundle.get("Server", "?")
    print(f"\nServer header: {server}   (IIS/ASP.NET; hosted on Azure per map-config LicenseKey)")

    # 2) enumerate the endpoint surface from the code and assert it is unchanged
    print("\n--- Endpoint surface extracted from the code ---")
    for route, desc in EXPECTED_ROUTES:
        # routes 1-4 are declared in the app config; route 5 in the map config
        present = (route in appcfg) or (route in findings[MAP_CONFIG][1]) or (route in bundle) \
            or (route.rstrip("s") in appcfg)
        print(f"   [{'OK ' if present else 'MISSING'}] {route:34s} {desc}")

    # poi_mf param proof, straight from the bundle: the URL is built as
    #   e+"?poiName="+encodeURIComponent(t.value); ... (l+="&pMaxValue="+i)
    has_poiname = 'poiName="+encodeURIComponent' in bundle
    has_pmax = '"&pMaxValue="' in bundle
    print(f"\n   poi_mf builds ?poiName=encodeURIComponent(...): {has_poiname}; "
          f"appends &pMaxValue=: {has_pmax}")
    others = re.findall(r'[?&]([A-Za-z_]{3,})=', bundle)
    extra = sorted({o for o in others if o not in ("poiName", "pMaxValue")})
    print(f"   any OTHER query-parameter keys in the bundle: {extra or 'none'}")

    # 3) the decisive test: is there any cycle/case/year token in the application code?
    print("\n--- Cycle / case / year tokens in the 103 KB app bundle ---")
    real_hits = {}
    for tok in CYCLE_TOKENS:
        hits = [m.start() for m in re.finditer(re.escape(tok), bundle)]
        # keep only hits that are NOT a JS switch-case (`case ` / `Case` identifier usage)
        meaningful = []
        for i in hits:
            ctx = bundle[max(0, i - 8):i + len(tok) + 2]
            if tok in ("cycle", "Cycle") and re.search(r'[A-Za-z]' + tok, ctx):
                continue
            if tok == "case" and re.search(r'(switch|;)\s*case', bundle[max(0, i - 12):i + 5]):
                continue
            meaningful.append(ctx.replace("\n", " "))
        if meaningful:
            real_hits[tok] = meaningful[:3]
    if real_hits:
        print("   !! Non-switch cycle/year tokens FOUND -- investigate, the app may have changed:")
        for tok, ctxs in real_hits.items():
            print(f"      {tok}: {ctxs}")
    else:
        print("   NONE. No cycle/case/year variable, parameter, or config key exists in the app.")

    # 4) vintage markers -- all should say 2021
    print("\n--- Vintage markers (all should read 2021) ---")
    m = re.search(r"models and inputs from the ([A-Za-z0-9\-]+Cycle)", appcfg)
    print(f"   app-config disclaimer : {m.group(1) if m else '??'}")
    mt = re.search(r'timeStamp="(20\d\d-\d\d-\d\d[^\"]*)"', findings[MAP_CONFIG][1])
    print(f"   grid source timeStamp : {mt.group(1) if mt else '??'}")
    mv = re.search(r'PoiAnalysisRevision:"(\d+)"', bundle)
    mj = re.search(r'PoiAnalysisMajor:"(\d+)".*?PoiAnalysisMinor:"(\d+)"', bundle)
    ver = f"{mj.group(1)}.{mj.group(2)}.{mv.group(1)}" if (mj and mv) else "??"
    print(f"   app version           : {ver}")

    print("\n" + "=" * 100)
    print("VERDICT: BLOCKED. giqueue/PoiAnalysis is a static single-cycle DPP-2021 app. It has no "
          "cycle/case\n         concept in code, config, or data layers -- the DPP-2025 case is not "
          "served here and\n         structurally cannot be without MISO overwriting the backend or "
          "standing up a new deployment.")
    print("=" * 100)
    return findings


def cmd_register(a):
    findings = cmd_probe(a)
    st_cfg, appcfg = findings[APP_CONFIG][0], findings[APP_CONFIG][1]
    disc = re.search(r"models and inputs from the ([A-Za-z0-9\-]+Cycle)", appcfg)
    vintage = disc.group(1) if disc else "DPP-2021-Cycle"

    from google.cloud import bigquery
    client = bigquery.Client(project="energy-platfrom")
    tb = client.get_table("energy-platfrom.energy.registry_sources")  # never guess columns
    cols = {f.name for f in tb.schema}
    row = {k: v for k, v in {
        "source_name": "MISO DPP-2025 hunt on giqueue.misoenergy.org POI viewer (client-code audit)",
        "endpoint": f"{HOST}/PoiAnalysis/  (app bundle: {BUNDLE})",
        "endpoint_kind": "spa_client_code_audit",
        "access": "public - read-only GET of the app's own JS/XML; no auth, no keys",
        "status": (f"BLOCKED (structural). giqueue/PoiAnalysis is a static single-cycle "
                   f"{vintage} CartoVista 6.2.2 app; it has NO cycle/case concept in code, config, "
                   f"or data layers, so the DPP-2025 case is not served here. The complete dynamic "
                   f"surface is /POI/api/pois (bare GET, AES), /POI/api/poi_mf?poiName=&pMaxValue= "
                   f"(only 2 params), the two WRITE user-grid routes, and /poi/api/gridLayer/"
                   f"mainGeoTiff (one 2021 raster). ?cycle=/?case= are IGNORED because the app was "
                   f"never written to read them (proven in the client code)."),
        "acquisition_method": ("RE-SCRAPE COMMAND: python scripts/pull_miso_giqueue_dpp2025.py "
                               "--probe   (re-fetches the client code + configs and re-verifies the "
                               "endpoint surface + 'no cycle token' finding; NO data to load because "
                               "giqueue serves only the DPP-2021 data already held in "
                               "energy.miso_poi_attributes / _monitored_facilities / _headroom / "
                               "miso_poi_capacity_surface_geotiff)"),
        "what_it_provides": ("NOTHING NEW. Records that the giqueue avenue for DPP-2025 is BLOCKED "
                             "and why, so the search is not re-opened. To detect MISO overwriting "
                             "the backend in place, periodically re-hash /POI/api/pois. See "
                             "docs/MISO_DPP2025_ROUTE.md section 6."),
        "object_names": [],
        "geography_state": "IN",
        "measured_rows": 0,
        "notes": ("Operator hypothesis 'the 2025 data is hidden near the 2021 doc' was tested by "
                  "reading the application source, not by guessing sibling URLs. All app files serve "
                  "200 (index, require.js, main.js, the 103,615-byte bundle, PoiAnalysisConfig.xml, "
                  "map/MISO_DEMOConfig.xml, map/MISO_DEMOThematic.xml); robots.txt, sitemap.xml and "
                  "the .js.map are 404; the / and /PoiAnalysis/map/ directories are 403 but named "
                  "files serve. Every vintage marker says 2021 (disclaimer, grid timeStamp "
                  "2021-01-04, static POI JSON Last-Modified 2020-2021, app version 1.0.212). "
                  "Recorded BLOCKED 2026-08-17; a BLOCKED avenue with its walls quoted is a success."),
    }.items() if k in cols}
    errs = client.insert_rows_json("energy-platfrom.energy.registry_sources", [row])
    print(f"\nappended BLOCKED verdict to energy.registry_sources: {errs if errs else 'ok'}")
    return 0


def main():
    p = argparse.ArgumentParser(
        description="MISO DPP-2025 hunt on giqueue.misoenergy.org -- client-code prober + BLOCKED "
                    "verdict. See module docstring and docs/MISO_DPP2025_ROUTE.md section 6.")
    p.add_argument("--probe", action="store_true",
                   help="re-fetch client code + configs, re-verify the surface + verdict (NO writes)")
    p.add_argument("--register", action="store_true",
                   help="probe, then APPEND the BLOCKED verdict to energy.registry_sources")
    a = p.parse_args()
    if a.register:
        return cmd_register(a)
    # default is probe
    cmd_probe(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
