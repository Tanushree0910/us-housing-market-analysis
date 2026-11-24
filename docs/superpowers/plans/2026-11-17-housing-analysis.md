# U.S. Housing Market Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the SQL Server analysis and the four-page Power BI dashboard that answer the three README questions, and publish them in the repo as a resume project.

**Architecture:** Four wide Zillow CSVs are loaded into SQL Server (`raw`), reshaped into one long table per region and month (`core`), and analysed in views (`rpt`). Power BI imports the `rpt` views. The report is kept in the repo as a Power BI Project (`.pbip`, plain text) plus a `.pbix` copy. Every headline number is checked by `sql/99_validation_checks.sql` against reference values computed from the raw files.

**Tech Stack:** SQL Server 2017+ (T-SQL, `BULK INSERT … FORMAT='CSV'`), sqlcmd, Power BI Desktop (PBIP with TMDL model and PBIR report), Python 3 standard library (governance checker and reference numbers), PowerShell (screen capture on the owner's PC).

**Spec:** `docs/superpowers/specs/2026-11-17-housing-analysis-design.md`

## Global Constraints

- Follow `CONSTITUTION.md`. Work on branch `claude/charming-rubin-9jw9w3`. Never write to `data/*.csv`. Ask the owner before any send, publish, delete, install or architecture change.
- File names: `sql/NN_snake_case.sql` numbered in run order, `screenshots/kebab-case.png`, Power BI base name `us_housing_market`. No file over 50 MB.
- Database `HousingMarket`; schemas `raw`, `core`, `rpt`. Every script can be re-run without error and gives the same result.
- Run scripts with `sqlcmd -S <server> -E -b -I -v DataDir="<PC data folder>" -i <file>`. `<server>` is found in Task 3 and saved in the test log.
- Colours: header `#0d366b` (white text), page `#f9f9f7`, card `#fcfcfb`, home value `#2a78d6`, rent `#eb6834`, ink `#0b0b0b` / `#52514e` / `#898781`, gridline `#e1e0d9`, up-delta `#006300`. Font: Segoe UI.
- Page names, in order: `Overview`, `1 · Growth`, `2 · Rent vs price`, `3 · Supply`.
- "Large metros" means `size_rank BETWEEN 1 AND 100`. "Latest month" means `2026-09-30`.
- After each task: run `python3 tools/governance_check.py` and `python3 -m unittest discover -s tests -t .`, add a test log in `logs/tests/`, then commit.
- Text files are written in the cloud repo and copied to the PC with `_host`. Files that Power BI saves are read back into the repo. Binary files (`.pbix`, `.png`) are committed and pushed from the PC clone (decision 0004); text files may be too.

## Review Focus

1. **SQL Server can't read the CSV folder.** The SQL Server service may be refused access to files on the owner's Desktop, giving "Operating system error 5". The load must stop with that clear error, not a half-loaded table. Task 4 tests this, and the fix (copying the files to a folder the service can read) needs the owner's approval.
2. **Region names with commas, a byte-order mark or Windows line endings.** These must load intact. `New York, NY` must be stored as one name for RegionID 394913, and the first header column must be `RegionID` with no hidden character. Tested in Task 4.
3. **Gaps in a monthly series.** 169 home-value series have missing months. Year-over-year must be NULL where the month 12 months back is missing, never a comparison with the wrong month. Tested in Task 6.
4. **Running a script twice.** It must give the same row counts, with no duplicate rows or "already exists" errors. Tested in Tasks 4 and 5.
5. **The SQL Server name isn't `localhost`, e.g. `localhost\SQLEXPRESS`.** The Power BI refresh must still work, because the name is a model parameter. Tested in Task 10.

---

### Task 0: Owner setup and PC git

- [ ] **Step 1:** The owner connects the PC: in the Claude desktop app, go to Settings → Claude Code → Remote Control and add the `housing data` folder. The agent calls `list_computer_folders` and then `request_computer_folder`, and the owner approves.
- [ ] **Step 2:** The agent checks `git --version` on the PC and that git can reach GitHub (`git ls-remote https://github.com/tanushree0910/us-housing-market-analysis`). If git is missing or not signed in, ask the owner before installing or signing in.
- [ ] **Step 3:** Clone the repo into the shared folder (`housing data\us-housing-market-analysis`) and check out `claude/charming-rubin-9jw9w3`. Copy the two new Zillow files the owner downloaded into its `data/` unchanged. Commit and push from the PC (decision 0004). In the cloud repo, pull. Expected: `data/` holds 4 CSVs, and the checker reports exactly 2 problems, the missing SOURCES rows (fixed in Task 2).

### Task 1: Constitution amendment and checker support for Power BI Project files

**Files:**
- Modify: `tools/governance_rules.py` (`FOLDER_RULES`, `FOLDER_HINTS`; add `POWERBI_PROJECT_DIR`)
- Modify: `tools/governance_check.py:9-22` (`check_layout`)
- Modify: `CONSTITUTION.md` (Article 3 `powerbi/` row, version line → 1.1). The owner says yes at the hook prompt.
- Modify: `.gitignore` (add `powerbi/**/.pbi/localSettings.json` and `powerbi/**/.pbi/cache.abf`)
- Create: `docs/decisions/0003-power-bi-project-format.md` (Status `Accepted`)
- Test: `tests/test_governance_check.py` (class `LayoutTests`)

**Interfaces:**
- Produces: `rules.POWERBI_PROJECT_DIR = re.compile(r"^[a-z0-9_]+\.(SemanticModel|Report)$")`. `powerbi/` top-level files match `^([a-z0-9_]+\.(pbix|pbip)|\.gitkeep)$`.

- [ ] **Step 1: Write the failing tests**

```python
def test_powerbi_project_files_allowed(self):
    self.repo.write("powerbi/us_housing_market.pbip")
    self.repo.write("powerbi/us_housing_market.pbix")
    self.repo.write("powerbi/us_housing_market.SemanticModel/definition/tables/fact_metro_month.tmdl")
    self.repo.write("powerbi/us_housing_market.Report/definition/pages/overview/page.json")
    self.assertEqual(gc.check_layout(self.repo.root), [])

def test_powerbi_unknown_subfolder_flagged(self):
    self.repo.write("powerbi/old/report.pbix")
    problems = gc.check_layout(self.repo.root)
    self.assertEqual(len(problems), 1)
    self.assertIn("powerbi/old/report.pbix", problems[0])

def test_powerbi_bad_project_name_flagged(self):
    self.repo.write("powerbi/Housing.Report/definition.pbir")
    self.assertEqual(len(gc.check_layout(self.repo.root)), 1)

def test_powerbi_other_file_type_flagged(self):
    self.repo.write("powerbi/notes.txt")
    self.assertEqual(len(gc.check_layout(self.repo.root)), 1)
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_governance_check -v`. Expected: `test_powerbi_project_files_allowed` FAILS, with a "must not contain sub-folders" problem and a wrong-name problem for `.pbip`.
- [ ] **Step 3:** In `check_layout`, a `powerbi/` path with more than 2 parts is allowed when `parts[1]` matches `POWERBI_PROJECT_DIR`; otherwise it's flagged as now. Widen the top-level `powerbi` regex and its hint to `snake_case.pbix, snake_case.pbip, or the snake_case.SemanticModel/ and snake_case.Report/ folders Power BI creates`.
- [ ] **Step 4:** Run all tests. Expected: all PASS (79 tests).
- [ ] **Step 5:** Edit `CONSTITUTION.md` Article 3, with the owner's yes. Change the 2nd rule to "These folders accept only these files, and have no sub-folders except the Power BI project folders below". Change the `powerbi/` row to `snake_case.pbix`, `snake_case.pbip`, and the `snake_case.SemanticModel/` and `snake_case.Report/` folders Power BI Desktop creates (any contents), with example `us_housing_market.pbip`. Change the version line to `Version 1.1 — amended 2026-11-17 (decision 0003)`. Update `CLAUDE.md` only if it repeats the old rule.
- [ ] **Step 6:** Write decision 0003: Power BI Project format (owner chose option B), the alternative of a `.pbix` only, and the amendment it required. Run the checker and the tests, write the test log `logs/tests/2026-11-17-powerbi-project-layout.md`, then commit: `feat: allow Power BI project folders (constitution 1.1)`.

### Task 2: Register the new raw files

**Files:**
- Modify: `data/SOURCES.md` (2 rows)
- Create: `docs/decisions/0005-zillow-only-data.md` (Status `Accepted`: Redfin dropped; question 3 uses Zillow inventory and days to pending)

- [ ] **Step 1:** Run `python3 tools/governance_check.py`. Expected: FAIL, naming both new CSVs as having no SOURCES row.
- [ ] **Step 2:** For each new file, add a row with Source `Zillow Research — For-Sale Inventory, metro, monthly, smoothed` or `Zillow Research — Days to Pending, metro, monthly, smoothed`, URL `https://www.zillow.com/research/data/`, Added = the date it is committed, and SHA-256 from `python3 tools/governance_check.py --fingerprint data/<file>`.
- [ ] **Step 3:** Generate this task's reference numbers. Use a Python script in the scratchpad (stdlib `csv`, `encoding='utf-8-sig'`), run on the 2 new files, and print: row count, number of month columns, first month, non-empty value count, distinct RegionID count across all 4 files, and the U.S. (RegionID 102001) values for `2026-09-30` and `2025-09-30`. Paste the output into the test log `logs/tests/YYYY-MM-DD-new-raw-files.md`. Tasks 4–8 use these numbers.
- [ ] **Step 4:** Run the checker and the tests (expected PASS), then commit: `data: register Zillow inventory and days-to-pending files`.

### Task 3: Check the owner's PC is ready

No repo code. Output: test log `logs/tests/YYYY-MM-DD-pc-environment.md`.

- [ ] **Step 1:** On the PC, run `sqlcmd -?`. Expected: usage text. If it's missing, ask the owner before installing anything (`winget install sqlcmd`).
- [ ] **Step 2:** Run `sqlcmd -S localhost -E -Q "SELECT @@SERVERNAME, SERVERPROPERTY('ProductVersion')"`. If that fails, try `localhost\SQLEXPRESS`. Expected: major version ≥ 14 (SQL Server 2017). Record the working server name.
- [ ] **Step 3:** Run `Get-ItemProperty` on the Power BI Desktop install, or check Help → About. Record the version. In Options → Preview features, the PBIP, TMDL and PBIR options must be on (if they're listed), and Desktop must be restarted after changing them.
- [ ] **Step 4:** Write the test log and commit: `test: record PC environment check`.

### Task 4: Database and raw load

**Files:**
- Create: `sql/01_create_database.sql` (database `HousingMarket`, schemas `raw`, `core`, `rpt`; if-not-exists guards)
- Create: `sql/02_load_raw_files.sql` (procedure plus 4 calls)
- Create: `sql/99_validation_checks.sql`

**Interfaces:**
- Produces: `raw.usp_load_wide_csv @file_path NVARCHAR(400), @table_name SYSNAME`. It drops and recreates `raw.<table_name>` with columns `RegionID INT, SizeRank INT, RegionName NVARCHAR(100), RegionType NVARCHAR(20), StateName NVARCHAR(10)`, plus one `NVARCHAR(30)` column per month named exactly like the header (e.g. `[2026-09-30]`).
- Produces: tables `raw.zhvi_wide`, `raw.zori_wide`, `raw.inventory_wide`, `raw.days_to_pending_wide`.
- Produces: in `99_validation_checks.sql`, temp table `#check (check_name NVARCHAR(200), expected NVARCHAR(100), actual NVARCHAR(100), result AS CASE WHEN expected = actual THEN 'PASS' ELSE 'FAIL' END)`. It ends by selecting all rows, then `THROW 50001, 'Validation failed', 1` if any row has `result = 'FAIL'`. Later tasks add rows to it.

- [ ] **Step 1: Write the failing checks** in `99_validation_checks.sql`:
  - `raw.zhvi_wide rows` = `895`
  - `raw.zori_wide rows` = `741`
  - inventory and days-to-pending rows = the Task 2 numbers
  - `zhvi month columns` = `321`
  - `zori month columns` = `141`
  - `name of 394913` = `New York, NY`
  - `first column of raw.zhvi_wide` = `RegionID`
- [ ] **Step 2:** Run `99` on the PC. Expected: the run fails with "Invalid object name 'raw.zhvi_wide'", or with FAIL rows.
- [ ] **Step 3:** Implement the procedure. It reads the header line by bulk-loading the file into a one-column temp table, using a field terminator that never appears (`0x07`) and `ROWTERMINATOR = '0x0a'`. It strips a leading BOM and a trailing `\r`, builds the `CREATE TABLE` with dynamic SQL (`QUOTENAME` on every name), then runs `BULK INSERT … WITH (FORMAT='CSV', FIRSTROW=2, FIELDQUOTE='"', CODEPAGE='65001', ROWTERMINATOR='0x0a')`. If an error happens, the table is dropped and the error re-thrown. The 4 calls use `$(DataDir)` and the original file names.
- [ ] **Step 4:** Run `01`, `02` and `99`. Expected: all PASS. If it fails with "Operating system error 5", stop and ask the owner to approve copying the CSVs to `C:\HousingData` (Review Focus 1). Record any bug in `logs/bugs/`.
- [ ] **Step 5:** Run `02` and then `99` again. Expected: the same counts, all PASS (Review Focus 4).
- [ ] **Step 6:** Copy the files back to the repo, write the test log, then commit: `feat(sql): create database and load raw Zillow files`.

### Task 5: Core tables

**Files:**
- Create: `sql/03_build_core_tables.sql`
- Modify: `sql/99_validation_checks.sql`

**Interfaces:**
- Produces: `core.metro (metro_id INT PK, metro_name NVARCHAR(100), state_code NVARCHAR(10) NULL, region_type NVARCHAR(20), size_rank INT)`. It's the union of all 4 raw tables; `size_rank` comes from ZHVI when present, otherwise the lowest value found.
- Produces: `core.metro_month (metro_id INT, month_end DATE, home_value DECIMAL(12,2) NULL, rent_monthly DECIMAL(10,2) NULL, for_sale_inventory INT NULL, days_to_pending INT NULL, PK (metro_id, month_end))`.

- [ ] **Step 1: Add the failing checks:**
  - `core.metro rows` = the Task 2 distinct-ID count across all 4 files. It's at least `908`, which is the count for ZHVI and ZORI alone.
  - `home_value non-null` = `238029`
  - `rent_monthly non-null` = `53977`
  - inventory and days-to-pending non-null = the Task 2 counts
  - `US home_value 2026-09` = `366157.15`
  - `US rent 2026-09` = `1931.94`
  - `duplicate metro_month keys` = `0`
- [ ] **Step 2:** Run `99`. Expected: FAIL.
- [ ] **Step 3:** Implement the script. It drops and recreates both tables. The unpivot is built with dynamic SQL: `CROSS APPLY (VALUES ('2000-01-31', [2000-01-31]), …)`, generated from `sys.columns` where the name is a date. Empty strings are skipped. Values use `TRY_CAST(... AS FLOAT)` and are then rounded to the column type. The 4 measures are merged with a `FULL OUTER JOIN` on `(metro_id, month_end)`.
- [ ] **Step 4:** Run `03` twice, then `99`. Expected: all PASS.
- [ ] **Step 5:** Write the test log, then commit: `feat(sql): reshape raw files into core tables`.

### Task 6: Question 1 — home value growth

**Files:**
- Create: `sql/04_home_value_growth.sql`
- Modify: `sql/99_validation_checks.sql`

**Interfaces:**
- Produces: view `rpt.v_home_value_growth (metro_id, month_end, home_value, home_value_1y_ago, yoy_pct DECIMAL(9,4))`. `yoy_pct` is a percentage, e.g. `1.19`.

- [ ] **Step 1: Add the failing checks** (rounded to 2 decimals):
  - `US yoy 2026-09` = `1.19`
  - `Syracuse yoy 2026-09` (395143) = `6.62`
  - `Austin yoy 2026-09` (394355) = `-4.31`
  - `top large metro 2026-09` = `Syracuse, NY`
  - `bottom large metro 2026-09` = `Austin, TX`
  - `gap months with yoy` = `0`. This counts rows where `yoy_pct IS NOT NULL` and no row exists for that metro at `EOMONTH(month_end, -12)` (Review Focus 3).
- [ ] **Step 2:** Run `99`. Expected: FAIL.
- [ ] **Step 3:** Implement the view with `LAG(home_value, 12)` and `LAG(month_end, 12)` over `metro_id` ordered by `month_end`, on non-null home values only. `yoy_pct` is NULL unless the lagged month equals `EOMONTH(month_end, -12)`.
- [ ] **Step 4:** Run `04` and `99`. Expected: all PASS. Write the test log, then commit: `feat(sql): year-over-year home value growth`.

### Task 7: Question 2 — rent-to-price

**Files:**
- Create: `sql/05_rent_to_price.sql`
- Modify: `sql/99_validation_checks.sql`

**Interfaces:**
- Produces: view `rpt.v_rent_to_price (metro_id, month_end, home_value, rent_monthly, rent_to_price_pct DECIMAL(9,4))` = `rent_monthly * 12 / home_value * 100`. It only has rows where both values exist.

- [ ] **Step 1: Add the failing checks:**
  - `rows 2026-09` = `728`
  - `US rent_to_price 2026-09` = `6.33`
  - `highest large metro` = `Jackson, MS` (`8.31`)
  - `lowest large metro` = `San Jose, CA` (`3.00`)
- [ ] **Step 2:** Run `99`. Expected: FAIL. Then implement, and run `05` and `99`. Expected: PASS.
- [ ] **Step 3:** Write the test log, then commit: `feat(sql): rent-to-price ratio`.

### Task 8: Question 3 — supply vs price

**Files:**
- Create: `sql/06_supply_vs_price.sql`
- Modify: `sql/99_validation_checks.sql`

**Interfaces:**
- Produces: view `rpt.v_supply_vs_price (metro_id, month_end, for_sale_inventory, inventory_yoy_pct, days_to_pending, days_to_pending_yoy_change INT, home_value_yoy_pct)`. It uses the same 12-month guard as Task 6; `home_value_yoy_pct` comes from `rpt.v_home_value_growth`.
- Produces: view `rpt.v_supply_price_correlation (month_end, metros INT, r_inventory_vs_price DECIMAL(6,4), r_days_vs_price DECIMAL(6,4))`. These are Pearson correlations across large metros that have all three values, computed with `SUM`/`COUNT` aggregates.

- [ ] **Step 1:** Compute the reference values in a scratchpad Python script from the raw CSVs, for `2026-09-30`, using the same definitions: the number of metros and both r values to 4 decimals, plus the U.S. `inventory_yoy_pct` and `days_to_pending`. Add these as failing checks.
- [ ] **Step 2:** Run `99`. Expected: FAIL. Then implement, and run `06` and `99`. Expected: PASS.
- [ ] **Step 3:** Write the test log, then commit: `feat(sql): supply versus price views`.

### Task 9: Power BI model views

**Files:**
- Create: `sql/07_powerbi_views.sql`
- Modify: `sql/99_validation_checks.sql`

**Interfaces:**
- Produces: `rpt.dim_metro (metro_id, metro_name, state_code, region_type, size_rank, is_large_metro BIT)`.
- Produces: `rpt.dim_month (month_end DATE, year INT, month_num INT, month_label NCHAR(8) e.g. 'Sep 2026')`, covering every month from `2000-01-31` to the latest `month_end` in `core.metro_month`.
- Produces: `rpt.fact_metro_month (metro_id, month_end, home_value, rent_monthly, for_sale_inventory, days_to_pending, home_value_yoy_pct, rent_yoy_pct, rent_to_price_pct, inventory_yoy_pct, days_to_pending_yoy_change)`. It has one row per `core.metro_month` row and reuses the Task 6–8 views.

- [ ] **Step 1:** Add the failing checks:
  - `fact rows` = the `core.metro_month` row count
  - `dim_month rows` = `321`
  - `large metros` = `100`
  - `US rent_yoy 2026-09` = `2.70`
- [ ] **Step 2:** Run `99`. Expected: FAIL. Then implement, and run `07` and `99`. Expected: PASS.
- [ ] **Step 3:** Run every script `01`–`07` and then `99` in order from a fresh state (`DROP DATABASE HousingMarket` first, which is this project's own database). Expected: all PASS. Write the test log, then commit: `feat(sql): Power BI model views`.

### Task 10: Power BI semantic model (TMDL)

**Files:**
- Create: `powerbi/us_housing_market.pbip`
- Create: `powerbi/us_housing_market.SemanticModel/definition.pbism`
- Create: `powerbi/us_housing_market.SemanticModel/definition/{database,model,expressions,relationships}.tmdl`
- Create: `powerbi/us_housing_market.SemanticModel/definition/tables/{dim_metro,dim_month,fact_metro_month,supply_price_correlation,measures}.tmdl`

**Interfaces:**
- Consumes: the Task 9 views and `rpt.v_supply_price_correlation`.
- Produces: M parameters `SqlServer` (the value from Task 3) and `SqlDatabase` = `"HousingMarket"`. Every table imports with `Sql.Database(SqlServer, SqlDatabase)`.
- Produces: relationships `fact_metro_month[metro_id] → dim_metro[metro_id]` and `fact_metro_month[month_end] → dim_month[month_end]`, both many-to-one with single direction.
- Produces: these measures in table `measures`. Each one uses the latest `month_end` in the current filter context unless noted.

| Measure | What it shows |
|---|---|
| `Home Value` | the home value |
| `Home Value YoY %` | 1-year change in home value |
| `Rent` | the monthly rent |
| `Rent YoY %` | 1-year change in rent |
| `Rent to Price %` | yearly rent compared with home value |
| `Inventory YoY %` | 1-year change in homes for sale |
| `Days to Pending` | days from listing to pending |
| `Home Value Index` | `Home Value` ÷ the Sep 2015 home value × 100, for each month |
| `Rent Index` | the same calculation for rent |
| `Inventory vs Price r` | the correlation from `supply_price_correlation` |
| `Latest Month Label` | e.g. "Sep 2026" |

- [ ] **Step 1:** Write the files. Copy them to the PC, open the `.pbip` in Power BI Desktop and click Refresh. Expected: no load errors.
- [ ] **Step 2:** In DAX query view, run `EVALUATE` with `CALCULATETABLE(ROW(...the measures...), dim_metro[metro_id] = 102001)`. Expected:
  - `Home Value` = 366157.15
  - `Home Value YoY %` = 1.19
  - `Rent` = 1931.94
  - `Rent YoY %` = 2.70
  - `Rent to Price %` = 6.33
  - `Latest Month Label` = "Sep 2026"
- [ ] **Step 3:** Review Focus 5: change `SqlServer` to the alternative name form for the same server (e.g. `.` vs `localhost`), refresh, and expect success. Then set it back.
- [ ] **Step 4:** Save in Power BI. Copy every file under `powerbi/` back from the PC into the repo, so the repo holds what Power BI wrote. Run the checker and the tests, write the test log, then commit: `feat(powerbi): semantic model`.

### Task 11: Report pages and theme (PBIR)

**Files:**
- Create: `powerbi/us_housing_market.Report/definition.pbir`, `definition/report.json`, `definition/pages/pages.json`, one folder per page with `page.json` and `visuals/*/visual.json`
- Create: `powerbi/us_housing_market.Report/StaticResources/RegisteredResources/navy_header_theme.json`

**Interfaces:**
- Consumes: the Task 10 measures and columns.
- Produces: the theme sets data colours `["#2a78d6","#eb6834"]`, background `#f9f9f7`, card/visual background `#fcfcfb`, text `#0b0b0b`/`#52514e`, and font Segoe UI. Every page is 1280 × 720, with a navy header shape (`#0d366b`, 0–72 px high), a white title "U.S. Housing Market Analysis", a subtitle with `Latest Month Label`, and a page navigator.

- [ ] **Step 1:** Overview page:
  - 3 cards (Home Value, Rent, Rent to Price %), each with its YoY % below, filtered to metro 102001
  - a line chart of `Home Value Index` and `Rent Index` by `dim_month[month_end]` from 2015, U.S. only, with the legend on and end labels
  - a bar chart of the top 5 large metros by `Home Value YoY %` for the latest month
  - an empty text box for the takeaways (filled in Task 13)
- [ ] **Step 2:** `1 · Growth` page:
  - a month slicer (single select, default the latest month) and a state slicer
  - two bar charts: top 10 and bottom 10 large metros by `Home Value YoY %`
  - a metro slicer driving a `Home Value` line chart
- [ ] **Step 3:** `2 · Rent vs price` page:
  - an Azure Maps bubble map with location `metro_name`, size and colour `Rent to Price %`, and the sequential blue ramp
  - a table of metro, state, Rent to Price %, Home Value and Rent, sorted descending
  - a state slicer
  - If the map visual is turned off on the owner's PC or account, replace it with a bar chart of the top 20 and note it in the test log.
- [ ] **Step 4:** `3 · Supply` page:
  - a scatter of `Inventory YoY %` (x) against `Home Value YoY %` (y), one dot per large metro, latest month
  - a card for `Inventory vs Price r`
  - a line chart of the U.S. `Days to Pending` from 2018
- [ ] **Step 5:** Open the report in Power BI Desktop and look at each page with computer use. Expected: no broken visuals, and the numbers match the Task 10 values. Fix any issues, then save in Power BI and copy the files back. Run the checker and the tests, write the test log, then commit: `feat(powerbi): four report pages with navy header theme`.

### Task 12: .pbix copy and screenshots

**Files:**
- Create (pushed from the PC clone): `powerbi/us_housing_market.pbix`
- Create (pushed from the PC clone): `screenshots/overview.png`, `screenshots/growth.png`, `screenshots/rent-vs-price.png`, `screenshots/supply.png`

- [ ] **Step 1:** In Power BI, choose File → Save as → `us_housing_market.pbix` in the PC folder. Check that it's under 50 MB.
- [ ] **Step 2:** For each page, maximise Power BI, hide the panes, and show the page. Then run a PowerShell `System.Drawing` screen capture of the report canvas into the PC folder, using the PNG names above. Look at each image and check it's sharp and not cut off.
- [ ] **Step 3:** Commit and push the 5 files from the PC clone, then pull in the cloud repo. Expected: the checker and the tests PASS. Write the test log, then commit.

### Task 13: Findings and README

**Files:**
- Modify: `README.md` (Findings section, screenshots, "How to run it", "Skills shown")
- Modify: Overview takeaways text box (Task 11 files), then redo the `overview.png` capture and push from Task 12

- [ ] **Step 1:** Write 3 to 5 takeaways, each backed by a number in `99_validation_checks.sql`, e.g. "Since Sep 2015 U.S. home values rose 88% while rents rose 64%".
- [ ] **Step 2:** In the README:
  - one paragraph per question, with its screenshot and finding
  - "How to run it": the sqlcmd order `01`–`07`, then `99`; then open the `.pbip` or `.pbix` and set `SqlServer`
  - a "Skills shown" list: dynamic SQL, unpivot, window functions, views, validation tests, star schema, DAX, Power BI Project format
- [ ] **Step 3:** Run the checker and the tests, write the test log, then commit: `docs: findings and README`.

### Task 14: Finish

- [ ] **Step 1:** Run `superpowers:requesting-code-review` on the whole branch. Fix the findings.
- [ ] **Step 2:** Complete the session journal, run both checks, push, and ask the owner whether to open a pull request.
