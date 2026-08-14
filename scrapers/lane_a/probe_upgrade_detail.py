import sys, time, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read().decode("utf-8", "replace")

for uid in ("b0117", "b3800.5"):
    for ep in ("UpgradeDetails", "UpgradeCostAllocations"):
        s, body = get(f"https://www.pjm.com/m/ProjectConst/{ep}?upgradeId={uid}")
        print(f"=== {ep}?upgradeId={uid} -> {s}, {len(body):,}b")
        print(body[:2200])
        print("...")
        time.sleep(1.2)
