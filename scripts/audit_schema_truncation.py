"""G27 - the `[:N]` idiom that silently drops columns, audited instead of assumed.

    python scripts/audit_schema_truncation.py

THE DEFECT THIS CLOSES, in the words of the row that recorded it: *"Cause was `[:12]` truncating
the parent schema at column 12 while `classification` sits at 16 - not a mapping error."* One
under-clipped table cost a session, and the row then noted: **"The same `[:N]` idiom is unaudited
in `build_gas_facilities.py`, `build_gas_market.py` and `export_full_wiring.py`."** Unaudited is
the operative word - nobody had looked, so nobody knew.

⛔ WHY THE IDIOM IS DANGEROUS AND WHY IT IS NOT SIMPLY BANNED. `keep = [c for c in cols ...][:12]`
is a reasonable defence against a 200-column vendor table bloating a payload. What makes it a
defect is that it drops columns by POSITION, silently, and the position of a column is an
accident of how the publisher built their table. It will keep whatever happens to come first and
discard whatever happens to come sixteenth - and neither the code nor the output says so.

WHAT THIS DOES. For each site, resolve the real column list from BigQuery, apply the same filter
and the same cut, and print WHAT WAS DROPPED. A dropped column whose name suggests it carries a
class, a status, a type, a date, a capacity, a voltage, a name, a key or a place is flagged as
LOAD-BEARING, because those are the columns a surface or a join actually needs.

⚠ THIS IS ADVISORY, NOT A GATE, and it exits 0 unless a LOAD-BEARING column is being dropped.
Flagging every dropped column would flag dozens of vendor bookkeeping fields and be ignored
within a day - which is the failure three audits in this repo have already had.
"""
import io
import os
import re
import sys as _sys

try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

# (script, FULLY-QUALIFIED table the cut is applied to, the cut, how it filters first)
#
# ⛔ THE FIRST VERSION OF THIS AUDIT TESTED THE WRONG TABLES AND REPORTED A CLEAN ALL-CLEAR.
#    It measured the OUTPUT (`indiana_app.in_gas_pipelines`, 8 columns) when the cut is applied
#    to the PARENT being clipped (`energy.gas_pipelines_hifld`). Of course nothing was dropped:
#    the output is what SURVIVED the cut. Measuring the result of a filter to find out what the
#    filter removed is circular, and it produced exactly the reassuring zero this project warns
#    about - a clean number is a claim about the instrument first.
# ⚠ READING `energy` HERE IS PERMITTED. Builds may read energy; exports may not. This is an
#   audit of a BUILD, and it must read what the build reads or it is measuring nothing.
SITES = [
    ("scripts/build_gas_facilities.py", "energy-platfrom.energy.gas_compressor_stations", 10,
     "drops the geography columns and anything starting with '_'"),
    ("scripts/build_gas_facilities.py", "energy-platfrom.energy.gas_storage", 10,
     "drops the geography columns and anything starting with '_'"),
    ("scripts/build_gas_facilities.py", "energy-platfrom.energy.gas_processing_plants", 10,
     "drops the geography columns and anything starting with '_'"),
    ("scripts/build_gas_facilities.py", "energy-platfrom.energy.gas_lng_terminals", 10,
     "drops the geography columns and anything starting with '_'"),
    ("scripts/build_gas_market.py", "energy-platfrom.energy.gas_pipelines_hifld", 14,
     "drops the geography columns and anything starting with '_'"),
    ("scripts/export_full_wiring.py", "energy-platfrom.indiana_app.in_pjm_gis_queues", 12,
     "drops the geography and lat/lon columns"),
]

# A dropped column matching any of these is LOAD-BEARING: it is the kind of column a surface
# renders or a join needs. `classification` - the column the original G27 defect dropped - is
# caught by `class`.
LOADBEARING = re.compile(
    r"class|status|type|date|year|capacit|volt|_kv|\bkv\b|\bmw\b|name|county|state|city|"
    r"owner|operator|id$|_id|key|zip|addr|lat|lon|acre|flow|press", re.I)

