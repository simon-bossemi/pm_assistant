param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("list-chats", "list-messages")]
    [string]$Command,

    [ValidateSet("device_code", "client_credentials")]
    [string]$AuthMode = "device_code",

    [string]$ChatId,
    [int]$Top = 10,
    [ValidateSet("json", "table")]
    [string]$Output = "table",
    [string]$TenantId,
    [string]$ClientId,
    [string]$ClientSecret,
    [string]$UserId
)

$scriptPath = "C:\Agents\pm_assistant\tools\teams_graph\teams_graph_reader.py"
$args = @(
    $scriptPath,
    "--auth-mode", $AuthMode,
    "--top", $Top,
    "--output", $Output,
    $Command
)

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

if ($ChatId) {
    $args += @("--chat-id", $ChatId)
}

& py @args
exit $LASTEXITCODE
