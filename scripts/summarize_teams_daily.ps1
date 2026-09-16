param(
    [ValidateSet("device_code", "client_credentials")]
    [string]$AuthMode = "device_code",
    [string]$Date = (Get-Date -Format "yyyy-MM-dd"),
    [string]$Timezone = "Asia/Seoul",
    [int]$MaxChats = 20,
    [int]$PageSize = 50,
    [int]$MaxPagesPerChat = 4,
    [string[]]$ChatId,
    [string]$OutputFile,
    [string]$TenantId,
    [string]$ClientId,
    [string]$ClientSecret,
    [string]$UserId
)

$scriptPath = "C:\Agents\pm_assistant\tools\teams_graph\teams_daily_summary.py"
$args = @(
    $scriptPath,
    "--auth-mode", $AuthMode,
    "--date", $Date,
    "--timezone", $Timezone,
    "--max-chats", $MaxChats,
    "--page-size", $PageSize,
    "--max-pages-per-chat", $MaxPagesPerChat
)

if ($OutputFile) {
    $args += @("--output-file", $OutputFile)
}

if ($TenantId) {
    $args += @("--tenant-id", $TenantId)
}

if ($ClientId) {
    $args += @("--client-id", $ClientId)
}

if ($ClientSecret) {
    $args += @("--client-secret", $ClientSecret)
}

if ($UserId) {
    $args += @("--user-id", $UserId)
}

foreach ($id in $ChatId) {
    $args += @("--chat-id", $id)
}

& py @args
exit $LASTEXITCODE
