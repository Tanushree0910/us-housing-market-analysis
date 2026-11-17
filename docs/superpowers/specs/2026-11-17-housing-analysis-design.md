# U.S. Housing Market Analysis — Design

Date: 2026-11-17 · Owner-approved choices are marked **(owner)**; everything else is the agent's call and can be corrected.

## Why

A resume project. The owner has no SQL or Power BI project on their resume yet **(owner)**. The audience is hiring managers and recruiters who skim the GitHub page for a minute or two. Success means:

- they see clean, readable SQL that shows real skills, such as dynamic SQL, reshaping wide data to long, window functions, views and validation,
- they see a polished Power BI dashboard (screenshots on GitHub, plus a file they can download and open),
- the README tells the story in about 30 seconds: question, chart, finding.

## Goals

Answer the three README questions, unchanged **(owner)**:

1. Which metros have grown fastest year over year?
2. Where is the rent-to-price ratio highest?
3. How do inventory and days on market relate to price changes?

## Non-goals and anti-goals

- No Redfin data **(owner)**. Question 3 uses Zillow's own inventory and days-to-pending files instead **(owner)**.
- No forecasting, no machine learning, and no web app.
- **Anti-goal:** numbers on the dashboard that don't match the raw files. Every headline number is checked against values computed independently from the CSVs.
- **Anti-goal:** a crowded, amateur-looking dashboard.

## Data

| File | Measure | Months |
|---|---|---|
| `Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv` (in repo) | typical home value | 2000-01 → 2026-09, 895 regions |
| `Metro_zori_uc_sfrcondomfr_sm_month.csv` (in repo) | typical monthly rent | 2015-01 → 2026-09, 741 regions |
| Zillow "For-Sale Inventory (Smooth, All Homes, Monthly)", Metro & U.S. **(owner downloaded)** | homes listed for sale | from ~2018 |
| Zillow "Days to Pending (Smooth, All Homes, Monthly)", Metro & U.S. **(owner downloaded)** | days from listing to pending | from ~2018 |

All four files are "wide": the first 5 columns are `RegionID, SizeRank, RegionName, RegionType, StateName`, followed by one column per month-end date. Rent IDs are not a subset of home-value IDs (908 distinct regions across the first two files), and 169 home-value series have months missing in the middle.

## How it gets made

### Approaches considered (Power BI)

- **A. Build by operating Power BI on screen and save a `.pbix`.** This fits the current rules, but it's slow and fragile, and GitHub can't show what's inside.
- **B. Power BI Project format (`.pbip`) written as text, plus a `.pbix` copy (chosen (owner)).** The text files are written directly and checked by opening them in Power BI Desktop. It's faster and readable on GitHub, and the `.pbix` copy is for one-click download. It needs a constitution amendment (Article 3: `powerbi/` gets the project sub-folders).

### Where things run **(owner)**

- The repo in the cloud session is the source of truth for all text files.
- The owner's Windows PC runs SQL Server, sqlcmd and Power BI Desktop. The agent works on it through the Claude desktop app's computer connection, which the owner approved. The PC working folder is the owner's `housing data` folder on the Desktop, which holds the CSVs.
- Binary files (`.pbix`, `.png`) can't travel from the PC to the cloud repo directly. The owner uploads them to the working branch on GitHub.

### SQL design (agent's call)

- Database `HousingMarket`, with three schemas: `raw` (wide copies of the CSVs), `core` (clean tables) and `rpt` (views for analysis and Power BI).
- Scripts in `sql/`, run in order with `sqlcmd -b`. Every script can be re-run and drops or recreates what it owns.
- `raw.usp_load_wide_csv` reads a file's header line, builds a matching wide table with dynamic SQL, then loads it with `BULK INSERT … FORMAT = 'CSV'`. That needs SQL Server 2017 or later.
- `core.metro` is the union of regions across all four files. `core.metro_month` has one row per region per month, with `home_value`, `rent_monthly`, `for_sale_inventory` and `days_to_pending`.
- Year-over-year uses `LAG(…, 12)`, guarded so it only compares months exactly 12 months apart, because some series have gaps.
- `sql/99_validation_checks.sql` compares SQL results against reference numbers computed from the raw CSVs in Python, and fails the run if any check fails.

### Dashboard design **(owner)**

- **Layout B:** four pages, shown as tabs: Overview, 1 · Growth, 2 · Rent vs price, 3 · Supply.
- **Style C, "Navy header":** a navy title bar `#0d366b` with white text on every page, and a clean light body (page `#f9f9f7`, cards `#fcfcfb`).
- **Chart colours:** home value blue `#2a78d6`, rent orange `#eb6834`. These were checked for colour-blind safety.
- **Ink colours:** primary `#0b0b0b`, secondary `#52514e`, muted `#898781`. Gridlines are `#e1e0d9` and "up" deltas are `#006300`.
- **Font:** Segoe UI.
- **Overview page:** three cards (typical home value, typical rent, rent-to-price, each with a change vs last year), a line chart of home value vs rent indexed to Sep 2015 = 100, the 5 fastest-growing large metros, and key takeaways.
- **Growth page:** a month selector (defaults to the latest month), a state filter, the top 10 and bottom 10 of the 100 largest metros by 1-year growth, and a trend line for a chosen metro.
- **Rent vs price page:** a map of rent-to-price by metro, a ranked table and a state filter.
- **Supply page:** a scatter of inventory change vs price change (one dot per large metro), the U.S. days-to-pending trend from 2018, and a correlation card.

### What is left to the builder

Exact visual sizes and positions within the layout, DAX formatting strings, wording of chart titles, and which takeaway sentences to write. The takeaways must be backed by the validated numbers.

## Reference numbers (September 2026, from the raw files)

- U.S. home value **$366,157.15**, +1.19% over the year. U.S. rent **$1,931.94**, +2.70% over the year. U.S. rent-to-price **6.33%**.
- Fastest-growing of the 100 largest metros: Syracuse, NY (+6.62%). Slowest: Austin, TX (−4.31%).
- Highest rent-to-price of the 100 largest metros: Jackson, MS (8.31%). Lowest: San Jose, CA (3.00%). 728 regions have both a value and a rent.
