const assert=require('node:assert/strict'),A=require('./dist/analytics.js'),d=require('./dist/source.json');
const expected={focus:92,req:8,docs:27,validation:44,all:395};
for(const [scope,n] of Object.entries(expected)){
 const rows=d.rows.filter(A.scopes[scope].match);assert.equal(rows.length,n);
 assert.equal(Object.values(A.countStatus(rows)).reduce((a,b)=>a+b,0),n);
 for(const key of ['section','team','owner'])assert.equal(A.groupRows(rows,key).reduce((sum,g)=>sum+g.total,0),n);
 for(const field of ['due','preDue']){const due=A.dueSummary(rows,field,'2026-09-16');assert.equal(due.months.reduce((sum,m)=>sum+m.total,0)+due.missing,n);assert(due.months.every(m=>m.confirmed+m.unconfirmed===m.total));}
}
const sample=[{status:'P-D',due:'2026-09-15',preDue:'2026-09-15'},{status:'Done',due:'2026-09-15',preDue:'2026-09-15'},{status:'Unknown',due:'2026-09-16',preDue:''}];
assert.equal(A.dueSummary(sample,'due','2026-09-16').past.length,1);
assert.equal(A.dueSummary(sample,'preDue','2026-09-16').past.length,0);
assert.equal(A.dueSummary(sample,'due','2026-09-16').upcoming.length,1);
assert.equal(A.dueSummary(sample,'preDue','2026-09-16').missing,1);
assert.equal(A.groupRows(d.rows.filter(A.scopes.docs.match),'group').length,8);
assert.equal(A.docType('SAD for Security SWCs'),'SAD');
console.log('PASS: chart totals reconcile across all five scopes; date buckets, unknowns, document groups, and milestone completion semantics checked.');
