import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {setup,run,base} from './runner.mjs';
const workspace=process.argv[2]; if(!workspace) throw Error('workspace argument required');
const html=`<!doctype html><html><head><title>Local browser fixture</title></head><body><h1>Browser fixture</h1><label>Name <input id="name"></label><label><input id="agree" type="checkbox"> Agree</label><button id="first" onclick="document.querySelector('#result').textContent='first'">Save</button><button id="second" onclick="document.querySelector('#result').textContent='second'">Save</button><p id="result">none</p><button id="dialog" onclick="document.querySelector('#dialog-result').textContent=confirm('Confirm fixture?')?'accepted':'dismissed'">Confirm</button><p id="dialog-result">none</p><iframe id="frame" title="Fixture frame" src="/frame"></iframe><a id="download" href="/download" download="fixture.txt">Download</a><button id="error" onclick="throw new Error('fixture expected error')">Error</button><script>setTimeout(()=>{const b=document.createElement('button');b.id='delayed';b.textContent='Delayed';b.onclick=()=>document.querySelector('#result').textContent='delayed';document.body.append(b)},700)</script></body></html>`;
const server=http.createServer((req,res)=>{if(req.url==='/download'){res.writeHead(200,{'Content-Type':'text/plain','Content-Disposition':'attachment; filename=fixture.txt'});res.end('browser-lab-download\n');}else {res.setHeader('Content-Type','text/html');res.end(req.url==='/frame'?'<button id="frame-button" onclick="this.textContent=\'Frame clicked\'">Frame button</button>':html);}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));const url=`http://127.0.0.1:${server.address().port}`;
const all=[];const checks=[];
async function suite(tool){const ctx=setup(workspace,tool);const calls=[];const command=async(...args)=>{const r=await run(ctx,tool,args);calls.push(r);console.log(`${tool} ${args[0]}: ${r.code}, ${r.ms}ms`);return r;};const ok=async(label,args,pattern)=>{const r=await command(...args);assert.equal(r.code,0,JSON.stringify(r));if(pattern)assert.match(r.stdout,pattern);checks.push({tool,label,pass:true});return r;};
try{
await ok('open',['open',url]);
const snap=await ok('snapshot',['snapshot']);
const snapText=snap.stdout;
const nameRef=snapText.match(/textbox "Name\s*" \[ref=(\w+)\]/)[1];
await ok('explicit-delayed-wait',tool==='pw'?['run-code',`async page => { await page.locator('#delayed').waitFor({timeout:2000}); }`]:['wait','#delayed','--timeout','2000']);
await ok('trace-start',[tool==='pw'?'tracing-start':'trace',...(tool==='pw'?[]:['start'])]);
if(tool==='pw'){
 await ok('input',['fill',nameRef,'Ada']);await ok('checkbox',['check','#agree']);await ok('duplicate-target',['click','#second']);await ok('duplicate-assert',['run-code',`async page => { if(await page.locator('#result').textContent() !== 'second') throw Error('duplicate selection'); }`]);await ok('delayed',['click','#delayed']);
 await ok('assert-state',['run-code',`async page => { if(await page.locator('#name').inputValue() !== 'Ada') throw Error('name'); if(!await page.locator('#agree').isChecked()) throw Error('checkbox'); if(await page.locator('#result').textContent() !== 'delayed') throw Error('delayed'); }`]);
 await ok('iframe',['run-code',`async page => { await page.frameLocator('#frame').locator('#frame-button').click(); if(await page.frameLocator('#frame').locator('#frame-button').textContent()!=='Frame clicked') throw Error('frame'); }`]);
 await ok('dialog-click',['click','#dialog']); await ok('dialog-accept',['dialog-accept']);
 await ok('dialog-assert',['run-code',`async page => { if(await page.locator('#dialog-result').textContent() !== 'accepted') throw Error('dialog'); }`]);
 await ok('download',['run-code',`async page => { const [d] = await Promise.all([page.waitForEvent('download'),page.locator('#download').click()]); await d.saveAs(${JSON.stringify(path.join(ctx.root,'downloads/fixture.txt'))}); }`]);
}else{
 await ok('input',['fill','@'+nameRef,'Ada']);await ok('checkbox',['check','#agree']);await ok('duplicate-target',['click','#second']);await ok('duplicate-assert',['get','text','#result'],/second/);await ok('delayed',['click','#delayed']);
 await ok('assert-input',['get','value','#name'],/Ada/);await ok('assert-checkbox',['is','checked','#agree'],/true/);await ok('assert-delayed',['get','text','#result'],/delayed/);
 await ok('iframe',['frame','#frame']);await ok('iframe-click',['click','#frame-button']);await ok('iframe-assert',['get','text','#frame-button'],/Frame clicked/);await ok('main',['frame','main']);
 await ok('dialog-click',['click','#dialog']);await ok('dialog-accept',['dialog','accept']);await ok('dialog-assert',['get','text','#dialog-result'],/accepted/);
 const d=await command('download','#download',path.join(ctx.root,'downloads/fixture.txt'));checks.push({tool,label:'download',pass:d.code===0,error:d.stderr});
}
if(fs.existsSync(path.join(ctx.root,'downloads/fixture.txt'))){assert.equal(fs.readFileSync(path.join(ctx.root,'downloads/fixture.txt'),'utf8'),'browser-lab-download\n');checks.push({tool,label:'download-content',pass:true});}else checks.push({tool,label:'download-content',pass:false,error:'File absent'});
await ok('screenshot',['screenshot',...(tool==='ab'?[path.join(ctx.root,'artifacts/screenshot.png')]:[])]);
await ok('trace-stop',[tool==='pw'?'tracing-stop':'trace',...(tool==='pw'?[]:['stop',path.join(ctx.root,'artifacts/trace.json')])]);
await ok('expected-page-error',['click','#error']);const er=await command(...(tool==='pw'?['console','error']:['errors']));checks.push({tool,label:'error-retrieval',pass:er.code===0&&/fixture expected error/.test(er.stdout),output:er.stdout});
const missing=await command('click','#does-not-exist');assert.notEqual(missing.code,0,'missing selector must fail');assert.equal(missing.timedOut,false);checks.push({tool,label:'missing-exits-nonzero',pass:true});
const timeout=tool==='pw'?await command('run-code',`async page => { await page.locator('#does-not-exist').waitFor({timeout:500}); }`):await command('wait','#does-not-exist','--timeout','500');assert.notEqual(timeout.code,0);assert.match(timeout.stdout+timeout.stderr,/timeout|timed out/i);assert.equal(timeout.timedOut,false);checks.push({tool,label:'timeout-exits-nonzero',pass:true,ms:timeout.ms});
}catch(e){checks.push({tool,label:'suite',pass:false,error:e.message});console.error(e.message.slice(0,1200));}finally{const close=await command('close');checks.push({tool,label:'session-close',pass:close.code===0&&!close.timedOut});fs.writeFileSync(path.join(ctx.root,'calls.json'),JSON.stringify(calls,null,2));all.push({tool,commands:calls.length,outputBytes:calls.reduce((a,r)=>a+r.outputBytes,0),durationMs:calls.reduce((a,r)=>a+r.ms,0)});}}
try{await suite('pw');await suite('ab');}finally{server.close();fs.writeFileSync(path.join(workspace,'results.json'),JSON.stringify({url,all,checks},null,2));}
if(checks.some(c=>!c.pass))process.exitCode=1;
