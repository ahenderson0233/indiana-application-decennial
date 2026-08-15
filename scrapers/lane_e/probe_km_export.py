"""Replicate the KM DART page's own EXCEL download button for NGPL OA point capacity."""
import time
import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "DecennialGroup-research/1.0 (ahenderson@decennialgroup.com)"}
OUT = r"C:\Users\ahend\AppData\Local\Temp\claude\C--Users-ahend-Downloads-Decennial-Summer-Work-Remaking-Orennia-REBUILD-PLANNING\e2c5e15c-d0e5-487b-889b-f478a7c7d3d4\scratchpad\probes"

s = requests.Session()
s.headers.update(UA)
url = "https://pipeline2.kindermorgan.com/Capacity/OpAvailPoint.aspx?code=NGPL"
r1 = s.get(url, timeout=45)
print("GET", r1.status_code, len(r1.content))
soup = BeautifulSoup(r1.text, "html.parser")
form = soup.find("form")
data = {}
for inp in form.find_all("input"):
    n = inp.get("name")
    if not n:
        continue
    t = (inp.get("type") or "").lower()
    if t in ("submit", "image", "button"):
        continue  # only include the button we click
    data[n] = inp.get("value") or ""
for sel in form.find_all("select"):
    n = sel.get("name")
    if not n:
        continue
    opt = sel.find("option", selected=True) or sel.find("option")
    data[n] = opt.get("value") if opt is not None else ""
# set download format + click the image button
data["ctl00$WebSplitter1$tmpl1$ContentPlaceHolder1$HeaderBTN1$DownloadDDL"] = "EXCEL"
data["ctl00$WebSplitter1$tmpl1$ContentPlaceHolder1$HeaderBTN1$btnDownload.x"] = "5"
data["ctl00$WebSplitter1$tmpl1$ContentPlaceHolder1$HeaderBTN1$btnDownload.y"] = "5"
data["ctl00$hdnIsDownload"] = "true"
time.sleep(1.1)
r2 = s.post(url, data=data, timeout=90)
print("POST", r2.status_code, len(r2.content), r2.headers.get("Content-Type"), r2.headers.get("Content-Disposition"))
open(OUT + r"\km_ngpl_oa.bin", "wb").write(r2.content)
