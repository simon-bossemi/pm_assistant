[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("init", "run", "module", "pip", "repl")]
    [string]$Action = "run",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Stop"

$workspaceRoot = Split-Path -Parent $PSScriptRoot
$venvDir = Join-Path $workspaceRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\\python.exe"
$vendorDir = Join-Path $workspaceRoot ".pydeps"

function Get-PythonExe {
    if (Test-Path $venvPython) {
        return $venvPython
    }

    return "py"
}

function Test-VenvPip {
    if (-not (Test-Path $venvPython)) {
        return $false
    }

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $venvPython -m pip --version 1>$null 2>$null
    $ErrorActionPreference = $previousPreference
    return ($LASTEXITCODE -eq 0)
}

function Enter-PythonPath {
    New-Item -ItemType Directory -Force -Path $vendorDir | Out-Null

    if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
        $env:PYTHONPATH = $vendorDir
    } else {
        $env:PYTHONPATH = "$vendorDir;$($env:PYTHONPATH)"
    }
}

function Initialize-Venv {
    New-Item -ItemType Directory -Force -Path $vendorDir | Out-Null

    if (-not (Test-Path $venvPython)) {
        Write-Host "Creating workspace virtual environment at $venvDir"
        try {
            & py -m venv $venvDir
        } catch {
            if (-not (Test-Path $venvPython)) {
                throw
            }
        }
    } else {
        Write-Host "Workspace virtual environment already exists at $venvDir"
    }

    if (Test-VenvPip) {
        Write-Host "Upgrading pip in workspace virtual environment"
        & $venvPython -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to upgrade pip in workspace virtual environment."
        }
    } else {
        Write-Host "Virtual environment was created, but pip is unavailable there on this machine."
        Write-Host "Falling back to workspace-local package installs in $vendorDir"
    }
}

Push-Location $workspaceRoot
try {
    switch ($Action) {
        "init" {
            Initialize-Venv
        }

        "run" {
            if (-not $Args -or $Args.Count -eq 0) {
                throw "Usage: .\\scripts\\pm_python.ps1 run <script.py> [args...]"
            }

            Enter-PythonPath
            $pythonExe = Get-PythonExe
            & $pythonExe @Args
        }

        "module" {
            if (-not $Args -or $Args.Count -eq 0) {
                throw "Usage: .\\scripts\\pm_python.ps1 module <module> [args...]"
            }

            Enter-PythonPath
            $pythonExe = Get-PythonExe
            & $pythonExe -m @Args
        }

        "pip" {
            New-Item -ItemType Directory -Force -Path $vendorDir | Out-Null
            if (Test-VenvPip) {
                & $venvPython -m pip @Args
            } else {
                & py -m pip @Args --target $vendorDir
            }
        }

        "repl" {
            Enter-PythonPath
            $pythonExe = Get-PythonExe
            & $pythonExe
        }
    }
}
finally {
    Pop-Location
}
