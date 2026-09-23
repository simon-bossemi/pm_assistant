(function(root){
 'use strict';
 const focus=['SDK','Host SW','AI Model Dev. Tools for Eagle N','Ref. Models'];
 const labels={G:'On track',R:'Risky',D:'Delayed','P-D':'Pre-silicon done',Done:'Done for B0',Unknown:'Not recorded'};
 const clean=v=>String(v??'').replace(/\s+/g,' ').trim();
 const issueKey=v=>clean(v).match(/\b[A-Z][A-Z0-9]+-\d+\b/)?.[0]||'';
 function parseSheet(book,index,meta,kind){
  const sheet=book.Sheets[book.SheetNames[index]], range=XLSX.utils.decode_range(sheet['!ref']||'A1');
  const cell=(r,c)=>sheet[XLSX.utils.encode_cell({r:r-1,c:c-1})];
  const val=(r,c)=>{const x=cell(r,c);return x?clean(x.w??x.v??''):''};
  const header=Array.from({length:Math.min(range.e.r+1,30)},(_,i)=>i+1).find(r=>val(r,1).replace(/\s/g,'').toLowerCase()==='level1'&&/^JIRA/i.test(val(r,6)));
  if(!header)throw new Error('This workbook sheet has no Level1/JIRA header.');
  const date=(r,c)=>{const x=cell(r,c);if(!x)return '';if(x.t==='d')return new Date(x.v).toISOString().slice(0,10);if(x.t==='n'){const d=XLSX.SSF.parse_date_code(x.v,{date1904:!!book.Workbook?.WBProps?.date1904});if(d&&d.y>=2000&&d.y<2100)return `${d.y}-${String(d.m).padStart(2,'0')}-${String(d.d).padStart(2,'0')}`;}const t=val(r,c);return /^20\d\d-\d\d-\d\d/.test(t)?t.slice(0,10):t;};
  const yearText=Array.from({length:range.e.c+1},(_,i)=>val(header,i+1)).join('');
  let section='',group='',month='',year=Number(yearText.match(/20\d{2}/)?.[0]||2026),lastWeek=0;
  const weeks=[];
  for(let c=13;c<=range.e.c+1;c++){const w=val(header+2,c);if(!/^W\d+$/.test(w))continue;const n=Number(w.slice(1));if(n<lastWeek)year++;lastWeek=n;month=val(header+1,c)||month;weeks.push({column:c,week:w,month,year});}
  const rows=[];
  for(let r=header+1;r<=range.e.r+1;r++){
   let a=val(r,1),b=val(r,2);
   if(a){
    if(a==='Feature'&&val(r+1,1)==='Requirements')a='Feature Requirements';
    else if(a==='AI Model')a='AI Model Dev. Tools for Eagle N';
    else if(a==='Dev. Tools'&&section.startsWith('AI Model'))a=section;
    else if(/^for Eagle[- ]N$/i.test(a)&&section.startsWith('AI Model'))a=section;
    else if(a==='Dev. Spec.'||a==='Dev. Spec. Documents')a='Dev. Spec. Documents';
    else if(a==='Documents'&&section==='Dev. Spec. Documents')a=section;
    if(a!==section){section=a;group='';}
   }
   if(b)group=b;
   const timeline=weeks.flatMap(w=>{const x=cell(r,w.column),text=val(r,w.column),fill=x?.s?.fgColor?.rgb||x?.s?.fill?.fgColor?.rgb||'',color=/^[0-9A-Fa-f]{6,8}$/.test(fill)&&!['FFFFFF','000000'].includes(fill.slice(-6))?fill.slice(-6):'';return text||color?[{...w,text,color}]:[]});
   const raw=Array.from({length:12},(_,c)=>val(r,c+1));
   if(!raw.some(Boolean)&&!timeline.length)continue;
   const ticket=val(r,6),key=issueKey(ticket),title=val(r,3)||b||(a?section:'Unspecified feature');
   const links=[];for(let c=1;c<=range.e.c+1;c++){const href=cell(r,c)?.l?.Target;if(href&&/^https?:\/\//i.test(href))links.push({column:XLSX.utils.encode_col(c-1),text:val(r,c)||href,url:href});}
   const status=val(r,7)||'Unknown', review=/\breview\b/i.test(title), documentType=/\bSRS\b/i.test(title)?'SRS':/\bSAD\b/i.test(title)?'SAD':/\bSUD\b/i.test(title)?'SUD':'';
   rows.push({id:`${kind||'sheet'}-row-${r}`,row:r,sheet:book.SheetNames[index],kind,section,group,title,team:val(r,4),owner:val(r,5),ticket,key,url:links.find(x=>x.column==='F')?.url||(key?'https://bos-semi.atlassian.net/browse/'+key:''),status,preTarget:date(r,8),summary:val(r,11),sdk:val(r,10),preDue:date(r,8),due:date(r,9),timeline,links,raw,review,documentType,writingTicket:!review&&!!documentType,reviewTicket:review&&!!key});
  }
  return {sheet:book.SheetNames[index],rows,weeks,header};
 }
 function parseWorkbook(book,meta={}){
  const dev=parseSheet(book,0,meta,'development'), docs=book.SheetNames.length>1?parseSheet(book,1,meta,'documentation'):{sheet:'',rows:[],weeks:[],header:0};
  return {...meta,sheet:dev.sheet,documentationSheet:docs.sheet,rows:dev.rows,docRows:docs.rows,weeks:dev.weeks,docWeeks:docs.weeks,sheets:book.SheetNames,importedAt:new Date().toISOString()};
 }
 const api={focus,labels,parseWorkbook};root.Plan=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
