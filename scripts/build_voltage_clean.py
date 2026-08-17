"""G13 — audit and repair the voltage labels BEFORE anything is coloured or filtered by them.

Operator, 2026-08-17: *"The substations/buses/transmission lines should also be filterable by kV and
the transmission lines should depict different colors based on their voltage - some mislabeled and
should be audited/fixed."*

⛔ THE AUDIT CAME FIRST, DELIBERATELY. Colouring a map by a wrong field renders the error in high
contrast and makes it look authoritative. Two real defects were found:

**1. A NULL SENTINEL CARRIED AS A NUMERIC VOLTAGE.** 335 of 2,623 HIFLD lines have
   `kv = -999999` and `voltage_raw = '-999999'`. That is HIFLD's "not available" marker loaded as
   a number. It is the *"unpublished is NULL, never 0"* rule with a minus sign: any colour ramp,
   MIN(), or `kv < 100` test treats these as the lowest-voltage lines in the state.
   ⭐ **65 of the 335 are RECOVERABLE**: their `volt_class` says `UNDER 100` (46) or `100-161` (19)
   even though `kv` is the sentinel. The band is known; only the exact number is not. Throwing all
   335 away would discard information we hold.

**2. OSM CONTRIBUTES 1,114 LINES WITH NO `volt_class` AT ALL** — every one of them NULL — while
   carrying perfectly clean `kv` (138, 345, 161, 765). So a class-based filter or legend silently
   drops the entire OSM contribution, which is 30% of the merged layer and the half that adds
   coverage HIFLD lacks. The class is trivially derivable from kv.

RESULT: `kv_clean` (NULL where the value is a sentinel — never 0, never negative) and
`volt_class_clean` (a single normalised vocabulary across both publishers, with **`UNKNOWN` as a
first-class value** rather than a silent gap). Unknown voltage must get its own colour on the map,
never the bottom of the scale.

Also measured and recorded, though not repairable here: **1,584 of 3,010 substations (53%) have a
NULL `max_kv`.** The screener's "substation of at least N kV" filter therefore silently discards
more than half the substations — a wrong FAIL rather than a wrong pass, and the user is not told.
That belongs in the UI as a disclosed denominator.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from google.cloud import bigquery

DS = "energy-platfrom.indiana_app"
client = bigquery.Client(project="energy-platfrom")

SQL = f"""
CREATE OR REPLACE TABLE `{DS}.in_transmission_voltage` AS
WITH base AS (
  SELECT *,
         -- a sentinel is NOT a voltage. NULL it, never zero it.
         CASE WHEN kv IS NULL OR kv <= 0 THEN NULL ELSE kv END AS kv_clean
  FROM `{DS}.in_transmission_union`
)
SELECT * EXCEPT(kv_clean), kv_clean,
  CASE
    -- 1. a real number wins, whatever the publisher's class says
    WHEN kv_clean >= 735 THEN '735 and above'
    WHEN kv_clean >= 500 THEN '500-734'
    WHEN kv_clean >= 300 THEN '300-499'
    WHEN kv_clean >= 200 THEN '200-299'
    WHEN kv_clean >= 100 THEN '100-199'
    WHEN kv_clean >  0   THEN 'under 100'
    -- 2. no number, but the publisher stated a BAND - recover it (65 lines)
    WHEN UPPER(IFNULL(volt_class,'')) = 'UNDER 100'     THEN 'under 100'
    WHEN UPPER(IFNULL(volt_class,'')) = '100-161'       THEN '100-199'
    WHEN UPPER(IFNULL(volt_class,'')) = '220-287'       THEN '200-299'
    WHEN UPPER(IFNULL(volt_class,'')) = '345'           THEN '300-499'
    WHEN UPPER(IFNULL(volt_class,'')) = '735 AND ABOVE' THEN '735 and above'
    -- 3. genuinely unknown, and it says so
    ELSE 'unknown'
  END AS volt_class_clean,
  CASE WHEN kv IS NOT NULL AND kv <= 0 THEN TRUE ELSE FALSE END AS had_sentinel,
  CURRENT_TIMESTAMP() AS built_at
FROM base
"""
client.query(SQL).result()

m = list(client.query(f"""
SELECT COUNT(*) n,
       COUNTIF(had_sentinel) sentinels,
       COUNTIF(kv_clean IS NULL) kv_unknown,
       COUNTIF(volt_class_clean = 'unknown') class_unknown,
       COUNTIF(had_sentinel AND volt_class_clean != 'unknown') recovered
FROM `{DS}.in_transmission_voltage`"""))[0]
print(f"in_transmission_voltage: {m.n:,} lines")
print(f"  carried the -999999 sentinel  : {m.sentinels:,}")
print(f"  ⭐ band RECOVERED from volt_class: {m.recovered:,}  (kv still unknown, class now known)")
print(f"  kv genuinely unknown           : {m.kv_unknown:,}")
print(f"  class genuinely unknown        : {m.class_unknown:,}")
print()
for r in client.query(f"""SELECT volt_class_clean, COUNT(*) n, COUNTIF(src='osm') from_osm
  FROM `{DS}.in_transmission_voltage` GROUP BY 1 ORDER BY n DESC"""):
    print(f"   {r.volt_class_clean:16s} {r.n:>6,}   (osm contributes {r.from_osm:,})")

sub = list(client.query(f"""
SELECT COUNT(*) n, COUNTIF(max_kv IS NULL) unknown_kv
FROM `{DS}.in_substations_dedup`"""))[0]
print()
print(f"substations: {sub.unknown_kv:,} of {sub.n:,} ({100*sub.unknown_kv/sub.n:.0f}%) have NO voltage")
print("  -> a 'substation of at least N kV' filter silently discards every one of them.")
print("     Disclose that denominator in the UI; do not treat unknown as 0.")

client.query(f"DELETE FROM `{DS}._registry` WHERE table_name='in_transmission_voltage'").result()
client.query(
    f"INSERT INTO `{DS}._registry` (table_name, source, method, n_rows, gb_scanned, built_at, notes) "
    f"VALUES (@t,@s,@m,@n,0.0,CURRENT_TIMESTAMP(),@no)",
    job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("t", "STRING", "in_transmission_voltage"),
        bigquery.ScalarQueryParameter("s", "STRING", f"{DS}.in_transmission_union"),
        bigquery.ScalarQueryParameter("m", "STRING",
            "kv_clean nulls the -999999 sentinel; volt_class_clean normalises one vocabulary across "
            "HIFLD and OSM, preferring a real kv, then the publisher's stated band, then 'unknown'"),
        bigquery.ScalarQueryParameter("n", "INT64", int(m.n)),
        bigquery.ScalarQueryParameter("no", "STRING",
            f"G13 audit-before-colour. {m.sentinels} lines carried kv=-999999, HIFLD's not-available "
            f"marker loaded as a number - any colour ramp or 'kv < 100' test read them as the "
            f"lowest-voltage lines in the state. {m.recovered} of those had a usable volt_class and "
            f"were RECOVERED to a band rather than discarded. All 1,114 OSM lines had a NULL "
            f"volt_class while carrying clean kv, so a class filter dropped 30% of the merged layer. "
            f"'unknown' is a first-class value and must get its OWN colour, never the bottom of the "
            f"scale. Separately: 1,584 of 3,010 substations have NULL max_kv, so a kV filter "
            f"silently discards 53% of them - disclose that denominator.")])).result()
print("registered in_transmission_voltage")
