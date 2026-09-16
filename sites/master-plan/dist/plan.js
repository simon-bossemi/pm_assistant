(function(root){
 'use strict';
 const focus=['Host SW','AI Model Dev. Tools','Ref. Models','SDK Installer'];
 const labels={G:'On track',R:'Risky',D:'Delayed','P-D':'Pre-silicon done',Done:'Done for B0',Unknown:'Not recorded'};
 function parseWorkbook(book,meta={}){
  const sheet=book.Sheets[book.SheetNames[0]], range=XLSX.utils.decode_range(sheet['!ref']||'A1');
  const cell=(r,c)=>sheet[XLSX.utils.encode_cell({r:r-1,c:c-1})];
  const val=(r,c)=>{const x=cell(r,c);return x?String(x.w??x.v??'').trim():''};
  const header=Array.from({length:Math.min(range.e.r+1,30)},(_,i)=>i+1).find(r=>val(r,1).replace(/\s/g,'').toLowerCase()==='level1'&&val(r,6)==='JIRA');
  if(!header||!val(header,3).includes('Features')||!val(header,7).includes('Status'))throw new Error('This file does not match the master-plan columns (Level1, features, JIRA and Status).');
  const date=(r,c)=>{const x=cell(r,c);if(!x)return '';if(x.t==='d')return new Date(x.v).toISOString().slice(0,10);if(x.t==='n'){const d=XLSX.SSF.parse_date_code(x.v,{date1904:!!book.Workbook?.WBProps?.date1904});if(d&&d.y>=2000&&d.y<2100)return `${d.y}-${String(d.m).padStart(2,'0')}-${String(d.d).padStart(2,'0')}`;}const t=val(r,c);return /^20\d\d-\d\d-\d\d/.test(t)?t.slice(0,10):t;};
  const yearText=Array.from({length:range.e.c+1},(_,i)=>val(header,i+1)).join('');
  let section='',group='',month='',year=Number(yearText.match(/20\d{2}/)?.[0]||2026),lastWeek=0;
  const weeks=[];
  for(let c=13;c<=range.e.c+1;c++){const w=val(header+2,c);if(!/^W\d+$/.test(w))continue;const n=Number(w.slice(1));if(n<lastWeek)year++;lastWeek=n;month=val(header+1,c)||month;weeks.push({column:c,week:w,month,year});}
  const rows=[];
  for(let r=header+3;r<=range.e.r+1;r++){
   let a=val(r,1),b=val(r,2);
   if(a){if(a==='Feature'&&val(r+1,1)==='Requirements')a='Feature Requirements';else if(a==='Requirements'&&section==='Feature Requirements')a=section;else if(a==='Dev. Spec.'||a==='Dev. Spec. Documents')a='Dev. Spec. Documents';else if(a==='Documents'&&section==='Dev. Spec. Documents')a=section;else if(a==='AI Model'||a==='AI Model Dev. Tools')a='AI Model Dev. Tools';else if(a==='Dev. Tools'&&section==='AI Model Dev. Tools')a=section;if(a!==section){section=a;group='';}}
   if(b){if(section==='Dev. Spec. Documents'&&/^\(|^for the parts/.test(b)){if(!group.includes(b)){const previous=group;group+=' '+b;for(let i=rows.length-1;i>=0&&rows[i].section===section&&rows[i].group===previous;i--)rows[i].group=group;}}else group=b;}
   const timeline=weeks.flatMap(w=>{const x=cell(r,w.column),text=val(r,w.column),fill=x?.s?.fgColor?.rgb||x?.s?.fill?.fgColor?.rgb||'',color=/^[0-9A-Fa-f]{6,8}$/.test(fill)&&!['FFFFFF','000000'].includes(fill.slice(-6))?fill.slice(-6):'';return text||color?[{...w,text,color}]:[];});
   const raw=Array.from({length:12},(_,c)=>val(r,c+1));
   if(!raw.some(Boolean)&&!timeline.length)continue;
   const ticket=val(r,6),key=ticket.match(/\b[A-Z][A-Z0-9]+-\d+\b/)?.[0]||'';
   const links=[];for(let c=1;c<=range.e.c+1;c++){const href=cell(r,c)?.l?.Target;if(href&&/^https?:\/\//i.test(href))links.push({column:XLSX.utils.encode_col(c-1),text:val(r,c)||href,url:href});}
   const status=val(r,7)||'Unknown';
   rows.push({id:'row-'+r,row:r,section,group,title:val(r,3)||b||(a?section:'Unspecified feature'),team:val(r,4),owner:val(r,5),ticket,key,url:links.find(x=>x.column==='F')?.url||(key?'https://bos-semi.atlassian.net/browse/'+key:''),status,preTarget:date(r,8),summary:val(r,9),sdk:val(r,10),preDue:date(r,11),due:date(r,12),timeline,links,raw});
  }
  if(!focus.every(s=>rows.some(r=>r.section===s)))throw new Error('One or more of the four focus sections could not be found. The current plan has been kept.');
  return {...meta,sheet:book.SheetNames[0],rows,weeks,importedAt:new Date().toISOString()};
 }
 const api={focus,labels,parseWorkbook};root.Plan=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
