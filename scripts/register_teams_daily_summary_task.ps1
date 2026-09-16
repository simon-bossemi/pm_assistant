param(
    [string]$TaskName = "PM Assistant Teams Daily Summary",
    [string]$RunTime = "18:00",
    [ValidateSet("device_code", "client_credentials")]
    [string]$AuthMode = "device_code",
    [string]$Timezone = "Asia/Seoul",
    [int]$MaxChats = 20,
    [int]$PageSize = 50,
    [int]$MaxPagesPerChat = 4,
    [string[]]$ChatId,
    [string]$OutputFile,
    [string]$TenantId = $env:MS_TENANT_ID,
    [string]$ClientId = $env:MS_CLIENT_ID,
    [string]$ClientSecret = $env:MS_CLIENT_SECRET,
    [string]$UserId = $env:MS_USER_ID
)

$scriptPath = "C:\Agents\pm_assistant\scripts\summarize_teams_daily.ps1"
$argumentParts = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", ('"{0}"' -f $scriptPath),
    "-AuthMode", $AuthMode,
    "-Timezone", ('"{0}"' -f $Timezone),
    "-MaxChats", $MaxChats,
    "-PageSize", $PageSize,
    "-MaxPagesPerChat", $MaxPagesPerChat
)

if ($OutputFile) {
    $argumentParts += @("-OutputFile", ('"{0}"' -f $OutputFile))
}

if ($TenantId) {
    $argumentParts += @("-TenantId", ('"{0}"' -f $TenantId))
}

if ($ClientId) {
    $argumentParts += @("-ClientId", ('"{0}"' -f $ClientId))
}

if ($ClientSecret) {
    $argumentParts += @("-ClientSecret", ('"{0}"' -f $ClientSecret))
}

if ($UserId) {
    $argumentParts += @("-UserId", ('"{0}"' -f $UserId))
}

foreach ($id in $ChatId) {
    $argumentParts += @("-ChatId", ('"{0}"' -f $id))
}

$triggerTime = [datetime]::ParseExact($RunTime, "HH:mm", $null)
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument ($argumentParts -join " ")
$trigger = New-ScheduledTaskTrigger -Daily -At $triggerTime
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
Write-Output "Registered task '$TaskName' to run daily at $RunTime."
