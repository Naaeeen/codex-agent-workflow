import {spawn} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
export const base=path.dirname(fileURLToPath(import.meta.url));
export const node=String.raw`{{CODEX_HOME}}\tools\agent-kit\runtime\node-v24.22.2-win-x64\node.exe`;
export const chrome=String.raw`{{TOOLS_ROOT}}/browser-lab/runtime/chrome-win64/chrome.exe`;
export function setup(workspace,session='lab') {
  if(!/^[a-zA-Z0-9_-]+$/.test(session)) throw Error('Invalid session');
  const root=path.resolve(workspace,session); fs.mkdirSync(root,{recursive:true});
  for(const p of ['home','local','temp','downloads','artifacts','.playwright']) fs.mkdirSync(path.join(root,p),{recursive:true});
  const env={...process.env};
  for(const k of Object.keys(env)) if(/^(AGENT_BROWSER_|PLAYWRIGHT_|BROWSER_USE_|BROWSERBASE_|BROWSERLESS_|AI_GATEWAY_)/.test(k)) delete env[k];
  Object.assign(env,{NO_UPDATE_NOTIFIER:'1',CI:'1',USERPROFILE:path.join(root,'home'),HOME:path.join(root,'home'),LOCALAPPDATA:path.join(root,'local'),APPDATA:path.join(root,'local'),TEMP:path.join(root,'temp'),TMP:path.join(root,'temp'),AGENT_BROWSER_NO_VERSION_CHECK:'1',AGENT_BROWSER_NO_AUTO_DIALOG:'1',AGENT_BROWSER_DEFAULT_TIMEOUT:'1500',AGENT_BROWSER_IDLE_TIMEOUT_MS:'60000',AGENT_BROWSER_DOWNLOAD_PATH:path.join(root,'downloads'),AGENT_BROWSER_SCREENSHOT_DIR:path.join(root,'artifacts')});
  const pwConfig=path.join(root,'pw-config.json'), abConfig=path.join(root,'ab-config.json');
  fs.writeFileSync(pwConfig,JSON.stringify({browser:{browserName:'chromium',isolated:true,launchOptions:{headless:true,executablePath:chrome}},outputDir:path.join(root,'artifacts'),timeouts:{action:1500,navigation:15000,expect:1500,idle:60000}}));
  fs.writeFileSync(abConfig,JSON.stringify({headed:false,executablePath:chrome,downloadPath:path.join(root,'downloads')}));
  return {root,env,pwConfig,abConfig,session};
}
export function run(ctx,tool,args,timeout=30000){
  const exe=tool==='pw'?node:path.join(base,'node_modules/agent-browser/bin/agent-browser-win32-x64.exe');
  const argv=tool==='pw'?[path.join(base,'node_modules/@playwright/cli/playwright-cli.js'),`-s=${ctx.session}`, ...args]:['--session',ctx.session,'--config',ctx.abConfig,...args];
  if(tool==='pw'&&args[0]==='open') argv.push('--config',ctx.pwConfig);
  return new Promise(resolve=>{const t=performance.now();let stdout='',stderr='',timedOut=false;const proc=spawn(exe,argv,{cwd:ctx.root,env:ctx.env,windowsHide:true}); const timer=setTimeout(()=>{timedOut=true;proc.kill();},timeout);proc.stdout.on('data',d=>stdout+=d);proc.stderr.on('data',d=>stderr+=d);proc.on('error',e=>stderr+=e.message);proc.on('close',code=>{clearTimeout(timer);resolve({tool,args,code,timedOut,ms:Math.round(performance.now()-t),stdout,stderr,outputBytes:Buffer.byteLength(stdout+stderr)});});});
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
 const [tool,workspace,session,...args]=process.argv.slice(2);
 if(!['pw','ab'].includes(tool)||!workspace||!session||!args.length) throw Error('Usage: node runner.mjs pw|ab workspace session command [args]');
 if(args.some(a=>/^(--(all|cdp|auto-connect|profile|persistent|provider|headed|config|extension|session)(=|$)|-p|-s(=|$)|attach$|connect$|close-all$|kill-all$)/.test(a))) throw Error('Connection/global/profile/session overrides require a separately reviewed invocation');
 const ctx=setup(workspace,session);const r=await run(ctx,tool,args); process.stdout.write(r.stdout);process.stderr.write(r.stderr);if(r.timedOut){const cleanup=await run(ctx,tool,['close']);process.stderr.write(`Timed out; owned-session close exit=${cleanup.code}, timedOut=${cleanup.timedOut}\n`);}process.exitCode=r.timedOut?124:r.code??1;
}
