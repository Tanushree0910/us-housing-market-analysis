# 0003: Keep the Power BI report as a Power BI Project plus a .pbix copy

## Date
2026-11-17

## Status
Accepted

## Decision
Store the dashboard in `powerbi/` as a Power BI Project: `us_housing_market.pbip` with the `us_housing_market.SemanticModel/` and `us_housing_market.Report/` folders Power BI Desktop creates. Also keep a `us_housing_market.pbix` copy so anyone can open the report in one click. CONSTITUTION.md Article 3 is amended to allow these two sub-folders in `powerbi/` (version 1.1), and the checker enforces it. Power BI's local files `.pbi/localSettings.json` and `.pbi/cache.abf` are git-ignored.

## Reason
The owner chose this option. The project format is plain text, so the agent can write the data model and report directly, which is faster and more reliable than building the report by operating Power BI on screen. Hiring managers can also read the model and formulas on GitHub.

## Alternatives
- A `.pbix` file only, built by operating Power BI Desktop on screen: fits the old rules, but is slow and error-prone, and GitHub cannot show what is inside the file.
