# Test: .pbix copy and dashboard screenshots

## What was tested
`powerbi/us_housing_market.pbix` (File → Save as → Power BI file, from the saved project) and the four page screenshots in `screenshots/`.

## How
1. Saved the project as `powerbi/us_housing_market.pbix`: 8,285,998 bytes (8.3 MB), under the 50 MB limit (Article 3).
2. Collapsed the Data, Visualizations and Filters panes, then captured each page.
   - First attempt: a full-screen grab, auto-cropped to the navy header. It came out cut off on the right. Cause: the Claude app window sits on top of part of the Power BI window on the owner's screen.
   - Final method: capture the Power BI window itself with the Windows `PrintWindow` API (flag 2, full content), which draws the window even when something covers it. A Python PIL script then crops it to the report page (the navy header's left and right edges, at 1280:720).
3. Looked at each image: `overview.png`, `growth.png`, `rent-vs-price.png` and `supply.png` are each 1326 × 746 pixels, sharp, not cut off, and show the expected numbers (U.S. $366,157 / $1,932 / 6.33%, Syracuse 6.62%, Austin −4.31%, Jackson 8.31%, r = 0.30). The Overview capture already includes the final takeaways (Task 13 step 1), so it does not need a second capture.
4. `python tools/governance_check.py`: no problems (names match Article 3). `python -m unittest discover -s tests -t .`: OK (1 skipped on Windows).

## Result
PASS

## Bugs
None
