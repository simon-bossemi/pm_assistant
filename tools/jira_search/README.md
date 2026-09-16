# Jira Search

This toolset lets PM Assistant query Jira projects and tickets available to the configured Atlassian account.

Base URL:

- `https://bos-semi.atlassian.net`

## List accessible projects

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\list_jira_projects.ps1
```

## Search issues

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\search_jira.ps1 -Jql "text ~ \"Tenstorrent\" order by updated DESC"
```

## Read one ticket in detail

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\get_jira_issue.ps1 -Key PTTM-158
```

## Create a ticket

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\create_jira_issue.ps1 -ProjectKey PTTM -IssueType Task -Summary "Example ticket" -Description "Created by PM Assistant"
```

Examples:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\search_jira.ps1 -Jql "assignee = currentUser() order by updated DESC"
powershell -ExecutionPolicy Bypass -File .\scripts\search_jira.ps1 -Jql "project = BOS AND statusCategory != Done order by updated DESC" -MaxResults 25
```

Output is written under `C:\Agents\pm_assistant\jira`.
