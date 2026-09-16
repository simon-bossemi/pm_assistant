[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$module = Get-ChildItem -Path $env:USERPROFILE -Recurse -Filter "Microsoft.Graph.Authentication.psd1" -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty FullName

if ($module) {
    Write-Host "Microsoft.Graph.Authentication is already installed."
    exit 0
}

Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Scope CurrentUser -Force | Out-Null
Set-PSRepository -Name PSGallery -InstallationPolicy Trusted
Install-Module Microsoft.Graph.Authentication -Scope CurrentUser -Repository PSGallery -Force

Write-Host "Microsoft.Graph.Authentication installed."

