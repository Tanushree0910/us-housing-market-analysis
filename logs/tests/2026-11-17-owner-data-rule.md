# Test: Repo checks after the raw-data rule change

## What was tested
The repo after amending CONSTITUTION.md Article 2 (version 1.2: agents may add files the owner downloaded, unchanged, and handle git), updating `CLAUDE.md`, adding decision 0003, and updating the design doc and plan for git on the owner's PC. Also confirmed that the cloud session cannot reach Zillow's file host (`files.zillowstatic.com` is refused by the network proxy), which is why the files travel through git on the PC.

## How
`python3 tools/governance_check.py` and `python3 -m unittest discover -s tests -t .`

## Result
PASS

## Bugs
None
