# Zillow SQL Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the owner's Housing Data SQL into the repo in run order, load Zillow inventory and days to pending, replace the Redfin market view with a Zillow one, and answer README question 3.

**Architecture:**
- T-SQL scripts in `sql/`, run in number order in SSMS against the `Housing Data` database.
- A Python test checks every expected number in the scripts' check queries against the CSVs, so the numbers can't drift.

**Tech Stack:** SQL Server 2025 (T-SQL), SSMS, Python 3 stdlib `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-19-zillow-sql-pipeline-design.md`

## Global Constraints

- Database: `[Housing Data]`. Every script starts with `USE [Housing Data];`.
- Default data folder in scripts: `C:\Projects\us-housing-market-analysis\data\`. Set once at the top of the load script.
- Raw tables are never altered or dropped by any script (Article 2). Loads run only when the table doesn't exist.
- Long-table shape: `RegionID int, RegionName nvarchar(200), RegionType nvarchar(20), StateName nvarchar(10), SizeRank int, month_date date, <value> decimal(18,4)`.
- Every script ends with check queries, each with a comment giving the expected result, matching the owner's existing style.
- Names: `sql/NN_snake_case.sql` (Article 3).

## Review Focus

1. **The CSV has Windows line endings** (Git on Windows converts them). The last month's value must not carry a hidden `\r`. Test via the expected count of the last month in Task 1's checks.
2. **Metro names with commas inside quotes** ("Atlanta, GA") must load into one column. Checked by the Atlanta check row.
3. **Re-running the load script** must not duplicate rows or touch `ZHVI_HomeValue` / `ZORI_Rentals`. The script's guard plus a re-run row-count check.
4. **SQL Server can't read the data folder** (permissions). The script fails with a clear message naming the folder and the fix.
5. **A month where inventory exists but days to pending doesn't** must still appear in `fact_market`, with `days_to_pending` NULL. The FULL JOIN row count is 95,346, not 51,457.

---

### Task 1: Load script for Zillow wide CSVs

**Files:**
- Create: `sql/01_load_zillow.sql`, `tests/test_sql_expectations.py`

**Interfaces:**
- Produces: tables `dbo.Inventory_ForSale(…, inventory)` and `dbo.DaysToPending(…, days_to_pending)`.
- Produces: procedure `dbo.load_zillow_wide @file nvarchar(400), @table sysname, @value_column sysname`:
  1. Reads the header with `OPENROWSET(BULK …, SINGLE_CLOB)`.
  2. Builds an all-`nvarchar(400)` staging table.
  3. Runs `BULK INSERT … WITH (FORMAT='CSV', FIRSTROW=2, FIELDQUOTE='"', ROWTERMINATOR='0x0a', CODEPAGE='65001')`.
  4. Unpivots non-blank cells, trimming `CHAR(13)`, into `@table`.
- The same script loads `ZHVI_HomeValue` and `ZORI_Rentals` only if they are missing, using the same procedure with value columns `home_value` and `rent`.
- Produces in `tests/test_sql_expectations.py`: `zillow_long(file) -> dict[(region_id, month), float]`, used by later tasks.

- [ ] **Step 1: Failing test.** `test_load_checks_match_csv` parses `sql/01_load_zillow.sql` for lines `-- expect <name>: <number>` and asserts:
  - `inventory_rows: 95318`, `days_to_pending_rows: 51485`, `zhvi_rows: 238029`, `zori_rows: 53977`;
  - `inventory_last_month_rows`: the count for 2026-10-31, computed by the test;
  - `atlanta_inventory_2026_09: 33948`.
- [ ] **Step 2:** `cd <worktree> && python3 -m unittest tests.test_sql_expectations -v` → FAIL (file missing).
- [ ] **Step 3:** Write the script: procedure, four guarded loads, check queries with the `-- expect` lines. A permission failure is caught (`TRY…CATCH`) and re-raised with: "SQL Server can't read <folder>. Check the path at the top of this script."
- [ ] **Step 4:** Test → PASS. Governance checker → OK.
- [ ] **Step 5:** Commit `feat(sql): load Zillow inventory and days-to-pending into Housing Data`.

### Task 2: Dimensions and existing facts, renamed into run order

**Files:**
- Create (moved with `git mv`, content updated):
  - `sql/02_dim_metro.sql` (from `dim_metro.sql`)
  - `sql/03_dim_date.sql` (from `SQLQuery2.sql`)
  - `sql/04_fact_home_values.sql` (from `SQLQuery3.sql`)
  - `sql/05_fact_rent.sql` (from `SQLQuery4.sql`)
- Delete: `sql/SQLQuery1.sql`. Its `dim_metro` v1 is replaced by v2 in `dim_metro.sql`. Its column-listing query was exploratory.
- Modify: `tests/test_sql_expectations.py`

**Interfaces:**
- `dim_metro` (v3) is a UNION of the four tables; expect 928 rows and 928 distinct RegionIDs.
- `dim_date` covers dates from all four tables, so its range is 2000-01-01 to 2026-12-31.
- `fact_home_values` and `fact_rent` keep their columns. Add `USE [Housing Data];`, which `SQLQuery3–4` lacked.

- [ ] **Step 1: Failing tests:** `test_dim_metro_checks_match_csv` (928/928, 0 missing per table) and `test_dim_date_checks_match_csv` (first 2000-01-01, last 2026-12-31, total days computed).
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Move and update the scripts, keeping the owner's comments. Add a header note on each saying where it came from.
- [ ] **Step 4:** Test → PASS. Checker → OK.
- [ ] **Step 5:** Commit `refactor(sql): put star-schema scripts in run order and cover all four Zillow tables`.

### Task 3: Zillow `fact_market` and README question 3

**Files:**
- Create: `sql/06_fact_market.sql` (Zillow version; the Redfin `sql/fact_market.sql` content is not carried over), `sql/07_analysis.sql` (from `analysis.sql`, plus Q9–Q10)
- Modify: `tests/test_sql_expectations.py`, `powerbi/core_measures.dax`

**Interfaces:**
- `fact_market(RegionID, month_date, inventory, days_to_pending)`: a FULL JOIN of the two new tables. Expect 95,346 rows, 928 metros, 2018-03-31 to 2026-10-31. Atlanta, 2026-09-30: inventory 33,948, days to pending 72.
- Q9: for each metro, the latest-month YoY % change in home value next to the YoY % change in inventory and in days to pending, metros only.
- Q10: the correlation across metros (Pearson, computed in SQL) between YoY home-value change and each of the other two, with the expected values in comments.
- DAX: `Avg Inventory = AVERAGE(fact_market[inventory])` and `Avg Days to Pending = AVERAGE(fact_market[days_to_pending])`, with verification values for Atlanta, Sep 2026.

- [ ] **Step 1: Failing tests:**
  - `test_fact_market_checks_match_csv`;
  - `test_q10_correlations_match_csv`: the test computes both correlations from the CSVs and compares them to the `-- expect` lines, to 3 decimals.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Write the scripts and the DAX additions.
- [ ] **Step 4:** Test → PASS. Checker → OK.
- [ ] **Step 5:** Commit `feat(sql): Zillow market view and inventory/days-to-pending analysis`.

### Task 4: Data sources, README, records

**Files:**
- Modify: `data/SOURCES.md` (two rows, fingerprints from `python3 tools/governance_check.py --fingerprint`), `README.md` (Zillow only; four data sets; Q3 wording "inventory and days to pending"; how to run the scripts in order)
- Resolve `powerbi/core_measures.dax` per the owner's decision (see the open question below)
- Create: `logs/tests/2026-11-19-zillow-sql-pipeline.md`, the session journal

- [ ] **Step 1:** Run the checker → it lists the remaining problems (missing `SOURCES.md` rows, the `.dax` file).
- [ ] **Step 2:** Make the changes.
- [ ] **Step 3:** Checker → `OK`. Full test suite → PASS.
- [ ] **Step 4:** Commit `docs: Zillow-only sources and README; records`. Push and open a pull request. Don't merge without the owner's request.
- [ ] **Step 5 (owner, in SSMS):** run `01`–`07` in order and send screenshots of each script's check results. Any mismatch becomes a bug log and a fix.

## Open question for the owner

- **`.dax` file home.** (A) Allow `.dax` files in `powerbi/` (amend Article 3 and the checker rule). (B) Move the file to `docs/powerbi-measures.dax`. Recommended: **A**, because the measures belong next to the report.
