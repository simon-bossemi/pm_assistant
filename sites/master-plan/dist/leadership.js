'use strict';
// The selected worksheets define ticket membership; Jira defines live evidence.
const programStatus=value=>String(value||'').trim().toLowerCase();
const programPdReached=issue=>/pre.silicon done/.test(programStatus(issue.currentStatus||issue.jiraStatus))||['p-d','done','closed'].includes(programStatus(issue.currentStatus||issue.jiraStatus));
const programDone=issue=>['done','closed'].includes(programStatus(issue.currentStatus||issue.jiraStatus));
const programLink=key=>`<a href="https://bos-semi.atlassian.net/browse/${esc(key)}" target="_blank" rel="noopener noreferrer">${esc(key)} ↗</a>`;
const programFacts=(issues,asOf)=>{
 const pdLate=issues.filter(i=>i.pdDueDate&&i.pdDueDate<asOf&&!programPdReached(i));
 const emulator=issues.filter(i=>i.emulatorValidationDueDate).sort((a,b)=>a.emulatorValidationDueDate.localeCompare(b.emulatorValidationDueDate));
 const emulatorPast=emulator.filter(i=>i.emulatorValidationDueDate<asOf);
 const emulatorGaps=issues.filter(i=>i.workbookEmulatorDue&&!i.emulatorValidationDueDate);
 const reviews=(docControls.pairs||[]).filter(p=>p.reviewControl?.action);
 return {pdLate,emulator,emulatorPast,emulatorGaps,reviews,unavailable:issues.filter(i=>i.fetchError)};
};
function programMetrics(issues,asOf){
 const f=programFacts(issues,asOf);
 return [
  ['Scoped Jira tickets',issues.length,'Two named worksheets',''],
  ['P-D reached',issues.filter(programPdReached).length,'Current Jira status',''],
  ['P-D past target',f.pdLate.length,'Open milestone · Jira','danger'],
  ['Emulator targets',f.emulator.length,`${f.emulatorPast.length} elapsed · ${f.emulatorGaps.length} workbook gaps`,f.emulatorPast.length?'danger':''],
  ['Review actions',f.reviews.length,'P-D writing → assigned review',f.reviews.length?'danger':'']
 ];
}
function programEmulatorBoard(issues,compact=false){
 const f=programFacts(issues,state.asOf),dated=f.emulator;
 const gapRows=f.emulatorGaps.map(i=>`<tr><td>${programLink(i.key)}<span class="subline">${esc(i.title)}</span></td><td>${esc(i.workbookEmulatorDue)}</td><td>Missing in Jira</td></tr>`).join('');
 return `<article class="chart-card validation-control"><div class="chart-heading"><div><span class="eyebrow">EMULATOR VALIDATION</span><h3>Due-date control</h3><p>${dated.length} Jira targets · ${f.emulatorPast.length} elapsed · ${f.emulatorGaps.length} workbook/Jira gaps</p></div><span class="source-pill">Jira custom field</span></div>
 <div class="validation-timeline" role="list" aria-label="Emulator validation due dates">${dated.map(i=>`<div role="listitem" class="validation-stop ${i.emulatorValidationDueDate<state.asOf?'past':''}"><time datetime="${i.emulatorValidationDueDate}">${esc(fmt(i.emulatorValidationDueDate))}</time><span>${programLink(i.key)}</span><small>${esc(i.title)}</small></div>`).join('')||'<p>No Jira emulator validation targets have been recorded.</p>'}</div>
 <p class="chart-footnote">A due date is a target, not proof that emulator validation occurred. P-D status is a separate milestone. ${f.emulatorPast.length?'Elapsed dates require an owner to confirm validation evidence.':'No recorded Jira emulator target has elapsed.'}</p>
 ${gapRows?`<details class="reconcile-gaps" ${compact?'':'open'}><summary>${f.emulatorGaps.length} workbook targets missing in Jira</summary><div class="table-scroll"><table><thead><tr><th>Ticket</th><th>Workbook target</th><th>Jira</th></tr></thead><tbody>${gapRows}</tbody></table></div></details>`:''}</article>`;
}
globalThis.renderDashboard=function(rows){
 const issues=jiraScope.issues||[],facts=programFacts(issues,state.asOf),focus=['sdk','host','ai','ref'];
 const dueList=facts.pdLate.slice().sort((a,b)=>a.pdDueDate.localeCompare(b.pdDueDate)).slice(0,5);
 const sourceTime=jiraScope.observedAt?new Date(jiraScope.observedAt).toLocaleString('en-GB',{timeZone:'Asia/Seoul',dateStyle:'medium',timeStyle:'short'}):'unavailable';
 return `<div class="visual-dashboard leadership-dashboard">
 <div class="lead-hero"><div><span class="eyebrow">EAGLE-N B0 · PROGRAM CONTROL</span><h2>Delivery confidence, grounded in Jira</h2><p>Manage P-D commitments, emulator validation targets and document review readiness across the two selected plan tabs.</p></div><div class="lead-asof"><span>Checked Jira snapshot</span><strong>${esc(sourceTime)} KST</strong><small>Refresh through Codex on request</small></div></div>
 <div class="decision-strip"><div><strong>${facts.pdLate.length}</strong><span>Open P-D targets past date</span><button data-view="dates">Inspect dates →</button></div><div><strong>${facts.emulator.length}</strong><span>Emulator targets in Jira</span><button data-view="dates">Inspect validation →</button></div><div><strong>${facts.reviews.length}</strong><span>Document review actions</span><button data-cohort="docs">Review pairs →</button></div><div><strong>${facts.unavailable.length}</strong><span>Jira tickets unavailable</span><button data-view="monitor">Inspect evidence →</button></div></div>
 <div class="dashboard-section-heading"><h3>Level 1 delivery</h3><p>Unique Jira tickets · status from Jira · select an area for detail</p></div>
 <div class="cohort-grid">${focus.map(mode=>`<article class="chart-card cohort"><div class="chart-heading"><button data-cohort="${mode}" class="cohort-title">${esc(Analytics.scopes[mode].title)} <span>↗</span></button></div><p class="cohort-subtitle">${esc(Analytics.scopes[mode].subtitle)}</p>${statusDonut([],mode)}</article>`).join('')}</div>
 ${cumulativeCohortChart()}
 <div class="lead-management-grid"><article class="chart-card"><span class="eyebrow">ACTION QUEUE</span><h3>Owner decisions</h3><p>Open P-D targets past their Jira date need recovery or milestone evidence.</p><ol class="lead-actions">${dueList.map(i=>`<li><strong>${programLink(i.key)}</strong><span>${esc(i.pdDueDate)} · ${esc(i.assignee||'Assign owner')}</span><small>${esc(i.title)}</small></li>`).join('')||'<li>No open P-D target is past its Jira date.</li>'}</ol><button data-view="risks">Open all warnings →</button></article>
 ${programEmulatorBoard(issues,true)}</div>
 <div class="lead-bottom"><div><span class="eyebrow">DOCUMENT GATE</span><strong>${facts.reviews.length} action${facts.reviews.length===1?'':'s'} required</strong><p>When SRS, SAD or SUD writing reaches P-D, its paired review must be In Progress and assigned.</p><button data-cohort="docs">Open documentation control →</button></div><div><span class="eyebrow">REPORTING</span><strong>One evidence trail</strong><p>Weekly ticket history, date movement and owner decisions feed the management report.</p><button data-view="report">Open management report →</button></div></div>
 <p class="chart-footnote">Scope: development first tab and Eagle-N B0 Doc Delivery Plan tab. Workbook entries define membership and grouping; Jira supplies ticket status, owner, dates and history. Repeated rows do not increase ticket totals.</p></div>`;
};
globalThis.renderDates=function(rows){
 const issues=jiraScope.issues||[],facts=programFacts(issues,state.asOf),horizon=new Date(state.asOf+'T12:00:00');horizon.setDate(horizon.getDate()+14);
 const until=horizon.toISOString().slice(0,10),near=issues.filter(i=>i.pdDueDate&&i.pdDueDate>=state.asOf&&i.pdDueDate<=until&&!programPdReached(i));
 const dated=issues.filter(i=>i.pdDueDate),missing=issues.length-dated.length;
 const pdRows=[...issues].sort((a,b)=>(facts.pdLate.includes(a)?0:near.includes(a)?1:2)-(facts.pdLate.includes(b)?0:near.includes(b)?1:2)||(a.pdDueDate||'9999').localeCompare(b.pdDueDate||'9999'));
 const changes=(jiraScope.changes||[]).filter(c=>['pdDueDate','emulatorValidationDueDate'].includes(c.field)).slice().reverse();
 return `<div class="intel-page leadership-dates"><div class="section-intro"><div><span class="eyebrow">DELIVERY CONTROL</span><h3>P-D and emulator targets</h3><p>Both target fields and changes below come directly from scoped Jira tickets. Neither target confirms actual completion.</p></div><label>As of<input type="date" id="as-of" value="${state.asOf}"></label></div>
 <div class="signal-grid"><div><strong>${dated.length}</strong><span>P-D targets in Jira</span></div><div class="danger"><strong>${facts.pdLate.length}</strong><span>Open and past P-D target</span></div><div><strong>${near.length}</strong><span>P-D within 14 days</span></div><div><strong>${missing}</strong><span>P-D target missing</span></div></div>
 <div class="date-executive-note"><b>Delivery reading</b><p>${facts.pdLate.length} tickets need P-D recovery or milestone evidence; ${near.length} reach their P-D target by ${esc(until)}. Emulator validation has ${facts.emulator.length} Jira target dates and ${facts.emulatorGaps.length} workbook dates still absent from Jira.</p></div>
 ${programEmulatorBoard(issues)}
 <article class="chart-card"><div class="chart-heading"><div><h3>P-D target register</h3><p>Current status and assignee from Jira. Open late items are first.</p></div><span class="source-pill">${issues.length} scoped tickets</span></div><div class="table-scroll"><table><thead><tr><th>Ticket / owner</th><th>P-D target</th><th>Jira status</th><th>Control</th></tr></thead><tbody>${pdRows.map(i=>`<tr class="${facts.pdLate.includes(i)?'risk-row':''}"><td>${programLink(i.key)}<span class="subline">${esc(i.assignee||'Unassigned')} · ${esc(i.title)}</span></td><td>${esc(i.pdDueDate||'Missing')}</td><td>${esc(i.currentStatus||'Unavailable')}</td><td>${programPdReached(i)?'P-D reached':facts.pdLate.includes(i)?'Past target':near.includes(i)?'Due within 14 days':i.pdDueDate?'Open target':'Target missing'}</td></tr>`).join('')}</tbody></table></div></article>
 <article class="chart-card"><h3>Jira target change ledger</h3><p>P-D and Emulator Validation Due Date changes recorded in ticket histories.</p><div class="table-scroll"><table><thead><tr><th>Changed</th><th>Ticket</th><th>Field</th><th>From</th><th>To</th></tr></thead><tbody>${changes.slice(0,150).map(c=>`<tr><td>${esc(c.at?.slice(0,10)||'—')}</td><td>${programLink(c.key)}</td><td>${c.field==='pdDueDate'?'P-D due':'Emulator validation due'}</td><td>${esc(c.from)}</td><td>${esc(c.to)}</td></tr>`).join('')||'<tr><td colspan="5">No Jira target changes captured.</td></tr>'}</tbody></table></div><p class="chart-footnote">Showing the latest 150 of ${changes.length} changes. History is observed from Jira; gaps in Jira changelog coverage are not estimated.</p></article></div>`;
};
globalThis.renderJiraHistory=function(){
 const points=observations();
 return `<div class="intel-page"><div class="section-intro"><div><span class="eyebrow">WEEK OVER WEEK · JIRA HISTORY</span><h3>Ticket evolution</h3><p>Scope from the two selected tabs; creation and status transitions from each Jira ticket.</p></div></div><p class="evidence-note">Area membership is the current workbook mapping, applied retrospectively. Counts before the current plan capture are reconstructed, not historical workbook observations.</p><div class="inline-controls"><label>Show<select id="history-series"><option value="total">Focus total + four areas</option>${HistoryCore.focus.map(s=>`<option ${historyState.series===s?'selected':''}>${esc(s)}</option>`).join('')}</select></label><button data-view="dates">Inspect date movement →</button></div><article class="chart-card">${points.length?trendChart(points):'<p>No Jira history is available.</p>'}<details id="weekly-data" open><summary>Weekly Jira ticket totals</summary><div class="table-scroll"><table><thead><tr><th>Week starting</th><th>All scoped tickets</th><th>Four focus areas</th>${HistoryCore.focus.map(s=>`<th>${esc(s)}</th>`).join('')}</tr></thead><tbody>${points.map(p=>`<tr><th>${p.week}</th><td>${p.observation.rowCount}</td><td>${p.observation.focusRows}</td>${HistoryCore.focus.map(s=>`<td>${p.observation.groups[s]?.rows||0}</td>`).join('')}</tr>`).join('')}</tbody></table></div></details></article>${jiraWeeklyStatusChart()}</div>`;
};
globalThis.renderRisks=function(){
 const issues=jiraScope.issues||[],facts=programFacts(issues,state.asOf);
 const unassigned=issues.filter(i=>!i.assignee),missingPd=issues.filter(i=>!i.pdDueDate);
 const moved=new Map();
 for(const c of jiraScope.changes||[]){
  if(c.field!=='pdDueDate')continue;
  const before=String(c.from||'').slice(0,10),after=String(c.to||'').slice(0,10);
  if(/^20\d\d-\d\d-\d\d$/.test(before)&&/^20\d\d-\d\d-\d\d$/.test(after)&&after>before)moved.set(c.key,(moved.get(c.key)||0)+1);
 }
 const repeated=[...moved].filter(([,n])=>n>=2).sort((a,b)=>b[1]-a[1]);
 const rows=[
  ...facts.pdLate.map(i=>({p:'P1',type:'P-D target elapsed',key:i.key,owner:i.assignee,detail:`${i.pdDueDate} passed; Jira is not P-D or Done.`})),
  ...facts.reviews.map(p=>({p:'P1',type:'Document review gate',key:p.writing.key,owner:p.review?.jira?.assignee,detail:`Writing is P-D; review ${p.review?.key||'unlinked'} is not both In Progress and assigned.`})),
  ...repeated.map(([key,n])=>({p:'P2',type:'Repeated P-D slippage',key,owner:issues.find(i=>i.key===key)?.assignee,detail:`${n} later-date moves appear in Jira history.`})),
  ...facts.emulatorGaps.map(i=>({p:'P2',type:'Emulator date mismatch',key:i.key,owner:i.assignee,detail:`Workbook target ${i.workbookEmulatorDue}; Jira emulator date missing.`})),
  ...unassigned.map(i=>({p:'P3',type:'Owner missing',key:i.key,owner:'',detail:'No current Jira assignee.'}))
 ];
 return `<div class="intel-page leadership-warnings"><div class="section-intro"><div><span class="eyebrow">EARLY WARNING · JIRA CONTROL</span><h3>${rows.length} actionable signals</h3><p>Prioritized evidence for owner review, not confirmed blockers or a delivery forecast.</p></div><label>As of<input type="date" id="as-of" value="${state.asOf}"></label></div>
 <div class="warning-ai-summary"><div class="warning-ai-head"><span class="eyebrow">CODEX CONTROL SYNTHESIS</span><h3>What needs attention</h3><p>${facts.pdLate.length} open P-D targets have elapsed and ${facts.reviews.length} document review gates need action. ${repeated.length} tickets show repeated P-D slippage; ${facts.emulatorGaps.length} workbook emulator dates are absent from Jira. Review ownership and recovery evidence before reporting these as resolved.</p><small>Generated from the current scoped Jira snapshot and the two selected worksheet mappings.</small></div><div class="warning-ai-kpis"><div class="p1"><strong>${facts.pdLate.length+facts.reviews.length}</strong><span>P1 · schedule/gate</span></div><div class="p2"><strong>${repeated.length+facts.emulatorGaps.length}</strong><span>P2 · reconcile</span></div><div class="p3"><strong>${unassigned.length}</strong><span>P3 · assign owner</span></div></div></div>
 <div class="signal-grid"><div><strong>${issues.length}</strong><span>Scoped Jira tickets</span></div><div><strong>${missingPd.length}</strong><span>P-D target absent</span></div><div><strong>${facts.emulator.length}</strong><span>Emulator targets in Jira</span></div><div><strong>${facts.unavailable.length}</strong><span>Jira reads unavailable</span></div></div>
 <div class="warning-list">${rows.map(r=>`<article class="warning ${r.p==='P1'?'high':r.p==='P2'?'conditional':'review'}"><div><span class="risk-type">${r.p} · ${esc(r.type)}</span><h4>${programLink(r.key)}</h4><p>${esc(r.detail)}</p><small>Owner: ${esc(r.owner||'Assign owner')}</small></div></article>`).join('')||'<p>No signals generated from the available evidence.</p>'}</div><p class="evidence-note">A missing P-D date is a coverage gap; it is not automatically a late delivery. Emulator validation completion evidence is not inferred from P-D status. Hypothesized dependencies remain in the separate review view.</p></div>`;
};
globalThis.renderDocControls=function(){
 const pairs=docControls.pairs||[],actions=pairs.filter(p=>p.reviewControl?.action);
 const link=key=>key?programLink(key):'No ticket';
 return `<div class="intel-page"><div class="section-intro"><div><span class="eyebrow">DOCUMENTATION GATE</span><h3>SRS / SAD / SUD writing and review</h3><p>The named documentation tab pairs writing and review work. Jira supplies status and assignee.</p></div></div><div class="signal-grid"><div><strong>${pairs.length}</strong><span>Writing/review pairs</span></div><div class="danger"><strong>${actions.length}</strong><span>P-D review actions</span></div><div><strong>${docControls.tests?.children?.length||0}</strong><span>ITCP-47 test requests</span></div></div><div class="date-executive-note"><b>Control rule</b><p>Once writing reaches P-D, its paired review must be In Progress and assigned. ${actions.length} pair${actions.length===1?'':'s'} currently need owner action.</p></div><article class="chart-card"><h3>Document delivery register</h3><div class="table-scroll"><table><thead><tr><th>Document</th><th>Writing</th><th>Jira status</th><th>Review</th><th>Jira status</th><th>Reviewer</th><th>Gate</th></tr></thead><tbody>${pairs.map(p=>`<tr class="${p.reviewControl?.action?'risk-row':''}"><td>${esc(p.writing.title)}</td><td>${link(p.writing.key)}</td><td>${esc(p.writing.jira?.status||'Unavailable')}</td><td>${link(p.review?.key)}</td><td>${esc(p.review?.jira?.status||'Unavailable')}</td><td>${esc(p.review?.jira?.assignee||'Unassigned')}</td><td>${p.reviewControl?.action?'Action required':p.reviewControl?.required?'Ready':'Monitor'}</td></tr>`).join('')}</tbody></table></div></article><p class="evidence-note">Document rows are pairing context. Open Validation plan for feature-to-test-request review; no Jira dependency or review links are created by this dashboard.</p></div>`;
};
globalThis.updateSource=function(){
 $('sheet-name').textContent='Development + documentation plan tabs';
 const stamp=new Date(jiraScope.observedAt||data.observedAt).toLocaleString('en-GB',{timeZone:'Asia/Seoul',dateStyle:'medium',timeStyle:'short'});
 $('source').textContent=`${jiraScope.issues?.length||0} scoped Jira tickets · checked ${stamp} KST · workbook membership captured on request`;
 $('footer-source').textContent='Scope: two selected SharePoint tabs · Jira evidence checked '+stamp+' KST';
 $('reset').hidden=data===published;
};
globalThis.sourceInfo=function(){
 $('detail-eyebrow').textContent='DATA PROVENANCE';
 $('detail-body').innerHTML=`<h2>How this board is measured</h2><p><b>Ticket population:</b> unique Jira keys on the <a href="https://bossemi.sharepoint.com/:x:/s/PMSE/cQo4LgVYMRfGQaKdR-b8D2_WEgUCP0nQCp26_EAwfnRFcWAtmg" target="_blank" rel="noopener noreferrer">development first tab ↗</a> and the <a href="https://bossemi.sharepoint.com/:x:/s/PMSE/cQrKXi27PAQKTKPHmKvkBjQpEgUCjylZMzQgeoXVWIXpe6HmkA" target="_blank" rel="noopener noreferrer">Eagle-N B0 Doc Delivery Plan tab ↗</a>. Blank rows and repeated keys do not increase the count.</p><p><b>Jira evidence:</b> ticket status, owner, P-D Due Date, Emulator Validation Due Date, comments and changelog were checked at ${esc(jiraScope.observedAt||'unavailable')}. Worksheet dates provide reconciliation context only.</p><p>Due dates are targets, not proof of completion. P-D and final Done are distinct Jira milestones. Weekly area membership uses today's worksheet categorization applied to historical ticket creation dates. Refresh runs through Codex only when requested.</p>`;
 $('detail').showModal();
};
document.getElementById('source-info').onclick=sourceInfo;
