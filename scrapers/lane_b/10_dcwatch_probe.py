"""Fetch Data Center Watch /report page (robots-allowed), inspect structure for Indiana rows."""
import re
from bq_util import polite_get, save_scratch

r = polite_get("https://www.datacenterwatch.org/report")
print("report ->", r.status_code, len(r.text))
save_scratch("dcwatch_report.html", r.text)
txt = re.sub(r"<script[^>]*>.*?</script>", " ", r.text, flags=re.S)
txt = re.sub(r"<style[^>]*>.*?</style>", " ", txt, flags=re.S)
plain = re.sub(r"<[^>]+>", "\n", txt)
plain = re.sub(r"\n{2,}", "\n", plain)
save_scratch("dcwatch_report.txt", plain)
ii = [i for i, line in enumerate(plain.splitlines()) if re.search(r"Indiana", line)]
lines = plain.splitlines()
print("lines mentioning Indiana:", len(ii))
for i in ii[:25]:
    print("----", "\n".join(l.strip() for l in lines[max(0, i-2):i+6] if l.strip())[:500])
