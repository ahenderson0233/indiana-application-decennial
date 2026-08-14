"""Find the current IURC IRP page from the IURC home nav."""
import re
from bq_util import polite_get, save_scratch

r = polite_get("https://www.in.gov/iurc/")
print("iurc home ->", r.status_code, len(r.text))
save_scratch("ingov_iurc_home.html", r.text)
links = sorted(set(re.findall(r'href="(/iurc/[^"#?]+|https://www\.in\.gov/iurc/[^"#?]+)"', r.text)))
for l in links:
    print("  ", l)
irp = [l for l in links if re.search(r"irp|resource", l, re.I)]
print("\nIRP-ish:", irp)
