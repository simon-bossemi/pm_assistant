$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot

py (Join-Path $PSScriptRoot 'build_jira_history.py')
py (Join-Path $PSScriptRoot 'summarize_master_plan_jira.py')

Write-Host 'Jira capture and dashboard facts are ready.'
Write-Host 'Codex must now regenerate sites\master-plan\dist\ai-report.json, validate, build, and privately publish the Site.'
