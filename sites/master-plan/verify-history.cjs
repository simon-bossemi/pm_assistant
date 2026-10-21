const assert=require('node:assert/strict');
const H=require('./dist/history-core.js');
const source=require('./dist/source.json');
const history=require('./dist/jira-history.json');

assert.equal(H.week('2026-09-13T15:01:00Z'),'2026-09-14');
assert.equal(H.week('2026-09-13T14:59:00Z'),'2026-09-07');
const weeks=H.weekly([
  {observedAt:'2026-09-01T01:00:00Z',rowCount:1},
  {observedAt:'2026-09-04T01:00:00Z',rowCount:2},
  {observedAt:'2026-09-16T01:00:00Z',rowCount:3}
]);
assert.equal(weeks.length,3);
assert.equal(weeks[0].observation.rowCount,2);
assert.equal(weeks[1].observation,null);
assert.equal(H.summarize(source).rowCount,source.rows.length);
const keys=new Set(history.issues.map(i=>i.key));
assert.equal(keys.size,history.issues.length);
assert.ok(history.issues.every(i=>i.created && i.currentStatus));
assert.ok(history.changes.every(c=>keys.has(c.key) && c.at));
assert.ok(history.changes.some(c=>c.field==='status'));
assert.ok(history.changes.some(c=>c.field==='pdDueDate'));

async function localPersistence(base){
 const get=async path=>{const r=await fetch(base+path);assert.equal(r.status,200);return r.json()};
 const before=await get('/api/history');
 assert.ok(before.snapshots.length>=2);
 const savedResponse=await fetch(base+'/api/snapshots',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({plan:source})});
 assert.equal(savedResponse.status,201);
 const saved=(await savedResponse.json()).saved;
 const restored=await get('/api/snapshots/'+encodeURIComponent(saved.id));
 assert.deepEqual(restored,source);
 assert.equal(restored.docRows.length,source.docRows.length);
 assert.equal(restored.docWorkbookBase64,source.docWorkbookBase64);
 const again=await fetch(base+'/api/snapshots',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({plan:source})});
 assert.equal(again.status,201);
 assert.equal((await again.json()).saved.id,saved.id);
 const after=await get('/api/history');
 assert.ok(after.snapshots.some(s=>s.id===saved.id));
}
(async()=>{
 if(process.argv[2])await localPersistence(process.argv[2].replace(/\/$/,''));
 console.log('PASS: Korea week boundaries, historical gaps, Jira event keys and local two-workbook snapshot persistence.');
})().catch(error=>{console.error(error);process.exitCode=1});
