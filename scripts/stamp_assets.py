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

import hashlib, os, re, glob, json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = ["app.js", "common.js", "style.css"]


def stamp_payloads():
    """G101 - give every gzipped payload a version token, for the SAME reason the scripts have one.

    `fetchGz` asked for `data/*.gz` with no version, so a rebuilt payload kept serving from cache
    and the page rendered stale figures while its provenance line claimed they were fresh. That is
    worse than an error, because it looks like the BUILD failed.

    ⚠ The token is mtime+size, deliberately NOT a content hash. `data/` is ~247 MB across 122
    files, most of it the 92 on-demand county files, and re-reading all of it on every stamp run
    buys only one thing: not re-downloading a payload that was rebuilt to identical bytes. That is
    rare and harmless. A stale payload is neither.
    """
    man, root = {}, os.path.join(REPO, "data")
    for path in glob.glob(os.path.join(root, "**", "*.gz"), recursive=True):
        st = os.stat(path)
        rel = os.path.relpath(path, REPO).replace(os.sep, "/")
        man[rel] = f"{int(st.st_mtime):x}-{st.st_size:x}"
    out = os.path.join(root, "payload_manifest.json")
    prev = None
    if os.path.exists(out):
        try:
            prev = json.load(open(out, encoding="utf-8"))
        except Exception:
            prev = None
    # Written every run, but only REPORTED as changed when it actually differs -- so the line in
    # the console means something.
    with open(out, "w", encoding="utf-8") as f:
        json.dump(man, f, separators=(",", ":"), sort_keys=True)
    n_new = 0 if prev is None else sum(1 for k, v in man.items() if prev.get(k) != v)
    if prev is None:
        print(f"  payload manifest -> {len(man)} payloads (created)")
    else:
        print(f"  payload manifest -> {len(man)} payloads, {n_new} changed since last stamp")
    return man


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

stamp_payloads()

print(f"ASSET STAMP COMPLETE - {changed} page(s) updated")
