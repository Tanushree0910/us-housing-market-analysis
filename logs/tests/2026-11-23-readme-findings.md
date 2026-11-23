# Test: README findings and dashboard takeaways match the validated numbers

## What was tested
The rewritten `README.md` (findings per question, screenshots, how it works, how to run it, skills shown, data) and the six takeaways on the dashboard's Overview page.

## How
1. Listed every number quoted in the README and takeaways, and checked that each one has a check in `sql/99_validation_checks.sql` that compares SQL with a value computed separately from the raw CSVs in Python:
   - U.S. index since Sep 2015: home value 187.60 (+88%), rent 163.63 (+64%).
   - U.S. 1-year changes: home value +1.19%, rent +2.70%.
   - U.S. rent-to-price 6.33% now and 6.24% a year earlier, so +0.09 points.
   - Fastest and slowest large metros: Syracuse +6.62%, Austin −4.31%.
   - 4 of the top 5 are in NY or CT; 7 of the bottom 10 are in TX or FL.
   - Rent-to-price extremes: Jackson 8.31%, San Jose 3.00%.
   - Correlations: inventory r = 0.2968 (shown as 0.30) and days to pending r = 0.0624 (shown as 0.06).
   - U.S. days to pending: 56, up 2.
   - Large metros: 99 regions, 97 with home values.
2. Added 5 checks while doing this (4 for the takeaways, 1 for the rent-to-price a year earlier). Each value was computed in Python first. These checks guard results that already existed, so they passed on their first run.
3. `sqlcmd -S localhost -E -C -b -I -i sql/99_validation_checks.sql`: 58 checks, all PASS, exit 0. The README states 58; an earlier draft said 69 by mistake and was corrected before commit.
4. Every relative link in the README points to a file that exists.
5. `python tools/governance_check.py`: no problems. `python -m unittest discover -s tests -t .`: OK (1 skipped on Windows).

## Result
PASS

## Bugs
None
