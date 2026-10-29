const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const cli = path.resolve(__dirname, '../bin/install.js');
function fixture() {
 const home=fs.mkdtempSync(path.join(os.tmpdir(),'agy-install-test-'));
 const fake=path.join(home,'skills');
 fs.writeFileSync(fake, '#!/bin/sh\nprintf "%s\\n" "$@" > "$AGY_TEST_ARGS"\nexit "${AGY_TEST_EXIT:-0}"\n', {mode:0o755});
 const env={...process.env,HOME:home,AGY_DELEGATE_SKILLS_BIN:fake,AGY_TEST_ARGS:path.join(home,'args')};
 return {home,env, run:(args=[],input='')=>spawnSync(process.execPath,[cli,...args],{env,input,encoding:'utf8'})};
}
test('noninteractive install selects global agents and copies helper',()=>{
 const f=fixture(); const r=f.run(['--yes','--global','--agent','codex','--agent','opencode']); assert.equal(r.status,0,r.stderr); assert.ok(fs.existsSync(path.join(f.home,'.local/bin/agy-delegate'))); const args=fs.readFileSync(f.env.AGY_TEST_ARGS,'utf8'); assert.match(args,/--copy/); assert.match(args,/--global/); assert.match(args,/codex/); assert.match(args,/opencode/);
});
test('conflicting helper is not overwritten',()=>{
 const f=fixture(), dest=path.join(f.home,'.local/bin/agy-delegate'); fs.mkdirSync(path.dirname(dest),{recursive:true}); fs.writeFileSync(dest,'mine'); const r=f.run(['--yes','--global','--agent','codex']); assert.notEqual(r.status,0); assert.equal(fs.readFileSync(dest,'utf8'),'mine'); assert.equal(fs.existsSync(f.env.AGY_TEST_ARGS),false);
});
test('cancelled skill install does not install helper',()=>{
 const f=fixture(); f.env.AGY_TEST_EXIT='1'; const r=f.run(['--yes','--project','--agent','codex']); assert.notEqual(r.status,0); assert.equal(fs.existsSync(path.join(f.home,'.local/bin/agy-delegate')),false);
});
test('uninstall preserves modified helper',()=>{
 const f=fixture(), dest=path.join(f.home,'.local/bin/agy-delegate'); fs.mkdirSync(path.dirname(dest),{recursive:true}); fs.writeFileSync(dest,'modified'); const r=f.run(['uninstall','--yes']); assert.notEqual(r.status,0); assert.equal(fs.readFileSync(dest,'utf8'),'modified');
});
test('skills cancellation with zero exit does not install helper',()=>{
 const f=fixture(); fs.writeFileSync(f.env.AGY_DELEGATE_SKILLS_BIN,'#!/bin/sh\necho "Installation cancelled"\nexit 0\n',{mode:0o755}); const r=f.run(['--yes','--global','--agent','codex']); assert.notEqual(r.status,0); assert.equal(fs.existsSync(path.join(f.home,'.local/bin/agy-delegate')),false);
});
