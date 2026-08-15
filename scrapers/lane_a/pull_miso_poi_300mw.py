"""Bounded MISO POI re-harvest at pMaxValue=300 (operator directive): the same public
giqueue endpoint the platform already harvested at 99,999 MW, re-asked at a 300 MW-class
request for INDIANA POIs only — this yields the single representative headroom number the
infinite probe cannot. Read-only GETs, >=1.15s throttle, identifying UA, resumable.
Loads energy-platfrom.indiana_app.in_miso_poi_300mw (+_registry row, same run)."""
import json, os, time, urllib.parse, urllib.request, datetime
from google.cloud import bigquery

HOST = "https://giqueue.misoenergy.org"
MF_URL = f"{HOST}/POI/api/poi_mf"
PMAX = 300
UA = ("DecennialGroup-research/1.0 (read-only public MISO POI viewer; "
      "ahenderson@decennialgroup.com)")
MIN_INTERVAL = 1.15
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_cache_300mw")
os.makedirs(CACHE, exist_ok=True)
NDJSON = os.path.join(CACHE, "poi_mf_300.ndjson")
DONE = os.path.join(CACHE, "done.tsv")
DS = "energy-platfrom.indiana_app"

client = bigquery.Client(project="energy-platfrom")
names = [r.poi_name for r in client.query(
    f"SELECT poi_name FROM `{DS}.in_bus_headroom_miso` WHERE location_status='indiana' ORDER BY poi_name")]
done = set()
if os.path.exists(DONE):
    done = {l.split("\t")[0] for l in open(DONE, encoding="utf-8")}
todo = [n for n in names if n not in done]
print(f"{len(names)} Indiana POIs, {len(done)} done, {len(todo)} to fetch "
      f"(~{len(todo)*MIN_INTERVAL/60:.1f} min)", flush=True)

_last = 0.0
def fetch(url, retries=3):
    global _last
    err = None
    for a in range(retries):
        dt = time.time() - _last
        if dt < MIN_INTERVAL: time.sleep(MIN_INTERVAL - dt)
        _last = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception as e:
            err = e; time.sleep(2.5 * (a + 1))
    raise RuntimeError(f"{url}: {err}")

n = 0
with open(NDJSON, "a", encoding="utf-8") as out, open(DONE, "a", encoding="utf-8") as dn:
    for i, name in enumerate(todo, 1):
        url = f"{MF_URL}?poiName={urllib.parse.quote(name)}&pMaxValue={PMAX}"
        try:
            recs = json.loads(fetch(url))
        except Exception as e:
            dn.write(f"{name}\tERROR\t{str(e)[:100]}\n"); dn.flush()
            print(f"  !! {name}: {str(e)[:90]}", flush=True); continue
        for rec in recs:
            rec["_poi_name_requested"] = name
            rec["_pmax_request_mw"] = PMAX
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        n += len(recs)
        dn.write(f"{name}\tOK\t{len(recs)}\n")
        if i % 50 == 0:
            out.flush(); dn.flush(); print(f"  {i}/{len(todo)} ({n:,} rows)", flush=True)
print(f"crawl complete: {n:,} facility rows", flush=True)

rows = [json.loads(l) for l in open(NDJSON, encoding="utf-8")]
# stringify everything: autodetect on mixed publisher types is a schema roulette
rows = [{k: (None if v is None else str(v)) for k, v in r.items()} for r in rows]
job = client.load_table_from_json(
    rows, f"{DS}.in_miso_poi_300mw",
    job_config=bigquery.LoadJobConfig(autodetect=True, write_disposition="WRITE_TRUNCATE"))
job.result()
total = client.get_table(f"{DS}.in_miso_poi_300mw").num_rows
client.query(f"""INSERT `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
  VALUES ('in_miso_poi_300mw','giqueue.misoenergy.org POI/api/poi_mf?pMaxValue=300',
          'bounded re-harvest, Indiana POIs only', {total}, 0, CURRENT_TIMESTAMP(),
          'the 300MW-class request the 99999 probe could not answer; observed vintage per publisher payload')""").result()
print(f"LOADED in_miso_poi_300mw: {total:,} rows. 300MW HARVEST COMPLETE", flush=True)
