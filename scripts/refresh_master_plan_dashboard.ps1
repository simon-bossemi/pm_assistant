$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$workbook = Join-Path $projectRoot 'work_notes\linked-master-plan.xlsx'
$sourceWorkbook = 'C:\Users\SimonJacqmart\OneDrive - 보스반도체\PM_SE 팀 - Documents\Project Mgmt\Project\N1 B0\Eagle-N B0 SW Master Plan-SyncupVer.xlsx'
if (-not (Test-Path -LiteralPath $sourceWorkbook)) { throw "The linked SharePoint workbook was not found: $sourceWorkbook" }
Copy-Item -LiteralPath $sourceWorkbook -Destination $workbook -Force
node (Join-Path $projectRoot 'sites\master-plan\export-source.cjs') $workbook

py (Join-Path $PSScriptRoot 'build_jira_history.py')
py (Join-Path $PSScriptRoot 'build_doc_controls.py')
py (Join-Path $PSScriptRoot 'summarize_master_plan_jira.py')

Write-Host 'Jira capture and dashboard facts are ready.'
Write-Host 'Codex must now regenerate sites\master-plan\dist\ai-report.json, validate, build, and privately publish the Site.'
