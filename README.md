# PM Assistant Email Setup

This workspace now sends mail through the Outlook desktop app installed on this PC. It uses your signed-in Outlook profile, so no SMTP configuration is needed.

## File

- `send-email.ps1`: creates an Outlook draft or sends directly through Outlook

## Usage

Open a draft to Simon:

```powershell
.\send-email.ps1 -Subject "Test email" -Body "Hello Simon"
```

Send immediately through Outlook:

```powershell
.\send-email.ps1 -Subject "Project update" -Body "Hello Simon, here is the latest update." -Send
```

Use a body file:

```powershell
.\send-email.ps1 -Subject "Weekly summary" -BodyFile ".\summary.txt"
```

Add recipients or attachments:

```powershell
.\send-email.ps1 -To "someone@example.com" -Cc "team@example.com" -Subject "Hello" -Body "Test" -Attachments ".\report.pdf"
```

## Notes

- Outlook desktop must be installed and signed in
- Without `-Send`, the script opens a draft for review
- The default recipient is `simon.jacqmart@bos-semi.com`

## Python Helper

Python is available on this machine through the `py` launcher even though the `python` app alias is not enabled.
Use the helper below to avoid that mismatch and prefer the workspace virtual environment automatically.
If the local virtual environment cannot manage packages cleanly, the helper falls back to installing packages into a workspace-local `.pydeps` folder.

## File

- `scripts/pm_python.ps1`: initializes and runs Python using `.venv` when available

## Usage

Create or refresh the workspace virtual environment:

```powershell
.\scripts\pm_python.ps1 init
```

Run a Python script with the workspace environment:

```powershell
.\scripts\pm_python.ps1 run .\tools\confluence_crawler\confluence_crawler.py --help
```

Run a Python module:

```powershell
.\scripts\pm_python.ps1 module pip --version
```

Install packages into the workspace virtual environment:

```powershell
.\scripts\pm_python.ps1 pip install requests
```

## Teams Graph Reader

This workspace includes a read-only Microsoft Teams helper that uses Microsoft Graph with an approved Entra app. It does not bypass tenant policy and still requires IT-approved permissions.

## Files

- `scripts/read_teams.ps1`
- `tools/teams_graph/teams_graph_reader.py`

## Usage

List your chats with device code sign-in:

```powershell
.\scripts\read_teams.ps1 -Command list-chats -AuthMode device_code -TenantId "<tenant-id>" -ClientId "<client-id>"
```

List messages from one chat:

```powershell
.\scripts\read_teams.ps1 -Command list-messages -AuthMode device_code -TenantId "<tenant-id>" -ClientId "<client-id>" -ChatId "<chat-id>"
```

Use app-only auth after IT grants application permissions:

```powershell
.\scripts\read_teams.ps1 -Command list-chats -AuthMode client_credentials -TenantId "<tenant-id>" -ClientId "<client-id>" -ClientSecret "<secret>" -UserId "<user-id>" -Output json
```

## Teams Daily Summary

Generate a markdown summary for one day of Teams conversations:

```powershell
.\scripts\summarize_teams_daily.ps1 -AuthMode device_code -Date "2026-06-11" -TenantId "<tenant-id>" -ClientId "<client-id>"
```

The script writes a markdown file like `outputs\teams_daily_summary_2026-06-11.md`.

If `OPENAI_API_KEY` is set, it uses OpenAI to produce a tighter summary. Otherwise it generates a simple extractive digest from the captured messages.
