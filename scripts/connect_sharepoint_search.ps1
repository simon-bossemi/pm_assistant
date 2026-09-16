$commonPath = "C:\Agents\pm_assistant\tools\sharepoint_search\sharepoint_search_common.ps1"
. $commonPath

$context = Ensure-SharePointGraphConnection
$config = Get-SharePointSearchConfig

Write-Host "Connected to Microsoft Graph."
Write-Host "Account: $($context.Account)"
Write-Host "Tenant: $($config.TenantHost)"
Write-Host "Scopes: $($config.GraphScopes -join ', ')"

