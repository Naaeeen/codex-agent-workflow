import fs from 'node:fs';import path from 'node:path';import http from 'node:http';import assert from 'node:assert/strict';import {createRequire} from 'node:module';import {setup,run,chrome} from './runner.mjs';
const require=createRequire(import.meta.url);const {chromium}=require('playwright-core');
const workspace=process.argv[2];if(!workspace)throw Error('workspace required');fs.mkdirSync(workspace,{recursive:true});const results=[];const checks=[];let owner,p,pw,ab,endpoint;
const server=http.createServer((q,r)=>{r.setHeader('Content-Type','text/html');r.end('<title>CDP fixture</title><h1>Controlled local CDP</h1><button id="set" onclick="localStorage.setItem(\'lab\',\'shared\')">Set shared</button>')});
async function checked(ctx,tool,args){const r=await run(ctx,tool,args);results.push(r);assert.equal(r.code,0,JSON.stringify(r));return r;}
async function closeAttached(ctx,tool){if(!ctx)return;const r=await run(ctx,tool,['close']);results.push(r);checks.push({label:`${tool}-scoped-close`,pass:r.code===0&&!r.timedOut});}
try{
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
 const profile=path.join(workspace,'owned-profile');owner=await chromium.launchPersistentContext(profile,{headless:true,executablePath:chrome,args:['--remote-debugging-port=0','--remote-debugging-address=127.0.0.1']});
 p=owner.pages()[0];await p.goto(`http://127.0.0.1:${server.address().port}`);
 const port=fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').split('\n')[0];endpoint=`http://127.0.0.1:${port}`;
 pw=setup(workspace,'pw-cdp');fs.writeFileSync(pw.pwConfig,JSON.stringify({browser:{browserName:'chromium',cdpEndpoint:endpoint},outputDir:path.join(pw.root,'artifacts')}));
 for(const a of [['open'],['snapshot'],['run-code',`async page => { await page.goto(${JSON.stringify(p.url())}); await page.locator('#set').click(); }`]]) await checked(pw,'pw',a);
 checks.push({label:'pw-cdp-write-visible-to-owner',pass:await p.evaluate(()=>localStorage.getItem('lab'))==='shared'});
 await closeAttached(pw,'pw');pw=undefined;checks.push({label:'pw-close-preserves-owner',pass:!p.isClosed()});
 ab=setup(workspace,'ab-cdp');for(const a of [['connect',endpoint],['snapshot'],['eval','localStorage.getItem("lab")']]){const r=await checked(ab,'ab',a);if(a[0]==='eval')checks.push({label:'ab-cdp-read-shared-storage',pass:r.stdout.includes('shared')});}
 await closeAttached(ab,'ab');ab=undefined;checks.push({label:'ab-close-preserves-owner',pass:!p.isClosed()});
}catch(e){checks.push({label:'adapter-suite',pass:false,error:e.message});}finally{
 await closeAttached(pw,'pw');await closeAttached(ab,'ab');
 if(owner){try{await owner.close();checks.push({label:'owner-close',pass:true});}catch(e){checks.push({label:'owner-close',pass:false,error:e.message});}}
 server.close();fs.writeFileSync(path.join(workspace,'cdp-results.json'),JSON.stringify({endpoint,scope:'Local owned browser only; no cloud provider tested',results,checks},null,2));console.log(JSON.stringify(checks));
}
if(checks.some(c=>!c.pass))process.exitCode=1;
