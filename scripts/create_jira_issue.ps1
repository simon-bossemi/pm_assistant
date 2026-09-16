param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectKey,

    [Parameter(Mandatory = $true)]
    [string]$IssueType,

    [Parameter(Mandatory = $true)]
    [string]$Summary,

    [Parameter(Mandatory = $true)]
    [string]$Description
)

$scriptPath = "C:\Agents\pm_assistant\tools\jira_search\jira_search.py"
py $scriptPath create --project-key $ProjectKey --issue-type $IssueType --summary $Summary --description $Description
exit $LASTEXITCODE
