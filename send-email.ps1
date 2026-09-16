param(
    [Parameter(Mandatory = $true)]
    [string]$Subject,

    [string]$Body,

    [string]$BodyFile,

    [string]$To = "simon.jacqmart@bos-semi.com",

    [string]$Cc,

    [string]$Bcc,

    [string[]]$Attachments,

    [switch]$Send
)

if (-not $Body -and -not $BodyFile) {
    throw "Provide -Body or -BodyFile."
}

if ($BodyFile) {
    $resolvedBodyFile = Resolve-Path -LiteralPath $BodyFile -ErrorAction Stop
    $Body = Get-Content -LiteralPath $resolvedBodyFile -Raw -Encoding UTF8
}

try {
    $outlook = New-Object -ComObject Outlook.Application
} catch {
    throw "Could not open Outlook through COM automation. Make sure Outlook desktop is installed and signed in."
}

$mail = $outlook.CreateItem(0)
$mail.To = $To
$mail.Subject = $Subject
$mail.Body = $Body

if ($Cc) {
    $mail.CC = $Cc
}

if ($Bcc) {
    $mail.BCC = $Bcc
}

if ($Attachments) {
    foreach ($attachment in $Attachments) {
        $resolvedAttachment = Resolve-Path -LiteralPath $attachment -ErrorAction Stop
        [void]$mail.Attachments.Add($resolvedAttachment.Path)
    }
}

if ($Send) {
    $mail.Send()
    Write-Host "Email sent to $To through Outlook."
} else {
    $mail.Display()
    Write-Host "Outlook draft opened for $To."
}
