"""FRESHNESS CHECK for the MISO interconnection queue. Writes NO table, by design.

⛔ THIS SCRIPT EXISTS BECAUSE I BUILT A DUPLICATE AND HAD TO UNDO IT.

While hunting DPP-2025 I found MISO's own public JSON queue endpoint, wrote a loader, and landed
`in_miso_giqueue_projects` (468 Indiana rows) — before checking whether we already held it.
**We did.** `in_queue_miso` is the same endpoint's data, with the SAME 27 DPP-2025 rows and THREE
MORE columns (`withdrawndate`, `neginservice`, `don`). That is G25 — "a plan built on what you
remember instead of what you hold" — and the duplicate table was dropped.

Two copies of one thing WILL drift, and the loser is invisible. So this script keeps the useful part
of that work (a known-good public endpoint) and throws away the harmful part (a second copy):
it COMPARES the live publisher feed against our clip and reports drift. It writes nothing, so it
needs no `_registry` row.

THE ENDPOINT, recorded so nobody has to rediscover it:
    GET https://www.misoenergy.org/api/giqueue/getprojects
    HTTP 200, ~2.24 MB, unauthenticated, no params, no cookies. JSON array, 23 fields per project.
    ⚠ `?cycle=` / `?studyCycle=` are IGNORED — the identical full array returns regardless, so any
      filtering MUST be client-side.
    ⚠ There is no DPP-2024. MISO's cycles run 2022, 2023, 2025, 2026. A gap is not a missing scrape.
    ⚠ No lat/lon anywhere in the payload.

⛔ AND IT IS NOT BUS HEADROOM. 23 queue fields, none of them FCITC, constraint, contingency, DFAX,
rating or loading. The DPP-2025 transfer study remains 403 ProtectedData on CartoVista — see
`docs/MISO_DPP2025_ROUTE.md`.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import json
import urllib.request
from google.cloud import bigquery

URL = "https://www.misoenergy.org/api/giqueue/getprojects"
DS = "energy-platfrom.indiana_app"
UA = {"User-Agent": "Mozilla/5.0 (compatible; DecennialResearch/1.0)"}
client = bigquery.Client(project="energy-platfrom")

with urllib.request.urlopen(urllib.request.Request(URL, headers=dict(UA)), timeout=120) as r:
    live = json.loads(r.read())
IN = [x for x in live if (x.get("state") or "").strip().upper() in ("IN", "INDIANA")]
live_2025 = sum(1 for x in IN if x.get("studyCycle") == "DPP-2025")

held = list(client.query(f"""
SELECT COUNT(*) n, COUNTIF(studycycle='DPP-2025') c2025 FROM `{DS}.in_queue_miso`"""))[0]

print(f"live publisher feed : {len(IN):>4} Indiana rows, {live_2025:>3} DPP-2025")
print(f"our clip in_queue_miso: {held.n:>4} Indiana rows, {held.c2025:>3} DPP-2025")
drift = len(IN) - held.n
print()
if drift > 0:
    print(f"DRIFT: the publisher has {drift} MORE Indiana rows than our clip.")
    print("  -> ask the platform session to refresh energy.queue_miso, then re-clip.")
    print("  -> do NOT write a second table here; that is what created this script.")
elif drift < 0:
    print(f"our clip has {-drift} MORE rows than the live feed - projects can leave the feed; not an error")
else:
    print("IN SYNC - no action needed")