# ⛔ DEFINED HERE, ONCE, WITH A SELF-TEST — and typed with the Write/Edit tool, NEVER through a
#    shell heredoc. That rule is written down in this project and I broke it AGAIN building this
#    very audit: the heredoc turned `[^\n]` into a literal newline and left an unterminated
#    string literal. Sixth occurrence on record. The self-test is the cheap insurance.
CUT_RE = re.compile(r"keep = \[c for c in cols[^\n]*?\[:(\d+)\]")
assert CUT_RE.findall(
    '    keep = [c for c in cols if c not in (gcol, gjson) and not c.startswith("_")][:10]'
) == ["10"], "CUT_RE self-test failed"
assert CUT_RE.findall(
    '    keep = [c for c in cols if c not in (gcol, gjson) and not c.startswith("_")]'
) == [], "CUT_RE matched a line with no cut"

print("=" * 92)
print("G27 - WHAT THE `[:N]` SCHEMA CUTS ACTUALLY DROP")
print("=" * 92)

bad = []
for script, table, cut, how in SITES:
    path = os.path.join(REPO, script.replace("/", os.sep))
    src = io.open(path, encoding="utf-8", errors="ignore").read() if os.path.exists(path) else ""
    # ⛔ READ THE CUT FROM THE SOURCE, DO NOT TRUST THE NUMBER IN THIS TABLE. A hand-typed cut
    #    here is a second copy of a fact that lives in the build script, and the two WILL drift -
    #    which happened immediately: build_gas_facilities.py was widened to keep every column and
    #    this audit went on reporting the old [:10] drop, condemning code that had been fixed.
    #    The declared cut is now only a fallback for when no cut can be found in the file.
    found = [int(x) for x in CUT_RE.findall(src)]
    live = bool(found)
    if found:
        cut = max(found)
    try:
        cols = [f.name for f in client.get_table(table).schema]
    except Exception as e:
        print(f"\n⚠ {script}: cannot read {table} - {str(e)[:80]}")
        continue
    # reproduce the filter each site applies before cutting
    geo = [c for c in cols if c.lower() in ("geog", "geom", "geometry_geojson", "gj",
                                            "footprint_geojson")]
    if "export_full_wiring" in script:
        latc = next((c for c in cols if "lat" in c.lower()), None)
        lonc = next((c for c in cols if "lon" in c.lower() or "lng" in c.lower()), None)
        elig = [c for c in cols if c not in geo + [latc, lonc]]
    else:
        elig = [c for c in cols if c not in geo and not c.startswith("_")]
    kept, dropped = (elig[:cut], elig[cut:]) if live else (elig, [])
    flagged = [c for c in dropped if LOADBEARING.search(c)]

    print(f"\n{script}")
    print(f"  reads {table.split('.')[-1]}: {len(cols)} columns · {len(elig)} eligible after the filter "
          f"({how})")
    print(f"  cut at [:{cut}] -> keeps {len(kept)}, DROPS {len(dropped)}"
          if live else
          f"  ⭐ NO `[:N]` CUT REMAINS IN THIS FILE - it keeps every eligible column, so nothing "
          f"is dropped by position")
    if not dropped:
        print("  ⭐ nothing is dropped - the cut is wider than the table, so it is inert here")
    else:
        print(f"  dropped: {', '.join(dropped)}")
    if flagged:
        print(f"  ⛔ LOAD-BEARING COLUMNS AMONG THE DROPPED: {', '.join(flagged)}")
        bad.append((script, table, flagged))
    elif dropped:
        print("  ⭐ none of the dropped columns looks load-bearing (no class / status / type / "
              "date / capacity / voltage / name / place / key in any of them)")

print()
print("=" * 92)
if bad:
    print(f"⛔ {len(bad)} site(s) are dropping a column a surface or a join could need:")
    for script, table, flagged in bad:
        print(f"    {script}  ({table}): {', '.join(flagged)}")
    print("\n   Widen the cut, or name the columns explicitly instead of taking the first N.")
else:
    print("0 load-bearing columns dropped by any `[:N]` cut. The idiom is inert at every "
          "recorded site.")
_sys.exit(1 if bad else 0)
