# Eagle B0 master plan dashboard

Private Sites project: `appgprj_6aaa4125c9008191b9e05460b44f7875`.

## Refresh policy

Only when Simon requests a refresh. No scheduled job. Never run `fill_due_dates.py` to refresh this dashboard: it can modify upstream data. Read the workbook and date database only.

The site's **Load & save workbook** button parses the first worksheet and retains the original XLSX (up to 1 MB) plus all parsed rows in D1. Same content within one Korea calendar day is deduplicated. Historical snapshots are immutable and not pruned. Latest saved observation loads on restart. Original workbook download and parsed baseline export are available in Weekly evolution.

For a Codex refresh, run `export-source.cjs` with the exact current local workbook path, then `extract-history.py`. Preserve `dist/baseline.json`. Review dependency hypotheses against changed tickets; update evidence only, never create Jira links. Validate and publish through Sites skills. The published source is seeded once into persistent history with its actual capture timestamp, preserving previous observations and owner reviews. Never publish local `.wrangler` test state.

## Data semantics

- Focus feature counts are worksheet rows, including unticketed/placeholder rows, not unique Jira tickets or effort estimates.
- Full-feature history begins on 16 September 2026. Older `duedates.db` observations contain ticket dates but no historical Level 1 membership; historical ticket charts explicitly map them to current sections. Missing weeks are gaps.
- Weekly points select the last observation in each Monday–Sunday Korea-time week. Multiple daily observations remain archived.
- Column K is the P-D target. Column L (Feature Due Date) is the Feature Done **target**, never an actual finish date. Only `Done` confirms final completion; `P-D` confirms a separate pre-silicon milestone. No actual completion dates are available.
- Date ledger combines legacy database changes with changes between durable workbook captures. Snapshot comparisons flag duplicate keys rather than silently pairing them.
- Dependency suggestions are workbook-based hypotheses. Acceptance/rejection is a dashboard review record, not a Jira dependency or a confirmed scheduling blocker.
- Warning rules expose recorded delays, missing data, late targets, repeated observed slippage, milestone order and conditional final-date inversions. They are review signals, not forecasts.

## Implementation and validation

Vanilla HTML/CSS/JS; SheetJS for XLSX parsing; a Cloudflare-compatible Worker and D1 for durable state. Drizzle schema/migrations are included. `build.cjs` builds the Worker with embedded static assets and hosting metadata.

`verify-source.py` independently reconciles all source rows against openpyxl. `verify-analytics.cjs` checks chart counts and milestone semantics. `verify-history.cjs` checks Korea week boundaries, gaps, history counts, dependency risks and local D1 APIs at port 8766. Run API tests only against the local test database; never add synthetic test reviews or observations to production.

Browser QA includes keyboard navigation, charts, filters, mobile/desktop layout and report views. The Codex in-app file-picker automation may return OS file-read permission errors; this does not invalidate the independently verified XLSX parser/API path. Test original-file picker behavior in a regular browser when available.

The configured reporting-style directory was unavailable on this machine. The built-in report uses the existing dashboard's BOS navy/teal presentation and exports self-contained HTML.
