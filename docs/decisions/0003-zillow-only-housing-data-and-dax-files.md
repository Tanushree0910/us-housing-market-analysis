# 0003: Zillow only, the Housing Data database, and .dax files in powerbi/ (constitution v1.2)

## Date
2026-11-19

## Status
Accepted

## Decision
- Build all SQL on the **Housing Data** database. The HousingMarket database is left untouched.
- Use **Zillow data only**. Redfin is dropped. The Redfin tables and the `map_redfin_metro` view stay in the database unused, until the owner decides to remove them.
- README question 3 now uses Zillow for-sale inventory and mean days to pending. Both files were added to `data/`.
- SQL scripts are numbered in run order (`01_load_zillow.sql` to `07_analysis.sql`).
- **Amend Article 3** so `powerbi/` also accepts `snake_case.dax` measure files next to the report. The constitution moves to version 1.2.

## Reason
- The owner's scripts, analysis queries and Power BI measures were all built on Housing Data. Keeping it avoids rewriting them.
- Without Redfin, Zillow's inventory and days-to-pending data still answers the README's third question.
- The owner keeps their Power BI measures in a `.dax` file. The measures belong next to the report they serve.

## Alternatives
- **The HousingMarket database:** it already held all four Zillow data sets. Rejected, because none of the owner's scripts or report used it, so everything would have needed rewriting.
- **Keeping Redfin:** the owner chose not to use it.
- **Moving the measures to `docs/powerbi-measures.dax`, with no rule change:** rejected in favour of keeping the measures with the report.
