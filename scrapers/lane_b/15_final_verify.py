"""Final verification: registry rows this run + table counts."""
from bq_util import query

rows, _ = query("""SELECT table_name, n_rows, FORMAT_TIMESTAMP('%m-%d %H:%M', built_at) t, SUBSTR(method,0,55) m
FROM `energy-platfrom.indiana_app._registry` WHERE built_at >= '2026-08-14' ORDER BY built_at""")
print("registry rows this run:")
for r in rows:
    print("  ", dict(r))

rows, _ = query("""
SELECT 'in_iurc_dockets' t, COUNT(*) n FROM `energy-platfrom.indiana_app.in_iurc_dockets`
UNION ALL SELECT 'in_grid_plans', COUNT(*) FROM `energy-platfrom.indiana_app.in_grid_plans`
UNION ALL SELECT 'in_ordinances_dc', COUNT(*) FROM `energy-platfrom.indiana_app.in_ordinances_dc`
UNION ALL SELECT 'in_news_dc', COUNT(*) FROM `energy-platfrom.indiana_app.in_news_dc`
UNION ALL SELECT 'in_dc_actions', COUNT(*) FROM `energy-platfrom.indiana_app.in_dc_actions`
ORDER BY t""")
print("final table counts:")
for r in rows:
    print("  ", dict(r))
