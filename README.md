# U.S. Housing Market Analysis

SQL Server + Power BI analysis of home values, rents and market conditions across U.S. metros.

## Questions this project answers
- Which metros have grown fastest year over year?
- Where is the rent-to-price ratio highest?
- How do inventory and days on market relate to price changes?

## Data
- Zillow Research: ZHVI (home values) and ZORI (rents), metro level, monthly
- Redfin Data Center: Housing Market Tracker, metro level

## Tools
SQL Server, SSMS, Power BI Desktop

## Repo structure
- `/data` raw source files
- `/sql` queries and views
- `/powerbi` Power BI report: project files (.pbip) and a .pbix copy
- `/screenshots` dashboard images
- `/docs` decision records, templates and plans
- `/logs` session journals, bug logs and test logs
- `/tools` the governance checker
- `/tests` tests for the checker and hooks

## Governance
The rules for this repo are in [CONSTITUTION.md](CONSTITUTION.md). AI agents start from [CLAUDE.md](CLAUDE.md).
Decisions are recorded in `docs/decisions/`, and every agent session, bug and test is logged in `logs/`.
Run `python3 tools/governance_check.py` to check the repo. The same check runs on GitHub for every change.

## Findings
_To be added._
