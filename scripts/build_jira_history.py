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
def fetch(item):
    key,row=item; s=jira.session()
    try:
        res=s.get(f"{s.base_url}/rest/api/3/issue/{key}", params={'expand':'changelog','fields':'summary,status,created,updated'}, timeout=8)
        if res.status_code != 200: return [],[]
        p=res.json(); f=p.get('fields',{}); histories=p.get('changelog',{}).get('histories',[])
        issue={'key':key,'section':row.get('section',''),'title':row.get('title',''),'created':f.get('created'),'updated':f.get('updated'),'historyCount':len(histories)}
        local=[]
        for h in histories:
            for it in h.get('items',[]):
                if it.get('field') in {'status','duedate','assignee','summary'}:
                    local.append({'key':key,'section':row.get('section',''),'title':row.get('title',''),'at':h.get('created'),'field':it.get('field'),'from':it.get('fromString') or 'Not recorded','to':it.get('toString') or 'Not recorded'})
        return [issue],local
    except Exception:
        return [],[]
issues=[]; changes=[]
with ThreadPoolExecutor(max_workers=6) as ex:
    for f in as_completed([ex.submit(fetch,x) for x in rows.items()]):
        i,c=f.result(); issues.extend(i); changes.extend(c)
out={'source':'Jira filter 19455 · labels = "host_sw_master_plan" ORDER BY created DESC · REST issue changelog','filterId':'19455','jql':'labels = "host_sw_master_plan" ORDER BY created DESC','observedAt':datetime.now(timezone.utc).isoformat(),'mappingNotice':'Only tickets returned by Jira filter 19455 are included. Categories use the currently displayed workbook section when available; otherwise they are marked Unmapped Jira ticket.','issues':issues,'changes':changes}
(site/'jira-history.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'issues':len(issues),'changes':len(changes),'observedAt':out['observedAt']}))
