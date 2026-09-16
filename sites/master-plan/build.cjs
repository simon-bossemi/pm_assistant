const fs=require('fs'),path=require('path');
const root=__dirname,dist=path.join(root,'dist');
const extensions={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.txt':'text/plain; charset=utf-8'};
const assets={};
for(const f of fs.readdirSync(dist)){if(fs.statSync(path.join(dist,f)).isFile()&&extensions[path.extname(f)])assets['/'+f]={body:fs.readFileSync(path.join(dist,f),'utf8'),type:extensions[path.extname(f)]};}
for(const f of fs.readdirSync(path.join(dist,'vendor')))assets['/vendor/'+f]={body:fs.readFileSync(path.join(dist,'vendor',f),'utf8'),type:extensions[path.extname(f)]||'text/plain'};
fs.mkdirSync(path.join(dist,'server'),{recursive:true});fs.mkdirSync(path.join(dist,'.openai'),{recursive:true});
fs.writeFileSync(path.join(dist,'server','assets.mjs'),'export const assets='+JSON.stringify(assets)+';\n');
fs.copyFileSync(path.join(root,'server','worker.mjs'),path.join(dist,'server','index.js'));
fs.copyFileSync(path.join(root,'.openai','hosting.json'),path.join(dist,'.openai','hosting.json'));
fs.cpSync(path.join(root,'drizzle'),path.join(dist,'.openai','drizzle'),{recursive:true});
console.log('Built Worker and '+Object.keys(assets).length+' assets with D1 migrations.');
