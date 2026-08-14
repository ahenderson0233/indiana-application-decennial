"""PJM RTEP per-upgrade detail + cost-allocation fragments -> BQ.

Endpoints (public GET, no login; the page's own modal loaders):
    /m/ProjectConst/UpgradeDetails?upgradeId={id}          HTML fragment: criteria violation,
        description, type, driver, sub-region, location, task, equipment, related materials links
    /m/ProjectConst/UpgradeCostAllocations?upgradeId={id}  HTML fragment: per-zone percent under
        'Non-Load Ratio Share' / 'Load Ratio Share'

SCOPE THIS RUN: the 932 Indiana-naming upgrade ids from indiana_app.in_pjm_rtep_upgrades
(same token-match as in_rto_expansion). Full universe is 15,443 ids = ~9.4h at >=1.1s/request
x2 endpoints; deliberately not attempted in-session. FULL-UNIVERSE RE-SCRAPE: run with --all.

Resumable: NDJSON cache + done-file; re-running skips finished ids. >=1.1s between requests
(one host). Observed event dates: the fragments carry no dates — dates stay in
in_pjm_rtep_upgrades' own columns; these tables carry identity/cost-split facts + _pulled_at.
"""
from __future__ import annotations

import argparse
import html as html_mod
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", r"C:\Users\ahend\bq-key.json")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"
BASE = "https://www.pjm.com/m/ProjectConst"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "_cache_pjm_details")
ND_DET = os.path.join(CACHE, "details.ndjson")
ND_CA = os.path.join(CACHE, "costalloc.ndjson")
DONE = os.path.join(CACHE, "done.tsv")
IN_TOKEN = r"(^|[^A-Z])IN([^A-Z]|$)"

_last = [0.0]


def get(url):
    dt = time.time() - _last[0]
    if dt < 1.1:
        time.sleep(1.1 - dt)
    _last[0] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.status, r.read(8_000_000).decode("utf-8", "replace")


def parse_details(uid, body):
    kv = {}
    pairs = re.findall(
        r'<div class="upgradeIDRowHeader">([^<]*)</div>\s*'
        r'<div class="upgradeID(?:RowContent|nonGridContent)">(.*?)</div>', body, re.S)
    mats = []
    for k, v in pairs:
        k = html_mod.unescape(k).strip()
        if k == "Related Projects & Materials":
            continue
        kv[k] = html_mod.unescape(re.sub(r"<[^>]+>", "", v)).strip() or None
    seg = body.split("Related Projects &amp; Materials")[-1] if "Related Projects &amp; Materials" in body \
        else body.split("Related Projects & Materials")[-1] if "Related Projects & Materials" in body else ""
    for href, label in re.findall(r'<a href="([^"]*)"[^>]*>(.*?)</a>', seg, re.S):
        label = html_mod.unescape(re.sub(r"<[^>]+>", "", label)).strip()
        if label:
            mats.append({"label": label, "href": html_mod.unescape(href).strip()})
    return {
        "upgrade_id": uid,
        "criteria_violation": kv.get("Criteria Violation"),
        "description": kv.get("Description"),
        "project_type": kv.get("Project Type"),
        "driver": kv.get("Driver"),
        "sub_region": kv.get("Sub Region"),
        "location": kv.get("Location"),
        "task": kv.get("Task"),
        "equipment": kv.get("Equipment"),
        "related_materials": json.dumps(mats) if mats else None,
        "n_related_materials": len(mats),
    }


def parse_costalloc(uid, body):
    rows = []
    # sections: <h3>NAME</h3> ... <div class="costAllocationColumnList"> items </div>
    for sec_name, sec_body in re.findall(
            r"<h3>([^<]*)</h3>\s*<div class=\"costAllocationColumnList\">(.*?)</div>\s*(?=<h3>|</div>|\Z)",
            body, re.S):
        for zone, pct in re.findall(
                r'<div class="costAllocationPercentItem"><span><b>([^<]*?):?</b></span>'
                r'<span>\s*([0-9.,-]+)\s*</span></div>', sec_body):
            rows.append({
                "upgrade_id": uid,
                "share_type": html_mod.unescape(sec_name).strip(),
                "zone": html_mod.unescape(zone).strip().rstrip(":"),
                "percent": float(pct.replace(",", "")),
            })
    return rows


