const fs=require('fs');
global.XLSX=require('./dist/vendor/xlsx.full.min.js');
const {parseWorkbook}=require('./dist/plan.js');
const source=process.argv[2];
const data=parseWorkbook(XLSX.read(fs.readFileSync(source),{type:'buffer',cellDates:true,cellStyles:true}),{name:require('path').basename(source),modifiedAt:fs.statSync(source).mtime.toISOString(),mode:'published'});
data.observedAt=new Date().toISOString();
data.workbookBase64=fs.readFileSync(source).toString('base64');
fs.writeFileSync('dist/source.json',JSON.stringify(data));
console.log(JSON.stringify({sheet:data.sheet,rows:data.rows.length,sections:Object.fromEntries([...new Set(data.rows.map(r=>r.section))].map(s=>[s,data.rows.filter(r=>r.section===s).length]))}));
