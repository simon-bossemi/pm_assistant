param(
    [Parameter(Mandatory = $true)]
    [string]$Key
)

$scriptPath = "C:\Agents\pm_assistant\tools\jira_search\jira_search.py"
py $scriptPath issue --key $Key
exit $LASTEXITCODE

