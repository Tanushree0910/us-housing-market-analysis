# Test: Fixes from the final whole-branch review

## What was tested
The three findings fixed after a fresh-context review of the whole branch (Critical 0, Important 2, Minor 9; one minor was re-graded Important):
1. The byte-order-mark check in `sql/99_validation_checks.sql` could not fail.
2. The loader in `sql/02_load_raw_files.sql` silently skipped up to 10 malformed rows (BULK INSERT's default `MAXERRORS`).
3. `2026-11-17-raw-load.md` gave the wrong reason why SQL Server could read the data folder, and the README did not explain file access.

## How
1. **BOM check.** RED: under the database collation `SQL_Latin1_General_CP1_CI_AS`, `N'RegionID' = NCHAR(65279) + N'RegionID'` is true, so the old check passed even with a BOM. Fix: a check on `UNICODE(name)` of the first column, expecting 82 (`R`), plus a sanity check that a BOM-prefixed name gives 65279. GREEN: both PASS.
2. **Bad rows.** RED: a scratchpad file with 3 data rows, one with RegionID `abc`, loaded 2 rows with exit 0 and no warning. Fix: `MAXERRORS = 0` on the data load. GREEN: the same file now stops with `Msg 4864 … row 3, column 1 (RegionID)`, exit 1, and no table is left behind. The four real files still load in full (895 / 741 / 928 / 716 rows).
3. **File access.** `icacls` shows that `NT Service\MSSQLSERVER` has no rights on the data folder. With `-E`, `BULK INSERT` reads the file using the caller's own Windows login. The test log was corrected, and the README's "How to run it" now explains this and what to do with a SQL login or a remote server.
4. Full rebuild: dropped `HousingMarket`, then ran `01`–`07` and `99` with `sqlcmd -S localhost -E -C -b -I`. Every script exit 0; 60 checks, all PASS. The README now says 60.
5. `python tools/governance_check.py`: no problems. `python -m unittest discover -s tests -t .`: OK (1 skipped on Windows).

## Result
PASS

## Bugs
None logged separately. All three were found by the review and fixed with a failing test first.
