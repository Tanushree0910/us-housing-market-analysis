# 0004: Use Zillow data only; drop Redfin

## Date
2026-11-17

## Status
Accepted

## Decision
The analysis uses four Zillow Research files only: home values (ZHVI), rents (ZORI), For-Sale Inventory and Days to Pending, all at metro level, monthly and smoothed. Redfin data is not used. README question 3 ("How do inventory and days on market relate to price changes?") is answered with Zillow's For-Sale Inventory and Days to Pending files. The owner downloaded both new files and they were added to `data/` unchanged.

Because the two new files run one month further (to 2026-10-31) than the home-value file, the analysis window ends at the latest home-value month, 2026-09-30, for every measure.

## Reason
The owner chose it (design doc, 2026-11-17). All four files share Zillow's region IDs, names and wide layout, so one loader and one metro list cover everything. Redfin uses different region names and a long format, so joining it to Zillow would need a fuzzy name match that could silently pair the wrong metros.

## Alternatives
- Redfin market tracker and price-drop files: rejected for the join risk above and because they add a second data model to explain.
- Keep October 2026 for the supply measures only: rejected so every page and headline number refers to the same latest month.
