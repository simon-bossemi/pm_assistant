"""Build direct Jira evidence for documentation writing/review pairs and ITCP-47 tests."""
import json, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'/'jira_search'))
import jira_search as jira
SITE=ROOT/'sites/master-plan/dist'

def issue(s,key):
    r=s.get(f'{s.base_url}/rest/api/3/issue/{key}',params={'fields':'summary,status,assignee,duedate,created,updated,parent,labels'},timeout=45)
    if r.status_code != 200:
        return {'key':key,'error':f'HTTP {r.status_code}'}
    f=r.json().get('fields',{})
    return {'key':key,'summary':f.get('summary',''),'status':(f.get('status') or {}).get('name',''),'assignee':(f.get('assignee') or {}).get('displayName',''),'dueDate':f.get('duedate') or '','created':f.get('created'),'updated':f.get('updated'),'labels':f.get('labels',[]),'parent':(f.get('parent') or {}).get('key','')}

def normal(v):
    x=str(v or '').lower()
    if 'pre-silicon' in x or x=='p-d': return 'P-D'
    if 'progress' in x: return 'In Progress'
    if x in {'done','closed'}: return 'Done'
    if x in {'resolved'}: return 'Resolved'
    if 'reopen' in x: return 'Reopened'
    if not x: return 'Unknown'
    return 'To Do'

def match_tests(text,tests):
    x=text.lower()
    # The Quantization feature has two distinct requests under ITCP-47:
    # LLM execution and Vision QDQ execution. Keep this mapping explicit so
    # the validation board does not collapse the feature into one request.
    if 'quantization' in x or 'quantized' in x:
        keys = ['ITCP-48','ITCP-50']
        return [k for k in keys if k in tests]
    keys=[]
    if 'installer' in x or 'install' in x: keys += ['ITCP-51','ITCP-52']
    if 'vision' in x: keys += ['ITCP-50','ITCP-54']
    if 'llm' in x or 'quant' in x: keys += ['ITCP-48']
    if 'sdk' in x: keys += ['ITCP-53']
    if 'scarthgap' in x or 'yocto' in x: keys += ['ITCP-55']
    keys=[k for k in dict.fromkeys(keys) if k in tests]
    return keys or ['ITCP-47']

def validation_features(source,tests):
    """Return feature-level test coverage from the workbook's Spec. rows.

    These rows are supporting feature labels only. Test requests are read
    directly from the ITCP-47 Jira hierarchy and an empty match is preserved
    as a coverage gap rather than represented by the parent epic itself.
    """
    features=[]
    seen=set()
    for r in source.get('docRows',[]):
        if r.get('section')!='Spec.' or r.get('review') or not r.get('title'):
            continue
        label=(r.get('title') or '').strip()
        if label in seen:
            continue
        seen.add(label)
        keys=match_tests(label+' '+(r.get('group') or ''),tests)
        if keys==['ITCP-47']:
            keys=[]
        features.append({
            'feature':label,
            'group':r.get('group',''),
            'sourceKey':r.get('key',''),
            'tests':[tests[k] for k in keys if k in tests],
        })
    return features

def main():
    source=json.loads((SITE/'source.json').read_text(encoding='utf-8'))
    hist=json.loads((SITE/'jira-history.json').read_text(encoding='utf-8'))
    docs=[r for r in source.get('docRows',[]) if r.get('section')=='Dev. Spec. Documents']
    keys=[]
    for r in docs:
        if r.get('key') and r['key'] not in keys: keys.append(r['key'])
    tests={}
    s=jira.session()
    child=jira.search_issues('parent = ITCP-47 ORDER BY created ASC',100)
    for i in child.get('issues',[]):
        f=i.get('fields') or {}; tests[i.get('key')]= {'key':i.get('key'),'summary':f.get('summary',''),'status':(f.get('status') or {}).get('name',''),'assignee':(f.get('assignee') or {}).get('displayName','')}
    parent=issue(s,'ITCP-47'); tests['ITCP-47']=parent
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs={pool.submit(issue,jira.session(),k):k for k in keys}
        direct={}
        for f in as_completed(futs): direct[futs[f]]=f.result()
    pairs=[]
    for i,row in enumerate(docs):
        if not row.get('documentType') or row.get('review'): continue
        review=docs[i+1] if i+1<len(docs) and docs[i+1].get('review') else None
        w=direct.get(row.get('key'),{'key':row.get('key'),'error':'No Jira key'})
        rv=direct.get(review.get('key'),{'key':review.get('key'),'error':'No Jira key'}) if review else {'error':'No adjacent review row'}
        required=normal(w.get('status'))=='P-D'
        pairs.append({'writing':{**row,'jira':w,'jiraStatus':normal(w.get('status'))},'review':{**review,'jira':rv,'jiraStatus':normal(rv.get('status'))} if review else None,'reviewControl':{'required':required,'statusOk':not required or normal(rv.get('status'))=='In Progress','assigneeOk':not required or bool(rv.get('assignee')),'action':required and (normal(rv.get('status'))!='In Progress' or not rv.get('assignee'))}})
    pd=[]
    issue_map={i['key']:i for i in hist.get('issues',[])}
    for r in source.get('rows',[]):
        i=issue_map.get(r.get('key'))
        if i and normal(i.get('currentStatus'))=='P-D':
            ks=match_tests((r.get('title','')+' '+r.get('group','')),tests)
            pd.append({'key':r.get('key'),'title':r.get('title'),'section':r.get('section'),'tests':[tests.get(k,{'key':k,'error':'Not retrieved'}) for k in ks]})
    validation=validation_features(source,tests)
    out={'source':'SharePoint workbook documentation sheet + direct Jira issue reads','observedAt':datetime.now(timezone.utc).isoformat(),'documentationSheet':source.get('documentationSheet'),'pairs':pairs,'tests':{'parent':parent,'children':[v for k,v in tests.items() if k!='ITCP-47']},'pdFeatures':pd,'validationFeatures':validation,'policy':'When a writing ticket is Jira P-D, its adjacent review ticket must be In Progress and assigned. This dashboard reports the exception; it does not mutate Jira.'}
    (SITE/'doc-controls.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'pairs':len(pairs),'reviewActions':sum(1 for p in pairs if p['reviewControl']['action']),'pdFeatures':len(pd),'validationFeatures':len(validation),'tests':len(tests)}))

if __name__=='__main__': main()
