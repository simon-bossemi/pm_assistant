"""Generate a dated management brief from the Jira capture; no invented progress."""
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parents[1]
SITE = ROOT / 'sites' / 'master-plan' / 'dist'
capture = json.loads((SITE / 'jira-history.json').read_text(encoding='utf-8'))
docs = json.loads((SITE / 'doc-controls.json').read_text(encoding='utf-8'))
issues = capture['issues']
today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()

def status(issue):
    value = str(issue.get('currentStatus') or '').strip().lower()
    if 'progress' in value:
        return 'In Progress'
    if 'pre-silicon' in value or value == 'p-d':
        return 'Pre-silicon Done'
    if value == 'resolved':
        return 'Resolved'
    if 'reopen' in value:
        return 'Reopened'
    if value in {'done', 'closed'}:
        return 'Done'
    if value == 'to do':
        return 'To Do'
    return 'Other / unavailable'

def pd_reached(issue):
    return status(issue) in {'Pre-silicon Done', 'Done'}

def summarize(rows):
    counts = Counter(status(issue) for issue in rows)
    late = [issue for issue in rows if issue.get('pdDueDate') and issue['pdDueDate'] < today and not pd_reached(issue)]
    missing = sum(not issue.get('pdDueDate') for issue in rows)
    targets = sum(bool(issue.get('emulatorValidationDueDate')) for issue in rows)
    return counts, late, missing, targets

groups = defaultdict(list)
for issue in issues:
    groups[issue.get('section') or 'Unmapped'].append(issue)
counts, late, missing, emulator = summarize(issues)
emulator_gaps = [issue for issue in issues if issue.get('workbookEmulatorDue') and not issue.get('emulatorValidationDueDate')]
review_actions = [pair for pair in docs.get('pairs', []) if pair.get('reviewControl', {}).get('action')]
focus = ['SDK', 'Host SW', 'AI Model Dev. Tools for Eagle N', 'Ref. Models']
focus_members = {name: [issue for issue in issues if issue['section'] == name or name in issue.get('sections', [])] for name in focus}
focus_total = len({issue['key'] for rows in focus_members.values() for issue in rows})
overlap_keys = [issue['key'] for issue in issues if sum(issue in focus_members[name] for name in focus) > 1]
groups.update(focus_members)
sections = []
for name, rows in sorted(groups.items(), key=lambda pair: (-len(pair[1]), pair[0])):
    values, overdue, without, targets = summarize(rows)
    sections.append({
        'name': name, 'tickets': len(rows), 'toDo': values['To Do'],
        'inProgress': values['In Progress'], 'preSiliconDone': values['Pre-silicon Done'],
        'resolved': values['Resolved'], 'reopened': values['Reopened'], 'done': values['Done'],
        'overdue': len(overdue), 'missingDue': without,
        'summary': (f"{len(rows)} scoped Jira tickets; {values['Pre-silicon Done']} at P-D and "
                    f"{values['Done']} finally Done. {len(overdue)} open P-D target(s) elapsed. "
                    f"{targets} emulator validation target(s) recorded in Jira.")
    })
attention = []
if late:
    attention.append(f"Recover or verify the {len(late)} open P-D target(s) past date; assign owners and record the decision in Jira.")
if review_actions:
    attention.append(f"Start and assign {len(review_actions)} document review(s) whose writing ticket reached P-D.")
if emulator_gaps:
    attention.append(f"Reconcile {len(emulator_gaps)} emulator targets present in the workbook but absent from Jira: " +
                     ', '.join(issue['key'] for issue in emulator_gaps) + '.')
unassigned = sum(not issue.get('assignee') for issue in issues)
if unassigned:
    attention.append(f"Assign the {unassigned} scoped ticket(s) without a Jira assignee before relying on their dates.")
if not attention:
    attention.append('No immediate data or gate exception was identified in this capture; review the full ticket register for local decisions.')
report = {
    'generatedAt': datetime.now(timezone.utc).isoformat(),
    'sourceObservedAt': capture['observedAt'],
    'title': 'Eagle-N B0 software delivery review',
    'overall': (f"The two selected plan tabs contain {len(issues)} unique Jira tickets, including {focus_total} in the four Level 1 delivery areas. "
                f"Jira currently shows {counts['Pre-silicon Done']} at P-D, {counts['In Progress']} In Progress, "
                f"{counts['To Do']} To Do and {counts['Done']} finally Done. "
                f"{len(late)} open P-D targets have elapsed; {emulator} emulator validation due dates are recorded in Jira, "
                f"with {len(emulator_gaps)} workbook/Jira date gaps. "
                f"The documentation gate has {len(review_actions)} writing-to-review actions. "
                f"{len(overlap_keys)} tickets belong to more than one Level 1 area, so area counts may sum above the unique focus total. "
                "These are evidence-led control signals, not forecasts of delivery."),
    'attention': attention,
    'sections': sections,
    'documentation': {'pairs': len(docs.get('pairs', [])), 'reviewActions': len(review_actions),
                      'writingReviewRule': 'After writing reaches P-D, the paired review must be In Progress and assigned.',
                      'testEpic': 'ITCP-47', 'testRequests': len(docs.get('tests', {}).get('children', []))},
    'limitations': ('Ticket membership and Level 1 categories come from the named workbook tabs. Jira provides status, owner, '
                    'P-D Due Date, Emulator Validation Due Date and changelog. Due dates are targets; neither P-D status '
                    'nor a date proves emulator validation or final feature completion. Current category labels are applied '
                    'to earlier Jira events. Two workbook-only emulator dates remain reconciliation gaps. '
                    f"Cross-area membership: {', '.join(overlap_keys) or 'none'}; every key counts once globally. "
                    'Dependencies are unconfirmed hypotheses. Refresh is on request through Codex.')
}
(SITE / 'ai-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'tickets': len(issues), 'focusTickets': focus_total, 'pdLate': len(late),
                  'emulatorTargets': emulator, 'emulatorGaps': len(emulator_gaps), 'reviewActions': len(review_actions)}))
