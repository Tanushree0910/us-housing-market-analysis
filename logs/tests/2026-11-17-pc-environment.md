# Test: Owner's PC is ready for SQL Server and Power BI work

## What was tested
The tools on the owner's Windows 11 PC that the plan relies on: sqlcmd, SQL Server and Power BI Desktop.

## How
- `sqlcmd -?`: go-sqlcmd v1.10.0. It supports `-b` (exit on error), `-I` (quoted identifiers), `-v` (variables), `-E` (Windows login), `-C` (trust the server certificate) and `-l` (login timeout).
- `sqlcmd -S localhost -E -C -l 5 -Q "SELECT @@SERVERNAME, SERVERPROPERTY('ProductVersion'), SERVERPROPERTY('Edition')"`: server `Tanushree`, version `17.0.1000.7` (SQL Server 2025, so at least 2017 as required), Developer Edition (64-bit).
- `sqlcmd -S . -E -C -l 5 -b -I -v X="hi" -Q "SELECT '$(X)', @@SERVERNAME"`: the `.` name form also connects, and `-v` variables work.
- `sys.dm_server_services`: the SQL Server service runs as `NT Service\MSSQLSERVER`. This matters for Review Focus 1 (can the service read the CSV folder).
- Existing databases: `master`, `tempdb`, `model`, `msdb`, `Housing Data` (the owner's earlier practice database, left untouched). `HousingMarket` does not exist yet.
- Power BI Desktop: Windows uninstall registry entry `Microsoft Power BI Desktop (x64)` version `2.159.883.0`. No preview-feature overrides are stored in the user settings, so the release defaults apply; the PBIP/TMDL/PBIR format is confirmed when the project is opened in Task 10.

**Server name used from here on:** `localhost`. Every sqlcmd call also needs `-C`, because the local instance uses a self-signed certificate.

## Result
PASS

## Bugs
None
