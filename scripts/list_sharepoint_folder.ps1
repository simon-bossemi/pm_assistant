param(
    [Parameter(Mandatory = $true)]
    [string]$ShareUrl,

    [string]$OutputRoot = "C:\Agents\pm_assistant\sharepoint_search"
)

$scriptPath = "C:\Agents\pm_assistant\tools\sharepoint_search\sharepoint_shared_folder.py"
py $scriptPath --share-url $ShareUrl --output-root $OutputRoot
exit $LASTEXITCODE
