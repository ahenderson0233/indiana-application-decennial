"""Audit the six Lane D sources: did the all-columns pull actually keep all columns?

Lane D claims `outFields=*` / all-columns on every source. Verify rather than trust: compare
each refreshed table's column count against the older held copy of the same source where one
exists, and list any column present upstream but absent from ours.

The operator's point stands behind this: an endpoint often carries more than one signal, so a
dropped column can silently be a dropped signal. READ-ONLY.
"""
# stdout must survive its own output: this console is cp1252 and characters like U+2248/U+2192/U+2717 raise
# UnicodeEncodeError from print() itself. The honesty audit once crashed on its own
# FAILURE path for exactly this reason. Degrade the glyph, never the run.
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
EN = "energy-platfrom.energy"
client = bigquery.Client(project="energy-platfrom")

# (our refreshed table, the older/parallel copy to compare against)
PAIRS = [
 ("in_si_refresh_indy_code_enforcement", f"{EN}.si_d12_indy_marion_code_enforcement"),
 ("in_si_refresh_indy_code_enforcement", f"{EN}.agis_indy_code_enforcement"),
 ("in_si_refresh_sri_taxsale_in",        f"{EN}.si_d1_sri_taxsale_listings"),
 ("in_si_refresh_ibtr_appeals",          f"{EN}.appeals_in_ibtr_determinations"),
 ("in_si_refresh_warn_notices",          f"{EN}.warn_notices"),
 ("in_si_refresh_iocs_eviction",         f"{EN}.si_d17_in_iocs_court_year"),
 ("in_si_refresh_brownfield_epa_in",     f"{EN}.brownfield_epa_repowering"),
]

def cols(full):
    """Case-INSENSITIVE. A first pass compared raw names and reported CASE_TYPE as missing while
    case_type was 'extra' — the same column counted twice, in both directions. The scary number
    was the instrument, not the data."""
    try:
        t = client.get_table(full)
        return {s.name.lower() for s in t.schema}, t.num_rows
    except Exception:
        return None, None

print("Lane D completeness audit — ours vs the older held copy\n")
for ours, theirs in PAIRS:
    a, an = cols(f"{DS}.{ours}")
    b, bn = cols(theirs)
    if a is None:
        print(f"  {ours}: OUR TABLE MISSING"); continue
    if b is None:
        print(f"  {ours:<38} {len(a):>3} cols / {an:>9,} rows   (no comparison copy: {theirs.split('.')[-1]})")
        continue
    only_theirs = sorted(b - a)
    print(f"  {ours:<38} {len(a):>3} cols / {an:>9,} rows   vs {theirs.split('.')[-1]}: "
          f"{len(b)} cols / {bn:,} rows")
    if only_theirs:
        print(f"      !! {len(only_theirs)} column(s) upstream but NOT in ours: {only_theirs[:14]}")
    else:
        print(f"      ok — nothing upstream is missing from ours "
              f"(+{len(a - b)} columns ours has that the old copy lacks)")

# a dropped column can be a dropped signal, so also report what OUR tables uniquely carry
print("\nColumns our refreshed tables add over the older copies (the 'extra signals' surface):")
for ours, theirs in PAIRS:
    a, _ = cols(f"{DS}.{ours}"); b, _ = cols(theirs)
    if a and b:
        extra = sorted(a - b)
        if extra:
            print(f"  {ours}: +{len(extra)} → {extra[:12]}")
