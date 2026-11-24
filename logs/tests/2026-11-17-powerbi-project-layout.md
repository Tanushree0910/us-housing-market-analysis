# Test: Checker allows Power BI project folders

## What was tested
The layout check in `tools/governance_check.py` after allowing `.pbip` files and the `snake_case.SemanticModel/` and `snake_case.Report/` folders in `powerbi/`. New tests: `test_powerbi_project_files_allowed`, `test_powerbi_unknown_subfolder_flagged`, `test_powerbi_bad_project_name_flagged`, `test_powerbi_other_file_type_flagged`.

## How
Ran `python3 -m unittest tests.test_governance_check` before the change: `test_powerbi_project_files_allowed` failed, as expected. After the change, ran `python3 tools/governance_check.py` and `python3 -m unittest discover -s tests -t .`.

## Result
PASS

## Bugs
None
