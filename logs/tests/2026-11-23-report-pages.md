# Test: Four report pages with the navy header theme

## What was tested
The PBIR report in `powerbi/us_housing_market.Report/`: the custom theme `navy_header_theme.json`, the pages Overview, 1 · Growth, 2 · Rent vs price and 3 · Supply (31 visuals), and 26 report measures added to `headline_measures`. Opened in Power BI Desktop 2.159 on the owner's PC.

## How
1. The visual format (`visualContainer` schema 2.14.0) was taken from a visual Power BI saved in this project; the pages and visuals were then written as JSON. Top-N, bottom-N and U.S.-only logic is in DAX measures (`Growth Rank High/Low`, `Top 5/10 Growth`, `Bottom 10 Growth`, `US …`), so no visual needs a hand-written filter.
2. First load: two faults found.
   - The "top 5" chart listed small metros. Cause: their rank is blank, and DAX treats blank as 0, so `blank <= 5` was true. Fixed with `NOT ISBLANK ( r ) && r <= N` in all three top/bottom measures.
   - The rent-to-price change card showed an error. Cause: a variable named `now`, which is the DAX function `NOW`. Renamed to `ratio_now` / `ratio_before`.
3. DAX checks against the open model (Power BI's ADOMD client):
   - The top 5 are Syracuse 6.62%, Bridgeport 6.15%, Milwaukee 5.31%, Hartford 5.13% and Albany 5.04%, the same as SQL (`04_home_value_growth.sql`).
   - `Top 10 Growth` and `Bottom 10 Growth` each return 10 metros. Slowest is Austin, TX. Filtered to Texas, the ranking returns 6 metros.
   - The scatter has 97 points (the large metros that have both changes).
   - U.S. cards: $366,157, +1.19%; $1,932, +2.70%; 6.33%, +0.09 pts. The change colours return `#006300`.
   - `Header Subtitle` is "Zillow metro data · latest month: Sep 2026".
4. Looked at every page on screen:
   - **Overview:** navy header with title, subtitle and page buttons; 3 U.S. cards with green changes; home value vs rent index since Sep 2015 (home value 187.6, rent 163.6); top 5 large metros; takeaways box (text added in Task 13).
   - **1 · Growth:** month, state and metro slicers. The top 10 starts with Syracuse and the bottom 10 with Austin; the trend line shows the U.S. by default. Picking Abilene, TX changed the trend line and left both rankings unchanged, so the "no filter" interactions work. The selection was then cleared.
   - **2 · Rent vs price:** the Azure Maps visual showed "To display Azure Maps visuals, sign in", because Power BI is not signed in on this PC. As the plan allows, it was replaced by a bar chart of the top 20 large metros by rent-to-price, starting with Jackson, MS at 8.31% (same as SQL). The ranking table lists every metro, highest first, and the State column was dropped so the Rent column fits.
   - **3 · Supply:** scatter of inventory change against home value change (97 metros), correlation card 0.30 (SQL: 0.2968), and the U.S. days-to-pending line since 2018.
5. Saved in Power BI. `python tools/governance_check.py`: no problems. `python -m unittest discover -s tests -t .`: OK (1 skipped on Windows).

## Result
PASS

## Bugs
None logged separately: both faults were found and fixed during this task, before the first commit of the report.
