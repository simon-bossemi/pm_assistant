# Eagle-N B0 program control dashboard

Private Sites project: `appgprj_6aaa4125c9008191b9e05460b44f7875`.

The dashboard counts **unique Jira tickets**, never workbook rows. Its population is every Jira key in the first worksheet of `Eagle-N B0 SW Dev. Master Plan.xlsx` plus the `Eagle-N B0 Doc Delivery Plan` worksheet of `Eagle-N B0 SW Master Plan-SyncupVer.xlsx`. The two SharePoint workbooks define ticket membership, Level 1 categories and writing/review relationships. Jira issue detail and changelog provide current status, owner, P-D Due Date, Emulator Validation Due Date, comments and weekly history. A repeated ticket counts once globally, but can appear in two Level 1 cohorts when the source plan places it in both.

This public code mirror excludes the refreshed October 2026 workbook/Jira JSON and original workbook bytes. Run the on-request refresh locally before building a current dashboard. Older data files remain in the repository and its history; they require separate cleanup.

## On-request refresh

There is no scheduled capture or in-site Jira refresh. When Simon requests a refresh:

1. Obtain the current two SharePoint workbooks. Prefer the local synchronized development copy. Fetch the documentation workbook if its synchronized copy is locked. Do not modify either source workbook.
2. Run `scripts/refresh_master_plan_dashboard.ps1 -DevelopmentWorkbook <path> -DocumentationWorkbook <path>` from `C:\Agents\pm_assistant`. The script exports the exact tabs, queries each scoped Jira ticket and its changelog, checks document review pairs and ITCP-47 test requests, and generates the management brief.
3. Run `py -3 sites/master-plan/verify-current-scope.py` and JavaScript syntax checks, then `node sites/master-plan/build.cjs`.
4. Review the dashboard in a local preview, push the exact Site source, package it and deploy to the existing owner-private Site. Mirror agent/scripts/Site source to `simon-bossemi/pm_assistant` without input/output workbooks or generated private reports.

Refresh statistics and source provenance for 2026-10-21 are in `work_notes/master-plan-scope-refresh-2026-10-21.md`.

## Interpretation

- P-D Due Date and Emulator Validation Due Date are **targets**, not actual completion dates. Jira P-D status is a separate milestone and does not prove emulator validation.
- Weekly history replays each issue's creation and status transitions. Level 1 category membership comes from the current worksheets and is applied retrospectively, so it is not a historical record of category changes.
- The first tab's seven emulator target dates reconcile to five Jira dates. The other two are visible as workbook/Jira gaps, not silently accepted as Jira commitments.
- After an SRS/SAD/SUD writing ticket reaches Jira P-D, the paired review must be In Progress and assigned. A review may serve two writing tickets.
- Dependency hypotheses and test-request wording matches are review aids. The dashboard does not create Jira links or alter source tickets.
- The published source contains the original captured workbook bytes for audit, and the Worker retains immutable saved observations in D1. Older observations remain available but are not allowed to override a newer published capture on page load.

The Site uses vanilla HTML/CSS/JS, SheetJS for parsing, and a Cloudflare Worker with D1 for durable snapshots and owner reviews. `build.cjs` embeds static assets in the Worker.