def load_done():
    done = set()
    if os.path.exists(DONE):
        with open(DONE, encoding="utf-8") as f:
            for line in f:
                done.add(line.split("\t")[0])
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="full 15,443-id universe (hours)")
    ap.add_argument("--crawl", action="store_true")
    ap.add_argument("--load", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    from google.cloud import bigquery
    c = bigquery.Client(project="energy-platfrom")

    if a.crawl:
        os.makedirs(CACHE, exist_ok=True)
        where = "" if a.all else \
            f"WHERE REGEXP_CONTAINS(UPPER(IFNULL(state,'')), r'{IN_TOKEN}')"
        ids = [r.upgrade_id for r in c.query(
            f"SELECT DISTINCT upgrade_id FROM `energy-platfrom.indiana_app.in_pjm_rtep_upgrades` "
            f"{where} ORDER BY upgrade_id").result()]
        done = load_done()
        todo = [i for i in ids if i not in done]
        if a.limit:
            todo = todo[:a.limit]
        print(f"{len(ids):,} ids in scope, {len(done):,} done, {len(todo):,} to fetch "
              f"(~{len(todo) * 2 * 1.1 / 60:.0f} min)", flush=True)
        t0 = time.time()
        with open(ND_DET, "a", encoding="utf-8") as fd, \
             open(ND_CA, "a", encoding="utf-8") as fc, \
             open(DONE, "a", encoding="utf-8") as dn:
            for i, uid in enumerate(todo, 1):
                try:
                    s1, b1 = get(f"{BASE}/UpgradeDetails?upgradeId={urllib.parse.quote(uid)}")
                    det = parse_details(uid, b1)
                    s2, b2 = get(f"{BASE}/UpgradeCostAllocations?upgradeId={urllib.parse.quote(uid)}")
                    cas = parse_costalloc(uid, b2)
                except Exception as e:  # noqa: BLE001
                    dn.write(f"{uid}\tERROR\t{str(e)[:120]}\n")
                    dn.flush()
                    print(f"  !! {uid}: {str(e)[:100]}", flush=True)
                    continue
                fd.write(json.dumps(det, ensure_ascii=False) + "\n")
                for r in cas:
                    fc.write(json.dumps(r, ensure_ascii=False) + "\n")
                dn.write(f"{uid}\tOK\t{len(cas)}\n")
                if i % 25 == 0:
                    fd.flush(); fc.flush(); dn.flush()
                    el = time.time() - t0
                    print(f"  [{i:,}/{len(todo):,}] {el/60:.1f}m elapsed, "
                          f"ETA {(len(todo)-i)*el/i/60:.1f}m, last={uid}", flush=True)
        print("crawl complete", flush=True)

    if a.load:
        sys.path.insert(0, HERE)
        from register_helper import register
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        n_ids = len(load_done())
        for nd, dest, srcurl in (
                (ND_DET, "in_pjm_rtep_upgrade_details", f"{BASE}/UpgradeDetails?upgradeId={{id}}"),
                (ND_CA, "in_pjm_rtep_cost_allocations",
                 f"{BASE}/UpgradeCostAllocations?upgradeId={{id}}")):
            rows = []
            with open(nd, encoding="utf-8") as f:
                for line in f:
                    r = json.loads(line)
                    r["_pulled_at"] = stamp
                    r["_source_url"] = srcurl
                    r["_scope"] = ("FULL-UNIVERSE" if False else
                                   "INDIANA SLICE: ids where in_pjm_rtep_upgrades.state "
                                   "token-matches IN")
                    rows.append(r)
            full = f"energy-platfrom.indiana_app.{dest}"
            from google.cloud import bigquery as bq2
            c.load_table_from_json(rows, full, job_config=bq2.LoadJobConfig(
                write_disposition="WRITE_TRUNCATE", autodetect=True)).result()
            n = list(c.query(f"SELECT COUNT(*) n FROM `{full}`").result())[0].n
            print(f"loaded {n:,} rows -> {full}")
            if n != len(rows):
                raise RuntimeError(f"ROW CONSERVATION FAILED {len(rows)} -> {n}")
            if dest == "in_pjm_rtep_upgrade_details":
                register(dest,
                         "PJM RTEP upgrade detail fragments (public GET, no login) " + srcurl,
                         "one GET per upgrade id over the Indiana-naming ids from "
                         "in_pjm_rtep_upgrades; HTML fragment parsed verbatim (criteria "
                         "violation, description, type, driver, sub-region, location, task, "
                         "equipment, related-materials links). RE-SCRAPE (this slice): python "
                         "pull_pjm_upgrade_details.py --crawl --load ; FULL UNIVERSE: add --all "
                         "(~9.4h at 1.1s/request, resumable)",
                         int(n), 0.0,
                         f"One row per upgrade id; {n_ids} ids crawled this run (932 Indiana-"
                         f"naming of 15,443 total - INDIANA SLICE, not the universe). No dates "
                         f"served in fragments (dates live in in_pjm_rtep_upgrades columns); "
                         f"related_materials carries TEAC/proposal-window links incl. 'N/A' "
                         f"hrefs exactly as published. PLOTTABILITY: JOINABLE_IDENTITY "
                         f"(upgrade_id -> in_pjm_rtep_upgrades; named locations; no coords).")
            else:
                register(dest,
                         "PJM RTEP per-upgrade cost-allocation splits (public GET, no login) "
                         + srcurl,
                         "same crawl as in_pjm_rtep_upgrade_details; sections 'Non-Load Ratio "
                         "Share'/'Load Ratio Share' parsed to one row per (upgrade_id, "
                         "share_type, zone, percent)",
                         int(n), 0.0,
                         f"Cost-split percentages by transmission zone for the Indiana-naming "
                         f"RTEP upgrades ({n_ids} ids crawled; INDIANA SLICE of 15,443). "
                         f"percent is the published allocation %, not dollars; dollars = "
                         f"percent x cost columns in in_pjm_rtep_upgrades (units $M per PJM "
                         f"definitions sheet). PLOTTABILITY: JOINABLE_IDENTITY via upgrade_id "
                         f"and zone code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
