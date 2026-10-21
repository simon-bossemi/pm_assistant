"""Capture Jira status, dates, comments and history for the selected worksheet tickets."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'tools' / 'jira_search'))
import jira_search as jira

SITE = ROOT / 'sites' / 'master-plan' / 'dist'
plan = json.loads((SITE / 'source.json').read_text(encoding='utf-8'))
scope = {}
for row in [*plan['rows'], *plan['docRows']]:
    key = row.get('key')
    if not key:
        continue
    if key not in scope:
        section = 'SDK' if row.get('section') in {'SDK Packaging', 'SDK Installer'} else row.get('section', '')
        scope[key] = {'key': key, 'section': section, 'sections': [],
                      'title': row.get('title', ''), 'workbookEmulatorDue': ''}
    if row.get('section') and row['section'] not in scope[key]['sections']:
        scope[key]['sections'].append(row['section'])
    if row.get('emulatorDue') and not scope[key]['workbookEmulatorDue']:
        scope[key]['workbookEmulatorDue'] = row['emulatorDue']

meta = jira.session()
fields = meta.get(f'{meta.base_url}/rest/api/3/field', timeout=30).json()
pd_fields = [str(x['id']) for x in fields if str(x.get('name', '')).strip().lower() == 'p-d due date']
emulator_fields = [str(x['id']) for x in fields if str(x.get('name', '')).strip().lower() == 'emulator validation due date']

def date(value):
    value = str(value or '')
    return value[:10] if len(value) >= 10 and value[4] == '-' and value[7] == '-' else ''

def plain(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ''.join(plain(part) for part in value)
    if isinstance(value, dict):
        return str(value.get('text') or '') + plain(value.get('content') or [])
    return ''

def fetch(row):
    key = row['key']
    session = jira.session()
    try:
        wanted = ['summary', 'status', 'assignee', 'duedate', 'created', 'updated', 'comment', *pd_fields, *emulator_fields]
        response = session.get(f'{session.base_url}/rest/api/3/issue/{key}',
                               params={'expand': 'changelog', 'fields': ','.join(wanted)}, timeout=45)
        if response.status_code != 200:
            raise RuntimeError(f'HTTP {response.status_code}')
        payload = response.json()
        values = payload.get('fields') or {}
        histories = (payload.get('changelog') or {}).get('histories') or []
        comments = (values.get('comment') or {}).get('comments') or []
        latest = max(comments, key=lambda c: c.get('created', ''), default=None)
        issue = {**row, 'title': values.get('summary') or row['title'],
                 'created': values.get('created'), 'updated': values.get('updated'),
                 'currentStatus': (values.get('status') or {}).get('name', ''),
                 'assignee': (values.get('assignee') or {}).get('displayName', ''),
                 'dueDate': date(values.get('duedate')),
                 'pdDueDate': next((date(values.get(f)) for f in pd_fields if date(values.get(f))), ''),
                 'emulatorValidationDueDate': next((date(values.get(f)) for f in emulator_fields if date(values.get(f))), ''),
                 'historyCount': len(histories),
                 'lastComment': ({'id': latest.get('id'), 'at': latest.get('created'),
                                  'author': (latest.get('author') or {}).get('displayName', ''),
                                  'text': plain(latest.get('body'))[:2500]} if latest else None)}
        changes = []
        for history in histories:
            for item in history.get('items', []):
                raw = str(item.get('field') or '')
                field = ('pdDueDate' if raw in set(pd_fields) | {'P-D Due Date'} else
                         'emulatorValidationDueDate' if raw in set(emulator_fields) | {'Emulator Validation Due Date'} else raw)
                if field in {'status', 'duedate', 'pdDueDate', 'emulatorValidationDueDate', 'assignee', 'summary'}:
                    changes.append({'key': key, 'section': row['section'], 'title': issue['title'],
                                    'at': history.get('created'), 'field': field,
                                    'from': item.get('fromString') or 'Not recorded',
                                    'to': item.get('toString') or 'Not recorded'})
        return issue, changes
    except Exception as exc:
        return {**row, 'fetchError': str(exc), 'currentStatus': '', 'assignee': '',
                'pdDueDate': '', 'emulatorValidationDueDate': '', 'dueDate': '',
                'created': None, 'updated': None, 'lastComment': None}, []

issues, changes = [], []
with ThreadPoolExecutor(max_workers=8) as pool:
    futures = [pool.submit(fetch, row) for row in scope.values()]
    for future in as_completed(futures):
        issue, events = future.result()
        issues.append(issue)
        changes.extend(events)

issues.sort(key=lambda issue: (issue['section'], issue['key']))
changes.sort(key=lambda change: (change.get('at') or '', change['key']))
out = {'source': 'Jira issue detail and changelog; scope from the named development and documentation worksheets',
       'scope': 'two selected SharePoint worksheets', 'observedAt': datetime.now(timezone.utc).isoformat(),
       'pdDueFields': pd_fields, 'emulatorValidationDueFields': emulator_fields,
       'mappingNotice': 'One ticket is counted once globally. Worksheet rows define scope and category; Jira provides status, owner, dates, and history. Unavailable tickets remain visible.',
       'issues': issues, 'changes': changes}
(SITE / 'jira-history.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
by_key = {}
for row in [*plan['rows'], *plan['docRows']]:
    if row.get('key') and row['key'] not in by_key:
        by_key[row['key']] = row
monitor = []
for issue in issues:
    row = by_key.get(issue['key'], {})
    status = issue['currentStatus'].lower()
    pd_done = 'pre-silicon' in status or status in {'p-d', 'done', 'closed'}
    done = status in {'done', 'closed'}
    pd_late = bool(issue['pdDueDate'] and issue['pdDueDate'] < today and not pd_done)
    final_late = bool(issue['dueDate'] and issue['dueDate'] < today and not done)
    mismatch = bool(row.get('preDue') and row['preDue'] != issue['pdDueDate'])
    assessment = ('completed' if done else 'delayed' if pd_late or final_late else
                  'P-D achieved' if pd_done else 'at risk' if mismatch else
                  'on track' if status == 'in progress' else 'needs verification')
    reasons = ([f"P-D target {issue['pdDueDate']} passed without Jira P-D"] if pd_late else []) + (
        [f"Final target {issue['dueDate']} passed without Jira Done"] if final_late else []) + (
        [f"Workbook P-D {row.get('preDue')} differs from Jira {issue['pdDueDate'] or 'not recorded'}"] if mismatch else [])
    monitor.append({'key': issue['key'], 'summary': issue['title'], 'section': issue['section'],
                    'assignee': issue['assignee'], 'status': issue['currentStatus'],
                    'pdDueDate': issue['pdDueDate'], 'dueDate': issue['dueDate'],
                    'emulatorValidationDueDate': issue['emulatorValidationDueDate'],
                    'workbookPd': row.get('preDue', ''), 'updated': issue['updated'],
                    'lastComment': issue['lastComment'], 'assessment': assessment,
                    'reasons': reasons, 'url': 'https://bos-semi.atlassian.net/browse/' + issue['key']})
(SITE / 'monitor.json').write_text(json.dumps({'observedAt': out['observedAt'], 'scope': out['scope'],
                                                'total': len(monitor), 'issues': monitor}, ensure_ascii=False), encoding='utf-8')
print(json.dumps({'scopeKeys': len(scope), 'issues': len(issues), 'unavailable': sum(bool(i.get('fetchError')) for i in issues),
                  'emulatorTargets': sum(bool(i.get('emulatorValidationDueDate')) for i in issues),
                  'changes': len(changes), 'observedAt': out['observedAt']}))
