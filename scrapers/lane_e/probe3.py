from probe import get

# Vector via gasnom vendor (ColdFusion EBB)
get("gasnom_vector_oa.html", "https://www.gasnom.com/ip/vector/cap_operationally_available.cfm")
get("gasnom_vector_dl.html", "https://www.gasnom.com/ip/vector/transposting.cfm?id=1")
get("gasnom_robots.txt", "https://www.gasnom.com/robots.txt")

# KM NGPL point-level OA (screen + export flags)
get("km_ngpl_oa_point.html", "https://pipeline2.kindermorgan.com/Capacity/OpAvailPoint.aspx?code=NGPL")
get("km_robots2.txt", "https://pipeline2.kindermorgan.com/robots.txt")

# TC eConnects inner frame (asset menu)
get("tce_frame_a0.html", "https://www.tceconnects.com/infopost/TCeConnects.aspx?v=1.3&SID=67&info=Y&assetid=0")

# ET alternate host from search result
get("nslet_tgc_oa.html", "https://nsletconnect.energytransfer.com/ipost/TGC/capacity/operationally-available-by-location")

# Trellis: common infopost capacity endpoints (guesses based on PTMS conventions)
get("trellis_try_oa1.html", "https://dtmidstream.trellisenergy.com/ptms/public/infopost/getOperationallyAvailable.do?globalTSP=10")
get("trellis_js_common.js", "https://dtmidstream.trellisenergy.com/ptms/js/homeAndInfopostCommon.js?ver=202607302344")
