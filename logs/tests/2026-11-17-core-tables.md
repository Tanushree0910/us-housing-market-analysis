# Test: Core tables built from the raw files

## What was tested
`sql/03_build_core_tables.sql` (`core.metro`, `core.metro_month`) and the Task 5 checks in `sql/99_validation_checks.sql`.

## How
1. Added 12 checks to `99` and ran it before `03` existed: failed with `Invalid object name 'core.metro'`, exit 1.
2. Reference numbers from a scratchpad Python script over the raw CSVs (stdlib `csv`): 928 distinct regions; 240,674 region-months with at least one value up to 2026-09-30; non-empty cells home value 238,029, rent 53,977, inventory 94,391 and days to pending 50,769 (the last two counted to 2026-09-30, see `2026-11-17-new-raw-files.md`).
3. Ran `sqlcmd -S localhost -E -C -b -I -i sql/03_build_core_tables.sql` twice: both runs reported 928 metros, 240,674 metro-months, 2000-01-31 to 2026-09-30, exit 0 (Review Focus 4).
4. Ran `99`: all 30 checks PASS, including U.S. Sep 2026 home value 366157.15, rent 1931.94, inventory 1407575, days to pending 56, no duplicate keys, latest month 2026-09-30.

## Result
PASS

## Bugs
None
