const fs=require('fs'),path=require('path');
const dist=path.join(__dirname,'dist');
global.XLSX=require(path.join(dist,'vendor/xlsx.full.min.js'));
const {parseWorkbook}=require(path.join(dist,'plan.js'));
const source=process.argv[2],docSource=process.argv[3]||source;
if(!source)throw new Error('Pass the development workbook, then the documentation workbook.');
const data=parseWorkbook(XLSX.read(fs.readFileSync(source),{type:'buffer',cellDates:true,cellStyles:true}),{name:path.basename(source),modifiedAt:fs.statSync(source).mtime.toISOString(),mode:'published'});
if(docSource!==source){
 const docs=parseWorkbook(XLSX.read(fs.readFileSync(docSource),{type:'buffer',cellDates:true,cellStyles:true}));
 if(docs.documentationSheet!=='Eagle-N B0 Doc Delivery Plan')throw new Error('Documentation workbook is missing Eagle-N B0 Doc Delivery Plan.');
 data.docRows=docs.docRows;data.docWeeks=docs.docWeeks;data.documentationSheet=docs.documentationSheet;
 data.documentationName=path.basename(docSource);data.documentationModifiedAt=fs.statSync(docSource).mtime.toISOString();
 data.docWorkbookBase64=fs.readFileSync(docSource).toString('base64');
}
data.observedAt=new Date().toISOString();
data.workbookBase64=fs.readFileSync(source).toString('base64');
fs.writeFileSync(path.join(dist,'source.json'),JSON.stringify(data));
console.log(JSON.stringify({sheet:data.sheet,developmentRows:data.rows.length,documentationSheet:data.documentationSheet,documentationRows:data.docRows.length,developmentKeys:new Set(data.rows.map(r=>r.key).filter(Boolean)).size,documentationKeys:new Set(data.docRows.map(r=>r.key).filter(Boolean)).size}));
