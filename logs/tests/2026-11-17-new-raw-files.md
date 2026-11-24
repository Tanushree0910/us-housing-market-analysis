# Test: New raw files registered, with reference numbers

## What was tested
The two new Zillow files the owner downloaded (`Metro_invt_fs_uc_sfrcondo_sm_month.csv`, `Metro_mean_doz_pending_uc_sfrcondo_sm_month.csv`): they are byte-identical to the owner's download, they have `data/SOURCES.md` rows, and the reference numbers that Tasks 4–8 check against.

## How
- `cmp` of each file against the owner's download in the parent folder: identical.
- `python tools/governance_check.py` before the SOURCES rows: FAILED with exactly 2 problems (both files not listed). After: clean.
- Fingerprints from `python tools/governance_check.py --fingerprint data/<file>`.
- A scratchpad Python script (stdlib `csv`, `encoding='utf-8-sig'`) over all 4 raw files printed:

```
zhvi: header0='RegionID' rows=895 month_cols=321 first=2000-01-31 last=2026-09-30 nonempty=238029 US 2026-09-30=366157.1523869674 US 2025-09-30=361858.8864864355
zori: header0='RegionID' rows=741 month_cols=141 first=2015-01-31 last=2026-09-30 nonempty=53977 US 2026-09-30=1931.9376933761196 US 2025-09-30=1881.170709301828
inventory: header0='RegionID' rows=928 month_cols=104 first=2018-03-31 last=2026-10-31 nonempty=95318 US 2026-09-30=1407575.0 US 2025-09-30=1373160.0
days_to_pending: header0='RegionID' rows=716 month_cols=104 first=2018-03-31 last=2026-10-31 nonempty=51485 US 2026-09-30=56.0 US 2025-09-30=54.0
distinct RegionID across 4 files: 928
```

- Limited to months up to 2026-09-30 (the analysis window, decision 0005): inventory 103 month columns and 94391 non-empty values; days to pending 103 month columns and 50769 non-empty values. All supply values are whole numbers written as `N.0`.

- `python -m unittest discover -s tests -t .`: first run 1 error (symlink test, BUG-001); after the fix 79 tests run, 78 pass and 1 is skipped on Windows (it runs on GitHub's Linux CI).

## Result
PASS

## Bugs
[BUG-001](../bugs/BUG-001-symlink-test-fails-on-windows.md)
