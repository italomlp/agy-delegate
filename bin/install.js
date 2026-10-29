#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const readline = require('node:readline/promises');
const { spawn, spawnSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const helper = path.join(root, 'agy-delegate.py');
const target = path.join(os.homedir(), '.local', 'bin', 'agy-delegate');
const skill = path.join(root, 'skills', 'agy-delegate');
const receipt = path.join(os.homedir(), '.local', 'share', 'agy-delegate', 'installer.json');
const legacyHashes = new Set([
 'ebd3309921c3420dd21ff210b79eba826be0ffd04210ecf2b85bfe19170809ae',
 '4296374cfc72eb4eb820bfb218a8608cbb4e2da047696d2994b56237b4d1d900',
 '82f1097423dd1e650e1386a7366ff1303957804899fca58bebb6d4973ad9f9f5',
]);
function hash(file) { return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'); }
function managed(file) {
 if (!fs.existsSync(file) || fs.lstatSync(file).isSymbolicLink() || !fs.lstatSync(file).isFile()) return false;
 const digest=hash(file);
 if (digest===hash(helper) || legacyHashes.has(digest)) return true;
 try { return JSON.parse(fs.readFileSync(receipt,'utf8')).helperSha256===digest; } catch { return false; }
}
function saveReceipt() {
 fs.mkdirSync(path.dirname(receipt),{recursive:true});
 const temp=receipt+'.'+process.pid+'.tmp';
 try { fs.writeFileSync(temp,JSON.stringify({helperSha256:hash(target)})+'\n',{mode:0o600,flag:'wx'}); fs.renameSync(temp,receipt); }
 finally { try { fs.unlinkSync(temp); } catch(e) { if(e.code!=='ENOENT') throw e; } }
}
function usage() {
 console.log('Usage: npx agy-delegate [--global|--project] [--agent NAME ...] [--yes]\n       npx agy-delegate uninstall [--yes]\n\nWithout options, choose scope and agents interactively.');
}
function same(a,b) { return fs.readFileSync(a).equals(fs.readFileSync(b)); }
function locate(name) { const r=spawnSync(name, ['--version'], {stdio:'ignore'}); return !r.error && r.status===0; }
function skills(args) {
 const override=process.env.AGY_DELEGATE_SKILLS_BIN;
 const command=override || process.execPath;
 const cmdArgs=override ? args : [require.resolve('skills/bin/cli.mjs'), ...args];
 return new Promise((resolve, reject) => {
  const child=spawn(command,cmdArgs,{stdio:['inherit','pipe','inherit']});
  let tail='';
  child.stdout.on('data', chunk => { process.stdout.write(chunk); tail=(tail+chunk.toString()).slice(-16384); });
  child.on('error',reject);
  child.on('close',code => resolve(code === 0 && /installation cancelled/i.test(tail) ? 1 : (code ?? 1)));
 });
}
async function main() {
 const args=process.argv.slice(2); let action='install', scope=null, yes=false, agents=[];
 if (args[0]==='uninstall') { action='uninstall'; args.shift(); }
 while(args.length) {
  const arg=args.shift();
  if(arg==='--help'||arg==='-h') { usage(); return 0; }
  if(arg==='--yes'||arg==='-y') yes=true;
  else if(arg==='--global'||arg==='--project') { if(scope && scope!==arg.slice(2)) throw Error('Choose one scope.'); scope=arg.slice(2); }
  else if(arg==='--agent'||arg==='-a') { const name=args.shift(); if(!name||name.startsWith('-')) throw Error('--agent requires a name.'); agents.push(name); }
  else throw Error('Unknown option: '+arg);
 }
 if(action==='uninstall') {
  if(fs.existsSync(target)) {
   if(!managed(target)) throw Error('Helper is not a recognized unmodified installation and was preserved: '+target);
   if(!yes) { if(!process.stdin.isTTY) throw Error('Use --yes to uninstall noninteractively.'); const rl=readline.createInterface({input:process.stdin,output:process.stdout}); const reply=await rl.question('Remove unchanged helper at '+target+'? [y/N] '); rl.close(); if(!/^y(es)?$/i.test(reply.trim())) return 1; }
   fs.unlinkSync(target); console.log('Removed '+target);
  } else console.log('Helper not installed: '+target);
  console.log('Skill files and configuration were preserved. To remove the skill, inspect it first, then use: npx skills remove agy-delegate');
  return 0;
 }
 if(!locate('python3')) throw Error('Python 3 is required. Install it before continuing.');
 if(!locate(process.env.AGY_BIN||'agy')) console.error('Warning: agy was not found or could not start. Install and authenticate it before use.');
 console.log('Helper destination: '+target);
 if(!(process.env.PATH||'').split(path.delimiter).includes(path.dirname(target))) console.warn('Add '+path.dirname(target)+' to PATH to run agy-delegate.');
 if(fs.existsSync(target) && !managed(target)) throw Error('Existing helper is not a recognized unmodified installation and was preserved: '+target+'; move it aside after reviewing it.');
 if(!scope) {
  if(yes) throw Error('Specify --global or --project with --yes.');
  if(!process.stdin.isTTY) throw Error('Interactive input unavailable; specify --global or --project and --agent NAME --yes.');
  const rl=readline.createInterface({input:process.stdin,output:process.stdout});
  const answer=(await rl.question('Install skill globally or in this project? [global/project] (global): ')).trim().toLowerCase(); rl.close();
  if(answer && !['global','project'].includes(answer)) throw Error('Choose global or project.'); scope=answer||'global';
 }
 if(yes && !agents.length) throw Error('Specify at least one --agent with --yes.');
 const skillArgs=['add',skill,'--skill','agy-delegate','--copy'];
 if(scope==='global') skillArgs.push('--global');
 for(const agent of agents) skillArgs.push('--agent',agent);
 if(yes) skillArgs.push('--yes');
 console.log('Select agents in the skills installer.');
 const result=await skills(skillArgs);
 if(result!==0) { console.error('Skill installation did not complete; helper was not installed.'); return result; }
 fs.mkdirSync(path.dirname(target),{recursive:true});
 if(fs.existsSync(target) && !managed(target)) throw Error('Helper changed during installation; preserved: '+target);
 const temp=target+'.'+process.pid+'.tmp';
 try { fs.copyFileSync(helper,temp,fs.constants.COPYFILE_EXCL); fs.chmodSync(temp,0o755); fs.renameSync(temp,target); }
 finally { try { fs.unlinkSync(temp); } catch(e) { if(e.code!=='ENOENT') throw e; } }
 saveReceipt();
 console.log('Helper installed: '+target+'\nStart a new agent session. Automatic delegation depends on skill discovery and host policies.');
 return 0;
}
main().then(code=>process.exitCode=code).catch(err=>{console.error('agy-delegate:',err.message);process.exitCode=1;});
