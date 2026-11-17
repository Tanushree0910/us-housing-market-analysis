# 0003: Agents add the owner's downloaded data files and handle git

## Date
2026-11-17

## Status
Accepted

## Decision
The owner chooses and downloads raw data. An agent may copy a file the owner downloaded into `data/` unchanged, under its original name, record it in `data/SOURCES.md`, and commit, push and pull it with git. Existing raw files stay read-only. CONSTITUTION.md Article 2 gains this rule (version 1.2), and `CLAUDE.md` "Adding raw data" is updated to match.

## Reason
The owner asked for it. They want to find and download the data themselves, but not to upload files to GitHub by hand. The agent works on the owner's PC through the Claude desktop app's computer connection and uses git there, so downloaded files, the `.pbix` and the screenshots can be pushed without the owner's help.

## Alternatives
- The owner uploads every new file through the GitHub website: this was the old rule. It was rejected because the owner wants the agent to do the git work.
- The agent downloads data from Zillow itself: Zillow's file host is blocked from the cloud session, and the owner wants to choose and download the data themselves.
