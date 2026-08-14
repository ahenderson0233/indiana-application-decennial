"""Correction: remove dc_party relevance where it came from substring 'vantage' inside 'Advantage' etc."""
from bq_util import query

sql = r"""
UPDATE `energy-platfrom.indiana_app.in_iurc_dockets`
SET relevance = NULLIF(ARRAY_TO_STRING(ARRAY(
      SELECT x FROM UNNEST(SPLIT(relevance,';')) x WHERE x != 'dc_party'), ';'), '')
WHERE relevance LIKE '%dc_party%'
  AND NOT REGEXP_CONTAINS(LOWER(parties),
      r'data cent|amazon|google|microsoft|meta platforms|\baws\b|digital crossroads|\bqts\b|\bvantage\b|surge dev|stargate')
"""
rows, gb = query(sql)
print("dc_party relabel done")
rows, _ = query("""SELECT relevance, COUNT(*) n FROM `energy-platfrom.indiana_app.in_iurc_dockets`
                   WHERE relevance LIKE '%dc_party%' GROUP BY 1""")
for r in rows:
    print(" ", dict(r))
