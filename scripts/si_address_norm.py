"""THE ONE ADDRESS NORMALISER. Every SI placement builder imports it; nobody re-types it.

⛔ WHY THIS MODULE EXISTS. `build_warn_placement.py` and `build_si_cmbs_signals.py` each carried
their own copy of SUFFIXES/DIRECTIONALS/naddr/ncity, on the reasoning that either should be
re-runnable alone. `audit_si_upstream_width.py` then had to assert the two copies were character-
identical — a *guard on a duplicate*, which is the §2.15c defect the project has hit repeatedly:
**two copies of one thing WILL drift, and the loser is invisible.** A third caller (G156's NFIRS
and SBA placement, 2026-08-22b) would have made it three copies and three ways to drift.

⭐ THE FIX IS NOT A BETTER GUARD, IT IS ONE COPY. Importing costs nothing — these builders already
share a Python process and a repo — and it makes the audit's job "is there exactly one definition"
rather than "do N copies still match".

⚠ IF YOU CHANGE A SUFFIX OR A DIRECTIONAL, YOU CHANGE EVERY PLACEMENT IN THE ESTATE. WARN, CMBS,
NFIRS and SBA all place through this. Re-run all four builders and re-measure the placement rates
before committing, because a normaliser change moves counts silently and in both directions.

RE-SCRAPE COMMAND: n/a - library module, imported by the placement builders.
"""

# ⚠ ORDER MATTERS. The long form is replaced by the short one, so "NORTHEAST" must be matched
# before "NORTH" would eat its first five characters. Python's list order is the match order, and
# the longer directionals therefore sit AFTER the short ones only because each pattern is
# word-anchored (\b...\b) - "NORTHEAST" never matches the \bNORTH\b pattern. Keep the anchors.
SUFFIXES = [("STREET", "ST"), ("AVENUE", "AVE"), ("ROAD", "RD"), ("DRIVE", "DR"),
            ("BOULEVARD", "BLVD"), ("PARKWAY", "PKWY"), ("LANE", "LN"), ("COURT", "CT"),
            ("PLACE", "PL"), ("CIRCLE", "CIR"), ("HIGHWAY", "HWY"), ("TERRACE", "TER"),
            ("TRAIL", "TRL"), ("SUITE", ""), ("STE", ""), ("UNIT", ""), ("BUILDING", ""),
            ("BLDG", "")]
DIRECTIONALS = [("NORTH", "N"), ("SOUTH", "S"), ("EAST", "E"), ("WEST", "W"),
                ("NORTHEAST", "NE"), ("NORTHWEST", "NW"), ("SOUTHEAST", "SE"),
                ("SOUTHWEST", "SW")]


def naddr(col, drop_dir=False):
    """A BigQuery expression normalising a street address for exact comparison.

    `drop_dir=True` additionally strips the directional entirely - the second, looser pass, for
    publishers that disagree about whether a road is "W 16TH ST" or "16TH ST".
    """
    e = f"UPPER(TRIM({col}))"
    e = f"REGEXP_REPLACE({e}, r'[^A-Z0-9 ]', ' ')"
    for long, short in SUFFIXES:
        e = f"REGEXP_REPLACE({e}, r'\\b{long}\\b', '{short}')"
    for long, short in DIRECTIONALS:
        e = f"REGEXP_REPLACE({e}, r'\\b{long}\\b', '{short}')"
    if drop_dir:
        e = f"REGEXP_REPLACE({e}, r'\\b(N|S|E|W|NE|NW|SE|SW)\\b', ' ')"
    return f"TRIM(REGEXP_REPLACE({e}, r' +', ' '))"


def ncity(col):
    """City normalised to bare alphanumerics - 'St. John' and 'ST JOHN' must not differ."""
    return (f"TRIM(REGEXP_REPLACE(REGEXP_REPLACE(UPPER(TRIM({col})), r'[^A-Z0-9]', ''), "
            r"r' +', ' '))")


# ⛔ SELF-TEST AT IMPORT. A normaliser that silently stops normalising places nothing and fails
# nowhere - the join just returns fewer rows, which reads as "the data is sparse". These assertions
# are on the EXPRESSION TEXT, not on BigQuery, so they cost nothing and run every import.
_probe = naddr("x")
assert "STREET" in _probe and "'ST'" in _probe, "SUFFIXES did not reach the expression"
assert "NORTHWEST" in _probe, "DIRECTIONALS did not reach the expression"
assert naddr("x", drop_dir=True) != _probe, "drop_dir did not change the expression"
del _probe
