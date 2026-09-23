import json, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).parents[1] / 'tools' / 'jira_search'))
import jira_search as jira

root=Path(__file__).parents[1]
site=root/'sites'/'master-plan'/'dist'
plan=json.loads((site/'source.json').read_text(encoding='utf-8'))
workbook_rows={r['key']:r for r in plan['rows'] if r.get('key')}
search=jira.search_issues('labels = "host_sw_master_plan" ORDER BY created DESC', 200)
rows={i.get('key'):workbook_rows.get(i.get('key'), {'key':i.get('key'),'section':'Unmapped Jira ticket','title':(i.get('fields') or {}).get('summary','')}) for i in search.get('issues',[]) if i.get('key')}
meta=jira.session()
field_rows=meta.get(f"{meta.base_url}/rest/api/3/field", timeout=30).json()
pd_fields=[str(x.get('id')) for x in field_rows if str(x.get('name') or '').strip().lower()=='p-d due date']
if not pd_fields:
    pd_fields=[str(x.get('id')) for x in field_rows if 'p-d' in str(x.get('name') or '').lower() and 'due' in str(x.get('name') or '').lower() and 'date' in str(x.get('name') or '').lower()]
def normalize_date(value):
    text=str(value or '')
    return text[:10] if len(text)>=10 and text[4]=='-' and text[7]=='-' else ''
def fetch(item):
    key,row=item; s=jira.session()
    try:
        requested=['summary','status','assignee','duedate','created','updated',*pd_fields]
        res=s.get(f"{s.base_url}/rest/api/3/issue/{key}", params={'expand':'changelog','fields':','.join(requested)}, timeout=8)
        if res.status_code != 200: return [],[]
        p=res.json(); f=p.get('fields',{}); histories=p.get('changelog',{}).get('histories',[])
        pd_due=next((normalize_date(f.get(field)) for field in pd_fields if normalize_date(f.get(field))), '')
        issue={'key':key,'section':row.get('section',''),'title':row.get('title',''),'created':f.get('created'),'updated':f.get('updated'),'currentStatus':(f.get('status') or {}).get('name',''),'assignee':(f.get('assignee') or {}).get('displayName',''),'dueDate':f.get('duedate') or '','pdDueDate':pd_due,'historyCount':len(histories)}
        local=[]
        for h in histories:
            for it in h.get('items',[]):
                raw_field=str(it.get('field') or '')
                field='pdDueDate' if raw_field in set(pd_fields)|{'P-D Due Date','P-D due date'} else raw_field
                if field in {'status','duedate','pdDueDate','assignee','summary'}:
                    local.append({'key':key,'section':row.get('section',''),'title':row.get('title',''),'at':h.get('created'),'field':field,'from':it.get('fromString') or 'Not recorded','to':it.get('toString') or 'Not recorded'})
        return [issue],local
    except Exception:
        return [],[]
issues=[]; changes=[]
with ThreadPoolExecutor(max_workers=6) as ex:
    for f in as_completed([ex.submit(fetch,x) for x in rows.items()]):
        i,c=f.result(); issues.extend(i); changes.extend(c)
out={'source':'Jira filter 19455 · labels = "host_sw_master_plan" ORDER BY created DESC · REST issue changelog','filterId':'19455','jql':'labels = "host_sw_master_plan" ORDER BY created DESC','observedAt':datetime.now(timezone.utc).isoformat(),'pdDueFields':pd_fields,'mappingNotice':'Only tickets returned by Jira filter 19455 are included. Categories use the currently displayed workbook section when available; otherwise they are marked Unmapped Jira ticket. P-Due dates are read from Jira custom field P-D Due Date.','issues':issues,'changes':changes}
(site/'jira-history.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'issues':len(issues),'changes':len(changes),'observedAt':out['observedAt']}))
