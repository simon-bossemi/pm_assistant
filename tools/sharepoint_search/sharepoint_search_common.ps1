$script:SharePointSearchConfig = @{
    TenantHost        = "bossemi.sharepoint.com"
    SharePointHomeUrl = "https://bossemi.sharepoint.com/_layouts/15/sharepoint.aspx"
    GraphScopes       = @("Sites.Read.All", "Files.Read.All")
    DefaultEntityType = @("site", "driveItem", "listItem")
    DefaultOutputRoot = "C:\Agents\pm_assistant\sharepoint_search"
}

function Get-SharePointSearchConfig {
    return $script:SharePointSearchConfig
}

function Import-GraphAuthenticationModule {
    if (Get-Command Connect-MgGraph -ErrorAction SilentlyContinue) {
        return
    }

    $manifest = Get-ChildItem -Path $env:USERPROFILE -Recurse -Filter "Microsoft.Graph.Authentication.psd1" -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName

    if (-not $manifest) {
        throw "Microsoft.Graph.Authentication is not installed. Run .\scripts\setup_sharepoint_search.ps1 first."
    }

    Import-Module $manifest -Force
}

function Ensure-SharePointGraphConnection {
    param(
        [switch]$ForceLogin
    )

    Import-GraphAuthenticationModule

    $config = Get-SharePointSearchConfig
    $context = Get-MgContext -ErrorAction SilentlyContinue
    $needsLogin = $ForceLogin -or -not $context -or $context.AuthType -ne "Delegated"

    if (-not $needsLogin) {
        foreach ($scope in $config.GraphScopes) {
            if ($context.Scopes -notcontains $scope) {
                $needsLogin = $true
                break
            }
        }
    }

    if ($needsLogin) {
        Connect-MgGraph -Scopes $config.GraphScopes -ContextScope CurrentUser -UseDeviceCode -NoWelcome | Out-Null
        $context = Get-MgContext -ErrorAction SilentlyContinue
    }

    if (-not $context) {
        throw "Microsoft Graph sign-in did not complete."
    }

    return $context
}

function Convert-SearchSummary {
    param(
        [string]$Summary
    )

    if (-not $Summary) {
        return ""
    }

    $cleaned = $Summary -replace "<c\d+>", "" -replace "</c\d+>", "" -replace "<ddd/>", "..." -replace "<[^>]+>", " "
    return (($cleaned -split "\s+") -join " ").Trim()
}

function Convert-SearchHitToRecord {
    param(
        [psobject]$Hit
    )

    $resource = $Hit.resource
    if (-not $resource) {
        return $null
    }

    $displayName = $resource.name
    if (-not $displayName -and $resource.displayName) {
        $displayName = $resource.displayName
    }
    if (-not $displayName -and $resource.fields -and $resource.fields.title) {
        $displayName = $resource.fields.title
    }
    if (-not $displayName) {
        $displayName = $Hit.hitId
    }

    $odataType = $resource.'@odata.type'
    if ($odataType) {
        $odataType = $odataType -replace '^#microsoft\.graph\.', ''
    } else {
        $odataType = "unknown"
    }

    [pscustomobject]@{
        Rank             = $Hit.rank
        Type             = $odataType
        Name             = $displayName
        WebUrl           = $resource.webUrl
        Summary          = Convert-SearchSummary -Summary $Hit.summary
        LastModifiedDate = $resource.lastModifiedDateTime
        HitId            = $Hit.hitId
    }
}

function New-SearchArtifactPaths {
    param(
        [string]$OutputRoot,
        [string]$Query
    )

    if (-not $OutputRoot) {
        $OutputRoot = (Get-SharePointSearchConfig).DefaultOutputRoot
    }

    New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $slug = ($Query.ToLowerInvariant() -replace '[^a-z0-9]+', '-').Trim('-')
    if (-not $slug) {
        $slug = "query"
    }

    return @{
        JsonPath = Join-Path $OutputRoot "$timestamp-$slug.json"
        MdPath   = Join-Path $OutputRoot "$timestamp-$slug.md"
    }
}

function Write-SearchArtifacts {
    param(
        [string]$OutputRoot,
        [string]$Query,
        [string[]]$EntityTypes,
        [psobject]$Response,
        [object[]]$Records
    )

    $paths = New-SearchArtifactPaths -OutputRoot $OutputRoot -Query $Query
    $config = Get-SharePointSearchConfig

    $jsonPayload = [pscustomobject]@{
        tenant_host  = $config.TenantHost
        sharepoint   = $config.SharePointHomeUrl
        query        = $Query
        entity_types = $EntityTypes
        response     = $Response
    }
    $jsonPayload | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $paths.JsonPath -Encoding UTF8

    $lines = @(
        "# SharePoint Search Results",
        "",
        "- Tenant: $($config.TenantHost)",
        "- Query: $Query",
        "- Entity types: $($EntityTypes -join ', ')",
        "- Result count: $($Records.Count)",
        ""
    )

    if ($Records.Count -eq 0) {
        $lines += "- No results returned."
    } else {
        $lines += "## Results"
        foreach ($record in $Records) {
            $lines += ""
            $lines += "### [$($record.Type)] $($record.Name)"
            $lines += "- Rank: $($record.Rank)"
            if ($record.LastModifiedDate) {
                $lines += "- Last modified: $($record.LastModifiedDate)"
            }
            if ($record.WebUrl) {
                $lines += "- URL: $($record.WebUrl)"
            }
            if ($record.Summary) {
                $lines += "- Summary: $($record.Summary)"
            }
        }
    }

    Set-Content -LiteralPath $paths.MdPath -Value ($lines -join "`r`n") -Encoding UTF8
    return $paths
}
