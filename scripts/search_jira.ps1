param(
    [Parameter(Mandatory = $true)]
    [string]$Jql,

    [int]$MaxResults = 25
)

$scriptPath = "C:\Agents\pm_assistant\tools\jira_search\jira_search.py"
py $scriptPath search --jql $Jql --max-results $MaxResults
exit $LASTEXITCODE
