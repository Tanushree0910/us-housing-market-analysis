# U.S. Housing Market Analysis

SQL Server + Power BI analysis of home values, rents and market conditions across U.S. metros.

## Questions this project answers
- Which metros have grown fastest year over year?
- Where is the rent-to-price ratio highest?
- How do inventory and days to pending (how fast homes go under contract) relate to price changes?

## Data
Zillow Research, metro level, monthly (files and fingerprints in [data/SOURCES.md](data/SOURCES.md)):
- ZHVI: typical home values
- ZORI: typical rents
- For-sale inventory
- Mean days to pending

## Tools
SQL Server, SSMS, Power BI Desktop

## Repo structure
- `/data` raw source files
- `/sql` load script, views and analysis, numbered in run order
- `/powerbi` Power BI report (.pbix) and its measures (.dax)
- `/screenshots` dashboard images
- `/docs` decision records, templates and plans
- `/logs` session journals, bug logs and test logs
- `/tools` the governance checker
- `/tests` tests for the checker and hooks

## Running the SQL
In SSMS, against the `Housing Data` database, run the scripts in `sql/` in number order:

1. `01_load_zillow.sql` - loads the Zillow CSVs into tables (only tables that don't exist yet; check the folder path at the top first)
2. `02_dim_metro.sql`, `03_dim_date.sql` - metro and date dimensions
3. `04_fact_home_values.sql`, `05_fact_rent.sql`, `06_fact_market.sql` - fact views
4. `07_analysis.sql` - the business questions (Q1-Q10)

Each script ends with check queries showing the results to expect.

## Governance
The rules for this repo are in [CONSTITUTION.md](CONSTITUTION.md). AI agents start from [CLAUDE.md](CLAUDE.md).
Decisions are recorded in `docs/decisions/`, and every agent session, bug and test is logged in `logs/`.
Run `python3 tools/governance_check.py` to check the repo. The same check runs on GitHub for every change.
`main` is protected on GitHub by the "Protect main" ruleset (setup steps in [docs/github-setup.md](docs/github-setup.md)). AI agents work only in worktrees under `.worktrees/`, never on `main`.

## Findings
_To be added._
