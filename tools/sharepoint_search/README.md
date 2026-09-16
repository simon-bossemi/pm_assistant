# SharePoint Search

This toolset lets PM Assistant search SharePoint sites and documents under:

- `https://bossemi.sharepoint.com/_layouts/15/sharepoint.aspx`

It signs in with Microsoft Graph delegated permissions and scopes searches to the `bossemi.sharepoint.com` tenant.

## One-time setup

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_sharepoint_search.ps1
```

## Sign in

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\connect_sharepoint_search.ps1
```

The script uses device-code sign-in and requests:

- `Sites.Read.All`
- `Files.Read.All`

## Search

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\search_sharepoint.ps1 -Query "NPU compiler"
```

Examples:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\search_sharepoint.ps1 -Query "tensor layout"
powershell -ExecutionPolicy Bypass -File .\scripts\search_sharepoint.ps1 -Query "manual" -EntityType driveItem
powershell -ExecutionPolicy Bypass -File .\scripts\search_sharepoint.ps1 -Query "platform" -EntityType site -Top 20
```

Output is saved under `C:\Agents\pm_assistant\sharepoint_search`.

## List a shared folder directly

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\list_sharepoint_folder.ps1 -ShareUrl "https://bossemi.sharepoint.com/:f:/s/PMSE/IgA8TwLDzkRtSayUAD-ydhf4AT1eqPyZa7DnG9g9q-zK5Ew?e=6Q1wGo"
```

This uses Microsoft sign-in and saves a JSON and Markdown listing for that exact shared folder link.
