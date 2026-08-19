"""G82 - make D11 and D27 reach a PARCEL, using the address we already hold.

    python scripts/build_si_address_to_parcel.py

Operator, 2026-08-19: *"We should be able to reach a parcel with D11, D27, and D19, and this should
be further explored (e.g., if we have an address, we can match it to the parcel through geocoding
or a join key)."*

⭐ THE OPERATOR IS RIGHT THAT THE ADDRESS IS ALREADY THERE. `in_si_d11_admitted` (983 rows) and
`in_si_d27_admitted` (156) BOTH carry `address_line`, `city`, `addr_state` and `zip`, populated on
every single row. They were filed owner-grain not for lack of an address but because nobody joined
on one.

⛔ AND THE CEILING IS NOT THE MATCHER, IT IS THE CORPUS. Measured: there is **no statewide parcel
address column anywhere in the estate** - not on `in_sites`, not on `in_parcel_attrs`, not on
`in_si_candidates`. The only address-to-parcel corpus we hold is **Marion County's own crosswalk**
(`in_marion_parcel_crosswalk`, 347,049 rows). So this can reach parcels in Marion and nowhere else,
which caps the addressable universe at **342 of 1,139 rows** (311 D11 + 31 D27 with an
Indianapolis address). ⭐ **That is the same DLGF Gateway blocker as G104/G70/G71/G81** and it is
the honest answer to "why don't we have more".

⛔ NO GEOCODING. A street centreline is not a parcel, and the project bans deriving one. This
matches the address we HOLD against the address the county PUBLISHES, or it records no match.

⚠ TWO VALUE-VOCABULARY TRAPS in these tables, both live:
  * `addr_state` is **'IN' on 770 rows and 'Indiana   ' - space-padded - on 213**. A plain
    `= 'IN'` filter silently drops 22% of D11.
  * D27 carries at least one row whose `addr_state` is 'IN' while the ZIP is **06010, which is
    Bristol CONNECTICUT**. The debtor's mailing address is not always the Indiana site, so a zip
    that contradicts the state is recorded, not silently trusted.

⚠ `keying` IS RECORDED HONESTLY, because a weak match must be visible as one:
    address_exact   number + street stem + city agree
    address_nostem  number + city agree and the street matched on prefix only
  ⛔ Nothing is emitted on a city-only or name-only basis. That is how D19_warn would land on the
  wrong parcel, and a wrong parcel is worse than no parcel.

WRITES `indiana_app.in_si_address_parcel`. Reads indiana_app only.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import re
import collections
from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
OUT = f"{DS}.in_si_address_parcel"
client = bigquery.Client(project="energy-platfrom")

DIRS = r"(?:N|S|E|W|NE|NW|SE|SW|NORTH|SOUTH|EAST|WEST)"
SUFFIX = (r"(?:STREET|ST|AVENUE|AVE|ROAD|RD|DRIVE|DR|LANE|LN|BOULEVARD|BLVD|COURT|CT|PLACE|PL|"
          r"CIRCLE|CIR|PARKWAY|PKWY|TERRACE|TER|WAY|TRAIL|TRL|HIGHWAY|HWY|PIKE|SQUARE|SQ)")
UNIT = r"(?:SUITE|STE|UNIT|APT|APARTMENT|FLOOR|FL|BLDG|BUILDING|ROOM|RM|#)"


def norm_addr(raw):
    """'500 S. POLK STREET SUITE 15' -> (500, 'POLK'). Returns (None, None) when unusable."""
    s = str(raw or "").upper()
    s = re.sub(r"[.,]", " ", s)
    s = re.sub(rf"\b{UNIT}\b.*$", " ", s)          # drop the unit and everything after it
    s = re.sub(r"\s+", " ", s).strip()
    m = re.match(r"^(\d+)\s+(.*)$", s)
    if not m:
        return None, None
    num, rest = m.group(1), m.group(2)
    rest = re.sub(rf"^{DIRS}\s+", " ", rest)       # leading directional
    rest = re.sub(rf"\s+{DIRS}$", " ", rest)       # trailing directional
    rest = re.sub(rf"\s+{SUFFIX}$", " ", rest)     # street type
    rest = re.sub(r"[^A-Z0-9 ]", " ", rest)
    rest = re.sub(r"\s+", " ", rest).strip()
    return (num, rest) if rest else (num, None)


def _selftest():
    assert norm_addr("500 S. POLK STREET SUITE 15") == ("500", "POLK"), norm_addr("500 S. POLK STREET SUITE 15")
    assert norm_addr("77 N. SEWELL RD.") == ("77", "SEWELL")
    assert norm_addr("16 EAST 9TH STREET") == ("16", "9TH")
    assert norm_addr("12550 RICHLANE DR") == ("12550", "RICHLANE")
    assert norm_addr("PO BOX 1234") == (None, None)     # ⛔ a PO box is not a site
    assert norm_addr("") == (None, None)


_selftest()

# ---- the county's own address -> parcel corpus (Marion only) ----
cross = collections.defaultdict(set)
n_cross = 0
for r in client.query(f"""
    SELECT STNUMBER, FULL_STNAME, STREET_NAME, CITY, ZIPCODE, PARCEL_I, STATEPARCELNUMBER
    FROM `{DS}.in_marion_parcel_crosswalk`
    WHERE PARCEL_I IS NOT NULL AND STNUMBER IS NOT NULL"""):
    for street in (r.FULL_STNAME, r.STREET_NAME):
        num, stem = norm_addr(f"{r.STNUMBER} {street or ''}")
        if num and stem:
            cross[(num, stem, (r.CITY or "").strip().upper())].add(
                (r.PARCEL_I, r.STATEPARCELNUMBER, (r.ZIPCODE or "").strip()))
    n_cross += 1
print(f"Marion crosswalk: {n_cross:,} rows -> {len(cross):,} distinct (number, street, city) keys")

out, stats = [], collections.Counter()
for tbl, sig, idcol, namecol, datecol in [
        ("in_si_d11_admitted", "D11", "entity_id", "entity_name", "observed_date"),
        ("in_si_d27_admitted", "D27", "filing_id", "debtor_name", "filing_date")]:
    for r in client.query(f"""
        SELECT {idcol} AS ident, {namecol} AS nm, address_line, city, addr_state, zip,
               CAST({datecol} AS STRING) AS evdate
        FROM `{DS}.{tbl}`"""):
        stats[f"{sig} rows"] += 1
        city = (r.city or "").strip().upper()
        # ⚠ TRIM: addr_state is 'IN' on some rows and 'Indiana   ' on others.
        st = (r.addr_state or "").strip().upper()[:2]
        if st and st != "IN":
            stats[f"{sig} out-of-state"] += 1
            continue
        num, stem = norm_addr(r.address_line)
        if not (num and stem):
            stats[f"{sig} unparseable address"] += 1
            continue
        if city not in ("INDIANAPOLIS", "INDPLS"):
            stats[f"{sig} outside the only corpus we hold (Marion)"] += 1
            continue
        hits = cross.get((num, stem, city)) or cross.get((num, stem, "INDIANAPOLIS"))
        keying = "address_exact"
        if not hits:
            # prefix fallback: same number + city, street matched on stem prefix
            cand = {k: v for k, v in cross.items()
                    if k[0] == num and k[2] == city and (k[1].startswith(stem) or stem.startswith(k[1]))}
            if len(cand) == 1:
                hits = next(iter(cand.values()))
                keying = "address_nostem"
        if not hits:
            stats[f"{sig} no parcel at that address"] += 1
            continue
        if len({h[0] for h in hits}) > 1:
            stats[f"{sig} ambiguous - NOT placed"] += 1
            continue
        h = next(iter(hits))
        zip_conflict = bool(r.zip and h[2] and str(r.zip)[:5] != h[2][:5])
        out.append({
            "signal": sig, "source_table": tbl, "entity_id": str(r.ident),
            "entity_name": r.nm, "event_date": r.evdate,
            "address_line": r.address_line, "city": r.city, "zip": r.zip,
            "parcel_id": h[0], "state_parcel_number": h[1], "parcel_zip": h[2],
            "keying": keying, "zip_conflict": zip_conflict,
            "county_fips": "18097",
        })
        stats[f"{sig} MATCHED ({keying})"] += 1

print("\nfunnel:")
for k in sorted(stats):
    print(f"   {k:52s} {stats[k]:5d}")
print(f"\n  matched rows: {len(out)}  ->  {len({o['parcel_id'] for o in out})} distinct parcels")
print(f"  zip conflicts (mailing address may not be the site): "
      f"{sum(1 for o in out if o['zip_conflict'])}")

schema = [bigquery.SchemaField(n, "BOOL" if n == "zip_conflict" else "STRING")
          for n in ("signal", "source_table", "entity_id", "entity_name", "event_date",
                    "address_line", "city", "zip", "parcel_id", "state_parcel_number",
                    "parcel_zip", "keying", "zip_conflict", "county_fips")]
client.load_table_from_json(
    out, OUT, job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE"),
).result()
print(f"\n{OUT}: {len(out)} rows written")

client.query(f"""
INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes)
VALUES (
 'in_si_address_parcel',
 'indiana_app.in_si_d11_admitted + in_si_d27_admitted x in_marion_parcel_crosswalk',
 'street address normalised (unit dropped, directional and street-type stripped) to '
 '(number, street stem, city) and matched against the county crosswalk; exact first, then a '
 'unique prefix fallback recorded as address_nostem; ambiguous addresses and PO boxes are NOT '
 'placed; NO GEOCODING - a centreline is not a parcel. '
 'RE-SCRAPE COMMAND: python scripts/build_si_address_to_parcel.py',
 {len(out)}, 0.0, CURRENT_TIMESTAMP(),
 'G82. MARION ONLY, and that is the finding: there is no statewide parcel address column in the '
 'estate, so 342 of 1,139 D11/D27 rows are even addressable and the rest wait on the DLGF Gateway '
 'pull with G104/G70/G71/G81. addr_state carries two vocabularies (IN and a space-padded '
 'Indiana). zip_conflict flags rows whose mailing ZIP disagrees with the parcel ZIP.'
)""").result()
print("  _registry row written")
print("SI ADDRESS -> PARCEL COMPLETE")
