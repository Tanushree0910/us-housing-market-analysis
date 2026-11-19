# Test: Zillow SQL pipeline

## What was tested
- The SQL scripts `sql/01_load_zillow.sql` to `sql/07_analysis.sql`, and the market measures in `powerbi/core_measures.dax`.
- Every expected number in the scripts' check queries, recomputed from the Zillow CSVs:
  - row counts;
  - newest month;
  - Atlanta hand-check values;
  - metro and date counts;
  - `fact_market` size;
  - the two Q10 correlations.
- Whether the four Zillow files agree on each metro's details.
- The governance checker, including the new rule allowing `.dax` files in `powerbi/`.

## How
- Ran `python3 -m unittest discover -s tests -t .` (all tests, including `tests/test_sql_expectations.py`).
- Ran `python3 tools/governance_check.py`.
- The SQL itself was **not executed here**, because installing SQL Server in this workspace was blocked. The owner runs scripts 01–07 in SSMS and compares each check query with its `-- expect` line. Any mismatch is logged as a bug.

## Result
PASS

## Bugs
None found by the tests. Two problems were caught while reviewing the SQL, before any test run:
- `PRINT` can't contain a sub-query. Fixed by using a variable.
- A first draft dropped the unused Redfin view without approval. Removed.
