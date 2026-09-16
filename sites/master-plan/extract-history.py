import sqlite3,json,datetime
from pathlib import Path
root=Path(__file__).parent
con=sqlite3.connect('file:C:/bos/tools/tools/duedatefiller/duedates.db?mode=ro',uri=True)
con.row_factory=sqlite3.Row
source=json.loads((root/'dist/source.json').read_text(encoding='utf-8'))
mapping={r['key']:r for r in source['rows'] if r['key']}
runs=[]; changes=[]; previous={}; errors=0
for run in con.execute('SELECT run_id,saved_at,worksheet FROM runs ORDER BY saved_at,run_id'):
    records={}
    for r in con.execute('SELECT * FROM ticket_dates WHERE run_id=? ORDER BY id',(run['run_id'],)):
        key=r['ticket'];current=mapping.get(key)
        records[key]={'key':key,'preDue':r['jira_pd_due_date'],'due':r['jira_feature_due_date'],'jiraStatus':r['jira_status'],'owner':r['assignee'],'error':r['error'],'currentSection':current['section'] if current else 'Unmapped to current workbook'}
    for key,r in records.items():
        if r['error']:errors+=1;continue
        if key in previous:
            for field in ['preDue','due']:
                old=previous[key][field];new=r[field]
                if old!=new:
                    delta=None
                    try:delta=(datetime.date.fromisoformat(new)-datetime.date.fromisoformat(old)).days
                    except (ValueError,TypeError):pass
                    changes.append({'runId':run['run_id'],'observedAt':run['saved_at'],'key':key,'field':field,'old':old,'new':new,'days':delta,'kind':'assigned' if not old else 'cleared' if not new else 'slipped' if delta and delta>0 else 'pulled-in' if delta and delta<0 else 'changed','currentSection':r['currentSection']})
        previous[key]=r
    runs.append({'id':run['run_id'],'observedAt':run['saved_at'],'records':list(records.values()),'trackedTickets':len(records)})
out={'source':'Due Date Filler SQLite history','extractedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mappingNotice':'Historical ticket membership uses current Level 1 labels. Unticketed rows and historical reclassification cannot be reconstructed. Ticket counts are not complete historical feature totals. Date changes compare successive successful saved runs, not Excel-versus-Jira differences within one sync.','runs':runs,'changes':changes,'errorRecords':errors}
(root/'dist/legacy-history.json').write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
baseline=root/'dist/baseline.json'
if not baseline.exists():baseline.write_text(json.dumps(source,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print(json.dumps({'runs':len(runs),'dateChanges':len(changes),'errorRecords':errors,'first':runs[0]['observedAt'],'last':runs[-1]['observedAt']}))
