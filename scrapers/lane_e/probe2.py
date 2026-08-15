from probe import get

# Vector download page (DNN) - hoping for direct CSV links
get("vector_dl_oa.html", "https://www.vector-pipeline.com/Informational-Postings/Downloads/Operationally-Available-Capacity")
# Energy Transfer ipost root -> asset list
get("et_ipost_root.html", "https://pipelines.energytransfer.com/ipost")
get("et_tgc_oa_byloc.html", "https://pipelines.energytransfer.com/ipost/TGC/capacity/operationally-available-by-location")
# TC eConnects infopost shell
get("tceconnects_infopost.html", "https://www.tceconnects.com/infopost/")
# Kinder Morgan NGPL portal shell
get("km_ngpl_home.html", "https://pipeportal.kindermorgan.com/PortalUI/DefaultKM.aspx?TSP=NGPL")
# Trellis MGT infopost home fragment
get("trellis_mgt_infoposthome.html", "https://dtmidstream.trellisenergy.com/ptms/public/infopost/getInfoPostingHome.do?globalTSP=10")
# GasQuest app page
get("gasquest_ip.html", "https://www.gasquest.com/informational-posting")
