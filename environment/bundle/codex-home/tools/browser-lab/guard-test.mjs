import {spawnSync} from 'node:child_process';import assert from 'node:assert/strict';import {node,base} from './runner.mjs';import path from 'node:path';
for(const args of [['--profile=C:\\not-used'],['--profile','C:\\not-used'],['--headed=true'],['--config=other.json'],['--session=other'],['-s=other'],['connect'],['close-all'],['-p','remote'],['-p=remote'],['close','--all']]){
 const r=spawnSync(node,[path.join(base,'runner.mjs'),'pw',path.join(base,'guard-test'),'guard',...args],{encoding:'utf8',windowsHide:true});assert.notEqual(r.status,0);assert.match(r.stderr,/overrides require/);
}
console.log('11 override guard tests passed');
