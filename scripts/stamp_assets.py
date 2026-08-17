"""Stamp app.js / common.js / style.css references with a content hash, so a deploy is never stale.

WHY THIS EXISTS. `app.js`, `common.js` and `style.css` were referenced by bare filename. Browsers
cache those aggressively and revalidate lazily, and **GitHub Pages does the same** - so after a
deploy a returning user keeps running the previous build with no error anywhere. It looks exactly
like "the fix didn't work".

Caught 2026-08-17 in the worst possible way: the Power Plan rewrite was verified as "not working"
in a browser that was executing the PREVIOUS app.js. A fetch with a cache-busting query returned
the new file and parsed cleanly, while `openDossier.constructor.name` in the page still read
`Function` instead of `AsyncFunction`. Two fresh tabs did not clear it. That is a full debugging
cycle spent on a stale asset, and it is the "does it work vs is it current" rule (BACKLOG rule 10)
wearing new clothes.

The fix is a content hash in the query string: `app.js?v=a1b2c3d4`. Same URL while the file is
unchanged (so caching still works and is still desirable), new URL the instant a byte changes.

Idempotent. Run it after editing any of the three assets, and before committing a deploy.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import hashlib, os, re, glob

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = ["app.js", "common.js", "style.css"]


def digest(path):
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:8]


stamps = {}
for a in ASSETS:
    p = os.path.join(REPO, a)
    if os.path.exists(p):
        stamps[a] = digest(p)
        print(f"  {a:12s} -> v={stamps[a]}")

changed = 0
for html in sorted(glob.glob(os.path.join(REPO, "*.html"))):
    src = open(html, encoding="utf-8").read()
    out = src
    for a, v in stamps.items():
        attr = "href" if a.endswith(".css") else "src"
        # match the asset with or without an existing ?v= stamp, and rewrite it
        out = re.sub(rf'({attr}=")({re.escape(a)})(\?v=[0-9a-f]+)?(")',
                     lambda m: f'{m.group(1)}{m.group(2)}?v={v}{m.group(4)}', out)
    if out != src:
        open(html, "w", encoding="utf-8").write(out)
        changed += 1
        print(f"  stamped {os.path.basename(html)}")

print(f"ASSET STAMP COMPLETE - {changed} page(s) updated")
