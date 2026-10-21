param(
    [Parameter(Mandatory = $true)][string]$DevelopmentWorkbook,
    [Parameter(Mandatory = $true)][string]$DocumentationWorkbook
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
foreach ($source in @($DevelopmentWorkbook, $DocumentationWorkbook)) {
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Workbook not readable: $source" }
}
node (Join-Path $projectRoot 'sites\master-plan\export-source.cjs') $DevelopmentWorkbook $DocumentationWorkbook
if ($LASTEXITCODE -ne 0) { throw 'Worksheet export failed.' }
py (Join-Path $PSScriptRoot 'build_jira_history.py')
if ($LASTEXITCODE -ne 0) { throw 'Jira capture failed.' }
py (Join-Path $PSScriptRoot 'build_doc_controls.py')
if ($LASTEXITCODE -ne 0) { throw 'Documentation and test capture failed.' }
py (Join-Path $PSScriptRoot 'generate_program_report.py')
if ($LASTEXITCODE -ne 0) { throw 'Management report generation failed.' }
Write-Host 'Jira scope, dates, documentation controls and management brief are ready. Validate, build and privately publish the Site through Codex.'
