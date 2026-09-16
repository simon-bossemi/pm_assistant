# Confluence Crawler

This is the PM Assistant copy of the Confluence crawler used in `review_engineer`.

## Config

The crawler is already configured for:

- `https://bos-semi.atlassian.net/wiki`
- Atlassian account `simon.jacqmart@bos-semi.com`
- output root `C:\Agents\pm_assistant\wiki`

Credentials are stored in `tools\confluence_crawler\.env`.

## Run

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\crawl_confluence.ps1
```

Optional filters:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\crawl_confluence.ps1 -SpaceKey ENG -MaxPages 50
```

Single page:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\crawl_confluence.ps1 -PageId 123456789
```

