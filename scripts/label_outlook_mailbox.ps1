param(
    [datetime]$StartDate = ((Get-Date).Date.AddDays(-((([int](Get-Date).DayOfWeek + 6) % 7)))),
    [datetime]$EndDate = (Get-Date).Date.AddDays(1),
    [string]$FolderName = "Inbox",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Ensure-Category {
    param(
        $Categories,
        [string]$Name,
        [int]$Color = 0
    )

    foreach ($category in $Categories) {
        if ($category.Name -eq $Name) {
            return
        }
    }

    $null = $Categories.Add($Name, $Color)
}

function Remove-CategoryIfPresent {
    param(
        $Categories,
        [string]$Name
    )

    foreach ($category in $Categories) {
        if ($category.Name -eq $Name) {
            $category.Remove()
            return
        }
    }
}

function Get-MailLabel {
    param(
        [string]$Subject,
        [string]$SenderName
    )

    if ($null -eq $Subject) { $Subject = "" }
    if ($null -eq $SenderName) { $SenderName = "" }
    $text = (($Subject + " " + $SenderName).ToLowerInvariant())

    if ($text -match "bos-installer|installer") { return "Installer" }
    if ($text -match "quantization|pttm-484|pttm-323|nsdt-1691|bos-1107") { return "Quantization" }
    if ($text -match "fc rc5\.1|release repack|internal milestone testing|package rel[e|a]se") { return "Release-RC5" }
    if ($text -match "bmw|rivian|chery|nxp|bos-1108|bos-1109|bos-1110|support call|adas soc|trinity|eagle-n a0|f2f - ar status") { return "Customer" }
    if ($text -match "agenda|weekly report|weekly action items|weekly update|deep-dive|meeting deck") { return "Meetings" }
    if ($text -match "teams|sent a message|message, 1 mention|new messages in teams|new activity in teams") { return "Chat" }
    if ($text -match "llk|resnet|scope and planning|project management scope") { return "Internal-Tech" }
    if ($text -match "newsletter|copilot ai credits|monthly goal updates|daily digest|atlassian|cb insights") { return "Admin" }
    return "General"
}

$outlook = New-Object -ComObject Outlook.Application
$namespace = $outlook.GetNamespace("MAPI")
$masterCategories = $namespace.Categories

Ensure-Category -Categories $masterCategories -Name "Customer" -Color 1
Ensure-Category -Categories $masterCategories -Name "Meetings" -Color 2
Ensure-Category -Categories $masterCategories -Name "Admin" -Color 3
Ensure-Category -Categories $masterCategories -Name "Installer" -Color 4
Ensure-Category -Categories $masterCategories -Name "Quantization" -Color 5
Ensure-Category -Categories $masterCategories -Name "Release-RC5" -Color 6
Ensure-Category -Categories $masterCategories -Name "Internal-Tech" -Color 7
Ensure-Category -Categories $masterCategories -Name "Chat" -Color 8
Ensure-Category -Categories $masterCategories -Name "General" -Color 9

$folder = $namespace.GetDefaultFolder(6)

if ($FolderName -ne "Inbox") {
    $folder = $folder.Folders.Item($FolderName)
    if (-not $folder) {
        throw "Folder '$FolderName' was not found under Inbox."
    }
}

$items = $folder.Items
$items.Sort("[ReceivedTime]", $true)

$processed = 0
$updated = 0
$counts = @{}

foreach ($item in $items) {
    if (-not $item -or $item.Class -ne 43) {
        continue
    }

    $received = [datetime]$item.ReceivedTime
    if ($received -lt $StartDate) {
        break
    }

    if ($received -ge $EndDate) {
        continue
    }

    $processed++
    $label = Get-MailLabel -Subject $item.Subject -SenderName $item.SenderName
    if (-not $counts.ContainsKey($label)) {
        $counts[$label] = 0
    }
    $counts[$label]++

    if ($item.Categories -ne $label) {
        if (-not $DryRun) {
            $item.Categories = $label
            $item.Save()
        }
        $updated++
    }
}

"FOLDER=$FolderName"
"START=$($StartDate.ToString("yyyy-MM-dd HH:mm"))"
"END=$($EndDate.ToString("yyyy-MM-dd HH:mm"))"
"PROCESSED=$processed"
"UPDATED=$updated"
$counts.GetEnumerator() | Sort-Object Name | ForEach-Object { "{0}={1}" -f $_.Name, $_.Value }

Remove-CategoryIfPresent -Categories $masterCategories -Name "ThisWeek"
