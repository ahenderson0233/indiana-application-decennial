"""Registry correction rows: news provider outcome; dcwatch quarterly wall on actions."""
from bq_util import register

register("in_news_dc",
         source="CORRECTION note (no data change)",
         method="provider outcome record",
         n_rows=0, gb_scanned=0.0,
         notes="Of the two permitted providers, Bing News RSS produced all 283 rows (114 queries OK). "
               "GDELT DOC API returned HTTP 429 on every call despite 5.5s spacing (server text demands 5s) "
               "- 0 rows this run; treat GDELT as rate-limited-unavailable from this network, retry later if needed.")

register("in_dc_actions",
         source="CORRECTION note (no data change)",
         method="source wall record",
         n_rows=0, gb_scanned=0.0,
         notes="datacenterwatch.org quarterly pages (/q22025, /q3-q4-2025, /q1-2026) render content client-side "
               "from /api/* which robots.txt DISALLOWS -> quarterly content BLOCKED for compliant crawling "
               "(0 'Indiana' strings in served HTML). Original /report page is server-rendered: parsed; its 2nd IN entry "
               "(Burns Harbor) split-format missed by parser but already held in energy.dc_opposition_tracker.")
print("DONE")
