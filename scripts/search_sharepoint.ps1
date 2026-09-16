param(
    [Parameter(Mandatory = $true)]
    [string]$Query,

    [ValidateSet("site", "driveItem", "listItem")]
    [string[]]$EntityType = @("site", "driveItem", "listItem"),

    [int]$Top = 10,

    [int]$From = 0,

    [string]$OutputRoot
)

$commonPath = "C:\Agents\pm_assistant\tools\sharepoint_search\sharepoint_search_common.ps1"
. $commonPath

if ($Top -lt 1) {
    throw "-Top must be at least 1."
}

if ($From -lt 0) {
    throw "-From must be 0 or greater."
}

$context = Ensure-SharePointGraphConnection
$config = Get-SharePointSearchConfig

$body = @{
    requests = @(
        @{
            entityTypes = $EntityType
            query       = @{
                queryString   = $Query
                queryTemplate = '({searchTerms}) Path:"https://bossemi.sharepoint.com"'
            }
            from        = $From
            size        = $Top
        }
    )
} | ConvertTo-Json -Depth 10

$response = Invoke-MgGraphRequest -Method POST -Uri "https://graph.microsoft.com/v1.0/search/query" -Body $body -ContentType "application/json"

$records = @()
if ($response.value) {
    foreach ($searchResponse in $response.value) {
        foreach ($container in $searchResponse.hitsContainers) {
            foreach ($hit in $container.hits) {
                $record = Convert-SearchHitToRecord -Hit $hit
                if ($record) {
                    $records += $record
                }
            }
        }
    }
}

$paths = Write-SearchArtifacts -OutputRoot $OutputRoot -Query $Query -EntityTypes $EntityType -Response $response -Records $records

Write-Host "Microsoft Graph account: $($context.Account)"
Write-Host "Tenant scope: $($config.TenantHost)"
Write-Host "Results saved to:"
Write-Host "  $($paths.JsonPath)"
Write-Host "  $($paths.MdPath)"

if ($records.Count -eq 0) {
    Write-Host "No results returned."
    exit 0
}

$records | Select-Object Rank, Type, Name, LastModifiedDate, WebUrl | Format-Table -AutoSize
