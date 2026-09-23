$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$workbook = Join-Path $projectRoot 'work_notes\linked-master-plan.xlsx'
$sourceWorkbook = $null
$oneDriveRoots = Get-ChildItem -LiteralPath $env:USERPROFILE -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'OneDrive - *' }
foreach ($oneDriveRoot in $oneDriveRoots) {
    $candidate = Get-ChildItem -LiteralPath $oneDriveRoot.FullName -Recurse -File -Filter 'Eagle-N B0 SW Master Plan-SyncupVer.xlsx' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($candidate) { $sourceWorkbook = $candidate.FullName; break }
}
if (-not $sourceWorkbook) { throw 'The linked SharePoint workbook was not found in the synced OneDrive folders.' }
Copy-Item -LiteralPath $sourceWorkbook -Destination $workbook -Force
node (Join-Path $projectRoot 'sites\master-plan\export-source.cjs') $workbook

py (Join-Path $PSScriptRoot 'build_jira_history.py')
py (Join-Path $PSScriptRoot 'build_doc_controls.py')
py (Join-Path $PSScriptRoot 'summarize_master_plan_jira.py')
py (Join-Path $PSScriptRoot 'generate_ai_report.py')

Write-Host 'Jira capture and dashboard facts are ready.'
Write-Host 'Codex must now validate, build, and privately publish the Site.'
