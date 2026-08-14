"""Read Municode's public app bundle to learn the search API params; retry census crosswalk."""
import re, json
from bq_util import polite_get, allowed, save_scratch

r = polite_get("https://library.municode.com/in/avon")
print("app shell ->", r.status_code, len(r.text))
save_scratch("municode_shell.html", r.text)
srcs = re.findall(r'src="([^"]+\.js[^"]*)"', r.text)
print("script tags:", srcs[:10])

base = "https://library.municode.com"
hits = {}
for s in srcs:
    u = s if s.startswith("http") else base + (s if s.startswith("/") else "/" + s)
    try:
        rb = polite_get(u)
        if rb.status_code != 200:
            print(f"{u} -> {rb.status_code}")
            continue
        txt = rb.text
        print(f"{u} -> 200, {len(txt)}B")
        for m in re.finditer(r'[\'"]([A-Za-z0-9/{}._-]*[Ss]earch[A-Za-z0-9/{}._-]*)[\'"]', txt):
            hits[m.group(1)] = hits.get(m.group(1), 0) + 1
        # capture parameter-ish fragments around 'search'
        frags = re.findall(r'.{80}api/search.{200}', txt) + re.findall(r'.{80}SearchContent.{200}', txt)
        if frags:
            save_scratch("municode_search_frags.txt", "\n\n----\n\n".join(frags))
            print("frag sample:", frags[0][:250])
    except Exception as e:
        print(f"{u} FAILED: {e}")
print("\nsearch-ish strings (top):")
for k, v in sorted(hits.items(), key=lambda kv: -kv[1])[:40]:
    print(f"  {v:3d}  {k}")

# census national fallback
for u in [
    "https://www2.census.gov/geo/docs/reference/codes2020/national_place_by_county2020.txt",
    "https://www2.census.gov/geo/docs/reference/codes/files/st18_in_places.txt",
]:
    ok, _ = allowed(u)
    if not ok:
        print("census robots disallow:", u); continue
    r = polite_get(u)
    print(f"{u} -> {r.status_code}, {len(r.text)}B")
    if r.status_code == 200:
        name = u.split("/")[-1]
        save_scratch(name, r.text)
        print(r.text[:200])
        break
