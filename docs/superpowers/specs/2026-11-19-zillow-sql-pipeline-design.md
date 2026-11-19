# Zillow SQL Pipeline — Design

**Owner decisions (2026-11-19):**
- Build on the **Housing Data** database. Leave HousingMarket untouched.
- Drop Redfin. Use Zillow only.

## Intent
The README asks three questions:
1. Which metros grew fastest year over year?
2. Where is the rent-to-price ratio highest?
3. How do inventory and days on market relate to price changes?

The owner's existing star schema (`dim_metro`, `dim_date`, `fact_home_values`, `fact_rent`), `analysis.sql` and the Power BI measures already answer questions 1 and 2. Question 3 depended on Redfin. It moves to two Zillow data sets that are now in `data/`: for-sale inventory (`Metro_invt_fs_…`) and mean days to pending (`Metro_mean_doz_pending_…`).

## Facts the design rests on
- Each Zillow file is wide: five ID columns (`RegionID, SizeRank, RegionName, RegionType, StateName`), then one column per month-end date.
- The owner's `ZHVI_HomeValue` (238,029 rows) and `ZORI_Rentals` (53,977 rows) contain exactly the non-blank cells of their CSVs, one row per metro per month.
- Inventory has 95,318 non-blank cells across 928 metros. Days to pending has 51,485 across 716 metros. Both run from 2018-03-31 to 2026-10-31.
- Across all four files there are 928 distinct `RegionID`s, with no conflicting names, types, states or ranks. `102001` is the United States ("country") row.
- The Power BI report uses only `dim_date`, `dim_metro` and measures. The Redfin `fact_market` view is used only by its own script.

## Design
- **Loading:** one script loads any Zillow wide CSV into a long table, `(RegionID, RegionName, RegionType, StateName, SizeRank, month_date, <value>)`, keeping non-blank cells only.
  - It works out the month columns from the file's header, so new months need no edits.
  - It creates and loads a table only if that table doesn't exist yet. Re-running the script never changes the owner's existing `ZHVI_HomeValue` / `ZORI_Rentals`.
  - New tables: `dbo.Inventory_ForSale` (value column `inventory`) and `dbo.DaysToPending` (value column `days_to_pending`).
- **Views:**
  - `dim_metro` covers metros from all four tables: 928 rows.
  - `dim_date` covers dates from all four tables.
  - `fact_market` is replaced with a Zillow version: inventory and days to pending per metro-month (95,346 rows).
- **Analysis:** add the README's third question to the analysis script. It compares each metro's year-over-year change in inventory and in days to pending with its home-value change.
- **Power BI:** add `Avg Inventory` and `Avg Days to Pending` measures to the DAX file.
- **Repo:**
  - Scripts are renamed to Article 3's `NN_snake_case.sql` in run order. The `SQLQuery1–4` drafts are folded into them.
  - The two new files get `SOURCES.md` rows.
  - The README drops Redfin.

## Not in scope
- Changing the Power BI report file itself. Only the owner edits `.pbix`.
- Deleting the Redfin tables or the HousingMarket database.
