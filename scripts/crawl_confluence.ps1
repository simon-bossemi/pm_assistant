param(
    [string]$SpaceKey,
    [string]$AncestorId,
    [string[]]$PageId,
    [int]$MaxPages,
    [double]$DelaySeconds,
    [string]$OutputRoot
)

$scriptPath = "C:\Agents\pm_assistant\tools\confluence_crawler\confluence_crawler.py"
$arguments = @($scriptPath)

if ($SpaceKey) {
    $arguments += @("--space-key", $SpaceKey)
}

if ($AncestorId) {
    $arguments += @("--ancestor-id", $AncestorId)
}

if ($PageId) {
    foreach ($value in $PageId) {
        $arguments += @("--page-id", $value)
    }
}

if ($PSBoundParameters.ContainsKey("MaxPages")) {
    $arguments += @("--max-pages", $MaxPages.ToString())
}

if ($PSBoundParameters.ContainsKey("DelaySeconds")) {
    $arguments += @("--delay-seconds", $DelaySeconds.ToString())
}

if ($OutputRoot) {
    $arguments += @("--output-root", $OutputRoot)
}

py @arguments
exit $LASTEXITCODE
