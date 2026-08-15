"""Lane E: polite probe of pipeline EBB endpoints. Saves responses to scratchpad for inspection.
>=1.1s per host, UA identifies us, no logins, GET only."""
import sys, time, os, json
import requests

UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"
OUT = r"C:\Users\ahend\AppData\Local\Temp\claude\C--Users-ahend-Downloads-Decennial-Summer-Work-Remaking-Orennia-REBUILD-PLANNING\e2c5e15c-d0e5-487b-889b-f478a7c7d3d4\scratchpad\probes"
os.makedirs(OUT, exist_ok=True)

last_hit = {}  # host -> ts

def get(name, url, timeout=30, allow_redirects=True):
    from urllib.parse import urlparse
    host = urlparse(url).netloc
    wait = 1.1 - (time.time() - last_hit.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout, allow_redirects=allow_redirects)
        last_hit[host] = time.time()
        ct = r.headers.get("Content-Type", "?")
        path = os.path.join(OUT, name)
        with open(path, "wb") as f:
            f.write(r.content)
        print(f"{r.status_code} {len(r.content):>9,}B {ct[:60]:<60} {name} {url}")
        if r.history:
            print(f"    redirects: {' -> '.join(h.url for h in r.history)} -> {r.url}")
        return r
    except Exception as e:
        last_hit[host] = time.time()
        print(f"ERR {type(e).__name__}: {e} {name} {url}")
        return None

if __name__ == "__main__":
    batch = sys.argv[1] if len(sys.argv) > 1 else "1"
    if batch == "1":
        # robots first (cheap, one per host)
        get("robots_anrpl.txt", "https://ebb.anrpl.com/robots.txt")
        get("robots_tceconnects.txt", "https://ebb.tceconnects.com/robots.txt")
        get("robots_et.txt", "https://pipelines.energytransfer.com/robots.txt")
        get("robots_tallgrass.txt", "https://pipeline.tallgrassenergylp.com/robots.txt")
        get("robots_enbridge_infopost.txt", "https://infopost.enbridge.com/robots.txt")
        get("robots_bwp.txt", "https://infopost.bwpipelines.com/robots.txt")
        get("robots_trellis.txt", "https://dtmidstream.trellisenergy.com/robots.txt")
        get("robots_km.txt", "https://pipeline.kindermorgan.com/robots.txt")
        get("robots_vector.txt", "https://www.vector-pipeline.com/robots.txt")
        # home/menu pages
        get("anr_home.html", "https://ebb.anrpl.com/")
        get("tallgrass_rex_point_oa.html", "https://pipeline.tallgrassenergylp.com/Pages/Point.aspx?pipeline=501&type=OA")
        get("vector_oa.html", "https://www.vector-pipeline.com/Informational-Postings/Capacity/Operationally-Available")
        get("et_pepl_oa.html", "https://pipelines.energytransfer.com/ipost/PEPL/capacity/operationally-available")
        get("km_home.html", "https://pipeline.kindermorgan.com/")
        get("trellis_mgt.html", "https://dtmidstream.trellisenergy.com/ptms/home/infopost/MGT")
        get("bwp_home.html", "https://infopost.bwpipelines.com/")
        get("enbridge_infopost.html", "https://infopost.enbridge.com/")
        get("tceconnects_home.html", "https://ebb.tceconnects.com/")
